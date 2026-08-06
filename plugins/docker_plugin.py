import subprocess
from .base import Plugin


def _run(cmd: str) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip() or r.stderr.strip()


class DockerPlugin(Plugin):
    name = "docker"
    description = "Docker container and image management"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "docker_ps",
                "description": "List running (or all) Docker containers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "all": {"type": "boolean", "description": "Show all containers including stopped ones"}
                    }
                }
            },
            {
                "name": "docker_logs",
                "description": "Fetch logs from a container",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "container": {"type": "string", "description": "Container name or ID"},
                        "lines": {"type": "integer", "description": "Number of lines to tail (default 50)"}
                    },
                    "required": ["container"]
                }
            },
            {
                "name": "docker_start_stop",
                "description": "Start or stop a Docker container",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "container": {"type": "string", "description": "Container name or ID"},
                        "action": {"type": "string", "enum": ["start", "stop", "restart"]}
                    },
                    "required": ["container", "action"]
                }
            },
            {
                "name": "docker_images",
                "description": "List Docker images",
                "input_schema": {"type": "object", "properties": {}}
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "docker_ps": lambda all=False: _run(f"docker ps {'-a' if all else ''}"),
            "docker_logs": lambda container, lines=50: _run(f"docker logs --tail {lines} {container}"),
            "docker_start_stop": lambda container, action: _run(f"docker {action} {container}"),
            "docker_images": lambda: _run("docker images"),
        }
