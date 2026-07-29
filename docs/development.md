# Development

## Environment

- Windows 10 or Windows 11, 64-bit
- Python `>=3.12,<3.14`
- PowerShell

Recommended setup:

```powershell
cd ScreenAssistant
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Dependency Policy

Add a dependency only when the standard library or existing project dependencies are not enough. Windows API work should prefer `ctypes` unless a later module explicitly chooses `pywin32`.

Current runtime dependency:

- `PySide6`: UI, tray, overlays, Qt event loop.

Optional dependencies:

- `mss`, `Pillow`: future capture/live-view and static image processing paths.

## Quality Checks

```powershell
python -m unittest discover -s tests
python -m compileall .
ruff check .
mypy .
```

`ruff` and `mypy` require the `dev` optional dependencies.
