#!/bin/bash
# FlowOS Universal Installer — macOS · Linux · Termux (Android)
# Usage: curl -fsSL https://flowos.wiki/install.sh | bash

set -e

FLOWOS_DIR="$HOME/.flowos"
REPO="https://raw.githubusercontent.com/Mattjhagen/FlowOS-Project-Aquarius/main"
KEYFILE="$FLOWOS_DIR/api_key"

# ── Detect platform ──────────────────────────────────────────────
detect_platform() {
    if [ -d "/data/data/com.termux" ] && [ -n "$PREFIX" ]; then
        echo "termux"
    elif [ "$(uname -s)" = "Darwin" ]; then
        echo "macos"
    elif [ "$(uname -s)" = "Linux" ]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

PLATFORM=$(detect_platform)

case "$PLATFORM" in
    termux)
        BIN_DIR="$PREFIX/bin"
        PYTHON="python3"
        ;;
    macos|linux)
        BIN_DIR="$HOME/.local/bin"
        PYTHON="python3"
        ;;
    *)
        echo ""
        echo "  Unsupported platform detected."
        echo "  On Windows, run this in PowerShell instead:"
        echo "    irm https://flowos.wiki/install.ps1 | iex"
        echo ""
        exit 1
        ;;
esac

BIN="$BIN_DIR/flowos"

# Create dirs upfront
mkdir -p "$FLOWOS_DIR/plugins"
mkdir -p "$BIN_DIR"

# ── Colors ───────────────────────────────────────────────────────
CY='\033[38;5;45m'
WH='\033[97m'
GR='\033[38;5;245m'
YL='\033[38;5;220m'
RD='\033[38;5;196m'
BD='\033[1m'
RS='\033[0m'

ok()   { echo -e "  ${CY}+${RS}  ${WH}$1${RS}"; }
info() { echo -e "  ${GR}·  $1${RS}"; }
warn() { echo -e "  ${YL}!${RS}  ${YL}$1${RS}"; }
fail() { echo -e "  ${RD}x${RS}  ${RD}$1${RS}"; exit 1; }
step() { echo -e "\n  ${CY}${BD}$1${RS}"; }

# ── Banner ───────────────────────────────────────────────────────
echo ""
echo -e "  ${CY}${BD}"
echo '   ███████╗██╗      ██████╗ ██╗    ██╗ ██████╗ ███████╗'
echo '   ██╔════╝██║     ██╔═══██╗██║    ██║██╔═══██╗██╔════╝'
echo '   █████╗  ██║     ██║   ██║██║ █╗ ██║██║   ██║███████╗'
echo '   ██╔══╝  ██║     ██║   ██║██║███╗██║██║   ██║╚════██║'
echo '   ██║     ███████╗╚██████╔╝╚███╔███╔╝╚██████╔╝███████║'
echo '   ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝ ╚══════╝'
echo -e "${RS}"

case "$PLATFORM" in
    termux) EDITION="Termux / Android Edition" ;;
    macos)  EDITION="macOS Edition" ;;
    linux)  EDITION="Linux Edition" ;;
esac
echo -e "           ${GR}AI-Powered Desktop OS  ·  ${EDITION}${RS}"
echo ""
echo -e "  ${CY}─────────────────────────────────────────────────────${RS}"
echo ""

# ── Check Python ─────────────────────────────────────────────────
step "Checking Python..."
if ! command -v "$PYTHON" &>/dev/null; then
    case "$PLATFORM" in
        macos)  fail "Python 3 not found. Install with: brew install python3  or  https://python.org/downloads" ;;
        linux)  fail "Python 3 not found. Install with: sudo apt install python3 python3-pip" ;;
    esac
fi
PY_VER=$("$PYTHON" --version 2>&1)
ok "$PY_VER found"

# ── Install system packages ──────────────────────────────────────
step "Installing system packages..."
case "$PLATFORM" in
    termux)
        pkg update -y -q 2>/dev/null || true
        pkg install -y -q python python-pip python-psutil git curl rust 2>/dev/null || true
        ok "Termux packages ready"
        ;;
    macos)
        # macOS: python3 + pip already available; no extra pkg manager needed
        ok "macOS system deps already present"
        ;;
    linux)
        # Try to ensure pip is available
        if ! "$PYTHON" -m pip --version &>/dev/null 2>&1; then
            if command -v apt-get &>/dev/null; then
                warn "Installing python3-pip via apt..."
                sudo apt-get install -y -q python3-pip 2>/dev/null || true
            elif command -v dnf &>/dev/null; then
                warn "Installing python3-pip via dnf..."
                sudo dnf install -y -q python3-pip 2>/dev/null || true
            elif command -v pacman &>/dev/null; then
                warn "Installing python-pip via pacman..."
                sudo pacman -S --noconfirm python-pip 2>/dev/null || true
            else
                warn "Could not install pip automatically — ensure pip3 is available."
            fi
        fi
        ok "Linux deps ready"
        ;;
esac

# ── Install Python packages ──────────────────────────────────────
step "Installing Python packages..."
case "$PLATFORM" in
    termux)
        # psutil installed via pkg (pre-built); skip it in pip
        "$PYTHON" -m pip install --quiet anthropic rich prompt_toolkit requests
        ;;
    macos|linux)
        "$PYTHON" -m pip install --quiet --user anthropic rich prompt_toolkit requests psutil
        ;;
esac
ok "Python packages installed"

# ── Download FlowOS source ────────────────────────────────────────
step "Downloading FlowOS..."
FILES="flowos.py tools.py session.py plugin_manager.py"
for f in $FILES; do
    curl -fsSL "$REPO/$f" -o "$FLOWOS_DIR/$f" \
        && info "$f" \
        || fail "Failed to download $f"
done

PLUGINS="base file_manager git_plugin web_browser notes code_runner system_monitor weather clipboard"
for p in $PLUGINS; do
    curl -fsSL "$REPO/plugins/${p}.py" -o "$FLOWOS_DIR/plugins/${p}.py" 2>/dev/null \
        && info "plugins/${p}.py" || true
done
ok "FlowOS source downloaded"

# ── API key setup ────────────────────────────────────────────────
step "API key setup..."
if [ -f "$KEYFILE" ] && [ -s "$KEYFILE" ]; then
    ok "Existing API key found — keeping it"
else
    echo ""
    echo -e "  ${WH}Enter your Anthropic API key to get started.${RS}"
    echo -e "  ${GR}Get one at: console.anthropic.com${RS}"
    echo ""
    printf "  API Key: "
    read -r API_KEY
    if [ -n "$API_KEY" ]; then
        echo "$API_KEY" > "$KEYFILE"
        chmod 600 "$KEYFILE"
        ok "API key saved"
    else
        warn "No key entered — add later: echo 'sk-...' > ~/.flowos/api_key"
    fi
fi

# ── Create launcher ───────────────────────────────────────────────
step "Creating launcher..."
cat > "$BIN" << LAUNCHER
#!/bin/bash
KEYFILE="\$HOME/.flowos/api_key"
if [ -f "\$KEYFILE" ] && [ -s "\$KEYFILE" ]; then
    export ANTHROPIC_API_KEY=\$(cat "\$KEYFILE")
fi
if [ -z "\$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "  No API key found. Enter your Anthropic API key:"
    printf "  API Key: "
    read -r ANTHROPIC_API_KEY
    if [ -n "\$ANTHROPIC_API_KEY" ]; then
        echo "\$ANTHROPIC_API_KEY" > "\$KEYFILE"
        chmod 600 "\$KEYFILE"
        export ANTHROPIC_API_KEY
    fi
fi
exec ${PYTHON} "\$HOME/.flowos/flowos.py" "\$@"
LAUNCHER

chmod +x "$BIN"
ok "Launcher created at $BIN"

# Install updater
curl -fsSL "$REPO/termux/update.sh" -o "$BIN_DIR/flowos-update" 2>/dev/null \
    && chmod +x "$BIN_DIR/flowos-update" \
    && ok "Updater created at $BIN_DIR/flowos-update" || true

# ── PATH check (macOS/Linux) ─────────────────────────────────────
if [ "$PLATFORM" = "macos" ] || [ "$PLATFORM" = "linux" ]; then
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        echo ""
        warn "Add ~/.local/bin to your PATH to use the 'flowos' command:"
        echo ""
        echo -e "  ${CY}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc${RS}"
        echo -e "  ${GR}(replace .zshrc with .bashrc if you use bash)${RS}"
    fi
fi

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo -e "  ${CY}─────────────────────────────────────────────────────${RS}"
echo ""
echo -e "  ${CY}${BD}FlowOS is ready!${RS}"
echo ""
echo -e "  ${WH}Start FlowOS:${RS}   ${CY}flowos${RS}"
echo -e "  ${WH}Update:${RS}         ${CY}flowos-update${RS}"
echo -e "  ${WH}Change API key:${RS} ${CY}echo 'sk-...' > ~/.flowos/api_key${RS}"
echo ""
