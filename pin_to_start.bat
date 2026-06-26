@echo off
setlocal

cd /d "%~dp0"

set "BAT_PATH=%CD%\app_hotkey_manager.bat"
set "SHORTCUT_NAME=App Hotkey Manager"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "SHORTCUT_PATH=%START_MENU%\%SHORTCUT_NAME%.lnk"

if not exist "%BAT_PATH%" (
  echo app_hotkey_manager.bat not found:
  echo %BAT_PATH%
  goto :end
)

powershell -NoProfile -ExecutionPolicy Bypass -Command " = New-Object -ComObject WScript.Shell;  = .CreateShortcut('%SHORTCUT_PATH%'); .TargetPath = '%BAT_PATH%'; .WorkingDirectory = '%CD%'; .Description = 'App Hotkey Manager'; .Save(); Write-Host 'Shortcut created: %SHORTCUT_PATH%'"

if exist "%SHORTCUT_PATH%" (
  echo.
  echo Done! Open Start Menu, find "App Hotkey Manager", right-click and select "Pin to Start".
) else (
  echo Create shortcut failed.
)

:end
echo.
pause
endlocal