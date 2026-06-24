# -*- coding: utf-8 -*-

import atexit
import ctypes
import sys

from hotkey_manager import (
    kernel32, DEFAULT_MUTEX_NAME, ERROR_ALREADY_EXISTS,
    load_config, HotkeyManager,
)
from gui import HotkeyManagerApp


def main():
    config = load_config()
    mutex_name = config.get("mutex_name", DEFAULT_MUTEX_NAME)
    display_name = config.get("display_name", "App Hotkey Manager")

    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        print(f"{display_name} is already running.")
        return

    atexit.register(kernel32.CloseHandle, mutex)

    manager = HotkeyManager(config)

    app = HotkeyManagerApp(manager)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
