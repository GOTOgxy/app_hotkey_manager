@echo off
setlocal

cd /d "%~dp0"

set "SOURCE_EXE=%CD%\dist\app_hotkey_manager.exe"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_EXE=%STARTUP_DIR%\app_hotkey_manager.exe"

if not exist "%SOURCE_EXE%" (
  echo EXE not found:
  echo %SOURCE_EXE%
  echo Please build the project first.
  goto :end
)

copy /y "%SOURCE_EXE%" "%TARGET_EXE%" >nul
if errorlevel 1 (
  echo Install failed.
  goto :end
)

if exist "%TARGET_EXE%" (
  echo Startup install complete.
  echo %TARGET_EXE%
) else (
  echo Install failed.
)

:end
echo.
pause
endlocal
