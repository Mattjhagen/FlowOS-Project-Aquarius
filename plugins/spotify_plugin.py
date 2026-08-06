import subprocess
import shutil
import platform
from .base import Plugin

# Linux: sudo snap install spotify
# macOS: brew install --cask spotify  (AppleScript control)
# DBus control on Linux: works when Spotify snap is running


def _dbus(cmd: str) -> str:
    return subprocess.run(
        f"dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify "
        f"/org/mpris/MediaPlayer2 {cmd}",
        shell=True, capture_output=True, text=True
    ).stdout.strip() or "Done."


def _applescript(script: str) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.stdout.strip() or r.stderr.strip() or "Done."


def _is_mac() -> bool:
    return platform.system() == "Darwin"


def _play_pause() -> str:
    if _is_mac():
        return _applescript('tell application "Spotify" to playpause')
    return _dbus("org.mpris.MediaPlayer2.Player.PlayPause")


def _next_track() -> str:
    if _is_mac():
        return _applescript('tell application "Spotify" to next track')
    return _dbus("org.mpris.MediaPlayer2.Player.Next")


def _prev_track() -> str:
    if _is_mac():
        return _applescript('tell application "Spotify" to previous track')
    return _dbus("org.mpris.MediaPlayer2.Player.Previous")


def _current_track() -> str:
    if _is_mac():
        script = '''
        tell application "Spotify"
            set t to name of current track
            set a to artist of current track
            set al to album of current track
            return a & " — " & t & " (" & al & ")"
        end tell'''
        return _applescript(script)
    # DBus: read metadata
    r = subprocess.run(
        "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify "
        "/org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Get "
        "string:'org.mpris.MediaPlayer2.Player' string:'Metadata'",
        shell=True, capture_output=True, text=True
    )
    out = r.stdout
    title = _parse_dbus_string(out, "xesam:title")
    artist = _parse_dbus_string(out, "xesam:artist")
    album = _parse_dbus_string(out, "xesam:album")
    if title:
        return f"{artist} — {title} ({album})"
    return "Could not read track info. Is Spotify running?"


def _parse_dbus_string(output: str, key: str) -> str:
    lines = output.split("\n")
    for i, line in enumerate(lines):
        if key in line and i + 1 < len(lines):
            val = lines[i + 1].strip()
            if '"' in val:
                return val.split('"')[1]
    return ""


def _set_volume(level: int) -> str:
    level = max(0, min(100, level))
    if _is_mac():
        return _applescript(f'tell application "Spotify" to set sound volume to {level}')
    return _dbus(f"org.mpris.MediaPlayer2.Player.Volume double:{level/100}")


def _open_spotify() -> str:
    if _is_mac():
        subprocess.Popen(["open", "-a", "Spotify"])
        return "Opening Spotify..."
    elif shutil.which("spotify"):
        subprocess.Popen(["spotify"])
        return "Opening Spotify..."
    else:
        return "Spotify not found. Install it: sudo snap install spotify"


def _search_and_play(query: str) -> str:
    encoded = query.replace(" ", "%20")
    uri = f"spotify:search:{encoded}"
    if _is_mac():
        subprocess.Popen(["open", uri])
        return f"Searching Spotify for: {query}"
    elif shutil.which("spotify"):
        subprocess.Popen(["spotify", "--uri", uri])
        return f"Searching Spotify for: {query}"
    return "Spotify not found. Install it: sudo snap install spotify"


class SpotifyPlugin(Plugin):
    name = "spotify"
    description = "Control Spotify — play/pause, skip, volume, current track"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "spotify_play_pause",
                "description": "Toggle play/pause in Spotify",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "spotify_next",
                "description": "Skip to the next track in Spotify",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "spotify_prev",
                "description": "Go back to the previous track in Spotify",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "spotify_current",
                "description": "Get the currently playing track, artist, and album",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "spotify_volume",
                "description": "Set Spotify volume (0-100)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer", "description": "Volume level 0-100"}
                    },
                    "required": ["level"]
                }
            },
            {
                "name": "spotify_open",
                "description": "Open the Spotify app",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "spotify_search",
                "description": "Search for a song, artist, or album in Spotify",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for"}
                    },
                    "required": ["query"]
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "spotify_play_pause": lambda: _play_pause(),
            "spotify_next": lambda: _next_track(),
            "spotify_prev": lambda: _prev_track(),
            "spotify_current": lambda: _current_track(),
            "spotify_volume": lambda level: _set_volume(level),
            "spotify_open": lambda: _open_spotify(),
            "spotify_search": lambda query: _search_and_play(query),
        }
