from __future__ import annotations

from dataclasses import replace

from config.settings import DrawingSettings, EraserSettings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from drawing.document import DrawingDocument
from drawing.events import PointerEvent
from drawing.tools import DrawingTool, create_tool


class DrawingController(Service):
    def __init__(self, settings: DrawingSettings, eraser_settings: EraserSettings, bus: EventBus) -> None:
        self.settings = settings
        self.eraser_settings = eraser_settings
        self.bus = bus
        self.document = DrawingDocument()
        self._tool: DrawingTool = create_tool(settings)
        self._drawing = False
        self._erasing = False
        self._subscriptions: list[Subscription] = []

    def start(self) -> None:
        if not self.settings.enabled:
            return
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("drawing.pointer.down", self._pointer_down),
            self.bus.subscribe("drawing.pointer.move", self._pointer_move),
            self.bus.subscribe("drawing.pointer.up", self._pointer_up),
            self.bus.subscribe("drawing.cancel", self._cancel),
            self.bus.subscribe("drawing.clear", self._clear),
            self.bus.subscribe("drawing.undo", self._undo),
            self.bus.subscribe("drawing.redo", self._redo),
            self.bus.subscribe("drawing.shape.commit", self._commit_shape),
            self.bus.subscribe("drawing.tool.select", self._select_tool),
            self.bus.subscribe("drawing.style.change", self._change_style),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]
        self.bus.publish("drawing.document.ready", document=self.document)
        self.bus.publish("drawing.tool.changed", tool=self.settings.default_tool)

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._tool.cancel()
        self._drawing = False
        self._erasing = False

    def _pointer_down(self, event: Event) -> None:
        pointer = event.payload["event"]
        if self.settings.default_tool == "eraser":
            if self.eraser_settings.mode == "pixel":
                self._start_pixel_eraser(pointer)
            else:
                self._erasing = True
                self._erase_at(pointer.position)
            return
        self._drawing = True
        self._tool.pointer_down(pointer)
        preview = self._tool.preview()
        if preview:
            self.bus.publish("drawing.preview.changed", preview=preview, dirty=preview.bounds())

    def _pointer_move(self, event: Event) -> None:
        if self._erasing:
            self._erase_at(event.payload["event"].position)
            return
        if not self._drawing:
            return
        preview = self._tool.preview()
        old_bounds = preview.bounds() if preview else None
        self._tool.pointer_move(event.payload["event"])
        preview = self._tool.preview()
        if preview:
            dirty = preview.bounds()
            if old_bounds:
                dirty = dirty.united(old_bounds)
            self.bus.publish("drawing.preview.changed", preview=preview, dirty=dirty)

    def _pointer_up(self, event: Event) -> None:
        if self._erasing:
            self._erasing = False
            return
        if not self._drawing:
            return
        preview = self._tool.preview()
        old_bounds = preview.bounds() if preview else None
        shape = self._tool.pointer_up(event.payload["event"])
        self._drawing = False
        if shape is None:
            if old_bounds:
                self.bus.publish("drawing.preview.cleared", dirty=old_bounds)
            return
        dirty = self.document.add_shape(shape)
        if old_bounds:
            dirty = dirty.united(old_bounds)
        self.bus.publish("drawing.shape.added", shape=shape, dirty=dirty)

    def _erase_at(self, position) -> None:
        dirty = self.document.erase_at(position)
        if not dirty.isNull():
            self.bus.publish("drawing.document.changed", dirty=dirty)

    def _start_pixel_eraser(self, pointer) -> None:
        eraser_width = max(1, self.eraser_settings.size)
        self._drawing = True
        self._tool = create_tool(replace(self.settings, default_tool="eraser", width=eraser_width))
        self._tool.pointer_down(pointer)
        preview = self._tool.preview()
        if preview:
            self.bus.publish("drawing.preview.changed", preview=preview, dirty=preview.bounds())

    def _cancel(self, _event: Event) -> None:
        preview = self._tool.preview()
        self._tool.cancel()
        self._drawing = False
        self._erasing = False
        if preview:
            self.bus.publish("drawing.preview.cleared", dirty=preview.bounds())

    def _clear(self, _event: Event) -> None:
        dirty = self.document.clear()
        self._tool.cancel()
        self._drawing = False
        self._erasing = False
        self.bus.publish("drawing.document.changed", dirty=dirty)

    def _undo(self, _event: Event) -> None:
        dirty = self.document.undo()
        self.bus.publish("drawing.document.changed", dirty=dirty)

    def _redo(self, _event: Event) -> None:
        dirty = self.document.redo()
        self.bus.publish("drawing.document.changed", dirty=dirty)

    def _commit_shape(self, event: Event) -> None:
        shape = event.payload.get("shape")
        if shape is None:
            return
        dirty = self.document.add_shape(shape)
        self.bus.publish("drawing.shape.added", shape=shape, dirty=dirty)

    def _select_tool(self, event: Event) -> None:
        tool = event.payload.get("tool")
        if not isinstance(tool, str):
            return
        preview = self._tool.preview()
        self._tool.cancel()
        self._drawing = False
        if preview:
            self.bus.publish("drawing.preview.cleared", dirty=preview.bounds())
        self.settings = replace(self.settings, default_tool=tool)
        self._tool = create_tool(self.settings)
        self.bus.publish("drawing.tool.changed", tool=tool)

    def _change_style(self, event: Event) -> None:
        color = event.payload.get("color", self.settings.color)
        width = event.payload.get("width", self.settings.width)
        line_style = event.payload.get("line_style", self.settings.line_style)
        if not isinstance(color, str) or not isinstance(width, int) or not isinstance(line_style, str):
            return
        self.settings = replace(
            self.settings,
            color=color,
            width=max(1, min(64, width)),
            line_style=line_style,
        )
        if not self._drawing:
            self._tool = create_tool(self.settings)

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if settings is None:
            return
        self.settings = replace(
            settings.drawing,
            default_tool=self.settings.default_tool,
            color=self.settings.color,
            width=self.settings.width,
            line_style=self.settings.line_style,
        )
        self.eraser_settings = settings.eraser
        if not self._drawing:
            self._tool = create_tool(self.settings)
