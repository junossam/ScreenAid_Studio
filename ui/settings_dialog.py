from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from application.startup import StartupManager
from core.event_bus import EventBus
from core.localization import tr
from services.settings.settings_manager import SettingsManager
from ui.settings_sections import (
    build_command_mode_tab,
    build_hotkeys_tab,
    build_region_tab,
    export_dialog_settings,
    import_dialog_settings,
    reset_dialog_to_defaults,
)
from ui.settings_tabs import (
    build_about_tab,
    build_capture_tab,
    build_click_tab,
    build_drawing_tab,
    build_general_tab,
    build_live_tab,
    build_magnifier_tab,
    build_notification_tab,
    build_overlay_tab,
    build_pinned_tab,
)
from ui.settings_values import load_dialog_values, save_dialog_values


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings_manager: SettingsManager,
        startup_manager: StartupManager,
        locales_dir: Path,
        bus: EventBus | None = None,
    ) -> None:
        super().__init__()
        self.settings_manager = settings_manager
        self.startup_manager = startup_manager
        self.locales_dir = locales_dir
        self.bus = bus
        self.parser = settings_manager.load_parser()
        self.setWindowTitle(tr("settings.title"))
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "resources" / "tray_icon.ico")))
        self.setMinimumWidth(420)
        self._build()
        self._load_values()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        for widget, title in (
            (build_general_tab(self), "settings.tab.general"),
            (build_overlay_tab(self), "settings.tab.overlay"),
            (build_click_tab(self), "settings.tab.click"),
            (build_capture_tab(self), "settings.tab.capture"),
            (build_notification_tab(self), "settings.tab.notification"),
            (build_drawing_tab(self), "settings.tab.drawing"),
            (build_pinned_tab(self), "settings.tab.pinned"),
            (build_live_tab(self), "settings.tab.live"),
            (build_magnifier_tab(self), "settings.tab.magnifier"),
            (build_hotkeys_tab(self), "settings.tab.hotkeys"),
            (build_command_mode_tab(self), "settings.tab.command_mode"),
            (build_region_tab(self), "settings.tab.region"),
            (build_about_tab(self), "settings.tab.about"),
        ):
            tabs.addTab(self._scrollable(widget), tr(title))
        layout.addWidget(tabs)
        self.notice = QLabel(tr("settings.notice"))
        layout.addWidget(self.notice)
        layout.addWidget(self._buttons())

    def _buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox()
        save_button = buttons.addButton(tr("settings.save"), QDialogButtonBox.ButtonRole.ActionRole)
        save_close_button = buttons.addButton(tr("settings.save_and_close"), QDialogButtonBox.ButtonRole.ActionRole)
        cancel_button = buttons.addButton(tr("settings.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        import_button = buttons.addButton(tr("settings.import_settings"), QDialogButtonBox.ButtonRole.ActionRole)
        export_button = buttons.addButton(tr("settings.export_settings"), QDialogButtonBox.ButtonRole.ActionRole)
        reset_button = buttons.addButton(tr("settings.reset_defaults"), QDialogButtonBox.ButtonRole.ResetRole)
        save_button.clicked.connect(lambda: self._save(False))
        save_close_button.clicked.connect(lambda: self._save(True))
        cancel_button.clicked.connect(self.reject)
        import_button.clicked.connect(lambda: import_dialog_settings(self))
        export_button.clicked.connect(lambda: export_dialog_settings(self))
        reset_button.clicked.connect(lambda: reset_dialog_to_defaults(self))
        return buttons

    def _scrollable(self, widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setWidget(widget)
        return area

    def _load_values(self) -> None:
        load_dialog_values(self)

    def _save(self, close: bool) -> None:
        save_dialog_values(self, close)

    def _bool(self, section: str, key: str, fallback: bool) -> bool:
        return self.parser.getboolean(section, key, fallback=fallback)

    def _int(self, section: str, key: str, fallback: int) -> int:
        return self.parser.getint(section, key, fallback=fallback)

    def _float(self, section: str, key: str, fallback: float) -> float:
        return self.parser.getfloat(section, key, fallback=fallback)

    def _set(self, section: str, key: str, value: object) -> None:
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        if isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        self.parser.set(section, key, text)

    def _sync_click_option_state(self, enabled: bool) -> None:
        widgets = (
            self.show_left,
            self.show_right,
            self.show_both,
            self.show_wheel,
            self.show_wheel_drag,
            self.click_images,
            self.show_double,
            self.show_text,
            self.image_size,
            self.image_gap,
            self.click_duration,
            self.click_fade,
            self.click_radius,
            self.click_pressed_radius,
            self.click_outline_width,
            self.left_color,
            self.right_color,
            self.both_color,
            self.middle_color,
            self.wheel_color,
            self.outline_color,
        )
        for widget in widgets:
            widget.setEnabled(enabled)

    def _sync_notification_option_state(self, enabled: bool) -> None:
        widgets = (
            self.notification_capture_completed,
            self.notification_capture_failed,
            self.notification_hotkey_failed,
            self.notification_pin_failed,
            self.notification_live_failed,
            self.notification_drawing_mode_changed,
            self.notification_pause_changed,
            self.notification_command_blocked,
            self.notification_click_effects_changed,
            self.notification_manual_failed,
        )
        for widget in widgets:
            widget.setEnabled(enabled)

    @staticmethod
    def _spin(minimum: int, maximum: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        return spin

    @staticmethod
    def _double_spin(minimum: float, maximum: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        return spin
