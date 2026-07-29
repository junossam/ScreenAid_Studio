from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize


@dataclass(frozen=True, slots=True)
class ToolbarMetrics:
    button_size: int
    icon_size: QSize
    padding: int
    margin_x: int
    margin_y: int
    spacing: int


def toolbar_metrics(button_size: int) -> ToolbarMetrics:
    size = min(48, max(22, int(button_size)))
    return ToolbarMetrics(
        button_size=size,
        icon_size=QSize(max(14, round(size * 0.64)), max(14, round(size * 0.64))),
        padding=max(1, round(size * 0.11)),
        margin_x=max(5, round(size * 0.28)),
        margin_y=max(4, round(size * 0.20)),
        spacing=max(3, round(size * 0.14)),
    )


def toolbar_style(button_size: int) -> str:
    metrics = toolbar_metrics(button_size)
    height = max(20, metrics.button_size - 2)
    return f"""
        QWidget {{
            background: rgba(32, 34, 38, 235);
            border: 1px solid rgba(255, 255, 255, 70);
            border-radius: 6px;
        }}
        QToolButton, QPushButton {{
            color: white;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: {metrics.padding}px;
            min-width: {metrics.button_size}px;
            min-height: {height}px;
        }}
        QToolButton:checked {{
            background: #0a84ff;
            border-color: #8cc7ff;
        }}
        QToolButton:hover, QPushButton:hover {{
            background: rgba(255, 255, 255, 35);
        }}
        QPushButton:disabled {{
            color: rgba(255, 255, 255, 90);
        }}
        QLabel {{
            color: rgba(255, 255, 255, 160);
            border: 0;
            padding: 5px 7px;
        }}
        """
