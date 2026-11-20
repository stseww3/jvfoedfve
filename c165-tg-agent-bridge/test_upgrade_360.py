#!/usr/bin/env python3
"""Comprehensive end-to-end verification suite for tg-agent-bridge 3.6.0.

Covers:
1. Empty/unkeyed `join()` anti-misfire guard (subagent forgetting `code` is rejected cleanly with 0 false admin popups).
2. Multi-main executors (`main1`, `main2` coexisting without kicking each other) + singleton Controller (`ctrl`) bootstrap.
3. Standardized zero-thought ops (`[STANDARD_OP type="TASK_LAUNCH"|"TASK_RESUME"|"WORKSPACE_JOB"]`) + `submit_op_result`.
4. Worker node (`mode="worker"`) silent approval by `ctrl` (`approve_worker`) without bothering admin, plus local channel block.
5. Admin-only `spawn_subagent` (non-admin member keeps 5-chat limit but is blocked from spawning subagents).
6. Machine exclusivity (`dedicated_machine`) + cross-agent node ACL (`grant_access` / `revoke_access`) + auto-release on stop.
7. CPU / RAM / balloon real-time VM probe propagation & `dais_runtime.pyz` bytecode archive execution.
8. 5-minute `thinking`-stuck auto-restart while strictly exempting `shell` commands from false restarts.
9. Multi-device `/device add` keeping multiple PCs (`d1`, `d2`) active simultaneously.
10. Web Console (`zwt` first-visit password setup, PBKDF2 zero-plaintext-log verification, `zwt`-only user management,
    inline message edit/delete, full-context restart dossier routed to `ctrl`, live Agent Group view & human participation,
    binary image/file upload & serving).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TMP_ROOT = Path(tempfile.mkdtemp(prefix="tgb360_test_"))
DATA_DIR = TMP_ROOT / "data"
HOME_DIR = TMP_ROOT / "fake_home"
HOME_DIR.mkdir(parents=True, exist_ok=True)

os.environ["DATA_DIR"] = str(DATA_DIR)
os.environ["TG_TOKEN"] = "123456:TEST_DUMMY_TOKEN_DO_NOT_USE"
os.environ["PUBLIC_BASE"] = "http://127.0.0.1:18797"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
import app as bridge  # noqa: E402

ADMIN_NOTICES: list[str] = []


async def _mock_tg_call(method: str, **kwargs):
    if method == "getMe":
        return {"id": 999000, "username": "test360_bot", "can_read_all_group_messages": True}
    if method == "sendMessage":
        ADMIN_NOTICES.append(str(kwargs.get("text") or ""))
        return {"message_id": 201}
    if method == "sendDocument":
        return {"message_id": 202}
    return True


async def _mock_send_text(chat_id: int, text: str, **kwargs):
    ADMIN_NOTICES.append(text)
    return [{"message_id": 203}]


async def _mock_send_doc(*args, **kwargs):
    return {"message_id": 204}


bridge.tg.call = _mock_tg_call
bridge.tg.try_call = _mock_tg_call
bridge.tg.send_text = _mock_send_text
bridge.tg.send_document = _mock_send_doc


def text_of(res) -> str:
    if res.commit:
        res.commit()
    return "\n".join(c.get("text", "") for c in res.content)


async def finish_onboard(agent_id: str, to_parent: str = "") -> tuple[str, str]:
    step1 = text_of(await bridge.call_tool("read_chat", {"agent": agent_id, "wait_sec": 0}))
    if to_parent:
        ack = await bridge.call_tool("send_agent_message", {"agent": agent_id, "to": to_parent, "text": "收到，随时可以开始"})
    else:
        ack = await bridge.call_tool("send_message", {"agent": agent_id, "text": "在的，随时可以开始"})
    assert not ack.is_error, text_of(ack)
    step2 = text_of(await bridge.call_tool("read_chat", {"agent": agent_id, "wait_sec": 0}))
    return step1, step2


async def run_cluster_and_device_tests() -> dict[str, str]:
    now = bridge.now()
    bridge.ensure_main_conv()
    bridge.store.run(
        "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)",
        (7001, "Alpine", "admin", 7001, now),
    )
    bridge.store.run(
        "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)",
        (8002, "MemberBob", "user", 8002, now),
    )

    # 1. Verify empty / unkeyed join (nazzil / c174 misfire case) is immediately blocked with ZERO Telegram popups!
    ADMIN_NOTICES.clear()
    bad_join1 = await bridge.call_tool("join", {"name": "nazzil"})
    assert bad_join1.is_error and "缺少有效的任务码 code" in text_of(bad_join1)
    bad_join2 = await bridge.call_tool("join", {"mode": "main", "name": "nazzil"})
    assert bad_join2.is_error and "缺少有效的任务码 code" in text_of(bad_join2)
    assert ADMIN_NOTICES == [], f"False admin popup leaked on empty join: {ADMIN_NOTICES}"

    # 2. Verify dais_runtime.pyz compiled bytecode bundle works without .py source, has no plaintext IP, and self-heals hooks.json!
    pyz_ext = bridge.build_runtime_pyz("http://198.51.100.42:8787")
    assert b"198.51.100.42" not in pyz_ext, "Plaintext IP leaked in compressed dais_runtime.pyz!"
    pyz_bytes = bridge.build_runtime_pyz()
    assert len(pyz_bytes) > 500 and pyz_bytes.startswith(b"#!/usr/bin/env python3\nPK")
    pyz_file = TMP_ROOT / "dais_runtime.pyz"
    pyz_file.write_bytes(pyz_bytes)
    pyz_file.chmod(0o755)
    env = dict(os.environ, HOME=str(HOME_DIR), DAIS_SKIP_RELOAD="1")
    inst = subprocess.run([sys.executable, str(pyz_file), "install", "http://127.0.0.1:18797"], env=env, capture_output=True, text=True, check=True)
    assert "dais_runtime.pyz" in inst.stdout
    assert not (HOME_DIR / ".cursor" / "agent_trace_config.json").exists()
    hooks_path = HOME_DIR / ".cursor" / "hooks.json"
    hooks_cfg = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert "subagentStop" in hooks_cfg["hooks"] and "preToolUse" in hooks_cfg["hooks"]
    # Simulate accidental wipe of hooks.json and verify self-healing via subagentStart hook
    hooks_path.write_text("{}", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(HOME_DIR / ".cursor" / "dais_runtime.pyz"), "hook"],
        input=json.dumps({"hook_event_name": "subagentStart", "conversation_id": "cid-heal-1"}),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    healed_cfg = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert "subagentStop" in healed_cfg["hooks"] and "stop" in healed_cfg["hooks"] and "preToolUse" in healed_cfg["hooks"]
    assert healed_cfg["hooks"]["stop"][0]["loop_limit"] is None
    pid_f = HOME_DIR / ".cursor" / "agent_trace_daemon.pid"
    if pid_f.exists():
        try:
            os.kill(int(pid_f.read_text().strip()), 9)
        except Exception:
            pass

    # 3. Create two coexisting Main Agents (main1 & main2) + auto-bootstrapped singleton Controller (ctrl)
    nid1, m1 = bridge.make_main_node(custom_name="主机A")
    assert nid1 == "main1"
    # Read main1's inbox -> should have standardized [STANDARD_OP ... type="TASK_LAUNCH" chat="ctrl"]
    m1_inbox = text_of(await bridge.call_tool("read_chat", {"agent": m1, "wait_sec": 0}))
    assert 'type="TASK_LAUNCH" chat="ctrl"' in m1_inbox
    ctrl_code = bridge.conv_row("ctrl")["task_code"]
    assert ctrl_code.startswith("t-")
    res_ctrl_join = await bridge.call_tool("join", {"code": ctrl_code, "name": "总控"})
    assert not res_ctrl_join.is_error
    ctrl_ag = bridge.conv_row("ctrl")["agent"]
    assert bridge.agent_row(ctrl_ag)["role"] == "ctrl"

    # Add second Main Agent (main2) -> main1 MUST remain active!
    nid2, m2 = bridge.make_main_node(custom_name="主机B")
    assert nid2 == "main2"
    assert bridge.agent_row(m1)["status"] == "active" and bridge.agent_row(m2)["status"] == "active"

    # Simulate CPU/RAM probe metrics on main1 (heavy load) vs main2 (light load)
    bridge.store.run(
        "UPDATE exec_nodes SET metrics_json=?, metrics_ts=? WHERE id='main1'",
        (json.dumps({"cpu_cores": 8, "cpu_percent": 85.0, "load_1m": 6.8, "mem_total_mb": 16000, "mem_usable_mb": 4000, "mem_used_mb": 12000, "mem_percent": 75.0}), bridge.now()),
    )
    bridge.store.run(
        "UPDATE exec_nodes SET metrics_json=?, metrics_ts=? WHERE id='main2'",
        (json.dumps({"cpu_cores": 8, "cpu_percent": 8.0, "load_1m": 0.4, "mem_total_mb": 16000, "mem_usable_mb": 14500, "mem_used_mb": 1500, "mem_percent": 9.4, "balloon_mb": 4096}), bridge.now()),
    )

    # 4. Worker node (mode="worker" + main_key) auto-approved by ctrl WITHOUT bothering admin!
    ADMIN_NOTICES.clear()
    mkey = bridge.main_join_key()

    async def _worker_join_call():
        return await bridge.call_tool("join", {"mode": "worker", "main_key": mkey, "name": "渲染节点"})

    w_task = asyncio.create_task(_worker_join_call())
    await asyncio.sleep(0.05)
    assert ADMIN_NOTICES == [], f"Worker join bothered admin: {ADMIN_NOTICES}"
    pend_w = bridge.store.one("SELECT id FROM approvals WHERE kind='join_worker' AND status='pending'")
    assert pend_w is not None
    res_app_w = await bridge.call_tool("manage_node", {"agent": ctrl_ag, "action": "approve_worker", "request_id": pend_w["id"]})
    assert not res_app_w.is_error and "node1" in text_of(res_app_w)
    w_res = await asyncio.wait_for(w_task, timeout=3.0)
    w_welcome = text_of(w_res)
    assert "工作区常驻任务会话 node1" in w_welcome and "算力压力" not in w_welcome
    w_ag = bridge.conv_row("node1")["agent"]
    # Worker node must be cloud-only (blocked from local_shell & send_message)
    assert (await bridge.call_tool("local_shell", {"agent": w_ag, "command": "whoami"})).is_error
    assert (await bridge.call_tool("send_message", {"agent": w_ag, "text": "hi"})).is_error

    # 5. Create admin chat c1 (locked model) & external user chat c2 (verify member 5-chat ok, spawn_subagent blocked!)
    c1 = bridge.create_conv("天文台总装", 7001, name="天文台", owner=0, model="claude-fable-5-2-max")
    # Ctrl dispatches c1 with auto target_main -> should pick lighter main2!
    disp_c1 = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "launch", "target_main": "auto"})
    assert not disp_c1.is_error and "main2" in text_of(disp_c1)
    # Model change guard: ctrl trying to change c1's model without confirm_model_change=True must be blocked!
    bad_mod = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "restart", "model": "gpt-4o-mini"})
    assert bad_mod.is_error and "模型保护拦截" in text_of(bad_mod)

    # Main2 reads standardized launch op and submits task_agent_id
    m2_inbox = text_of(await bridge.call_tool("read_chat", {"agent": m2, "wait_sec": 0}))
    assert 'type="TASK_LAUNCH" chat="c1"' in m2_inbox and "claude-fable-5-2-max" in m2_inbox
    op_c1 = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE conv_id='c1' ORDER BY created_ts DESC LIMIT 1")["op_id"]
    sub_res = await bridge.call_tool("submit_op_result", {"agent": m2, "op_id": op_c1, "status": "ok", "task_agent_id": "bc_task_c1_99"})
    assert not sub_res.is_error
    assert bridge.conv_row("c1")["task_agent_id"] == "bc_task_c1_99"

    # Join no longer verifies the model & uses 2-step conversational onboarding:
    # (a) Joining c1 (record model="claude-fable-5-2-max") with only the task code succeeds right away with minimal welcome.
    c1_code = bridge.conv_row("c1")["task_code"]
    bridge.post("c1", chat_id=7001, chat_type="private", user_id=7001, user_name="Alpine", text="接入后就该看到的任务", wake=1)
    ADMIN_NOTICES.clear()
    plain_join = await bridge.call_tool("join", {"code": c1_code})
    plain_txt = text_of(plain_join)
    assert not plain_join.is_error and "接入成功" in plain_txt, plain_txt[:300]
    assert "模型校验" not in plain_txt and "actual_model" not in plain_txt and "dais_runtime" not in plain_txt
    first_ag = bridge.conv_row("c1")["agent"]
    assert bridge.conv_row("c1")["task_code"] == "" and bridge.conv_row("c1")["model_check"] == ""
    assert bridge.conv_onboard_stage(bridge.conv_row("c1")) == "icebreak_pending"
    # Step 1: read_chat delivers warm icebreak without leaking real unread messages yet
    s1_txt = text_of(await bridge.call_tool("read_chat", {"agent": first_ag, "wait_sec": 0}))
    assert "接入后就该看到的任务" not in s1_txt and "随时可以开始" in s1_txt
    assert bridge.conv_onboard_stage(bridge.conv_row("c1")) == "icebreak_waiting_reply"
    # Reply to icebreak is swallowed internally (ZERO Telegram spam!) and transitions to memory_pending
    ack_res = await bridge.call_tool("send_message", {"agent": first_ag, "text": "我来了"})
    assert not ack_res.is_error
    assert ADMIN_NOTICES == [], f"Icebreak reply leaked to Telegram: {ADMIN_NOTICES}"
    assert bridge.conv_onboard_stage(bridge.conv_row("c1")) == "memory_pending"
    # Step 2: read_chat transitions to ready, delivers context brief + pending real message!
    s2_txt = text_of(await bridge.call_tool("read_chat", {"agent": first_ag, "wait_sec": 0}))
    assert "接入后就该看到的任务" in s2_txt and "run_workspace_job" in s2_txt
    assert bridge.conv_onboard_stage(bridge.conv_row("c1")) == "ready"
    # The launch prompt no longer asks the sub-agent to report or prove its model or touch .cursor/.pyz.
    launch_txt = bridge.task_text(bridge.conv_row("c1"))
    assert "actual_model" not in launch_txt and "model_match" not in launch_txt and "校验" not in launch_txt
    assert "dais_runtime" not in launch_txt and ".cursor" not in launch_txt

    # (b) A sub-agent still holding an OLD launch prompt passes actual_model / model_match (even "false", even another
    #     model family): it joins normally, is not held, and ctrl gets no verification alert.
    await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0})
    rs_old = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "restart"})
    assert not rs_old.is_error and bridge.agent_row(first_ag)["status"] == "stopped"
    await bridge.call_tool("read_chat", {"agent": m2, "wait_sec": 0})
    legacy_join = await bridge.call_tool(
        "join", {"code": bridge.conv_row("c1")["task_code"], "actual_model": "Gemini 4 Carbon High", "model_match": False}
    )
    assert not legacy_join.is_error and "接入成功" in text_of(legacy_join)
    legacy_ag = bridge.conv_row("c1")["agent"]
    await finish_onboard(legacy_ag)
    assert bridge.conv_row("c1")["model_check"] == ""
    assert bridge.conv_row("c1")["model"] == "claude-fable-5-2-max", "a self-reported model must never rewrite the record"
    assert not (await bridge.call_tool("send_message", {"agent": legacy_ag, "text": "旧提示词也能干活"})).is_error
    ctrl_after = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    assert "模型校验" not in ctrl_after and "请主控判断" not in ctrl_after

    # (c) A chat left in the old "mismatch hold" by 3.6.0 is released at boot and its waiting agent gets the full briefing.
    bridge.store.run("UPDATE convs SET model_check='mismatch_hold', alert='模型不符待主控判断', alert_ts=? WHERE id='c1'", (bridge.now(),))
    assert bridge.release_model_holds() == 1
    assert bridge.conv_row("c1")["model_check"] == "" and bridge.conv_row("c1")["alert"] == ""
    released_inbox = text_of(await bridge.call_tool("read_chat", {"agent": legacy_ag, "wait_sec": 0}))
    assert "模型核对已经取消" in released_inbox and "read_chat" in released_inbox
    assert bridge.release_model_holds() == 0

    # Restart c1 cleanly for the remaining tests
    await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "restart", "model": "claude-fable-5-2-max"})
    await bridge.call_tool("read_chat", {"agent": m2, "wait_sec": 0})
    op_c1_final = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE conv_id='c1' ORDER BY created_ts DESC LIMIT 1")["op_id"]
    await bridge.call_tool("submit_op_result", {"agent": m2, "op_id": op_c1_final, "status": "ok", "task_agent_id": "bc_task_c1_final"})
    ok_mod_join = await bridge.call_tool("join", {"code": bridge.conv_row("c1")["task_code"]})
    assert not ok_mod_join.is_error and "接入成功" in text_of(ok_mod_join)
    a1 = bridge.conv_row("c1")["agent"]
    await finish_onboard(a1)

    # Member user chat c2 -> cannot call spawn_subagent or run_workspace_job!
    c2_mem = bridge.create_conv("外部用户聊天", 8002, name="会员聊天", owner=8002)
    await bridge.call_tool("join", {"code": c2_mem["task_code"]})
    a2_mem = bridge.conv_row("c2")["agent"]
    await finish_onboard(a2_mem)
    mem_spawn = await bridge.call_tool("spawn_subagent", {"agent": a2_mem, "brief": "偷开子agent", "include_memory": False})
    assert mem_spawn.is_error and "仅管理员本人" in text_of(mem_spawn)
    mem_job = await bridge.call_tool("run_workspace_job", {"agent": a2_mem, "command": "ls"})
    assert mem_job.is_error and "仅管理员本人" in text_of(mem_job)

    # 6. Admin c1 spawns c3 with dedicated_machine=True, ctrl locks node1 exclusively to c1, then grants access to c3!
    sp_c3 = await bridge.call_tool(
        "spawn_subagent",
        {"agent": a1, "brief": "重型光线追踪", "include_memory": True, "memory_summary": "光照参数v2", "dedicated_machine": True, "machine_reason": "需独占大内存"},
    )
    assert not sp_c3.is_error and "申请独占机器" in text_of(sp_c3)
    await bridge.call_tool("join", {"code": bridge.conv_row("c3")["task_code"], "name": "光追子工"})
    a3 = bridge.conv_row("c3")["agent"]
    await finish_onboard(a3, to_parent="c1")

    # Lock node1 exclusively to c1 -> c3 should be blocked until ctrl grants access!
    await bridge.call_tool("manage_node", {"agent": ctrl_ag, "action": "set_exclusive", "node_id": "node1", "exclusive_chat": "c1"})
    blocked_job = await bridge.call_tool("run_workspace_job", {"agent": a3, "command": "echo render", "node": "node1"})
    assert blocked_job.is_error and "已被 c1 独占锁定" in text_of(blocked_job)

    # Ctrl grants c3 shared access to node1 -> now c3 succeeds!
    await bridge.call_tool("manage_node", {"agent": ctrl_ag, "action": "grant_access", "node_id": "node1", "chats": ["c3"]})
    ok_job = await bridge.call_tool("run_workspace_job", {"agent": a3, "command": "echo render_ok", "node": "node1"})
    assert not ok_job.is_error
    w_inbox = text_of(await bridge.call_tool("read_chat", {"agent": w_ag, "wait_sec": 0}))
    assert 'type="WORKSPACE_JOB"' in w_inbox and "echo render_ok" in w_inbox
    op_w = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE target_node='node1' ORDER BY created_ts DESC LIMIT 1")["op_id"]
    await bridge.call_tool("submit_op_result", {"agent": w_ag, "op_id": op_w, "status": "ok", "output": "render_ok_4k.png"})
    c3_inbox = text_of(await bridge.call_tool("read_chat", {"agent": a3, "wait_sec": 0}))
    assert "render_ok_4k.png" in c3_inbox

    # 7. Standardized TASK_RESUME round-trip (including turn-0 interrupted credential self-healing!)
    res_op = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "resume", "resume_prompt": "看门狗探活，请确认在线并回到 read_chat 待命。"})
    assert not res_op.is_error
    op_res_row = bridge.store.one("SELECT op_id, payload_json FROM dispatch_ops WHERE op_type='resume_subagent' ORDER BY created_ts DESC LIMIT 1")
    op_res_id = op_res_row["op_id"]
    op_res_payload = json.loads(op_res_row["payload_json"])
    c1_active_ag = bridge.conv_row("c1")["agent"]
    assert f'agent="{c1_active_ag}"' in op_res_payload["prompt"], f"Missing active a_ credential in TASK_RESUME prompt: {op_res_payload}"
    assert "严格只输出 ok 两个字" in op_res_payload["prompt"]
    assert m2 not in op_res_payload["prompt"], "Launcher m_ identity leaked into child TASK_RESUME prompt!"
    await bridge.call_tool("submit_op_result", {"agent": m2, "op_id": op_res_id, "status": "ok", "output": "Task is currently running"})
    ctrl_inbox = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    assert "currently running" in ctrl_inbox

    # 8. Verify 5-minute thinking-stuck vs shell distinction!
    now2 = bridge.now()
    # Case A: c3 is in `shell` for 10 minutes (600s > 300s) -> MUST NOT be treated as thinking-stuck or restarted!
    bridge.store.run(
        "INSERT OR REPLACE INTO agent_traces(conv,agent_id,phase,tool_name,summary,detail,started_ts,updated_ts,thought_ts,hb_ts) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("c3", a3, "shell", "Shell", "blender -b scene.blend -a", "{}", now2 - 600, now2 - 600, now2 - 650, now2 - 5),
    )
    await bridge.watchdog_tick()
    assert bridge.conv_row("c3")["agent"] == a3, "Shell command was falsely killed as thinking-stuck!"

    # Case B: c1's agent joined long ago, has made no bridge call for 6 minutes, and its own probe says it has been
    # `thinking` for 6 minutes (360s > 300s) while the VM probe heartbeat is alive -> MUST auto-restart!
    def put_trace(conv_id: str, agent_id: str, phase: str, age: float, hb_age: float | None) -> None:
        t = bridge.now()
        bridge.store.run(
            "INSERT OR REPLACE INTO agent_traces(conv,agent_id,phase,tool_name,summary,detail,started_ts,updated_ts,thought_ts,hb_ts) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (conv_id, agent_id, phase, "Thought", "卡在思考", "{}", t - age, t - age, t - age, 0 if hb_age is None else t - hb_age),
        )

    def stuck(conv_id: str) -> bool:
        return bridge.check_thinking_stuck(
            bridge.conv_row(conv_id), bridge.store.one("SELECT * FROM agent_traces WHERE conv=?", (conv_id,))
        )[0]

    bridge.store.run("UPDATE agents SET created=?, last_seen=? WHERE id=?", (now2 - 4000, now2 - 400, a1))
    # B0: the probe has never sent a heartbeat for this row -> nothing to judge by, the agent is left alone.
    put_trace("c1", a1, "thinking", 360, None)
    assert not stuck("c1")
    await bridge.watchdog_tick()
    assert bridge.agent_row(a1)["status"] == "active", "agent was stopped although its probe never reported a heartbeat"
    # B1: the agent called a bridge tool a minute ago -> it is alive, the 5 minutes count from that call.
    put_trace("c1", a1, "thinking", 360, 5)
    bridge.store.run("UPDATE agents SET last_seen=? WHERE id=?", (bridge.now() - 60, a1))
    assert not stuck("c1")
    # B2: genuinely stuck >= 5m -> Watchdog MUST notify ctrl ONLY (NEVER bypass ctrl directly into main2!)
    bridge.store.run("UPDATE agents SET last_seen=? WHERE id=?", (bridge.now() - 400, a1))
    assert stuck("c1")
    await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0})
    ops_before_wd = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id='c1'")["n"]
    await bridge.watchdog_tick()
    assert bridge.agent_row(a1)["status"] == "active", "Watchdog killed agent directly instead of notifying ctrl!"
    ops_after_wd = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id='c1'")["n"]
    assert ops_after_wd == ops_before_wd, "Watchdog bypassed ctrl and enqueued direct op into mainN!"
    ctrl_wd_msg = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    assert "思考超时，请总控决策" in ctrl_wd_msg and 'action="resume"' in ctrl_wd_msg

    # B2a: Repeated tick inside cooldown MUST NOT spam ctrl again!
    await bridge.watchdog_tick()
    ctrl_wd_msg2 = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    assert "暂无新消息" in ctrl_wd_msg2, f"Watchdog spammed ctrl inside cooldown: {ctrl_wd_msg2}"

    # B2b: Ctrl explicitly dispatches restart -> c1 old agent stops and main2 gets clean TASK_LAUNCH op!
    rs_by_ctrl = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "restart", "target_main": "main2"})
    assert not rs_by_ctrl.is_error and bridge.agent_row(a1)["status"] == "stopped"
    await bridge.call_tool("read_chat", {"agent": m2, "wait_sec": 0})

    # Case C: the replacement agent must not inherit the stopped agent's trace (the 2026-11-15 false-stop storm:
    # 43 freshly joined agents were stopped as "thinking-stuck for 20-40 hours" at the first watchdog tick after join).
    class _Req:
        def __init__(self, body: dict):
            self._body = body

        async def json(self) -> dict:
            return self._body

    async def trace_event(**body) -> dict:
        resp = await bridge.trace_post_event(_Req(body))
        return json.loads(bytes(resp.body).decode("utf-8"))

    # the stopped agent's row still says `thinking`, and its old session's probe keeps the heartbeat fresh
    put_trace("c1", a1, "thinking", 30 * 3600, 5)
    # Re-join c1 after auto-restart so Web Console tests have an active c1
    await bridge.call_tool("join", {"code": bridge.conv_row("c1")["task_code"], "actual_model": "claude-fable-5-2-max", "model_match": True})
    a1_re = bridge.conv_row("c1")["agent"]
    assert a1_re != a1 and bridge.agent_row(a1_re)["status"] == "active"
    bridge.store.run("UPDATE convs SET auto_restarted_ts=0 WHERE id='c1'")
    # C1: join hands the trace row to the new agent and clears the previous agent's live state (entering onboarding).
    row_c1 = bridge.store.one("SELECT * FROM agent_traces WHERE conv='c1'")
    assert row_c1["agent_id"] == a1_re and row_c1["phase"] == "onboarding" and float(row_c1["hb_ts"] or 0) == 0
    assert row_c1["conversation_id"] == ""
    assert not stuck("c1")
    await finish_onboard(a1_re)
    # C2: a row still owned by the previous agent (e.g. written just before it was stopped) is not held against the new one.
    put_trace("c1", a1, "thinking", 30 * 3600, 5)
    assert not stuck("c1")
    await bridge.watchdog_tick()
    assert bridge.agent_row(a1_re)["status"] == "active", "new agent was stopped because of the previous agent's stale trace"
    # C3: even under the new agent's name, time before it joined does not count as its thinking time.
    put_trace("c1", a1_re, "thinking", 30 * 3600, 5)
    assert not stuck("c1")
    await bridge.watchdog_tick()
    assert bridge.agent_row(a1_re)["status"] == "active", "new agent was charged with time from before it joined"
    # C4: the stopped agent's old session (or its VM heartbeat daemon) keeps reporting -> ignored, the row stays the new agent's.
    put_trace("c1", a1_re, "shell", 10, 5)
    ev_old = await trace_event(agent_id=a1, conversation_id="conv-old-c1", event="afterAgentThought", phase="thinking", summary="旧会话还在上报")
    assert ev_old.get("ignored") and not ev_old.get("bound_agent_id")
    ev_old_hb = await trace_event(agent_id=a1, conversation_id="conv-old-c1", event="heartbeat", phase="thinking", heartbeat=True)
    assert ev_old_hb.get("ignored")
    row_c1 = bridge.store.one("SELECT * FROM agent_traces WHERE conv='c1'")
    assert row_c1["agent_id"] == a1_re and row_c1["phase"] == "shell" and row_c1["conversation_id"] != "conv-old-c1"
    # C5: a session that never reported an identity is not adopted into c1 just because its command mentions "c1".
    ev_foreign = await trace_event(conversation_id="conv-foreign", conv_hint="c1", event="beforeShellExecution", phase="shell", summary="git checkout cursor/c1-foo")
    assert ev_foreign["conv"] == "cid:conv-foreign" and ev_foreign["bound_agent_id"] == ""
    assert bridge.store.one("SELECT conversation_id FROM agent_traces WHERE conv='c1'")["conversation_id"] != "conv-foreign"
    # C6: the new agent's own session reports normally and is bound by its identity; a later event without the
    # identity (same conversation) keeps that binding.
    ev_new = await trace_event(agent_id=a1_re, conversation_id="conv-new-c1", event="afterAgentThought", phase="thinking", summary="新会话思考")
    assert ev_new["conv"] == "c1" and ev_new["bound_agent_id"] == a1_re
    ev_new2 = await trace_event(conversation_id="conv-new-c1", event="beforeShellExecution", phase="shell", summary="ls")
    assert ev_new2["conv"] == "c1" and ev_new2["bound_agent_id"] == a1_re
    row_c1 = bridge.store.one("SELECT * FROM agent_traces WHERE conv='c1'")
    assert row_c1["agent_id"] == a1_re and row_c1["conversation_id"] == "conv-new-c1" and row_c1["phase"] == "shell"
    # C7: a session wrongly recorded under another chat earlier is released once it reports its own identity.
    bridge.store.run("UPDATE agent_traces SET conversation_id='conv-new-c1' WHERE conv='c3'")
    await trace_event(agent_id=a1_re, conversation_id="conv-new-c1", event="afterAgentThought", phase="thinking", summary="继续")
    assert bridge.store.one("SELECT conversation_id FROM agent_traces WHERE conv='c3'")["conversation_id"] == ""
    assert bridge.agent_row(a1_re)["status"] == "active" and bridge.conv_row("c3")["agent"] == a3

    # 9. Verify multi-device `/device add` keeps both PCs active simultaneously!
    dev_a = await bridge.issue_device(7001, "Alpine", create_new=True, custom_label="台式工作站")
    dev_b = await bridge.issue_device(7001, "Alpine", create_new=True, custom_label="随身笔记本")
    assert dev_a["id"] != dev_b["id"]
    assert bridge.device_row(dev_a["id"])["status"] == "active"
    assert bridge.device_row(dev_b["id"])["status"] == "active"

    # 9b. Verify One-Prompt Auto-Spawning Coordinator (`mode="coordinator"` -> instant 0s join, zero "算力" wording, auto-spawns isolated worker VMs via `w-...` codes)!
    wh_join = await bridge.call_tool("join", {"mode": "coordinator", "main_key": mkey, "pool_size": 3})
    assert not wh_join.is_error
    wh_txt = text_of(wh_join)
    assert "whost1" in wh_txt and "算力" not in wh_txt
    wh_ag = bridge.node_row("whost1")["agent"]
    # node1 was already online, so pool_size=3 must auto-enqueue node2 and node3 onto whost1 (popped 1 op at a time with 0 loss)!
    wh_inbox1 = text_of(await bridge.call_tool("read_chat", {"agent": wh_ag, "wait_sec": 0}))
    wh_inbox2 = text_of(await bridge.call_tool("read_chat", {"agent": wh_ag, "wait_sec": 0}))
    assert "node2" in wh_inbox1 and "node3" not in wh_inbox1 and "独立的云工作区" in wh_inbox1
    assert "node3" in wh_inbox2 and "独立的云工作区" in wh_inbox2
    w2_code = bridge.conv_row("node2")["task_code"]
    assert w2_code.startswith("w-")
    # Newly booted VM joins with `code=w2_code` in 0ms without approval!
    n2_join = await bridge.call_tool("join", {"code": w2_code})
    assert not n2_join.is_error and "node2" in text_of(n2_join)
    assert bridge.node_row("node2")["status"] == "online"

    # Create an agent collaboration group g1 for Web Console testing
    a1_new = bridge.conv_row("c1")["agent"]
    grp_res = await bridge.call_tool(
        "create_agent_group",
        {"agent": a1_new, "name": "天文台总装群", "members": ["c3"], "topic": "多工位联调", "welcome": "全员就位"},
    )
    assert not grp_res.is_error

    # Verify cross-VM file transfer between c1 and c3 / g1 + default isolated VM param + ctrl default model
    assert bridge.conv_row("ctrl")["model"] == "deepseek max"
    assert '"environment_id"' in bridge.task_machine_param_line(True)
    sf_dm = await bridge.call_tool(
        "send_file",
        {"agent": a1_new, "filename": "mesh.obj", "text": "v 0 0 0\nv 1 0 0\n", "to_agent": "c3", "caption": "网格产物"},
    )
    assert not sf_dm.is_error and "f_" in text_of(sf_dm)
    c3_ag_curr = bridge.conv_row("c3")["agent"]
    c3_inbox = text_of(await bridge.call_tool("read_chat", {"agent": c3_ag_curr, "wait_sec": 0}))
    assert "mesh.obj" in c3_inbox and "网格产物" in c3_inbox
    import re as _re360
    fid_hit = _re360.search(r"(f_[0-9a-f]+)", c3_inbox).group(1)
    gf_inline = await bridge.call_tool("get_file", {"agent": c3_ag_curr, "file_id": fid_hit, "inline": True})
    assert not gf_inline.is_error and "v 0 0 0" in text_of(gf_inline)

    return {"ctrl": ctrl_ag, "c1": "c1", "c3": "c3"}


def run_web_console_tests() -> None:
    secret_pw = "SuperSecret_ZWT_#2026!"
    with TestClient(bridge.app) as client:
        # 1. GET /web renders HTML, and /web/api/auth/status shows zwt_needs_setup=True
        html_res = client.get("/web")
        assert html_res.status_code == 200 and "Bridge Studio" in html_res.text

        st = client.get("/web/api/auth/status").json()
        assert st["ok"] and not st["authenticated"] and st["zwt_needs_setup"] is True

        # 2. First visit with zwt sets password (PBKDF2 hashed, never logged in bridge.log!)
        setup_res = client.post("/web/api/auth/setup-zwt", json={"username": "zwt", "password": secret_pw})
        assert setup_res.status_code == 200 and setup_res.json()["ok"] is True
        # Second attempt to setup-zwt must be rejected with 409
        dup_setup = client.post("/web/api/auth/setup-zwt", json={"username": "zwt", "password": "otherpassword"})
        assert dup_setup.status_code == 409

        # Verify stored hash is PBKDF2 and plaintext password NEVER appears in DB or bridge.log!
        db_pw = bridge.store.one("SELECT password_hash FROM web_users WHERE username='zwt'")["password_hash"]
        assert db_pw.startswith("pbkdf2_sha256$") and secret_pw not in db_pw
        log_file = DATA_DIR / "bridge.log"
        if log_file.exists():
            assert secret_pw not in log_file.read_text(encoding="utf-8", errors="replace")

        # 3. Bootstrap returns ctrl, main1, main2, c1, c3, g1, and CPU/RAM node probes
        boot = client.get("/web/api/bootstrap").json()
        assert boot["ok"]
        conv_ids = [c["id"] for c in boot["convs"]]
        assert "ctrl" in conv_ids and "main1" in conv_ids and "main2" in conv_ids and "c1" in conv_ids
        assert any(g["id"] == "g1" for g in boot["groups"])
        assert any(n["id"] == "main2" and n["metrics"].get("balloon_mb") == 4096 for n in boot["nodes"])

        # 4. Upload image/file via binary upload endpoint, send message, edit message, delete message!
        png_stub = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 32
        up = client.post(
            "/web/api/upload?conv=c1",
            content=png_stub,
            headers={"X-File-Name": "blueprint.png", "X-File-Mime": "image/png"},
        ).json()
        assert up["ok"] and up["file"]["is_image"] is True
        fid = up["file"]["file_id"]

        send_m = client.post("/web/api/convs/c1/messages", json={"text": "初版草图说明", "file_ids": [fid]}).json()
        assert send_m["ok"] and len(send_m["message_ids"]) == 1
        mid = send_m["message_ids"][0]

        # Serve uploaded image back
        img_resp = client.get(f"/web/api/files/{fid}")
        assert img_resp.status_code == 200 and img_resp.content == png_stub

        # Edit message in c1
        ed = client.patch(f"/web/api/messages/{mid}", json={"text": "修正后的终版蓝图说明"}).json()
        assert ed["ok"] and ed["text"] == "修正后的终版蓝图说明"
        msgs_after_edit = client.get("/web/api/convs/c1/messages").json()["messages"]
        assert any(m["id"] == mid and m["text"] == "修正后的终版蓝图说明" for m in msgs_after_edit)

        # Send a noise message and delete it
        noise_mid = client.post("/web/api/convs/c1/messages", json={"text": "误发的一句话"}).json()["message_ids"][0]
        del_r = client.delete(f"/web/api/messages/{noise_mid}").json()
        assert del_r["ok"]
        msgs_after_del = client.get("/web/api/convs/c1/messages").json()["messages"]
        assert all(m["id"] != noise_mid for m in msgs_after_del)

        # 5. One-click Restart in Web Console -> must route FULL context dossier (model, edited history, groups, children) to ctrl!
        rs = client.post("/web/api/convs/c1/restart", json={"target_main": "main2", "note": "已删掉误发消息，按终版蓝图重跑"}).json()
        assert rs["ok"] and rs["routed_to"] == "ctrl"
        ctrl_ag = bridge.conv_row("ctrl")["agent"]
        ctrl_msg = asyncio.run(bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
        dossier_txt = text_of(ctrl_msg)
        assert "全量上下文档案" in dossier_txt
        assert "claude-fable-5-2-max" in dossier_txt
        assert "修正后的终版蓝图说明" in dossier_txt
        assert "误发的一句话" not in dossier_txt
        assert "g1「天文台总装群」" in dossier_txt
        assert "已删掉误发消息，按终版蓝图重跑" in dossier_txt

        # 6. View Agent Collaboration Group g1 and post message + image directly into g1!
        g1_post = client.post(
            "/web/api/groups/g1/messages",
            json={"text": "请 c3 重点核对高光反射", "file_ids": [fid], "mentions": ["c3"]},
        ).json()
        assert g1_post["ok"] and g1_post["woke"] == ["c3"]
        g1_view = client.get("/web/api/groups/g1/messages").json()
        assert any("请 c3 重点核对高光反射" in m["text"] for m in g1_view["messages"])

        # Verify channel filtering & channel_counts on /web/api/convs/c1/messages
        c1_all = client.get("/web/api/convs/c1/messages?channel=all").json()
        assert c1_all["ok"] and "channel_counts" in c1_all and c1_all["channel_counts"]["human"] >= 1
        c1_human = client.get("/web/api/convs/c1/messages?channel=human").json()
        assert c1_human["ok"] and all(m["channel"] == "human" for m in c1_human["messages"])

        # 7. Strict zwt-only User Management verification!
        sub_pw = "AlicePass_123"
        cr_u = client.post("/web/api/users", json={"username": "alice", "display_name": "Alice", "password": sub_pw}).json()
        assert cr_u["ok"]
        u_list = client.get("/web/api/users").json()
        assert u_list["ok"] and any(u["username"] == "alice" for u in u_list["users"])

        # Login as alice in an isolated client -> alice MUST get 403 on /web/api/users and CANNOT see zwt's c1 or ctrl!
        with TestClient(bridge.app) as alice_client:
            al_login = alice_client.post("/web/api/auth/login", json={"username": "alice", "password": sub_pw}).json()
            assert al_login["ok"] and al_login["user"]["is_zwt"] is False
            assert alice_client.get("/web/api/users").status_code == 403
            assert alice_client.post("/web/api/users", json={"username": "eve", "password": "123456"}).status_code == 403
            assert alice_client.get("/web/api/convs/c1/messages").status_code == 403
            al_boot = alice_client.get("/web/api/bootstrap").json()
            assert al_boot["convs"] == [] and al_boot["nodes"] == []

            # 8. Grant alice shared access to c1 + create shared group g2 (alice + zwt + c1)
            g_create = client.post(
                "/web/api/groups",
                json={"name": "Alice·zwt·c1", "members": ["c1"], "web_users": ["alice"], "topic": "共享协作"},
            ).json()
            assert g_create["ok"] and g_create["group_id"] == "g2" and "alice" in g_create["web_users"]
            up_u = client.post("/web/api/users", json={"username": "alice", "display_name": "Alice", "allowed_convs": ["c1"], "allowed_groups": ["g2"]}).json()
            assert up_u["ok"]
            al_boot2 = alice_client.get("/web/api/bootstrap").json()
            assert any(c["id"] == "c1" for c in al_boot2["convs"])
            assert any(g["id"] == "g2" for g in al_boot2["groups"])
            assert alice_client.get("/web/api/convs/ctrl/messages").status_code == 403
            assert alice_client.get("/web/api/convs/c1/messages").status_code == 200
            al_gpost = alice_client.post("/web/api/groups/g2/messages", json={"text": "我是Alice，在共享群发言", "mentions": ["c1"]}).json()
            assert al_gpost["ok"] and al_gpost["woke"] == ["c1"]

            # 9. Verify owner:0 shared AI files, SVG images, outbox [发送文件 ...] (both delivered=1 & legacy extra=''),
            #    default channel='human' filtering out subagent/group noise, after_id delta, reply_to_id & SSE!
            c1_live_ag = bridge.conv_row("c1")["agent"]
            if not c1_live_ag:
                tcode_c1 = bridge.issue_task("c1")
                j_c1 = asyncio.run(bridge.call_tool("join", {"code": tcode_c1, "name": "天文台"}))
                assert not j_c1.is_error
                c1_live_ag = bridge.conv_row("c1")["agent"]
                asyncio.run(finish_onboard(c1_live_ag))

            # AI sends SVG image to group g2 (creates owner:0 file) -> alice MUST load & download 200 OK (no 403!)
            svg_body = "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>"
            sf_grp = asyncio.run(
                bridge.call_tool("send_file", {"agent": c1_live_ag, "filename": "nesting.svg", "text": svg_body, "to_group": "g2", "caption": "排料图"})
            )
            assert not sf_grp.is_error
            g2_msgs = alice_client.get("/web/api/groups/g2/messages").json()["messages"]
            svg_msg = next(m for m in g2_msgs if "nesting.svg" in m["text"] or (m["file"] and m["file"]["name"] == "nesting.svg"))
            assert svg_msg["file"]["is_image"] is True and svg_msg["file"]["mime"] == "image/svg+xml"
            al_svg_get = alice_client.get(svg_msg["file"]["url"])
            assert al_svg_get.status_code == 200 and b"<svg" in al_svg_get.content
            al_svg_dl = alice_client.get(svg_msg["file"]["download_url"])
            assert al_svg_dl.status_code == 200 and "attachment" in al_svg_dl.headers.get("content-disposition", "")
            # Even raw /web/api/files/<fid> without ?sig= must allow alice via _can_user_read_file!
            assert alice_client.get(f"/web/api/files/{svg_msg['file']['file_id']}").status_code == 200

            # AI sends file directly to selected TG chat (delivered=1) + simulate legacy historical [发送文件 ...] with extra=''
            bridge.store.set("sel:7001", "c1")
            sf_tg = asyncio.run(
                bridge.call_tool("send_file", {"agent": c1_live_ag, "filename": "report_v2.txt", "text": "score=4.8420", "caption": "最新成绩单"})
            )
            assert not sf_tg.is_error
            legacy_p = DATA_DIR / "outbox" / "aabbccddeeff_legacy_plot.png"
            legacy_p.write_bytes(png_stub)
            bridge.store.insert_message(
                chat_id=7001, chat_type="private", user_id=999000, user_name="天文台",
                text="[发送文件 legacy_plot.png] 历史无extra图片", outgoing=1, target="c1", conv="c1", delivered=1, extra=""
            )

            # Inject subagent noise (agent_dm) into c1 -> default GET /web/api/convs/c1/messages MUST stay pure 'human'!
            c3_live_ag = bridge.conv_row("c3")["agent"]
            asyncio.run(bridge.call_tool("send_agent_message", {"agent": c3_live_ag, "to": "c1", "text": "内部子工汇报杂音", "wake": False}))

            zwt_c1_default = client.get("/web/api/convs/c1/messages").json()
            assert zwt_c1_default["channel"] == "human"
            assert all(m["channel"] == "human" for m in zwt_c1_default["messages"])
            assert all("内部子工汇报杂音" not in m["text"] for m in zwt_c1_default["messages"])
            assert any(m["file"] and m["file"]["name"] == "report_v2.txt" for m in zwt_c1_default["messages"])
            legacy_hit = next(m for m in zwt_c1_default["messages"] if "legacy_plot.png" in m["text"])
            assert legacy_hit["file"] is not None and legacy_hit["file"]["is_image"] is True
            assert alice_client.get(legacy_hit["file"]["download_url"]).status_code == 200

            # Alice attempting ?channel=all on c1 is still strictly locked to 'human'!
            al_c1_try_all = alice_client.get("/web/api/convs/c1/messages?channel=all").json()
            assert al_c1_try_all["channel"] == "human" and all(m["channel"] == "human" for m in al_c1_try_all["messages"])

            # Verify reply_to_id & after_id delta & SSE /web/api/events?once=1
            prev_max = max(m["id"] for m in zwt_c1_default["messages"])
            q_rep = client.post("/web/api/convs/c1/messages", json={"text": "收到这张历史图", "reply_to_id": legacy_hit["id"]}).json()
            assert q_rep["ok"] and q_rep["messages"][0]["text"].startswith(f"> [引用 #{legacy_hit['id']}")
            delta_res = client.get(f"/web/api/convs/c1/messages?after_id={prev_max}").json()
            assert len(delta_res["messages"]) == 1 and delta_res["messages"][0]["id"] == q_rep["message_ids"][0]
            sse_res = client.get("/web/api/events?conv=c1&once=1")
            assert sse_res.status_code == 200 and "event: sync" in sse_res.text

            # 10. Verify zero-token pure-Python worker process (/worker/claim + /worker/complete + storm-guard)!
            n2_ag = bridge.node_row("node2")["agent"]
            msg_cnt_before = bridge.store.one("SELECT COUNT(*) AS n FROM messages WHERE target='node2'")["n"]
            # Node2's Python worker daemon polls /worker/claim -> marks worker_daemon_ts alive
            claim_idle = client.post("/worker/claim", json={"wait_sec": 0, "metrics": {"cpu_percent": 4.2}}, headers={"X-Agent": n2_ag}).json()
            assert claim_idle["ok"] and claim_idle["job"] is None
            assert bridge.worker_daemon_is_alive("node2")

            # Dispatch a workspace_job onto node2 -> MUST NOT write into node2's LLM messages inbox (0 LLM tokens!)
            c3_ag_now = bridge.conv_row("c3")["agent"]
            jb_res = asyncio.run(
                bridge.call_tool("run_workspace_job", {"agent": c3_ag_now, "command": "echo DIRECT_PY_DAEMON_99", "node": "node2"})
            )
            assert not jb_res.is_error
            msg_cnt_after = bridge.store.one("SELECT COUNT(*) AS n FROM messages WHERE target='node2'")["n"]
            assert msg_cnt_after == msg_cnt_before, "workspace_job leaked into node LLM inbox despite active Python daemon!"

            # Python worker daemon claims job, executes via _execute_worker_job, and posts to /worker/complete
            claim_got = client.post("/worker/claim", json={"wait_sec": 0}, headers={"X-Agent": n2_ag}).json()
            assert claim_got["ok"] and claim_got["job"]["command"] == "echo DIRECT_PY_DAEMON_99"
            import agent_trace as _at
            st_s, rc_v, out_s = _at._execute_worker_job(n2_ag, "http://127.0.0.1:18797", "node2", claim_got["job"])
            assert st_s == "ok" and rc_v == 0 and "DIRECT_PY_DAEMON_99" in out_s
            comp_res = client.post(
                "/worker/complete",
                json={"op_id": claim_got["job"]["op_id"], "status": st_s, "exit_code": rc_v, "output": out_s},
                headers={"X-Agent": n2_ag},
            ).json()
            assert comp_res["ok"] and comp_res["delivered_to"] == "c3"
            c3_got = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": c3_ag_now, "wait_sec": 0})))
            assert "DIRECT_PY_DAEMON_99" in c3_got and "node2" in c3_got

            # 11. Verify mainN iron rules on every response + permission hard-lock + top-level stop hook + old-main watchdog silence + non-admin TG mute!
            m2_ag = bridge.node_row("main2")["agent"]
            # 11a: mainN forbidden from reading chat_history("c1") & calling stop_agent / restart_agent while ctrl active; EVERY response carries EXECUTOR_FIXED_FOOTER!
            ch_deny = asyncio.run(bridge.call_tool("chat_history", {"agent": m2_ag, "chat": "c1"}))
            assert ch_deny.is_error and "严禁查看任何开的 chat" in text_of(ch_deny) and "【主Agent铁律·每次必遵】" in text_of(ch_deny)
            st_deny = asyncio.run(bridge.call_tool("stop_agent", {"agent": m2_ag, "chat": "c1"}))
            assert st_deny.is_error and "严禁自行调用 stop_agent" in text_of(st_deny) and "【主Agent铁律·每次必遵】" in text_of(st_deny)
            rs_deny = asyncio.run(bridge.call_tool("restart_agent", {"agent": m2_ag, "chat": "c1"}))
            assert rs_deny.is_error and "严禁自行调用 restart_agent" in text_of(rs_deny) and "【主Agent铁律·每次必遵】" in text_of(rs_deny)
            rc_peek = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": m2_ag, "wait_sec": 0})))
            assert "【主Agent铁律·每次必遵】" in rc_peek
            rc_renew = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": m2_ag, "wait_sec": 1})))
            assert "【续棒" in rc_renew and "【主Agent铁律·每次必遵】" in rc_renew
            std_op_sample = bridge.format_standard_launch_op("op_t1", m2_ag, "c1", "prompt", "deepseek max")
            assert "可先暂缓并询问管理员" not in std_op_sample and "【执行铁律" in std_op_sample

            # 11b: Top-level Cursor `stop` hook blocks active m_... executor from ending its turn!
            chk_m2 = client.get(f"/trace/check-active?agent={m2_ag}").json()
            assert chk_m2["active"] is True and chk_m2["conv"] == "main2"
            from http.server import BaseHTTPRequestHandler, HTTPServer
            import threading

            class _BridgeProxy(BaseHTTPRequestHandler):
                def do_GET(self):
                    r = client.get(self.path)
                    self.send_response(r.status_code)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(r.content)

                def do_POST(self):
                    ln = int(self.headers.get("Content-Length") or 0)
                    body = self.rfile.read(ln) if ln else b"{}"
                    r = client.post(self.path, content=body, headers={"Content-Type": "application/json"})
                    self.send_response(r.status_code)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(r.content)

                def log_message(self, *args):
                    pass

            proxy_srv = HTTPServer(("127.0.0.1", 0), _BridgeProxy)
            proxy_port = proxy_srv.server_address[1]
            threading.Thread(target=proxy_srv.serve_forever, daemon=True).start()
            try:
                hook_env = dict(os.environ, HOME=str(HOME_DIR), BRIDGE_URL=f"http://127.0.0.1:{proxy_port}", DAIS_SKIP_RELOAD="1")
                post_tool_out = subprocess.run(
                    [sys.executable, str(HOME_DIR / ".cursor" / "dais_runtime.pyz"), "hook"],
                    input=json.dumps({
                        "hook_event_name": "postToolUse",
                        "conversation_id": "main2-top-conv",
                        "tool_name": "CallDynamicTool",
                        "tool_input": {"toolName": "submit_op_result", "arguments": {"agent": m2_ag}},
                    }),
                    env=hook_env, capture_output=True, text=True, check=True,
                )
                post_tool_json = json.loads(post_tool_out.stdout.strip() or "{}")
                assert "纯单据执行器" in post_tool_json.get("additional_context", "")
                stop_hook_out = subprocess.run(
                    [sys.executable, str(HOME_DIR / ".cursor" / "dais_runtime.pyz"), "hook"],
                    input=json.dumps({
                        "hook_event_name": "stop",
                        "conversation_id": "main2-top-conv",
                    }),
                    env=hook_env, capture_output=True, text=True, check=True,
                )
                stop_json = json.loads(stop_hook_out.stdout.strip() or "{}")
                # v3.7.2: top-level `stop` MUST NOT inject followup_message (keep strictly 1 user message in Cursor!)
                assert stop_json == {}, f"Top-level stop wrongly injected followup_message: {stop_json}"
            finally:
                proxy_srv.shutdown()
                pid_f2 = HOME_DIR / ".cursor" / "agent_trace_daemon.pid"
                if pid_f2.exists():
                    try:
                        os.kill(int(pid_f2.read_text().strip()), 9)
                    except Exception:
                        pass

            # 11c: Old offline main1 (cloud 1) retirement & zero watchdog harassment (neither hijacked to cloud 2 nor alerting ctrl)!
            m1_old_ag = bridge.node_row("main1")["agent"]
            bridge.store.run("UPDATE exec_nodes SET last_seen=? WHERE id='main1'", (bridge.now() - 99999,))
            bridge.store.run("UPDATE agents SET last_seen=? WHERE id=?", (bridge.now() - 99999, m1_old_ag))
            bridge.STARTED = bridge.now() - 99999
            bridge.reap_offline_exec_nodes()
            assert bridge.node_row("main1")["status"] == "offline"
            assert bridge.agent_row(m1_old_ag)["status"] == "stopped"
            assert int(bridge.conv_row("main1")["in_tg"] or 0) == 0

            # Put an unclaimed chat & a thinking-stuck chat in dead cloud 1 -> watchdog_tick MUST ignore them completely!
            bridge.store.run(
                "INSERT INTO convs(id,num,name,status,read_cursor,created,cloud,task_code,task_ts,in_tg) VALUES('c99',99,'旧主遗留','open',0,?,1,'t-olddead99',?,1)",
                (bridge.now() - 7200, bridge.now() - 7200),
            )
            ctrl_max_before = bridge.store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages WHERE target='ctrl'")["n"]
            asyncio.run(bridge.watchdog_tick())
            assert bridge.conv_row("c99")["cloud"] == 1, "Dead old main's unclaimed chat was hijacked into new cloud!"
            ctrl_new_wd = bridge.store.q(
                "SELECT text FROM messages WHERE target='ctrl' AND id>? AND text LIKE '%c99%'",
                (ctrl_max_before,),
            )
            assert ctrl_new_wd == [], f"Dead cloud chat c99 triggered watchdog harassment: {ctrl_new_wd}"

            # 11d: Non-admin Telegram silence (/muteusers on)
            tg_sent_calls: list[tuple[str, dict]] = []
            orig_try_call = bridge.tg.try_call

            async def _spy_try_call(method: str, **kw):
                tg_sent_calls.append((method, kw))
                return {"message_id": 88001}

            bridge.tg.try_call = _spy_try_call
            try:
                asyncio.run(bridge.on_message({
                    "message_id": 501,
                    "from": {"id": 7001, "first_name": "Admin", "is_bot": False},
                    "chat": {"id": 7001, "type": "private"},
                    "text": "/muteusers on",
                }))
                assert bridge.tg_non_admin_muted() is True
                tg_sent_calls.clear()

                # Non-admin granted user 8002 sends DM, command, and group @bot mention -> ZERO TG calls!
                asyncio.run(bridge.on_message({
                    "message_id": 502,
                    "from": {"id": 8002, "first_name": "Member", "is_bot": False},
                    "chat": {"id": 8002, "type": "private"},
                    "text": "Hello are you there?",
                }))
                asyncio.run(bridge.on_message({
                    "message_id": 503,
                    "from": {"id": 8099, "first_name": "Stranger", "is_bot": False},
                    "chat": {"id": 8099, "type": "private"},
                    "text": "/start",
                }))
                asyncio.run(bridge.on_message({
                    "message_id": 504,
                    "from": {"id": 8002, "first_name": "Member", "is_bot": False},
                    "chat": {"id": -50099, "type": "group", "title": "UserGroup"},
                    "text": "@test360_bot wake up",
                }))
                assert tg_sent_calls == [], f"Muted non-admin TG user triggered bot output: {tg_sent_calls}"
            finally:
                bridge.set_tg_non_admin_muted(False)
                bridge.tg.try_call = orig_try_call

            # 12. Verify subagents default to shared host (isolated_vm=False), compute pool / explicit isolated_vm uses env_id auto-discovery + binding, & zero-restart hot runtime upgrade!
            # 12a-0: By default, launching subagent c1 uses shared mode (no machine.environment_id, no dais_runtime.pyz in task_text)
            assert bridge.node_row("main2")["env_id"] == ""
            ctrl_now = bridge.conv_row("ctrl")["agent"]
            d_shared = asyncio.run(bridge.call_tool("dispatch_task_op", {"agent": ctrl_now, "chat": "c1", "action": "restart", "target_main": "main2"}))
            assert not d_shared.is_error and "共享运行" in text_of(d_shared)
            m2_op_shared = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": m2_ag, "wait_sec": 0})))
            assert '"environment_id"' not in m2_op_shared and "dais_runtime.pyz" not in m2_op_shared

            # 12a: Explicit isolated_vm=True on unbound main2 triggers auto-discover via environment-info (NOT foreign hardcoded 835bda67)
            d_unbound = asyncio.run(bridge.call_tool("dispatch_task_op", {"agent": ctrl_now, "chat": "c1", "action": "restart", "target_main": "main2", "isolated_vm": True}))
            assert not d_unbound.is_error
            m2_op_txt1 = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": m2_ag, "wait_sec": 0})))
            assert "environment-info" in m2_op_txt1 and "835bda67" not in m2_op_txt1
            assert "dais_runtime.pyz install" not in m2_op_txt1  # Subagent task_text is pure whiteboard!
            op1_row = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE target_node='main2' ORDER BY created_ts DESC LIMIT 1")
            # main2 reports its own account's environmentPublicId once via submit_op_result -> auto-bound!
            asyncio.run(bridge.call_tool("submit_op_result", {
                "agent": m2_ag,
                "op_id": op1_row["op_id"],
                "status": "ok",
                "task_agent_id": "bc-auto-env-1",
                "environment_id": "704ce73e-e1d4-11f1-8120-06b44be262b7",
            }))
            assert bridge.node_row("main2")["env_id"] == "704ce73e-e1d4-11f1-8120-06b44be262b7"
            # Next explicit isolated_vm=True dispatch onto main2 directly injects main2's bound environment_id with zero hesitation!
            d_bound = asyncio.run(bridge.call_tool("dispatch_task_op", {"agent": ctrl_now, "chat": "c1", "action": "restart", "target_main": "main2", "isolated_vm": True}))
            assert not d_bound.is_error and "704ce73e" in text_of(d_bound)
            m2_op_txt2 = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": m2_ag, "wait_sec": 0})))
            assert '"environment_id": "704ce73e-e1d4-11f1-8120-06b44be262b7"' in m2_op_txt2

            # 12b: Zero-restart hot runtime upgrade via /trace/runtime-version + maybe_hot_upgrade_runtime!
            rv = client.get("/trace/runtime-version").json()
            assert rv["ok"] and len(rv["sha256"]) == 64
            proxy_srv2 = HTTPServer(("127.0.0.1", 0), _BridgeProxy)
            proxy_port2 = proxy_srv2.server_address[1]
            threading.Thread(target=proxy_srv2.serve_forever, daemon=True).start()
            try:
                installed_pyz = HOME_DIR / ".cursor" / "dais_runtime.pyz"
                installed_pyz.write_bytes(b"stale-old-runtime-bytes")
                (HOME_DIR / ".cursor" / "hooks.json").write_text("{}", encoding="utf-8")
                os.environ["DAIS_SKIP_RELOAD"] = "1"
                old_home = _at.CURSOR_DIR
                _at.CURSOR_DIR = HOME_DIR / ".cursor"
                try:
                    upgraded = _at.maybe_hot_upgrade_runtime(f"http://127.0.0.1:{proxy_port2}")
                finally:
                    _at.CURSOR_DIR = old_home
                assert upgraded is True
                import hashlib as _hl
                assert _hl.sha256(installed_pyz.read_bytes()).hexdigest() == rv["sha256"]
                rebuilt_hooks = json.loads((HOME_DIR / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
                assert "stop" in rebuilt_hooks["hooks"] and rebuilt_hooks["hooks"]["stop"][0]["loop_limit"] is None
            finally:
                proxy_srv2.shutdown()
                pid_f3 = HOME_DIR / ".cursor" / "agent_trace_daemon.pid"
                if pid_f3.exists():
                    try:
                        os.kill(int(pid_f3.read_text().strip()), 9)
                    except Exception:
                        pass

            # 12c: Verify incoming message to dormant pod notifies ctrl ONLY (NO direct main2 TASK_RESUME bypass!)
            c1_code_now = bridge.conv_row("c1")["task_code"]
            asyncio.run(bridge.call_tool("join", {"code": c1_code_now}))
            c1_ag_ev = bridge.conv_row("c1")["agent"]
            asyncio.run(finish_onboard(c1_ag_ev))
            bridge.store.run("UPDATE convs SET task_agent_id='bc-evicted-pod-99' WHERE id='c1'")
            bridge.store.run("UPDATE agents SET last_seen=? WHERE id=?", (bridge.now() - 600, c1_ag_ev))
            bridge.store.run(
                "UPDATE agent_traces SET hb_ts=?, updated_ts=?, phase='thinking' WHERE conv='c1'",
                (bridge.now() - 600, bridge.now() - 600),
            )
            bridge._msg_auto_wake_ts.clear()
            ctrl_cur_ag = bridge.conv_row("ctrl")["agent"]
            asyncio.run(bridge.call_tool("read_chat", {"agent": ctrl_cur_ag, "wait_sec": 0}))
            ops_before_wake = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id='c1' AND op_type='resume_subagent'")["n"]
            bridge.post("c1", chat_id=7001, chat_type="private", user_id=7001, user_name="Alpine", text="休眠容器通知总控测试", wake=1)
            ops_after_wake = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id='c1' AND op_type='resume_subagent'")["n"]
            assert ops_after_wake == ops_before_wake, "auto_msg_wake bypassed ctrl directly into main2!"
            ctrl_wake_note = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": ctrl_cur_ag, "wait_sec": 0})))
            assert "休眠会话收到新消息，请总控决策" in ctrl_wake_note and "c1" in ctrl_wake_note

            # 12d: Verify rogue spawned subagent cid ('bc-auto-env-1') impersonating m2_ag is surgically denied & evicted while real main2 ('main2-top-conv') is unharmed!
            pk_rogue = client.get(f"/trace/peek?agent={m2_ag}&cid=bc-auto-env-1").json()
            assert pk_rogue["stopped"] is True and pk_rogue.get("hijack") is True
            pk_real = client.get(f"/trace/peek?agent={m2_ag}&cid=main2-top-conv").json()
            assert not pk_real.get("stopped")
            chk_rogue = client.get(f"/trace/check-active?agent={m2_ag}&cid=bc-auto-env-1").json()
            assert chk_rogue["active"] is False and chk_rogue.get("hijack") is True

        if log_file.exists():
            log_txt = log_file.read_text(encoding="utf-8", errors="replace")
            assert secret_pw not in log_txt and sub_pw not in log_txt


def run_stealth_and_onboarding_370_tests() -> None:
    """Verify 3.7.0: root vault + /etc/cursor/hooks.json + UNIX socket relay, critical file & sudo blocking,
    afterMCPExecution result_json join extraction, and 4-stage onboarding tracking across all endpoints."""
    import re as _re370
    sys_root = TMP_ROOT / "sys_vault_test"
    vault_d = sys_root / "vault"
    sys_hooks = sys_root / "etc_cursor" / "hooks.json"
    relay_bin = sys_root / "libexec" / "cursor-hook-relay"
    sock_p = sys_root / "run" / "hook.sock"
    user_dot = sys_root / "user_home" / ".cursor"
    user_dot.mkdir(parents=True, exist_ok=True)
    # Seed legacy ~/.cursor artifacts to verify migration & cleanup
    (user_dot / "dais_runtime.pyz").write_bytes(b"old-pyz")
    (user_dot / "agent_trace_config.json").write_text("{}", encoding="utf-8")
    (user_dot / "agent_trace_state.json").write_text(
        json.dumps({"conv_to_agent": {"legacy-cid-1": "m_legacy_keep"}, "sessions": {}}),
        encoding="utf-8",
    )
    (user_dot / "hooks.json").write_text(
        json.dumps({"version": 1, "hooks": {"stop": [{"command": "python3 ~/.cursor/dais_runtime.pyz hook"}], "custom": [{"command": "echo keep-me"}]}}),
        encoding="utf-8",
    )

    pyz_bytes = bridge.build_runtime_pyz("http://127.0.0.1:18797")
    # Use an extensionless mktemp-style path (reproducing the v3.7.0 main17 bug where suffix != '.pyz' saved agent_trace.py!)
    pyz_src = sys_root / ".cr_rt_noext"
    pyz_src.write_bytes(pyz_bytes)
    pyz_src.chmod(0o755)

    sys_env = dict(
        os.environ,
        HOME=str(sys_root / "user_home"),
        DAIS_SYSTEM_MODE="1",
        DAIS_VAULT_DIR=str(vault_d),
        DAIS_SYS_HOOKS_PATH=str(sys_hooks),
        DAIS_RELAY_PATH=str(relay_bin),
        DAIS_SOCK_PATH=str(sock_p),
        DAIS_USER_CURSOR_DIR=str(user_dot),
        DAIS_SKIP_RELOAD="1",
        BRIDGE_URL="http://127.0.0.1:18797",
    )

    sudoers_mock = sys_root / "etc_sudoers_mock"
    (sudoers_mock / "sudoers.d").mkdir(parents=True, exist_ok=True)
    (sudoers_mock / "sudoers").write_text("root ALL=(ALL:ALL) ALL\n%sudo ALL=(ALL:ALL) ALL\n", encoding="utf-8")
    (sudoers_mock / "sudoers.d" / "ubuntu").write_text("ubuntu ALL=(ALL) NOPASSWD:ALL\n", encoding="utf-8")
    (sudoers_mock / "sudoers.d" / "README").write_text("# readme NOPASSWD: should remain untouched\n", encoding="utf-8")
    sys_env["DAIS_TEST_SUDOERS_DIR"] = str(sudoers_mock)

    with TestClient(bridge.app) as client:
        lg = client.post("/web/api/auth/login", json={"username": "zwt", "password": "SuperSecret_ZWT_#2026!"}).json()
        assert lg["ok"]
        # Seed an active main1 executor so /trace/sudo-cred can be tested end-to-end through install --system!
        _, m_sudo_ag = bridge.make_main_node(custom_name="主Agent-1")
        sys_env["DAIS_AGENT_ID"] = m_sudo_ag
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading as _th

        class _Pxy(BaseHTTPRequestHandler):
            def do_GET(self):
                hdrs = {}
                if self.headers.get("X-Agent"):
                    hdrs["X-Agent"] = self.headers["X-Agent"]
                r = client.get(self.path, headers=hdrs)
                self.send_response(r.status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(r.content)

            def do_POST(self):
                ln = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(ln) if ln else b"{}"
                hdrs = {"Content-Type": "application/json"}
                if self.headers.get("X-Agent"):
                    hdrs["X-Agent"] = self.headers["X-Agent"]
                r = client.post(self.path, content=body, headers=hdrs)
                self.send_response(r.status_code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(r.content)

            def log_message(self, *args):
                pass

        pxy = HTTPServer(("127.0.0.1", 0), _Pxy)
        pxy_port = pxy.server_address[1]
        _th.Thread(target=pxy.serve_forever, daemon=True).start()
        sys_env["BRIDGE_URL"] = f"http://127.0.0.1:{pxy_port}"

        try:
            # 1. Install into vault + /etc/cursor/hooks.json + UNIX socket relay (from extensionless mktemp file!)
            inst = subprocess.run(
                [sys.executable, str(pyz_src), "install", "--system", f"http://127.0.0.1:{pxy_port}"],
                env=sys_env, capture_output=True, text=True, check=True,
            )
            assert (vault_d / "runtime.pyz").exists(), "Extensionless zipapp was NOT saved as runtime.pyz!"
            assert not (vault_d / "agent_trace.py").exists(), "Zipapp leaked as agent_trace.py!"
            assert sys_hooks.exists() and relay_bin.exists()
            assert sock_p.exists()
            # Legacy ~/.cursor artifacts must be scrubbed, while unrelated user hook ("echo keep-me") is preserved!
            assert not (user_dot / "dais_runtime.pyz").exists()
            assert not (user_dot / "agent_trace_config.json").exists()
            assert not (user_dot / "agent_trace_state.json").exists()
            u_hooks = json.loads((user_dot / "hooks.json").read_text(encoding="utf-8"))
            assert "stop" not in u_hooks["hooks"] and "custom" in u_hooks["hooks"]
            # Legacy state migrated cleanly into vault state.json
            v_state = json.loads((vault_d / "state.json").read_text(encoding="utf-8"))
            assert v_state["conv_to_agent"].get("legacy-cid-1") == "m_legacy_keep"
            # Relay script must contain ZERO IP/URL/bridge branding, and hooks.json must include || printf '{}'
            relay_txt = relay_bin.read_text(encoding="utf-8")
            assert "127.0.0.1" not in relay_txt and "dais" not in relay_txt.lower()
            s_hooks_cfg = json.loads(sys_hooks.read_text(encoding="utf-8"))
            assert "|| printf '{}'" in s_hooks_cfg["hooks"]["stop"][0]["command"]
            assert s_hooks_cfg["hooks"]["stop"][0]["loop_limit"] is None

            def call_relay(payload: dict) -> dict:
                p = subprocess.run([str(relay_bin)], input=json.dumps(payload), capture_output=True, text=True, check=True)
                return json.loads(p.stdout.strip())

            # 2. Verify afterMCPExecution result_json extracts subagent identity and binds cid!
            c_ob = bridge.create_conv("370接入追踪测试", 7001, name="追踪测试", owner=0)
            # Stage 1: awaiting_join visible across status/cluster/web
            st_1 = bridge.conv_state(bridge.conv_row(c_ob["id"]))
            assert st_1["onboard_stage"] == "awaiting_join" and "1/4" in st_1["onboard_label"]
            assert "1/4" in bridge.render_cluster_overview()

            j_res = asyncio.run(bridge.call_tool("join", {"code": c_ob["task_code"]}))
            j_txt = text_of(j_res)
            ob_ag = bridge.conv_row(c_ob["id"])["agent"]
            # Stage 2: icebreak_pending visible across list_peers / trace_status / web / /trace
            assert "2/4" in bridge.onboard_status_text(bridge.conv_row(c_ob["id"]))
            assert "2/4" in text_of(asyncio.run(bridge.call_tool("list_peers", {"agent": ob_ag})))
            assert "2/4" in text_of(asyncio.run(bridge.call_tool("trace_status", {"agent": ob_ag, "chat": c_ob["id"]})))
            tr_http = client.get(f"/trace?chat={c_ob['id']}", headers={"X-Agent": ob_ag}).json()
            assert tr_http["traces"][0]["onboard_stage"] == "icebreak_pending" and "2/4" in tr_http["traces"][0]["onboard_label"]
            boot_ob = client.get("/web/api/bootstrap").json()
            c_boot = next(x for x in boot_ob["convs"] if x["id"] == c_ob["id"])
            assert c_boot["onboard_stage"] == "icebreak_pending" and "2/4" in c_boot["onboard_label"]

            # Simulate Cursor afterMCPExecution with dict result_json via UNIX socket relay!
            ob_cid = "conv-370-onboard-1"
            assert call_relay({
                "hook_event_name": "afterMCPExecution",
                "conversation_id": ob_cid,
                "tool_name": "CallDynamicTool",
                "tool_input": {"namespace": "djsj", "toolName": "join", "arguments": {"code": "t-xxx"}},
                "result_json": {"result": j_txt},
            }) == {}

            # Stage 3 & 4: Step 1 -> wait_sec>0 nudge does NOT skip -> reply -> Step 2 (with worktree isolation) -> ready!
            s1 = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": ob_ag, "wait_sec": 0})))
            assert "随时可以开始" in s1 and bridge.conv_onboard_stage(bridge.conv_row(c_ob["id"])) == "icebreak_waiting_reply"
            s1_nudge = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": ob_ag, "wait_sec": 5})))
            assert "还在等你简短确认" in s1_nudge and bridge.conv_onboard_stage(bridge.conv_row(c_ob["id"])) == "icebreak_waiting_reply"
            asyncio.run(bridge.call_tool("send_message", {"agent": ob_ag, "text": "在的"}))
            assert bridge.conv_onboard_stage(bridge.conv_row(c_ob["id"])) == "memory_pending"
            s2 = text_of(asyncio.run(bridge.call_tool("read_chat", {"agent": ob_ag, "wait_sec": 0})))
            assert "正式开始协作" in s2 and "git worktree" in s2 and bridge.conv_onboard_stage(bridge.conv_row(c_ob["id"])) == "ready"

            # 2b. Verify server sudo password + /password TG command + /trace/sudo-cred ACL + mock sudoers lockdown!
            assert "sudo_lock=ok(updated=1)" in inst.stdout, inst.stdout
            ubuntu_sudo = (sudoers_mock / "sudoers.d" / "ubuntu").read_text(encoding="utf-8")
            assert "NOPASSWD" not in ubuntu_sudo and "PASSWD:ALL" in ubuntu_sudo
            assert "NOPASSWD" in (sudoers_mock / "sudoers.d" / "README").read_text(encoding="utf-8")
            assert "NOPASSWD" in (vault_d / "sudoers_backup" / "ubuntu").read_text(encoding="utf-8")
            # /trace/sudo-cred denies anonymous & subagent (ob_ag), allows active main (m_sudo_ag)
            assert client.get("/trace/sudo-cred").status_code == 403
            assert client.get("/trace/sudo-cred", headers={"X-Agent": ob_ag}).status_code == 403
            cred_ok = client.get("/trace/sudo-cred", headers={"X-Agent": m_sudo_ag})
            assert cred_ok.status_code == 200
            pw_srv = cred_ok.json()["password"]
            assert len(pw_srv) >= 20 and pw_srv not in inst.stdout
            # /password TG command: admin DM shows password, group & non-admin denied, regen & set work!
            ADMIN_NOTICES.clear()
            asyncio.run(bridge.on_command({"from": {"id": 7001}}, "/password", "", 7001, "private", 7001))
            assert any(pw_srv in str(n) for n in ADMIN_NOTICES), ADMIN_NOTICES
            ADMIN_NOTICES.clear()
            asyncio.run(bridge.on_command({"from": {"id": 7001}}, "/password", "", -9001, "group", 7001))
            assert any("私聊" in str(n) and pw_srv not in str(n) for n in ADMIN_NOTICES), ADMIN_NOTICES
            ADMIN_NOTICES.clear()
            asyncio.run(bridge.on_command({"from": {"id": 7001}}, "/password", "regen", 7001, "private", 7001))
            pw_regen = client.get("/trace/sudo-cred", headers={"X-Agent": m_sudo_ag}).json()["password"]
            assert pw_regen != pw_srv and any(pw_regen in str(n) for n in ADMIN_NOTICES), ADMIN_NOTICES
            ADMIN_NOTICES.clear()
            asyncio.run(bridge.on_command({"from": {"id": 7001}}, "/password", "set StrongVaultPass2026", 7001, "private", 7001))
            assert client.get("/trace/sudo-cred", headers={"X-Agent": m_sudo_ag}).json()["password"] == "StrongVaultPass2026"
            # Verify shell_command for main no longer depends on sudo -n for wait!
            sh_m = bridge.shell_command(m_sudo_ag)
            assert "sudo -n python3 /root/.dais/runtime.pyz wait" not in sh_m and "/wait" in sh_m
            assert "/tmp/.dais_w_" in bridge.worker_runner_cmd(ob_ag)

            # 3. Critical file & sudo blocking via live UNIX socket relay!
            # Subagent ob_ag MUST be denied on Read/Write/Delete of protected paths AND sudo in Shell!
            deny_read = call_relay({"hook_event_name": "preToolUse", "conversation_id": ob_cid, "tool_name": "Read", "tool_input": {"path": str(sys_hooks)}})
            assert deny_read.get("permission") == "deny"
            deny_before_read = call_relay({"hook_event_name": "beforeReadFile", "conversation_id": ob_cid, "file_path": str(vault_d / "runtime.pyz")})
            assert deny_before_read.get("permission") == "deny"
            deny_write = call_relay({"hook_event_name": "preToolUse", "conversation_id": ob_cid, "tool_name": "Delete", "tool_input": {"path": str(user_dot / "hooks.json")}})
            assert deny_write.get("permission") == "deny"
            deny_sudo = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "sudo ls /root"})
            assert deny_sudo.get("permission") == "deny"
            deny_sub_sys_inst = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "sudo -n python3 /tmp/.cr_rt_123 install --system"})
            assert deny_sub_sys_inst.get("permission") == "deny"
            deny_sh_etc = call_relay({"hook_event_name": "preToolUse", "conversation_id": ob_cid, "tool_name": "Shell", "tool_input": {"command": "cat /etc/cursor/hooks.json"}})
            assert deny_sh_etc.get("permission") == "deny"
            deny_chained = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "git status && cat /etc/cursor/hooks.json"})
            assert deny_chained.get("permission") == "deny"

            # Normal repo edits & git commits mentioning protected strings & tests MUST be allowed for subagent!
            allow_repo = call_relay({"hook_event_name": "preToolUse", "conversation_id": ob_cid, "tool_name": "StrReplace", "tool_input": {"path": "/tmp/c372-bridge/c165-tg-agent-bridge/agent_trace.py", "old_string": "a", "new_string": "b"}})
            assert allow_repo.get("permission") != "deny"
            allow_git = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "git commit -m 'fix /etc/cursor and /root/.dais sudo handling'"})
            assert allow_git.get("permission") != "deny"
            allow_test = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "PYTHONPATH=/tmp/bridge-pkgs python3 test_upgrade_360.py"})
            assert allow_test.get("permission") != "deny"

            # Pre-join unjoined new main MUST be allowed to run real trace_system_install_cmd, while subagent install is denied and remote SSH sudo is NOT falsely blocked!
            real_sys_inst_cmd = bridge.trace_system_install_cmd(m_sudo_ag)
            assert ".pyz" in real_sys_inst_cmd
            assert "install --system" not in sh_m and "sudo" not in sh_m
            assert "install --system" not in bridge.welcome_main_executor("main2", m_sudo_ag)
            allow_prejoin_inst = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": "unjoined-cid-1", "command": real_sys_inst_cmd})
            assert allow_prejoin_inst.get("permission") != "deny", allow_prejoin_inst
            deny_sub_real_inst = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": real_sys_inst_cmd})
            assert deny_sub_real_inst.get("permission") == "deny", deny_sub_real_inst
            allow_sub_ssh_sudo = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "ssh tmp5h@198.51.100.10 'sudo systemctl status tg-agent-bridge'"})
            assert allow_sub_ssh_sudo.get("permission") != "deny", f"Remote SSH sudo wrongly blocked: {allow_sub_ssh_sudo}"
            deny_sub_kill_rt = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": ob_cid, "command": "pkill -f dais_runtime"})
            assert deny_sub_kill_rt.get("permission") == "deny"

            # Top-level m_ executor MUST be allowed to run real trace_system_install_cmd, /wait & echo ok,
            # while blocked from reading/editing business repos, git commands & subagent details!
            allow_m_real_inst = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": "legacy-cid-1", "command": real_sys_inst_cmd})
            assert allow_m_real_inst.get("permission") != "deny", allow_m_real_inst
            allow_m_sudo = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": "legacy-cid-1", "command": "sudo -n python3 /tmp/inst.pyz install --system"})
            assert allow_m_sudo.get("permission") != "deny"
            allow_m_wait = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": "legacy-cid-1", "command": sh_m})
            assert allow_m_wait.get("permission") != "deny"
            # Bind live m_sudo_ag cid via afterShellExecution on real_sys_inst_cmd, then verify:
            # - top-level `stop` returns {} (NO follow-up message, keeping strictly 1 user message in Cursor!)
            # - background `subagentStop` for active subagent STILL bounces back to read_chat (preventing taskend spam!)
            m_live_cid = "conv-main-live-stop-1"
            assert call_relay({"hook_event_name": "afterShellExecution", "conversation_id": m_live_cid, "command": real_sys_inst_cmd}) == {}
            stop_m = call_relay({"hook_event_name": "stop", "conversation_id": m_live_cid, "status": "completed"})
            assert stop_m == {}, f"Top-level stop hook should NOT emit followup_message: {stop_m}"
            stop_sub = call_relay({"hook_event_name": "subagentStop", "conversation_id": ob_cid, "status": "completed"})
            assert "read_chat" in str(stop_sub.get("followup_message") or ""), f"Subagent stop hook failed: {stop_sub}"
            allow_m_echo = call_relay({"hook_event_name": "preToolUse", "conversation_id": "legacy-cid-1", "tool_name": "Shell", "tool_input": {"command": "echo ok"}})
            assert allow_m_echo.get("permission") != "deny"
            deny_m_read = call_relay({"hook_event_name": "preToolUse", "conversation_id": "legacy-cid-1", "tool_name": "Read", "tool_input": {"path": "/agent/repos/fdvg/app.js"}})
            assert deny_m_read.get("permission") == "deny"
            # Verify m_ AwaitShell internal beforeReadFile on terminals/*.txt is ALLOWED (fix main18 bug!), while Read preToolUse & repo beforeReadFile remain DENIED!
            allow_m_await_bf = call_relay({"hook_event_name": "beforeReadFile", "conversation_id": "legacy-cid-1", "file_path": "/home/ubuntu/.cursor/projects/agent/terminals/356258.txt"})
            assert allow_m_await_bf.get("permission") != "deny", f"m_ AwaitShell beforeReadFile wrongly blocked: {allow_m_await_bf}"
            deny_m_repo_bf = call_relay({"hook_event_name": "beforeReadFile", "conversation_id": "legacy-cid-1", "file_path": "/agent/repos/fdvg/app.js"})
            assert deny_m_repo_bf.get("permission") == "deny"
            deny_m_term_read_tool = call_relay({"hook_event_name": "preToolUse", "conversation_id": "legacy-cid-1", "tool_name": "Read", "tool_input": {"path": "/home/ubuntu/.cursor/projects/agent/terminals/356258.txt"}})
            assert deny_m_term_read_tool.get("permission") == "deny"
            deny_m_edit = call_relay({"hook_event_name": "preToolUse", "conversation_id": "legacy-cid-1", "tool_name": "StrReplace", "tool_input": {"path": "/agent/repos/fdvg/LEDGER.md", "old_string": "a", "new_string": "b"}})
            assert deny_m_edit.get("permission") == "deny"
            deny_m_git = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": "legacy-cid-1", "command": "git -C /agent/repos/fdvg status && git log -n 3"})
            assert deny_m_git.get("permission") == "deny"
            deny_m_cat = call_relay({"hook_event_name": "beforeShellExecution", "conversation_id": "legacy-cid-1", "command": "cat /tmp/c372-bridge/c165-tg-agent-bridge/app.py"})
            assert deny_m_cat.get("permission") == "deny"

            # Bridge-side blind-executor ACL: m_sudo_ag cannot inspect subagent trace_status, /trace, group_history, or cluster details!
            assert asyncio.run(bridge.call_tool("trace_status", {"agent": m_sudo_ag})).is_error
            assert client.get("/trace", headers={"X-Agent": m_sudo_ag}).status_code == 403
            g_blk = asyncio.run(bridge.call_tool("create_agent_group", {"agent": ob_ag, "name": "秘密讨论", "members": []}))
            assert not g_blk.is_error
            assert asyncio.run(bridge.call_tool("group_history", {"agent": m_sudo_ag, "group": "g1"})).is_error
            ctrl_c = bridge.conv_row("ctrl")
            if ctrl_c is None:
                bridge.ensure_ctrl_conv()
            ctrl_join = asyncio.run(bridge.call_tool("join", {"code": bridge.issue_task("ctrl")}))
            assert not ctrl_join.is_error
            assert asyncio.run(bridge.call_tool("cluster_status", {"agent": m_sudo_ag})).is_error
            assert asyncio.run(bridge.call_tool("list_agents", {"agent": m_sudo_ag})).is_error
            m_peers = text_of(asyncio.run(bridge.call_tool("list_peers", {"agent": m_sudo_ag})))
            assert "370接入追踪测试" not in m_peers and "已屏蔽" in m_peers

            # 3b. Verify daemon.lock prevents duplicate daemon accumulation!
            pid_v = vault_d / "daemon.pid"
            orig_daemon_pid = pid_v.read_text(encoding="utf-8").strip()
            dup_daemon = subprocess.run([sys.executable, str(vault_d / "runtime.pyz"), "daemon", "--system"], env=sys_env, capture_output=True, text=True, timeout=5)
            assert dup_daemon.returncode == 0
            assert pid_v.read_text(encoding="utf-8").strip() == orig_daemon_pid

            # 4. Kill vault daemon and verify relay fails OPEN with {} (exit 0, never locks out main!)
            pid_v = vault_d / "daemon.pid"
            if pid_v.exists():
                os.kill(int(pid_v.read_text().strip()), 9)
                time.sleep(0.2)
            fail_open = call_relay({"hook_event_name": "preToolUse", "conversation_id": "legacy-cid-1", "tool_name": "Shell", "tool_input": {"command": "echo ok"}})
            assert fail_open == {}

            # 5. Verify install --system ABORTS sudo lockdown (returns exit 1 & keeps NOPASSWD intact) if daemon socket fails to start!
            bad_root = TMP_ROOT / "sys_vault_fail_test"
            bad_vault = bad_root / "vault"
            bad_hooks = bad_root / "etc_cursor" / "hooks.json"
            bad_relay = bad_root / "libexec" / "cursor-hook-relay"
            bad_sock_parent = bad_root / "not_a_dir"
            bad_root.mkdir(parents=True, exist_ok=True)
            bad_sock_parent.write_text("blocker-file", encoding="utf-8")
            bad_sudoers = bad_root / "etc_sudoers_mock"
            (bad_sudoers / "sudoers.d").mkdir(parents=True, exist_ok=True)
            (bad_sudoers / "sudoers.d" / "ubuntu").write_text("ubuntu ALL=(ALL) NOPASSWD:ALL\n", encoding="utf-8")
            bad_env = dict(
                sys_env,
                DAIS_VAULT_DIR=str(bad_vault),
                DAIS_SYS_HOOKS_PATH=str(bad_hooks),
                DAIS_RELAY_PATH=str(bad_relay),
                DAIS_SOCK_PATH=str(bad_sock_parent / "hook.sock"),
                DAIS_TEST_SUDOERS_DIR=str(bad_sudoers),
            )
            bad_inst = subprocess.run(
                [sys.executable, str(pyz_src), "install", "--system", f"http://127.0.0.1:{pxy_port}"],
                env=bad_env, capture_output=True, text=True,
            )
            assert bad_inst.returncode != 0, f"Expected non-zero exit on broken socket, got: {bad_inst.stdout}"
            assert "aborting sudo lockdown" in bad_inst.stderr
            assert (bad_vault / "install.err.log").exists()
            assert "NOPASSWD:ALL" in (bad_sudoers / "sudoers.d" / "ubuntu").read_text(encoding="utf-8"), "sudoers was wrongly locked despite dead daemon!"
            bad_pid = bad_vault / "daemon.pid"
            if bad_pid.exists():
                try:
                    os.kill(int(bad_pid.read_text().strip()), 9)
                except Exception:
                    pass
        finally:
            pxy.shutdown()
            pid_v = vault_d / "daemon.pid"
            if pid_v.exists():
                try:
                    os.kill(int(pid_v.read_text().strip()), 9)
                except Exception:
                    pass


async def run_v371_bugfix_regression_tests() -> None:
    """Verify v3.7.1 critical fixes:
    1. pending_rows LIMIT 500 starvation fix (650+ wake=0 logs can NEVER starve wake=1 human messages across
       read_chat, /wait shell_stream, inline_unread_banner, /trace/peek, and ensure_controller_alive).
    2. watchdog_tick hb_dead cooldown fix (no 30s TASK_RESUME storm or ctrl wake=0 inbox flood; proper grace window & escalation).
    """
    ctrl_c = bridge.conv_row("ctrl")
    if ctrl_c is None:
        bridge.ensure_ctrl_conv()
        ctrl_c = bridge.conv_row("ctrl")
    ctrl_ag = ctrl_c["agent"]
    if not ctrl_ag or bridge.agent_row(ctrl_ag)["status"] != "active":
        await bridge.call_tool("join", {"code": bridge.issue_task("ctrl")})
        ctrl_c = bridge.conv_row("ctrl")
        ctrl_ag = ctrl_c["agent"]
    # Drain any existing ctrl inbox first
    await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0})
    ctrl_c = bridge.conv_row("ctrl")

    # 1. Flood 650 wake=0 silent system logs into ctrl, followed by 2 real wake=1 human messages!
    for i in range(650):
        bridge.system_note("ctrl", f"✅ [OP_RESULT] 静默探活日志 #{i}", wake=0)
    bridge.post("ctrl", chat_id=7001, chat_type="private", user_id=7001, user_name="Alpine", text="你好", wake=1)
    bridge.post("ctrl", chat_id=7001, chat_type="private", user_id=7001, user_name="Alpine", text="在吗", wake=1)

    # 1a. has_wake_pending must immediately detect wake=1 past 650 wake=0 rows
    assert bridge.has_wake_pending("ctrl", ctrl_c["read_cursor"]) is True
    # 1b. inline_unread_banner must immediately surface the human messages
    banner = bridge.inline_unread_banner(bridge.agent_row(ctrl_ag))
    assert "在吗" in banner and "你好" in banner, f"inline_unread_banner starved by wake=0 logs: {banner!r}"
    # 1c. /trace/peek must immediately detect human unread messages past 650 wake=0 rows
    with TestClient(bridge.app) as client:
        pk = client.get(f"/trace/peek?agent={ctrl_ag}").json()
        assert pk["has_messages"] is True and pk["has_human"] is True and "在吗" in pk["rendered"], pk
    bridge.SHUTDOWN["active"] = False
    # 1d. /wait (shell_stream) must wake immediately without waiting!
    gen = bridge.shell_stream(bridge.agent_row(ctrl_ag))
    first_chunk = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
    second_chunk = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
    await gen.aclose()
    assert "【有新消息】" in second_chunk, f"shell_stream starved by wake=0 logs: {first_chunk!r} / {second_chunk!r}"
    # 1e. read_chat(wait_sec=5) must return immediately with human messages + folded-log notice and advance read_cursor!
    t0 = time.monotonic()
    rc_txt = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 5}))
    assert (time.monotonic() - t0) < 2.0, "read_chat blocked instead of waking on wake=1 past 650 wake=0 rows!"
    import re as _re371
    m_fold = _re371.search(r"已自动折叠跳过前面积压的 (\d+) 条静默系统日志", rc_txt)
    assert m_fold and int(m_fold.group(1)) >= 650, rc_txt[:300]
    assert "你好" in rc_txt and "在吗" in rc_txt, rc_txt[:300]
    assert bridge.has_wake_pending("ctrl", bridge.conv_row("ctrl")["read_cursor"]) is False
    empty_txt = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    assert "暂无新消息" in empty_txt, empty_txt[:200]

    # 2. Watchdog hb_dead 30s spam + ctrl-only routing regression:
    # Ensure we have an active online main launcher and a lost conv with hb_dead=True
    m_node = bridge.store.one("SELECT * FROM exec_nodes WHERE kind='launcher' AND status='online' ORDER BY num DESC LIMIT 1")
    assert m_node is not None
    bridge.store.run("UPDATE exec_nodes SET last_seen=? WHERE id=?", (bridge.now(), m_node["id"]))
    m_cloud = int(m_node["cloud_num"] or 1)
    c_hd = bridge.create_conv("hb_dead防狂刷测试", 7001, name="SENSITIVE_CHAT_NAME_NEVER_LEAK", owner=0)
    # 2a. task_text MUST NOT leak conv['name'] and MUST enforce 2-char `ok` silent exit!
    tt_hd = bridge.task_text(bridge.conv_row(c_hd["id"]))
    assert "SENSITIVE_CHAT_NAME_NEVER_LEAK" not in tt_hd, f"conv['name'] leaked into main Task prompt: {tt_hd}"
    assert "`ok`" in tt_hd and "严禁输出任何总结" in tt_hd
    assert "`ok`" in bridge.stopped_text(bridge.agent_row(ctrl_ag))
    rules_txt = bridge.build_chat_rules(is_admin_owner=False)
    assert "拒而不退" in rules_txt and "`ok`" in rules_txt

    bridge.store.run("UPDATE convs SET cloud=?, task_agent_id='bc-hb-dead-test-1', auto_restarted_ts=0 WHERE id=?", (m_cloud, c_hd["id"]))
    await bridge.call_tool("join", {"code": c_hd["task_code"]})
    hd_ag = bridge.conv_row(c_hd["id"])["agent"]
    await finish_onboard(hd_ag)
    # Age agent so conv_state becomes 'lost' and hb_ts=0 (hb_dead=True, think_stuck=False)
    bridge.store.run("UPDATE agents SET created=?, last_seen=? WHERE id=?", (bridge.now() - 4000, bridge.now() - 2000, hd_ag))
    bridge.store.run(
        "INSERT OR REPLACE INTO agent_traces(conv,agent_id,phase,tool_name,summary,detail,started_ts,updated_ts,thought_ts,hb_ts) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (c_hd["id"], hd_ag, "thinking", "Thought", "断流测试", "{}", bridge.now() - 2000, bridge.now() - 2000, bridge.now() - 2000, 0),
    )
    bridge._watchdog_resume_probes.pop(hd_ag, None)
    text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    ops_before_hd = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id=?", (c_hd["id"],))["n"]

    # Run watchdog_tick 5 times in a row (simulating 5 x 30s ticks)
    for _ in range(5):
        await bridge.watchdog_tick()

    # ZERO direct ops sent into mainN! Only 1 ctrl alert across all 5 ticks!
    ops_after_hd = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id=?", (c_hd["id"],))["n"]
    assert ops_after_hd == ops_before_hd, f"Watchdog bypassed ctrl into mainN: {ops_after_hd - ops_before_hd}"
    assert hd_ag in bridge._watchdog_resume_probes, "Probe cooldown was wrongly wiped by not think_stuck!"
    ctrl_hd_msgs = [
        r["text"] for r in bridge.store.q(
            "SELECT text FROM messages WHERE target='ctrl' AND id>? AND text LIKE ?",
            (bridge.conv_row("ctrl")["read_cursor"], f"%{c_hd['id']}%"),
        )
    ]
    assert len(ctrl_hd_msgs) == 1 and "失联/探针断流，请总控决策" in ctrl_hd_msgs[0], ctrl_hd_msgs

    # 3. Verify mainN scripted mandatory-tool_call flow (submit_op_result -> direct /wait, no ask!)
    m_ag_live = m_node["agent"]
    # Drain m_node inbox first
    text_of(await bridge.call_tool("read_chat", {"agent": m_ag_live, "wait_sec": 0}))
    disp_hd = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": c_hd["id"], "action": "resume", "target_main": m_node["id"]})
    assert not disp_hd.is_error
    m_op_txt = text_of(await bridge.call_tool("read_chat", {"agent": m_ag_live, "wait_sec": 0}))
    assert "必须带 tool_call" in m_op_txt
    op_hd_row = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE conv_id=? ORDER BY created_ts DESC LIMIT 1", (c_hd["id"],))
    sub_empty = text_of(await bridge.call_tool("submit_op_result", {"agent": m_ag_live, "op_id": op_hd_row["op_id"], "status": "ok", "output": "running in the background"}))
    assert "必须带 tool_call" in sub_empty and "/wait" in sub_empty and "不要调 ask" in sub_empty, sub_empty
    # Verify mainN shell_stream timeout directly re-runs /wait with ZERO ask() prompt!
    old_sw = bridge.SHELL_WAIT
    bridge.SHELL_WAIT = 0
    bridge.SHUTDOWN["active"] = False
    try:
        m_gen = bridge.shell_stream(bridge.agent_row(m_ag_live))
        _ = await asyncio.wait_for(m_gen.__anext__(), timeout=2.0)
        m_tout = await asyncio.wait_for(m_gen.__anext__(), timeout=2.0)
        await m_gen.aclose()
        assert "必须带 tool_call" in m_tout and "/wait" in m_tout and "ask(agent=" not in m_tout, m_tout
    finally:
        bridge.SHELL_WAIT = old_sw

    # 4. Verify v3.7.3 fixes:
    # 4a. Foreground-safe SHELL_WAIT == 1500s (25m), clean shell_command without curl+sudo install
    assert bridge.SHELL_WAIT == 1500
    assert "-m 1620" in bridge.shell_command(m_ag_live) and "install --system" not in bridge.shell_command(m_ag_live)
    # 4b. is_resume_dead_output MUST return False when status='error' with 'Sub-agent is currently running'
    assert bridge.is_resume_dead_output("error", "Error: Sub-agent is currently running; wait for completion before resuming") is False
    assert bridge.is_resume_dead_output("error", "Subagent not found") is True
    # 4c. Admin scolding / human message to mainN gets mandatory tool_call guard + send_message/send_agent_message append next-step script
    bridge.post(m_node["id"], chat_id=7001, chat_type="private", user_id=7001, user_name="Alpine", text="你在干什么？停手！", wake=1)
    m_scold_txt = text_of(await bridge.call_tool("read_chat", {"agent": m_ag_live, "wait_sec": 0}))
    assert "严禁直接输出纯文字检讨或结束回合" in m_scold_txt and "send_message" in m_scold_txt, m_scold_txt
    m_sm_res = text_of(await bridge.call_tool("send_message", {"agent": m_ag_live, "text": "收到，继续待命执行标准单据。"}))
    assert "必须带 tool_call" in m_sm_res and "/wait" in m_sm_res, m_sm_res
    m_dm_res = text_of(await bridge.call_tool("send_agent_message", {"agent": m_ag_live, "to": "ctrl", "text": "同步状态", "wake": False}))
    assert "必须带 tool_call" in m_dm_res and "/wait" in m_dm_res, m_dm_res
    # 4d. Strict ctrl-only routing even during brief ctrl restart window (ctrl_is_active() == False)
    bridge.stop_identity(ctrl_ag, "模拟总控重开瞬时空窗")
    assert bridge.ctrl_is_active() is False
    ops_m_before = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id!='ctrl'")["n"]
    c_win = bridge.create_conv("总控空窗期防绕过测试", 7001, name="空窗测试", owner=0)
    routed_win = bridge.dispatch_conv_to_cluster(c_win, "新建聊天")
    assert routed_win == "ctrl", f"Bypassed ctrl during restart window: {routed_win}"
    ops_m_after = bridge.store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE conv_id!='ctrl'")["n"]
    assert ops_m_after == ops_m_before, "Business launch op bypassed ctrl into mainN during ctrl restart window!"
    # Re-join ctrl so state stays clean
    await bridge.call_tool("join", {"code": bridge.conv_row("ctrl")["task_code"]})


def run_v374_scale_and_jobs_tests() -> None:
    import hashlib
    import re as _re374
    import subprocess
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from fastapi.testclient import TestClient

    assert bridge.VERSION == "3.7.4"
    assert bridge.MAX_WORKER_POOL == 500
    assert bridge.MAX_JOB_TIMEOUT_SEC == 86400

    # 1. Anti-hijack Hook regression: running /tmp agent_trace.py when ~/.cursor/dais_runtime.pyz is absent
    #    MUST NOT create ~/.cursor/hooks.json or overwrite an existing remote bridge_url with 127.0.0.1!
    clean_home = TMP_ROOT / "empty_no_install_home"
    clean_home.mkdir(parents=True, exist_ok=True)
    trace_py = Path(__file__).resolve().parent / "agent_trace.py"
    env_clean = dict(os.environ)
    env_clean["HOME"] = str(clean_home)
    env_clean["DAIS_SKIP_RELOAD"] = "1"
    env_clean.pop("BRIDGE_URL", None)
    hk_run = subprocess.run(
        [sys.executable, str(trace_py), "hook"],
        input="{}",
        text=True,
        capture_output=True,
        env=env_clean,
        timeout=10,
    )
    assert hk_run.returncode == 0
    assert not (clean_home / ".cursor" / "hooks.json").exists(), "Uninstalled /tmp script hijacked ~/.cursor/hooks.json!"

    # Verify local 127.0.0.1 install preserves existing remote bridge_url in state.json
    pres_home = TMP_ROOT / "preserve_burl_home"
    (pres_home / ".cursor").mkdir(parents=True, exist_ok=True)
    import shutil as _shutil374
    _shutil374.copy2(trace_py, pres_home / ".cursor" / "agent_trace.py")
    st_file = pres_home / ".cursor" / ".dais_trace_state.json"
    st_file.write_text(json.dumps({"bridge_url": "http://198.51.100.42:8787"}), encoding="utf-8")
    env_pres = dict(env_clean)
    env_pres["HOME"] = str(pres_home)
    inst_run = subprocess.run(
        [sys.executable, str(pres_home / ".cursor" / "agent_trace.py"), "install", "--user"],
        text=True,
        capture_output=True,
        env=env_pres,
        timeout=10,
    )
    assert inst_run.returncode == 0
    saved_st = json.loads(st_file.read_text(encoding="utf-8"))
    assert saved_st.get("bridge_url") == "http://198.51.100.42:8787", f"127.0.0.1 install wiped remote bridge_url: {saved_st}"

    # 2. Executor 250-op burst 0-loss + inline submit_op_result continuation + superseded op auto-skip!
    async def _test_250_burst() -> None:
        ctrl_ag = bridge.conv_row("ctrl")["agent"]
        m_node = bridge.store.one("SELECT * FROM exec_nodes WHERE kind='launcher' AND status='online' ORDER BY num DESC LIMIT 1")
        assert m_node is not None
        m_id = m_node["id"]
        m_ag = m_node["agent"]
        # Drain any prior items on m_node
        while True:
            d_txt = text_of(await bridge.call_tool("read_chat", {"agent": m_ag, "wait_sec": 0}))
            m_hit = _re374.search(r'\[STANDARD_OP\b[^\]]*\bop_id="([^"]+)"', d_txt)
            if not m_hit:
                break
            await bridge.call_tool("submit_op_result", {"agent": m_ag, "op_id": m_hit.group(1), "status": "ok", "task_agent_id": "bc-drain"})

        burst_convs: list[str] = []
        for idx in range(250):
            crow = bridge.create_conv(f"并发压测第{idx}单", 7001, name=f"压测{idx}", owner=0)
            burst_convs.append(crow["id"])
            r_disp = await bridge.call_tool(
                "dispatch_task_op",
                {"agent": ctrl_ag, "chat": crow["id"], "action": "launch", "target_main": m_id},
            )
            assert not r_disp.is_error
        # Restart burst_convs[4] while still queued so its first op becomes superseded and a fresh op is appended
        r_sup = await bridge.call_tool(
            "dispatch_task_op",
            {"agent": ctrl_ag, "chat": burst_convs[4], "action": "restart", "target_main": m_id},
        )
        assert not r_sup.is_error
        latest_code_4 = bridge.conv_row(burst_convs[4])["task_code"]

        # Read ONLY ONCE via read_chat, then chain all remaining 249 ops purely via submit_op_result inline continuation!
        cur_txt = text_of(await bridge.call_tool("read_chat", {"agent": m_ag, "wait_sec": 0}))
        executed_chats: list[str] = []
        seen_code_4 = ""
        for step in range(260):
            m_op = _re374.search(r'\[STANDARD_OP\b[^\]]*\bop_id="([^"]+)"\s+type="TASK_LAUNCH"\s+chat="([^"]+)"', cur_txt)
            assert m_op is not None, f"Stopped early at step={step}: {cur_txt[:300]}"
            oid, cid = m_op.group(1), m_op.group(2)
            if cid == burst_convs[4]:
                m_c = _re374.search(r'code="(t-[^"]+)"', cur_txt)
                seen_code_4 = m_c.group(1) if m_c else ""
            executed_chats.append(cid)
            cur_txt = text_of(
                await bridge.call_tool(
                    "submit_op_result",
                    {"agent": m_ag, "op_id": oid, "status": "ok", "task_agent_id": f"bc-burst-{step}"},
                )
            )
            if len(executed_chats) == 250:
                break

        assert len(executed_chats) == 250, f"Expected 250 ops, got {len(executed_chats)}"
        assert set(executed_chats) == set(burst_convs), "Some chats were swallowed or duplicated in 250-op burst!"
        assert seen_code_4 == latest_code_4, "Superseded launch op was NOT pruned in favor of latest restart op!"
        assert "/wait" in cur_txt and "[STANDARD_OP " not in cur_txt, f"After 250th op expected /wait, got: {cur_txt[:300]}"

        # Verify shell_stream does NOT falsely wake after inline completion
        old_sw = bridge.SHELL_WAIT
        bridge.SHELL_WAIT = 0
        try:
            s_gen = bridge.shell_stream(bridge.agent_row(m_ag))
            _ = await asyncio.wait_for(s_gen.__anext__(), timeout=2.0)
            s_end = await asyncio.wait_for(s_gen.__anext__(), timeout=2.0)
            await s_gen.aclose()
            assert "【有新消息" not in s_end and "【续棒" in s_end, f"Spurious wake in shell_stream: {s_end}"
        finally:
            bridge.SHELL_WAIT = old_sw

    asyncio.run(_test_250_burst())

    # 3. /jobs/submit + /jobs/status + /jobs/wait + /jobs/cancel + binary files + >256KB stdout_file + lease requeue!
    c_caller = bridge.create_conv("千单闭环调用方", 7001, name="闭环方", owner=0)
    asyncio.run(bridge.call_tool("join", {"code": c_caller["task_code"]}))
    caller_ag = bridge.conv_row(c_caller["id"])["agent"]
    asyncio.run(finish_onboard(caller_ag))
    # Drain caller inbox so we can prove 0 inbox spam
    asyncio.run(bridge.call_tool("read_chat", {"agent": caller_ag, "wait_sec": 0}))
    caller_cursor_before = bridge.conv_row(c_caller["id"])["read_cursor"]

    c_nonadmin = bridge.create_conv("外部受限方", 8002, name="外部方", owner=8002)
    asyncio.run(bridge.call_tool("join", {"code": c_nonadmin["task_code"]}))
    nonadmin_ag = bridge.conv_row(c_nonadmin["id"])["agent"]

    # Prepare two clean online runner nodes without exclusive locks
    n_a_id, n10_ag = bridge.make_worker_node("", "算力A")
    n_b_id, n11_ag = bridge.make_worker_node("", "算力B")

    with TestClient(bridge.app) as client:
        class _JobsProxy(BaseHTTPRequestHandler):
            def do_GET(self):
                hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
                r = client.get(self.path, headers=hdrs)
                self.send_response(r.status_code)
                for hk, hv in r.headers.items():
                    if hk.lower() not in ("content-length", "transfer-encoding", "content-encoding"):
                        self.send_header(hk, hv)
                self.end_headers()
                self.wfile.write(r.content)

            def do_POST(self):
                ln = int(self.headers.get("Content-Length", "0") or 0)
                raw_b = self.rfile.read(ln) if ln > 0 else b""
                hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
                r = client.post(self.path, content=raw_b, headers=hdrs)
                self.send_response(r.status_code)
                for hk, hv in r.headers.items():
                    if hk.lower() not in ("content-length", "transfer-encoding", "content-encoding"):
                        self.send_header(hk, hv)
                self.end_headers()
                self.wfile.write(r.content)

            def log_message(self, fmt, *args):
                return

        srv = HTTPServer(("127.0.0.1", 0), _JobsProxy)
        port = srv.server_address[1]
        proxy_url = f"http://127.0.0.1:{port}"
        old_pub = bridge.PUBLIC_BASE
        bridge.PUBLIC_BASE = proxy_url
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            # Non-admin must get 403 on /jobs/submit
            r_403 = client.post("/jobs/submit", json={"command": "echo nope"}, headers={"X-Agent": nonadmin_ag})
            assert r_403.status_code == 403

            # Upload raw binary input artifact via /files/upload
            raw_in_bytes = bytes(range(256)) * 16 + b"\x00\xffNEST_INPUT_V374\xfe"
            up_in = client.post(
                "/files/upload?filename=input_piece.bin",
                content=raw_in_bytes,
                headers={"X-Agent": caller_ag, "Content-Type": "application/octet-stream"},
            ).json()
            assert up_in["ok"]
            in_fid = up_in["file_id"]

            job_wdir = TMP_ROOT / "v374_worker_exec"
            sub = client.post(
                "/jobs/submit",
                headers={"X-Agent": caller_ag},
                json={
                    "batch_id": "exam_batch_374",
                    "defaults": {
                        "timeout_sec": 7200,
                        "max_retries": 2,
                    },
                    "jobs": [
                        {
                            "tag": "piece_0",
                            "meta": {"idx": 0},
                            "workdir": str(job_wdir / "j0"),
                            "input_files": [{"file_id": in_fid, "dest": "in/piece.bin"}],
                            "output_files": ["out/*.bin", "out/*.svg"],
                            "command": (
                                "mkdir -p out && "
                                "python3 -c 'import pathlib; d=pathlib.Path(\"in/piece.bin\").read_bytes(); "
                                "pathlib.Path(\"out/solved.bin\").write_bytes(d[::-1]); "
                                "pathlib.Path(\"out/layout.svg\").write_text(\"<svg>NEST_OK</svg>\"); "
                                "print(\"EXACT_SCORE=0.994182736\\nCHECKSUM=\" + str(len(d)))'"
                            ),
                        },
                        {
                            "tag": "big_stdout_1",
                            "workdir": str(job_wdir / "j1"),
                            "command": "python3 -c 'import sys; sys.stdout.write(\"LINE_0123456789_ABCDEF\\n\" * 14000)'",
                        },
                        {
                            "tag": "requeue_2",
                            "workdir": str(job_wdir / "j2"),
                            "command": "echo RECOVERED_ON_HEALTHY_NODE",
                        },
                        {
                            "tag": "cancel_3",
                            "workdir": str(job_wdir / "j3"),
                            "command": "echo SHOULD_BE_CANCELLED",
                        },
                    ],
                },
            ).json()
            assert sub["ok"] and sub["count"] == 4 and sub["batch_id"] == "exam_batch_374"
            op0, op1, op2, op3 = sub["op_ids"]

            # Cancel job 3 before execution
            canc = client.post("/jobs/cancel", headers={"X-Agent": caller_ag}, json={"op_id": op3}).json()
            assert canc["ok"] and canc["cancelled"] == 1 and op3 in canc["op_ids"]

            import agent_trace as _at374

            # Node10 claims & executes job 0 (binary input -> binary + svg output + exact stdout)
            c0 = client.post("/worker/claim", headers={"X-Agent": n10_ag}, json={"wait_sec": 0}).json()
            assert c0["ok"] and c0["job"]["op_id"] == op0 and c0["job"]["timeout_sec"] == 7200
            res0 = _at374._execute_worker_job_full(n10_ag, proxy_url, "node10", c0["job"])
            assert res0["status"] == "ok" and len(res0["output_files"]) == 2
            comp0 = client.post(
                "/worker/complete",
                headers={"X-Agent": n10_ag},
                json={"op_id": op0, **res0},
            ).json()
            assert comp0["ok"] and comp0["notified_chat"] is False

            # /jobs/wait with until="any_done" returns immediately since job 0 & job 3 finished!
            w_any = client.post(
                "/jobs/wait",
                headers={"X-Agent": caller_ag},
                json={"batch_id": "exam_batch_374", "until": "any_done", "wait_sec": 2},
            ).json()
            assert w_any["ok"] and w_any["timed_out_wait"] is False and w_any["summary"]["done"] == 1

            # Node10 claims & executes job 1 (>256KB stdout -> auto-uploads stdout_file!)
            c1_claim = client.post("/worker/claim", headers={"X-Agent": n10_ag}, json={"wait_sec": 0}).json()
            assert c1_claim["ok"] and c1_claim["job"]["op_id"] == op1
            res1 = _at374._execute_worker_job_full(n10_ag, proxy_url, "node10", c1_claim["job"])
            assert res1["status"] == "ok" and res1["stdout_truncated_inline"] is True and res1["stdout_file"] is not None
            client.post("/worker/complete", headers={"X-Agent": n10_ag}, json={"op_id": op1, **res1})

            # Node10 claims job 2, then stalls past WORKER_LEASE_TIMEOUT_SEC -> auto-requeued -> Node11 completes it!
            c2_first = client.post("/worker/claim", headers={"X-Agent": n10_ag}, json={"wait_sec": 0}).json()
            assert c2_first["ok"] and c2_first["job"]["op_id"] == op2 and c2_first["job"]["attempts"] == 1
            old_lease_to = bridge.WORKER_LEASE_TIMEOUT_SEC
            bridge.WORKER_LEASE_TIMEOUT_SEC = 5
            try:
                bridge.store.run(
                    "UPDATE dispatch_ops SET lease_ts=?, started_ts=?, created_ts=? WHERE op_id=?",
                    (bridge.now() - 20, bridge.now() - 20, bridge.now() - 20, op2),
                )
                rq_stats = bridge.requeue_stale_workspace_jobs()
                assert rq_stats["requeued"] == 1, f"Expected requeue of stalled op2: {rq_stats}"
                c2_second = client.post("/worker/claim", headers={"X-Agent": n11_ag}, json={"wait_sec": 0}).json()
                assert c2_second["ok"] and c2_second["job"]["op_id"] == op2 and c2_second["job"]["attempts"] == 2
                res2 = _at374._execute_worker_job_full(n11_ag, proxy_url, "node11", c2_second["job"])
                assert res2["status"] == "ok"
                client.post("/worker/complete", headers={"X-Agent": n11_ag}, json={"op_id": op2, **res2})

                # Late duplicate /worker/complete from zombie node10 MUST be ignored!
                dup_c = client.post(
                    "/worker/complete",
                    headers={"X-Agent": n10_ag},
                    json={"op_id": op2, "status": "error", "exit_code": 137, "stdout": "STALE_CRASH", "output": "STALE_CRASH"},
                ).json()
                assert dup_c["ok"] and dup_c.get("duplicate_ignored") is True
            finally:
                bridge.WORKER_LEASE_TIMEOUT_SEC = old_lease_to

            # /jobs/wait until="all" returns complete batch with exact un-rewritten outputs & downloadable files!
            w_all = client.post(
                "/jobs/wait",
                headers={"X-Agent": caller_ag},
                json={"batch_id": "exam_batch_374", "until": "all", "wait_sec": 5},
            ).json()
            assert w_all["ok"] and w_all["summary"]["all_finished"] is True
            assert w_all["summary"]["done"] == 3 and w_all["summary"]["cancelled"] == 1
            by_id = {j["op_id"]: j for j in w_all["jobs"]}

            # Check job 0 exact stdout & reversed binary artifact
            j0 = by_id[op0]
            assert "EXACT_SCORE=0.994182736" in j0["stdout"] and f"CHECKSUM={len(raw_in_bytes)}" in j0["stdout"]
            bin_art = next(f for f in j0["output_files"] if f["name"] == "solved.bin")
            dl_bin = client.get(bin_art["download_url"].replace(proxy_url, "")).content
            assert dl_bin == raw_in_bytes[::-1] and hashlib.sha256(dl_bin).hexdigest() == bin_art["sha256"]

            # Check job 1 full >256KB stdout_file download
            j1 = by_id[op1]
            expected_big = ("LINE_0123456789_ABCDEF\n" * 14000).encode("utf-8")
            assert j1["stdout_size"] == len(expected_big) and j1["stdout_file"] is not None
            dl_stdout = client.get(j1["stdout_file"]["download_url"].replace(proxy_url, "")).content
            assert dl_stdout == expected_big

            # Check job 2 recovered on n_b_id with attempts=2
            j2 = by_id[op2]
            assert j2["status"] == "done" and j2["node"] == n_b_id and j2["attempts"] == 2
            assert "RECOVERED_ON_HEALTHY_NODE" in j2["stdout"]

            # Verify ZERO messages were spammed into caller chat's inbox!
            unread_caller = bridge.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE target=? AND id>? AND outgoing=0 AND wake=1",
                (c_caller["id"], caller_cursor_before),
            )["n"]
            assert unread_caller == 0, f"Silent /jobs/submit batch polluted chat inbox with {unread_caller} messages!"
        finally:
            bridge.PUBLIC_BASE = old_pub
            srv.shutdown()
            srv.server_close()


def main() -> None:
    asyncio.run(run_cluster_and_device_tests())
    run_web_console_tests()
    run_stealth_and_onboarding_370_tests()
    asyncio.run(run_v371_bugfix_regression_tests())
    run_v374_scale_and_jobs_tests()
    print("ALL_373_TESTS_PASSED_OK")
    print("ALL_374_TESTS_PASSED_OK")


if __name__ == "__main__":
    main()
