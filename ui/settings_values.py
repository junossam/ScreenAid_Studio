from __future__ import annotations

from core.hotkeys import DEFAULT_HOTKEYS
from ui.settings_sections import COMMAND_KEY_DEFAULTS, combo_data, set_combo_data


def load_dialog_values(dialog) -> None:
    dialog.startup_enabled.setChecked(dialog.startup_manager.is_enabled())
    language = dialog.parser.get("app", "language", fallback="ko")
    dialog.language.setCurrentIndex(max(0, dialog.language.findData(language)))
    set_combo_data(dialog.storage_mode, dialog.parser.get("storage", "mode", fallback="portable"))
    dialog.overlay_enabled.setChecked(dialog._bool("overlay", "enabled", True))
    dialog.overlay_click_through.setChecked(dialog._bool("overlay", "click_through", True))
    dialog.overlay_opacity.setValue(dialog._float("overlay", "opacity", 1.0))
    _load_click(dialog)
    _load_capture(dialog)
    _load_drawing(dialog)
    _load_windows(dialog)
    _load_region_and_keys(dialog)


def save_dialog_values(dialog, close: bool) -> None:
    _save_overlay(dialog)
    _save_click(dialog)
    _save_capture(dialog)
    _save_drawing(dialog)
    _save_windows(dialog)
    _save_region_and_keys(dialog)
    dialog._set("app", "language", dialog.language.currentData() or "ko")
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
    dialog.show_notification.setChecked(dialog._bool("capture", "show_notification", True))
    dialog.remember_last_region.setChecked(dialog._bool("capture", "remember_last_region", True))


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
    dialog.live_queue_size.setValue(dialog._int("live_view", "max_queue_size", 1))


def _load_region_and_keys(dialog) -> None:
    dialog.region_opacity.setValue(dialog._int("region_selection", "dark_overlay_opacity", 110))
    dialog.region_border_width.setValue(dialog._int("region_selection", "border_width", 2))
    dialog.region_show_size.setChecked(dialog._bool("region_selection", "show_size", True))
    dialog.region_show_coordinates.setChecked(dialog._bool("region_selection", "show_coordinates", False))
    dialog.region_min_width.setValue(dialog._int("region_selection", "minimum_width", 4))
    dialog.region_min_height.setValue(dialog._int("region_selection", "minimum_height", 4))
    for name, field in dialog.hotkey_fields.items():
        field.setText(dialog.parser.get("hotkeys", name, fallback=DEFAULT_HOTKEYS[name]))
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
        ("show_notification", dialog.show_notification),
        ("remember_last_region", dialog.remember_last_region),
    ):
        dialog._set("capture", key, control.isChecked())
    dialog._set("capture", "image_format", dialog.image_format.currentText())
    dialog._set("capture", "jpeg_quality", dialog.jpeg_quality.value())
    dialog._set("capture", "save_directory", dialog.save_directory.text().strip())
    dialog._set("capture", "filename_pattern", dialog.filename_pattern.text().strip())


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
    dialog._set("live_view", "min_fps", dialog.live_min_fps.value())
    dialog._set("live_view", "max_fps", dialog.live_max_fps.value())
    dialog._set("live_view", "max_queue_size", 1)


def _save_region_and_keys(dialog) -> None:
    dialog._set("region_selection", "dark_overlay_opacity", dialog.region_opacity.value())
    dialog._set("region_selection", "border_width", dialog.region_border_width.value())
    dialog._set("region_selection", "show_size", dialog.region_show_size.isChecked())
    dialog._set("region_selection", "show_coordinates", dialog.region_show_coordinates.isChecked())
    dialog._set("region_selection", "minimum_width", dialog.region_min_width.value())
    dialog._set("region_selection", "minimum_height", dialog.region_min_height.value())
    for name, field in dialog.hotkey_fields.items():
        dialog._set("hotkeys", name, field.text().strip())
    dialog._set("command_mode", "enabled", True)
    dialog._set("command_mode", "timeout_ms", dialog.command_mode_timeout.value())
    for name, field in dialog.command_key_fields.items():
        dialog._set("command_mode", name, field.text().strip())
