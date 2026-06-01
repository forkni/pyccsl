@echo off
setlocal enabledelayedexpansion

echo.
echo  =====================================================
echo   pyccsl - Python Claude Code Status Line Installer
echo  =====================================================
echo.

:: ── Check Python ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found in PATH.
    echo          Install Python 3.10+ from https://python.org
    echo.
    pause & exit /b 1
)

:: ── Paths ─────────────────────────────────────────────
set "INSTALL_DIR=%USERPROFILE%\.claude"
set "SCRIPT_SRC=%~dp0pyccsl.py"
set "SCRIPT_DST=%INSTALL_DIR%\pyccsl.py"
set "SETTINGS_JSON=%INSTALL_DIR%\settings.json"

:: Verify source exists
if not exist "%SCRIPT_SRC%" (
    echo  [ERROR] pyccsl.py not found next to install.cmd.
    echo          Run install.cmd from the extracted folder.
    echo.
    pause & exit /b 1
)

:: ── Create .claude dir if needed ──────────────────────
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo  Created %INSTALL_DIR%
)

:: ── Copy script ───────────────────────────────────────
echo  Copying pyccsl.py to %INSTALL_DIR% ...
copy /Y "%SCRIPT_SRC%" "%SCRIPT_DST%" >nul
if errorlevel 1 (
    echo  [ERROR] Copy failed. Check permissions on %INSTALL_DIR%
    echo.
    pause & exit /b 1
)
echo  [OK] pyccsl.py installed.

:: ── Context window choice ─────────────────────────────
echo.
echo  Select context window for your model:
echo.
echo    1  200,000 tokens  ^(default - Sonnet / Haiku^)
echo    2  1,000,000 tokens ^(Opus extended context^)
echo    3  Custom value
echo.
set /p "CTX_CHOICE=  Enter 1, 2, or 3 [default=1]: "

if "!CTX_CHOICE!"=="2" (
    set "CTX=1000000"
    echo.
    echo  Using 1,000,000 token window.
) else if "!CTX_CHOICE!"=="3" (
    set /p "CTX=  Enter token count (e.g. 512000): "
    echo.
    echo  Using !CTX! token window.
) else (
    set "CTX=200000"
    echo.
    echo  Using 200,000 token window.
)

:: ── Write temp PowerShell helper ──────────────────────
set "PS_TMP=%TEMP%\pyccsl_install_%RANDOM%.ps1"

(
echo $claudeDir  = "$env:USERPROFILE\.claude"
echo $scriptPath = ($claudeDir -replace '\\','/'^) + '/pyccsl.py'
echo $settingsPath = $claudeDir + '\settings.json'
echo $fields = 'folder,git,model,perf-cache-rate,perf-session-time,perf-message-count,tokens,compact-remaining'
echo $cmd = "python $scriptPath $fields --style pipes --no-emoji --context-window %CTX%"
echo.
echo if (Test-Path $settingsPath^) {
echo     $raw = Get-Content $settingsPath -Raw -Encoding UTF8
echo     try   { $json = $raw ^| ConvertFrom-Json }
echo     catch { $json = [PSCustomObject]@{} }
echo } else {
echo     $json = [PSCustomObject]@{}
echo }
echo.
echo $sl = [PSCustomObject]@{ type = 'command'; command = $cmd }
echo.
echo if ($json.PSObject.Properties.Name -contains 'statusLine'^) {
echo     $json.statusLine = $sl
echo } else {
echo     $json ^| Add-Member -MemberType NoteProperty -Name 'statusLine' -Value $sl
echo }
echo.
echo $json ^| ConvertTo-Json -Depth 20 ^| Set-Content $settingsPath -Encoding UTF8
echo Write-Host " [OK] settings.json updated."
) > "%PS_TMP%"

:: ── Apply settings ────────────────────────────────────
echo.
echo  Updating Claude Code settings.json ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_TMP%"
set "PS_ERR=!errorlevel!"
del "%PS_TMP%" 2>nul

if !PS_ERR! neq 0 (
    echo.
    echo  [ERROR] Failed to update settings.json.
    echo          You can add the statusLine entry manually - see README.md.
    echo.
    pause & exit /b 1
)

:: ── Done ──────────────────────────────────────────────
echo.
echo  =====================================================
echo   Installation complete!
echo   Restart Claude Code to activate the status line.
echo  =====================================================
echo.
pause
endlocal
