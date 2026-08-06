import subprocess
import platform
from .base import Plugin


def _read_clipboard() -> str:
    sys = platform.system()
    try:
        if sys == "Darwin":
            r = subprocess.run("pbpaste", capture_output=True, text=True)
            return r.stdout or "(clipboard is empty)"
        elif sys == "Linux":
            r = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True)
            return r.stdout or r.stderr or "(clipboard is empty)"
        return "Clipboard not supported on this platform"
    except Exception as e:
        return f"Error reading clipboard: {e}"


def _write_clipboard(text: str) -> str:
    sys = platform.system()
    try:
        if sys == "Darwin":
            subprocess.run("pbcopy", input=text, text=True, check=True)
            return f"Copied {len(text)} characters to clipboard."
        elif sys == "Linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
            return f"Copied {len(text)} characters to clipboard."
        return "Clipboard not supported on this platform"
    except Exception as e:
        return f"Error writing clipboard: {e}"


class ClipboardPlugin(Plugin):
    name = "clipboard"
    description = "Read from and write to the system clipboard"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "clipboard_read",
                "description": "Read the current contents of the system clipboard",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "clipboard_write",
                "description": "Write text to the system clipboard",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to copy to clipboard"}
                    },
                    "required": ["text"]
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "clipboard_read": lambda: _read_clipboard(),
            "clipboard_write": _write_clipboard,
        }
