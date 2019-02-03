#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import cura.Scene.CuraSceneNode #To create a mesh node in the scene as result of our read.
import cura.Scene.GCodeListDecorator #To store g-code in the mesh so that you could print it.
import cura.CuraApplication #To get the active build plate.
import cura.LayerDataDecorator #To store layer data in the mesh so that you can visualise it in layer view.
import numpy #For the material colour mapping.
import UM.Mesh.MeshReader #The class we're extending.
import UM.MimeTypeDatabase #Register the SVG MIME type.
import xml.etree.ElementTree #To read SVG files.

import Parse #To parse the SVG.
import WriteGCode #To serialise the commands as g-code.

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

	def _read(self, file_name) -> cura.Scene.CuraSceneNode.CuraSceneNode:
		"""
		Read the specified SVG file.

		The toolpath represented by the file gets put in the current scene as
		g-code.
		:param file_name: The name of the file to read.
		:return: A scene node that contains the print to execute.
		"""
		#Parse the document and generate its g-code.
		document = xml.etree.ElementTree.parse(file_name)
		commands = Parse.parse(document)
		gcode, layer_data_builder = WriteGCode.write_gcode(commands)

		scene_node = cura.Scene.CuraSceneNode.CuraSceneNode()

		#Build the layer data decorator.
		material_colour_map = numpy.zeros(8, 4)
		material_colour_map[0, :] = [0.0, 0.7, 0.9, 1.0]
		material_colour_map[1, :] = [0.7, 0.9, 0.0, 1.0]
		material_colour_map[2, :] = [0.9, 0.0, 0.7, 1.0]
		material_colour_map[3, :] = [0.7, 0.0, 0.0, 1.0]
		material_colour_map[4, :] = [0.0, 0.7, 0.0, 1.0]
		material_colour_map[5, :] = [0.0, 0.0, 0.7, 1.0]
		material_colour_map[6, :] = [0.3, 0.3, 0.3, 1.0]
		material_colour_map[7, :] = [0.7, 0.7, 0.7, 1.0]
		layer_data = layer_data_builder.build(material_colour_map)
		layer_data_decorator = cura.LayerDataDecorator.LayerDataDecorator()
		layer_data_decorator.setLayerData(layer_data)
		scene_node.addDecorator(layer_data_decorator)

		#Store the g-code.
		gcode_list_decorator = cura.Scene.GCodeListDecorator.GCodeListDecorator()
		gcode_list = gcode.split("\n")
		gcode_list_decorator.setGCodeList(gcode_list)
		scene_node.addDecorator(gcode_list_decorator)
		active_build_plate_id = cura.CuraApplication.CuraApplication.getInstance().getMultiBuildPlateModel().activeBuildPlate
		gcode_dict = {active_build_plate_id: gcode_list}
		cura.CuraApplication.CuraApplication.getInstance().getController().getScene().gcode_dict = gcode_dict

		cura.CuraApplication.CuraApplication.getInstance().getBackend().backendStateChange.emit(UM.Backend.Backend.BackendState.Disabled) #Don't try slicing this node.

		return scene_node