# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from itertools import cycle
from typing import Any, List, Optional, Tuple, Iterable

import pyqtgraph as pg
from PySide6.QtCore import Qt, QDateTime, QEvent, QPointF, QRectF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QDateTimeEdit

__all__ = ['Plot']

from gui._data_model import DataModel
from gui._time_span_edit import TimeSpanEdit


class Plot(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, *args: Any) -> None:
        super().__init__(parent, *args)

        self.setObjectName('plot_widget')

        self.setWindowTitle(self.tr('Plot'))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QVBoxLayout = QVBoxLayout(self)

        plot: pg.PlotWidget = pg.PlotWidget(self)
        self.canvas: pg.PlotItem = plot.getPlotItem()
        self.canvas.setAxisItems({'bottom': pg.DateAxisItem()})
        self.canvas.vb.setAutoVisible(x=True, y=True)
        self.canvas.vb.setMouseMode(pg.ViewBox.RectMode)
        self.canvas.vb.setDefaultPadding(0.0)
        layout.addWidget(plot)
        cursor_balloon: pg.TextItem = pg.TextItem()
        plot.addItem(cursor_balloon, True)  # ignore bounds

        x_range_layout: QHBoxLayout = QHBoxLayout()
        layout.addLayout(x_range_layout)
        layout.setStretch(1, 0)

        self.start_time: QDateTimeEdit = QDateTimeEdit(self)
        self.end_time: QDateTimeEdit = QDateTimeEdit(self)
        self.time_span: TimeSpanEdit = TimeSpanEdit(self)
        self.start_time.setDisabled(True)
        self.end_time.setDisabled(True)
        self.time_span.setDisabled(True)
        x_range_layout.addWidget(self.start_time, 0, Qt.AlignmentFlag.AlignLeft)
        x_range_layout.addWidget(self.time_span, 0, Qt.AlignmentFlag.AlignHCenter)
        x_range_layout.addWidget(self.end_time, 0, Qt.AlignmentFlag.AlignRight)
        self.start_time.clearMinimumDateTime()
        self.start_time.clearMaximumDateTime()
        self.end_time.clearMinimumDateTime()
        self.end_time.clearMaximumDateTime()

        def on_mouse_moved(event: Tuple[QPointF]) -> None:
            pos: QPointF = event[0]
            if plot.sceneBoundingRect().contains(pos):
                point: QPointF = self.canvas.vb.mapSceneToView(pos)
                if plot.visibleRange().contains(point):
                    cursor_balloon.setPos(point)
                    cursor_balloon.setText(f'{datetime.fromtimestamp(round(point.x()))}\n{point.y()}')
                    balloon_border: QRectF = cursor_balloon.boundingRect()
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

        def on_lim_changed(arg: Tuple[pg.PlotWidget, List[List[float]]]) -> None:
            rect: List[List[float]] = arg[1]
            x_lim: List[float]
            y_lim: List[float]
            x_lim, y_lim = rect
            self.start_time.blockSignals(True)
            self.end_time.blockSignals(True)
            self.time_span.blockSignals(True)
            self.start_time.setDateTime(QDateTime.fromMSecsSinceEpoch(round(min(x_lim) * 1000)))
            self.end_time.setDateTime(QDateTime.fromMSecsSinceEpoch(round(max(x_lim) * 1000)))
            self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
            self.time_span.blockSignals(False)
            self.end_time.blockSignals(False)
            self.start_time.blockSignals(False)

        def on_plot_left(event: QEvent) -> None:
            self._mouse_moved_signal_proxy.flush()
            cursor_balloon.setVisible(False)
            event.accept()

        self._mouse_moved_signal_proxy: pg.SignalProxy = pg.SignalProxy(plot.scene().sigMouseMoved,
                                                                        rateLimit=10, slot=on_mouse_moved)
        self._axis_range_changed_signal_proxy: pg.SignalProxy = pg.SignalProxy(plot.sigRangeChanged,
                                                                               rateLimit=10, slot=on_lim_changed)
        self._last_time_range_rolled: datetime = datetime.fromtimestamp(0)
        plot.leaveEvent = on_plot_left

        def on_start_time_changed(new_time: QDateTime):
            self.time_span.blockSignals(True)
            self.time_span.from_two_q_date_time(new_time, self.end_time.dateTime())
            self.time_span.blockSignals(False)
            self.canvas.vb.setXRange(self.start_time.dateTime().toPython().timestamp(),
                                     self.end_time.dateTime().toPython().timestamp(),
                                     padding=0.0)

        def on_end_time_changed(new_time: QDateTime):
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

        def on_time_span_changed(delta: timedelta):
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

        self.lines: List[pg.PlotDataItem] = []

    def clear(self) -> None:
        self.canvas.clearPlots()

    def plot(self, data_model: DataModel, x_column_name: str, y_column_names: Iterable[str], *,
             colors: Iterable[QColor] = (), visibility: Iterable[bool] = ()) -> None:
        if self.lines:
            self.clear()

        x_column: int = data_model.header.index(x_column_name)
        y_column_name: str
        color: QColor
        visible: bool
        for y_column_name, color, visible in zip(y_column_names,
                                                 cycle(colors or pg.CONFIG_OPTIONS['foreground']),
                                                 cycle(visibility or True)):
            y_column: int = data_model.header.index(y_column_name)
            self.lines.append(self.canvas.plot(data_model[x_column], data_model[y_column],
                                               pen=color))
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

        self.canvas.vb.autoRange(padding=0.0)

        self.start_time.setEnabled(bool(self.lines))
        self.end_time.setEnabled(bool(self.lines))
        self.time_span.setEnabled(bool(self.lines))

    def replot(self, index: int, data_model: DataModel, x_column_name: str, y_column_name: str, *,
               color: Optional[QColor] = None, roll: bool = False) -> None:
        if color is None:
            color = self.lines[index].opts['pen']
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

        self.canvas.vb.disableAutoRange()
        self.lines[index].setData(data_model[x_column], data_model[y_column], pen=color)

    def set_line_visible(self, index: int, visible: bool) -> None:
        self.canvas.vb.disableAutoRange()
        self.lines[index].setVisible(visible)
