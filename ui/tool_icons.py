from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def tool_icon(tool: str, color: str = "#ffffff") -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap, color, 3)
    if tool in {"freehand", "highlighter"}:
        points = [QPoint(6, 18), QPoint(11, 10), QPoint(17, 14), QPoint(24, 6)]
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)
    elif tool == "line":
        painter.drawLine(6, 22, 26, 8)
    elif tool == "arrow":
        painter.drawLine(6, 22, 25, 8)
        painter.drawLine(25, 8, 20, 8)
        painter.drawLine(25, 8, 24, 13)
    elif tool == "rectangle":
        painter.drawRect(QRect(7, 8, 18, 15))
    elif tool == "ellipse":
        painter.drawEllipse(QRect(6, 8, 20, 15))
    elif tool == "eraser":
        painter.drawRect(QRect(9, 12, 15, 9))
        painter.drawLine(8, 22, 25, 22)
    elif tool.startswith("stamp_") or tool == "stamp":
        painter.end()
        return stamp_icon(tool.removeprefix("stamp_") if tool.startswith("stamp_") else "star", color)
    painter.end()
    return QIcon(pixmap)


def stamp_icon(stamp: str, color: str = "#ffffff") -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap, color, 3)
    painter.setBrush(QColor(color))
    if stamp == "heart":
        painter.drawPath(_heart_path(QRect(6, 6, 20, 20)))
    elif stamp == "check":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(7, 17, 13, 23)
        painter.drawLine(13, 23, 25, 9)
    elif stamp == "x":
        painter.drawLine(8, 8, 24, 24)
        painter.drawLine(24, 8, 8, 24)
    elif stamp == "exclamation":
        painter.drawRoundedRect(QRect(14, 6, 4, 15), 2, 2)
        painter.drawEllipse(QRect(13, 24, 6, 6))
    else:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(_star_path(QRect(5, 5, 22, 22)))
    painter.end()
    return QIcon(pixmap)


def command_icon(command: str) -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap, "#ffffff", 3)
    if command == "undo":
        painter.drawArc(QRect(7, 8, 18, 16), 40 * 16, 240 * 16)
        painter.drawLine(8, 8, 8, 15)
        painter.drawLine(8, 8, 15, 8)
    elif command == "redo":
        painter.drawArc(QRect(7, 8, 18, 16), -100 * 16, 240 * 16)
        painter.drawLine(24, 8, 24, 15)
        painter.drawLine(17, 8, 24, 8)
    elif command == "clear":
        painter.drawLine(9, 9, 23, 23)
        painter.drawLine(23, 9, 9, 23)
    elif command == "pass":
        painter.drawLine(6, 16, 24, 16)
        painter.drawLine(18, 10, 24, 16)
        painter.drawLine(18, 22, 24, 16)
    elif command == "done":
        painter.drawLine(7, 16, 13, 22)
        painter.drawLine(13, 22, 25, 9)
    painter.end()
    return QIcon(pixmap)


def swatch_icon(color: str) -> QIcon:
    pixmap = _pixmap()
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(QColor("#ffffff"), 2))
    painter.setBrush(QColor(color))
    painter.drawEllipse(QRect(7, 7, 18, 18))
    painter.end()
    return QIcon(pixmap)


def width_icon(width: int, color: str = "#ffffff") -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap, color, width)
    painter.drawLine(6, 16, 26, 16)
    painter.end()
    return QIcon(pixmap)


def line_style_icon(style: str, color: str = "#ffffff") -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap, color, 3)
    pen = painter.pen()
    pen.setStyle(
        {
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
            "dashdot": Qt.PenStyle.DashDotLine,
        }.get(style, Qt.PenStyle.SolidLine)
    )
    painter.setPen(pen)
    painter.drawLine(5, 16, 27, 16)
    painter.end()
    return QIcon(pixmap)


def _pixmap() -> QPixmap:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    return pixmap


def _painter(pixmap: QPixmap, color: str, width: int) -> QPainter:
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    return painter


def _star_path(rect: QRect) -> QPainterPath:
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
    points = [QPointF(x + w * px, y + h * py) for px, py in ratios]
    path = QPainterPath(points[0])
    for point in points[1:]:
        path.lineTo(point)
    path.closeSubpath()
    return path


def _heart_path(rect: QRect) -> QPainterPath:
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
