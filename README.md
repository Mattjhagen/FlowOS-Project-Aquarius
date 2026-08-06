# FlowOS Desktop

An AI-powered desktop operating system interface. Instead of typing shell commands or clicking through menus, you talk to FlowOS and it runs your computer.

> Evolved from [Project Aquarius](https://github.com/Mattjhagen/FlowOS-Project-Aquarius) — originally a mobile OS concept, now a full desktop CLI with a bootable ISO on the roadmap.

---

## What it does

FlowOS replaces your shell session with an AI that has real system access. It can run commands, manage files, install packages, check resources, and control your machine — all through natural conversation.

```
→ what's eating my memory?
  → checking system resources
  Chrome is using 1.4GB (38%). Want me to kill it or just show you the breakdown?

→ push my flowos changes to github
  → git status
  → git commit: "update plugin system"
  → git push origin main
  Done. 3 files changed, pushed to main.

→ what's the weather in Austin?
  Austin, US
  Partly cloudy — 31°C / 88°F (feels like 34°C)
  Humidity: 62%  Wind: 18 km/h
```

---

## Install

```bash
git clone https://github.com/Mattjhagen/FlowOS-Project-Aquarius.git
cd FlowOS-Project-Aquarius
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
python3 flowos.py
```

On first launch, a setup wizard lets you pick which plugins to enable.

---

## Plugins

FlowOS ships with 6 optional plugins. Enable them at startup or anytime with the `plugins` command.

| Plugin | What it does |
|---|---|
| `git` | Status, commit, push, log, diff |
| `docker` | List containers, view logs, start/stop |
| `ssh` | Run commands on remote machines |
| `notes` | Save and retrieve persistent notes |
| `weather` | Current conditions and 3-day forecast |
| `clipboard` | Read from and write to the system clipboard |

### Managing plugins

```
→ plugins              # interactive toggle menu
→ enable docker        # enable a specific plugin
→ disable weather      # disable a specific plugin
→ reload plugins       # reload without restarting
```

---

## Built-in commands

| Command | Action |
|---|---|
| `clear` | Start a new session |
| `sessions` | View and resume past sessions |
| `plugins` | Open the plugin manager |
| `enable <name>` | Enable a plugin |
| `disable <name>` | Disable a plugin |
| `reload plugins` | Reload plugins live |
| `exit` | Quit |

---

## Core tools (always available)

- **run_command** — execute any shell command
- **read_file** / **write_file** — file I/O
- **get_system_info** — CPU, memory, disk usage
- **list_processes** — running processes
- **install_package** — auto-detects brew/apt/pip

---

## Roadmap

- [x] CLI with real system tool access
- [x] Persistent session history
- [x] Plugin system
- [ ] GUI layer (terminal emulator + chat panel)
- [ ] Bootable ISO (Alpine/Buildroot base)
- [ ] Local LLM support (offline mode via Ollama)
- [ ] Custom plugin API (write your own)

---

## Architecture

```
flowos.py          — main CLI loop + agent runner
tools.py           — core system tools
plugin_manager.py  — plugin loading, config, setup wizard
session.py         — session persistence (~/.flowos/sessions/)
plugins/
  base.py          — Plugin base class
  git_plugin.py
  docker_plugin.py
  ssh_plugin.py
  notes_plugin.py
  weather_plugin.py
  clipboard_plugin.py
```

Sessions and notes are stored in `~/.flowos/`.

---

## Writing a plugin

Create a file in `plugins/` that extends `Plugin`:

```python
from plugins.base import Plugin

class MyPlugin(Plugin):
    name = "myplugin"
    description = "Does something useful"

    @classmethod
    def tool_definitions(cls):
        return [{
            "name": "my_tool",
            "description": "Does a thing",
            "input_schema": {
                "type": "object",
                "properties": {
                    "arg": {"type": "string", "description": "An argument"}
                },
                "required": ["arg"]
            }
        }]

    @classmethod
    def tool_handlers(cls):
        return {
            "my_tool": lambda arg: f"You passed: {arg}"
        }
```

Then register it in `plugin_manager.py` under `AVAILABLE_PLUGINS`.

---

Built with [Claude](https://anthropic.com) · [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)
