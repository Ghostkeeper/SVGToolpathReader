#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import cura.Settings.ExtruderManager #To get settings from the active extruder.
import cura.LayerDataBuilder #One of the results of the function.
import cura.LayerPolygon #Filling layer data.
import math
import numpy #To create the Polygon data.
import typing

from . import ExtrudeCommand #To differentiate between the command types.
from . import TravelCommand #To differentiate between the command types.

def write_gcode(commands) -> typing.Tuple[str, cura.LayerDataBuilder.LayerDataBuilder]:
	"""
	Converts a list of commands into g-code.
	:param commands: The list of extrude and travel commands to write.
	:return: A g-code string that would print the commands, as well as a layer
	data builder that represents the same file for layer view.
	"""
	#Cache some settings we'll use often.
	extruder_number = cura.Settings.ExtruderManager.ExtruderManager.getInstance().activeExtruderIndex
	extruder_stack = cura.Settings.ExtruderManager.ExtruderManager.getInstance().getActiveExtruderStack()
	layer_height_0 = extruder_stack.getProperty("layer_height_0", "value")
	material_flow = extruder_stack.getProperty("material_flow", "value") / 100
	material_diameter = extruder_stack.getProperty("material_diameter", "value")
	machine_center_is_zero = extruder_stack.getProperty("machine_center_is_zero", "value") #Necessary to know if we need to offset the coordinates for layer view.
	machine_gcode_flavor = extruder_stack.getProperty("machine_gcode_flavor", "value") #Necessary to track if we need to extrude volumetric or lengthwise.
	machine_width = extruder_stack.getProperty("machine_width", "value")
	machine_depth = extruder_stack.getProperty("machine_depth", "value")
	is_volumetric = machine_gcode_flavor in {"UltiGCode", "RepRap (Volumetric)"}
	speed_travel = extruder_stack.getProperty("speed_travel", "value") * 60 #Convert to mm/min for g-code.
	speed_print = extruder_stack.getProperty("speed_wall_0", "value") * 60 #Convert to mm/min for g-code.

	path = []
	gcodes = []

	x = 0
	y = 0
	e = 0
	f = 0

	for command in commands:
		gcode = ";Unknown command of type {typename}!".format(typename=command.__class__.__name__)
		if isinstance(command, TravelCommand.TravelCommand):
			#Since SVG has positive Y going down but g-code has positive Y going up, we need to invert the Y axis.
			if not machine_center_is_zero:
				command.y = machine_depth - command.y
			else:
				command.y = -command.y

			gcode = "G0"
			if command.x != x:
				x = command.x
				gcode += " X{x}".format(x=x)
			if command.y != y:
				y = command.y
				gcode += " Y{y}".format(y=y)
			if speed_travel * 60 != f:
				f = speed_travel * 60
				gcode += " F{f}".format(f=f)
			if not machine_center_is_zero:
				path.append([x - machine_width / 2, -y + machine_depth / 2, 0])
			else:
				path.append([x, -y, 0])
		elif isinstance(command, ExtrudeCommand.ExtrudeCommand):
			#Since SVG has positive Y going down but g-code has positive Y going up, we need to invert the Y axis.
			if not machine_center_is_zero:
				command.y = machine_depth - command.y
			else:
				command.y = -command.y

			distance = math.sqrt((command.x - x) * (command.x - x) + (command.y - y) * (command.y - y))
			mm3 = distance * layer_height_0 * command.line_width * material_flow
			delta_e = mm3 if is_volumetric else (mm3 / (math.pi * material_diameter * material_diameter / 4))

			gcode = "G1"
			if command.x != x:
				x = command.x
				gcode += " X{x}".format(x=x)
			if command.y != y:
				y = command.y
				gcode += " Y{y}".format(y=y)
			if speed_print * 60 != f:
				f = speed_print * 60
				gcode += " F{f}".format(f=f)
			if delta_e != 0:
				e += delta_e
				gcode += " E{e}".format(e=e)
			if not machine_center_is_zero:
				path.append([x - machine_width / 2, -y + machine_depth / 2, command.line_width])
			else:
				path.append([x, -y, command.line_width])
		gcodes.append(gcode)

	builder = cura.LayerDataBuilder.LayerDataBuilder()
	builder.addLayer(0)
	layer = builder.getLayer(0)
	layer.setHeight(0)
	layer.setThickness(layer_height_0)

	if path:
		coordinates = numpy.empty((len(path), 3), numpy.float32)
		types = numpy.empty((len(path) - 1, 1), numpy.int32)
		widths = numpy.empty((len(path) - 1, 1), numpy.float32)
		thicknesses = numpy.empty((len(path) - 1, 1), numpy.float32)
		feedrates = numpy.empty((len(path) - 1, 1), numpy.float32)
		for i, point in enumerate(path):
			coordinates[i, :] = [point[0], layer_height_0, point[1]]
			if i > 0:
				if point[2] == 0:
					feedrates[i - 1] = speed_travel
					types[i - 1] = cura.LayerPolygon.LayerPolygon.MoveCombingType
					widths[i - 1] = 0.1
					thicknesses[i - 1] = 0.0
				else:
					feedrates[i - 1] = speed_print
					types[i - 1] = cura.LayerPolygon.LayerPolygon.Inset0Type
					widths[i - 1] = point[2]
					thicknesses[i - 1] = layer_height_0

		polygon = cura.LayerPolygon.LayerPolygon(extruder_number, types, coordinates, widths, thicknesses, feedrates)
		polygon.buildCache()
		layer.polygons.append(polygon)

	return "\n".join(gcodes), builder