#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import copy #Copy nodes for <use> elements.
import cura.Settings.ExtruderManager #To get settings from the active extruder.
import importlib #To import the FreeType library.
import math #Computing curves and such.
import numpy #Transformation matrices.
import os.path #To import the FreeType library.
import re #Parsing D attributes of paths.
import sys #To import the FreeType library.
import typing
import UM.Logger #To log parse errors and warnings.
import UM.Platform #To select the correct fonts.
import xml.etree.ElementTree #Just typing.

from . import ExtrudeCommand
from . import TravelCommand

#Import FreeType into sys.modules so that the library can reference itself with absolute imports.
this_plugin_path = os.path.dirname(__file__)
freetype_path = os.path.join(this_plugin_path, "freetype", "__init__.py")
spec = importlib.util.spec_from_file_location("freetype", freetype_path)
freetype_module = importlib.util.module_from_spec(spec)
sys.modules["freetype"] = freetype_module
spec.loader.exec_module(freetype_module)
import freetype

class Parser:
	"""
	Parses an SVG file.
	"""

	_namespace = "{http://www.w3.org/2000/svg}" #Namespace prefix for all SVG elements.
	_xlink_namespace = "{http://www.w3.org/1999/xlink}" #Namespace prefix for XLink references within the document.

	def __init__(self):
		extruder_stack = cura.Settings.ExtruderManager.ExtruderManager.getInstance().getActiveExtruderStack()
		self.resolution = extruder_stack.getProperty("meshfix_maximum_resolution", "value")

		self.system_fonts = {"Times New Roman", "Arial", "MonoType Corsova", "Impact", "Courier New", "Segoe UI"} #TODO: Detect system fonts.
		if UM.Platform.Platform.isWindows():
			self.safe_fonts = {
				"serif": "Times New Roman",
				"sans-serif": "Arial",
				"cursive": "MonoType Corsova",
				"fantasy": "Impact",
				"monospace": "Courier New",
				"system-ui": "Segoe UI"
			}
		elif UM.Platform.Platform.isOSX():
			self.safe_fonts = {
				"serif": "Times",
				"sans-serif": "Helvetica",
				"cursive": "Apple Chancery",
				"fantasy": "Papyrus",
				"monospace": "Courier",
				"system-ui": ".SF NS Text"
			}
		elif UM.Platform.Platform.isLinux():
			self.safe_fonts = { #Linux has its safe fonts available through the system fc-match system, which automatically redirects it to the system's preference.
				"serif": "serif",
				"sans-serif": "sans-serif",
				"cursive": "cursive",
				"fantasy": "fantasy",
				"monospace": "monospace",
				"system-ui": "system-ui"
			}

	def apply_transformation(self, x, y, transformation) -> typing.Tuple[float, float]:
		"""
		Apply a transformation matrix on some coordinates.
		:param x: The X coordinate of the position to transform.
		:param y: The Y coordinate of the position to transform.
		:param transformation: A transformation matrix to transform this
		coordinate by.
		:return: The transformed X and Y coordinates.
		"""
		position = numpy.array(((float(x), float(y), 1)))
		new_position = numpy.matmul(transformation, position)
		return new_position[0], new_position[1]

	def convert_css(self, css) -> typing.Dict[str, str]:
		"""
		Obtains the CSS properties that we can use from a piece of CSS.
		:param css: The piece of CSS to parse.
		:return: A dictionary containing all CSS attributes that we can parse
		that were discovered in the CSS string.
		"""
		is_float = lambda s: re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s) is not None
		tautology = lambda s: True
		attribute_validate = { #For each supported attribute, a predicate to validate whether it is correctly formed.
			"stroke-width": is_float,
			"transform": tautology,
			"font-family": tautology
		}
		result = {}

		pieces = css.split(";")
		for piece in pieces:
			piece = piece.strip()
			for attribute in attribute_validate:
				if piece.startswith(attribute + ":"):
					piece = piece[len(attribute) + 1:]
					piece = piece.strip()
					if attribute_validate[attribute](piece): #Only store the attribute if it has a valid value.
						result[attribute] = piece

		return result

	def convert_float(self, dictionary, attribute, default: float) -> float:
		"""
		Parses an attribute as float, if possible.

		If impossible or missing, this returns the default.
		:param dictionary: The attributes dictionary to get the attribute from.
		:param attribute: The attribute to get from the dictionary.
		:param default: The default value for this attribute.
		:return: A floating point number that was in the attribute, or the default.
		"""
		try:
			return float(dictionary.get(attribute, default))
		except ValueError: #Not parsable as float.
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

		for font in fonts:
			if font in self.safe_fonts:
				font = self.safe_fonts[font]
			if font in self.system_fonts:
				return font
		return self.safe_fonts["sans-serif"] #None of these fonts are available.

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
		if len(points) % 2 != 0: #If we have an odd number of points, leave out the last.
			points = points[:-1]

		for x, y in (points[i:i + 2] for i in range(0, len(points), 2)):
			yield x, y

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
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, -values[1]), (0, 1, -values[2]), (0, 0, 1))))
				transformation = numpy.matmul(transformation, numpy.array(((math.cos(values[0] / 180 * math.pi), -math.sin(values[0] / 180 * math.pi), 0), (math.sin(values[0] / 180 * math.pi), math.cos(values[0] / 180 * math.pi), 0), (0, 0, 1))))
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, values[1]), (0, 1, -values[2]), (0, 0, 1))))
			elif name == "skew":
				if len(values) != 2:
					continue #Invalid: Needs 2 arguments.
				transformation = numpy.matmul(transformation, numpy.array(((1, math.tan(values[0] / 180 * math.pi), 0), (math.tan(values[1] / 180 * math.pi), 1, 0), (0, 0, 1))))
			elif name == "skewx":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, math.tan(values[0] / 180 * math.pi), 0), (0, 1, 0), (1, 0, 0))))
			elif name == "skewy":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(transformation, numpy.array(((1, 0, 0), (math.tan(values[0] / 180 * math.pi), 1, 0), (1, 0, 0))))
			else:
				continue #Invalid: Unrecognised transformation operation (or 3D).

		return transformation

	def defaults(self, element) -> None:
		"""
		Sets the defaults for some properties on the document root.
		:param element: The document root.
		"""
		extruder_stack = cura.Settings.ExtruderManager.ExtruderManager.getInstance().getActiveExtruderStack()

		if "stroke-width" not in element.attrib:
			element.attrib["stroke-width"] = extruder_stack.getProperty("wall_line_width_0", "value")
		if "transform" not in element.attrib:
			element.attrib["transform"] = ""

	def dereference_uses(self, element, definitions) -> None:
		"""
		Finds all <use> elements and dereferences them.

		This needs to happen recursively (not just with one XPath query) because
		the definitions themselves may again use other definitions.

		If the uses are recursing infinitely, this currently freezes the loading
		thread. TODO: Track the current stack to check for circular references.
		:param element: The scope within a document within which to find uses of
		definitions to replace them.
		:param definitions: The definitions to search through, indexed by their
		IDs.
		"""
		for use in element.findall(self._namespace + "use"): #TODO: This is case-sensitive. The SVG specification says that is correct, but the rest of this implementation is not sensitive.
			link = use.attrib.get(self._xlink_namespace + "href")
			link = use.attrib.get("href", link)
			if link is None:
				UM.Logger.Logger.log("w", "Encountered <use> element without href!")
				continue
			if not link.startswith("#"):
				UM.Logger.Logger.log("w", "SVG document links to {link}, which is outside of this document.".format(link=link))
				#TODO: To support this, we need to:
				#TODO:  - Reference the URL relative to this document.
				#TODO:  - Download the URL if it is not local.
				#TODO:  - Open and parse the document's XML to fetch different definitions.
				#TODO:  - Fetch the correct subelement from the resulting document, for the fragment of the URL.
				continue
			link = link[1:]
			if link not in definitions:
				UM.Logger.Logger.log("w", "Reference to unknown element with ID: {link}".format(link=link))
				continue
			element_copy = copy.deepcopy(definitions[link])
			transform = use.attrib.get("transform", "")
			if transform:
				element_transform = element_copy.attrib.get("transform", "")
				element_copy.attrib["transform"] = transform + " " + element_transform
			x = use.attrib.get("x", "0")
			y = use.attrib.get("y", "0")
			element_transform = element_copy.attrib.get("transform", "")
			element_copy.attrib["transform"] = "translate({x},{y}) ".format(x=x, y=y) + element_transform
			element.append(element_copy)
			element.remove(use)

		for child in element: #Recurse (after dereferencing uses).
			self.dereference_uses(child, definitions)

	def extrude_arc(self, start_x, start_y, rx, ry, rotation, large_arc, sweep_flag, end_x, end_y, line_width, transformation) -> typing.Generator[ExtrudeCommand.ExtrudeCommand, None, None]:
		"""
		Yields points of an elliptical arc spaced at the required resolution.

		The parameters of the arc include the starting X,Y coordinates as well
		as all of the parameters of an A command in an SVG path.
		:param start_x: The X coordinate where the arc starts.
		:param start_y: The Y coordinate where the arc starts.
		:param rx: The X radius of the ellipse to follow.
		:param ry: The Y radius of the ellipse to follow.
		:param rotation: The rotation angle of the ellipse in radians.
		:param large_arc: Whether to take the longest way around or the shortest
		side of the ellipse.
		:param sweep_flag: On which side of the path the centre of the ellipse
		will be.
		:param end_x: The X coordinate of the final position to end up at.
		:param end_y: The Y coordinate of the final position to end up at.
		:param line_width: The width of the lines to extrude with.
		:param transformation: A transformation matrix to apply to the arc.
		:return: A sequence of extrude commands that follow the arc.
		"""
		if start_x == end_x and start_y == end_y: #Nothing to draw.
			return
		rx = abs(rx)
		ry = abs(ry)
		if rx == 0 or ry == 0: #Invalid radius. Skip this arc.
			yield ExtrudeCommand.ExtrudeCommand(end_x, end_y, line_width)
			return
		start_tx, start_ty = self.apply_transformation(start_x, start_y, transformation)
		end_tx, end_ty = self.apply_transformation(end_x, end_y, transformation)
		if (end_tx - start_tx) * (end_tx - start_tx) + (end_ty - start_ty) * (end_ty - start_ty) <= self.resolution * self.resolution: #Too small to fit with higher resolution.
			yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width)
			return

		#Implementation of https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes to find centre of ellipse.
		#Based off: https://stackoverflow.com/a/12329083
		sin_rotation = math.sin(rotation / 180 * math.pi)
		cos_rotation = math.cos(rotation / 180 * math.pi)
		x1 = cos_rotation * (start_x - end_x) / 2.0 + sin_rotation * (start_y - end_y) / 2.0
		y1 = cos_rotation * (start_y - end_y) / 2.0 + sin_rotation * (start_x - end_x) / 2.0
		lambda_multiplier = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
		if lambda_multiplier > 1:
			rx *= math.sqrt(lambda_multiplier)
			ry *= math.sqrt(lambda_multiplier)
		sum_squares = rx * y1 * rx * y1 + ry * x1 * ry * x1
		coefficient = math.sqrt(abs((rx * ry * rx * ry - sum_squares) / sum_squares))
		if large_arc == sweep_flag:
			coefficient = -coefficient
		cx_original = coefficient * rx * y1 / ry
		cy_original = -coefficient * ry * x1 / rx
		cx = cos_rotation * cx_original - sin_rotation * cy_original + (start_x + end_x) / 2.0
		cy = sin_rotation * cx_original + cos_rotation * cy_original + (start_y + end_y) / 2.0
		xcr_start = (x1 - cx_original) / rx
		xcr_end = (x1 + cx_original) / rx
		ycr_start = (y1 - cy_original) / ry
		ycr_end = (y1 + cy_original) / ry

		mod = math.sqrt(xcr_start * xcr_start + ycr_start * ycr_start)
		start_angle = math.acos(xcr_start / mod)
		if ycr_start < 0:
			start_angle = -start_angle
		dot = -xcr_start * xcr_end - ycr_start * ycr_end
		mod = math.sqrt((xcr_start * xcr_start + ycr_start * ycr_start) * (xcr_end * xcr_end + ycr_end * ycr_end))
		delta_angle = math.acos(dot / mod)
		if xcr_start * ycr_end - ycr_start * xcr_end < 0:
			delta_angle = -delta_angle
		delta_angle %= math.pi * 2
		if not sweep_flag:
			delta_angle -= math.pi * 2
		end_angle = start_angle + delta_angle

		#Use Newton's method to find segments of the required length along the ellipsis, basically using binary search.
		current_x = start_x
		current_y = start_y
		current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
		while (current_tx - end_tx) * (current_tx - end_tx) + (current_ty - end_ty) * (current_ty - end_ty) > self.resolution * self.resolution: #While further than the resolution, make new points.
			lower_angle = start_angle #Regardless of in which direction the delta_angle goes.
			upper_angle = end_angle
			current_error = self.resolution
			new_x = current_x
			new_y = current_y
			new_angle = lower_angle
			while abs(current_error) > 0.001: #Continue until 1 micron error.
				new_angle = (lower_angle + upper_angle) / 2
				if new_angle == lower_angle or new_angle == upper_angle: #Get out of infinite loop if we're ever stuck.
					break
				new_x = math.cos(new_angle) * rx
				new_x_temp = new_x
				new_y = math.sin(new_angle) * ry
				new_x = cos_rotation * new_x - sin_rotation * new_y
				new_y = sin_rotation * new_x_temp + cos_rotation * new_y
				new_x += cx
				new_y += cy
				new_tx, new_ty = self.apply_transformation(new_x, new_y, transformation)
				current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
				current_step = math.sqrt((new_tx - current_tx) * (new_tx - current_tx) + (new_ty - current_ty) * (new_ty - current_ty))
				current_error = current_step - self.resolution
				if current_error > 0: #Step is too far.
					upper_angle = new_angle
				else: #Step is not far enough.
					lower_angle = new_angle
			current_x = new_x
			current_y = new_y
			current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
			yield ExtrudeCommand.ExtrudeCommand(current_tx, current_ty, line_width)
			start_angle = new_angle
		yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width)

	def extrude_cubic(self, start_x, start_y, handle1_x, handle1_y, handle2_x, handle2_y, end_x, end_y, line_width, transformation) -> typing.Generator[ExtrudeCommand.ExtrudeCommand, None, None]:
		"""
		Yields points of a cubic (Bézier) arc spaced at the required resolution.

		A cubic arc takes three adjacent line segments (from start to handle1,
		from handle1 to handle2 and from handle2 to end) and varies a parameter
		p. Along the first and second line segment, a point is drawn at the
		ratio p between the segment's start and end. A line segment is drawn
		between these sliding points, and another point is made at a ratio of p
		along this line segment. That point follows a quadratic curve. Then the
		same thing is done for the second and third line segments, creating
		another point that follows a quadratic curve. Between these two points,
		a last line segment is drawn and a final point is drawn at a ratio of p
		along this line segment. As p varies from 0 to 1, this final point moves
		along the cubic curve.
		:param start_x: The X coordinate where the curve starts.
		:param start_y: The Y coordinate where the curve starts.
		:param handle1_x: The X coordinate of the first handle.
		:param handle1_y: The Y coordinate of the first handle.
		:param handle2_x: The X coordinate of the second handle.
		:param handle2_y: The Y coordinate of the second handle.
		:param end_x: The X coordinate where the curve ends.
		:param end_y: The Y coordinate where the curve ends.
		:param line_width: The width of the line to extrude.
		:param transformation: A transformation matrix to apply to the curve.
		:return: A sequence of commands necessary to print this curve.
		"""
		current_x = start_x
		current_y = start_y
		current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
		end_tx, end_ty = self.apply_transformation(end_x, end_y, transformation)
		p_min = 0
		p_max = 1
		while (current_tx - end_tx) * (current_tx - end_tx) + (current_ty - end_ty) * (current_ty - end_ty) > self.resolution * self.resolution: #Keep stepping until we're closer than one step from our goal.
			#Find the value for p that gets us exactly one step away (after transformation).
			new_x = current_x
			new_y = current_y
			new_error = self.resolution
			new_p = p_min
			while abs(new_error) > 0.001: #Continue until 1 micron error.
				#Graduate towards smaller steps first.
				#This is necessary because the cubic curve can loop back on itself and the halfway point may be beyond the intersection.
				#If we were to try a high p value that happens to fall very close to the starting point due to the loop,
				#we would think that the p is not high enough even though it is actually too high and thus skip the loop.
				#With cubic curves, that looping point can never occur at 1/4 of the curve or earlier, so try 1/4 of the parameter.
				new_p = (p_min * 3 + p_max) / 4
				if new_p == p_min or new_p == p_max: #Get out of infinite loop if we're ever stuck.
					break
				#Calculate the three points on the linear segments.
				linear1_x = start_x + new_p * (handle1_x - start_x)
				linear1_y = start_y + new_p * (handle1_y - start_y)
				linear2_x = handle1_x + new_p * (handle2_x - handle1_x)
				linear2_y = handle1_y + new_p * (handle2_y - handle1_y)
				linear3_x = handle2_x + new_p * (end_x - handle2_x)
				linear3_y = handle2_y + new_p * (end_y - handle2_y)
				#Calculate the two points on the quadratic curves.
				quadratic1_x = linear1_x + new_p * (linear2_x - linear1_x)
				quadratic1_y = linear1_y + new_p * (linear2_y - linear1_y)
				quadratic2_x = linear2_x + new_p * (linear3_x - linear2_x)
				quadratic2_y = linear2_y + new_p * (linear3_y - linear2_y)
				#Interpolate on the line between those points to get the final cubic position for new_p.
				new_x = quadratic1_x + new_p * (quadratic2_x - quadratic1_x)
				new_y = quadratic1_y + new_p * (quadratic2_y - quadratic1_y)
				new_tx, new_ty = self.apply_transformation(new_x, new_y, transformation)
				new_error = math.sqrt((new_tx - current_tx) * (new_tx - current_tx) + (new_ty - current_ty) * (new_ty - current_ty)) - self.resolution
				if new_error > 0: #Step is too far.
					p_max = new_p
				else: #Step is not far enough.
					p_min = new_p
			current_x = new_x
			current_y = new_y
			current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
			yield ExtrudeCommand.ExtrudeCommand(current_tx, current_ty, line_width)
			p_min = new_p
			p_max = 1
		yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width) #And the last step to end exactly on our goal.

	def extrude_quadratic(self, start_x, start_y, handle_x, handle_y, end_x, end_y, line_width, transformation) -> typing.Generator[ExtrudeCommand.ExtrudeCommand, None, None]:
		"""
		Yields points of a quadratic arc spaced at the required resolution.

		A quadratic arc takes two adjacent line segments (from start to handle
		and from handle to end) and varies a parameter p. Along each of these
		two line segments, a point is drawn at the ratio p between the segment's
		start and end. A line segment is drawn between these sliding points, and
		another point is made at a ratio of p along this line segment. As p
		varies from 0 to 1, this last point moves along the quadratic curve.
		:param start_x: The X coordinate where the curve starts.
		:param start_y: The Y coordinate where the curve starts.
		:param handle_x: The X coordinate of the handle halfway along the curve.
		:param handle_y: The Y coordinate of the handle halfway along the curve.
		:param end_x: The X coordinate where the curve ends.
		:param end_y: The Y coordinate where the curve ends.
		:param line_width: The width of the line to extrude.
		:param transformation: A transformation matrix to apply to the curve.
		:return: A sequence of commands necessary to print this curve.
		"""
		end_tx, end_ty = self.apply_transformation(end_x, end_y, transformation)
		#First check if handle lies exactly between start and end. If so, we just draw one line from start to finish.
		if start_x == end_x:
			if handle_x == start_x and (start_y <= handle_y <= end_y or start_y >= handle_y >= end_y):
				yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width)
				return
		elif start_y == end_y:
			if handle_y == start_y and (start_x <= handle_x <= end_x or start_x >= handle_x >= end_x):
				yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width)
				return
		else:
			slope_deviation = (handle_x - start_x) / (end_x - start_x) - (handle_y - start_y) / (end_y - start_y)
			if abs(slope_deviation) == 0:
				if start_x <= handle_x <= end_x or start_x >= handle_x >= end_x:
					yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width)
					return

		current_x = start_x
		current_y = start_y
		current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
		p_min = 0
		p_max = 1
		while (current_tx - end_tx) * (current_tx - end_tx) + (current_ty - end_ty) * (current_ty - end_ty) > self.resolution * self.resolution: #Keep stepping until we're closer than one step from our goal.
			#Find the value for p that gets us exactly one step away (after transformation).
			new_x = current_x
			new_y = current_y
			new_error = self.resolution
			new_p = p_min
			while abs(new_error) > 0.001: #Continue until 1 micron error.
				new_p = (p_min + p_max) / 2
				if new_p == p_min or new_p == p_max: #Get out of infinite loop if we're ever stuck.
					break
				#Calculate the two points on the linear segments.
				linear1_x = start_x + new_p * (handle_x - start_x)
				linear1_y = start_y + new_p * (handle_y - start_y)
				linear2_x = handle_x + new_p * (end_x - handle_x)
				linear2_y = handle_y + new_p * (end_y - handle_y)
				#Interpolate on the line between those points to get the final quadratic position for new_p.
				new_x = linear1_x + new_p * (linear2_x - linear1_x)
				new_y = linear1_y + new_p * (linear2_y - linear1_y)
				new_tx, new_ty = self.apply_transformation(new_x, new_y, transformation)
				new_error = math.sqrt((new_tx - current_tx) * (new_tx - current_tx) + (new_ty - current_ty) * (new_ty - current_ty)) - self.resolution
				if new_error > 0: #Step is too far.
					p_max = new_p
				else: #Step is not far enough.
					p_min = new_p
			current_x = new_x
			current_y = new_y
			current_tx, current_ty = self.apply_transformation(current_x, current_y, transformation)
			yield ExtrudeCommand.ExtrudeCommand(current_tx, current_ty, line_width)
			p_min = new_p
			p_max = 1
		yield ExtrudeCommand.ExtrudeCommand(end_tx, end_ty, line_width) #And the last step to end exactly on our goal.

	def find_definitions(self, element) -> typing.Dict[str, xml.etree.ElementTree.Element]:
		"""
		Finds all element definitions in an element tree.
		:param element: An element whose descendants we must register.
		:return: A dictionary mapping element IDs to their elements.
		"""
		definitions = {}
		for definition in element.findall(".//*[@id]"):
			definitions[definition.attrib["id"]] = definition
		return definitions

	def inheritance(self, element) -> None:
		"""
		Pass inherited properties of elements down through the node tree.

		Some properties, if not specified by child elements, should be taken
		from parent elements.

		This also parses the style property and turns it into the corresponding
		attributes.
		:param element: The parent element whose attributes have to be applied
		to all descendants.
		"""
		css = {} #Dictionary of all the attributes that we'll track.

		#Special case CSS entries that have an SVG attribute.
		if "transform" in element.attrib:
			css["transform"] = element.attrib["transform"]
		if "stroke-width" in element.attrib:
			try:
				css["stroke-width"] = str(float(element.attrib["stroke-width"]))
			except ValueError: #Not parseable as float.
				pass

		#Find <style> subelements and add them to our CSS.
		for child in element:
			if child.tag.lower() == self._namespace + "style":
				style_css = self.convert_css(child.text)
				css.update(style_css) #Merge into main CSS file, overwriting attributes if necessary.

		#CSS in the 'style' attribute overrides <style> element and separate attributes.
		if "style" in element.attrib:
			style_css = self.convert_css(element.attrib["style"])
			css.update(style_css)
			del element.attrib["style"]

		#Put all CSS attributes in the attrib dict, even if they are not normally available in SVG. It'll be easier to parse there if we keep it separated.
		tracked_css = {"stroke-width", "transform"}
		for attribute in css:
			element.attrib[attribute] = css[attribute]

		#Pass CSS on to children.
		for child in element:
			for attribute in css:
				if attribute == "transform": #Transform is special because it adds on to the children's transforms.
					if "transform" not in child.attrib:
						child.attrib["transform"] = ""
					child.attrib["transform"] = css["transform"] + " " + child.attrib["transform"]
				else:
					if attribute not in child.attrib:
						child.attrib[attribute] = css[attribute]
			self.inheritance(child)

	def parse(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses an XML element and returns the paths required to print said
		element.

		This function delegates the parsing to the correct specialist function.
		:param element: The element to print.
		:return: A sequence of commands necessary to print this element.
		"""
		if not element.tag.lower().startswith(self._namespace):
			return #Ignore elements not in the SVG namespace.
		tag = element.tag[len(self._namespace):].lower()
		if tag == "circle":
			yield from self.parse_circle(element)
		elif tag == "defs":
			return #Ignore defs.
		elif tag == "ellipse":
			yield from self.parse_ellipse(element)
		elif tag == "g":
			yield from self.parse_g(element)
		elif tag == "line":
			yield from self.parse_line(element)
		elif tag == "path":
			yield from self.parse_path(element)
		elif tag == "polygon":
			yield from self.parse_polygon(element)
		elif tag == "polyline":
			yield from self.parse_polyline(element)
		elif tag == "rect":
			yield from self.parse_rect(element)
		elif tag == "svg":
			yield from self.parse_svg(element)
		elif tag == "switch":
			yield from self.parse_switch(element)
		elif tag == "text":
			yield from self.parse_text(element)
		else:
			UM.Logger.Logger.log("w", "Unknown element {element_tag}.".format(element_tag=tag))
			#SVG specifies that you should ignore any unknown elements.

	def parse_circle(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Circle element.
		:param element: The Circle element.
		:return: A sequence of commands necessary to print this element.
		"""
		cx = self.convert_float(element.attrib, "cx", 0)
		cy = self.convert_float(element.attrib, "cy", 0)
		r = self.convert_float(element.attrib, "r", 0)
		if r == 0:
			return #Circles without radius don't exist here.
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))

		tx, ty = self.apply_transformation(cx + r, cy, transformation)
		yield TravelCommand.TravelCommand(x=tx, y=ty)
		yield from self.extrude_arc(cx + r, cy, r, r, 0, False, False, cx, cy - r, line_width, transformation)
		yield from self.extrude_arc(cx, cy - r, r, r, 0, False, False, cx - r, cy, line_width, transformation)
		yield from self.extrude_arc(cx - r, cy, r, r, 0, False, False, cx, cy + r, line_width, transformation)
		yield from self.extrude_arc(cx, cy + r, r, r, 0, False, False, cx + r, cy, line_width, transformation)

	def parse_ellipse(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Ellipse element.
		:param element: The Ellipse element.
		:return: A sequence of commands necessary to print this element.
		"""
		cx = self.convert_float(element.attrib, "cx", 0)
		cy = self.convert_float(element.attrib, "cy", 0)
		rx = self.convert_float(element.attrib, "rx", 0)
		if rx == 0:
			return #Ellipses without radius don't exist here.
		ry = self.convert_float(element.attrib, "ry", 0)
		if ry == 0:
			return
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))

		tx, ty = self.apply_transformation(cx + rx, cy, transformation)
		yield TravelCommand.TravelCommand(x=tx, y=ty)
		yield from self.extrude_arc(cx + rx, cy, rx, ry, 0, False, False, cx, cy - ry, line_width, transformation)
		yield from self.extrude_arc(cx, cy - ry, rx, ry, 0, False, False, cx - rx, cy, line_width, transformation)
		yield from self.extrude_arc(cx - rx, cy, rx, ry, 0, False, False, cx, cy + ry, line_width, transformation)
		yield from self.extrude_arc(cx, cy + ry, rx, ry, 0, False, False, cx + rx, cy, line_width, transformation)

	def parse_g(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the G element.

		This element simply passes on its attributes to its children.
		:param element: The G element.
		:return: A sequence of commands necessary to print this element.
		"""
		for child in element:
			yield from self.parse(child)

	def parse_line(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Line element.

		This element creates a line from one coordinate to another.
		:param element: The Line element.
		:return: A sequence of commands necessary to print this element.
		"""
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))
		x1 = self.convert_float(element.attrib, "x1", 0)
		y1 = self.convert_float(element.attrib, "y1", 0)
		x2 = self.convert_float(element.attrib, "x2", 0)
		y2 = self.convert_float(element.attrib, "y2", 0)

		x1, y1 = self.apply_transformation(x1, y1, transformation)
		x2, y2 = self.apply_transformation(x2, y2, transformation)
		yield TravelCommand.TravelCommand(x=x1, y=y1)
		yield ExtrudeCommand.ExtrudeCommand(x=x2, y=y2, line_width=line_width)

	def parse_path(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Path element.

		This element creates arbitrary curves. It is as powerful as all the
		other elements put together!
		:param element: The Path element.
		:return: A sequence of commands necessary to print this element.
		"""
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))
		d = element.attrib.get("d", "")
		x = 0 #Starting position.
		y = 0

		d = d.replace(",", " ")
		d = d.strip()

		start_x = 0 #Track movement command for Z command to return to beginning.
		start_y = 0
		previous_quadratic_x = 0 #Track the previous curve handle of Q commands for the T command.
		previous_quadratic_y = 0 #This is always absolute!
		previous_cubic_x = 0 #And for the second cubic handle of C commands for the S command, too.
		previous_cubic_y = 0

		#Since all commands in the D attribute are single-character letters, we can split the thing on alpha characters and process each command separately.
		commands = re.findall(r"[A-Za-z][^A-Za-z]*", d)
		for command in commands:
			command = command.strip()
			command_name = command[0]
			command = command[1:]
			parameters = [float(match) for match in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", command)] #Ignore parameters that are not properly formatted floats.

			#Process M and m commands first since they can have some of their parameters apply to different commands.
			if command_name == "M": #Move.
				if len(parameters) < 2:
					continue #Not enough parameters to the M command. Skip it.
				x = parameters[0]
				y = parameters[1]
				tx, ty = self.apply_transformation(x, y, transformation)
				yield TravelCommand.TravelCommand(x=tx, y=ty)
				if len(parameters) >= 2:
					command_name = "L" #The next parameters are interpreted as being lines.
					parameters = parameters[2:]
				start_x = x #Start a new path.
				start_y = y
			if command_name == "m": #Move relatively.
				if len(parameters) < 2:
					continue #Not enough parameters to the m command. Skip it.
				x += parameters[0]
				y += parameters[1]
				tx, ty = self.apply_transformation(x, y, transformation)
				yield TravelCommand.TravelCommand(x=tx, y=ty)
				if len(parameters) >= 2:
					command_name = "l" #The next parameters are interpreted as being relative lines.
					parameters = parameters[2:]
				start_x = x #Start a new path.
				start_y = y

			if command_name == "A": #Elliptical arc.
				while len(parameters) >= 7:
					if (parameters[3] != 0 and parameters[3] != 1) or (parameters[4] != 0 and parameters[4] != 1):
						parameters = parameters[7:]
						continue #The two flag parameters need to be 0 or 1, otherwise we won't be able to interpret them.
					parameters[3] = parameters[3] != 0 #Convert to boolean.
					parameters[4] = parameters[4] != 0
					yield from self.extrude_arc(start_x=x, start_y=y,
					                 rx=parameters[0], ry=parameters[1],
					                 rotation=parameters[2],
					                 large_arc=parameters[3], sweep_flag=parameters[4],
					                 end_x=parameters[5], end_y=parameters[6], line_width=line_width, transformation=transformation)
					x = parameters[5]
					y = parameters[6]
					parameters = parameters[7:]
			elif command_name == "a": #Elliptical arc to relative position.
				while len(parameters) >= 7:
					if (parameters[3] != 0 and parameters[3] != 1) or (parameters[4] != 0 and parameters[4] != 1):
						parameters = parameters[7:]
						continue #The two flag parameters need to be 0 or 1, otherwise we won't be able to interpret them.
					parameters[3] = parameters[3] != 0 #Convert to boolean.
					parameters[4] = parameters[4] != 0
					yield from self.extrude_arc(start_x=x, start_y=y,
					                 rx=parameters[0], ry=parameters[1],
					                 rotation=parameters[2],
					                 large_arc=parameters[3], sweep_flag=parameters[4],
					                 end_x=x + parameters[5], end_y=y + parameters[6], line_width=line_width, transformation=transformation)
					x += parameters[5]
					y += parameters[6]
					parameters = parameters[7:]
			elif command_name == "C": #Cubic curve (Bézier).
				while len(parameters) >= 6:
					previous_cubic_x = parameters[2]
					previous_cubic_y = parameters[3]
					yield from self.extrude_cubic(start_x=x, start_y=y,
					                              handle1_x=parameters[0], handle1_y=parameters[1],
					                              handle2_x=previous_cubic_x, handle2_y=previous_cubic_y,
					                              end_x=parameters[4], end_y=parameters[5],
					                              line_width=line_width, transformation=transformation)
					x = parameters[4]
					y = parameters[5]
					parameters = parameters[6:]
			elif command_name == "c": #Relative cubic curve (Bézier).
				while len(parameters) >= 6:
					previous_cubic_x = x + parameters[2]
					previous_cubic_y = y + parameters[3]
					yield from self.extrude_cubic(start_x=x, start_y=y,
					                              handle1_x=x + parameters[0], handle1_y=y + parameters[1],
					                              handle2_x=previous_cubic_x, handle2_y=previous_cubic_y,
					                              end_x=x + parameters[4], end_y=y + parameters[5],
					                              line_width=line_width, transformation=transformation)
					x += parameters[4]
					y += parameters[5]
					parameters = parameters[6:]
			elif command_name == "H": #Horizontal line.
				while len(parameters) >= 1:
					x = parameters[0]
					tx, ty = self.apply_transformation(x, y, transformation)
					yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
					parameters = parameters[1:]
			elif command_name == "h": #Relative horizontal line.
				while len(parameters) >= 1:
					x += parameters[0]
					tx, ty = self.apply_transformation(x, y, transformation)
					yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
					parameters = parameters[1:]
			elif command_name == "L": #Line.
				while len(parameters) >= 2:
					x = parameters[0]
					y = parameters[1]
					tx, ty = self.apply_transformation(x, y, transformation)
					yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
					parameters = parameters[2:]
			elif command_name == "l": #Relative line.
				while len(parameters) >= 2:
					x += parameters[0]
					y += parameters[1]
					tx, ty = self.apply_transformation(x, y, transformation)
					yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
					parameters = parameters[2:]
			elif command_name == "Q": #Quadratic curve.
				while len(parameters) >= 4:
					previous_quadratic_x = parameters[0]
					previous_quadratic_y = parameters[1]
					yield from self.extrude_quadratic(start_x=x, start_y=y,
					                                  handle_x=previous_quadratic_x, handle_y=previous_quadratic_y,
					                                  end_x=parameters[2], end_y=parameters[3],
					                                  line_width=line_width, transformation=transformation)
					x = parameters[2]
					y = parameters[3]
					parameters = parameters[4:]
			elif command_name == "q": #Relative quadratic curve.
				while len(parameters) >= 4:
					previous_quadratic_x = x + parameters[0]
					previous_quadratic_y = y + parameters[1]
					yield from self.extrude_quadratic(start_x=x, start_y=y,
					                                  handle_x=previous_quadratic_x, handle_y=previous_quadratic_y,
					                                  end_x=x + parameters[2], end_y=y + parameters[3],
					                                  line_width=line_width, transformation=transformation)
					x += parameters[2]
					y += parameters[3]
					parameters = parameters[4:]
			elif command_name == "S": #Smooth cubic curve (Bézier).
				while len(parameters) >= 4:
					#Mirror the handle around the current position.
					handle1_x = x + (x - previous_cubic_x)
					handle1_y = y + (y - previous_cubic_y)
					previous_cubic_x = parameters[0] #For the next curve, store the coordinates of the second handle.
					previous_cubic_y = parameters[1]
					yield from self.extrude_cubic(start_x=x, start_y=y,
					                              handle1_x=handle1_x, handle1_y=handle1_y,
					                              handle2_x=previous_cubic_x, handle2_y=previous_cubic_y,
					                              end_x=parameters[2], end_y=parameters[3],
					                              line_width=line_width, transformation=transformation)
					x = parameters[2]
					y = parameters[3]
					parameters = parameters[4:]
			elif command_name == "s": #Relative smooth cubic curve (Bézier).
				while len(parameters) >= 4:
					#Mirror the handle around the current position.
					handle1_x = x + (x - previous_cubic_x)
					handle1_y = y + (y - previous_cubic_y)
					previous_cubic_x = x + parameters[0] #For the next curve, store the coordinates of the second handle.
					previous_cubic_y = y + parameters[1]
					yield from self.extrude_cubic(start_x=x, start_y=y,
					                              handle1_x=handle1_x, handle1_y=handle1_y,
					                              handle2_x=previous_cubic_x, handle2_y=previous_cubic_y,
					                              end_x=x + parameters[2], end_y=y + parameters[3],
					                              line_width=line_width, transformation=transformation)
					x += parameters[2]
					y += parameters[3]
					parameters = parameters[4:]
			elif command_name == "T": #Smooth quadratic curve.
				while len(parameters) >= 2:
					#Mirror the handle around the current position.
					previous_quadratic_x = x + (x - previous_quadratic_x)
					previous_quadratic_y = y + (y - previous_quadratic_y)
					yield from self.extrude_quadratic(start_x=x, start_y=y,
					                                  handle_x=previous_quadratic_x, handle_y=previous_quadratic_y,
					                                  end_x=parameters[0], end_y=parameters[1],
					                                  line_width=line_width, transformation=transformation)
					x = parameters[0]
					y = parameters[1]
					parameters = parameters[2:]
			elif command_name == "t": #Relative smooth quadratic curve.
				while len(parameters) >= 2:
					#Mirror the handle around the current position.
					previous_quadratic_x = x + (x - previous_quadratic_x)
					previous_quadratic_y = y + (y - previous_quadratic_y)
					yield from self.extrude_quadratic(start_x=x, start_y=y,
					                                  handle_x=previous_quadratic_x, handle_y=previous_quadratic_y,
					                                  end_x=x + parameters[0], end_y=y + parameters[1],
					                                  line_width=line_width, transformation=transformation)
					x += parameters[0]
					y += parameters[1]
					parameters = parameters[2:]
			elif command_name == "V": #Vertical line.
				while len(parameters) >= 1:
					y = parameters[0]
					tx, ty = self.apply_transformation(x, y, transformation)
					yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
					parameters = parameters[1:]
			elif command_name == "v": #Relative vertical line.
				while len(parameters) >= 1:
					y += parameters[0]
					tx, ty = self.apply_transformation(x, y, transformation)
					yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
					parameters = parameters[1:]
			elif command_name == "Z" or command_name == "z":
				x = start_x
				y = start_y
				tx, ty = self.apply_transformation(x, y, transformation)
				yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
			else: #Unrecognised command, or M or m which we processed separately.
				pass

			if command_name != "Q" and command_name != "q" and command_name != "T" and command_name != "t":
				previous_quadratic_x = x
				previous_quadratic_y = y
			if command_name != "C" and command_name != "c" and command_name != "S" and command_name != "s":
				previous_cubic_x = x
				previous_cubic_y = y

	def parse_polygon(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Polygon element.

		This element lists a number of vertices past which to travel, and the
		polygon is closed at the end.
		:param element: The Polygon element.
		:return: A sequence of commands necessary to print this element.
		"""
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))

		first_x = None #Save these in order to get back to the starting coordinates. And to use a travel command.
		first_y = None
		for x, y in self.convert_points(element.attrib.get("points", "")):
			x, y = self.apply_transformation(x, y, transformation)
			if first_x is None or first_y is None:
				first_x = x
				first_y = y
				yield TravelCommand.TravelCommand(x=x, y=y)
			else:
				yield ExtrudeCommand.ExtrudeCommand(x=x, y=y, line_width=line_width)
		if first_x is not None and first_y is not None: #Close the polygon.
			yield ExtrudeCommand.ExtrudeCommand(x=first_x, y=first_y, line_width=line_width)

	def parse_polyline(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Polyline element.

		This element lists a number of vertices past which to travel. The line
		is not closed into a loop, contrary to the Polygon element.
		:param element: The Polyline element.
		:return: A sequence of commands necessary to print this element.
		"""
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))

		is_first = True #We must use a travel command for the first coordinate pair.
		for x, y in self.convert_points(element.attrib.get("points", "")):
			x, y = self.apply_transformation(x, y, transformation)
			if is_first:
				yield TravelCommand.TravelCommand(x=x, y=y)
				is_first = False
			else:
				yield ExtrudeCommand.ExtrudeCommand(x=x, y=y, line_width=line_width)

	def parse_rect(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Rect element.
		:param element: The Rect element.
		:return: A sequence of commands necessary to print this element.
		"""
		x = self.convert_float(element.attrib, "x", 0)
		y = self.convert_float(element.attrib, "y", 0)
		rx = self.convert_float(element.attrib, "rx", 0)
		ry = self.convert_float(element.attrib, "ry", 0)
		width = self.convert_float(element.attrib, "width", 0)
		height = self.convert_float(element.attrib, "height", 0)
		line_width = self.convert_float(element.attrib, "stroke-width", 0)
		transformation = self.convert_transform(element.attrib.get("transform", ""))

		if width == 0 or height == 0:
			return #No surface, no print!
		rx = min(rx, width / 2) #Limit rounded corners to half the rectangle.
		ry = min(ry, height / 2)
		tx, ty = self.apply_transformation(x + rx, y, transformation)
		yield TravelCommand.TravelCommand(x=tx, y=ty)
		tx, ty = self.apply_transformation(x + width - rx, y, transformation)
		yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
		yield from self.extrude_arc(x + width - rx, y, rx, ry, 0, False, True, x + width, y + ry, line_width, transformation)
		tx, ty = self.apply_transformation(x + width, y + height - ry, transformation)
		yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
		yield from self.extrude_arc(x + width, y + height - ry, rx, ry, 0, False, True, x + width - rx, y + height, line_width, transformation)
		tx, ty = self.apply_transformation(x + rx, y + height, transformation)
		yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
		yield from self.extrude_arc(x + rx, y + height, rx, ry, 0, False, True, x, y + height - ry, line_width, transformation)
		tx, ty = self.apply_transformation(x, y + ry, transformation)
		yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
		yield from self.extrude_arc(x, y + ry, rx, ry, 0, False, True, x + rx, y, line_width, transformation)

	def parse_svg(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the SVG element, which basically concatenates all commands put
		forth by its children.
		:param element: The SVG element.
		:return: A sequence of commands necessary to print this element.
		"""
		for child in element:
			yield from self.parse(child)

	def parse_switch(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Switch element, which can decide to show or not show its
		child elements based on if features are implemented or not.
		:param element: The Switch element.
		:return: A sequence of commands necessary to print this element.
		"""
		#For some of these features we're actually lying, since we support most of what the feature entails so for 99% of the files that use them it should be fine.
		supported_features = {
			"", #If there is no required feature, this will appear in the set.
			"http://www.w3.org/TR/SVG11/feature#SVG", #Since v1.0.0.
			"http://www.w3.org/TR/SVG11/feature#SVGDOM", #Since v1.0.0.
			"http://www.w3.org/TR/SVG11/feature#SVG-static", #Since v1.0.0.
			"http://www.w3.org/TR/SVG11/feature#SVGDOM-static", #Since v1.0.0.
			"http://www.w3.org/TR/SVG11/feature#Structure", #Actually unsupported: <symbol> and <use>.
			"http://www.w3.org/TR/SVG11/feature#BasicStructure", #Actually unsupported: <use>.
			"http://www.w3.org/TR/SVG11/feature#ConditionalProcessing", #Actually unsupported: requiredExtensions and systemLanguage.
			"http://www.w3.org/TR/SVG11/feature#Shape" #Since v1.0.0.
			"http://www.w3.org/TR/SVG11/feature#PaintAttribute" #Actually unsupported: stroke-dasharray and stroke-dashoffset.
			"http://www.w3.org/TR/SVG11/feature#BasicPaintAttribute" #Actually unsupported: stroke-dasharray and stroke-dashoffset.
			"http://www.w3.org/TR/SVG11/feature#ColorProfile" #Doesn't apply to g-code.
			"http://www.w3.org/TR/SVG11/feature#Gradient" #Doesn't apply to g-code.
		}
		required_features = element.attrib.get("requiredFeatures", "")
		required_features = {feature.strip() for feature in required_features.split(",")}

		if required_features - supported_features:
			return #Not all required features are supported.
		else:
			for child in element:
				yield from self.parse(child)

	def parse_text(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Text element, which writes a bit of text.
		:param element: The Text element.
		:return: A sequence of commands necessary to write the text.
		"""
		x = self.convert_float(element.attrib, "x", 0)
		y = self.convert_float(element.attrib, "y", 0)
		dx = self.convert_float(element.attrib, "dx", 0)
		dy = self.convert_float(element.attrib, "dy", 0)
		rotate = self.convert_float(element.attrib, "rotate", 0)
		length_adjust = element.attrib.get("lengthAdjust", "spacing")
		text_length = self.convert_float(element.attrib, "textLength", 0) #TODO: Support percentages.
		text = element.text

		face = freetype.Face("C:\\Windows\\Fonts\\coolvetica rg.ttf") #TODO: Use correct font, and don't hard-code it.
		face.set_char_size(48 * 64)
		for index, character in enumerate(text):
			face.load_char(character)
			outline = face.glyph.outline
			start = 0
			for contour_index in range(len(outline.contours)):
				end = outline.contours[contour_index]
				points = outline.points[start:end + 1]
				points.append(points[0]) #Close the polygon.
				tags = outline.tags[start:end + 1]
				tags.append(tags[0])

				segments = [[points[0]]]
				for point_index in range(1, len(points)):
					segments[-1].append(points[point_index])
					if tags[point_index] & (1 << 0) and point_index < (len(points) - 1): #MoveTo command, so a new segment.
						segments.append([points[point_index]])
				yield TravelCommand.TravelCommand(points[0][0] / 100, points[0][1] / 100)
				for segment in segments:
					if len(segment) == 2:
						yield ExtrudeCommand.ExtrudeCommand(segment[1][0] / 100, segment[1][1] / 100)
					elif len(segment) == 3:
						UM.Logger.Logger.log("d", "Cubic curve") #TODO.
					else:
						UM.Logger.Logger.log("d", "Multiple cubic curves") #TODO.

				start = end + 1