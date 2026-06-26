# App Hotkey Manager

Windows 全局快捷键管理工具。通过系统托盘运行，支持为多个应用绑定全局快捷键，实现一键切换/隐藏/启动。

零依赖，纯 Python stdlib 实现，通过 ctypes 直接调用 Win32 API。

## 功能

- 全局快捷键注册（RegisterHotKey），后台常驻
- 系统托盘图标，单击/双击显示 UI，右键菜单
- 内置管理界面（tkinter），支持添加/编辑/删除/启用/禁用快捷键
- 支持录制快捷键（自动识别修饰键 + 主键）
- 允许快捷键重复，通过启用/禁用控制
- 双击列表直接切换"启用"和"启动未运行"状态
- 工具栏"运行中"全局开关，一键启用/禁用所有热键
- 配置文件可选，缺失时以空配置启动
- 单实例运行（Mutex）
- 支持开机自启动

## 内置支持的应用

### 网易云音乐 `cloudmusic`

| 状态 | 行为 |
|------|------|
| 未启动 | 不处理 |
| 已启动，不在前台 | 切到前台 |
| 已在前台 | 隐藏（托盘模式） |
| 已启动但无可见窗口 | 尝试恢复到前台 |

### Zotero `zotero`

| 状态 | 行为 |
|------|------|
| 未启动 | 可按配置启动 |
| 已启动，不在前台 | 切到前台 |
| 已在前台 | 最小化 + 从任务栏隐藏 |
| 已启动但无可见窗口 | 尝试恢复到前台 |

### Termius `termius`

| 状态 | 行为 |
|------|------|
| 未启动 | 可按配置启动 |
| 已启动，不在前台 | 切到前台 |
| 已在前台 | 最小化 + 从任务栏隐藏 |
| 已启动但无可见窗口 | 尝试恢复到前台 |

### 自身 `hot_key_manager`

绑定后可通过快捷键切换管理界面的显示/隐藏。

### 通用应用 `generic`

支持任意 Windows 应用，只需填写 exe 名称或安装路径（至少填一个）。通过兜底逻辑查找主窗口（有标题的可见窗口）。

| 配置项 | 必填 | 说明 |
|--------|------|------|
| `exe_name` | 二选一 | 可执行文件名，如 `QQMusic.exe`（可从安装路径自动提取） |
| `install_path` | 二选一 | 安装路径，用于启动应用 |
| `title_keyword` | 否 | 窗口标题关键词，用于更精确匹配主窗口 |

## 项目结构

| 文件 | 职责 |
|------|------|
| `app.py` | 入口：mutex 单实例检查 + mainloop |
| `hotkey_manager.py` | 核心逻辑：Win32 API、AppController、HotkeyManager — **零 tkinter** |
| `gui.py` | 界面：tkinter UI、托盘图标、对话框 |
| `app_hotkey_config.json` | 运行时配置（可选） |
| `app_hotkey_manager.bat` | 双击启动（`pythonw app.py`） |
| `install_startup.bat` | 安装开机自启动 |
| `uninstall_startup.bat` | 卸载开机自启动 |
| `pin_to_start.bat` | 在开始菜单创建快捷方式，手动固定到开始屏幕 |
| `requirements.txt` | Python 依赖（无第三方依赖） |

## 技术架构

```
┌─────────────────────────────────────────────────┐
│                   main thread                    │
│                                                  │
│  ┌──────────────────┐   ┌─────────────────────┐ │
│  │  tkinter mainloop │   │  tray window (HWND) │ │
│  │  (message pump)   │   │  WndProc callback    │ │
│  │                   │   │  sets flag on click  │ │
│  │  after(10) polls: │   └─────────────────────┘ │
│  │  - tray events    │                           │
│  │  after(20) polls: │                           │
│  │  - hotkey queue   │                           │
│  └────────┬──────────┘                           │
│           │                                      │
│  ┌────────▼──────────────────────────────────┐  │
│  │         HotkeyManagerApp (tk.Tk)          │  │
│  │  - Treeview list UI (双击切换启用/启动)   │  │
│  │  - "运行中" 全局开关                       │  │
│  │  - EntryDialog (add/edit)                 │  │
│  │  - HotkeyCaptureDialog (record hotkey)    │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ thread-safe queue
┌──────────────────────▼──────────────────────────┐
│              hotkey polling thread               │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  hidden message-only HWND                  │ │
│  │  - created in this thread                  │ │
│  │  - RegisterHotKey / UnregisterHotKey       │ │
│  │  - PeekMessageW(WM_HOTKEY) → queue         │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 关键设计决策

**为什么热键在子线程？**
- tkinter 的消息循环会消费所有 Win32 消息（包括 WM_HOTKEY）
- 如果热键窗口在主线程，`PeekMessageW` 无法获取消息
- 子线程拥有独立的消息循环和 HWND，热键消息不会被 tkinter 抢占

**为什么托盘在主线程？**
- ctypes 的 `WINFUNCTYPE` 回调需要 Python GIL
- 托盘窗口的 WndProc 由 tkinter 消息泵调用（主线程持有 GIL），回调安全
- 子线程的 ctypes 回调会因 GIL 问题崩溃（`PyEval_RestoreThread` 错误）

**线程通信方式：**
- 热键线程 → 主线程：`_hotkey_queue`（thread-safe list + Lock）
- 托盘线程 → 主线程：`_tray_event` flag（主线程 `after(10)` 轮询读取）
- 主线程 → 热键线程：`_pending_registers` / `_pending_unregisters` 队列

**任务栏隐藏（Zotero / Termius）：**
- 通过 `SetWindowLongPtrW` 将 `WS_EX_APPWINDOW` 切换为 `WS_EX_TOOLWINDOW`
- 同时保存/恢复窗口位置（`GetWindowRect` / `SetWindowPos`）
- 禁用 DWM 动画（`DWMWA_TRANSITIONS_FORCEDISABLED`）实现即时切换

### 核心类

| 类 | 文件 | 职责 |
|---|------|------|
| `AppController` | hotkey_manager.py | 应用控制逻辑：查找进程、窗口激活/隐藏、启动应用 |
| `HotkeyManager` | hotkey_manager.py | 快捷键生命周期：注册/注销/轮询/增删改查条目 |
| `CallbackController` | hotkey_manager.py | 通用回调控制器（用于 `hot_key_manager`） |
| `HotkeyManagerApp` | gui.py | tkinter UI：列表展示、托盘图标、对话框 |
| `EntryDialog` | gui.py | 添加/编辑条目对话框 |
| `HotkeyCaptureDialog` | gui.py | 快捷键录制对话框 |

### Win32 API 调用

通过 ctypes 直接调用，无第三方依赖：

| API | 用途 |
|-----|------|
| `RegisterHotKey` / `UnregisterHotKey` | 注册/注销全局热键 |
| `PeekMessageW` | 非阻塞读取消息 |
| `EnumWindows` | 枚举窗口查找目标应用主窗口 |
| `SetForegroundWindow` | 切换到前台 |
| `ShowWindow` | 显示/隐藏/最小化窗口 |
| `Shell_NotifyIconW` | 管理系统托盘图标 |
| `DwmSetWindowAttribute` | 禁用窗口动画 |
| `SetWindowLongPtrW` | 修改窗口扩展样式（任务栏隐藏） |
| `CreateToolhelp32Snapshot` | 枚举进程 |

## 配置

配置文件：`app_hotkey_config.json`（可选，缺失时以空配置启动）

```json
{
  "display_name": "App Hotkey Manager",
  "mutex_name": "Global\\AppHotkeyManager",
  "entries": [
    {
      "app": "cloudmusic",
      "hotkey": "CTRL+ALT+Q",
      "launch_if_not_running": false,
      "install_path": ""
    },
    {
      "app": "zotero",
      "hotkey": "CTRL+ALT+Z",
      "launch_if_not_running": true,
      "install_path": "C:\\Program Files\\Zotero\\zotero.exe"
    },
    {
      "app": "termius",
      "hotkey": "CTRL+ALT+T",
      "launch_if_not_running": true,
      "install_path": ""
    },
    {
      "app": "hot_key_manager",
      "hotkey": "CTRL+ALT+H",
      "launch_if_not_running": false,
      "install_path": ""
    },
    {
      "app": "generic",
      "exe_name": "QQMusic.exe",
      "title_keyword": "",
      "hotkey": "CTRL+ALT+M",
      "install_path": "C:\\Program Files\\Tencent\\QQMusic\\QQMusic.exe"
    }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `display_name` | 运行时显示名称 |
| `mutex_name` | 单实例互斥体名称，一般不用改 |
| `entries` | 快捷键绑定列表 |
| `app` | 应用 ID：`cloudmusic`、`zotero`、`termius`、`hot_key_manager`、`generic` |
| `hotkey` | 快捷键字符串 |
| `enabled` | 是否启用（默认 `true`），可通过 UI 切换 |
| `launch_if_not_running` | 未启动时是否尝试启动 |
| `install_path` | 安装路径，留空则自动查找（注册表 App Paths → 默认路径） |

### 快捷键写法

格式：`修饰键+修饰键+主键`

```text
CTRL+ALT+Q
CTRL+ALT+Z
CTRL+SHIFT+Z
ALT+F10
WIN+1
```

支持的修饰键：`CTRL`、`ALT`、`SHIFT`、`WIN`

支持的主键：`A-Z`、`0-9`、`F1-F24`、`TAB`、`ESC`、`SPACE`、`ENTER`、方向键、`HOME`、`END`、`PAGEUP`、`PAGEDOWN`、`INSERT`、`DELETE`

### install_path 查找顺序

1. 配置中填写的 `install_path`
2. Windows 注册表 `App Paths`
3. 内置的常见默认安装路径

## 文件说明

| 文件 | 作用 |
|------|------|
| `app.py` | 入口文件 |
| `hotkey_manager.py` | 核心逻辑（Win32 API、控制器、管理器） |
| `gui.py` | tkinter UI（主界面、对话框、托盘） |
| `app_hotkey_config.json` | 运行时配置 |
| `app_hotkey_manager.bat` | 双击启动 |
| `install_startup.bat` | 安装开机自启动 |
| `uninstall_startup.bat` | 卸载开机自启动 |
| `pin_to_start.bat` | 在开始菜单创建快捷方式 |
| `requirements.txt` | Python 依赖（空，无第三方依赖） |
| `README.md` | 项目文档 |

## 环境

- Windows 10 / 11
- Python 3.10+（`PATH` 中可用）

## 运行

双击 `app_hotkey_manager.bat`，或命令行执行：

```bat
pythonw app.py
```

- 左键点击托盘图标：显示管理界面
- 右键点击托盘图标：菜单（显示 / 退出）
- 关闭窗口（X）：最小化到托盘
- 配置 `hot_key_manager` 快捷键：切换界面显示/隐藏

## 开机自启动

```bat
install_startup.bat
uninstall_startup.bat
```

将启动脚本复制到 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`，用户登录后自动运行。

## 固定到开始屏幕

双击 `pin_to_start.bat`，在开始菜单创建快捷方式后右键固定到开始屏幕。
