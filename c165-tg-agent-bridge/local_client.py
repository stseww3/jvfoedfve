"""本地通道客户端：在你的电脑上运行，主动连服务器，替 agent 在工作区里执行命令和读写文件。

配置在同目录的 local.env（bot 发给信任用户的）或 .env（管理员自己的）里：CLIENT_TOKEN、PUBLIC_BASE，
LOCAL_LANG=en 时控制台用英文。
每个聊天要电脑主人在 Telegram 里批准，服务器只转发绑定到这台电脑、已经批准的聊天的操作；
每个聊天用工作区根目录下自己的子目录（main、c1、c2…）。
网页控制台 http://127.0.0.1:<LOCAL_WEB_PORT> 可以看记录，也可以一键暂停。
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import platform
import subprocess
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import websockets
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv(ROOT / "local.env")
load_dotenv(ROOT / ".env")

CLIENT_TOKEN = os.environ["CLIENT_TOKEN"]
PUBLIC_BASE = os.environ.get("PUBLIC_BASE", "http://127.0.0.1:8787").rstrip("/")
WS_URL = PUBLIC_BASE.replace("https://", "wss://").replace("http://", "ws://") + "/client"
ALLOWED_ROOT = Path(os.environ.get("ALLOWED_ROOT", ROOT / "workspaces")).resolve()
WEB_PORT = int(os.environ.get("LOCAL_WEB_PORT", "8791"))
LANG = "en" if os.environ.get("LOCAL_LANG", "zh").lower().startswith("en") else "zh"
WINDOWS = platform.system() == "Windows"

ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)

STATE = {"online": False, "paused": False, "error": "", "device": ""}
HISTORY: deque = deque(maxlen=100)
JOBS: set[asyncio.Task] = set()


def resolve(workspace: str, relative: str = ".") -> Path:
    name = (workspace or "default").replace("\\", "/").strip("/")
    if not name or "/" in name or name in (".", ".."):
        raise ValueError("工作区名不合法")
    base = (ALLOWED_ROOT / name).resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = (base / (relative or ".").replace("\\", "/").lstrip("/")).resolve()
    if target != base and base not in target.parents:
        raise ValueError("路径超出工作区")
    return target


def run_job(job: dict) -> str:
    op = job["op"]
    payload = job.get("payload") or {}
    workspace = job.get("workspace") or "default"
    if op == "shell":
        cwd = resolve(workspace)
        command = str(payload.get("command") or "")
        argv = (
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
            if WINDOWS else ["/bin/bash", "-lc", command]
        )
        try:
            done = subprocess.run(
                argv,
                cwd=str(cwd),
                capture_output=True,
                timeout=int(payload.get("timeout_sec") or 120),
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return f"超时（{payload.get('timeout_sec')} 秒），命令已被终止。\ncwd: {cwd}"
        return f"exit: {done.returncode}\ncwd: {cwd}\nstdout:\n{done.stdout[-80000:]}\nstderr:\n{done.stderr[-20000:]}"
    if op == "list":
        folder = resolve(workspace, payload.get("path") or ".")
        if not folder.is_dir():
            raise ValueError("不是目录")
        lines = []
        for child in sorted(folder.iterdir())[:500]:
            if child.is_dir():
                lines.append(f"dir\t{child.name}")
            else:
                lines.append(f"file\t{child.name}\t{child.stat().st_size}")
        return "\n".join(lines) or "(空目录)"
    if op == "read":
        path = resolve(workspace, payload.get("path") or "")
        if not path.is_file():
            raise ValueError("不是文件")
        return path.read_text(encoding="utf-8", errors="replace")[:200000]
    if op == "write":
        path = resolve(workspace, payload.get("path") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        if payload.get("content_base64"):
            path.write_bytes(base64.b64decode(payload["content_base64"]))
        else:
            path.write_text(str(payload.get("content") or ""), encoding="utf-8")
        return f"已写入 {path}（{path.stat().st_size} 字节）"
    raise ValueError(f"未知操作 {op}")


async def handle_job(conn, job: dict) -> None:
    payload = job.get("payload") or {}
    record = {
        "time": time.strftime("%H:%M:%S"),
        "agent": job.get("agent", ""),
        "op": job.get("op", ""),
        "preview": str(payload.get("command") or payload.get("path") or "")[:300],
        "ok": None,
    }
    HISTORY.appendleft(record)
    if STATE["paused"]:
        ok, output = False, "用户在本地控制台暂停了本地通道。"
    else:
        try:
            ok, output = True, await asyncio.to_thread(run_job, job)
        except Exception as exc:
            ok, output = False, f"执行失败：{exc}"
    record["ok"] = ok
    await conn.send(json.dumps({"type": "result", "id": job["id"], "ok": ok, "output": output}, ensure_ascii=False))


async def hub() -> None:
    while True:
        delay = 3
        try:
            async with websockets.connect(WS_URL, open_timeout=20, max_size=64 * 1024 * 1024, proxy=None) as conn:
                await conn.send(json.dumps({
                    "type": "hello",
                    "token": CLIENT_TOKEN,
                    "allowed_root": str(ALLOWED_ROOT),
                    "os": platform.platform(),
                }))
                async for raw in conn:
                    message = json.loads(raw)
                    if message.get("type") == "hello_ok":
                        STATE["online"], STATE["error"] = True, ""
                        name = message.get("name") or ""
                        STATE["device"] = f"{message.get('device', '')}「{name}」" if name else str(message.get("device", ""))
                    elif message.get("type") == "job":
                        task = asyncio.create_task(handle_job(conn, message))
                        JOBS.add(task)
                        task.add_done_callback(JOBS.discard)
        except websockets.ConnectionClosed as exc:
            if exc.rcvd is not None and exc.rcvd.code == 4401:
                STATE["error"] = (
                    "The server rejected this CLIENT_TOKEN: it was revoked or replaced (/device reset, /device del). "
                    "Replace local.env with the latest one the bot sent you."
                ) if LANG == "en" else (
                    "服务器拒绝了这个 CLIENT_TOKEN：它被作废或换过了（/device reset、/device del）。"
                    "信任用户用 bot 最新发来的 local.env 替换；管理员核对本机 .env 和服务器 .env 里的 CLIENT_TOKEN。"
                )
                delay = 30
            else:
                STATE["error"] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            STATE["error"] = f"{type(exc).__name__}: {exc}"
        STATE["online"] = False
        await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(hub())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def local_only(request: Request, call_next):
    # 挡住 DNS 重绑定：别的网站把自己的域名解析到 127.0.0.1，也读不到控制台
    if request.headers.get("host", "").rsplit(":", 1)[0] not in ("127.0.0.1", "localhost"):
        return PlainTextResponse("forbidden", status_code=403)
    return await call_next(request)


PAGE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>本地通道</title>
<style>
body{margin:0;background:#11150f;color:#e6ebde;font:14px/1.5 "Segoe UI",sans-serif}
header{padding:16px 20px;border-bottom:1px solid #2a3324;display:flex;gap:16px;align-items:center}
main{padding:16px 20px}
.row{padding:8px 0;border-top:1px solid #2a3324}
button{background:#d7f26a;color:#17200c;border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}
button.stop{background:#ff8d8d;color:#2a0d0d}
code{white-space:pre-wrap;word-break:break-all;color:#cfd8c0}
.ok{color:#b6e38a}.bad{color:#ff8d8d}.dim{color:#8a9580}
</style></head><body>
<header><b id="ttl">本地通道</b><span id="st"></span><button id="tg" onclick="toggle()"></button></header>
<main><div class="dim" id="root"></div><div id="list"></div></main>
<script>
const esc = s => String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const T = {
  zh: {title: '本地通道', on: '已连接服务器', dev: '，这台电脑是 ', off: '未连接 ', resume: '恢复执行', pause: '暂停全部',
       root: '工作区根目录：', note: '（每个聊天要电脑主人在 Telegram 里批准，服务器才会转发它的操作；各聊天用自己的子目录）',
       running: '执行中', ok: '成功', bad: '失败/拒绝', empty: '还没有操作记录'},
  en: {title: 'Local channel', on: 'Connected to the server', dev: ', this computer is ', off: 'Not connected ', resume: 'Resume', pause: 'Pause all',
       root: 'Workspace root: ', note: ' (the computer owner approves each chat in Telegram before the server forwards its operations; each chat uses its own subfolder)',
       running: 'running', ok: 'done', bad: 'failed/refused', empty: 'No operations yet'},
};
async function refresh(){
  const d = await (await fetch('/api/state')).json();
  const t = T[d.lang] || T.zh;
  document.title = t.title;
  document.documentElement.lang = d.lang;
  document.getElementById('ttl').textContent = t.title;
  const st = document.getElementById('st');
  st.textContent = d.online ? (t.on + (d.device ? t.dev + d.device : '')) : (t.off + (d.error||''));
  st.className = d.online ? 'ok' : 'bad';
  const b = document.getElementById('tg');
  b.textContent = d.paused ? t.resume : t.pause;
  b.className = d.paused ? '' : 'stop';
  document.getElementById('root').textContent = t.root + d.root + t.note;
  document.getElementById('list').innerHTML = d.history.map(h =>
    `<div class="row">${esc(h.time)} <b>${esc(h.agent)}</b> ${esc(h.op)} <span class="${h.ok===false?'bad':(h.ok?'ok':'dim')}">${h.ok===null?t.running:(h.ok?t.ok:t.bad)}</span><br><code>${esc(h.preview)}</code></div>`
  ).join('') || `<div class="row dim">${t.empty}</div>`;
}
async function toggle(){ await fetch('/api/pause',{method:'POST',headers:{'X-Local-Console':'1'}}); refresh(); }
refresh(); setInterval(refresh, 1500);
</script></body></html>"""


@app.get("/")
async def index() -> HTMLResponse:
    return HTMLResponse(PAGE)


@app.get("/api/state")
async def api_state() -> JSONResponse:
    return JSONResponse({**STATE, "lang": LANG, "root": str(ALLOWED_ROOT), "history": list(HISTORY)})


@app.post("/api/pause")
async def api_pause(request: Request) -> JSONResponse:
    # 带自定义请求头的跨站请求要先过浏览器预检，这里不放行，别的网页就按不了暂停/恢复
    if request.headers.get("x-local-console") != "1":
        return JSONResponse({"error": "forbidden"}, status_code=403)
    STATE["paused"] = not STATE["paused"]
    return JSONResponse({"paused": STATE["paused"]})


if __name__ == "__main__":
    import uvicorn

    if LANG == "en":
        print(f"Local channel console: http://127.0.0.1:{WEB_PORT}  workspaces: {ALLOWED_ROOT}  server: {WS_URL}")
    else:
        print(f"本地通道控制台：http://127.0.0.1:{WEB_PORT}  工作区：{ALLOWED_ROOT}  服务器：{WS_URL}")
    uvicorn.run(app, host="127.0.0.1", port=WEB_PORT, log_level="warning")
