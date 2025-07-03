from typing import ClassVar

from pyqtgraph.Qt import QtCore, QtWidgets

__all__ = ["DoubleClickSpinBox", "DoubleClickDoubleSpinBox", "DoubleClickDateTimeEdit"]


class DoubleClickSpinBox(QtWidgets.QSpinBox):
    doubleClicked: ClassVar[QtCore.Signal] = QtCore.Signal(name="doubleClicked")

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, sender: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.MouseButtonDblClick and sender is self.lineEdit():
            self.doubleClicked.emit()
        return super().eventFilter(sender, event)


class DoubleClickDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    doubleClicked: ClassVar[QtCore.Signal] = QtCore.Signal(name="doubleClicked")

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, sender: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.MouseButtonDblClick and sender is self.lineEdit():
            self.doubleClicked.emit()
        return super().eventFilter(sender, event)


class DoubleClickDateTimeEdit(QtWidgets.QDateTimeEdit):
    doubleClicked: ClassVar[QtCore.Signal] = QtCore.Signal(name="doubleClicked")

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, sender: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.MouseButtonDblClick and sender is self.lineEdit():
            self.doubleClicked.emit()
        return super().eventFilter(sender, event)
