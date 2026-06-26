@echo off
setlocal

cd /d "%~dp0"

set "SOURCE=%CD%\app_hotkey_manager.bat"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP_DIR%\app_hotkey_manager.bat"

if not exist "%SOURCE%" (
  echo app_hotkey_manager.bat not found:
  echo %SOURCE%
  goto :end
)

copy /y "%SOURCE%" "%TARGET%" >nul
if errorlevel 1 (
  echo Install failed.
  goto :end
)

if exist "%TARGET%" (
  echo Startup install complete.
  echo %TARGET%
) else (
  echo Install failed.
)

:end
echo.
pause
endlocal