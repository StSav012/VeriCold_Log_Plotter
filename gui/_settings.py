# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final, Optional, Sequence, cast

from pyqtgraph.Qt import QtCore, QtGui

__all__ = ['Settings']


class Settings(QtCore.QSettings):
    """ convenient internal representation of the application settings """
    LINE_ENDS: Final[list[str]] = [r'Line Feed (\n)', r'Carriage Return (\r)', r'CR+LF (\r\n)', r'LF+CR (\n\r)']
    _LINE_ENDS: Final[list[str]] = ['\n', '\r', '\r\n', '\n\r']
    CSV_SEPARATORS: Final[list[str]] = [r'comma (,)', r'tab (\t)', r'semicolon (;)', r'space ( )']
    _CSV_SEPARATORS: Final[list[str]] = [',', '\t', ';', ' ']

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.check_items_names: list[str] = []
        self.check_items_values: list[bool] = []

        self.line_colors: dict[str, QtGui.QColor] = dict()
        self.line_enabled: dict[str, bool] = dict()
        self.data_series_names: dict[int, str] = dict()

        self.beginGroup('plot')
        key: str
        for key in self.allKeys():
            if key.endswith(' color'):
                self.line_colors[key[:-6]] = cast(QtGui.QColor, self.value(key))
            if key.endswith(' enabled'):
                self.line_enabled[key[:-8]] = cast(bool, self.value(key, False, bool))

        i: int
        for i in range(self.beginReadArray('dataSeries')):
            self.setArrayIndex(i)
            self.data_series_names[i] = cast(str, self.value('name'))
        self.endArray()
        self.endGroup()

    def sync(self) -> None:
        self.beginGroup('plot')
        key: str
        color: QtGui.QColor
        enabled: bool
        for key, color in self.line_colors.items():
            self.setValue(f'{key} color', color)
        for key, enabled in self.line_enabled.items():
            self.setValue(f'{key} enabled', enabled)

        i: int
        n: str
        self.beginWriteArray('dataSeries', len(self.data_series_names))
        for i, n in self.data_series_names.items():
            self.setArrayIndex(i)
            self.setValue('name', n)
        self.endArray()
        self.endGroup()

        super().sync()

    @property
    def dialog(self) -> dict[str,
                             dict[str, tuple[str]] |
                             dict[str, tuple[Path]] |
                             dict[str, tuple[Sequence[str], Sequence[str], str]]]:
        return {
            self.tr('View'): {
                self.tr('Translation file:'): ('translation_path',),
            },
            self.tr('Export'): {
                self.tr('Line ending:'): (self.LINE_ENDS, self._LINE_ENDS, 'line_end'),
                self.tr('CSV separator:'): (self.CSV_SEPARATORS, self._CSV_SEPARATORS, 'csv_separator'),
            }
        }

    @property
    def line_end(self) -> str:
        self.beginGroup('export')
        v: int = cast(int, self.value('lineEnd', self._LINE_ENDS.index(os.linesep), int))
        self.endGroup()
        return self._LINE_ENDS[v]

    @line_end.setter
    def line_end(self, new_value: str) -> None:
        self.beginGroup('export')
        self.setValue('lineEnd', self._LINE_ENDS.index(new_value))
        self.endGroup()

    @property
    def csv_separator(self) -> str:
        self.beginGroup('export')
        v: int = cast(int, self.value('csvSeparator', self._CSV_SEPARATORS.index('\t'), int))
        self.endGroup()
        return self._CSV_SEPARATORS[v]

    @csv_separator.setter
    def csv_separator(self, new_value: str) -> None:
        self.beginGroup('export')
        self.setValue('csvSeparator', self._CSV_SEPARATORS.index(new_value))
        self.endGroup()

    @property
    def translation_path(self) -> Optional[Path]:
        self.beginGroup('translation')
        v: str = cast(str, self.value('filePath', '', str))
        self.endGroup()
        return Path(v) if v else None

    @translation_path.setter
    def translation_path(self, new_value: Optional[Path]) -> None:
        self.beginGroup('translation')
        self.setValue('filePath', str(new_value) if new_value is not None else '')
        self.endGroup()

    @property
    def argument(self) -> str:
        self.beginGroup('plot')
        v: str = cast(str, self.value('xAxis'))
        self.endGroup()
        return v

    @argument.setter
    def argument(self, new_value: str) -> None:
        self.beginGroup('plot')
        self.setValue('xAxis', new_value)
        self.endGroup()
