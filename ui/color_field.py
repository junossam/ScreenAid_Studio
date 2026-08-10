from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from core.localization import tr


class ColorField(QWidget):
    """A hex color QLineEdit paired with a swatch button that opens a color picker.

    Exposes text()/setText() so it's a drop-in replacement for the QLineEdit
    fields settings load/save code already reads and writes.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._edit = QLineEdit()
        self._swatch = QPushButton()
        self._swatch.setFixedSize(28, 24)
        self._swatch.setCursor(self._edit.cursor())
        self._swatch.clicked.connect(self._pick_color)
        self._edit.textChanged.connect(self._update_swatch)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._swatch)
        self._update_swatch()

    def text(self) -> str:
        return self._edit.text()

    def setText(self, value: str) -> None:
        self._edit.setText(value)

    def _pick_color(self) -> None:
        initial = QColor(self._edit.text())
        if not initial.isValid():
            initial = QColor("#ffffff")
        color = QColorDialog.getColor(initial, self, tr("settings.pick_color"))
        if color.isValid():
            self._edit.setText(color.name())

    def _update_swatch(self) -> None:
        color = QColor(self._edit.text())
        if not color.isValid():
            color = QColor("#ffffff")
        self._swatch.setStyleSheet(
            f"QPushButton {{ background-color: {color.name()}; border: 1px solid #888888; border-radius: 3px; }}"
        )
