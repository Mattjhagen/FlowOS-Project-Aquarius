import json
from pathlib import Path
from datetime import datetime
from .base import Plugin

NOTES_DIR = Path.home() / ".flowos" / "notes"


def _ensure():
    NOTES_DIR.mkdir(parents=True, exist_ok=True)


def _save_note(title: str, content: str) -> str:
    _ensure()
    slug = title.lower().replace(" ", "_")[:40]
    path = NOTES_DIR / f"{slug}.md"
    path.write_text(f"# {title}\n_{datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n{content}")
    return f"Note saved: {path}"


def _get_note(title: str) -> str:
    _ensure()
    slug = title.lower().replace(" ", "_")[:40]
    path = NOTES_DIR / f"{slug}.md"
    if path.exists():
        return path.read_text()
    # fuzzy search
    matches = [f for f in NOTES_DIR.glob("*.md") if title.lower() in f.stem]
    if matches:
        return matches[0].read_text()
    return f"No note found matching '{title}'"


def _list_notes() -> str:
    _ensure()
    notes = list(NOTES_DIR.glob("*.md"))
    if not notes:
        return "No notes yet."
    return "\n".join(
        f"- {f.stem.replace('_', ' ')} ({datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d')})"
        for f in sorted(notes, key=lambda x: x.stat().st_mtime, reverse=True)
    )


def _delete_note(title: str) -> str:
    _ensure()
    slug = title.lower().replace(" ", "_")[:40]
    path = NOTES_DIR / f"{slug}.md"
    if path.exists():
        path.unlink()
        return f"Deleted: {title}"
    return f"Note not found: {title}"


class NotesPlugin(Plugin):
    name = "notes"
    description = "Persistent note-taking — save, retrieve, and list notes"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "note_save",
                "description": "Save a new note or overwrite an existing one",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Note title"},
                        "content": {"type": "string", "description": "Note content (markdown supported)"}
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "note_get",
                "description": "Retrieve a note by title",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Note title to retrieve"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "note_list",
                "description": "List all saved notes",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "note_delete",
                "description": "Delete a note by title",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"}
                    },
                    "required": ["title"]
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "note_save": _save_note,
            "note_get": _get_note,
            "note_list": lambda: _list_notes(),
            "note_delete": _delete_note,
        }
