#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

project(SVGToolpathReader)
cmake_minimum_required(VERSION 3.10.2) #Oldest version it's been tested with.

#Project metadata.
set(SVGTOOLPATHREADER_PLUGIN_NAME "SVG Toolpath Reader" CACHE STRING "The name of the plug-in in distribution.")
set(SVGTOOLPATHREADER_VERSION_MAJOR 1 CACHE STRING "The major version number, indicating a backward compatibility break.")
set(SVGTOOLPATHREADER_VERSION_MINOR 1 CACHE STRING "The minor version number, indicating a forward compatibility break.")
set(SVGTOOLPATHREADER_VERSION_PATCH 0 CACHE STRING "The patch version number, indicating an incremental improvement without compatibility break.")
set(SVGTOOLPATHREADER_SUPPORTED_SDKS "5.0.0;6.0.0" CACHE STRING "List of supported Cura SDK versions.")

#Installation.
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/plugin.json.in" plugin.json)
set(installed_files
	__init__.py
	ExtrudeCommand.py
	icon.svg
	LICENSE.md
	Parser.py
	README.md
	SVGToolpathReader.py
	TravelCommand.py
	WriteGCode.py
)
set(installed_files_freetype
	__init__.py
	ft_errors.py
	ft_structs.py
	ft_types.py
	libfreetype.dll
	libfreetype.dylib
	raw.py
)
set(installed_files_freetype_ft_enums
	__init__.py
	ft_curve_tags.py
	ft_encodings.py
	ft_face_flags.py
	ft_fstypes.py
	ft_glyph_bbox_modes.py
	ft_glyph_formats.py
	ft_kerning_modes.py
	ft_lcd_filters.py
	ft_load_flags.py
	ft_load_targets.py
	ft_open_modes.py
	ft_outline_flags.py
	ft_pixel_modes.py
	ft_render_modes.py
	ft_stroker_borders.py
	ft_stroker_linecaps.py
	ft_stroker_linejoins.py
	ft_style_flags.py
	tt_adobe_ids.py
	tt_apple_ids.py
	tt_mac_ids.py
	tt_mac_langids.py
	tt_ms_ids.py
	tt_ms_langids.py
	tt_name_ids.py
	tt_platforms.py
)
set(installed_paths "")
foreach(f IN LISTS installed_files)
	list(APPEND installed_paths ${CMAKE_CURRENT_SOURCE_DIR}/${f})
endforeach()
list(APPEND installed_paths ${CMAKE_CURRENT_BINARY_DIR}/plugin.json)
set(installed_paths_freetype "")
foreach(f IN LISTS installed_files_freetype)
	list(APPEND installed_paths_freetype ${CMAKE_CURRENT_SOURCE_DIR}/freetype/${f})
endforeach()
set(installed_paths_freetype_ft_enums "")
foreach(f IN LISTS installed_files_freetype_ft_enums)
	list(APPEND installed_paths_freetype_ft_enums ${CMAKE_CURRENT_SOURCE_DIR}/freetype/ft_enums/${f})
endforeach()

#Find out where to install this thing.
if(WIN32)
	set(cura_directory "$ENV{APPDATA}\\cura")
elseif(APPLE)
	set(cura_directory "$ENV{HOME}/Library/Application Support/cura")
else()
	set(cura_directory "$ENV{HOME}/.local/share/cura")
endif()
#Figure out the latest Cura release that's installed.
file(GLOB versions RELATIVE "${cura_directory}" "${cura_directory}/*")
set(latest_version 2.0)
foreach(version ${versions})
	if(IS_DIRECTORY "${cura_directory}/${version}")
		if(${version} VERSION_GREATER ${latest_version})
			set(latest_version ${version})
		endif()
	endif()
endforeach()
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
	set(CMAKE_INSTALL_PREFIX "${cura_directory}/${latest_version}/plugins" CACHE PATH "Location of the Cura plug-ins folder to install this plug-in to." FORCE)
endif()
install(FILES ${installed_paths} DESTINATION SVGToolpathReader)
install(FILES ${installed_paths_freetype} DESTINATION SVGToolpathReader/freetype)
install(FILES ${installed_paths_freetype_ft_enums} DESTINATION SVGToolpathReader/freetype/ft_enums)

#Packing this into a .curapackage file.
add_custom_target(pack COMMAND "") #Packs for all supported SDK versions.
foreach(sdk_version ${SVGTOOLPATHREADER_SUPPORTED_SDKS})
	file(COPY ${installed_paths} DESTINATION pack${sdk_version}/files/plugins/SVGToolpathReader)
	file(COPY ${installed_paths_freetype} DESTINATION pack${sdk_version}/files/plugins/SVGToolpathReader/freetype)
	file(COPY ${installed_paths_freetype_ft_enums} DESTINATION pack${sdk_version}/files/plugins/SVGToolpathReader/freetype/ft_enums)
	file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/cmake/[Content_Types].xml" DESTINATION pack${sdk_version})
	file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/cmake/_rels" DESTINATION pack${sdk_version})
	configure_file("${CMAKE_CURRENT_SOURCE_DIR}/cmake/package.json.in" pack${sdk_version}/package.json)
	set(packaged_files
		package.json
		[Content_Types].xml
		_rels
		files
	)
	add_custom_target(pack${sdk_version}
		COMMAND "${CMAKE_COMMAND}" -E tar cfv ../SVGToolpathReader${sdk_version}.curapackage --format=zip ${packaged_files}
		WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/pack${sdk_version}
	)
	add_dependencies(pack pack${sdk_version})
endforeach()

#Let CPack find it.
include(InstallRequiredSystemLibraries)
set(CPACK_PACKAGE_VERSION_MAJOR ${SVGTOOLPATHREADER_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${SVGTOOLPATHREADER_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${SVGTOOLPATHREADER_VERSION_PATCH})
set(CPACK_PACKAGE_NAME ${SVGTOOLPATHREADER_PLUGIN_NAME})
set(CPACK_PACKAGE_DESCRIPTION_FILE ${CMAKE_CURRENT_SOURCE_DIR}/README.md)
set(CPACK_GENERATOR ZIP)
include(CPack)
