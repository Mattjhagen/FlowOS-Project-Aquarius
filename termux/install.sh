#!/data/data/com.termux/files/usr/bin/bash
# FlowOS installer for Termux (Android)
# Usage: curl -fsSL https://flowos.wiki/install.sh | bash

set -e

FLOWOS_DIR="$HOME/.flowos"
BIN="$PREFIX/bin/flowos"
KEYFILE="$HOME/.flowos/api_key"
REPO="https://raw.githubusercontent.com/Mattjhagen/FlowOS-Project-Aquarius/main"

# ── Colors ──────────────────────────────────────────────────────
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

echo ""
echo -e "  ${CY}${BD}"
echo '   ███████╗██╗      ██████╗ ██╗    ██╗ ██████╗ ███████╗'
echo '   ██╔════╝██║     ██╔═══██╗██║    ██║██╔═══██╗██╔════╝'
echo '   █████╗  ██║     ██║   ██║██║ █╗ ██║██║   ██║███████╗'
echo '   ██╔══╝  ██║     ██║   ██║██║███╗██║██║   ██║╚════██║'
echo '   ██║     ███████╗╚██████╔╝╚███╔███╔╝╚██████╔╝███████║'
echo '   ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝ ╚══════╝'
echo -e "${RS}"
echo -e "              ${GR}AI-Powered Desktop OS  ·  Termux Edition${RS}"
echo ""
echo -e "  ${CY}─────────────────────────────────────────────────────${RS}"
echo ""

# ── Check Termux ────────────────────────────────────────────────
if [ -z "$PREFIX" ] || [ ! -d "/data/data/com.termux" ]; then
    warn "This installer is designed for Termux on Android."
    warn "It may still work on other Linux systems."
fi

# ── Update & install system packages ────────────────────────────
step "Installing system packages..."
pkg update -y -q 2>/dev/null || true
pkg install -y -q \
    python \
    python-pip \
    git \
    curl \
    clang \
    libffi \
    openssl \
    2>/dev/null
ok "System packages ready"

# ── Install Python dependencies ──────────────────────────────────
step "Installing Python packages..."
pip install --quiet --upgrade pip 2>/dev/null || true
pip install --quiet \
    anthropic \
    rich \
    prompt_toolkit \
    psutil \
    requests
ok "Python packages installed"

# ── Download FlowOS source ────────────────────────────────────────
step "Downloading FlowOS..."
mkdir -p "$FLOWOS_DIR/plugins"

FILES="flowos.py tools.py session.py plugin_manager.py"
for f in $FILES; do
    curl -fsSL "$REPO/$f" -o "$FLOWOS_DIR/$f" \
        && info "  $f" \
        || fail "Failed to download $f"
done

# Download plugins
PLUGINS="file_manager git_plugin web_browser notes code_runner system_monitor weather clipboard"
for p in $PLUGINS; do
    curl -fsSL "$REPO/plugins/${p}.py" -o "$FLOWOS_DIR/plugins/${p}.py" 2>/dev/null \
        && info "  plugins/${p}.py" || true
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
        ok "API key saved to $KEYFILE"
    else
        warn "No key entered — you can add it later: echo 'sk-...' > $KEYFILE"
    fi
fi

# ── Create launcher ───────────────────────────────────────────────
step "Creating launcher..."
cat > "$BIN" << 'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
FLOWOS_DIR="$HOME/.flowos"
KEYFILE="$FLOWOS_DIR/api_key"

if [ -f "$KEYFILE" ] && [ -s "$KEYFILE" ]; then
    export ANTHROPIC_API_KEY=$(cat "$KEYFILE")
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "  No API key found. Enter your Anthropic API key:"
    echo "  (get one at console.anthropic.com)"
    echo ""
    printf "  API Key: "
    read -r ANTHROPIC_API_KEY
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "$ANTHROPIC_API_KEY" > "$KEYFILE"
        chmod 600 "$KEYFILE"
        export ANTHROPIC_API_KEY
    fi
fi

exec python "$FLOWOS_DIR/flowos.py" "$@"
LAUNCHER

chmod +x "$BIN"
ok "Launcher created at $BIN"

# Install updater
curl -fsSL "$REPO/termux/update.sh" -o "$PREFIX/bin/flowos-update" 2>/dev/null \
    && chmod +x "$PREFIX/bin/flowos-update" \
    && ok "Updater created at $PREFIX/bin/flowos-update" || true

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
echo -e "  ${GR}Tip: pin Termux to your home screen for instant AI access.${RS}"
echo ""
