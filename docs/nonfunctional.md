# Nonfunctional Requirements

This document tracks the 8-1 SRS requirements that are enforced by the current
codebase.

## P0 Guards

- Overlay windows default to click-through except while drawing explicitly needs input.
- Capture is only started by a user command.
- `EventBus` isolates handler failures so one feature cannot stop later subscribers.
- `SettingsManager` backs up unreadable settings and falls back to defaults.
- Runtime logging is disabled; the app does not configure file or console log handlers.

## Privacy Rules

The app must not persist screen images, clipboard contents, typed text, private
URLs, passwords, tokens, API keys, mouse coordinates, or user names unless the
user explicitly saves or copies a capture.

No runtime log files are created.

## Performance Diagnostics

`PerformanceProbe` is disabled by default. When enabled by tests or development
code, it stores only in-memory allowlisted metadata:

- `operation`
- `duration_ms`
- `width`
- `height`
- `fps_target`
- `fps_actual`
- `frames_dropped`
- `backend`

The probe does not write logs, start threads, timers, capture loops, or polling.

## Verification

Run the automatic checks before integration:

```powershell
python -m unittest discover -s tests
python -m compileall .
```

Manual release checks still need real Windows hardware for idle CPU, memory,
GDI handles, hook lifecycle, clipboard behavior, DPI, and multi-monitor accuracy.
