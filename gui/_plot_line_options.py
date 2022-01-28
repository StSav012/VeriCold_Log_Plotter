# coding: utf-8
from typing import Any, Final, Optional, Sequence

import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QWidget

from gui._settings import Settings

__all__ = ['PlotLineOptions']


class PlotLineOptions(QWidget):
    _count: int = 0

    DEFAULT_COLOR: Final[QColor] = pg.mkColor(pg.CONFIG_OPTIONS['foreground'])

    toggled: Signal = Signal(int, bool, name='toggled')
    itemChanged: Signal = Signal(int, str, name='itemChanged')
    colorChanged: Signal = Signal(int, QColor, name='colorChanged')

    def __init__(self, settings: Settings, items: Sequence[str], parent: Optional[QWidget] = None, *args: Any) -> None:
        super().__init__(parent, *args)

        self._index: int = PlotLineOptions._count

        self.settings: Settings = settings

        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.check_box: QCheckBox = QCheckBox(self)
        self.options: QComboBox = QComboBox(self)
        self.color_selector: pg.ColorButton = pg.ColorButton(self)

        self.layout.addWidget(self.check_box, 0)
        self.layout.addWidget(self.options, 1)
        self.layout.addWidget(self.color_selector, 0)

        self.set_items(items)

        self.check_box.toggled.connect(self.on_check_toggled)
        self.options.currentTextChanged.connect(self.on_combo_changed)
        self.color_selector.sigColorChanged.connect(self.on_color_changed)

        PlotLineOptions._count += 1

    def set_items(self, items: Sequence[str]) -> None:
        self.setEnabled(bool(items))
        self.options.blockSignals(True)
        self.options.clear()
        self.options.addItems(items)
        if (self._index < len(self.settings.data_series_names)
                and self.settings.data_series_names[self._index] in items):
            self.options.setCurrentText(self.settings.data_series_names[self._index])
        self.color_selector.blockSignals(True)
        self.color_selector.setColor(self.settings.line_colors.get(self.options.currentText(), self.DEFAULT_COLOR))
        self.color_selector.blockSignals(False)
        self.check_box.blockSignals(True)
        self.check_box.setChecked(self.settings.line_enabled.get(self.options.currentText(), False))
        self.check_box.blockSignals(False)
        self.options.blockSignals(False)

    @property
    def index(self) -> int:
        return self.options.currentIndex()

    @property
    def option(self) -> str:
        return self.options.currentText()

    @property
    def color(self) -> QColor:
        return self.color_selector.color()

    @property
    def checked(self) -> bool:
        return self.check_box.isChecked()

    def on_check_toggled(self, new_state: bool) -> None:
        self.settings.line_enabled[self.options.currentText()] = new_state
        self.toggled.emit(self._index, new_state)

    def on_combo_changed(self, new_text: str) -> None:
        self.settings.data_series_names[self._index] = new_text
        self.itemChanged.emit(self._index, new_text)

    def on_color_changed(self, emitter: pg.ColorButton) -> None:
        self.settings.line_colors[self.options.currentText()] = emitter.color()
        self.colorChanged.emit(self._index, emitter.color())
