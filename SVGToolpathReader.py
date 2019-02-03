#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import UM.Mesh.MeshReader #The class we're extending.
import UM.MimeTypeDatabase #Register the SVG MIME type.

class SVGToolpathReader(UM.Mesh.MeshReader.MeshReader):
	"""
	Interface class between Cura and the logic to read SVG files as toolpath.
	"""

	def __init__(self):
		"""
		Register the SVG extension upon start-up.
		"""
		super().__init__()
		self._supported_extensions = ["svg"]
		UM.MimeTypeDatabase.MimeTypeDatabase.addMimeType(UM.MimeTypeDatabase.MimeType(name="image/svg+xml", comment="Scalable Vector Graphics", suffixes=self._supported_extensions))

	def _read(self, file_name) -> None:
		"""
		Read the specified SVG file.

		The toolpath represented by the file gets put in the current scene as g-code.
		:param file_name: The name of the file to read.
		"""
		#TODO.