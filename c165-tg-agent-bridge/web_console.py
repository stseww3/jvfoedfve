"""Web Console backend for tg-agent-bridge 3.6.0.

Provides:
- Zero-log PBKDF2-HMAC-SHA256 authentication (built-in superadmin `zwt` sets password on first visit)
- Strict `zwt`-only user management
- Full conversation viewer & composer (ctrl, main1..N, c1..M), inline message edit & delete
- Full-context one-click conversation restart routed through singleton Controller (`ctrl`)
- Live Agent Collaboration Group (`g1`, `g2`...) viewer, human participation & selective wakeup
- Dependency-free binary image/file upload (drag-drop, clipboard paste, mobile picker) & preview
- Real-time cluster CPU/RAM/balloon probe telemetry API
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import mimetypes
import re
import secrets
import time
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse

log = logging.getLogger("bridge.web")

COOKIE_NAME = "dais_web_sid"
PBKDF2_ITERATIONS = 310_000
SESSION_TTL_SEC = 30 * 86400
SUPERADMIN_USER = "zwt"

_LOGIN_FAILS: dict[str, list[float]] = {}


def _now() -> float:
    return time.time()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or not stored.startswith("pbkdf2_sha256$"):
        return False
    parts = stored.split("$")
    if len(parts) != 4:
        return False
    try:
        iters = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(dk, expected)


def _sid_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _rate_limited(ip: str) -> bool:
    now_ts = _now()
    bucket = [t for t in _LOGIN_FAILS.get(ip, []) if now_ts - t < 300]
    _LOGIN_FAILS[ip] = bucket
    return len(bucket) >= 12


def _record_fail(ip: str) -> None:
    _LOGIN_FAILS.setdefault(ip, []).append(_now())


def _clear_fails(ip: str) -> None:
    _LOGIN_FAILS.pop(ip, None)


def ensure_web_superadmin(store) -> None:
    store.run(
        "INSERT OR IGNORE INTO web_users(username,password_hash,role,tg_owner,display_name,disabled,created) "
        "VALUES(?,?,?,?,?,0,?)",
        (SUPERADMIN_USER, "", "superadmin", 0, "zwt", _now()),
    )
    store.run("UPDATE web_users SET role='superadmin', tg_owner=0, disabled=0 WHERE username=?", (SUPERADMIN_USER,))


def _extract_session_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        tok = auth[7:].strip()
        if tok:
            return tok
    return (request.cookies.get(COOKIE_NAME) or "").strip()


def _current_web_user(store, request: Request):
    tok = _extract_session_token(request)
    if not tok:
        return None
    th = _sid_hash(tok)
    srow = store.one("SELECT * FROM web_sessions WHERE token_hash=?", (th,))
    if srow is None:
        return None
    if float(srow["expires"] or 0) < _now():
        store.run("DELETE FROM web_sessions WHERE token_hash=?", (th,))
        return None
    urow = store.one("SELECT * FROM web_users WHERE username=?", (srow["username"],))
    if urow is None or int(urow["disabled"] or 0):
        return None
    return urow


def _is_zwt(user) -> bool:
    return user is not None and user["username"] == SUPERADMIN_USER and user["role"] == "superadmin"


def _issue_web_session(store, username: str, ua: str = "") -> str:
    raw = "ws_" + secrets.token_urlsafe(36)
    now_ts = _now()
    store.run(
        "INSERT INTO web_sessions(token_hash,username,created,expires,ua) VALUES(?,?,?,?,?)",
        (_sid_hash(raw), username, now_ts, now_ts + SESSION_TTL_SEC, (ua or "")[:200]),
    )
    store.run("UPDATE web_users SET last_login=? WHERE username=?", (now_ts, username))
    store.run("DELETE FROM web_sessions WHERE expires<?", (now_ts,))
    return raw


def _set_auth_cookie(resp: JSONResponse, raw_token: str, request: Request) -> JSONResponse:
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "") == "https"
    resp.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_TTL_SEC,
        httponly=True,
        samesite="lax",
        secure=is_https,
        path="/",
    )
    return resp


def _next_virtual_owner(store) -> int:
    row = store.one("SELECT MIN(tg_owner) AS m FROM web_users WHERE tg_owner < 0")
    cur_min = int(row["m"] or 0) if row else 0
    return (cur_min - 1) if cur_min < 0 else -100001


def _parse_id_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        s = raw.strip()
        if s.startswith("["):
            try:
                arr = json.loads(s)
                items = arr if isinstance(arr, list) else []
            except Exception:
                items = []
        else:
            items = re.split(r"[,，\s]+", s)
    else:
        items = []
    seen: list[str] = []
    for x in items:
        v = str(x or "").strip().lower().lstrip("/")
        if v and v not in seen:
            seen.append(v)
    return seen


def _user_allowed_convs(user) -> set[str]:
    if user is None or "allowed_convs" not in user.keys():
        return set()
    return set(_parse_id_list(user["allowed_convs"] or "[]"))


def _user_allowed_groups(user) -> set[str]:
    if user is None or "allowed_groups" not in user.keys():
        return set()
    return set(_parse_id_list(user["allowed_groups"] or "[]"))


def _can_access_conv(bridge, user, conv) -> bool:
    if conv is None or conv["status"] == "deleted":
        return False
    if _is_zwt(user):
        return True
    if bridge.is_system_conv_id(conv["id"]):
        return False
    if (conv["id"] or "").lower() in _user_allowed_convs(user):
        return True
    owner = int(user["tg_owner"] or 0)
    return owner != 0 and bridge.conv_owner(conv) == owner


def _can_access_group(user, grow) -> bool:
    if grow is None:
        return False
    if _is_zwt(user):
        return True
    if grow["status"] != "open":
        return False
    if (grow["id"] or "").lower() in _user_allowed_groups(user):
        return True
    owner = int(user["tg_owner"] or 0)
    return owner != 0 and int(grow["owner"] or 0) == owner


def _group_web_members(store, group_id: str) -> list[str]:
    gid = (group_id or "").lower()
    names = ["zwt"]
    for u in store.q("SELECT username, display_name, allowed_groups, disabled FROM web_users WHERE username!=? ORDER BY created", (SUPERADMIN_USER,)):
        if int(u["disabled"] or 0):
            continue
        if gid in _parse_id_list(u["allowed_groups"] or "[]"):
            names.append(u["display_name"] or u["username"])
    return names


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".avif"}
_OUTBOX_INDEX_CACHE: dict[str, Any] = {"ts": 0.0, "dir": "", "by_suffix": {}}


def _detect_mime_and_image(filename: str, raw_mime: str = "") -> tuple[str, bool]:
    ext = Path(filename or "").suffix.lower()
    guessed = mimetypes.guess_type(filename or "")[0] or ""
    if ext == ".svg":
        guessed = "image/svg+xml"
    elif ext == ".webp" and not guessed:
        guessed = "image/webp"
    mime = (raw_mime or "").strip()
    if not mime or mime == "application/octet-stream":
        mime = guessed or "application/octet-stream"
    if ext == ".svg" and not mime.startswith("image/"):
        mime = "image/svg+xml"
    is_img = mime.startswith("image/") or ext in _IMAGE_EXTS
    return mime, is_img


def _web_file_sig(bridge, file_id: str) -> str:
    if hasattr(bridge, "sign"):
        return str(bridge.sign(f"webfile:{file_id}"))[:20]
    return hashlib.sha256(f"webfile:{file_id}".encode("utf-8")).hexdigest()[:20]


def _outbox_sig(bridge, disk_name: str) -> str:
    if hasattr(bridge, "sign"):
        return str(bridge.sign(f"outbox:{disk_name}"))[:20]
    cand = (bridge.DATA / "outbox" / disk_name).resolve()
    return hashlib.sha256(str(cand).encode("utf-8")).hexdigest()[:20]


def _resolve_file_disk_path(bridge, frow) -> Path | None:
    if frow is None:
        return None
    raw_p = str(frow["path"] or "").strip()
    if raw_p:
        p = Path(raw_p)
        if p.exists():
            return p
        alt = bridge.DATA / "files" / p.name
        if alt.exists():
            return alt
    return None


def _build_file_headers(filename: str, fallback_id: str, mime: str, force_download: bool = False) -> dict[str, str]:
    orig = (filename or fallback_id or "file").replace("\r", "").replace("\n", "")
    ascii_fn = re.sub(r"[^\x20-\x7e]", "_", orig).replace('"', "_").replace("\\", "_").strip() or fallback_id or "file"
    if "." not in ascii_fn and "." in orig:
        ext = Path(orig).suffix[:16]
        if re.match(r"^\.[A-Za-z0-9_\-]+$", ext):
            ascii_fn = f"{fallback_id}{ext}"
    inline_ok = mime.startswith(("image/", "text/", "application/pdf"))
    disp = "attachment" if force_download else ("inline" if inline_ok else "attachment")
    quoted = urllib.parse.quote(orig, safe="")
    return {
        "Content-Disposition": f"{disp}; filename=\"{ascii_fn}\"; filename*=UTF-8''{quoted}",
        "Cache-Control": "private, max-age=86400",
    }


def _serialize_file(store, file_id: str, bridge: Any = None) -> dict[str, Any] | None:
    if not file_id:
        return None
    frow = store.one("SELECT * FROM files WHERE id=?", (file_id,))
    if frow is None:
        return None
    if bridge is not None and _resolve_file_disk_path(bridge, frow) is None:
        return None
    fname = frow["name"] or frow["id"]
    mime, is_img = _detect_mime_and_image(fname, frow["mime"] or "")
    sig_q = f"?sig={_web_file_sig(bridge, frow['id'])}" if bridge is not None else ""
    dl_sep = "&" if sig_q else "?"
    base_url = f"/web/api/files/{frow['id']}{sig_q}"
    return {
        "file_id": frow["id"],
        "name": fname,
        "size": int(frow["size"] or 0),
        "mime": mime,
        "is_image": is_img,
        "url": base_url,
        "download_url": f"{base_url}{dl_sep}download=1",
    }


def _get_outbox_index(outbox_dir: Path) -> dict[str, list[tuple[float, Path]]]:
    now_ts = _now()
    dir_key = str(outbox_dir)
    if _OUTBOX_INDEX_CACHE["dir"] == dir_key and now_ts - float(_OUTBOX_INDEX_CACHE["ts"]) < 2.0:
        return _OUTBOX_INDEX_CACHE["by_suffix"]
    by_suffix: dict[str, list[tuple[float, Path]]] = {}
    if outbox_dir.exists():
        try:
            for entry in outbox_dir.iterdir():
                if not entry.is_file():
                    continue
                nm = entry.name
                sep = nm.find("_")
                suf = nm[sep + 1 :].lower() if sep > 0 else nm.lower()
                try:
                    mt = entry.stat().st_mtime
                except OSError:
                    mt = 0.0
                by_suffix.setdefault(suf, []).append((mt, entry))
        except OSError:
            pass
    _OUTBOX_INDEX_CACHE["ts"] = now_ts
    _OUTBOX_INDEX_CACHE["dir"] = dir_key
    _OUTBOX_INDEX_CACHE["by_suffix"] = by_suffix
    return by_suffix


def _extract_outbox_file(text: str, extra: str, bridge: Any = None, msg_ts: float = 0.0) -> dict[str, Any] | None:
    cand_path: Path | None = None
    fname = ""
    if extra:
        try:
            pay = json.loads(extra)
        except Exception:
            pay = None
        if isinstance(pay, dict) and pay.get("kind") == "file" and pay.get("file"):
            raw_p = Path(str(pay["file"]))
            fname = str(pay.get("filename") or raw_p.name)
            if raw_p.exists():
                cand_path = raw_p
            elif bridge is not None:
                alt = bridge.DATA / "outbox" / raw_p.name
                if alt.exists():
                    cand_path = alt

    if cand_path is None and bridge is not None and text:
        m = re.match(r"^\[发送文件\s+([^\]]+)\]", text.strip())
        if m:
            fname = m.group(1).strip()
            safe = (re.sub(r"[^\w.\-]", "_", fname)[:80] or "file").lower()
            idx = _get_outbox_index(bridge.DATA / "outbox")
            cands = idx.get(safe) or []
            if cands:
                if msg_ts > 0:
                    cand_path = min(cands, key=lambda item: abs(item[0] - msg_ts))[1]
                else:
                    cand_path = max(cands, key=lambda item: item[0])[1]

    if cand_path is None or not cand_path.exists():
        return None
    if not fname:
        fname = cand_path.name
    mime, is_img = _detect_mime_and_image(fname)
    tok = _outbox_sig(bridge, cand_path.name) if bridge is not None else hashlib.sha256(str(cand_path.resolve()).encode("utf-8")).hexdigest()[:20]
    q_base = f"path_sig={tok}&p={urllib.parse.quote(cand_path.name)}&fn={urllib.parse.quote(fname)}"
    try:
        fsize = cand_path.stat().st_size
    except OSError:
        fsize = 0
    return {
        "file_id": f"out_{tok}",
        "name": fname,
        "size": fsize,
        "mime": mime,
        "is_image": is_img,
        "url": f"/web/api/outbox-file?{q_base}",
        "download_url": f"/web/api/outbox-file?{q_base}&download=1",
    }


def _can_user_read_file(bridge, store, user, frow) -> bool:
    if user is None or frow is None:
        return False
    if _is_zwt(user):
        return True
    fconv = (frow["conv"] or "").strip()
    uid_owner = int(user["tg_owner"] or 0)
    a_convs = _user_allowed_convs(user)
    a_grps = _user_allowed_groups(user)
    if fconv == "":
        return True
    if fconv.startswith("owner:"):
        try:
            fowner = int(fconv.split(":", 1)[1])
        except ValueError:
            fowner = -999999999
        if uid_owner != 0 and fowner == uid_owner:
            return True
        if fowner == 0 and (a_convs or a_grps):
            return True
    else:
        fc = bridge.conv_row(fconv)
        if fc is not None and _can_access_conv(bridge, user, fc):
            return True

    fid = frow["id"]
    like_pat = f"%{fid}%"
    for cid in a_convs:
        hit = store.one("SELECT 1 AS ok FROM messages WHERE conv=? AND (file_id=? OR text LIKE ?) LIMIT 1", (cid, fid, like_pat))
        if hit is not None:
            return True
    if uid_owner != 0:
        hit_own = store.one(
            "SELECT 1 AS ok FROM messages m JOIN convs c ON c.id=m.conv WHERE c.owner=? AND (m.file_id=? OR m.text LIKE ?) LIMIT 1",
            (uid_owner, fid, like_pat),
        )
        if hit_own is not None:
            return True
    for gid in a_grps:
        ghit = store.one("SELECT 1 AS ok FROM agent_group_messages WHERE group_id=? AND text LIKE ? LIMIT 1", (gid, like_pat))
        if ghit is not None:
            return True
    return False


def _serialize_conv(bridge, crow) -> dict[str, Any]:
    info = bridge.conv_state(crow)
    trow = bridge.store.one("SELECT * FROM agent_traces WHERE conv=?", (crow["id"],))
    think_stuck, stuck_s = bridge.check_thinking_stuck(crow, trow)
    tline = bridge.trace_one_liner(crow["id"])
    cid = crow["id"]
    if cid in ("ctrl", "main"):
        kind = "ctrl"
    elif bridge.is_main_node_id(cid):
        kind = "launcher"
    elif bridge.is_worker_node_id(cid):
        kind = "runner"
    else:
        kind = "chat"
    return {
        "id": cid,
        "num": int(crow["num"] or 0),
        "name": bridge.conv_name(crow),
        "raw_name": crow["name"] or "",
        "brief": crow["brief"] or "",
        "kind": kind,
        "status": crow["status"],
        "state": info["state"],
        "state_label": bridge.STATE_TEXT.get(info["state"], info["state"]),
        "model": bridge.effective_conv_model(crow) or "",
        "actual_model": crow["actual_model"] or "",
        "model_check": crow["model_check"] or "",
        "cloud": bridge.cloud_of(crow) if kind == "chat" else int(crow["cloud"] or 0),
        "owner": bridge.conv_owner(crow),
        "in_tg": bridge.conv_in_tg(crow),
        "parent_conv": crow["parent_conv"] or "",
        "dedicated_req": bool(int(crow["dedicated_req"] or 0)),
        "dedicated_node": crow["dedicated_node"] or "",
        "task_agent_id": crow["task_agent_id"] or "",
        "git": bridge.git_info(crow),
        "pending": info["pending"],
        "unread": info["unread"],
        "phase": (trow["phase"] if trow else "") or "",
        "thinking_stuck": think_stuck,
        "thinking_stuck_sec": round(stuck_s, 1) if think_stuck else 0,
        "trace_line": tline,
        "created": float(crow["created"] or 0),
    }


def _build_full_restart_dossier(bridge, conv, operator_note: str = "") -> str:
    """汇总 100% 完整上下文信息通知总控（ctrl），杜绝漏信息导致主控误操作！"""
    cid = conv["id"]
    eff_model = bridge.effective_conv_model(conv) or "继承默认（未显式指定）"
    cnum = bridge.cloud_of(conv)
    git_s = bridge.git_text(conv) or "暂未记录 Git 仓库分支"
    parent_s = conv["parent_conv"] or "无（顶层会话）"
    children = [
        r["id"] + (f"「{r['name']}」" if r["name"] else "")
        for r in bridge.store.q("SELECT id, name FROM convs WHERE parent_conv=? AND status='open' ORDER BY num", (cid,))
    ]
    groups = [
        f"{g['id']}「{g['name']}」"
        for g in bridge.store.q(
            "SELECT g.id, g.name FROM agent_groups g JOIN agent_group_members m ON m.group_id=g.id "
            "WHERE m.conv=? AND g.status='open' ORDER BY g.num",
            (cid,),
        )
    ]
    trow = bridge.store.one("SELECT * FROM agent_traces WHERE conv=?", (cid,))
    trace_summary = "无历史轨迹"
    if trow:
        try:
            det = json.loads(trow["detail"] or "{}")
        except Exception:
            det = {}
        parts = [f"phase={trow['phase'] or '-'}", f"摘要={trow['summary'] or '-'}"]
        if det.get("file_path"):
            parts.append(f"最后改文件={det['file_path']}")
        if det.get("cwd"):
            parts.append(f"目录={det['cwd']}")
        if det.get("last_thought"):
            parts.append(f"最后思考={str(det['last_thought'])[:120]}")
        trace_summary = " | ".join(parts)

    msg_rows = [
        r for r in bridge.store.q("SELECT * FROM messages WHERE conv=? ORDER BY id DESC LIMIT 12", (cid,))
        if not bridge.is_keepalive(r)
    ]
    msg_rows.reverse()
    total_msgs = bridge.store.one("SELECT COUNT(*) AS n FROM messages WHERE conv=?", (cid,))["n"]
    recent_digest = "\n".join(
        f"  #{r['id']} [{'AI' if r['outgoing'] else (r['user_name'] or '用户')}]: {(r['text'] or '')[:160]}"
        for r in msg_rows[-8:]
    ) or "  （暂无历史发言）"

    ded_info = (
        f"当前独占节点={conv['dedicated_node']}"
        if conv["dedicated_node"]
        else ("曾申请独占机器" if int(conv["dedicated_req"] or 0) else "共享节点模式（默认不独占）")
    )
    op_note_line = f"- 管理员重开附言：{operator_note}\n" if operator_note else ""

    return (
        f"【Web 控制台管理员手动重开指令 · 全量上下文档案】\n"
        f"管理员在 Web 面板点击了重开聊天：{bridge.conv_tag(conv)}（编号 `{cid}`）。\n"
        f"{op_note_line}"
        f"请依据以下【完整上下文档案】执行标准化重开，保持原有参数与模型设置：\n"
        f"- 原定模型（必须保持一致）：`{eff_model}`\n"
        f"- 原始职责说明（brief）：{conv['brief'] or '无'}\n"
        f"- 历史所属目录/主Agent：`cloud{cnum}` | 机器占用策略：{ded_info}\n"
        f"- 父会话：{parent_s} | 名下活跃派生子工：{', '.join(children) or '无'}\n"
        f"- 所在 Agent 协作群：{', '.join(groups) or '无'}\n"
        f"- GitHub 仓库与分支：{git_s}\n"
        f"- 父记忆交接摘要（memory_note）：{(conv['memory_note'] or '无')[:400]}\n"
        f"- 中断前最后工作现场：{trace_summary}\n"
        f"- 历史消息总数：{total_msgs} 条（管理员最新编辑/删减已落库生效，最近摘录如下）：\n"
        f"{recent_digest}\n\n"
        f"👉 请立即调用 `dispatch_task_op(chat=\"{cid}\", action=\"restart\", target_main=\"auto\", model=\"{bridge.effective_conv_model(conv) or ''}\")` "
        f"向健康的主 Agent 下发标准化 `[TASK_LAUNCH]` 启动单！"
    )


def register_web_console(app: FastAPI, bridge: Any) -> None:
    store = bridge.store
    ui_path = Path(__file__).resolve().parent / "web_ui.html"

    @app.get("/")
    @app.get("/web")
    @app.get("/web/")
    async def web_index() -> Response:
        ensure_web_superadmin(store)
        if not ui_path.exists():
            return PlainTextResponse("web_ui.html not found", status_code=404)
        return HTMLResponse(
            ui_path.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/web/api/auth/status")
    async def web_auth_status(request: Request) -> JSONResponse:
        ensure_web_superadmin(store)
        zwt_row = store.one("SELECT password_hash FROM web_users WHERE username=?", (SUPERADMIN_USER,))
        zwt_needs_setup = bool(zwt_row is not None and not (zwt_row["password_hash"] or "").strip())
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({
                "ok": True,
                "authenticated": False,
                "zwt_needs_setup": zwt_needs_setup,
                "version": bridge.VERSION,
            })
        return JSONResponse({
            "ok": True,
            "authenticated": True,
            "version": bridge.VERSION,
            "user": {
                "username": user["username"],
                "display_name": user["display_name"] or user["username"],
                "role": user["role"],
                "is_zwt": _is_zwt(user),
                "tg_owner": int(user["tg_owner"] or 0),
            },
        })

    @app.post("/web/api/auth/check-user")
    async def web_check_user(request: Request) -> JSONResponse:
        ensure_web_superadmin(store)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        uname = str((body or {}).get("username") or "").strip().lower()
        if uname == SUPERADMIN_USER:
            row = store.one("SELECT password_hash FROM web_users WHERE username=?", (SUPERADMIN_USER,))
            needs_setup = bool(row is not None and not (row["password_hash"] or "").strip())
            return JSONResponse({"ok": True, "username": SUPERADMIN_USER, "needs_setup": needs_setup})
        return JSONResponse({"ok": True, "username": uname, "needs_setup": False})

    @app.post("/web/api/auth/setup-zwt")
    async def web_setup_zwt(request: Request) -> JSONResponse:
        ensure_web_superadmin(store)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "无效的请求数据"}, status_code=400)
        uname = str((body or {}).get("username") or "").strip().lower()
        pwd = str((body or {}).get("password") or "")
        if uname != SUPERADMIN_USER:
            return JSONResponse({"ok": False, "error": "仅超级管理员 zwt 支持首次初始化设密"}, status_code=403)
        if len(pwd) < 6 or len(pwd) > 128:
            return JSONResponse({"ok": False, "error": "密码长度需在 6 ~ 128 位之间"}, status_code=400)
        row = store.one("SELECT password_hash FROM web_users WHERE username=?", (SUPERADMIN_USER,))
        if row is not None and (row["password_hash"] or "").strip():
            return JSONResponse({"ok": False, "error": "zwt 密码已初始化过，请直接登录"}, status_code=409)
        pw_hash = hash_password(pwd)
        store.run(
            "UPDATE web_users SET password_hash=?, role='superadmin', tg_owner=0, disabled=0 WHERE username=? AND password_hash=''",
            (pw_hash, SUPERADMIN_USER),
        )
        verify_row = store.one("SELECT password_hash FROM web_users WHERE username=?", (SUPERADMIN_USER,))
        if verify_row is None or verify_row["password_hash"] != pw_hash:
            return JSONResponse({"ok": False, "error": "初始化冲突，请刷新后直接登录"}, status_code=409)
        sid = _issue_web_session(store, SUPERADMIN_USER, request.headers.get("user-agent", ""))
        log.info("web superadmin zwt initialized password hash")
        resp = JSONResponse({
            "ok": True,
            "token": sid,
            "user": {"username": SUPERADMIN_USER, "display_name": "zwt", "role": "superadmin", "is_zwt": True, "tg_owner": 0},
        })
        return _set_auth_cookie(resp, sid, request)

    @app.post("/web/api/auth/login")
    async def web_login(request: Request) -> JSONResponse:
        ensure_web_superadmin(store)
        ip = request.client.host if request.client else "unknown"
        if _rate_limited(ip):
            return JSONResponse({"ok": False, "error": "登录尝试过于频繁，请 5 分钟后再试"}, status_code=429)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "无效的请求数据"}, status_code=400)
        uname = str((body or {}).get("username") or "").strip().lower()
        pwd = str((body or {}).get("password") or "")
        if not uname:
            return JSONResponse({"ok": False, "error": "请输入用户名"}, status_code=400)
        urow = store.one("SELECT * FROM web_users WHERE username=?", (uname,))
        if urow is not None and uname == SUPERADMIN_USER and not (urow["password_hash"] or "").strip():
            return JSONResponse({
                "ok": False,
                "needs_setup": True,
                "error": "检测到 zwt 首次访问，请先设定你的管理员密码",
            })
        if urow is None or int(urow["disabled"] or 0) or not verify_password(pwd, urow["password_hash"] or ""):
            _record_fail(ip)
            return JSONResponse({"ok": False, "error": "用户名或密码错误"}, status_code=401)
        _clear_fails(ip)
        sid = _issue_web_session(store, urow["username"], request.headers.get("user-agent", ""))
        log.info("web user login ok: %s", urow["username"])
        resp = JSONResponse({
            "ok": True,
            "token": sid,
            "user": {
                "username": urow["username"],
                "display_name": urow["display_name"] or urow["username"],
                "role": urow["role"],
                "is_zwt": _is_zwt(urow),
                "tg_owner": int(urow["tg_owner"] or 0),
            },
        })
        return _set_auth_cookie(resp, sid, request)

    @app.post("/web/api/auth/logout")
    async def web_logout(request: Request) -> JSONResponse:
        tok = _extract_session_token(request)
        if tok:
            store.run("DELETE FROM web_sessions WHERE token_hash=?", (_sid_hash(tok),))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(COOKIE_NAME, path="/")
        return resp

    @app.post("/web/api/auth/change-password")
    async def web_change_password(request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        old_pw = str((body or {}).get("old_password") or "")
        new_pw = str((body or {}).get("new_password") or "")
        if not verify_password(old_pw, user["password_hash"] or ""):
            return JSONResponse({"ok": False, "error": "当前密码不正确"}, status_code=403)
        if len(new_pw) < 6 or len(new_pw) > 128:
            return JSONResponse({"ok": False, "error": "新密码长度需在 6 ~ 128 位之间"}, status_code=400)
        store.run("UPDATE web_users SET password_hash=? WHERE username=?", (hash_password(new_pw), user["username"]))
        return JSONResponse({"ok": True})

    # ---------------------------------------------------------------- 用户管理（严格仅限 zwt）

    @app.get("/web/api/users")
    async def web_list_users(request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if not _is_zwt(user):
            return JSONResponse({"ok": False, "error": "仅超级管理员 zwt 有权管理用户"}, status_code=403)
        rows = store.q("SELECT username, role, tg_owner, display_name, disabled, allowed_convs, allowed_groups, created, last_login, password_hash FROM web_users ORDER BY username='zwt' DESC, created")
        items = []
        for r in rows:
            owner_id = int(r["tg_owner"] or 0)
            a_convs = _parse_id_list(r["allowed_convs"] or "[]")
            a_grps = _parse_id_list(r["allowed_groups"] or "[]")
            chat_cnt = (bridge.chat_count(owner_id) + len(a_convs)) if owner_id != 0 else len(bridge.open_convs())
            items.append({
                "username": r["username"],
                "display_name": r["display_name"] or r["username"],
                "role": r["role"],
                "tg_owner": owner_id,
                "disabled": bool(int(r["disabled"] or 0)),
                "allowed_convs": a_convs,
                "allowed_groups": a_grps,
                "has_password": bool((r["password_hash"] or "").strip()),
                "chat_count": chat_cnt,
                "created": float(r["created"] or 0),
                "last_login": float(r["last_login"] or 0),
            })
        return JSONResponse({"ok": True, "users": items, "chat_limit": bridge.CHAT_LIMIT})

    @app.post("/web/api/users")
    async def web_upsert_user(request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if not _is_zwt(user):
            return JSONResponse({"ok": False, "error": "仅超级管理员 zwt 有权管理用户"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        uname = re.sub(r"[^a-z0-9_.\-]", "", str((body or {}).get("username") or "").strip().lower())[:32]
        if not uname:
            return JSONResponse({"ok": False, "error": "用户名仅限字母、数字、下划线或短横线"}, status_code=400)
        disp = str((body or {}).get("display_name") or uname).strip()[:40]
        pwd = str((body or {}).get("password") or "")
        disabled = 1 if (body or {}).get("disabled") else 0
        raw_tg_owner = (body or {}).get("tg_owner")
        has_ac = "allowed_convs" in (body or {})
        has_ag = "allowed_groups" in (body or {})
        ac_list = [bridge.parse_conv(x) for x in _parse_id_list((body or {}).get("allowed_convs")) if bridge.parse_conv(x) and not bridge.is_system_conv_id(bridge.parse_conv(x))]
        ag_list = [bridge.parse_group(x) for x in _parse_id_list((body or {}).get("allowed_groups")) if bridge.parse_group(x)]

        existing = store.one("SELECT * FROM web_users WHERE username=?", (uname,))
        if uname == SUPERADMIN_USER:
            if pwd:
                if len(pwd) < 6:
                    return JSONResponse({"ok": False, "error": "密码至少 6 位"}, status_code=400)
                store.run("UPDATE web_users SET password_hash=?, display_name=? WHERE username=?", (hash_password(pwd), disp, SUPERADMIN_USER))
            else:
                store.run("UPDATE web_users SET display_name=? WHERE username=?", (disp, SUPERADMIN_USER))
            return JSONResponse({"ok": True, "username": SUPERADMIN_USER})

        if existing is None:
            if len(pwd) < 6:
                return JSONResponse({"ok": False, "error": "新建用户密码至少 6 位"}, status_code=400)
            tg_owner = int(raw_tg_owner) if str(raw_tg_owner or "").lstrip("-").isdigit() and int(raw_tg_owner) != 0 else _next_virtual_owner(store)
            store.run(
                "INSERT INTO web_users(username,password_hash,role,tg_owner,display_name,disabled,allowed_convs,allowed_groups,created) VALUES(?,?,?,?,?,?,?,?,?)",
                (uname, hash_password(pwd), "user", tg_owner, disp, disabled, json.dumps(ac_list), json.dumps(ag_list), _now()),
            )
            log.info("web user created by zwt: %s (owner=%s, convs=%s, groups=%s)", uname, tg_owner, ac_list, ag_list)
        else:
            tg_owner = int(raw_tg_owner) if str(raw_tg_owner or "").lstrip("-").isdigit() and int(raw_tg_owner) != 0 else int(existing["tg_owner"] or _next_virtual_owner(store))
            final_ac = json.dumps(ac_list) if has_ac else (existing["allowed_convs"] or "[]")
            final_ag = json.dumps(ag_list) if has_ag else (existing["allowed_groups"] or "[]")
            if pwd:
                if len(pwd) < 6:
                    return JSONResponse({"ok": False, "error": "重置密码至少 6 位"}, status_code=400)
                store.run(
                    "UPDATE web_users SET password_hash=?, display_name=?, tg_owner=?, disabled=?, allowed_convs=?, allowed_groups=? WHERE username=?",
                    (hash_password(pwd), disp, tg_owner, disabled, final_ac, final_ag, uname),
                )
            else:
                store.run(
                    "UPDATE web_users SET display_name=?, tg_owner=?, disabled=?, allowed_convs=?, allowed_groups=? WHERE username=?",
                    (disp, tg_owner, disabled, final_ac, final_ag, uname),
                )
            if disabled:
                store.run("DELETE FROM web_sessions WHERE username=?", (uname,))
        return JSONResponse({"ok": True, "username": uname})

    @app.delete("/web/api/users/{target_username}")
    async def web_delete_user(target_username: str, request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if not _is_zwt(user):
            return JSONResponse({"ok": False, "error": "仅超级管理员 zwt 有权管理用户"}, status_code=403)
        uname = target_username.strip().lower()
        if uname == SUPERADMIN_USER:
            return JSONResponse({"ok": False, "error": "不能删除超级管理员 zwt"}, status_code=400)
        store.run("DELETE FROM web_sessions WHERE username=?", (uname,))
        store.run("DELETE FROM web_users WHERE username=?", (uname,))
        log.info("web user deleted by zwt: %s", uname)
        return JSONResponse({"ok": True})

    # ---------------------------------------------------------------- 全局侧栏状态：会话 + 主控/主Agent + 节点探针 + 协作群

    @app.get("/web/api/bootstrap")
    async def web_bootstrap(request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        bridge.ensure_main_conv()
        is_super = _is_zwt(user)
        convs_out: list[dict[str, Any]] = []

        if is_super:
            ctrl_c = bridge.conv_row("ctrl") if bridge.ctrl_is_active() or (bridge.conv_row("ctrl") and bridge.conv_row("ctrl")["task_code"]) else bridge.conv_row("main")
            if ctrl_c is not None:
                convs_out.append(_serialize_conv(bridge, ctrl_c))
            for mn in store.q("SELECT * FROM exec_nodes WHERE kind='launcher' AND status!='removed' ORDER BY num"):
                mc = bridge.conv_row(mn["id"])
                if mc is not None:
                    convs_out.append(_serialize_conv(bridge, mc))
            all_chat_rows = [
                r for r in store.q("SELECT * FROM convs WHERE status!='deleted' ORDER BY status!='open', IFNULL(owner,0)!=0, num DESC")
                if not bridge.is_system_conv_id(r["id"])
            ]
            for r in all_chat_rows:
                convs_out.append(_serialize_conv(bridge, r))
        else:
            owner_id = int(user["tg_owner"] or 0)
            allowed_c = _user_allowed_convs(user)
            seen_cids: set[str] = set()
            for cid_allow in sorted(allowed_c):
                rc = bridge.conv_row(cid_allow)
                if rc is not None and rc["status"] != "deleted" and not bridge.is_system_conv_id(rc["id"]):
                    convs_out.append(_serialize_conv(bridge, rc))
                    seen_cids.add(rc["id"])
            my_rows = [
                r for r in store.q(
                    "SELECT * FROM convs WHERE owner=? AND status!='deleted' AND IFNULL(in_tg,1)=1 ORDER BY status!='open', num DESC",
                    (owner_id,),
                )
                if not bridge.is_system_conv_id(r["id"]) and r["id"] not in seen_cids
            ]
            for r in my_rows:
                convs_out.append(_serialize_conv(bridge, r))

        groups_out = []
        for g in store.q("SELECT * FROM agent_groups WHERE status!='closed' ORDER BY num DESC"):
            if not _can_access_group(user, g):
                continue
            mems = bridge.group_members(g["id"])
            web_mems = _group_web_members(store, g["id"])
            last_gm = store.one("SELECT text, sender_name, ts FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT 1", (g["id"],))
            msg_cnt = store.one("SELECT COUNT(*) AS n FROM agent_group_messages WHERE group_id=?", (g["id"],))["n"]
            groups_out.append({
                "id": g["id"],
                "name": g["name"] or g["id"],
                "topic": g["topic"] or "",
                "status": g["status"],
                "members": mems,
                "web_members": web_mems,
                "message_count": msg_cnt,
                "last_text": (last_gm["text"][:80] if last_gm and last_gm["text"] else ""),
                "last_sender": (last_gm["sender_name"] if last_gm else ""),
                "last_ts": float(last_gm["ts"] or 0) if last_gm else 0,
            })

        nodes_out = []
        if is_super:
            for n in store.q("SELECT * FROM exec_nodes WHERE status!='removed' ORDER BY kind!='launcher', num"):
                metrics = bridge.node_metrics_dict(n)
                mounted = [c["id"] for c in bridge.open_convs() if bridge.cloud_of(c) == int(n["cloud_num"] or -999)] if n["kind"] == "launcher" else []
                pend_ops = store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE target_node=? AND status='pending'", (n["id"],))["n"]
                nodes_out.append({
                    "id": n["id"],
                    "kind": n["kind"],
                    "name": n["name"] or n["id"],
                    "cloud_num": int(n["cloud_num"] or 0),
                    "online": bridge.node_is_online(n),
                    "status": n["status"],
                    "exclusive_conv": n["exclusive_conv"] or "",
                    "allowed_convs": bridge.node_allowed_list(n),
                    "mounted_convs": mounted,
                    "pending_ops": pend_ops,
                    "metrics": metrics,
                    "metrics_age_sec": round(max(0.0, _now() - float(n["metrics_ts"] or 0)), 1) if n["metrics_ts"] else None,
                })

        return JSONResponse({
            "ok": True,
            "version": bridge.VERSION,
            "convs": convs_out,
            "groups": groups_out,
            "nodes": nodes_out,
        })

    # ---------------------------------------------------------------- 新建对话 & 一键全量上下文重开

    @app.post("/web/api/convs")
    async def web_create_conv(request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        brief = str((body or {}).get("brief") or "").strip()[:1500]
        name = str((body or {}).get("name") or "").strip()[:20]
        model = " ".join(str((body or {}).get("model") or "").split())[:100]

        if _is_zwt(user):
            admin_dms = bridge.admin_chats()
            home_dm = admin_dms[0] if admin_dms else 0
            conv = bridge.create_conv(brief=brief, home_chat=home_dm, name=name, owner=0, model=model, in_tg=True)
            bridge.dispatch_conv_to_cluster(conv, "管理员在 Web 控制台新建了聊天", requester="web_admin")
        else:
            owner_id = int(user["tg_owner"] or 0)
            if bridge.CHAT_LIMIT > 0 and bridge.chat_count(owner_id) >= bridge.CHAT_LIMIT:
                return JSONResponse({"ok": False, "error": f"你的聊天数量已达上限（最多 {bridge.CHAT_LIMIT} 个）"}, status_code=403)
            conv = bridge.create_conv(brief=brief, home_chat=max(0, owner_id), name=name, owner=owner_id, model="", in_tg=True)
            bridge.dispatch_conv_to_cluster(conv, f"Web 用户 {user['username']} 新建了聊天", requester="web_user")
        return JSONResponse({"ok": True, "conv": _serialize_conv(bridge, bridge.conv_row(conv["id"]))})

    @app.post("/web/api/convs/{conv_id}/restart")
    async def web_restart_conv(conv_id: str, request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        cid = bridge.parse_conv(conv_id)
        conv = bridge.conv_row(cid) if cid else None
        if not _can_access_conv(bridge, user, conv):
            return JSONResponse({"ok": False, "error": "无权操作该会话"}, status_code=403)
        if cid in ("main",) or bridge.is_main_node_id(cid) or bridge.is_worker_node_id(cid):
            return JSONResponse({"ok": False, "error": "顶层主 Agent / 工作机请在 Cursor 云端页面查看，业务会话与总控支持一键重开"}, status_code=400)

        try:
            body = await request.json()
        except Exception:
            body = {}
        operator_note = str((body or {}).get("note") or "").strip()[:500]
        target_main = str((body or {}).get("target_main") or "auto").strip().lower()
        new_model_req = " ".join(str((body or {}).get("model") or "").split())[:100]

        if cid == "ctrl":
            if not _is_zwt(user):
                return JSONResponse({"ok": False, "error": "仅 zwt 可重开总控"}, status_code=403)
            if new_model_req:
                bridge.update_conv_model("ctrl", new_model_req)
            op_id = bridge.ensure_controller_alive(force=True)
            return JSONResponse({"ok": True, "routed_to": "bootstrap", "op_id": op_id or ""})

        if conv["status"] != "open":
            store.run("UPDATE convs SET status='open', closed=0 WHERE id=?", (cid,))
            conv = bridge.conv_row(cid)

        if new_model_req:
            bridge.update_conv_model(cid, new_model_req)
            conv = bridge.conv_row(cid)
        else:
            bridge.lock_in_conv_model(conv)
            conv = bridge.conv_row(cid)
        dossier = _build_full_restart_dossier(bridge, conv, operator_note=operator_note)

        # 同步 read_cursor 到当前最后一条历史消息（确保重开接手时把编辑/删减后的完整最近记录一次性看全，不重复当未读刷屏）
        max_mid = int((store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages WHERE conv=?", (cid,)) or {"n": 0})["n"] or 0)
        old_ag = bridge.active_agent(conv)
        if old_ag is not None:
            bridge.stop_identity(old_ag["id"], "管理员在 Web 控制台点击重开")
        store.run("UPDATE convs SET task_agent_id='', read_cursor=MAX(read_cursor, ?) WHERE id=?", (max_mid, cid))

        if bridge.ctrl_is_active():
            # 按用户要求：通知唯一主控（ctrl），把完整无损上下文信息全量交给主控去向主 Agent 发标准化命令！
            bridge.issue_task(cid)
            if target_main and target_main != "auto":
                dossier += f"\n（管理员建议优先派往主 Agent：`{target_main}`）"
            bridge.system_note("ctrl", dossier, wake=1)
            routed = "ctrl"
        else:
            # 若总控此刻恰好不在线，直接向最优在线 mainN 下发标准化启动单兜底，同时把完整档案留存给 ctrl
            launcher = bridge.node_row(target_main) if target_main and target_main != "auto" else None
            if launcher is None or not bridge.node_is_online(launcher):
                launcher = bridge.select_best_launcher(for_conv=cid)
            if launcher is not None and bridge.is_main_node_id(launcher["id"]):
                _, nid = bridge.enqueue_launch_op(bridge.conv_row(cid), launcher, requester="web_restart")
                bridge.system_note("ctrl", dossier + f"\n（注：因总控暂未在线，桥已先行向 {nid} 下发标准化启动单兜底）", wake=0)
                routed = nid
            else:
                bridge.restart_conv(bridge.conv_row(cid), "Web 控制台重开")
                fresh = bridge.conv_row(cid)
                bridge.system_note("main", dossier + "\n\n" + bridge.task_note(fresh, "Web 控制台重开"), wake=1)
                routed = "main"

        return JSONResponse({
            "ok": True,
            "routed_to": routed,
            "conv": _serialize_conv(bridge, bridge.conv_row(cid)),
        })

    def _serialize_conv_msg_row(conv_disp_name: str, r) -> dict[str, Any]:
        raw_txt = r["text"] or ""
        msg_ts = float(r["ts"] or 0)
        files_list: list[dict[str, Any]] = []
        seen_fids: set[str] = set()
        primary_f = _serialize_file(store, r["file_id"] or "", bridge=bridge) or _extract_outbox_file(
            raw_txt, r["extra"] or "", bridge=bridge, msg_ts=msg_ts
        )
        if primary_f:
            files_list.append(primary_f)
            seen_fids.add(primary_f["file_id"])
        if raw_txt:
            for m_fid in re.findall(r"\b(f_[0-9a-f]{8,20})\b", raw_txt):
                if m_fid not in seen_fids:
                    extra_f = _serialize_file(store, m_fid, bridge=bridge)
                    if extra_f:
                        files_list.append(extra_f)
                        seen_fids.add(m_fid)
        f_meta = files_list[0] if files_list else None

        ctype = r["chat_type"] or "private"
        ctitle = r["chat_title"] or ""
        uname = r["user_name"] or ""
        is_out = bool(int(r["outgoing"] or 0))
        if ctype in ("private", "group", "supergroup", "channel"):
            msg_channel = "human"
            peer_label = ctitle if ctype in ("group", "supergroup") and ctitle else ("Web" if ctitle == "Web控制台" else "Telegram")
            sender_display = (uname or conv_disp_name) if is_out else (uname or "用户")
        elif ctype == "agent_dm":
            msg_channel = "agent_dm"
            peer_label = (ctitle or "其他Agent") if is_out else (uname or ctitle.removeprefix("来自 ").strip() or "Agent")
            sender_display = f"我 → {peer_label}" if is_out else f"{peer_label} → 我"
        elif ctype == "agent_group":
            msg_channel = "agent_group"
            peer_label = ctitle.split(" 成员:")[0].strip() if ctitle else "协作群"
            sender_display = f"{uname or conv_disp_name}" if is_out else (uname or "群成员")
        else:
            msg_channel = "system"
            peer_label = "标准单据" if "[STANDARD_OP" in raw_txt else ("重开档案" if "全量上下文档案" in raw_txt else "系统通知")
            sender_display = uname or "系统"

        return {
            "id": r["id"],
            "ts": msg_ts,
            "chat_id": int(r["chat_id"] or 0),
            "chat_type": ctype,
            "chat_title": ctitle,
            "channel": msg_channel,
            "peer_label": peer_label,
            "sender_display": sender_display,
            "user_name": uname,
            "text": raw_txt,
            "outgoing": is_out,
            "delivered": bool(int(r["delivered"] if r["delivered"] is not None else 1)),
            "tg_msg_id": int(r["tg_msg_id"] or 0),
            "file": f_meta,
            "files": files_list,
        }

    def _serialize_group_msg_row(r) -> dict[str, Any]:
        try:
            mnt = json.loads(r["mentions"] or "[]")
        except Exception:
            mnt = []
        raw_gtxt = r["text"] or ""
        g_files: list[dict[str, Any]] = []
        seen_gf: set[str] = set()
        for m_fid in re.findall(r"\b(f_[0-9a-f]{8,20})\b", raw_gtxt):
            if m_fid not in seen_gf:
                gf = _serialize_file(store, m_fid, bridge=bridge)
                if gf:
                    g_files.append(gf)
                    seen_gf.add(m_fid)
        f_meta = g_files[0] if g_files else None
        return {
            "id": r["id"],
            "sender_conv": r["sender_conv"] or "",
            "sender_name": r["sender_name"] or r["sender_conv"] or "",
            "text": raw_gtxt,
            "mentions": mnt if isinstance(mnt, list) else [],
            "ts": float(r["ts"] or 0),
            "file": f_meta,
            "files": g_files,
        }

    # ---------------------------------------------------------------- 消息读取、发送、在线编辑与删除

    @app.get("/web/api/convs/{conv_id}/messages")
    async def web_get_messages(
        conv_id: str,
        request: Request,
        limit: int = 120,
        before_id: int = 0,
        after_id: int = 0,
        channel: str = "",
    ) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        cid = bridge.parse_conv(conv_id)
        conv = bridge.conv_row(cid) if cid else None
        if not _can_access_conv(bridge, user, conv):
            return JSONResponse({"ok": False, "error": "无权查看该会话"}, status_code=403)

        lim = max(1, min(int(limit), 300))
        ka_mark = getattr(bridge, "KEEPALIVE_MARK", '{"keepalive": true}')
        is_super = _is_zwt(user)
        is_sys_conv = cid in ("ctrl", "main") or bridge.is_main_node_id(cid) or bridge.is_worker_node_id(cid)

        # 避免把旧版 main 的历史孤儿告警混进独立总控 ctrl；仅当 ctrl 尚无任何记录时才回退兼容
        if cid == "ctrl" and is_super:
            has_ctrl_own = store.one(
                "SELECT 1 AS ok FROM messages WHERE conv='ctrl' AND IFNULL(extra,'') != ? LIMIT 1",
                (ka_mark,),
            )
            if has_ctrl_own is None:
                conv_clause = "conv IN ('ctrl','main')"
                conv_params: tuple[Any, ...] = ()
            else:
                conv_clause = "conv=?"
                conv_params = ("ctrl",)
        else:
            conv_clause = "conv=?"
            conv_params = (cid,)

        counts = {"human": 0, "agent_dm": 0, "agent_group": 0, "system": 0, "collab": 0, "all": 0}
        for cr in store.q(
            f"SELECT IFNULL(chat_type,'private') AS ct, COUNT(*) AS n FROM messages "
            f"WHERE {conv_clause} AND IFNULL(extra,'') != ? GROUP BY ct",
            (*conv_params, ka_mark),
        ):
            ct = cr["ct"] or "private"
            cnt = int(cr["n"] or 0)
            if ct in ("private", "group", "supergroup", "channel"):
                counts["human"] += cnt
            elif ct == "agent_dm":
                counts["agent_dm"] += cnt
            elif ct == "agent_group":
                counts["agent_group"] += cnt
            else:
                counts["system"] += cnt
        counts["collab"] = counts["agent_dm"] + counts["agent_group"]
        counts["all"] = counts["human"] + counts["collab"] + counts["system"]

        if not is_super and not is_sys_conv:
            ch = "human"
        else:
            raw_ch = (channel or "").strip().lower()
            if not raw_ch or raw_ch == "default":
                ch = "all" if is_sys_conv else "human"
            else:
                ch = raw_ch

        if ch == "human":
            ch_sql = "AND IFNULL(chat_type,'private') IN ('private','group','supergroup','channel')"
        elif ch == "collab":
            ch_sql = "AND chat_type IN ('agent_dm','agent_group')"
        elif ch == "agent_dm":
            ch_sql = "AND chat_type='agent_dm'"
        elif ch == "agent_group":
            ch_sql = "AND chat_type='agent_group'"
        elif ch == "system":
            ch_sql = "AND IFNULL(chat_type,'private') NOT IN ('private','group','supergroup','channel','agent_dm','agent_group')"
        else:
            ch = "all"
            ch_sql = ""

        has_more = False
        if after_id > 0:
            rows = store.q(
                f"SELECT * FROM messages WHERE {conv_clause} AND IFNULL(extra,'') != ? {ch_sql} AND id>? "
                f"ORDER BY id ASC LIMIT ?",
                (*conv_params, ka_mark, int(after_id), lim),
            )
        elif before_id > 0:
            raw_rows = store.q(
                f"SELECT * FROM messages WHERE {conv_clause} AND IFNULL(extra,'') != ? {ch_sql} AND id<? "
                f"ORDER BY id DESC LIMIT ?",
                (*conv_params, ka_mark, int(before_id), lim + 1),
            )
            has_more = len(raw_rows) > lim
            rows = list(reversed(raw_rows[:lim]))
        else:
            raw_rows = store.q(
                f"SELECT * FROM messages WHERE {conv_clause} AND IFNULL(extra,'') != ? {ch_sql} "
                f"ORDER BY id DESC LIMIT ?",
                (*conv_params, ka_mark, lim + 1),
            )
            has_more = len(raw_rows) > lim
            rows = list(reversed(raw_rows[:lim]))

        # 计算该通道最新 120 条摘要签名，供增量轮询秒级感知编辑或删除
        sig_rows = store.q(
            f"SELECT id, LENGTH(IFNULL(text,'')) AS tl, IFNULL(delivered,1) AS dl FROM messages "
            f"WHERE {conv_clause} AND IFNULL(extra,'') != ? {ch_sql} ORDER BY id DESC LIMIT 120",
            (*conv_params, ka_mark),
        )
        win_sig = hashlib.md5(
            "|".join(f"{sr['id']}:{sr['tl']}:{sr['dl']}" for sr in sig_rows).encode("utf-8")
        ).hexdigest()[:12]

        conv_disp_name = bridge.conv_name(conv)
        msgs = [_serialize_conv_msg_row(conv_disp_name, r) for r in rows if not bridge.is_keepalive(r)]
        return JSONResponse({
            "ok": True,
            "conv": _serialize_conv(bridge, conv),
            "channel": ch,
            "channel_counts": counts if is_super else {"human": counts["human"], "collab": 0, "system": 0, "all": counts["human"]},
            "has_more": has_more,
            "window_sig": win_sig,
            "messages": msgs,
        })

    @app.post("/web/api/convs/{conv_id}/messages")
    async def web_send_conv_message(conv_id: str, request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        cid = bridge.parse_conv(conv_id)
        conv = bridge.conv_row(cid) if cid else None
        if not _can_access_conv(bridge, user, conv):
            return JSONResponse({"ok": False, "error": "无权向该会话发消息"}, status_code=403)
        if conv["status"] != "open":
            return JSONResponse({"ok": False, "error": "该会话已关闭，请先点击重开"}, status_code=400)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)

        text = str((body or {}).get("text") or "").strip()
        file_ids = [str(x).strip() for x in ((body or {}).get("file_ids") or []) if str(x).strip()]
        reply_to_id = int((body or {}).get("reply_to_id") or 0)
        if not text and not file_ids:
            return JSONResponse({"ok": False, "error": "消息内容不能为空"}, status_code=400)

        target_cid = "ctrl" if (cid == "main" and bridge.ctrl_is_active()) else cid
        if reply_to_id > 0 and not text.startswith("> [引用 #"):
            qrow = store.one("SELECT id, user_name, outgoing, text FROM messages WHERE id=? AND conv=?", (reply_to_id, target_cid))
            if qrow is not None:
                q_author = (qrow["user_name"] or ("AI" if qrow["outgoing"] else "用户")).strip()[:20]
                q_clean = re.sub(r"^> \[引用 #[^\n]+\n*", "", qrow["text"] or "").strip()
                q_snip = re.sub(r"\s+", " ", q_clean)[:64] or "[附件]"
                text = f"> [引用 #{reply_to_id} {q_author}] {q_snip}\n\n{text}".strip()

        admin_dms = bridge.admin_chats()
        chat_id_val = (admin_dms[0] if admin_dms else 0) if _is_zwt(user) else int(user["tg_owner"] or 0)
        sender_name = (user["display_name"] or user["username"]) + " (Web)"

        inserted_ids = []
        if file_ids:
            for idx, fid in enumerate(file_ids):
                frow = store.one("SELECT id FROM files WHERE id=?", (fid,))
                if frow is None:
                    continue
                store.run("UPDATE files SET conv=? WHERE id=?", (target_cid, fid))
                msg_txt = text if idx == len(file_ids) - 1 else ""
                mid = bridge.post(
                    target_cid,
                    conv=target_cid,
                    chat_id=chat_id_val,
                    chat_type="private",
                    chat_title="Web控制台",
                    user_id=0 if _is_zwt(user) else int(user["tg_owner"] or 0),
                    user_name=sender_name,
                    text=msg_txt,
                    file_id=fid,
                    wake=1 if idx == len(file_ids) - 1 else 0,
                )
                inserted_ids.append(mid)
        else:
            mid = bridge.post(
                target_cid,
                conv=target_cid,
                chat_id=chat_id_val,
                chat_type="private",
                chat_title="Web控制台",
                user_id=0 if _is_zwt(user) else int(user["tg_owner"] or 0),
                user_name=sender_name,
                text=text,
                wake=1,
            )
            inserted_ids.append(mid)

        if not bridge.is_system_conv_id(target_cid):
            bridge.reset_dm_streaks_for(target_cid)
        conv_disp = bridge.conv_name(bridge.conv_row(target_cid) or conv)
        created_msgs = []
        for mid_i in inserted_ids:
            mr = store.one("SELECT * FROM messages WHERE id=?", (mid_i,))
            if mr is not None:
                created_msgs.append(_serialize_conv_msg_row(conv_disp, mr))
        return JSONResponse({"ok": True, "message_ids": inserted_ids, "messages": created_msgs})

    @app.patch("/web/api/messages/{msg_id}")
    async def web_edit_message(msg_id: int, request: Request) -> JSONResponse:
        """在线修改 TG / 会话对话记录（同步更新数据库与已缓存补发包，并尽力同步编辑 Telegram 消息）。"""
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        mrow = store.one("SELECT * FROM messages WHERE id=?", (msg_id,))
        if mrow is None:
            return JSONResponse({"ok": False, "error": "消息不存在"}, status_code=404)
        conv = bridge.conv_row(mrow["conv"] or mrow["target"] or "")
        if not _can_access_conv(bridge, user, conv):
            return JSONResponse({"ok": False, "error": "无权编辑该消息"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        new_text = str((body or {}).get("text") or "")

        extra_str = mrow["extra"] or ""
        if extra_str and not bridge.is_keepalive(mrow):
            try:
                ep = json.loads(extra_str)
                if isinstance(ep, dict) and "text" in ep:
                    ep["text"] = (bridge.conv_prefix(conv) if mrow["outgoing"] and conv else "") + new_text
                    extra_str = json.dumps(ep, ensure_ascii=False)
            except Exception:
                pass

        store.run("UPDATE messages SET text=?, extra=? WHERE id=?", (new_text, extra_str, msg_id))
        tg_synced = False
        if int(mrow["tg_msg_id"] or 0) > 0 and int(mrow["chat_id"] or 0) != 0 and int(mrow["outgoing"] or 0) == 1 and bridge.TG_TOKEN:
            tg_text = (bridge.conv_prefix(conv) if conv else "") + new_text
            res_tg = await bridge.tg.try_call("editMessageText", chat_id=int(mrow["chat_id"]), message_id=int(mrow["tg_msg_id"]), text=tg_text[:4000])
            tg_synced = bool(res_tg)
        return JSONResponse({"ok": True, "id": msg_id, "text": new_text, "tg_synced": tg_synced})

    @app.delete("/web/api/messages/{msg_id}")
    async def web_delete_message(msg_id: int, request: Request) -> JSONResponse:
        """删除单条对话记录（从 SQLite 移除，若关联了 Telegram 消息一并尝试撤回删除）。"""
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        mrow = store.one("SELECT * FROM messages WHERE id=?", (msg_id,))
        if mrow is None:
            return JSONResponse({"ok": False, "error": "消息不存在"}, status_code=404)
        conv = bridge.conv_row(mrow["conv"] or mrow["target"] or "")
        if not _can_access_conv(bridge, user, conv):
            return JSONResponse({"ok": False, "error": "无权删除该消息"}, status_code=403)
        tg_deleted = False
        if int(mrow["tg_msg_id"] or 0) > 0 and int(mrow["chat_id"] or 0) != 0 and bridge.TG_TOKEN:
            store.run("DELETE FROM tgmsgs WHERE chat_id=? AND tg_msg_id=?", (int(mrow["chat_id"]), int(mrow["tg_msg_id"])))
            res_del = await bridge.tg.try_call("deleteMessage", chat_id=int(mrow["chat_id"]), message_id=int(mrow["tg_msg_id"]))
            tg_deleted = bool(res_del)
        store.run("DELETE FROM messages WHERE id=?", (msg_id,))
        bridge.mark_menu_dirty()
        return JSONResponse({"ok": True, "id": msg_id, "tg_deleted": tg_deleted})

    # ---------------------------------------------------------------- Agent 协作群直看、插话发言、编辑与删除

    @app.post("/web/api/groups")
    async def web_create_group(request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if not _is_zwt(user):
            return JSONResponse({"ok": False, "error": "仅超级管理员 zwt 可新建协作群"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        gname = re.sub(r"\s+", " ", str((body or {}).get("name") or "")).strip()[:20] or "协作群"
        topic = str((body or {}).get("topic") or "").strip()[:500]
        welcome = str((body or {}).get("welcome") or "").strip()[:1000]
        conv_members = [bridge.parse_conv(x) for x in _parse_id_list((body or {}).get("members")) if bridge.parse_conv(x)]
        web_users_list = [u for u in _parse_id_list((body or {}).get("web_users")) if u and u != SUPERADMIN_USER]

        gnum = int((store.one("SELECT IFNULL(MAX(num),0) AS n FROM agent_groups") or {"n": 0})["n"] or 0) + 1
        gid = f"g{gnum}"
        store.run(
            "INSERT INTO agent_groups(id,num,name,topic,creator,owner,status,streak,streak_ts,created) VALUES(?,?,?,?,?,0,'open',0,0.0,?)",
            (gid, gnum, gname, topic, "zwt", _now()),
        )
        valid_convs = []
        for cid_m in conv_members:
            crow = bridge.conv_row(cid_m)
            if crow is not None and crow["status"] != "deleted":
                store.run("INSERT OR IGNORE INTO agent_group_members(group_id,conv,joined) VALUES(?,?,?)", (gid, cid_m, _now()))
                valid_convs.append(cid_m)
        granted_web = []
        for wu_name in web_users_list:
            urow = store.one("SELECT * FROM web_users WHERE username=?", (wu_name,))
            if urow is not None:
                cur_g = _parse_id_list(urow["allowed_groups"] or "[]")
                if gid not in cur_g:
                    cur_g.append(gid)
                store.run("UPDATE web_users SET allowed_groups=? WHERE username=?", (json.dumps(cur_g), wu_name))
                granted_web.append(wu_name)
        if welcome:
            sender_lbl = "👑 zwt (管理员)"
            store.run(
                "INSERT INTO agent_group_messages(group_id,sender_conv,sender_name,text,mentions,ts) VALUES(?,?,?,?,?,?)",
                (gid, "admin", sender_lbl, welcome, json.dumps(valid_convs), _now()),
            )
            header_title = f"{gid}「{gname}」 成员:{','.join(['zwt', *granted_web, *valid_convs])}"
            for m_cid in valid_convs:
                bridge.post(
                    m_cid,
                    conv=m_cid,
                    chat_id=0,
                    chat_type="agent_group",
                    chat_title=header_title,
                    user_id=0,
                    user_name=sender_lbl,
                    text=welcome,
                    mention=1,
                    outgoing=0,
                    delivered=1,
                    sender="web_admin",
                    wake=1,
                )
        return JSONResponse({"ok": True, "group_id": gid, "members": valid_convs, "web_users": granted_web})

    @app.get("/web/api/groups/{group_id}/messages")
    async def web_get_group_messages(
        group_id: str,
        request: Request,
        limit: int = 150,
        before_id: int = 0,
        after_id: int = 0,
    ) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        gid = bridge.parse_group(group_id)
        grow = bridge.group_row(gid) if gid else None
        if grow is None:
            return JSONResponse({"ok": False, "error": "协作群不存在"}, status_code=404)
        if not _can_access_group(user, grow):
            return JSONResponse({"ok": False, "error": "无权查看该协作群"}, status_code=403)

        lim = max(1, min(int(limit), 300))
        has_more = False
        if after_id > 0:
            rows = store.q(
                "SELECT * FROM agent_group_messages WHERE group_id=? AND id>? ORDER BY id ASC LIMIT ?",
                (gid, int(after_id), lim),
            )
        elif before_id > 0:
            raw_rows = store.q(
                "SELECT * FROM agent_group_messages WHERE group_id=? AND id<? ORDER BY id DESC LIMIT ?",
                (gid, int(before_id), lim + 1),
            )
            has_more = len(raw_rows) > lim
            rows = list(reversed(raw_rows[:lim]))
        else:
            raw_rows = store.q(
                "SELECT * FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT ?",
                (gid, lim + 1),
            )
            has_more = len(raw_rows) > lim
            rows = list(reversed(raw_rows[:lim]))

        sig_rows = store.q(
            "SELECT id, LENGTH(IFNULL(text,'')) AS tl FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT 120",
            (gid,),
        )
        win_sig = hashlib.md5("|".join(f"{sr['id']}:{sr['tl']}" for sr in sig_rows).encode("utf-8")).hexdigest()[:12]

        mems = bridge.group_members(gid)
        web_mems = _group_web_members(store, gid)
        member_details = []
        for m in mems:
            mc = bridge.conv_row(m)
            if mc is not None:
                st = bridge.conv_state(mc)["state"]
                member_details.append({"id": m, "name": bridge.conv_name(mc), "state": st})
        msgs = [_serialize_group_msg_row(r) for r in rows]
        return JSONResponse({
            "ok": True,
            "group": {
                "id": grow["id"],
                "name": grow["name"] or grow["id"],
                "topic": grow["topic"] or "",
                "status": grow["status"],
                "members": member_details,
                "web_members": web_mems,
            },
            "has_more": has_more,
            "window_sig": win_sig,
            "messages": msgs,
        })

    @app.post("/web/api/groups/{group_id}/messages")
    async def web_send_group_message(group_id: str, request: Request) -> JSONResponse:
        """管理员或授权 Web 用户直接在协作群发言（支持附带图片/文件，支持唤醒全群、指定 Agent 或静默群聊）。"""
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        gid = bridge.parse_group(group_id)
        grow = bridge.group_row(gid) if gid else None
        if grow is None or grow["status"] != "open":
            return JSONResponse({"ok": False, "error": "协作群不存在或已关闭"}, status_code=404)
        if not _can_access_group(user, grow):
            return JSONResponse({"ok": False, "error": "无权在该协作群发言"}, status_code=403)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        text = str((body or {}).get("text") or "").strip()
        file_ids = [str(x).strip() for x in ((body or {}).get("file_ids") or []) if str(x).strip()]
        raw_mentions = (body or {}).get("mentions")
        reply_to_id = int((body or {}).get("reply_to_id") or 0)

        if reply_to_id > 0 and not text.startswith("> [引用 #"):
            qrow = store.one("SELECT id, sender_name, text FROM agent_group_messages WHERE id=? AND group_id=?", (reply_to_id, gid))
            if qrow is not None:
                q_author = (qrow["sender_name"] or "成员").strip()[:20]
                q_clean = re.sub(r"^> \[引用 #[^\n]+\n*", "", qrow["text"] or "").strip()
                q_snip = re.sub(r"\s+", " ", q_clean)[:64] or "[附件]"
                text = f"> [引用 #{reply_to_id} {q_author}] {q_snip}\n\n{text}".strip()

        file_notes = []
        for fid in file_ids:
            frow = store.one("SELECT id FROM files WHERE id=?", (fid,))
            if frow is not None:
                store.run("UPDATE files SET conv='' WHERE id=?", (fid,))
                file_notes.append(bridge.file_note(fid))
        full_text = "\n".join(p for p in [text, *file_notes] if p).strip()
        if not full_text:
            return JSONResponse({"ok": False, "error": "发言内容不能为空"}, status_code=400)

        mems = bridge.group_members(gid)
        web_mems = _group_web_members(store, gid)
        if raw_mentions is None or "all" in [str(x).lower() for x in raw_mentions]:
            wake_set = set(mems)
            mention_record = ["all"]
        else:
            wake_set = {str(x).strip().lower() for x in raw_mentions if str(x).strip().lower() in mems}
            mention_record = sorted(wake_set)

        store.run("UPDATE agent_groups SET streak=0, streak_ts=? WHERE id=?", (_now(), gid))
        sender_conv_val = "admin" if _is_zwt(user) else f"web:{user['username']}"
        sender_label = f"👑 {user['display_name'] or user['username']} (管理员)" if _is_zwt(user) else f"👤 {user['display_name'] or user['username']} (Web)"
        gm_id = store.run(
            "INSERT INTO agent_group_messages(group_id,sender_conv,sender_name,text,mentions,ts) VALUES(?,?,?,?,?,?)",
            (gid, sender_conv_val, sender_label, full_text, json.dumps(mention_record, ensure_ascii=False), _now()),
        )
        header_title = f"{bridge.group_tag(grow)} 成员:{','.join([*web_mems, *mems])}（在本群回复请调用 send_group_message(group=\"{gid}\", text=...)）"
        for m_cid in mems:
            if file_ids:
                for idx, fid in enumerate(file_ids):
                    is_last = idx == len(file_ids) - 1
                    bridge.post(
                        m_cid,
                        conv=m_cid,
                        chat_id=0,
                        chat_type="agent_group",
                        chat_title=header_title,
                        user_id=0,
                        user_name=sender_label,
                        text=full_text if is_last else "",
                        file_id=fid,
                        mention=int(m_cid in wake_set),
                        outgoing=0,
                        delivered=1,
                        sender=sender_conv_val,
                        wake=(1 if m_cid in wake_set else 0) if is_last else 0,
                    )
            else:
                bridge.post(
                    m_cid,
                    conv=m_cid,
                    chat_id=0,
                    chat_type="agent_group",
                    chat_title=header_title,
                    user_id=0,
                    user_name=sender_label,
                    text=full_text,
                    mention=int(m_cid in wake_set),
                    outgoing=0,
                    delivered=1,
                    sender=sender_conv_val,
                    wake=1 if m_cid in wake_set else 0,
                )
        gmrow = store.one("SELECT * FROM agent_group_messages WHERE id=?", (gm_id,))
        return JSONResponse({
            "ok": True,
            "id": gm_id,
            "woke": sorted(wake_set),
            "message": _serialize_group_msg_row(gmrow) if gmrow else None,
        })

    @app.patch("/web/api/group-messages/{gm_id}")
    async def web_edit_group_message(gm_id: int, request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        gmrow = store.one("SELECT * FROM agent_group_messages WHERE id=?", (gm_id,))
        if gmrow is None:
            return JSONResponse({"ok": False, "error": "消息不存在"}, status_code=404)
        if not _is_zwt(user) and gmrow["sender_conv"] != f"web:{user['username']}":
            return JSONResponse({"ok": False, "error": "无权编辑他人群记录"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        new_text = str((body or {}).get("text") or "")
        store.run("UPDATE agent_group_messages SET text=? WHERE id=?", (new_text, gm_id))
        return JSONResponse({"ok": True, "id": gm_id, "text": new_text})

    @app.delete("/web/api/group-messages/{gm_id}")
    async def web_delete_group_message(gm_id: int, request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        gmrow = store.one("SELECT * FROM agent_group_messages WHERE id=?", (gm_id,))
        if gmrow is None:
            return JSONResponse({"ok": False, "error": "消息不存在"}, status_code=404)
        if not _is_zwt(user) and gmrow["sender_conv"] != f"web:{user['username']}":
            return JSONResponse({"ok": False, "error": "无权删除他人群记录"}, status_code=403)
        store.run("DELETE FROM agent_group_messages WHERE id=?", (gm_id,))
        return JSONResponse({"ok": True, "id": gm_id})

    # ---------------------------------------------------------------- 实时 SSE 增量脉冲（零闪烁推送）

    @app.get("/web/api/events")
    async def web_sse_events(request: Request, conv: str = "", group: str = "", once: int = 0) -> Response:
        user = _current_web_user(store, request)
        if user is None:
            return PlainTextResponse("unauthorized", status_code=401)

        cid = bridge.parse_conv(conv) if conv else ""
        if cid:
            crow = bridge.conv_row(cid)
            if not _can_access_conv(bridge, user, crow):
                cid = ""
        gid = bridge.parse_group(group) if group else ""
        if gid:
            grow = bridge.group_row(gid)
            if not _can_access_group(user, grow):
                gid = ""

        def _snapshot() -> dict[str, Any]:
            m_stat = store.one("SELECT IFNULL(MAX(id),0) AS mx, COUNT(*) AS cnt FROM messages") or {"mx": 0, "cnt": 0}
            g_stat = store.one("SELECT IFNULL(MAX(id),0) AS mx, COUNT(*) AS cnt FROM agent_group_messages") or {"mx": 0, "cnt": 0}
            t_stat = store.one("SELECT IFNULL(MAX(updated_ts),0) AS ts FROM agent_traces") or {"ts": 0}
            snap: dict[str, Any] = {
                "msg_max": int(m_stat["mx"] or 0),
                "msg_cnt": int(m_stat["cnt"] or 0),
                "grp_max": int(g_stat["mx"] or 0),
                "grp_cnt": int(g_stat["cnt"] or 0),
                "trace_ts": round(float(t_stat["ts"] or 0), 2),
            }
            if cid:
                c_stat = store.one(
                    "SELECT IFNULL(MAX(id),0) AS mx, COUNT(*) AS cnt, IFNULL(SUM(LENGTH(IFNULL(text,''))),0) AS tlen FROM messages WHERE conv=?",
                    (cid,),
                ) or {"mx": 0, "cnt": 0, "tlen": 0}
                cr = bridge.conv_row(cid)
                snap["active_conv"] = {
                    "id": cid,
                    "max_id": int(c_stat["mx"] or 0),
                    "cnt": int(c_stat["cnt"] or 0),
                    "tlen": int(c_stat["tlen"] or 0),
                    "trace": bridge.trace_one_liner(cid) if cr else "",
                    "state": bridge.conv_state(cr)["state"] if cr else "",
                }
            if gid:
                gr_stat = store.one(
                    "SELECT IFNULL(MAX(id),0) AS mx, COUNT(*) AS cnt, IFNULL(SUM(LENGTH(IFNULL(text,''))),0) AS tlen FROM agent_group_messages WHERE group_id=?",
                    (gid,),
                ) or {"mx": 0, "cnt": 0, "tlen": 0}
                snap["active_group"] = {
                    "id": gid,
                    "max_id": int(gr_stat["mx"] or 0),
                    "cnt": int(gr_stat["cnt"] or 0),
                    "tlen": int(gr_stat["tlen"] or 0),
                }
            return snap

        async def _stream():
            last_key = ""
            started = _now()
            last_ping = started
            while True:
                snap = _snapshot()
                cur_key = json.dumps(snap, sort_keys=True, ensure_ascii=False)
                if cur_key != last_key:
                    last_key = cur_key
                    yield f"event: sync\ndata: {cur_key}\n\n"
                    last_ping = _now()
                    if once:
                        break
                elif _now() - last_ping >= 12.0:
                    yield ": keepalive\n\n"
                    last_ping = _now()
                if once or (_now() - started >= 52.0):
                    break
                if await request.is_disconnected():
                    break
                await asyncio.sleep(0.6)

        return StreamingResponse(
            _stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ---------------------------------------------------------------- 零依赖高兼容二进制文件/图片上传与预览（拖拽 / 粘贴 / 手机选图）

    @app.post("/web/api/upload")
    async def web_upload_file(request: Request, conv: str = "") -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        raw_name = urllib.parse.unquote(request.headers.get("x-file-name") or "upload.bin")
        raw_mime = (request.headers.get("x-file-mime") or request.headers.get("content-type") or "").split(";")[0].strip()
        data = await request.body()
        if not data:
            return JSONResponse({"ok": False, "error": "上传文件内容为空"}, status_code=400)
        if len(data) > 50 * 1024 * 1024:
            return JSONResponse({"ok": False, "error": "单个文件不能超过 50MB"}, status_code=413)

        file_id = "f_" + secrets.token_hex(5)
        clean_fn = re.sub(r"[\\/\x00-\x1f]", "_", raw_name).strip()[:100] or "file.bin"
        safe_disk = re.sub(r"[^\w.\-]", "_", clean_fn)[:80] or "file.bin"
        path = bridge.DATA / "files" / f"{file_id}_{safe_disk}"
        path.write_bytes(data)
        mime, _ = _detect_mime_and_image(clean_fn, raw_mime)
        cid = bridge.parse_conv(conv) if conv else ""
        store.run(
            "INSERT INTO files(id,chat_id,tg_file_id,name,size,mime,path,ts,conv) VALUES(?,?,?,?,?,?,?,?,?)",
            (file_id, 0, "", clean_fn, len(data), mime, str(path), _now(), cid),
        )
        return JSONResponse({"ok": True, "file": _serialize_file(store, file_id, bridge=bridge)})

    @app.get("/web/api/files/{file_id}")
    async def web_serve_file(file_id: str, request: Request, sig: str = "", download: int = 0) -> Response:
        user = _current_web_user(store, request)
        sig_valid = bool(sig and hmac.compare_digest(sig, _web_file_sig(bridge, file_id)))
        if user is None and not sig_valid:
            return PlainTextResponse("unauthorized", status_code=401)
        frow = store.one("SELECT * FROM files WHERE id=?", (file_id,))
        disk_path = _resolve_file_disk_path(bridge, frow)
        if frow is None or disk_path is None:
            return PlainTextResponse("not found", status_code=404)
        if not sig_valid and not _can_user_read_file(bridge, store, user, frow):
            return PlainTextResponse("forbidden", status_code=403)
        fname = frow["name"] or file_id
        mime, _ = _detect_mime_and_image(fname, frow["mime"] or "")
        return FileResponse(
            disk_path,
            media_type=mime,
            headers=_build_file_headers(fname, file_id, mime, force_download=bool(download)),
        )

    @app.get("/web/api/outbox-file")
    async def web_serve_outbox_file(
        request: Request,
        path_sig: str = "",
        p: str = "",
        fn: str = "",
        download: int = 0,
    ) -> Response:
        safe_name = Path(p).name
        if not safe_name:
            return PlainTextResponse("not found", status_code=404)
        cand = bridge.DATA / "outbox" / safe_name
        sig_new = _outbox_sig(bridge, safe_name)
        sig_legacy = hashlib.sha256(str(cand).encode("utf-8")).hexdigest()[:16]
        sig_ok = bool(path_sig) and (
            hmac.compare_digest(path_sig, sig_new) or hmac.compare_digest(path_sig, sig_legacy)
        )
        user = _current_web_user(store, request)
        if user is None and not sig_ok:
            return PlainTextResponse("unauthorized", status_code=401)
        if not sig_ok or not cand.exists():
            return PlainTextResponse("not found", status_code=404)
        orig_name = Path(fn).name if fn else (safe_name.split("_", 1)[1] if "_" in safe_name else safe_name)
        mime, _ = _detect_mime_and_image(orig_name)
        return FileResponse(
            cand,
            media_type=mime,
            headers=_build_file_headers(orig_name, "outbox_file", mime, force_download=bool(download)),
        )
