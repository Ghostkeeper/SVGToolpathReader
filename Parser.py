#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import cura.Settings.ExtruderManager #To get settings from the active extruder.
import math #Computing curves and such.
import numpy #Transformation matrices.
import re #Parsing D attributes of paths.
import typing
import UM.Logger #To log parse errors and warnings.

from . import ExtrudeCommand
from . import TravelCommand

class Parser:
	"""
	Parses an SVG file.
	"""

	_namespace = "{http://www.w3.org/2000/svg}" #Namespace prefix for all SVG elements.

	def __init__(self):
		extruder_stack = cura.Settings.ExtruderManager.ExtruderManager.getInstance().getActiveExtruderStack()
		self.resolution = extruder_stack.getProperty("meshfix_maximum_resolution", "value")

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

	def consume_float(self, d) -> typing.Tuple[float, str]:
		"""
		Take a floating point number from a string, if it's in front.

		If there is no floating point in front, this raises a ValueError.
		:param d: A (part of a) d attribute of a path.
		:return: A tuple of the first floating point number, and the string with
		the floating point number consumed.
		"""
		number = re.search(r"^[-+]?\d*\.?\d+([eE][-+]?\d+)?", d)
		if not number:
			raise ValueError("This string doesn't start with a number: " + d[:10])
		number = number.group(0)
		return float(number), d[len(number):]

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
				transformation = numpy.matmul(numpy.array(((values[0], values[1], values[2]), (values[3], values[4], values[5]), (0, 0, 1))), transformation)
			elif name == "translate":
				if len(values) == 1:
					values.append(0)
				if len(values) != 2:
					continue #Invalid: Translate needs at least 1 and at most 2 arguments.
				transformation = numpy.matmul(numpy.array(((1, 0, values[0]), (0, 1, values[1]), (0, 0, 1))), transformation)
			elif name == "translatex":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(numpy.array(((1, 0, values[0]), (0, 1, 0), (0, 0, 1))), transformation)
			elif name == "translatey":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(numpy.array(((1, 0, 0), (0, 1, values[0]), (0, 0, 1))), transformation)
			elif name == "scale":
				if len(values) == 1:
					values.append(values[0]) #Y scale needs to be the same as X scale then.
				if len(values) != 2:
					continue #Invalid: Scale needs at least 1 and at most 2 arguments.
				transformation = numpy.matmul(numpy.array(((values[0], 0, 0), (0, values[1], 0), (0, 0, 1))), transformation)
			elif name == "scalex":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(numpy.array(((values[0], 0, 0), (0, 1, 0), (0, 0, 1))), transformation)
			elif name == "scaley":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(numpy.array(((1, 0, 0), (0, values[0], 0), (0, 0, 1))), transformation)
			elif name == "rotate" or name == "rotatez": #Allow the 3D operation rotateZ as it simply rotates the 2D image in the same way.
				if len(values) == 1:
					values.append(0)
					values.append(0)
				if len(values) != 3:
					continue #Invalid: Rotate needs 1 or 3 arguments.
				transformation = numpy.matmul(numpy.array(((1, 0, -values[1]), (0, 1, -values[2]), (0, 0, 1))), transformation)
				transformation = numpy.matmul(numpy.array(((math.cos(values[0] / 180 * math.pi), -math.sin(values[0] / 180 * math.pi), 0), (math.sin(values[0] / 180 * math.pi), math.cos(values[0] / 180 * math.pi), 0), (0, 0, 1))), transformation)
				transformation = numpy.matmul(numpy.array(((1, 0, values[1]), (0, 1, -values[2]), (0, 0, 1))), transformation)
			elif name == "skew":
				if len(values) != 2:
					continue #Invalid: Needs 2 arguments.
				transformation = numpy.matmul(numpy.array(((1, math.tan(values[0] / 180 * math.pi), 0), (math.tan(values[1] / 180 * math.pi), 1, 0), (0, 0, 1))), transformation)
			elif name == "skewx":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(numpy.array(((1, math.tan(values[0] / 180 * math.pi), 0), (0, 1, 0), (1, 0, 0))), transformation)
			elif name == "skewy":
				if len(values) != 1:
					continue #Invalid: Needs 1 argument.
				transformation = numpy.matmul(numpy.array(((1, 0, 0), (math.tan(values[0] / 180 * math.pi), 1, 0), (1, 0, 0))), transformation)
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
		if (end_x - start_x) * (end_x - start_x) + (end_y - start_y) * (end_y - start_y) <= self.resolution * self.resolution: #Too small to fit with higher resolution.
			yield ExtrudeCommand.ExtrudeCommand(end_x, end_y, line_width)
			return

		#Implementation of https://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes to find centre of ellipse.
		#Based off: https://stackoverflow.com/a/12329083
		sin_rotation = math.sin(rotation)
		cos_rotation = math.cos(rotation)
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
		current_x_transformed, current_y_transformed = self.apply_transformation(current_x, current_y, transformation)
		end_x_transformed, end_y_transformed = self.apply_transformation(end_x, end_y, transformation)
		while (current_x_transformed - end_x_transformed) * (current_x_transformed - end_x_transformed) + (current_y_transformed - end_y_transformed) * (current_y_transformed - end_y_transformed) > self.resolution * self.resolution: #While further than the resolution, make new points.
			lower_angle = start_angle #Regardless of in which direction the delta_angle goes.
			upper_angle = end_angle
			current_error = self.resolution
			new_x = current_x
			new_y = current_y
			new_angle = lower_angle
			while abs(current_error) > 0.001: #Continue until 1 micron error.
				new_angle = (lower_angle + upper_angle) / 2
				new_x = math.cos(new_angle) * rx
				new_x_temp = new_x
				new_y = math.sin(new_angle) * ry
				new_x = cos_rotation * new_x - sin_rotation * new_y
				new_y = sin_rotation * new_x_temp + cos_rotation * new_y
				new_x += cx
				new_y += cy
				new_x_transformed, new_y_transformed = self.apply_transformation(new_x, new_y, transformation)
				current_x_transformed, current_y_transformed = self.apply_transformation(current_x, current_y, transformation)
				current_step = math.sqrt((new_x_transformed - current_x_transformed) * (new_x_transformed - current_x_transformed) + (new_y_transformed - current_y_transformed) * (new_y_transformed - current_y_transformed))
				current_error = current_step - self.resolution
				if current_error > 0: #Step is too far.
					upper_angle = new_angle
				else: #Step is not far enough.
					lower_angle = new_angle
			current_x = new_x
			current_y = new_y
			current_x_transformed, current_y_transformed = self.apply_transformation(current_x, current_y, transformation)
			yield ExtrudeCommand.ExtrudeCommand(current_x_transformed, current_y_transformed, line_width)
			start_angle = new_angle
		end_x_transformed, end_y_transformed = self.apply_transformation(end_x, end_y, transformation)
		yield ExtrudeCommand.ExtrudeCommand(end_x_transformed, end_y_transformed, line_width)

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
		stroke_width = None
		transform = element.attrib.get("transform")
		if "stroke-width" in element.attrib:
			try:
				stroke_width = str(float(element.attrib["stroke-width"]))
			except ValueError: #Not parsable as float.
				pass

		if "style" in element.attrib: #CSS overrides attribute.
			css = element.attrib["style"]
			pieces = css.split(";")
			for piece in pieces:
				piece = piece.strip()
				if piece.startswith("stroke-width:"):
					piece = piece[len("stroke-width:"):]
					piece = piece.strip()
					try:
						stroke_width = str(float(piece))
					except ValueError: #Not parsable as float.
						pass #Leave it at the default or the attribute.
				elif piece.startswith("transform:"):
					piece = piece[len("transform:"):]
					transform = piece.strip()
			del element.attrib["style"]
		if stroke_width is not None:
			element.attrib["stroke-width"] = stroke_width
		if transform is not None:
			element.attrib["transform"] = transform

		for child in element:
			if stroke_width is not None and "stroke-width" not in child.attrib:
				child.attrib["stroke-width"] = stroke_width
			if transform is not None:
				if "transform" not in child.attrib:
					child.attrib["transform"] = ""
				child.attrib["transform"] = transform + " " + child.attrib["transform"]
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

		#We're going to consume the D parameter front-to-back, which re-creates a slightly smaller string every time.
		#This is quadratic! TODO: Fix that up.
		while d != "":
			if d[0] == "M": #Move.
				d = d[1:].strip()
				try:
					new_x, d = self.consume_float(d)
					d = d.strip()
					new_y, d = self.consume_float(d)
					d = d.strip()
				except ValueError:
					continue #Not enough parameters to the M command. Skip it.
				x = new_x
				y = new_y
				tx, ty = self.apply_transformation(x, y, transformation)
				yield TravelCommand.TravelCommand(x=tx, y=ty)
				try:
					_, _ = self.consume_float(d) #See if next up is another float.
					#No error? Then it is a new float. Add an L command in front so that next coordinate pairs get interpreted as lines.
					d = "L" + d
				except ValueError: #Not another coordinate pair. Just continue parsing the next command then.
					continue
			elif d[0] == "m": #Move (relative).
				d = d[1:].strip()
				try:
					dx, d = self.consume_float(d)
					d = d.strip()
					dy, d = self.consume_float(d)
				except ValueError:
					continue #Not enough parameters to the m command. Skip it.
				x += dx
				y += dy
				tx, ty = self.apply_transformation(x, y, transformation)
				yield TravelCommand.TravelCommand(x=tx, y=ty)
				try:
					_, _ = self.consume_float(d) #See if next up is another float.
					#No error? Then it is a new float. Add an l command in front so that next coordinate pairs get interpreted as relative lines.
					d = "l" + d
				except ValueError: #Not another coordinate pair. Just continue parsing the next command then.
					continue
			elif d[0] == "L": #Line.
				d = d[1:].strip()
				try:
					while True: #Until interrupted by ValueError.
						new_x, new_d = self.consume_float(d)
						new_d = new_d.strip()
						new_y, d = self.consume_float(new_d)
						x = new_x
						y = new_y
						tx, ty = self.apply_transformation(x, y, transformation)
						yield ExtrudeCommand.ExtrudeCommand(x=tx, y=ty, line_width=line_width)
				except ValueError:
					continue #Not enough parameters for another coordinate pair. Skip it.
			else: #Unrecognised command.
				#TODO: Implement H, h, V, v, A, a, C, c, S, s, Q, q, T, t, Z and z.
				d = d[1:].strip()

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
		Parses the SVG element, which basically concatenates all commands put forth
		by its children.
		:param element: The SVG element.
		:return: A sequence of commands necessary to print this element.
		"""
		for child in element:
			yield from self.parse(child)