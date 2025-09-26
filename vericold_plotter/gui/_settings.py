import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, NamedTuple, Self, TypeVar, cast, overload

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

__all__ = ["Settings"]

_T: TypeVar = TypeVar("_T")


class Settings(QtCore.QSettings):
    """Convenient internal representation of the application settings."""

    LINE_ENDS: ClassVar[dict[str, str]] = {
        "\n": QtCore.QCoreApplication.translate("line end", r"Line Feed (\n)"),
        "\r": QtCore.QCoreApplication.translate("line end", r"Carriage Return (\r)"),
        "\r\n": QtCore.QCoreApplication.translate("line end", r"CR+LF (\r\n)"),
        "\n\r": QtCore.QCoreApplication.translate("line end", r"LF+CR (\n\r)"),
    }
    CSV_SEPARATORS: ClassVar[dict[str, str]] = {
        ",": QtCore.QCoreApplication.translate("csv separator", r"comma (,)"),
        "\t": QtCore.QCoreApplication.translate("csv separator", r"tab (\t)"),
        ";": QtCore.QCoreApplication.translate("csv separator", r"semicolon (;)"),
        " ": QtCore.QCoreApplication.translate("csv separator", r"space ( )"),
    }

    if TYPE_CHECKING:
        # to silence IDE warnings, make `value` return a provided type

        @overload
        def value(self, key: str, /) -> _T: ...
        @overload
        def value(self, key: str, /, default_value: _T = ...) -> _T: ...
        @overload
        def value(self, key: str, /, default_value: _T = ..., value_type: type[_T] = ...) -> _T: ...
        def value(self, key: str, /, default_value: _T = ..., value_type: type[_T] = ...) -> _T:
            return cast(_T, super().value(key, default_value, value_type))

    class CheckBox(NamedTuple):
        callback: str

    class PathEntry(NamedTuple):
        callback: str

    class ComboBox(NamedTuple):
        callback: str
        text: Sequence[str]
        data: Sequence[str] | None = None

    class SpinBox(NamedTuple):
        callback: str
        min: int
        max: int
        step: int = 1
        prefix: str = ""
        suffix: str = ""

    class DoubleSpinBox(NamedTuple):
        callback: str
        min: float
        max: float
        step: float
        prefix: str = ""
        suffix: str = ""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.check_items_names: list[str] = []
        self.check_items_values: list[bool] = []

        self.line_colors: dict[str, QtGui.QColor] = dict()
        self.line_enabled: dict[str, bool] = dict()
        self.data_series_names: dict[int, str] = dict()

        with self.section("plot"):
            key: str
            for key in self.allKeys():
                if key.endswith(" color"):
                    self.line_colors[key.removesuffix(" color")] = cast(QtGui.QColor, self.value(key))
                if key.endswith(" enabled"):
                    self.line_enabled[key.removesuffix(" enabled")] = cast(bool, self.value(key, False, bool))

            i: int
            for i in range(self.beginReadArray("dataSeries")):
                self.setArrayIndex(i)
                self.data_series_names[i] = cast(str, self.value("name"))
            self.endArray()

    def sync(self) -> None:
        with self.section("plot"):
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

        super().sync()

    @property
    def dialog(
        self,
    ) -> dict[
        str,
        dict[str, CheckBox | PathEntry | ComboBox | SpinBox | DoubleSpinBox],
    ]:
        return {
            self.tr("View"): {
                self.tr("Translation file:"): Settings.PathEntry(
                    callback=Settings.translation_path.fget.__name__,
                ),
                self.tr("Lines count:"): Settings.SpinBox(
                    callback=Settings.plot_lines_count.fget.__name__,
                    min=1,
                    max=99,
                ),
            },
            self.tr("Export"): {
                self.tr("Line ending:"): Settings.ComboBox(
                    Settings.line_end.fget.__name__,
                    list(Settings.LINE_ENDS.values()),
                    list(Settings.LINE_ENDS.keys()),
                ),
                self.tr("CSV separator:"): Settings.ComboBox(
                    Settings.csv_separator.fget.__name__,
                    list(Settings.CSV_SEPARATORS.values()),
                    list(Settings.CSV_SEPARATORS.keys()),
                ),
            },
        }

    @contextmanager
    def section(self, section: str) -> Iterator[Self]:
        self.beginGroup(section)
        try:
            yield self
        finally:
            self.endGroup()

    def save(self, w: QtWidgets.QWidget) -> None:
        name: str = w.objectName()
        if not name:
            raise AttributeError(f"No name given for {w}")
        with suppress(AttributeError), self.section("state"):
            # noinspection PyUnresolvedReferences
            self.setValue(name, w.saveState())
        with suppress(AttributeError), self.section("geometry"):
            # noinspection PyUnresolvedReferences
            self.setValue(name, w.saveGeometry())

    def restore(self, w: QtWidgets.QWidget) -> None:
        name: str = w.objectName()
        if not name:
            raise AttributeError(f"No name given for {w}")
        with suppress(AttributeError), self.section("state"):
            # noinspection PyUnresolvedReferences
            w.restoreState(self.value(name, QtCore.QByteArray()))
        with suppress(AttributeError), self.section("geometry"):
            # noinspection PyUnresolvedReferences
            w.restoreGeometry(self.value(name, QtCore.QByteArray()))

    @property
    def line_end(self) -> str:
        with self.section("export"):
            return list(Settings.LINE_ENDS.keys())[
                cast(
                    int,
                    self.value(
                        "lineEnd",
                        list(Settings.LINE_ENDS.keys()).index(os.linesep),
                        int,
                    ),
                )
            ]

    @line_end.setter
    def line_end(self, new_value: str) -> None:
        with self.section("export"):
            self.setValue("lineEnd", list(Settings.LINE_ENDS.keys()).index(new_value))

    @property
    def csv_separator(self) -> str:
        with self.section("export"):
            return list(Settings.CSV_SEPARATORS.keys())[
                cast(
                    int,
                    self.value(
                        "csvSeparator",
                        list(Settings.CSV_SEPARATORS.keys()).index("\t"),
                        int,
                    ),
                )
            ]

    @csv_separator.setter
    def csv_separator(self, new_value: str) -> None:
        with self.section("export"):
            self.setValue("csvSeparator", list(Settings.CSV_SEPARATORS.keys()).index(new_value))

    @property
    def translation_path(self) -> Path | None:
        with self.section("translation"):
            v: str = cast(str, self.value("filePath", "", str))
        return Path(v) if v else None

    @translation_path.setter
    def translation_path(self, new_value: Path | None) -> None:
        with self.section("translation"):
            self.setValue("filePath", str(new_value) if new_value is not None else "")

    @property
    def plot_lines_count(self) -> int:
        with self.section("plot"):
            return cast(int, self.value("plotLinesCount", 8, int))

    @plot_lines_count.setter
    def plot_lines_count(self, plot_lines_count: int) -> None:
        with self.section("plot"):
            self.setValue("plotLinesCount", plot_lines_count)

    @property
    def argument(self) -> str:
        with self.section("plot"):
            return cast(str, self.value("xAxis"))

    @argument.setter
    def argument(self, new_value: str) -> None:
        with self.section("plot"):
            self.setValue("xAxis", new_value)

    @property
    def opened_file_name(self) -> str:
        with self.section("location"):
            return cast(str, self.value("open", str(Path.cwd()), str))

    @opened_file_name.setter
    def opened_file_name(self, filename: str) -> None:
        with self.section("location"):
            self.setValue("open", filename)

    @property
    def exported_file_name(self) -> str:
        with self.section("location"):
            return cast(str, self.value("export", str(Path.cwd()), str))

    @exported_file_name.setter
    def exported_file_name(self, filename: str) -> None:
        with self.section("location"):
            self.setValue("export", filename)

    @property
    def export_dialog_state(self) -> QtCore.QByteArray:
        with self.section("location"):
            return cast(QtCore.QByteArray, self.value("exportDialogState", QtCore.QByteArray()))

    @export_dialog_state.setter
    def export_dialog_state(self, state: QtCore.QByteArray) -> None:
        with self.section("location"):
            self.setValue("exportDialogState", state)

    @property
    def export_dialog_geometry(self) -> QtCore.QByteArray:
        with self.section("location"):
            return cast(QtCore.QByteArray, self.value("exportDialogGeometry", QtCore.QByteArray()))

    @export_dialog_geometry.setter
    def export_dialog_geometry(self, state: QtCore.QByteArray) -> None:
        with self.section("location"):
            self.setValue("exportDialogGeometry", state)

    @property
    def open_dialog_state(self) -> QtCore.QByteArray:
        with self.section("location"):
            return cast(QtCore.QByteArray, self.value("openDialogState", QtCore.QByteArray()))

    @open_dialog_state.setter
    def open_dialog_state(self, state: QtCore.QByteArray) -> None:
        with self.section("location"):
            self.setValue("openDialogState", state)

    @property
    def open_dialog_geometry(self) -> QtCore.QByteArray:
        with self.section("location"):
            return cast(QtCore.QByteArray, self.value("openDialogGeometry", QtCore.QByteArray()))

    @open_dialog_geometry.setter
    def open_dialog_geometry(self, state: QtCore.QByteArray) -> None:
        with self.section("location"):
            self.setValue("openDialogGeometry", state)
