#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import typing
import UM.Logger #To log parse errors and warnings.

from . import ExtrudeCommand
from . import TravelCommand

def parse(element) -> typing.Iterable[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand]]:
	"""
	Parses an XML element and returns the paths required to print said element.

	This function delegates the parsing to the correct specialist function.
	:param element: The element to print.
	:return: A sequence of commands necessary to print this element.
	"""
	if element.tag == "svg":
		return parseSvg(element)
	else:
		UM.Logger.Logger.log("w", "Unknown element {element_tag}.".format(element_tag=element.tag))
		return [] #SVG specifies that you should ignore any unknown elements.

def parseSvg(element) -> typing.Iterable[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand]]:
	"""
	Parses the SVG element, which basically concatenates all commands put forth
	by its children.
	:param element: The SVG element.
	:return: A sequence of commands necessary to print this element.
	"""
	for child in element:
		yield parse(child)