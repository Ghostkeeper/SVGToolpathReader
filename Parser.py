#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import cura.Settings.ExtruderManager #To get settings from the active extruder.
import math #Computing curves and such.
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
		self.default_line_width = extruder_stack.getProperty("wall_line_width_0", "value")

	def extrude_arc(self, start_x, start_y, rx, ry, rotation, large_arc, sweep_flag, end_x, end_y):
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
		:return: A sequence of extrude commands that follow the arc.
		"""
		if start_x == end_x and start_y == end_y: #Nothing to draw.
			return
		rx = abs(rx)
		ry = abs(ry)
		if rx == 0 or ry == 0: #Invalid radius. Skip this arc.
			yield ExtrudeCommand.ExtrudeCommand(end_x, end_y, self.default_line_width)
			return
		if (end_x - start_x) * (end_x - start_x) + (end_y - start_y) * (end_y - start_y) <= self.resolution * self.resolution: #Too small to fit with higher resolution.
			yield ExtrudeCommand.ExtrudeCommand(end_x, end_y, self.default_line_width)
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
		end_angle = (start_angle + delta_angle) % (math.pi * 2)

		#Use Newton's method to find segments of the required length along the ellipsis, basically using binary search.
		current_x = start_x
		current_y = start_y
		while (current_x - end_x) * (current_x - end_x) + (current_y - end_y) * (current_y - end_y) > self.resolution * self.resolution: #While further than the resolution, make new points.
			lower_angle = start_angle #Regardless of in which direction the delta_angle goes.
			upper_angle = end_angle
			current_error = self.resolution
			new_x = current_x
			new_y = current_y
			while abs(current_error) > 0.001: #Continue until 1 micron error.
				new_angle = (lower_angle + upper_angle) / 2
				new_x = math.cos(new_angle) * rx
				new_x_temp = new_x
				new_y = math.sin(new_angle) * ry
				new_x = cos_rotation * new_x - sin_rotation * new_y
				new_y = sin_rotation * new_x_temp + cos_rotation * new_y
				new_x += cx
				new_y += cy
				current_step_2 = (new_x - current_x) * (new_x - current_x) + (new_y - current_y) * (new_y - current_y)
				current_error = math.sqrt(current_step_2) - self.resolution
				if current_error > 0: #Step is too far.
					upper_angle = new_angle
				else: #Step is not far enough.
					lower_angle = new_angle
			current_x = new_x
			current_y = new_y
			yield ExtrudeCommand.ExtrudeCommand(current_x, current_y, self.default_line_width)
		yield ExtrudeCommand.ExtrudeCommand(end_x, end_y, self.default_line_width)

	def parse(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses an XML element and returns the paths required to print said element.

		This function delegates the parsing to the correct specialist function.
		:param element: The element to print.
		:return: A sequence of commands necessary to print this element.
		"""
		if not element.tag.startswith(self._namespace):
			return #Ignore elements not in the SVG namespace.
		tag = element.tag[len(self._namespace):]
		if tag == "rect":
			yield from self.parseRect(element)
		elif tag == "svg":
			yield from self.parseSvg(element)
		else:
			UM.Logger.Logger.log("w", "Unknown element {element_tag}.".format(element_tag=tag))
			#SVG specifies that you should ignore any unknown elements.

	def parseSvg(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the SVG element, which basically concatenates all commands put forth
		by its children.
		:param element: The SVG element.
		:return: A sequence of commands necessary to print this element.
		"""
		for child in element:
			yield from self.parse(child)

	def parseRect(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses the Rect element.
		:param element: The Rect element.
		:return: A sequence of commands necessary to print this element.
		"""
		x = self.tryFloat(element.attrib, "x", 0)
		y = self.tryFloat(element.attrib, "y", 0)
		rx = self.tryFloat(element.attrib, "rx", 0)
		ry = self.tryFloat(element.attrib, "ry", 0)
		width = self.tryFloat(element.attrib, "width", 0)
		height = self.tryFloat(element.attrib, "height", 0)

		if width == 0 or height == 0:
			return #No surface, no print!
		rx = min(rx, width / 2) #Limit rounded corners to half the rectangle.
		ry = min(ry, height / 2)

		yield TravelCommand.TravelCommand(x=x + rx, y=y)
		yield ExtrudeCommand.ExtrudeCommand(x=x + width - rx, y=y)
		yield from self.extrude_arc(x + width - rx, y, rx, ry, 0, False, True, x + width, y + ry)
		yield ExtrudeCommand.ExtrudeCommand(x=x + width, y=y + height - ry)
		yield from self.extrude_arc(x + width, y + height - ry, rx, ry, 0, False, True, x + width - rx, y + height)
		yield ExtrudeCommand.ExtrudeCommand(x=x + rx, y=y + height)
		yield from self.extrude_arc(x + rx, y + height, rx, ry, 0, False, True, x, y + height - ry)
		yield ExtrudeCommand.ExtrudeCommand(x=x, y=y + ry)
		yield from self.extrude_arc(x, y + ry, rx, ry, 0, False, True, x + rx, y)

	def tryFloat(self, dictionary, attribute, default: float) -> float:
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