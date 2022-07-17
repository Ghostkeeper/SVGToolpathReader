# Cura plug-in to read SVG files as toolpaths.
# Copyright (C) 2022 Ghostkeeper
# This plug-in is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This plug-in is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for details.
# You should have received a copy of the GNU Affero General Public License along with this plug-in. If not, see <https://gnu.org/licenses/>.

import os.path  # To find the QML file to display.
try:
	from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, Qt  # To display an interface to the user.
	qt_version = 6
except ImportError:
	from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, Qt
	qt_version = 5
import threading  # To wait for the user to close the UI.
import UM.Application
import UM.Mesh.MeshReader  # To return the correct prompt response for the preread.
import UM.Message  # To show errors.

class Configuration(QObject):
	"""
	This class shows a dialogue that asks the user how he'd like to load the
	file.

	You can show the dialogue with the ``prompt`` function.
	"""

	_show_ui_trigger = pyqtSignal()
	"""
	Signal to show the UI.

	This is necessary because the UI can only be created on the QML Engine
	thread. Creating it from the emittance of this trigger moves the creation
	to that thread.
	"""

	def __init__(self) -> None:
		"""
		Creates the configuration object.

		This doesn't create the actual UI yet. That will be created lazily by
		the ``prompt`` function.
		"""
		super().__init__(parent=UM.Application.Application.getInstance().getMainWindow())
		self.ui_element = None
		self._file_name = None
		self._ui_lock = threading.Lock()
		self._status = UM.Mesh.MeshReader.MeshReader.PreReadResult.failed
		self._show_ui_trigger.connect(self._prompt)
		self._height = 0.1

	def prompt(self, file_name) -> UM.Mesh.MeshReader.MeshReader.PreReadResult:
		"""
		Asks the user how he'd like to read the file.

		This will show a dialogue to the user with some options. The thread
		will be blocked until the dialogue is closed.
		:param file_name: The path to the file that is to be read.
		:return: The result of the dialogue, whether it is accepted, declined
		or there was an error.
		"""
		self._file_name = file_name
		self._ui_lock.acquire()
		self._show_ui_trigger.emit()
		self._wait_for_ui()
		return self._status

	def create_ui(self):
		"""
		Loads the dialogue element from the QML file.
		"""
		application = UM.Application.Application.getInstance()

		if application.getGlobalContainerStack() is None:
			message = UM.Message.Message("Unable to load in SVG files before adding a printer. Please add a printer first")
			message.show()
			return
		self._height = application.getGlobalContainerStack().getProperty("layer_height_0", "value")  # First time showing this dialogue, use one layer as height.
		qml_path = os.path.join(application.getPluginRegistry().getPluginPath("SVGToolpathReader"), "ConfigurationDialogue.qml")
		self.ui_element = application.createQmlComponent(qml_path, {"manager": self})
		if qt_version >= 6:
			self.ui_element.setFlags(self.ui_element.flags() & Qt.WindowType.WindowCloseButtonHint & Qt.WindowType.WindowMinimizeButtonHint & Qt.WindowType.WindowMaximizeButtonHint)
		else:
			self.ui_element.setFlags(self.ui_element.flags() & ~Qt.WindowCloseButtonHint & ~Qt.WindowMinimizeButtonHint & ~Qt.WindowMaximizeButtonHint)

	@pyqtSlot()
	def confirm(self):
		"""
		Triggered when the user clicks the OK button in the interface.

		This allows the SVG file to be read with the settings written in that
		interface.
		"""
		self._status = UM.Mesh.MeshReader.MeshReader.PreReadResult.accepted
		self.ui_element.close()
		self._ui_lock.acquire(blocking=False)
		self._ui_lock.release()

	@pyqtSlot()
	def cancel(self):
		"""
		Triggered when the user closes the dialogue rather than clicking OK.
		"""
		self._status = UM.Mesh.MeshReader.MeshReader.PreReadResult.cancelled
		self.ui_element.close()
		self._ui_lock.acquire(blocking=False)
		self._ui_lock.release()

	heightChanged = pyqtSignal()

	@pyqtSlot(int)
	def setHeight(self, height):
		if height != self._height:
			self._height = height
			self.heightChanged.emit()

	@pyqtProperty(float, notify=heightChanged, fset=setHeight)
	def height(self):
		return self._height

	def _prompt(self) -> UM.Mesh.MeshReader.MeshReader.PreReadResult:
		"""
		Actually asks the user how he'd like to read the file.

		This time it will be executed in the QML engine thread so that new
		elements can be created if necessary.
		:param file_name: The path to the file that is to be read.
		:return: The result of the dialogue, whether it is accepted, declined
		or there was an error.
		"""
		if self.ui_element is None:
			self.create_ui()
		self.ui_element.show()
		return UM.Mesh.MeshReader.MeshReader.PreReadResult.accepted

	def _wait_for_ui(self):
		self._ui_lock.acquire()
		self._ui_lock.release()