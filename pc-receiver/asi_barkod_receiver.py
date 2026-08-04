#!/usr/bin/env python3
"""
Windows PC receiver for Asi Barkod Okuyucu.

Receives delivery-confirmed barcode payloads through Ably and writes them to
the currently focused Windows application, similar to a keyboard-wedge reader.
"""

from __future__ import annotations

import csv
import ctypes
import datetime as dt
import json
import os
import queue
import socket
import ssl
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
from dataclasses import dataclass
from typing import Any

import certifi

try:
    from cloud_bridge import CloudBridgeService, JobResult

    CLOUD_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CloudBridgeService = None  # type: ignore[assignment]
    JobResult = None  # type: ignore[assignment]
    CLOUD_AVAILABLE = False

try:
    import winsound
except ModuleNotFoundError:
    winsound = None  # type: ignore[assignment]

try:
    import qrcode

    QR_AVAILABLE = True
except ModuleNotFoundError:
    qrcode = None  # type: ignore[assignment]
    QR_AVAILABLE = False

try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk

    TRAY_AVAILABLE = True
except ModuleNotFoundError:
    pystray = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]
    TRAY_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import messagebox, ttk

    TK_AVAILABLE = True
except ModuleNotFoundError:
    tk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    TK_AVAILABLE = False


APP_VERSION = "0.5.0"
PWA_NAME = "Aşı Barkod PWA"
PWA_URL = "https://asi-barkod-pwa.vercel.app/"
PWA_RELEASE_URL = f"{PWA_URL.rstrip('/')}/api/release"
GITHUB_REPOSITORY = "hmatepad13/asi-barkod-okuyucu"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
RELEASES_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
GS = "\x1d"
DEFAULT_TEST_DATA = "010869983996110521K18115724Y5\x1d17280531102585Q004A\x1d999\x1d97001"
DEFAULT_GS_MODE = "f8"
DEFAULT_PREFIX_MODE = "none"
DEFAULT_KEY_DELAY_MS = 5
PREFIX_MODES = {"aim_datamatrix_gs1", "none"}
GS_MODES = {"f8", "unicode", "ctrl_right_bracket", "remove", "pipe", "text"}
SUFFIX_MODES = {"ENTER", "TAB", "NONE"}
INSTANCE_MUTEX_NAME = "Local\\AsiBarkodReceiver"
SHOW_WINDOW_EVENT_NAME = "Local\\AsiBarkodReceiverShowWindow"
_instance_mutex: Any = None
_show_window_event: Any = None


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    is_newer: bool
    download_url: str
    filename: str
    page_url: str
    notes: str


def version_key(value: str) -> tuple[int, ...]:
    core = value.strip().lstrip("vV").split("-", 1)[0]
    parts = core.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return ()
    return tuple(int(part) for part in parts)


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    candidate_key = version_key(candidate)
    current_key = version_key(current)
    if not candidate_key or not current_key:
        return False
    width = max(len(candidate_key), len(current_key))
    return candidate_key + (0,) * (width - len(candidate_key)) > current_key + (0,) * (width - len(current_key))


def format_release_notes(value: str, max_length: int = 1800) -> str:
    lines = []
    for raw_line in value.replace("\r", "").split("\n"):
        line = raw_line.strip()
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        return "Sürüm notu bulunmuyor."
    if len(text) > max_length:
        return text[: max_length - 3].rstrip() + "..."
    return text


def format_file_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def fetch_latest_release() -> UpdateInfo:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"AsiBarkodReceiver/{APP_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=8, context=github_ssl_context()) as response:
        payload = json.load(response)

    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        raise ValueError("GitHub sürüm bilgisi alınamadı")

    download_url = ""
    filename = ""
    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name.lower().endswith(".exe") and "windows-kurulum" in name.lower() and url:
            filename = os.path.basename(name)
            download_url = url
            break

    return UpdateInfo(
        version=tag.lstrip("vV"),
        is_newer=is_newer_version(tag),
        download_url=download_url,
        filename=filename,
        page_url=str(payload.get("html_url") or RELEASES_URL),
        notes=format_release_notes(str(payload.get("body") or "")),
    )


def github_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def fetch_pwa_release() -> str:
    request = urllib.request.Request(
        PWA_RELEASE_URL,
        headers={"Accept": "application/json", "User-Agent": f"AsiBarkodReceiver/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=8, context=github_ssl_context()) as response:
        payload = json.load(response)
    release = str(payload.get("release") or "").strip() if isinstance(payload, dict) else ""
    if not release:
        raise ValueError("PWA sürüm bilgisi alınamadı")
    return release


def play_success_beep() -> None:
    if winsound is None:
        return
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except RuntimeError:
        pass


def user_data_dir() -> str:
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "AsiBarkod")


def bundled_resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def receiver_id() -> str:
    path = os.path.join(user_data_dir(), "receiver_id.txt")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
            if value:
                return value
    except OSError:
        pass

    value = str(uuid.uuid4())
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(value)
    except OSError:
        fallback = f"{socket.gethostname()}-{uuid.getnode():012x}"
        return fallback
    return value


def settings_path() -> str:
    return os.path.join(user_data_dir(), "settings.json")


def sanitize_settings(payload: Any) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    suffix = str(payload.get("suffix", "ENTER")).upper()
    gs_mode = str(payload.get("gsMode", DEFAULT_GS_MODE)).lower()
    prefix_mode = str(payload.get("prefixMode", DEFAULT_PREFIX_MODE)).lower()
    return {
        "writeEnabled": bool(payload.get("writeEnabled", True)),
        "successSoundEnabled": bool(payload.get("successSoundEnabled", True)),
        "suffix": suffix if suffix in SUFFIX_MODES else "ENTER",
        "gsMode": gs_mode if gs_mode in GS_MODES else DEFAULT_GS_MODE,
        "prefixMode": prefix_mode if prefix_mode in PREFIX_MODES else DEFAULT_PREFIX_MODE,
    }


def load_settings() -> dict[str, Any]:
    try:
        with open(settings_path(), "r", encoding="utf-8") as handle:
            return sanitize_settings(json.load(handle))
    except (OSError, ValueError, TypeError):
        return sanitize_settings({})


def save_settings(payload: dict[str, Any]) -> None:
    path = settings_path()
    temp_path = f"{path}.tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(sanitize_settings(payload), handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


def visible_control_chars(value: str) -> str:
    return value.replace(GS, "<GS>")


def prefix_for_mode(mode: str) -> str:
    if mode == "aim_datamatrix_gs1":
        return "]d2"
    return ""


def csv_safe(value: str) -> str:
    return value.replace(GS, "\\x1d")


def event_to_dict(event: ScanEvent | None) -> dict[str, str] | None:
    if event is None:
        return None
    return {
        "data": event.data,
        "visibleData": visible_control_chars(event.data),
        "device": event.device,
        "format": event.fmt,
        "suffix": event.suffix,
        "source": event.source,
        "receivedAt": event.received_at,
    }


def test_event(data: str | None = None) -> ScanEvent:
    return ScanEvent(
        data=data or DEFAULT_TEST_DATA,
        device="PC test",
        fmt="DATA_MATRIX",
        suffix="",
        source="manual-test",
        received_at=dt.datetime.now().isoformat(timespec="seconds"),
    )


def ensure_logs_dir() -> str:
    path = os.path.join(user_data_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path


class KeyboardWriter:
    """Small SendInput wrapper. Windows only."""

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_MENU = 0x12
    VK_CAPITAL = 0x14
    VK_RETURN = 0x0D
    VK_TAB = 0x09
    VK_F8 = 0x77
    VK_OEM_6 = 0xDD  # ] key on US/Turkish-Q layouts

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", ctypes.c_ulong),
            ("wParamL", ctypes.c_ushort),
            ("wParamH", ctypes.c_ushort),
        ]

    class INPUT_UNION(ctypes.Union):
        pass

    class INPUT(ctypes.Structure):
        pass

    INPUT_UNION._fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]
    INPUT._fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("KeyboardWriter sadece Windows uzerinde calisir")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.SendInput.argtypes = (
            ctypes.c_uint,
            ctypes.POINTER(self.INPUT),
            ctypes.c_int,
        )
        self.user32.SendInput.restype = ctypes.c_uint
        self.user32.VkKeyScanW.argtypes = (ctypes.c_wchar,)
        self.user32.VkKeyScanW.restype = ctypes.c_short
        self.user32.GetKeyState.argtypes = (ctypes.c_int,)
        self.user32.GetKeyState.restype = ctypes.c_short

    def send_text(self, text: str, gs_mode: str) -> None:
        delay_seconds = DEFAULT_KEY_DELAY_MS / 1000.0
        caps_lock_on = bool(self.user32.GetKeyState(self.VK_CAPITAL) & 1)
        if caps_lock_on:
            self._send_vk(self.VK_CAPITAL)
        try:
            for ch in text:
                if ch == GS:
                    self._send_group_separator(gs_mode)
                else:
                    self._send_unicode_char(ch)
                if delay_seconds:
                    time.sleep(delay_seconds)
        finally:
            if caps_lock_on:
                self._send_vk(self.VK_CAPITAL)

    def send_suffix(self, suffix: str) -> None:
        suffix = suffix.upper().strip()
        if suffix == "ENTER":
            self._send_vk(self.VK_RETURN)
        elif suffix == "TAB":
            self._send_vk(self.VK_TAB)

    def _send_group_separator(self, gs_mode: str) -> None:
        mode = gs_mode.lower().strip()
        if mode == "f8":
            self._send_vk(self.VK_F8)
        elif mode == "unicode":
            self._send_unicode_char(GS)
        elif mode == "ctrl_right_bracket":
            self._send_ctrl_right_bracket()
        elif mode == "remove":
            return
        elif mode == "pipe":
            self._send_unicode_char("|")
        elif mode == "text":
            self.send_text("<GS>", "remove")
        else:
            self._send_vk(self.VK_F8)

    def _send_unicode_char(self, ch: str) -> None:
        code = ord(ch)

        # Harf ve rakamlari aktif klavye duzenine uygun sanal tus olarak gonder.
        if 32 <= code <= 126:
            vk_res = self.user32.VkKeyScanW(ch)
            if vk_res != -1:
                vk = vk_res & 0xFF
                modifiers = (vk_res >> 8) & 0xFF
                if not modifiers & ~0x07:
                    shift = bool(modifiers & 0x01)
                    control = bool(modifiers & 0x02)
                    alt = bool(modifiers & 0x04)
                    modifier_keys = []
                    if control:
                        modifier_keys.append(self.VK_CONTROL)
                    if alt:
                        modifier_keys.append(self.VK_MENU)
                    if shift:
                        modifier_keys.append(self.VK_SHIFT)

                    inputs_list = [self._keyboard_input(key) for key in modifier_keys]
                    inputs_list.extend((self._keyboard_input(vk), self._keyboard_input(vk, key_up=True)))
                    inputs_list.extend(self._keyboard_input(key, key_up=True) for key in reversed(modifier_keys))
                    arr = (self.INPUT * len(inputs_list))(*inputs_list)
                    self._send_inputs(arr)
                    return

        # Klavyede direkt karşılığı olmayan diğer karakterler için Unicode yöntemine (VK_PACKET) düş
        inputs = (self.INPUT * 2)(
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(
                    ki=self.KEYBDINPUT(0, code, self.KEYEVENTF_UNICODE, 0, 0)
                ),
            ),
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(
                    ki=self.KEYBDINPUT(0, code, self.KEYEVENTF_UNICODE | self.KEYEVENTF_KEYUP, 0, 0)
                ),
            ),
        )
        self._send_inputs(inputs)

    def _keyboard_input(self, vk: int, key_up: bool = False) -> INPUT:
        flags = self.KEYEVENTF_KEYUP if key_up else 0
        return self.INPUT(
            type=self.INPUT_KEYBOARD,
            union=self.INPUT_UNION(ki=self.KEYBDINPUT(vk, 0, flags, 0, 0)),
        )

    def _send_vk(self, vk: int) -> None:
        inputs = (self.INPUT * 2)(
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(ki=self.KEYBDINPUT(vk, 0, 0, 0, 0)),
            ),
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(ki=self.KEYBDINPUT(vk, 0, self.KEYEVENTF_KEYUP, 0, 0)),
            ),
        )
        self._send_inputs(inputs)

    def _send_ctrl_right_bracket(self) -> None:
        inputs = (self.INPUT * 4)(
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(ki=self.KEYBDINPUT(self.VK_CONTROL, 0, 0, 0, 0)),
            ),
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(ki=self.KEYBDINPUT(self.VK_OEM_6, 0, 0, 0, 0)),
            ),
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(ki=self.KEYBDINPUT(self.VK_OEM_6, 0, self.KEYEVENTF_KEYUP, 0, 0)),
            ),
            self.INPUT(
                type=self.INPUT_KEYBOARD,
                union=self.INPUT_UNION(ki=self.KEYBDINPUT(self.VK_CONTROL, 0, self.KEYEVENTF_KEYUP, 0, 0)),
            ),
        )
        self._send_inputs(inputs)

    def _send_inputs(self, inputs: Any) -> None:
        sent = self.user32.SendInput(len(inputs), inputs, ctypes.sizeof(self.INPUT))
        if sent != len(inputs):
            raise ctypes.WinError(ctypes.get_last_error())


@dataclass
class ScanEvent:
    data: str
    device: str
    fmt: str
    suffix: str
    source: str
    received_at: str


class ReceiverApp:
    def __init__(self, start_hidden: bool = False) -> None:
        saved_settings = load_settings()
        self.root = tk.Tk()
        self.root.title("Aşı Barkod PC Alıcı")
        try:
            self.root.iconbitmap(default=bundled_resource_path("assets", "asi_barkod_icon.ico"))
        except tk.TclError:
            # A missing icon must never prevent the receiver from opening.
            pass
        self.root.geometry("860x680")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.root.bind("<Unmap>", self.on_unmap)

        self.message_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.cloud_bridge: Any = None
        self.writer = KeyboardWriter() if sys.platform == "win32" else None
        self.started_at = dt.datetime.now().isoformat(timespec="seconds")
        self.last_event: ScanEvent | None = None
        self.last_error = ""
        self.scan_count = 0
        self.history: list[ScanEvent] = []
        self.scan_lock = threading.Lock()
        self.tray_icon: Any = None
        self.tray_thread: threading.Thread | None = None
        self.exiting = False
        self.write_enabled_var = tk.BooleanVar(value=saved_settings["writeEnabled"])
        self.success_sound_enabled_var = tk.BooleanVar(value=saved_settings["successSoundEnabled"])
        self.suffix_var = tk.StringVar(value=saved_settings["suffix"])
        self.gs_mode_var = tk.StringVar(value=saved_settings["gsMode"])
        self.prefix_mode_var = tk.StringVar(value=saved_settings["prefixMode"])
        self.status_var = tk.StringVar(value="Hazir")
        self.cloud_status_var = tk.StringVar(
            value="Ably bulut desteği hazırlanmadı" if not CLOUD_AVAILABLE else "Ably bulut bağlantısı bekliyor"
        )
        self.pwa_status_var = tk.StringVar(value="PWA sitesi kontrol ediliyor")
        self.cloud_connected = False
        self.pwa_site_available: bool | None = None
        self.pwa_check_pending = False
        self.update_progress_var = tk.StringVar(value="")
        self.pwa_qr_image: Any = None

        self.build_ui()
        for variable in (
            self.write_enabled_var,
            self.success_sound_enabled_var,
            self.suffix_var,
            self.gs_mode_var,
            self.prefix_mode_var,
        ):
            variable.trace_add("write", self.on_setting_changed)
        self.start_tray_icon()
        if start_hidden and TRAY_AVAILABLE:
            self.root.withdraw()
        self.root.after(100, self.pump_messages)
        self.root.after(300, self.check_pwa_site)

    def build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Aşı Barkod PC Alıcı", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        update_area = ttk.Frame(header)
        update_area.pack(side=tk.RIGHT)
        ttk.Label(update_area, text=f"PC v{APP_VERSION}").pack(side=tk.LEFT, padx=(0, 8))
        self.update_button = ttk.Button(
            update_area,
            text="Güncellemeleri denetle",
            command=self.check_for_updates,
        )
        self.update_button.pack(side=tk.LEFT)

        pwa_box = ttk.LabelFrame(frame, text="Telefon uygulaması (iPhone / Android)")
        pwa_box.pack(fill=tk.X, pady=(12, 8))
        pwa_content = ttk.Frame(pwa_box)
        pwa_content.pack(fill=tk.X, padx=10, pady=10)

        if QR_AVAILABLE and TRAY_AVAILABLE and ImageTk is not None:
            qr = qrcode.QRCode(version=None, box_size=4, border=2)
            qr.add_data(PWA_URL)
            qr.make(fit=True)
            qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            resampling = getattr(getattr(Image, "Resampling", Image), "NEAREST")
            qr_image = qr_image.resize((132, 132), resampling)
            self.pwa_qr_image = ImageTk.PhotoImage(qr_image)
            ttk.Label(pwa_content, image=self.pwa_qr_image).pack(side=tk.LEFT, padx=(0, 16))
        else:
            ttk.Label(pwa_content, text="QR oluşturulamadı").pack(side=tk.LEFT, padx=(0, 16))

        pwa_info = ttk.Frame(pwa_content)
        pwa_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(pwa_info, text=PWA_NAME, font=("Segoe UI", 15, "bold")).pack(anchor=tk.W)
        ttk.Label(pwa_info, text=PWA_URL, font=("Consolas", 11)).pack(anchor=tk.W, pady=(6, 10))
        pwa_status_row = ttk.Frame(pwa_info)
        pwa_status_row.pack(anchor=tk.W, pady=(0, 4))
        self.pwa_status_dot = tk.Canvas(pwa_status_row, width=14, height=14, highlightthickness=0, bd=0)
        self.pwa_status_dot.pack(side=tk.LEFT, padx=(0, 6))
        self.pwa_status_dot_oval = self.pwa_status_dot.create_oval(2, 2, 12, 12, fill="#838b98", outline="")
        ttk.Label(pwa_status_row, textvariable=self.pwa_status_var).pack(side=tk.LEFT)
        cloud_status_row = ttk.Frame(pwa_info)
        cloud_status_row.pack(anchor=tk.W, pady=(0, 8))
        self.cloud_status_dot = tk.Canvas(cloud_status_row, width=14, height=14, highlightthickness=0, bd=0)
        self.cloud_status_dot.pack(side=tk.LEFT, padx=(0, 6))
        self.cloud_status_dot_oval = self.cloud_status_dot.create_oval(2, 2, 12, 12, fill="#c62828", outline="")
        ttk.Label(cloud_status_row, textvariable=self.cloud_status_var).pack(side=tk.LEFT)
        ttk.Label(pwa_info, text="Okuyucu biçimleri: DataMatrix · QR Kod").pack(anchor=tk.W, pady=(0, 8))
        pwa_buttons = ttk.Frame(pwa_info)
        pwa_buttons.pack(anchor=tk.W)
        ttk.Button(pwa_buttons, text="Siteyi aç", command=lambda: webbrowser.open(PWA_URL)).pack(side=tk.LEFT)
        ttk.Button(pwa_buttons, text="Adresi kopyala", command=self.copy_pwa_url).pack(side=tk.LEFT, padx=8)
        ttk.Label(
            pwa_info,
            text="Telefon kamerasını QR'a tutun veya adresi Safari/Chrome'da açın.",
        ).pack(anchor=tk.W, pady=(10, 0))

        settings = ttk.Frame(frame)
        settings.pack(fill=tk.X, pady=6)

        ttk.Label(settings, text="Son tus").grid(row=0, column=0, sticky=tk.W)
        ttk.Combobox(
            settings,
            textvariable=self.suffix_var,
            values=("ENTER", "TAB", "NONE"),
            width=10,
            state="readonly",
        ).grid(row=0, column=1, padx=(6, 18))

        ttk.Label(settings, text="GS ayirici").grid(row=0, column=2, sticky=tk.W)
        ttk.Combobox(
            settings,
            textvariable=self.gs_mode_var,
            values=("f8", "unicode", "ctrl_right_bracket", "remove", "pipe", "text"),
            width=18,
            state="readonly",
        ).grid(row=0, column=3, padx=(6, 18))

        ttk.Checkbutton(settings, text="Aktif alana yaz", variable=self.write_enabled_var).grid(row=0, column=4)
        ttk.Checkbutton(settings, text="Başarı sesi", variable=self.success_sound_enabled_var).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky=tk.W,
            padx=(0, 18),
            pady=(8, 0),
        )

        ttk.Label(settings, text="Karekod modu").grid(row=1, column=2, sticky=tk.W, pady=(8, 0))
        ttk.Combobox(
            settings,
            textvariable=self.prefix_mode_var,
            values=("aim_datamatrix_gs1", "none"),
            width=20,
            state="readonly",
        ).grid(row=1, column=3, padx=(6, 18), pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=8)
        ttk.Button(buttons, text="Baslat", command=self.start_server).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Durdur", command=self.stop_server).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons, text="Test yazisi gonder", command=self.send_test_text).pack(side=tk.LEFT)

        self.update_progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.update_progress_label = ttk.Label(frame, textvariable=self.update_progress_var)

        ttk.Label(frame, textvariable=self.status_var).pack(anchor=tk.W, pady=(8, 4))
        columns = ("time", "device", "format", "data")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.tree.heading("time", text="Saat")
        self.tree.heading("device", text="Cihaz")
        self.tree.heading("format", text="Format")
        self.tree.heading("data", text="Ham veri")
        self.tree.column("time", width=130, anchor=tk.W)
        self.tree.column("device", width=150, anchor=tk.W)
        self.tree.column("format", width=110, anchor=tk.W)
        self.tree.column("data", width=390, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        note = ttk.Label(
            frame,
            text=(
                "Kullanim: once Baslat'a basin, sonra barkodun yazilacagi PC uygulamasinda ilgili alana tiklayin. "
                "Telefon okutunca veri aktif alana yazilir."
            ),
            wraplength=780,
        )
        note.pack(anchor=tk.W, pady=(10, 0))

    def copy_pwa_url(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(PWA_URL)
        self.root.update_idletasks()
        self.status_var.set("Aşı Barkod PWA adresi kopyalandı")

    def check_pwa_site(self) -> None:
        if self.pwa_check_pending:
            return
        self.pwa_check_pending = True

        def worker() -> None:
            try:
                release = fetch_pwa_release()
                self.enqueue_message(("pwa_status", (True, f"PWA sitesi erişilebilir · sürüm {release}")))
            except Exception as exc:
                self.enqueue_message(("pwa_status", (False, f"PWA sitesi erişilemiyor · {exc}")))

        threading.Thread(target=worker, daemon=True, name="AsiBarkodPwaCheck").start()

    def start_server(self) -> None:
        if self.cloud_bridge is not None:
            self.status_var.set("Alici zaten calisiyor")
            return
        self.start_cloud_bridge()
        self.status_var.set("Alıcı çalışıyor: Ably bağlantısı kuruluyor")

    def forward_cloud_scan(self, job: dict[str, Any]) -> Any:
        started = time.perf_counter()
        event = ScanEvent(
            data=str(job.get("data", "")),
            device=str(job.get("device", "Telefon PWA")),
            fmt=str(job.get("format", "DATA_MATRIX")),
            suffix="",
            source="phone-pwa-ably",
            received_at=dt.datetime.now().isoformat(timespec="seconds"),
        )
        if not event.data:
            return JobResult(False, "Boş barkod verisi", 0)
        delivered = self.handle_scan(event)
        return JobResult(
            delivered,
            "Aktif pencereye yazılamadı" if not delivered else "",
            int((time.perf_counter() - started) * 1000),
        )

    def start_cloud_bridge(self) -> None:
        if not CLOUD_AVAILABLE or CloudBridgeService is None:
            self.cloud_status_var.set("Bulut destegi yuklu degil")
            return
        if self.cloud_bridge is not None:
            return
        self.cloud_bridge = CloudBridgeService(
            receiver_id=receiver_id(),
            receiver_name=socket.gethostname(),
            forward=self.forward_cloud_scan,
            status=lambda text: self.enqueue_message(("cloud_status", text)),
            connection_state=lambda connected: self.enqueue_message(("cloud_connection", connected)),
        )
        self.cloud_bridge.start()

    def stop_server(self) -> None:
        if self.cloud_bridge is None:
            self.status_var.set("Alici zaten durdu")
            return
        self.cloud_bridge.stop()
        self.cloud_bridge = None
        self.cloud_status_var.set("Bulut baglantisi durdu")
        self.status_var.set("Alici durdu")

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": self.cloud_bridge is not None,
            "cloudStatus": self.cloud_status_var.get(),
            "writeEnabled": bool(self.write_enabled_var.get()),
            "successSoundEnabled": bool(self.success_sound_enabled_var.get()),
            "suffix": self.suffix_var.get(),
            "gsMode": self.gs_mode_var.get(),
            "prefixMode": self.prefix_mode_var.get(),
            "lastDevice": self.last_event.device if self.last_event else "",
            "lastScan": event_to_dict(self.last_event),
            "history": [event_to_dict(item) for item in self.history[:20]],
            "scanCount": self.scan_count,
            "lastError": self.last_error,
            "startedAt": self.started_at,
        }

    def configure(self, payload: dict[str, Any]) -> None:
        if "writeEnabled" in payload:
            self.write_enabled_var.set(bool(payload["writeEnabled"]))
        if "successSoundEnabled" in payload:
            self.success_sound_enabled_var.set(bool(payload["successSoundEnabled"]))
        if str(payload.get("suffix", "")).upper() in SUFFIX_MODES:
            self.suffix_var.set(str(payload["suffix"]).upper())
        if str(payload.get("gsMode", "")).lower() in GS_MODES:
            self.gs_mode_var.set(str(payload["gsMode"]).lower())
        if str(payload.get("prefixMode", "")).lower() in PREFIX_MODES:
            self.prefix_mode_var.set(str(payload["prefixMode"]).lower())

    def current_settings(self) -> dict[str, Any]:
        return {
            "writeEnabled": bool(self.write_enabled_var.get()),
            "successSoundEnabled": bool(self.success_sound_enabled_var.get()),
            "suffix": self.suffix_var.get(),
            "gsMode": self.gs_mode_var.get(),
            "prefixMode": self.prefix_mode_var.get(),
        }

    def on_setting_changed(self, *_: Any) -> None:
        try:
            save_settings(self.current_settings())
        except OSError as exc:
            self.enqueue_message(("error", f"Ayar kaydetme hatasi: {exc}"))

    def send_test_text(self, data: str | None = None) -> None:
        self.handle_scan(test_event(data))

    def check_for_updates(self) -> None:
        self.update_button.configure(state=tk.DISABLED)
        self.status_var.set("Güncelleme kontrol ediliyor...")
        threading.Thread(target=self._check_for_updates_worker, daemon=True).start()

    def _check_for_updates_worker(self) -> None:
        try:
            self.enqueue_message(("update_result", fetch_latest_release()))
        except Exception as exc:
            self.enqueue_message(("update_error", str(exc)))

    def show_update_result(self, info: UpdateInfo) -> None:
        self.update_button.configure(state=tk.NORMAL)
        if not info.is_newer:
            self.status_var.set(f"Program güncel: v{APP_VERSION}")
            messagebox.showinfo("Güncelleme", f"Program güncel.\n\nSürüm: v{APP_VERSION}")
            return

        if not info.download_url:
            self.status_var.set(f"Yeni sürüm bulundu: v{info.version}")
            if messagebox.askyesno(
                "Güncelleme bulundu",
                f"Yeni sürüm: v{info.version}\n\n"
                f"Neler değişti:\n{info.notes}\n\n"
                "İndirme sayfası açılsın mı?",
            ):
                webbrowser.open(info.page_url)
            return

        if messagebox.askyesno(
            "Güncelleme bulundu",
            f"Mevcut sürüm: v{APP_VERSION}\nYeni sürüm: v{info.version}\n\n"
            f"Neler değişti:\n{info.notes}\n\n"
            "Kurulum dosyası indirilsin mi?",
        ):
            self.update_button.configure(state=tk.DISABLED)
            self.status_var.set(f"v{info.version} indiriliyor...")
            self.update_progress.configure(value=0, mode="determinate")
            self.update_progress.pack(fill=tk.X, pady=(4, 0))
            self.update_progress_label.pack(anchor=tk.W, pady=(2, 4))
            self.update_progress_var.set(f"v{info.version} indiriliyor...")
            threading.Thread(target=self._download_update_worker, args=(info,), daemon=True).start()

    def _download_update_worker(self, info: UpdateInfo) -> None:
        try:
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            filename = info.filename or f"Asi-Barkod-Windows-Kurulum-v{info.version}.exe"
            destination = os.path.join(downloads_dir, os.path.basename(filename))
            temp_path = f"{destination}.part"
            request = urllib.request.Request(
                info.download_url,
                headers={"User-Agent": f"AsiBarkodReceiver/{APP_VERSION}"},
            )
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=30,
                    context=github_ssl_context(),
                ) as response, open(temp_path, "wb") as handle:
                    total = int(response.headers.get("Content-Length") or 0)
                    downloaded = 0
                    last_report = 0.0
                    while True:
                        block = response.read(1024 * 256)
                        if not block:
                            break
                        handle.write(block)
                        downloaded += len(block)
                        now = time.monotonic()
                        if now - last_report >= 0.15 or (total and downloaded >= total):
                            self.enqueue_message(("update_progress", (info.version, downloaded, total)))
                            last_report = now
                os.replace(temp_path, destination)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            self.enqueue_message(("update_downloaded", (info, destination)))
        except Exception as exc:
            self.enqueue_message(("update_error", str(exc)))

    def show_downloaded_update(self, info: UpdateInfo, path: str) -> None:
        self.update_button.configure(state=tk.NORMAL)
        self.update_progress.stop()
        self.update_progress.configure(value=100)
        self.update_progress_var.set(
            f"v{info.version} indirildi · {format_file_size(os.path.getsize(path))}"
        )
        self.status_var.set(f"Güncelleme indirildi: {os.path.basename(path)}")
        if messagebox.askyesno(
            "Güncelleme indirildi",
            f"v{info.version} indirildi.\n\n"
            f"Neler değişti:\n{info.notes}\n\n"
            "Şimdi kurulsun mu? Program kapanacaktır.",
        ):
            try:
                os.startfile(path)
            except OSError as exc:
                self.status_var.set(f"Kurulum açılamadı: {exc}")
                messagebox.showerror("Güncelleme", f"Kurulum dosyası açılamadı:\n{exc}")
                return
            self.exit_application()

    def handle_scan(self, event: ScanEvent) -> bool:
        with self.scan_lock:
            return self._handle_scan_locked(event)

    def _handle_scan_locked(self, event: ScanEvent) -> bool:
        suffix = self.suffix_var.get()
        try:
            self.log_event(event, suffix)
        except Exception as exc:
            self.last_error = str(exc)
            self.enqueue_message(("error", f"Log yazma hatasi: {exc}"))
        self.last_event = event
        self.scan_count += 1
        self.history.insert(0, event)
        del self.history[20:]

        if self.write_enabled_var.get() and self.writer is not None:
            try:
                self.writer.send_text(
                    prefix_for_mode(self.prefix_mode_var.get()) + event.data,
                    self.gs_mode_var.get(),
                )
                self.writer.send_suffix(suffix)
            except Exception as exc:
                self.last_error = str(exc)
                self.enqueue_message(("error", f"Yazma hatasi: {exc}"))
                return False

        self.enqueue_message(("scan", event))
        if self.success_sound_enabled_var.get():
            play_success_beep()
        return True

    def log_event(self, event: ScanEvent, suffix: str) -> None:
        path = os.path.join(ensure_logs_dir(), f"scans-{dt.date.today().isoformat()}.csv")
        file_exists = os.path.exists(path)
        with open(path, "a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if not file_exists:
                writer.writerow(["received_at", "device", "format", "suffix", "source", "data"])
            writer.writerow([
                event.received_at,
                event.device,
                event.fmt,
                suffix,
                event.source,
                csv_safe(event.data),
            ])

    def enqueue_message(self, item: tuple[str, Any]) -> None:
        if item[0] == "error":
            self.last_error = str(item[1])
        self.message_queue.put(item)

    def pump_messages(self) -> None:
        while True:
            try:
                kind, payload = self.message_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "scan":
                event: ScanEvent = payload
                self.tree.insert(
                    "",
                    0,
                    values=(
                        event.received_at,
                        event.device,
                        event.fmt,
                        visible_control_chars(event.data),
                    ),
                )
                self.status_var.set(f"Okundu: {event.device} / {event.fmt}")
            elif kind == "error":
                self.status_var.set(str(payload))
            elif kind == "cloud_status":
                self.cloud_status_var.set(str(payload))
            elif kind == "cloud_connection":
                self.set_cloud_connection_state(bool(payload))
            elif kind == "pwa_status":
                available, text = payload
                self.pwa_check_pending = False
                self.set_pwa_site_status(bool(available), str(text))
                # A failure is retried sooner; a healthy site is checked again while the PC remains open.
                self.root.after(60_000 if not available else 600_000, self.check_pwa_site)
            elif kind == "update_result":
                self.show_update_result(payload)
            elif kind == "update_downloaded":
                info, path = payload
                self.show_downloaded_update(info, path)
            elif kind == "update_progress":
                version, downloaded, total = payload
                if total:
                    percent = min(100, downloaded * 100 / total)
                    self.update_progress.configure(value=percent)
                    self.update_progress_var.set(
                        f"v{version} indiriliyor · %{percent:.0f} "
                        f"({format_file_size(downloaded)} / {format_file_size(total)})"
                    )
                else:
                    self.update_progress.configure(mode="indeterminate")
                    self.update_progress.start(12)
                    self.update_progress_var.set(
                        f"v{version} indiriliyor · {format_file_size(downloaded)}"
                    )
            elif kind == "update_error":
                self.update_button.configure(state=tk.NORMAL)
                if hasattr(self, "update_progress"):
                    self.update_progress.stop()
                    self.update_progress.pack_forget()
                    self.update_progress_label.pack_forget()
                    self.update_progress_var.set("")
                self.status_var.set("Güncelleme kontrolü başarısız")
                messagebox.showerror(
                    "Güncelleme",
                    "Güncelleme otomatik kontrol edilemedi. "
                    "İndirme sayfası tarayıcıda açılacak.\n\n"
                    f"Ayrıntı: {payload}",
                )
                if not webbrowser.open(RELEASES_URL):
                    messagebox.showinfo("Güncelleme bağlantısı", RELEASES_URL)
            elif kind == "show_window":
                self.show_window()
            elif kind == "exit_application":
                self.exit_application()
                return

        self.root.after(100, self.pump_messages)

    def tray_image(self) -> Any:
        icon_path = bundled_resource_path("assets", "asi_barkod_icon.png")
        try:
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            with Image.open(icon_path) as source:
                return source.convert("RGBA").resize((64, 64), resampling)
        except (OSError, AttributeError):
            image = Image.new("RGB", (64, 64), "#b7251c")
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((7, 7, 57, 57), radius=9, fill="#ffffff")
            draw.rectangle((17, 16, 22, 48), fill="#b7251c")
            draw.rectangle((27, 16, 32, 48), fill="#b7251c")
            draw.rectangle((37, 16, 42, 48), fill="#b7251c")
            draw.rectangle((47, 16, 50, 48), fill="#b7251c")
            return image

    def start_tray_icon(self) -> None:
        if not TRAY_AVAILABLE or self.tray_icon is not None:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Pencereyi ac", self.request_show_window, default=True),
            pystray.MenuItem("Programdan cik", self.request_exit_application),
        )
        self.tray_icon = pystray.Icon("AsiBarkodReceiver", self.tray_image(), "Asi Barkod PC Alicisi", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True, name="AsiBarkodTray")
        self.tray_thread.start()

    def request_show_window(self, icon: Any = None, item: Any = None) -> None:
        self.enqueue_message(("show_window", None))

    def request_exit_application(self, icon: Any = None, item: Any = None) -> None:
        self.enqueue_message(("exit_application", None))

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def set_cloud_connection_state(self, connected: bool) -> None:
        self.cloud_connected = connected
        if hasattr(self, "cloud_status_dot"):
            self.cloud_status_dot.itemconfigure(
                self.cloud_status_dot_oval,
                fill="#18a957" if connected else "#d22f27",
            )

    def set_pwa_site_status(self, available: bool, text: str) -> None:
        self.pwa_site_available = available
        self.pwa_status_var.set(text)
        if hasattr(self, "pwa_status_dot"):
            self.pwa_status_dot.itemconfigure(
                self.pwa_status_dot_oval,
                fill="#18a957" if available else "#d22f27",
            )

    def hide_to_tray(self) -> None:
        if not TRAY_AVAILABLE:
            self.exit_application()
            return
        self.root.withdraw()

    def on_unmap(self, event: Any) -> None:
        if event.widget is self.root:
            self.root.after_idle(self.hide_if_minimized)

    def hide_if_minimized(self) -> None:
        if not self.exiting and self.root.state() == "iconic":
            self.hide_to_tray()

    def exit_application(self) -> None:
        if self.exiting:
            return
        self.exiting = True
        self.stop_server()
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.destroy()

    def run(self) -> None:
        self.start_server()
        self.root.mainloop()


def show_existing_instance() -> bool:
    if sys.platform != "win32":
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenEventW.argtypes = (ctypes.c_uint32, ctypes.c_bool, ctypes.c_wchar_p)
    kernel32.OpenEventW.restype = ctypes.c_void_p
    handle = kernel32.OpenEventW(0x0002, False, SHOW_WINDOW_EVENT_NAME)
    if not handle:
        return False
    try:
        kernel32.SetEvent(ctypes.c_void_p(handle))
        return True
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))


def start_show_window_listener(app: ReceiverApp) -> None:
    """Lets a desktop/start-menu shortcut reopen the already tray-hidden app."""
    if sys.platform != "win32":
        return
    global _show_window_event
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateEventW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p)
    kernel32.CreateEventW.restype = ctypes.c_void_p
    event = kernel32.CreateEventW(None, False, False, SHOW_WINDOW_EVENT_NAME)
    if not event:
        return
    _show_window_event = event

    def listen() -> None:
        while not app.exiting:
            if kernel32.WaitForSingleObject(ctypes.c_void_p(event), 500) == 0:
                app.enqueue_message(("show_window", None))

    threading.Thread(target=listen, daemon=True, name="AsiBarkodShowWindow").start()


def acquire_single_instance() -> bool:
    global _instance_mutex
    if sys.platform != "win32":
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, INSTANCE_MUTEX_NAME)
    if not handle:
        return True
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        return False
    _instance_mutex = handle
    return True


def main() -> None:
    try:
        if not TK_AVAILABLE:
            raise RuntimeError("Windows arayüz bileşeni bulunamadı; uygulamayı güncel kurulum paketiyle yeniden yükleyin.")
        if not acquire_single_instance():
            for _ in range(10):
                if show_existing_instance():
                    break
                time.sleep(0.1)
            return
        app = ReceiverApp(start_hidden="--tray" in sys.argv)
        start_show_window_listener(app)
        app.run()
    except Exception as exc:
        if sys.stderr is not None:
            print(f"Hata: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
