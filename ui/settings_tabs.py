from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.localization import available_languages, tr
from ui.settings_sections import (
    CAPTURE_MODE_OPTIONS,
    DRAWING_TOOL_OPTIONS,
    ERASER_MODE_OPTIONS,
    LINE_STYLE_OPTIONS,
    STORAGE_MODE_OPTIONS,
    add_translated_items,
)


def build_general_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.language = QComboBox()
    for language in available_languages(dialog.locales_dir):
        dialog.language.addItem(language.name, language.code)
    dialog.storage_mode = QComboBox()
    add_translated_items(dialog.storage_mode, "storage", STORAGE_MODE_OPTIONS)
    dialog.start_minimized = QCheckBox()
    dialog.startup_enabled = QCheckBox()
    layout.addRow(tr("settings.language"), dialog.language)
    layout.addRow(tr("settings.storage_mode"), dialog.storage_mode)
    layout.addRow(tr("settings.start_minimized"), dialog.start_minimized)
    layout.addRow(tr("settings.start_with_windows"), dialog.startup_enabled)
    return widget


def build_overlay_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    description = QLabel(tr("settings.overlay_description"))
    description.setWordWrap(True)
    description.setStyleSheet("QLabel { color: #555; padding-bottom: 6px; }")
    dialog.overlay_enabled = QCheckBox()
    dialog.overlay_click_through = QCheckBox()
    dialog.overlay_opacity = dialog._double_spin(0.1, 1.0, 0.05)
    layout.addRow(description)
    layout.addRow(tr("settings.enable_overlay"), dialog.overlay_enabled)
    layout.addRow(tr("settings.overlay_click_through"), dialog.overlay_click_through)
    layout.addRow(tr("settings.overlay_opacity"), dialog.overlay_opacity)
    return widget


def build_click_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.click_enabled = QCheckBox()
    dialog.show_left = QCheckBox()
    dialog.show_right = QCheckBox()
    dialog.show_both = QCheckBox()
    dialog.show_wheel = QCheckBox()
    dialog.show_wheel_drag = QCheckBox()
    dialog.click_images = QCheckBox()
    dialog.show_double = QCheckBox()
    dialog.show_text = QCheckBox()
    dialog.image_size = dialog._spin(16, 128)
    dialog.image_gap = dialog._spin(0, 80)
    dialog.click_duration = dialog._spin(50, 3000)
    dialog.click_fade = dialog._spin(0, 3000)
    dialog.click_radius = dialog._spin(4, 160)
    dialog.click_pressed_radius = dialog._spin(4, 180)
    dialog.click_outline_width = dialog._spin(1, 20)
    dialog.left_color = QLineEdit()
    dialog.right_color = QLineEdit()
    dialog.both_color = QLineEdit()
    dialog.middle_color = QLineEdit()
    dialog.wheel_color = QLineEdit()
    dialog.outline_color = QLineEdit()
    layout.addRow(tr("settings.enable_click_indicator"), dialog.click_enabled)
    layout.addRow(_click_indicator_group(dialog))
    layout.addRow(tr("settings.use_png_images"), dialog.click_images)
    layout.addRow(tr("settings.show_click_text"), dialog.show_text)
    layout.addRow(tr("settings.image_size"), dialog.image_size)
    layout.addRow(tr("settings.image_gap"), dialog.image_gap)
    layout.addRow(tr("settings.click_duration"), dialog.click_duration)
    layout.addRow(tr("settings.click_fade"), dialog.click_fade)
    layout.addRow(tr("settings.click_radius"), dialog.click_radius)
    layout.addRow(tr("settings.click_pressed_radius"), dialog.click_pressed_radius)
    layout.addRow(tr("settings.click_outline_width"), dialog.click_outline_width)
    layout.addRow(_click_color_group(dialog))
    dialog.click_enabled.toggled.connect(dialog._sync_click_option_state)
    return widget


def build_capture_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.capture_enabled = QCheckBox()
    dialog.capture_default_mode = QComboBox()
    add_translated_items(dialog.capture_default_mode, "capture_mode", CAPTURE_MODE_OPTIONS)
    dialog.include_annotations = QCheckBox()
    dialog.include_click_effects = QCheckBox()
    dialog.include_cursor = QCheckBox()
    dialog.copy_to_clipboard = QCheckBox()
    dialog.auto_save = QCheckBox()
    dialog.open_pinned = QCheckBox()
    dialog.image_format = QComboBox()
    dialog.image_format.addItems(["PNG", "JPEG", "BMP"])
    dialog.jpeg_quality = dialog._spin(1, 100)
    dialog.save_directory = QLineEdit()
    dialog.filename_pattern = QLineEdit()
    dialog.remember_last_region = QCheckBox()
    for label, control in (
        ("settings.enable_capture", dialog.capture_enabled),
        ("settings.default_capture_mode", dialog.capture_default_mode),
        ("settings.include_annotations", dialog.include_annotations),
        ("settings.include_click_effects", dialog.include_click_effects),
        ("settings.include_cursor", dialog.include_cursor),
        ("settings.copy_to_clipboard", dialog.copy_to_clipboard),
        ("settings.auto_save_png", dialog.auto_save),
        ("settings.open_pinned_after_capture", dialog.open_pinned),
        ("settings.image_format", dialog.image_format),
        ("settings.jpeg_quality", dialog.jpeg_quality),
        ("settings.save_directory", dialog.save_directory),
        ("settings.filename_pattern", dialog.filename_pattern),
        ("settings.remember_last_region", dialog.remember_last_region),
    ):
        layout.addRow(tr(label), control)
    return widget


def build_notification_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.notification_enabled = QCheckBox()
    dialog.notification_capture_completed = QCheckBox()
    dialog.notification_capture_failed = QCheckBox()
    dialog.notification_hotkey_failed = QCheckBox()
    dialog.notification_pin_failed = QCheckBox()
    dialog.notification_live_failed = QCheckBox()
    dialog.notification_drawing_mode_changed = QCheckBox()
    dialog.notification_pause_changed = QCheckBox()
    dialog.notification_command_blocked = QCheckBox()
    dialog.notification_click_effects_changed = QCheckBox()
    dialog.notification_manual_failed = QCheckBox()
    layout.addRow(tr("settings.notification_enabled"), dialog.notification_enabled)
    for label, control in (
        ("settings.notification_capture_completed", dialog.notification_capture_completed),
        ("settings.notification_capture_failed", dialog.notification_capture_failed),
        ("settings.notification_hotkey_failed", dialog.notification_hotkey_failed),
        ("settings.notification_pin_failed", dialog.notification_pin_failed),
        ("settings.notification_live_failed", dialog.notification_live_failed),
        ("settings.notification_drawing_mode_changed", dialog.notification_drawing_mode_changed),
        ("settings.notification_pause_changed", dialog.notification_pause_changed),
        ("settings.notification_command_blocked", dialog.notification_command_blocked),
        ("settings.notification_click_effects_changed", dialog.notification_click_effects_changed),
        ("settings.notification_manual_failed", dialog.notification_manual_failed),
    ):
        layout.addRow(tr(label), control)
    dialog.notification_enabled.toggled.connect(dialog._sync_notification_option_state)
    return widget


def build_drawing_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.drawing_enabled = QCheckBox()
    dialog.default_tool = QComboBox()
    add_translated_items(dialog.default_tool, "tool", DRAWING_TOOL_OPTIONS)
    dialog.drawing_width = dialog._spin(1, 64)
    dialog.line_style = QComboBox()
    add_translated_items(dialog.line_style, "line_style", LINE_STYLE_OPTIONS)
    dialog.drawing_color = QLineEdit()
    dialog.toolbar_button_size = dialog._spin(22, 48)
    dialog.drawing_opacity = dialog._spin(0, 255)
    dialog.drawing_undo_limit = dialog._spin(1, 1000)
    dialog.pass_through_on_start = QCheckBox()
    dialog.show_click_effects_while_drawing = QCheckBox()
    dialog.confirm_clear_all = QCheckBox()
    dialog.drawing_smoothing = QCheckBox()
    dialog.highlighter_color = QLineEdit()
    dialog.highlighter_width = dialog._spin(1, 96)
    dialog.highlighter_opacity = dialog._spin(0, 255)
    dialog.highlighter_snap_horizontal = QCheckBox()
    dialog.eraser_mode = QComboBox()
    add_translated_items(dialog.eraser_mode, "eraser_mode", ERASER_MODE_OPTIONS)
    dialog.eraser_size = dialog._spin(1, 128)
    for label, control in (
        ("settings.enable_drawing", dialog.drawing_enabled),
        ("settings.default_tool", dialog.default_tool),
        ("settings.drawing_color", dialog.drawing_color),
        ("settings.toolbar_button_size", dialog.toolbar_button_size),
        ("settings.stroke_width", dialog.drawing_width),
        ("settings.line_style", dialog.line_style),
        ("settings.drawing_opacity", dialog.drawing_opacity),
        ("settings.undo_limit", dialog.drawing_undo_limit),
        ("settings.pass_through_on_start", dialog.pass_through_on_start),
        ("settings.show_click_effects_while_drawing", dialog.show_click_effects_while_drawing),
        ("settings.confirm_clear_all", dialog.confirm_clear_all),
        ("settings.smoothing", dialog.drawing_smoothing),
        ("settings.highlighter_color", dialog.highlighter_color),
        ("settings.highlighter_width", dialog.highlighter_width),
        ("settings.highlighter_opacity", dialog.highlighter_opacity),
        ("settings.highlighter_snap_horizontal", dialog.highlighter_snap_horizontal),
        ("settings.eraser_mode", dialog.eraser_mode),
        ("settings.eraser_size", dialog.eraser_size),
    ):
        layout.addRow(tr(label), control)
    return widget


def build_pinned_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.pinned_enabled = QCheckBox()
    dialog.pinned_default_zoom = dialog._double_spin(0.1, 8.0, 0.05)
    dialog.pinned_min_zoom = dialog._double_spin(0.1, 8.0, 0.05)
    dialog.pinned_max_zoom = dialog._double_spin(0.1, 8.0, 0.05)
    dialog.pinned_click_through = QCheckBox()
    layout.addRow(tr("settings.enable_pinned_window"), dialog.pinned_enabled)
    layout.addRow(tr("settings.default_zoom"), dialog.pinned_default_zoom)
    layout.addRow(tr("settings.min_zoom"), dialog.pinned_min_zoom)
    layout.addRow(tr("settings.max_zoom"), dialog.pinned_max_zoom)
    layout.addRow(tr("settings.pinned_click_through"), dialog.pinned_click_through)
    return widget


def build_live_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.live_enabled = QCheckBox()
    dialog.live_fps = dialog._spin(1, 30)
    dialog.live_min_fps = dialog._spin(1, 30)
    dialog.live_max_fps = dialog._spin(1, 30)
    layout.addRow(tr("settings.enable_live_view"), dialog.live_enabled)
    layout.addRow(tr("settings.default_fps"), dialog.live_fps)
    layout.addRow(tr("settings.min_fps"), dialog.live_min_fps)
    layout.addRow(tr("settings.max_fps"), dialog.live_max_fps)
    return widget


def build_magnifier_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QFormLayout(widget)
    dialog.magnifier_enabled = QCheckBox()
    dialog.magnifier_scale = dialog._double_spin(1.1, 5.0, 0.1)
    dialog.magnifier_keep_drawings = QCheckBox()
    layout.addRow(tr("settings.enable_magnifier"), dialog.magnifier_enabled)
    layout.addRow(tr("settings.magnifier_scale"), dialog.magnifier_scale)
    layout.addRow(tr("settings.magnifier_keep_drawings"), dialog.magnifier_keep_drawings)
    return widget


def build_about_tab(dialog) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)
    for title_key, value_key in (
        ("settings.about_name", "settings.about_name_value"),
        ("settings.about_version", "settings.about_version_value"),
        ("settings.about_copyright", "settings.about_copyright_value"),
        ("settings.about_license", "settings.about_license_value"),
        ("settings.about_usage", "settings.about_usage_value"),
        ("settings.about_ai", "settings.about_ai_value"),
        ("settings.about_github", "settings.about_github_value"),
        ("settings.about_site", "settings.about_site_value"),
    ):
        label = QLabel(f"<b>{tr(title_key)}</b><br>{tr(value_key)}")
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        layout.addWidget(label)
    manual_button = QPushButton(tr("settings.open_user_manual"))
    manual_button.clicked.connect(lambda: dialog.bus.publish("manual.open") if dialog.bus is not None else None)
    layout.addWidget(manual_button)
    layout.addStretch(1)
    return widget


def _click_indicator_group(dialog) -> QGroupBox:
    group = QGroupBox(tr("settings.click_indicator_options"))
    grid = QGridLayout(group)
    options = (
        (tr("settings.show_left_click"), dialog.show_left),
        (tr("settings.show_right_click"), dialog.show_right),
        (tr("settings.show_both_click"), dialog.show_both),
        (tr("settings.show_wheel"), dialog.show_wheel),
        (tr("settings.show_wheel_drag"), dialog.show_wheel_drag),
        (tr("settings.show_double_click"), dialog.show_double),
    )
    for index, (label, checkbox) in enumerate(options):
        checkbox.setText(label)
        grid.addWidget(checkbox, index // 2, index % 2)
    return group


def _click_color_group(dialog) -> QGroupBox:
    group = QGroupBox(tr("settings.click_colors"))
    layout = QFormLayout(group)
    layout.addRow(tr("settings.left_color"), dialog.left_color)
    layout.addRow(tr("settings.right_color"), dialog.right_color)
    layout.addRow(tr("settings.both_color"), dialog.both_color)
    layout.addRow(tr("settings.middle_color"), dialog.middle_color)
    layout.addRow(tr("settings.wheel_color"), dialog.wheel_color)
    layout.addRow(tr("settings.outline_color"), dialog.outline_color)
    return group
