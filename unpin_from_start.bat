@echo off
setlocal

set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "SHORTCUT_PATH=%START_MENU%\App Hotkey Manager.lnk"

if exist "%SHORTCUT_PATH%" (
  del /f /q "%SHORTCUT_PATH%"
  echo Shortcut removed.
) else (
  echo Shortcut not found.
)

echo.
pause
endlocal