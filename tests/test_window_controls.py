from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowControlsTest(unittest.TestCase):
    def _class_methods(self, relative_path: str, class_name: str) -> set[str]:
        tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
        self.fail(f"{class_name} not found in {relative_path}")

    def _source(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_pinned_window_has_close_and_menu_controls(self) -> None:
        methods = self._class_methods("pinned/window.py", "PinnedWindow")
        self.assertIn("keyPressEvent", methods)
        self.assertIn("contextMenuEvent", methods)
        self.assertIn("set_click_through", methods)
        self.assertIn("set_annotation_mode", methods)
        self.assertIn("set_annotation_tool", methods)
        self.assertIn("set_annotation_style", methods)
        self.assertIn("undo_annotation", methods)
        self.assertIn("redo_annotation", methods)
        self.assertIn("clear_annotations", methods)
        self.assertIn("annotated_image", methods)
        self.assertIn("copy_annotated_image", methods)
        self.assertIn("save_annotated_image_as", methods)
        source = self._source("pinned/window.py")
        self.assertIn("QShortcut", source)
        self.assertIn("StrongFocus", source)
        self.assertIn("_activate_for_keyboard", source)
        self.assertIn("DrawingDocument", source)
        self.assertIn("AnnotationToolbar", source)
        self.assertIn('tr("pinned.annotation_mode")', source)
        self.assertIn('tr("pinned.copy_annotated")', source)
        self.assertIn('tr("pinned.save_annotated")', source)
        self.assertIn("QGuiApplication.clipboard", source)
        self.assertIn("QFileDialog.getSaveFileName", source)
        self.assertIn("_window_to_image_point", source)
        self.assertIn("_position_toolbar", source)
        self.assertIn("closeEvent", methods)

    def test_live_window_matches_pinned_window_controls(self) -> None:
        methods = self._class_methods("live_view/window.py", "LiveViewWindow")
        self.assertIn("keyPressEvent", methods)
        self.assertIn("contextMenuEvent", methods)
        self.assertIn("set_click_through", methods)
        self.assertIn("set_fps", methods)
        self.assertIn("set_paused", methods)
        self.assertIn("toggle_pause", methods)
        self.assertIn("pin_current_frame", methods)
        source = self._source("live_view/window.py")
        self.assertIn("QShortcut", source)
        self.assertIn("StrongFocus", source)
        self.assertIn("_activate_for_keyboard", source)
        self.assertIn("FPS_PRESETS = (1, 5, 10, 15, 30)", source)
        self.assertIn("pin.image", source)

    def test_click_through_disables_noactivate_when_input_is_enabled(self) -> None:
        source = self._source("utils/winapi.py")
        self.assertIn("WS_EX_TRANSPARENT | WS_EX_NOACTIVATE", source)
        self.assertIn("style &= ~WS_EX_NOACTIVATE", source)
        self.assertIn("SWP_FRAMECHANGED", source)

    def test_drawing_overlay_blocks_underlying_mouse_input(self) -> None:
        overlay = self._source("overlay/window.py")
        hook = self._source("mouse/hook.py")
        winapi = self._source("utils/winapi.py")

        self.assertIn("_create_pen_cursor", overlay)
        self.assertIn("setCursor(self._pen_cursor)", overlay)
        self.assertIn("unsetCursor()", overlay)
        self.assertIn("setOverrideCursor", overlay)
        self.assertIn("restoreOverrideCursor", overlay)
        self.assertIn("_override_cursor_active", overlay)
        self.assertIn('"drawing.style.change"', overlay)
        self.assertIn("_update_pen_cursor", overlay)
        self.assertIn("ScreenCoordinateMapper", overlay)
        self.assertNotIn("screenAt(QPoint(0, 0))", overlay)
        self.assertIn("QColor(color)", overlay)
        self.assertIn("_paint_input_capture_surface", overlay)
        self.assertIn("QColor(0, 0, 0, 1)", overlay)
        self.assertIn("overlay.capture_visuals.suspended", overlay)
        self.assertIn("_capture_visual_suppressions", overlay)
        self.assertIn('"overlay.input_mode.changed"', overlay)
        self.assertIn('"overlay.input_mode.changed"', hook)
        self.assertIn("_should_block", hook)
        self.assertIn("return 1", hook)
        self.assertIn("window_from_point(event.x, event.y) in self._overlay_hwnds", hook)
        self.assertIn("mouse.input_exclusion.changed", hook)
        self.assertIn("mouse.blocking.suspended", hook)
        self.assertIn("_is_inside_input_exclusion", hook)
        self.assertIn("WindowFromPoint", winapi)

    def test_drawing_toolbar_registers_mouse_input_exclusion(self) -> None:
        toolbar = self._source("ui/drawing_toolbar.py")
        floating = self._source("ui/floating_tool_window.py")

        self.assertIn("input_geometry_changed", floating)
        self.assertIn("mouse.input_exclusion.changed", toolbar)
        self.assertIn("mouse.blocking.suspended", toolbar)
        self.assertIn("ScreenCoordinateMapper", toolbar)
        self.assertIn("qt_to_physical_rect(self._window.frameGeometry())", toolbar)
        self.assertNotIn("devicePixelRatio() if screen is not None", toolbar)

    def test_capture_fallback_paths_convert_between_qt_and_physical_coordinates(self) -> None:
        capture_manager = self._source("capture/manager.py")
        gdi = self._source("capture/gdi.py")
        region_selection = self._source("capture/region_selection.py")

        self.assertIn("qt_to_physical_point(QCursor.pos())", capture_manager)
        self.assertNotIn("QGuiApplication", gdi)
        self.assertNotIn("grabWindow", gdi)
        self.assertNotIn("CAPTUREBLT", gdi)
        self.assertIn("SRCCOPY,", gdi)
        self.assertIn('raise OSError("BitBlt failed")', gdi)
        self.assertIn("physical_rect = self._coordinates.qt_to_physical_rect", region_selection)
        self.assertIn("physical_rect.width()", region_selection)
        self.assertIn("QTimer.singleShot(50", capture_manager)
        self.assertIn('"overlay.capture_visuals.suspended"', capture_manager)

    def test_capture_windows_open_at_visual_selection_size(self) -> None:
        pinned_manager = self._source("pinned/manager.py")
        pinned_window = self._source("pinned/window.py")
        live_window = self._source("live_view/window.py")

        self.assertIn("_display_size_for_rect", pinned_manager)
        self.assertIn("physical_to_qt_rect(rect).size()", pinned_manager)
        self.assertIn('event.payload.get("display_size")', pinned_manager)
        self.assertIn("display_size if isinstance(display_size, QSize) else None", pinned_manager)
        self.assertIn("display_size: QSize | None = None", pinned_window)
        self.assertIn("self._display_size = display_size or image.size()", pinned_window)
        self.assertIn("self._display_rect = self._coordinates.physical_to_qt_rect(self.source_rect)", live_window)
        self.assertIn("self._display_rect.width()", live_window)
        self.assertIn("display_size=QSize(self.size())", live_window)
        self.assertIn("painter.drawImage(target, self._image)", pinned_window)
        self.assertIn("painter.drawImage(self._image_target_rect(), self._latest_image)", live_window)
        self.assertNotIn("QPixmap.fromImage(self._image).scaled", pinned_window)
        self.assertNotIn("QPixmap.fromImage(self._latest_image).scaled", live_window)

    def test_pinned_and_live_captures_suppress_click_visuals(self) -> None:
        pinned_manager = self._source("pinned/manager.py")
        live_manager = self._source("live_view/manager.py")

        self.assertIn('"overlay.capture_visuals.suspended"', pinned_manager)
        self.assertIn('source="pinned_capture"', pinned_manager)
        self.assertIn("QTimer.singleShot(50", pinned_manager)
        self.assertIn("_capture_selected_region", pinned_manager)
        self.assertIn('"overlay.capture_visuals.suspended"', live_manager)
        self.assertIn('source="live_view"', live_manager)
        self.assertIn("_start_window", live_manager)

    def test_pinned_manager_accepts_images_from_other_features(self) -> None:
        methods = self._class_methods("pinned/manager.py", "PinnedWindowManager")
        source = self._source("pinned/manager.py")
        self.assertIn("_pin_image", methods)
        self.assertIn('self.bus.subscribe("pin.image", self._pin_image)', source)

    def test_service_container_owns_drawing_toolbar(self) -> None:
        source = self._source("application/service_container.py")
        self.assertIn("DrawingToolbar", source)
        self.assertIn("drawing_toolbar", source)
        self.assertIn("ToolbarPositionStore", source)
        self.assertIn("toolbar_position_store", source)


if __name__ == "__main__":
    unittest.main()
