#!/bin/sh
# FlowOS auto-start on login

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/flowos"
export TERM=xterm-256color
export HOME=/home/flowos

KEYFILE="$HOME/.flowos/api_key"
mkdir -p "$HOME/.flowos"

# Load API key if it exists
if [ -f "$KEYFILE" ]; then
    export ANTHROPIC_API_KEY=$(cat "$KEYFILE")
fi

# SSH session: drop to a normal shell — key is already exported above
if [ -n "$SSH_CONNECTION" ]; then
    echo ""
    echo "  FlowOS — connected via SSH"
    echo "  Run 'flowos' to start the AI interface."
    echo ""
    exec /bin/bash
fi

# Console login: prompt for key on first boot, then launch FlowOS
if [ -z "$ANTHROPIC_API_KEY" ]; then
    cat /etc/motd 2>/dev/null
    echo ""
    echo "  To get started, enter your Anthropic API key."
    echo "  Get one at: console.anthropic.com"
    echo ""
    printf "  API Key: "
    read -r ANTHROPIC_API_KEY
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "$ANTHROPIC_API_KEY" > "$KEYFILE"
        chmod 600 "$KEYFILE"
        export ANTHROPIC_API_KEY
        echo ""
        echo "  Key saved. Starting FlowOS..."
        echo ""
    fi
fi

exec python3 /opt/flowos/flowos.py
