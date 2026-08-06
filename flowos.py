#!/usr/bin/env python3
import os
import sys
import json
import platform
import anthropic
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

from tools import TOOL_DEFINITIONS, execute_tool
from session import load_session, save_session, list_sessions, new_session_id

console = Console()

HISTORY_FILE = Path.home() / ".flowos" / "history"
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

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

You have tools for: running shell commands, reading/writing files, checking system resources, listing processes, and installing packages.

Keep responses short and direct. You are the OS, not a chatbot."""


def print_banner():
    console.print(Panel(
        Text("FlowOS Desktop", style="bold cyan", justify="center") ,
        subtitle="[dim]type 'exit' to quit · 'sessions' to resume · 'clear' to reset[/dim]",
        border_style="cyan"
    ))
    console.print()


def print_tool_call(name: str, inputs: dict):
    label = {
        "run_command": f"[dim]$ {inputs.get('command', '')}[/dim]",
        "read_file": f"[dim]reading {inputs.get('path', '')}[/dim]",
        "write_file": f"[dim]writing {inputs.get('path', '')}[/dim]",
        "get_system_info": "[dim]checking system resources[/dim]",
        "list_processes": "[dim]listing processes[/dim]",
        "install_package": f"[dim]installing {inputs.get('package', '')} via {inputs.get('manager', 'auto')}[/dim]",
    }.get(name, f"[dim]{name}[/dim]")
    console.print(f"  [cyan]→[/cyan] {label}")


def run_agent_loop(client: anthropic.Anthropic, messages: list, session_id: str):
    while True:
        with Live(Spinner("dots", text="[cyan]thinking...[/cyan]"), console=console, refresh_per_second=10):
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages
            )

        # Collect text content and tool uses
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # Print any text response
        if text_parts:
            text = "\n".join(text_parts).strip()
            if text:
                console.print(Markdown(text))
                console.print()

        # If no tool calls, we're done
        if not tool_uses or response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            save_session(session_id, messages)
            break

        # Execute tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tool_use in tool_uses:
            print_tool_call(tool_use.name, tool_use.input)
            result = execute_tool(tool_use.name, tool_use.input)
            # Truncate very long outputs
            if len(result) > 3000:
                result = result[:3000] + "\n... (truncated)"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result
            })

        console.print()
        messages.append({"role": "user", "content": tool_results})
        save_session(session_id, messages)
        # Loop continues — model will process tool results


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.")
        console.print("Set it with: [cyan]export ANTHROPIC_API_KEY=your_key[/cyan]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print_banner()

    # Check for resume flag
    session_id = new_session_id()
    messages = []

    if len(sys.argv) > 1 and sys.argv[1] == "--resume":
        sessions = list_sessions()
        if sessions:
            console.print("[bold]Recent sessions:[/bold]")
            for i, s in enumerate(sessions[:5]):
                console.print(f"  [cyan]{i+1}.[/cyan] [{s['modified']}] {s['preview']}")
            console.print()
            choice = prompt("Resume session (number) or press Enter to start new: ").strip()
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

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.lower() == "clear":
            messages = []
            session_id = new_session_id()
            console.clear()
            print_banner()
            console.print("[dim]Session cleared.[/dim]\n")
            continue

        if user_input.lower() == "sessions":
            sessions = list_sessions()
            if not sessions:
                console.print("[dim]No previous sessions found.[/dim]\n")
            else:
                console.print("[bold]Recent sessions:[/bold]")
                for i, s in enumerate(sessions[:5]):
                    console.print(f"  [cyan]{i+1}.[/cyan] [{s['modified']}] {s['preview']}")
                console.print()
            continue

        messages.append({"role": "user", "content": user_input})
        console.print()

        try:
            run_agent_loop(client, messages, session_id)
        except anthropic.APIError as e:
            console.print(f"[red]API error:[/red] {e}\n")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}\n")


if __name__ == "__main__":
    main()
