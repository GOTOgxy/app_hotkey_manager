@echo off
setlocal

cd /d "%~dp0"

python -V >nul 2>nul
if errorlevel 1 (
  echo Python was not found in PATH.
  echo Please add python to PATH first.
  goto :end
)

python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo PyInstaller is not installed for the current python.
  echo Run: python -m pip install pyinstaller
  goto :end
)

if not exist "app_hotkey_config.json" (
  echo Config file not found: app_hotkey_config.json
  echo Please create or edit app_hotkey_config.json first.
  goto :end
)

echo Using python from PATH
echo Working directory: %CD%
echo.

if exist "dist\app_hotkey_manager.exe" (
  del /f /q "dist\app_hotkey_manager.exe" >nul 2>nul
  if exist "dist\app_hotkey_manager.exe" (
    echo Existing dist\app_hotkey_manager.exe could not be replaced.
    echo Please close the running exe and try again.
    goto :end
  )
)

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  app_hotkey_manager.spec

if errorlevel 1 (
  echo.
  echo Build failed.
  goto :end
)

echo.
echo Build complete.
echo Output: %CD%\dist\app_hotkey_manager.exe

:end
echo.
pause
endlocal
