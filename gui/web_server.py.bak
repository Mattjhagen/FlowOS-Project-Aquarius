import asyncio, json, os, sys, pathlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
app = FastAPI(title="FlowOS Web GUI")
GUI_DIR = pathlib.Path(__file__).parent

@app.get("/", response_class=HTMLResponse)
async def index():
    p = GUI_DIR / "web.html"
    return HTMLResponse(p.read_text() if p.exists() else "<h1>web.html missing</h1>")

@app.get("/api/system")
async def system_stats():
    try:
        import psutil
        m = psutil.virtual_memory(); d = psutil.disk_usage("/")
        return {"cpu": psutil.cpu_percent(interval=0.1),
                "mem_used": round(m.used/1e9,1), "mem_total": round(m.total/1e9,1), "mem_pct": m.percent,
                "disk_used": round(d.used/1e9,1), "disk_total": round(d.total/1e9,1), "disk_pct": d.percent}
    except Exception as e: return {"error": str(e)}

@app.get("/api/plugins")
async def list_plugins():
    try:
        from plugin_manager import AVAILABLE_PLUGINS, load_enabled_plugins
        enabled = {p.name for p in load_enabled_plugins()}
        return [{"name": n, "description": desc, "enabled": n in enabled}
                for n, (_, _, desc) in AVAILABLE_PLUGINS.items()]
    except Exception as e: return [{"error": str(e)}]

@app.post("/api/plugins/{name}/enable")
async def enable_plugin(name: str):
    try:
        from plugin_manager import enable_plugin as _e; _e(name); return {"ok": True}
    except Exception as e: return {"ok": False, "error": str(e)}

@app.post("/api/plugins/{name}/disable")
async def disable_plugin(name: str):
    try:
        from plugin_manager import disable_plugin as _d; _d(name); return {"ok": True}
    except Exception as e: return {"ok": False, "error": str(e)}

active = []

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept(); active.append(ws)
    try:
        import anthropic
        from tools import get_tools, execute_tool
        from plugin_manager import load_enabled_plugins
        key = os.environ.get("ANTHROPIC_API_KEY") or _key_file()
        if not key:
            await ws.send_json({"type":"error","text":"No API key. Set ANTHROPIC_API_KEY or ~/.flowos/api_key"}); return
        client = anthropic.Anthropic(api_key=key)
        plugins = load_enabled_plugins()
        tools = get_tools(plugins)
        messages = []
        while True:
            data = await ws.receive_json()
            if data.get("type") != "message": continue
            text = data.get("text","").strip()
            if not text: continue
            messages.append({"role":"user","content":text})
            while True:
                resp = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=4096,
                    system="You are FlowOS, an AI that IS the operating system. You have real access to the user's machine. Be direct and action-oriented.",
                    tools=tools, messages=messages)
                tool_results = []
                for block in resp.content:
                    if block.type == "text" and block.text:
                        await ws.send_json({"type":"text","text":block.text})
                    elif block.type == "tool_use":
                        await ws.send_json({"type":"tool_call","name":block.name,"input":block.input})
                        result = str(execute_tool(block.name, block.input, plugins))[:3000]
                        await ws.send_json({"type":"tool_result","name":block.name,"result":result})
                        tool_results.append({"type":"tool_result","tool_use_id":block.id,"content":result})
                if resp.stop_reason == "end_turn" or not tool_results:
                    messages.append({"role":"assistant","content":resp.content})
                    await ws.send_json({"type":"done"}); break
                messages.append({"role":"assistant","content":resp.content})
                messages.append({"role":"user","content":tool_results})
    except WebSocketDisconnect: pass
    except Exception as e:
        try: await ws.send_json({"type":"error","text":str(e)})
        except: pass
    finally:
        if ws in active: active.remove(ws)

def _key_file():
    p = pathlib.Path.home()/".flowos"/"api_key"
    return p.read_text().strip() if p.exists() else None

def main():
    port = int(os.environ.get("FLOWOS_PORT", 7071))
    print(f"\n  FlowOS Web GUI -> http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__": main()