from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import partial
from itertools import cycle
from typing import TypeVar, cast

import numpy as np
from numpy.typing import NDArray
from pyqtgraph import (
    CONFIG_OPTIONS,
    AxisItem,
    DateAxisItem,
    PlotDataItem,
    PlotItem,
    PlotWidget,
    SignalProxy,
    TextItem,
    ViewBox,
)
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent  # type: ignore
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.functions import mkBrush, mkPen

from ._data_model import DataModel
from ._double_click_spin_box import DoubleClickDateTimeEdit, DoubleClickDoubleSpinBox
from ._time_span_edit import TimeSpanEdit

__all__ = ["Plot"]

_T = TypeVar("_T")
_THE_BEGINNING_OF_TIME: datetime = datetime.fromtimestamp(0)


def normalize(a: NDArray[_T]) -> NDArray[_T]:
    min_a: _T = np.nanmin(a)
    max_a: _T = np.nanmax(a)
    return (a - min_a) / (max_a - min_a)


class Plot(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None, *args: object) -> None:
        super().__init__(parent, *args)

        self.setObjectName("plot_widget")

        self.setWindowTitle(self.tr("Plot"))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QtWidgets.QGridLayout = QtWidgets.QGridLayout(self)

        plot: PlotWidget = PlotWidget(self)
        self.lines: list[PlotDataItem] = []

        cursor_balloon: TextItem = TextItem()
        plot.addItem(cursor_balloon, True)  # ignore bounds

        self.canvas: PlotItem = plot.getPlotItem()
        self.canvas.setAxisItems({"bottom": DateAxisItem()})
        is_dark: bool = self.palette().color(QtGui.QPalette.ColorRole.Window).lightness() < 128

        def set_colors(background_color: str, foreground_color: str) -> None:
            ax: AxisItem
            _label: str
            plot.setBackground(mkBrush(background_color))
            for _label, ax_d in self.canvas.axes.items():
                ax = ax_d["item"]
                ax.setPen(foreground_color)
                ax.setTextPen(foreground_color)
            cursor_balloon.setColor(foreground_color)

        if is_dark:
            set_colors("k", "d")
        else:
            set_colors("w", "k")

        @QtCore.Slot()
        def on_view_all_triggered() -> None:
            if not self.lines:
                return
            all_data: list[NDArray[np.float64]] = [
                d for d in (d[~np.isnan(d)] for d in (line.xData for line in self.lines) if d is not None) if d.shape[0]
            ]
            if all_data:
                min_x: float = min(float(d[0]) for d in all_data)
                max_x: float = max(float(d[-1]) for d in all_data)
                self.canvas.vb.autoRange(padding=0.0)
                self.canvas.vb.setXRange(min_x, max_x, padding=0.0)

        @QtCore.Slot()
        def on_grid_menu_about_to_show() -> None:
            self.x_grid_opacity.blockSignals(True)
            self.x_grid_opacity.setValue(self.grid_x)
            self.x_grid_opacity.blockSignals(False)
            self.y_grid_opacity.blockSignals(True)
            self.y_grid_opacity.setValue(self.grid_y)
            self.y_grid_opacity.blockSignals(False)

        @QtCore.Slot(float)
        def on_x_grid_opacity_changed(opacity: float) -> None:
            self.grid_x = opacity

        @QtCore.Slot(float)
        def on_y_grid_opacity_changed(opacity: float) -> None:
            self.grid_y = opacity

        self.mouse_mode = ViewBox.RectMode

        for action in cast(QtWidgets.QMenu, self.canvas.vb.menu).actions():
            if action.menu() is None:
                continue
            if (
                len(cast(QtWidgets.QMenu, action.menu()).actions()) == 1
                and isinstance(cast(QtWidgets.QMenu, action.menu()).actions()[0], QtWidgets.QWidgetAction)
                and any(
                    child in (cl.gridLayout for cl in self.canvas.vb.menu.ctrl)
                    for child in cast(QtWidgets.QWidgetAction, cast(QtWidgets.QMenu, action.menu()).actions()[0])
                    .defaultWidget()
                    .children()
                )
            ):
                cast(QtWidgets.QMenu, self.canvas.vb.menu).removeAction(action)

        new_menu: QtWidgets.QMenu = QtWidgets.QMenu(QtCore.QCoreApplication.translate("PlotItem", "Grid"))
        new_wa: QtWidgets.QWidgetAction = QtWidgets.QWidgetAction(new_menu)
        new_w: QtWidgets.QWidget = QtWidgets.QWidget(new_menu)
        new_w_l: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        new_w.setLayout(new_w_l)
        self.x_grid_opacity: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, new_w)
        self.y_grid_opacity: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, new_w)
        self.x_grid_opacity.setRange(0, 255)
        self.y_grid_opacity.setRange(0, 255)
        self.x_grid_opacity.valueChanged.connect(on_x_grid_opacity_changed)
        self.y_grid_opacity.valueChanged.connect(on_y_grid_opacity_changed)
        new_w_l.addRow(QtCore.QCoreApplication.translate("PlotItem", "Show X Grid"), self.x_grid_opacity)
        new_w_l.addRow(QtCore.QCoreApplication.translate("PlotItem", "Show Y Grid"), self.y_grid_opacity)
        new_wa.setDefaultWidget(new_w)
        new_menu.addAction(new_wa)
        new_menu.aboutToShow.connect(on_grid_menu_about_to_show)
        self.canvas.vb.menu.addMenu(new_menu)
        self.canvas.ctrlMenu = None

        self.canvas.vb.disableAutoRange()
        self.canvas.vb.setAutoVisible(x=True, y=True)
        self.canvas.vb.setDefaultPadding(0.0)
        self.canvas.vb.menu.viewAll.triggered.connect(on_view_all_triggered)
        layout.addWidget(plot, 0, 1)

        x_range_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(x_range_layout, 1, 1)

        self.start_time: DoubleClickDateTimeEdit = DoubleClickDateTimeEdit(self)
        self.end_time: DoubleClickDateTimeEdit = DoubleClickDateTimeEdit(self)
        self.time_span: TimeSpanEdit = TimeSpanEdit(self)
        self.start_time.setDisabled(True)
        self.end_time.setDisabled(True)
        self.time_span.setDisabled(True)
        x_range_layout.addWidget(self.start_time, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        x_range_layout.addWidget(self.time_span, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        x_range_layout.addWidget(self.end_time, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        self.start_time.clearMinimumDateTime()
        self.start_time.clearMaximumDateTime()
        self.end_time.clearMinimumDateTime()
        self.end_time.clearMaximumDateTime()

        y_range_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        layout.addLayout(y_range_layout, 0, 0)

        self.start_y: DoubleClickDoubleSpinBox = DoubleClickDoubleSpinBox(self)
        self.end_y: DoubleClickDoubleSpinBox = DoubleClickDoubleSpinBox(self)
        self.y_span: DoubleClickDoubleSpinBox = DoubleClickDoubleSpinBox(self)
        self.start_y.setDisabled(True)
        self.end_y.setDisabled(True)
        self.y_span.setDisabled(True)
        self.start_y.setRange(0.0 if self.canvas.getAxis("left").logMode else -np.inf, np.inf)
        self.end_y.setRange(0.0 if self.canvas.getAxis("left").logMode else -np.inf, np.inf)
        self.y_span.setRange(10.0 ** -self.y_span.decimals(), np.inf)
        y_range_layout.addWidget(self.end_y, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        y_range_layout.addWidget(self.y_span, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        y_range_layout.addWidget(self.start_y, 0, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.start_y.clear()
        self.end_y.clear()
        self.y_span.clear()

        layout.setColumnStretch(0, 0)
        layout.setRowStretch(1, 0)

        def on_mouse_moved(event: tuple[QtCore.QPointF]) -> None:
            pos: QtCore.QPointF = event[0]
            if plot.sceneBoundingRect().contains(pos):
                point: QtCore.QPointF = self.canvas.vb.mapSceneToView(pos)
                if plot.visibleRange().contains(point):
                    cursor_balloon.setPos(point)
                    x: float = point.x()
                    y: float = point.y()
                    if self.canvas.axes["left"]["item"].logMode:
                        y = 10.0**y
                    x_str: str = self.locale().toString(
                        QtCore.QDateTime.fromMSecsSinceEpoch(round(x * 1000.0)),
                        QtCore.QLocale.FormatType.NarrowFormat,
                    )
                    y_str: str = self.locale().toString(y, "g", max(0, 6 - int(np.floor(np.log10(abs(y))))))
                    cursor_balloon.setText("\n".join((x_str, y_str)))
                    balloon_border: QtCore.QRectF = cursor_balloon.boundingRect()
                    sx: float
                    sy: float
                    sx, sy = self.canvas.vb.viewPixelSize()
                    balloon_width: float = balloon_border.width() * sx
                    balloon_height: float = balloon_border.height() * sy
                    anchor_x: float = 0.0 if point.x() - plot.visibleRange().left() < balloon_width else 1.0
                    anchor_y: float = 0.0 if plot.visibleRange().bottom() - point.y() < balloon_height else 1.0
                    cursor_balloon.setAnchor((anchor_x, anchor_y))
                    cursor_balloon.setVisible(True)
                else:
                    cursor_balloon.setVisible(False)
            else:
                cursor_balloon.setVisible(False)

        def on_view_range_changed(arg: tuple[PlotWidget, list[list[float]]]) -> None:
            view_range: list[list[float]] = arg[1]
            x_min: float
            x_max: float
            y_min: float
            y_max: float
            [[x_min, x_max], [y_min, y_max]] = view_range
            self.start_time.blockSignals(True)
            self.end_time.blockSignals(True)
            self.time_span.blockSignals(True)
            self.start_y.blockSignals(True)
            self.end_y.blockSignals(True)
            self.y_span.blockSignals(True)
            self.start_time.setDateTime(QtCore.QDateTime.fromMSecsSinceEpoch(round(x_min * 1000.0)))
            self.end_time.setDateTime(QtCore.QDateTime.fromMSecsSinceEpoch(round(x_max * 1000.0)))
            self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
            log_mode: bool = self.canvas.getAxis("left").logMode
            self.start_y.setRange(0.0 if log_mode else -np.inf, np.inf)
            self.end_y.setRange(0.0 if log_mode else -np.inf, np.inf)
            start: float = 10.0**y_min if log_mode else y_min
            end: float = 10.0**y_max if log_mode else y_max
            span: float = end - start
            decimals: int = max(
                2,
                2 - (int(np.floor(np.log10(abs(start)))) if start != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(end)))) if end != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(span)))) if span != 0.0 else 0),
            )
            self.start_y.setDecimals(decimals)
            self.end_y.setDecimals(decimals)
            self.y_span.setDecimals(decimals)
            self.start_y.setValue(start)
            self.end_y.setValue(end)
            self.y_span.setValue(span)
            self.start_y.setMaximum(end)
            self.end_y.setMinimum(start)
            self.y_span.blockSignals(False)
            self.end_y.blockSignals(False)
            self.start_y.blockSignals(False)
            self.time_span.blockSignals(False)
            self.end_time.blockSignals(False)
            self.start_time.blockSignals(False)

        def on_plot_left(event: QtCore.QEvent) -> None:
            self._mouse_moved_signal_proxy.flush()
            cursor_balloon.setVisible(False)
            event.accept()

        def on_mouse_clicked(event: MouseClickEvent) -> None:
            if event.double():
                self.auto_range_y(start=True, end=True)
            event.accept()

        self._mouse_moved_signal_proxy: SignalProxy = SignalProxy(
            plot.sceneObj.sigMouseMoved,
            rateLimit=10,
            slot=on_mouse_moved,
        )
        self._axis_range_changed_signal_proxy: SignalProxy = SignalProxy(
            plot.sigRangeChanged,
            rateLimit=10,
            slot=on_view_range_changed,
        )
        self._last_time_range_rolled: datetime = datetime.fromtimestamp(0)
        plot.leaveEvent = on_plot_left
        plot.sceneObj.sigMouseClicked.connect(on_mouse_clicked)

        @QtCore.Slot(QtCore.QDateTime)
        def on_start_time_changed(new_time: QtCore.QDateTime) -> None:
            self.time_span.blockSignals(True)
            self.time_span.from_two_q_date_time(new_time, self.end_time.dateTime())
            self.time_span.blockSignals(False)
            with self._axis_range_changed_signal_proxy.block():
                self.canvas.vb.setXRange(
                    self.start_time.dateTime().toMSecsSinceEpoch() / 1000.0,
                    self.end_time.dateTime().toMSecsSinceEpoch() / 1000.0,
                    padding=0.0,
                )

        @QtCore.Slot(QtCore.QDateTime)
        def on_end_time_changed(new_time: QtCore.QDateTime) -> None:
            self.start_time.blockSignals(True)
            if new_time.addMSecs(-round(self.time_span.total_seconds * 1000.0)) >= self.start_time.minimumDateTime():
                self.start_time.setDateTime(new_time.addMSecs(-round(self.time_span.total_seconds * 1000.0)))
            else:
                self.start_time.setDateTime(self.start_time.minimumDateTime())
                self.time_span.blockSignals(True)
                self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
                self.time_span.blockSignals(False)
            self.start_time.blockSignals(False)
            with self._axis_range_changed_signal_proxy.block():
                self.canvas.vb.setXRange(
                    self.start_time.dateTime().toMSecsSinceEpoch() / 1000.0,
                    self.end_time.dateTime().toMSecsSinceEpoch() / 1000.0,
                    padding=0.0,
                )

        @QtCore.Slot(timedelta)
        def on_time_span_changed(delta: timedelta) -> None:
            self.start_time.blockSignals(True)
            if (
                self.end_time.dateTime().addMSecs(-round(delta.total_seconds() * 1000.0))
                >= self.start_time.minimumDateTime()
            ):
                self.start_time.setDateTime(self.end_time.dateTime().addMSecs(-round(delta.total_seconds() * 1000.0)))
            else:
                self.start_time.setDateTime(self.start_time.minimumDateTime())
                self.time_span.blockSignals(True)
                self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
                self.time_span.blockSignals(False)
            self.start_time.blockSignals(False)
            with self._axis_range_changed_signal_proxy.block():
                self.canvas.vb.setXRange(
                    self.start_time.dateTime().toMSecsSinceEpoch() / 1000.0,
                    self.end_time.dateTime().toMSecsSinceEpoch() / 1000.0,
                    padding=0.0,
                )

        @QtCore.Slot(float)
        def on_start_y_changed(start: float) -> None:
            log_mode: bool = self.canvas.getAxis("left").logMode
            if log_mode and start <= 0.0:
                start = 10.0 ** self.canvas.vb.viewRange()[1][0]
                self.start_y.blockSignals(True)
                self.start_y.setValue(start)
                self.start_y.blockSignals(False)
                return

            end: float = self.end_y.value()
            span: float = end - start
            decimals: int = max(
                2,
                2 - (int(np.floor(np.log10(abs(start)))) if start != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(end)))) if end != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(span)))) if span != 0.0 else 0),
            )
            if span == 0.0:
                span = self.y_span.value()
                end = start + span
                decimals = max(
                    2,
                    2 - (int(np.floor(np.log10(abs(start)))) if start != 0.0 else 0),
                    2 - (int(np.floor(np.log10(abs(end)))) if end != 0.0 else 0),
                )
            if log_mode and end <= 0.0:
                end = self.end_y.value()
                span = end - start
            self.start_y.blockSignals(True)
            self.start_y.setDecimals(decimals)
            self.start_y.setValue(start)
            self.start_y.blockSignals(False)
            self.end_y.blockSignals(True)
            self.end_y.setDecimals(decimals)
            self.end_y.setValue(end)
            self.end_y.blockSignals(False)
            self.y_span.blockSignals(True)
            self.y_span.setValue(span)
            self.y_span.setDecimals(decimals)
            self.y_span.setMinimum(10.0**-decimals)
            self.y_span.blockSignals(False)
            self.end_y.setMinimum(start)
            with self._axis_range_changed_signal_proxy.block():
                if log_mode:
                    self.canvas.vb.setYRange(np.log10(start), np.log10(end), padding=0.0)
                else:
                    self.canvas.vb.setYRange(start, end, padding=0.0)

        @QtCore.Slot(float)
        def on_end_y_changed(end: float) -> None:
            log_mode: bool = self.canvas.getAxis("left").logMode
            if log_mode and end <= 0.0:
                end = 10.0 ** self.canvas.vb.viewRange()[1][1]
                self.end_y.blockSignals(True)
                self.end_y.setValue(end)
                self.end_y.blockSignals(False)
                return

            start: float = self.start_y.value()
            span: float = end - start
            decimals: int = max(
                2,
                2 - (int(np.floor(np.log10(abs(start)))) if start != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(end)))) if end != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(span)))) if span != 0.0 else 0),
            )
            if span == 0.0:
                span = self.y_span.value()
                start = end - span
                decimals = max(
                    2,
                    2 - (int(np.floor(np.log10(abs(start)))) if start != 0.0 else 0),
                    2 - (int(np.floor(np.log10(abs(end)))) if end != 0.0 else 0),
                )
            if log_mode and start <= 0.0:
                start = self.start_y.value()
                span = end - start
            self.start_y.blockSignals(True)
            self.start_y.setDecimals(decimals)
            self.start_y.setValue(start)
            self.start_y.blockSignals(False)
            self.end_y.blockSignals(True)
            self.end_y.setDecimals(decimals)
            self.end_y.setValue(end)
            self.end_y.blockSignals(False)
            self.y_span.blockSignals(True)
            self.y_span.setDecimals(decimals)
            self.y_span.setValue(span)
            self.y_span.setMinimum(10.0**-decimals)
            self.y_span.blockSignals(False)
            self.start_y.setMaximum(end)
            with self._axis_range_changed_signal_proxy.block():
                if log_mode:
                    self.canvas.vb.setYRange(np.log10(start), np.log10(end), padding=0.0)
                else:
                    self.canvas.vb.setYRange(start, end, padding=0.0)

        @QtCore.Slot(float)
        def on_y_span_changed(span: float) -> None:
            self.start_y.blockSignals(True)
            self.end_y.blockSignals(True)
            log_mode: bool = self.canvas.getAxis("left").logMode
            self.start_y.setRange(0.0 if log_mode else -np.inf, np.inf)
            self.end_y.setRange(0.0 if log_mode else -np.inf, np.inf)
            center: float = (self.start_y.value() + self.end_y.value()) / 2.0
            start: float = center - span / 2.0
            end: float = center + span / 2.0
            if log_mode:
                if start <= 0.0:
                    start = self.start_y.value()
                    span = end - start
                if end <= 0.0:
                    end = self.end_y.value()
                    span = end - start
            self.start_y.setValue(start)
            self.end_y.setValue(end)
            self.start_y.setMaximum(end)
            self.end_y.setMinimum(start)
            decimals: int = max(
                2,
                2 - (int(np.floor(np.log10(abs(start)))) if start != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(end)))) if end != 0.0 else 0),
                2 - (int(np.floor(np.log10(abs(span)))) if span != 0.0 else 0),
            )
            self.start_y.setDecimals(decimals)
            self.end_y.setDecimals(decimals)
            self.y_span.setDecimals(decimals)
            self.y_span.setMinimum(10.0**-decimals)
            self.end_y.blockSignals(False)
            self.start_y.blockSignals(False)
            with self._axis_range_changed_signal_proxy.block():
                if self.canvas.getAxis("left").logMode:
                    self.canvas.vb.setYRange(np.log10(start), np.log10(end), padding=0.0)
                else:
                    self.canvas.vb.setYRange(start, end, padding=0.0)

        self.start_time.dateTimeChanged.connect(on_start_time_changed)
        self.end_time.dateTimeChanged.connect(on_end_time_changed)
        self.time_span.timeSpanChanged.connect(on_time_span_changed)
        self.start_y.valueChanged.connect(on_start_y_changed)
        self.end_y.valueChanged.connect(on_end_y_changed)
        self.y_span.valueChanged.connect(on_y_span_changed)
        self.start_time.doubleClicked.connect(partial(self.auto_range_x, start=True, end=False))
        self.end_time.doubleClicked.connect(partial(self.auto_range_x, start=False, end=True))
        self.time_span.doubleClicked.connect(partial(self.auto_range_x, start=True, end=True))
        self.start_y.doubleClicked.connect(partial(self.auto_range_y, start=True, end=False))
        self.end_y.doubleClicked.connect(partial(self.auto_range_y, start=False, end=True))
        self.y_span.doubleClicked.connect(partial(self.auto_range_y, start=True, end=True))

        now: QtCore.QDateTime = QtCore.QDateTime.currentDateTime()
        self.canvas.vb.setXRange(
            now.toMSecsSinceEpoch() / 1000.0 - 1800.0,
            now.toMSecsSinceEpoch() / 1000.0 + 1800.0,
            padding=0.0,
        )

    def auto_range_x(self, start: bool = True, end: bool = True) -> None:
        if not self.lines:
            return
        line: PlotDataItem
        visible_data: list[NDArray[np.float64]] = []
        x_min: float
        x_max: float
        y_min: float
        y_max: float
        [[x_min, x_max], [y_min, y_max]] = self.canvas.vb.viewRange()
        for line in self.lines:
            if not line.isVisible():
                continue
            line_data_x: NDArray[np.float64] | None
            line_data_y: NDArray[np.float64] | None
            line_data_x, line_data_y = line.getData()
            if line_data_x is None or not line_data_x.size:
                continue
            visible_line_data_x: NDArray[np.float64] = line_data_x[(line_data_y >= y_min) & (line_data_y <= y_max)]
            if visible_line_data_x.size:
                visible_data.append(visible_line_data_x)
        if not visible_data:
            return
        min_x: float = x_min
        max_x: float = x_max
        if start:
            min_x = min(cast(float, np.nanmin(d)) for d in visible_data)
        if end:
            max_x = max(cast(float, np.nanmax(d)) for d in visible_data)
        self.canvas.vb.setXRange(min_x, max_x, padding=0.0)

    def auto_range_y(self, start: bool = True, end: bool = True) -> None:
        if not self.lines:
            return
        line: PlotDataItem
        visible_data: list[NDArray[np.float64]] = []
        x_min: float
        x_max: float
        y_min: float
        y_max: float
        [[x_min, x_max], [y_min, y_max]] = self.canvas.vb.viewRange()
        for line in self.lines:
            if not line.isVisible():
                continue
            line_data_x: NDArray[np.float64] | None
            line_data_y: NDArray[np.float64] | None
            line_data_x, line_data_y = line.getData()
            if line_data_y is None or not line_data_y.size:
                continue
            visible_line_data_y: NDArray[np.float64] = line_data_y[(line_data_x >= x_min) & (line_data_x <= x_max)]
            if visible_line_data_y.size:
                visible_data.append(visible_line_data_y)
        if not visible_data:
            return
        min_y: float = y_min
        max_y: float = y_max
        if start:
            min_y = min(cast(float, np.nanmin(d)) for d in visible_data)
        if end:
            max_y = max(cast(float, np.nanmax(d)) for d in visible_data)
        self.canvas.vb.setYRange(min_y, max_y, padding=0.0)

    def clear(self) -> None:
        self.canvas.clearPlots()

    def plot(
        self,
        data_model: DataModel,
        y_column_names: Iterable[str | None],
        *,
        normalized: bool = False,
        colors: Iterable[QtGui.QColor] = (),
        visibility: Iterable[bool] = (),
    ) -> None:
        if self.lines:
            self.clear()

        visibility = list(visibility)
        y_column_names = list(y_column_names)

        if len(visibility) < len(y_column_names):
            visibility += [True] * (len(y_column_names) - len(visibility))

        y_column_name: str | None
        color: QtGui.QColor
        visible: bool
        y_column_names = tuple(y_column_names)
        line: PlotDataItem
        if all(y_column_names):
            header: list[str] = data_model.header
            x_range: tuple[float, float] | None = None
            for y_column_name, color, visible in zip(
                y_column_names,
                cycle(colors or [CONFIG_OPTIONS["foreground"]]),
                visibility,
            ):
                y_column: int = header.index(cast(str, y_column_name))  # no Nones here
                x_column: int = y_column - 1
                while x_column >= 0:
                    if header[x_column].endswith(("(secs)", "(s)")):
                        break
                    x_column -= 1
                else:
                    continue

                x_data: NDArray[np.float64] = data_model[x_column]
                good: NDArray[np.int64] = np.argwhere(~np.isnan(x_data))

                if good.shape[0] > 1:
                    if x_range is None:
                        x_range = float(x_data[good[0]]), float(x_data[good[-1]])
                    else:
                        x_range = (
                            min(float(x_data[good[0]]), *x_range),
                            max(float(x_data[good[-1]]), *x_range),
                        )

                changing: NDArray[np.bool_] = (
                    np.concatenate(([True], np.diff(x_data) != 0.0))
                    if x_data.shape[0] > 1
                    else np.full_like(x_data, True, dtype=np.bool_)
                )

                line = self.canvas.plot(
                    x_data[changing],
                    normalize(data_model[y_column][changing]) if normalized else data_model[y_column][changing],
                    pen=color,
                    label=y_column_name,
                )
                line.curve.opts["pen"].setCosmetic(True)
                line.setVisible(visible)
                self.lines.append(line)
            if x_range is not None:
                self.canvas.vb.setXRange(x_range[0], x_range[-1], padding=0.0)
        else:
            for y_column_name, color, visible in zip(
                y_column_names, cycle(colors or [CONFIG_OPTIONS["foreground"]]), visibility
            ):
                line = self.canvas.plot(
                    [],
                    [],
                    pen=color,
                    label=y_column_name,
                )
                line.curve.opts["pen"].setCosmetic(True)
                line.setVisible(visible)
                self.lines.append(line)
        # restore log state if set
        log_mode_y: bool = self.canvas.getAxis("left").logMode
        if log_mode_y:
            for i in self.canvas.items:
                if hasattr(i, "setLogMode"):
                    i.setLogMode(False, log_mode_y)

        good_lines: list[PlotDataItem] = [
            line
            for line, visible in zip(self.lines, visibility)
            if (visible and line.yData is not None and line.yData.size and not np.all(np.isnan(line.yData)))
        ]
        if good_lines:
            data: list[NDArray[np.float64]] = [line.yData for line in good_lines]
            min_y: float
            max_y: float
            if self.canvas.axes["left"]["item"].logMode:
                positive_data: list[NDArray[np.float64]] = [d[d > 0] for d in data]
                min_y = np.log10(min(cast(float, np.nanmin(d)) for d in positive_data))
                max_y = np.log10(max(cast(float, np.nanmax(d)) for d in positive_data))
            else:
                min_y = min(cast(float, np.nanmin(d)) for d in data)
                max_y = max(cast(float, np.nanmax(d)) for d in data)
            self.canvas.vb.setYRange(min_y, max_y, padding=0.0)

        self.start_time.setEnabled(bool(good_lines))
        self.end_time.setEnabled(bool(good_lines))
        self.time_span.setEnabled(bool(good_lines))
        self.start_y.setEnabled(bool(good_lines))
        self.end_y.setEnabled(bool(good_lines))
        self.y_span.setEnabled(bool(good_lines))

    def replot(
        self,
        index: int,
        data_model: DataModel,
        y_column_name: str | None,
        *,
        normalized: bool = False,
        color: QtGui.QColor | QtGui.QPen | None = None,
        roll: bool = False,
    ) -> None:
        if y_column_name is None:
            return
        if index >= len(self.lines):
            return

        if color is None:
            color = self.lines[index].opts["pen"]
        if isinstance(color, QtGui.QPen):
            color.setCosmetic(True)
        else:
            color = mkPen(color, cosmetic=True)
        header: list[str] = data_model.header
        y_column: int = header.index(y_column_name)
        x_column: int = y_column - 1
        while x_column >= 0:
            if header[x_column].endswith(("(secs)", "(s)")):
                break
            x_column -= 1
        else:
            return

        if (
            roll
            and self.lines[index].xData is not None
            and self.lines[index].xData.size
            and datetime.now() - self._last_time_range_rolled >= timedelta(seconds=1)  # don't roll too often
        ):
            shift: float = data_model[x_column][-1] - self.lines[index].xData[-1]
            x_axis: AxisItem = self.canvas.getAxis("bottom")
            self.canvas.vb.setXRange(min(x_axis.range) + shift, max(x_axis.range) + shift, padding=0.0)
            self._last_time_range_rolled = datetime.now()

        x_data: NDArray[np.float64] = data_model[x_column]
        changing: NDArray[np.bool_] = (
            np.concatenate(([True], np.diff(x_data) != 0.0))
            if x_data.shape[0] > 1
            else np.full_like(x_data, True, dtype=np.bool_)
        )

        self.lines[index].setData(
            x_data[changing],
            normalize(data_model[y_column][changing]) if normalized else data_model[y_column][changing],
            pen=color,
            label=y_column_name,
        )

        self.canvas.scene().update()

    def set_line_visible(self, index: int, visible: bool) -> None:
        self.lines[index].setVisible(visible)

    @property
    def view_range(self) -> list[list[float]]:
        return self.canvas.vb.viewRange()

    @property
    def mouse_mode(self) -> int:
        return self.canvas.vb.state["mouseMode"]

    @mouse_mode.setter
    def mouse_mode(self, new_value: int) -> None:
        if new_value not in (ViewBox.RectMode, ViewBox.PanMode):
            raise ValueError("Invalid mouse mode")
        self.canvas.vb.setMouseMode(new_value)

    @property
    def grid_x(self) -> int:
        return int(cast(AxisItem, self.canvas.getAxis("bottom")).grid)

    @grid_x.setter
    def grid_x(self, grid_x: int) -> None:
        if not (0 <= grid_x < 256):
            raise ValueError("Invalid grid opacity")
        cast(AxisItem, self.canvas.getAxis("bottom")).setGrid((grid_x > 0) and grid_x)
        # print(self.canvas.ctrlMenu.children())

    @property
    def grid_y(self) -> int:
        return int(cast(AxisItem, self.canvas.getAxis("left")).grid)

    @grid_y.setter
    def grid_y(self, grid_y: int) -> None:
        if not (0 <= grid_y < 256):
            raise ValueError("Invalid grid opacity")
        cast(AxisItem, self.canvas.getAxis("left")).setGrid((grid_y > 0) and grid_y)
