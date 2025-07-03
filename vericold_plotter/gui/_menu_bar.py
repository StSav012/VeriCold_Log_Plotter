from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

__all__ = ["MenuBar"]


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent=parent)

        self.menu_file: QtWidgets.QMenu = QtWidgets.QMenu(self)
        self.menu_view: QtWidgets.QMenu = QtWidgets.QMenu(self)
        self.menu_about: QtWidgets.QMenu = QtWidgets.QMenu(self)
        self.action_open: QtGui.QAction = QtGui.QAction(self)
        self.action_export: QtGui.QAction = QtGui.QAction(self)
        self.action_export_visible: QtGui.QAction = QtGui.QAction(self)
        self.action_reload: QtGui.QAction = QtGui.QAction(self)
        self.action_auto_reload: QtGui.QAction = QtGui.QAction(self)
        self.action_preferences: QtGui.QAction = QtGui.QAction(self)
        self.action_quit: QtGui.QAction = QtGui.QAction(self)
        self.action_about: QtGui.QAction = QtGui.QAction(self)
        self.action_about_qt: QtGui.QAction = QtGui.QAction(self)

        self.setup_ui()

    def setup_ui(self) -> None:
        self.setObjectName("menu_bar")
        self.menu_file.setObjectName("menu_file")
        self.menu_file.setObjectName("menu_view")
        self.menu_about.setObjectName("menu_about")

        self.action_open.setIcon(
            QtGui.QIcon.fromTheme(
                "document-open",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton),
            )
        )
        self.action_open.setObjectName("action_open")
        self.action_export.setIcon(QtGui.QIcon.fromTheme("document-save-as"))
        self.action_export.setObjectName("action_export")
        self.action_export_visible.setIcon(QtGui.QIcon.fromTheme("document-save-as"))
        self.action_export_visible.setObjectName("action_export_visible")
        self.action_reload.setIcon(
            QtGui.QIcon.fromTheme(
                "view-refresh",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload),
            )
        )
        self.action_reload.setObjectName("action_reload")
        self.action_auto_reload.setObjectName("action_auto_reload")
        self.action_preferences.setMenuRole(QtGui.QAction.MenuRole.PreferencesRole)
        self.action_preferences.setObjectName("action_preferences")
        self.action_quit.setIcon(
            QtGui.QIcon.fromTheme(
                "application-exit",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton),
            )
        )
        self.action_quit.setMenuRole(QtGui.QAction.MenuRole.QuitRole)
        self.action_quit.setObjectName("action_quit")
        self.action_about.setIcon(
            QtGui.QIcon.fromTheme(
                "help-about",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogHelpButton),
            )
        )
        self.action_about.setMenuRole(QtGui.QAction.MenuRole.AboutRole)
        self.action_about.setObjectName("action_about")
        self.action_about_qt.setIcon(
            QtGui.QIcon.fromTheme(
                "help-about-qt",
                QtGui.QIcon(":/qt-project.org/qmessagebox/images/qtlogo-64.png"),
            )
        )
        self.action_about_qt.setMenuRole(QtGui.QAction.MenuRole.AboutQtRole)
        self.action_about_qt.setObjectName("action_about_qt")
        self.menu_file.addAction(self.action_open)
        self.menu_file.addAction(self.action_export)
        self.menu_file.addAction(self.action_export_visible)
        self.menu_file.addAction(self.action_reload)
        self.menu_file.addAction(self.action_auto_reload)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_preferences)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_quit)
        self.menu_about.addAction(self.action_about)
        self.menu_about.addAction(self.action_about_qt)
        self.addAction(self.menu_file.menuAction())
        self.addAction(self.menu_view.menuAction())
        self.addAction(self.menu_about.menuAction())

        self.action_export.setEnabled(False)
        self.action_export_visible.setEnabled(False)
        self.action_reload.setEnabled(False)
        self.action_auto_reload.setEnabled(False)
        self.action_auto_reload.setCheckable(True)

        self.action_open.setShortcut(QtGui.QKeySequence("Ctrl+O"))
        self.action_export.setShortcuts((QtGui.QKeySequence("Ctrl+S"), QtGui.QKeySequence("Ctrl+E")))
        self.action_export_visible.setShortcuts(
            (
                QtGui.QKeySequence("Shift+Ctrl+S"),
                QtGui.QKeySequence("Shift+Ctrl+E"),
            )
        )
        self.action_reload.setShortcuts((QtGui.QKeySequence("Ctrl+R"), QtGui.QKeySequence("F5")))
        self.action_preferences.setShortcut(QtGui.QKeySequence("Ctrl+,"))
        self.action_quit.setShortcuts((QtGui.QKeySequence("Ctrl+Q"), QtGui.QKeySequence("Ctrl+X")))
        self.action_about.setShortcut(QtGui.QKeySequence("F1"))

        self.action_about.triggered.connect(self.on_action_about_triggered)
        self.action_about_qt.triggered.connect(self.on_action_about_qt_triggered)

        self.menu_file.setTitle(self.tr("&File"))
        self.menu_view.setTitle(self.tr("&View"))
        self.menu_about.setTitle(self.tr("&About"))
        self.action_open.setText(self.tr("&Open…"))
        self.action_export.setText(self.tr("&Export…"))
        self.action_export_visible.setText(self.tr("Export &Visible…"))
        self.action_reload.setText(self.tr("&Reload"))
        self.action_auto_reload.setText(self.tr("&Auto Reload"))
        self.action_preferences.setText(self.tr("&Preferences…"))
        self.action_quit.setText(self.tr("&Quit"))
        self.action_about.setText(self.tr("&About"))
        self.action_about_qt.setText(self.tr("About &Qt"))

    @QtCore.Slot()
    def on_action_about_triggered(self) -> None:
        try:
            from .._version import __version__
        except ImportError:
            __version__ = None

        QtWidgets.QMessageBox.about(
            self,
            self.tr("About VeriCold Log Plotter"),
            "<html><p>"
            + (
                (self.tr("VeriCold Log Plotter is version {0}").format(__version__) + "</p><p>")
                if __version__ is not None
                else ""
            )
            + self.tr("VeriCold logfiles are created by Oxford Instruments plc.")
            + "</p><p>"
            + self.tr("VeriCold Log Plotter is licensed under the {0}.").format(
                "<a href='https://www.gnu.org/copyleft/lesser.html'>{}</a>".format(self.tr("GNU LGPL version 3"))
            )
            + "</p><p>"
            + self.tr("The source code is available on {0}.").format(
                "<a href='https://github.com/StSav012/VeriCold_Log_Plotter'>GitHub</a>"
            )
            + "</p></html>",
        )

    @QtCore.Slot()
    def on_action_about_qt_triggered(self) -> None:
        QtWidgets.QMessageBox.aboutQt(self)
