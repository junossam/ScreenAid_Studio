from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Protocol

from PySide6.QtCore import QPoint

from config.settings import DrawingSettings
from drawing.events import PointerEvent
from drawing.shapes import Shape, ShapeType
from drawing.stamps import is_stamp_tool, stamp_name_from_tool


class DrawingTool(Protocol):
    def pointer_down(self, event: PointerEvent) -> None:
        ...

    def pointer_move(self, event: PointerEvent) -> None:
        ...

    def pointer_up(self, event: PointerEvent) -> Shape | None:
        ...

    def cancel(self) -> None:
        ...

    def preview(self) -> Shape | None:
        ...


@dataclass(slots=True)
class FreehandTool:
    settings: DrawingSettings
    min_point_distance: int = 2
    _shape: Shape | None = None

    def pointer_down(self, event: PointerEvent) -> None:
        self._shape = Shape(
            shape_type=ShapeType.FREEHAND,
            points=[event.position],
            stroke_color=self.settings.color,
            stroke_width=self.settings.width,
            stroke_style=self.settings.line_style,
            stroke_opacity=self.settings.opacity,
        )

    def pointer_move(self, event: PointerEvent) -> None:
        if self._shape is None:
            return
        if self._should_add(event.position):
            self._shape.points.append(event.position)

    def pointer_up(self, event: PointerEvent) -> Shape | None:
        if self._shape is None:
            return None
        if self._should_add(event.position):
            self._shape.points.append(event.position)
        shape = self._shape
        self._shape = None
        if len(shape.points) == 1:
            shape.points.append(shape.points[0] + QPoint(1, 1))
        return shape

    def cancel(self) -> None:
        self._shape = None

    def preview(self) -> Shape | None:
        return self._shape

    def _should_add(self, point: QPoint) -> bool:
        if self._shape is None or not self._shape.points:
            return True
        last = self._shape.points[-1]
        dx = point.x() - last.x()
        dy = point.y() - last.y()
        return dx * dx + dy * dy >= self.min_point_distance * self.min_point_distance


@dataclass(slots=True)
class PixelEraserTool(FreehandTool):
    def pointer_down(self, event: PointerEvent) -> None:
        self._shape = Shape(
            shape_type=ShapeType.ERASER,
            points=[event.position],
            stroke_color="#000000",
            stroke_width=max(1, self.settings.width),
            stroke_style="solid",
            stroke_opacity=255,
        )


@dataclass(slots=True)
class TwoPointTool:
    settings: DrawingSettings
    shape_type: ShapeType
    _start: QPoint | None = None
    _current: QPoint | None = None

    def pointer_down(self, event: PointerEvent) -> None:
        self._start = event.position
        self._current = event.position

    def pointer_move(self, event: PointerEvent) -> None:
        if self._start is None:
            return
        self._current = self._snapped(event.position, event.shift)

    def pointer_up(self, event: PointerEvent) -> Shape | None:
        if self._start is None:
            return None
        self._current = self._snapped(event.position, event.shift)
        shape = self.preview()
        self.cancel()
        return shape

    def cancel(self) -> None:
        self._start = None
        self._current = None

    def preview(self) -> Shape | None:
        if self._start is None or self._current is None:
            return None
        return Shape(
            shape_type=self.shape_type,
            points=[self._start, self._current],
            stroke_color=self.settings.color,
            stroke_width=self.settings.width,
            stroke_style=self.settings.line_style,
            stroke_opacity=self.settings.opacity,
        )

    def _snapped(self, point: QPoint, enabled: bool) -> QPoint:
        if not enabled or self._start is None:
            return point
        dx = point.x() - self._start.x()
        dy = point.y() - self._start.y()
        if abs(dx) >= abs(dy):
            return QPoint(point.x(), self._start.y())
        return QPoint(self._start.x(), point.y())


@dataclass(slots=True)
class StampTool:
    settings: DrawingSettings
    stamp_name: str
    _center: QPoint | None = None
    _edge: QPoint | None = None

    def pointer_down(self, event: PointerEvent) -> None:
        self._center = event.position
        size = self._default_size()
        self._edge = event.position + QPoint(size // 2, size // 2)

    def pointer_move(self, event: PointerEvent) -> None:
        if self._center is not None:
            self._edge = event.position

    def pointer_up(self, event: PointerEvent) -> Shape | None:
        if self._center is None:
            return None
        if self._edge is None or event.position == self._center:
            size = self._default_size()
            self._edge = self._center + QPoint(size // 2, size // 2)
        else:
            self._edge = event.position
        shape = self.preview()
        self.cancel()
        return shape

    def cancel(self) -> None:
        self._center = None
        self._edge = None

    def preview(self) -> Shape | None:
        if self._center is None or self._edge is None:
            return None
        dx = abs(self._edge.x() - self._center.x())
        dy = abs(self._edge.y() - self._center.y())
        half = max(12, dx, dy)
        top_left = self._center - QPoint(half, half)
        bottom_right = self._center + QPoint(half, half)
        return Shape(
            shape_type=ShapeType.STAMP,
            points=[top_left, bottom_right],
            stroke_color=self.settings.color,
            stroke_width=max(2, self.settings.width),
            stroke_style="solid",
            stroke_opacity=self.settings.opacity,
            fill_color=self.settings.color,
            fill_opacity=self.settings.opacity,
            stamp_name=self.stamp_name,
        )

    def _default_size(self) -> int:
        return max(28, min(96, self.settings.width * 8))


def create_tool(settings: DrawingSettings) -> DrawingTool:
    if is_stamp_tool(settings.default_tool):
        return StampTool(settings, stamp_name_from_tool(settings.default_tool))
    match settings.default_tool:
        case ShapeType.ERASER.value:
            return PixelEraserTool(settings)
        case ShapeType.LINE.value:
            return TwoPointTool(settings, ShapeType.LINE)
        case ShapeType.ARROW.value:
            return TwoPointTool(settings, ShapeType.ARROW)
        case ShapeType.RECTANGLE.value:
            return TwoPointTool(settings, ShapeType.RECTANGLE)
        case ShapeType.ELLIPSE.value:
            return TwoPointTool(settings, ShapeType.ELLIPSE)
        case ShapeType.HIGHLIGHTER.value:
            highlighter = FreehandTool(
                replace(
                    settings,
                    width=max(settings.width, 14),
                    opacity=min(settings.opacity, 90),
                    line_style="solid",
                )
            )
            return highlighter
        case _:
            return FreehandTool(settings)
