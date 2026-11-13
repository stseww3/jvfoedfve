#!/usr/bin/env python3
"""Cursor 云端 VM 实时动作/改文件/命令/思考/耗时追踪器 + 子 agent 第3/4层防断连守卫。

支持四种用法：
1. 自动安装钩子与守护进程（热加载进当前 VM 的 exec-daemon，无需重启 VM）：
   python3 agent_trace.py install http://173.249.205.165:8787
2. Cursor hooks.json 自动回调入口（由 exec-daemon 在每次命令/改文件/思考/MCP/退出时通过 stdin JSON 调用）：
   python3 agent_trace.py hook
3. 断线自愈长等待（替代裸 curl /wait，桥平滑重启或网络抖动自动重连不退出）：
   python3 agent_trace.py wait <agent_id> [bridge_url] [max_sec]
4. 手动状态查看或命令包装：
   python3 agent_trace.py status [bridge_url]
   python3 agent_trace.py run -- <cmd...>
"""

from __future__ import annotations

import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CURSOR_DIR = Path.home() / ".cursor"
CONFIG_PATH = CURSOR_DIR / "agent_trace_config.json"
STATE_PATH = CURSOR_DIR / "agent_trace_state.json"
LOCK_PATH = CURSOR_DIR / "agent_trace.lock"
PID_PATH = CURSOR_DIR / "agent_trace_daemon.pid"
HOOKS_PATH = CURSOR_DIR / "hooks.json"
TERMINALS_DIR = CURSOR_DIR / "projects" / "agent" / "terminals"

AGENT_RE = re.compile(r"\b([am]_[0-9a-f]{12,32})\b")
CONV_HINT_RE = re.compile(r"(?<![A-Za-z0-9])(c[1-9]\d{0,3})(?=[_\-/.\s]|$)", re.I)
SECRET_PATTERNS = [
    (re.compile(r"\b([am]_[0-9a-f]{6})[0-9a-f]{6,26}\b"), r"\1***"),
    (re.compile(r"\btgb_[A-Za-z0-9_\-]{8,}\b"), "tgb_***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]{8,}", re.I), r"\1***"),
    (re.compile(r"(password|passwd|token|secret|key)(\s*[=:]\s*)([^\s'\"&]+)", re.I), r"\1\2***"),
]

HOOK_EVENTS = [
    "preToolUse",
    "postToolUse",
    "postToolUseFailure",
    "beforeShellExecution",
    "afterShellExecution",
    "beforeReadFile",
    "afterFileEdit",
    "beforeMCPExecution",
    "afterMCPExecution",
    "afterAgentThought",
    "afterAgentResponse",
    "subagentStart",
    "subagentStop",
]


def scrub(text: str, limit: int = 240) -> str:
    if not text:
        return ""
    cleaned = " ".join(str(text).split())
    for pat, repl in SECRET_PATTERNS:
        cleaned = pat.sub(repl, cleaned)
    if len(cleaned) > limit:
        return cleaned[:limit] + "…"
    return cleaned


def load_config() -> dict[str, Any]:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"bridge_url": os.environ.get("BRIDGE_URL", "http://173.249.205.165:8787").rstrip("/")}


def save_config(cfg: dict[str, Any]) -> None:
    CURSOR_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


class StateLock:
    def __enter__(self) -> dict[str, Any]:
        CURSOR_DIR.mkdir(parents=True, exist_ok=True)
        self._fp = open(LOCK_PATH, "a+", encoding="utf-8")
        fcntl.flock(self._fp.fileno(), fcntl.LOCK_EX)
        try:
            if STATE_PATH.exists():
                self.data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            else:
                self.data = {}
        except Exception:
            self.data = {}
        self.data.setdefault("conv_to_agent", {})
        self.data.setdefault("sessions", {})
        return self.data

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            tmp = STATE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(STATE_PATH)
        except Exception:
            pass
        try:
            fcntl.flock(self._fp.fileno(), fcntl.LOCK_UN)
            self._fp.close()
        except Exception:
            pass


def post_json(url: str, payload: dict[str, Any], timeout: float = 0.9) -> dict[str, Any] | None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip().startswith("{") else {}
    except Exception:
        return None


def get_json(url: str, timeout: float = 1.8) -> dict[str, Any] | None:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def parse_json_maybe(val: Any) -> Any:
    if isinstance(val, str):
        s = val.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return val
    return val


def extract_agent_id(payload: dict[str, Any]) -> str:
    """只从权威输入源（MCP 调用参数、join 返回或 /wait 轮询命令）提取 a_xxx / m_xxx 身份，避免查日志输出时把别的聊天身份误绑到当前会话。"""
    candidates: list[str] = []
    event = str(payload.get("hook_event_name") or "")
    tname = str(payload.get("tool_name") or "")
    ti = parse_json_maybe(payload.get("tool_input"))
    if isinstance(ti, dict):
        if isinstance(ti.get("agent"), str):
            candidates.append(ti["agent"])
        args = ti.get("arguments")
        if isinstance(args, dict) and isinstance(args.get("agent"), str):
            candidates.append(args["agent"])
        cmd_s = str(ti.get("command") or "")
        if cmd_s and (is_wait_command(cmd_s) or "bind trace session" in cmd_s or "agent_trace.py" in cmd_s):
            candidates.append(cmd_s)
    elif isinstance(ti, str) and ("\"agent\"" in ti or is_wait_command(ti)):
        candidates.append(ti)
    raw_cmd = str(payload.get("command") or "")
    if raw_cmd and (is_wait_command(raw_cmd) or "bind trace session" in raw_cmd or "agent_trace.py" in raw_cmd):
        candidates.append(raw_cmd)
    # 仅在 join 调用返回时从输出提取新分发的身份
    is_join = (
        "join" in tname.lower()
        or (isinstance(ti, dict) and str(ti.get("toolName") or "") == "join")
    )
    if is_join and event in ("afterMCPExecution", "postToolUse"):
        for key in ("tool_output", "result", "output"):
            v = payload.get(key)
            if isinstance(v, str):
                candidates.append(v)
    for text in candidates:
        m = AGENT_RE.search(text)
        if m:
            return m.group(1)
    return ""


def extract_conv_hint(payload: dict[str, Any], ti: dict[str, Any]) -> str:
    """从工作目录、文件路径或命令参数里自动识别 c161 / c164 等聊天号，辅助把旧会话自动绑定回对应 agent。"""
    texts: list[str] = []
    for k in ("cwd", "file_path", "command"):
        if isinstance(payload.get(k), str):
            texts.append(payload[k])
    for k in ("working_directory", "cwd", "path", "file_path", "target_file", "command"):
        if isinstance(ti.get(k), str):
            texts.append(ti[k])
    for t in texts:
        # 优先匹配路径组件里的聊天号（如 /jvfoedfve-c165/、/c161_audit/、/tmp/c164_）
        for m in CONV_HINT_RE.finditer(t):
            cand = m.group(1).lower()
            num = int(cand[1:])
            if 1 <= num <= 9999:
                return cand
    return ""


def build_inbox_alert(bridge_url: str, agent_id: str) -> str:
    """每次 Shell 命令（或文件/普通工具）跑完时毫秒级顺带查收收件箱状态（不粘贴未脱敏外部正文，避免 GPT 模型误判为工具输出注入攻击而忽略！）。"""
    if not agent_id:
        return ""
    peek = get_json(
        f"{bridge_url}/trace/peek?agent={urllib.parse.quote(agent_id)}",
        timeout=0.9,
    )
    if not peek:
        return ""
    if peek.get("stopped"):
        note = str(peek.get("note") or "身份已停用").strip()
        return (
            f"[dais bridge hook] Your sub-agent identity ({agent_id[:8]}...) has been stopped ({note}). "
            "Stop all work and end your turn immediately."
        )
    if not peek.get("has_messages"):
        return ""
    cnt = int(peek.get("count") or 1)
    conv_s = str(peek.get("conv") or "")
    src = "Telegram user/admin" if peek.get("has_human") else "peer agent / main controller"
    return (
        f"[dais bridge hook] Chat {conv_s} has {cnt} unread incoming message(s) from {src} waiting in your inbox. "
        f"User responsiveness is top priority: before running further commands or edits, call dais `read_chat(agent=\"{agent_id}\", wait_sec=0)` "
        "now and reply via `send_message` (or `send_agent_message`)."
    )


def summarize_file_edit(payload: dict[str, Any], ti: dict[str, Any]) -> tuple[str, str]:
    path = (
        payload.get("file_path")
        or ti.get("path")
        or ti.get("file_path")
        or ti.get("target_file")
        or ""
    )
    snippet = ""
    delta = ""
    if isinstance(ti.get("new_string"), str):
        old_lines = len(str(ti.get("old_string") or "").splitlines())
        new_lines = len(ti["new_string"].splitlines())
        delta = f"+{new_lines}/-{old_lines}行"
        first_line = next((ln.strip() for ln in ti["new_string"].splitlines() if ln.strip()), "")
        snippet = scrub(first_line, 90)
    elif isinstance(ti.get("contents"), str):
        new_lines = len(ti["contents"].splitlines())
        delta = f"写入{new_lines}行"
        first_line = next((ln.strip() for ln in ti["contents"].splitlines() if ln.strip()), "")
        snippet = scrub(first_line, 90)
    elif isinstance(payload.get("edits"), list) and payload["edits"]:
        e0 = payload["edits"][0] if isinstance(payload["edits"][0], dict) else {}
        ns = str(e0.get("new_string") or e0.get("newText") or "")
        if ns:
            first_line = next((ln.strip() for ln in ns.splitlines() if ln.strip()), "")
            snippet = scrub(first_line, 90)
    short_path = str(path)
    if len(short_path) > 70:
        short_path = "…" + short_path[-69:]
    desc = f"改文件 {short_path}"
    if delta:
        desc += f" ({delta})"
    if snippet:
        desc += f": {snippet}"
    return str(path), desc


def is_wait_command(cmd: str) -> bool:
    return ("/wait" in cmd and ("curl " in cmd or "agent_trace.py wait" in cmd)) or "agent_trace.py wait" in cmd


def daemon_alive() -> bool:
    try:
        if not PID_PATH.exists():
            return False
        pid = int(PID_PATH.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", errors="replace")
        return "agent_trace.py" in cmdline and "daemon" in cmdline
    except Exception:
        return False


def ensure_daemon() -> None:
    if daemon_alive():
        return
    try:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "daemon"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def handle_hook() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        print("{}")
        return 0
    try:
        payload = json.loads(raw)
    except Exception:
        print("{}")
        return 0

    event = str(payload.get("hook_event_name") or "")
    cid = str(payload.get("conversation_id") or payload.get("session_id") or "")
    now_ts = time.time()
    cfg = load_config()
    bridge_url = cfg["bridge_url"]

    found_agent = extract_agent_id(payload)
    ti = parse_json_maybe(payload.get("tool_input"))
    if not isinstance(ti, dict):
        ti = {}
    conv_hint = extract_conv_hint(payload, ti)

    with StateLock() as st:
        if cid and found_agent:
            st["conv_to_agent"][cid] = found_agent
        agent_id = found_agent or (st["conv_to_agent"].get(cid, "") if cid else "")
        sess = st["sessions"].setdefault(cid or agent_id or "default", {})
        if agent_id:
            sess["agent_id"] = agent_id

        # 若该子 agent 已被停用，或在准备跑耗时工具前收件箱已有未读人类消息 -> 直接前置提醒/拦截！
        pre_alert_ctx = ""
        if event == "preToolUse" and agent_id and agent_id.startswith("a_"):
            peek_pre = get_json(
                f"{bridge_url}/trace/peek?agent={urllib.parse.quote(agent_id)}",
                timeout=0.9,
            )
            if peek_pre and peek_pre.get("stopped"):
                print(
                    json.dumps(
                        {
                            "permission": "deny",
                            "user_message": "【🛑 身份已停用】你的子 agent 已被父 agent 或主控停止回收，禁止再启动新命令或工具，请立即结束回合退出。",
                        },
                        ensure_ascii=False,
                    )
                )
                return 0
            tname_cur = str(payload.get("tool_name") or "")
            is_dais_call = (
                tname_cur.startswith("MCP:")
                or "dais" in tname_cur.lower()
                or tname_cur in ("read_chat", "send_message", "send_file", "get_file", "ask", "join", "send_agent_message", "send_group_message")
                or (tname_cur == "CallDynamicTool" and str(ti.get("namespace") or "") == "dais")
            )
            if peek_pre and peek_pre.get("has_messages") and not is_dais_call:
                cnt_p = int(peek_pre.get("count") or 1)
                conv_p = str(peek_pre.get("conv") or "")
                max_id = int(peek_pre.get("max_id") or 0)
                # 当收到人类/管理员 TG 未读消息，且当前正准备跑耗时 Shell/查找（非保存文件的 Write/StrReplace）时，直接首次硬阻断要求先秒回用户！
                if (
                    peek_pre.get("has_human")
                    and tname_cur not in ("Write", "StrReplace", "GetDynamicTools")
                    and int(sess.get("denied_msg_id") or 0) < max_id
                ):
                    sess["denied_msg_id"] = max_id
                    print(
                        json.dumps(
                            {
                                "permission": "deny",
                                "user_message": (
                                    f"[dais bridge priority gate] Chat {conv_p} has {cnt_p} unread Telegram message(s) from the user/admin (latest #{max_id}). "
                                    f"Call dais `read_chat(agent=\"{agent_id}\", wait_sec=0)` and send a quick `send_message` reply FIRST, then re-run this tool."
                                ),
                            },
                            ensure_ascii=False,
                        )
                    )
                    return 0
                pre_alert_ctx = (
                    f"[dais bridge hook] Chat {conv_p} has {cnt_p} unread incoming message(s) (latest #{max_id}). "
                    f"Immediately after this step completes, call dais `read_chat(agent=\"{agent_id}\", wait_sec=0)` and reply first."
                )

        # 第 4 层防断连：子 agent 试图结束回合时向桥查询身份是否仍有效，有效则当场拽回 read_chat
        if event == "subagentStop":
            if agent_id and agent_id.startswith("a_"):
                chk = get_json(
                    f"{bridge_url}/trace/check-active?agent={urllib.parse.quote(agent_id)}",
                    timeout=1.8,
                )
                if chk and chk.get("active"):
                    post_json(
                        f"{bridge_url}/trace/event",
                        {
                            "agent_id": agent_id,
                            "conversation_id": cid,
                            "event": "subagentStop_blocked",
                            "phase": "thinking",
                            "tool_name": "subagentStop",
                            "summary": "子 agent 试图结束回合，已被第4层 subagentStop 钩子当场拽回 read_chat",
                            "started_ts": now_ts,
                            "ts": now_ts,
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "followup_message": (
                                    f"【防断连钩子拦截】你的子 agent 身份仍然有效（聊天 {chk.get('conv', '')} 未被停用），"
                                    "管理员严禁子 agent 断开 MCP 或结束回合！"
                                    f"现在立刻调用 dais 的 read_chat(agent=\"{agent_id}\") 继续挂起等待消息，不要输出告别文字。"
                                )
                            },
                            ensure_ascii=False,
                        )
                    )
                    return 0
            print("{}")
            return 0

        phase = ""
        tool_name = str(payload.get("tool_name") or "")
        summary = ""
        detail: dict[str, Any] = {}
        duration_ms = int(float(payload.get("duration_ms") or payload.get("duration") or 0))
        started_ts = float(sess.get("started_ts") or now_ts)

        if event == "beforeShellExecution" or (event == "preToolUse" and tool_name == "Shell"):
            cmd = str(payload.get("command") or ti.get("command") or "")
            cwd = str(payload.get("cwd") or ti.get("working_directory") or ti.get("cwd") or "")
            if is_wait_command(cmd):
                phase = "idle_wait"
                tool_name = "wait"
                summary = "终端长等待新消息 (/wait)"
            else:
                phase = "shell"
                tool_name = "Shell"
                summary = f"执行命令: {scrub(cmd, 150)}"
                detail = {"command": scrub(cmd, 300), "cwd": cwd}
            started_ts = now_ts
        elif event == "afterShellExecution" or (event == "postToolUse" and tool_name == "Shell"):
            cmd = str(payload.get("command") or ti.get("command") or "")
            if is_wait_command(cmd):
                phase = "thinking"
                tool_name = "wait_done"
                summary = "收到新消息唤醒，准备调用 read_chat"
            else:
                phase = "thinking"
                tool_name = "Shell"
                summary = f"命令已完成({duration_ms // 1000}s)，正在思考下一步: {scrub(cmd, 90)}"
            started_ts = now_ts
        elif event == "beforeReadFile" or (event == "preToolUse" and tool_name in ("Read", "Grep", "Glob")):
            target = str(
                payload.get("file_path")
                or ti.get("path")
                or ti.get("glob_pattern")
                or ti.get("pattern")
                or ""
            )
            phase = "file_read"
            tool_name = tool_name or "Read"
            summary = f"读取/检索 ({tool_name}): {scrub(target, 140)}"
            detail = {"target": scrub(target, 240)}
            started_ts = now_ts
        elif event == "preToolUse" and tool_name in ("Write", "StrReplace", "Delete"):
            fpath, desc = summarize_file_edit(payload, ti)
            phase = "file_edit"
            summary = desc
            detail = {"file_path": fpath}
            started_ts = now_ts
        elif event == "afterFileEdit" or (event == "postToolUse" and tool_name in ("Write", "StrReplace", "Delete")):
            fpath, desc = summarize_file_edit(payload, ti)
            phase = "thinking"
            tool_name = tool_name or "FileEdit"
            summary = f"已完成{desc}，正在思考下一步"
            detail = {"file_path": fpath}
            started_ts = now_ts
        elif event == "beforeMCPExecution" or (event == "preToolUse" and tool_name == "CallDynamicTool"):
            mcp_tool = str(ti.get("toolName") or tool_name or "")
            mcp_args = ti.get("arguments") if isinstance(ti.get("arguments"), dict) else ti
            if mcp_tool == "read_chat" and (mcp_args or {}).get("wait_sec", 1) != 0:
                phase = "idle_wait"
                tool_name = "read_chat"
                summary = "MCP read_chat 挂起等消息"
            else:
                phase = "mcp"
                tool_name = mcp_tool or "MCP"
                summary = f"调用 MCP 工具: {scrub(mcp_tool, 80)}"
            started_ts = now_ts
        elif event == "afterMCPExecution" or (event == "postToolUse" and tool_name == "CallDynamicTool"):
            mcp_tool = str(ti.get("toolName") or tool_name or "")
            phase = "thinking"
            tool_name = mcp_tool or "MCP"
            summary = f"完成 MCP {scrub(mcp_tool, 60)}，正在思考/处理"
            started_ts = now_ts
        elif event == "afterAgentThought":
            thought = scrub(str(payload.get("text") or ""), 180)
            phase = "thinking"
            tool_name = "Thought"
            dur_s = f"{duration_ms / 1000:.1f}s" if duration_ms else ""
            summary = f"思考({dur_s}): {thought}" if thought else f"完成一段思考({dur_s})"
            detail = {"last_thought": thought, "thought_ms": duration_ms}
            started_ts = now_ts
        elif event == "preToolUse":
            phase = "tool"
            summary = f"调用工具 {tool_name}: {scrub(json.dumps(ti, ensure_ascii=False), 120)}"
            started_ts = now_ts
        elif event in ("postToolUse", "postToolUseFailure"):
            err = scrub(str(payload.get("error_message") or ""), 100)
            phase = "thinking"
            summary = f"工具 {tool_name} {'失败(' + err + ')' if err else '返回'}，正在思考下一步"
            started_ts = now_ts
        elif event == "afterAgentResponse":
            phase = "thinking"
            tool_name = "Response"
            summary = f"输出回复: {scrub(str(payload.get('text') or ''), 120)}"
            started_ts = now_ts

        if phase:
            real_model = str(payload.get("model") or sess.get("model") or "").strip()
            if real_model:
                detail["model"] = real_model
                sess["model"] = real_model
            sess.update(
                {
                    "phase": phase,
                    "tool_name": tool_name,
                    "summary": summary,
                    "detail": detail,
                    "started_ts": started_ts,
                    "updated_ts": now_ts,
                    "conversation_id": cid,
                }
            )
            # 清理超过 6 小时未活动的本地会话缓存
            stale = [k for k, v in st["sessions"].items() if now_ts - float(v.get("updated_ts") or 0) > 21600]
            for k in stale:
                st["sessions"].pop(k, None)

    if phase and (agent_id or cid):
        ev_resp = post_json(
            f"{bridge_url}/trace/event",
            {
                "agent_id": agent_id,
                "conversation_id": cid,
                "conv_hint": conv_hint,
                "event": event,
                "phase": phase,
                "tool_name": tool_name,
                "summary": summary,
                "detail": detail,
                "duration_ms": duration_ms,
                "started_ts": started_ts,
                "output_ts": now_ts if phase != "shell" else 0,
                "ts": now_ts,
            },
        )
        # 若服务端通过目录/命令里的 conv_hint 自动识别出了该会话的 agent_id，立刻写回本地映射！
        bound_id = str((ev_resp or {}).get("bound_agent_id") or "").strip()
        if bound_id and not agent_id and cid:
            agent_id = bound_id
            with StateLock() as st2:
                st2["conv_to_agent"][cid] = bound_id
                if cid in st2["sessions"]:
                    st2["sessions"][cid]["agent_id"] = bound_id

    ensure_daemon()

    # 每次运行任何 Shell 命令（或改文件等非 read_chat 工具）返回时，自动顺带收取各方未读消息并插播给 AI！
    out_obj: dict[str, Any] = {}
    if event == "preToolUse" and pre_alert_ctx:
        out_obj["additional_context"] = pre_alert_ctx
    elif agent_id and event in ("postToolUse", "postToolUseFailure"):
        is_dais_read = (
            tool_name in ("MCP:read_chat", "MCP:join", "read_chat", "join")
            or (tool_name == "CallDynamicTool" and str(ti.get("toolName") or "") in ("read_chat", "join"))
        )
        if not is_dais_read:
            alert_txt = build_inbox_alert(bridge_url, agent_id)
            if alert_txt:
                out_obj["additional_context"] = alert_txt

    print(json.dumps(out_obj, ensure_ascii=False))
    return 0


def latest_terminal_activity(since_ts: float) -> tuple[float, str]:
    """检查 Cursor terminals 目录下最近更新的终端输出文件，判断长命令是在持续输出还是卡死。"""
    if not TERMINALS_DIR.exists():
        return 0.0, ""
    best_mtime = 0.0
    best_file: Path | None = None
    try:
        for entry in os.scandir(TERMINALS_DIR):
            if not entry.name.endswith(".txt"):
                continue
            st = entry.stat()
            if st.st_mtime >= since_ts - 5 and st.st_mtime > best_mtime:
                best_mtime = st.st_mtime
                best_file = Path(entry.path)
    except Exception:
        return 0.0, ""
    if best_file is None:
        return 0.0, ""
    try:
        with open(best_file, "rb") as fp:
            fp.seek(0, os.SEEK_END)
            size = fp.tell()
            fp.seek(max(0, size - 2048))
            tail = fp.read().decode("utf-8", errors="replace")
        lines = [ln.strip() for ln in tail.splitlines() if ln.strip() and not ln.startswith("---")]
        last_line = scrub(lines[-1], 120) if lines else ""
        return best_mtime, last_line
    except Exception:
        return best_mtime, ""


def run_daemon() -> int:
    CURSOR_DIR.mkdir(parents=True, exist_ok=True)
    if daemon_alive():
        return 0
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    idle_ticks = 0
    try:
        while True:
            time.sleep(8)
            now_ts = time.time()
            cfg = load_config()
            bridge_url = cfg["bridge_url"]
            updates: list[dict[str, Any]] = []
            with StateLock() as st:
                sessions = st.get("sessions", {})
                for key, sess in list(sessions.items()):
                    agent_id = sess.get("agent_id") or ""
                    cid = sess.get("conversation_id") or ""
                    phase = sess.get("phase") or ""
                    updated = float(sess.get("updated_ts") or 0)
                    started = float(sess.get("started_ts") or updated or now_ts)
                    if not (agent_id or cid) or not phase:
                        continue
                    # 只给正在跑命令、改文件、思考的活跃会话发持续耗时心跳（超过 2 小时无事件则停止心跳，让外界看到停滞）
                    if phase in ("shell", "thinking", "file_edit", "file_read", "tool", "mcp") and now_ts - updated < 7200:
                        detail = dict(sess.get("detail") or {})
                        out_ts = 0.0
                        if phase == "shell":
                            out_ts, last_line = latest_terminal_activity(started)
                            if last_line:
                                detail["last_output"] = last_line
                            if out_ts:
                                detail["output_age_sec"] = int(max(0, now_ts - out_ts))
                        updates.append(
                            {
                                "agent_id": agent_id,
                                "conversation_id": cid,
                                "event": "heartbeat",
                                "phase": phase,
                                "tool_name": sess.get("tool_name") or "",
                                "summary": sess.get("summary") or "",
                                "detail": detail,
                                "duration_ms": int((now_ts - started) * 1000),
                                "started_ts": started,
                                "output_ts": out_ts,
                                "ts": now_ts,
                                "heartbeat": True,
                            }
                        )
            if updates:
                idle_ticks = 0
                for item in updates:
                    post_json(f"{bridge_url}/trace/event", item, timeout=1.2)
            else:
                idle_ticks += 1
                if idle_ticks > 450:  # 1 小时完全无活跃任务则自动退出，下次钩子触发再拉起
                    break
    finally:
        try:
            if PID_PATH.exists() and PID_PATH.read_text(encoding="utf-8").strip() == str(os.getpid()):
                PID_PATH.unlink()
        except Exception:
            pass
    return 0


def reload_exec_daemon() -> str:
    """在当前 Cursor 云端 VM 内自动寻找 exec-daemon 控制端口并触发 ReloadAgentSkills 热加载 hooks.json。"""
    for cmdline_file in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            raw = Path(cmdline_file).read_bytes().decode("utf-8", errors="replace")
            parts = [p for p in raw.split("\x00") if p]
            if not any("exec-daemon" in p for p in parts):
                continue
            port = ""
            token = ""
            for i, arg in enumerate(parts):
                if arg == "--port" and i + 1 < len(parts):
                    port = parts[i + 1]
                elif arg == "--auth-token" and i + 1 < len(parts):
                    token = parts[i + 1]
            if port and token:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/agent.v1.ControlService/ReloadAgentSkills",
                    data=b"{}",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    return f"reloaded exec-daemon on port {port} (HTTP {resp.status})"
        except Exception as exc:
            return f"reload_attempt_err: {exc}"
    return "exec-daemon not detected (hooks.json written for next load)"


def install_hooks(bridge_url: str) -> int:
    bridge_url = bridge_url.rstrip("/")
    CURSOR_DIR.mkdir(parents=True, exist_ok=True)
    target_script = CURSOR_DIR / "agent_trace.py"
    src_script = Path(__file__).resolve()
    if src_script != target_script:
        target_script.write_text(src_script.read_text(encoding="utf-8"), encoding="utf-8")
    target_script.chmod(0o755)
    save_config({"bridge_url": bridge_url})

    cmd_str = f"python3 {target_script} hook"
    existing: dict[str, Any] = {"version": 1, "hooks": {}}
    if HOOKS_PATH.exists():
        try:
            parsed = json.loads(HOOKS_PATH.read_text(encoding="utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("hooks"), dict):
                existing = parsed
                existing["version"] = int(existing.get("version") or 1)
        except Exception:
            pass

    hooks_map = existing.setdefault("hooks", {})
    for ev in HOOK_EVENTS:
        arr = hooks_map.get(ev)
        if not isinstance(arr, list):
            arr = []
        arr = [item for item in arr if not (isinstance(item, dict) and "agent_trace.py" in str(item.get("command") or ""))]
        entry: dict[str, Any] = {"command": cmd_str}
        if ev == "subagentStop":
            entry["loop_limit"] = 20
        arr.append(entry)
        hooks_map[ev] = arr

    HOOKS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    reload_note = reload_exec_daemon()
    ensure_daemon()
    print(f"[agent_trace] installed at {target_script}, hooks={HOOKS_PATH}, {reload_note}")
    return 0


def wait_loop(agent_id: str, bridge_url: str, max_sec: int = 6660) -> int:
    """第 3 层防断连：断线/平滑重启自愈长等待，收到真正终端通知行或超时才返回。"""
    bridge_url = bridge_url.rstrip("/")
    deadline = time.time() + max_sec
    post_json(
        f"{bridge_url}/trace/event",
        {
            "agent_id": agent_id,
            "event": "wait_start",
            "phase": "idle_wait",
            "tool_name": "wait",
            "summary": "终端自愈长等待新消息 (/wait)",
            "started_ts": time.time(),
            "ts": time.time(),
        },
    )
    last_line = ""
    while time.time() < deadline:
        rem = max(15, int(deadline - time.time()))
        req = urllib.request.Request(
            f"{bridge_url}/wait",
            headers={"X-Agent": agent_id},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=min(rem + 30, 6720)) as resp:
                while True:
                    raw = resp.readline()
                    if not raw:
                        break
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        last_line = line
                        if any(tag in line for tag in ("【有新消息】", "【等到时】", "已停用", "身份不对")):
                            print(line, flush=True)
                            return 0
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:
                pass
            if exc.code == 403 and body:
                print(body, flush=True)
                return 0
        except Exception:
            pass
        # 服务重启或网络闪断：自动短暂退避后重连，不退出终端等待！
        if time.time() + 3 >= deadline:
            break
        time.sleep(2.0)

    if last_line:
        print(last_line, flush=True)
    else:
        print(
            f"【连接重试到时】这不是用户消息。现在立刻调用 read_chat(agent=\"{agent_id}\") 继续等待，严禁结束回合。",
            flush=True,
        )
    return 0


def run_wrapped(args: list[str]) -> int:
    agent_id = os.environ.get("TG_AGENT_ID", "")
    if "--agent" in args:
        idx = args.index("--agent")
        if idx + 1 < len(args):
            agent_id = args[idx + 1]
            args = args[:idx] + args[idx + 2 :]
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        print("Usage: agent_trace.py run [--agent a_xxx] -- <command...>", file=sys.stderr)
        return 2
    cfg = load_config()
    bridge_url = cfg["bridge_url"]
    cmd_str = " ".join(args)
    started = time.time()
    if agent_id:
        post_json(
            f"{bridge_url}/trace/event",
            {
                "agent_id": agent_id,
                "event": "cli_run_start",
                "phase": "shell",
                "tool_name": "CLI",
                "summary": f"执行命令: {scrub(cmd_str, 150)}",
                "started_ts": started,
                "ts": started,
            },
        )
    proc = subprocess.Popen(args)
    while True:
        ret = proc.poll()
        if ret is not None:
            break
        time.sleep(8)
        if agent_id:
            now_ts = time.time()
            post_json(
                f"{bridge_url}/trace/event",
                {
                    "agent_id": agent_id,
                    "event": "heartbeat",
                    "phase": "shell",
                    "tool_name": "CLI",
                    "summary": f"执行命令: {scrub(cmd_str, 150)}",
                    "duration_ms": int((now_ts - started) * 1000),
                    "started_ts": started,
                    "ts": now_ts,
                    "heartbeat": True,
                },
            )
    end_ts = time.time()
    if agent_id:
        post_json(
            f"{bridge_url}/trace/event",
            {
                "agent_id": agent_id,
                "event": "cli_run_end",
                "phase": "thinking",
                "tool_name": "CLI",
                "summary": f"命令退出(code={ret}, {int(end_ts - started)}s): {scrub(cmd_str, 100)}",
                "duration_ms": int((end_ts - started) * 1000),
                "started_ts": end_ts,
                "ts": end_ts,
            },
        )
    return int(ret)


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] == "hook":
        return handle_hook()
    cmd = argv[0]
    if cmd == "install":
        url = argv[1] if len(argv) > 1 else load_config()["bridge_url"]
        return install_hooks(url)
    if cmd == "daemon":
        return run_daemon()
    if cmd == "wait":
        if len(argv) < 2:
            print("缺少 agent_id", file=sys.stderr)
            return 2
        url = argv[2] if len(argv) > 2 else load_config()["bridge_url"]
        max_sec = int(argv[3]) if len(argv) > 3 and argv[3].isdigit() else 6660
        return wait_loop(argv[1], url, max_sec)
    if cmd == "run":
        return run_wrapped(argv[1:])
    if cmd in ("status", "panel"):
        url = load_config()["bridge_url"]
        agent_hdr = os.environ.get("TG_AGENT_ID", "")
        for item in argv[1:]:
            if item.startswith(("a_", "m_")):
                agent_hdr = item
            elif item.startswith("http"):
                url = item
        if not agent_hdr and STATE_PATH.exists():
            try:
                st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
                for v in (st.get("conv_to_agent") or {}).values():
                    if str(v).startswith("m_"):
                        agent_hdr = str(v)
                        break
            except Exception:
                pass
        req = urllib.request.Request(f"{url.rstrip('/')}/trace", headers={"X-Agent": agent_hdr} if agent_hdr else {})
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as exc:
            data = {"error": str(exc)}
        if cmd == "panel" and isinstance(data.get("traces"), list):
            print(f"=== AI 实时动作追踪面板 (v{data.get('version', '?')}, 共 {len(data['traces'])} 条) ===")
            for tr in data["traces"]:
                stuck = " ⚠️疑似停滞!" if tr.get("suspected_stuck") else ""
                print(f"• {tr['chat']} [{tr['name']}] ({tr['state']}) | {tr['phase']} {tr['elapsed_sec']}s | {tr['summary']}{stuck}")
                for ev in tr.get("recent_events") or []:
                    print(f"    - {ev['time']} [{ev['phase']}] {ev['summary']}")
            return 0
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    print(f"未知子命令: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
