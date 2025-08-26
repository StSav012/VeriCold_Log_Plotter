from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pyqtgraph.Qt import QtWidgets

from ._open_file_path_entry import OpenFilePathEntry
from ._settings import Settings

__all__ = ["Preferences"]


class Preferences(QtWidgets.QDialog):
    """GUI preferences dialog."""

    def __init__(self, settings: Settings, parent: QtWidgets.QWidget | None = None, *args: object) -> None:
        super().__init__(parent, *args)

        self.settings: Settings = settings
        self.setModal(True)
        self.setWindowTitle(self.tr("Preferences"))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        combo_box: QtWidgets.QComboBox
        check_box: QtWidgets.QCheckBox
        spin_box: QtWidgets.QSpinBox | QtWidgets.QDoubleSpinBox
        open_file_path_entry: OpenFilePathEntry
        key: str
        value: (
            dict[str, tuple[str]]
            | dict[str, tuple[Path]]
            | dict[str, tuple[Sequence[str], str]]
            | dict[str, tuple[Sequence[str], Sequence[str], str]]
        )
        for key, value in self.settings.dialog.items():
            if isinstance(value, dict):
                box: QtWidgets.QGroupBox = QtWidgets.QGroupBox(key, self)
                box_layout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(box)
                key2: str
                value2: tuple[str] | tuple[Path] | tuple[Sequence[str], str] | tuple[Sequence[str], Sequence[str], str]
                value3: Sequence[str]
                value3a: Sequence[str] | slice
                value3b: Sequence[Any] | tuple[str]
                index: int
                item: str
                for key2, value2 in value.items():
                    if isinstance(value2, tuple) and isinstance(value2[-1], str) and value2[-1]:
                        if len(value2) == 1:
                            if isinstance(getattr(self.settings, value2[-1]), bool):
                                check_box = QtWidgets.QCheckBox(key2, box)
                                check_box.callback = value2[-1]
                                check_box.setChecked(getattr(self.settings, value2[-1]))
                                check_box.toggled.connect(
                                    lambda x, sender=check_box: setattr(self.settings, sender.callback, x)
                                )
                                box_layout.addWidget(check_box)
                            elif isinstance(getattr(self.settings, value2[-1]), (Path, type(None))):
                                open_file_path_entry = OpenFilePathEntry(getattr(self.settings, value2[-1]), box)
                                open_file_path_entry.callback = value2[-1]
                                open_file_path_entry.changed.connect(
                                    lambda x, sender=open_file_path_entry: setattr(self.settings, sender.callback, x)
                                )
                                box_layout.addRow(key2, open_file_path_entry)
                            # no else
                        elif len(value2) == 2:
                            value3 = value2[0]
                            if isinstance(value3, Sequence):
                                combo_box = QtWidgets.QComboBox(box)
                                combo_box.callback = value2[-1]
                                for item in value3:
                                    combo_box.addItem(item)
                                combo_box.setCurrentIndex(getattr(self.settings, value2[-1]))
                                combo_box.currentIndexChanged.connect(
                                    lambda x, sender=combo_box: setattr(self.settings, sender.callback, x)
                                )
                                box_layout.addRow(key2, combo_box)
                            # no else
                        elif len(value2) == 3:
                            value3a = value2[0]
                            value3b = value2[1]
                            if isinstance(value3a, Sequence) and isinstance(value3b, Sequence):
                                combo_box = QtWidgets.QComboBox(box)
                                combo_box.callback = value2[-1]
                                for index, item in enumerate(value3a):
                                    combo_box.addItem(item, value3b[index])
                                combo_box.setCurrentIndex(value3b.index(getattr(self.settings, value2[-1])))
                                combo_box.currentIndexChanged.connect(
                                    lambda _, sender=combo_box: setattr(
                                        self.settings,
                                        sender.callback,
                                        sender.currentData(),
                                    )
                                )
                                box_layout.addRow(key2, combo_box)
                            elif (
                                isinstance(value3a, slice)
                                and isinstance(getattr(self.settings, value2[-1]), (int, float))
                                and isinstance(value3b, tuple)
                            ):
                                if (
                                    (value3a.start is None or isinstance(value3a.start, int))
                                    and (value3a.stop is None or isinstance(value3a.stop, int))
                                    and (value3a.step is None or isinstance(value3a.step, int))
                                    and isinstance(getattr(self.settings, value2[-1]), int)
                                ):
                                    spin_box = QtWidgets.QSpinBox(box)
                                else:
                                    spin_box = QtWidgets.QDoubleSpinBox(box)
                                spin_box.callback = value2[-1]
                                if value3a.start is not None:
                                    spin_box.setMinimum(value3a.start)
                                if value3a.stop is not None:
                                    spin_box.setMaximum(value3a.stop)
                                if value3a.step is not None:
                                    spin_box.setSingleStep(value3a.step)
                                spin_box.setValue(getattr(self.settings, value2[-1]))
                                if len(value3b) == 2:
                                    spin_box.setPrefix(str(value3b[0]))
                                    spin_box.setSuffix(str(value3b[1]))
                                elif len(value3b) == 1:
                                    spin_box.setSuffix(str(value3b[0]))
                                # no else
                                spin_box.valueChanged.connect(
                                    lambda _, sender=spin_box: setattr(
                                        self.settings,
                                        sender.callback,
                                        sender.value(),
                                    )
                                )
                                box_layout.addRow(key2, spin_box)
                            # no else
                        # no else
                    # no else
                layout.addWidget(box)
            # no else
        buttons: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close, self
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
