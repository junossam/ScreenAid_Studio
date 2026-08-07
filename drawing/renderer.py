from __future__ import annotations

from math import atan2, cos, sin

from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from drawing.geometry import curve_path
from drawing.shapes import Shape, ShapeType


class ShapeRenderer:
    def paint_shape(self, painter: QPainter, shape: Shape) -> None:
        if not shape.is_visible or len(shape.points) < 2:
            return
        try:
            if shape.shape_type == ShapeType.ERASER:
                self._paint_eraser(painter, shape)
                return
            color = QColor(shape.stroke_color)
            color.setAlpha(shape.stroke_opacity)
            pen = QPen(
                color,
                shape.stroke_width,
                self._pen_style(shape.stroke_style),
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            self._paint_by_type(painter, shape)
        except Exception:
            return

    def _paint_by_type(self, painter: QPainter, shape: Shape) -> None:
        if shape.shape_type in {ShapeType.FREEHAND, ShapeType.HIGHLIGHTER}:
            painter.drawPath(self._path(shape))
            return
        start = shape.points[0]
        end = shape.points[1]
        if shape.shape_type == ShapeType.LINE:
            painter.drawLine(start, end)
        elif shape.shape_type == ShapeType.ARROW:
            painter.drawLine(start, end)
            self._paint_arrow_head(painter, start, end, shape.stroke_width)
        elif shape.shape_type == ShapeType.RECTANGLE:
            painter.drawRect(QRect(start, end).normalized())
        elif shape.shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(QRect(start, end).normalized())
        elif shape.shape_type == ShapeType.STAMP:
            self._paint_stamp(painter, shape, QRect(start, end).normalized())

    def _paint_eraser(self, painter: QPainter, shape: Shape) -> None:
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setPen(
            QPen(
                Qt.GlobalColor.transparent,
                shape.stroke_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawPath(self._path(shape))
        painter.restore()

    def _path(self, shape: Shape) -> QPainterPath:
        return curve_path(shape.points)

    def _paint_arrow_head(self, painter: QPainter, start, end, width: int) -> None:
        angle = atan2(end.y() - start.y(), end.x() - start.x())
        length = max(12, width * 4)
        left = QPointF(
            end.x() - length * cos(angle - 0.55),
            end.y() - length * sin(angle - 0.55),
        )
        right = QPointF(
            end.x() - length * cos(angle + 0.55),
            end.y() - length * sin(angle + 0.55),
        )
        painter.drawPolygon(QPolygonF([QPointF(end), left, right]))

    def _paint_stamp(self, painter: QPainter, shape: Shape, rect: QRect) -> None:
        color = QColor(shape.fill_color or shape.stroke_color)
        color.setAlpha(shape.fill_opacity or shape.stroke_opacity)
        painter.setPen(QPen(color, max(2, shape.stroke_width), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        name = shape.stamp_name
        if name == "heart":
            painter.setBrush(color)
            painter.drawPath(self._heart_path(rect))
        elif name == "check":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(self._check_points(rect))
        elif name == "x":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())
        elif name == "exclamation":
            painter.drawRoundedRect(
                rect.center().x() - max(2, rect.width() // 12),
                rect.top() + rect.height() // 8,
                max(4, rect.width() // 6),
                max(12, rect.height() * 5 // 9),
                3,
                3,
            )
            dot = max(4, rect.width() // 7)
            painter.drawEllipse(rect.center().x() - dot // 2, rect.bottom() - dot * 2, dot, dot)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._star_path(rect))

    def _star_path(self, rect: QRect) -> QPainterPath:
        points = self._star_points(rect)
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        path.closeSubpath()
        return path

    def _star_points(self, rect: QRect) -> list[QPointF]:
        x = rect.left()
        y = rect.top()
        w = rect.width()
        h = rect.height()
        ratios = (
            (0.52, 0.08),
            (0.62, 0.40),
            (0.91, 0.30),
            (0.68, 0.55),
            (0.80, 0.88),
            (0.50, 0.68),
            (0.20, 0.86),
            (0.32, 0.56),
            (0.08, 0.34),
            (0.40, 0.40),
        )
        return [QPointF(x + w * px, y + h * py) for px, py in ratios]

    def _heart_path(self, rect: QRect) -> QPainterPath:
        path = QPainterPath()
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()
        path.moveTo(x + w * 0.5, y + h * 0.88)
        path.cubicTo(x + w * 0.08, y + h * 0.62, x + w * 0.08, y + h * 0.22, x + w * 0.32, y + h * 0.18)
        path.cubicTo(x + w * 0.44, y + h * 0.16, x + w * 0.5, y + h * 0.27, x + w * 0.5, y + h * 0.35)
        path.cubicTo(x + w * 0.5, y + h * 0.27, x + w * 0.56, y + h * 0.16, x + w * 0.68, y + h * 0.18)
        path.cubicTo(x + w * 0.92, y + h * 0.22, x + w * 0.92, y + h * 0.62, x + w * 0.5, y + h * 0.88)
        return path

    def _check_points(self, rect: QRect) -> QPolygonF:
        return QPolygonF(
            [
                QPointF(rect.left() + rect.width() * 0.18, rect.top() + rect.height() * 0.55),
                QPointF(rect.left() + rect.width() * 0.42, rect.top() + rect.height() * 0.78),
                QPointF(rect.left() + rect.width() * 0.84, rect.top() + rect.height() * 0.25),
            ]
        )

    def _pen_style(self, name: str) -> Qt.PenStyle:
        return {
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
            "dashdot": Qt.PenStyle.DashDotLine,
        }.get(name, Qt.PenStyle.SolidLine)
