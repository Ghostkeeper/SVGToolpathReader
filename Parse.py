#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import typing

from . import ExtrudeCommand
from . import TravelCommand

def parse(element) -> typing.List[typing.Union[TravelCommand.TravelCommand, ExtrudeCommand.ExtrudeCommand]]:
	"""
	Parses an XML element and returns the paths required to print said element.
	:param element: The element to print.
	:return: A list of commands necessary to print this element.
	"""
	return list() #TODO: Implement.