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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response

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


def _can_access_conv(bridge, user, conv) -> bool:
    if conv is None or conv["status"] == "deleted":
        return False
    if _is_zwt(user):
        return True
    if bridge.is_system_conv_id(conv["id"]):
        return False
    owner = int(user["tg_owner"] or 0)
    return owner != 0 and bridge.conv_owner(conv) == owner


def _serialize_file(store, file_id: str) -> dict[str, Any] | None:
    if not file_id:
        return None
    frow = store.one("SELECT * FROM files WHERE id=?", (file_id,))
    if frow is None:
        return None
    mime = frow["mime"] or "application/octet-stream"
    return {
        "file_id": frow["id"],
        "name": frow["name"] or frow["id"],
        "size": int(frow["size"] or 0),
        "mime": mime,
        "is_image": mime.startswith("image/"),
        "url": f"/web/api/files/{frow['id']}",
    }


def _extract_outbox_file(text: str, extra: str) -> dict[str, Any] | None:
    if not extra:
        return None
    try:
        pay = json.loads(extra)
    except Exception:
        return None
    if isinstance(pay, dict) and pay.get("kind") == "file" and pay.get("file"):
        p = Path(str(pay["file"]))
        if p.exists():
            fname = str(pay.get("filename") or p.name)
            mime = mimetypes.guess_type(fname)[0] or "application/octet-stream"
            tok = hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:16]
            return {
                "file_id": f"out_{tok}",
                "name": fname,
                "size": p.stat().st_size,
                "mime": mime,
                "is_image": mime.startswith("image/"),
                "url": f"/web/api/outbox-file?path_sig={tok}&p={urllib.parse.quote(str(p.name))}",
            }
    return None


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
        f"请严格依据以下【完整无损档案】执行标准化重开，严禁遗漏任何参数或擅自更换模型：\n"
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
        rows = store.q("SELECT username, role, tg_owner, display_name, disabled, created, last_login, password_hash FROM web_users ORDER BY username='zwt' DESC, created")
        items = []
        for r in rows:
            owner_id = int(r["tg_owner"] or 0)
            chat_cnt = bridge.chat_count(owner_id) if owner_id != 0 else len(bridge.open_convs())
            items.append({
                "username": r["username"],
                "display_name": r["display_name"] or r["username"],
                "role": r["role"],
                "tg_owner": owner_id,
                "disabled": bool(int(r["disabled"] or 0)),
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
                "INSERT INTO web_users(username,password_hash,role,tg_owner,display_name,disabled,created) VALUES(?,?,?,?,?,?,?)",
                (uname, hash_password(pwd), "user", tg_owner, disp, disabled, _now()),
            )
            log.info("web user created by zwt: %s (owner=%s)", uname, tg_owner)
        else:
            tg_owner = int(raw_tg_owner) if str(raw_tg_owner or "").lstrip("-").isdigit() and int(raw_tg_owner) != 0 else int(existing["tg_owner"] or _next_virtual_owner(store))
            if pwd:
                if len(pwd) < 6:
                    return JSONResponse({"ok": False, "error": "重置密码至少 6 位"}, status_code=400)
                store.run(
                    "UPDATE web_users SET password_hash=?, display_name=?, tg_owner=?, disabled=? WHERE username=?",
                    (hash_password(pwd), disp, tg_owner, disabled, uname),
                )
            else:
                store.run(
                    "UPDATE web_users SET display_name=?, tg_owner=?, disabled=? WHERE username=?",
                    (disp, tg_owner, disabled, uname),
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
            my_rows = [
                r for r in store.q(
                    "SELECT * FROM convs WHERE owner=? AND status!='deleted' AND IFNULL(in_tg,1)=1 ORDER BY status!='open', num DESC",
                    (owner_id,),
                )
                if not bridge.is_system_conv_id(r["id"])
            ]
            for r in my_rows:
                convs_out.append(_serialize_conv(bridge, r))

        groups_out = []
        g_owner = 0 if is_super else int(user["tg_owner"] or 0)
        g_sql = "SELECT * FROM agent_groups WHERE status!='closed' ORDER BY num DESC" if is_super else "SELECT * FROM agent_groups WHERE status='open' AND owner=? ORDER BY num DESC"
        g_args = () if is_super else (g_owner,)
        for g in store.q(g_sql, g_args):
            mems = bridge.group_members(g["id"])
            last_gm = store.one("SELECT text, sender_name, ts FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT 1", (g["id"],))
            msg_cnt = store.one("SELECT COUNT(*) AS n FROM agent_group_messages WHERE group_id=?", (g["id"],))["n"]
            groups_out.append({
                "id": g["id"],
                "name": g["name"] or g["id"],
                "topic": g["topic"] or "",
                "status": g["status"],
                "members": mems,
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

        if cid == "ctrl":
            if not _is_zwt(user):
                return JSONResponse({"ok": False, "error": "仅 zwt 可重开总控"}, status_code=403)
            op_id = bridge.ensure_controller_alive(force=True)
            return JSONResponse({"ok": True, "routed_to": "bootstrap", "op_id": op_id or ""})

        if conv["status"] != "open":
            store.run("UPDATE convs SET status='open', closed=0 WHERE id=?", (cid,))
            conv = bridge.conv_row(cid)

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

    # ---------------------------------------------------------------- 消息读取、发送、在线编辑与删除

    @app.get("/web/api/convs/{conv_id}/messages")
    async def web_get_messages(conv_id: str, request: Request, limit: int = 120, before_id: int = 0) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        cid = bridge.parse_conv(conv_id)
        conv = bridge.conv_row(cid) if cid else None
        if not _can_access_conv(bridge, user, conv):
            return JSONResponse({"ok": False, "error": "无权查看该会话"}, status_code=403)

        lim = max(1, min(int(limit), 300))
        if cid in ("ctrl", "main") and _is_zwt(user):
            if before_id > 0:
                rows = list(reversed(store.q("SELECT * FROM messages WHERE conv IN ('ctrl','main') AND id<? ORDER BY id DESC LIMIT ?", (before_id, lim))))
            else:
                rows = list(reversed(store.q("SELECT * FROM messages WHERE conv IN ('ctrl','main') ORDER BY id DESC LIMIT ?", (lim,))))
        else:
            if before_id > 0:
                rows = list(reversed(store.q("SELECT * FROM messages WHERE conv=? AND id<? ORDER BY id DESC LIMIT ?", (cid, before_id, lim))))
            else:
                rows = list(reversed(store.q("SELECT * FROM messages WHERE conv=? ORDER BY id DESC LIMIT ?", (cid, lim))))

        msgs = []
        for r in rows:
            if bridge.is_keepalive(r):
                continue
            f_meta = _serialize_file(store, r["file_id"] or "") or _extract_outbox_file(r["text"] or "", r["extra"] or "")
            msgs.append({
                "id": r["id"],
                "ts": float(r["ts"] or 0),
                "chat_id": int(r["chat_id"] or 0),
                "chat_type": r["chat_type"] or "private",
                "user_name": r["user_name"] or "",
                "text": r["text"] or "",
                "outgoing": bool(int(r["outgoing"] or 0)),
                "delivered": bool(int(r["delivered"] if r["delivered"] is not None else 1)),
                "tg_msg_id": int(r["tg_msg_id"] or 0),
                "file": f_meta,
            })
        return JSONResponse({
            "ok": True,
            "conv": _serialize_conv(bridge, conv),
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
        if not text and not file_ids:
            return JSONResponse({"ok": False, "error": "消息内容不能为空"}, status_code=400)

        target_cid = "ctrl" if (cid == "main" and bridge.ctrl_is_active()) else cid
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
        return JSONResponse({"ok": True, "message_ids": inserted_ids})

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

    @app.get("/web/api/groups/{group_id}/messages")
    async def web_get_group_messages(group_id: str, request: Request, limit: int = 150) -> JSONResponse:
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        gid = bridge.parse_group(group_id)
        grow = bridge.group_row(gid) if gid else None
        if grow is None:
            return JSONResponse({"ok": False, "error": "协作群不存在"}, status_code=404)
        if not _is_zwt(user) and int(grow["owner"] or 0) != int(user["tg_owner"] or 0):
            return JSONResponse({"ok": False, "error": "无权查看该协作群"}, status_code=403)

        lim = max(1, min(int(limit), 300))
        rows = list(reversed(store.q("SELECT * FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT ?", (gid, lim))))
        mems = bridge.group_members(gid)
        member_details = []
        for m in mems:
            mc = bridge.conv_row(m)
            if mc is not None:
                st = bridge.conv_state(mc)["state"]
                member_details.append({"id": m, "name": bridge.conv_name(mc), "state": st})
        msgs = []
        for r in rows:
            try:
                mnt = json.loads(r["mentions"] or "[]")
            except Exception:
                mnt = []
            # 解析是否附带 [文件 f_xxx ...]
            f_hit = re.search(r"\b(f_[0-9a-f]{8,16})\b", r["text"] or "")
            f_meta = _serialize_file(store, f_hit.group(1)) if f_hit else None
            msgs.append({
                "id": r["id"],
                "sender_conv": r["sender_conv"] or "",
                "sender_name": r["sender_name"] or r["sender_conv"] or "",
                "text": r["text"] or "",
                "mentions": mnt if isinstance(mnt, list) else [],
                "ts": float(r["ts"] or 0),
                "file": f_meta,
            })
        return JSONResponse({
            "ok": True,
            "group": {
                "id": grow["id"],
                "name": grow["name"] or grow["id"],
                "topic": grow["topic"] or "",
                "status": grow["status"],
                "members": member_details,
            },
            "messages": msgs,
        })

    @app.post("/web/api/groups/{group_id}/messages")
    async def web_send_group_message(group_id: str, request: Request) -> JSONResponse:
        """管理员直接在 Agent 协作群发言（支持附带图片/文件，支持唤醒全群或指定成员）。"""
        user = _current_web_user(store, request)
        if user is None:
            return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
        gid = bridge.parse_group(group_id)
        grow = bridge.group_row(gid) if gid else None
        if grow is None or grow["status"] != "open":
            return JSONResponse({"ok": False, "error": "协作群不存在或已关闭"}, status_code=404)
        if not _is_zwt(user) and int(grow["owner"] or 0) != int(user["tg_owner"] or 0):
            return JSONResponse({"ok": False, "error": "无权在该协作群发言"}, status_code=403)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "请求格式错误"}, status_code=400)
        text = str((body or {}).get("text") or "").strip()
        file_ids = [str(x).strip() for x in ((body or {}).get("file_ids") or []) if str(x).strip()]
        raw_mentions = (body or {}).get("mentions")

        file_notes = []
        for fid in file_ids:
            frow = store.one("SELECT id FROM files WHERE id=?", (fid,))
            if frow is not None:
                # 管理员在群里发的文件设为公共可读（conv=''） zodat 群内所有子 agent 都能调 get_file 读取！
                store.run("UPDATE files SET conv='' WHERE id=?", (fid,))
                file_notes.append(bridge.file_note(fid))
        full_text = "\n".join(p for p in [text, *file_notes] if p).strip()
        if not full_text:
            return JSONResponse({"ok": False, "error": "发言内容不能为空"}, status_code=400)

        mems = bridge.group_members(gid)
        if raw_mentions is None or "all" in [str(x).lower() for x in raw_mentions]:
            wake_set = set(mems)
            mention_record = ["all"]
        else:
            wake_set = {str(x).strip().lower() for x in raw_mentions if str(x).strip().lower() in mems}
            mention_record = sorted(wake_set)

        # 管理员亲自发言自动清零群防死循环计数，恢复流水线活力
        store.run("UPDATE agent_groups SET streak=0, streak_ts=? WHERE id=?", (_now(), gid))
        sender_label = f"👑 {user['display_name'] or user['username']} (管理员)" if _is_zwt(user) else f"{user['username']} (Web)"
        gm_id = store.run(
            "INSERT INTO agent_group_messages(group_id,sender_conv,sender_name,text,mentions,ts) VALUES(?,?,?,?,?,?)",
            (gid, "admin", sender_label, full_text, json.dumps(mention_record, ensure_ascii=False), _now()),
        )
        header_title = f"{bridge.group_tag(grow)} 成员:{','.join(mems)}"
        for m_cid in mems:
            # 若带了文件，给群内成员自动共享读取或已设 conv=''
            for fid in file_ids:
                bridge.post(
                    m_cid,
                    conv=m_cid,
                    chat_id=0,
                    chat_type="agent_group",
                    chat_title=header_title,
                    user_id=0,
                    user_name=sender_label,
                    text="",
                    file_id=fid,
                    mention=int(m_cid in wake_set),
                    outgoing=0,
                    delivered=1,
                    sender="web_admin",
                    wake=0,
                )
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
                sender="web_admin",
                wake=1 if m_cid in wake_set else 0,
            )
        return JSONResponse({"ok": True, "id": gm_id, "woke": sorted(wake_set)})

    @app.patch("/web/api/group-messages/{gm_id}")
    async def web_edit_group_message(gm_id: int, request: Request) -> JSONResponse:
        user = _current_web_user(store, request)
        if not _is_zwt(user):
            return JSONResponse({"ok": False, "error": "无权编辑群记录"}, status_code=403)
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
        if not _is_zwt(user):
            return JSONResponse({"ok": False, "error": "无权删除群记录"}, status_code=403)
        store.run("DELETE FROM agent_group_messages WHERE id=?", (gm_id,))
        return JSONResponse({"ok": True, "id": gm_id})

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
        mime = raw_mime if (raw_mime and raw_mime != "application/octet-stream") else (mimetypes.guess_type(clean_fn)[0] or "application/octet-stream")
        cid = bridge.parse_conv(conv) if conv else ""
        store.run(
            "INSERT INTO files(id,chat_id,tg_file_id,name,size,mime,path,ts,conv) VALUES(?,?,?,?,?,?,?,?,?)",
            (file_id, 0, "", clean_fn, len(data), mime, str(path), _now(), cid),
        )
        return JSONResponse({"ok": True, "file": _serialize_file(store, file_id)})

    @app.get("/web/api/files/{file_id}")
    async def web_serve_file(file_id: str, request: Request) -> Response:
        user = _current_web_user(store, request)
        if user is None:
            return PlainTextResponse("unauthorized", status_code=401)
        frow = store.one("SELECT * FROM files WHERE id=?", (file_id,))
        if frow is None or not Path(frow["path"]).exists():
            return PlainTextResponse("not found", status_code=404)
        if not _is_zwt(user):
            fc = bridge.conv_row(frow["conv"] or "") if frow["conv"] else None
            if fc is None or not _can_access_conv(bridge, user, fc):
                return PlainTextResponse("forbidden", status_code=403)
        mime = frow["mime"] or "application/octet-stream"
        disp = "inline" if mime.startswith(("image/", "text/", "application/pdf")) else "attachment"
        return FileResponse(
            frow["path"],
            media_type=mime,
            headers={"Content-Disposition": f"{disp}; filename*=UTF-8''{urllib.parse.quote(frow['name'] or file_id)}"},
        )

    @app.get("/web/api/outbox-file")
    async def web_serve_outbox_file(request: Request, path_sig: str = "", p: str = "") -> Response:
        user = _current_web_user(store, request)
        if user is None:
            return PlainTextResponse("unauthorized", status_code=401)
        safe_name = Path(p).name
        cand = bridge.DATA / "outbox" / safe_name
        expected = hashlib.sha256(str(cand).encode("utf-8")).hexdigest()[:16]
        if not safe_name or not hmac.compare_digest(path_sig, expected) or not cand.exists():
            return PlainTextResponse("not found", status_code=404)
        mime = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        return FileResponse(cand, media_type=mime)
