# Testing

## Automatic Tests

Run:

```powershell
cd ScreenAssistant
python -m unittest discover -s tests
python -m compileall .
```

The project also defines pytest settings, so this is valid when `pytest` is installed:

```powershell
pytest
```

## Manual Smoke Tests

1. Run `python main.py`.
2. Confirm the tray icon appears.
3. Open command mode with `Ctrl+Alt+A`.
4. Press `D` to toggle drawing mode.
5. Open command mode again and press `P` to return to input pass-through.
6. Open command mode again and press `R` to capture a region.
7. Open command mode again and press `K` to pin a selected region.
8. Open command mode again and press `X` to stop live views if any are open.
9. Confirm the selected overlay is not present in the capture.
10. Quit from the tray menu.
11. Confirm the process exits and hotkeys are released.

## Performance Checks

For each feature stage, record:

- Idle CPU
- Memory
- Thread count
- GDI and USER handle count when native resources are involved
- Capture duration for representative regions

## Release Verification

Use [traceability.md](traceability.md) to confirm every requirement has an
implementation and verification path.

Use [release.md](release.md) for blocker checks and manual Windows release
approval.
