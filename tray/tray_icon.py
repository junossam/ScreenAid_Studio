from __future__ import annotations

import ctypes
from pathlib import Path

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QCoreApplication, Qt
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId
from config.settings import Settings
from core.event_bus import Event, EventBus, Subscription
from core.localization import tr
from core.service import Service
from utils.winapi import register_window_message


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]


class _TaskbarCreatedFilter(QAbstractNativeEventFilter):
    def __init__(self, tray: "TrayIcon") -> None:
        super().__init__()
        self.tray = tray

    def nativeEventFilter(self, _event_type: QByteArray, message: int):
        msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
        if msg.message == self.tray.taskbar_created_message:
            self.tray.restore_after_taskbar_created()
        return False, 0


class TrayIcon(Service):
    def __init__(self, settings: Settings, bus: EventBus, dispatcher: CommandDispatcher, base_dir: Path) -> None:
        self.settings = settings
        self.bus = bus
        self.dispatcher = dispatcher
        self.base_dir = base_dir
        self._tray = QSystemTrayIcon()
        self._menu = QMenu()
        self._pause_action: QAction | None = None
        self._subscriptions: list[Subscription] = []
        self._paused = False
        self._drawing = False
        self._click_effects_visible = True
        self._taskbar_created_message = register_window_message("TaskbarCreated")
        self._taskbar_filter = _TaskbarCreatedFilter(self)
        self._filter_installed = False
        self._tray.activated.connect(self._handle_activation)

    def start(self) -> None:
        self._menu.clear()
        self._pause_action = self._action(tr("tray.pause_all"), CommandId.TOGGLE_PAUSE)
        self._pause_action.setCheckable(True)
        self._menu.addAction(self._pause_action)
        self._menu.addSeparator()
        self._menu.addAction(self._action(tr("tray.toggle_overlay"), CommandId.TOGGLE_OVERLAY))
        self._menu.addAction(self._action(tr("tray.toggle_drawing_mode"), CommandId.TOGGLE_DRAWING_MODE))
        self._menu.addAction(self._action(tr("tray.input_pass_through"), CommandId.DRAWING_PASS_THROUGH))
        self._menu.addAction(self._action(tr("tray.undo_drawing"), CommandId.UNDO_DRAWING))
        self._menu.addAction(self._action(tr("tray.redo_drawing"), CommandId.REDO_DRAWING))
        self._menu.addAction(self._action(tr("tray.clear_drawing"), CommandId.CLEAR_DRAWING))
        self._menu.addAction(self._action(tr("tray.settings"), CommandId.OPEN_SETTINGS))
        self._menu.addAction(self._action(tr("tray.open_manual"), CommandId.OPEN_USER_MANUAL))
        self._menu.addSeparator()
        self._menu.addAction(self._action(tr("tray.capture_region"), CommandId.CAPTURE_REGION))
        self._menu.addAction(self._action(tr("tray.capture_last_region"), CommandId.CAPTURE_LAST_REGION))
        self._menu.addAction(self._action(tr("tray.capture_current_monitor"), CommandId.CAPTURE_CURRENT_MONITOR))
        self._menu.addAction(self._action(tr("tray.capture_virtual_screen"), CommandId.CAPTURE_VIRTUAL_SCREEN))
        self._menu.addAction(self._action(tr("tray.capture_active_window"), CommandId.CAPTURE_ACTIVE_WINDOW))
        self._menu.addAction(self._action(tr("tray.pin_region"), CommandId.PIN_REGION))
        self._menu.addAction(self._action(tr("tray.pin_last_capture"), CommandId.PIN_LAST_CAPTURE))
        self._menu.addSeparator()
        self._menu.addAction(self._action(tr("tray.start_live_region"), CommandId.LIVE_REGION))
        self._menu.addAction(self._action(tr("tray.stop_live_views"), CommandId.LIVE_STOP_ALL))
        self._menu.addSeparator()
        self._menu.addAction(self._action(tr("tray.quit"), CommandId.QUIT_APPLICATION))
        self._tray.setContextMenu(self._menu)
        self._install_native_filter()
        if not self._subscriptions:
            self._subscriptions = [
                self.bus.subscribe("capture.completed", self._capture_completed),
                self.bus.subscribe("capture.failed", self._capture_failed),
                self.bus.subscribe("hotkey.failed", self._hotkey_failed),
                self.bus.subscribe("pin.failed", self._pin_failed),
                self.bus.subscribe("live.failed", self._live_failed),
                self.bus.subscribe("drawing.mode.changed", self._drawing_mode_changed),
                self.bus.subscribe("app.pause.changed", self._pause_changed),
                self.bus.subscribe("app.command.blocked", self._command_blocked),
                self.bus.subscribe("click_effects.temp.changed", self._click_effects_changed),
                self.bus.subscribe("manual.failed", self._manual_failed),
            ]
        self._restore_tray_icon()

    def stop(self) -> None:
        self._remove_native_filter()
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._tray.hide()

    @property
    def taskbar_created_message(self) -> int:
        return self._taskbar_created_message

    def restore_after_taskbar_created(self) -> None:
        self._restore_tray_icon()

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.dispatcher.dispatch(CommandId.OPEN_SETTINGS)
            return
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self._show_menu()

    def _show_menu(self) -> None:
        self._menu.popup(QCursor.pos())

    def _action(self, text: str, command_id: CommandId) -> QAction:
        action = QAction(text, self._menu)
        action.triggered.connect(lambda: self.dispatcher.dispatch(command_id))
        return action

    def _install_native_filter(self) -> None:
        if self._filter_installed:
            return
        app = QCoreApplication.instance()
        if app is not None:
            app.installNativeEventFilter(self._taskbar_filter)
            self._filter_installed = True

    def _remove_native_filter(self) -> None:
        if not self._filter_installed:
            return
        app = QCoreApplication.instance()
        if app is not None:
            app.removeNativeEventFilter(self._taskbar_filter)
        self._filter_installed = False

    def _restore_tray_icon(self) -> None:
        self._tray.setContextMenu(self._menu)
        self._refresh_status()
        self._tray.show()

    def _icon(self) -> QIcon:
        icon_path = self.base_dir / "resources" / "tray_icon.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#00a6ff"), 3))
        painter.drawEllipse(6, 6, 20, 20)
        painter.setPen(QPen(QColor("#ff3b30"), 3))
        painter.drawLine(16, 9, 16, 23)
        painter.drawLine(9, 16, 23, 16)
        painter.end()
        return QIcon(pixmap)

    def _status_icon(self) -> QIcon:
        pixmap = self._icon().pixmap(32, 32)
        if pixmap.isNull():
            return self._icon()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        badges = self._status_badges()
        for index, (color, text) in enumerate(badges[:3]):
            x = 19 - index * 10
            y = 19
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QColor(color))
            painter.drawEllipse(x, y, 12, 12)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(x, y - 1, 12, 14, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return QIcon(pixmap)

    def _status_badges(self) -> list[tuple[str, str]]:
        badges = []
        if self._paused:
            badges.append(("#ff3b30", "P"))
        if self._drawing:
            badges.append(("#0a84ff", "D"))
        if not self._click_effects_visible:
            badges.append(("#ff9f0a", "C"))
        return badges

    def _status_texts(self) -> list[str]:
        statuses = []
        if self._paused:
            statuses.append(tr("status.paused"))
        if self._drawing:
            statuses.append(tr("status.drawing"))
        if not self._click_effects_visible:
            statuses.append(tr("status.click_effects_hidden"))
        return statuses or [tr("status.normal")]

    def _refresh_status(self) -> None:
        self._tray.setIcon(self._status_icon())
        self._tray.setToolTip(f"{tr('app.title')}({', '.join(self._status_texts())})")

    def _capture_completed(self, event: Event) -> None:
        if not self.settings.capture.show_notification:
            return
        result = event.payload["result"]
        message = tr("notify.capture_completed", width=result.width, height=result.height)
        if event.payload.get("copied"):
            message += f" {tr('notify.to_clipboard')}"
        saved_path = event.payload.get("saved_path")
        if saved_path:
            message += f"\n{tr('notify.saved', path=saved_path)}"
        self._tray.showMessage(tr("app.title"), message, QSystemTrayIcon.MessageIcon.Information, 1800)

    def _capture_failed(self, event: Event) -> None:
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.capture_failed", error=event.payload.get("error", "unknown error")),
            QSystemTrayIcon.MessageIcon.Warning,
            2200,
        )

    def _hotkey_failed(self, event: Event) -> None:
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.hotkey_failed", error=event.payload.get("error", "unknown error")),
            QSystemTrayIcon.MessageIcon.Warning,
            2600,
        )

    def _pin_failed(self, event: Event) -> None:
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.pin_failed", error=event.payload.get("error", "unknown error")),
            QSystemTrayIcon.MessageIcon.Warning,
            2200,
        )

    def _live_failed(self, event: Event) -> None:
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.live_failed", error=event.payload.get("error", "unknown error")),
            QSystemTrayIcon.MessageIcon.Warning,
            2200,
        )

    def _drawing_mode_changed(self, event: Event) -> None:
        pass_through = event.payload.get("pass_through", True)
        self._drawing = not pass_through
        self._refresh_status()
        message = tr("notify.input_pass_through") if pass_through else tr("notify.drawing_mode")
        self._tray.showMessage(
            tr("app.title"),
            message,
            QSystemTrayIcon.MessageIcon.Information,
            1200,
        )

    def _pause_changed(self, event: Event) -> None:
        paused = bool(event.payload.get("paused", False))
        self._paused = paused
        if paused:
            self._drawing = False
        if self._pause_action is not None:
            self._pause_action.setChecked(paused)
            self._pause_action.setText(tr("tray.resume_all") if paused else tr("tray.pause_all"))
        self._refresh_status()
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.paused") if paused else tr("notify.resumed"),
            QSystemTrayIcon.MessageIcon.Information,
            1200,
        )

    def _command_blocked(self, event: Event) -> None:
        self._tray.showMessage(
            tr("app.title"),
            event.payload.get("reason", tr("notify.command_blocked")),
            QSystemTrayIcon.MessageIcon.Information,
            1200,
        )

    def _click_effects_changed(self, event: Event) -> None:
        enabled = bool(event.payload.get("enabled", True))
        self._click_effects_visible = enabled
        self._refresh_status()
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.click_effects_enabled") if enabled else tr("notify.click_effects_disabled"),
            QSystemTrayIcon.MessageIcon.Information,
            1200,
        )

    def _manual_failed(self, event: Event) -> None:
        self._tray.showMessage(
            tr("app.title"),
            tr("notify.manual_failed", error=event.payload.get("error", "unknown error")),
            QSystemTrayIcon.MessageIcon.Warning,
            2200,
        )
