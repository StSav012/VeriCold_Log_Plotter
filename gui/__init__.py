# -*- coding: utf-8 -*-
from typing import Set

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator, QUrl
from PySide6.QtWidgets import QApplication

from gui._ui import MainWindow


def run() -> None:
    import sys

    app: QApplication = QApplication(sys.argv)

    languages: Set[str] = set(QLocale().uiLanguages() + [QLocale().bcp47Name(), QLocale().name()])
    language: str
    qt_translator: QTranslator = QTranslator()
    for language in languages:
        if qt_translator.load('qt_' + language,
                              QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(qt_translator)
            break
    qtbase_translator: QTranslator = QTranslator()
    for language in languages:
        if qtbase_translator.load('qtbase_' + language,
                                  QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(qtbase_translator)
            break

    window: MainWindow = MainWindow(application=app)
    # if a command line argument starts with `-check`, enable the auto-reload timer
    argv: str
    check_file_updates: bool = '-check' in sys.argv[1:] or '--check' in sys.argv[1:]
    for argv in sys.argv[1:]:
        if argv.split()[0] == '-check':
            check_file_updates = True
            argv = ' '.join(argv.split()[1:])
        if window.load_file(QUrl(argv).path() or argv, check_file_updates=check_file_updates):
            break
    window.show()
    app.exec()
