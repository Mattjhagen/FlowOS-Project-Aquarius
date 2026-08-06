import json
import importlib
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from plugins.base import Plugin

console = Console()

CONFIG_PATH = Path.home() / ".flowos" / "plugins.json"

AVAILABLE_PLUGINS = {
    "git":       ("plugins.git_plugin",       "GitPlugin",       "Git repository management"),
    "docker":    ("plugins.docker_plugin",    "DockerPlugin",    "Docker container management"),
    "ssh":       ("plugins.ssh_plugin",       "SSHPlugin",       "Run commands on remote machines"),
    "notes":     ("plugins.notes_plugin",     "NotesPlugin",     "Persistent note-taking"),
    "weather":   ("plugins.weather_plugin",   "WeatherPlugin",   "Weather and forecast lookup"),
    "clipboard": ("plugins.clipboard_plugin", "ClipboardPlugin", "Read/write system clipboard"),
}


def load_config() -> list:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return []


def save_config(enabled: list):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(enabled, indent=2))


def load_plugin(name: str) -> Plugin | None:
    entry = AVAILABLE_PLUGINS.get(name)
    if not entry:
        return None
    module_path, class_name, _ = entry
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        cls.on_load()
        return cls
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not load plugin '{name}': {e}")
        return None


def load_active_plugins() -> list[Plugin]:
    enabled = load_config()
    plugins = []
    for name in enabled:
        plugin = load_plugin(name)
        if plugin:
            plugins.append(plugin)
    return plugins


def get_all_tools(plugins: list[Plugin]) -> tuple[list, dict]:
    tool_defs = []
    tool_handlers = {}
    for plugin in plugins:
        tool_defs.extend(plugin.tool_definitions())
        tool_handlers.update(plugin.tool_handlers())
    return tool_defs, tool_handlers


def show_plugin_table(enabled: list):
    table = Table(title="FlowOS Plugins", border_style="cyan")
    table.add_column("Status", width=8)
    table.add_column("Name", style="bold")
    table.add_column("Description")

    for name, (_, _, desc) in AVAILABLE_PLUGINS.items():
        status = "[green]ON[/green]" if name in enabled else "[dim]off[/dim]"
        table.add_row(status, name, desc)

    console.print(table)


def setup_wizard(first_run: bool = False):
    enabled = load_config()

    if first_run:
        console.print("\n[bold cyan]Welcome to FlowOS![/bold cyan]")
        console.print("Choose which plugins to enable:\n")
    else:
        console.print("\n[bold]Plugin Manager[/bold]")
        show_plugin_table(enabled)
        console.print()

    changed = False
    for name, (_, _, desc) in AVAILABLE_PLUGINS.items():
        current = name in enabled
        label = f"[bold]{name}[/bold] — {desc}"
        if first_run:
            result = Confirm.ask(f"  Enable {label}?", default=current)
        else:
            result = Confirm.ask(f"  {'Disable' if current else 'Enable'} {label}?", default=False)

        if first_run:
            if result and name not in enabled:
                enabled.append(name)
                changed = True
            elif not result and name in enabled:
                enabled.remove(name)
                changed = True
        else:
            if result:
                if current and name in enabled:
                    enabled.remove(name)
                elif not current and name not in enabled:
                    enabled.append(name)
                changed = True

    if changed:
        save_config(enabled)
        console.print(f"\n[green]Saved.[/green] Active plugins: {', '.join(enabled) or 'none'}\n")
    else:
        console.print("\n[dim]No changes.[/dim]\n")

    return enabled


def enable_plugin(name: str) -> str:
    if name not in AVAILABLE_PLUGINS:
        return f"Unknown plugin: '{name}'. Available: {', '.join(AVAILABLE_PLUGINS)}"
    enabled = load_config()
    if name in enabled:
        return f"Plugin '{name}' is already enabled."
    enabled.append(name)
    save_config(enabled)
    return f"Plugin '{name}' enabled. Restart FlowOS or type 'reload plugins' to activate."


def disable_plugin(name: str) -> str:
    enabled = load_config()
    if name not in enabled:
        return f"Plugin '{name}' is not enabled."
    enabled.remove(name)
    save_config(enabled)
    return f"Plugin '{name}' disabled."
