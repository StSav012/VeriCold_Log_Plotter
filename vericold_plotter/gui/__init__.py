from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

__all__ = ["run"]

"""Compatibility fixes"""

if not hasattr(QtGui, "QAction"):  # PyQt5, PySide2
    QtGui.QAction = QtWidgets.QAction  # type: ignore

if not hasattr(QtWidgets.QApplication, "exec"):  # PySide2
    QtWidgets.QApplication.exec = QtWidgets.QApplication.exec_

if not hasattr(QtCore.QDateTime, "toPython"):  # PyQt5, PyQt6
    # see https://stackoverflow.com/a/72057407/8554611 to find out why we can't reduce lambda here
    QtCore.QDateTime.toPython = lambda self: QtCore.QDateTime.toPyDateTime(self)  # type: ignore

if not hasattr(QtCore.QLibraryInfo, "path"):  # PyQt5, PySide2
    QtCore.QLibraryInfo.path = QtCore.QLibraryInfo.location

if not hasattr(QtCore.QLibraryInfo, "LibraryPath"):  # PyQt5, PySide2
    QtCore.QLibraryInfo.LibraryPath = QtCore.QLibraryInfo.LibraryLocation  # type: ignore

if not hasattr(QtCore, "Slot"):  # PyQt5, PyQt6
    QtCore.Slot = QtCore.pyqtSlot  # type: ignore


def run() -> int:
    import sys

    from ._app import app
    from ._ui import MainWindow

    window: MainWindow = MainWindow()
    # if a command line argument starts with `-check`, enable the auto-reload timer
    index: int
    argv: str
    check_file_updates: bool = "-check" in sys.argv[1:] or "--check" in sys.argv[1:]
    for index, argv in enumerate(sys.argv[1:], start=1):
        if argv.split()[0] == "-check":
            check_file_updates = True
            sys.argv[index] = argv[len("-check") :].lstrip()
    window.load_file(
        (QtCore.QUrl(argv).path() or argv for argv in sys.argv[1:]),
        check_file_updates=check_file_updates,
    )
    window.show()
    return app.exec()
