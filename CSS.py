#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

class CSS:
	"""
	Tracks and parses CSS attributes for an element.

	The main function of this class is to group together all CSS properties for
	an element. In order to construct it easily, it will also do the work of
	parsing the (supported) CSS attributes.
	"""

	def __init__(self):
		"""
		Creates a new set of CSS attributes.
		"""
		self.font_family = "serif"
		self.font_size = "12pt"
		self.font_weight = "400"
		self.font_style = "normal"
		self.stroke_dasharray = ""
		self.stroke_width = "0"
		self.text_decoration = ""
		self.text_decoration_line = ""
		self.text_decoration_style = "solid"
		self.text_transform = "none"
		self.transform = ""