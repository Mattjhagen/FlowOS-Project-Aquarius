import subprocess
from pathlib import Path
from .base import Plugin


def _run(cmd: str, cwd: str = None) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30)
    return r.stdout.strip() or r.stderr.strip()


class GitPlugin(Plugin):
    name = "git"
    description = "Git repository management — status, commit, push, branch, log, diff"

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "git_status",
                "description": "Show the working tree status of a git repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the git repo (defaults to current dir)"}
                    }
                }
            },
            {
                "name": "git_commit",
                "description": "Stage all changes and create a git commit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Commit message"},
                        "path": {"type": "string", "description": "Path to the git repo"}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "git_push",
                "description": "Push commits to the remote repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the git repo"},
                        "branch": {"type": "string", "description": "Branch name (defaults to current)"}
                    }
                }
            },
            {
                "name": "git_log",
                "description": "Show recent commit history",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the git repo"},
                        "count": {"type": "integer", "description": "Number of commits to show (default 10)"}
                    }
                }
            },
            {
                "name": "git_diff",
                "description": "Show unstaged or staged changes in a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the git repo"},
                        "staged": {"type": "boolean", "description": "Show staged changes instead of unstaged"}
                    }
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "git_status": lambda path=None: _run("git status", cwd=path or "."),
            "git_commit": lambda message, path=None: _run(f'git add -A && git commit -m "{message}"', cwd=path or "."),
            "git_push": lambda path=None, branch=None: _run(f"git push origin {branch or 'HEAD'}", cwd=path or "."),
            "git_log": lambda path=None, count=10: _run(f"git log --oneline -n {count}", cwd=path or "."),
            "git_diff": lambda path=None, staged=False: _run(f"git diff {'--staged' if staged else ''}", cwd=path or "."),
        }
