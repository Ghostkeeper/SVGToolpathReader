#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import cura.LayerDataBuilder
import typing

def write_gcode(commands) -> typing.Tuple[str, cura.LayerDataBuilder.LayerDataBuilder]:
	"""
	Converts a list of commands into g-code.
	:param commands: The list of extrude and travel commands to write.
	:return: A g-code string that would print the commands, as well as a layer
	data builder that represents the same file for layer view.
	"""
	return ("", cura.LayerDataBuilder.LayerDataBuilder()) #TODO: Implement.