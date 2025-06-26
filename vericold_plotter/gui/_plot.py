from datetime import datetime, timedelta
from itertools import cycle
from typing import Iterable, TypeVar, cast

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

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)

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

        self.canvas.autoBtn.clicked.disconnect(self.canvas.autoBtnClicked)
        self.canvas.autoBtn.clicked.connect(self.auto_range_y)

        menu_action: QtGui.QAction
        for menu_action in self.canvas.ctrlMenu.actions():
            if menu_action.text() not in [
                QtCore.QCoreApplication.translate("PlotItem", "Grid"),
            ]:
                menu_action.deleteLater()

        self.canvas.vb.disableAutoRange()
        self.canvas.vb.setAutoVisible(x=True, y=True)
        self.canvas.vb.setDefaultPadding(0.0)
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
                    x: float = point.x()
                    y: float = point.y()
                    if self.canvas.axes["left"]["item"].logMode:
                        y = 10**y
                    # don't use `datetime.fromtimestamp` here directly to avoid OSError on Windows when x < 0
                    cursor_balloon.setText(f"{_THE_BEGINNING_OF_TIME + timedelta(seconds=x)}\n{y}")
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

        def on_lim_changed(arg: tuple[PlotWidget, list[list[float]]]) -> None:
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
                self.auto_range_y()
            event.accept()

        self._mouse_moved_signal_proxy: SignalProxy = SignalProxy(
            plot.scene().sigMouseMoved,
            rateLimit=10,
            slot=on_mouse_moved,
        )
        self._axis_range_changed_signal_proxy: SignalProxy = SignalProxy(
            plot.sigRangeChanged,
            rateLimit=10,
            slot=on_lim_changed,
        )
        self._last_time_range_rolled: datetime = datetime.fromtimestamp(0)
        plot.leaveEvent = on_plot_left
        plot.scene().sigMouseClicked.connect(on_mouse_clicked)

        def on_start_time_changed(new_time: QtCore.QDateTime) -> None:
            self.time_span.blockSignals(True)
            self.time_span.from_two_q_date_time(new_time, self.end_time.dateTime())
            self.time_span.blockSignals(False)
            self.canvas.vb.setXRange(
                self.start_time.dateTime().toPython().timestamp(),
                self.end_time.dateTime().toPython().timestamp(),
                padding=0.0,
            )

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
            self.canvas.vb.setXRange(
                self.start_time.dateTime().toPython().timestamp(),
                self.end_time.dateTime().toPython().timestamp(),
                padding=0.0,
            )

        def on_time_span_changed(delta: timedelta) -> None:
            self.start_time.blockSignals(True)
            if (
                self.end_time.dateTime().addMSecs(-round(delta.total_seconds() * 1000))
                >= self.start_time.minimumDateTime()
            ):
                self.start_time.setDateTime(self.end_time.dateTime().addMSecs(-round(delta.total_seconds() * 1000)))
            else:
                self.start_time.setDateTime(self.start_time.minimumDateTime())
                self.time_span.blockSignals(True)
                self.time_span.from_two_q_date_time(self.start_time.dateTime(), self.end_time.dateTime())
                self.time_span.blockSignals(False)
            self.start_time.blockSignals(False)
            self.canvas.vb.setXRange(
                self.start_time.dateTime().toPython().timestamp(),
                self.end_time.dateTime().toPython().timestamp(),
                padding=0.0,
            )

        self.start_time.dateTimeChanged.connect(on_start_time_changed)
        self.end_time.dateTimeChanged.connect(on_end_time_changed)
        self.time_span.timeSpanChanged.connect(on_time_span_changed)

    @QtCore.Slot()
    def auto_range_y(self) -> None:
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
            if not line.isVisible() or line.yData is None or not line.yData.size:
                continue
            visible_data_piece: NDArray[np.float64] = line.yData[(line.xData >= x_min) & (line.xData <= x_max)]
            if np.any((visible_data_piece >= y_min) & (visible_data_piece <= y_max)):
                visible_data.append(visible_data_piece)
        if not visible_data:
            return
        min_y: float
        max_y: float
        if self.canvas.axes["left"]["item"].logMode:
            positive_data: list[NDArray[np.float64]] = [d[d > 0] for d in visible_data]
            min_y = np.log10(min(cast(float, np.nanmin(d)) for d in positive_data))
            max_y = np.log10(max(cast(float, np.nanmax(d)) for d in positive_data))
        else:
            min_y = min(cast(float, np.nanmin(d)) for d in visible_data)
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

                line = self.canvas.plot(
                    x_data,
                    normalize(data_model[y_column]) if normalized else data_model[y_column],
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

        self.lines[index].setData(
            data_model[x_column],
            normalize(data_model[y_column]) if normalized else data_model[y_column],
            pen=color,
        )

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
