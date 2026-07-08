# -*- coding: utf-8 -*-

import ctypes
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from hotkey_manager import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_WIN,
    NIF_ICON,
    NIF_MESSAGE,
    NIF_TIP,
    NIM_ADD,
    NIM_DELETE,
    TRAY_ICON_ID,
    HotkeyManager,
    NOTIFYICONDATAW,
    VIRTUAL_KEYS,
    WNDCLASS,
    gdi32,
    kernel32,
    shell32,
    user32,
)


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def _clamp(value, low, high):
    return max(low, min(high, value))


def _compute_ui_scale(root):
    try:
        dpi_scale = root.winfo_fpixels("1i") / 96.0
    except tk.TclError:
        dpi_scale = 1.0
    screen_w = max(root.winfo_screenwidth(), 1)
    screen_h = max(root.winfo_screenheight(), 1)
    resolution_scale = min(screen_w / 1920, screen_h / 1080)
    return _clamp(max(dpi_scale, resolution_scale, 1.0), 1.0, 1.45)


def scaled(widget, value):
    scale = getattr(widget.winfo_toplevel(), "ui_scale", 1.0)
    return int(round(value * scale))


def ui_font(widget, size, weight=None):
    return ctk.CTkFont(family="Microsoft YaHei UI", size=scaled(widget, size), weight=weight)


def _dialog_font(widget, delta=0, weight=None):
    size = 19 + delta
    return ctk.CTkFont(family="Microsoft YaHei UI", size=scaled(widget, size), weight=weight)


def _menu_font(widget, size=18):
    return ("Microsoft YaHei UI", scaled(widget, size))


def _readonly_entry(parent, variable):
    entry = ctk.CTkEntry(parent, textvariable=variable, font=_dialog_font(parent))
    entry.bind("<Key>", lambda _event: "break")
    return entry


class _BindXDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, width, height):
        super().__init__(parent)
        self._bindx_root = parent.winfo_toplevel()
        self.ui_scale = getattr(self._bindx_root, "ui_scale", 1.0)
        self.result = None

        self.title(title)
        self.geometry(f"{scaled(self, width)}x{scaled(self, height)}")
        self.minsize(scaled(self, width), scaled(self, height))
        self.resizable(False, False)
        self.configure(fg_color=("#f4f4f5", "#18181b"))
        self.transient(self._bindx_root)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill=tk.BOTH, expand=True, padx=scaled(self, 20), pady=scaled(self, 18))
        self.after(50, self.focus_force)

    def _center_on_parent(self):
        self.update_idletasks()
        parent = self._bindx_root
        x = parent.winfo_x() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_y() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _label(self, parent, text, width=118):
        return ctk.CTkLabel(parent, text=text, width=scaled(self, width), anchor="w", font=_dialog_font(self))

    def _row(self, parent=None, pady=(0, 10)):
        row = ctk.CTkFrame(parent or self.body, fg_color="transparent")
        row.pack(fill=tk.X, pady=(scaled(self, pady[0]), scaled(self, pady[1])))
        return row

    def _button_row(self):
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill=tk.X, pady=(scaled(self, 12), 0))
        return row

    def _secondary_button(self, parent, text, command, width=84):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=scaled(self, width),
            font=_dialog_font(self),
            fg_color="#52525b",
            hover_color="#3f3f46",
        )

    def _on_cancel(self):
        self.result = None
        self.destroy()


class HotkeyCaptureDialog(_BindXDialog):
    KEYSYM_MAP = {
        "return": "ENTER",
        "escape": "ESC",
        "space": "SPACE",
        "left": "LEFT",
        "right": "RIGHT",
        "up": "UP",
        "down": "DOWN",
        "home": "HOME",
        "end": "END",
        "prior": "PAGEUP",
        "next": "PAGEDOWN",
        "insert": "INSERT",
        "delete": "DELETE",
        "tab": "TAB",
    }
    MODIFIER_MAP = {
        "control_l": "CTRL",
        "control_r": "CTRL",
        "alt_l": "ALT",
        "alt_r": "ALT",
        "shift_l": "SHIFT",
        "shift_r": "SHIFT",
        "super_l": "WIN",
        "super_r": "WIN",
        "meta_l": "WIN",
        "meta_r": "WIN",
    }
    MODIFIER_ORDER = ("CTRL", "ALT", "SHIFT", "WIN")

    def __init__(self, parent, current_hotkey=""):
        super().__init__(parent, "录制快捷键", 560, 250)
        self.captured_hotkey = current_hotkey
        self.captured = False
        self._pressed = set()

        ctk.CTkLabel(self.body, text="请按下快捷键组合", font=_dialog_font(self, 2, "bold")).pack(anchor=tk.W, pady=(0, scaled(self, 10)))
        self.hotkey_var = tk.StringVar(value=current_hotkey or "等待输入...")
        ctk.CTkLabel(self.body, textvariable=self.hotkey_var, font=_dialog_font(self, 5, "bold")).pack(fill=tk.X, pady=(0, scaled(self, 18)))

        btns = self._button_row()
        self.ok_btn = ctk.CTkButton(btns, text="确认", command=self._on_ok, width=scaled(self, 88), font=_dialog_font(self))
        self.ok_btn.pack(side=tk.RIGHT, padx=(scaled(self, 8), 0))
        self.ok_btn.configure(state=tk.NORMAL if current_hotkey else tk.DISABLED)
        self._secondary_button(btns, "取消", self._on_cancel).pack(side=tk.RIGHT, padx=(scaled(self, 8), 0))
        self._secondary_button(btns, "清除", self._on_clear).pack(side=tk.RIGHT)

        self.bind("<KeyPress>", self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)
        self._center_on_parent()

    def _normalize(self, keysym):
        key = keysym.lower()
        if key in self.MODIFIER_MAP:
            return self.MODIFIER_MAP[key]
        if len(key) == 1:
            return key.upper()
        if key.startswith("f") and key[1:].isdigit():
            return key.upper()
        return self.KEYSYM_MAP.get(key, key.upper())

    def _on_key_release(self, event):
        name = self._normalize(event.keysym)
        if name in self.MODIFIER_ORDER:
            self._pressed.discard(name)

    def _on_key_press(self, event):
        name = self._normalize(event.keysym)
        if name in self.MODIFIER_ORDER:
            self._pressed.add(name)
            return
        if name not in VIRTUAL_KEYS:
            self.hotkey_var.set(f"不支持：{name}")
            self.ok_btn.configure(state=tk.DISABLED)
            return
        modifiers = [mod for mod in self.MODIFIER_ORDER if mod in self._pressed]
        self.captured_hotkey = "+".join(modifiers + [name])
        self.hotkey_var.set(self.captured_hotkey)
        self.captured = True
        self.ok_btn.configure(state=tk.NORMAL)

    def _on_clear(self):
        self.captured_hotkey = ""
        self.captured = False
        self._pressed.clear()
        self.hotkey_var.set("等待输入...")
        self.ok_btn.configure(state=tk.DISABLED)

    def _on_ok(self):
        if self.captured_hotkey:
            self.result = self.captured_hotkey
            self.destroy()


class EntryDialog(_BindXDialog):
    APP_IDS = ["cloudmusic", "zotero", "termius", "hot_key_manager", "generic", "web_app"]
    APP_NAMES = {
        "cloudmusic": "网易云音乐",
        "zotero": "Zotero",
        "termius": "Termius",
        "hot_key_manager": "Hot Key Manager",
        "generic": "通用应用",
        "web_app": "网页应用",
    }
    BROWSER_MAP = {"Edge": "msedge.exe", "Chrome": "chrome.exe"}

    def __init__(self, parent, entry=None):
        super().__init__(parent, "编辑条目" if entry else "添加条目", 680, 560)
        self.entry = entry

        self.app_var = tk.StringVar(value=entry["config_entry"]["app"] if entry else self.APP_IDS[0])
        self.hotkey_var = tk.StringVar(value=entry["hotkey"] if entry else "")
        self.enabled_var = tk.BooleanVar(value=entry["enabled"] if entry else True)
        default_launch = entry["config_entry"].get("launch_if_not_running", False) if entry else False
        if entry is None and self.app_var.get() == "generic":
            default_launch = True
        self.launch_var = tk.BooleanVar(value=default_launch)
        self.path_var = tk.StringVar(value=entry["config_entry"].get("install_path", "") if entry else "")
        self.exe_var = tk.StringVar(value=entry["config_entry"].get("exe_name", "") if entry else "")
        self.keyword_var = tk.StringVar(value=entry["config_entry"].get("title_keyword", "") if entry else "")
        saved_exe = entry["config_entry"].get("exe_name", "") if entry else ""
        self.browser_var = tk.StringVar(value="Chrome" if saved_exe == "chrome.exe" else "Edge")

        row = self._row()
        self._label(row, "应用：").pack(side=tk.LEFT)
        ctk.CTkOptionMenu(row, values=self.APP_IDS, variable=self.app_var, command=self._on_app_changed, width=scaled(self, 230), font=_dialog_font(self)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        row = self._row()
        self._label(row, "快捷键：").pack(side=tk.LEFT)
        _readonly_entry(row, self.hotkey_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkButton(row, text="录制", command=self._capture_hotkey, width=scaled(self, 82), font=_dialog_font(self)).pack(side=tk.LEFT, padx=(scaled(self, 8), 0))

        row = self._row()
        self._label(row, "启用：").pack(side=tk.LEFT)
        ctk.CTkCheckBox(row, text="", variable=self.enabled_var, width=scaled(self, 28), font=_dialog_font(self)).pack(side=tk.LEFT)

        row = self._row()
        self._label(row, "启动未运行：").pack(side=tk.LEFT)
        ctk.CTkCheckBox(row, text="", variable=self.launch_var, width=scaled(self, 28), font=_dialog_font(self)).pack(side=tk.LEFT)

        row = self._row()
        self._label(row, "安装路径：").pack(side=tk.LEFT)
        ctk.CTkEntry(row, textvariable=self.path_var, font=_dialog_font(self)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._secondary_button(row, "浏览", self._browse, width=82).pack(side=tk.LEFT, padx=(scaled(self, 8), 0))

        self.row_exe = self._row()
        self._label(self.row_exe, "exe 名称：").pack(side=tk.LEFT)
        ctk.CTkEntry(self.row_exe, textvariable=self.exe_var, font=_dialog_font(self)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.row_keyword = self._row()
        self._label(self.row_keyword, "标题关键词：").pack(side=tk.LEFT)
        ctk.CTkEntry(self.row_keyword, textvariable=self.keyword_var, font=_dialog_font(self)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.row_browser = self._row()
        self._label(self.row_browser, "浏览器：").pack(side=tk.LEFT)
        ctk.CTkOptionMenu(self.row_browser, values=["Edge", "Chrome"], variable=self.browser_var, width=scaled(self, 180), font=_dialog_font(self)).pack(side=tk.LEFT)

        btns = self._button_row()
        ctk.CTkButton(btns, text="确认", command=self._on_ok, width=scaled(self, 92), font=_dialog_font(self)).pack(side=tk.RIGHT, padx=(scaled(self, 8), 0))
        self._secondary_button(btns, "取消", self._on_cancel, width=92).pack(side=tk.RIGHT)

        self._on_app_changed()
        self._center_on_parent()

    def _capture_hotkey(self):
        dlg = HotkeyCaptureDialog(self, self.hotkey_var.get())
        self.wait_window(dlg)
        if getattr(dlg, "result", None):
            self.hotkey_var.set(dlg.result)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="选择可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
            parent=self,
        )
        if path:
            self.path_var.set(path)

    def _on_app_changed(self, _value=None):
        app = self.app_var.get()
        if app == "generic":
            self.row_exe.pack(fill=tk.X, pady=(0, scaled(self, 10)))
            self.row_keyword.pack(fill=tk.X, pady=(0, scaled(self, 10)))
            self.row_browser.pack_forget()
            if self.entry is None:
                self.launch_var.set(True)
        elif app == "web_app":
            self.row_exe.pack_forget()
            self.row_keyword.pack(fill=tk.X, pady=(0, scaled(self, 10)))
            self.row_browser.pack(fill=tk.X, pady=(0, scaled(self, 10)))
        else:
            self.row_exe.pack_forget()
            self.row_keyword.pack_forget()
            self.row_browser.pack_forget()
            if self.entry is None:
                self.launch_var.set(False)

    def _on_ok(self):
        hotkey = self.hotkey_var.get().strip()
        if not hotkey:
            messagebox.showwarning("提示", "请录制快捷键", parent=self)
            return

        app = self.app_var.get()
        if app == "web_app":
            keyword = self.keyword_var.get().strip()
            if not keyword:
                messagebox.showwarning("提示", "网页应用必须填写标题关键词", parent=self)
                return
            self.result = {
                "app": "web_app",
                "hotkey": hotkey,
                "enabled": self.enabled_var.get(),
                "launch_if_not_running": False,
                "install_path": "",
                "exe_name": self.BROWSER_MAP[self.browser_var.get()],
                "title_keyword": keyword,
            }
            self.destroy()
            return

        self.result = {
            "app": app,
            "hotkey": hotkey,
            "enabled": self.enabled_var.get(),
            "launch_if_not_running": self.launch_var.get(),
            "install_path": self.path_var.get().strip(),
        }
        if app == "generic":
            exe_name = self.exe_var.get().strip()
            install_path = self.path_var.get().strip()
            if not exe_name and not install_path:
                messagebox.showwarning("提示", "通用应用必须填写 exe 名称或安装路径", parent=self)
                return
            if exe_name:
                self.result["exe_name"] = exe_name
            self.result["title_keyword"] = self.keyword_var.get().strip()
        self.destroy()


class HotkeyManagerApp(ctk.CTk):
    SELF_APP_ID = "hot_key_manager"

    def __init__(self, manager: HotkeyManager):
        super().__init__()
        self.manager = manager
        self.ui_scale = _compute_ui_scale(self)
        ctk.set_widget_scaling(self.ui_scale)
        ctk.set_window_scaling(self.ui_scale)
        self.tk.call("tk", "scaling", self.ui_scale)

        self.title("App Hotkey Manager")
        self.geometry(f"{scaled(self, 1120)}x{scaled(self, 760)}")
        self.minsize(scaled(self, 900), scaled(self, 620))
        self.configure(fg_color=("#f4f4f5", "#18181b"))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_tree_style()
        self.manager.set_self_callback(self.toggle_ui)
        self._create_tray_icon()
        self._create_ui()
        self._refresh_list()
        self.manager.start_polling_thread()
        self.after(100, self._refresh_list)

        self.tray_menu = tk.Menu(self, tearoff=0, font=_menu_font(self))
        self.tray_menu.add_command(label="显示主窗口", command=self._show_window)
        self.tray_menu.add_separator()
        self.tray_menu.add_command(label="退出", command=self._quit_app)

        self._start_polling()
        self._start_hotkey_polling()

    def _setup_tree_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            borderwidth=0,
            relief="flat",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#18181b",
            font=("Microsoft YaHei UI", scaled(self, 20)),
            rowheight=scaled(self, 66),
        )
        style.configure(
            "Treeview.Heading",
            background="#e4e4e7",
            foreground="#27272a",
            relief="flat",
            font=("Microsoft YaHei UI", scaled(self, 21), "bold"),
        )
        style.map("Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

    def _create_programmatic_icon(self):
        size = 16
        hdc_screen = user32.GetDC(None)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, size, size)
        gdi32.SelectObject(hdc_mem, hbm)

        hbr_bg = gdi32.CreateSolidBrush(0x00CC6633)
        rect = wintypes.RECT(0, 0, size, size)
        user32.FillRect(hdc_mem, ctypes.byref(rect), hbr_bg)
        gdi32.DeleteObject(hbr_bg)

        gdi32.SetBkMode(hdc_mem, 1)
        hfont = gdi32.CreateFontW(12, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Consolas")
        old_font = gdi32.SelectObject(hdc_mem, hfont)
        gdi32.SetTextColor(hdc_mem, 0x00FFFFFF)
        gdi32.TextOutW(hdc_mem, 2, 1, "HK", 2)
        gdi32.SelectObject(hdc_mem, old_font)
        gdi32.DeleteObject(hfont)

        mask_bm = gdi32.CreateBitmap(size, size, 1, 1, None)
        hdc_mask = gdi32.CreateCompatibleDC(None)
        gdi32.SelectObject(hdc_mask, mask_bm)
        rect_mask = wintypes.RECT(0, 0, size, size)
        hbr_white = gdi32.CreateSolidBrush(0x00FFFFFF)
        user32.FillRect(hdc_mask, ctypes.byref(rect_mask), hbr_white)
        gdi32.DeleteObject(hbr_white)

        class ICONINFO(ctypes.Structure):
            _fields_ = [
                ("fIcon", wintypes.BOOL),
                ("xHotspot", wintypes.DWORD),
                ("yHotspot", wintypes.DWORD),
                ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p),
            ]

        icon_info = ICONINFO(True, 0, 0, mask_bm, hbm)
        h_icon = user32.CreateIconIndirect(ctypes.byref(icon_info))

        gdi32.DeleteObject(mask_bm)
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mask)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)
        return h_icon

    def _create_tray_icon(self):
        self.tray_hwnd = None
        self.tray_icon_id = TRAY_ICON_ID
        self._tray_event = 0

        self._tray_wndproc_ref = ctypes.WINFUNCTYPE(
            ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )(self._tray_wndproc_impl)

        wc = WNDCLASS()
        wc.lpfnWndProc = ctypes.cast(self._tray_wndproc_ref, ctypes.c_void_p)
        wc.lpszClassName = "AppHotkeyManagerTray"
        wc.hInstance = kernel32.GetModuleHandleW(None)
        user32.RegisterClassW(ctypes.byref(wc))

        self.tray_hwnd = user32.CreateWindowExW(
            0, wc.lpszClassName, "AppHotkeyManagerTray",
            0, 0, 0, 0, 0, None, None, wc.hInstance, None
        )

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.tray_hwnd
        nid.uID = self.tray_icon_id
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = 0x0400
        nid.hIcon = self._create_programmatic_icon()
        nid.szTip = "App Hotkey Manager"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _tray_wndproc_impl(self, hwnd, msg, wparam, lparam):
        if msg == 0x0400:
            self._tray_event = lparam
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_tray_menu(self):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.tray_hwnd)
        self.tray_menu.tk_popup(pt.x, pt.y)
        self.tray_menu.grab_release()

    def _remove_tray_icon(self):
        if self.tray_hwnd:
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = self.tray_hwnd
            nid.uID = self.tray_icon_id
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            user32.DestroyWindow(self.tray_hwnd)
            self.tray_hwnd = None

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def toggle_ui(self):
        if self.state() in {"withdrawn", "iconic"}:
            self._show_window()
        else:
            self.withdraw()

    def _create_ui(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill=tk.BOTH, expand=True, padx=scaled(self, 18), pady=scaled(self, 18))

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill=tk.X, pady=(0, scaled(self, 12)))
        ctk.CTkLabel(header, text="热键", font=ui_font(self, 20, "bold")).pack(side=tk.LEFT)

        toolbar = ctk.CTkFrame(outer, corner_radius=10)
        toolbar.pack(fill=tk.X, pady=(0, scaled(self, 12)))
        ctk.CTkButton(toolbar, text="添加", command=self._add_entry, width=76).pack(side=tk.LEFT, padx=(12, 6), pady=10)
        ctk.CTkButton(toolbar, text="编辑", command=self._edit_entry, width=76).pack(side=tk.LEFT, padx=6, pady=10)
        ctk.CTkButton(toolbar, text="删除", command=self._delete_entry, width=76, fg_color="#52525b", hover_color="#3f3f46").pack(side=tk.LEFT, padx=6, pady=10)
        ctk.CTkButton(toolbar, text="刷新", command=self._refresh_list, width=76, fg_color="#52525b", hover_color="#3f3f46").pack(side=tk.LEFT, padx=6, pady=10)
        self.running_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(toolbar, text="运行中", variable=self.running_var, onvalue=True, offvalue=False, command=self._toggle_all, font=ui_font(self, 14)).pack(side=tk.LEFT, padx=(scaled(self, 18), 0), pady=10)
        ctk.CTkButton(toolbar, text="退出", command=self._quit_app, width=76, fg_color="#991b1b", hover_color="#7f1d1d").pack(side=tk.RIGHT, padx=(6, 12), pady=10)

        list_frame = ctk.CTkFrame(outer, corner_radius=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("app", "hotkey", "enabled", "registered", "launch", "path")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("app", text="应用")
        self.tree.heading("hotkey", text="快捷键")
        self.tree.heading("enabled", text="启用")
        self.tree.heading("registered", text="注册")
        self.tree.heading("launch", text="启动未运行")
        self.tree.heading("path", text="安装路径")
        self.tree.column("app", width=160, minwidth=90)
        self.tree.column("hotkey", width=150, minwidth=110)
        self.tree.column("enabled", width=80, minwidth=60, anchor=tk.CENTER)
        self.tree.column("registered", width=130, minwidth=100, anchor=tk.CENTER)
        self.tree.column("launch", width=130, minwidth=100, anchor=tk.CENTER)
        self.tree.column("path", width=340, minwidth=140)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(scaled(self, 12), 0), pady=scaled(self, 12))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, scaled(self, 12)), pady=scaled(self, 12))

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

        self.context_menu = tk.Menu(self, tearoff=0, font=_menu_font(self))
        self.context_menu.add_command(label="编辑", command=self._edit_entry)
        self.context_menu.add_command(label="启用/禁用", command=self._toggle_entry)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除", command=self._delete_entry)

        status_frame = ctk.CTkFrame(outer, fg_color="transparent")
        status_frame.pack(fill=tk.X)
        self.status_label = ctk.CTkLabel(status_frame, text="就绪", text_color="#71717a", font=ui_font(self, 14))
        self.status_label.pack(side=tk.LEFT, padx=2, pady=(scaled(self, 8), 0))

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for entry in self.manager.entries:
            app_id = entry["config_entry"].get("app", "")
            if app_id == "generic":
                exe_name = entry["config_entry"].get("exe_name", "")
                if not exe_name:
                    install_path = entry["config_entry"].get("install_path", "")
                    if install_path:
                        exe_name = Path(install_path).name
                app_name = f"通用 | {exe_name}" if exe_name else "通用"
            elif app_id == "web_app":
                exe_name = entry["config_entry"].get("exe_name", "")
                browser = "Chrome" if exe_name == "chrome.exe" else "Edge"
                keyword = entry["config_entry"].get("title_keyword", "")
                app_name = f"网页 | {browser} | {keyword}"
            else:
                app_name = EntryDialog.APP_NAMES.get(app_id, app_id)
            hotkey = entry["hotkey"]
            enabled = "✓" if entry.get("enabled", True) else "✗"
            if not entry.get("enabled", True):
                registered = "未启用"
            elif entry.get("registered"):
                registered = "已注册"
            else:
                err = entry.get("last_error")
                registered = f"失败 {err}" if err else "待注册"
            launch = "✓" if entry["config_entry"].get("launch_if_not_running", False) else "✗"
            path = entry["config_entry"].get("install_path", "")
            self.tree.insert("", tk.END, iid=str(entry["id"]), values=(app_name, hotkey, enabled, registered, launch, path))
        self.status_label.configure(text=f"共 {len(self.manager.entries)} 个条目")

    def _start_polling(self):
        self._poll_tray_events()
        self.after(10, self._start_polling)

    def _start_hotkey_polling(self):
        self.manager.process_hotkeys()
        self.after(20, self._start_hotkey_polling)

    def _poll_tray_events(self):
        if self._tray_event:
            ev = self._tray_event
            self._tray_event = 0
            if ev == 0x0205:
                self._show_tray_menu()
            elif ev in {0x0202, 0x0203}:
                self._show_window()

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _add_entry(self):
        dlg = EntryDialog(self)
        self.wait_window(dlg)
        if getattr(dlg, "result", None):
            data = dlg.result
            try:
                entry = self.manager.add_entry(
                    app_id=data["app"],
                    hotkey=data["hotkey"],
                    enabled=data["enabled"],
                    launch_if_not_running=data["launch_if_not_running"],
                    install_path=data["install_path"],
                    exe_name=data.get("exe_name", ""),
                    title_keyword=data.get("title_keyword", ""),
                )
            except ValueError as exc:
                messagebox.showerror("错误", str(exc), parent=self)
                return
            if entry:
                self._refresh_list()
                self.after(100, self._refresh_list)

    def _edit_entry(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            messagebox.showinfo("提示", "请先选择一个条目", parent=self)
            return
        entry = self.manager.entry_map.get(entry_id)
        if not entry:
            return
        dlg = EntryDialog(self, entry)
        self.wait_window(dlg)
        if getattr(dlg, "result", None):
            data = dlg.result
            try:
                self.manager.update_entry(
                    entry_id=entry_id,
                    app_id=data["app"],
                    hotkey=data["hotkey"],
                    enabled=data["enabled"],
                    launch_if_not_running=data["launch_if_not_running"],
                    install_path=data["install_path"],
                    exe_name=data.get("exe_name", ""),
                    title_keyword=data.get("title_keyword", ""),
                )
            except ValueError as exc:
                messagebox.showerror("错误", str(exc), parent=self)
                return
            self._refresh_list()
            self.after(100, self._refresh_list)

    def _delete_entry(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            messagebox.showinfo("提示", "请先选择一个条目", parent=self)
            return
        if messagebox.askyesno("确认", "确定要删除这个条目吗？", parent=self):
            self.manager.remove_entry(entry_id)
            self._refresh_list()

    def _toggle_entry(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            messagebox.showinfo("提示", "请先选择一个条目", parent=self)
            return
        self.manager.toggle_entry(entry_id)
        self._refresh_list()
        self.after(100, self._refresh_list)

    def _toggle_all(self):
        if self.running_var.get():
            for entry in self.manager.entries:
                if entry.get("enabled", True):
                    self.manager._register_one(entry)
        else:
            self.manager.unregister_all()
        self._refresh_list()
        self.after(100, self._refresh_list)

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        entry_id = self._get_selected_id()
        if entry_id is None:
            return
        entry = self.manager.entry_map.get(entry_id)
        if not entry:
            return
        if column == "#3":
            self.manager.toggle_entry(entry_id)
            self._refresh_list()
            self.after(100, self._refresh_list)
        elif column == "#5":
            old_val = entry["config_entry"].get("launch_if_not_running", False)
            entry["config_entry"]["launch_if_not_running"] = not old_val
            self.manager._save_config()
            self._refresh_list()
        else:
            self._edit_entry()

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _on_close(self):
        self.withdraw()

    def _quit_app(self):
        self.manager.unregister_all()
        self._remove_tray_icon()
        self.manager.stop_polling_thread()
        self.after(100, self.destroy)
