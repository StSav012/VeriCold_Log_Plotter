from collections.abc import Sequence
from functools import partial
from typing import Any

from pyqtgraph.Qt import QtCore, QtWidgets

from ._open_file_path_entry import OpenFilePathEntry
from ._settings import Settings

__all__ = ["Preferences"]


class PreferencePage(QtWidgets.QGroupBox):
    """A page of the Preferences dialog."""

    def __init__(
        self,
        value: dict[
            str,
            Settings.CheckBox | Settings.PathEntry | Settings.ComboBox | Settings.SpinBox | Settings.DoubleSpinBox,
        ],
        settings: Settings,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._changed_settings: dict[str, object] = {}

        # https://forum.qt.io/post/671245
        def _on_event(x: bool | int | float | str, *, callback: str) -> None:
            self._changed_settings[callback] = x

        def _on_combo_box_current_index_changed(_: int, *, sender: QtWidgets.QComboBox, callback: str) -> None:
            self._changed_settings[callback] = sender.currentData()

        if not (isinstance(value, dict) and value):
            raise TypeError(f"Invalid type: {type(value)}")

        layout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self)
        layout.setLabelAlignment(layout.labelAlignment() | QtCore.Qt.AlignmentFlag.AlignVCenter)

        key2: str
        value2: Settings.CheckBox | Settings.PathEntry | Settings.ComboBox | Settings.SpinBox | Settings.DoubleSpinBox

        check_box: QtWidgets.QCheckBox
        open_file_path_entry: OpenFilePathEntry
        combo_box: QtWidgets.QComboBox
        spin_box: QtWidgets.QSpinBox
        double_spin_box: QtWidgets.QDoubleSpinBox

        for key2, value2 in value.items():
            current_value: Any = getattr(settings, value2.callback)
            if not isinstance(value2, tuple) or not isinstance(value2.callback, str) or not value2.callback:
                continue
            if isinstance(value2, Settings.CheckBox):
                check_box = QtWidgets.QCheckBox(key2, self)
                check_box.callback = value2.callback
                check_box.setChecked(getattr(settings, value2.callback))
                check_box.toggled.connect(partial(_on_event, callback=value2.callback))
                layout.addWidget(check_box)
            elif isinstance(value2, Settings.PathEntry):
                open_file_path_entry = OpenFilePathEntry(current_value, self)
                open_file_path_entry.callback = value2.callback
                open_file_path_entry.changed.connect(partial(_on_event, callback=value2.callback))
                layout.addRow(key2, open_file_path_entry)
            elif isinstance(value2, Settings.ComboBox):
                combo_box = QtWidgets.QComboBox(self)
                combo_box.setEditable(False)
                combo_box.callback = value2.callback
                if isinstance(value2.data, Sequence):
                    for text, data in zip(value2.text, value2.data, strict=False):
                        combo_box.addItem(text, data)
                    combo_box.setCurrentIndex(value2.data.index(current_value))
                else:
                    for text in value2.text:
                        combo_box.addItem(text, text)
                    combo_box.setCurrentIndex(value2.text.index(current_value))
                combo_box.currentIndexChanged.connect(
                    partial(
                        _on_combo_box_current_index_changed,
                        sender=combo_box,
                        callback=value2.callback,
                    )
                )
                layout.addRow(key2, combo_box)
            elif isinstance(value2, Settings.SpinBox):
                spin_box = QtWidgets.QSpinBox(self)
                spin_box.callback = value2.callback
                spin_box.setMinimum(value2.min)
                spin_box.setMaximum(value2.max)
                spin_box.setSingleStep(value2.step)
                spin_box.setValue(getattr(settings, value2.callback))
                spin_box.setPrefix(str(value2.prefix))
                spin_box.setSuffix(str(value2.suffix))
                spin_box.valueChanged.connect(partial(_on_event, callback=value2.callback))
                layout.addRow(key2, spin_box)
            elif isinstance(value2, Settings.DoubleSpinBox):
                double_spin_box = QtWidgets.QDoubleSpinBox(self)
                double_spin_box.callback = value2.callback
                double_spin_box.setMinimum(value2.min)
                double_spin_box.setMaximum(value2.max)
                double_spin_box.setSingleStep(value2.step)
                double_spin_box.setValue(getattr(settings, value2.callback))
                double_spin_box.setPrefix(str(value2.prefix))
                double_spin_box.setSuffix(str(value2.suffix))
                double_spin_box.valueChanged.connect(partial(_on_event, callback=value2.callback))
                layout.addRow(key2, double_spin_box)
            # no else

    @property
    def changed_settings(self) -> dict[str, Any]:
        return self._changed_settings.copy()


class PreferencesBody(QtWidgets.QWidget):
    """The main area of the GUI preferences dialog."""

    def __init__(self, settings: Settings, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("preferencesBody")

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        key: str
        value: dict[
            str,
            Settings.CheckBox | Settings.PathEntry | Settings.ComboBox | Settings.SpinBox | Settings.DoubleSpinBox,
        ]
        self._boxes: list[PreferencePage] = []
        for key, value in settings.dialog.items():
            if not (isinstance(value, dict) and value):
                continue
            box: PreferencePage = PreferencePage(value, settings, self)
            box.setTitle(key)
            layout.addWidget(box)
            self._boxes.append(box)
        self.setLayout(layout)

    @property
    def changed_settings(self) -> dict[str, object]:
        changed_settings: dict[str, object] = {}
        for box in self._boxes:
            changed_settings.update(box.changed_settings)
        return changed_settings


class Preferences(QtWidgets.QDialog):
    """GUI preferences dialog."""

    def __init__(self, settings: Settings, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesDialog")

        self._settings: Settings = settings
        self.setModal(True)
        self.setWindowTitle(self.tr("Preferences"))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        self._preferences_body: PreferencesBody = PreferencesBody(settings=settings, parent=parent)
        layout.addWidget(self._preferences_body)
        buttons: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        self.adjustSize()

        self._settings.restore(self)
        self._settings.restore(self._preferences_body)

    def reject(self) -> None:
        self._settings.save(self)
        self._settings.save(self._preferences_body)
        return super().reject()

    def accept(self) -> None:
        self._settings.save(self)
        self._settings.save(self._preferences_body)

        for key, value in self._preferences_body.changed_settings.items():
            setattr(self._settings, key, value)
        return super().accept()
