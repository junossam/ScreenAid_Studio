from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QMenu, QToolButton, QWidget

from core.drawing_shortcuts import (
    STAMP_NAMES,
    TOOL_ACTIONS,
    next_eraser_mode,
    next_stamp_tool,
    next_width,
    with_shortcut,
)
from core.localization import tr
from ui.floating_tool_window import FloatingToolWindow, ToolDragHandle
from ui.toolbar_metrics import toolbar_metrics, toolbar_style
from ui.tool_icons import command_icon, line_style_icon, stamp_icon, swatch_icon, tool_icon, width_icon


class AnnotationToolbar(FloatingToolWindow):
    TOOLS = (
        ("freehand", "tool.freehand"),
        ("highlighter", "tool.highlighter"),
        ("line", "tool.line"),
        ("arrow", "tool.arrow"),
        ("rectangle", "tool.rectangle"),
        ("ellipse", "tool.ellipse"),
        ("stamp_star", "tool.stamp"),
        ("eraser", "tool.eraser"),
    )
    COLORS = ("#ff3b30", "#ffcc00", "#34c759", "#0a84ff", "#ffffff", "#1c1c1e")
    WIDTHS = (2, 4, 8, 14)
    LINE_STYLES = ("solid", "dash", "dot", "dashdot")

    def __init__(
        self,
        parent: QWidget,
        current_tool: str,
        current_color: str,
        current_width: int,
        current_line_style: str,
        on_tool_selected: Callable[[str], None],
        on_style_changed: Callable[[str, int, str], None],
        on_undo: Callable[[], None],
        on_redo: Callable[[], None],
        on_clear: Callable[[], None],
        on_done: Callable[[], None],
        toolbar_button_size: int = 28,
        current_eraser_mode: str = "object",
        on_eraser_mode_changed: Callable[[str], None] | None = None,
        shortcut_keys: dict[str, str] | None = None,
        on_key_pressed: Callable[[object], bool] | None = None,
    ) -> None:
        super().__init__()
        self._owner = parent
        self.setWindowTitle(tr("annotation_toolbar.title"))
        self._current_tool = current_tool
        self._color = current_color
        self._width = current_width
        self._line_style = current_line_style
        self._eraser_mode = current_eraser_mode
        self._on_tool_selected = on_tool_selected
        self._on_style_changed = on_style_changed
        self._on_eraser_mode_changed = on_eraser_mode_changed
        self._toolbar_button_size = toolbar_button_size
        self._shortcut_keys = dict(shortcut_keys or {})
        self._on_key_pressed = on_key_pressed
        self._color_actions: list = []
        self._buttons: dict[str, QToolButton] = {}
        self._color_button = QToolButton(self)
        self._width_button = QToolButton(self)
        self._style_button = QToolButton(self)
        self._stamp_button: QToolButton | None = None
        self._eraser_button: QToolButton | None = None
        self._undo_button = QToolButton(self)
        self._redo_button = QToolButton(self)
        self._clear_button = QToolButton(self)
        self._done_button = QToolButton(self)
        self._build(on_undo, on_redo, on_clear, on_done)
        self.set_visible(False)

    def set_visible(self, visible: bool) -> None:
        self.setVisible(visible)
        if visible:
            self.raise_()

    def set_current_tool(self, tool: str) -> None:
        self._current_tool = tool
        for name, button in self._buttons.items():
            button.setChecked(self._button_key(tool) == name)
        if self._stamp_button is not None:
            self._stamp_button.setIcon(stamp_icon(self._stamp_name(tool)))

    def apply_tool_shortcut(self, tool: str) -> None:
        # Repeating the stamp or eraser key cycles stamp types / eraser modes.
        if tool == "stamp_star":
            self._select_tool(next_stamp_tool(self._current_tool))
        elif tool == "eraser" and self._current_tool == "eraser":
            self._select_eraser_mode(next_eraser_mode(self._eraser_mode))
        else:
            self._select_tool(tool)

    def select_color_index(self, index: int) -> None:
        if 0 <= index < len(self.COLORS):
            self._select_color(self.COLORS[index])

    def step_width(self, step: int) -> None:
        target = next_width(self.WIDTHS, self._width, step)
        if target != self._width:
            self._select_width(target)

    def set_shortcut_keys(self, keys: dict[str, str]) -> None:
        self._shortcut_keys = dict(keys)
        self._apply_shortcut_hints()

    def keyPressEvent(self, event) -> None:
        # Keys typed while this toolbar has focus belong to its pinned window.
        if self._on_key_pressed is not None and self._on_key_pressed(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def set_action_state(self, can_undo: bool, can_redo: bool, can_clear: bool | None = None) -> None:
        self._undo_button.setEnabled(can_undo)
        self._redo_button.setEnabled(can_redo)
        self._clear_button.setEnabled(can_undo if can_clear is None else can_clear)

    def _build(
        self,
        on_undo: Callable[[], None],
        on_redo: Callable[[], None],
        on_clear: Callable[[], None],
        on_done: Callable[[], None],
    ) -> None:
        layout = QHBoxLayout(self)
        self._layout = layout
        layout.addWidget(ToolDragHandle(self))
        group = QButtonGroup(self)
        group.setExclusive(True)
        for tool, label in self.TOOLS:
            button = QToolButton(self)
            button.setIcon(tool_icon(tool))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setToolTip(tr(label))
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=tool: self._select_tool(value))
            if tool == "stamp_star":
                self._stamp_button = button
                button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
                button.setMenu(self._stamp_menu())
            elif tool == "eraser":
                self._eraser_button = button
                button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
                button.setMenu(self._eraser_menu())
            group.addButton(button)
            layout.addWidget(button)
            self._buttons[tool] = button
        layout.addSpacing(6)
        self._add_popup_button(layout, self._color_button, tr("tool.color"), self._color_menu())
        layout.addSpacing(6)
        self._add_popup_button(layout, self._width_button, tr("tool.stroke_width"), self._width_menu())
        layout.addSpacing(6)
        self._add_popup_button(layout, self._style_button, tr("tool.line_style"), self._line_style_menu())
        layout.addSpacing(6)
        for button, tooltip, icon_name, callback in (
            (self._undo_button, tr("annotation.undo"), "undo", on_undo),
            (self._redo_button, tr("annotation.redo"), "redo", on_redo),
            (self._clear_button, tr("annotation.clear"), "clear", on_clear),
            (self._done_button, tr("annotation.done"), "done", on_done),
        ):
            button.setIcon(command_icon(icon_name))
            button.setToolTip(tooltip)
            button.clicked.connect(callback)
            layout.addWidget(button)
        self._apply_shortcut_hints()
        self.apply_toolbar_size(self._toolbar_button_size)
        self.set_current_tool(self._current_tool)
        self._sync_style_buttons()
        self.set_action_state(can_undo=False, can_redo=False)

    def _select_tool(self, tool: str) -> None:
        self.set_current_tool(tool)
        self._on_tool_selected(tool)

    def _select_color(self, color: str) -> None:
        self._color = color
        self._sync_style_buttons()
        self._on_style_changed(self._color, self._width, self._line_style)

    def _select_width(self, width: int) -> None:
        self._width = width
        self._sync_style_buttons()
        self._on_style_changed(self._color, self._width, self._line_style)

    def _select_line_style(self, line_style: str) -> None:
        self._line_style = line_style
        self._sync_style_buttons()
        self._on_style_changed(self._color, self._width, self._line_style)

    def _select_eraser_mode(self, mode: str) -> None:
        self._eraser_mode = mode
        self._sync_style_buttons()
        self._select_tool("eraser")
        if self._on_eraser_mode_changed is not None:
            self._on_eraser_mode_changed(mode)

    def _sync_style_buttons(self) -> None:
        self._color_button.setIcon(swatch_icon(self._color))
        self._width_button.setIcon(width_icon(self._width))
        self._style_button.setIcon(line_style_icon(self._line_style))
        if self._eraser_button is not None:
            self._eraser_button.setToolTip(self._key_hint(tr(f"eraser_mode.{self._eraser_mode}"), "tool_eraser"))

    def _key_hint(self, text: str, action: str) -> str:
        return with_shortcut(text, self._shortcut_keys.get(action, ""))

    def _apply_shortcut_hints(self) -> None:
        for tool, label in self.TOOLS:
            if tool != "eraser":
                self._buttons[tool].setToolTip(self._key_hint(tr(label), TOOL_ACTIONS[tool]))
        for index, action in enumerate(self._color_actions):
            key = self._shortcut_keys.get(f"color_{index + 1}", "").strip()
            action.setText(f"{self.COLORS[index]}\t{key}" if key else self.COLORS[index])
        width_keys = " / ".join(
            key for key in (self._shortcut_keys.get(name, "").strip() for name in ("width_down", "width_up")) if key
        )
        self._width_button.setToolTip(with_shortcut(tr("tool.stroke_width"), width_keys))
        self._undo_button.setToolTip(self._key_hint(tr("annotation.undo"), "undo"))
        self._redo_button.setToolTip(self._key_hint(tr("annotation.redo"), "redo"))
        self._clear_button.setToolTip(self._key_hint(tr("annotation.clear"), "clear"))
        self._done_button.setToolTip(with_shortcut(tr("annotation.done"), "Esc"))
        self._sync_style_buttons()

    def _add_popup_button(self, layout: QHBoxLayout, button: QToolButton, tooltip: str, menu: QMenu) -> None:
        button.setToolTip(tooltip)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(menu)
        layout.addWidget(button)
        self._sync_style_buttons()

    def apply_toolbar_size(self, button_size: int) -> None:
        self._toolbar_button_size = button_size
        metrics = toolbar_metrics(button_size)
        self.setStyleSheet(toolbar_style(button_size))
        self._layout.setContentsMargins(metrics.margin_x, metrics.margin_y, metrics.margin_x, metrics.margin_y)
        self._layout.setSpacing(metrics.spacing)
        for button in self.findChildren(QToolButton):
            button.setIconSize(metrics.icon_size)
        self.adjustSize()

    def _color_menu(self) -> QMenu:
        menu = QMenu(self)
        for color in self.COLORS:
            action = menu.addAction(swatch_icon(color), color)
            action.triggered.connect(lambda _checked=False, value=color: self._select_color(value))
            self._color_actions.append(action)
        return menu

    def _width_menu(self) -> QMenu:
        menu = QMenu(self)
        for width in self.WIDTHS:
            action = menu.addAction(width_icon(width), str(width))
            action.triggered.connect(lambda _checked=False, value=width: self._select_width(value))
        return menu

    def _line_style_menu(self) -> QMenu:
        menu = QMenu(self)
        for line_style in self.LINE_STYLES:
            action = menu.addAction(line_style_icon(line_style), line_style)
            action.triggered.connect(lambda _checked=False, value=line_style: self._select_line_style(value))
        return menu

    def _stamp_menu(self) -> QMenu:
        menu = QMenu(self)
        for stamp in STAMP_NAMES:
            action = menu.addAction(stamp_icon(stamp), tr(f"stamp.{stamp}"))
            action.triggered.connect(lambda _checked=False, value=stamp: self._select_tool(f"stamp_{value}"))
        return menu

    def _eraser_menu(self) -> QMenu:
        menu = QMenu(self)
        for mode in ("object", "pixel"):
            action = menu.addAction(tr(f"eraser_mode.{mode}"))
            action.triggered.connect(lambda _checked=False, value=mode: self._select_eraser_mode(value))
        return menu

    def _button_key(self, tool: str) -> str:
        return "stamp_star" if tool.startswith("stamp_") else tool

    def _stamp_name(self, tool: str) -> str:
        return tool.removeprefix("stamp_") if tool.startswith("stamp_") else "star"
