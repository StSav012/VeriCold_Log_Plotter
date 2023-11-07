# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, ClassVar, Final, Iterable, Sequence, TextIO, cast, final

import numpy as np
from numpy.typing import NDArray
from pyqtgraph import ComboBox, ViewBox
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from gui._data_model import DataModel
from gui._menu_bar import MenuBar
from gui._plot import Plot
from gui._plot_line_options import PlotLineOptions
from gui._preferences import Preferences
from gui._settings import Settings
from log_parser import parse

__all__ = ["MainWindow", "PLOT_LINES_COUNT"]

PLOT_LINES_COUNT: Final[int] = 8


@final
class MainWindow(QtWidgets.QMainWindow):
    _initial_window_title: ClassVar[str] = QtWidgets.QApplication.translate(
        "initial main window title",
        "VeriCold Plotter",
    )

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent=parent)

        self.settings: Settings = Settings("SavSoft", "VeriCold Plotter", self)
        self.install_translation()

        self.central_widget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.main_layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.central_widget)

        self.dock_settings: QtWidgets.QDockWidget = QtWidgets.QDockWidget(self)
        self.box_settings: QtWidgets.QWidget = QtWidgets.QWidget(self.dock_settings)
        self.settings_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.box_settings)
        self.layout_x_axis: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        self.combo_x_axis: ComboBox = ComboBox(self.box_settings)
        self.combo_y_axis: ComboBox = ComboBox(self.box_settings)
        self.line_options_y_axis: list[PlotLineOptions] = [
            PlotLineOptions(items=[], settings=self.settings, parent=self.dock_settings)
            for _ in range(PLOT_LINES_COUNT)
        ]

        self.data_model: DataModel = DataModel()
        self.plot: Plot = Plot(self)

        self.export_all: bool = True
        self.menu_bar: MenuBar = MenuBar(self)

        self.status_bar: QtWidgets.QStatusBar = QtWidgets.QStatusBar(self)

        self._opened_file_name: str = ""
        self._exported_file_name: str = ""

        self.reload_timer: QtCore.QTimer = QtCore.QTimer(self)
        self.file_created: float = 0.0

        self.setup_ui()

    def setup_ui(self) -> None:
        # https://ru.stackoverflow.com/a/1032610
        window_icon: QtGui.QPixmap = QtGui.QPixmap()
        # language=SVG
        window_icon.loadFromData(
            b"""
<svg version="1.1" viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#282e70"/>
    <path d="M 23 44 A 44 44 0 1 1 23 84" fill="none" stroke="#fff" stroke-linecap="round" stroke-width="18"/>
    <path d="M 45 32 A 36.5 36.5 0 1 1 45 96 A 40 40 0 1 0 45 32" fill="#282e70" stroke="none"/>
</svg>
"""
        )
        self.setWindowIcon(QtGui.QIcon(window_icon))

        self.setObjectName("main_window")
        self.resize(640, 480)
        self.central_widget.setObjectName("central_widget")
        self.main_layout.setObjectName("main_layout")
        self.main_layout.addWidget(self.plot)
        self.setCentralWidget(self.central_widget)
        self.setMenuBar(self.menu_bar)
        self.status_bar.setObjectName("status_bar")
        self.setStatusBar(self.status_bar)

        self.menu_bar.action_open.triggered.connect(self.on_action_open_triggered)
        self.menu_bar.action_export.triggered.connect(self.on_action_export_triggered)
        self.menu_bar.action_export_visible.triggered.connect(self.on_action_export_visible_triggered)
        self.menu_bar.action_reload.triggered.connect(self.on_action_reload_triggered)
        self.menu_bar.action_auto_reload.toggled.connect(self.on_action_auto_reload_toggled)
        self.menu_bar.action_preferences.triggered.connect(self.on_action_preferences_triggered)
        self.menu_bar.action_quit.triggered.connect(self.on_action_quit_triggered)

        self.dock_settings.setObjectName("dock_settings")
        self.dock_settings.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.dock_settings.setFeatures(
            cast(
                QtWidgets.QDockWidget.DockWidgetFeature,
                self.dock_settings.features() & ~self.dock_settings.DockWidgetFeature.DockWidgetClosable,
            )
        )
        self.dock_settings.setWidget(self.box_settings)
        self.layout_x_axis.addRow(self.tr("x-axis:"), self.combo_x_axis)
        self.layout_x_axis.addRow(self.tr("y-axis:"), self.combo_y_axis)
        self.settings_layout.addLayout(self.layout_x_axis)
        cb: PlotLineOptions
        for cb in self.line_options_y_axis:
            self.settings_layout.addWidget(cb)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.dock_settings)

        self.setWindowTitle(MainWindow._initial_window_title)
        self.dock_settings.setWindowTitle(self.tr("Options"))

        self.load_settings()

        self.combo_x_axis.currentTextChanged.connect(self.on_x_axis_changed)
        self.combo_y_axis.setItems((self.tr("absolute"), self.tr("relative"), self.tr("logarithmic")))
        self.combo_y_axis.currentIndexChanged.connect(self.on_y_axis_mode_changed)
        for cb in self.line_options_y_axis:
            cb.itemChanged.connect(self.on_y_axis_changed)
            cb.colorChanged.connect(self.on_color_changed)
            cb.toggled.connect(self.on_line_toggled)

        self.reload_timer.setInterval(1000)
        self.reload_timer.timeout.connect(self.on_timeout)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.reload_timer.stop()
        self.save_settings()
        event.accept()

    def load_settings(self) -> None:
        self.settings.beginGroup("location")
        self._opened_file_name = cast(str, self.settings.value("open", str(Path.cwd()), str))
        self._exported_file_name = cast(str, self.settings.value("export", str(Path.cwd()), str))
        self.settings.endGroup()

        self.settings.beginGroup("window")
        # Fallback: Center the window
        desktop: QtGui.QScreen = QtWidgets.QApplication.screens()[0]
        window_frame: QtCore.QRect = self.frameGeometry()
        desktop_center: QtCore.QPoint = desktop.availableGeometry().center()
        window_frame.moveCenter(desktop_center)
        self.move(window_frame.topLeft())

        # noinspection PyTypeChecker
        self.restoreGeometry(cast(QtCore.QByteArray, self.settings.value("geometry", QtCore.QByteArray())))
        # noinspection PyTypeChecker
        self.restoreState(cast(QtCore.QByteArray, self.settings.value("state", QtCore.QByteArray())))
        self.settings.endGroup()

        self.settings.beginGroup("plot")
        self.plot.mouse_mode = cast(int, self.settings.value("mouseMode", ViewBox.PanMode, int))
        self.settings.endGroup()

    def save_settings(self) -> None:
        self.settings.beginGroup("location")
        self.settings.setValue("open", self._opened_file_name)
        self.settings.setValue("export", self._exported_file_name)
        self.settings.endGroup()

        self.settings.beginGroup("window")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("state", self.saveState())
        self.settings.endGroup()

        self.settings.beginGroup("plot")
        self.settings.setValue("mouseMode", self.plot.mouse_mode)
        self.settings.endGroup()

        self.settings.sync()

    def install_translation(self) -> None:
        if self.settings.translation_path is not None:
            translator: QtCore.QTranslator = QtCore.QTranslator(self)
            translator.load(str(self.settings.translation_path))
            QtWidgets.QApplication.instance().installTranslator(translator)

    def load_file(self, file_name: str | Iterable[str], check_file_updates: bool = False) -> bool:
        if not file_name:
            return False
        titles: list[str]
        data: NDArray[np.float64]
        if isinstance(file_name, (set, Sequence, Iterable)) and not isinstance(file_name, str):
            all_titles: list[list[str]] = []
            all_data: list[NDArray[np.float64]] = []
            _file_names: Iterable[str] = file_name
            for file_name in _file_names:
                try:
                    titles, data = parse(file_name)
                except (IOError, RuntimeError) as ex:
                    self.status_bar.showMessage(" ".join(repr(a) for a in ex.args))
                    continue
                else:
                    all_titles.append(titles)
                    all_data.append(data)
            if not all_titles or not all_data:
                return False
            # use only the files with identical columns
            titles = all_titles[-1]
            i: int = len(all_titles) - 2
            while i >= 0 and all_titles[i] == titles:
                i -= 1
            data = np.column_stack(all_data[i + 1 :])
        else:
            try:
                titles, data = parse(file_name)
            except (IOError, RuntimeError) as ex:
                self.status_bar.showMessage(" ".join(repr(a) for a in ex.args))
                return False
        self._opened_file_name = file_name
        self.data_model.set_data(data, titles)

        self.combo_x_axis.blockSignals(True)
        self.combo_x_axis.setItems(
            tuple(
                filter(
                    lambda t: t.endswith("(secs)") or t.endswith("(s)"),
                    self.data_model.header,
                )
            )
        )
        self.combo_x_axis.setCurrentText(self.settings.argument)
        self.combo_x_axis.blockSignals(False)

        cb: PlotLineOptions
        for cb in self.line_options_y_axis:
            cb.set_items(
                tuple(
                    filter(
                        lambda t: not (t.endswith("(secs)") or t.endswith("(s)")),
                        self.data_model.header,
                    )
                )
            )
        self.plot.plot(
            self.data_model,
            self.combo_x_axis.value(),
            (cb.option for cb in self.line_options_y_axis),
            colors=(cb.color for cb in self.line_options_y_axis),
            visibility=(cb.checked for cb in self.line_options_y_axis),
        )
        self.menu_bar.action_export.setEnabled(True)
        self.menu_bar.action_export_visible.setEnabled(True)
        self.menu_bar.action_reload.setEnabled(True)
        self.menu_bar.action_auto_reload.setEnabled(True)
        self.status_bar.showMessage(self.tr("Ready"))
        self.file_created = Path(self._opened_file_name).lstat().st_mtime
        self.check_file_updates = check_file_updates
        self.setWindowTitle(f"{file_name} — {MainWindow._initial_window_title}")
        return True

    def visible_data(self) -> tuple[NDArray[np.float64], list[str]]:
        header = [self.data_model.header[0]] + [o.option for o in self.line_options_y_axis]
        data = self.data_model.data[[self.data_model.header.index(h) for h in header]]

        # crop the visible rectangle
        x_min: float
        x_max: float
        y_min: float
        y_max: float
        ((x_min, x_max), (y_min, y_max)) = self.plot.view_range
        data = data[..., ((data[0] >= x_min) & (data[0] <= x_max))]
        somehow_visible_lines: list[bool] = [True] + [bool(np.any((d >= y_min) & (d <= y_max))) for d in data[1:]]
        data = data[somehow_visible_lines]
        header = [h for h, b in zip(header, somehow_visible_lines) if b]
        return data, header

    def save_csv(self, filename: str) -> bool:
        data: NDArray[np.float64] = self.data_model.data
        header: list[str]
        if self.export_all:
            header = self.data_model.header
        else:
            data, header = self.visible_data()
        try:
            f_out: TextIO
            with open(filename, "wt", newline="") as f_out:
                f_out.write(self.settings.csv_separator.join(header) + self.settings.line_end)
                f_out.writelines(
                    (
                        (
                            self.settings.csv_separator.join(f"{xii}" for xii in xi)
                            if isinstance(xi, Iterable)
                            else f"{xi}"
                        )
                        + self.settings.line_end
                    )
                    for xi in data.T
                )
        except IOError as ex:
            self.status_bar.showMessage(" ".join(ex.args))
            return False
        else:
            self._exported_file_name = filename
            self.status_bar.showMessage(self.tr("Saved to {0}").format(filename))
            return True

    def save_xlsx(self, filename: str) -> bool:
        try:
            from pyexcelerate import Font, Format, Panes, Style, Workbook, Worksheet
        except ImportError as ex:
            self.status_bar.showMessage(" ".join(repr(a) for a in ex.args))
            return False

        if not Path(filename).suffix.casefold() == ".xlsx":
            filename += ".xlsx"

        data: NDArray[np.float64] = self.data_model.data
        header: list[str]
        if self.export_all:
            header = self.data_model.header
        else:
            data, header = self.visible_data()
        try:
            workbook: Workbook = Workbook()
            worksheet: Worksheet = workbook.new_sheet(str(Path(self._opened_file_name).with_suffix("").name))
            worksheet.panes = Panes(y=1)  # freeze first row

            header_style: Style = Style(font=Font(bold=True))
            datetime_style: Style = Style(format=Format("yyyy-mm-dd hh:mm:ss"), size=-1)
            auto_size_style: Style = Style(size=-1)

            col: int
            row: int
            for col in range(data.shape[0]):
                worksheet.set_cell_value(1, col + 1, header[col])
                if header[col].endswith(("(s)", "(secs)")):
                    for row in range(data.shape[1]):
                        worksheet.set_cell_value(row + 2, col + 1, datetime.fromtimestamp(data[col, row]))
                        worksheet.set_cell_style(row + 2, col + 1, datetime_style)
                else:
                    for row in range(data.shape[1]):
                        worksheet.set_cell_value(row + 2, col + 1, data[col, row])
                        worksheet.set_cell_style(row + 2, col + 1, auto_size_style)
            worksheet.set_row_style(1, header_style)
            workbook.save(filename)
        except IOError as ex:
            self.status_bar.showMessage(" ".join(ex.args))
            return False
        else:
            self._exported_file_name = filename
            self.status_bar.showMessage(self.tr("Saved to {0}").format(filename))
            return True

    @property
    def check_file_updates(self) -> bool:
        return self.reload_timer.isActive()

    @check_file_updates.setter
    def check_file_updates(self, new_value: bool) -> None:
        self.menu_bar.action_auto_reload.setChecked(new_value)

    @QtCore.Slot()
    def on_action_open_triggered(self) -> None:
        new_file_names: list[str]
        new_file_names, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            self.tr("Open"),
            self._opened_file_name,
            f'{self.tr("VeriCold data logfile")} (*.vcl);;{self.tr("All Files")} (*.*)',
        )
        self.load_file(new_file_names)

    def export(self) -> None:
        import importlib.util

        supported_formats: dict[str, str] = {".csv": f'{self.tr("Text with separators")}(*.csv)'}
        supported_formats_callbacks: dict[str, Callable[[str], bool]] = {".csv": self.save_csv}
        if importlib.util.find_spec("pyexcelerate") is not None:
            supported_formats[".xlsx"] = f'{self.tr("Microsoft Excel")}(*.xlsx)'
            supported_formats_callbacks[".xlsx"] = self.save_xlsx
        selected_filter: str = ""
        if self._exported_file_name:
            exported_file_name_ext: str = Path(self._exported_file_name).suffix
            if exported_file_name_ext in supported_formats:
                selected_filter = supported_formats[exported_file_name_ext]
        new_file_name: str
        new_file_name_filter: str  # BUG: `new_file_name_filter` is empty when a native dialog is used
        # noinspection PyTypeChecker
        new_file_name, new_file_name_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr("Export"),
            str(
                Path(self._exported_file_name or self._opened_file_name)
                .with_name(Path(self._opened_file_name).name)
                .with_suffix("")
            ),
            ";;".join(supported_formats.values()),
            selected_filter,
        )
        if not new_file_name:
            return
        new_file_name_ext: str = Path(new_file_name).suffix
        if new_file_name_ext in supported_formats_callbacks:
            supported_formats_callbacks[new_file_name_ext](new_file_name)

    @QtCore.Slot()
    def on_action_export_triggered(self) -> None:
        self.export_all = True
        self.export()

    @QtCore.Slot()
    def on_action_export_visible_triggered(self) -> None:
        self.export_all = False
        self.export()

    @QtCore.Slot()
    def on_action_reload_triggered(self) -> None:
        self.load_file(self._opened_file_name)

    @QtCore.Slot(bool)
    def on_action_auto_reload_toggled(self, new_state: bool) -> None:
        if new_state:
            self.reload_timer.start()
        else:
            self.reload_timer.stop()

    @QtCore.Slot()
    def on_action_preferences_triggered(self) -> None:
        preferences_dialog: Preferences = Preferences(self.settings, self)
        preferences_dialog.exec()
        self.install_translation()

    @QtCore.Slot()
    def on_action_quit_triggered(self) -> None:
        self.close()

    @QtCore.Slot(str)
    def on_x_axis_changed(self, new_text: str) -> None:
        normalized: bool = self.combo_y_axis.currentIndex() == 1
        sender_index: int
        for sender_index in range(min(len(self.line_options_y_axis), len(self.plot.lines))):
            self.plot.replot(
                sender_index,
                self.data_model,
                new_text,
                self.line_options_y_axis[sender_index].option,
                normalized=normalized,
            )
        self.settings.argument = new_text

    @QtCore.Slot(int, str)
    def on_y_axis_changed(self, sender_index: int, title: str) -> None:
        normalized: bool = self.combo_y_axis.currentIndex() == 1
        self.plot.replot(
            sender_index,
            self.data_model,
            self.combo_x_axis.currentText(),
            title,
            color=self.settings.line_colors.get(title, PlotLineOptions.DEFAULT_COLOR),
            normalized=normalized,
        )

    @QtCore.Slot(int)
    def on_y_axis_mode_changed(self, new_index: int) -> None:
        # PlotItem.setLogMode causes a crash here sometimes; the reason is unknown
        log_mode_y: bool = new_index == 2
        if self.plot.canvas.getAxis("left").logMode != log_mode_y:
            for i in self.plot.canvas.items:
                if hasattr(i, "setLogMode"):
                    i.setLogMode(False, log_mode_y)
            self.plot.canvas.getAxis("left").setLogMode(log_mode_y)
            self.plot.canvas.vb.enableAutoRange()
            self.plot.canvas.recomputeAverages()

        sender_index: int
        for sender_index in range(len(self.line_options_y_axis)):
            self.plot.replot(
                sender_index,
                self.data_model,
                self.combo_x_axis.currentText(),
                self.line_options_y_axis[sender_index].option,
                normalized=(new_index == 1),
            )
        self.plot.auto_range_y()

    @QtCore.Slot(int, QtGui.QColor)
    def on_color_changed(self, sender_index: int, new_color: QtGui.QColor) -> None:
        normalized: bool = self.combo_y_axis.currentIndex() == 1
        self.plot.replot(
            sender_index,
            self.data_model,
            self.combo_x_axis.currentText(),
            self.line_options_y_axis[sender_index].option,
            color=new_color,
            normalized=normalized,
        )

    @QtCore.Slot(int, bool)
    def on_line_toggled(self, sender_index: int, new_state: bool) -> None:
        self.plot.set_line_visible(sender_index, new_state)

    @QtCore.Slot()
    def on_timeout(self) -> None:
        if not self._opened_file_name:
            return

        if not Path(self._opened_file_name).exists():
            return

        if self.file_created == Path(self._opened_file_name).lstat().st_mtime:
            return
        else:
            self.file_created = Path(self._opened_file_name).lstat().st_mtime

        titles: list[str]
        data: NDArray[np.float64]
        try:
            titles, data = parse(self._opened_file_name)
        except (IOError, RuntimeError) as ex:
            self.status_bar.showMessage(" ".join(repr(a) for a in ex.args))
        else:
            self.data_model.set_data(data, titles)

            sender_index: int
            for sender_index in range(min(len(self.line_options_y_axis), len(self.plot.lines))):
                self.plot.replot(
                    sender_index,
                    self.data_model,
                    self.combo_x_axis.currentText(),
                    self.line_options_y_axis[sender_index].option,
                    roll=True,
                )

            self.status_bar.showMessage(
                self.tr("Reloaded {0}").format(datetime.now().isoformat(sep=" ", timespec="seconds"))
            )
