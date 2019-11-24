#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import collections  # For the named tuple.
import math  # For computing transformation matrices from Euclidean angles.
import numpy  # For computing transformation matrices.
import re  # For parsing the CSS source.
import typing
import UM.Logger  # Reporting parsing failures.

CSSAttribute = collections.namedtuple("CSSAttribute", [
	"name",  # The name of the attribute.
	"value",  # The current value of the attribute.
	"validate",  # A validation predicate for the attribute.
])

class CSS:
	"""
	Tracks and parses CSS attributes for an element.

	The main function of this class is to group together all CSS properties for
	an element. In order to construct it easily, it will also do the work of
	parsing the (supported) CSS attributes.
	"""

	def __init__(self, parser) -> None:
		"""
		Creates a new set of CSS attributes.

		The attributes are initialised to their defaults.
		:param parser: The parser that is currently parsing a document.
		"""
		self.parser = parser

		# Some re-usable validation functions
		is_float = lambda s: re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s) is not None
		tautology = lambda s: True
		is_list_of_lengths = lambda s: re.fullmatch(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(cap|ch|em|ex|ic|lh|rem|rlh|vh|vw|vi|vb|vmin|vmax|px|cm|mm|Q|in|pc|pt|%)?[,\s])*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)?(cap|ch|em|ex|ic|lh|rem|rlh|vh|vw|vi|vb|vmin|vmax|px|cm|mm|Q|in|pc|pt|%)?", s) is not None
		is_length = lambda s: re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(cap|ch|em|ex|ic|lh|rem|rlh|vh|vw|vi|vb|vmin|vmax|px|cm|mm|Q|in|pc|pt|%)?", s)

		self.attributes = {
			# Name                   Name again                            Default   Validation function
			"font-family":           CSSAttribute("font-family",           "serif",  tautology),
			"font-size":             CSSAttribute("font-size",             "12pt",   is_length),
			"font-style":            CSSAttribute("font-style",            "normal", lambda s: s in {"normal", "italic", "oblique", "initial"}),  # Don't include "inherit" since we want it to inherit then as if not set.
			"font-weight":           CSSAttribute("font-weight",           "400",    is_float),
			"stroke-dasharray":      CSSAttribute("stroke-dasharray",      "",       is_list_of_lengths),
			"stroke-dashoffset":     CSSAttribute("stroke-dashoffset",     "0",      is_length),
			"stroke-width":          CSSAttribute("stroke-width",          "0",      is_length),
			"text-decoration":       CSSAttribute("text-decoration",       "",       tautology),  # Not going to do any sort of validation on this one since it has all the colours and that's just way too complex.
			"text-decoration-line":  CSSAttribute("text-decoration-line",  "",       lambda s: all([part in {"none", "overline", "underline", "line-through", "initial"} for part in s.split()])),
			"text-decoration-style": CSSAttribute("text-decoration-style", "solid",  lambda s: s in {"solid", "double", "dotted", "dashed", "wavy", "initial"}),
			"text-transform":        CSSAttribute("text-transform",        "none",   lambda s: s in {"none", "capitalize", "uppercase", "lowercase", "initial"}),  # Don't include "inherit" again.
			"transform":             CSSAttribute("transform",             "",       tautology)  # Not going to do any sort of validation on this one because all the transformation functions make it very complex.
		}
		self.dasharray = []
		self.dasharray_length = 0

	def parse(self, css) -> None:
		"""
		Parse the supported CSS properties from a string of serialised CSS.

		The results are stored in this CSS instance.
		:param css: The piece of CSS to parse.
		"""
		pieces = css.split(";")
		for piece in pieces:
			piece = piece.strip()
			if ":" not in piece:  # Only parse well-formed CSS rules, which are key-value pairs separated by a colon.
				UM.Logger.Logger.log("w", "Ill-formed CSS rule: {piece}".format(piece=piece))
				continue
			attribute = piece[:piece.index(":")]
			value = piece[piece.index(":") + 1]
			if attribute not in self.attributes:
				UM.Logger.Logger.log("w", "Unknown CSS attribute {attribute}".format(attribute=attribute))
				continue
			if not self.attributes[attribute].validate(value):
				UM.Logger.Logger.log("w", "Invalid value for CSS attribute {attribute}: {value}".format(attribute=attribute, value=value))
				continue
			self.attributes[attribute].value = value

	def convert_dasharray(self, dasharray) -> None:
		"""
		Parses a stroke-dasharray property out of CSS.

		The length elements are converted into millimetres for extrusion.

		The result is stored in self.dasharray, to be used with the next drawn
		lines. Also, the total length is computed and stored in
		self.dasharray_length for re-use.
		:param dasharray: A stroke-dasharray property value.
		"""
		dasharray = dasharray.replace(",", " ")
		length_list = dasharray.split()
		self.dasharray = []
		self.dasharray_length = 0
		for length in length_list:
			length_mm = self.convert_length(length)
			if length_mm < 0:
				continue  # Invalid. Ignore this one.
			self.dasharray.append(length_mm)
			self.dasharray_length += length_mm
		if len(self.dasharray) % 2 == 1:  # Double the sequence so that every segment is the same w.r.t. which is extruded and which is travelled.
			self.dasharray *= 2
			self.dasharray_length *= 2

	def convert_length(self, dimension, vertical=False, parent_size=None) -> float:
		"""
		Converts a CSS dimension to millimetres.

		For pixels, this assumes a resolution of 96 dots per inch.
		:param dimension: A CSS dimension.
		:param vertical: The dimension is a vertical one, so it should be taken
		relative to other vertical dimensions for some units, such as the
		vertical size of the parent if using percentages.
		:param parent_size: The size in millimetres of the element that contains
		the element that we're getting the dimension for. If ``None``, this will
		be set to the printer's width.
		:return: How many millimetres long that dimension is.
		"""
		number = re.match(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", dimension)
		if not number:
			return 0
		number = number.group(0)
		unit = dimension[len(number):].strip().lower()
		number = float(number)

		if unit == "mm":
			return number
		elif unit == "px":
			return number / 96 * 25.4
		elif unit == "cm":
			return number * 10
		elif unit == "q":
			return number / 4
		elif unit == "in":
			return number * 25.4
		elif unit == "pc":
			return number * 12 / 72 * 25.4
		elif unit == "pt":
			return number / 72 * 25.4

		elif unit == "%":
			if parent_size is None:
				if vertical:
					parent_size = self.parser.image_h
				else:
					parent_size = self.parser.image_w
			return number / 100 * parent_size
		elif unit == "vh" or unit == "vb":
			return number / 100 * self.parser.image_w
		elif unit == "vw" or unit == "vi":
			return number / 100 * self.parser.image_h
		elif unit == "vmin":
			return number / 100 * min(self.parser.image_w, self.parser.image_h)
		elif unit == "vmax":
			return number / 100 * max(self.parser.image_w, self.parser.image_h)

		else:  # Assume viewport-units.
			if vertical:
				return number * self.parser.unit_h
			else:
				return number * self.parser.unit_w
		#TODO: Implement font-relative sizes.

	def convert_float(self, dictionary, attribute, default: float) -> float:
		"""
		Parses an attribute as float, if possible.

		If impossible or missing, this returns the default.
		:param dictionary: The attributes dictionary to get the attribute from.
		:param attribute: The attribute to get from the dictionary.
		:param default: The default value for this attribute, in case the
		value is missing or invalid.
		:return: A floating point number that was in the attribute, or the default.
		"""
		try:
			return float(dictionary.get(attribute, default))
		except ValueError:  # Not parsable as float.
			return default

	def convert_font_family(self, font_family) -> str:
		"""
		Parses a font-family, converting it to the file name of a single font
		that is installed on the system.
		:param font_family: The font-family property from CSS.
		:return: The file name of a font that is installed on the system that
		most closely approximates the desired font family.
		"""
		fonts = font_family.split(",")
		fonts = [font.strip() for font in fonts]

		self.parser.detect_fonts_thread.join()  # All fonts need to be in at this point.

		for font in fonts:
			if font in self.parser.safe_fonts:
				font = self.parser.safe_fonts[font]
			for candidate in self.parser.system_fonts:
				if font.lower() == candidate.lower():  # Case-insensitive matching.
					return candidate
		UM.Logger.Logger.log("w", "Desired fonts not available on the system: {family}".format(family=font_family))
		if self.parser.safe_fonts["serif"] in self.parser.system_fonts:
			return self.parser.safe_fonts["serif"]
		if self.parser.system_fonts:
			return next(iter(self.parser.system_fonts))  # Take an arbitrary font that is available. Running out of options, here!
		return "Noto Sans"  # Default font of Cura. Hopefully that gets installed somewhere.

	def convert_points(self, points) -> typing.Generator[typing.Tuple[float, float], None, None]:
		"""
		Parses a points attribute, turning it into a list of coordinate pairs.

		If there is a syntax error, that part of the points will get ignored.
		Other parts might still be included.
		:param points: A series of points.
		:return: A list of x,y pairs.
		"""
		points = points.replace(",", " ")
		while "  " in points:
			points = points.replace("  ", " ")
		points = points.strip()
		points = points.split()
		if len(points) % 2 != 0:  # If we have an odd number of points, leave out the last.
			points = points[:-1]

		for x, y in (points[i:i + 2] for i in range(0, len(points), 2)):
			try:
				yield float(x), float(y)
			except ValueError:  # Not properly formatted floats.
				continue

	def convert_transform(self, transform) -> numpy.ndarray:
		"""
		Parses a transformation attribute, turning it into a transformation
		matrix.

		If there is a syntax error somewhere in the transformation, that part of
		the transformation gets ignored. Other parts might still be applied.

		3D transformations are not supported.
		:param transform: A series of transformation commands.
		:return: A Numpy array that would apply the transformations indicated
		by the commands. The array is a 2D affine transformation (3x3).
		"""
		transformation = numpy.identity(3)

		transform = transform.replace(")", ") ") #Ensure that every command is separated by spaces, even though func(0.5)fanc(2) is allowed.
		while "  " in transform:
			transform = transform.replace("  ", " ")
		transform = transform.replace(", ", ",") #Don't split on commas.
		transform = transform.replace(" ,", ",")
		commands = transform.split()
		for command in commands:
			command = command.strip()
			if command == "none":
				continue #Ignore.
			if command == "initial":
				transformation = numpy.identity(3)
				continue

			if "(" not in command:
				continue #Invalid: Not a function.
			name_and_value = command.split("(")
			if len(name_and_value) != 2:
				continue #Invalid: More than one opening bracket.
			name, value = name_and_value
			name = name.strip().lower()
			if ")" not in value:
				continue #Invalid: Bracket not closed.
			value = value[:value.find(")")] #Ignore everything after closing bracket. Should be nothing due to splitting on spaces higher.
			values = [float(val) for val in value.replace(",", " ").split() if val]

			if name == "matrix":
				if len(values) != 6:
					continue #Invalid: Needs 6 arguments.
				transformation = numpy.matmul(transformation, numpy.array(((values[0], values[1], values[2]), (values[3], values[4], values[5]), (0, 0, 1))))
			elif name == "translate":
				if len(values) == 1:
					values.append(0)
				if len(values) != 2:
					continue #Invalid: Translate needs at least 1 and at most 2 arguments.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, values[0]), (0, 1, values[1]), (0, 0, 1))))
			elif name == "translatex":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, values[0]), (0, 1, 0), (0, 0, 1))))
			elif name == "translatey":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, 0), (0, 1, values[0]), (0, 0, 1))))
			elif name == "scale":
				if len(values) == 1:
					values.append(values[0]) #Y scale needs to be the same as X scale then.
				if len(values) != 2:
					continue #Invalid: Scale needs at least 1 and at most 2 arguments.
				transformation = numpy.matmul(transformation, numpy.array(((values[0], 0, 0), (0, values[1], 0), (0, 0, 1))))
			elif name == "scalex":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((values[0], 0, 0), (0, 1, 0), (0, 0, 1))))
			elif name == "scaley":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, 0), (0, values[0], 0), (0, 0, 1))))
			elif name == "rotate" or name == "rotatez": #Allow the 3D operation rotateZ as it simply rotates the 2D image in the same way.
				if len(values) == 1:
					values.append(0)
					values.append(0)
				if len(values) != 3:
					continue #Invalid: Rotate needs 1 or 3 arguments.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, values[1]), (0, 1, values[2]), (0, 0, 1))))
				transformation = numpy.matmul(transformation, numpy.array(((math.cos(values[0] / 180 * math.pi), -math.sin(values[0] / 180 * math.pi), 0), (math.sin(values[0] / 180 * math.pi), math.cos(values[0] / 180 * math.pi), 0), (0, 0, 1))))
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, -values[1]), (0, 1, -values[2]), (0, 0, 1))))
			elif name == "skew":
				if len(values) != 2:
					continue #Invalid: Needs 2 arguments.
				transformation = numpy.matmul(transformation, numpy.array(((1, math.tan(values[0] / 180 * math.pi), 0), (math.tan(values[1] / 180 * math.pi), 1, 0), (0, 0, 1))))
			elif name == "skewx":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, math.tan(values[0] / 180 * math.pi), 0), (0, 1, 0), (0, 0, 1))))
			elif name == "skewy":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, 0), (math.tan(values[0] / 180 * math.pi), 1, 0), (0, 0, 1))))
			else:
				continue #Invalid: Unrecognised transformation operation (or 3D).

		return transformation