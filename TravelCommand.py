#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

class TravelCommand:
	"""
	Data structure that represents a movement to a certain spot without
	extruding.

	Such intermediary data structures are necessary in order to perform the
	transformations on SVG elements correctly.
	"""

	def __init__(self, x=0, y=0):
		"""
		Initialises defaults for all fields.
		:param x: The X position to travel to.
		:param y: The Y position to travel to.
		"""
		self.x = x
		self.y = y