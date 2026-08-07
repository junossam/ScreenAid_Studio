# Release Policy

ScreenAid Studio cannot be released while any blocker below is unresolved.

## Release Blockers

- Critical defects.
- Any chance of permanently blocking normal mouse or keyboard input.
- Hook or hotkey release failure on shutdown.
- Process, worker, timer, bitmap, DC, or window resource left behind after exit.
- Corrupt settings that prevent startup.
- Repeated memory, GDI, USER handle, or thread growth.
- Capture UI, click indicator, or helper overlay included unexpectedly in captured images.
- Major multi-monitor or mixed-DPI coordinate errors.
- Unbounded live-frame or work queues.
- Runtime log file creation in normal user mode.
- Sensitive data persisted without explicit user action.
- Network activity without user consent.
- Missing required package resources, locales, or documents.
- Failed core user acceptance scenario.

## Automatic Gate

Run:

```powershell
python -m unittest discover -s tests
python -m compileall .
```

Required checks:

- Unit and integration-style tests with `unittest`.
- Python bytecode compilation with `compileall`.

Optional checks, when those modules are installed:

```powershell
ruff check .
mypy .
```

Missing optional modules are reported as skipped, not as release approval.

## Manual Release Checklist

Feature:

- [ ] Click indicator
- [ ] Drawing
- [ ] Capture
- [ ] Last capture save command
- [ ] Pinned window
- [ ] Live region window
- [ ] Current-screen fullscreen magnifier
- [ ] Tray
- [ ] Hotkeys and command mode
- [ ] Settings
- [ ] Notifications
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
- [ ] Portable EXE on a machine without Python

Distribution:

- [ ] PyInstaller folder distribution
- [ ] `dist\ScreenAidStudio\ScreenAidStudio.exe`
- [ ] Console window hidden
- [ ] No administrator privilege prompt
- [ ] `resources\tray_icon.ico` applied
- [ ] `portable.flag` included
- [ ] `docs` user manual included
- [ ] User manual opens from tray menu
- [ ] User manual opens from settings program information tab
- [ ] `locales\ko.ini` and `locales\en.ini` load as UTF-8

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

The first stable release requires all core automatic checks to pass, all release blockers to be closed, and Windows manual results to be recorded in this file or an attached release note.
