//Cura plug-in to read SVG files as toolpaths.
//Copyright (C) 2020 Ghostkeeper
//This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
//This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
//You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import QtQuick 2.1
import QtQuick.Controls 2.1

import UM 1.1 as UM

UM.Dialog {
	minimumWidth: 350 * screenScaleFactor
	minimumHeight: 100 * screenScaleFactor

	title: "Load SVG image as toolpath"

	Item { //Row for height (mm).
		anchors {
			left: parent.left
			right: parent.right
		}
		height: childrenRect.height

		Label {
			text: "Height (mm)"
			anchors.verticalCenter: heightField.verticalCenter
		}
		TextField {
			id: heightField
			anchors.right: parent.right
			validator: IntValidator {
				bottom: 0
			}
		}
	}

	Item { //Row for buttons.
		anchors {
			left: parent.left
			right: parent.right
			bottom: parent.bottom
		}
		height: childrenRect.height

		Button {
			anchors.right: parent.right
			text: "OK"
			onClicked: manager.confirm()
		}
	}
}