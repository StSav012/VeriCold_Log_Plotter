import os
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, cast

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

__all__ = ["Settings"]


class Settings(QtCore.QSettings):
    """Convenient internal representation of the application settings."""

    LINE_ENDS: ClassVar[dict[str, str]] = {
        "\n": QtWidgets.QApplication.translate("line end", r"Line Feed (\n)"),
        "\r": QtWidgets.QApplication.translate("line end", r"Carriage Return (\r)"),
        "\r\n": QtWidgets.QApplication.translate("line end", r"CR+LF (\r\n)"),
        "\n\r": QtWidgets.QApplication.translate("line end", r"LF+CR (\n\r)"),
    }
    CSV_SEPARATORS: ClassVar[dict[str, str]] = {
        ",": QtWidgets.QApplication.translate("csv separator", r"comma (,)"),
        "\t": QtWidgets.QApplication.translate("csv separator", r"tab (\t)"),
        ";": QtWidgets.QApplication.translate("csv separator", r"semicolon (;)"),
        " ": QtWidgets.QApplication.translate("csv separator", r"space ( )"),
    }

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.check_items_names: list[str] = []
        self.check_items_values: list[bool] = []

        self.line_colors: dict[str, QtGui.QColor] = dict()
        self.line_enabled: dict[str, bool] = dict()
        self.data_series_names: dict[int, str] = dict()

        self.beginGroup("plot")
        key: str
        for key in self.allKeys():
            if key.endswith(" color"):
                self.line_colors[key[:-6]] = cast(QtGui.QColor, self.value(key))
            if key.endswith(" enabled"):
                self.line_enabled[key[:-8]] = cast(bool, self.value(key, False, bool))

        i: int
        for i in range(self.beginReadArray("dataSeries")):
            self.setArrayIndex(i)
            self.data_series_names[i] = cast(str, self.value("name"))
        self.endArray()
        self.endGroup()

    def sync(self) -> None:
        self.beginGroup("plot")
        key: str
        color: QtGui.QColor
        enabled: bool
        for key, color in self.line_colors.items():
            self.setValue(f"{key} color", color)
        for key, enabled in self.line_enabled.items():
            self.setValue(f"{key} enabled", enabled)

        i: int
        n: str
        self.beginWriteArray("dataSeries", len(self.data_series_names))
        for i, n in self.data_series_names.items():
            self.setArrayIndex(i)
            self.setValue("name", n)
        self.endArray()
        self.endGroup()

        super().sync()

    @property
    def dialog(
        self,
    ) -> dict[
        str, dict[str, tuple[str]] | dict[str, tuple[Path]] | dict[str, tuple[Sequence[str], Sequence[str], str]]
    ]:
        return {
            self.tr("View"): {
                self.tr("Translation file:"): ("translation_path",),
                self.tr("Lines count (restart to apply):"): (
                    slice(1, 99),
                    (),
                    Settings.plot_lines_count.fget.__name__,
                ),
            },
            self.tr("Export"): {
                self.tr("Line ending:"): (
                    list(Settings.LINE_ENDS.values()),
                    list(Settings.LINE_ENDS.keys()),
                    "line_end",
                ),
                self.tr("CSV separator:"): (
                    list(Settings.CSV_SEPARATORS.values()),
                    list(Settings.CSV_SEPARATORS.keys()),
                    "csv_separator",
                ),
            },
        }

    @property
    def line_end(self) -> str:
        self.beginGroup("export")
        v: int = cast(int, self.value("lineEnd", list(Settings.LINE_ENDS.keys()).index(os.linesep), int))
        self.endGroup()
        return list(Settings.LINE_ENDS.keys())[v]

    @line_end.setter
    def line_end(self, new_value: str) -> None:
        self.beginGroup("export")
        self.setValue("lineEnd", list(Settings.LINE_ENDS.keys()).index(new_value))
        self.endGroup()

    @property
    def csv_separator(self) -> str:
        self.beginGroup("export")
        v: int = cast(int, self.value("csvSeparator", list(Settings.CSV_SEPARATORS.keys()).index("\t"), int))
        self.endGroup()
        return list(Settings.CSV_SEPARATORS.keys())[v]

    @csv_separator.setter
    def csv_separator(self, new_value: str) -> None:
        self.beginGroup("export")
        self.setValue("csvSeparator", list(Settings.CSV_SEPARATORS.keys()).index(new_value))
        self.endGroup()

    @property
    def translation_path(self) -> Path | None:
        self.beginGroup("translation")
        v: str = cast(str, self.value("filePath", "", str))
        self.endGroup()
        return Path(v) if v else None

    @translation_path.setter
    def translation_path(self, new_value: Path | None) -> None:
        self.beginGroup("translation")
        self.setValue("filePath", str(new_value) if new_value is not None else "")
        self.endGroup()

    @property
    def plot_lines_count(self) -> int:
        self.beginGroup("plot")
        v: int = cast(int, self.value("plotLinesCount", 8, int))
        self.endGroup()
        return v

    @plot_lines_count.setter
    def plot_lines_count(self, plot_lines_count: int) -> None:
        self.beginGroup("plot")
        self.setValue("plotLinesCount", plot_lines_count)
        self.endGroup()

    @property
    def argument(self) -> str:
        self.beginGroup("plot")
        v: str = cast(str, self.value("xAxis"))
        self.endGroup()
        return v

    @argument.setter
    def argument(self, new_value: str) -> None:
        self.beginGroup("plot")
        self.setValue("xAxis", new_value)
        self.endGroup()

    @property
    def opened_file_name(self) -> str:
        try:
            self.beginGroup("location")
            return cast(str, self.value("open", str(Path.cwd()), str))
        finally:
            self.endGroup()

    @opened_file_name.setter
    def opened_file_name(self, filename: str) -> None:
        self.beginGroup("location")
        self.setValue("open", filename)
        self.endGroup()

    @property
    def exported_file_name(self) -> str:
        try:
            self.beginGroup("location")
            return cast(str, self.value("export", str(Path.cwd()), str))
        finally:
            self.endGroup()

    @exported_file_name.setter
    def exported_file_name(self, filename: str) -> None:
        self.beginGroup("location")
        self.setValue("export", filename)
        self.endGroup()

    @property
    def export_dialog_state(self) -> QtCore.QByteArray:
        try:
            self.beginGroup("location")
            return cast(QtCore.QByteArray, self.value("exportDialogState", QtCore.QByteArray()))
        finally:
            self.endGroup()

    @export_dialog_state.setter
    def export_dialog_state(self, state: QtCore.QByteArray) -> None:
        self.beginGroup("location")
        self.setValue("exportDialogState", state)
        self.endGroup()

    @property
    def export_dialog_geometry(self) -> QtCore.QByteArray:
        try:
            self.beginGroup("location")
            return cast(QtCore.QByteArray, self.value("exportDialogGeometry", QtCore.QByteArray()))
        finally:
            self.endGroup()

    @export_dialog_geometry.setter
    def export_dialog_geometry(self, state: QtCore.QByteArray) -> None:
        self.beginGroup("location")
        self.setValue("exportDialogGeometry", state)
        self.endGroup()

    @property
    def open_dialog_state(self) -> QtCore.QByteArray:
        try:
            self.beginGroup("location")
            return cast(QtCore.QByteArray, self.value("openDialogState", QtCore.QByteArray()))
        finally:
            self.endGroup()

    @open_dialog_state.setter
    def open_dialog_state(self, state: QtCore.QByteArray) -> None:
        self.beginGroup("location")
        self.setValue("openDialogState", state)
        self.endGroup()

    @property
    def open_dialog_geometry(self) -> QtCore.QByteArray:
        try:
            self.beginGroup("location")
            return cast(QtCore.QByteArray, self.value("openDialogGeometry", QtCore.QByteArray()))
        finally:
            self.endGroup()

    @open_dialog_geometry.setter
    def open_dialog_geometry(self, state: QtCore.QByteArray) -> None:
        self.beginGroup("location")
        self.setValue("openDialogGeometry", state)
        self.endGroup()
