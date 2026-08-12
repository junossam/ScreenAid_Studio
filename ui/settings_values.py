from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from core.command_mode import parse_command_key
from core.hotkeys import DEFAULT_HOTKEYS, parse_hotkey
from core.localization import tr
from ui.settings_sections import COMMAND_KEY_DEFAULTS, combo_data, set_combo_data


def load_dialog_values(dialog) -> None:
    dialog.startup_enabled.setChecked(dialog.startup_manager.is_enabled())
    language = dialog.parser.get("app", "language", fallback="ko")
    dialog.language.setCurrentIndex(max(0, dialog.language.findData(language)))
    set_combo_data(dialog.storage_mode, dialog.parser.get("storage", "mode", fallback="portable"))
    dialog.start_minimized.setChecked(dialog._bool("app", "start_minimized", False))
    dialog.overlay_enabled.setChecked(dialog._bool("overlay", "enabled", True))
    dialog.overlay_click_through.setChecked(dialog._bool("overlay", "click_through", True))
    dialog.overlay_opacity.setValue(dialog._float("overlay", "opacity", 1.0))
    _load_click(dialog)
    _load_capture(dialog)
    _load_notification(dialog)
    _load_drawing(dialog)
    _load_windows(dialog)
    _load_region_and_keys(dialog)


def save_dialog_values(dialog, close: bool) -> None:
    _save_overlay(dialog)
    _save_click(dialog)
    _save_capture(dialog)
    _save_notification(dialog)
    _save_drawing(dialog)
    _save_windows(dialog)
    _save_region_and_keys(dialog)
    dialog._set("app", "language", dialog.language.currentData() or "ko")
    dialog._set("app", "start_minimized", dialog.start_minimized.isChecked())
    dialog._set("storage", "mode", combo_data(dialog.storage_mode, "portable"))
    dialog._set("startup", "enabled", dialog.startup_enabled.isChecked())
    dialog.settings_manager.save_parser(dialog.parser)
    dialog.settings_manager.mirror_to_storage_mode(dialog.parser, combo_data(dialog.storage_mode, "portable"))
    dialog.startup_manager.set_enabled(dialog.startup_enabled.isChecked())
    if dialog.bus is not None:
        dialog.bus.publish("settings.saved", settings=dialog.settings_manager.load())
    if close:
        dialog.accept()


def _load_click(dialog) -> None:
    dialog.click_enabled.setChecked(dialog._bool("click_indicator", "enabled", True))
    dialog.show_left.setChecked(dialog._bool("click_indicator", "show_left", True))
    dialog.show_right.setChecked(dialog._bool("click_indicator", "show_right", True))
    dialog.show_both.setChecked(dialog._bool("click_indicator", "show_both", True))
    dialog.show_wheel.setChecked(dialog._bool("click_indicator", "show_wheel", True))
    dialog.show_wheel_drag.setChecked(dialog._bool("click_indicator", "show_wheel_drag", True))
    dialog.click_images.setChecked(dialog._bool("click_indicator", "use_images", True))
    dialog.show_double.setChecked(dialog._bool("click_indicator", "show_double", True))
    dialog.show_text.setChecked(dialog._bool("click_indicator", "show_text", False))
    dialog.image_size.setValue(dialog._int("click_indicator", "image_size", 36))
    dialog.image_gap.setValue(dialog._int("click_indicator", "image_gap", 10))
    dialog.click_duration.setValue(dialog._int("click_indicator", "duration_ms", 220))
    dialog.click_fade.setValue(dialog._int("click_indicator", "fade_ms", 360))
    dialog.click_radius.setValue(dialog._int("click_indicator", "radius", 30))
    dialog.click_pressed_radius.setValue(dialog._int("click_indicator", "pressed_radius", 34))
    dialog.click_outline_width.setValue(dialog._int("click_indicator", "width", 3))
    dialog.left_color.setText(dialog.parser.get("click_indicator", "left_color", fallback="#ff3b30"))
    dialog.right_color.setText(dialog.parser.get("click_indicator", "right_color", fallback="#0a84ff"))
    dialog.both_color.setText(dialog.parser.get("click_indicator", "both_color", fallback="#bf5af2"))
    dialog.middle_color.setText(dialog.parser.get("click_indicator", "middle_color", fallback="#34c759"))
    dialog.wheel_color.setText(dialog.parser.get("click_indicator", "wheel_color", fallback="#ffcc00"))
    dialog.outline_color.setText(dialog.parser.get("click_indicator", "outline_color", fallback="#1c1c1e"))
    dialog._sync_click_option_state(dialog.click_enabled.isChecked())


def _load_capture(dialog) -> None:
    dialog.capture_enabled.setChecked(dialog._bool("capture", "enabled", True))
    set_combo_data(dialog.capture_default_mode, dialog.parser.get("capture", "default_mode", fallback="region"))
    dialog.include_annotations.setChecked(dialog._bool("capture", "include_annotations", True))
    dialog.include_click_effects.setChecked(dialog._bool("capture", "include_click_effects", False))
    dialog.include_cursor.setChecked(dialog._bool("capture", "include_cursor", False))
    dialog.copy_to_clipboard.setChecked(dialog._bool("capture", "copy_to_clipboard", True))
    dialog.auto_save.setChecked(dialog._bool("capture", "auto_save", False))
    dialog.open_pinned.setChecked(dialog._bool("capture", "open_pinned_window", False))
    dialog.image_format.setCurrentText(dialog.parser.get("capture", "image_format", fallback="PNG").upper())
    dialog.jpeg_quality.setValue(dialog._int("capture", "jpeg_quality", 90))
    dialog.save_directory.setText(dialog.parser.get("capture", "save_directory", fallback="captures"))
    dialog.filename_pattern.setText(dialog.parser.get("capture", "filename_pattern", fallback="ScreenAidStudio_{date}_{time}"))
    dialog.remember_last_region.setChecked(dialog._bool("capture", "remember_last_region", True))


def _load_notification(dialog) -> None:
    dialog.notification_enabled.setChecked(dialog._bool("notification", "enabled", True))
    dialog.notification_capture_completed.setChecked(
        dialog._bool("notification", "capture_completed", dialog._bool("capture", "show_notification", True))
    )
    for key, control in (
        ("capture_failed", dialog.notification_capture_failed),
        ("hotkey_failed", dialog.notification_hotkey_failed),
        ("pin_failed", dialog.notification_pin_failed),
        ("live_failed", dialog.notification_live_failed),
        ("drawing_mode_changed", dialog.notification_drawing_mode_changed),
        ("pause_changed", dialog.notification_pause_changed),
        ("command_blocked", dialog.notification_command_blocked),
        ("click_effects_changed", dialog.notification_click_effects_changed),
        ("manual_failed", dialog.notification_manual_failed),
    ):
        control.setChecked(dialog._bool("notification", key, True))
    dialog._sync_notification_option_state(dialog.notification_enabled.isChecked())


def _load_drawing(dialog) -> None:
    dialog.drawing_enabled.setChecked(dialog._bool("drawing", "enabled", True))
    set_combo_data(dialog.default_tool, dialog.parser.get("drawing", "default_tool", fallback="freehand"))
    dialog.drawing_color.setText(dialog.parser.get("drawing", "color", fallback="#00a6ff"))
    dialog.toolbar_button_size.setValue(dialog._int("drawing", "toolbar_button_size", 28))
    dialog.drawing_width.setValue(dialog._int("drawing", "width", 4))
    set_combo_data(dialog.line_style, dialog.parser.get("drawing", "line_style", fallback="solid"))
    dialog.drawing_opacity.setValue(dialog._int("drawing", "opacity", 255))
    dialog.drawing_undo_limit.setValue(dialog._int("drawing", "undo_limit", 100))
    dialog.pass_through_on_start.setChecked(dialog._bool("drawing", "pass_through_on_start", True))
    dialog.show_click_effects_while_drawing.setChecked(dialog._bool("drawing", "show_click_effects_while_drawing", False))
    dialog.confirm_clear_all.setChecked(dialog._bool("drawing", "confirm_clear_all", False))
    dialog.drawing_smoothing.setChecked(dialog._bool("drawing", "smoothing", True))
    dialog.highlighter_color.setText(dialog.parser.get("highlighter", "color", fallback="#ffff00"))
    dialog.highlighter_width.setValue(dialog._int("highlighter", "width", 24))
    dialog.highlighter_opacity.setValue(dialog._int("highlighter", "opacity", 90))
    dialog.highlighter_snap_horizontal.setChecked(dialog._bool("highlighter", "snap_horizontal", False))
    set_combo_data(dialog.eraser_mode, dialog.parser.get("eraser", "mode", fallback="object"))
    dialog.eraser_size.setValue(dialog._int("eraser", "size", 24))


def _load_windows(dialog) -> None:
    dialog.pinned_enabled.setChecked(dialog._bool("pinned_window", "enabled", True))
    dialog.pinned_default_zoom.setValue(dialog._float("pinned_window", "default_zoom", 1.0))
    dialog.pinned_min_zoom.setValue(dialog._float("pinned_window", "min_zoom", 0.25))
    dialog.pinned_max_zoom.setValue(dialog._float("pinned_window", "max_zoom", 4.0))
    dialog.pinned_click_through.setChecked(dialog._bool("pinned_window", "click_through", False))
    dialog.live_enabled.setChecked(dialog._bool("live_view", "enabled", True))
    dialog.live_fps.setValue(dialog._int("live_view", "default_fps", 10))
    dialog.live_min_fps.setValue(dialog._int("live_view", "min_fps", 1))
    dialog.live_max_fps.setValue(dialog._int("live_view", "max_fps", 30))
    dialog.window_border_enabled.setChecked(dialog._bool("window_border", "enabled", False))
    dialog.window_border_color.setText(dialog.parser.get("window_border", "color", fallback="#00a6ff"))
    dialog.window_border_width.setValue(dialog._int("window_border", "width", 2))
    set_combo_data(dialog.window_border_style, dialog.parser.get("window_border", "style", fallback="solid"))
    dialog.magnifier_enabled.setChecked(dialog._bool("magnifier", "enabled", True))
    dialog.magnifier_scale.setValue(dialog._float("magnifier", "scale", 2.0))
    dialog.magnifier_keep_drawings.setChecked(dialog._bool("magnifier", "keep_drawings_on_close", False))
    dialog.live_zoom_enabled.setChecked(dialog._bool("live_zoom", "enabled", True))
    dialog.live_zoom_min_scale.setValue(dialog._float("live_zoom", "min_scale", 1.0))
    dialog.live_zoom_max_scale.setValue(dialog._float("live_zoom", "max_scale", 8.0))
    dialog.live_zoom_default_scale.setValue(dialog._float("live_zoom", "default_scale", 2.0))
    dialog.live_zoom_wheel_step.setValue(dialog._float("live_zoom", "wheel_step", 0.25))


def _load_region_and_keys(dialog) -> None:
    dialog.region_opacity.setValue(dialog._int("region_selection", "dark_overlay_opacity", 110))
    dialog.region_border_width.setValue(dialog._int("region_selection", "border_width", 2))
    dialog.region_show_size.setChecked(dialog._bool("region_selection", "show_size", True))
    dialog.region_show_coordinates.setChecked(dialog._bool("region_selection", "show_coordinates", False))
    dialog.region_min_width.setValue(dialog._int("region_selection", "minimum_width", 4))
    dialog.region_min_height.setValue(dialog._int("region_selection", "minimum_height", 4))
    for name, field in dialog.hotkey_fields.items():
        field.setText(dialog.parser.get("hotkeys", name, fallback=DEFAULT_HOTKEYS[name]))
    dialog.command_mode_show_hint.setChecked(dialog._bool("command_mode", "show_hint", True))
    dialog.command_mode_timeout.setValue(dialog._int("command_mode", "timeout_ms", 5000))
    for name, field in dialog.command_key_fields.items():
        field.setText(dialog.parser.get("command_mode", name, fallback=COMMAND_KEY_DEFAULTS[name]))


def _save_overlay(dialog) -> None:
    dialog._set("overlay", "enabled", dialog.overlay_enabled.isChecked())
    dialog._set("overlay", "click_through", dialog.overlay_click_through.isChecked())
    dialog._set("overlay", "opacity", dialog.overlay_opacity.value())


def _save_click(dialog) -> None:
    for key, control in (
        ("enabled", dialog.click_enabled),
        ("show_left", dialog.show_left),
        ("show_right", dialog.show_right),
        ("show_both", dialog.show_both),
        ("show_wheel", dialog.show_wheel),
        ("show_wheel_drag", dialog.show_wheel_drag),
        ("use_images", dialog.click_images),
        ("show_double", dialog.show_double),
        ("show_text", dialog.show_text),
    ):
        dialog._set("click_indicator", key, control.isChecked())
    for key, control in (
        ("image_size", dialog.image_size),
        ("image_gap", dialog.image_gap),
        ("duration_ms", dialog.click_duration),
        ("fade_ms", dialog.click_fade),
        ("radius", dialog.click_radius),
        ("pressed_radius", dialog.click_pressed_radius),
        ("width", dialog.click_outline_width),
    ):
        dialog._set("click_indicator", key, control.value())
    for key, control in (
        ("left_color", dialog.left_color),
        ("right_color", dialog.right_color),
        ("both_color", dialog.both_color),
        ("middle_color", dialog.middle_color),
        ("wheel_color", dialog.wheel_color),
        ("outline_color", dialog.outline_color),
    ):
        dialog._set("click_indicator", key, control.text().strip())


def _save_capture(dialog) -> None:
    dialog._set("capture", "enabled", dialog.capture_enabled.isChecked())
    dialog._set("capture", "default_mode", combo_data(dialog.capture_default_mode, "region"))
    for key, control in (
        ("include_annotations", dialog.include_annotations),
        ("include_click_effects", dialog.include_click_effects),
        ("include_cursor", dialog.include_cursor),
        ("copy_to_clipboard", dialog.copy_to_clipboard),
        ("auto_save", dialog.auto_save),
        ("open_pinned_window", dialog.open_pinned),
        ("remember_last_region", dialog.remember_last_region),
    ):
        dialog._set("capture", key, control.isChecked())
    dialog._set("capture", "image_format", dialog.image_format.currentText())
    dialog._set("capture", "jpeg_quality", dialog.jpeg_quality.value())
    dialog._set("capture", "save_directory", dialog.save_directory.text().strip())
    dialog._set("capture", "filename_pattern", dialog.filename_pattern.text().strip())


def _save_notification(dialog) -> None:
    for key, control in (
        ("enabled", dialog.notification_enabled),
        ("capture_completed", dialog.notification_capture_completed),
        ("capture_failed", dialog.notification_capture_failed),
        ("hotkey_failed", dialog.notification_hotkey_failed),
        ("pin_failed", dialog.notification_pin_failed),
        ("live_failed", dialog.notification_live_failed),
        ("drawing_mode_changed", dialog.notification_drawing_mode_changed),
        ("pause_changed", dialog.notification_pause_changed),
        ("command_blocked", dialog.notification_command_blocked),
        ("click_effects_changed", dialog.notification_click_effects_changed),
        ("manual_failed", dialog.notification_manual_failed),
    ):
        dialog._set("notification", key, control.isChecked())
    dialog._set("capture", "show_notification", dialog.notification_capture_completed.isChecked())


def _save_drawing(dialog) -> None:
    dialog._set("drawing", "enabled", dialog.drawing_enabled.isChecked())
    dialog._set("drawing", "default_tool", combo_data(dialog.default_tool, "freehand"))
    dialog._set("drawing", "color", dialog.drawing_color.text().strip())
    dialog._set("drawing", "toolbar_button_size", dialog.toolbar_button_size.value())
    dialog._set("drawing", "width", dialog.drawing_width.value())
    dialog._set("drawing", "line_style", combo_data(dialog.line_style, "solid"))
    dialog._set("drawing", "opacity", dialog.drawing_opacity.value())
    dialog._set("drawing", "undo_limit", dialog.drawing_undo_limit.value())
    for key, control in (
        ("pass_through_on_start", dialog.pass_through_on_start),
        ("show_click_effects_while_drawing", dialog.show_click_effects_while_drawing),
        ("confirm_clear_all", dialog.confirm_clear_all),
        ("smoothing", dialog.drawing_smoothing),
    ):
        dialog._set("drawing", key, control.isChecked())
    dialog._set("highlighter", "color", dialog.highlighter_color.text().strip())
    dialog._set("highlighter", "width", dialog.highlighter_width.value())
    dialog._set("highlighter", "opacity", dialog.highlighter_opacity.value())
    dialog._set("highlighter", "snap_horizontal", dialog.highlighter_snap_horizontal.isChecked())
    dialog._set("eraser", "mode", combo_data(dialog.eraser_mode, "object"))
    dialog._set("eraser", "size", dialog.eraser_size.value())


def _save_windows(dialog) -> None:
    dialog._set("pinned_window", "enabled", dialog.pinned_enabled.isChecked())
    dialog._set("pinned_window", "default_zoom", dialog.pinned_default_zoom.value())
    dialog._set("pinned_window", "min_zoom", dialog.pinned_min_zoom.value())
    dialog._set("pinned_window", "max_zoom", dialog.pinned_max_zoom.value())
    dialog._set("pinned_window", "click_through", dialog.pinned_click_through.isChecked())
    dialog._set("live_view", "enabled", dialog.live_enabled.isChecked())
    dialog._set("live_view", "default_fps", dialog.live_fps.value())
    min_fps, max_fps = _resolve_fps_range(dialog)
    dialog._set("live_view", "min_fps", min_fps)
    dialog._set("live_view", "max_fps", max_fps)
    dialog._set("window_border", "enabled", dialog.window_border_enabled.isChecked())
    dialog._set("window_border", "color", dialog.window_border_color.text().strip())
    dialog._set("window_border", "width", dialog.window_border_width.value())
    dialog._set("window_border", "style", combo_data(dialog.window_border_style, "solid"))
    dialog._set("magnifier", "enabled", dialog.magnifier_enabled.isChecked())
    dialog._set("magnifier", "scale", dialog.magnifier_scale.value())
    dialog._set("magnifier", "keep_drawings_on_close", dialog.magnifier_keep_drawings.isChecked())
    dialog._set("live_zoom", "enabled", dialog.live_zoom_enabled.isChecked())
    dialog._set("live_zoom", "min_scale", dialog.live_zoom_min_scale.value())
    dialog._set("live_zoom", "max_scale", dialog.live_zoom_max_scale.value())
    dialog._set("live_zoom", "default_scale", dialog.live_zoom_default_scale.value())
    dialog._set("live_zoom", "wheel_step", dialog.live_zoom_wheel_step.value())


def _resolve_fps_range(dialog) -> tuple[int, int]:
    min_fps = dialog.live_min_fps.value()
    max_fps = dialog.live_max_fps.value()
    if min_fps > max_fps:
        min_fps, max_fps = max_fps, min_fps
        dialog.live_min_fps.setValue(min_fps)
        dialog.live_max_fps.setValue(max_fps)
        QMessageBox.warning(dialog, tr("settings.title"), tr("settings.fps_range_swapped"))
    return min_fps, max_fps


def _save_region_and_keys(dialog) -> None:
    dialog._set("region_selection", "dark_overlay_opacity", dialog.region_opacity.value())
    dialog._set("region_selection", "border_width", dialog.region_border_width.value())
    dialog._set("region_selection", "show_size", dialog.region_show_size.isChecked())
    dialog._set("region_selection", "show_coordinates", dialog.region_show_coordinates.isChecked())
    dialog._set("region_selection", "minimum_width", dialog.region_min_width.value())
    dialog._set("region_selection", "minimum_height", dialog.region_min_height.value())
    invalid_hotkeys = _save_hotkey_fields(dialog)
    dialog._set("command_mode", "enabled", True)
    dialog._set("command_mode", "show_hint", dialog.command_mode_show_hint.isChecked())
    dialog._set("command_mode", "timeout_ms", dialog.command_mode_timeout.value())
    invalid_command_keys, duplicate_command_keys = _save_command_key_fields(dialog)
    _warn_about_rejected_keys(dialog, invalid_hotkeys, invalid_command_keys, duplicate_command_keys)


def _save_hotkey_fields(dialog) -> list[str]:
    invalid = []
    for name, field in dialog.hotkey_fields.items():
        text = field.text().strip()
        if parse_hotkey(text) is None:
            invalid.append(name)
            text = dialog.parser.get("hotkeys", name, fallback=DEFAULT_HOTKEYS[name])
            field.setText(text)
        dialog._set("hotkeys", name, text)
    return invalid


def _save_command_key_fields(dialog) -> tuple[list[str], list[str]]:
    entered = {name: field.text().strip() for name, field in dialog.command_key_fields.items()}
    parsed_vk: dict[str, int] = {}
    invalid: list[str] = []
    for name, text in entered.items():
        vk = parse_command_key(text)
        if vk is None:
            invalid.append(name)
        else:
            parsed_vk[name] = vk

    vk_counts: dict[int, int] = {}
    for vk in parsed_vk.values():
        vk_counts[vk] = vk_counts.get(vk, 0) + 1
    duplicates = [name for name, vk in parsed_vk.items() if vk_counts[vk] > 1]

    for name, field in dialog.command_key_fields.items():
        if name in invalid or name in duplicates:
            text = dialog.parser.get("command_mode", name, fallback=COMMAND_KEY_DEFAULTS[name])
            field.setText(text)
        else:
            text = entered[name]
        dialog._set("command_mode", name, text)
    return invalid, duplicates


def _warn_about_rejected_keys(
    dialog,
    invalid_hotkeys: list[str],
    invalid_command_keys: list[str],
    duplicate_command_keys: list[str],
) -> None:
    if not (invalid_hotkeys or invalid_command_keys or duplicate_command_keys):
        return
    lines = []
    if invalid_hotkeys:
        names = ", ".join(tr(f"hotkey.{name}") for name in invalid_hotkeys)
        lines.append(f"{tr('settings.invalid_hotkeys')}: {names}")
    if invalid_command_keys:
        names = ", ".join(tr(f"hotkey.{name}") for name in invalid_command_keys)
        lines.append(f"{tr('settings.invalid_command_keys')}: {names}")
    if duplicate_command_keys:
        names = ", ".join(tr(f"hotkey.{name}") for name in duplicate_command_keys)
        lines.append(f"{tr('settings.duplicate_command_keys')}: {names}")
    QMessageBox.warning(dialog, tr("settings.title"), "\n".join(lines))
