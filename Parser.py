#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import typing
import UM.Logger #To log parse errors and warnings.

from . import ExtrudeCommand
from . import TravelCommand

class Parser:
	"""
	Parses an SVG file.
	"""

	_namespace = "{http://www.w3.org/2000/svg}" #Namespace prefix for all SVG elements.

	def parse(self, element) -> typing.Generator[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand], None, None]:
		"""
		Parses an XML element and returns the paths required to print said element.

		This function delegates the parsing to the correct specialist function.
		:param element: The element to print.
		:return: A sequence of commands necessary to print this element.
		"""
		if element.tag == self._namespace + "rect":
			yield from self.parseRect(element)
		if element.tag == self._namespace + "svg":
			yield from self.parseSvg(element)
		else:
			UM.Logger.Logger.log("w", "Unknown element {element_tag}.".format(element_tag=element.tag))
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
		#TODO: Implement rx and ry.
		width = self.tryFloat(element.attrib, "width", 0)
		height = self.tryFloat(element.attrib, "height", 0)

		if width == 0 or height == 0:
			return #No surface, no print!

		yield TravelCommand.TravelCommand(x=x, y=y)
		yield ExtrudeCommand.ExtrudeCommand(x=x + width, y=y)
		yield ExtrudeCommand.ExtrudeCommand(x=x + width, y=y + width)
		yield ExtrudeCommand.ExtrudeCommand(x=x, y=y + width)
		yield ExtrudeCommand.ExtrudeCommand(x=x, y=y)

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