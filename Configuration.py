# Cura plug-in to read SVG files as toolpaths.
# Copyright (C) 2020 Ghostkeeper
# This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
# You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import PyQt5.QtCore  # To display an interface to the user.
import UM.Mesh.MeshReader  # To return the correct prompt response for the preread.

class Configuration(PyQt5.QtCore.QObject):
	"""
	This class shows a dialogue that asks the user how he'd like to load the
	file.

	You can show the dialogue with the ``prompt`` function.
	"""

	def prompt(self, file_name) -> UM.Mesh.MeshReader.MeshReader.PreReadResult:
		"""
		Asks the user how he'd like to read the file.

		This will show a dialogue to the user with some options. The thread
		will be blocked until the dialogue is closed.
		:param file_name: The path to the file that is to be read.
		:return: The result of the dialogue, whether it is accepted, declined
		or there was an error.
		"""
		print("Test prompt!", file_name)
		return UM.Mesh.MeshReader.MeshReader.PreReadResult.accepted