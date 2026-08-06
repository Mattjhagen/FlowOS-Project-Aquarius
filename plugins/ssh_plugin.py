import subprocess
from .base import Plugin


def _ssh_run(host: str, command: str, port: int = 22) -> str:
    cmd = f"ssh -p {port} -o ConnectTimeout=10 -o StrictHostKeyChecking=no {host} '{command}'"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip() or r.stderr.strip()


class SSHPlugin(Plugin):
    name = "ssh"
    description = "Run commands on remote machines over SSH"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "ssh_run",
                "description": "Execute a command on a remote machine via SSH",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "description": "user@hostname or IP, e.g. matt@192.168.0.169"},
                        "command": {"type": "string", "description": "Command to run on the remote machine"},
                        "port": {"type": "integer", "description": "SSH port (default 22)"}
                    },
                    "required": ["host", "command"]
                }
            },
            {
                "name": "ssh_copy_file",
                "description": "Copy a file to or from a remote machine using scp",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source path (use user@host:path for remote)"},
                        "destination": {"type": "string", "description": "Destination path (use user@host:path for remote)"}
                    },
                    "required": ["source", "destination"]
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        def ssh_copy(source, destination):
            r = subprocess.run(
                f"scp -o StrictHostKeyChecking=no {source} {destination}",
                shell=True, capture_output=True, text=True, timeout=60
            )
            return r.stdout.strip() or r.stderr.strip() or "Done."

        return {
            "ssh_run": lambda host, command, port=22: _ssh_run(host, command, port),
            "ssh_copy_file": ssh_copy,
        }
