#!/usr/bin/env python3
import os
import sys
import platform
import anthropic

# --store flag: launch the GUI plugin store
if "--store" in sys.argv:
    from gui.server import run as run_store
    run_store()
    sys.exit(0)
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from pathlib import Path

from tools import TOOL_DEFINITIONS as CORE_TOOLS, execute_tool as execute_core_tool
from session import load_session, save_session, list_sessions, new_session_id
from plugin_manager import (
    load_active_plugins, get_all_tools, show_plugin_table,
    setup_wizard, enable_plugin, disable_plugin, load_config, AVAILABLE_PLUGINS
)

console = Console()

HISTORY_FILE = Path.home() / ".flowos" / "history"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
PLUGINS_CONFIG = Path.home() / ".flowos" / "plugins.json"

SYSTEM_PROMPT = f"""You are FlowOS, an AI-powered desktop operating system assistant. You ARE the operating system interface — not a helper layered on top of it.

System: {platform.system()} {platform.release()} ({platform.machine()})
User home: {Path.home()}

Your role:
- Execute real system tasks using your tools — don't just describe what to do, do it
- Be concise and action-oriented. Narrate what you're doing as you do it
- When a user asks to open, install, run, or configure something — do it
- After running a command, always summarize the result in plain language
- If something fails, diagnose and try an alternative
- Maintain awareness of what's been done in this session
- Never ask for confirmation on read-only operations
- For writes, installs, or deletes — briefly state what you're about to do, then do it

You have core tools for: shell commands, file I/O, system resources, processes, and package installs.
Additional plugin tools may also be available depending on what the user has enabled.

Keep responses short and direct. You are the OS, not a chatbot."""


def print_banner(active_plugins: list):
    plugin_names = [p.name for p in active_plugins]
    subtitle = f"[dim]plugins: {', '.join(plugin_names) or 'none'} · 'plugins' to manage · 'exit' to quit[/dim]"
    console.print(Panel(
        Text("FlowOS Desktop", style="bold cyan", justify="center"),
        subtitle=subtitle,
        border_style="cyan"
    ))
    console.print()


def build_tool_executor(plugin_handlers: dict):
    def execute_tool(name: str, inputs: dict) -> str:
        # Try core tools first, then plugins
        if name in plugin_handlers:
            try:
                result = plugin_handlers[name](**inputs)
                return str(result) if result is not None else "Done."
            except Exception as e:
                return f"Plugin tool error: {e}"
        return execute_core_tool(name, inputs)
    return execute_tool


def print_tool_call(name: str, inputs: dict):
    label = {
        "run_command": f"[dim]$ {inputs.get('command', '')}[/dim]",
        "read_file": f"[dim]reading {inputs.get('path', '')}[/dim]",
        "write_file": f"[dim]writing {inputs.get('path', '')}[/dim]",
        "get_system_info": "[dim]checking system resources[/dim]",
        "list_processes": "[dim]listing processes[/dim]",
        "install_package": f"[dim]installing {inputs.get('package', '')}[/dim]",
        "git_status": "[dim]git status[/dim]",
        "git_commit": f"[dim]git commit: {inputs.get('message', '')}[/dim]",
        "git_push": "[dim]git push[/dim]",
        "git_log": "[dim]git log[/dim]",
        "git_diff": "[dim]git diff[/dim]",
        "docker_ps": "[dim]docker ps[/dim]",
        "docker_logs": f"[dim]docker logs {inputs.get('container', '')}[/dim]",
        "ssh_run": f"[dim]ssh {inputs.get('host', '')} '{inputs.get('command', '')}'[/dim]",
        "note_save": f"[dim]saving note: {inputs.get('title', '')}[/dim]",
        "note_get": f"[dim]reading note: {inputs.get('title', '')}[/dim]",
        "note_list": "[dim]listing notes[/dim]",
        "weather_now": f"[dim]weather: {inputs.get('location', 'auto')}[/dim]",
        "clipboard_read": "[dim]reading clipboard[/dim]",
        "clipboard_write": "[dim]writing to clipboard[/dim]",
        "browser_open": f"[dim]opening {inputs.get('url', '')}[/dim]",
        "browser_search": f"[dim]searching: {inputs.get('query', '')}[/dim]",
        "browser_screenshot": f"[dim]screenshot of {inputs.get('url', '')}[/dim]",
        "browser_fetch": f"[dim]fetching {inputs.get('url', '')}[/dim]",
        "spotify_play_pause": "[dim]spotify: play/pause[/dim]",
        "spotify_next": "[dim]spotify: next track[/dim]",
        "spotify_prev": "[dim]spotify: previous track[/dim]",
        "spotify_current": "[dim]spotify: current track[/dim]",
        "spotify_volume": f"[dim]spotify: volume → {inputs.get('level', '')}[/dim]",
        "spotify_open": "[dim]opening Spotify[/dim]",
        "spotify_search": f"[dim]spotify search: {inputs.get('query', '')}[/dim]",
        "server_status": "[dim]server: checking status[/dim]",
        "server_services": "[dim]server: listing services[/dim]",
        "server_logs": f"[dim]server: logs for {inputs.get('service', '')}[/dim]",
        "server_restart_service": f"[dim]server: restarting {inputs.get('service', '')}[/dim]",
        "server_docker_ps": "[dim]server: docker ps[/dim]",
        "server_docker_logs": f"[dim]server: docker logs {inputs.get('container', '')}[/dim]",
        "server_deploy": f"[dim]server: deploying {inputs.get('repo_path', '')}[/dim]",
        "server_snap_list": "[dim]server: snap list[/dim]",
        "server_snap_install": f"[dim]server: snap install {inputs.get('package', '')}[/dim]",
        "server_run": f"[dim]server: $ {inputs.get('command', '')}[/dim]",
    }.get(name, f"[dim]{name}({', '.join(f'{k}={v}' for k, v in inputs.items())})[/dim]")
    console.print(f"  [cyan]→[/cyan] {label}")


def run_agent_loop(client: anthropic.Anthropic, messages: list, session_id: str,
                   all_tools: list, execute_tool):
    while True:
        with Live(Spinner("dots", text="[cyan]thinking...[/cyan]"), console=console, refresh_per_second=10):
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=all_tools,
                messages=messages
            )

        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if text_parts:
            text = "\n".join(text_parts).strip()
            if text:
                console.print(Markdown(text))
                console.print()

        if not tool_uses or response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            save_session(session_id, messages)
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tool_use in tool_uses:
            print_tool_call(tool_use.name, tool_use.input)
            result = execute_tool(tool_use.name, tool_use.input)
            if len(str(result)) > 3000:
                result = str(result)[:3000] + "\n... (truncated)"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result)
            })

        console.print()
        messages.append({"role": "user", "content": tool_results})
        save_session(session_id, messages)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.")
        console.print("Set it with: [cyan]export ANTHROPIC_API_KEY=your_key[/cyan]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # First-run setup wizard
    if not PLUGINS_CONFIG.exists():
        setup_wizard(first_run=True)

    # Load plugins
    active_plugins = load_active_plugins()
    plugin_tool_defs, plugin_handlers = get_all_tools(active_plugins)
    all_tools = CORE_TOOLS + plugin_tool_defs
    execute_tool = build_tool_executor(plugin_handlers)

    print_banner(active_plugins)

    # Resume session flag
    session_id = new_session_id()
    messages = []

    if len(sys.argv) > 1 and sys.argv[1] == "--resume":
        sessions = list_sessions()
        if sessions:
            console.print("[bold]Recent sessions:[/bold]")
            for i, s in enumerate(sessions[:5]):
                console.print(f"  [cyan]{i+1}.[/cyan] [{s['modified']}] {s['preview']}")
            console.print()
            choice = prompt("Resume session (number) or Enter for new: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(sessions):
                selected = sessions[int(choice) - 1]
                session_id = selected["id"]
                messages = load_session(session_id)
                console.print(f"[dim]Resumed session from {selected['modified']}[/dim]\n")

    history = FileHistory(str(HISTORY_FILE))

    while True:
        try:
            user_input = prompt(
                "→ ",
                history=history,
                auto_suggest=AutoSuggestFromHistory()
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.lower() == "clear":
            messages = []
            session_id = new_session_id()
            console.clear()
            print_banner(active_plugins)
            console.print("[dim]Session cleared.[/dim]\n")
            continue

        if user_input.lower() == "sessions":
            sessions = list_sessions()
            if not sessions:
                console.print("[dim]No previous sessions.[/dim]\n")
            else:
                console.print("[bold]Recent sessions:[/bold]")
                for i, s in enumerate(sessions[:5]):
                    console.print(f"  [cyan]{i+1}.[/cyan] [{s['modified']}] {s['preview']}")
                console.print()
            continue

        if user_input.lower() == "plugins":
            setup_wizard(first_run=False)
            # Reload plugins after changes
            active_plugins = load_active_plugins()
            plugin_tool_defs, plugin_handlers = get_all_tools(active_plugins)
            all_tools = CORE_TOOLS + plugin_tool_defs
            execute_tool = build_tool_executor(plugin_handlers)
            console.print(f"[dim]Active: {', '.join(p.name for p in active_plugins) or 'none'}[/dim]\n")
            continue

        if user_input.lower().startswith("enable "):
            name = user_input[7:].strip()
            console.print(enable_plugin(name) + "\n")
            continue

        if user_input.lower().startswith("disable "):
            name = user_input[8:].strip()
            console.print(disable_plugin(name) + "\n")
            active_plugins = load_active_plugins()
            plugin_tool_defs, plugin_handlers = get_all_tools(active_plugins)
            all_tools = CORE_TOOLS + plugin_tool_defs
            execute_tool = build_tool_executor(plugin_handlers)
            continue

        if user_input.lower() == "reload plugins":
            active_plugins = load_active_plugins()
            plugin_tool_defs, plugin_handlers = get_all_tools(active_plugins)
            all_tools = CORE_TOOLS + plugin_tool_defs
            execute_tool = build_tool_executor(plugin_handlers)
            console.print(f"[green]Reloaded.[/green] Active: {', '.join(p.name for p in active_plugins) or 'none'}\n")
            continue

        messages.append({"role": "user", "content": user_input})
        console.print()

        try:
            run_agent_loop(client, messages, session_id, all_tools, execute_tool)
        except anthropic.APIError as e:
            console.print(f"[red]API error:[/red] {e}\n")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}\n")


if __name__ == "__main__":
    main()
