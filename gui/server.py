import sys
import os
import subprocess
import webbrowser
import threading
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from plugin_manager import (
    AVAILABLE_PLUGINS, load_config, save_config,
    load_active_plugins, get_all_tools
)
import psutil

app = FastAPI(title="FlowOS Store")

GUI_DIR = Path(__file__).parent

PLUGIN_META = {
    "git":        {"icon": "⎇",  "category": "Developer",    "snap": None,        "color": "#7C3AED"},
    "docker":     {"icon": "◫",  "category": "Developer",    "snap": "docker",    "color": "#7C3AED"},
    "ssh":        {"icon": "⚡",  "category": "Developer",    "snap": None,        "color": "#7C3AED"},
    "notes":      {"icon": "◧",  "category": "Productivity", "snap": None,        "color": "#0891B2"},
    "weather":    {"icon": "◎",  "category": "Productivity", "snap": None,        "color": "#0891B2"},
    "clipboard":  {"icon": "⊡",  "category": "System",       "snap": None,        "color": "#EA580C"},
    "browser":    {"icon": "◉",  "category": "Media",        "snap": "chromium",  "color": "#DB2777"},
    "spotify":    {"icon": "◈",  "category": "Media",        "snap": "spotify",   "color": "#DB2777"},
    "homeserver": {"icon": "⊞",  "category": "System",       "snap": None,        "color": "#EA580C"},
}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = GUI_DIR / "store.html"
    return HTMLResponse(html_path.read_text())


@app.get("/api/plugins")
async def list_plugins():
    enabled = load_config()
    plugins = []
    for name, (module, cls, desc) in AVAILABLE_PLUGINS.items():
        meta = PLUGIN_META.get(name, {})
        plugins.append({
            "name": name,
            "description": desc,
            "enabled": name in enabled,
            "icon": meta.get("icon", "◆"),
            "category": meta.get("category", "Other"),
            "snap": meta.get("snap"),
            "color": meta.get("color", "#00B4D8"),
        })
    return plugins


@app.post("/api/plugins/{name}/enable")
async def enable_plugin(name: str):
    if name not in AVAILABLE_PLUGINS:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    enabled = load_config()
    if name not in enabled:
        enabled.append(name)
        save_config(enabled)
    return {"name": name, "enabled": True}


@app.post("/api/plugins/{name}/disable")
async def disable_plugin(name: str):
    enabled = load_config()
    if name in enabled:
        enabled.remove(name)
        save_config(enabled)
    return {"name": name, "enabled": False}


@app.get("/api/system")
async def system_info():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    enabled = load_config()
    return {
        "cpu": psutil.cpu_percent(interval=0.3),
        "memory_percent": mem.percent,
        "disk_percent": disk.percent,
        "plugins_enabled": len(enabled),
        "plugins_total": len(AVAILABLE_PLUGINS),
    }


@app.post("/api/launch")
async def launch_flowos():
    project_dir = str(Path(__file__).parent.parent)
    import platform
    sys_name = platform.system()
    try:
        if sys_name == "Darwin":
            subprocess.Popen([
                "osascript", "-e",
                f'tell application "Terminal" to do script "cd {project_dir} && python3 flowos.py"'
            ])
        else:
            for term in ["gnome-terminal", "xterm", "konsole", "xfce4-terminal"]:
                if subprocess.run(["which", term], capture_output=True).returncode == 0:
                    subprocess.Popen([term, "--", "bash", "-c",
                        f"cd {project_dir} && python3 flowos.py; exec bash"])
                    break
        return {"launched": True}
    except Exception as e:
        return {"launched": False, "error": str(e)}


_SNAP_API = "https://api.snapcraft.io/v2/snaps/find"
_SNAP_HEADERS = {"Snap-Device-Series": "16", "User-Agent": "FlowOS/0.2"}


@app.get("/api/snaps/search")
async def snap_search(q: str = Query(default=""), category: str = Query(default="")):
    import platform, sys
    # Try snapcraft API with multiple fallback approaches
    params = {"q": q or category or "featured", "fields": "title,summary,media,download,version"}
    headers_v2 = {"Snap-Device-Series": "16", "User-Agent": "FlowOS/0.2", "X-Ubuntu-Series": "16"}
    urls = [
        "https://api.snapcraft.io/v2/snaps/find",
        "https://search.apps.ubuntu.com/api/v1/search",
    ]
    for url in urls:
        try:
            from urllib.request import Request, urlopen
            from urllib.parse import urlencode
            req = Request(url + "?" + urlencode(params), headers=headers_v2)
            with urlopen(req, timeout=8) as resp:
                import json
                data = json.loads(resp.read())
                results = data.get("results", data.get("_embedded", {}).get("clickindex:package", []))
                snaps = []
                for r in results[:20]:
                    s = r.get("snap", r)
                    snaps.append({
                        "name": s.get("name", r.get("package_name", "")),
                        "title": s.get("title", r.get("title", "")),
                        "summary": s.get("summary", r.get("summary", "")),
                        "icon": (s.get("media") or [{}])[0].get("url", "") if isinstance(s.get("media"), list) else r.get("icon_url", ""),
                        "version": s.get("version", r.get("version", "")),
                    })
                if snaps:
                    return snaps
        except Exception:
            continue
    # Fallback: curated list
    curated = [
        {"name": "chromium",  "title": "Chromium",      "summary": "Open source web browser",          "icon": "", "version": "latest"},
        {"name": "spotify",   "title": "Spotify",       "summary": "Music streaming service",          "icon": "", "version": "latest"},
        {"name": "docker",    "title": "Docker",        "summary": "Container platform",               "icon": "", "version": "latest"},
        {"name": "code",      "title": "VS Code",       "summary": "Code editor by Microsoft",         "icon": "", "version": "latest"},
        {"name": "vlc",       "title": "VLC",           "summary": "Media player",                     "icon": "", "version": "latest"},
        {"name": "ffmpeg",    "title": "FFmpeg",        "summary": "Audio/video converter",            "icon": "", "version": "latest"},
        {"name": "htop",      "title": "htop",          "summary": "Interactive process viewer",       "icon": "", "version": "latest"},
        {"name": "gimp",      "title": "GIMP",          "summary": "GNU Image Manipulation Program",   "icon": "", "version": "latest"},
        {"name": "obs-studio","title": "OBS Studio",    "summary": "Streaming and recording software", "icon": "", "version": "latest"},
        {"name": "telegram-desktop","title": "Telegram","summary": "Messaging app",                    "icon": "", "version": "latest"},
    ]
    if q:
        curated = [s for s in curated if q.lower() in s["name"] or q.lower() in s["title"].lower() or q.lower() in s["summary"].lower()]
    return curated


@app.post("/api/snaps/install")
async def snap_install(body: dict):
    import platform, shutil
    name = body.get("name", "").strip()
    if not name or not all(c.isalnum() or c in "-+" for c in name):
        raise HTTPException(status_code=400, detail="Invalid snap name")

    if platform.system() == "Darwin":
        return {"ok": False, "cmd": f"brew install {name}"}

    if not shutil.which("snap"):
        return {"ok": False, "cmd": f"sudo apt install snapd && sudo snap install {name}"}

    try:
        result = subprocess.run(
            ["sudo", "snap", "install", name],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return {"ok": True, "cmd": None}
        return {"ok": False, "cmd": f"sudo snap install {name}", "error": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "cmd": f"sudo snap install {name}"}
    except Exception as e:
        return {"ok": False, "cmd": f"sudo snap install {name}"}


def open_browser(port: int):
    import time
    time.sleep(0.8)
    webbrowser.open(f"http://localhost:{port}")


def run(port: int = 7070, open_tab: bool = True):
    if open_tab:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
