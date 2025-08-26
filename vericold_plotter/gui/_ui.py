from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import ClassVar, cast, final

import numpy as np
from numpy.typing import NDArray
from pyqtgraph import ComboBox, ViewBox
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from ..log_parser import parse
from ._data_model import DataModel
from ._file_dialog import FileDialog
from ._menu_bar import MenuBar
from ._plot import Plot
from ._plot_line_options import PlotLineOptions
from ._preferences import Preferences
from ._settings import Settings

__all__ = ["MainWindow"]


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

        self.dock_settings: QtWidgets.QDockWidget = QtWidgets.QDockWidget(self)
        self.box_settings: QtWidgets.QWidget = QtWidgets.QWidget(self.dock_settings)
        self.settings_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.box_settings)
        self.layout_y_axis: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        self.combo_y_axis: ComboBox = ComboBox(self.box_settings)
        self.line_options_y_axis: list[PlotLineOptions] = [
            PlotLineOptions(items=[], settings=self.settings, parent=self.dock_settings)
            for _ in range(self.settings.plot_lines_count)
        ]

        self.data_model: DataModel = DataModel()
        self.plot: Plot = Plot(self)

        self.menu_bar: MenuBar = MenuBar(self)

        self.status_bar: QtWidgets.QStatusBar = QtWidgets.QStatusBar(self)

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
    <rect width="128" height="128" fill="#282e70"/>
    <path d="M 23 44 A 44 44 0 1 1 23 84" fill="none" stroke="#fff" stroke-linecap="round" stroke-width="18"/>
    <path d="M 45 32 A 36.5 36.5 0 1 1 45 96 A 40 40 0 1 0 45 32" fill="#282e70" stroke="none"/>
</svg>
"""
        )
        self.setWindowIcon(QtGui.QIcon(window_icon))

        self.setObjectName("main_window")
        self.resize(640, 480)
        self.setCentralWidget(self.plot)
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
        self.dock_settings.setWidget(self.box_settings)
        self.menu_bar.menu_view.addAction(self.dock_settings.toggleViewAction())

        self.layout_y_axis.addRow(self.tr("y-axis:"), self.combo_y_axis)
        self.settings_layout.addLayout(self.layout_y_axis)
        cb: PlotLineOptions
        for cb in self.line_options_y_axis:
            self.settings_layout.addWidget(cb)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.dock_settings)

        self.setWindowTitle(MainWindow._initial_window_title)
        self.dock_settings.setWindowTitle(self.tr("&Options"))

        self.load_settings()

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
        self.plot.grid_x = cast(int, self.settings.value("gridX", 80, int))
        self.plot.grid_y = cast(int, self.settings.value("gridY", 80, int))
        self.settings.endGroup()

    def save_settings(self) -> None:
        self.settings.beginGroup("window")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("state", self.saveState())
        self.settings.endGroup()

        self.settings.beginGroup("plot")
        self.settings.setValue("mouseMode", self.plot.mouse_mode)
        self.settings.setValue("gridX", self.plot.grid_x)
        self.settings.setValue("gridY", self.plot.grid_y)
        self.settings.endGroup()

        self.settings.sync()

    def install_translation(self) -> None:
        if self.settings.translation_path is not None:
            translator: QtCore.QTranslator = QtCore.QTranslator(self)
            translator.load(str(self.settings.translation_path))
            QtWidgets.QApplication.instance().installTranslator(translator)

    def load_file(
        self,
        file_name: str | Iterable[str],
        check_file_updates: bool | None = None,
    ) -> bool:
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
                except (OSError, RuntimeError) as ex:
                    self.status_bar.showMessage(" ".join(str(a) for a in ex.args))
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
            except (OSError, RuntimeError) as ex:
                self.status_bar.showMessage(" ".join(str(a) for a in ex.args))
                return False
        self.settings.opened_file_name = file_name
        self.data_model.set_data(data, titles)

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
            (cb.option for cb in self.line_options_y_axis),
            colors=(cb.color for cb in self.line_options_y_axis),
            visibility=(cb.checked for cb in self.line_options_y_axis),
        )
        self.menu_bar.action_export.setEnabled(True)
        self.menu_bar.action_export_visible.setEnabled(True)
        self.menu_bar.action_reload.setEnabled(True)
        self.menu_bar.action_auto_reload.setEnabled(True)
        now: QtCore.QDateTime = QtCore.QDateTime.currentDateTime()
        self.status_bar.showMessage(
            self.tr("Loaded {date} at {time}").format(
                date=self.locale().toString(now.date(), QtCore.QLocale.FormatType.NarrowFormat),
                time=self.locale().toString(now.time(), QtCore.QLocale.FormatType.NarrowFormat),
            )
        )
        self.file_created = Path(self.settings.opened_file_name).lstat().st_mtime
        if check_file_updates is not None:
            self.check_file_updates = check_file_updates
        self.setWindowTitle(f"{file_name} — {MainWindow._initial_window_title}")
        return True

    def visible_data(self) -> tuple[NDArray[np.float64], list[str]]:
        header = [self.data_model.header[0]] + [o.option for o in self.line_options_y_axis if o.checked]
        data = self.data_model.data[[self.data_model.header.index(h) for h in header]]

        # ignore all-NaN lines
        data = data[..., ~np.all(np.isnan(data[1:]), axis=0)]

        # crop to the visible rectangle
        x_min: float
        x_max: float
        y_min: float
        y_max: float
        ((x_min, x_max), (y_min, y_max)) = self.plot.view_range
        # ignore points outside the selected time range
        data = data[..., ((data[0] >= x_min) & (data[0] <= x_max))]
        # ignore lines where all values are out of Y range
        data = data[..., np.any((data[1:] >= y_min) & (data[1:] <= y_max), axis=0)]
        somehow_visible_lines: list[bool] = [True] + [bool(np.any((d >= y_min) & (d <= y_max))) for d in data[1:]]
        data = data[somehow_visible_lines]
        header = [h for h, b in zip(header, somehow_visible_lines) if b]
        return data, header

    @property
    def check_file_updates(self) -> bool:
        return self.reload_timer.isActive()

    @check_file_updates.setter
    def check_file_updates(self, new_value: bool) -> None:
        self.menu_bar.action_auto_reload.setChecked(new_value)

    @QtCore.Slot()
    def on_action_open_triggered(self) -> None:
        fd: FileDialog = FileDialog(self.settings, self)
        new_file_names: list[str] = fd.get_open_filenames()
        if new_file_names:
            self.load_file(new_file_names)

    def export(self, export_all: bool = True) -> None:
        data: NDArray[np.float64]
        header: list[str]
        if export_all:
            data = self.data_model.data
            header = self.data_model.header
        else:
            data, header = self.visible_data()
        try:
            fd: FileDialog = FileDialog(self.settings, self)
            fd.export(data, header)
        except OSError as ex:
            self.status_bar.showMessage(" ".join(ex.args))
        else:
            self.status_bar.showMessage(self.tr("Saved to {0}").format(self.settings.exported_file_name))

    @QtCore.Slot()
    def on_action_export_triggered(self) -> None:
        self.export(export_all=True)

    @QtCore.Slot()
    def on_action_export_visible_triggered(self) -> None:
        self.export(export_all=False)

    @QtCore.Slot()
    def on_action_reload_triggered(self) -> None:
        self.load_file(self.settings.opened_file_name)

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

    @QtCore.Slot(int, str)
    def on_y_axis_changed(self, sender_index: int, title: str) -> None:
        normalized: bool = self.combo_y_axis.currentIndex() == 1
        self.plot.replot(
            sender_index,
            self.data_model,
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
            self.line_options_y_axis[sender_index].option,
            color=new_color,
            normalized=normalized,
        )

    @QtCore.Slot(int, bool)
    def on_line_toggled(self, sender_index: int, new_state: bool) -> None:
        self.plot.set_line_visible(sender_index, new_state)

    @QtCore.Slot()
    def on_timeout(self) -> None:
        if not self.settings.opened_file_name:
            return

        if not Path(self.settings.opened_file_name).exists():
            return

        if self.file_created == Path(self.settings.opened_file_name).lstat().st_mtime:
            return
        self.file_created = Path(self.settings.opened_file_name).lstat().st_mtime

        titles: list[str]
        data: NDArray[np.float64]
        try:
            titles, data = parse(self.settings.opened_file_name)
        except (OSError, RuntimeError) as ex:
            self.status_bar.showMessage(" ".join(repr(a) for a in ex.args))
        else:
            self.data_model.set_data(data, titles)

            sender_index: int
            for sender_index in range(min(len(self.line_options_y_axis), len(self.plot.lines))):
                self.plot.replot(
                    sender_index,
                    self.data_model,
                    self.line_options_y_axis[sender_index].option,
                    roll=True,
                )

        now: QtCore.QDateTime = QtCore.QDateTime.currentDateTime()
        self.status_bar.showMessage(
            self.tr("Reloaded {date} at {time}").format(
                date=self.locale().toString(now.date(), QtCore.QLocale.FormatType.NarrowFormat),
                time=self.locale().toString(now.time(), QtCore.QLocale.FormatType.NarrowFormat),
            )
        )
