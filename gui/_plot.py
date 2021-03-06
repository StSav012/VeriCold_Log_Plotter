# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from itertools import cycle
from typing import Any, Iterable, Optional, cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from numpy.typing import NDArray
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent  # type: ignore
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

__all__ = ['Plot']

from gui._data_model import DataModel
from gui._time_span_edit import TimeSpanEdit


class Plot(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, *args: Any) -> None:
        super().__init__(parent, *args)

        self.setObjectName('plot_widget')

        self.setWindowTitle(self.tr('Plot'))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)

        plot: pg.PlotWidget = pg.PlotWidget(self)
        self.lines: list[pg.PlotDataItem] = []

        cursor_balloon: pg.TextItem = pg.TextItem()
        plot.addItem(cursor_balloon, True)  # ignore bounds

        self.canvas: pg.PlotItem = plot.getPlotItem()
        self.canvas.setAxisItems({'bottom': pg.DateAxisItem()})
        is_dark: bool = self.palette().color(QtGui.QPalette.ColorRole.Window).lightness() < 128

        def set_colors(background_color: str, foreground_color: str) -> None:
            ax: pg.AxisItem
            label: str
            plot.setBackground(pg.mkBrush(background_color))
            for label, ax_d in self.canvas.axes.items():
                ax = ax_d['item']
                ax.setPen(foreground_color)
                ax.setTextPen(foreground_color)
            cursor_balloon.setColor(foreground_color)

        if is_dark:
            set_colors('k', 'd')
        else:
            set_colors('w', 'k')

        def auto_range_y() -> None:
            if not self.lines:
                return
            line: pg.PlotDataItem
            visible_data: list[NDArray[np.float64]] = []
            x_min: float
            x_max: float
            y_min: float
            y_max: float
            [[x_min, x_max], [y_min, y_max]] = self.canvas.vb.viewRange()
            for line in self.lines:
                if line.yData is None or not line.yData.size:
                    continue
                visible_data_piece: NDArray[np.float64] = line.yData[(line.xData >= x_min) & (line.xData <= x_max)]
                if np.any((visible_data_piece >= y_min) & (visible_data_piece <= y_max)):
                    visible_data.append(visible_data_piece)
            if not visible_data:
                return
            min_y: float = min(np.nanmin(d) for d in visible_data)
            max_y: float = max(np.nanmax(d) for d in visible_data)
            self.canvas.vb.setYRange(min_y, max_y, padding=0.0)

        def on_view_all_triggered() -> None:
            if not self.lines:
                return
            line: pg.PlotDataItem
            min_x: float = min(line.xData[0] for line in self.lines if line.xData is not None and line.xData.size)
            max_x: float = min(line.xData[-1] for line in self.lines if line.xData is not None and line.xData.size)
            self.canvas.vb.autoRange(padding=0.0)
            self.canvas.vb.setXRange(min_x, max_x, padding=0.0)

        self.canvas.autoBtn.clicked.disconnect(self.canvas.autoBtnClicked)
        self.canvas.autoBtn.clicked.connect(auto_range_y)

        menu_action: QtGui.QAction
        for menu_action in self.canvas.ctrlMenu.actions():
            if menu_action.text() in [
                QtCore.QCoreApplication.translate('PlotItem', 'Grid'),
            ]:
                self.canvas.vb.menu.addAction(menu_action)
            else:
                menu_action.deleteLater()
        self.canvas.ctrlMenu = None

        self.canvas.vb.disableAutoRange()
        self.canvas.vb.setAutoVisible(x=True, y=True)
        self.canvas.vb.setMouseMode(pg.ViewBox.RectMode)
        self.canvas.vb.setDefaultPadding(0.0)
        self.canvas.vb.menu.axes[0].deleteLater()
        self.canvas.vb.menu.ctrl[1].invertCheck.hide()
        self.canvas.vb.menu.ctrl[1].label.hide()
        self.canvas.vb.menu.ctrl[1].linkCombo.hide()
        self.canvas.vb.menu.ctrl[1].mouseCheck.hide()
        self.canvas.vb.menu.viewAll.triggered.connect(on_view_all_triggered)
        layout.addWidget(plot)

        x_range_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        layout.addLayout(x_range_layout)
        layout.setStretch(1, 0)

        self.start_time: QtWidgets.QDateTimeEdit = QtWidgets.QDateTimeEdit(self)
        self.end_time: QtWidgets.QDateTimeEdit = QtWidgets.QDateTimeEdit(self)
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

        def on_mouse_moved(event: tuple[QtCore.QPointF]) -> None:
            pos: QtCore.QPointF = event[0]
            if plot.sceneBoundingRect().contains(pos):
                point: QtCore.QPointF = self.canvas.vb.mapSceneToView(pos)
                if plot.visibleRange().contains(point):
                    cursor_balloon.setPos(point)
                    cursor_balloon.setText(f'{datetime.fromtimestamp(round(point.x()))}\n{point.y()}')
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

        def on_lim_changed(arg: tuple[pg.PlotWidget, list[list[float]]]) -> None:
            rect: list[list[float]] = arg[1]
            x_lim: list[float]
            y_lim: list[float]
            x_lim, y_lim = rect
            self.start_time.blockSignals(True)
            self.end_time.blockSignals(True)
            self.time_span.blockSignals(True)
            self.start_time.setDateTime(QtCore.QDateTime.fromMSecsSinceEpoch(round(min(x_lim) * 1000)))
            self.end_time.setDateTime(QtCore.QDateTime.fromMSecsSinceEpoch(round(max(x_lim) * 1000)))
            self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
            self.time_span.blockSignals(False)
            self.end_time.blockSignals(False)
            self.start_time.blockSignals(False)

        def on_plot_left(event: QtCore.QEvent) -> None:
            self._mouse_moved_signal_proxy.flush()
            cursor_balloon.setVisible(False)
            event.accept()

        def on_mouse_clicked(event: MouseClickEvent) -> None:
            if event.double():
                auto_range_y()
            event.accept()

        self._mouse_moved_signal_proxy: pg.SignalProxy = pg.SignalProxy(plot.scene().sigMouseMoved,
                                                                        rateLimit=10, slot=on_mouse_moved)
        self._axis_range_changed_signal_proxy: pg.SignalProxy = pg.SignalProxy(plot.sigRangeChanged,
                                                                               rateLimit=10, slot=on_lim_changed)
        self._last_time_range_rolled: datetime = datetime.fromtimestamp(0)
        plot.leaveEvent = on_plot_left
        plot.scene().sigMouseClicked.connect(on_mouse_clicked)

        def on_start_time_changed(new_time: QtCore.QDateTime) -> None:
            self.time_span.blockSignals(True)
            self.time_span.from_two_q_date_time(new_time, self.end_time.dateTime())
            self.time_span.blockSignals(False)
            self.canvas.vb.setXRange(self.start_time.dateTime().toPython().timestamp(),
                                     self.end_time.dateTime().toPython().timestamp(),
                                     padding=0.0)

        def on_end_time_changed(new_time: QtCore.QDateTime) -> None:
            self.start_time.blockSignals(True)
            if new_time.addMSecs(-round(self.time_span.total_seconds * 1000)) >= self.start_time.minimumDateTime():
                self.start_time.setDateTime(new_time.addMSecs(-round(self.time_span.total_seconds * 1000)))
            else:
                self.start_time.setDateTime(self.start_time.minimumDateTime())
                self.time_span.blockSignals(True)
                self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
                self.time_span.blockSignals(False)
            self.start_time.blockSignals(False)
            self.canvas.vb.setXRange(self.start_time.dateTime().toPython().timestamp(),
                                     self.end_time.dateTime().toPython().timestamp(),
                                     padding=0.0)

        def on_time_span_changed(delta: timedelta) -> None:
            self.start_time.blockSignals(True)
            if (self.end_time.dateTime().addMSecs(-round(delta.total_seconds() * 1000))
                    >= self.start_time.minimumDateTime()):
                self.start_time.setDateTime(self.end_time.dateTime().addMSecs(-round(delta.total_seconds() * 1000)))
            else:
                self.start_time.setDateTime(self.start_time.minimumDateTime())
                self.time_span.blockSignals(True)
                self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
                self.time_span.blockSignals(False)
            self.start_time.blockSignals(False)
            self.canvas.vb.setXRange(self.start_time.dateTime().toPython().timestamp(),
                                     self.end_time.dateTime().toPython().timestamp(),
                                     padding=0.0)

        self.start_time.dateTimeChanged.connect(on_start_time_changed)
        self.end_time.dateTimeChanged.connect(on_end_time_changed)
        self.time_span.timeSpanChanged.connect(on_time_span_changed)

    def clear(self) -> None:
        self.canvas.clearPlots()

    def plot(self, data_model: DataModel, x_column_name: Optional[str], y_column_names: Iterable[Optional[str]], *,
             colors: Iterable[QtGui.QColor] = (), visibility: Iterable[bool] = ()) -> None:
        if self.lines:
            self.clear()

        y_column_name: Optional[str]
        color: QtGui.QColor
        visible: bool
        y_column_names = tuple(y_column_names)
        if x_column_name is not None and all(y_column_names):
            x_column: int = data_model.header.index(x_column_name)
            for y_column_name, color, visible in zip(y_column_names,
                                                     cycle(colors or [pg.CONFIG_OPTIONS['foreground']]),
                                                     cycle(visibility or [True])):
                y_column: int = data_model.header.index(cast(str, y_column_name))  # no Nones here
                self.lines.append(self.canvas.plot(data_model[x_column], data_model[y_column], pen=color))
                self.lines[-1].curve.opts['pen'].setCosmetic(True)
                self.lines[-1].setVisible(visible)
            self.canvas.vb.setXRange(data_model[x_column][0], data_model[x_column][-1], padding=0.0)
        else:
            for y_column_name, color, visible in zip(y_column_names,
                                                     cycle(colors or [pg.CONFIG_OPTIONS['foreground']]),
                                                     cycle(visibility or [True])):
                self.lines.append(self.canvas.plot([], [], pen=color))
                self.lines[-1].curve.opts['pen'].setCosmetic(True)
                self.lines[-1].setVisible(visible)

        self.start_time.blockSignals(True)
        self.end_time.blockSignals(True)
        self.time_span.blockSignals(True)
        self.start_time.setDateTime(self.start_time.minimumDateTime())
        self.end_time.setDateTime(self.end_time.maximumDateTime())
        self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
        self.time_span.blockSignals(False)
        self.end_time.blockSignals(False)
        self.start_time.blockSignals(False)

        line: pg.PlotDataItem
        good_lines: list[pg.PlotDataItem] = [line for line in self.lines
                                             if (line.yData is not None
                                                 and line.yData.size
                                                 and not np.all(np.isnan(line.yData)))]
        if good_lines:
            min_y: float = min(cast(float, np.nanmin(line.yData)) for line in good_lines)
            max_y: float = max(cast(float, np.nanmax(line.yData)) for line in good_lines)
            self.canvas.vb.setYRange(min_y, max_y, padding=0.0)

        self.start_time.setEnabled(bool(good_lines))
        self.end_time.setEnabled(bool(good_lines))
        self.time_span.setEnabled(bool(good_lines))

    def replot(self, index: int, data_model: DataModel, x_column_name: Optional[str], y_column_name: Optional[str], *,
               color: Optional[QtGui.QColor | QtGui.QPen] = None, roll: bool = False) -> None:
        if x_column_name is None or y_column_name is None:
            return

        if color is None:
            color = self.lines[index].opts['pen']
        if isinstance(color, QtGui.QPen):
            color.setCosmetic(True)
        else:
            color = pg.mkPen(color, cosmetic=True)
        x_column: int = data_model.header.index(x_column_name)
        y_column: int = data_model.header.index(y_column_name)

        if (
                roll
                and self.lines[index].xData is not None and self.lines[index].xData.size
                and datetime.now() - self._last_time_range_rolled >= timedelta(seconds=1)  # don't roll too often
        ):
            shift: float = data_model[x_column][-1] - self.lines[index].xData[-1]
            x_axis: pg.AxisItem = self.canvas.getAxis('bottom')
            self.canvas.vb.setXRange(min(x_axis.range) + shift, max(x_axis.range) + shift, padding=0.0)
            self._last_time_range_rolled = datetime.now()

        self.lines[index].setData(data_model[x_column], data_model[y_column], pen=color)

    def set_line_visible(self, index: int, visible: bool) -> None:
        self.lines[index].setVisible(visible)

    @property
    def view_range(self) -> list[list[float]]:
        return self.canvas.vb.viewRange()
