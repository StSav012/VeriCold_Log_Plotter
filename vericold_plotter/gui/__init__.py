import sys
from typing import cast

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

_old_locale_to_string = QtCore.QLocale.toString


def _locale_to_string(locale: QtCore.QLocale, *args: object) -> str:
    if len(args) == 2 and isinstance(args[0], QtCore.QTime) and args[1] == QtCore.QLocale.FormatType.ShortFormat:
        fmt: QtCore.QLocale.FormatType = cast(QtCore.QLocale.FormatType, args[1])

        def insert_text_after(s: str, what: str, where: str) -> str:
            index: int = 0
            quote_indices: list[int] = []
            quote_index: int = 0
            while (quote_index := s.find("'", quote_index)) != -1:
                quote_indices.append(quote_index)
                quote_index += 1
            while (index := s.find(where, index)) != -1:
                if any(a <= index <= b for a, b in zip(quote_indices[:-1:2], quote_indices[1::2], strict=True)):
                    for a, b in zip(quote_indices[:-1:2], quote_indices[1::2], strict=True):
                        if a <= index <= b:
                            index = b
                            break
                    continue
                index += len(where)
                s = s[:index] + what + s[index:]
                index += len(what)
            return s

        def remove_quotes(s: str) -> str:
            quote_indices: list[int] = []
            quote_index: int = 0
            while (quote_index := s.find("'", quote_index)) != -1:
                quote_indices.append(quote_index)
                quote_index += 1
            for b, a in zip(quote_indices[-1::-2], quote_indices[-2::-2], strict=True):
                s = s[:a] + s[b + 1 :]
            return s

        template: str = locale.timeFormat(fmt)
        template_without_literals: str = remove_quotes(template)
        # NB: do NOT test for ‘m’ before ‘mm’
        fix_ups: dict[str, str] = {
            "h.mm": ".ss",
            "h:mm": ":ss",
            "H.mm": ".ss",
            "H:mm": ":ss",
            "h.m": ".s",
            "h:m": ":s",
            "H.m": ".s",
            "H:m": ":s",
            "H'h'mm": "'m'ss",
            "h'h'mm": "'m'ss",
            "H'h'm": "'m's",
            "h'h'm": "'m's",
            "ཆུ་ཚོད་ hh སྐར་མ་ mm": " སྐར་ཆ་ ss",
            "ཆུ་ཚོད་ HH སྐར་མ་ mm": " སྐར་ཆ་ ss",
            "ཆུ་ཚོད་ h སྐར་མ་ mm": " སྐར་ཆ་ ss",
            "ཆུ་ཚོད་ H སྐར་མ་ mm": " སྐར་ཆ་ ss",
            "ཆུ་ཚོད་ hh སྐར་མ་ m": " སྐར་ཆ་ s",
            "ཆུ་ཚོད་ HH སྐར་མ་ m": " སྐར་ཆ་ s",
            "ཆུ་ཚོད་ h སྐར་མ་ m": " སྐར་ཆ་ s",
            "ཆུ་ཚོད་ H སྐར་མ་ m": " སྐར་ཆ་ s",
        }
        if not any(s in template_without_literals for s in fix_ups.values()):
            for hm, s in fix_ups.items():
                if hm in template:
                    template = insert_text_after(template, s, hm)
                    break

        return _old_locale_to_string(locale, cast(QtCore.QTime, args[0]), template)

    # noinspection PyArgumentList
    return _old_locale_to_string(locale, *args)


QtCore.QLocale.toString = _locale_to_string


if sys.platform == "win32":

    class DockWidget(QtWidgets.QDockWidget):
        """A `QtWidgets.QDockWidget` that doesn't display an `&` in the title.

        The issue occurs on Windows OS.
        """

        def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
            super().__init__(parent)

            @QtCore.Slot()
            def on_top_level_changed(_top_level: bool) -> None:
                if self.windowHandle() is not None:
                    self.windowHandle().setTitle(self.windowTitle().replace("&", ""))

            self.topLevelChanged.connect(on_top_level_changed)

        def restoreGeometry(self, geometry: QtCore.QByteArray | bytes | bytearray | memoryview) -> bool:
            res: bool = super().restoreGeometry(geometry)
            if self.windowHandle() is not None:
                self.windowHandle().setTitle(self.windowTitle().replace("&", ""))
            return res

        def setWindowTitle(self, title: str) -> None:
            super().setWindowTitle(title.replace("&", ""))
            if self.windowHandle() is not None:
                self.windowHandle().setTitle(title.replace("&", ""))
            self.toggleViewAction().setText(title)

    QtWidgets.QDockWidget = DockWidget


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
