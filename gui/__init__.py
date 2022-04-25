# -*- coding: utf-8 -*-
from typing import Set

from pyqtgraph.Qt import QtCore, QtWidgets

from gui._ui import MainWindow


def run() -> None:
    import sys

    app: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)

    languages: Set[str] = set(QtCore.QLocale().uiLanguages() + [QtCore.QLocale().bcp47Name(), QtCore.QLocale().name()])
    language: str
    qt_translator: QtCore.QTranslator = QtCore.QTranslator()
    for language in languages:
        if qt_translator.load('qt_' + language,
                              QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)):
            app.installTranslator(qt_translator)
            break
    qtbase_translator: QtCore.QTranslator = QtCore.QTranslator()
    for language in languages:
        if qtbase_translator.load('qtbase_' + language,
                                  QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)):
            app.installTranslator(qtbase_translator)
            break

    window: MainWindow = MainWindow(application=app)
    # if a command line argument starts with `-check`, enable the auto-reload timer
    index: int
    argv: str
    check_file_updates: bool = '-check' in sys.argv[1:] or '--check' in sys.argv[1:]
    for index, argv in enumerate(sys.argv[1:], start=1):
        if argv.split()[0] == '-check':
            check_file_updates = True
            sys.argv[index] = argv[len('-check'):].lstrip()
    window.load_file((QtCore.QUrl(argv).path() or argv for argv in sys.argv[1:]), check_file_updates=check_file_updates)
    window.show()
    app.exec()
