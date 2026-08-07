from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDateTime, QObject, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from config.settings import Settings
from core.event_bus import Event, EventBus
from drawing.document import DrawingDocument
from drawing.events import PointerEvent
from drawing.renderer import ShapeRenderer
from drawing.shapes import Shape
from mouse.events import MouseEvent, MouseEventType
from overlay.coordinates import ScreenCoordinateMapper
from overlay.effects import ClickButtonTracker, ClickEffect, ClickEffectType
from utils.winapi import set_click_through


class OverlayWindow(QObject):
    """Coordinates one borderless topmost window per monitor for click
    indicators and full-screen drawing.

    A single window spanning multiple monitors with different display
    scale factors cannot be rendered or hit-tested correctly by Windows -
    one HWND only has one DPI context - so one window is created per
    QScreen instead. All state (drawing document, click effects, pass
    through mode) lives here; each per-monitor window just paints its own
    slice of that shared state, translated into its own local coordinates.
    """

    def __init__(self, settings: Settings, bus: EventBus, base_dir: Path) -> None:
        super().__init__()
        self.settings = settings
        self.bus = bus
        self.base_dir = base_dir
        self._click_effect: ClickEffect | None = None
        self._document: DrawingDocument | None = None
        self._preview: Shape | None = None
        self._renderer = ShapeRenderer()
        self._coordinates = ScreenCoordinateMapper()
        self._button_tracker = ClickButtonTracker()
        self._held_click_buttons: set[MouseEventType] = set()
        self._click_images = self._load_click_images()
        self._cursor_color = settings.drawing.color
        self._pen_cursor = self._create_pen_cursor(self._cursor_color)
        self._override_cursor_active = False
        self._pass_through = settings.drawing.pass_through_on_start or not settings.drawing.enabled
        self._paused = False
        self._click_effects_visible = True
        self._capture_visual_suppressions: set[str] = set()
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(33)
        self._animation_timer.timeout.connect(self._tick_effects)
        self._windows: list[_MonitorOverlayWindow] = []
        self._create_windows()
        self._wire_events()

    # -- QWidget-like interface used by AppController --------------------

    def show(self) -> None:
        for window in self._windows:
            window.show()

    def hide(self) -> None:
        for window in self._windows:
            window.hide()

    def close(self) -> None:
        self._set_pen_cursor_active(False)
        for window in self._windows:
            window.close()

    def isVisible(self) -> bool:
        return any(window.isVisible() for window in self._windows)

    # -- window management -------------------------------------------------

    def _create_windows(self) -> None:
        for screen in QGuiApplication.screens():
            self._windows.append(_MonitorOverlayWindow(screen, self))

    def showEvent(self) -> None:
        self._apply_input_mode()

    def _wire_events(self) -> None:
        self.bus.subscribe("mouse.event", self._handle_mouse_event)
        self.bus.subscribe("drawing.document.ready", self._set_document)
        self.bus.subscribe("drawing.preview.changed", self._preview_changed)
        self.bus.subscribe("drawing.preview.cleared", self._preview_cleared)
        self.bus.subscribe("drawing.shape.added", self._shape_added)
        self.bus.subscribe("drawing.document.changed", self._document_changed)
        self.bus.subscribe("drawing.mode.toggle", self._toggle_drawing_mode)
        self.bus.subscribe("drawing.mode.pass_through", self._set_pass_through)
        self.bus.subscribe("drawing.mode.draw", self._set_draw_mode)
        self.bus.subscribe("drawing.style.change", self._drawing_style_changed)
        self.bus.subscribe("app.pause.changed", self._set_paused)
        self.bus.subscribe("click_effects.toggle_temp", self._toggle_click_effects)
        self.bus.subscribe("overlay.capture_visuals.suspended", self._set_capture_visuals_suspended)
        self.bus.subscribe("settings.saved", self._settings_saved)
        self.bus.subscribe("overlay.clear", self._clear)
        self.bus.subscribe("overlay.repaint", self._repaint_requested)

    def _handle_mouse_event(self, event: Event) -> None:
        if self._paused:
            return
        mouse_event: MouseEvent = event.payload["event"]
        if not self._pass_through:
            self._handle_drawing_mouse_event(mouse_event)
            return
        if self._capture_visual_suppressions:
            return
        if not self._click_effects_enabled():
            return
        if mouse_event.event_type in self._press_events():
            self._held_click_buttons.add(mouse_event.event_type)
            self._start_click_effect(mouse_event, hold_until_release=True)
        elif mouse_event.event_type == MouseEventType.MOVE:
            if MouseEventType.MIDDLE_DOWN in self._held_click_buttons:
                if self._button_tracker.apply(mouse_event) == ClickEffectType.MIDDLE:
                    self._start_click_effect(mouse_event, hold_until_release=True)
                else:
                    self._move_click_effect(mouse_event)
            elif self._held_click_buttons:
                self._move_click_effect(mouse_event)
        elif mouse_event.event_type in {MouseEventType.WHEEL, MouseEventType.HWHEEL}:
            self._start_click_effect(mouse_event, hold_until_release=False)
        elif mouse_event.event_type in self._release_events():
            self._button_tracker.apply(mouse_event)
            self._held_click_buttons.discard(self._matching_press_event(mouse_event.event_type))
            self._move_click_effect(mouse_event)
            if not self._held_click_buttons:
                self._release_click_effect()

    def _set_document(self, event: Event) -> None:
        self._document = event.payload["document"]
        self._repaint_all()

    def _preview_changed(self, event: Event) -> None:
        self._preview = event.payload["preview"]
        self._repaint_rect(event.payload["dirty"])

    def _preview_cleared(self, event: Event) -> None:
        self._preview = None
        self._repaint_rect(event.payload["dirty"])

    def _shape_added(self, event: Event) -> None:
        self._preview = None
        self._repaint_rect(event.payload["dirty"])

    def _document_changed(self, event: Event) -> None:
        self._preview = None
        dirty = event.payload["dirty"]
        if dirty.isNull():
            self._repaint_all()
        else:
            self._repaint_rect(dirty)

    def _clear(self, _event: Event) -> None:
        self._click_effect = None
        self._preview = None
        self._button_tracker.reset()
        self._held_click_buttons.clear()
        self._animation_timer.stop()
        self._repaint_all()

    def _repaint_requested(self, _event: Event) -> None:
        self._repaint_all()

    def _set_capture_visuals_suspended(self, event: Event) -> None:
        source = str(event.payload.get("source", "capture"))
        suspended = bool(event.payload.get("suspended", False))
        if suspended:
            self._capture_visual_suppressions.add(source)
            self._click_effect = None
            self._button_tracker.reset()
            self._held_click_buttons.clear()
            self._animation_timer.stop()
        else:
            self._capture_visual_suppressions.discard(source)
        self._repaint_all()

    def _repaint_all(self) -> None:
        for window in self._windows:
            window.update()

    def _repaint_rect(self, rect_global: QRect) -> None:
        for window in self._windows:
            window.update(rect_global.translated(-window.origin()))

    def _start_click_effect(self, event: MouseEvent, *, hold_until_release: bool) -> None:
        effect_type = self._effect_type(event)
        if effect_type is None:
            return
        now = self._now_ms()
        old_dirty = self._effect_dirty_bounds(self._click_effect) if self._click_effect else QRect()
        self._click_effect = ClickEffect(
            effect_type=effect_type,
            center=self._physical_to_qt_point(event.x, event.y),
            radius=self.settings.click_indicator.radius,
            pressed_radius=self.settings.click_indicator.pressed_radius,
            color=self._effect_color(effect_type),
            outline_color=self.settings.click_indicator.outline_color,
            width=self.settings.click_indicator.width,
            created_ms=now,
            hold_until_ms=10**15 if hold_until_release else now + self.settings.click_indicator.duration_ms,
            fade_ms=self.settings.click_indicator.fade_ms,
        )
        dirty = old_dirty.united(self._effect_dirty_bounds(self._click_effect))
        self._repaint_rect(dirty)
        if not self._animation_timer.isActive():
            self._animation_timer.start()

    def _move_click_effect(self, event: MouseEvent) -> None:
        if not self._click_effect:
            return
        old_dirty = self._effect_dirty_bounds(self._click_effect)
        self._click_effect.center = self._physical_to_qt_point(event.x, event.y)
        dirty = old_dirty.united(self._effect_dirty_bounds(self._click_effect))
        self._repaint_rect(dirty)

    def _release_click_effect(self) -> None:
        if not self._click_effect:
            return
        self._click_effect.release(self._now_ms())
        if not self._animation_timer.isActive():
            self._animation_timer.start()

    def _tick_effects(self) -> None:
        if not self._click_effect:
            self._animation_timer.stop()
            return
        dirty = self._effect_dirty_bounds(self._click_effect)
        if not self._click_effect.update(self._now_ms()):
            self._click_effect = None
            self._animation_timer.stop()
        self._repaint_rect(dirty)

    def _paint_content(self, painter: QPainter) -> None:
        if self._document:
            for shape in self._document.shapes():
                self._renderer.paint_shape(painter, shape)
        if self._preview:
            self._renderer.paint_shape(painter, self._preview)
        if self._click_effect and not self._capture_visual_suppressions:
            self._paint_click_effect(painter, self._click_effect)

    def _paint_click_effect(self, painter: QPainter, effect: ClickEffect) -> None:
        painter.save()
        painter.setOpacity(effect.opacity)
        radius = effect.current_radius()
        painter.setPen(QPen(QColor(effect.outline_color), effect.width + 2))
        painter.drawEllipse(effect.center, radius, radius)
        painter.setPen(QPen(QColor(effect.color), effect.width))
        painter.drawEllipse(effect.center, radius, radius)
        if not self._paint_click_image(painter, effect):
            self._paint_click_symbol(painter, effect)
        if self.settings.click_indicator.show_text:
            self._paint_click_text(painter, effect)
        painter.restore()

    def _paint_click_image(self, painter: QPainter, effect: ClickEffect) -> bool:
        if not self.settings.click_indicator.use_images:
            return False
        image = self._click_images.get(effect.effect_type)
        if image is None or image.isNull():
            return False
        target = self._click_image_rect(effect)
        painter.drawImage(target, image)
        return True

    def _effect_dirty_bounds(self, effect: ClickEffect | None) -> QRect:
        if effect is None:
            return QRect()
        dirty = effect.bounds()
        if self.settings.click_indicator.use_images:
            dirty = dirty.united(self._click_image_rect(effect))
        return dirty

    def _click_image_rect(self, effect: ClickEffect) -> QRect:
        side = self.settings.click_indicator.image_size
        gap = self.settings.click_indicator.image_gap
        center = effect.center
        candidates = [
            QRect(center.x() + gap, center.y() + gap, side, side),
            QRect(center.x() - gap - side, center.y() + gap, side, side),
            QRect(center.x() + gap, center.y() - gap - side, side, side),
            QRect(center.x() - gap - side, center.y() - gap - side, side, side),
        ]
        work_area = self._coordinates.work_area_for_point(center)
        for rect in candidates:
            if work_area.contains(rect):
                return rect
        return self._clamp_rect(candidates[0], work_area)

    def _paint_click_symbol(self, painter: QPainter, effect: ClickEffect) -> None:
        color = QColor(effect.color)
        painter.setPen(QPen(color, max(2, effect.width)))
        center = effect.center
        radius = effect.current_radius()
        if effect.effect_type == ClickEffectType.LEFT:
            painter.drawLine(center + QPoint(-radius // 3, 0), center + QPoint(0, radius // 3))
        elif effect.effect_type == ClickEffectType.RIGHT:
            painter.drawLine(center + QPoint(radius // 3, 0), center + QPoint(0, radius // 3))
        elif effect.effect_type == ClickEffectType.DOUBLE:
            painter.drawLine(center + QPoint(-radius // 3, -radius // 4), center + QPoint(0, radius // 6))
            painter.drawLine(center + QPoint(radius // 3, -radius // 4), center + QPoint(0, radius // 6))
        elif effect.effect_type == ClickEffectType.MIDDLE:
            painter.drawLine(center + QPoint(0, -radius // 2), center + QPoint(0, radius // 2))
        elif effect.effect_type == ClickEffectType.BOTH:
            painter.drawLine(center + QPoint(-radius // 3, 0), center + QPoint(0, radius // 3))
            painter.drawLine(center + QPoint(radius // 3, 0), center + QPoint(0, radius // 3))
        elif effect.effect_type in {ClickEffectType.WHEEL_UP, ClickEffectType.WHEEL_DOWN}:
            direction = -1 if effect.effect_type == ClickEffectType.WHEEL_UP else 1
            painter.drawLine(center, center + QPoint(0, direction * radius // 2))
            painter.drawLine(center + QPoint(-6, direction * radius // 3), center + QPoint(0, direction * radius // 2))
            painter.drawLine(center + QPoint(6, direction * radius // 3), center + QPoint(0, direction * radius // 2))

    def _paint_click_text(self, painter: QPainter, effect: ClickEffect) -> None:
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(effect.color))
        text = effect.effect_type.value.replace("_", " ").title()
        rect = effect.bounds().translated(0, effect.current_radius() + 8)
        painter.drawText(rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)

    def _paint_input_capture_surface(self, painter: QPainter, rect: QRect) -> None:
        if self._pass_through or self._paused:
            return
        painter.fillRect(rect, QColor(0, 0, 0, 1))

    def _effect_type(self, event: MouseEvent) -> ClickEffectType | None:
        effect_type = self._button_tracker.apply(event)
        if effect_type == ClickEffectType.LEFT and not self.settings.click_indicator.show_left:
            return None
        if effect_type == ClickEffectType.RIGHT and not self.settings.click_indicator.show_right:
            return None
        if effect_type == ClickEffectType.DOUBLE and not self.settings.click_indicator.show_double:
            return None
        if effect_type == ClickEffectType.BOTH and not self.settings.click_indicator.show_both:
            return None
        if effect_type == ClickEffectType.MIDDLE and not self.settings.click_indicator.show_wheel_drag:
            return None
        if effect_type in {
            ClickEffectType.WHEEL_UP,
            ClickEffectType.WHEEL_DOWN,
            ClickEffectType.WHEEL_LEFT,
            ClickEffectType.WHEEL_RIGHT,
        } and not self.settings.click_indicator.show_wheel:
            return None
        return effect_type

    def _settings_saved(self, event: Event) -> None:
        self.settings = event.payload["settings"]
        self._click_images = self._load_click_images()
        self._update_pen_cursor(self.settings.drawing.color)
        if not self._click_effects_enabled():
            self._click_effect = None
            self._button_tracker.reset()
            self._held_click_buttons.clear()
            self._animation_timer.stop()
            self._repaint_all()

    def _toggle_click_effects(self, _event: Event) -> None:
        self._click_effects_visible = not self._click_effects_visible
        if not self._click_effects_visible:
            self._click_effect = None
            self._button_tracker.reset()
            self._held_click_buttons.clear()
            self._animation_timer.stop()
            self._repaint_all()
        self.bus.publish("click_effects.temp.changed", enabled=self._click_effects_visible)

    def _click_effects_enabled(self) -> bool:
        return self.settings.click_indicator.enabled and self._click_effects_visible

    def _effect_color(self, effect_type: ClickEffectType) -> str:
        if effect_type == ClickEffectType.LEFT:
            return self.settings.click_indicator.left_color
        if effect_type == ClickEffectType.RIGHT:
            return self.settings.click_indicator.right_color
        if effect_type == ClickEffectType.DOUBLE:
            return self.settings.click_indicator.left_color
        if effect_type == ClickEffectType.BOTH:
            return self.settings.click_indicator.both_color
        if effect_type == ClickEffectType.MIDDLE:
            return self.settings.click_indicator.middle_color
        return self.settings.click_indicator.wheel_color

    def _load_click_images(self) -> dict[ClickEffectType, QImage]:
        base_dir = Path(self.settings.click_indicator.image_directory)
        if not base_dir.is_absolute():
            base_dir = self.base_dir / base_dir
        names = {
            ClickEffectType.LEFT: "left.png",
            ClickEffectType.RIGHT: "right.png",
            ClickEffectType.DOUBLE: "double.png",
            ClickEffectType.BOTH: "both.png",
            ClickEffectType.MIDDLE: "middle.png",
            ClickEffectType.WHEEL_UP: "wheel_up.png",
            ClickEffectType.WHEEL_DOWN: "wheel_down.png",
            ClickEffectType.WHEEL_LEFT: "wheel_left.png",
            ClickEffectType.WHEEL_RIGHT: "wheel_right.png",
        }
        return {
            effect_type: QImage(str(base_dir / filename))
            for effect_type, filename in names.items()
        }

    @staticmethod
    def _clamp_rect(rect: QRect, bounds: QRect) -> QRect:
        x = min(max(rect.left(), bounds.left()), bounds.right() - rect.width() + 1)
        y = min(max(rect.top(), bounds.top()), bounds.bottom() - rect.height() + 1)
        return QRect(x, y, rect.width(), rect.height())

    def _now_ms(self) -> int:
        return QDateTime.currentMSecsSinceEpoch()

    def _toggle_drawing_mode(self, _event: Event) -> None:
        if self._paused:
            return
        self._pass_through = not self._pass_through
        self._apply_input_mode()

    def _set_pass_through(self, _event: Event) -> None:
        self._pass_through = True
        self.bus.publish("drawing.cancel")
        self._apply_input_mode()

    def _set_draw_mode(self, _event: Event) -> None:
        if self._paused or not self.settings.drawing.enabled:
            return
        self._pass_through = False
        self._apply_input_mode()

    def _set_paused(self, event: Event) -> None:
        self._paused = bool(event.payload.get("paused", False))
        if self._paused:
            self._pass_through = True
            self.bus.publish("drawing.cancel")
            self._click_effect = None
            self._preview = None
            self._button_tracker.reset()
            self._held_click_buttons.clear()
            self._animation_timer.stop()
        self._apply_input_mode()
        self._repaint_all()

    def _handle_drawing_mouse_event(self, event: MouseEvent) -> None:
        if event.event_type == MouseEventType.LEFT_DOWN:
            self.bus.publish("drawing.pointer.down", event=self._pointer_event_from_mouse(event))
        elif event.event_type == MouseEventType.MOVE:
            self.bus.publish("drawing.pointer.move", event=self._pointer_event_from_mouse(event))
        elif event.event_type == MouseEventType.LEFT_UP:
            self.bus.publish("drawing.pointer.up", event=self._pointer_event_from_mouse(event))

    def _apply_input_mode(self) -> None:
        hwnds: list[int] = []
        for window in self._windows:
            hwnd = int(window.winId()) if window.winId() else 0
            if hwnd:
                set_click_through(hwnd, self._pass_through)
                hwnds.append(hwnd)
            window.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._pass_through)
        cursor_active = not self._pass_through and not self._paused
        for window in self._windows:
            if cursor_active:
                window.setCursor(self._pen_cursor)
            else:
                window.unsetCursor()
        self._set_pen_cursor_active(cursor_active)
        self._repaint_all()
        if hwnds:
            self.bus.publish("overlay.input_mode.changed", hwnds=hwnds, pass_through=self._pass_through)

    def _drawing_style_changed(self, event: Event) -> None:
        color = event.payload.get("color")
        if isinstance(color, str):
            self._update_pen_cursor(color)

    def _update_pen_cursor(self, color: str) -> None:
        self._cursor_color = color
        was_active = self._override_cursor_active
        if was_active:
            self._set_pen_cursor_active(False)
        self._pen_cursor = self._create_pen_cursor(color)
        if not self._pass_through and not self._paused:
            for window in self._windows:
                window.setCursor(self._pen_cursor)
            self._set_pen_cursor_active(True)

    def _set_pen_cursor_active(self, active: bool) -> None:
        if active == self._override_cursor_active:
            return
        if active:
            QGuiApplication.setOverrideCursor(self._pen_cursor)
            self._override_cursor_active = True
        else:
            QGuiApplication.restoreOverrideCursor()
            self._override_cursor_active = False

    @staticmethod
    def _create_pen_cursor(color: str) -> QCursor:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#1c1c1e"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(8, 25, 23, 10)
        painter.setPen(QPen(QColor("#ffffff"), 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(10, 23, 21, 12)
        painter.setPen(QPen(QColor(color), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(23, 10, 27, 6)
        painter.end()
        return QCursor(pixmap, 8, 25)

    def _pointer_event_from_mouse(self, event: MouseEvent) -> PointerEvent:
        return PointerEvent(
            position=self._physical_to_qt_point(event.x, event.y),
            timestamp_ms=event.timestamp_ms,
            shift=False,
            alt=False,
        )

    def _physical_to_qt_point(self, x: int, y: int) -> QPoint:
        return self._coordinates.physical_to_qt_point(x, y)

    @staticmethod
    def _press_events() -> set[MouseEventType]:
        return {MouseEventType.LEFT_DOWN, MouseEventType.RIGHT_DOWN, MouseEventType.MIDDLE_DOWN}

    @staticmethod
    def _release_events() -> set[MouseEventType]:
        return {MouseEventType.LEFT_UP, MouseEventType.RIGHT_UP, MouseEventType.MIDDLE_UP}

    @staticmethod
    def _matching_press_event(event_type: MouseEventType) -> MouseEventType:
        mapping = {
            MouseEventType.LEFT_UP: MouseEventType.LEFT_DOWN,
            MouseEventType.RIGHT_UP: MouseEventType.RIGHT_DOWN,
            MouseEventType.MIDDLE_UP: MouseEventType.MIDDLE_DOWN,
        }
        return mapping[event_type]


class _MonitorOverlayWindow(QWidget):
    def __init__(self, screen, coordinator: OverlayWindow) -> None:
        super().__init__()
        self._coordinator = coordinator
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setMouseTracking(True)

    def origin(self) -> QPoint:
        return self.geometry().topLeft()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._coordinator.showEvent()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._coordinator._paint_input_capture_surface(painter, self.rect())
        painter.translate(-self.origin())
        self._coordinator._paint_content(painter)

    def mousePressEvent(self, event) -> None:
        if self._coordinator._pass_through or event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._coordinator._pass_through:
            event.ignore()
            return
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._coordinator._pass_through or event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._coordinator.bus.publish("drawing.cancel")
            event.accept()
            return
        super().keyPressEvent(event)
