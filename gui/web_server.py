import os, sys, pathlib, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
app = FastAPI()
GUI_DIR = pathlib.Path(__file__).parent

@app.get("/", response_class=HTMLResponse)
async def index():
    p = GUI_DIR / "web.html"
    return HTMLResponse(p.read_text() if p.exists() else "<h1>web.html missing</h1>")

@app.get("/api/system")
async def system_stats():
    try:
        import psutil
        try:
            cpu = psutil.cpu_percent(interval=0.1)
        except:
            cpu = 0.0
        try:
            m = psutil.virtual_memory()
            mu, mt, mp = round(m.used/1e9,1), round(m.total/1e9,1), m.percent
        except:
            mu, mt, mp = 0, 0, 0
        try:
            d = psutil.disk_usage("/data")
            du, dt, dp = round(d.used/1e9,1), round(d.total/1e9,1), d.percent
        except:
            du, dt, dp = 0, 0, 0
        return {"cpu": cpu, "mem_used": mu, "mem_total": mt, "mem_pct": mp,
                "disk_used": du, "disk_total": dt, "disk_pct": dp}
    except Exception as e:
        return {"error": str(e)}

def _cfg():
    p = pathlib.Path.home() / ".flowos" / "plugins.json"
    if p.exists():
        try: return json.load(open(p))
        except: pass
    return []

def _save_cfg(data):
    p = pathlib.Path.home() / ".flowos" / "plugins.json"
    p.parent.mkdir(exist_ok=True)
    json.dump(data, open(p, "w"))

@app.get("/api/plugins")
async def list_plugins():
    try:
        from plugin_manager import AVAILABLE_PLUGINS
        enabled = set(_cfg())
        return [{"name": n, "description": desc, "enabled": n in enabled}
                for n, (_, _, desc) in AVAILABLE_PLUGINS.items()]
    except Exception as e:
        return [{"error": str(e)}]

@app.post("/api/plugins/{name}/enable")
async def enable_plugin(name: str):
    try:
        pl = _cfg()
        if name not in pl: pl.append(name)
        _save_cfg(pl)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/plugins/{name}/disable")
async def disable_plugin(name: str):
    try:
        _save_cfg([x for x in _cfg() if x != name])
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

active = []

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    active.append(ws)
    try:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            kf = pathlib.Path.home() / ".flowos" / "api_key"
            key = kf.read_text().strip() if kf.exists() else None
        if not key:
            await ws.send_json({"type": "error", "text": "No API key. Run: echo sk-ant-... > ~/.flowos/api_key"})
            return

        import anthropic
        from tools import TOOL_DEFINITIONS, execute_tool

        client = anthropic.Anthropic(api_key=key)
        messages = []

        while True:
            data = await ws.receive_json()
            if data.get("type") != "message": continue
            text = data.get("text", "").strip()
            if not text: continue
            messages.append({"role": "user", "content": text})

            while True:
                resp = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system="You are FlowOS, an AI OS. You have real system access. Be direct and concise.",
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )
                tool_results = []
                for block in resp.content:
                    if block.type == "text" and block.text:
                        await ws.send_json({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        await ws.send_json({"type": "tool_call", "name": block.name, "input": block.input})
                        result = str(execute_tool(block.name, block.input))[:3000]
                        await ws.send_json({"type": "tool_result", "name": block.name, "result": result})
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

                if resp.stop_reason == "end_turn" or not tool_results:
                    messages.append({"role": "assistant", "content": resp.content})
                    await ws.send_json({"type": "done"})
                    break
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user", "content": tool_results})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try: await ws.send_json({"type": "error", "text": str(e)})
        except: pass
    finally:
        if ws in active: active.remove(ws)

if __name__ == "__main__":
    port = int(os.environ.get("FLOWOS_PORT", 7071))
    print(f"\n  FlowOS -> http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
