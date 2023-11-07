# coding: utf-8
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pyqtgraph import FileDialog
from pyqtgraph.Qt import QtCore, QtWidgets

__all__ = ["OpenFilePathEntry"]


class OpenFilePathEntry(QtWidgets.QWidget):
    changed: ClassVar[QtCore.Signal] = QtCore.Signal(Path, name="changed")

    def __init__(
        self,
        initial_file_path: Path | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._path: Path | None = None

        layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout(self)

        self.text: QtWidgets.QLabel = QtWidgets.QLabel(self)
        self.path = initial_file_path
        self.text.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
            | QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(self.text)

        self.browse_button: QtWidgets.QPushButton = QtWidgets.QPushButton(self.tr("Browse…"), self)
        self.browse_button.clicked.connect(self.on_browse_button_clicked)
        self.layout().addWidget(self.browse_button)

        layout.setStretch(1, 0)

    @property
    def path(self) -> Path | None:
        return self._path

    @path.setter
    def path(self, path: Path | None) -> None:
        if path is None or not path.is_file():
            self._path = None
            self.text.clear()
            self.text.setToolTip("")
        else:
            self._path = path
            self.text.setText(str(path))
            self.text.setToolTip(str(self._path))

    @QtCore.Slot()
    def on_browse_button_clicked(self) -> None:
        new_file_name: str
        new_file_name, _ = FileDialog.getOpenFileName(
            self,
            self.tr("Open"),
            str(self._path or ""),
            self.tr("Translations") + "(*.qm)",
        )
        if new_file_name:
            self.path = Path(new_file_name)
            self.changed.emit(self.path)
