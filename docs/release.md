# Release Policy

ScreenAid Studio cannot be released while any blocker below is unresolved.

## Release Blockers

- Critical defects.
- Any chance of blocking normal mouse or keyboard input.
- Hook or hotkey release failure on shutdown.
- Process, worker, timer, bitmap, DC, or window resource left behind after exit.
- Corrupt settings that prevent startup.
- Repeated memory, GDI, USER handle, or thread growth.
- Capture UI included in the captured image.
- Major multi-monitor or mixed-DPI coordinate errors.
- Unbounded live-frame or work queues.
- Runtime log file creation.
- Sensitive data persisted without explicit user action.
- Network activity without user consent.
- Missing required package resources or documents.
- Failed core user acceptance scenario.

## Automatic Gate

Run:

```powershell
python tools\quality_gate.py
```

Required checks:

- Forbidden source pattern scan.
- Unit and integration-style tests with `unittest`.
- Python bytecode compilation with `compileall`.

Optional full gate:

```powershell
python tools\quality_gate.py --full
```

`--full` also runs `ruff` and `mypy` when those modules are installed. Missing
optional modules are reported as skipped, not as release approval.

## Manual Release Checklist

Feature:

- [ ] Click indicator
- [ ] Drawing
- [ ] Capture
- [ ] Pinned window
- [ ] Live window
- [ ] Tray
- [ ] Hotkeys
- [ ] Settings
- [ ] Pause or pass-through recovery (`Ctrl+Alt+A` then `Space`, tray Pause All)
- [ ] Clean shutdown

Environment:

- [ ] Windows 10
- [ ] Windows 11
- [ ] Single monitor
- [ ] Multi-monitor
- [ ] Mixed DPI
- [ ] Negative monitor coordinates
- [ ] Portrait monitor
- [ ] Remote Desktop

Distribution:

- [ ] PyInstaller folder distribution
- [ ] `dist\ScreenAidStudio\ScreenAidStudio.exe`
- [ ] Console window hidden
- [ ] No administrator privilege prompt
- [ ] `resources\tray_icon.ico` applied
- [ ] `portable.flag` included
- [ ] `docs` user manual included
- [ ] User manual opens from tray menu
- [ ] User manual opens from settings Copyright/About tab

Quality:

- [ ] Automatic gate
- [ ] Regression set
- [ ] Performance measurements
- [ ] Long-run reliability test
- [ ] Security review
- [ ] Privacy review
- [ ] Accessibility review
- [ ] User acceptance test

## Acceptance Criteria

The first stable release requires all core automatic checks to pass, all release
blockers to be closed, and Windows manual results to be recorded in this file or
an attached release note.
