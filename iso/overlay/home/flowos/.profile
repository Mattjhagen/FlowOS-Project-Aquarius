#!/bin/sh
# FlowOS auto-start on login

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/flowos"
export TERM=xterm-256color
export HOME=/home/flowos

# First-run: prompt for API key if not set
KEYFILE="$HOME/.flowos/api_key"
if [ ! -f "$KEYFILE" ]; then
    mkdir -p "$HOME/.flowos"
    cat /etc/motd
    echo ""
    echo "  To get started, enter your Anthropic API key."
    echo "  Get one free at: console.anthropic.com"
    echo ""
    printf "  API Key: "
    read -r ANTHROPIC_API_KEY
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "$ANTHROPIC_API_KEY" > "$KEYFILE"
        chmod 600 "$KEYFILE"
        echo ""
        echo "  Key saved. Starting FlowOS..."
        echo ""
    fi
fi

if [ -f "$KEYFILE" ]; then
    export ANTHROPIC_API_KEY=$(cat "$KEYFILE")
fi

# Launch FlowOS
exec python3 /opt/flowos/flowos.py
