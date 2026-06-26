@echo off
setlocal

set "TARGET=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\app_hotkey_manager.bat"

if exist "%TARGET%" (
  del /f /q "%TARGET%"
  if exist "%TARGET%" (
    echo Remove failed.
  ) else (
    echo Startup entry removed.
  )
) else (
  echo Startup entry was not found.
)

echo.
pause
endlocal