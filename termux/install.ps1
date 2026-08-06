# FlowOS Windows Installer
# Usage (PowerShell): irm https://flowos.wiki/install.ps1 | iex
#
# Requires: Python 3 — https://python.org/downloads
#           (check "Add Python to PATH" during install)

$ErrorActionPreference = "Stop"

$FLOWOS_DIR = "$env:USERPROFILE\.flowos"
$REPO = "https://raw.githubusercontent.com/Mattjhagen/FlowOS-Project-Aquarius/main"
$KEYFILE = "$FLOWOS_DIR\api_key"
$LAUNCHER_DIR = "$env:USERPROFILE\.local\bin"

function ok($msg)   { Write-Host "  [+] $msg" -ForegroundColor Cyan }
function info($msg) { Write-Host "   ·  $msg" -ForegroundColor Gray }
function warn($msg) { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function step($msg) { Write-Host "`n  >>> $msg" -ForegroundColor Cyan }
function fail($msg) { Write-Host "  [x] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "   ███████╗██╗      ██████╗ ██╗    ██╗ ██████╗ ███████╗" -ForegroundColor Cyan
Write-Host "   ██╔════╝██║     ██╔═══██╗██║    ██║██╔═══██╗██╔════╝" -ForegroundColor Cyan
Write-Host "   █████╗  ██║     ██║   ██║██║ █╗ ██║██║   ██║███████╗" -ForegroundColor Cyan
Write-Host "   ██╔══╝  ██║     ██║   ██║██║███╗██║██║   ██║╚════██║" -ForegroundColor Cyan
Write-Host "   ██║     ███████╗╚██████╔╝╚███╔███╔╝╚██████╔╝███████║" -ForegroundColor Cyan
Write-Host "   ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝ ╚══════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "           AI-Powered Desktop OS  ·  Windows Edition" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ─────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host ""

# ── Find Python ───────────────────────────────────────────────────
step "Checking Python..."
$PYTHON = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ("$ver" -match "Python 3") {
            $PYTHON = $cmd
            ok "$ver found ($cmd)"
            break
        }
    } catch {}
}

if (-not $PYTHON) {
    warn "Python 3 not found."
    Write-Host ""
    Write-Host "  Install Python 3 from: https://python.org/downloads" -ForegroundColor White
    Write-Host "  (check 'Add Python to PATH' during install)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Then re-run this installer." -ForegroundColor White
    Write-Host ""
    exit 1
}

# ── Create dirs ───────────────────────────────────────────────────
step "Setting up directories..."
New-Item -ItemType Directory -Force -Path "$FLOWOS_DIR\plugins" | Out-Null
New-Item -ItemType Directory -Force -Path $LAUNCHER_DIR | Out-Null
ok "Directories created"

# ── Install Python packages ────────────────────────────────────────
step "Installing Python packages..."
& $PYTHON -m pip install --quiet --upgrade pip
& $PYTHON -m pip install --quiet anthropic rich prompt_toolkit requests psutil
ok "Python packages installed"

# ── Download FlowOS source ─────────────────────────────────────────
step "Downloading FlowOS..."
$FILES = @("flowos.py", "tools.py", "session.py", "plugin_manager.py")
foreach ($f in $FILES) {
    try {
        Invoke-WebRequest -Uri "$REPO/$f" -OutFile "$FLOWOS_DIR\$f" -UseBasicParsing
        info $f
    } catch {
        fail "Failed to download $f"
    }
}

$PLUGINS = @("file_manager","git_plugin","web_browser","notes","code_runner","system_monitor","weather","clipboard")
foreach ($p in $PLUGINS) {
    try {
        Invoke-WebRequest -Uri "$REPO/plugins/${p}.py" -OutFile "$FLOWOS_DIR\plugins\${p}.py" -UseBasicParsing
        info "plugins\${p}.py"
    } catch {}
}
ok "FlowOS source downloaded"

# ── API key setup ──────────────────────────────────────────────────
step "API key setup..."
if ((Test-Path $KEYFILE) -and (Get-Item $KEYFILE).Length -gt 0) {
    ok "Existing API key found — keeping it"
} else {
    Write-Host ""
    Write-Host "  Enter your Anthropic API key." -ForegroundColor White
    Write-Host "  Get one at: console.anthropic.com" -ForegroundColor DarkGray
    Write-Host ""
    $API_KEY = Read-Host "  API Key"
    if ($API_KEY) {
        Set-Content -Path $KEYFILE -Value $API_KEY -NoNewline
        ok "API key saved"
    } else {
        warn "No key entered — add later: Set-Content ~\.flowos\api_key 'sk-...'"
    }
}

# ── Create launcher ────────────────────────────────────────────────
step "Creating launcher..."

$launcherBat = @"
@echo off
set KEYFILE=%USERPROFILE%\.flowos\api_key
if exist "%KEYFILE%" (
    for /f "usebackq delims=" %%K in ("%KEYFILE%") do set ANTHROPIC_API_KEY=%%K
)
if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo   No API key found.
    set /p ANTHROPIC_API_KEY="  Enter Anthropic API key: "
    echo %ANTHROPIC_API_KEY% > "%KEYFILE%"
)
${PYTHON} "%USERPROFILE%\.flowos\flowos.py" %*
"@
Set-Content -Path "$LAUNCHER_DIR\flowos.bat" -Value $launcherBat
ok "Launcher created at $LAUNCHER_DIR\flowos.bat"

# ── Add to PATH ────────────────────────────────────────────────────
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$LAUNCHER_DIR*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$LAUNCHER_DIR", "User")
    ok "Added $LAUNCHER_DIR to user PATH"
    warn "Restart your terminal for 'flowos' to work"
}

# ── Done ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ─────────────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host ""
Write-Host "  FlowOS is ready!" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Start FlowOS:   " -NoNewline -ForegroundColor White
Write-Host "flowos" -ForegroundColor Cyan
Write-Host "  Update:         " -NoNewline -ForegroundColor White
Write-Host "flowos-update" -ForegroundColor Cyan
Write-Host "  Change API key: " -NoNewline -ForegroundColor White
Write-Host "Set-Content ~\.flowos\api_key 'sk-...'" -ForegroundColor Cyan
Write-Host ""
