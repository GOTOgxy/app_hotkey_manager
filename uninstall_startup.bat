@echo off
setlocal

set "TARGET_EXE=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\app_hotkey_manager.exe"

if exist "%TARGET_EXE%" (
  del /f /q "%TARGET_EXE%"
  if exist "%TARGET_EXE%" (
    echo Remove failed.
  ) else (
    echo Startup entry removed.
  )
) else (
  echo Startup EXE was not found.
)

echo.
pause
endlocal
