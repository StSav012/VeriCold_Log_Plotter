# coding: utf-8
from datetime import timedelta
from typing import Tuple, List, cast

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QLineEdit

__all__ = ['TimeSpanEdit']


class TimeDeltaValidator(QValidator):
    def validate(self, text: str, cursor_position: int) -> Tuple[QValidator.State, str, int]:
        # remove invalid characters
        valid_characters: str = '0123456789:' + self.locale().decimalPoint()
        i: int = 0
        while i < len(text):
            while i < len(text) and text[i] not in valid_characters:
                text = text[:i] + text[i + 1:]
                if i <= cursor_position:
                    cursor_position -= 1
            else:
                i += 1

        if not text:
            return QValidator.State.Invalid, text, cursor_position

        parts: List[str] = text.split(':')
        if not parts[-1]:  # text ends with ':', the rest has not been entered yet
            return QValidator.State.Intermediate, text, cursor_position
        ok: bool
        seconds: float
        seconds, ok = self.locale().toDouble(parts[-1])
        if not ok or seconds > 60.:
            return QValidator.State.Invalid, text, cursor_position

        if len(parts) >= 2:
            minutes: int
            minutes, ok = self.locale().toUShort(parts[-2])
            if not ok or minutes > 60:
                return QValidator.State.Invalid, text, cursor_position

        if len(parts) >= 3:
            hours: int
            hours, ok = self.locale().toUShort(parts[-3])
            if not ok or hours > 24:
                return QValidator.State.Invalid, text, cursor_position

        if len(parts) >= 4:
            days: int
            days, ok = self.locale().toULongLong(parts[-4])
            if not ok:
                return QValidator.State.Invalid, text, cursor_position

        if len(parts) >= 5:
            return QValidator.State.Invalid, text, cursor_position

        return QValidator.State.Acceptable, text, cursor_position


class TimeSpanEdit(QLineEdit):
    timeSpanChanged: Signal = Signal(timedelta, name='timeSpanChanged')

    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.setValidator(TimeDeltaValidator())
        self.setAlignment(cast(Qt.Alignment, Qt.AlignmentFlag.AlignRight))

        self.editingFinished.connect(self._on_edit_finished)

    @property
    def time_delta(self) -> timedelta:
        if not self.text():
            raise ValueError
        parts: List[str] = self.text().split(':')
        ok: bool
        seconds: float
        minutes: int = 0
        hours: int = 0
        days: int = 0
        seconds, ok = self.locale().toDouble(parts[-1])
        if not ok or seconds > 60.:
            raise ValueError
        if len(parts) >= 2:
            minutes, ok = self.locale().toUShort(parts[-2])
            if not ok or minutes > 60:
                raise ValueError
        if len(parts) >= 3:
            hours, ok = self.locale().toUShort(parts[-3])
            if not ok or hours > 24:
                raise ValueError
        if len(parts) >= 4:
            days, ok = self.locale().toULongLong(parts[-4])
            if not ok:
                raise ValueError
        if len(parts) >= 5:
            raise ValueError
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @time_delta.setter
    def time_delta(self, delta: timedelta) -> None:
        days: int = delta.days
        seconds: float = delta.seconds % 60 + 1e-6 * delta.microseconds
        minutes: int = (delta.seconds // 60) % 60
        hours: int = delta.seconds // 3600
        seconds_str: str = f'{seconds:02.0f}' if abs(seconds % 1.0) < 0.001 else f'{seconds:06.3f}'
        if days > 0:
            self.setText(f'{days}:{hours:02d}:{minutes:02d}:{seconds_str}')
        elif hours > 0:
            self.setText(f'{hours:02d}:{minutes:02d}:{seconds_str}')
        elif minutes > 0:
            self.setText(f'{minutes:02d}:{seconds_str}')
        else:
            self.setText(seconds_str)

    @property
    def total_seconds(self) -> float:
        return self.time_delta.total_seconds()

    def from_two_q_date_time(self, date_time_1: QDateTime, date_time_2: QDateTime) -> None:
        self.time_delta = abs(date_time_2.toPython() - date_time_1.toPython())

    def _on_edit_finished(self) -> None:
        self.timeSpanChanged.emit(self.time_delta)
