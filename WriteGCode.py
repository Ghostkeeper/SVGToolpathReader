#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import cura.Settings.ExtruderManager #To get settings from the active extruder.
import cura.LayerDataBuilder #One of the results of the function.
import cura.LayerPolygon #Filling layer data.
import json #To read this plugin's version for the g-code headers.
import math
import numpy #To create the Polygon data.
import os.path #To read this plugin's version for the g-code headers.
import UM.PluginRegistry #To read this plugin's version for the g-code headers.
import time #To get today's date for the g-code headers.
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
	material_flow = extruder_stack.getProperty("material_flow_layer_0", "value") / 100
	material_diameter = extruder_stack.getProperty("material_diameter", "value")
	machine_center_is_zero = extruder_stack.getProperty("machine_center_is_zero", "value") #Necessary to know if we need to offset the coordinates for layer view.
	machine_gcode_flavor = extruder_stack.getProperty("machine_gcode_flavor", "value") #Necessary to track if we need to extrude volumetric or lengthwise.
	machine_end_gcode = extruder_stack.getProperty("machine_end_gcode", "value")
	machine_width = extruder_stack.getProperty("machine_width", "value")
	machine_depth = extruder_stack.getProperty("machine_depth", "value")
	is_volumetric = machine_gcode_flavor in {"UltiGCode", "RepRap (Volumetric)"}
	speed_travel = extruder_stack.getProperty("speed_travel_layer_0", "value")
	speed_print = extruder_stack.getProperty("speed_print_layer_0", "value")
	retraction_enable = extruder_stack.getProperty("retraction_enable", "value")
	retraction_speed = extruder_stack.getProperty("retraction_retract_speed", "value")
	unretraction_speed = extruder_stack.getProperty("retraction_prime_speed", "value")
	retraction_distance = extruder_stack.getProperty("retraction_amount", "value")

	path = []
	gcodes = []

	x = 0
	y = 0
	e = 0
	f = 0
	min_x = machine_width
	min_y = machine_depth
	max_x = -machine_width
	max_y = -machine_depth
	is_retracted = retraction_enable #If retracting, we start off retracted as per the start g-code.

	for command in commands:
		gcode = ";Unknown command of type {typename}!".format(typename=command.__class__.__name__)
		if isinstance(command, TravelCommand.TravelCommand):
			#Since SVG has positive Y going down but g-code has positive Y going up, we need to invert the Y axis.
			if not machine_center_is_zero:
				command.y = machine_depth - command.y
			else:
				command.y = -command.y

			gcode = ""
			if not is_retracted and retraction_enable:
				gcode += "G0 F{speed} E{e}\n".format(speed=retraction_speed * 60, e=e - retraction_distance)
				is_retracted = True
			gcode += "G0"
			if command.x != x:
				x = command.x
				min_x = min(min_x, x)
				max_x = max(max_x, x)
				gcode += " X{x}".format(x=x)
			if command.y != y:
				y = command.y
				min_y = min(min_y, y)
				max_y = max(max_y, y)
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

			gcode = ""
			if is_retracted:
				gcode += "G0 F{speed} E{e}\n".format(speed=unretraction_speed, e=e)
				is_retracted = False
			gcode += "G1"
			if command.x != x:
				x = command.x
				min_x = min(min_x, x)
				max_x = max(max_x, x)
				gcode += " X{x}".format(x=x)
			if command.y != y:
				y = command.y
				min_y = min(min_y, y)
				max_y = max(max_y, y)
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

	machine_start_gcode = get_start_gcode(min_x, min_y, max_x, max_y)
	gcodes = [machine_start_gcode] + gcodes

	gcodes.append("M140 S0") #Cool everything down.
	gcodes.append("M104 S0")
	gcodes.append("M107") #Fans off.
	gcodes.append(machine_end_gcode)

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
					if retraction_enable:
						types[i - 1] = cura.LayerPolygon.LayerPolygon.MoveRetractionType
					else:
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

def get_start_gcode(min_x, min_y, max_x, max_y) -> str:
	"""
	Returns the proper starting g-code for the current printer.

	This doesn't just include the ordinary start g-code setting, but also any
	headers specified by the g-code flavour, heating commands, priming maybe,
	just anything that is required to get the printer going.
	:param min_x: The minimum X coordinate that we're moving to.
	:param min_y: The minimum Y coordinate that we're moving to.
	:param max_x: The maximum X coordinate that we're moving to.
	:param max_y: The maximum Y coordinate that we're moving to.
	:return: The proper starting g-code for the current printer.
	"""
	extruder_number = cura.Settings.ExtruderManager.ExtruderManager.getInstance().activeExtruderIndex
	extruder_stack = cura.Settings.ExtruderManager.ExtruderManager.getInstance().getActiveExtruderStack()
	machine_gcode_flavor = extruder_stack.getProperty("machine_gcode_flavor", "value")
	machine_name = extruder_stack.getProperty("machine_name", "value")
	material_print_temperature_layer_0 = extruder_stack.getProperty("material_print_temperature_layer_0", "value")
	material_guid = extruder_stack.getProperty("material_guid", "value")
	machine_nozzle_size = extruder_stack.getProperty("machine_nozzle_size", "value")
	machine_nozzle_id = extruder_stack.getProperty("machine_nozzle_id", "value")
	machine_buildplate_type = extruder_stack.getProperty("machine_buildplate_type", "value")
	material_bed_temperature_layer_0 = extruder_stack.getProperty("material_bed_temperature_layer_0", "value")
	machine_width = extruder_stack.getProperty("machine_width", "value")
	machine_depth = extruder_stack.getProperty("machine_depth", "value")
	machine_height = extruder_stack.getProperty("machine_height", "value")
	prime_blob_enable = extruder_stack.getProperty("prime_blob_enable", "value")
	extruder_prime_pos_x = extruder_stack.getProperty("extruder_prime_pos_x", "value")
	extruder_prime_pos_y = extruder_stack.getProperty("extruder_prime_pos_y", "value")
	acceleration_wall_0 = extruder_stack.getProperty("acceleration_wall_0", "value")
	jerk_wall_0 = extruder_stack.getProperty("jerk_wall_0", "value")
	layer_height_0 = extruder_stack.getProperty("layer_height_0", "value")
	retraction_enable = extruder_stack.getProperty("retraction_enable", "value")
	retraction_speed = extruder_stack.getProperty("retraction_speed", "value")
	retraction_distance = extruder_stack.getProperty("retraction_amount", "value")

	result = ""

	if machine_gcode_flavor == "Griffin":
		plugin_path = UM.PluginRegistry.PluginRegistry.getInstance().getPluginPath("SVGToolpathReader")
		with open(os.path.join(plugin_path, "plugin.json")) as f:
			plugin_json = json.load(f)
		svgtoolpathreader_version = plugin_json["version"]
		result += """;START_OF_HEADER
;HEADER_VERSION:0.1
;FLAVOR:Griffin
;GENERATOR.NAME:SVGToolpathReader
;GENERATOR.VERSION:{svgtoolpathreader_version}
;GENERATOR.BUILD_DATE:{today}
;TARGET_MACHINE.NAME:{printer_name}
;EXTRUDER_TRAIN.{extruder_number}.INITIAL_TEMPERATURE:{print_temperature}
;EXTRUDER_TRAIN.{extruder_number}.MATERIAL.VOLUME_USED:6666
;EXTRUDER_TRAIN.{extruder_number}.MATERIAL.GUID:{guid}
;EXTRUDER_TRAIN.{extruder_number}.NOZZLE.DIAMETER:{nozzle_diameter}
;EXTRUDER_TRAIN.{extruder_number}.NOZZLE.NAME:{nozzle_name}
;BUILD_PLATE.TYPE:{buildplate_type}
;BUILD_PLATE.INITIAL_TEMPERATURE:{buildplate_temperature}
;PRINT.TIME:666
;PRINT.SIZE.MIN.X:{min_x}
;PRINT.SIZE.MIN.Y:{min_y}
;PRINT.SIZE.MIN.Z:{layer_height}
;PRINT.SIZE.MAX.X:{max_x}
;PRINT.SIZE.MAX.Y:{max_y}
;PRINT.SIZE.MAX.Z:{layer_height}
;END_OF_HEADER
""".format(svgtoolpathreader_version=svgtoolpathreader_version,
           today=time.strftime("%Y-%m-%d"),
           printer_name=machine_name,
           extruder_number=extruder_number,
           print_temperature=material_print_temperature_layer_0,
           guid=material_guid,
           nozzle_diameter=machine_nozzle_size,
           nozzle_name=machine_nozzle_id,
           buildplate_type=machine_buildplate_type,
           buildplate_temperature=material_bed_temperature_layer_0,
           printer_width=machine_width,
           printer_depth=machine_depth,
           printer_height=machine_height,
           min_x=min_x,
           min_y=min_y,
           max_x=max_x,
           max_y=max_y,
           layer_height=layer_height_0)

	result += "T" + str(extruder_number) + "\n" #Correct extruder.
	result += "M82\n" #Absolute extrusion mode only.
	result += "G92 E0\n" #Reset E, wherever it ended up in the previous print is now 0.
	result += "M109 S{print_temperature}\n".format(print_temperature=material_print_temperature_layer_0) #Heat extruder.
	result += "M190 S{bed_temperature}\n".format(bed_temperature=material_bed_temperature_layer_0) #Heat build plate.
	if prime_blob_enable: #Prime, if necessary.
		result += "G0 F15000 X{prime_x} Y{prime_y} Z2\n".format(prime_x=extruder_prime_pos_x, prime_y=extruder_prime_pos_y)
		result += "G280\n"
	if retraction_enable:
		result += "G0 F{speed} E-{distance}".format(speed=retraction_speed * 60, distance=retraction_distance)
	result += "M107\n" #Fans on.
	result += "M204 S{acceleration}\n".format(acceleration=acceleration_wall_0)
	result += "M205 X{jerk} Y{jerk}\n".format(jerk=jerk_wall_0)
	result += ";LAYER:0\n"
	result += "G0 F15000 Z{layer_height}".format(layer_height=layer_height_0)

	return result