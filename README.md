# App Hotkey Manager

这是一个只运行在 Windows 上的快捷键管理工具。

你可以在构建前填写一份配置，把多个全局快捷键绑定到多个已支持的软件上。构建完成后会生成一个 `exe`，运行这个 `exe` 后，就会按配置注册这些快捷键。

当前内置支持的软件：

- `cloudmusic`
- `zotero`

## 当前行为

### 网易云 `cloudmusic`

- 未启动时：默认不处理
- 已启动且不在前台：切到前台
- 已在前台：隐藏
- 已启动但没有可见主窗口：尝试恢复到前台

### Zotero `zotero`

- 未启动时：可按配置决定是否启动
- 已启动且不在前台：切到前台
- 已在前台：最小化
- 已启动但没有可见主窗口：尝试恢复到前台

## 配置文件

构建前请编辑：

[`app_hotkey_config.json`](C:\Users\gxy\Documents\New project 2\app_hotkey_config.json)

模板：

[`app_hotkey_config.example.json`](C:\Users\gxy\Documents\New project 2\app_hotkey_config.example.json)

配置示例：

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
    }
  ]
}
```

### 字段说明

- `display_name`
  运行时的显示名称
- `mutex_name`
  单实例互斥体名称，一般不用改
- `entries`
  快捷键绑定列表
- `app`
  当前支持 `cloudmusic` 或 `zotero`
- `hotkey`
  快捷键字符串
- `launch_if_not_running`
  程序未启动时是否尝试启动
- `install_path`
  程序安装路径。建议在需要“未启动时自动启动”的软件上填写

### 关于 `install_path`

- 如果你希望软件未启动时也能通过快捷键拉起，建议填写 `install_path`
- 这比写死在代码里更适合迁移到另一台机器
- 如果 `install_path` 为空，程序会继续尝试：
  - Windows 注册表中的 `App Paths`
  - 常见默认安装路径

也就是说：

- `install_path` 是推荐项
- 不是唯一方案
- 对 Win10 和 Win11 都通用

### 快捷键写法

格式：

```text
修饰键+修饰键+主键
```

示例：

```text
CTRL+ALT+Q
CTRL+SHIFT+Z
ALT+F10
WIN+1
```

支持的修饰键：

- `CTRL`
- `ALT`
- `SHIFT`
- `WIN`

支持的主键：

- `A` 到 `Z`
- `0` 到 `9`
- `F1` 到 `F24`
- `TAB`
- `ESC`
- `SPACE`
- `ENTER`
- `LEFT`
- `UP`
- `RIGHT`
- `DOWN`
- `HOME`
- `END`
- `PAGEUP`
- `PAGEDOWN`
- `INSERT`
- `DELETE`

## 打包环境

- Windows 10 或 Windows 11
- `python` 已加入系统 `PATH`
- 已安装 Python 包 `pyinstaller`

安装：

```powershell
python -m pip install pyinstaller
```

## 构建

1. 编辑 [`app_hotkey_config.json`](C:\Users\gxy\Documents\New project 2\app_hotkey_config.json)
2. 运行：

```bat
build_exe.bat
```

输出文件：

[`app_hotkey_manager.exe`](C:\Users\gxy\Documents\New project 2\dist\app_hotkey_manager.exe)

## 运行

直接运行：

[`app_hotkey_manager.exe`](C:\Users\gxy\Documents\New project 2\dist\app_hotkey_manager.exe)

最终用户运行 `exe` 时，不需要安装 Python。

## 开机自启动

安装开机自启动：

```bat
install_startup.bat
```

删除开机自启动：

```bat
uninstall_startup.bat
```

当前实现方式：

- `install_startup.bat` 会把 [`app_hotkey_manager.exe`](C:\Users\gxy\Documents\New project 2\dist\app_hotkey_manager.exe) 复制到当前用户的启动目录
- 启动目录位置是 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
- 用户登录 Windows 后，系统会自动运行这个目录中的 `app_hotkey_manager.exe`
