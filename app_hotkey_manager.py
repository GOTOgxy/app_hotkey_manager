# -*- coding: utf-8 -*-

import atexit
import ctypes
import json
import subprocess
import sys
import time
import winreg
from ctypes import wintypes
from pathlib import Path


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
ERROR_ALREADY_EXISTS = 183

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMAXIMIZED = 3
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9

WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
GW_OWNER = 4

CONFIG_FILE_NAME = "app_hotkey_config.json"
DEFAULT_MUTEX_NAME = "Global\\AppHotkeyManager"


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]
user32.EnumWindows.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.GetForegroundWindow.restype = wintypes.HWND

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL

user32.IsZoomed.argtypes = [wintypes.HWND]
user32.IsZoomed.restype = wintypes.BOOL

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL

user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = wintypes.LPARAM

kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL

kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE


HOTKEY_MODIFIERS = {
    "ALT": MOD_ALT,
    "CTRL": MOD_CONTROL,
    "CONTROL": MOD_CONTROL,
    "SHIFT": MOD_SHIFT,
    "WIN": MOD_WIN,
    "WINDOWS": MOD_WIN,
}

VIRTUAL_KEYS = {
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{str(num): ord(str(num)) for num in range(0, 10)},
    **{f"F{num}": 0x6F + num for num in range(1, 25)},
    "TAB": 0x09,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_embedded_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return get_base_dir()


def get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value.strip()


def get_class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value.strip()


def get_window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def iter_windows_for_pid(pid: int):
    windows = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        if get_window_pid(hwnd) == pid:
            windows.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return windows


def iter_processes_by_name(exe_name: str):
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        has_item = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))

        while has_item:
            if entry.szExeFile.lower() == exe_name.lower():
                yield entry.th32ProcessID
            has_item = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)


def get_process_image_path(pid: int) -> str | None:
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not process:
        return None

    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        ok = kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size))
        if not ok:
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(process)


def parse_hotkey(hotkey: str) -> tuple[int, int]:
    tokens = [token.strip().upper() for token in hotkey.split("+") if token.strip()]
    if len(tokens) < 2:
        raise ValueError(f"Invalid hotkey '{hotkey}'. Example: CTRL+ALT+Q")

    modifiers = 0
    key_token = tokens[-1]
    for token in tokens[:-1]:
        if token not in HOTKEY_MODIFIERS:
            raise ValueError(f"Unsupported modifier '{token}' in hotkey '{hotkey}'")
        modifiers |= HOTKEY_MODIFIERS[token]

    if modifiers == 0:
        raise ValueError(f"Hotkey '{hotkey}' must include at least one modifier")

    virtual_key = VIRTUAL_KEYS.get(key_token)
    if virtual_key is None:
        raise ValueError(f"Unsupported key '{key_token}' in hotkey '{hotkey}'")

    return modifiers, virtual_key


class AppController:
    def __init__(
        self,
        *,
        app_id: str,
        exe_name: str,
        primary_window_classes: set[str] | None = None,
        ignored_window_classes: set[str] | None = None,
        hide_window_classes: set[str] | None = None,
        hide_mode: str = "minimize",
        launch_if_not_running: bool = False,
        install_path: str | None = None,
        launch_candidates: list[str] | None = None,
        app_paths_registry_names: list[str] | None = None,
        launch_timeout_seconds: float = 8.0,
    ):
        self.app_id = app_id
        self.exe_name = exe_name
        self.primary_window_classes = primary_window_classes or set()
        self.ignored_window_classes = ignored_window_classes or set()
        self.hide_window_classes = hide_window_classes or set()
        self.hide_mode = hide_mode
        self.launch_if_not_running = launch_if_not_running
        self.install_path = install_path
        self.launch_candidates = launch_candidates or []
        self.app_paths_registry_names = app_paths_registry_names or []
        self.launch_timeout_seconds = launch_timeout_seconds

    def iter_target_processes(self):
        return iter_processes_by_name(self.exe_name)

    def find_main_window(self, pid: int) -> int | None:
        preferred = []
        fallback = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def callback(hwnd, _lparam):
            if get_window_pid(hwnd) != pid:
                return True

            if user32.GetWindow(hwnd, GW_OWNER):
                return True

            class_name = get_class_name(hwnd)
            if class_name in self.ignored_window_classes:
                return True

            title = get_window_text(hwnd)
            is_visible = bool(user32.IsWindowVisible(hwnd))

            if class_name in self.primary_window_classes:
                preferred.append((0 if is_visible else 1, hwnd))
                return True

            if title:
                fallback.append((0 if is_visible else 1, hwnd))
                return True

            if class_name:
                fallback.append((1 if is_visible else 2, hwnd))
            return True

        user32.EnumWindows(callback, 0)
        if preferred:
            preferred.sort(key=lambda item: item[0])
            return preferred[0][1]
        if fallback:
            fallback.sort(key=lambda item: item[0])
            return fallback[0][1]
        return None

    def is_foreground_window(self, hwnd: int) -> bool:
        return bool(hwnd and user32.IsWindowVisible(hwnd) and user32.GetForegroundWindow() == hwnd)

    def activate_window(self, hwnd: int) -> bool:
        if not hwnd:
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        elif user32.IsZoomed(hwnd):
            user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)
        return bool(user32.SetForegroundWindow(hwnd))

    def hide_window(self, hwnd: int) -> bool:
        if not hwnd:
            return False
        if self.hide_mode == "tray":
            return self._hide_to_tray(hwnd)
        if self.hide_mode == "hide":
            user32.ShowWindow(hwnd, SW_HIDE)
            return True
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        return True

    def _hide_to_tray(self, hwnd: int) -> bool:
        pid = get_window_pid(hwnd)
        hidden_any = False
        for candidate in iter_windows_for_pid(pid):
            class_name = get_class_name(candidate)
            owner = user32.GetWindow(candidate, GW_OWNER)
            should_hide = (
                candidate == hwnd
                or owner == hwnd
                or class_name in self.hide_window_classes
            )
            if should_hide and user32.IsWindowVisible(candidate):
                user32.ShowWindow(candidate, SW_HIDE)
                hidden_any = True
        return hidden_any or not user32.IsWindowVisible(hwnd)

    def relaunch_existing_instance(self, pid: int) -> bool:
        image_path = get_process_image_path(pid)
        if not image_path:
            return False
        try:
            subprocess.Popen([image_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            return False

        return self.wait_for_any_window_and_activate(existing_pids={pid}, timeout_seconds=5.0)

    def read_app_path_from_registry(self) -> str | None:
        registry_names = self.app_paths_registry_names or [self.exe_name]
        for registry_name in registry_names:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{registry_name}",
                ) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if value and Path(value).exists():
                        return value
            except OSError:
                continue
        return None

    def resolve_launch_path(self) -> str | None:
        if self.install_path and Path(self.install_path).exists():
            return self.install_path

        registry_path = self.read_app_path_from_registry()
        if registry_path:
            return registry_path

        for candidate in self.launch_candidates:
            if Path(candidate).exists():
                return candidate
        return None

    def launch_app(self) -> bool:
        launch_path = self.resolve_launch_path()
        if not launch_path:
            return False
        try:
            subprocess.Popen([launch_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            return False

    def wait_for_any_window_and_activate(self, existing_pids: set[int] | None = None, timeout_seconds: float | None = None) -> bool:
        existing_pids = existing_pids or set()
        deadline = time.time() + (timeout_seconds or self.launch_timeout_seconds)
        while time.time() < deadline:
            pids = list(self.iter_target_processes())
            candidate_pids = [pid for pid in pids if pid not in existing_pids] or pids
            for pid in candidate_pids:
                hwnd = self.find_main_window(pid)
                if hwnd:
                    return self.activate_window(hwnd)
            time.sleep(0.15)
        return False

    def toggle(self):
        pids = list(self.iter_target_processes())
        if not pids:
            if self.launch_if_not_running:
                if self.launch_app():
                    self.wait_for_any_window_and_activate()
            return

        for pid in pids:
            hwnd = self.find_main_window(pid)
            if hwnd:
                if self.is_foreground_window(hwnd):
                    self.hide_window(hwnd)
                else:
                    self.activate_window(hwnd)
                return

        self.relaunch_existing_instance(pids[0])


def create_builtin_controller(app_id: str, entry: dict) -> AppController:
    app_id = app_id.lower()
    install_path = entry.get("install_path")
    if app_id == "cloudmusic":
        return AppController(
            app_id=app_id,
            exe_name="cloudmusic.exe",
            primary_window_classes={"OrpheusBrowserHost"},
            ignored_window_classes={
                "OrpheusShadow",
                "GDI+ Hook Window Class",
                "Chrome_SystemMessageWindow",
                "Chrome_WidgetWin_0",
                "Base_PowerMessageWindow",
                "IME",
                "MSCTFIME UI",
            },
            hide_window_classes={
                "OrpheusBrowserHost",
                "OrpheusShadow",
                "MiniPlayer",
                "icon",
            },
            hide_mode="tray",
            launch_if_not_running=bool(entry.get("launch_if_not_running", False)),
            install_path=install_path,
            app_paths_registry_names=["cloudmusic.exe"],
        )

    if app_id == "zotero":
        return AppController(
            app_id=app_id,
            exe_name="zotero.exe",
            primary_window_classes={"MozillaWindowClass", "Chrome_WidgetWin_1"},
            ignored_window_classes={"MozillaDropShadowWindowClass"},
            hide_mode="minimize",
            launch_if_not_running=bool(entry.get("launch_if_not_running", True)),
            install_path=install_path,
            launch_candidates=[
                r"C:\Program Files\Zotero\zotero.exe",
                r"C:\Program Files (x86)\Zotero\zotero.exe",
            ],
            app_paths_registry_names=["zotero.exe", "Zotero.exe"],
            launch_timeout_seconds=10.0,
        )

    raise ValueError(f"Unsupported app '{app_id}'. Supported values: cloudmusic, zotero")


def load_config() -> dict:
    config_path = get_embedded_dir() / CONFIG_FILE_NAME
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_hotkey_entries(config: dict):
    entries = config.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Config must contain a non-empty 'entries' list")

    built_entries = []
    seen_hotkeys = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry #{index} must be an object")

        hotkey = entry.get("hotkey")
        app_id = entry.get("app")
        if not hotkey or not app_id:
            raise ValueError(f"Entry #{index} must contain 'hotkey' and 'app'")

        modifiers, virtual_key = parse_hotkey(hotkey)
        hotkey_signature = (modifiers, virtual_key)
        if hotkey_signature in seen_hotkeys:
            raise ValueError(f"Duplicate hotkey '{hotkey}' in config")
        seen_hotkeys.add(hotkey_signature)

        controller = create_builtin_controller(app_id, entry)
        built_entries.append(
            {
                "id": index,
                "hotkey": hotkey,
                "modifiers": modifiers,
                "virtual_key": virtual_key,
                "controller": controller,
            }
        )
    return built_entries


def register_hotkeys(entries):
    for entry in entries:
        ok = user32.RegisterHotKey(None, entry["id"], entry["modifiers"], entry["virtual_key"])
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())


def unregister_hotkeys(entries):
    for entry in entries:
        user32.UnregisterHotKey(None, entry["id"])


def message_loop(entries):
    msg = wintypes.MSG()
    entry_map = {entry["id"]: entry for entry in entries}
    while True:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            if msg.message == WM_HOTKEY and msg.wParam in entry_map:
                entry_map[msg.wParam]["controller"].toggle()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.05)


def main():
    config = load_config()
    mutex_name = config.get("mutex_name", DEFAULT_MUTEX_NAME)
    display_name = config.get("display_name", "App Hotkey Manager")
    entries = build_hotkey_entries(config)

    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        print(f"{display_name} is already running.")
        return

    atexit.register(kernel32.CloseHandle, mutex)
    register_hotkeys(entries)
    atexit.register(unregister_hotkeys, entries)

    print(f"{display_name} started.")
    for entry in entries:
        print(f"{entry['hotkey']} -> {entry['controller'].app_id}")
    message_loop(entries)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
