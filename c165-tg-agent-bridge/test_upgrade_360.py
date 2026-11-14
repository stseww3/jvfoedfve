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


bridge.tg.call = _mock_tg_call
bridge.tg.try_call = _mock_tg_call
bridge.tg.send_text = _mock_send_text


def text_of(res) -> str:
    if res.commit:
        res.commit()
    return "\n".join(c.get("text", "") for c in res.content)


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
    assert bad_join1.is_error and "严禁不填 code 调用 join" in text_of(bad_join1)
    bad_join2 = await bridge.call_tool("join", {"mode": "main", "name": "nazzil"})
    assert bad_join2.is_error and "严禁不填 code 调用 join" in text_of(bad_join2)
    assert ADMIN_NOTICES == [], f"False admin popup leaked on empty join: {ADMIN_NOTICES}"

    # 2. Verify dais_runtime.pyz compiled bytecode bundle works without .py source!
    pyz_bytes = bridge.build_runtime_pyz()
    assert len(pyz_bytes) > 500 and pyz_bytes.startswith(b"#!/usr/bin/env python3\nPK")
    pyz_file = TMP_ROOT / "dais_runtime.pyz"
    pyz_file.write_bytes(pyz_bytes)
    pyz_file.chmod(0o755)
    env = dict(os.environ, HOME=str(HOME_DIR))
    inst = subprocess.run([sys.executable, str(pyz_file), "install", "http://127.0.0.1:18797"], env=env, capture_output=True, text=True, check=True)
    assert "dais_runtime.pyz" in inst.stdout
    hooks_cfg = json.loads((HOME_DIR / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert "subagentStop" in hooks_cfg["hooks"] and "preToolUse" in hooks_cfg["hooks"]
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

    # Verify subagent model verification:
    # (a) Joining c1 (required model="claude-fable-5-2-max") WITHOUT answering actual_model/model_match is blocked WITHOUT burning task_code!
    c1_code = bridge.conv_row("c1")["task_code"]
    no_mod_ans = await bridge.call_tool("join", {"code": c1_code})
    assert no_mod_ans.is_error and "子 Agent 入网模型校验" in text_of(no_mod_ans)
    assert bridge.conv_row("c1")["task_code"] == c1_code

    # (b) Joining c1 with mismatched model (model_match=False) puts subagent in mismatch_hold, blocks business tools, preserves unread msgs, and alerts ctrl!
    bridge.post("c1", chat_id=7001, chat_type="private", user_id=7001, user_name="Alpine", text="等正确模型来处理的任务", wake=1)
    wrong_join = await bridge.call_tool("join", {"code": c1_code, "actual_model": "GPT-5 Mini", "model_match": False})
    assert not wrong_join.is_error and "模型校验未通过·已上报主控判断" in text_of(wrong_join)
    wrong_ag = bridge.conv_row("c1")["agent"]
    assert bridge.conv_row("c1")["model_check"] == "mismatch_hold"
    # Business tools MUST be blocked while held!
    blocked_send = await bridge.call_tool("send_message", {"agent": wrong_ag, "text": "我不该能说话"})
    assert blocked_send.is_error and "等待主控判断" in text_of(blocked_send)
    # read_chat while held MUST NOT consume user's unread message!
    held_read = await bridge.call_tool("read_chat", {"agent": wrong_ag, "wait_sec": 0})
    assert "等待主控裁决" in text_of(held_read)
    # Ctrl received mismatch alert!
    ctrl_alert = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0}))
    assert "子 Agent 模型校验不匹配" in ctrl_alert and "GPT-5 Mini" in ctrl_alert and "claude-fable-5-2-max" in ctrl_alert

    # (c) Test ctrl judging "restart" -> kills wrong_ag, issues new task_code; then test lying conflict (actual="Gemini 4 Carbon", model_match=True) -> ALSO held; then test ctrl "approve_model" -> unblocks!
    rs_fix = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "restart", "model": "claude-fable-5-2-max"})
    assert not rs_fix.is_error
    assert bridge.agent_row(wrong_ag)["status"] == "stopped"
    # Drain main2's launch op
    await bridge.call_tool("read_chat", {"agent": m2, "wait_sec": 0})
    # Subagent claims model_match=True with obvious cross-family conflict -> still caught and held!
    lie_join = await bridge.call_tool("join", {"code": bridge.conv_row("c1")["task_code"], "actual_model": "Gemini 4 Carbon High", "model_match": True})
    assert "模型家族明显冲突" in text_of(lie_join) and bridge.conv_row("c1")["model_check"] == "mismatch_hold"
    held_ag2 = bridge.conv_row("c1")["agent"]
    # Drain ctrl alert and test ctrl judging `approve_model` -> unblocks held_ag2 and delivers unread message!
    await bridge.call_tool("read_chat", {"agent": ctrl_ag, "wait_sec": 0})
    app_mod = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "approve_model"})
    assert not app_mod.is_error and bridge.conv_row("c1")["model_check"] == "approved"
    unblocked_inbox = text_of(await bridge.call_tool("read_chat", {"agent": held_ag2, "wait_sec": 0}))
    assert "主控模型裁决放行" in unblocked_inbox and "等正确模型来处理的任务" in unblocked_inbox

    # Restart c1 cleanly with matching Claude Opus model for remaining tests
    await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "restart", "model": "claude-fable-5-2-max"})
    await bridge.call_tool("read_chat", {"agent": m2, "wait_sec": 0})
    op_c1_final = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE conv_id='c1' ORDER BY created_ts DESC LIMIT 1")["op_id"]
    await bridge.call_tool("submit_op_result", {"agent": m2, "op_id": op_c1_final, "status": "ok", "task_agent_id": "bc_task_c1_final"})
    ok_mod_join = await bridge.call_tool("join", {"code": bridge.conv_row("c1")["task_code"], "actual_model": "Claude 4.5 Opus (claude-fable-5-2-max)", "model_match": True})
    assert not ok_mod_join.is_error and "接手成功" in text_of(ok_mod_join)
    a1 = bridge.conv_row("c1")["agent"]
    assert bridge.conv_row("c1")["model_check"] == "ok"

    # Member user chat c2 -> cannot call spawn_subagent or run_workspace_job!
    c2_mem = bridge.create_conv("外部用户聊天", 8002, name="会员聊天", owner=8002)
    await bridge.call_tool("join", {"code": c2_mem["task_code"]})
    a2_mem = bridge.conv_row("c2")["agent"]
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

    # 7. Standardized TASK_RESUME round-trip
    res_op = await bridge.call_tool("dispatch_task_op", {"agent": ctrl_ag, "chat": "c1", "action": "resume"})
    assert not res_op.is_error
    op_res_id = bridge.store.one("SELECT op_id FROM dispatch_ops WHERE op_type='resume_subagent' ORDER BY created_ts DESC LIMIT 1")["op_id"]
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

    # Case B: c1 is in `thinking` for 6 minutes (360s > 300s) with active VM probe heartbeat -> MUST auto-restart!
    bridge.store.run(
        "INSERT OR REPLACE INTO agent_traces(conv,agent_id,phase,tool_name,summary,detail,started_ts,updated_ts,thought_ts,hb_ts) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("c1", a1, "thinking", "Thought", "卡在思考", "{}", now2 - 360, now2 - 360, now2 - 360, now2 - 5),
    )
    await bridge.watchdog_tick()
    assert bridge.agent_row(a1)["status"] == "stopped", "5-minute thinking-stuck agent was NOT auto-restarted!"
    # Re-join c1 after auto-restart so Web Console tests have an active c1
    await bridge.call_tool("join", {"code": bridge.conv_row("c1")["task_code"], "actual_model": "claude-fable-5-2-max", "model_match": True})

    # 9. Verify multi-device `/device add` keeps both PCs active simultaneously!
    dev_a = await bridge.issue_device(7001, "Alpine", create_new=True, custom_label="台式工作站")
    dev_b = await bridge.issue_device(7001, "Alpine", create_new=True, custom_label="随身笔记本")
    assert dev_a["id"] != dev_b["id"]
    assert bridge.device_row(dev_a["id"])["status"] == "active"
    assert bridge.device_row(dev_b["id"])["status"] == "active"

    # Create an agent collaboration group g1 for Web Console testing
    a1_new = bridge.conv_row("c1")["agent"]
    grp_res = await bridge.call_tool(
        "create_agent_group",
        {"agent": a1_new, "name": "天文台总装群", "members": ["c3"], "topic": "多工位联调", "welcome": "全员就位"},
    )
    assert not grp_res.is_error

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

        if log_file.exists():
            log_txt = log_file.read_text(encoding="utf-8", errors="replace")
            assert secret_pw not in log_txt and sub_pw not in log_txt


def main() -> None:
    asyncio.run(run_cluster_and_device_tests())
    run_web_console_tests()
    print("ALL_360_TESTS_PASSED_OK")


if __name__ == "__main__":
    main()
