# -*- coding: utf-8 -*-

import ctypes
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from hotkey_manager import (
    MOD_CONTROL, MOD_ALT, MOD_SHIFT, MOD_WIN,
    WM_LBUTTONDBLCLK, WM_RBUTTONUP,
    TRAY_ICON_ID, NIF_MESSAGE, NIF_ICON, NIF_TIP,
    NIM_ADD, NIM_DELETE,
    gdi32, user32, kernel32, shell32,
    WNDCLASS, NOTIFYICONDATAW,
    HotkeyManager, parse_hotkey, VIRTUAL_KEYS,
)


class HotkeyCaptureDialog(tk.Toplevel):
    def __init__(self, parent, current_hotkey: str = ""):
        super().__init__(parent)
        self.title("录制快捷键")
        self.geometry("400x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.captured_hotkey = current_hotkey
        self.modifiers = 0
        self.virtual_key = 0
        self.captured = False
        self._pressed_modifiers = set()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="请按下快捷键组合：", font=("", 12)).pack(pady=(0, 10))

        self.hotkey_var = tk.StringVar(value=current_hotkey or "等待输入...")
        self.hotkey_label = ttk.Label(main_frame, textvariable=self.hotkey_var, font=("", 14, "bold"))
        self.hotkey_label.pack(pady=(0, 10))

        self.debug_var = tk.StringVar(value="")
        ttk.Label(main_frame, textvariable=self.debug_var, font=("", 9), foreground="gray").pack()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()

        self.ok_btn = ttk.Button(btn_frame, text="确认", command=self._on_ok, state=tk.DISABLED)
        self.ok_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="清除", command=self._on_clear).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

        self.bind("<KeyPress>", self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)

    def _on_key_release(self, event):
        self._pressed_modifiers.discard(event.keysym)

    def _on_key_press(self, event):
        MODIFIER_KEYSYM = {
            "Control_L": MOD_CONTROL, "Control_R": MOD_CONTROL,
            "Alt_L": MOD_ALT, "Alt_R": MOD_ALT,
            "Shift_L": MOD_SHIFT, "Shift_R": MOD_SHIFT,
            "Super_L": MOD_WIN, "Super_R": MOD_WIN,
            "Meta_L": MOD_WIN, "Meta_R": MOD_WIN,
        }

        if event.keysym in MODIFIER_KEYSYM:
            self._pressed_modifiers.add(event.keysym)
            return

        modifiers = 0
        for ks in self._pressed_modifiers:
            modifiers |= MODIFIER_KEYSYM.get(ks, 0)

        key_upper = event.keysym.upper()
        virtual_key = VIRTUAL_KEYS.get(key_upper)

        if virtual_key is None:
            if len(event.char) == 1:
                char = event.char.upper()
                virtual_key = VIRTUAL_KEYS.get(char)

        if virtual_key is None or modifiers == 0:
            return

        self.modifiers = modifiers
        self.virtual_key = virtual_key
        self.captured = True

        parts = []
        if modifiers & MOD_CONTROL:
            parts.append("CTRL")
        if modifiers & MOD_ALT:
            parts.append("ALT")
        if modifiers & MOD_SHIFT:
            parts.append("SHIFT")
        if modifiers & MOD_WIN:
            parts.append("WIN")
        parts.append(key_upper)

        self.captured_hotkey = "+".join(parts)
        self.hotkey_var.set(self.captured_hotkey)
        self.debug_var.set(f"tracked modifiers: {self._pressed_modifiers}")
        self.ok_btn.config(state=tk.NORMAL)

    def _on_clear(self):
        self.captured_hotkey = ""
        self.modifiers = 0
        self.virtual_key = 0
        self.captured = False
        self._pressed_modifiers.clear()
        self.hotkey_var.set("等待输入...")
        self.ok_btn.config(state=tk.DISABLED)

    def _on_ok(self):
        if self.captured:
            self.result = self.captured_hotkey
            self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class EntryDialog(tk.Toplevel):
    APP_IDS = ["cloudmusic", "zotero", "termius", "hot_key_manager", "generic"]
    APP_NAMES = {"cloudmusic": "网易云音乐", "zotero": "Zotero", "termius": "Termius", "hot_key_manager": "Hot Key Manager", "generic": "通用应用"}

    def __init__(self, parent, entry: dict | None = None):
        super().__init__(parent)
        self.title("编辑条目" if entry else "添加条目")
        self.geometry("450x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.entry = entry
        self.result = None

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        row1 = ttk.Frame(main_frame)
        row1.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row1, text="应用：", width=10).pack(side=tk.LEFT)
        self.app_var = tk.StringVar(value=entry["config_entry"]["app"] if entry else self.APP_IDS[0])
        self.app_combo = ttk.Combobox(row1, textvariable=self.app_var, values=self.APP_IDS, state="readonly", width=20)
        self.app_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.app_combo.bind("<<ComboboxSelected>>", self._on_app_changed)

        row2 = ttk.Frame(main_frame)
        row2.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row2, text="快捷键：", width=10).pack(side=tk.LEFT)
        self.hotkey_var = tk.StringVar(value=entry["hotkey"] if entry else "")
        self.hotkey_entry = ttk.Entry(row2, textvariable=self.hotkey_var, state="readonly", width=20)
        self.hotkey_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row2, text="录制", command=self._capture_hotkey, width=6).pack(side=tk.LEFT, padx=(5, 0))

        row3 = ttk.Frame(main_frame)
        row3.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row3, text="启用：", width=10).pack(side=tk.LEFT)
        self.enabled_var = tk.BooleanVar(value=entry["enabled"] if entry else True)
        ttk.Checkbutton(row3, variable=self.enabled_var).pack(side=tk.LEFT)

        row4 = ttk.Frame(main_frame)
        row4.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row4, text="启动未运行：", width=10).pack(side=tk.LEFT)
        self.launch_var = tk.BooleanVar(
            value=entry["config_entry"].get("launch_if_not_running", False) if entry else False
        )
        ttk.Checkbutton(row4, variable=self.launch_var).pack(side=tk.LEFT)

        row5 = ttk.Frame(main_frame)
        row5.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row5, text="安装路径：", width=10).pack(side=tk.LEFT)
        self.path_var = tk.StringVar(
            value=entry["config_entry"].get("install_path", "") if entry else ""
        )
        ttk.Entry(row5, textvariable=self.path_var, width=25).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row5, text="浏览", command=self._browse, width=6).pack(side=tk.LEFT, padx=(5, 0))

        self.row_exe = ttk.Frame(main_frame)
        self.row_exe.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.row_exe, text="exe 名称：", width=10).pack(side=tk.LEFT)
        self.exe_var = tk.StringVar(
            value=entry["config_entry"].get("exe_name", "") if entry else ""
        )
        ttk.Entry(self.row_exe, textvariable=self.exe_var, width=25).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.row_keyword = ttk.Frame(main_frame)
        self.row_keyword.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.row_keyword, text="标题关键词：", width=10).pack(side=tk.LEFT)
        self.keyword_var = tk.StringVar(
            value=entry["config_entry"].get("title_keyword", "") if entry else ""
        )
        ttk.Entry(self.row_keyword, textvariable=self.keyword_var, width=25).pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="确认", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT)

        self._on_app_changed()

    def _capture_hotkey(self):
        dlg = HotkeyCaptureDialog(self, self.hotkey_var.get())
        self.wait_window(dlg)
        if hasattr(dlg, "result") and dlg.result:
            self.hotkey_var.set(dlg.result)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="选择可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if path:
            self.path_var.set(path)

    def _on_app_changed(self, event=None):
        is_generic = self.app_var.get() == "generic"
        if is_generic:
            self.row_exe.pack(fill=tk.X, pady=(0, 10))
            self.row_keyword.pack(fill=tk.X, pady=(0, 10))
        else:
            self.row_exe.pack_forget()
            self.row_keyword.pack_forget()

    def _on_ok(self):
        hotkey = self.hotkey_var.get().strip()
        if not hotkey:
            messagebox.showwarning("提示", "请录制快捷键", parent=self)
            return

        self.result = {
            "app": self.app_var.get(),
            "hotkey": hotkey,
            "enabled": self.enabled_var.get(),
            "launch_if_not_running": self.launch_var.get(),
            "install_path": self.path_var.get().strip(),
        }

        if self.app_var.get() == "generic":
            exe_name = self.exe_var.get().strip()
            install_path = self.path_var.get().strip()
            if not exe_name and not install_path:
                messagebox.showwarning("提示", "通用应用必须填写 exe 名称或安装路径", parent=self)
                return
            if exe_name:
                self.result["exe_name"] = exe_name
            self.result["title_keyword"] = self.keyword_var.get().strip()

        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class HotkeyManagerApp(tk.Tk):
    SELF_APP_ID = "hot_key_manager"

    def __init__(self, manager: HotkeyManager):
        super().__init__()
        self.manager = manager

        self.title("App Hotkey Manager")
        self.geometry("700x400")
        self.minsize(600, 300)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.manager.set_self_callback(self.toggle_ui)
        self._create_tray_icon()
        self._create_ui()
        self._refresh_list()
        self.manager.start_polling_thread()

        self.tray_menu = tk.Menu(self, tearoff=0)
        self.tray_menu.add_command(label="显示主窗口", command=self._show_window)
        self.tray_menu.add_separator()
        self.tray_menu.add_command(label="退出", command=self._quit_app)

        self._start_polling()

    def _create_programmatic_icon(self):
        SIZE = 16
        hdc_screen = user32.GetDC(None)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, SIZE, SIZE)
        gdi32.SelectObject(hdc_mem, hbm)

        hbr_bg = gdi32.CreateSolidBrush(0x00CC6633)
        rect = wintypes.RECT(0, 0, SIZE, SIZE)
        user32.FillRect(hdc_mem, ctypes.byref(rect), hbr_bg)
        gdi32.DeleteObject(hbr_bg)

        gdi32.SetBkMode(hdc_mem, 1)
        hfont = gdi32.CreateFontW(
            12, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Consolas"
        )
        old_font = gdi32.SelectObject(hdc_mem, hfont)
        gdi32.SetTextColor(hdc_mem, 0x00FFFFFF)
        gdi32.TextOutW(hdc_mem, 2, 1, "HK", 2)
        gdi32.SelectObject(hdc_mem, old_font)
        gdi32.DeleteObject(hfont)

        mask_bm = gdi32.CreateBitmap(SIZE, SIZE, 1, 1, None)
        hdc_mask = gdi32.CreateCompatibleDC(None)
        gdi32.SelectObject(hdc_mask, mask_bm)
        rect_mask = wintypes.RECT(0, 0, SIZE, SIZE)
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

        icon_info = ICONINFO()
        icon_info.fIcon = True
        icon_info.xHotspot = 0
        icon_info.yHotspot = 0
        icon_info.hbmMask = mask_bm
        icon_info.hbmColor = hbm
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

        h_icon = self._create_programmatic_icon()

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.tray_hwnd
        nid.uID = self.tray_icon_id
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = 0x0400
        nid.hIcon = h_icon
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
        if self.state() == "withdrawn" or self.state() == "iconic":
            self._show_window()
        else:
            self.withdraw()

    def _create_ui(self):
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="添加", command=self._add_entry, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除", command=self._delete_entry, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑", command=self._edit_entry, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(toolbar, text="启用/禁用", command=self._toggle_entry, width=10).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(toolbar, text="退出", command=self._quit_app, width=8).pack(side=tk.RIGHT, padx=2)

        list_frame = ttk.Frame(self, padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("app", "hotkey", "enabled", "launch", "path")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("app", text="应用")
        self.tree.heading("hotkey", text="快捷键")
        self.tree.heading("enabled", text="启用")
        self.tree.heading("launch", text="启动未运行")
        self.tree.heading("path", text="安装路径")

        self.tree.column("app", width=100, minwidth=80)
        self.tree.column("hotkey", width=120, minwidth=100)
        self.tree.column("enabled", width=60, minwidth=50, anchor=tk.CENTER)
        self.tree.column("launch", width=90, minwidth=80, anchor=tk.CENTER)
        self.tree.column("path", width=200, minwidth=100)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self._edit_entry())
        self.tree.bind("<Button-3>", self._on_right_click)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self._edit_entry)
        self.context_menu.add_command(label="启用/禁用", command=self._toggle_entry)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除", command=self._delete_entry)

        status_frame = ttk.Frame(self, padding=(5, 2))
        status_frame.pack(fill=tk.X)
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

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
            else:
                app_name = EntryDialog.APP_NAMES.get(app_id, app_id)
            hotkey = entry["hotkey"]
            enabled = "是" if entry.get("enabled", True) else "否"
            launch = "是" if entry["config_entry"].get("launch_if_not_running", False) else "否"
            path = entry["config_entry"].get("install_path", "")

            self.tree.insert("", tk.END, iid=str(entry["id"]),
                           values=(app_name, hotkey, enabled, launch, path))

        count = len(self.manager.entries)
        self.status_label.config(text=f"共 {count} 个条目")

    def _start_polling(self):
        self.manager.process_hotkeys()

        if self._tray_event:
            ev = self._tray_event
            self._tray_event = 0
            if ev == 0x0205:  # WM_RBUTTONUP
                self._show_tray_menu()
            elif ev == 0x0202:  # WM_LBUTTONUP
                self._show_window()
            elif ev == 0x0203:  # WM_LBUTTONDBLCLK
                self._show_window()

        self.after(50, self._start_polling)

    def _get_selected_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _add_entry(self):
        dlg = EntryDialog(self)
        self.wait_window(dlg)

        if hasattr(dlg, "result") and dlg.result:
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
            except ValueError as e:
                messagebox.showerror("错误", str(e))
                return
            if entry:
                self._refresh_list()

    def _edit_entry(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            messagebox.showinfo("提示", "请先选择一个条目")
            return

        entry = self.manager.entry_map.get(entry_id)
        if not entry:
            return

        dlg = EntryDialog(self, entry)
        self.wait_window(dlg)

        if hasattr(dlg, "result") and dlg.result:
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
            except ValueError as e:
                messagebox.showerror("错误", str(e))
                return
            self._refresh_list()

    def _delete_entry(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            messagebox.showinfo("提示", "请先选择一个条目")
            return

        if messagebox.askyesno("确认", "确定要删除这个条目吗？"):
            self.manager.remove_entry(entry_id)
            self._refresh_list()

    def _toggle_entry(self):
        entry_id = self._get_selected_id()
        if entry_id is None:
            messagebox.showinfo("提示", "请先选择一个条目")
            return

        self.manager.toggle_entry(entry_id)
        self._refresh_list()

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
