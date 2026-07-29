# Requirements Traceability

This table is the working traceability baseline for the first implementation
stage. Manual Windows results must be filled during release verification.

| Requirement ID | Requirement | Implementation | Test ID | Status |
| --- | --- | --- | --- | --- |
| FR-CLICK-001 | Show click indicators without blocking input | `overlay.window`, `overlay.effects`, `mouse.events` | TC-CLICK-001 | automated partial |
| FR-CLICK-002 | Show bundled PNG click images with vector fallback | `resources.click_indicators`, `overlay.window` | TC-RES-001 | automated |
| FR-CLICK-003 | Detect basic left double-click and left-right combined click | `overlay.effects` | TC-CLICK-002 | automated |
| FR-CLICK-004 | Select click indicator categories independently and apply changes immediately | `ui.settings_dialog`, `overlay.window`, `config.settings` | TC-CLICK-004 | automated partial |
| FR-DRAW-001 | Draw screen annotations with undoable document state | `drawing.document`, `drawing.tools`, `drawing.controller` | TC-DRAW-001 | automated partial |
| FR-DRAW-002 | Support freehand, highlighter, line, arrow, rectangle, and ellipse tools | `drawing.tools`, `drawing.renderer` | TC-DRAW-002 | automated partial |
| FR-DRAW-003 | Undo and redo drawing shapes | `drawing.document`, `drawing.controller` | TC-DRAW-003 | automated |
| FR-DRAW-004 | Erase drawing objects by hit area or erase the passed path in pixel mode | `drawing.document`, `drawing.controller`, `drawing.renderer` | TC-DRAW-004, TC-DRAW-005 | automated |
| FR-DRAW-005 | Select drawing tools and stroke style from a draggable icon toolbar | `ui.drawing_toolbar`, `ui.tool_icons`, `ui.floating_tool_window`, `drawing.controller` | TC-DRAW-005 | automated partial |
| FR-DRAW-006 | Block underlying application mouse input while drawing mode is active | `overlay.window`, `mouse.hook`, `utils.winapi` | TC-DRAW-006 | automated partial |
| FR-CAP-001 | Capture a requested screen region | `capture.manager`, `capture.gdi`, `capture.models` | TC-CAP-001 | automated partial |
| FR-PIN-001 | Open captured image as a static pinned window | `pinned.manager`, `pinned.window` | TC-PIN-001 | manual smoke |
| FR-PIN-002 | Support pinned-window zoom and click-through | `pinned.window` | TC-PIN-002 | manual smoke |
| FR-PIN-003 | Draw styled independent annotations inside pinned windows with an unclipped draggable icon toolbar | `pinned.window`, `ui.annotation_toolbar`, `ui.tool_icons`, `ui.floating_tool_window`, `drawing.document`, `drawing.tools`, `drawing.renderer` | TC-PIN-003 | automated partial |
| FR-PIN-004 | Export pinned-window annotations to clipboard or image file | `pinned.window` | TC-PIN-004 | automated partial |
| FR-LIVE-001 | Open a selected live view region with a worker-backed queue-size-1 capture policy | `live_view.manager`, `live_view.window`, `live_view.worker` | TC-LIVE-001 | automated partial |
| FR-PAUSE-001 | Pause and resume assistive features without exiting | `core.app_controller`, `overlay.window`, `live_view.manager`, `tray.tray_icon`, `core.hotkeys` | TC-PAUSE-001 | automated partial |
| FR-I18N-001 | Support Korean and English UI strings with file-based language extension | `core.localization`, `locales`, `ui.settings_dialog`, `tray.tray_icon`, `pinned.window`, `live_view.window`, `ui.drawing_toolbar`, `ui.annotation_toolbar` | TC-I18N-001 | automated partial |
| FR-TRAY-001 | Dispatch commands from tray and configurable hotkeys | `tray.tray_icon`, `core.hotkeys`, `application.command_dispatcher`, `ui.settings_dialog` | TC-TRAY-001 | automated partial |
| FR-SET-001 | Open a scrollable multi-tab settings window and atomically save INI values | `ui.settings_dialog`, `ui.settings_manager`, `services.settings.settings_manager` | TC-SET-002 | automated partial |
| OPS-START-001 | Toggle current-user Windows autostart | `application.startup`, `ui.settings_dialog` | TC-START-001 | manual smoke |
| NFR-REL-001 | Isolate feature errors | `core.event_bus`, `application.command_dispatcher` | RT-REL-001 | automated |
| NFR-PRIV-001 | Do not create runtime log files or persist sensitive input data | `app`, `application.app_paths`, `services.diagnostics.performance` | ST-PRIV-001 | automated partial |
| NFR-PERF-001 | Measure performance without polling overhead | `services.diagnostics.performance` | PT-PERF-001 | automated |
| NFR-SET-001 | Recover safely from invalid settings | `services.settings.settings_manager`, `config.settings` | TC-SET-001 | automated partial |
| OPS-PATH-001 | Store settings in configurable portable or AppData locations, with portable as the default | `application.app_paths`, `services.settings.settings_manager`, `ui.settings_dialog`, `app` | TC-PATH-001 | automated |
| OPS-SINGLE-001 | Prevent duplicate running instances | `core.single_instance`, `app` | RV-SINGLE-001 | manual smoke |
| NFR-HOOK-001 | Keep hook callbacks lightweight and avoid direct UI calls | `mouse.hook` | RV-HOOK-001 | code reviewed |
| NFR-LIFE-001 | Unsubscribe feature event handlers during stop | `drawing.controller`, `capture.manager`, `tray.tray_icon` | RT-LIFE-001 | code reviewed |
| QA-GATE-001 | Run repeatable quality checks before release | `tools.quality_gate` | QA-GATE-001 | automated |

## Current Gap Summary

The following first-release SRS items are not fully implemented yet and must not
be marked as accepted:

- Full advanced preview pages.
- Packaged installer validation.
- Full Windows 10, Windows 11, multi-monitor, and mixed-DPI manual evidence.

## Test Case Format

Each release test case should record:

- Test ID
- Purpose
- Related requirements
- Preconditions
- Test environment
- Steps
- Expected result
- Actual result
- Pass or fail
- Evidence
- Defect ID
- Notes

## Trace Status

Use these states: `not started`, `designed`, `implementing`, `implemented`,
`testing`, `verified`, `deferred`, `excluded`.

Deferred or excluded items require a target version and reason.
