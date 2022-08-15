# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Final, Iterable, Optional, Sequence, TextIO, cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from numpy.typing import NDArray
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from gui._data_model import DataModel
from gui._plot import Plot
from gui._plot_line_options import PlotLineOptions
from gui._preferences import Preferences
from gui._settings import Settings
from log_parser import parse

PLOT_LINES_COUNT: Final[int] = 8


class MainWindow(QtWidgets.QMainWindow):
    _initial_window_title: Final[str] = QtWidgets.QApplication.translate('initial main window title',
                                                                         'VeriCold Plotter')

    def __init__(self, application: Optional[QtWidgets.QApplication] = None,
                 parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

        self.settings: Settings = Settings('SavSoft', 'VeriCold Plotter', self)
        self.application: Optional[QtWidgets.QApplication] = application
        self.install_translation()

        self.central_widget: QtWidgets.QWidget = QtWidgets.QWidget(self)
        self.main_layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self.central_widget)

        self.dock_settings: QtWidgets.QDockWidget = QtWidgets.QDockWidget(self)
        self.box_settings: QtWidgets.QWidget = QtWidgets.QWidget(self.dock_settings)
        self.settings_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self.box_settings)
        self.layout_x_axis: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        self.combo_x_axis: pg.ComboBox = pg.ComboBox(self.box_settings)
        self.combo_y_axis: pg.ComboBox = pg.ComboBox(self.box_settings)
        self.line_options_y_axis: list[PlotLineOptions] = [PlotLineOptions(items=[],
                                                                           settings=self.settings,
                                                                           parent=self.dock_settings)
                                                           for _ in range(PLOT_LINES_COUNT)]

        self.data_model: DataModel = DataModel()
        self.plot: Plot = Plot(self)

        self.export_all: bool = True
        self.menu_bar: QtWidgets.QMenuBar = QtWidgets.QMenuBar(self)
        self.menu_file: QtWidgets.QMenu = QtWidgets.QMenu(self.menu_bar)
        self.menu_about: QtWidgets.QMenu = QtWidgets.QMenu(self.menu_bar)
        self.action_open: QtGui.QAction = QtGui.QAction(self)
        self.action_export: QtGui.QAction = QtGui.QAction(self)
        self.action_export_visible: QtGui.QAction = QtGui.QAction(self)
        self.action_reload: QtGui.QAction = QtGui.QAction(self)
        self.action_auto_reload: QtGui.QAction = QtGui.QAction(self)
        self.action_preferences: QtGui.QAction = QtGui.QAction(self)
        self.action_quit: QtGui.QAction = QtGui.QAction(self)
        self.action_about: QtGui.QAction = QtGui.QAction(self)
        self.action_about_qt: QtGui.QAction = QtGui.QAction(self)

        self.status_bar: QtWidgets.QStatusBar = QtWidgets.QStatusBar(self)

        self._opened_file_name: str = ''
        self._exported_file_name: str = ''

        self.reload_timer: QtCore.QTimer = QtCore.QTimer(self)
        self.file_created: float = 0.0

        self.setup_ui()

    def setup_ui(self) -> None:
        # https://ru.stackoverflow.com/a/1032610
        window_icon: QtGui.QPixmap = QtGui.QPixmap()
        # noinspection PyTypeChecker
        window_icon.loadFromData(b'''\
                    <svg version="1.1" viewBox="0 0 135 135" xmlns="http://www.w3.org/2000/svg">\
                    <path d="m0 0h135v135h-135v-135" fill="#282e70"/>\
                    <path d="m23 51c3.4-8.7 9.4-16 17-22s17-8.2 26-8.2c9.3 0 19 2.9 26 8.2 7.7 5.3 14 13 17 22 4.1 11 \
                    4.1 23 0 33-3.4 8.7-9.4 16-17 22-7.7 5.3-17 8.2-26 8.2-9.3 0-19-2.9-26-8.2s-14-13-17-22" \
                    fill="none" stroke="#fff" stroke-linecap="round" stroke-width="19"/>\
                    <path d="m50 31c-.58-1.1 6.3-7.5 21-7.8 6.5-.15 14 1.3 22 5.7 6.3 3.6 12 9.1 16 16 3.8 6.6 6 14 \
                    6.1 23v4e-6c-.003 8.2-2.3 16-6.1 23-4.2 7.3-10 13-16 16-7.7 4.4-16 5.8-22 \
                    5.7l-5e-6-1e-5c-14-.33-21-6.7-21-7.8.58-1.1 8.3 2.5 20 1.2 0-1e-5 4e-6-1e-5 \
                    4e-6-1e-5 5.5-.62 12-2.5 18-6.5 4.9-3.2 9.4-7.9 13-14 2.8-5.2 4.5-11 \
                    4.5-18v-2e-6c.003-6.4-1.7-13-4.5-18-3.1-5.8-7.7-11-13-14-5.9-4-12-5.8-18-6.5-12-1.4-20 \
                    2.3-20 1.2z" fill="#282e70"/></svg>\
                    ''', 'SVG')
        self.setWindowIcon(QtGui.QIcon(window_icon))

        self.setObjectName('main_window')
        self.resize(640, 480)
        self.central_widget.setObjectName('central_widget')
        self.main_layout.setObjectName('main_layout')
        self.main_layout.addWidget(self.plot)
        self.setCentralWidget(self.central_widget)
        self.menu_bar.setGeometry(QtCore.QRect(0, 0, 800, 29))
        self.menu_bar.setObjectName('menu_bar')
        self.menu_file.setObjectName('menu_file')
        self.menu_about.setObjectName('menu_about')
        self.setMenuBar(self.menu_bar)
        self.status_bar.setObjectName('status_bar')
        self.setStatusBar(self.status_bar)
        self.action_open.setIcon(
            QtGui.QIcon.fromTheme('document-open',
                                  self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton)))
        self.action_open.setObjectName('action_open')
        self.action_export.setIcon(QtGui.QIcon.fromTheme('document-save-as'))
        self.action_export.setObjectName('action_export')
        self.action_export_visible.setIcon(QtGui.QIcon.fromTheme('document-save-as'))
        self.action_export_visible.setObjectName('action_export_visible')
        self.action_reload.setIcon(
            QtGui.QIcon.fromTheme('view-refresh',
                                  self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload)))
        self.action_reload.setObjectName('action_reload')
        self.action_auto_reload.setObjectName('action_auto_reload')
        self.action_preferences.setMenuRole(QtGui.QAction.MenuRole.PreferencesRole)
        self.action_preferences.setObjectName('action_preferences')
        self.action_quit.setIcon(
            QtGui.QIcon.fromTheme('application-exit',
                                  self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton)))
        self.action_quit.setMenuRole(QtGui.QAction.MenuRole.QuitRole)
        self.action_quit.setObjectName('action_quit')
        self.action_about.setIcon(
            QtGui.QIcon.fromTheme('help-about',
                                  self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogHelpButton)))
        self.action_about.setMenuRole(QtGui.QAction.MenuRole.AboutRole)
        self.action_about.setObjectName('action_about')
        self.action_about_qt.setIcon(
            QtGui.QIcon.fromTheme('help-about-qt',
                                  QtGui.QIcon(':/qt-project.org/q''messagebox/images/qt''logo-64.png')))
        self.action_about_qt.setMenuRole(QtGui.QAction.MenuRole.AboutQtRole)
        self.action_about_qt.setObjectName('action_about_qt')
        self.menu_file.addAction(self.action_open)
        self.menu_file.addAction(self.action_export)
        self.menu_file.addAction(self.action_export_visible)
        self.menu_file.addAction(self.action_reload)
        self.menu_file.addAction(self.action_auto_reload)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_preferences)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_quit)
        self.menu_about.addAction(self.action_about)
        self.menu_about.addAction(self.action_about_qt)
        self.menu_bar.addAction(self.menu_file.menuAction())
        self.menu_bar.addAction(self.menu_about.menuAction())

        self.action_export.setEnabled(False)
        self.action_export_visible.setEnabled(False)
        self.action_reload.setEnabled(False)
        self.action_auto_reload.setEnabled(False)
        self.action_auto_reload.setCheckable(True)

        self.action_open.setShortcut(QtGui.QKeySequence('Ctrl+O'))
        self.action_export.setShortcuts((QtGui.QKeySequence('Ctrl+S'), QtGui.QKeySequence('Ctrl+E')))
        self.action_export_visible.setShortcuts((QtGui.QKeySequence('Shift+Ctrl+S'),
                                                 QtGui.QKeySequence('Shift+Ctrl+E')))
        self.action_reload.setShortcuts((QtGui.QKeySequence('Ctrl+R'), QtGui.QKeySequence('F5')))
        self.action_preferences.setShortcut(QtGui.QKeySequence('Ctrl+,'))
        self.action_quit.setShortcuts((QtGui.QKeySequence('Ctrl+Q'), QtGui.QKeySequence('Ctrl+X')))
        self.action_about.setShortcut(QtGui.QKeySequence('F1'))

        self.action_open.triggered.connect(self.on_action_open_triggered)
        self.action_export.triggered.connect(self.on_action_export_triggered)
        self.action_export_visible.triggered.connect(self.on_action_export_visible_triggered)
        self.action_reload.triggered.connect(self.on_action_reload_triggered)
        self.action_auto_reload.toggled.connect(self.on_action_auto_reload_toggled)
        self.action_preferences.triggered.connect(self.on_action_preferences_triggered)
        self.action_quit.triggered.connect(self.on_action_quit_triggered)
        self.action_about.triggered.connect(self.on_action_about_triggered)
        self.action_about_qt.triggered.connect(self.on_action_about_qt_triggered)

        self.dock_settings.setObjectName('dock_settings')
        self.dock_settings.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
        self.dock_settings.setFeatures(cast(QtWidgets.QDockWidget.DockWidgetFeature,
                                            self.dock_settings.features()
                                            & ~self.dock_settings.DockWidgetFeature.DockWidgetClosable))
        self.dock_settings.setWidget(self.box_settings)
        self.layout_x_axis.addRow(self.tr('x-axis:'), self.combo_x_axis)
        self.layout_x_axis.addRow(self.tr('y-axis:'), self.combo_y_axis)
        self.settings_layout.addLayout(self.layout_x_axis)
        cb: PlotLineOptions
        for cb in self.line_options_y_axis:
            self.settings_layout.addWidget(cb)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.dock_settings)

        self.setWindowTitle(self._initial_window_title)
        self.menu_file.setTitle(self.tr('File'))
        self.menu_about.setTitle(self.tr('About'))
        self.action_open.setText(self.tr('Open...'))
        self.action_export.setText(self.tr('Export...'))
        self.action_export_visible.setText(self.tr('Export Visible...'))
        self.action_reload.setText(self.tr('Reload'))
        self.action_auto_reload.setText(self.tr('Auto Reload'))
        self.action_preferences.setText(self.tr('Preferences...'))
        self.action_quit.setText(self.tr('Quit'))
        self.action_about.setText(self.tr('About'))
        self.action_about_qt.setText(self.tr('About QtCore.Qt'))
        self.dock_settings.setWindowTitle(self.tr('Options'))

        self.load_settings()

        self.combo_x_axis.currentTextChanged.connect(self.on_x_axis_changed)
        self.combo_y_axis.setItems((self.tr('absolute'), self.tr('relative'), self.tr('logarithmic')))
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
        self.settings.beginGroup('location')
        self._opened_file_name = cast(str, self.settings.value('open', str(Path.cwd()), str))
        self._exported_file_name = cast(str, self.settings.value('export', str(Path.cwd()), str))
        self.settings.endGroup()

        self.settings.beginGroup('window')
        # Fallback: Center the window
        desktop: QtGui.QScreen = QtWidgets.QApplication.screens()[0]
        window_frame: QtCore.QRect = self.frameGeometry()
        desktop_center: QtCore.QPoint = desktop.availableGeometry().center()
        window_frame.moveCenter(desktop_center)
        self.move(window_frame.topLeft())

        # noinspection PyTypeChecker
        self.restoreGeometry(cast(QtCore.QByteArray, self.settings.value('geometry', QtCore.QByteArray())))
        # noinspection PyTypeChecker
        self.restoreState(cast(QtCore.QByteArray, self.settings.value('state', QtCore.QByteArray())))
        self.settings.endGroup()

    def save_settings(self) -> None:
        self.settings.beginGroup('location')
        self.settings.setValue('open', self._opened_file_name)
        self.settings.setValue('export', self._exported_file_name)
        self.settings.endGroup()

        self.settings.beginGroup('window')
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('state', self.saveState())
        self.settings.endGroup()
        self.settings.sync()

    def install_translation(self) -> None:
        if self.application is not None and self.settings.translation_path is not None:
            translator: QtCore.QTranslator = QtCore.QTranslator(self)
            translator.load(str(self.settings.translation_path))
            self.application.installTranslator(translator)

    def load_file(self, file_name: str | Iterable[str],
                  check_file_updates: bool = False) -> bool:
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
                    self.status_bar.showMessage(' '.join(repr(a) for a in ex.args))
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
            data = np.column_stack(all_data[i + 1:])
        else:
            try:
                titles, data = parse(file_name)
            except (IOError, RuntimeError) as ex:
                self.status_bar.showMessage(' '.join(repr(a) for a in ex.args))
                return False
        self._opened_file_name = file_name
        self.data_model.set_data(data, titles)

        self.combo_x_axis.blockSignals(True)
        self.combo_x_axis.setItems(tuple(filter(lambda t: t.endswith('(secs)') or t.endswith('(s)'),
                                                self.data_model.header)))
        self.combo_x_axis.setCurrentText(self.settings.argument)
        self.combo_x_axis.blockSignals(False)

        cb: PlotLineOptions
        for cb in self.line_options_y_axis:
            cb.set_items(tuple(filter(lambda t: not (t.endswith('(secs)') or t.endswith('(s)')),
                                      self.data_model.header)))
        self.plot.plot(self.data_model,
                       self.combo_x_axis.value(),
                       (cb.option for cb in self.line_options_y_axis),
                       colors=(cb.color for cb in self.line_options_y_axis),
                       visibility=(cb.checked for cb in self.line_options_y_axis))
        self.action_export.setEnabled(True)
        self.action_export_visible.setEnabled(True)
        self.action_reload.setEnabled(True)
        self.action_auto_reload.setEnabled(True)
        self.status_bar.showMessage(self.tr('Ready'))
        self.file_created = Path(self._opened_file_name).lstat().st_mtime
        self.check_file_updates = check_file_updates
        self.setWindowTitle(f'{file_name} — {self._initial_window_title}')
        return True

    def visible_data(self) -> tuple[NDArray[np.float64], list[str]]:
        o: PlotLineOptions
        header = [self.data_model.header[0]] + [o.option for o in self.line_options_y_axis]
        h: str
        data = self.data_model.data[[self.data_model.header.index(h) for h in header]]

        # crop the visible rectangle
        x_min: float
        x_max: float
        y_min: float
        y_max: float
        ((x_min, x_max), (y_min, y_max)) = self.plot.view_range
        data = data[..., ((data[0] >= x_min) & (data[0] <= x_max))]
        d: NDArray[np.float64]
        somehow_visible_lines: list[bool] = [True] + [bool(np.any((d >= y_min) & (d <= y_max))) for d in data[1:]]
        data = data[somehow_visible_lines]
        b: bool
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
            with open(filename, 'wt', newline='') as f_out:
                f_out.write(self.settings.csv_separator.join(header) + self.settings.line_end)
                f_out.writelines(((self.settings.csv_separator.join(f'{xii}' for xii in xi)
                                   if isinstance(xi, Iterable)
                                   else f'{xi}'
                                   ) + self.settings.line_end)
                                 for xi in data.T)
        except IOError as ex:
            self.status_bar.showMessage(' '.join(ex.args))
            return False
        else:
            self._exported_file_name = filename
            self.status_bar.showMessage(self.tr('Saved to {0}').format(filename))
            return True

    def save_xlsx(self, filename: str) -> bool:
        try:
            import xlsxwriter  # type: ignore
            from xlsxwriter import Workbook
            from xlsxwriter.format import Format  # type: ignore
            from xlsxwriter.worksheet import Worksheet  # type: ignore
        except ImportError as ex:
            self.status_bar.showMessage(' '.join(repr(a) for a in ex.args))
            return False

        data: NDArray[np.float64] = self.data_model.data
        header: list[str]
        if self.export_all:
            header = self.data_model.header
        else:
            data, header = self.visible_data()
        try:
            workbook: Workbook = Workbook(filename,
                                          {'default_date_format': 'dd.mm.yyyy hh:mm:ss',
                                           'nan_inf_to_errors': True})
            header_format: Format = workbook.add_format({'bold': True})
            worksheet: Worksheet = workbook.add_worksheet(str(Path(self._opened_file_name).with_suffix('').name))
            worksheet.freeze_panes(1, 0)  # freeze first row
            col: int
            row: int
            for col in range(data.shape[0]):
                worksheet.write_string(0, col, header[col], header_format)
                if header[col].endswith(('(s)', '(secs)')):
                    for row in range(data.shape[1]):
                        worksheet.write_datetime(row + 1, col, datetime.fromtimestamp(data[col, row]))
                else:
                    for row in range(data.shape[1]):
                        worksheet.write_number(row + 1, col, data[col, row])
            workbook.close()
        except IOError as ex:
            self.status_bar.showMessage(' '.join(ex.args))
            return False
        else:
            self._exported_file_name = filename
            self.status_bar.showMessage(self.tr('Saved to {0}').format(filename))
            return True

    @property
    def check_file_updates(self) -> bool:
        return self.reload_timer.isActive()

    @check_file_updates.setter
    def check_file_updates(self, new_value: bool) -> None:
        self.action_auto_reload.setChecked(new_value)

    def on_action_open_triggered(self) -> None:
        new_file_name: str
        new_file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, self.tr('Open'),
            self._opened_file_name,
            f'{self.tr("VeriCold data logfile")} (*.vcl);;{self.tr("All Files")} (*.*)')
        self.load_file(new_file_name)

    def export(self) -> None:
        supported_formats: dict[str, str] = {'.csv': f'{self.tr("Text with separators")} (*.csv)'}
        supported_formats_callbacks: dict[str, Callable[[str], bool]] = {'.csv': self.save_csv}
        try:
            import xlsxwriter
        except ImportError:
            pass
        else:
            supported_formats['.xlsx'] = f'{self.tr("Microsoft Excel")} (*.xlsx)'
            supported_formats_callbacks['.xlsx'] = self.save_xlsx
        selected_filter: str = ''
        if self._exported_file_name:
            exported_file_name_ext: str = Path(self._exported_file_name).suffix
            if exported_file_name_ext in supported_formats:
                selected_filter = supported_formats[exported_file_name_ext]
        new_file_name: str
        new_file_name_filter: str  # BUG: it's empty when a native dialog is used
        # noinspection PyTypeChecker
        new_file_name, new_file_name_filter = QtWidgets.QFileDialog.getSaveFileName(
            self, self.tr('Export'),
            str(Path(self._exported_file_name or self._opened_file_name)
                .with_name(Path(self._opened_file_name).name)),
            ';;'.join(supported_formats.values()),
            selected_filter,
        )
        if not new_file_name:
            return
        new_file_name_ext: str = Path(new_file_name).suffix
        if new_file_name_ext in supported_formats_callbacks:
            supported_formats_callbacks[new_file_name_ext](new_file_name)

    def on_action_export_triggered(self) -> None:
        self.export_all = True
        self.export()

    def on_action_export_visible_triggered(self) -> None:
        self.export_all = False
        self.export()

    def on_action_reload_triggered(self) -> None:
        self.load_file(self._opened_file_name)

    def on_action_auto_reload_toggled(self, new_state: bool) -> None:
        if new_state:
            self.reload_timer.start()
        else:
            self.reload_timer.stop()

    def on_action_preferences_triggered(self) -> None:
        preferences_dialog: Preferences = Preferences(self.settings, self)
        preferences_dialog.exec()
        self.install_translation()

    def on_action_quit_triggered(self) -> None:
        self.close()

    def on_action_about_triggered(self) -> None:
        QtWidgets.QMessageBox.about(self,
                                    self.tr("About VeriCold Log Plotter"),
                                    "<html><p>"
                                    + self.tr("VeriCold logfiles are created by Oxford Instruments plc.")
                                    + "</p><br><p>"
                                    + self.tr("VeriCold Log Plotter is licensed under the {0}.")
                                    .format("<a href='https://www.gnu.org/copyleft/lesser.html'>{0}</a>"
                                            .format(self.tr("GNU LGPL version 3")))
                                    + "</p><p>"
                                    + self.tr("The source code is available on {0}.").format(
                                        "<a href='https://github.com/StSav012/VeriCold_Log_Plotter'>GitHub</a>")
                                    + "</p></html>")

    def on_action_about_qt_triggered(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self)

    def on_x_axis_changed(self, new_text: str) -> None:
        normalized: bool = (self.combo_y_axis.currentIndex() == 1)
        sender_index: int
        for sender_index in range(min(len(self.line_options_y_axis), len(self.plot.lines))):
            self.plot.replot(sender_index, self.data_model,
                             new_text, self.line_options_y_axis[sender_index].option,
                             normalized=normalized)
        self.settings.argument = new_text

    def on_y_axis_changed(self, sender_index: int, title: str) -> None:
        normalized: bool = (self.combo_y_axis.currentIndex() == 1)
        self.plot.replot(sender_index, self.data_model, self.combo_x_axis.currentText(), title,
                         color=self.settings.line_colors.get(title, PlotLineOptions.DEFAULT_COLOR),
                         normalized=normalized)

    def on_y_axis_mode_changed(self, new_index: int) -> None:
        # PlotItem.setLogMode causes a crash here sometimes; the reason is unknown
        log_mode_y: bool = (new_index == 2)
        if self.plot.canvas.getAxis('left').logMode != log_mode_y:
            for i in self.plot.canvas.items:
                if hasattr(i, 'setLogMode'):
                    i.setLogMode(False, log_mode_y)
            self.plot.canvas.getAxis('left').setLogMode(log_mode_y)
            self.plot.canvas.enableAutoRange()
            self.plot.canvas.recomputeAverages()

        sender_index: int
        for sender_index in range(len(self.line_options_y_axis)):
            self.plot.replot(sender_index, self.data_model,
                             self.combo_x_axis.currentText(),
                             self.line_options_y_axis[sender_index].option,
                             normalized=(new_index == 1))
        self.plot.auto_range_y()

    def on_color_changed(self, sender_index: int, new_color: QtGui.QColor) -> None:
        normalized: bool = (self.combo_y_axis.currentIndex() == 1)
        self.plot.replot(sender_index, self.data_model,
                         self.combo_x_axis.currentText(), self.line_options_y_axis[sender_index].option,
                         color=new_color,
                         normalized=normalized)

    def on_line_toggled(self, sender_index: int, new_state: bool) -> None:
        self.plot.set_line_visible(sender_index, new_state)

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
            self.status_bar.showMessage(' '.join(repr(a) for a in ex.args))
        else:
            self.data_model.set_data(data, titles)

            sender_index: int
            for sender_index in range(min(len(self.line_options_y_axis), len(self.plot.lines))):
                self.plot.replot(sender_index, self.data_model,
                                 self.combo_x_axis.currentText(), self.line_options_y_axis[sender_index].option,
                                 roll=True)

            self.status_bar.showMessage(self.tr('Reloaded {0}')
                                        .format(datetime.now().isoformat(sep=' ', timespec='seconds')))
