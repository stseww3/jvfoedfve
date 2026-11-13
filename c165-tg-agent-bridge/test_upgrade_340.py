#!/usr/bin/env python3
"""End-to-end offline verification suite for tg-agent-bridge 3.4.0 + agent_trace.py."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

TMP_ROOT = Path(tempfile.mkdtemp(prefix="tgb340_test_"))
DATA_DIR = TMP_ROOT / "data"
HOME_DIR = TMP_ROOT / "fake_home"
HOME_DIR.mkdir(parents=True, exist_ok=True)

os.environ["DATA_DIR"] = str(DATA_DIR)
os.environ["TG_TOKEN"] = "123456:TEST_DUMMY_TOKEN_DO_NOT_USE"
os.environ["PUBLIC_BASE"] = "http://127.0.0.1:18787"
os.environ["AGENT_STREAK_LIMIT"] = "4"
os.environ["GROUP_STREAK_LIMIT"] = "5"

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402
import app as bridge  # noqa: E402


async def _noop_tg_call(method: str, **kwargs):
    if method == "getMe":
        return {"id": 999000, "username": "test_bridge_bot", "can_read_all_group_messages": True}
    if method in ("sendMessage", "sendDocument"):
        return {"message_id": 101}
    return True


async def _noop_tg_try_call(method: str, **kwargs):
    return await _noop_tg_call(method, **kwargs)


async def _noop_send_text(chat_id: int, text: str, **kwargs):
    return [{"message_id": 102}]


bridge.tg.call = _noop_tg_call
bridge.tg.try_call = _noop_tg_try_call
bridge.tg.send_text = _noop_send_text


def text_of(res) -> str:
    if res.commit:
        res.commit()
    return "\n".join(c.get("text", "") for c in res.content)


async def run_core_tests() -> dict[str, str]:
    now = bridge.now()
    bridge.ensure_main_conv()
    bridge.store.run(
        "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)",
        (7001, "AdminUser", "admin", 7001, now),
    )
    bridge.store.run(
        "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)",
        (8002, "ExternalUser", "user", 8002, now),
    )

    # 1. Main agent creation & [主控] 三句 fixed rules verification
    main_id = bridge.make_main(new_cloud=False)
    res_list = await bridge.call_tool("list_agents", {"agent": main_id})
    txt_list = text_of(res_list)
    assert "[主控] 三句：" in txt_list, f"Missing [主控] 三句 in main footer: {txt_list}"
    assert "run_in_background=true 是唯一防卡死关键" in txt_list

    # 2. Create c1 & c2 for admin, and c3 for external user (owner isolation test)
    res_c1 = await bridge.call_tool("create_chat", {"agent": main_id, "brief": "负责网关重构", "name": "网关组"})
    assert not res_c1.is_error
    c1_row = bridge.conv_row("c1")
    res_join1 = await bridge.call_tool("join", {"code": c1_row["task_code"], "name": "网关组"})
    assert not res_join1.is_error
    a1 = bridge.conv_row("c1")["agent"]
    assert a1.startswith("a_")

    res_c2 = await bridge.call_tool("create_chat", {"agent": main_id, "brief": "负责数据库迁移", "name": "存储组"})
    c2_row = bridge.conv_row("c2")
    await bridge.call_tool("join", {"code": c2_row["task_code"], "name": "存储组"})
    a2 = bridge.conv_row("c2")["agent"]

    # External user chat c3
    c3_ext = bridge.create_conv("外部用户私有任务", 8002, name="外部助手", owner=8002)
    await bridge.call_tool("join", {"code": c3_ext["task_code"]})
    a3_ext = bridge.conv_row("c3")["agent"]

    # Record git repo on c1 so spawned child memory inheritance can verify git propagation
    res_repo = await bridge.call_tool(
        "set_repo",
        {"agent": a1, "repo": "stseww3/jvfoedfve", "branch": "cursor/test-branch", "note": "网关目录"},
    )
    txt_repo = text_of(res_repo)
    assert "【子agent防断连固定铁律】" in txt_repo

    # Verify bind_task_id + watchdog_tick [主控] 三句 output
    res_bind = await bridge.call_tool("bind_task_id", {"agent": main_id, "chat": "c1", "task_agent_id": "task_abc_123"})
    assert "task_abc_123" in text_of(res_bind)

    # 3. Verify owner isolation in list_peers & send_agent_message
    peers_admin = text_of(await bridge.call_tool("list_peers", {"agent": a1}))
    assert "c1「网关组」" in peers_admin and "c2「存储组」" in peers_admin
    assert "c3「外部助手」" not in peers_admin, "Owner isolation leak in list_peers!"

    cross_dm = await bridge.call_tool("send_agent_message", {"agent": a1, "to": "c3", "text": "越权测试"})
    assert cross_dm.is_error and "权限隔离" in text_of(cross_dm)

    # 4. Agent-to-agent direct MCP messaging + wakeup + anti-ping-pong cap
    dm_res = await bridge.call_tool("send_agent_message", {"agent": a1, "to": "c2", "text": "请把新的表结构发我确认"})
    assert not dm_res.is_error
    inbox_c2 = text_of(await bridge.call_tool("read_chat", {"agent": a2, "wait_sec": 0}))
    assert "【Agent私聊" in inbox_c2 and "请把新的表结构发我确认" in inbox_c2
    assert "【子agent防断连固定铁律】" in inbox_c2

    # Trigger streak cap (AGENT_STREAK_LIMIT=4 in test env)
    for i in range(4):
        last_dm = await bridge.call_tool("send_agent_message", {"agent": a2, "to": "c1", "text": f"连发测试 #{i}"})
    assert "防乒乓死循环保护" in text_of(last_dm)

    # 5. Pure-MCP Agent Group creation, targeted mentions, and group_history
    grp_res = await bridge.call_tool(
        "create_agent_group",
        {
            "agent": a1,
            "name": "架构联调群",
            "members": ["c2"],
            "topic": "联调 3.4.0 接口",
            "welcome": "大家好，这里同步接口字段",
        },
    )
    assert not grp_res.is_error and "g1「架构联调群」" in text_of(grp_res)

    inbox_c2_grp = text_of(await bridge.call_tool("read_chat", {"agent": a2, "wait_sec": 0}))
    assert "架构联调群" in inbox_c2_grp and "大家好，这里同步接口字段" in inbox_c2_grp

    gmsg_res = await bridge.call_tool(
        "send_group_message",
        {"agent": a2, "group": "g1", "text": "store.py 已对齐字段", "mentions": ["c1"]},
    )
    assert not gmsg_res.is_error
    ghist = text_of(await bridge.call_tool("group_history", {"agent": a1, "group": "g1"}))
    assert "store.py 已对齐字段" in ghist

    # Drain c1 inbox before testing spawn notification
    await bridge.call_tool("read_chat", {"agent": a1, "wait_sec": 0})

    # 6. Sub-agent requesting Main to spawn sub-agent (with memory + custom model + group auto-join)
    spawn_res = await bridge.call_tool(
        "spawn_subagent",
        {
            "agent": a1,
            "brief": "编写自动化压力测试脚本并汇报结果",
            "include_memory": True,
            "memory_summary": "已完成网关鉴权改造，代码位于 c165-tg-agent-bridge/，端口 8787。",
            "model": "claude-4.5-opus",
            "name": "压测专员",
            "group": "g1",
        },
    )
    assert not spawn_res.is_error, text_of(spawn_res)
    assert "c4" in text_of(spawn_res)

    # Verify Main received strict 100%-obey instruction + [主控] 三句 in read_chat!
    main_inbox = text_of(await bridge.call_tool("read_chat", {"agent": main_id, "wait_sec": 0}))
    assert "【强制派生指令】" in main_inbox
    assert "主控必须 100% 完全按照该子 agent 的要求执行" in main_inbox
    assert "claude-4.5-opus" in main_inbox
    assert "已完成网关鉴权改造" in main_inbox
    assert "[主控] 三句：" in main_inbox

    # Child c4 joins -> verify child receives memory_summary + shared c1 history + inherited git repo + g1 membership!
    c4_row = bridge.conv_row("c4")
    join_c4 = await bridge.call_tool("join", {"code": c4_row["task_code"]})
    welcome_c4 = text_of(join_c4)
    a4 = bridge.conv_row("c4")["agent"]
    assert "已完成网关鉴权改造" in welcome_c4
    assert "stseww3/jvfoedfve" in welcome_c4
    assert "已授权你读取聊天 c1「网关组」" in welcome_c4
    assert "g1「架构联调群」" in welcome_c4

    # Verify parent c1 was automatically woken & notified when c4 joined!
    c1_wake = text_of(await bridge.call_tool("read_chat", {"agent": a1, "wait_sec": 0}))
    assert "c4「压测专员」 已上线接手" in c1_wake

    # Also test spawn_subagent with include_memory=False (clean slate)
    spawn_clean = await bridge.call_tool(
        "spawn_subagent",
        {
            "agent": a1,
            "brief": "独立检查外部文档格式",
            "include_memory": False,
            "model": "inherit",
            "name": "文档检查",
        },
    )
    assert not spawn_clean.is_error
    c5_row = bridge.conv_row("c5")
    welcome_c5 = text_of(await bridge.call_tool("join", {"code": c5_row["task_code"]}))
    a5 = bridge.conv_row("c5")["agent"]
    assert "已授权你读取聊天 c1" not in welcome_c5
    assert "stseww3/jvfoedfve" not in welcome_c5

    # Verify c2 CANNOT stop c5 (only parent c1 can!), and c1 CAN stop_spawned_agent c5
    bad_stop = await bridge.call_tool("stop_spawned_agent", {"agent": a2, "chat": "c5"})
    assert bad_stop.is_error
    ok_stop = await bridge.call_tool("stop_spawned_agent", {"agent": a1, "chat": "c5", "close": True})
    assert not ok_stop.is_error

    # 7. Verify strict cross-owner isolation in reverse (ExternalUser a3_ext cannot see/message/group Admin's c1/g1)
    peers_ext = text_of(await bridge.call_tool("list_peers", {"agent": a3_ext}))
    assert "c3「外部助手」" in peers_ext
    assert "c1" not in peers_ext and "g1" not in peers_ext
    assert (await bridge.call_tool("send_agent_message", {"agent": a3_ext, "to": "c1", "text": "hi"})).is_error
    assert (await bridge.call_tool("send_agent_message", {"agent": a1, "to": "main", "text": "hi"})).is_error
    assert (await bridge.call_tool("send_group_message", {"agent": a3_ext, "group": "g1", "text": "hi"})).is_error
    assert (await bridge.call_tool("group_history", {"agent": a3_ext, "group": "g1"})).is_error

    # 8. Verify 3.4.1 custom duration parser, smart admin device resolution, /local & /device duration controls
    assert bridge.parse_duration_spec("45m") == 2700
    assert bridge.parse_duration_spec("1h30m") == 5400
    assert bridge.parse_duration_spec("7d") == 604800
    assert bridge.parse_duration_spec("2.5") == 9000
    assert bridge.parse_duration_spec("永久") == bridge.PERMANENT_SEC
    assert bridge.parse_duration_spec("0") == 0

    # Set up unused d0 and online d3 (admin's Windows PC) + online d1 (external user 8002's PC)
    bridge.store.run("INSERT OR REPLACE INTO devices(id,name,owner,status,last_seen) VALUES('d0','管理员的电脑',0,'active',0)")
    bridge.store.run("INSERT OR REPLACE INTO devices(id,name,owner,status,last_seen) VALUES('d3','auouf的电脑',7001,'active',?)", (now,))
    bridge.store.run("INSERT OR REPLACE INTO devices(id,name,owner,status,last_seen) VALUES('d1','ext的电脑',8002,'active',?)", (now,))
    bridge.LOCAL["clients"]["d3"] = object()
    bridge.LOCAL["clients"]["d1"] = object()

    # Admin chat c1 automatically resolves to online d3 (not dead d0, and NEVER d1!)
    assert bridge.conv_device(bridge.conv_row("c1"))["id"] == "d3"
    assert bridge.conv_device(bridge.conv_row("c3"))["id"] == "d1"

    # Test /local without chat id (uses selected chat c1!) + custom duration "45m" + "永久"
    bridge.store.set("sel:7001", "c1")
    await bridge.on_command({"from": {"id": 7001}}, "/local", "45m", 7001, "private", 7001)
    c1_after = bridge.conv_row("c1")
    assert 2600 < c1_after["local_until"] - bridge.now() <= 2705 and c1_after["local_dev"] == "d3"

    # Test /device computer-wide pass ("24h") & ensure d3 pass NEVER leaks to external user's c3!
    await bridge.on_command({"from": {"id": 7001}}, "/device", "24h", 7001, "private", 7001)
    d3_row = bridge.device_row("d3")
    assert d3_row["auth_until"] > bridge.now() + 86000
    assert bridge.device_pass_active(d3_row, bridge.conv_row("c2")) is True
    assert bridge.device_pass_active(d3_row, bridge.conv_row("c3")) is False

    # Test /device window 30m and /device lock
    await bridge.on_command({"from": {"id": 7001}}, "/device", "window 30m", 7001, "private", 7001)
    assert bridge.device_window_sec(bridge.device_row("d3")) == 1800
    await bridge.on_command({"from": {"id": 7001}}, "/device", "lock", 7001, "private", 7001)
    assert bridge.device_row("d3")["auth_until"] == 0
    assert bridge.conv_row("c1")["local_until"] == 0

    return {"main": main_id, "a1": a1, "a2": a2, "a3_ext": a3_ext, "a4": a4, "a5_stopped": a5}


def run_http_and_hook_tests(ids: dict[str, str]) -> None:
    cfg = uvicorn.Config(bridge.app, host="127.0.0.1", port=18787, log_level="error")
    server = uvicorn.Server(cfg)
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    time.sleep(0.8)

    env = dict(os.environ)
    env["HOME"] = str(HOME_DIR)
    env["BRIDGE_URL"] = "http://127.0.0.1:18787"
    trace_py = str(Path(__file__).resolve().parent / "agent_trace.py")

    try:
        # 1. Install hooks into fake HOME
        inst = subprocess.run(
            [sys.executable, trace_py, "install", "http://127.0.0.1:18787"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "installed at" in inst.stdout
        hooks_file = HOME_DIR / ".cursor" / "hooks.json"
        assert hooks_file.exists()
        hooks_json = json.loads(hooks_file.read_text(encoding="utf-8"))
        assert "subagentStop" in hooks_json["hooks"] and "afterAgentThought" in hooks_json["hooks"]

        def fire_hook(payload: dict) -> dict:
            proc = subprocess.run(
                [sys.executable, str(HOME_DIR / ".cursor" / "agent_trace.py"), "hook"],
                input=json.dumps(payload),
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(proc.stdout.strip())

        # 2. Auto-bind conversation_id -> a1 via MCP call, then track Shell, FileEdit, Thought!
        cid = "conv-uuid-test-c1"
        assert fire_hook({
            "hook_event_name": "preToolUse",
            "conversation_id": cid,
            "tool_name": "CallDynamicTool",
            "tool_input": {"namespace": "dais", "toolName": "list_peers", "arguments": {"agent": ids["a1"]}},
        }) == {}

        assert fire_hook({
            "hook_event_name": "beforeShellExecution",
            "conversation_id": cid,
            "command": "pytest -q tests/test_gateway.py",
            "cwd": "/agent/repos/jvfoedfve",
        }) == {}

        assert fire_hook({
            "hook_event_name": "preToolUse",
            "conversation_id": cid,
            "tool_name": "StrReplace",
            "tool_input": {
                "path": "/opt/tg-agent-bridge/app.py",
                "old_string": "VERSION = '3.3.0'",
                "new_string": "VERSION = '3.4.0'\n# upgraded",
            },
        }) == {}

        assert fire_hook({
            "hook_event_name": "afterAgentThought",
            "conversation_id": cid,
            "text": "正在核对子 agent 记忆共享与模型透传逻辑是否覆盖全部边界情况",
            "duration_ms": 4200,
        }) == {}

        # 3. Verify Layer 4 subagentStop hook: active a1 MUST be bounced back with followup_message!
        stop_active = fire_hook({
            "hook_event_name": "subagentStop",
            "conversation_id": cid,
        })
        assert "followup_message" in stop_active and ids["a1"] in stop_active["followup_message"], stop_active

        # Verify stopped agent (a5_stopped) is allowed to exit cleanly ({})!
        cid_stopped = "conv-uuid-stopped-c5"
        fire_hook({
            "hook_event_name": "preToolUse",
            "conversation_id": cid_stopped,
            "tool_name": "CallDynamicTool",
            "tool_input": {"namespace": "dais", "toolName": "list_peers", "arguments": {"agent": ids["a5_stopped"]}},
        })
        stop_inactive = fire_hook({
            "hook_event_name": "subagentStop",
            "conversation_id": cid_stopped,
        })
        assert stop_inactive == {}, f"Stopped agent should not be bounced back: {stop_inactive}"

        # 4. Verify /trace HTTP JSON requires auth & enforces owner isolation
        import urllib.error
        import urllib.request
        try:
            urllib.request.urlopen("http://127.0.0.1:18787/trace?chat=c1&limit=10", timeout=3)
            raise AssertionError("Unauthenticated GET /trace should return 403!")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403

        req_admin_sub = urllib.request.Request(
            "http://127.0.0.1:18787/trace?chat=c1&limit=10",
            headers={"X-Agent": ids["a1"]},
        )
        with urllib.request.urlopen(req_admin_sub, timeout=3) as resp:
            tdata = json.loads(resp.read().decode("utf-8"))
        assert tdata["ok"] and tdata["version"] == "3.4.1"
        assert len(tdata["traces"]) == 1
        c1_trace = tdata["traces"][0]
        assert c1_trace["chat"] == "c1"
        assert len(c1_trace["recent_events"]) >= 4

        # External user's sub-agent MUST NOT see c1 in GET /trace!
        req_ext_sub = urllib.request.Request(
            "http://127.0.0.1:18787/trace?chat=c1&limit=10",
            headers={"X-Agent": ids["a3_ext"]},
        )
        with urllib.request.urlopen(req_ext_sub, timeout=3) as resp:
            tdata_ext = json.loads(resp.read().decode("utf-8"))
        assert tdata_ext["traces"] == [], f"Owner leak in GET /trace: {tdata_ext}"

        with urllib.request.urlopen("http://127.0.0.1:18787/trace/install.sh", timeout=3) as resp:
            install_sh = resp.read().decode("utf-8")
        assert "agent_trace.py install" in install_sh

    finally:
        server.should_exit = True
        # Stop background daemon started inside fake HOME
        pid_file = HOME_DIR / ".cursor" / "agent_trace_daemon.pid"
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text().strip()), 9)
            except Exception:
                pass


def main() -> None:
    ids = asyncio.run(run_core_tests())
    run_http_and_hook_tests(ids)
    print("ALL_340_TESTS_PASSED_OK")


if __name__ == "__main__":
    main()
