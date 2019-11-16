#Cura plug-in to read SVG files as toolpaths.
#Copyright (C) 2019 Ghostkeeper
#This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
#You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import re  # For parsing the CSS source.
import UM.Logger  # Reporting parsing failures.

class CSS:
	"""
	Tracks and parses CSS attributes for an element.

	The main function of this class is to group together all CSS properties for
	an element. In order to construct it easily, it will also do the work of
	parsing the (supported) CSS attributes.
	"""

	def __init__(self) -> None:
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

	def parse(self, css) -> None:
		"""
		Parse the supported CSS properties from a string of serialised CSS.

		The results are stored in this CSS instance.
		:param css: The piece of CSS to parse.
		"""
		is_float = lambda s: re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s) is not None
		tautology = lambda s: True
		is_list_of_lengths = lambda s: re.fullmatch(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(cap|ch|em|ex|ic|lh|rem|rlh|vh|vw|vi|vb|vmin|vmax|px|cm|mm|Q|in|pc|pt|%)?[,\s])*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)?(cap|ch|em|ex|ic|lh|rem|rlh|vh|vw|vi|vb|vmin|vmax|px|cm|mm|Q|in|pc|pt|%)?", s) is not None
		is_length = lambda s: re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(cap|ch|em|ex|ic|lh|rem|rlh|vh|vw|vi|vb|vmin|vmax|px|cm|mm|Q|in|pc|pt|%)?", s)
		attribute_validate = {  # For each supported attribute, a predicate to validate whether it is correctly formed.
			"font-family": tautology,
			"font-weight": is_float,
			"font-size": is_length,
			"font-style": lambda s: s in {"normal", "italic", "oblique", "initial"},  # Don't include "inherit" since we want it to inherit then as if not set.
			"stroke-dasharray": is_list_of_lengths,
			"stroke-dashoffset": is_length,
			"stroke-width": is_length,
			"text-decoration": tautology,  # Not going to do any sort of parsing on this one since it has all the colours and that's just way too complex.
			"text-decoration-line": lambda s: all([part in {"none", "overline", "underline", "line-through", "initial"} for part in s.split()]),
			"text-decoration-style": lambda s: s in {"solid", "double", "dotted", "dashed", "wavy", "initial"},
			"text-transform": lambda s: s in {"none", "capitalize", "uppercase", "lowercase", "initial"},  # Don't include "inherit" again.
			"transform": tautology  # Not going to do any sort of parsing on this one because all the transformation functions make it very complex.
		}

		pieces = css.split(";")
		for piece in pieces:
			piece = piece.strip()
			if ":" not in piece:  # Only parse well-formed CSS rules, which are key-value pairs separated by a colon.
				UM.Logger.Logger.log("w", "Ill-formed CSS rule: {piece}".format(piece=piece))
				continue
			attribute = piece[:piece.index(":")]
			value = piece[piece.index(":") + 1]
			if attribute not in attribute_validate:
				UM.Logger.Logger.log("w", "Unknown CSS attribute {attribute}".format(attribute=attribute))
				continue
			if not attribute_validate[attribute](value):
				UM.Logger.Logger.log("w", "Invalid value for CSS attribute {attribute}: {value}".format(attribute=attribute, value=value))
				continue
			#TODO: Store the value.
