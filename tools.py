import subprocess
import os
import psutil
import shutil
from pathlib import Path

TOOL_DEFINITIONS = [
    {
        "name": "run_command",
        "description": "Execute a shell command on the system and return its output. Use for any system operation, file listing, git commands, running scripts, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory to run the command in"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "get_system_info",
        "description": "Get current system resource usage: CPU, memory, disk, and top processes",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_processes",
        "description": "List running processes, optionally filtered by name",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Optional process name to filter by"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["cpu", "memory", "name"],
                    "description": "Sort processes by this field"
                }
            }
        }
    },
    {
        "name": "install_package",
        "description": "Install a package using the appropriate package manager (brew on macOS, apt on Linux, pip for Python packages)",
        "input_schema": {
            "type": "object",
            "properties": {
                "package": {
                    "type": "string",
                    "description": "Package name to install"
                },
                "manager": {
                    "type": "string",
                    "enum": ["auto", "brew", "snap", "apt", "pip", "npm", "cargo"],
                    "description": "Package manager to use. 'auto' detects the best one."
                }
            },
            "required": ["package"]
        }
    }
]


def run_command(command: str, working_dir: str = None) -> dict:
    try:
        cwd = Path(working_dir).expanduser() if working_dir else Path.home()
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        return {
            "success": result.returncode == 0,
            "stdout": output,
            "stderr": error,
            "returncode": result.returncode,
            "output": output if output else error
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"success": False, "output": str(e)}


def read_file(path: str) -> dict:
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return {"success": False, "output": f"File not found: {path}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"success": True, "output": content, "path": str(p), "size": p.stat().st_size}
    except Exception as e:
        return {"success": False, "output": str(e)}


def write_file(path: str, content: str) -> dict:
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "output": f"Written {len(content)} bytes to {p}"}
    except Exception as e:
        return {"success": False, "output": str(e)}


def get_system_info() -> dict:
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    top_procs = sorted(
        [p.info for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"])
         if p.info["name"]],
        key=lambda x: x.get("memory_percent") or 0,
        reverse=True
    )[:5]

    return {
        "success": True,
        "output": {
            "cpu_percent": cpu,
            "memory": {
                "total_gb": round(mem.total / 1e9, 1),
                "used_gb": round(mem.used / 1e9, 1),
                "percent": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / 1e9, 1),
                "used_gb": round(disk.used / 1e9, 1),
                "percent": disk.percent
            },
            "top_processes": top_procs
        }
    }


def list_processes(filter: str = None, sort_by: str = "memory") -> dict:
    sort_key = {"cpu": "cpu_percent", "memory": "memory_percent", "name": "name"}.get(sort_by, "memory_percent")

    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            if filter and filter.lower() not in (info["name"] or "").lower():
                continue
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if sort_by in ("cpu", "memory"):
        procs.sort(key=lambda x: x.get(sort_key) or 0, reverse=True)
    else:
        procs.sort(key=lambda x: (x.get("name") or "").lower())

    return {"success": True, "output": procs[:20]}


def install_package(package: str, manager: str = "auto") -> dict:
    import platform

    if manager == "auto":
        if platform.system() == "Darwin":
            manager = "brew"
        elif shutil.which("snap"):
            manager = "snap"
        elif shutil.which("apt"):
            manager = "apt"
        else:
            manager = "pip"

    commands = {
        "brew": f"brew install {package}",
        "snap": f"sudo snap install {package}",
        "apt": f"sudo apt-get install -y {package}",
        "pip": f"pip3 install {package}",
        "npm": f"npm install -g {package}",
        "cargo": f"cargo install {package}"
    }

    cmd = commands.get(manager)
    if not cmd:
        return {"success": False, "output": f"Unknown package manager: {manager}"}

    return run_command(cmd)


TOOL_HANDLERS = {
    "run_command": run_command,
    "read_file": read_file,
    "write_file": write_file,
    "get_system_info": get_system_info,
    "list_processes": list_processes,
    "install_package": install_package,
}


def execute_tool(name: str, inputs: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return f"Unknown tool: {name}"
    result = handler(**inputs)
    if isinstance(result.get("output"), dict):
        import json
        return json.dumps(result["output"], indent=2)
    return str(result.get("output", "Done."))
