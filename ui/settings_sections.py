from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from core.command_mode import COMMAND_MODE_COMMANDS
from core.hotkeys import DEFAULT_HOTKEYS
from core.localization import tr


COMMAND_KEY_DEFAULTS = {
    "toggle_overlay": "O",
    "toggle_click_effects": "E",
    "toggle_drawing": "D",
    "pass_through": "P",
    "clear_drawing": "C",
    "undo_drawing": "Z",
    "redo_drawing": "Y",
    "capture_region": "R",
    "capture_last_region": "L",
    "capture_monitor": "M",
    "capture_virtual": "V",
    "capture_window": "W",
    "pin_region": "K",
    "pin_last_capture": "B",
    "live_region": "G",
    "live_stop_all": "X",
    "fullscreen_magnifier": "F",
    "open_settings": "S",
    "toggle_pause": "Space",
}

CAPTURE_MODE_OPTIONS = ("region", "last_region", "current_monitor", "virtual_screen", "active_window")
DRAWING_TOOL_OPTIONS = (
    "freehand",
    "highlighter",
    "line",
    "arrow",
    "rectangle",
    "ellipse",
    "stamp_star",
    "stamp_heart",
    "eraser",
)
LINE_STYLE_OPTIONS = ("solid", "dash", "dot", "dashdot")
ERASER_MODE_OPTIONS = ("object", "pixel")
STORAGE_MODE_OPTIONS = ("portable", "appdata")


def add_translated_items(combo: QComboBox, prefix: str, values: tuple[str, ...]) -> None:
    for value in values:
        combo.addItem(tr(f"{prefix}.{value}"), value)


def set_combo_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(max(0, index))


def combo_data(combo: QComboBox, fallback: str) -> str:
    return combo.currentData() or fallback


def localize_dialog_buttons(buttons, reset_button) -> None:
    save = buttons.button(QDialogButtonBox.StandardButton.Save)
    cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    if save is not None:
        save.setText(tr("settings.save"))
    if cancel is not None:
        cancel.setText(tr("settings.cancel"))
    reset_button.setText(tr("settings.reset_defaults"))


def build_hotkeys_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.hotkey_fields = {}
    for name, default in DEFAULT_HOTKEYS.items():
        field = QLineEdit()
        field.setPlaceholderText(default)
        dialog.hotkey_fields[name] = field
        layout.addRow(tr(f"hotkey.{name}"), field)
    return widget


def build_command_mode_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.command_mode_show_hint = QCheckBox()
    dialog.command_mode_timeout = dialog._spin(500, 30000)
    dialog.command_key_fields = {}
    layout.addRow(tr("settings.command_mode_show_hint"), dialog.command_mode_show_hint)
    layout.addRow(tr("settings.command_mode_timeout"), dialog.command_mode_timeout)
    for name in COMMAND_MODE_COMMANDS:
        field = QLineEdit()
        dialog.command_key_fields[name] = field
        layout.addRow(tr(f"hotkey.{name}"), field)
    return widget


def build_region_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.region_opacity = dialog._spin(0, 255)
    dialog.region_border_width = dialog._spin(1, 20)
    dialog.region_show_size = QCheckBox()
    dialog.region_show_coordinates = QCheckBox()
    dialog.region_min_width = dialog._spin(1, 500)
    dialog.region_min_height = dialog._spin(1, 500)
    layout.addRow(tr("settings.region_opacity"), dialog.region_opacity)
    layout.addRow(tr("settings.region_border_width"), dialog.region_border_width)
    layout.addRow(tr("settings.region_show_size"), dialog.region_show_size)
    layout.addRow(tr("settings.region_show_coordinates"), dialog.region_show_coordinates)
    layout.addRow(tr("settings.region_min_width"), dialog.region_min_width)
    layout.addRow(tr("settings.region_min_height"), dialog.region_min_height)
    return widget


def reset_dialog_to_defaults(dialog) -> None:
    result = QMessageBox.question(
        dialog,
        tr("settings.reset_defaults"),
        tr("settings.reset_defaults_confirm"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if result != QMessageBox.StandardButton.Yes:
        return
    dialog.parser = dialog.settings_manager.load_defaults_parser()
    dialog.settings_manager.save_parser(dialog.parser)
    dialog.settings_manager.mirror_to_storage_mode(dialog.parser, dialog.parser.get("storage", "mode", fallback="portable"))
    dialog.startup_manager.set_enabled(dialog._bool("startup", "enabled", False))
    dialog._load_values()
    if dialog.bus is not None:
        dialog.bus.publish("settings.saved", settings=dialog.settings_manager.load())


def export_dialog_settings(dialog) -> None:
    path, _filter = QFileDialog.getSaveFileName(
        dialog,
        tr("settings.export_settings"),
        "ScreenAidStudio_settings.ini",
        "INI Files (*.ini)",
    )
    if not path:
        return
    try:
        dialog.settings_manager.export_parser(dialog.parser, Path(path))
    except Exception as exc:
        QMessageBox.warning(dialog, tr("settings.export_settings"), str(exc))


def import_dialog_settings(dialog) -> None:
    path, _filter = QFileDialog.getOpenFileName(
        dialog,
        tr("settings.import_settings"),
        "",
        "INI Files (*.ini)",
    )
    if not path:
        return
    result = QMessageBox.question(
        dialog,
        tr("settings.import_settings"),
        tr("settings.import_settings_confirm"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if result != QMessageBox.StandardButton.Yes:
        return
    try:
        parser = dialog.settings_manager.load_external_parser(Path(path))
        dialog.parser = parser
        dialog.settings_manager.save_parser(parser)
        dialog.settings_manager.mirror_to_storage_mode(parser, parser.get("storage", "mode", fallback="portable"))
        dialog.startup_manager.set_enabled(dialog._bool("startup", "enabled", False))
        dialog._load_values()
        if dialog.bus is not None:
            dialog.bus.publish("settings.saved", settings=dialog.settings_manager.load())
    except Exception as exc:
        QMessageBox.warning(dialog, tr("settings.import_settings"), str(exc))
