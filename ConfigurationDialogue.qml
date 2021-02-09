//Cura plug-in to read SVG files as toolpaths.
//Copyright (C) 2020 Ghostkeeper
//This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
//This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
//You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import QtQuick 2.1
import QtQuick.Controls 2.1

import UM 1.1 as UM

UM.Dialog {
	id: svg_reader_config_dialogue
	minimumWidth: 350 * screenScaleFactor
	minimumHeight: 100 * screenScaleFactor

	title: "Load SVG image as toolpath"

	onRejected: manager.cancel()
	onAccepted: manager.confirm()

	Item { //Row for height (mm).
		id: heightRow

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
			selectByMouse: true
			anchors.right: parent.right
			validator: DoubleValidator {
				bottom: 0
			}
			text: manager.height
			onEditingFinished: manager.height = text
		}
	}

	Item { //Row for center Enabled
		id: centerRow

		anchors {
			top: heightRow.bottom
			left: parent.left
			right: parent.right
		}
		height: childrenRect.height

		Label {
			text: "Center on buildplate"
			anchors.verticalCenter: heightField.verticalCenter
		}
		CheckBox {
			id: toggleCenterEnabled
			anchors.right: parent.right
	        checked: manager.centerEnabled
	        onClicked: manager.centerEnabled = checked
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
			anchors.left: parent.left
			text: "Cancel"
			onClicked: svg_reader_config_dialogue.rejected()
		}

		Button {
			anchors.right: parent.right
			text: "OK"
			onClicked: svg_reader_config_dialogue.accept()
		}
	}
}