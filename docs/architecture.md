# Architecture

ScreenAid Studio follows a small service-oriented architecture.

## Layers

- Presentation: tray menu, overlays, notifications, selection UI.
- Application: command dispatch, state store, service container, app controller.
- Domain: mouse events, drawing shapes, capture requests and results.
- Infrastructure: GDI capture, clipboard, and image saving.
- Platform: centralized Windows API declarations in `utils/winapi.py`.
- Localization: file-based language resources in `locales/*.ini` loaded through `core.localization`.

## Command And Event Flow

User intent enters through `CommandDispatcher`. Tray actions and global hotkeys dispatch commands such as `capture.region` or `drawing.mode.toggle`.

`EventBus` is reserved for facts and internal notifications, such as `capture.completed`, `capture.failed`, and drawing preview changes. Some capture and drawing services still use legacy command-like event names internally; those will be migrated incrementally without breaking the running app.

## Service Lifetime

`ServiceContainer` builds the core services. `AppController` starts and stops them in dependency order:

1. drawing and capture controllers
2. overlays
3. mouse hook
4. hotkeys
5. tray UI

Shutdown reverses the order and releases hotkeys, hooks, selection overlays, tray, and overlay windows.

## Current Limits

- `SettingsManager` is still represented by `config.Settings.load`.
- Windows platform APIs are centralized in `utils/winapi.py`; they are not yet split into `platform/windows/*`.
- Global pause/resume is implemented through `app.pause.changed`; plugin isolation is still planned.
