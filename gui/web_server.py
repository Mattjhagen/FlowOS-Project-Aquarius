import os, sys, pathlib, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
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


@app.get("/tty", response_class=HTMLResponse)
async def tty_page():
    p = GUI_DIR / "tty.html"
    return HTMLResponse(p.read_text() if p.exists() else "<h1>tty.html missing</h1>")

@app.get("/api/tty")
async def tty_stats():
    import os, time, socket, platform, subprocess
    out = {}
    try:
        import psutil
        try: out["cpu"] = psutil.cpu_percent(interval=0.1)
        except: out["cpu"] = 0
        try: out["cpu_count"] = psutil.cpu_count(logical=True)
        except: pass
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        out["cpu_model"] = line.split(":")[1].strip(); break
        except: pass
        try:
            la = os.getloadavg()
            out["load_avg"] = f"{la[0]:.2f} {la[1]:.2f} {la[2]:.2f}"
        except: pass
        try:
            m = psutil.virtual_memory()
            out["mem_pct"] = round(m.percent,1); out["mem_used"] = round(m.used/1e9,1)
            out["mem_total"] = round(m.total/1e9,1); out["mem_free"] = round(m.available/1e9,1)
        except: pass
        try:
            sw = psutil.swap_memory()
            out["swap_pct"] = round(sw.percent,1); out["swap_used"] = round(sw.used/1e9,1); out["swap_total"] = round(sw.total/1e9,1)
        except: pass
        try:
            temps = psutil.sensors_temperatures()
            for k in ["coretemp","cpu_thermal","k10temp","acpitz"]:
                if k in temps and temps[k]:
                    out["temp"] = round(temps[k][0].current,1); break
        except: pass
        try:
            boot = psutil.boot_time(); up = time.time()-boot
            d,h,mi = int(up//86400),int((up%86400)//3600),int((up%3600)//60)
            out["uptime"] = f"{d}d {h}h {mi}m" if d else (f"{h}h {mi}m" if h else f"{mi}m")
            out["boot_time"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(boot))
        except: pass
        try:
            procs=[]
            for p in psutil.process_iter(["pid","name","username","cpu_percent","memory_percent","memory_info"]):
                try:
                    i=p.info
                    procs.append({"pid":i["pid"],"name":i["name"],"user":i.get("username","?") or "?",
                        "cpu":round(i.get("cpu_percent") or 0,1),"mem":round(i.get("memory_percent") or 0,1),
                        "mem_mb":round((i.get("memory_info") and i["memory_info"].rss or 0)/1e6)})
                except: pass
            procs.sort(key=lambda x:x["cpu"],reverse=True)
            out["procs"]=procs[:12]; out["proc_count"]=len(psutil.pids())
        except: pass
        try:
            mounts=[]
            for part in psutil.disk_partitions(all=False):
                try:
                    u=psutil.disk_usage(part.mountpoint)
                    mounts.append({"mountpoint":part.mountpoint,"fstype":part.fstype,
                        "total":round(u.total/1e9,1),"used":round(u.used/1e9,1),
                        "free":round(u.free/1e9,1),"pct":round(u.percent,1)})
                except: pass
            mounts.sort(key=lambda x:x["total"],reverse=True)
            out["mounts"]=mounts
            main=next((m for m in mounts if m["mountpoint"]=="/"),mounts[0] if mounts else None)
            if main: out["disk_free"]=main["free"]
        except: pass
        try:
            addrs=psutil.net_if_addrs(); io1=psutil.net_io_counters(pernic=True)
            time.sleep(0.3); io2=psutil.net_io_counters(pernic=True)
            net={}
            for iface,al in addrs.items():
                if iface=="lo": continue
                ip=next((a.address for a in al if a.family==2),None)
                if not ip: continue
                i1=io1.get(iface); i2=io2.get(iface)
                net[iface]={"ip":ip,
                    "rx_sec":int((i2.bytes_recv-i1.bytes_recv)/0.3) if i1 and i2 else 0,
                    "tx_sec":int((i2.bytes_sent-i1.bytes_sent)/0.3) if i1 and i2 else 0,
                    "rx_total":i2.bytes_recv if i2 else 0,"tx_total":i2.bytes_sent if i2 else 0}
            out["net"]=net
        except: pass
        try:
            conns=psutil.net_connections()
            out["connections"]=len([c for c in conns if c.status=="ESTABLISHED"])
            ports=sorted(set(c.laddr.port for c in conns if c.status=="LISTEN" and c.laddr))
            out["listening_ports"]=" ".join(map(str,ports[:8]))
        except: pass
        try:
            users=[]
            for u in psutil.users():
                users.append({"name":u.name,"terminal":u.terminal or "?","host":u.host or "local",
                    "started":time.strftime("%H:%M %m/%d",time.localtime(u.started))})
            out["users"]=users; out["user_count"]=len(users)
        except: pass
    except Exception as e:
        out["error"]=str(e)
    try: out["hostname"]=socket.gethostname()
    except: pass
    try: out["kernel"]=platform.release()
    except: pass
    try: out["arch"]=platform.machine()
    except: pass
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    out["distro"]=line.split("=")[1].strip().strip('"'); break
    except: pass
    try:
        r=subprocess.run(["last","-n","1","-F"],capture_output=True,text=True,timeout=3)
        lines=[l for l in r.stdout.split("\n") if l.strip() and "wtmp" not in l]
        if lines: out["last_login"]=" ".join(lines[0].split()[:5])
    except: pass
    try:
        r=subprocess.run(["grep","-c","Failed password","/var/log/auth.log"],capture_output=True,text=True,timeout=3)
        out["failed_logins"]=int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    except: out["failed_logins"]=0
    try:
        r=subprocess.run(["tailscale","ip","-4"],capture_output=True,text=True,timeout=3)
        if r.returncode==0: out["tailscale_ip"]=r.stdout.strip()
    except: pass
    return out

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  FlowOS -> port {port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
