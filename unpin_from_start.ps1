$startMenu = [Environment]::GetFolderPath("StartMenu") + "\Programs"
$shortcutPath = Join-Path $startMenu "App Hotkey Manager.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item -Path $shortcutPath -Force
    Write-Host "Shortcut removed."
} else {
    Write-Host "Shortcut not found."
}
pause
