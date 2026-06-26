$batPath = Join-Path $PSScriptRoot "app_hotkey_manager.bat"
$startMenu = [Environment]::GetFolderPath("StartMenu") + "\Programs"
$shortcutPath = Join-Path $startMenu "App Hotkey Manager.lnk"

if (-not (Test-Path $batPath)) {
    Write-Host "app_hotkey_manager.bat not found: $batPath"
    pause
    exit 1
}

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = $batPath
$sc.WorkingDirectory = $PSScriptRoot
$sc.Description = "App Hotkey Manager"
$sc.Save()

Write-Host "Shortcut created: $shortcutPath"
Write-Host ""
Write-Host "Done! Open Start Menu, find 'App Hotkey Manager', right-click and select 'Pin to Start'."
pause
