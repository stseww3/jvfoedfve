#!/usr/bin/env python3
"""Comprehensive end-to-end verification suite for tg-agent-bridge 3.6.0."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

TMP_ROOT = Path(tempfile.mkdtemp(prefix="tgb360_test_"))
DATA_DIR = TMP_ROOT / "data"
HOME_DIR = TMP_ROOT / "fake_home"
HOME_DIR.mkdir(parents=True, exist_ok=True)

os.environ["DATA_DIR"] = str(DATA_DIR)
os.environ["TG_TOKEN"] = "123456:TEST_DUMMY_TOKEN_360"
os.environ["PUBLIC_BASE"] = "http://127.0.0.1:18788"

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx  # noqa: E402
import app as bridge  # noqa: E402


SENT_TG: list[tuple[int, str]] = []


async def _mock_tg_call(method: str, **kwargs):
    if method == "getMe":
        return {"id": 999001, "username": "test360_bot", "can_read_all_group_messages": True}
    if method in ("sendMessage", "sendDocument"):
        SENT_TG.append((int(kwargs.get("chat_id") or 0), str(kwargs.get("text") or kwargs.get("filename") or "")))
        return {"message_id": 200 + len(SENT_TG)}
    return True


async def _mock_send_text(chat_id: int, text: str, **kwargs):
    SENT_TG.append((int(chat_id), text))
    return [{"message_id": 200 + len(SENT_TG)}]


bridge.tg.call = _mock_tg_call
bridge.tg.try_call = _mock_tg_call
bridge.tg.send_text = _mock_send_text


def text_of(res) -> str:
    if res.commit:
        res.commit()
    return "\n".join(c.get("text", "") for c in res.content)


async def run_all_360_tests() -> None:
    now = bridge.now()
    bridge.ensure_main_conv()
    bridge.store.run(
        "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)",
        (7001, "auouf", "admin", 7001, now),
    )
    bridge.store.run(
        "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)",
        (8002, "GrantedMember", "user", 8002, now),
    )

    # 1. Multi-Main coexistence (main1 + main2) & auto-bootstrap of singleton Controller (ctrl)
    nid1, m1 = bridge.make_main_node(custom_name="主机A")
    assert nid1 == "main1" and m1.startswith("m_")
    # main1 inbox should immediately contain standardized [STANDARD_OP ... type="TASK_LAUNCH" chat="ctrl"]
    m1_inbox = text_of(await bridge.call_tool("read_chat", {"agent": m1, "wait_sec": 0}))
    assert 'type="TASK_LAUNCH" chat="ctrl"' in m1_inbox
    op_match = re.search(r'op_id="(op_[0-9a-f]+)"', m1_inbox)
    assert op_match, m1_inbox
    ctrl_code_match = re.search(r'code="(t-[0-9a-f]+)"', m1_inbox)
    assert ctrl_code_match, m1_inbox

    # main1 submits launch result for ctrl
    sub_res = await bridge.call_tool(
        "submit_op_result",
        {"agent": m1, "op_id": op_match.group(1), "status": "ok", "task_agent_id": "task_ctrl_001"},
    )
    assert not sub_res.is_error
    assert bridge.conv_row("ctrl")["task_agent_id"] == "task_ctrl_001"

    # Singleton Controller joins
    ctrl_join = await bridge.call_tool("join", {"code": ctrl_code_match.group(1)})
    assert not ctrl_join.is_error and "主控大脑" in text_of(ctrl_join)
    ctrl_agent = bridge.conv_row("ctrl")["agent"]
    assert bridge.agent_row(ctrl_agent)["role"] == "ctrl"

    # Add second Main Agent main2 -> main1 MUST remain active!
    nid2, m2 = bridge.make_main_node(custom_name="主机B")
    assert nid2 == "main2"
    assert bridge.agent_row(m1)["status"] == "active"
    assert bridge.agent_row(m2)["status"] == "active"
    bridge.waiting[m1] = 1
    bridge.waiting[m2] = 1

    # 2. Worker (compute node) join: approved by ctrl WITHOUT spamming Admin TG!
    SENT_TG.clear()
    worker_join_task = asyncio.create_task(bridge.call_tool("join", {"mode": "worker", "name": "渲染节点"}))
    await asyncio.sleep(0.08)
    assert SENT_TG == [], f"Worker join should not spam admin TG: {SENT_TG}"
    ctrl_inbox = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_agent, "wait_sec": 0}))
    assert "工作节点入网申请" in ctrl_inbox
    req_m = re.search(r'request_id="([0-9a-f]+)"', ctrl_inbox)
    assert req_m, ctrl_inbox

    app_w = await bridge.call_tool(
        "manage_node",
        {"agent": ctrl_agent, "action": "approve_worker", "request_id": req_m.group(1)},
    )
    assert not app_w.is_error and "node1" in text_of(app_w)
    w_res = await asyncio.wait_for(worker_join_task, timeout=3.0)
    w_txt = text_of(w_res)
    assert "工作区常驻任务会话 node1" in w_txt
    # Harmlessness check: never mention "算力机" to the worker model!
    assert "算力机" not in w_txt
    node1_agent = bridge.conv_row("node1")["agent"]
    bridge.waiting[node1_agent] = 1

    # Cloud-only enforcement on node1: local_shell must fail immediately
    loc_fail = await bridge.call_tool("local_shell", {"agent": node1_agent, "command": "whoami"})
    assert loc_fail.is_error and "云端环境" in text_of(loc_fail)

    # 3. CPU / Memory / Balloon Probe Load Balancing + Model Stability Protection
    bridge.store.run(
        "UPDATE exec_nodes SET metrics_json=?, metrics_ts=? WHERE id='main1'",
        (json.dumps({"cpu_cores": 4, "cpu_percent": 91.5, "load_1m": 3.8, "mem_total_mb": 16000, "mem_usable_mb": 1800, "mem_percent": 88.7}), bridge.now()),
    )
    bridge.store.run(
        "UPDATE exec_nodes SET metrics_json=?, metrics_ts=? WHERE id='main2'",
        (json.dumps({"cpu_cores": 8, "cpu_percent": 7.2, "load_1m": 0.4, "mem_total_mb": 32000, "mem_usable_mb": 29500, "balloon_mb": 4096, "mem_percent": 7.8}), bridge.now()),
    )

    c1 = bridge.create_conv("天文台总监", 7001, name="天文台", owner=0, model="claude-fable-5-2-max")
    # Auto dispatch should pick main2 (low CPU, high usable RAM)!
    disp1 = await bridge.call_tool(
        "dispatch_task_op",
        {"agent": ctrl_agent, "chat": c1["id"], "action": "launch", "target_main": "auto"},
    )
    assert not disp1.is_error and "main2" in text_of(disp1), text_of(disp1)

    # Model change without confirm_model_change=True MUST be blocked!
    disp_bad_model = await bridge.call_tool(
        "dispatch_task_op",
        {"agent": ctrl_agent, "chat": c1["id"], "action": "restart", "model": "gpt-4o-mini"},
    )
    assert disp_bad_model.is_error and "模型保护拦截" in text_of(disp_bad_model)

    # Claim c1 and c2
    c1_code = bridge.conv_row(c1["id"])["task_code"]
    await bridge.call_tool("join", {"code": c1_code})
    a_c1 = bridge.conv_row(c1["id"])["agent"]

    c2 = bridge.create_conv("材质工位", 7001, name="材质组", owner=0)
    await bridge.call_tool("join", {"code": c2["task_code"]})
    a_c2 = bridge.conv_row(c2["id"])["agent"]

    # 4. Machine Exclusivity + Cross-Agent Machine Grant + Remote Workspace Job
    await bridge.call_tool(
        "manage_node",
        {"agent": ctrl_agent, "action": "set_exclusive", "node_id": "node1", "exclusive_chat": c1["id"]},
    )
    # c2 trying to use node1 while exclusive to c1 must fail
    job_denied = await bridge.call_tool(
        "run_workspace_job",
        {"agent": a_c2, "command": "blender -b scene.blend -f 1", "node": "node1"},
    )
    assert job_denied.is_error and "独占锁定" in text_of(job_denied)

    # Controller grants c2 shared access to node1!
    grant_res = await bridge.call_tool(
        "manage_node",
        {"agent": ctrl_agent, "action": "grant_access", "node_id": "node1", "chats": [c2["id"]]},
    )
    assert not grant_res.is_error
    job_ok = await bridge.call_tool(
        "run_workspace_job",
        {"agent": a_c2, "command": "blender -b scene.blend -f 1", "node": "node1", "repo": "stseww3/jvfoedfve", "branch": "main"},
    )
    assert not job_ok.is_error and "node1" in text_of(job_ok)
    n1_inbox = text_of(await bridge.call_tool("read_chat", {"agent": node1_agent, "wait_sec": 0}))
    op_j = re.search(r'op_id="(op_[0-9a-f]+)"', n1_inbox)
    assert op_j and 'type="WORKSPACE_JOB"' in n1_inbox
    await bridge.call_tool(
        "submit_op_result",
        {"agent": node1_agent, "op_id": op_j.group(1), "status": "ok", "output": "Rendered frame_0001.png in 4.2s"},
    )
    c2_inbox = text_of(await bridge.call_tool("read_chat", {"agent": a_c2, "wait_sec": 0}))
    assert "Rendered frame_0001.png" in c2_inbox

    # 5. Non-Admin Granted User: keeps 5-chat access, strictly blocked from spawn_subagent & run_workspace_job!
    ext_conv = bridge.create_conv("外部翻译", 8002, name="翻译助手", owner=8002)
    await bridge.call_tool("join", {"code": ext_conv["task_code"]})
    a_ext = bridge.conv_row(ext_conv["id"])["agent"]
    sp_ext = await bridge.call_tool(
        "spawn_subagent",
        {"agent": a_ext, "brief": "越权开子工", "include_memory": False},
    )
    assert sp_ext.is_error and "仅管理员本人" in text_of(sp_ext)
    jb_ext = await bridge.call_tool(
        "run_workspace_job",
        {"agent": a_ext, "command": "ls"},
    )
    assert jb_ext.is_error and "仅管理员本人" in text_of(jb_ext)

    # Admin subagent spawn with dedicated_machine=True routes cleanly to ctrl
    sp_adm = await bridge.call_tool(
        "spawn_subagent",
        {"agent": a_c1, "brief": "高模烘焙", "include_memory": True, "dedicated_machine": True, "machine_reason": "高内存烘焙"},
    )
    assert not sp_adm.is_error and "申请独占机器" in text_of(sp_adm)

    # 6. 5-Minute Thinking-Stuck Auto-Restart vs Shell Distinction!
    # Case A: phase == 'shell' for 20 minutes -> MUST NOT be marked thinking-stuck or restarted!
    old_c2_agent = bridge.conv_row(c2["id"])["agent"]
    bridge.store.run(
        "INSERT OR REPLACE INTO agent_traces(conv,agent_id,phase,tool_name,summary,started_ts,updated_ts,thought_ts,hb_ts) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (c2["id"], old_c2_agent, "shell", "Shell", "cargo build --release", bridge.now() - 1200, bridge.now() - 1200, bridge.now() - 1200, bridge.now() - 5),
    )
    await bridge.watchdog_tick()
    assert bridge.conv_row(c2["id"])["agent"] == old_c2_agent, "Shell command was falsely restarted as thinking-stuck!"

    # Case B: phase == 'thinking' for > 5 minutes (320s) with active VM heartbeat -> MUST auto-restart!
    old_c1_agent = bridge.conv_row(c1["id"])["agent"]
    bridge.store.run(
        "INSERT OR REPLACE INTO agent_traces(conv,agent_id,phase,tool_name,summary,started_ts,updated_ts,thought_ts,hb_ts) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (c1["id"], old_c1_agent, "thinking", "Read", "思考下一步", bridge.now() - 320, bridge.now() - 320, bridge.now() - 320, bridge.now() - 4),
    )
    await bridge.watchdog_tick()
    assert bridge.agent_row(old_c1_agent)["status"] == "stopped", "5-min thinking-stuck agent was NOT auto-restarted!"
    assert bridge.conv_row(c1["id"])["model"] == "claude-fable-5-2-max"
    # Re-join c1 after auto-restart so it's active for web tests
    await bridge.call_tool("join", {"code": bridge.conv_row(c1["id"])["task_code"]})
    a_c1_new = bridge.conv_row(c1["id"])["agent"]

    # Create an agent collaboration group g1 for Web UI group tests
    grp_res = await bridge.call_tool(
        "create_agent_group",
        {"agent": a_c1_new, "name": "天文台总装群", "members": [c2["id"]], "topic": "总装联调", "welcome": "全员就位"},
    )
    assert not grp_res.is_error

    # 7. Multi-Device (/device add): adding a 2nd PC keeps the 1st PC active!
    dev1 = await bridge.issue_device(7001, "auouf", create_new=True, custom_label="台式机")
    dev2 = await bridge.issue_device(7001, "auouf", create_new=True, custom_label="笔记本")
    assert dev1["id"] != dev2["id"]
    assert bridge.device_row(dev1["id"])["status"] == "active"
    assert bridge.device_row(dev2["id"])["status"] == "active"

    # 8. Compiled dais_runtime.pyz verification (zero .py source inside!)
    pyz_bytes = bridge.build_runtime_pyz()
    assert pyz_bytes.startswith(b"#!/usr/bin/env python3\n")
    pyz_file = TMP_ROOT / "dais_runtime.pyz"
    pyz_file.write_bytes(pyz_bytes)
    pyz_file.chmod(0o755)
    with zipfile.ZipFile(pyz_file, "r") as zf:
        names = zf.namelist()
        assert "__main__.pyc" in names and not any(n.endswith(".py") for n in names), names
    env_sub = dict(os.environ, HOME=str(HOME_DIR))
    inst = subprocess.run([sys.executable, str(pyz_file), "install", "http://127.0.0.1:18788"], env=env_sub, capture_output=True, text=True, check=True)
    assert "dais_runtime.pyz" in inst.stdout
    assert (HOME_DIR / ".cursor" / "dais_runtime.pyz").exists()

    # Kill daemon spawned in fake HOME
    pid_f = HOME_DIR / ".cursor" / "agent_trace_daemon.pid"
    if pid_f.exists():
        try:
            os.kill(int(pid_f.read_text().strip()), 9)
        except Exception:
            pass

    # 9. Web Console End-to-End API & Security Verification
    SUPER_SECRET_PW = "Zwt_UltraSecret_#998877!"
    SUB_USER_PW = "Alice_Pass_12345!"
    transport = httpx.ASGITransport(app=bridge.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # HTML index
        r_html = await client.get("/web")
        assert r_html.status_code == 200 and "Bridge Studio" in r_html.text

        # Initial status -> zwt needs first-visit password setup
        st0 = (await client.get("/web/api/auth/status")).json()
        assert st0["authenticated"] is False and st0["zwt_needs_setup"] is True

        # Non-zwt cannot use setup-zwt
        bad_setup = await client.post("/web/api/auth/setup-zwt", json={"username": "hacker", "password": "password123"})
        assert bad_setup.status_code == 403

        # First-time zwt self-setup
        r_setup = await client.post("/web/api/auth/setup-zwt", json={"username": "zwt", "password": SUPER_SECRET_PW})
        assert r_setup.status_code == 200 and r_setup.json()["ok"] is True

        # Second setup attempt on zwt MUST be rejected (409)
        r_setup2 = await client.post("/web/api/auth/setup-zwt", json={"username": "zwt", "password": "anotherpassword"})
        assert r_setup2.status_code == 409

        # Verify password stored hashed, NOT plaintext in SQLite AND NOT in bridge.log!
        zwt_db = bridge.store.one("SELECT password_hash FROM web_users WHERE username='zwt'")
        assert zwt_db["password_hash"].startswith("pbkdf2_sha256$") and SUPER_SECRET_PW not in zwt_db["password_hash"]

        # Bootstrap data includes ctrl, main1, main2, c1, c2, g1, and CPU/RAM probes
        boot = (await client.get("/web/api/bootstrap")).json()
        assert boot["ok"] is True
        assert any(n["id"] == "main2" and n["metrics"]["balloon_mb"] == 4096 for n in boot["nodes"])
        assert any(g["id"] == "g1" for g in boot["groups"])

        # Upload image (simulating drag-drop / clipboard paste) & send message to c1
        fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR_FAKE_IMAGE_DATA"
        up_res = await client.post(
            f"/web/api/upload?conv={c1['id']}",
            content=fake_png,
            headers={"X-File-Name": "concept_art.png", "X-File-Mime": "image/png"},
        )
        assert up_res.status_code == 200 and up_res.json()["file"]["is_image"] is True
        fid = up_res.json()["file"]["file_id"]

        send_m = await client.post(f"/web/api/convs/{c1['id']}/messages", json={"text": "初版提示词", "file_ids": [fid]})
        assert send_m.status_code == 200
        mid = send_m.json()["message_ids"][0]

        # Edit message & verify DB updated
        edit_m = await client.patch(f"/web/api/messages/{mid}", json={"text": "修改后的精准提示词V2"})
        assert edit_m.status_code == 200
        msgs_c1 = (await client.get(f"/web/api/convs/{c1['id']}/messages")).json()["messages"]
        assert any(m["id"] == mid and m["text"] == "修改后的精准提示词V2" and m["file"]["file_id"] == fid for m in msgs_c1)

        # Send another message and delete it
        send_m2 = await client.post(f"/web/api/convs/{c1['id']}/messages", json={"text": "误发的一条废话"})
        mid2 = send_m2.json()["message_ids"][0]
        del_m2 = await client.delete(f"/web/api/messages/{mid2}")
        assert del_m2.status_code == 200
        msgs_after_del = (await client.get(f"/web/api/convs/{c1['id']}/messages")).json()["messages"]
        assert not any(m["id"] == mid2 for m in msgs_after_del)

        # Full-context one-click restart -> verify ctrl receives complete dossier (model, edited history, group g1, note)!
        rs_web = await client.post(
            f"/web/api/convs/{c1['id']}/restart",
            json={"target_main": "main2", "note": "已删掉误发消息并改好提示词V2"},
        )
        assert rs_web.status_code == 200 and rs_web.json()["routed_to"] == "ctrl"
        ctrl_dossier = text_of(await bridge.call_tool("read_chat", {"agent": ctrl_agent, "wait_sec": 0}))
        assert "claude-fable-5-2-max" in ctrl_dossier
        assert "修改后的精准提示词V2" in ctrl_dossier
        assert "g1「天文台总装群」" in ctrl_dossier
        assert "已删掉误发消息并改好提示词V2" in ctrl_dossier
        assert "main2" in ctrl_dossier

        # Agent Group g1 view & human speaking directly inside group!
        g_post = await client.post(
            "/web/api/groups/g1/messages",
            json={"text": "请材质组把铜件粗糙度调到 0.35", "file_ids": [fid], "mentions": [c2["id"]]},
        )
        assert g_post.status_code == 200 and c2["id"] in g_post.json()["woke"]
        g_view = (await client.get("/web/api/groups/g1/messages")).json()
        assert any("0.35" in gm["text"] for gm in g_view["messages"])
        c2_grp_inbox = text_of(await bridge.call_tool("read_chat", {"agent": a_c2, "wait_sec": 0}))
        assert "0.35" in c2_grp_inbox

        # User Management: zwt creates 'alice'; verify 'alice' CANNOT access /web/api/users or zwt's chats!
        mk_alice = await client.post(
            "/web/api/users",
            json={"username": "alice", "display_name": "Alice", "password": SUB_USER_PW},
        )
        assert mk_alice.status_code == 200

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as alice_client:
        r_al = await alice_client.post("/web/api/auth/login", json={"username": "alice", "password": SUB_USER_PW})
        assert r_al.status_code == 200 and r_al.json()["user"]["is_zwt"] is False
        # Alice blocked from user management (zwt-only!)
        assert (await alice_client.get("/web/api/users")).status_code == 403
        assert (await alice_client.post("/web/api/users", json={"username": "bob", "password": "password123"})).status_code == 403
        # Alice blocked from reading zwt's c1 chat!
        assert (await alice_client.get(f"/web/api/convs/{c1['id']}/messages")).status_code == 403

    # Verify ZERO password leak in bridge.log!
    log_text = (DATA_DIR / "bridge.log").read_text(encoding="utf-8")
    assert SUPER_SECRET_PW not in log_text and SUB_USER_PW not in log_text, "Password leaked in log!"


if __name__ == "__main__":
    asyncio.run(run_all_360_tests())
    print("ALL_360_TESTS_PASSED_OK")
