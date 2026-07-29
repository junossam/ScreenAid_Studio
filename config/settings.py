from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    language: str
    start_minimized: bool


@dataclass(frozen=True)
class StorageSettings:
    mode: str


@dataclass(frozen=True)
class OverlaySettings:
    enabled: bool
    click_through: bool
    opacity: float


@dataclass(frozen=True)
class ClickIndicatorSettings:
    enabled: bool
    use_images: bool
    image_directory: str
    show_left: bool
    show_right: bool
    show_both: bool
    show_double: bool
    show_wheel: bool
    show_wheel_drag: bool
    radius: int
    pressed_radius: int
    image_size: int
    image_gap: int
    duration_ms: int
    fade_ms: int
    left_color: str
    right_color: str
    both_color: str
    middle_color: str
    wheel_color: str
    outline_color: str
    color: str
    width: int
    show_text: bool


@dataclass(frozen=True)
class DrawingSettings:
    enabled: bool
    default_tool: str
    pass_through_on_start: bool
    show_click_effects_while_drawing: bool
    confirm_clear_all: bool
    undo_limit: int
    color: str
    width: int
    line_style: str
    opacity: int
    smoothing: bool
    toolbar_button_size: int
    toolbar_x: int
    toolbar_y: int


@dataclass(frozen=True)
class HighlighterSettings:
    color: str
    width: int
    opacity: int
    snap_horizontal: bool


@dataclass(frozen=True)
class EraserSettings:
    mode: str
    size: int


@dataclass(frozen=True)
class CaptureSettings:
    enabled: bool
    default_mode: str
    include_annotations: bool
    include_click_effects: bool
    include_cursor: bool
    copy_to_clipboard: bool
    auto_save: bool
    open_pinned_window: bool
    image_format: str
    jpeg_quality: int
    save_directory: str
    filename_pattern: str
    show_notification: bool
    remember_last_region: bool


@dataclass(frozen=True)
class PinnedWindowSettings:
    enabled: bool
    default_zoom: float
    min_zoom: float
    max_zoom: float
    click_through: bool


@dataclass(frozen=True)
class LiveViewSettings:
    enabled: bool
    default_fps: int
    min_fps: int
    max_fps: int
    max_queue_size: int


@dataclass(frozen=True)
class StartupSettings:
    enabled: bool


@dataclass(frozen=True)
class HotkeySettings:
    values: dict[str, str]


@dataclass(frozen=True)
class CommandModeSettings:
    enabled: bool
    timeout_ms: int
    keys: dict[str, str]


@dataclass(frozen=True)
class RegionSelectionSettings:
    dark_overlay_opacity: int
    border_width: int
    show_size: bool
    show_coordinates: bool
    minimum_width: int
    minimum_height: int


@dataclass(frozen=True)
class MagnifierSettings:
    enabled: bool
    scale: float
    size: int


@dataclass(frozen=True)
class Settings:
    app: AppSettings
    storage: StorageSettings
    overlay: OverlaySettings
    click_indicator: ClickIndicatorSettings
    drawing: DrawingSettings
    highlighter: HighlighterSettings
    eraser: EraserSettings
    capture: CaptureSettings
    pinned_window: PinnedWindowSettings
    live_view: LiveViewSettings
    startup: StartupSettings
    hotkeys: HotkeySettings
    command_mode: CommandModeSettings
    region_selection: RegionSelectionSettings
    magnifier: MagnifierSettings

    @classmethod
    def load(cls, path: Path) -> "Settings":
        parser = ConfigParser()
        parser.read(path, encoding="utf-8")
        return cls(
            app=AppSettings(
                language=parser.get("app", "language", fallback="ko"),
                start_minimized=parser.getboolean("app", "start_minimized", fallback=True),
            ),
            storage=StorageSettings(
                mode=parser.get("storage", "mode", fallback="portable"),
            ),
            overlay=OverlaySettings(
                enabled=parser.getboolean("overlay", "enabled", fallback=True),
                click_through=parser.getboolean("overlay", "click_through", fallback=True),
                opacity=parser.getfloat("overlay", "opacity", fallback=1.0),
            ),
            click_indicator=ClickIndicatorSettings(
                enabled=parser.getboolean("click_indicator", "enabled", fallback=True),
                use_images=parser.getboolean("click_indicator", "use_images", fallback=True),
                image_directory=parser.get(
                    "click_indicator",
                    "image_directory",
                    fallback="resources/click_indicators",
                ),
                show_left=parser.getboolean("click_indicator", "show_left", fallback=True),
                show_right=parser.getboolean("click_indicator", "show_right", fallback=True),
                show_both=parser.getboolean("click_indicator", "show_both", fallback=True),
                show_double=parser.getboolean("click_indicator", "show_double", fallback=True),
                show_wheel=parser.getboolean("click_indicator", "show_wheel", fallback=True),
                show_wheel_drag=parser.getboolean("click_indicator", "show_wheel_drag", fallback=True),
                radius=parser.getint("click_indicator", "radius", fallback=30),
                pressed_radius=parser.getint("click_indicator", "pressed_radius", fallback=34),
                image_size=max(16, parser.getint("click_indicator", "image_size", fallback=36)),
                image_gap=max(0, parser.getint("click_indicator", "image_gap", fallback=10)),
                duration_ms=parser.getint("click_indicator", "duration_ms", fallback=220),
                fade_ms=parser.getint("click_indicator", "fade_ms", fallback=360),
                left_color=parser.get("click_indicator", "left_color", fallback="#ff3b30"),
                right_color=parser.get("click_indicator", "right_color", fallback="#0a84ff"),
                both_color=parser.get("click_indicator", "both_color", fallback="#bf5af2"),
                middle_color=parser.get("click_indicator", "middle_color", fallback="#34c759"),
                wheel_color=parser.get("click_indicator", "wheel_color", fallback="#ffcc00"),
                outline_color=parser.get("click_indicator", "outline_color", fallback="#1c1c1e"),
                color=parser.get("click_indicator", "color", fallback="#ff3b30"),
                width=parser.getint("click_indicator", "width", fallback=3),
                show_text=parser.getboolean("click_indicator", "show_text", fallback=False),
            ),
            drawing=DrawingSettings(
                enabled=parser.getboolean("drawing", "enabled", fallback=True),
                default_tool=parser.get("drawing", "default_tool", fallback="freehand"),
                pass_through_on_start=parser.getboolean("drawing", "pass_through_on_start", fallback=True),
                show_click_effects_while_drawing=parser.getboolean(
                    "drawing", "show_click_effects_while_drawing", fallback=False
                ),
                confirm_clear_all=parser.getboolean("drawing", "confirm_clear_all", fallback=False),
                undo_limit=max(1, parser.getint("drawing", "undo_limit", fallback=100)),
                color=parser.get("drawing", "color", fallback="#00a6ff"),
                width=parser.getint("drawing", "width", fallback=4),
                line_style=parser.get("drawing", "line_style", fallback="solid"),
                opacity=min(255, max(0, parser.getint("drawing", "opacity", fallback=255))),
                smoothing=parser.getboolean("drawing", "smoothing", fallback=True),
                toolbar_button_size=min(48, max(22, parser.getint("drawing", "toolbar_button_size", fallback=28))),
                toolbar_x=max(0, parser.getint("drawing", "toolbar_x", fallback=20)),
                toolbar_y=max(0, parser.getint("drawing", "toolbar_y", fallback=80)),
            ),
            highlighter=HighlighterSettings(
                color=parser.get("highlighter", "color", fallback="#ffff00"),
                width=parser.getint("highlighter", "width", fallback=24),
                opacity=min(255, max(0, parser.getint("highlighter", "opacity", fallback=90))),
                snap_horizontal=parser.getboolean("highlighter", "snap_horizontal", fallback=False),
            ),
            eraser=EraserSettings(
                mode=parser.get("eraser", "mode", fallback="object"),
                size=max(1, parser.getint("eraser", "size", fallback=24)),
            ),
            capture=CaptureSettings(
                enabled=parser.getboolean("capture", "enabled", fallback=False),
                default_mode=parser.get("capture", "default_mode", fallback="region"),
                include_annotations=parser.getboolean("capture", "include_annotations", fallback=True),
                include_click_effects=parser.getboolean("capture", "include_click_effects", fallback=False),
                include_cursor=parser.getboolean("capture", "include_cursor", fallback=False),
                copy_to_clipboard=parser.getboolean("capture", "copy_to_clipboard", fallback=True),
                auto_save=parser.getboolean("capture", "auto_save", fallback=False),
                open_pinned_window=parser.getboolean("capture", "open_pinned_window", fallback=False),
                image_format=parser.get("capture", "image_format", fallback="PNG").upper(),
                jpeg_quality=min(100, max(1, parser.getint("capture", "jpeg_quality", fallback=90))),
                save_directory=parser.get("capture", "save_directory", fallback="captures"),
                filename_pattern=parser.get(
                    "capture", "filename_pattern", fallback="ScreenAidStudio_{date}_{time}"
                ),
                show_notification=parser.getboolean("capture", "show_notification", fallback=True),
                remember_last_region=parser.getboolean("capture", "remember_last_region", fallback=True),
            ),
            pinned_window=PinnedWindowSettings(
                enabled=parser.getboolean("pinned_window", "enabled", fallback=True),
                default_zoom=max(0.1, parser.getfloat("pinned_window", "default_zoom", fallback=1.0)),
                min_zoom=max(0.1, parser.getfloat("pinned_window", "min_zoom", fallback=0.25)),
                max_zoom=max(0.1, parser.getfloat("pinned_window", "max_zoom", fallback=4.0)),
                click_through=parser.getboolean("pinned_window", "click_through", fallback=False),
            ),
            live_view=LiveViewSettings(
                enabled=parser.getboolean("live_view", "enabled", fallback=True),
                default_fps=min(30, max(1, parser.getint("live_view", "default_fps", fallback=10))),
                min_fps=min(30, max(1, parser.getint("live_view", "min_fps", fallback=1))),
                max_fps=min(30, max(1, parser.getint("live_view", "max_fps", fallback=30))),
                max_queue_size=max(1, parser.getint("live_view", "max_queue_size", fallback=1)),
            ),
            startup=StartupSettings(
                enabled=parser.getboolean("startup", "enabled", fallback=False),
            ),
            hotkeys=HotkeySettings(
                values={
                    "command_mode": parser.get("hotkeys", "command_mode", fallback="Ctrl+Alt+A"),
                    "toggle_click_effects": parser.get(
                        "hotkeys", "toggle_click_effects", fallback="Ctrl+Alt+E"
                    ),
                }
            ),
            command_mode=CommandModeSettings(
                enabled=parser.getboolean("command_mode", "enabled", fallback=True),
                timeout_ms=max(500, parser.getint("command_mode", "timeout_ms", fallback=5000)),
                keys={
                    "toggle_overlay": parser.get("command_mode", "toggle_overlay", fallback="O"),
                    "toggle_click_effects": parser.get("command_mode", "toggle_click_effects", fallback="E"),
                    "toggle_drawing": parser.get("command_mode", "toggle_drawing", fallback="D"),
                    "pass_through": parser.get("command_mode", "pass_through", fallback="P"),
                    "clear_drawing": parser.get("command_mode", "clear_drawing", fallback="C"),
                    "undo_drawing": parser.get("command_mode", "undo_drawing", fallback="Z"),
                    "redo_drawing": parser.get("command_mode", "redo_drawing", fallback="Y"),
                    "capture_region": parser.get("command_mode", "capture_region", fallback="R"),
                    "capture_last_region": parser.get("command_mode", "capture_last_region", fallback="L"),
                    "capture_monitor": parser.get("command_mode", "capture_monitor", fallback="M"),
                    "capture_virtual": parser.get("command_mode", "capture_virtual", fallback="V"),
                    "capture_window": parser.get("command_mode", "capture_window", fallback="W"),
                    "pin_region": parser.get("command_mode", "pin_region", fallback="K"),
                    "pin_last_capture": parser.get("command_mode", "pin_last_capture", fallback="B"),
                    "live_region": parser.get("command_mode", "live_region", fallback="G"),
                    "live_stop_all": parser.get("command_mode", "live_stop_all", fallback="X"),
                    "open_settings": parser.get("command_mode", "open_settings", fallback="S"),
                    "toggle_pause": parser.get("command_mode", "toggle_pause", fallback="Space"),
                },
            ),
            region_selection=RegionSelectionSettings(
                dark_overlay_opacity=min(
                    255,
                    max(0, parser.getint("region_selection", "dark_overlay_opacity", fallback=110)),
                ),
                border_width=max(1, parser.getint("region_selection", "border_width", fallback=2)),
                show_size=parser.getboolean("region_selection", "show_size", fallback=True),
                show_coordinates=parser.getboolean("region_selection", "show_coordinates", fallback=False),
                minimum_width=max(1, parser.getint("region_selection", "minimum_width", fallback=4)),
                minimum_height=max(1, parser.getint("region_selection", "minimum_height", fallback=4)),
            ),
            magnifier=MagnifierSettings(
                enabled=parser.getboolean("magnifier", "enabled", fallback=False),
                scale=parser.getfloat("magnifier", "scale", fallback=2.0),
                size=parser.getint("magnifier", "size", fallback=260),
            ),
        )
