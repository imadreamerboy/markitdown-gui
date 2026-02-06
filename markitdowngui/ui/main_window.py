from __future__ import annotations

from qfluentwidgets import (
    FluentIcon as FIF,
    FluentWindow,
    NavigationItemPosition,
    Theme,
    setTheme,
)

from markitdowngui.core.settings import SettingsManager
from markitdowngui.ui.dialogs.about import AboutDialog
from markitdowngui.ui.help_interface import HelpInterface
from markitdowngui.ui.home_interface import HomeInterface
from markitdowngui.ui.settings_interface import SettingsInterface
from markitdowngui.utils.logger import AppLogger
from markitdowngui.utils.translations import DEFAULT_LANG, get_translation


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()

        self._init_window()
        self._init_interfaces()
        self._init_navigation()
        self.apply_theme()

        AppLogger.info("MainWindow initialized with FluentWindow")

    def _init_window(self) -> None:
        self.setWindowTitle(self.translate("app_title"))
        self.resize(980, 740)

        geometry = self.settings_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)

    def _init_interfaces(self) -> None:
        self.homeInterface = HomeInterface(self.settings_manager, self)
        self.settingsInterface = SettingsInterface(
            self.settings_manager, self.translate, self
        )
        self.helpInterface = HelpInterface(self.translate, self)

        self.settingsInterface.theme_mode_changed.connect(self._on_theme_mode_changed)
        self.helpInterface.check_updates_requested.connect(
            self.homeInterface.manual_update_check
        )
        self.helpInterface.show_shortcuts_requested.connect(
            self.homeInterface.show_shortcuts
        )
        self.helpInterface.show_about_requested.connect(self.show_about)

    def _init_navigation(self) -> None:
        self.addSubInterface(
            self.homeInterface, FIF.HOME, self.translate("nav_home")
        )
        self.addSubInterface(
            self.settingsInterface, FIF.SETTING, self.translate("nav_settings")
        )
        self.addSubInterface(self.helpInterface, FIF.HELP, self.translate("nav_help"))

        self.navigationInterface.addSeparator()
        self.navigationInterface.addItem(
            routeKey="convert_action",
            icon=FIF.PLAY,
            text=self.translate("nav_convert"),
            onClick=self.trigger_convert,
            position=NavigationItemPosition.BOTTOM,
        )

    def _on_theme_mode_changed(self, _mode: str) -> None:
        self.apply_theme()

    def trigger_convert(self) -> None:
        self.switchTo(self.homeInterface)
        self.homeInterface.convert_files()

    def apply_theme(self) -> None:
        theme_mode = self.settings_manager.get_theme_mode()
        if theme_mode == "dark":
            setTheme(Theme.DARK)
        elif theme_mode == "system":
            setTheme(Theme.AUTO)
        else:
            setTheme(Theme.LIGHT)

    def show_about(self) -> None:
        dlg = AboutDialog(self.translate, self)
        dlg.exec()

    def closeEvent(self, event) -> None:
        self.settings_manager.set_window_geometry(self.saveGeometry().data())
        self.homeInterface.shutdown()
        super().closeEvent(event)

    def translate(self, key: str) -> str:
        current_lang = self.settings_manager.get_current_language() or DEFAULT_LANG
        return get_translation(current_lang, key)
