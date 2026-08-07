from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction, QGuiApplication, QImage, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox, QWidget

from config.settings import DrawingSettings, EraserSettings, PinnedWindowSettings
from drawing.document import DrawingDocument
from drawing.events import PointerEvent
from drawing.renderer import ShapeRenderer
from drawing.shapes import Shape
from drawing.tools import DrawingTool, create_tool
from core.localization import tr
from ui.annotation_toolbar import AnnotationToolbar
from utils.winapi import set_click_through


class PinnedWindow(QWidget):
    def __init__(
        self,
        image: QImage,
        settings: PinnedWindowSettings,
        drawing_settings: DrawingSettings,
        eraser_settings: EraserSettings | None = None,
        display_size: QSize | None = None,
    ) -> None:
        super().__init__()
        self._image = image
        self._display_size = display_size or image.size()
        self._settings = settings
        self._drawing_settings = drawing_settings
        self._eraser_settings = eraser_settings or EraserSettings(mode="object", size=24)
        self._current_tool = drawing_settings.default_tool
        self._current_color = drawing_settings.color
        self._current_width = drawing_settings.width
        self._current_line_style = drawing_settings.line_style
        self._zoom = settings.default_zoom
        self._click_through = settings.click_through
        self._annotation_mode = False
        self._document = DrawingDocument()
        self._renderer = ShapeRenderer()
        self._tool: DrawingTool | None = None
        self._preview: Shape | None = None
        self._erasing = False
        self._drag_pos: QPoint | None = None
        self._setup_window()
        self._toolbar = AnnotationToolbar(
            parent=self,
            current_tool=self._current_tool,
            current_color=self._current_color,
            current_width=self._current_width,
            current_line_style=self._current_line_style,
            on_tool_selected=self.set_annotation_tool,
            on_style_changed=self.set_annotation_style,
            on_undo=self.undo_annotation,
            on_redo=self.redo_annotation,
            on_clear=self.clear_annotations,
            on_done=lambda: self.set_annotation_mode(False),
            toolbar_button_size=drawing_settings.toolbar_button_size,
        )
        self._toolbar_user_positioned = False
        self._toolbar.drag_finished.connect(self._annotation_toolbar_moved)
        self._position_toolbar()
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._escape_shortcut.activated.connect(self.close)

    def _setup_window(self) -> None:
        self.setWindowTitle(tr("pinned.title"))
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(80, 60)
        # Without this, close() only hides the window - it never fires
        # `destroyed`, so PinnedWindowManager never removes it from its
        # window list.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(self._scaled_size())
        self._apply_click_through()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        target = self._image_target_rect()
        painter.drawImage(target, self._image)
        self._paint_annotations(painter, target)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_toolbar") and self._toolbar.isVisible():
            self._position_toolbar()

    def closeEvent(self, event) -> None:
        self._toolbar.close()
        super().closeEvent(event)

    def set_toolbar_button_size(self, button_size: int) -> None:
        self._toolbar.apply_toolbar_size(button_size)
        if self._toolbar.isVisible():
            self._position_toolbar()

    def mousePressEvent(self, event) -> None:
        self._activate_for_keyboard()
        if self._annotation_mode and event.button() == Qt.MouseButton.LeftButton:
            if self._current_tool == "eraser":
                if self._eraser_settings.mode == "pixel":
                    self._tool = create_tool(self._active_drawing_settings())
                    self._tool.pointer_down(self._pointer_event(event))
                    self._preview = self._tool.preview()
                    self.update()
                else:
                    self._erasing = True
                    self._erase_at(self._pointer_event(event).position)
            else:
                self._tool = create_tool(self._active_drawing_settings())
                self._tool.pointer_down(self._pointer_event(event))
                self._preview = self._tool.preview()
                self.update()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._annotation_mode and self._erasing and event.buttons() & Qt.MouseButton.LeftButton:
            self._erase_at(self._pointer_event(event).position)
            event.accept()
            return
        if self._annotation_mode and self._tool is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._tool.pointer_move(self._pointer_event(event))
            self._preview = self._tool.preview()
            self.update()
            event.accept()
            return
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._annotation_mode and self._erasing and event.button() == Qt.MouseButton.LeftButton:
            self._erasing = False
            event.accept()
            return
        if self._annotation_mode and self._tool is not None and event.button() == Qt.MouseButton.LeftButton:
            shape = self._tool.pointer_up(self._pointer_event(event))
            self._tool = None
            self._preview = None
            if shape is not None:
                self._document.add_shape(shape)
            self._sync_toolbar_state()
            self.update()
            event.accept()
            return
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _erase_at(self, position) -> None:
        dirty = self._document.erase_at(position)
        self._sync_toolbar_state()
        self.update(self._image_rect_to_window(dirty) if not dirty.isNull() else self.rect())

    def wheelEvent(self, event) -> None:
        self._activate_for_keyboard()
        step = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.set_zoom(self._zoom * step)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        self._activate_for_keyboard()
        menu = QMenu(self)
        zoom_in = QAction(tr("pinned.zoom_in"), self)
        zoom_out = QAction(tr("pinned.zoom_out"), self)
        reset = QAction(tr("pinned.reset_zoom"), self)
        click_through = QAction(tr("pinned.click_through"), self)
        click_through.setCheckable(True)
        click_through.setChecked(self._click_through)
        annotation = QAction(tr("pinned.annotation_mode"), self)
        annotation.setCheckable(True)
        annotation.setChecked(self._annotation_mode)
        undo = QAction(tr("pinned.undo_annotation"), self)
        redo = QAction(tr("pinned.redo_annotation"), self)
        clear = QAction(tr("pinned.clear_annotations"), self)
        copy_annotated = QAction(tr("pinned.copy_annotated"), self)
        save_annotated = QAction(tr("pinned.save_annotated"), self)
        undo.setEnabled(not self._document.is_empty())
        redo.setEnabled(self._document.can_redo())
        clear.setEnabled(not self._document.is_empty())
        close = QAction(tr("pinned.close"), self)
        zoom_in.triggered.connect(lambda: self.set_zoom(self._zoom * 1.25))
        zoom_out.triggered.connect(lambda: self.set_zoom(self._zoom / 1.25))
        reset.triggered.connect(lambda: self.set_zoom(1.0))
        click_through.triggered.connect(self.set_click_through)
        annotation.triggered.connect(self.set_annotation_mode)
        undo.triggered.connect(self.undo_annotation)
        redo.triggered.connect(self.redo_annotation)
        clear.triggered.connect(self.clear_annotations)
        copy_annotated.triggered.connect(self.copy_annotated_image)
        save_annotated.triggered.connect(self.save_annotated_image_as)
        close.triggered.connect(self.close)
        for action in (zoom_in, zoom_out, reset, click_through):
            menu.addAction(action)
        menu.addSeparator()
        for action in (annotation, undo, redo, clear):
            menu.addAction(action)
        menu.addSeparator()
        for action in (copy_annotated, save_annotated):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(close)
        menu.exec(event.globalPos())

    def set_zoom(self, zoom: float) -> None:
        self._zoom = min(self._settings.max_zoom, max(self._settings.min_zoom, zoom))
        self.resize(self._scaled_size())
        self.update()

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = enabled
        if enabled:
            self.set_annotation_mode(False)
        self._apply_click_through()

    def set_annotation_mode(self, enabled: bool) -> None:
        self._annotation_mode = enabled and not self._click_through
        if not self._annotation_mode:
            self._erasing = False
            if self._tool is not None:
                self._tool.cancel()
                self._tool = None
                self._preview = None
        self._toolbar.set_visible(self._annotation_mode)
        if self._annotation_mode:
            self._position_toolbar()
        self._sync_toolbar_state()
        self.update()

    def set_annotation_tool(self, tool: str) -> None:
        self._current_tool = tool
        self._erasing = False
        if self._tool is not None:
            self._tool.cancel()
            self._tool = None
            self._preview = None
        self._toolbar.set_current_tool(tool)
        self.update()

    def set_annotation_style(self, color: str, width: int, line_style: str) -> None:
        self._current_color = color
        self._current_width = max(1, min(64, width))
        self._current_line_style = line_style
        if self._tool is not None:
            self._tool.cancel()
            self._tool = None
            self._preview = None
        self.update()

    def undo_annotation(self) -> None:
        dirty = self._document.undo()
        self._sync_toolbar_state()
        self.update(self._image_rect_to_window(dirty) if not dirty.isNull() else self.rect())

    def redo_annotation(self) -> None:
        dirty = self._document.redo()
        self._sync_toolbar_state()
        self.update(self._image_rect_to_window(dirty) if not dirty.isNull() else self.rect())

    def clear_annotations(self) -> None:
        dirty = self._document.clear()
        self._sync_toolbar_state()
        self.update(self._image_rect_to_window(dirty) if not dirty.isNull() else self.rect())

    def annotated_image(self) -> QImage:
        result = self._image.convertToFormat(QImage.Format.Format_ARGB32)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for shape in self._document.shapes():
            self._renderer.paint_shape(painter, shape)
        if self._preview is not None:
            self._renderer.paint_shape(painter, self._preview)
        painter.end()
        return result

    def copy_annotated_image(self) -> bool:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            QMessageBox.warning(self, tr("app.title"), tr("pinned.clipboard_unavailable"))
            return False
        clipboard.setImage(self.annotated_image())
        return True

    def save_annotated_image_as(self) -> bool:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("pinned.save_dialog_title"),
            str(Path.home() / "annotated_capture.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap Image (*.bmp)",
        )
        if not path:
            return False
        image_format = self._image_format_from_path(Path(path))
        ok = self.annotated_image().save(path, image_format)
        if not ok:
            QMessageBox.warning(self, tr("app.title"), tr("pinned.save_failed", path=path))
        return ok

    def _apply_click_through(self) -> None:
        if self.winId():
            set_click_through(int(self.winId()), self._click_through)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._click_through)

    def _activate_for_keyboard(self) -> None:
        if self._click_through:
            return
        self.activateWindow()
        self.setFocus(Qt.FocusReason.MouseFocusReason)

    def _paint_annotations(self, painter: QPainter, target: QRect) -> None:
        if self._document.is_empty() and self._preview is None:
            return
        painter.save()
        scale_x = target.width() / max(1, self._image.width())
        scale_y = target.height() / max(1, self._image.height())
        painter.translate(target.left(), target.top())
        painter.scale(scale_x, scale_y)
        for shape in self._document.shapes():
            self._renderer.paint_shape(painter, shape)
        if self._preview is not None:
            self._renderer.paint_shape(painter, self._preview)
        painter.restore()

    def _pointer_event(self, event) -> PointerEvent:
        return PointerEvent(
            position=self._window_to_image_point(event.position().toPoint()),
            timestamp_ms=0,
            shift=bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier),
            alt=bool(event.modifiers() & Qt.KeyboardModifier.AltModifier),
        )

    def _window_to_image_point(self, point: QPoint) -> QPoint:
        target = self._image_target_rect()
        x = min(max(point.x(), target.left()), target.right())
        y = min(max(point.y(), target.top()), target.bottom())
        image_x = round((x - target.left()) * self._image.width() / max(1, target.width()))
        image_y = round((y - target.top()) * self._image.height() / max(1, target.height()))
        return QPoint(image_x, image_y)

    def _image_rect_to_window(self, rect: QRect) -> QRect:
        target = self._image_target_rect()
        scale_x = target.width() / max(1, self._image.width())
        scale_y = target.height() / max(1, self._image.height())
        return QRect(
            target.left() + round(rect.left() * scale_x),
            target.top() + round(rect.top() * scale_y),
            max(1, round(rect.width() * scale_x)),
            max(1, round(rect.height() * scale_y)),
        )

    def _image_target_rect(self) -> QRect:
        size = self._image.size().scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        return QRect(
            (self.width() - size.width()) // 2,
            (self.height() - size.height()) // 2,
            size.width(),
            size.height(),
        )

    def _active_drawing_settings(self) -> DrawingSettings:
        width = self._current_width
        if self._current_tool == "eraser" and self._eraser_settings.mode == "pixel":
            width = max(1, self._eraser_settings.size)
        return replace(
            self._drawing_settings,
            default_tool=self._current_tool,
            color=self._current_color,
            width=width,
            line_style=self._current_line_style,
        )

    def _position_toolbar(self) -> None:
        if self._toolbar_user_positioned:
            self._toolbar.ensure_inside_available()
            return
        self._toolbar.move_near(self.frameGeometry())

    def _annotation_toolbar_moved(self, _window=None) -> None:
        self._toolbar_user_positioned = True

    def _sync_toolbar_state(self) -> None:
        self._toolbar.set_action_state(
            can_undo=not self._document.is_empty(),
            can_redo=self._document.can_redo(),
        )

    def _scaled_size(self) -> QSize:
        return QSize(
            max(80, round(self._display_size.width() * self._zoom)),
            max(60, round(self._display_size.height() * self._zoom)),
        )

    @staticmethod
    def _image_format_from_path(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            return "JPEG"
        if suffix == ".bmp":
            return "BMP"
        return "PNG"
