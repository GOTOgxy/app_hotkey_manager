@echo off
setlocal
cd /d "%~dp0"

set "BAT=%CD%\app_hotkey_manager.bat"
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\App Hotkey Manager.lnk"

if not exist "%BAT%" (
  echo app_hotkey_manager.bat not found
  goto :end
)

set "VBS=%TEMP%\pin_to_start_%RANDOM%.vbs"
echo Set ws = CreateObject("WScript.Shell") > "%VBS%"
echo Set sc = ws.CreateShortcut("%LNK%") >> "%VBS%"
echo sc.TargetPath = "%BAT%" >> "%VBS%"
echo sc.WorkingDirectory = "%CD%" >> "%VBS%"
echo sc.Description = "App Hotkey Manager" >> "%VBS%"
echo sc.Save >> "%VBS%"
cscript //nologo "%VBS%"
del /f /q "%VBS%"

if exist "%LNK%" (
  echo.
  echo Done! Open Start Menu, find "App Hotkey Manager", right-click and select "Pin to Start".
) else (
  echo Create shortcut failed.
)

:end
echo.
pause
endlocal