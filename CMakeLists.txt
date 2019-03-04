#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

project(SVGToolpathReader)
cmake_minimum_required(VERSION 3.12.3) #Oldest version it's been tested with.

#Project metadata.
set(SVGTOOLPATHREADER_PLUGIN_NAME "SVG Toolpath Reader" CACHE STRING "The name of the plug-in in distribution.")
set(SVGTOOLPATHREADER_VERSION_MAJOR 1 CACHE STRING "The major version number, indicating a backward compatibility break.")
set(SVGTOOLPATHREADER_VERSION_MINOR 0 CACHE STRING "The minor version number, indicating a forward compatibility break.")
set(SVGTOOLPATHREADER_VERSION_PATCH 0 CACHE STRING "The patch version number, indicating an incremental improvement without compatibility break.")

#Installation.
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/plugin.json.in plugin.json)
set(installed_files
	${CMAKE_CURRENT_SOURCE_DIR}/__init__.py
	${CMAKE_CURRENT_SOURCE_DIR}/ExtrudeCommand.py
	${CMAKE_CURRENT_SOURCE_DIR}/icon.svg
	${CMAKE_CURRENT_SOURCE_DIR}/LICENSE.md
	${CMAKE_CURRENT_SOURCE_DIR}/Parser.py
	${CMAKE_CURRENT_SOURCE_DIR}/plugin.json
	${CMAKE_CURRENT_SOURCE_DIR}/README.md
	${CMAKE_CURRENT_SOURCE_DIR}/SVGToolpathReader.py
	${CMAKE_CURRENT_SOURCE_DIR}/TravelCommand.py
	${CMAKE_CURRENT_SOURCE_DIR}/WriteGCode.py
)
install(FILES ${installed_files} DESTINATION SVGToolpathReader)

#Packaging: Create a .curapackage file.
include(InstallRequiredSystemLibraries)
set(CPACK_PACKAGE_VERSION_MAJOR ${SVGTOOLPATHREADER_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${SVGTOOLPATHREADER_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${SVGTOOLPATHREADER_VERSION_PATCH})
set(CPACK_PACKAGE_NAME ${SVGTOOLPATHREADER_PLUGIN_NAME})
set(CPACK_PACKAGE_DESCRIPTION_FILE ${CMAKE_CURRENT_SOURCE_DIR}/README.md)
set(CPACK_GENERATOR ZIP)
include(CPack)