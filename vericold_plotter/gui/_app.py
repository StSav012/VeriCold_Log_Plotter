import os
import sys
from collections.abc import Iterable
from typing import cast

from packaging.version import Version
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

__all__ = ["app"]


app: QtWidgets.QApplication = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
if Version(QtCore.qVersion()) < Version("6"):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

qtbase_translator: QtCore.QTranslator = QtCore.QTranslator()
if qtbase_translator.load(
    QtCore.QLocale(),
    "qtbase",
    "_",
    QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.LibraryPath.TranslationsPath),
):
    QtWidgets.QApplication.installTranslator(qtbase_translator)

if Version(QtCore.qVersion()) >= Version("6.5"):
    self_color_scheme: QtCore.Qt.ColorScheme = QtWidgets.QApplication.styleHints().colorScheme()
    environ_color_scheme: str
    if environ_color_scheme := os.environ.get("THEME", "").casefold():
        if (
            environ_color_scheme not in map(str.casefold, QtCore.Qt.ColorScheme.__members__)
            or QtCore.Qt.ColorScheme.__members__[environ_color_scheme.capitalize()] == QtCore.Qt.ColorScheme.Unknown
        ):
            supported_values: str = ", ".join(
                f"“{s.casefold()}”"
                for s in QtCore.Qt.ColorScheme.__members__
                if QtCore.Qt.ColorScheme.__members__[s] != QtCore.Qt.ColorScheme.Unknown
            )
            sys.stderr.write(f"“THEME” environment variable must be {supported_values}, or unset")
        elif self_color_scheme not in (QtCore.Qt.ColorScheme.Dark, QtCore.Qt.ColorScheme.Light):
            sys.stderr.write("“THEME” environment variable cannot be applied due to unknown app theme")
        else:
            if self_color_scheme != QtCore.Qt.ColorScheme.__members__[environ_color_scheme.capitalize()]:
                palette: QtGui.QPalette = QtWidgets.QApplication.palette()
                color_roles: Iterable[QtGui.QPalette.ColorRole]
                if isinstance(QtGui.QPalette.ColorRole, Iterable):
                    color_roles = QtGui.QPalette.ColorRole
                else:
                    color_roles = map(QtGui.QPalette.ColorRole, range(cast(int, QtGui.QPalette.ColorRole.NColorRoles)))
                cr: QtGui.QPalette.ColorRole
                for cr in color_roles:
                    if cr == QtGui.QPalette.ColorRole.NColorRoles:
                        continue
                    color: QtGui.QColor = palette.color(cr)
                    color = QtGui.QColor.fromHslF(color.hueF(), color.saturationF(), 1.0 - color.lightnessF())
                    palette.setColor(cr, color)
                QtWidgets.QApplication.setPalette(palette)
