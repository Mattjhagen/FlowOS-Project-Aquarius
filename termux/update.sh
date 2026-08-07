#!/data/data/com.termux/files/usr/bin/bash
# FlowOS updater for Termux
# Installed at $PREFIX/bin/flowos-update

FLOWOS_DIR="$HOME/.flowos"
REPO="https://raw.githubusercontent.com/Mattjhagen/FlowOS-Project-Aquarius/main"

CY='\033[38;5;45m'; WH='\033[97m'; GR='\033[38;5;245m'
RD='\033[38;5;196m'; BD='\033[1m'; RS='\033[0m'

ok()   { echo -e "  ${CY}+${RS}  ${WH}$1${RS}"; }
info() { echo -e "  ${GR}·  $1${RS}"; }
fail() { echo -e "  ${RD}x${RS}  ${RD}$1${RS}"; exit 1; }

echo ""
echo -e "  ${CY}${BD}Updating FlowOS...${RS}\n"

pip install --quiet --upgrade anthropic rich prompt_toolkit psutil requests
ok "Python packages updated"

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

echo ""
ok "FlowOS updated. Run: flowos"
echo ""
