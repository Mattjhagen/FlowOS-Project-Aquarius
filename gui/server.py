import sys
import os
import subprocess
import webbrowser
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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


def open_browser(port: int):
    import time
    time.sleep(0.8)
    webbrowser.open(f"http://localhost:{port}")


def run(port: int = 7070, open_tab: bool = True):
    if open_tab:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
