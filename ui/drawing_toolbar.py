from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QMenu, QToolButton, QWidget

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId
from core.event_bus import Event, EventBus, Subscription
from core.localization import tr
from core.service import Service
from config.settings import Settings
from overlay.coordinates import ScreenCoordinateMapper
from ui.floating_tool_window import FloatingToolWindow, ToolDragHandle
from ui.toolbar_metrics import toolbar_metrics, toolbar_style
from ui.tool_icons import command_icon, line_style_icon, stamp_icon, swatch_icon, tool_icon, width_icon


class DrawingToolbar(Service):
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
        bus: EventBus,
        dispatcher: CommandDispatcher,
        default_tool: str,
        default_color: str,
        default_width: int,
        default_line_style: str,
        toolbar_button_size: int,
        toolbar_x: int,
        toolbar_y: int,
    ) -> None:
        self.bus = bus
        self.dispatcher = dispatcher
        self._current_tool = default_tool
        self._color = default_color
        self._width = default_width
        self._line_style = default_line_style
        self._toolbar_button_size = toolbar_button_size
        self._toolbar_position = QPoint(toolbar_x, toolbar_y)
        self._coordinates = ScreenCoordinateMapper()
        self._paused = False
        self._window = FloatingToolWindow()
        self._buttons: dict[str, QToolButton] = {}
        self._color_button = QToolButton(self._window)
        self._width_button = QToolButton(self._window)
        self._style_button = QToolButton(self._window)
        self._stamp_button: QToolButton | None = None
        self._subscriptions: list[Subscription] = []
        self._window.input_geometry_changed.connect(self._publish_input_exclusion)
        self._window.drag_finished.connect(self._toolbar_drag_finished)
        self._build()

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("drawing.mode.changed", self._drawing_mode_changed),
            self.bus.subscribe("drawing.tool.changed", self._tool_changed),
            self.bus.subscribe("app.pause.changed", self._pause_changed),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]
        self._sync_buttons()

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._window.close()
        self.bus.publish("mouse.input_exclusion.changed", source="drawing_toolbar", rect=None)

    def _build(self) -> None:
        self._window.setWindowTitle(tr("drawing_toolbar.title"))
        layout = QHBoxLayout(self._window)
        self._layout = layout
        layout.addWidget(ToolDragHandle(self._window))
        group = QButtonGroup(self._window)
        group.setExclusive(True)
        for tool, label in self.TOOLS:
            button = QToolButton(self._window)
            button.setIcon(tool_icon(tool))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setToolTip(tr(label))
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, value=tool: self._select_tool(value))
            if tool == "stamp_star":
                self._stamp_button = button
                button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
                button.setMenu(self._stamp_menu())
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
        for label, command, icon_name in (
            (tr("tool.undo"), CommandId.UNDO_DRAWING, "undo"),
            (tr("tool.redo"), CommandId.REDO_DRAWING, "redo"),
            (tr("tool.clear"), CommandId.CLEAR_DRAWING, "clear"),
            (tr("tool.pass_through"), CommandId.DRAWING_PASS_THROUGH, "pass"),
        ):
            button = QToolButton(self._window)
            button.setIcon(command_icon(icon_name))
            button.setToolTip(label)
            button.clicked.connect(lambda _checked=False, item=command: self.dispatcher.dispatch(item))
            layout.addWidget(button)
        self._apply_toolbar_size()
        self._window.move_to_available(self._toolbar_position)

    def _select_tool(self, tool: str) -> None:
        self.bus.publish("drawing.tool.select", tool=tool)

    def _select_color(self, color: str) -> None:
        self._color = color
        self._sync_style_buttons()
        self._publish_style()

    def _select_width(self, width: int) -> None:
        self._width = width
        self._sync_style_buttons()
        self._publish_style()

    def _select_line_style(self, line_style: str) -> None:
        self._line_style = line_style
        self._sync_style_buttons()
        self._publish_style()

    def _publish_style(self) -> None:
        self.bus.publish(
            "drawing.style.change",
            color=self._color,
            width=self._width,
            line_style=self._line_style,
        )

    def _drawing_mode_changed(self, event: Event) -> None:
        pass_through = event.payload.get("pass_through", True)
        if pass_through or self._paused:
            self._window.hide()
        else:
            self._window.show()
            self._window.raise_()
            self._publish_input_exclusion()

    def _tool_changed(self, event: Event) -> None:
        tool = event.payload.get("tool")
        if isinstance(tool, str):
            self._current_tool = tool
            self._sync_buttons()

    def _pause_changed(self, event: Event) -> None:
        self._paused = bool(event.payload.get("paused", False))
        if self._paused:
            self._window.hide()
            self.bus.publish("mouse.input_exclusion.changed", source="drawing_toolbar", rect=None)

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if isinstance(settings, Settings):
            self._toolbar_button_size = settings.drawing.toolbar_button_size
            self._toolbar_position = QPoint(settings.drawing.toolbar_x, settings.drawing.toolbar_y)
            self._apply_toolbar_size()

    def _sync_buttons(self) -> None:
        for tool, button in self._buttons.items():
            button.setChecked(self._button_key(self._current_tool) == tool)
        self._sync_style_buttons()

    def _sync_style_buttons(self) -> None:
        self._color_button.setIcon(swatch_icon(self._color))
        self._width_button.setIcon(width_icon(self._width))
        self._style_button.setIcon(line_style_icon(self._line_style))
        if self._stamp_button is not None:
            self._stamp_button.setIcon(stamp_icon(self._stamp_name(self._current_tool)))

    def _add_popup_button(self, layout: QHBoxLayout, button: QToolButton, tooltip: str, menu: QMenu) -> None:
        button.setToolTip(tooltip)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(menu)
        menu.aboutToShow.connect(lambda: self.bus.publish("mouse.blocking.suspended", suspended=True))
        menu.aboutToHide.connect(lambda: self.bus.publish("mouse.blocking.suspended", suspended=False))
        layout.addWidget(button)
        self._sync_style_buttons()

    def _apply_toolbar_size(self) -> None:
        metrics = toolbar_metrics(self._toolbar_button_size)
        self._window.setStyleSheet(toolbar_style(self._toolbar_button_size))
        self._layout.setContentsMargins(metrics.margin_x, metrics.margin_y, metrics.margin_x, metrics.margin_y)
        self._layout.setSpacing(metrics.spacing)
        for button in self._window.findChildren(QToolButton):
            button.setIconSize(metrics.icon_size)
        self._window.adjustSize()
        self._publish_input_exclusion()

    def _publish_input_exclusion(self, _window: QWidget | None = None) -> None:
        if not self._window.isVisible():
            self.bus.publish("mouse.input_exclusion.changed", source="drawing_toolbar", rect=None)
            return
        rect = self._coordinates.qt_to_physical_rect(self._window.frameGeometry())
        self.bus.publish(
            "mouse.input_exclusion.changed",
            source="drawing_toolbar",
            rect=(
                rect.left(),
                rect.top(),
                rect.right() + 1,
                rect.bottom() + 1,
            ),
        )

    def _toolbar_drag_finished(self, _window: QWidget | None = None) -> None:
        point = self._window.frameGeometry().topLeft()
        self._toolbar_position = point
        self.bus.publish("drawing_toolbar.position.changed", x=point.x(), y=point.y())

    def _color_menu(self) -> QMenu:
        menu = QMenu(self._window)
        for color in self.COLORS:
            action = menu.addAction(swatch_icon(color), color)
            action.triggered.connect(lambda _checked=False, value=color: self._select_color(value))
        return menu

    def _width_menu(self) -> QMenu:
        menu = QMenu(self._window)
        for width in self.WIDTHS:
            action = menu.addAction(width_icon(width), str(width))
            action.triggered.connect(lambda _checked=False, value=width: self._select_width(value))
        return menu

    def _line_style_menu(self) -> QMenu:
        menu = QMenu(self._window)
        for line_style in self.LINE_STYLES:
            action = menu.addAction(line_style_icon(line_style), line_style)
            action.triggered.connect(lambda _checked=False, value=line_style: self._select_line_style(value))
        return menu

    def _stamp_menu(self) -> QMenu:
        menu = QMenu(self._window)
        menu.aboutToShow.connect(lambda: self.bus.publish("mouse.blocking.suspended", suspended=True))
        menu.aboutToHide.connect(lambda: self.bus.publish("mouse.blocking.suspended", suspended=False))
        for stamp in ("star", "heart", "check", "x", "exclamation"):
            action = menu.addAction(stamp_icon(stamp), tr(f"stamp.{stamp}"))
            action.triggered.connect(lambda _checked=False, value=stamp: self._select_tool(f"stamp_{value}"))
        return menu

    def _button_key(self, tool: str) -> str:
        return "stamp_star" if tool.startswith("stamp_") else tool

    def _stamp_name(self, tool: str) -> str:
        return tool.removeprefix("stamp_") if tool.startswith("stamp_") else "star"
