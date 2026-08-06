# Roadmap

이 문서는 개발 상태를 빠르게 파악하기 위한 내부 로드맵입니다. 사용자 명세서 역할은 하지 않습니다.

## Completed Core

- Tray app and single-instance guard
- Per Monitor DPI awareness
- Settings manager and portable mode
- Localization: Korean and English
- Command mode and configurable hotkeys
- Global mouse hook
- Click indicators with drag-follow and fade-out
- Transparent overlay and drawing mode
- Drawing tools: pen, highlighter, line, rectangle, ellipse, arrow, stamp, eraser
- Region, monitor, virtual screen, and active window capture
- Last capture save command
- Pinned capture windows
- Worker-based live region view with queue size 1
- Current-screen fullscreen magnifier with drawing support
- Windows Magnification API based live fullscreen magnifier
- Notification settings
- Developer diagnostics via `developer.log`
- PyInstaller folder distribution support
- User manual included in `docs`

## Stabilization Focus

- Manual verification on Windows 10 and Windows 11
- Multi-monitor and mixed-DPI regression checks
- Portable EXE verification on machines without Python
- Windows Magnification API input behavior across UIAccess environments
- Long-run idle CPU and memory checks
- Capture quality and excluded overlay regression checks

## Later Ideas

- Screen recording
- OCR
- Presentation timer
- Laser pointer mode
- Webcam overlay
- AI-assisted annotation tools
