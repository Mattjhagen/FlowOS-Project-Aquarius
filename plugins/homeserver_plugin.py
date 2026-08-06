import subprocess
import json
from .base import Plugin

# Pre-configured for matt@192.168.0.169
# All commands run over SSH — no extra install needed on the client
# Server needs: openssh-server (sudo snap install openssh  OR  sudo apt install openssh-server)

DEFAULT_HOST = "matt@192.168.0.169"


def _ssh(command: str, host: str = DEFAULT_HOST, timeout: int = 15) -> str:
    r = subprocess.run(
        f"ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no {host} '{command}'",
        shell=True, capture_output=True, text=True, timeout=timeout
    )
    return r.stdout.strip() or r.stderr.strip() or "No output."


def _server_status(host: str = DEFAULT_HOST) -> str:
    cmd = (
        "echo '=== CPU ===' && top -bn1 | grep 'Cpu(s)' | head -1; "
        "echo '=== Memory ===' && free -h | grep Mem; "
        "echo '=== Disk ===' && df -h / | tail -1; "
        "echo '=== Uptime ===' && uptime"
    )
    return _ssh(cmd, host)


def _server_services(host: str = DEFAULT_HOST) -> str:
    return _ssh("systemctl list-units --type=service --state=running --no-pager --plain | head -25", host)


def _server_logs(service: str, lines: int = 50, host: str = DEFAULT_HOST) -> str:
    return _ssh(f"sudo journalctl -u {service} -n {lines} --no-pager", host)


def _server_restart_service(service: str, host: str = DEFAULT_HOST) -> str:
    return _ssh(f"sudo systemctl restart {service} && echo 'Restarted {service}'", host)


def _server_docker_ps(host: str = DEFAULT_HOST) -> str:
    return _ssh("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", host)


def _server_docker_logs(container: str, lines: int = 50, host: str = DEFAULT_HOST) -> str:
    return _ssh(f"docker logs --tail {lines} {container}", host)


def _server_deploy(repo_path: str, host: str = DEFAULT_HOST) -> str:
    cmd = (
        f"cd {repo_path} && "
        "git pull && "
        "echo '--- pulled latest ---' && "
        "docker compose up -d --build 2>&1 | tail -20 || "
        "echo 'No docker-compose.yml found — pulled only'"
    )
    return _ssh(cmd, host, timeout=120)


def _server_snap_list(host: str = DEFAULT_HOST) -> str:
    return _ssh("snap list", host)


def _server_snap_install(package: str, host: str = DEFAULT_HOST) -> str:
    return _ssh(f"sudo snap install {package}", host, timeout=120)


def _server_run(command: str, host: str = DEFAULT_HOST) -> str:
    return _ssh(command, host)


class HomeServerPlugin(Plugin):
    name = "homeserver"
    description = f"Manage your home server at {DEFAULT_HOST} — status, services, docker, deploy, snaps"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "server_status",
                "description": f"Get CPU, memory, disk, and uptime of the home server ({DEFAULT_HOST})",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": f"SSH target (default: {DEFAULT_HOST})"}
                    }
                }
            },
            {
                "name": "server_services",
                "description": "List running systemd services on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"}
                    }
                }
            },
            {
                "name": "server_logs",
                "description": "Fetch journald logs for a service on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "systemd service name"},
                        "lines": {"type": "integer", "description": "Number of log lines (default 50)"},
                        "host": {"type": "string"}
                    },
                    "required": ["service"]
                }
            },
            {
                "name": "server_restart_service",
                "description": "Restart a systemd service on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "systemd service name"},
                        "host": {"type": "string"}
                    },
                    "required": ["service"]
                }
            },
            {
                "name": "server_docker_ps",
                "description": "List running Docker containers on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"}
                    }
                }
            },
            {
                "name": "server_docker_logs",
                "description": "Fetch logs from a Docker container on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "container": {"type": "string", "description": "Container name or ID"},
                        "lines": {"type": "integer", "description": "Lines to tail (default 50)"},
                        "host": {"type": "string"}
                    },
                    "required": ["container"]
                }
            },
            {
                "name": "server_deploy",
                "description": "Git pull and docker compose up a project on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Absolute path to the repo on the server"},
                        "host": {"type": "string"}
                    },
                    "required": ["repo_path"]
                }
            },
            {
                "name": "server_snap_list",
                "description": "List installed snaps on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"}
                    }
                }
            },
            {
                "name": "server_snap_install",
                "description": "Install a snap package on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "package": {"type": "string", "description": "Snap package name"},
                        "host": {"type": "string"}
                    },
                    "required": ["package"]
                }
            },
            {
                "name": "server_run",
                "description": "Run an arbitrary shell command on the home server",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to run"},
                        "host": {"type": "string"}
                    },
                    "required": ["command"]
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "server_status": lambda host=DEFAULT_HOST: _server_status(host),
            "server_services": lambda host=DEFAULT_HOST: _server_services(host),
            "server_logs": lambda service, lines=50, host=DEFAULT_HOST: _server_logs(service, lines, host),
            "server_restart_service": lambda service, host=DEFAULT_HOST: _server_restart_service(service, host),
            "server_docker_ps": lambda host=DEFAULT_HOST: _server_docker_ps(host),
            "server_docker_logs": lambda container, lines=50, host=DEFAULT_HOST: _server_docker_logs(container, lines, host),
            "server_deploy": lambda repo_path, host=DEFAULT_HOST: _server_deploy(repo_path, host),
            "server_snap_list": lambda host=DEFAULT_HOST: _server_snap_list(host),
            "server_snap_install": lambda package, host=DEFAULT_HOST: _server_snap_install(package, host),
            "server_run": lambda command, host=DEFAULT_HOST: _server_run(command, host),
        }
