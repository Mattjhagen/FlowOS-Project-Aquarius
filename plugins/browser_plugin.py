import subprocess
import shutil
import platform
import urllib.parse
import urllib.request
import json
from pathlib import Path
from .base import Plugin

# Snap: sudo snap install chromium
# macOS: brew install --cask chromium  (or use system Chrome/Safari)


def _open_url(url: str) -> str:
    sys = platform.system()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        if sys == "Darwin":
            subprocess.Popen(["open", url])
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", url])
        elif shutil.which("chromium"):
            subprocess.Popen(["chromium", url])
        elif shutil.which("chromium-browser"):
            subprocess.Popen(["chromium-browser", url])
        else:
            return "No browser found. Install chromium: sudo snap install chromium"
        return f"Opened {url}"
    except Exception as e:
        return f"Error opening URL: {e}"


def _web_search(query: str, engine: str = "google") -> str:
    engines = {
        "google": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
        "ddg": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}",
        "bing": f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
    }
    url = engines.get(engine, engines["google"])
    return _open_url(url)


def _screenshot(url: str = None, output: str = None) -> str:
    browser = shutil.which("chromium") or shutil.which("chromium-browser")
    if not browser:
        return "Chromium not found. Install it: sudo snap install chromium"

    out = output or str(Path.home() / "flowos_screenshot.png")
    target = url or "about:blank"
    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    try:
        result = subprocess.run(
            [browser, "--headless", "--disable-gpu", f"--screenshot={out}", target],
            capture_output=True, text=True, timeout=20
        )
        if Path(out).exists():
            return f"Screenshot saved to {out}"
        return result.stderr or "Screenshot failed — chromium returned no output"
    except subprocess.TimeoutExpired:
        return "Screenshot timed out"
    except Exception as e:
        return f"Error: {e}"


def _fetch_page_text(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FlowOS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8", errors="replace")
        # Strip HTML tags crudely for readability
        import re
        text = re.sub(r"<style[^>]*>.*?</style>", "", raw, flags=re.DOTALL)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s{2,}", "\n", text).strip()
        return text[:4000] + ("..." if len(text) > 4000 else "")
    except Exception as e:
        return f"Could not fetch page: {e}"


class BrowserPlugin(Plugin):
    name = "browser"
    description = "Open URLs, search the web, take screenshots, fetch page content"
    requires = []  # chromium via snap on Linux

    @classmethod
    def tool_definitions(cls):
        return [
            {
                "name": "browser_open",
                "description": "Open a URL in the default browser",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to open (http/https or bare domain)"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_search",
                "description": "Open a web search in the default browser",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "engine": {
                            "type": "string",
                            "enum": ["google", "ddg", "bing"],
                            "description": "Search engine (default: google)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "browser_screenshot",
                "description": "Take a headless screenshot of a URL using Chromium (must be installed via snap)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to screenshot"},
                        "output": {"type": "string", "description": "Output file path (default: ~/flowos_screenshot.png)"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_fetch",
                "description": "Fetch and return the readable text content of a web page",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"}
                    },
                    "required": ["url"]
                }
            }
        ]

    @classmethod
    def tool_handlers(cls):
        return {
            "browser_open": lambda url: _open_url(url),
            "browser_search": lambda query, engine="google": _web_search(query, engine),
            "browser_screenshot": lambda url, output=None: _screenshot(url, output),
            "browser_fetch": lambda url: _fetch_page_text(url),
        }
