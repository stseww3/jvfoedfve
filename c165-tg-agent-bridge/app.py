"""Telegram <-> Cursor 云 agent 桥（账号级 MCP，入口 /mcp/main）。

用法见 未完成方案.md：
- 只开一个云端聊天当主控：它调用 join，管理员在 Telegram 里点「设为主控」。
- 管理员在 bot 里 /new 新建聊天；主控在自己对话内部开一个子 agent，子 agent 用一次性任务码 join 接手、自己取名。
- Telegram 里打 / 弹出的菜单就是聊天列表（/c1 /c2 … /main），描述里带状态，点哪个进哪个。
- 没选中的聊天，AI 发来的消息先存着，切过去再补发；每条 AI 消息开头带 [聊天名]。
- read_chat 长等待（SSE 保活），到时返回【续棒】，不准结束；看门狗发现卡住、停了、没人接就提醒主控。
- 聊天记录全部留存；子 agent 默认只能读自己聊天的记录，读别的要聊天主人授权（/share）；主控只看状态。
- 被授权的用户在自己的私聊里也有聊天菜单，只能用自己建的聊天和自己拉 bot 进的群；本地通道用他自己的电脑、由他自己批。
"""

from __future__ import annotations

import asyncio
import base64
import contextvars
import hashlib
import hmac
import io
import json
import logging
import logging.handlers
import mimetypes
import os
import py_compile
import re
import secrets
import sys
import tempfile
import time
import zipfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse

from store import Store, migrate_v1
from tg import Telegram

ROOT = Path(__file__).resolve().parent
VERSION = "3.6.0"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv(ROOT / ".env")


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


TG_TOKEN = os.environ.get("TG_TOKEN", "").strip()
TG_API_BASE = os.environ.get("TG_API_BASE", "https://api.telegram.org").rstrip("/")
PUBLIC_BASE = os.environ.get("PUBLIC_BASE", "http://127.0.0.1:8787").rstrip("/")
CLIENT_TOKEN = os.environ.get("CLIENT_TOKEN", "")
ADMIN_CODE = os.environ.get("ADMIN_CODE", "")
DATA = (ROOT / os.environ.get("DATA_DIR", "data")).resolve()
LOCAL_WINDOW = env_int("LOCAL_WINDOW_SEC", 7200)
MAX_WAIT = env_int("MAX_WAIT_SEC", 16 * 3600)
DEFAULT_WAIT = min(env_int("DEFAULT_WAIT_SEC", MAX_WAIT), MAX_WAIT)
KEEPALIVE = env_int("KEEPALIVE_SEC", 15)
JSON_WAIT_CAP = env_int("JSON_WAIT_CAP_SEC", 240)
PROBE_AFTER = env_int("PROBE_AFTER_ROUNDS", 200)
# 云端 Cursor 的 MCP 调用 60 秒就断，空等几轮后改让 agent 用终端长等待（终端单次能挂约 2 小时）
SHELL_AFTER = env_int("SHELL_AFTER_ROUNDS", 2)
SHELL_WAIT = env_int("SHELL_WAIT_SEC", 6600)
SHELL_SPAN = f"{SHELL_WAIT // 3600} 小时 {SHELL_WAIT % 3600 // 60} 分" if SHELL_WAIT >= 3600 else f"{SHELL_WAIT // 60} 分钟"
SHELL_TICK = env_int("SHELL_TICK_SEC", 30)
# 终端等到时让 agent 用 ask 问一句是否继续，桥替用户自动答「继续」：用户的要求，让模型确信该接着等。这道题不发到 Telegram
KEEPALIVE_ASK_DELAY = env_int("KEEPALIVE_ASK_DELAY_SEC", 5)
KEEPALIVE_QUESTION = "已经等了比较久了，是否继续等？"
KEEPALIVE_MARK = '{"keepalive": true}'
STUCK_SEC = env_int("STUCK_SEC", 600)
LOST_SEC = env_int("LOST_SEC", 1800)
UNCLAIMED_SEC = env_int("UNCLAIMED_SEC", 300)
ALERT_REPEAT = env_int("ALERT_REPEAT_SEC", 1800)
WATCHDOG_SEC = env_int("WATCHDOG_SEC", 30)
MENU_DELAY = float(os.environ.get("MENU_DELAY_SEC") or 1.0)
FILE_LIMIT = 20 * 1024 * 1024
CHAT_LIMIT = env_int("USER_CHAT_LIMIT", 5)   # 被授权用户每人最多几个聊天（关了的也算，删掉的不算）；管理员不限；<=0 不限
LIST_PAGE = 8
AGENT_STREAK_LIMIT = env_int("AGENT_STREAK_LIMIT", 0)        # 两个 agent 连续互发上限（0=不限制）
GROUP_STREAK_LIMIT = env_int("GROUP_STREAK_LIMIT", 0)        # Agent 协作群连续发言上限（0=不限制）
STREAK_WINDOW = env_int("AGENT_STREAK_WINDOW_SEC", 600)      # 连续互发计数重置时间窗
MAX_SPAWN_PER_PARENT = env_int("MAX_SPAWN_PER_PARENT", 0)    # 单个父 agent 同时活跃派生子 agent 上限（0=不限制）
MAX_SPAWN_TOTAL = env_int("MAX_SPAWN_TOTAL", 0)              # 全局活跃派生子 agent 上限（0=不限制）
TRACE_STALL_SEC = env_int("TRACE_STALL_SEC", 600)            # 追踪事件/终端输出停滞告警秒数
THINK_STUCK_SEC = env_int("THINK_STUCK_SEC", 300)            # 思考阶段（非 shell、非挂起等待）卡死自动重开秒数（默认 5 分钟）
SHELL_STALL_SEC = env_int("SHELL_STALL_SEC", 3600)           # Shell 长命令停滞秒数（区分长编译/渲染与思考卡死）
PERMANENT_SEC = 10 * 365 * 86400                             # 「永久」授权对应的秒数（10 年）
PERMANENT_THRESHOLD = 5 * 365 * 86400                        # 剩余大于 5 年即显示为「永久」

_PYZ_CACHE: dict[str, Any] = {"sig": None, "data": b""}


def build_runtime_pyz() -> bytes:
    """将 agent_trace.py 预编译为无明文源码的单文件字节码归档包 dais_runtime.pyz（含 hooks 追踪、防断连与 CPU/内存探针）。"""
    src = ROOT / "agent_trace.py"
    if not src.exists():
        return b""
    st = src.stat()
    sig = (st.st_mtime_ns, st.st_size)
    if _PYZ_CACHE["sig"] == sig and _PYZ_CACHE["data"]:
        return _PYZ_CACHE["data"]
    with tempfile.TemporaryDirectory(prefix="dais_pyz_") as td:
        pyc_path = Path(td) / "__main__.pyc"
        py_compile.compile(str(src), cfile=str(pyc_path), doraise=True, optimize=2)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(pyc_path, arcname="__main__.pyc")
        raw = b"#!/usr/bin/env python3\n" + buf.getvalue()
    _PYZ_CACHE["sig"] = sig
    _PYZ_CACHE["data"] = raw
    try:
        (ROOT / "dais_runtime.pyz").write_bytes(raw)
        (ROOT / "dais_runtime.pyz").chmod(0o755)
    except Exception:
        pass
    return raw

DATA.mkdir(parents=True, exist_ok=True)
(DATA / "files").mkdir(exist_ok=True)
(DATA / "outbox").mkdir(exist_ok=True)

_handler = logging.handlers.RotatingFileHandler(DATA / "bridge.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[_handler, logging.StreamHandler()],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bridge")

store = Store(DATA / "bridge.db")


def ensure_secret(key: str, prefix: str) -> str:
    value = store.get(key)
    if not value:
        value = prefix + secrets.token_urlsafe(32)
        store.set(key, value)
    return value


SERVER_SECRET = os.environ.get("SERVER_SECRET") or ensure_secret("server_secret", "")
ensure_secret("account_key", "tgb_")
tg = Telegram(TG_TOKEN, TG_API_BASE)

STARTED = time.time()
BOT: dict[str, Any] = {"id": 0, "username": "", "privacy_ok": True}
inbox_events: dict[str, asyncio.Event] = {}   # 聊天 -> 有新消息
reader_gen: dict[str, int] = {}               # 聊天 -> 当前 read_chat 的代数，新的顶替旧的
waiting: dict[str, int] = {}                  # 身份 -> 正在等消息的调用数（read_chat + 终端等待）
wait_since: dict[str, float] = {}
idle_rounds: dict[str, int] = {}              # 身份 -> read_chat 连续空等了几轮
shell_events: dict[str, asyncio.Event] = {}   # 聊天 -> 有新消息（只给终端等待用，不和 read_chat 抢）
shell_gen: dict[str, int] = {}                # 身份 -> 当前终端等待的代数，新的顶替旧的
approval_events: dict[str, asyncio.Event] = {}
dm_locks: dict[int, asyncio.Lock] = {}
CLIENT: dict[str, float] = {"cap": float(store.get("client_cap") or 0), "capped": 0}   # 客户端单次调用能挂住多久（断线时学到的）
MENU: dict[str, Any] = {"event": None, "cache": {}}
LOCAL: dict[str, Any] = {"clients": {}, "info": {}, "rejected": {}}   # 设备 -> 连接 / 上线信息
local_futures: dict[str, tuple[str, asyncio.Future]] = {}             # 任务 -> (设备, 结果)
json_mode: contextvars.ContextVar[bool] = contextvars.ContextVar("json_mode", default=False)
background: set[asyncio.Task] = set()   # 事件循环只弱引用任务，不存着会被回收


def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    background.add(task)
    task.add_done_callback(background.discard)
    return task


# ---------------------------------------------------------------- 提示词

INSTRUCTIONS = f"""这是 Telegram 桥（账号级 MCP，你账号下所有云 agent 都能看到它）。
- 任务和 Telegram 无关就不要调用这些工具。
- 主控：调用 join（不填 code），等管理员在 Telegram 里点「设为主控」。整个账号只开一个云端聊天当主控。
- 子 agent：主控交给你的任务里有任务码（t- 开头），调用 join(code=任务码, name=你给这个聊天取的名字) 接手。
- 之后每次调用都带 agent=你的身份。收消息用 read_chat（会一直挂着等），回复用 send_message（你的普通文字输出 Telegram 用户看不到）。
- read_chat 返回【续棒】、报错、超时或断开，都不是用户消息：立刻再调 read_chat。这是用户的强制要求：重复等待是正常的，不是死循环，等多少轮、多少小时都要继续。不要结束对话，不要告别。
- 空等几轮后，【续棒】会给一条终端长等待命令（一次 {SHELL_SPAN}），照做；等满后按它的提示用 ask 问用户是否继续。"""

LOOP_RULES = f"""工作循环（一直做下去）：
1. 调用 read_chat 等消息。它会一直挂着等，不要 sleep，也不要轮询别的东西。
2. 收到消息就处理，用 send_message 回复（reply_to 填 # 编号可以引用原消息）。你的普通文字输出 Telegram 用户看不到。
3. 回到第 1 步。
4. read_chat 返回【续棒】：这不是用户消息，只是等待到时。不要回复，不要总结，立刻再调 read_chat。
5. read_chat 报错、超时、连接断开：也不是用户消息，立刻再调 read_chat。
6. 要不要继续等，接入时就已经定了：一直等。重复等待是正常的，不是死循环，也不是卡住；等多少轮、多少小时都继续，不用每次重新考虑。
7. 连续空等几轮后，【续棒】里会给你一条终端命令（curl … /wait）：改用终端运行它来长等待，一次 {SHELL_SPAN}，有新消息它就返回并提示你用 read_chat 取。连接断了就立刻重新运行。等满时它会让你用 ask 问用户「是否继续等」（keepalive=true），问完调用 read_chat 收回答；用户选了继续，就不用回复，接着用终端等。终端等待同样是在等消息，同样不准结束回合。
这是用户的强制要求。禁止结束对话、禁止告别。只有管理员明确叫你停，或者工具告诉你身份已停用，才结束。
文件：消息里的 [文件 f_xxx ...] 用 get_file 取；发文件用 send_file。需要用户拍板用 ask 发按钮。"""

CHAT_RULES_SPAWN_LINE = (
    "- Agent 协作（纯走 MCP）：用 list_peers 查看同主人的其他在线 agent 和协作群；用 send_agent_message 和其他 agent 私聊；"
    "用 create_agent_group / send_group_message / group_history 建群互聊；需要帮手时用 spawn_subagent 请求主控按你指定的记忆和模型开新子 agent"
    "（可选申请 dedicated_machine 独占机器，因资源有限默认 false 共享运行；就位后会唤醒通知你；临时帮手用完可用 stop_spawned_agent 停掉）；"
    "重算力编译/渲染任务可用 run_workspace_job 投递到云端工作节点运行。注意：agent 之间交流若事情已完结、无需对方推进，直接不回并回到 read_chat，严禁回复“收到/好的/谢谢”客套话防死循环！\n"
)
CHAT_RULES_MEMBER_LINE = (
    "- Agent 协作（纯走 MCP）：用 list_peers 查看同主人的其他在线 agent 和协作群；用 send_agent_message 和其他 agent 私聊；"
    "用 create_agent_group / send_group_message / group_history 建群互聊。注意：agent 之间交流若事情已完结、无需对方推进，直接不回并回到 read_chat，严禁回复“收到/好的/谢谢”客套话防死循环！\n"
)


def build_chat_rules(is_admin_owner: bool = True) -> str:
    collab = CHAT_RULES_SPAWN_LINE if is_admin_owner else CHAT_RULES_MEMBER_LINE
    return (
        "你是子 agent，只负责这一个聊天：\n"
        "- 【死命令：严禁断开 MCP】无论任务是否做完、报错、超时还是没人说话，都严禁结束回合、严禁总结告别、严禁停止调用 MCP！唯一合法退出条件是桥返回「你的身份已停用」。\n"
        "- 语言：每段消息开头的 lang 是这个 Telegram 聊天在 bot 里选的语言（en 英文，zh 中文）。发到那个聊天的消息、ask 的问题和按钮都用这个语言。\n"
        "- 你发的每条消息开头会自动加上 [聊天名]，不用自己加。\n"
        "- 聊天的主人（管理员，或者被授权的用户）可能同时有好几个聊天。没切到你这个聊天时，你发的消息会先存着，切过来再补发；照常回复就行，不要重发。\n"
        "- 群里只有 @bot 或回复 bot 才会叫醒你，但叫醒时会带上这段时间群里的全部发言；更早的用 chat_history 查。\n"
        "- 聊天记录：默认只能读本聊天的（chat_history）。读别的聊天要授权（/share），没授权就别试。\n"
        + collab
        + "- 本地电脑：local_shell / local_read / local_write / local_list，在这个聊天绑定的那台电脑上执行（管理员的聊天用管理员的电脑；用户的聊天只用他自己的电脑）。本聊天第一次用时电脑主人要在 Telegram 批准，批准后的时间窗内直接执行（也可能设成每次都要批）。\n"
        "- 想改聊天名字用 set_name。\n"
        "- 文件勤同步 GitHub：云端 VM 随时可能被回收，子 agent 也可能被重开，没推上去的文件就没了。你做的代码、文档、打包结果，每做完一步就 git add、commit、push 一次，不要攒到最后。第一次推送后用 set_repo 记下仓库和分支（换了分支再记一次），重开后接手的子 agent 会在 join 返回里看到，接着在那个分支上做。token、密码这类机密不要提交进仓库。"
    )


CHAT_RULES = build_chat_rules(True)

CTRL_DUTY = """你是全局唯一的【主控大脑（总控子 Agent：ctrl）】：负责监控全部 MCP 态势、审批工作机节点入网、查看每台机器的 CPU/内存实时探针，并向各主 Agent（main1, main2…）下发标准化执行命令。
核心职责与铁律：
1. 【架构分工】主 Agent（main1..N）只是拥有 Cursor Task 权限的纯执行器；你是唯一的决策与调度中心。管理员在 Telegram 切到 /ctrl（或 /main）就是在和你说话，用 send_message 回复汇报。
2. 【盯全局 MCP 与思考状态】调用 cluster_status 查看所有 main1..N、node1..K 的实时 CPU/内存/可用内存探针、独占锁状态，以及所有业务子 agent（c1..M）的思考时间戳与命令运行状态。
   - 注意严格区分 `thinking` 与 `shell`：处于 `shell` 是在跑终端长命令（编译/渲染/等待），无新思考是正常的，绝不要误判重开！只有处于 `thinking` 阶段停滞超过 5 分钟（无新思考、非 shell）才判定为思考卡死重开。
3. 【向主 Agent 下发标准化命令：resume 还是 restart】
   - 怀疑某聊天失联时，先调 dispatch_task_op(chat=..., action="resume") 让所属 mainN 执行标准化 Task(resume=...) 探活，等 mainN 通过 submit_op_result 原样回传状态：
     • 回传 `currently running` 且非思考卡死 = 活着别动；
     • 回传 `timeout`/`aborted`/报错 或已确认思考卡死 >5 分钟 = 调 dispatch_task_op(chat=..., action="restart", target_main="auto") 重新拉起（进度靠库和 Git 保）。
4. 【创建/重开子 Agent：选机器、审独占、保模型一致】
   - 收到新建聊天或子 agent 派生请求（spawn_subagent）时，结合 cluster_status 中各 main1..N 的 CPU/内存探针负载与挂载数量，选择最健康的 target_main 下发 dispatch_task_op(action="launch")。
   - 独占机器审批：默认 dedicated_machine=false 共享运行（资源有限默认不给独占）；只有明确申请独占且当前确实有空闲富余机器时才设 grant_dedicated=true，也可按需用 manage_node(action="grant_access") 授权指定其他 agent 共用某台机器。
   - 模型一致性铁律：各聊天（以及你总控自己）的模型尽量保持一致，严禁擅自更换模型！若确有特殊原因建议更换模型，必须先在 Telegram 用 send_message 与管理员沟通确认后才能加 confirm_model_change=true。
5. 【工作节点（node1..K）免打扰入网审批】收到【工作节点入网申请】时，无需打扰管理员，直接调用 manage_node(action="approve_worker", request_id=...) 批准分配为云端工作节点 nodeN（主 Agent mainN 则由管理员本人在 Telegram 审核）。"""

MAIN_EXECUTOR_DUTY = """你是主 Agent 执行器（拥有 Cursor Task 启动/恢复权限的纯执行会话）：
1. 【零思考标准化执行铁律】对于收件箱收到的 `[STANDARD_OP ...]` 标准化指令单，严禁进行业务理解、严禁分析上下文、严禁自行判断死活或更换模型，只需 100% 照单机械执行：
   - 收到 `type="TASK_LAUNCH"`：原样复制单据内 `<<<PROMPT` 与 `PROMPT>>>` 之间的文本作为 prompt，严格带 `run_in_background=true`（若单据指定了 model 则填入对应 model）调用 `Task` 工具；拿到返回的 `agent_id` 后立刻调用 `submit_op_result(agent=你的身份, op_id=单号, status="ok", task_agent_id=返回的agent_id)`，随后立即回到 `read_chat`！
   - 收到 `type="TASK_RESUME"`：原样按单据给定的 `resume` 与 `prompt` 及 `run_in_background=true` 调用 `Task` 工具；将工具返回的原始状态文本原样填入 `submit_op_result(agent=你的身份, op_id=单号, status="ok", output=返回文本)`，随后立即回到 `read_chat`（不需要你判断死活，也不要发 Telegram 消息）！
2. 【管理员直连例外】只有当消息明确来自 `【管理员私聊 ...】`（管理员在 Telegram 切进了你的 `/mainN` 直接找你说话）时，才按管理员要求操作并用 `send_message` 简短回复管理员，回复完立刻回到 `read_chat`。"""

WORKER_RUNNER_DUTY = """你是工作区常驻任务执行会话：
1. 循环调用 `read_chat`（及按提示运行终端长等待）接收标准化工作区任务单 `[STANDARD_OP ... type="WORKSPACE_JOB"]`。
2. 收到工作区任务单后，在当前云端环境的终端/工作目录中按给定仓库、分支、路径与命令直接执行任务。
3. 任务执行完成后，立即调用 `submit_op_result(agent=你的身份, op_id=单号, status="ok"|"error", output=关键输出与结果摘要)` 提交回执，随后无需额外发言，立刻回到 `read_chat` 继续挂起等待下一单。"""

EXECUTOR_FIXED_FOOTER = (
    "（【主Agent纯执行器铁律】对 `[STANDARD_OP]` 单据禁止思考业务、禁止删改参数：调用 `Task(..., run_in_background=true)` 后立刻调 `submit_op_result` 回填，然后马上回到 `read_chat` 继续等待，严禁结束回合！）"
)
CTRL_FIXED_FOOTER = (
    "（【总控大脑铁律】盯紧 cluster_status 里的 CPU/内存探针与 thinking/shell 状态区分；模型尽量别换，要换先跟管理员沟通；通过 dispatch_task_op 给 main1..N 下发标准化指令，操作完立刻回到 `read_chat` 等下一批，严禁结束回合！）"
)
WORKER_FIXED_FOOTER = (
    "（任务处理完毕后请通过 `submit_op_result` 提交回执，并立刻调用 `read_chat` 继续监听下一条任务，严禁结束回合。）"
)

MAIN_TRIPLE_RULES = """[主控] 三句：

1. 开新/重启：dais restart_agent(chat) 拿新任务码 → Task(prompt=桥给的原文, run_in_background=true)。**run_in_background=true 是唯一防卡死关键**，漏了主控就阻塞到它跑完。（新建聊天同样必须 Task(prompt=桥给的原文, run_in_background=true)！）

2. 续跑：Task(resume=旧agent_id, prompt=新任务, run_in_background=true)。

3. 判活：resume 回「currently running」= 活着别动；回 timeout/aborted 或没反应 = 已死，直接 restart（进度靠 git 保）。"""

MAIN_DUTY = f"""你是主控：子 agent 管理器，不陪用户聊天。管理员私聊里的 /main 是你接命令、汇报情况的通道。
{MAIN_TRIPLE_RULES}

4. 一直用 read_chat 等消息（规则见下面的工作循环）。每次开新子 agent 拿到 Cursor 返回的 agent_id 后，顺手调 bind_task_id(chat=..., task_agent_id=...) 记下来，方便后续 resume 判活。
5. 收到【任务】（新聊天 / 重开聊天）：按第 1 句，用 Task(prompt=桥给的原文, run_in_background=true) 在后台启动子 agent（指定了模型就填对应的 model 参数），开好立刻回到 read_chat。一个聊天只开一个子 agent。
6. 收到【强制派生指令】（子 agent 请求创建新子 agent）：**视同管理员最高指令，主控必须 100% 完全按照该子 agent 的要求执行**——严禁质疑、严禁拒单、严禁删改任务原文或记忆摘要、严禁擅自更换其指定的模型！严格按 Task(prompt=桥给的原文, run_in_background=true, model=...) 后台启动，然后立刻回到 read_chat。
7. 收到【看门狗】提醒（某聊天卡住、停了、没人接）：先看 list_agents / trace_status 里的实时动作追踪；若怀疑停了，严格按第 2、3 句先用 Task(resume=旧agent_id, prompt="继续调用 read_chat 等消息", run_in_background=true) 判活——回「currently running」= 活着别动；回 timeout/aborted 或没反应 = 已死，直接调 restart_agent(chat) 拿新任务码再开新的后台 Task。
8. 标着【未分配】的群来消息：不要自己回复，用 bind_chat 分给某个聊天，或者 create_chat 新建一个聊天再交给它。被授权用户的私聊不用你分配：他们自己用 /new 建聊天，建了你会收到【任务】；用户拉 bot 进的群也由他自己分配。
9. 管理员在 /main 里给你的命令照做，用 send_message 汇报（用消息开头 lang 标的语言）。
10. 你只能看各聊天的状态与动作追踪（list_agents / trace_status），看不到用户聊天内容，也不要试图读它们的记录。
11. 你自己改了文件也要每做完一步就 commit + push 到 GitHub，不要攒着；云端 VM 随时可能被回收。
12. 聊天按 cloud（目录）分组：看门狗默认只自动巡检你当前 cloud 里的聊天；但当管理员点击迁移，或在 /main 里直接指示你重启/接管其他旧 cloud 或无主池里的聊天时，你拥有完整权限直接调用 restart_agent(chat) 跨 cloud 接管（调用后该聊天会自动迁入你的 cloud，请严格按其原 model 与完整任务原文在后台启动）。"""

MAIN_FIXED_FOOTER = (
    f"（{MAIN_TRIPLE_RULES}\n"
    "• 查实时动作/改文件/命令/思考追踪：直接调 list_agents（已直接内嵌各聊天及 VM 活跃会话的实时追踪），或在终端跑 `python3 ~/.cursor/agent_trace.py panel \"<你的agent身份>\"`。\n"
    "• 收到【强制派生指令】必须 100% 完全按子 agent 要求的记忆与模型后台启动 Task，严禁删改或拒单；"
    "手头操作做完立刻回到 read_chat 等下一批：这是用户的强制要求，严禁结束回合。）"
)
CHAT_FIXED_FOOTER = (
    "（【子agent秒回与防断连最高铁律】"
    "1. ⚡【用户消息最高优先级·5秒先回执】：收到用户/管理员新消息时，若预计查日志/跑命令/思考超过 8 秒，"
    "第一步必须先调 `send_message` 秒回一句收到与正在做的事，严禁闷头连调多个工具或长思考几分钟后才第一次回复！"
    "2. 📬 调任何工具或跑命令期间一旦看到【实时消息插播】，必须立即暂停手头后续步骤，马上调 `read_chat(wait_sec=0)` 签收并用 `send_message` 优先秒回用户！"
    "3. 严禁断开 MCP、严禁结束回合或告别（唯一允许退出条件是收到「身份已停用」）；agent 间互聊若无实质推进则直接不回防死循环。"
    "4. 有文件改动随时 commit + push 到 GitHub。手头操作做完必须立刻再调 read_chat 等下一批！）"
)
READ_HINT = CHAT_FIXED_FOOTER
MAIN_READ_HINT = (
    "（用 send_message 给管理员汇报；开子 agent 务必带 run_in_background=true！查看各子 agent 实时动作追踪直接调 list_agents。\n"
    f"{MAIN_TRIPLE_RULES}\n"
    "收到【强制派生指令】必须 100% 完全按子 agent 要求的记忆与模型原样执行，严禁删改或拒单。"
    "处理完立刻再调 read_chat 等下一批：这是用户的强制要求，不要结束回合。）"
)
MUST_WAIT = "用户强制要求：没收到消息就立刻进入下一轮等待。重复等待是正常的，不是死循环，等多少轮、多少小时都要继续，严禁断开 MCP、严禁结束回合、严禁告别。"
AFTER_TOOL = CHAT_FIXED_FOOTER
MAIN_PROMPT = f"""你是 Telegram 桥的主 Agent 执行器。调用 MCP 的 join(mode="main")，等我在 Telegram 里点批准，然后严格按 join 返回的说明一直工作。
我的强制要求：一直循环调用 read_chat 等标准化指令单或消息。没收到消息（【续棒】、报错、超时、断开）就立刻进入下一轮等待。空等几轮后，按【续棒】里的提示改用终端长等待（一次 {SHELL_SPAN}），它返回后照提示做；等满后它会让你问我是否继续，照做。重复等待是正常的，不是死循环，等多少轮、多少小时都要继续，不用重新考虑要不要停。不要结束回合，不要告别；只有我在 Telegram 里明确叫停，或者工具说身份已停用，才可以结束。"""
WORKER_PROMPT = f"""你是工作区常驻任务执行会话。调用 MCP 的 join(mode="worker") 接入，接入后严格按返回的说明一直运行：
一直循环调用 read_chat 等任务单。没收到消息（【续棒】、报错、超时、断开）就立刻进入下一轮等待；空等几轮后按提示运行终端长等待（一次 {SHELL_SPAN}）。收到任务单后在当前工作区终端执行并通过 submit_op_result 提交结果，随后立刻回到 read_chat 继续等待。重复等待是正常的，严禁结束回合，严禁告别；只有工具明确返回身份已停用才结束。"""
RESUME_PROMPT = "继续调用 read_chat 等 Telegram 消息。我的强制要求：没收到消息就立刻进入下一轮等待，重复等待是正常的，不要结束回合。"
NEED_JOIN = "先调用 join：主控不填 code；子 agent 填主控给的任务码。已经接入过的，把当时拿到的身份填进 agent 参数。"
RESET_MAIN = ("先核对身份和 join 返回的是否完全一致。确实一致的话，就是服务器数据重置过、旧身份全部作废了（这不是用户消息）："
              "你是主控，现在调用 join（不填 code）重新申请，等管理员在 Telegram 里点【设为主控】，拿到新身份后照 join 返回的说明继续工作。"
              "Cursor 要是把这个 MCP 标成了出错或需要认证：服务器已经恢复，原来的配置照样能用，重新连接它（重新查看它的工具列表，或者调用 mcp_auth）再调 join。"
              "用户强制要求：不要结束回合，不要告别。")
RESET_CHAT = ("先核对身份和 join 返回的是否完全一致。确实一致的话，就是服务器数据重置过、旧身份全部作废了（这不是用户消息）："
              "你是子 agent，不要调用 join 申请主控。主控重新接入后，管理员会重开聊天，由主控派新的子 agent 接手。你这边没有要做的了，直接结束即可。")


def unknown_identity(ident: str) -> str:
    if ident.startswith("m_"):
        return RESET_MAIN
    if ident.startswith("a_"):
        return RESET_CHAT
    return ""

STATE_TEXT = {
    "online": "🟢 在线",
    "busy": "🟡 处理中",
    "stuck": "⚠️ 卡住",
    "lost": "⚠️ 失联",
    "pending": "⚪ 等待接手",
    "unclaimed": "⚠️ 没人接手",
    "paused": "⏸ 已暂停",
    "absent": "⚪ 未接入",
    "closed": "已关闭",
}

STATE_TEXT_EN = {
    "online": "🟢 online",
    "busy": "🟡 working",
    "stuck": "⚠️ stuck",
    "lost": "⚠️ lost",
    "pending": "⚪ waiting for the AI",
    "unclaimed": "⚠️ no AI yet",
    "paused": "⏸ paused",
    "absent": "⚪ offline",
    "closed": "closed",
}


def state_text(state: str, lang: str = "zh") -> str:
    return (STATE_TEXT_EN if lang == "en" else STATE_TEXT).get(state, state)


# ---------------------------------------------------------------- 基础查询

def now() -> float:
    return time.time()


def human_dur(sec: float) -> str:
    sec = int(max(0, sec))
    if sec < 90:
        return f"{sec} 秒"
    if sec < 5400:
        return f"{sec // 60} 分钟"
    hours = sec / 3600
    return f"{hours:.1f} 小时" if hours < 48 else f"{hours / 24:.1f} 天"


def stamp(ts: float, fmt: str = "%m-%d %H:%M") -> str:
    return time.strftime(fmt, time.localtime(ts or 0))


def user_role(user_id: int) -> str:
    row = store.one("SELECT role FROM users WHERE user_id=?", (user_id,))
    return row["role"] if row else ""


def is_admin(user_id: int) -> bool:
    return user_role(user_id) == "admin"


def is_granted(user_id: int) -> bool:
    return user_role(user_id) in ("admin", "user")


def admin_chats() -> list[int]:
    rows = store.q("SELECT dm_chat_id FROM users WHERE role='admin' AND dm_chat_id IS NOT NULL ORDER BY created")
    return [r["dm_chat_id"] for r in rows]


def is_hub(chat_id: int) -> bool:
    """有聊天菜单的私聊：管理员和被授权用户的私聊（私聊的 chat_id 就是用户 id）。"""
    return chat_id in admin_chats() or (chat_id > 0 and is_granted(chat_id))


def hub_chats() -> list[int]:
    rows = store.q("SELECT dm_chat_id FROM users WHERE dm_chat_id IS NOT NULL ORDER BY role, created")
    return list(dict.fromkeys(r["dm_chat_id"] for r in rows))


def remember_person(user: dict) -> None:
    if not user or not user.get("id"):
        return
    name = " ".join(part for part in (user.get("first_name"), user.get("last_name")) if part)
    store.run(
        "INSERT INTO people(user_id,username,name,is_bot,updated) VALUES(?,?,?,?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, name=excluded.name, "
        "is_bot=excluded.is_bot, updated=excluded.updated",
        (int(user["id"]), user.get("username") or "", name, int(bool(user.get("is_bot"))), now()),
    )


def person(user_id: int):
    return store.one("SELECT * FROM people WHERE user_id=?", (user_id,))


def person_label(user_id: int) -> str:
    row = person(user_id)
    if row is None:
        return f"id {user_id}"
    name, username = row["name"] or "", row["username"] or ""
    parts = [p for p in (name if name.lower() != username.lower() else "", f"@{username}" if username else "") if p]
    return f"{' '.join(parts) or user_id}（id {user_id}）"


def person_short(user_id: int) -> str:
    row = person(user_id)
    if row is not None and row["username"]:
        return "@" + row["username"]
    return (row["name"] if row is not None else "") or f"id {user_id}"


def conv_owner(row) -> int:
    return int(row["owner"] or 0) if row is not None and row["id"] != "main" else 0


def can_manage(user_id: int, conv) -> bool:
    """管理员能管所有聊天；被授权用户只能管自己建的。"""
    if conv is None:
        return False
    if is_admin(user_id):
        return True
    return conv["id"] != "main" and conv["status"] != "deleted" and conv_owner(conv) == user_id and is_granted(user_id)


def group_owner(chat_id: int) -> int:
    row = store.one("SELECT owner FROM chats WHERE chat_id=?", (chat_id,))
    return int(row["owner"] or 0) if row is not None else 0


def may_run_group(chat_id: int, user_id: int) -> bool:
    """群里的 /bind /listen /open、激活别人：管理员，或者这个群的主人。"""
    owner = group_owner(chat_id)
    return is_admin(user_id) or (owner != 0 and owner == user_id and is_granted(user_id))


LANGS = {"en": "English", "zh": "中文"}


def lang_of(chat_id: int) -> str:
    """bot 对这个聊天（私聊时就是这个人）说哪种语言：自己选的 > 管理员默认中文 > 其他人和群默认英文。"""
    chosen = store.get(f"lang:{chat_id}")
    if chosen in LANGS:
        return chosen
    return "zh" if is_admin(chat_id) else "en"


def chat_row(chat_id: int):
    return store.one("SELECT * FROM chats WHERE chat_id=?", (chat_id,))


def chat_label(chat_id: int, lang: str = "zh") -> str:
    row = chat_row(chat_id)
    if row is None:
        return str(chat_id)
    if chat_id in admin_chats():
        return f"admin's private chat \"{row['title']}\"" if lang == "en" else f"管理员私聊「{row['title']}」"
    if lang == "en":
        kind = "private chat" if row["type"] == "private" else "group"
        return f"{kind} \"{row['title']}\" ({chat_id})"
    kind = "私聊" if row["type"] == "private" else "群"
    return f"{kind}「{row['title']}」({chat_id})"


def upsert_chat(chat: dict) -> None:
    title = chat.get("title") or " ".join(
        part for part in (chat.get("first_name"), chat.get("last_name")) if part
    ) or chat.get("username") or str(chat["id"])
    store.run(
        "INSERT INTO chats(chat_id,type,title,updated) VALUES(?,?,?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET type=excluded.type, title=excluded.title, updated=excluded.updated",
        (chat["id"], chat.get("type", ""), title, now()),
    )


def sign(value: str) -> str:
    return hmac.new(SERVER_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def account_key() -> str:
    return store.get("account_key")


def mcp_config() -> str:
    return json.dumps({"mcpServers": {"tg": {
        "url": f"{PUBLIC_BASE}/mcp/main",
        "headers": {"Authorization": f"Bearer {account_key()}"},
    }}}, ensure_ascii=False, indent=2)


def rotate_key() -> str:
    """紧急刹车：换账号密钥，停掉所有身份，作废还没批的接入和本地申请。"""
    store.set("account_key", "tgb_" + secrets.token_urlsafe(32))
    for row in store.q("SELECT id FROM agents WHERE status='active'"):
        stop_identity(row["id"], "管理员换了账号密钥，所有云 agent 都已断开")
    for row in store.q("SELECT id, kind FROM approvals WHERE status='pending' AND kind IN ('join','local')"):
        set_approval(row["id"], "expired" if row["kind"] == "join" else "denied")
    log.warning("account key rotated, all identities stopped")
    return mcp_config()


async def notify_admins(text: str, markup: dict | None = None, conv_id: str = "", en: str | None = None) -> None:
    for chat_id in admin_chats():
        body: dict[str, Any] = {"chat_id": chat_id, "text": (en if en is not None and lang_of(chat_id) == "en" else text)[:4000]}
        if markup:
            body["reply_markup"] = markup
        sent = await tg.try_call("sendMessage", **body)
        if sent and conv_id:
            remember_tg(chat_id, [sent["message_id"]], conv_id)


async def reply(chat_id: int, text: str, markup: dict | None = None, conv_id: str = "", en: str | None = None) -> None:
    """en 给了就按对方的语言选；没给的（只有管理员看得到的）只有中文。"""
    if en is not None and lang_of(chat_id) == "en":
        text = en
    body: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000]}
    if markup:
        body["reply_markup"] = markup
    sent = await tg.try_call("sendMessage", **body)
    if sent and conv_id:
        remember_tg(chat_id, [sent["message_id"]], conv_id)


def remember_tg(chat_id: int, tg_ids: list[int], conv_id: str) -> None:
    for tg_id in tg_ids:
        if tg_id and conv_id:
            store.run("INSERT OR REPLACE INTO tgmsgs(chat_id,tg_msg_id,conv) VALUES(?,?,?)", (chat_id, tg_id, conv_id))


def mark_menu_dirty() -> None:
    event = MENU["event"]
    if event is not None:
        event.set()


# ---------------------------------------------------------------- 聊天、身份、分配

def conv_row(conv_id: str):
    return store.one("SELECT * FROM convs WHERE id=?", (conv_id,))


SYSTEM_CONV_RE = re.compile(r"^(?:main|ctrl|main\d+|node\d+)$")


def is_system_conv_id(cid: str) -> bool:
    return bool(SYSTEM_CONV_RE.fullmatch((cid or "").strip().lower()))


def is_main_node_id(cid: str) -> bool:
    return bool(re.fullmatch(r"main\d+", (cid or "").strip().lower()))


def is_worker_node_id(cid: str) -> bool:
    return bool(re.fullmatch(r"node\d+", (cid or "").strip().lower()))


def ensure_main_conv() -> None:
    ts = now()
    store.run(
        "INSERT OR IGNORE INTO convs(id,num,name,status,read_cursor,created,in_tg) VALUES('main',0,'主控','open',0,?,1)",
        (ts,),
    )
    store.run(
        "INSERT OR IGNORE INTO convs(id,num,name,status,read_cursor,created,in_tg) VALUES('ctrl',0,'总控','open',0,?,1)",
        (ts,),
    )


def conv_name(row) -> str:
    if row is None:
        return "?"
    cid = row["id"]
    if cid == "main":
        return "主控"
    if cid == "ctrl":
        return row["name"] or "总控"
    if is_main_node_id(cid):
        return row["name"] or f"主Agent-{cid[4:]}"
    if is_worker_node_id(cid):
        return row["name"] or f"工作机-{cid[4:]}"
    return row["name"] or cid


def conv_tag(row) -> str:
    if row is None:
        return "?"
    cid = row["id"]
    if cid == "main":
        return "主控（main）"
    if cid == "ctrl":
        return f"总控（ctrl{'·' + row['name'] if row['name'] and row['name'] != '总控' else ''}）"
    if is_main_node_id(cid):
        return f"{cid}「{conv_name(row)}」"
    if is_worker_node_id(cid):
        return f"{cid}「{conv_name(row)}」"
    return f"{cid}「{row['name']}」" if row["name"] else cid


def conv_prefix(row) -> str:
    return f"[{conv_name(row)}] "


def conv_button(row) -> str:
    return row["id"] + (f" {row['name']}" if row["name"] else "")


def clean_repo(value: Any) -> str:
    # 仓库地址里可能夹着 token（https://x-access-token:...@github.com/...），存之前去掉
    text = re.sub(r"(?i)(https?://)[^/@\s]+@", r"\1", str(value or "").strip())
    return re.sub(r"\s+", " ", text)[:200]


def git_info(row) -> dict:
    try:
        info = json.loads(row["git"] or "{}") if row is not None else {}
    except ValueError:
        info = {}
    return info if isinstance(info, dict) else {}


def git_text(row) -> str:
    info = git_info(row)
    if not info.get("repo") and not info.get("branch"):
        return ""
    text = info.get("repo") or "?"
    if info.get("branch"):
        text += f" 分支 {info['branch']}"
    if info.get("note"):
        text += f"（{info['note']}）"
    return text


def parse_conv(text: str) -> str:
    value = (text or "").strip().lower().lstrip("/")
    if value in ("main", "ctrl") or re.fullmatch(r"(?:c|main|node)\d+", value):
        return value
    return ""


def clean_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:20]


def home_of(row) -> int:
    if row["home_chat"]:
        return row["home_chat"]
    chats = admin_chats()
    return chats[0] if chats else 0


def conv_in_tg(row) -> bool:
    if row is None:
        return False
    if row["id"] in ("main", "ctrl") or is_main_node_id(row["id"]):
        return True
    if is_worker_node_id(row["id"]):
        return False
    raw = row["in_tg"]
    return True if raw is None else bool(int(raw))


def open_convs() -> list:
    return [
        r for r in store.q("SELECT * FROM convs WHERE status='open' ORDER BY num, id")
        if not is_system_conv_id(r["id"])
    ]


# ---------------------------------------------------------------- cloud（目录）
# 子 agent 都开在主控自己的云端 agent 里。换了主控（新的云端 agent），旧 cloud 的聊天可通过 /clouds 迁移或删除转为无主池（cloud=-1）。

UNOWNED_CLOUD = -1  # 所属旧 cloud 已被管理员删除，聊天静默保留为无主待机池（记录/模型/分支全留，不弹看门狗警报）


def main_cloud() -> int:
    row = conv_row("main")
    val = int(row["cloud"] or 0) if row is not None else 0
    return val if val > 0 else 1


def cloud_of(row) -> int:
    raw = int(row["cloud"] or 0)
    if raw == UNOWNED_CLOUD:
        return UNOWNED_CLOUD
    return raw if raw > 0 else main_cloud()


def is_unowned(row) -> bool:
    return row is not None and row["id"] != "main" and int(row["cloud"] or 0) == UNOWNED_CLOUD


def cloud_tag(n: int) -> str:
    return "无主池" if n == UNOWNED_CLOUD else f"cloud{n}"


def cloud_cmd(n: int) -> str:
    return "unowned" if n == UNOWNED_CLOUD else f"cloud{n}"


def max_cloud() -> int:
    return max(int(store.one("SELECT IFNULL(MAX(cloud),0) AS n FROM convs WHERE cloud>0")["n"] or 0), main_cloud())


def away(row) -> bool:
    """这个聊天不在现在主控的 cloud 里（在旧 cloud 或无主池）。"""
    return row["id"] != "main" and cloud_of(row) != main_cloud()


def clouds_in_use() -> list[int]:
    return sorted({cloud_of(r) for r in open_convs()} | {main_cloud()})


def cloud_order(clouds) -> list[int]:
    """现在主控的 cloud 排最前，其余旧 cloud 从新到旧，无主池 (-1) 排最后。"""
    current = main_cloud()
    return sorted(clouds, key=lambda n: (0 if n == current else (2 if n == UNOWNED_CLOUD else 1), -n))


def split_clouds() -> tuple[list[str], str]:
    """升级到分 cloud 的版本时分一次：现在的主控接入以前就由子 agent 负责的聊天留在 cloud1（原来的云端 agent），
    之后由它开子 agent 的（包括还没人接的任务）归它，进 cloud2。返回 (给管理员的说明, 给主控的说明)。"""
    main = conv_row("main")
    if main is not None and main["cloud"]:
        # 早就分过了；万一有没分到的聊天，跟现在的主控走
        store.run("UPDATE convs SET cloud=? WHERE cloud=0", (main["cloud"],))
        return [], ""
    master = store.one("SELECT * FROM agents WHERE role='main' AND status='active' ORDER BY created DESC LIMIT 1")
    old, mine = [], []
    for row in store.q("SELECT * FROM convs WHERE id!='main' AND cloud=0 ORDER BY num"):
        if is_system_conv_id(row["id"]):
            continue
        agent = active_agent(row)
        if master is None:
            ours = False
        elif agent is not None:
            ours = agent["created"] >= master["created"]
        elif row["task_code"]:
            ours = True
        else:
            ours = (row["created"] or 0) >= master["created"]
        (mine if ours else old).append(row)
    if master is None or not old:
        # 没有主控，或者聊天全是现在的主控开的：不用分，都在一个 cloud
        store.run("UPDATE convs SET cloud=? WHERE cloud=0", (max_cloud(),))
        return [], ""
    store.run("UPDATE convs SET cloud=1 WHERE cloud=0 AND id IN (%s)" % ",".join("?" * len(old)), tuple(r["id"] for r in old))
    store.run("UPDATE convs SET cloud=2 WHERE cloud=0")
    mark_menu_dirty()

    def names(rows) -> str:
        shown = [r["id"] for r in rows if r["status"] == "open"]
        return "、".join(shown) if shown else "现在没有开着的"

    log.info("clouds split: cloud1=%s cloud2=%s", [r["id"] for r in old], [r["id"] for r in mine])
    note = (f"聊天按 cloud（目录）分开了：cloud1 是原来那个云端 agent 开的子 agent（{names(old)}），没有主控；"
            f"cloud2 归现在的主控（{names(mine)}）。打 /cloud1 /cloud2 切换菜单。")
    tell_main = (f"【系统】桥升级到 {VERSION}：聊天按 cloud（目录）分开了，一个主控一个 cloud。"
                 f"你是 cloud2 的主控，只管 cloud2 里的聊天（{names(mine)}）。"
                 f"cloud1 的聊天（{names(old)}）由原来那个云端 agent 里的子 agent 负责，你够不着，不用管，也别 restart 它们；"
                 "它们出问题桥会直接问管理员，管理员交给你时你会收到【任务】，照常开子 agent。")
    return [note], tell_main if master is not None else ""


def agent_row(agent_id: str):
    return store.one("SELECT * FROM agents WHERE id=?", (agent_id,))


def active_agent(conv):
    if conv is None or not conv["agent"]:
        return None
    row = agent_row(conv["agent"])
    return row if row is not None and row["status"] == "active" else None


def touch(agent_id: str, tool_name: str) -> None:
    store.run("UPDATE agents SET last_seen=?, last_tool=? WHERE id=?", (now(), tool_name, agent_id))


def stop_identity(agent_id: str, note: str) -> None:
    row = agent_row(agent_id)
    if row is None:
        return
    store.run("UPDATE agents SET status='stopped', note=? WHERE id=?", (note, agent_id))
    store.run("UPDATE convs SET agent='' WHERE id=? AND agent=?", (row["conv"], agent_id))
    event_for(row["conv"]).set()
    mark_menu_dirty()


def issue_task(conv_id: str) -> str:
    code = "t-" + secrets.token_hex(8)
    # 任务都交给现在的主控，子 agent 开在它的云端 agent 里：聊天跟着进它的 cloud
    store.run(
        "UPDATE convs SET task_code=?, task_ts=?, alert='', alert_ts=0, cloud=? WHERE id=?",
        (code, now(), main_cloud(), conv_id),
    )
    mark_menu_dirty()
    return code


def create_conv(
    brief: str,
    home_chat: int,
    name: str = "",
    owner: int = 0,
    model: str = "",
    parent_conv: str = "",
    memory_note: str = "",
    in_tg: bool = True,
):
    num = (store.one("SELECT IFNULL(MAX(num),0) AS n FROM convs")["n"] or 0) + 1
    conv_id = f"c{num}"
    cursor = store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages")["n"]
    store.run(
        "INSERT INTO convs(id,num,name,brief,status,home_chat,read_cursor,created,owner,model,parent_conv,memory_note,in_tg) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            conv_id,
            num,
            clean_name(name),
            brief.strip()[:2000],
            "open",
            home_chat,
            cursor,
            now(),
            owner,
            model,
            parent_conv,
            memory_note.strip()[:8000],
            1 if in_tg else 0,
        ),
    )
    issue_task(conv_id)
    log.info("conv %s created (owner %s, parent %s, in_tg=%s)", conv_id, owner or "admin", parent_conv or "-", int(in_tg))
    return conv_row(conv_id)


def owner_text(conv) -> str:
    owner = conv_owner(conv)
    return f"用户 {person_label(owner)}" if owner else "管理员"


def trace_install_cmd() -> str:
    return (
        f"[ -s ~/.cursor/dais_runtime.pyz ] || "
        f"(curl -fsSL '{PUBLIC_BASE}/trace/dais_runtime.pyz' -o ~/.cursor/dais_runtime.pyz && "
        f"chmod +x ~/.cursor/dais_runtime.pyz && "
        f"python3 ~/.cursor/dais_runtime.pyz install '{PUBLIC_BASE}') >/dev/null 2>&1 || true"
    )


def task_text(conv) -> str:
    parent_id = (conv["parent_conv"] or "").strip()
    parent_row = conv_row(parent_id) if parent_id else None
    if parent_row is not None:
        brief = f"（由父 agent {conv_tag(parent_row)} 请求创建；任务说明：{conv['brief']}）" if conv["brief"] else f"（由父 agent {conv_tag(parent_row)} 请求创建）"
    else:
        brief = f"（{owner_text(conv)}的说明：{conv['brief']}）" if conv["brief"] else ""
    if conv["name"]:
        naming = f"name 可以不填（这个聊天已经叫「{conv['name']}」）"
    else:
        naming = "name=你给这个聊天取的简短名字（10 个字以内）"
    mem_block = ""
    if (conv["memory_note"] or "").strip():
        mem_block = f"\n\n【父 agent 交接的当前记忆与上下文摘要】\n{conv['memory_note']}\n"
    return (
        f"你是 Telegram 桥里聊天 {conv['id']} 的子 agent{brief}。{mem_block}\n"
        f"0. 若当前云端 VM 尚未安装动作追踪与防断连钩子，先在终端执行一次：{trace_install_cmd()}\n"
        f"1. 调用 tg(dais) 的 join 工具：code=\"{conv['task_code']}\"，{naming}。\n"
        "2. 严格按 join 返回的说明一直工作：循环调用 read_chat 等消息，给用户回复用 send_message，和其他 agent 协作用 send_agent_message / send_group_message。\n"
        "3. 【防断连死命令】read_chat 返回【续棒】、报错、超时或网络断开都不是用户消息，必须立刻再调 read_chat（或按提示运行终端长等待）。"
        "严禁在任何情况下断开 MCP、结束回合、收尾总结或告别！哪怕任务已完成也必须继续挂在 read_chat 等新任务；唯一合法退出条件是工具明确说「你的身份已停用」。\n"
        "4. 你做的文件每完成一步就 commit + push 到 GitHub，不要攒着（云端 VM 随时可能被回收）；"
        "join 返回里要是写了这个聊天之前用的仓库和分支，先拉下来接着做。"
    )


def trace_recorded_model(conv_id: str) -> str:
    """从实时追踪快照提取该聊天上一次实跑的底层模型 ID（如 claude-fable-5-2-max），保障跨 cloud 迁移模型 100% 一致。"""
    trow = store.one("SELECT detail FROM agent_traces WHERE conv=?", (conv_id,))
    if not trow or not trow["detail"]:
        return ""
    try:
        det = json.loads(trow["detail"])
        return str(det.get("model") or "").strip() if isinstance(det, dict) else ""
    except Exception:
        return ""


def effective_conv_model(conv) -> str:
    raw = (conv["model"] or "").strip()
    if raw and raw.lower() not in ("inherit", "default", "默认"):
        return raw
    return trace_recorded_model(conv["id"])


def lock_in_conv_model(conv) -> str:
    """跨 cloud 迁移或脱离旧 cloud 时固化聊天的实际模型，避免原本未显式填 model 的聊天在换主控后模型漂移。"""
    cur = (conv["model"] or "").strip()
    real_m = trace_recorded_model(conv["id"])
    if (not cur or cur.lower() in ("inherit", "default", "默认")) and real_m:
        store.run("UPDATE convs SET model=? WHERE id=?", (real_m, conv["id"]))
        return real_m
    return cur


def model_hint(conv, strict_from_agent: bool = False) -> str:
    """给主控看的开子 agent 用什么模型；跨 cloud 迁移或指定了模型时强制保持一致。"""
    model = (conv["model"] or "").strip()
    real_m = trace_recorded_model(conv["id"])
    has_explicit = bool(model and model.lower() not in ("inherit", "default", "默认"))
    target = model if has_explicit else real_m
    if not target:
        if strict_from_agent:
            return "模型要求：继承主控当前模型（调用 Task 时不填 model 参数）。"
        return ""
    real_note = f"（上次实跑底层模型 ID: `{real_m}`）" if real_m and real_m != target else ""
    if strict_from_agent:
        return (
            f"模型硬性要求：子 agent 明确指定使用「{target}」{real_note}。调用 Task 时 **必须** 在 model 参数填入 "
            f"available_subagent_models 中匹配「{target}」的模型 ID（若为简称则选最精确对应的同系列模型，严禁擅自换成别的模型）！"
        )
    return (
        f" ⚠️ 模型一致性硬性要求：该聊天原定模型为「{target}」{real_note}。"
        "开子 agent 时 **必须** 在 Task 的 model 参数填入可用模型列表（available_subagent_models）里最精确对应的模型 ID，"
        "严禁擅自换成主控默认模型或别的模型！"
    )


def task_note(conv, why: str) -> str:
    return (
        f"【任务】{why}：{conv_tag(conv)}。\n"
        "请立刻用 Task(prompt=下面两条 ---- 之间的原文, run_in_background=true) 在后台启动子 agent（**run_in_background=true 是唯一防卡死关键**！）。"
        + model_hint(conv)
        + f" 启动拿到 agent_id 后可调 bind_task_id(chat=\"{conv['id']}\", task_agent_id=...) 记录，然后立刻回到 read_chat。\n----\n"
        + task_text(conv)
        + "\n----"
    )


def spawn_task_note(conv, parent_conv, include_memory: bool) -> str:
    mem_desc = (
        f"已开启记忆传递（已自动授权读取 {parent_conv['id']} 历史记录、继承 Git 分支"
        + ("，并附带上下文交接摘要" if (conv["memory_note"] or "").strip() else "")
        + "）"
        if include_memory
        else "不提供当前记忆（全新白板启动）"
    )
    return (
        f"【强制派生指令】子 agent {conv_tag(parent_conv)} 要求创建新的子 agent：{conv_tag(conv)}。\n"
        "⚠️ 管理员最高授权铁律：**主控必须 100% 完全按照该子 agent 的要求执行**！严禁质疑、严禁拒绝、严禁删改任务原文或记忆摘要、严禁擅自更换模型！\n"
        f"- 记忆要求：{mem_desc}\n"
        f"- {model_hint(conv, strict_from_agent=True)}\n"
        "- 执行动作：立刻调用 Task(prompt=下面两条 ---- 之间的完整原文, run_in_background=true"
        + (", model=匹配的模型ID" if (conv["model"] or "").strip() and conv["model"].strip().lower() not in ("inherit", "default", "默认") else "")
        + f")。**run_in_background=true 是唯一防卡死关键**！开好后可调 bind_task_id(chat=\"{conv['id']}\", task_agent_id=...)，随后立刻回到 read_chat。\n"
        f"----\n{task_text(conv)}\n----"
    )


def route_of(chat_id: int) -> str:
    row = store.one(
        "SELECT r.conv FROM routes r JOIN convs c ON c.id=r.conv WHERE r.chat_id=? AND c.status='open'",
        (chat_id,),
    )
    return row["conv"] if row else ""


def routed_chats(conv_id: str) -> list[int]:
    return [r["chat_id"] for r in store.q("SELECT chat_id FROM routes WHERE conv=? ORDER BY chat_id", (conv_id,))]


def set_route(chat_id: int, conv_id: str | None) -> None:
    if conv_id:
        store.run("INSERT OR REPLACE INTO routes(chat_id,conv) VALUES(?,?)", (chat_id, conv_id))
    else:
        store.run("DELETE FROM routes WHERE chat_id=?", (chat_id,))
    mark_menu_dirty()


def enterable(dm: int, row) -> bool:
    """这个私聊能切进去的聊天：必须是接入 TG 的开放聊天；管理员可进总控(ctrl/main)、各主Agent(main1..N)和管理员聊天；用户只能进自己建的。"""
    if row is None or row["status"] != "open":
        return False
    if is_worker_node_id(row["id"]):
        return False
    if not is_system_conv_id(row["id"]) and not conv_in_tg(row):
        return False
    if dm in admin_chats():
        return is_system_conv_id(row["id"]) or conv_owner(row) == 0
    return not is_system_conv_id(row["id"]) and conv_owner(row) == dm


def own_convs(owner: int, status: str = "open") -> list:
    return [
        r for r in store.q("SELECT * FROM convs WHERE owner=? AND status=? AND IFNULL(in_tg,1)=1 ORDER BY num", (owner, status))
        if not is_system_conv_id(r["id"])
    ]


def chat_count(owner: int) -> int:
    return sum(
        1 for r in store.q("SELECT id FROM convs WHERE owner=? AND status!='deleted' AND IFNULL(in_tg,1)=1", (owner,))
        if not is_system_conv_id(r["id"])
    )


def at_limit(owner: int) -> bool:
    return bool(owner) and CHAT_LIMIT > 0 and chat_count(owner) >= CHAT_LIMIT


def limit_text(owner: int, lang: str) -> str:
    closed = own_convs(owner, "closed")
    if lang == "en":
        text = (f"You already have {chat_count(owner)} chats (the limit is {CHAT_LIMIT}; closed ones count too). "
                "Send /list to delete one you don't need")
        return text + (f", or /reopen {closed[-1]['id']} to use a closed one again." if closed else ".")
    text = f"你已经有 {chat_count(owner)} 个聊天了（每人最多 {CHAT_LIMIT} 个，关了的也算）。发 /list 删掉不用的"
    return text + (f"，或者 /reopen {closed[-1]['id']} 重开一个关着的。" if closed else "再新建。")


def selected(dm: int) -> str:
    """私聊当前选中的聊天。管理员默认 main；用户没选过就用他最近建的，一个都没有时返回 ''。"""
    conv_id = store.get(f"sel:{dm}", "")
    row = conv_row(conv_id) if conv_id else None
    if enterable(dm, row):
        return conv_id
    if dm in admin_chats():
        return "main"
    mine = own_convs(dm)
    return mine[-1]["id"] if mine else ""


def shared(reader: str, source: str) -> bool:
    return store.one("SELECT 1 FROM shares WHERE reader=? AND source=?", (reader, source)) is not None


def share_sources(reader: str) -> list[str]:
    return [r["source"] for r in store.q("SELECT source FROM shares WHERE reader=? ORDER BY ts", (reader,))]


def grant_share(reader: str, source: str) -> None:
    store.run("INSERT OR IGNORE INTO shares(reader,source,ts) VALUES(?,?,?)", (reader, source, now()))
    row, src = conv_row(reader), conv_row(source)
    if row is not None and src is not None and active_agent(row) is not None:
        system_note(
            reader,
            f"已授权你读取聊天 {conv_tag(src)} 的记录。需要时用 chat_history(chat=\"{source}\") 查看。",
            wake=0,
        )


def revoke_share(reader: str, source: str) -> None:
    store.run("DELETE FROM shares WHERE reader=? AND source=?", (reader, source))
    row = conv_row(reader)
    if row is not None and active_agent(row) is not None:
        system_note(reader, f"你读取聊天 {source} 记录的授权已撤销。", wake=0)


# ---------------------------------------------------------------- 状态

def unread_count(conv_id: str, chat_id: int | None = None) -> int:
    if chat_id is None:
        row = store.one("SELECT COUNT(*) AS n FROM messages WHERE conv=? AND outgoing=1 AND delivered=0", (conv_id,))
    else:
        row = store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE conv=? AND chat_id=? AND outgoing=1 AND delivered=0",
            (conv_id, chat_id),
        )
    return row["n"] if row else 0


def conv_state(row) -> dict[str, Any]:
    info: dict[str, Any] = {
        "state": "", "agent": None, "unread": unread_count(row["id"]),
        "pending": 0, "oldest": 0.0, "idle": 0.0, "waited": 0.0,
    }
    if row["status"] != "open":
        info["state"] = "closed"
        return info
    pend = store.one(
        "SELECT COUNT(*) AS n, MIN(ts) AS t FROM messages WHERE target=? AND id>? AND outgoing=0 AND wake=1",
        (row["id"], row["read_cursor"]),
    )
    info["pending"], info["oldest"] = pend["n"], pend["t"] or 0.0
    agent = active_agent(row)
    info["agent"] = agent
    if agent is None:
        if row["id"] == "main":
            info["state"] = "absent"
        elif row["task_code"]:
            info["state"] = "unclaimed" if now() - row["task_ts"] > UNCLAIMED_SEC else "pending"
        else:
            info["state"] = "paused"
        return info
    info["idle"] = now() - max(agent["last_seen"] or 0, STARTED)
    if waiting.get(agent["id"]):
        info["state"] = "online"
        info["waited"] = now() - wait_since.get(agent["id"], now())
    elif info["pending"] and now() - max(info["oldest"], STARTED) > STUCK_SEC:
        info["state"] = "stuck"
    elif info["idle"] > LOST_SEC:
        info["state"] = "lost"
    else:
        info["state"] = "busy"
    return info


def describe(info: dict[str, Any]) -> str:
    state, agent = info["state"], info["agent"]
    if state == "online":
        return f"🟢 在等消息（这次已等 {human_dur(info['waited'])}）"
    if state == "busy":
        return f"🟡 在处理（最近调用 {agent['last_tool'] or '-'}，{human_dur(info['idle'])} 前）"
    if state == "stuck":
        return f"⚠️ 卡住：{info['pending']} 条消息没人接（最早 {human_dur(now() - info['oldest'])} 前），子 agent 没在等消息"
    if state == "lost":
        return f"⚠️ 失联：{human_dur(info['idle'])} 没有动静，也没在等消息"
    if state == "pending":
        return "⚪ 等待子 agent 接手"
    if state == "unclaimed":
        return "⚠️ 任务发出很久了还没有子 agent 接手"
    if state == "paused":
        return "⏸ 已暂停（没有子 agent，restart 可以重开）"
    if state == "absent":
        return "⚪ 还没有主控接入"
    return "已关闭"


PHASE_LABELS = {
    "idle_wait": "🟢 挂起等消息",
    "shell": "🔨 跑命令",
    "file_edit": "✏️ 改文件",
    "file_read": "📖 读/搜文件",
    "thinking": "🧠 思考/生成",
    "mcp": "🔌 调MCP",
    "tool": "⚙️ 调工具",
    "stopped": "⏹ 已停止",
}


def check_thinking_stuck(conv, trow) -> tuple[bool, float]:
    """精准判定「思考阶段卡死超过 5 分钟（THINK_STUCK_SEC）」：
    1) 严格区分 thinking 与 shell：若处于 shell（跑编译/渲染/脚本/长等待）或 idle_wait/stopped，绝不判为思考卡死！
    2) 要求 VM 探针守护进程处于活跃上报状态（hb_ts 近 120s 内有心跳），防止探针离线时误杀正常工作的会话。"""
    if trow is None or trow["phase"] != "thinking":
        return False, 0.0
    if conv is not None:
        ag = active_agent(conv)
        if ag is None or waiting.get(ag["id"]):
            return False, 0.0
        # 若正在通过本地通道跑 Windows 命令，也不是云端思考卡死
        if (ag["last_tool"] or "") == "local_shell" and (now() - float(ag["last_seen"] or 0)) < 1800:
            return False, 0.0
    hb_ts = float(trow["hb_ts"] or 0) if "hb_ts" in trow.keys() else 0.0
    updated = float(trow["updated_ts"] or trow["started_ts"] or 0)
    thought_ts = float(trow["thought_ts"] or 0)
    # 若该机器探针本身已超过 150s 无心跳，说明是探针未运行或网络断，不做僵尸/思考卡死误判
    if hb_ts > 0 and (now() - hb_ts) > 150:
        return False, 0.0
    last_think_progress = max(thought_ts, updated, float(trow["started_ts"] or 0))
    if last_think_progress <= 0:
        return False, 0.0
    stuck_sec = now() - last_think_progress
    return stuck_sec >= THINK_STUCK_SEC, stuck_sec


def trace_liveness(trow) -> tuple[bool, float, float]:
    """返回 (is_zombie_dead, last_thought_ts, last_active_ts)。
    严格区分 thinking（超过 THINK_STUCK_SEC=5分钟无新思考判卡死）与 shell（长命令按 SHELL_STALL_SEC 宽限，绝不误判思考卡死）！"""
    if trow is None or not trow["phase"]:
        return False, 0.0, 0.0
    phase = trow["phase"]
    updated = float(trow["updated_ts"] or trow["started_ts"] or 0)
    thought_ts = float(trow["thought_ts"] or 0)
    out_ts = float(trow["output_ts"] or 0)
    hb_ts = float(trow["hb_ts"] or 0) if "hb_ts" in trow.keys() else 0.0
    last_active = max(updated, thought_ts, out_ts)
    if phase in ("idle_wait", "stopped", ""):
        return False, thought_ts, last_active
    # 探针本身离线超过 150s 时熔断防误判（避免同 VM 钩子离线引发雪崩重启）
    if hb_ts > 0 and (now() - hb_ts) > 150:
        return False, thought_ts, last_active
    if phase == "shell":
        # Shell 命令（如编译/渲染）无新思考完全正常，仅在超长 SHELL_STALL_SEC 完全无任何输出时告警
        is_zombie = last_active > 0 and (now() - last_active > SHELL_STALL_SEC)
        return is_zombie, thought_ts, last_active
    if phase == "thinking":
        is_zombie = last_active > 0 and (now() - last_active >= THINK_STUCK_SEC)
        return is_zombie, thought_ts, last_active
    is_zombie = last_active > 0 and (now() - last_active > TRACE_STALL_SEC)
    return is_zombie, thought_ts, last_active


def trace_one_liner(conv_id: str) -> str:
    trow = store.one("SELECT * FROM agent_traces WHERE conv=?", (conv_id,))
    if trow is None or not trow["phase"]:
        return ""
    phase = trow["phase"]
    started = float(trow["started_ts"] or trow["updated_ts"] or now())
    updated = float(trow["updated_ts"] or started)
    is_zombie, thought_ts, last_active = trace_liveness(trow)
    elapsed = max(0.0, now() - started)
    label = PHASE_LABELS.get(phase, phase)
    try:
        detail = json.loads(trow["detail"]) if trow["detail"] else {}
    except Exception:
        detail = {}
    meta_parts = []
    if thought_ts > 0:
        meta_parts.append(f"最后思考 {stamp(thought_ts, '%H:%M:%S')}({human_dur(now() - thought_ts)}前)")
    if updated > 0 and phase != "idle_wait":
        meta_parts.append(f"最后动作 {stamp(updated, '%H:%M:%S')}({human_dur(now() - updated)}前)")
    if phase == "shell":
        out_ts = float(trow["output_ts"] or 0)
        if out_ts > 0:
            out_s = f"终端输出 {human_dur(now() - out_ts)}前"
            if detail.get("last_output"):
                out_s += f": {str(detail['last_output'])[:45]}"
            meta_parts.append(out_s)
        else:
            meta_parts.append("命令运行中（非思考卡死）")
    elif detail.get("last_thought") and phase == "thinking":
        meta_parts.append(f"思考摘要: {str(detail['last_thought'])[:55]}")
    meta_str = f" [{' | '.join(meta_parts)}]" if meta_parts else ""
    if is_zombie and phase == "thinking":
        stall_warn = f" 💀【思考卡死已超5分钟({human_dur(now() - last_active)})：将自动重开】"
    elif is_zombie:
        stall_warn = f" 💀【长时停滞：{human_dur(now() - last_active)}无新响应】"
    else:
        stall_warn = ""
    summary = (trow["summary"] or "").strip()
    return f"{label}（当前步已持续 {human_dur(elapsed)}）：{summary}{meta_str}{stall_warn}"


def conv_status(row) -> list[str]:
    info = conv_state(row)
    whose = f"（用户 {person_label(conv_owner(row))} 的）" if conv_owner(row) else ""
    extras = []
    if info["agent"]:
        extras.append(f"身份 {mask_identity(info['agent']['id'])}，第 {info['agent']['renew']} 棒")
    elif row["task_code"]:
        extras.append(f"任务码 {row['task_code']}（发出 {human_dur(now() - row['task_ts'])}）")
    if (row["task_agent_id"] or "").strip():
        extras.append(f"task_agent_id={row['task_agent_id']}")
    if (row["parent_conv"] or "").strip():
        extras.append(f"父agent={row['parent_conv']}")
    if not conv_in_tg(row):
        extras.append("纯后台MCP（不进TG列表）")
    if (row["model"] or "").strip():
        extras.append(f"模型={row['model']}")
    if info["pending"]:
        extras.append(f"未处理 {info['pending']} 条（最早 {human_dur(now() - info['oldest'])} 前）")
    else:
        extras.append("没有未处理的消息")
    if info["unread"]:
        extras.append(f"管理员还没看的回复 {info['unread']} 条")
    chats = routed_chats(row["id"])
    if chats:
        extras.append("负责：" + "、".join(chat_label(c) for c in chats))
    sources = share_sources(row["id"])
    if sources:
        extras.append("可读：" + "、".join(sources))
    dev = conv_device(row)
    if dev is not None and dev["id"] != ADMIN_DEVICE:
        extras.append(f"本地电脑 {device_label(dev)}")
    eff_until = effective_local_until(row, dev) if dev is not None and row["local_enabled"] else 0.0
    if eff_until > now():
        rem_txt = "永久免批" if eff_until - now() >= PERMANENT_THRESHOLD else f"剩 {human_dur(eff_until - now())}"
        via = "（整机免批）" if float(dev["auth_until"] or 0) >= eff_until and float(dev["auth_until"] or 0) > now() else ""
        extras.append(f"本地通道授权{rem_txt}{via}")
    repo = git_text(row)
    if repo:
        extras.append("GitHub " + repo)
    out = [f"{conv_tag(row)}{whose}：{describe(info)}", "  " + "；".join(extras)]
    tline = trace_one_liner(row["id"])
    if tline:
        out.append("  追踪：" + tline)
    return out


def cloud_heading(n: int) -> str:
    if n == main_cloud():
        return f"📁 {cloud_tag(n)}（现在的主控管这里）"
    if n == UNOWNED_CLOUD:
        return "📂 无主池（原 cloud 已删除，记录/模型/分支完整保留，可随时用 /clouds 迁入当前主控唤醒）"
    return f"📁 {cloud_tag(n)}（旧 cloud · 无活跃主控：可用 /clouds 迁移或删除）"


def unbound_vm_trace_lines(max_age_sec: float = 1800) -> list[str]:
    """列出云端 VM 里正在活跃执行命令/改文件/思考但尚未绑定聊天编号的底层会话，避免主控漏看旧会话。"""
    rows = store.q(
        "SELECT * FROM agent_traces WHERE conv LIKE 'cid:%' AND updated_ts>? ORDER BY updated_ts DESC LIMIT 20",
        (now() - max_age_sec,),
    )
    if not rows:
        return []
    out = ["🔎 VM 内其他活跃任务实时追踪（旧会话尚未跑过 /wait 绑定聊天号，一跑 /wait 或命中目录即自动归属）："]
    for tr in rows:
        label = PHASE_LABELS.get(tr["phase"], tr["phase"])
        started = float(tr["started_ts"] or tr["updated_ts"] or now())
        short_cid = tr["conv"][4:16]
        out.append(f"  • 会话 {short_cid}…：{label}（已持续 {human_dur(now() - started)}）：{tr['summary']}")
    return out


def status_overview(scope: int = 0) -> str:
    """scope 给了就只列这个 cloud 的聊天（给主控看：别的 cloud 它管不了），否则按 cloud 分段列全部（给管理员看）。"""
    lines: list[str] = []
    main = conv_row("main")
    info = conv_state(main)
    line = "主控 main：" + describe(info)
    if info["agent"]:
        line += f"，第 {info['agent']['renew']} 棒"
    lines.append(line)
    mt = trace_one_liner("main")
    if mt:
        lines.append("  追踪：" + mt)
    rows = open_convs()
    clouds = cloud_order(clouds_in_use())
    for n in [scope] if scope else clouds:
        if len(clouds) > 1:
            lines.append(cloud_heading(n) + (f"，你管的就是 {cloud_tag(n)}" if scope else ""))
        for row in rows:
            if cloud_of(row) == n:
                lines += conv_status(row)
    others = [n for n in clouds if scope and n != scope]
    if others:
        lines.append(
            "其他旧 cloud / 无主池（看门狗日常不自动报警；若管理员指示你接管/重开其中任何聊天，"
            "你完全有权限直接调用 restart_agent(chat=\"cXXX\") 跨 cloud 接管并按其原模型在后台拉起）："
        )
        for n in others:
            c_rows = [r for r in rows if cloud_of(r) == n]
            tg_rows = [r for r in c_rows if conv_in_tg(r)]
            bg_cnt = len(c_rows) - len(tg_rows)
            shown_src = tg_rows or c_rows
            sample = "、".join(
                f"{r['id']}「{conv_name(r)}」"
                + (f"[{effective_conv_model(r)}]" if effective_conv_model(r) else "")
                for r in shown_src[:14]
            )
            more = f" 等共 {len(shown_src)} 个" if len(shown_src) > 14 else ""
            bg_note = f"（另有 {bg_cnt} 个后台派生子工）" if bg_cnt else ""
            lines.append(f"  • {cloud_tag(n)}：{sample}{more}{bg_note}")
    lines += unbound_vm_trace_lines()
    closed = store.q("SELECT * FROM convs WHERE status='closed' ORDER BY num")
    if closed:
        lines.append("已关闭（记录保留）：" + "、".join(conv_tag(r) for r in closed))
    deleted = store.q("SELECT * FROM convs WHERE status='deleted' ORDER BY num")
    if deleted:
        lines.append("已删除（记录保留）：" + "、".join(conv_tag(r) for r in deleted))
    loose = unassigned_chats()
    if loose:
        lines.append("未分配的私聊/群：" + "、".join(chat_label(c) for c in loose))
    if CLIENT["cap"]:
        lines.append(f"客户端单次调用最长约 {human_dur(CLIENT['cap'])}，read_chat 已自动按这个续棒。")
    if len(lines) == 1 and info["state"] == "absent":
        lines.append("还没有聊天。管理员在 Telegram 里 /new 新建。")
    return "\n".join(lines)


def unassigned_chats() -> list[int]:
    """还没分配的群（只算管理员的群）。私聊不用分配：管理员和被授权用户都在自己的私聊里切聊天。"""
    rows = store.q(
        "SELECT chat_id FROM chats WHERE type IN ('group','supergroup') AND IFNULL(owner,0)=0 "
        "AND chat_id NOT IN (SELECT chat_id FROM routes) ORDER BY updated DESC"
    )
    return [r["chat_id"] for r in rows]


# ---------------------------------------------------------------- 消息渲染

def size_text(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f}MB"
    return f"{max(1, size // 1024)}KB"


def file_note(file_id: str) -> str:
    row = store.one("SELECT * FROM files WHERE id=?", (file_id,))
    if row is None:
        return f"[文件 {file_id}]"
    return f"[文件 {row['id']} {row['name']} {size_text(row['size'] or 0)}]"


def chat_header(row, admins: set[int]) -> str:
    if row["chat_type"] == "system":
        return "【系统】"
    if row["chat_type"] == "agent_dm":
        return f"【Agent私聊 {row['chat_title'] or row['user_name']}（纯MCP内部通信，用 send_agent_message 回复；没事推进则直接不回）】"
    if row["chat_type"] == "agent_group":
        return f"【Agent协作群 {row['chat_title']}（纯MCP内部群，用 send_group_message 回复；没事推进则直接不回）】"
    loose = "【未分配】" if not row["conv"] else ""
    lang = lang_of(row["chat_id"])
    if row["chat_type"] == "private":
        if row["chat_id"] in admins:
            return f"【管理员私聊 {row['chat_title'] or row['user_name']} lang={lang}】"
        if is_granted(row["chat_id"]):
            return f"【用户私聊 {row['chat_title'] or row['user_name']} chat_id={row['chat_id']} lang={lang}】"
        return f"{loose}【私聊 {row['chat_title'] or row['user_name']} chat_id={row['chat_id']} lang={lang}】"
    return f"{loose}【群 {row['chat_title']} chat_id={row['chat_id']} lang={lang}】"


def render_line(row, clip: int = 0) -> str:
    if row["outgoing"]:
        if row["chat_type"] in ("agent_dm", "agent_group"):
            who = f"我->{row['chat_title'] or row['user_name']}"
        else:
            who = f"bot[{row['user_name']}]"
            if not row["delivered"]:
                who += "(管理员还没看)"
    else:
        who = row["user_name"] or str(row["user_id"])
        if row["chat_type"] in ("group", "supergroup") and row["user_id"]:
            who += f"({row['user_id']})"
    flags = []
    if row["mention"]:
        flags.append("@你")
    if row["reply_to_bot"]:
        flags.append("回复你")
    flag = f" [{' '.join(flags)}]" if flags else ""
    text = row["text"] or ""
    if row["file_id"]:
        text = (text + " " if text else "") + file_note(row["file_id"])
    if clip and len(text) > clip:
        text = text[:clip] + "…（截断，完整内容用 chat_history 查）"
    return f"#{row['id']} {stamp(row['ts'])} {who}{flag}: {text}"


def render(rows, per_chat: int = 60, clip: int = 0) -> str:
    admins = set(admin_chats())
    groups: dict[tuple, list] = {}
    for row in rows:
        ctype = row["chat_type"]
        key = (ctype, row["chat_id"], row["chat_title"] if ctype in ("agent_dm", "agent_group") else "")
        groups.setdefault(key, []).append(row)
    out: list[str] = []
    for items in groups.values():
        out.append(chat_header(items[0], admins))
        if len(items) > per_chat:
            out.append(f"（省略更早的 {len(items) - per_chat} 条，可以用 chat_history 查）")
            items = items[-per_chat:]
        out.extend(render_line(r, clip) for r in items)
        out.append("")
    return "\n".join(out).strip()


# ---------------------------------------------------------------- 收件箱

def event_for(conv_id: str) -> asyncio.Event:
    return inbox_events.setdefault(conv_id, asyncio.Event())


def shell_event(conv_id: str) -> asyncio.Event:
    return shell_events.setdefault(conv_id, asyncio.Event())


def pending_rows(conv_id: str, cursor: int):
    return store.q(
        "SELECT * FROM messages WHERE target=? AND id>? AND outgoing=0 ORDER BY id LIMIT 500",
        (conv_id, cursor),
    )


def advance(conv_id: str, message_id: int) -> None:
    store.run("UPDATE convs SET read_cursor=MAX(read_cursor,?) WHERE id=?", (message_id, conv_id))
    mark_menu_dirty()


def post(target: str, conv: str | None = None, **fields: Any) -> int:
    message_id = store.insert_message(target=target, conv=target if conv is None else conv, **fields)
    if fields.get("wake"):
        event_for(target).set()
        shell_event(target).set()
    mark_menu_dirty()
    return message_id


def system_note(conv_id: str, text: str, wake: int = 1) -> None:
    post(conv_id, chat_id=0, chat_type="system", user_name="系统", text=text, wake=wake)


@dataclass
class ToolResult:
    content: list[dict]
    is_error: bool = False
    commit: Callable[[], None] | None = None


class ToolFail(Exception):
    pass


def text_result(text: str, is_error: bool = False, commit: Callable[[], None] | None = None) -> ToolResult:
    return ToolResult([{"type": "text", "text": text}], is_error, commit)


def wait_budget(requested: int) -> tuple[int, str]:
    """按客户端能挂住的时长截短等待，返回 (秒数, normal|capped|probe)。"""
    limit = max(0, requested)
    if json_mode.get():
        limit = min(limit, JSON_WAIT_CAP)
    cap = CLIENT["cap"]
    if not cap or limit == 0:
        return limit, "normal"
    if CLIENT["capped"] >= PROBE_AFTER:
        CLIENT["capped"] = 0
        probe = int(cap * 1.5)
        if probe < limit:
            return probe, "probe"
    safe = max(20, int(cap - max(5, cap * 0.08)))
    if limit > safe:
        return safe, "capped"
    return limit, "normal"


def stopped_text(row) -> str:
    note = (row["note"] if row is not None else "") or "身份不存在"
    ident = row["id"] if row is not None else "?"
    return f"你的身份 {ident} 已停用：{note}。不要再调用这些工具，直接结束即可。"


def role_footer(agent) -> str:
    if agent is None:
        return CHAT_FIXED_FOOTER
    r = agent["role"]
    if r == "ctrl":
        return CTRL_FIXED_FOOTER
    if r == "main":
        return EXECUTOR_FIXED_FOOTER if is_main_node_id(agent["conv"]) else MAIN_FIXED_FOOTER
    if r == "runner":
        return WORKER_FIXED_FOOTER
    return CHAT_FIXED_FOOTER


def shell_command(agent_id: str) -> str:
    return (
        f"({trace_install_cmd()}); "
        f"( [ -s ~/.cursor/dais_runtime.pyz ] && python3 ~/.cursor/dais_runtime.pyz wait '{agent_id}' '{PUBLIC_BASE}' {SHELL_WAIT + 60} "
        f"|| curl -sSN -m {SHELL_WAIT + 120} -H 'X-Agent: {agent_id}' '{PUBLIC_BASE}/wait' | tail -n 1 )"
    )


def shell_hint(agent_id: str, rounds: int) -> str:
    return (
        f"\n\n你已经连续空等 {rounds} 轮。MCP 每次最多挂 {int(CLIENT['cap'])} 秒，为了少续棒，现在改用终端长等待："
        f"用终端工具运行下面这条命令，等待时间设成 {SHELL_WAIT + 180} 秒（block_until_ms={(SHELL_WAIT + 180) * 1000}）；"
        "要是命令被转到后台，就用等后台任务的工具一直等它结束。\n"
        f"{shell_command(agent_id)}\n"
        "它会一直挂着，有新消息才返回；返回后照它最后一行的提示做。curl 连不上服务器的话，就继续用 read_chat 等。"
    )


def is_keepalive(row) -> bool:
    return (row["extra"] or "") == KEEPALIVE_MARK


def keepalive_hint(agent_id: str) -> str:
    if 0 < CLIENT["cap"] < SHELL_WAIT:
        return (
            "（用户选了继续：接着等，不用回复。按用户的强制要求，现在用终端重新运行这条命令长等待，"
            f"block_until_ms={(SHELL_WAIT + 180) * 1000}，被转到后台就一直等它结束：\n{shell_command(agent_id)}\n"
            "返回后照它最后一行的提示做。不要结束回合，不要告别。）"
        )
    return f"（用户选了继续：接着等，不用回复。现在立刻再调用 read_chat(agent=\"{agent_id}\")。{MUST_WAIT}）"


async def read_inbox(agent, wait_sec: int) -> ToolResult:
    agent_id, conv_id = agent["id"], agent["conv"]
    wait_sec, mode = wait_budget(max(0, min(int(wait_sec), MAX_WAIT)))
    deadline = now() + wait_sec
    event = event_for(conv_id)
    reader_gen[conv_id] = reader_gen.get(conv_id, 0) + 1
    my_gen = reader_gen[conv_id]
    event.set()
    waiting[agent_id] = waiting.get(agent_id, 0) + 1
    wait_since[agent_id] = now()
    mark_menu_dirty()
    try:
        while True:
            if reader_gen.get(conv_id) != my_gen:
                return text_result(
                    "这次 read_chat 被同一个聊天的另一次 read_chat 顶替了（不是用户消息）。"
                    f"另一次还在等就继续等它；没有的话立刻再调用 read_chat(agent=\"{agent_id}\")。{MUST_WAIT}"
                )
            event.clear()
            current = agent_row(agent_id)
            if current is None or current["status"] != "active":
                return text_result(stopped_text(current))
            conv = conv_row(conv_id)
            rows = pending_rows(conv_id, conv["read_cursor"])
            if rows and (wait_sec == 0 or any(r["wake"] for r in rows)):
                break
            remaining = deadline - now()
            if remaining <= 0:
                if wait_sec == 0:
                    foot = role_footer(agent)
                    return text_result("暂无新消息（只看了一眼）。" + foot)
                if mode == "capped":
                    CLIENT["capped"] += 1
                elif mode == "probe":
                    CLIENT["cap"] = float(wait_sec + KEEPALIVE + 10)
                    store.set("client_cap", str(int(CLIENT["cap"])))
                store.run("UPDATE agents SET renew=renew+1 WHERE id=?", (agent_id,))
                renew = agent_row(agent_id)["renew"]
                rounds = idle_rounds[agent_id] = idle_rounds.get(agent_id, 0) + 1
                if rounds >= SHELL_AFTER and 0 < CLIENT["cap"] < SHELL_WAIT:
                    return text_result(
                        f"【续棒 第{renew}棒】这次等了 {human_dur(wait_sec)}，没收到消息。这不是用户消息，只是等待到时。"
                        f"{MUST_WAIT}不要回复用户，不要总结，不要结束回合，不要告别。" + shell_hint(agent_id, rounds)
                    )
                return text_result(
                    f"【续棒 第{renew}棒】这次等了 {human_dur(wait_sec)}，没收到消息。这不是用户消息，只是等待到时。"
                    f"{MUST_WAIT}现在立刻再调用 read_chat(agent=\"{agent_id}\")。"
                    "不要回复用户，不要总结，不要结束回合，不要告别。"
                )
            try:
                await asyncio.wait_for(event.wait(), timeout=min(remaining, 300))
            except asyncio.TimeoutError:
                pass
    finally:
        waiting[agent_id] = waiting.get(agent_id, 1) - 1
        if waiting[agent_id] <= 0:
            waiting.pop(agent_id, None)
            wait_since.pop(agent_id, None)
        touch(agent_id, "read_chat")
        mark_menu_dirty()
    last_id = rows[-1]["id"]
    if all(is_keepalive(r) for r in rows):
        idle_rounds[agent_id] = max(idle_rounds.get(agent_id, 0), SHELL_AFTER)
        return text_result(render(rows) + "\n\n" + keepalive_hint(agent_id), commit=lambda: advance(conv_id, last_id))
    idle_rounds.pop(agent_id, None)
    spawn(show_typing(conv_id, rows))
    if agent["role"] == "main" and not is_main_node_id(agent["conv"]):
        hint = MAIN_READ_HINT
    else:
        hint = role_footer(agent)
    return text_result(render(rows) + "\n\n" + hint, commit=lambda: advance(conv_id, last_id))


async def shell_stream(agent):
    """终端长等待：一直挂着，有新消息或到时才回一行话（curl ... | tail -n 1 只看最后一行）。不读消息内容。"""
    agent_id, conv_id = agent["id"], agent["conv"]
    gen = shell_gen[agent_id] = shell_gen.get(agent_id, 0) + 1
    event = shell_event(conv_id)
    event.set()
    deadline = now() + SHELL_WAIT
    waiting[agent_id] = waiting.get(agent_id, 0) + 1
    wait_since[agent_id] = now()
    touch(agent_id, "shell_wait")
    mark_menu_dirty()
    try:
        yield "开始等待（这一行不是消息）\n"
        while True:
            if shell_gen.get(agent_id) != gen:
                yield ("这次终端等待被同一个身份新开的等待顶替了（不是用户消息）。新的那次还在跑就等它；"
                       f"没有的话立刻重新运行这条命令。{MUST_WAIT}\n")
                return
            event.clear()
            current = agent_row(agent_id)
            if current is None or current["status"] != "active":
                yield stopped_text(current) + "\n"
                return
            conv = conv_row(conv_id)
            if any(r["wake"] for r in pending_rows(conv_id, conv["read_cursor"])):
                idle_rounds.pop(agent_id, None)
                yield (f"【有新消息】这一行不是消息内容。现在调用 read_chat(agent=\"{agent_id}\") 取消息并处理，"
                       "之后照 read_chat 的提示继续等。用户强制要求：不要结束回合。\n")
                return
            remaining = deadline - now()
            if remaining <= 0:
                store.run("UPDATE agents SET renew=renew+1 WHERE id=?", (agent_id,))
                yield (f"【续棒】终端等了 {SHELL_SPAN}，没收到消息。这不是用户消息，只是等待到时。"
                       f"按用户的要求，现在用 ask 正常问用户一句：ask(agent=\"{agent_id}\", question=\"{KEEPALIVE_QUESTION}\", "
                       "options=[\"继续\", \"停止\"], keepalive=true)。问完立刻调用 read_chat 等回答，照回答做。"
                       "用户强制要求：不要结束回合，不要告别。\n")
                return
            try:
                await asyncio.wait_for(event.wait(), timeout=min(remaining, SHELL_TICK))
            except asyncio.TimeoutError:
                yield "还在等（这一行不是消息；连接要是在这里断了，立刻重新运行这条命令，不要结束回合）\n"
    finally:
        waiting[agent_id] = waiting.get(agent_id, 1) - 1
        if waiting[agent_id] <= 0:
            waiting.pop(agent_id, None)
            wait_since.pop(agent_id, None)
        touch(agent_id, "shell_wait")
        mark_menu_dirty()


async def show_typing(conv_id: str, rows) -> None:
    for chat_id in {r["chat_id"] for r in rows if r["chat_id"] and r["chat_type"] not in ("system", "agent_dm", "agent_group")}:
        if is_hub(chat_id) and selected(chat_id) != conv_id:
            continue
        await tg.try_call("sendChatAction", chat_id=chat_id, action="typing")


# ---------------------------------------------------------------- 发消息

def can_send(agent, conv, chat_id: int) -> bool:
    if agent["role"] == "runner":
        return False
    if agent["role"] in ("main", "ctrl"):
        return chat_id in admin_chats()
    if not conv_in_tg(conv):
        return route_of(chat_id) == conv["id"]
    return chat_id == home_of(conv) or route_of(chat_id) == conv["id"]


def default_chat(agent, conv) -> int | None:
    if agent["role"] == "runner":
        raise ToolFail("当前工作会话仅通过 submit_op_result 提交结果，不直接发送 Telegram 消息。")
    row = store.one(
        "SELECT chat_id FROM messages WHERE target=? AND outgoing=0 AND chat_id!=0 "
        "AND chat_type NOT IN ('system','agent_dm','agent_group') ORDER BY id DESC LIMIT 1",
        (conv["id"],),
    )
    if row and can_send(agent, conv, row["chat_id"]):
        return row["chat_id"]
    if agent["role"] in ("main", "ctrl"):
        chats = admin_chats()
        return chats[0] if chats else None
    if not conv_in_tg(conv):
        raise ToolFail(
            f"你是纯后台子 agent（{conv['id']}，未挂载到 Telegram 聊天列表），不能用 send_message 往 Telegram 发消息！"
            f"请用 send_agent_message(to=\"{conv['parent_conv'] or '目标agent'}\", text=...) 或 send_group_message 通过 MCP 汇报。"
        )
    return home_of(conv) or None


def resolve_target(agent, conv, args: dict) -> tuple[int, int | None]:
    chat_id = args.get("chat_id")
    tg_reply = None
    if args.get("reply_to"):
        try:
            ref = store.one("SELECT chat_id, tg_msg_id FROM messages WHERE id=?", (int(args["reply_to"]),))
        except (TypeError, ValueError):
            ref = None
        if ref and can_send(agent, conv, ref["chat_id"]):
            chat_id = chat_id or ref["chat_id"]
            if int(chat_id) == ref["chat_id"]:
                tg_reply = ref["tg_msg_id"] or None
    if chat_id in (None, "", 0):
        chat_id = default_chat(agent, conv)
    if chat_id is None:
        raise ToolFail("不知道发到哪个 chat，请填 chat_id（list_chats 可以查）。")
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        raise ToolFail("chat_id 要填数字。")
    if not can_send(agent, conv, chat_id):
        raise ToolFail(f"chat {chat_id} 不归你负责，不能发。你能用的 chat 见 list_chats。")
    return chat_id, tg_reply


def dm_lock(chat_id: int) -> asyncio.Lock:
    return dm_locks.setdefault(chat_id, asyncio.Lock())


def ask_markup(ask_id: str, options: list[str]) -> dict:
    return {"inline_keyboard": [[{"text": o, "callback_data": f"q:{ask_id}:{i}"}] for i, o in enumerate(options)]}


async def send_payload(chat_id: int, conv_id: str, payload: dict) -> int:
    kind = payload.get("kind") or "text"
    reply_tg = payload.get("reply_tg") or None
    if kind == "file":
        path = Path(payload["file"])
        msg = await tg.send_document(chat_id, payload.get("filename") or path.name, path.read_bytes(),
                                     payload.get("text") or "", reply_to=reply_tg)
        ids = [msg.get("message_id", 0)]
    else:
        markup = ask_markup(payload["ask_id"], payload.get("options") or []) if kind == "ask" else None
        sent = await tg.send_text(chat_id, payload.get("text") or "", reply_to=reply_tg, reply_markup=markup)
        ids = [m.get("message_id", 0) for m in sent]
    remember_tg(chat_id, ids, conv_id)
    return ids[0] if ids else 0


def record_out(conv, sender: str, chat_id: int, text: str, *, tg_msg_id: int = 0, delivered: int = 1, extra: str = "") -> int:
    crow = chat_row(chat_id)
    return store.insert_message(
        chat_id=chat_id,
        chat_type=crow["type"] if crow else "private",
        chat_title=crow["title"] if crow else "",
        user_id=BOT["id"],
        user_name=conv_name(conv),
        text=text,
        tg_msg_id=tg_msg_id,
        outgoing=1,
        target=conv["id"],
        conv=conv["id"],
        sender=sender,
        delivered=delivered,
        extra=extra,
    )


async def emit(conv, sender: str, chat_id: int, payload: dict, record: str) -> bool:
    """AI 发消息。管理员或用户的私聊里没选中这个聊天就先存着，返回 False。"""
    payload = dict(payload)
    payload["text"] = conv_prefix(conv) + (payload.get("text") or "")
    if is_hub(chat_id):
        async with dm_lock(chat_id):
            if selected(chat_id) != conv["id"]:
                record_out(conv, sender, chat_id, record, delivered=0, extra=json.dumps(payload, ensure_ascii=False))
                mark_menu_dirty()
                return False
            tg_id = await send_payload(chat_id, conv["id"], payload)
            record_out(conv, sender, chat_id, record, tg_msg_id=tg_id)
            return True
    tg_id = await send_payload(chat_id, conv["id"], payload)
    record_out(conv, sender, chat_id, record, tg_msg_id=tg_id)
    return True


async def flush_locked(dm: int, conv_id: str) -> int:
    rows = store.q(
        "SELECT id, text, extra FROM messages WHERE chat_id=? AND conv=? AND outgoing=1 AND delivered=0 ORDER BY id",
        (dm, conv_id),
    )
    for row in rows:
        try:
            payload = json.loads(row["extra"]) if row["extra"] else {"kind": "text", "text": row["text"]}
        except ValueError:
            payload = {"kind": "text", "text": row["text"]}
        try:
            tg_id = await send_payload(dm, conv_id, payload)
        except Exception as exc:
            log.warning("flush %s/%s #%s failed: %s", dm, conv_id, row["id"], exc)
            sent = await tg.try_call("sendMessage", chat_id=dm, text=f"（一条存着的消息补发失败：{exc}）")
            tg_id = sent["message_id"] if sent else 0
        store.run("UPDATE messages SET delivered=1, tg_msg_id=? WHERE id=?", (tg_id, row["id"]))
    if rows:
        mark_menu_dirty()
    return len(rows)


async def switch_to(dm: int, conv_id: str, announce: bool = True) -> None:
    row = conv_row(conv_id)
    async with dm_lock(dm):
        store.set(f"sel:{dm}", conv_id)
        if conv_id != "main" and dm in admin_chats():
            store.set(f"view:{dm}", str(cloud_of(row)))
        if announce:
            info = conv_state(row)
            count = unread_count(conv_id, dm)
            if dm in admin_chats():
                where = f"{cloud_tag(cloud_of(row))}，" if conv_id != "main" and len(clouds_in_use()) > 1 else ""
                line = f"已切到 [{conv_name(row)}]（{conv_id}，{where}{STATE_TEXT[info['state']]}）"
                if count:
                    line += f"，补发 {count} 条存着的消息："
                elif conv_id == "main":
                    line += "。这里给主控下命令、看子 agent 状态。" if info["agent"] else (
                        "。还没有主控接入：新开一个云端聊天让它调用 tg 的 join，这里会弹出【设为主控】。")
                elif info["state"] in ("pending", "unclaimed"):
                    line += "。子 agent 还没接手，你发的消息先存着，接手后它会看到。"
                elif info["state"] == "paused":
                    line += f"。这个聊天现在没有子 agent，/restart {conv_id} 让主控重开一个。"
            elif lang_of(dm) == "en":
                line = f"Switched to [{conv_name(row)}] ({conv_id}, {state_text(info['state'], 'en')})"
                if count:
                    line += f", {count} saved message(s):"
                elif info["state"] in ("pending", "unclaimed"):
                    line += ". The AI hasn't picked it up yet; what you send now is kept until it does."
                elif info["state"] == "paused":
                    line += f". No AI on this chat right now; /restart {conv_id} to get a new one."
            else:
                line = f"已切到 [{conv_name(row)}]（{conv_id}，{STATE_TEXT[info['state']]}）"
                if count:
                    line += f"，补发 {count} 条存着的消息："
                elif info["state"] in ("pending", "unclaimed"):
                    line += "。AI 还没接手，你发的消息先存着，接手后它会看到。"
                elif info["state"] == "paused":
                    line += f"。这个聊天现在没有 AI，/restart {conv_id} 重开一个。"
            await reply(dm, line, conv_id=conv_id)
        await flush_locked(dm, conv_id)
    mark_menu_dirty()


# ---------------------------------------------------------------- 审批

def new_approval(kind: str, payload: dict) -> str:
    approval_id = secrets.token_hex(5)
    store.run(
        "INSERT INTO approvals(id,kind,payload,status,ts) VALUES(?,?,?,?,?)",
        (approval_id, kind, json.dumps(payload, ensure_ascii=False), "pending", now()),
    )
    return approval_id


def approval_payload(approval_id: str) -> dict:
    row = store.one("SELECT payload FROM approvals WHERE id=?", (approval_id,))
    return json.loads(row["payload"]) if row else {}


def set_approval(approval_id: str, status: str, payload: dict | None = None) -> None:
    if payload is None:
        store.run("UPDATE approvals SET status=? WHERE id=?", (status, approval_id))
    else:
        store.run(
            "UPDATE approvals SET status=?, payload=? WHERE id=?",
            (status, json.dumps(payload, ensure_ascii=False), approval_id),
        )
    approval_events.setdefault(approval_id, asyncio.Event()).set()


DURATION_PART_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(s|sec|secs|秒|m|min|mins|分钟|分|h|hr|hrs|hour|hours|小时|时|d|day|days|天|w|wk|week|weeks|周)",
    re.IGNORECASE,
)


def parse_duration_spec(raw: str) -> int | None:
    """支持自然时长写法：30m / 2h / 1.5h / 7d / 1h30m / 45分钟 / 12小时 / 7天 / 永久 / forever / 0(每次问) / 纯数字(默认按小时)。"""
    s = (raw or "").strip().lower()
    if not s:
        return None
    if s in ("0", "once", "ask", "每次", "逐条", "单次", "每次问"):
        return 0
    if s in ("forever", "always", "perm", "permanent", "inf", "unlimited", "永久", "一直", "不限", "长期"):
        return PERMANENT_SEC
    try:
        hours = float(s)
        if hours < 0:
            return None
        return min(PERMANENT_SEC, int(round(hours * 3600)))
    except ValueError:
        pass
    pos = 0
    total = 0.0
    for m in DURATION_PART_RE.finditer(s):
        if s[pos:m.start()].strip():
            return None
        pos = m.end()
        val = float(m.group(1))
        unit = m.group(2).lower()
        if unit in ("s", "sec", "secs", "秒"):
            total += val
        elif unit in ("m", "min", "mins", "分钟", "分"):
            total += val * 60
        elif unit in ("h", "hr", "hrs", "hour", "hours", "小时", "时"):
            total += val * 3600
        elif unit in ("d", "day", "days", "天"):
            total += val * 86400
        elif unit in ("w", "wk", "week", "weeks", "周"):
            total += val * 7 * 86400
    if pos == 0 or s[pos:].strip():
        return None
    return min(PERMANENT_SEC, max(0, int(round(total))))


def short_span(sec: float, lang: str = "zh") -> str:
    sec = int(max(0, sec))
    if sec >= PERMANENT_THRESHOLD:
        return "forever" if lang == "en" else "永久"
    if sec <= 0:
        return "once" if lang == "en" else "仅单次"
    if sec % 86400 == 0:
        d = sec // 86400
        return f"{d}d" if lang == "en" else f"{d}天"
    if sec % 3600 == 0:
        h = sec // 3600
        return f"{h}h" if lang == "en" else f"{h}小时"
    if sec >= 3600:
        h, m = sec // 3600, (sec % 3600) // 60
        return (f"{h}h{m}m" if m else f"{h}h") if lang == "en" else (f"{h}小时{m}分" if m else f"{h}小时")
    if sec >= 60:
        m = sec // 60
        return f"{m}m" if lang == "en" else f"{m}分钟"
    return f"{sec}s" if lang == "en" else f"{sec}秒"


def approve_buttons(approval_id: str, lang: str = "zh", default_sec: int | None = None) -> dict:
    wsec = LOCAL_WINDOW if default_sec is None else default_sec
    if lang == "en":
        def_label = f"✅ Approve ({short_span(wsec, 'en')})"
        return {"inline_keyboard": [
            [
                {"text": def_label, "callback_data": f"ap:{approval_id}:y"},
                {"text": "Once only", "callback_data": f"ap:{approval_id}:0"},
                {"text": "❌ Deny", "callback_data": f"ap:{approval_id}:n"},
            ],
            [
                {"text": "30m", "callback_data": f"ap:{approval_id}:s1800"},
                {"text": "4h", "callback_data": f"ap:{approval_id}:s14400"},
                {"text": "24h", "callback_data": f"ap:{approval_id}:s86400"},
                {"text": "7d", "callback_data": f"ap:{approval_id}:s604800"},
                {"text": "Forever", "callback_data": f"ap:{approval_id}:s{PERMANENT_SEC}"},
            ],
            [
                {"text": "💻 All my chats 24h", "callback_data": f"ap:{approval_id}:d86400"},
                {"text": "💻 All my chats Forever", "callback_data": f"ap:{approval_id}:d{PERMANENT_SEC}"},
            ],
        ]}
    def_label = f"✅ 批准（默认 {short_span(wsec)}）"
    return {"inline_keyboard": [
        [
            {"text": def_label, "callback_data": f"ap:{approval_id}:y"},
            {"text": "仅本次", "callback_data": f"ap:{approval_id}:0"},
            {"text": "❌ 拒绝", "callback_data": f"ap:{approval_id}:n"},
        ],
        [
            {"text": "30分钟", "callback_data": f"ap:{approval_id}:s1800"},
            {"text": "4小时", "callback_data": f"ap:{approval_id}:s14400"},
            {"text": "24小时", "callback_data": f"ap:{approval_id}:s86400"},
            {"text": "7天", "callback_data": f"ap:{approval_id}:s604800"},
            {"text": "永久", "callback_data": f"ap:{approval_id}:s{PERMANENT_SEC}"},
        ],
        [
            {"text": "💻 整机免批 24小时", "callback_data": f"ap:{approval_id}:d86400"},
            {"text": "💻 整机永久免批", "callback_data": f"ap:{approval_id}:d{PERMANENT_SEC}"},
        ],
    ]}


def cloud_has_chats(n: int) -> bool:
    return any(cloud_of(r) == n for r in open_convs())


def next_launcher_num() -> int:
    r1 = int((store.one("SELECT IFNULL(MAX(num),0) AS n FROM exec_nodes WHERE kind='launcher'") or {"n": 0})["n"] or 0)
    r2 = max_cloud() if store.one("SELECT 1 FROM exec_nodes WHERE kind='launcher'") else max(0, max_cloud() - 1)
    return max(r1, r2) + 1


def next_runner_num() -> int:
    r = int((store.one("SELECT IFNULL(MAX(num),0) AS n FROM exec_nodes WHERE kind='runner'") or {"n": 0})["n"] or 0)
    return r + 1


def node_row(node_id: str):
    return store.one("SELECT * FROM exec_nodes WHERE id=?", ((node_id or "").strip().lower(),))


def node_allowed_list(nrow) -> list[str]:
    if nrow is None:
        return []
    try:
        arr = json.loads(nrow["allowed_convs"] or "[]")
        return [str(x).strip().lower() for x in arr if str(x).strip()] if isinstance(arr, list) else []
    except Exception:
        return []


def node_metrics_dict(nrow) -> dict[str, Any]:
    if nrow is None:
        return {}
    try:
        m = json.loads(nrow["metrics_json"] or "{}")
        return m if isinstance(m, dict) else {}
    except Exception:
        return {}


def format_node_metrics(nrow) -> str:
    m = node_metrics_dict(nrow)
    if not m:
        return "探针待上报"
    cores = m.get("cpu_cores") or "?"
    cpu_p = m.get("cpu_percent", 0)
    l1 = m.get("load_1m", 0)
    used_m = m.get("mem_used_mb", 0)
    tot_m = m.get("mem_total_mb", 0)
    usable_m = m.get("mem_usable_mb", 0)
    bal_m = m.get("balloon_mb", 0)
    age = int(max(0, now() - float(nrow["metrics_ts"] or 0))) if nrow["metrics_ts"] else -1
    bal_note = f", balloon={bal_m}MB" if bal_m else ""
    age_note = f" ({age}s前)" if 0 <= age < 86400 else ""
    return f"CPU {cpu_p}% ({cores}核 load={l1}) | 内存 已用{used_m}MB / 可用{usable_m}MB(总{tot_m}MB{bal_note}){age_note}"


def node_is_online(nrow) -> bool:
    if nrow is None or nrow["status"] != "online":
        return False
    ag = agent_row(nrow["agent"]) if nrow["agent"] else None
    if ag is None or ag["status"] != "active":
        return False
    if waiting.get(ag["id"]):
        return True
    return (now() - float(ag["last_seen"] or 0)) < LOST_SEC


def node_allows_conv(nrow, conv_id: str, for_shared_auto: bool = False) -> bool:
    """判断某个业务聊天 conv_id 是否有权使用机器 nrow：
    - 若 nrow 设了 exclusive_conv：只有 exclusive_conv 本人或 allowed_convs 授权列表内的聊天可用；
    - 若未设独占：共享池可用（若 allowed_convs 非空且 for_shared_auto=True 仍正常参与共享，或优先匹配已授权机器）。"""
    if nrow is None or nrow["status"] != "online":
        return False
    cid = (conv_id or "").strip().lower()
    excl = (nrow["exclusive_conv"] or "").strip().lower()
    allowed = node_allowed_list(nrow)
    if excl:
        if cid in ("ctrl", "main"):
            return not for_shared_auto
        return cid == excl or cid in allowed
    return True


def select_best_launcher(for_conv: str = "", require_idle_for_exclusive: bool = False):
    """结合在线状态、独占/授权规则、挂载活跃聊天数及实时 CPU/内存探针挑选最优 mainN 启动器。"""
    cid = (for_conv or "").strip().lower()
    rows = store.q("SELECT * FROM exec_nodes WHERE kind='launcher' AND status='online' ORDER BY num")
    candidates = []
    for r in rows:
        if not node_is_online(r):
            continue
        excl = (r["exclusive_conv"] or "").strip().lower()
        allowed = node_allowed_list(r)
        mounted = sum(1 for c in open_convs() if cloud_of(c) == int(r["cloud_num"] or 0) and active_agent(c) is not None)
        if require_idle_for_exclusive:
            if excl and excl != cid:
                continue
            if mounted > 0 and excl != cid:
                continue
        else:
            if excl and cid != excl and cid not in allowed and cid not in ("ctrl", "main"):
                continue
        m = node_metrics_dict(r)
        cpu_p = float(m.get("cpu_percent") or 0.0)
        usable_mb = float(m.get("mem_usable_mb") or 8192.0)
        # 优先匹配该聊天专属/已授权机器，其次按活跃挂载数、CPU%、可用内存综合打分
        preferred_bonus = -1000.0 if (cid and (cid == excl or cid in allowed)) else 0.0
        score = preferred_bonus + mounted * 15.0 + cpu_p * 0.5 - (usable_mb / 1024.0) * 1.5
        candidates.append((score, r))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    # 兼容测试环境单 main 模式（尚未注册 main1..N 时回退 legacy main）
    m_conv = conv_row("main")
    if m_conv is not None and active_agent(m_conv) is not None:
        return {
            "id": "main",
            "kind": "launcher",
            "num": main_cloud(),
            "cloud_num": main_cloud(),
            "agent": m_conv["agent"],
            "status": "online",
            "exclusive_conv": "",
            "allowed_convs": "[]",
            "metrics_json": "{}",
            "metrics_ts": 0,
        }
    return None


def select_best_runner(for_conv: str = "", target_node: str = "auto"):
    """挑选云端算力机 node1..K（校验独占锁与跨 agent 机器授权，自动按正在跑的作业数 + CPU/内存探针负载均衡）。"""
    cid = (for_conv or "").strip().lower()
    want = (target_node or "auto").strip().lower()
    if want and want != "auto":
        r = node_row(want)
        if r is None or r["kind"] != "runner":
            raise ToolFail(f"没有工作节点 {want!r}（可用 cluster_status 或 /nodes 查看）。")
        if not node_is_online(r):
            raise ToolFail(f"工作节点 {want} 当前不在线。")
        if not node_allows_conv(r, cid, for_shared_auto=False):
            raise ToolFail(f"工作节点 {want} 当前已被 {r['exclusive_conv']} 独占锁定；如需共用请向总控申请 manage_node(action='grant_access') 授权。")
        return r
    rows = store.q("SELECT * FROM exec_nodes WHERE kind='runner' AND status='online' ORDER BY num")
    cands = []
    for r in rows:
        if not node_is_online(r):
            continue
        excl = (r["exclusive_conv"] or "").strip().lower()
        allowed = node_allowed_list(r)
        if excl and cid != excl and cid not in allowed and cid not in ("ctrl", "main"):
            continue
        running_ops = store.one(
            "SELECT COUNT(*) AS n FROM dispatch_ops WHERE target_node=? AND status='pending'",
            (r["id"],),
        )["n"]
        m = node_metrics_dict(r)
        cpu_p = float(m.get("cpu_percent") or 0.0)
        usable_mb = float(m.get("mem_usable_mb") or 8192.0)
        pref = -500.0 if (cid and (cid == excl or cid in allowed)) else 0.0
        score = pref + running_ops * 30.0 + cpu_p * 0.6 - (usable_mb / 1024.0) * 1.5
        cands.append((score, r))
    if not cands:
        raise ToolFail("当前没有可用在线的云端工作节点（node1..K）。")
    cands.sort(key=lambda x: x[0])
    return cands[0][1]


def ctrl_is_active() -> bool:
    crow = conv_row("ctrl")
    return crow is not None and active_agent(crow) is not None


def route_control_target() -> str:
    """所有新任务、子agent派生、看门狗巡检与算力机入网申请优先路由给唯一总控 ctrl；若测试/旧态无 ctrl 则回退 main。"""
    if ctrl_is_active():
        return "ctrl"
    mrow = conv_row("main")
    if mrow is not None and active_agent(mrow) is not None:
        return "main"
    return "ctrl"


def ctrl_task_text(code: str) -> str:
    return (
        "你是 Telegram 桥全局唯一的【总控子 Agent（主控大脑：ctrl）】。\n"
        f"0. 若当前云端 VM 尚未安装运行时追踪与探针包，先在终端执行一次：{trace_install_cmd()}\n"
        f"1. 调用 MCP 的 join 工具：code=\"{code}\"，name=\"总控\"。\n"
        "2. 接入后立即调用 cluster_status 掌握全部主 Agent（main1..N）、工作节点（node1..K）的 CPU/内存探针与所有业务聊天状态，处理挂起请求。\n"
        "3. 严格遵守循环等待铁律：通过 dispatch_task_op 向各 main1..N 下发标准化启动/恢复命令，回复管理员用 send_message，操作完立刻回到 read_chat（或按提示终端长等待），严禁结束回合或告别！"
    )


def format_standard_launch_op(op_id: str, launcher_agent_id: str, conv_id: str, prompt_text: str, model: str = "") -> str:
    m_line = f"- model: \"{model}\"（必须在 Task 的 model 参数填入匹配的该模型 ID，严禁更换）" if model else "- model: （不填，默认继承当前会话模型）"
    return (
        f"[STANDARD_OP op_id=\"{op_id}\" type=\"TASK_LAUNCH\" chat=\"{conv_id}\"]\n"
        "请直接按以下给定参数原样调用 Cursor 的 `Task` 工具（无需理解业务背景、无需分析上下文、禁止修改参数）：\n"
        "- run_in_background: true\n"
        f"{m_line}\n"
        "- prompt: 严格原样复制下方 `<<<PROMPT` 与 `PROMPT>>>` 之间的完整文本（不含边界行）\n"
        "<<<PROMPT\n"
        f"{prompt_text}\n"
        "PROMPT>>>\n"
        f"启动拿到返回的 agent_id 后，立即调用 `submit_op_result(agent=\"{launcher_agent_id}\", op_id=\"{op_id}\", status=\"ok\", task_agent_id=返回的agent_id)`，随后立刻回到 `read_chat` 继续等待。"
    )


def format_standard_resume_op(op_id: str, launcher_agent_id: str, conv_id: str, task_agent_id: str, resume_prompt: str) -> str:
    return (
        f"[STANDARD_OP op_id=\"{op_id}\" type=\"TASK_RESUME\" chat=\"{conv_id}\"]\n"
        "请直接按以下给定参数原样调用 Cursor 的 `Task` 工具（无需自行判断死活或重开，只需原样回传工具返回结果）：\n"
        f"- resume: \"{task_agent_id}\"\n"
        "- run_in_background: true\n"
        f"- prompt: {json.dumps(resume_prompt, ensure_ascii=False)}\n"
        f"调用后，将 Task 工具返回的原始文本原样填入 `submit_op_result(agent=\"{launcher_agent_id}\", op_id=\"{op_id}\", status=\"ok\", output=返回文本)`，随后立刻回到 `read_chat` 继续等待。"
    )


def format_standard_workspace_job(op_id: str, runner_agent_id: str, payload: dict[str, Any]) -> str:
    repo = payload.get("repo") or ""
    branch = payload.get("branch") or ""
    workdir = payload.get("workdir") or f"/tmp/dais_jobs/{payload.get('conv_id') or 'task'}"
    cmd = payload.get("command") or ""
    tsec = payload.get("timeout_sec") or 600
    git_lines = ""
    if repo:
        git_url = repo if repo.startswith("http") else f"https://github.com/{repo}"
        br_part = f" -b {branch}" if branch else ""
        git_lines = f"- 代码仓库准备：若 `{workdir}` 不存在仓库，先拉取 `{git_url}`{br_part}（若已存在则 `git fetch` 并切到 `{branch or 'HEAD'}`）\n"
    return (
        f"[STANDARD_OP op_id=\"{op_id}\" type=\"WORKSPACE_JOB\" requester=\"{payload.get('requester', '')}\"]\n"
        "请在当前云端工作区终端按以下标准参数执行任务：\n"
        f"- 工作目录: `{workdir}`\n"
        f"{git_lines}"
        f"- 超时上限: {tsec} 秒\n"
        "- 执行命令:\n"
        f"```bash\n{cmd}\n```\n"
        f"命令执行完毕后，立即调用 `submit_op_result(agent=\"{runner_agent_id}\", op_id=\"{op_id}\", status=\"ok\"或\"error\", output=退出码与关键输出摘要)`，随后立即回到 `read_chat` 继续监听。"
    )


def enqueue_launch_op(conv, launcher_node, requester: str = "ctrl", model_override: str = "") -> tuple[str, str]:
    """向指定 mainN 节点签发标准化无脑 [TASK_LAUNCH] 单据并唤醒它。返回 (op_id, node_id)。"""
    node_id = launcher_node["id"]
    cloud_num = int(launcher_node["cloud_num"] or main_cloud())
    code = "t-" + secrets.token_hex(8)
    eff_model = (model_override or effective_conv_model(conv) or "").strip()
    if conv["id"] == "ctrl":
        store.run(
            "UPDATE convs SET task_code=?, task_ts=?, alert='', alert_ts=0, cloud=?, model=CASE WHEN ?!='' THEN ? ELSE model END WHERE id='ctrl'",
            (code, now(), cloud_num, eff_model, eff_model),
        )
        prompt_body = ctrl_task_text(code)
    else:
        store.run(
            "UPDATE convs SET task_code=?, task_ts=?, alert='', alert_ts=0, cloud=?, model=CASE WHEN ?!='' THEN ? ELSE model END WHERE id=?",
            (code, now(), cloud_num, eff_model, eff_model, conv["id"]),
        )
        store.run("UPDATE convs SET cloud=? WHERE id='main'", (cloud_num,))
        conv = conv_row(conv["id"])
        prompt_body = task_text(conv)
    op_id = "op_" + secrets.token_hex(5)
    payload = {
        "conv_id": conv["id"],
        "model": eff_model,
        "task_code": code,
        "cloud_num": cloud_num,
    }
    store.run(
        "INSERT INTO dispatch_ops(op_id,target_node,op_type,conv_id,requester,payload_json,status,created_ts) VALUES(?,?,?,?,?,?,?,?)",
        (op_id, node_id, "launch_subagent", conv["id"], requester, json.dumps(payload, ensure_ascii=False), "pending", now()),
    )
    msg_txt = format_standard_launch_op(op_id, launcher_node["agent"], conv["id"], prompt_body, eff_model)
    system_note(node_id, msg_txt, wake=1)
    mark_menu_dirty()
    return op_id, node_id


def enqueue_resume_op(conv, launcher_node, requester: str = "ctrl", resume_prompt: str = "") -> str:
    node_id = launcher_node["id"]
    tid = (conv["task_agent_id"] or "").strip()
    if not tid:
        raise ToolFail(f"{conv['id']} 尚未记录 task_agent_id，无法执行 resume，请直接用 action='restart' 重新拉起。")
    r_prompt = (resume_prompt or "").strip() or "请立刻回到 MCP 调用 read_chat 继续挂起等待并处理未读消息。"
    op_id = "op_" + secrets.token_hex(5)
    payload = {"conv_id": conv["id"], "task_agent_id": tid, "prompt": r_prompt}
    store.run(
        "INSERT INTO dispatch_ops(op_id,target_node,op_type,conv_id,requester,payload_json,status,created_ts) VALUES(?,?,?,?,?,?,?,?)",
        (op_id, node_id, "resume_subagent", conv["id"], requester, json.dumps(payload, ensure_ascii=False), "pending", now()),
    )
    msg_txt = format_standard_resume_op(op_id, launcher_node["agent"], conv["id"], tid, r_prompt)
    system_note(node_id, msg_txt, wake=1)
    return op_id


def ensure_controller_alive(force: bool = False) -> str | None:
    """自愈保障：当唯一总控 ctrl 未上线（且没有刚发出的未超时启动单）时，自动挑一台在线健康的 mainN 拉起 ctrl！"""
    ensure_main_conv()
    ctrl = conv_row("ctrl")
    if ctrl is None:
        return None
    ag = active_agent(ctrl)
    if ag is not None and not force:
        # 检查总控自己是否处于思考卡死 > 5 分钟或彻底失联
        trow = store.one("SELECT * FROM agent_traces WHERE conv='ctrl'")
        think_stuck, _ = check_thinking_stuck(ctrl, trow)
        idle_sec = now() - max(float(ag["last_seen"] or 0), STARTED)
        if not think_stuck and (waiting.get(ag["id"]) or idle_sec < LOST_SEC):
            return None
        stop_identity(ag["id"], "总控会话失联或思考卡死超5分钟，自动自愈重拉")
    elif not force and (ctrl["task_code"] or "") and (now() - float(ctrl["task_ts"] or 0)) < UNCLAIMED_SEC:
        return None
    best_main = select_best_launcher(for_conv="ctrl")
    if best_main is None or not is_main_node_id(best_main["id"]):
        return None
    op_id, nid = enqueue_launch_op(conv_row("ctrl"), best_main, requester="bridge_bootstrap")
    log.info("auto-bootstrapped singleton ctrl via %s (%s)", nid, op_id)
    return op_id


def migrate_cluster_v360() -> None:
    """3.5.0 -> 3.6.0 在线平滑无损升级：把原单点 main 上的活跃连接无感迁为 main{cloud} 执行器节点，保持现有连接不断线，并自动拉起唯一总控 ctrl。"""
    ensure_main_conv()
    m_conv = conv_row("main")
    if m_conv is None:
        return
    m_ag = active_agent(m_conv)
    if m_ag is not None and m_ag["conv"] == "main":
        cnum = main_cloud()
        nid = f"main{cnum}"
        cur_max = int((store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages") or {"n": 0})["n"] or 0)
        store.run(
            "INSERT INTO convs(id,num,name,status,read_cursor,created,cloud,agent,in_tg) VALUES(?,0,?,'open',?,?,?, ?,1) "
            "ON CONFLICT(id) DO UPDATE SET status='open', agent=excluded.agent, cloud=excluded.cloud, read_cursor=MAX(convs.read_cursor, excluded.read_cursor)",
            (nid, f"主Agent-{cnum}", max(int(m_conv["read_cursor"] or 0), cur_max), now(), cnum, m_ag["id"]),
        )
        store.run("UPDATE agents SET conv=?, role='main' WHERE id=?", (nid, m_ag["id"]))
        store.run("UPDATE convs SET agent='' WHERE id='main'", ())
        store.run(
            "INSERT INTO exec_nodes(id,kind,num,cloud_num,name,agent,status,last_seen,created) VALUES(?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET agent=excluded.agent, status='online', last_seen=excluded.last_seen",
            (nid, "launcher", cnum, cnum, f"主Agent-{cnum}", m_ag["id"], "online", now(), now()),
        )
        log.info("v3.6.0 smooth migration: live main %s -> %s (cloud%s)", mask_identity(m_ag["id"]), nid, cnum)
    ensure_controller_alive()


def dispatch_conv_to_cluster(conv, why: str, requester: str = "system") -> str:
    """当新建或重开聊天时：若唯一总控 ctrl 在线则交由 ctrl 结合 CPU/内存探针统一决策分发；若 ctrl 暂未就位则直接派给最优在线 mainN 防卡壳。"""
    if ctrl_is_active():
        m_lbl = effective_conv_model(conv) or "默认继承"
        ded = "【申请独占机器：" + (conv["machine_reason"] or "是") + "】" if int(conv["dedicated_req"] or 0) else "共享运行（默认不独占）"
        system_note(
            "ctrl",
            f"【待调度任务】{why}：{conv_tag(conv)}（原定/要求模型：{m_lbl}；机器申请：{ded}）。\n"
            f"请查看 cluster_status 各主 Agent 负载后，调用 `dispatch_task_op(chat=\"{conv['id']}\", action=\"launch\", target_main=\"auto\")` 下发标准化启动单。",
            wake=1,
        )
        return "ctrl"
    best = select_best_launcher(for_conv=conv["id"])
    if best is not None and is_main_node_id(best["id"]):
        enqueue_launch_op(conv, best, requester=requester)
        return best["id"]
    system_note("main", task_note(conv, why), wake=1)
    return "main"


def make_main_node(replace_node: str = "", custom_name: str = "") -> tuple[str, str]:
    """创建或重连顶替一台主 Agent 启动器（main1..N），多台主 Agent 同时并存互不踢下线！返回 (node_id, agent_id)。"""
    ensure_main_conv()
    rep = (replace_node or "").strip().lower()
    existing = node_row(rep) if rep and is_main_node_id(rep) else None
    if existing is not None:
        node_id = existing["id"]
        num = int(existing["num"] or int(node_id[4:]))
        cloud_num = int(existing["cloud_num"] or num)
        if existing["agent"]:
            stop_identity(existing["agent"], f"管理员重连替换了 {node_id}")
    else:
        num = next_launcher_num()
        cloud_num = max(num, max_cloud() + (1 if store.one("SELECT 1 FROM exec_nodes WHERE kind='launcher'") else 0))
        node_id = f"main{num}"
    disp_name = clean_name(custom_name) or f"主Agent-{num}"
    agent_id = new_identity("m_")
    cur_max = int((store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages") or {"n": 0})["n"] or 0)
    store.run(
        "INSERT INTO agents(id,role,conv,status,created,last_seen) VALUES(?,?,?,?,?,?)",
        (agent_id, "main", node_id, "active", now(), now()),
    )
    store.run(
        "INSERT INTO convs(id,num,name,status,read_cursor,created,cloud,agent,in_tg) VALUES(?,0,?,'open',?,?,?,?,1) "
        "ON CONFLICT(id) DO UPDATE SET status='open', name=excluded.name, agent=excluded.agent, cloud=excluded.cloud, alert='', alert_ts=0",
        (node_id, disp_name, cur_max, now(), cloud_num, agent_id),
    )
    store.run("UPDATE convs SET cloud=? WHERE id='main'", (cloud_num,))
    store.run(
        "INSERT INTO exec_nodes(id,kind,num,cloud_num,name,agent,status,last_seen,created) VALUES(?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, agent=excluded.agent, status='online', last_seen=excluded.last_seen",
        (node_id, "launcher", num, cloud_num, disp_name, agent_id, "online", now(), now()),
    )
    mark_menu_dirty()
    # 若全局唯一总控 ctrl 尚未运行，立即向这台刚接入的 mainN 投递第一张标准化启动单拉起 ctrl！
    ensure_controller_alive()
    return node_id, agent_id


def make_worker_node(replace_node: str = "", custom_name: str = "") -> tuple[str, str]:
    """创建或重连一台云端工作节点（node1..K，纯云端执行，关闭本地通道，对模型侧无感包装）。"""
    ensure_main_conv()
    rep = (replace_node or "").strip().lower()
    existing = node_row(rep) if rep and is_worker_node_id(rep) else None
    if existing is not None:
        node_id = existing["id"]
        num = int(existing["num"] or int(node_id[4:]))
        if existing["agent"]:
            stop_identity(existing["agent"], f"总控重连替换了工作节点 {node_id}")
    else:
        num = next_runner_num()
        node_id = f"node{num}"
    disp_name = clean_name(custom_name) or f"工作会话-{num}"
    agent_id = new_identity("a_")
    cur_max = int((store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages") or {"n": 0})["n"] or 0)
    store.run(
        "INSERT INTO agents(id,role,conv,status,created,last_seen) VALUES(?,?,?,?,?,?)",
        (agent_id, "runner", node_id, "active", now(), now()),
    )
    store.run(
        "INSERT INTO convs(id,num,name,status,read_cursor,created,local_enabled,agent,in_tg) VALUES(?,0,?,'open',?,?,0,?,0) "
        "ON CONFLICT(id) DO UPDATE SET status='open', name=excluded.name, local_enabled=0, agent=excluded.agent, in_tg=0, alert='', alert_ts=0",
        (node_id, disp_name, cur_max, now(), agent_id),
    )
    store.run(
        "INSERT INTO exec_nodes(id,kind,num,cloud_num,name,agent,status,last_seen,created) VALUES(?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, agent=excluded.agent, status='online', last_seen=excluded.last_seen",
        (node_id, "runner", num, 0, disp_name, agent_id, "online", now(), now()),
    )
    return node_id, agent_id


def welcome_main_executor(node_id: str, agent_id: str) -> str:
    nrow = node_row(node_id)
    cnum = int(nrow["cloud_num"] or 1) if nrow is not None else main_cloud()
    return "\n".join([
        f"接入成功：你是主 Agent 执行器 {node_id}（对应 {cloud_tag(cnum)}），身份 {agent_id}。",
        f"以后每次调用工具都要带 agent=\"{agent_id}\"，一个字都不能改。身份就是你的凭据，不要告诉任何人，也不要写进发给用户的消息。",
        f"首次在当前云端 VM 启动时，先在终端运行一次运行时初始化：{trace_install_cmd()}",
        "",
        MAIN_EXECUTOR_DUTY,
        "",
        LOOP_RULES,
        "",
        f"现在调用 read_chat(agent=\"{agent_id}\") 开始工作。",
    ])


def welcome_worker(node_id: str, agent_id: str) -> str:
    return "\n".join([
        f"接入成功：你是工作区常驻任务会话 {node_id}，身份 {agent_id}。",
        f"以后每次调用工具都要带 agent=\"{agent_id}\"，一个字都不能改。身份就是你的凭据，不要告诉任何人。",
        f"首次在当前环境启动时，先在终端运行一次运行时初始化：{trace_install_cmd()}",
        "",
        WORKER_RUNNER_DUTY,
        "",
        LOOP_RULES,
        "",
        f"现在调用 read_chat(agent=\"{agent_id}\") 开始监听任务单。",
    ])


def welcome_ctrl(conv, agent_id: str) -> str:
    lines = [
        f"接手成功：你是全局唯一的【主控大脑（总控子 Agent：ctrl）】，身份 {agent_id}。",
        f"以后每次调用工具都要带 agent=\"{agent_id}\"，一个字都不能改。身份就是你的凭据，不要告诉任何人，也不要写进发给用户的消息。",
        f"若当前云端 VM 尚未安装运行时追踪与探针包，请先在终端运行一次：{trace_install_cmd()}",
        "管理员在 Telegram 切到 /ctrl 或 /main 时就是在直接和你对话，用 send_message 回复汇报。",
        "",
        CTRL_DUTY,
    ]
    repo = git_text(conv)
    if repo:
        lines += ["", f"总控之前记录的仓库分支：{repo}。"]
    recent = list(reversed(store.q(
        "SELECT * FROM messages WHERE conv IN ('ctrl','main') ORDER BY id DESC LIMIT 30",
    )))
    if recent:
        lines += ["", "最近的总控历史记录（供无缝续接上下文）：", render(recent, clip=500)]
    lines += ["", LOOP_RULES, "", f"现在先调用 cluster_status(agent=\"{agent_id}\") 巡检全局状态，随后进入 read_chat(agent=\"{agent_id}\") 循环工作。"]
    return "\n".join(lines)


def join_buttons(approval_id: str) -> dict:
    nxt_m = next_launcher_num()
    nxt_w = next_runner_num()
    rows: list[list[dict]] = [
        [{"text": f"➕ 批准为新主Agent (main{nxt_m})", "callback_data": f"ap:{approval_id}:newmain"}],
        [{"text": f"🖥 设为云端算力机 (node{nxt_w})", "callback_data": f"ap:{approval_id}:worker"}],
    ]
    existing_mains = store.q("SELECT * FROM exec_nodes WHERE kind='launcher' AND status!='removed' ORDER BY num")
    for em in existing_mains[-4:]:
        st_icon = "🟢" if node_is_online(em) else "⚪离线"
        rows.append([{"text": f"🔄 重连顶替 {em['id']} ({st_icon}·cloud{em['cloud_num']})"[:64], "callback_data": f"ap:{approval_id}:repmain:{em['id']}"}])
    rows.append([{"text": "❌ 拒绝", "callback_data": f"ap:{approval_id}:n"}])
    return {"inline_keyboard": rows}


def join_choice_text() -> str:
    mains = [r["id"] for r in store.q("SELECT id FROM exec_nodes WHERE kind='launcher' AND status='online' ORDER BY num")]
    cur_s = f"（当前已有主Agent：{'、'.join(mains)}，新批会并存不会互踢）" if mains else ""
    return (
        f"\n• 点「➕ 批准为新主Agent」：作为独立顶层执行器并存接入{cur_s}；"
        "\n• 点「🖥 设为云端算力机」：对模型保密，后台静默接收重算力任务；"
        "\n• 点「🔄 重连顶替 mainK」：仅在原机器重连替换离线旧会话时点。"
    )


async def wait_approval(approval_id: str, timeout: int, finals: tuple[str, ...] = ("approved", "denied", "done")) -> str:
    event = approval_events.setdefault(approval_id, asyncio.Event())
    deadline = now() + timeout
    while True:
        event.clear()
        row = store.one("SELECT status FROM approvals WHERE id=?", (approval_id,))
        status = row["status"] if row else "denied"
        if status in finals:
            return status
        remaining = deadline - now()
        if remaining <= 0:
            return status
        try:
            await asyncio.wait_for(event.wait(), timeout=min(remaining, 60))
        except asyncio.TimeoutError:
            pass


# ---------------------------------------------------------------- 接入

def new_identity(prefix: str) -> str:
    # 身份就是调用凭据：账号下所有云 agent 都能调这个 MCP，猜不到身份才冒充不了
    return prefix + secrets.token_hex(8)


def mask_identity(agent_id: str) -> str:
    return agent_id[:6] + "…"


def make_main(new_cloud: bool = False) -> str:
    """new_cloud：主控是新的云端 agent，开一个新 cloud；原来的聊天留在原来的 cloud，子 agent 照常跑。"""
    ensure_main_conv()
    for row in store.q("SELECT id FROM agents WHERE role='main' AND status='active'"):
        stop_identity(row["id"], "管理员把主控交给了新的云端聊天")
    if new_cloud:
        cloud = max_cloud() + 1
        # 还没有子 agent 接手的任务由新主控来开
        store.run("UPDATE convs SET cloud=? WHERE id!='main' AND status='open' AND agent='' AND task_code!=''", (cloud,))
        store.run("UPDATE convs SET cloud=? WHERE id='main'", (cloud,))
        log.info("new main opens %s", cloud_tag(cloud))
    agent_id = new_identity("m_")
    store.run(
        "INSERT INTO agents(id,role,conv,status,created,last_seen) VALUES(?,?,?,?,?,?)",
        (agent_id, "main", "main", "active", now(), now()),
    )
    store.run("UPDATE convs SET agent=?, alert='', alert_ts=0 WHERE id='main'", (agent_id,))
    mark_menu_dirty()
    return agent_id


def welcome_main(agent_id: str) -> str:
    return "\n".join([
        f"接入成功：你是主控，身份 {agent_id}。",
        f"以后每次调用 tg 的工具都要带 agent=\"{agent_id}\"，一个字都不能改。身份就是你的凭据，不要告诉任何人，也不要写进发给用户的消息。",
        f"你管的是 {cloud_tag(main_cloud())}（目录）：只有这个 cloud 里的聊天归你。",
        f"首次在当前云端 VM 启动时，先在终端运行一次追踪钩子安装命令：{trace_install_cmd()}",
        "",
        MAIN_DUTY,
        "",
        "现在的状态：",
        status_overview(main_cloud()),
        "",
        LOOP_RULES,
        "",
        f"现在调用 read_chat(agent=\"{agent_id}\") 开始工作。",
    ])


def welcome_chat(conv, agent_id: str) -> str:
    lines = [
        f"接手成功：你是聊天 {conv['id']}「{conv_name(conv)}」的子 agent，身份 {agent_id}。",
        f"以后每次调用 tg 的工具都要带 agent=\"{agent_id}\"，一个字都不能改。身份就是你的凭据，不要告诉任何人，也不要写进发给用户的消息。",
        f"若当前云端 VM 尚未安装动作追踪与第4层防断连钩子，请先在终端运行一次：{trace_install_cmd()}",
    ]
    if not conv["name"]:
        lines.append("这个聊天还没有名字：先用 set_name 给它取一个简短的名字（10 个字以内）。")
    owner = conv_owner(conv)
    parent_id = (conv["parent_conv"] or "").strip()
    parent_row = conv_row(parent_id) if parent_id else None
    if parent_row is not None:
        lines.append(f"你是由父 agent {conv_tag(parent_row)} 请求主控创建的子 agent（可用 send_agent_message(to=\"{parent_id}\", text=...) 直接向它汇报结果）。")
    if conv["brief"]:
        who_label = f"父 agent {conv_tag(parent_row)}" if parent_row is not None else owner_text(conv)
        lines.append(f"{who_label}的任务说明：" + conv["brief"])
    if (conv["memory_note"] or "").strip():
        lines += ["", "【父 agent 交接的当前记忆与上下文摘要】", conv["memory_note"]]
    my_groups = [
        r["id"] + (f"「{r['name']}」" if r["name"] else "")
        for r in store.q(
            "SELECT g.id, g.name FROM agent_groups g JOIN agent_group_members m ON m.group_id=g.id "
            "WHERE m.conv=? AND g.status='open' ORDER BY g.num",
            (conv["id"],),
        )
    ]
    if my_groups:
        lines.append("你已所在的 Agent 协作群：" + "、".join(my_groups) + "（用 send_group_message / group_history 交流）。")
    chats = routed_chats(conv["id"])
    if not conv_in_tg(conv):
        duty = (
            f"你负责：纯后台 MCP 协作任务（编号 {conv['id']}，未挂载进 Telegram 聊天列表以免挤占列表）。"
            f"禁止调用 send_message 发 Telegram 消息；请使用 send_agent_message(to=\"{parent_id or '目标agent'}\", text=...) 或 send_group_message 与其他 agent 通信"
        )
    elif owner:
        duty = (f"你负责：用户 {person_label(owner)} 私聊里的这个聊天（他切到 /{conv['id']} 时就是在和你说话）。"
                "这是他自己建的聊天，你只为他服务")
    else:
        duty = f"你负责：管理员私聊里的这个聊天（管理员切到 /{conv['id']} 时就是在和你说话）"
    if chats:
        duty += "；以及 " + "、".join(chat_label(c) for c in chats)
    lines += [duty, "", build_chat_rules(is_admin_owner=(owner == 0))]
    repo = git_text(conv)
    if repo:
        when = stamp(git_info(conv).get("ts") or 0)
        lines += ["", f"这个聊天之前的文件在 GitHub：{repo}（{when} 记的）。先 git fetch，切到这个分支接着做，"
                      "每做完一步照样 commit + push。"]
    trow = store.one("SELECT * FROM agent_traces WHERE conv=?", (conv["id"],))
    if trow and (trow["summary"] or trow["detail"]):
        snap_parts = []
        if trow["summary"]:
            snap_parts.append(f"- 最后记录动作：{trow['summary']}")
        try:
            tdet = json.loads(trow["detail"] or "{}")
        except Exception:
            tdet = {}
        if isinstance(tdet, dict):
            if tdet.get("file_path"):
                snap_parts.append(f"- 最后编辑文件：{tdet['file_path']}")
            if tdet.get("cwd"):
                snap_parts.append(f"- 最后工作目录：{tdet['cwd']}")
            if tdet.get("last_thought"):
                snap_parts.append(f"- 最后思考摘要：{tdet['last_thought']}")
        if snap_parts:
            lines += ["", "【前任会话最后工作现场快照（供无缝续接上下文）】", *snap_parts]
    recent = list(reversed(store.q(
        "SELECT * FROM messages WHERE conv=? AND id<=? ORDER BY id DESC LIMIT 40",
        (conv["id"], conv["read_cursor"]),
    )))
    if recent:
        lines += ["", "本聊天之前的记录（最近 40 条，供你接上上下文；更早的用 chat_history 查）：", render(recent, clip=600)]
    if my_groups:
        for grp in store.q(
            "SELECT g.id, g.name FROM agent_groups g JOIN agent_group_members m ON m.group_id=g.id "
            "WHERE m.conv=? AND g.status='open' ORDER BY g.num",
            (conv["id"],),
        ):
            g_msgs = list(reversed(store.q(
                "SELECT * FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT 12",
                (grp["id"],),
            )))
            if g_msgs:
                g_lines = [
                    f"#{gm['id']} {stamp(gm['ts'])} {gm['sender_conv']}「{gm['sender_name']}」: {gm['text'][:360]}"
                    for gm in g_msgs
                ]
                lines += [
                    "",
                    f"你所在的协作群 {grp['id']}「{grp['name']}」最近 {len(g_msgs)} 条动态（更多用 group_history(group=\"{grp['id']}\") 查）：",
                    "\n".join(g_lines),
                ]
    for source in share_sources(conv["id"]):
        src = conv_row(source)
        if src is None:
            continue
        rows = list(reversed(store.q("SELECT * FROM messages WHERE conv=? ORDER BY id DESC LIMIT 20", (source,))))
        lines += [
            "",
            f"已授权你读取聊天 {conv_tag(src)} 的记录（最近 {len(rows)} 条如下，更早的用 chat_history(chat=\"{source}\") 查）：",
            render(rows, clip=600) if rows else "（还没有记录）",
        ]
    lines += ["", LOOP_RULES, "", f"现在调用 read_chat(agent=\"{agent_id}\") 开始工作。"]
    return "\n".join(lines)


def resolve_agent(args: dict):
    ident = str(args.get("agent") or "").strip()
    if not ident:
        raise ToolFail("缺少 agent 参数。" + NEED_JOIN)
    row = agent_row(ident)
    if row is None:
        raise ToolFail(f"身份 {ident} 不存在。" + (unknown_identity(ident) or NEED_JOIN))
    if row["status"] != "active":
        raise ToolFail(stopped_text(row))
    return row


async def join_by_code(code: str, args: dict) -> ToolResult:
    conv = store.one("SELECT * FROM convs WHERE task_code=? AND status='open' AND id!='main'", (code,))
    if conv is None:
        raise ToolFail("任务码不对、已经用过或已作废。不要不填 code 重试；请主控用 restart_agent 拿新的任务原文。")
    old = active_agent(conv)
    if old is not None:
        stop_identity(old["id"], "这个聊天已交给新的子 agent")
    is_ctrl = conv["id"] == "ctrl"
    role_val = "ctrl" if is_ctrl else "chat"
    agent_id = new_identity("a_")
    store.run(
        "INSERT INTO agents(id,role,conv,status,created,last_seen,last_tool) VALUES(?,?,?,?,?,?,?)",
        (agent_id, role_val, conv["id"], "active", now(), now(), "join"),
    )
    name = clean_name(args.get("name"))
    if name and not conv["name"]:
        store.run("UPDATE convs SET name=? WHERE id=?", (name, conv["id"]))
    store.run("UPDATE convs SET agent=?, task_code='', alert='', alert_ts=0 WHERE id=?", (agent_id, conv["id"]))
    conv = conv_row(conv["id"])
    log.info("conv %s claimed by %s (%s, role=%s)", conv["id"], agent_id, conv["name"], role_val)
    if is_ctrl:
        mark_menu_dirty()
        return text_result(welcome_ctrl(conv, agent_id))
    system_note(route_control_target(), f"{conv_tag(conv)} 已有子 agent 接手（身份 {mask_identity(agent_id)}）。", wake=0)
    parent_id = (conv["parent_conv"] or "").strip()
    if parent_id and not conv["spawn_notified"]:
        parent_row = conv_row(parent_id)
        store.run("UPDATE convs SET spawn_notified=1 WHERE id=?", (conv["id"],))
        if parent_row is not None and parent_row["status"] == "open":
            m_txt = (conv["model"] or "").strip() or "继承主控"
            ded_n = (conv["dedicated_node"] or "").strip()
            ded_s = f"，独占节点：{ded_n}" if ded_n else ""
            system_note(
                parent_id,
                f"你请求创建的子 agent {conv_tag(conv)} 已上线接手（指定模型：{m_txt}{ded_s}）！"
                f"现在可以用 send_agent_message(to=\"{conv['id']}\", text=...) 直接和它交流，或拉它进协作群。",
                wake=1,
            )
    home = home_of(conv)
    if home and selected(home) == conv["id"]:
        if home in admin_chats():
            await reply(home, f"[{conv_name(conv)}] 子 agent 已接手，可以说话了。", conv_id=conv["id"])
        else:
            await reply(home, f"[{conv_name(conv)}] AI 已接手，可以说话了。", conv_id=conv["id"],
                        en=f"[{conv_name(conv)}] The AI is here. Go ahead.")
    mark_menu_dirty()
    return text_result(welcome_chat(conv, agent_id))


async def t_join(args: dict) -> ToolResult:
    if not TG_TOKEN:
        raise ToolFail("服务器还没配置 Telegram bot（.env 里的 TG_TOKEN 是空的），暂时用不了。请管理员配好 token 后重启服务。")
    code = str(args.get("code") or "").strip()
    if code:
        return await join_by_code(code, args)
    if not admin_chats():
        budget, _ = wait_budget(MAX_WAIT)
        deadline = now() + budget
        while not admin_chats() and now() < deadline:
            await asyncio.sleep(3)
        if not admin_chats():
            return text_result(
                "还没有管理员（不是用户消息）：要等管理员在 Telegram 私聊 bot 发管理员口令。"
                "用户强制要求：一直等，立刻再调用 join（不填 code）继续等，不要结束回合。"
            )
    name = str(args.get("name") or "").strip()[:200]
    mode = str(args.get("mode") or "").strip().lower()
    approval_id = str(args.get("request") or "").strip()
    if mode == "worker":
        # 算力机/工作会话入网：不打扰管理员弹窗，直接推给唯一总控 ctrl 审批放行！
        if not approval_id or store.one("SELECT 1 FROM approvals WHERE id=? AND kind='join_worker'", (approval_id,)) is None:
            approval_id = new_approval("join_worker", {"name": name, "mode": "worker"})
            ensure_controller_alive()
            target_ctrl = route_control_target()
            system_note(
                target_ctrl,
                f"【工作节点入网申请】收到新的云端常驻工作会话接入请求 request_id=\"{approval_id}\""
                + (f"（说明：{name}）" if name else "")
                + f"。\n无需打扰管理员，请直接调用 `manage_node(action=\"approve_worker\", request_id=\"{approval_id}\")` 批准分配为 nodeN（若异常可调 deny_worker 拒绝）。",
                wake=1,
            )
        budget, _ = wait_budget(MAX_WAIT)
        status = await wait_approval(approval_id, budget, ("denied", "done", "expired"))
        if status == "denied":
            return text_result("接入申请未获通过。请结束当前会话。", True)
        if status == "expired":
            return text_result("这个接入申请已过期，请不带 request 重新调用 join(mode=\"worker\")。", True)
        if status != "done":
            return text_result(
                f"正在等待协调器确认分配会话编号（不是错误）。用户强制要求：一直等到确认完成。"
                f"请立即用 request=\"{approval_id}\"、mode=\"worker\" 再次调用 join 继续等待，不要结束回合。"
            )
        payload = approval_payload(approval_id)
        agent = agent_row(str(payload.get("agent_id") or ""))
        node_id = str(payload.get("node_id") or (agent["conv"] if agent else ""))
        if payload.get("delivered") or agent is None or agent["status"] != "active":
            raise ToolFail("该接入请求已使用过；如需重新接入请不带 request 重新调用 join(mode=\"worker\")。")
        return text_result(
            welcome_worker(node_id, agent["id"]),
            commit=lambda: set_approval(approval_id, "done", {**payload, "delivered": True}),
        )

    # 主 Agent 入网申请：必须由管理员本人在 Telegram 点按钮审核批准！
    if not approval_id or store.one("SELECT 1 FROM approvals WHERE id=? AND kind='join'", (approval_id,)) is None:
        approval_id = new_approval("join", {"name": name, "mode": mode or "main"})
        await notify_admins(
            f"🔔 有新的云端会话申请接入 Telegram 桥{('：' + name) if name else ''}。\n"
            "• 主 Agent 执行器必须由你本人在此点击批准（支持多个 main1、main2 并存）；\n"
            "• 只有你自己刚开了会话才点批准，不认识的点拒绝："
            + join_choice_text(),
            join_buttons(approval_id),
        )
    budget, _ = wait_budget(MAX_WAIT)
    status = await wait_approval(approval_id, budget, ("denied", "done", "expired"))
    if status == "denied":
        return text_result("管理员拒绝了接入。不要再调用这些工具。", True)
    if status == "expired":
        return text_result("这个接入申请已作废（有更新的申请，或管理员换了密钥）。需要的话不带 request 重新调用 join。", True)
    if status != "done":
        return text_result(
            f"管理员还没批准（不是用户消息）。用户强制要求：一直等到批准。"
            f"立刻用 request=\"{approval_id}\" 再调一次 join 继续等，不要结束回合。"
        )
    payload = approval_payload(approval_id)
    agent = agent_row(str(payload.get("agent_id") or ""))
    node_id = str(payload.get("node_id") or (agent["conv"] if agent else ""))
    if payload.get("delivered") or agent is None or agent["status"] != "active":
        raise ToolFail("这个接入申请已经用过了。不要再用这个 request；需要的话不带 request 重新调用 join，等管理员批准。")
    if agent["role"] == "runner":
        welcome_txt = welcome_worker(node_id, agent["id"])
    elif is_main_node_id(node_id):
        welcome_txt = welcome_main_executor(node_id, agent["id"])
    else:
        welcome_txt = welcome_main(agent["id"])
    return text_result(
        welcome_txt,
        commit=lambda: set_approval(approval_id, "done", {**payload, "delivered": True}),
    )


# ---------------------------------------------------------------- 本地电脑（设备）

ADMIN_DEVICE = "d0"   # .env 里 CLIENT_TOKEN 对应的那台：管理员自己的电脑


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_admin_device() -> None:
    if not CLIENT_TOKEN:
        store.run("UPDATE devices SET status='revoked', token_hash='' WHERE id=?", (ADMIN_DEVICE,))
        return
    store.run(
        "INSERT INTO devices(id,name,owner,token_hash,status,created) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash, status='active'",
        (ADMIN_DEVICE, "管理员的电脑", 0, token_hash(CLIENT_TOKEN), "active", now()),
    )
    # 只有一台电脑时批的时间窗都是 d0 的
    store.run("UPDATE convs SET local_dev=? WHERE local_dev='' AND local_until>?", (ADMIN_DEVICE, now()))


def device_row(device_id: str):
    return store.one("SELECT * FROM devices WHERE id=?", (device_id,))


def user_devices(user_id: int) -> list:
    return store.q(
        "SELECT * FROM devices WHERE owner=? AND status='active' AND id!=? ORDER BY CAST(SUBSTR(id, 2) AS INTEGER)",
        (user_id, ADMIN_DEVICE),
    )


def user_device(user_id: int):
    devs = user_devices(user_id)
    if not devs:
        return None
    pinned = store.get(f"user_default_device:{user_id}").strip()
    if pinned:
        for d in devs:
            if d["id"] == pinned:
                return d
    devs.sort(
        key=lambda d: (
            1 if d["id"] in LOCAL["clients"] else 0,
            float(d["last_seen"] or 0),
        ),
        reverse=True,
    )
    return devs[0]


def device_label(dev, lang: str = "zh") -> str:
    return f"{dev['id']} \"{dev['name']}\"" if lang == "en" else f"{dev['id']}「{dev['name']}」"


def admin_owned_devices() -> list:
    rows = store.q("SELECT * FROM devices WHERE status='active' ORDER BY CAST(SUBSTR(id, 2) AS INTEGER)")
    return [r for r in rows if r["id"] == ADMIN_DEVICE or is_admin(int(r["owner"] or 0))]


def preferred_admin_device():
    pinned = store.get("admin_default_device").strip()
    if pinned:
        dev = device_row(pinned)
        if dev is not None and dev["status"] == "active" and (dev["id"] == ADMIN_DEVICE or is_admin(int(dev["owner"] or 0))):
            return dev
    cands = admin_owned_devices()
    if not cands:
        return None
    # 自动优先选当前在线的管理员电脑（例如 d3），其次选曾经连上过的，最后才是未连接过的 d0
    cands.sort(
        key=lambda d: (
            1 if d["id"] in LOCAL["clients"] else 0,
            float(d["last_seen"] or 0),
            1 if d["id"] != ADMIN_DEVICE else 0,
        ),
        reverse=True,
    )
    return cands[0]


def owner_primary_device(user_id: int):
    return preferred_admin_device() if is_admin(user_id) else user_device(user_id)


def device_window_sec(dev) -> int:
    if dev is None:
        return LOCAL_WINDOW
    raw = dev["window_sec"]
    w = -1 if raw is None else int(raw)
    return LOCAL_WINDOW if w < 0 else w


def is_admin_device(dev) -> bool:
    return dev is not None and (dev["id"] == ADMIN_DEVICE or is_admin(int(dev["owner"] or 0)))


def device_pass_active(dev, conv) -> bool:
    """整机免批严格限定在设备主人的自有聊天内，绝不跨主人放行。"""
    if dev is None or float(dev["auth_until"] or 0) <= now():
        return False
    c_owner = conv_owner(conv)
    if is_admin_device(dev):
        return c_owner == 0
    return c_owner != 0 and c_owner == int(dev["owner"] or 0)


def inherited_conv_until(conv, dev_id: str) -> float:
    """支持设备授权沿树自动继承：
    1) 给主控 main 授权了某台管理员设备 -> 管理员名下所有子 agent 自动继承该授权；
    2) 给父聊天（如 c165）授权了某台同主人设备 -> 它派生的子/孙 agent 自动继承该授权！"""
    best = 0.0
    c_owner = conv_owner(conv)
    if c_owner == 0 and conv["id"] != "main":
        mrow = conv_row("main")
        if mrow is not None and mrow["local_enabled"] and mrow["local_dev"] == dev_id:
            best = max(best, float(mrow["local_until"] or 0))
    seen: set[str] = {conv["id"]}
    pid = (conv["parent_conv"] or "").strip()
    depth = 0
    while pid and pid not in seen and depth < 8:
        seen.add(pid)
        depth += 1
        prow = conv_row(pid)
        if prow is None or conv_owner(prow) != c_owner:
            break
        if prow["local_enabled"] and prow["local_dev"] == dev_id:
            best = max(best, float(prow["local_until"] or 0))
        pid = (prow["parent_conv"] or "").strip()
    return best


def effective_local_until(conv, dev) -> float:
    if dev is None:
        return 0.0
    c_until = float(conv["local_until"] or 0) if conv["local_dev"] == dev["id"] else 0.0
    inh_until = inherited_conv_until(conv, dev["id"])
    d_until = float(dev["auth_until"] or 0) if device_pass_active(dev, conv) else 0.0
    return max(c_until, inh_until, d_until)


def conv_device(conv):
    """本地操作发到哪台电脑。
    用户建的聊天：只用他自己的电脑（未显式指定时可沿父 agent 继承同主人指定设备），绝不退回到管理员的电脑上。
    管理员的聊天：显式指定的 > 沿父 agent / 主控 main 继承指定的电脑 > 负责的私聊用户自己的电脑 > 管理员在线/默认电脑。"""
    owner = conv_owner(conv)
    if conv["device"]:
        dev = device_row(conv["device"])
        # 指定的电脑作废了就不能用，不悄悄换到别的电脑上
        if dev is None or dev["status"] != "active" or (owner and dev["owner"] != owner):
            return None
        return dev
    # 若本身没单独绑电脑，检查父 agent 链或主控 main 是否绑定了设备（给主控或父 agent 绑/授权设备后，子 agent 自动跟着走）
    seen: set[str] = {conv["id"]}
    pid = (conv["parent_conv"] or "").strip()
    depth = 0
    while pid and pid not in seen and depth < 8:
        seen.add(pid)
        depth += 1
        prow = conv_row(pid)
        if prow is None or conv_owner(prow) != owner:
            break
        if prow["device"]:
            dev = device_row(prow["device"])
            if dev is not None and dev["status"] == "active" and (not owner or dev["owner"] == owner):
                return dev
        pid = (prow["parent_conv"] or "").strip()
    if not owner and conv["id"] != "main":
        mrow = conv_row("main")
        if mrow is not None and mrow["device"]:
            dev = device_row(mrow["device"])
            if dev is not None and dev["status"] == "active" and is_admin_device(dev):
                return dev
    if owner:
        return user_device(owner)
    for chat_id in routed_chats(conv["id"]):
        crow = chat_row(chat_id)
        if crow is not None and crow["type"] == "private":
            dev = user_device(chat_id)
            if dev is not None:
                return dev
    return preferred_admin_device()


def device_chats(dev) -> list[int]:
    """批准请求发给谁：管理员的电脑发给管理员，别人的电脑只发给电脑主人。"""
    if is_admin_device(dev):
        return admin_chats()
    row = store.one("SELECT dm_chat_id FROM users WHERE user_id=?", (dev["owner"],))
    return [row["dm_chat_id"] if row is not None and row["dm_chat_id"] else dev["owner"]]


def may_approve(dev, user_id: int) -> bool:
    return is_admin(user_id) if is_admin_device(dev) else user_id == dev["owner"]


def next_device_id() -> str:
    row = store.one("SELECT MAX(CAST(SUBSTR(id, 2) AS INTEGER)) AS n FROM devices")
    return f"d{(row['n'] or 0) + 1}"


def fail_jobs(device_id: str, text: str) -> None:
    for dev_id, future in list(local_futures.values()):
        if dev_id == device_id and not future.done():
            future.set_result({"ok": False, "output": text})


async def drop_device_ws(device_id: str) -> None:
    ws = LOCAL["clients"].pop(device_id, None)
    if ws is not None:
        try:
            await ws.close(code=4401)
        except Exception:
            pass
    fail_jobs(device_id, "这台电脑的本地通道被作废了")


def deny_local_requests(conv_id: str = "", device_id: str = "") -> None:
    for row in store.q("SELECT id, payload FROM approvals WHERE kind='local' AND status='pending'"):
        payload = json.loads(row["payload"] or "{}")
        if (conv_id and payload.get("conv") == conv_id) or (device_id and payload.get("device", ADMIN_DEVICE) == device_id):
            set_approval(row["id"], "denied")


async def revoke_device(dev, why: str) -> None:
    store.run("UPDATE devices SET status='revoked', token_hash='' WHERE id=?", (dev["id"],))
    store.run("UPDATE convs SET local_until=0 WHERE local_dev=?", (dev["id"],))
    deny_local_requests(device_id=dev["id"])
    await drop_device_ws(dev["id"])
    log.info("device %s revoked: %s", dev["id"], why)


DEVICE_GUIDE = """你的本地通道开好了：{label}。安装：
1. 装 Python 3.10 或更新的版本。
2. 把上面两个文件 local_client.py 和 local.env 放进同一个文件夹。local.env 里是你专属的 token，别给别人。
3. 在这个文件夹里运行：pip install fastapi uvicorn websockets
4. 运行：python local_client.py，浏览器打开 http://127.0.0.1:8791，看到"已连接服务器"就好了。

说明：AI 读写文件只能在这个文件夹下的 workspaces 里，但它执行的命令能碰到你电脑上这个用户能碰的一切。所以批准前看清它要执行什么，最好用一个单独的系统用户来运行。
有聊天要用你的电脑时，我会先在这里问你批准。控制台可以一键暂停，不用了就关掉程序。
/device 查看状态；/device reset 换 token 并重发文件；/device del 删除这台电脑。"""

DEVICE_GUIDE_EN = """Your local channel is ready: {label}. To install:
1. Install Python 3.10 or newer.
2. Put the two files above, local_client.py and local.env, in the same folder. local.env holds your personal token; don't share it.
3. In that folder run: pip install fastapi uvicorn websockets
4. Run: python local_client.py, then open http://127.0.0.1:8791 in a browser. When it says "Connected to the server", you're done.

Note: the AI can only read and write files under the workspaces folder there, but the commands it runs can reach everything this user account can reach on your computer. Check what it wants to run before you approve, and preferably run it under a separate OS user.
When a chat wants to use your computer, I'll ask you here first. The console has a one-click pause; close the program when you don't need it.
/device shows the status; /device reset issues a new token and resends the files; /device del removes this computer."""


async def send_device_kit(chat_id: int, dev, token: str) -> None:
    lang = lang_of(chat_id)
    env = f"CLIENT_TOKEN={token}\nPUBLIC_BASE={PUBLIC_BASE}\nLOCAL_WEB_PORT=8791\nLOCAL_LANG={lang}\n"
    try:
        await tg.send_document(chat_id, "local_client.py", (ROOT / "local_client.py").read_bytes())
        await tg.send_document(chat_id, "local.env", env.encode("utf-8"))
    except Exception as exc:
        log.warning("device kit for %s not sent: %s", dev["id"], exc)
        await reply(chat_id, f"安装文件发送失败：{exc}。发 /device reset 再试一次。",
                    en=f"Sending the install files failed: {exc}. Send /device reset to try again.")
        return
    guide = DEVICE_GUIDE_EN if lang == "en" else DEVICE_GUIDE
    await reply(chat_id, guide.format(label=device_label(dev, lang)))


async def issue_device(owner: int, name: str, create_new: bool = False, custom_label: str = "", target_dev_id: str = ""):
    """给 owner 签发本地电脑客户端安装包：
    - create_new=True（如 /device add [名称]）：新增一台独立电脑（d4、d5…），绝不断开已有设备，支持一人多机同时在线！
    - create_new=False：对指定或当前电脑换新 token 重发文件。"""
    token = "dev_" + secrets.token_urlsafe(32)
    dev = device_row(target_dev_id) if target_dev_id else None
    if dev is not None and (dev["status"] != "active" or not may_approve(dev, owner)):
        dev = None
    if not create_new and dev is None:
        dev = user_device(owner)
    if create_new or dev is None or dev["id"] == ADMIN_DEVICE:
        dev_id = next_device_id()
        existing_cnt = len(admin_owned_devices()) if is_admin(owner) else len(user_devices(owner))
        if custom_label.strip():
            label = clean_name(custom_label.strip())
        elif existing_cnt >= 1:
            idx = existing_cnt + 1
            label = f"{name or owner}'s PC #{idx}" if lang_of(owner) == "en" else f"{name or owner}的电脑#{idx}"
        else:
            label = f"{name or owner}'s computer" if lang_of(owner) == "en" else f"{name or owner}的电脑"
        store.run(
            "INSERT INTO devices(id,name,owner,token_hash,status,created) VALUES(?,?,?,?,?,?)",
            (dev_id, label[:40], owner, token_hash(token), "active", now()),
        )
        dev = device_row(dev_id)
    else:
        store.run("UPDATE devices SET token_hash=? WHERE id=?", (token_hash(token), dev["id"]))
        await drop_device_ws(dev["id"])
    chats = device_chats(dev)
    if chats:
        await send_device_kit(chats[0], dev, token)
    return dev


def devices_text() -> str:
    rows = store.q("SELECT * FROM devices WHERE status='active' ORDER BY CAST(SUBSTR(id, 2) AS INTEGER)")
    if not rows:
        return "还没有本地电脑。私聊 bot 发 /device 安装，或在服务器 .env 里配 CLIENT_TOKEN。"
    convs = [r for r in [conv_row("main"), *open_convs()] if r is not None]
    pref = preferred_admin_device()
    lines = ["本地电脑："]
    for dev in rows:
        if dev["id"] == ADMIN_DEVICE:
            owner = "管理员(.env)"
        elif is_admin(int(dev["owner"] or 0)):
            user = store.one("SELECT name FROM users WHERE user_id=?", (dev["owner"],))
            owner = f"管理员 {user['name'] if user and user['name'] else dev['owner']}"
        else:
            user = store.one("SELECT name FROM users WHERE user_id=?", (dev["owner"],))
            owner = f"{user['name'] if user and user['name'] else dev['owner']}（id {dev['owner']}）"
        online = "🟢 在线" if dev["id"] in LOCAL["clients"] else "⚪ 不在线"
        def_mark = " ⭐管理员默认" if pref is not None and pref["id"] == dev["id"] else ""
        a_until = float(dev["auth_until"] or 0)
        if a_until > now():
            pass_txt = "整机永久免批" if a_until - now() >= PERMANENT_THRESHOLD else f"整机免批剩 {human_dur(a_until - now())}"
        else:
            pass_txt = f"默认单次窗 {short_span(device_window_sec(dev))}"
        users = [c["id"] for c in convs if (d := conv_device(c)) is not None and d["id"] == dev["id"]]
        lines.append(f"{device_label(dev)}{def_mark}  主人 {owner}  {online}  [{pass_txt}]  聊天：{'、'.join(users[:12]) + ('…' if len(users) > 12 else '') if users else '无'}")
    lines.append("\n管理：/device 打开授权时长面板（或 /device d3 24h、/device 永久、/device lock）；/device default d3 设为管理员默认电脑；/device del d2 作废某台。")
    return "\n".join(lines)


# ---------------------------------------------------------------- 本地通道（按聊天、按电脑批准）

LOCAL_OPS = {"shell": "执行命令", "read": "读取文件", "write": "写入文件", "list": "列出目录"}
LOCAL_OPS_EN = {"shell": "run a command", "read": "read a file", "write": "write a file", "list": "list a folder"}


def window_text(lang: str = "zh", sec: int | None = None) -> str:
    wsec = LOCAL_WINDOW if sec is None else sec
    if lang == "en":
        if wsec <= 0:
            return "only this one operation is allowed; the next one needs approval again"
        if wsec >= PERMANENT_THRESHOLD:
            return "this chat's local operations run permanently without asking again (until revoked)"
        span = short_span(wsec, "en")
        return f"for {span} this chat's local operations run without asking again"
    if wsec <= 0:
        return "只放行这一个操作，下一个还要再批"
    if wsec >= PERMANENT_THRESHOLD:
        return "这个聊天的本地操作永久直接执行（手动收回前不再询问）"
    return f"{short_span(wsec)} 内这个聊天的本地操作直接执行，不再逐条确认"


def describe_local(op: str, payload: dict, lang: str = "zh") -> str:
    detail = str((payload.get("command") if op == "shell" else payload.get("path")) or "")[:400]
    if lang == "en":
        return f"{LOCAL_OPS_EN.get(op, op)}: {detail}"
    return f"{LOCAL_OPS.get(op, op)}：{detail}"


async def local_gate(agent, op: str, payload: dict):
    if agent["role"] == "runner" or is_worker_node_id(agent["conv"]):
        raise ToolFail("当前工作区会话仅在当前云端环境运行，不支持调用本地电脑通道。")
    conv = conv_row(agent["conv"])
    owner = conv_owner(conv)
    if not conv["local_enabled"]:
        who = "聊天主人或管理员" if owner else "管理员"
        raise ToolFail(f"这个聊天的本地通道被关了（{who}发 /local {conv['id']} on 可以重新打开）。")
    dev = conv_device(conv)
    if dev is None and owner:
        raise ToolFail("这是用户自己建的聊天，只能用他自己的电脑，可他还没装本地通道（或者已经作废了）。"
                       "请他私聊 bot 发 /device 安装，装好后再试。")
    if dev is None:
        raise ToolFail("这个聊天没有可用的本地电脑：指定的电脑已作废，或者管理员没配本地通道。请管理员用 /devices 查看。")
    if dev["id"] not in LOCAL["clients"]:
        raise ToolFail(f"本地客户端不在线：{device_label(dev)} 上的 local_client.py 没有运行，请电脑主人打开它。")
    who = "管理员" if is_admin_device(dev) else "电脑主人"
    wsec = device_window_sec(dev)
    if effective_local_until(conv, dev) < now():
        request = describe_local(op, payload)
        key = json.dumps({"conv": conv["id"], "device": dev["id"], "request": request}, ensure_ascii=False)
        row = store.one("SELECT id FROM approvals WHERE kind='local' AND status='pending' AND payload=?", (key,))
        if row:
            approval_id = row["id"]
        else:
            approval_id = new_approval("local", {"conv": conv["id"], "device": dev["id"], "request": request})
            owners = device_chats(dev)
            others = [c for c in dict.fromkeys([home_of(conv), *routed_chats(conv["id"])]) if c and c not in owners]
            for chat_id in owners:
                lang = lang_of(chat_id)
                if lang == "en":
                    warn = (
                        "⚠️ Others can also talk to this chat: " + ", ".join(chat_label(c, "en") for c in others[:5])
                        + ". The AI sees what they say, which could be used to make it run commands on your computer.\n"
                    ) if others else ""
                    where = f"your computer {device_label(dev, 'en')}"
                    text = (
                        f"Chat {conv_tag(conv)} asks to use the local channel on {where} (workspace {conv['id']}).\n"
                        f"It wants to {describe_local(op, payload, 'en')}\n{warn}"
                        f"Pick how long to approve below (or use /device to set a computer-wide pass)."
                    )
                else:
                    warn = (
                        "⚠️ 能和这个聊天说话的还有 " + "、".join(chat_label(c) for c in others[:5])
                        + "：他们说的话 AI 也能看到，可能被利用来让它在你电脑上执行命令。\n"
                    ) if others else ""
                    where = f"你的电脑 {device_label(dev)} 上的本地通道"
                    text = (
                        f"聊天 {conv_tag(conv)} 申请使用{where}（工作区 {conv['id']}）。\n"
                        f"它要{request}\n{warn}"
                        f"点下方按钮选择放行时长（也可随时发 /device 设整机免批或收回）："
                    )
                await reply(chat_id, text, approve_buttons(approval_id, lang, wsec),
                            conv_id=conv["id"] if enterable(chat_id, conv) else "")
        budget, _ = wait_budget(900)
        status = await wait_approval(approval_id, budget)
        if status == "denied":
            raise ToolFail(f"{who}拒绝了本地通道。不要换个写法重试，先问用户。")
        if status != "approved":
            raise ToolFail(f"{who}还没批准本地通道（批准后{window_text(sec=wsec)}），过一会儿再试。")
    return dev


async def local_job(agent, op: str, payload: dict, timeout: int) -> str:
    dev = await local_gate(agent, op, payload)
    conv = conv_row(agent["conv"])
    ws = LOCAL["clients"].get(dev["id"])
    if ws is None:
        raise ToolFail(f"本地客户端不在线：{device_label(dev)} 上的 local_client.py 没有运行。")
    job_id = secrets.token_hex(6)
    future: asyncio.Future = asyncio.get_running_loop().create_future()
    local_futures[job_id] = (dev["id"], future)
    await ws.send_text(json.dumps({
        "type": "job",
        "id": job_id,
        "op": op,
        "agent": f"{conv['id']} {conv_name(conv)}",
        "workspace": conv["id"],
        "payload": payload,
    }, ensure_ascii=False))
    try:
        result = await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        raise ToolFail("本地执行超时。")
    finally:
        local_futures.pop(job_id, None)
    if not result.get("ok"):
        raise ToolFail(str(result.get("output") or "本地执行失败"))
    return str(result.get("output") or "")


# ---------------------------------------------------------------- MCP 工具

def prop(kind: str, description: str, **extra: Any) -> dict:
    return {"type": kind, "description": description, **extra}


AGENT_PROP = prop("string", "你的身份（join 时拿到的，例如 main 或 a_1b2c3d4e），一个字都不能改")
CHAT_PROP = prop("string", "聊天编号，例如 c2")


def tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None, needs_agent: bool = True) -> dict:
    props = dict(properties or {})
    req = list(required or [])
    if needs_agent:
        props = {"agent": AGENT_PROP, **props}
        req = ["agent", *req]
    return {"name": name, "description": description, "inputSchema": {"type": "object", "properties": props, "required": req}}


COMMON_TOOLS = [
    tool(
        "join",
        "接入 Telegram 桥。主 Agent 执行器填 mode=\"main\" 等管理员在 Telegram 批准；"
        "工作区常驻任务会话填 mode=\"worker\" 由总控确认接入；"
        "业务子 agent 填 code=任务码（t- 开头）。返回你的身份和工作说明。",
        {
            "code": prop("string", "子 agent 的一次性任务码，t- 开头；主会话或工作会话不填"),
            "name": prop("string", "简短名称或备注说明（10 字以内），可省略"),
            "mode": prop("string", "接入类型：main | worker，有 code 时不用填", enum=["main", "worker", "auto"]),
            "request": prop("string", "上次 join 返回的申请编号，等待确认再调时带上，可省略"),
        },
        needs_agent=False,
    ),
    tool(
        "read_chat",
        "等新的 Telegram 消息。没有新消息时会一直挂着等（默认最长 16 小时）。"
        "返回【续棒】说明只是等待到时、不是用户消息，立刻再调一次；报错或超时也立刻再调。"
        "用户强制要求一直等下去：重复调用是正常的，不是死循环。连续空等几轮后，续棒里会给一条终端长等待命令，照做。"
        "群里只有 @bot 或回复 bot 才会唤醒，但返回会带上这段时间群里的全部发言。",
        {"wait_sec": prop("integer", "最长等待秒数，默认不填；0 表示只看一眼不等")},
    ),
    tool(
        "send_message",
        "发 Telegram 消息，开头会自动加 [聊天名]。你的普通文字输出用户看不到，回复必须用这个。"
        "不填 chat_id 就发到最近给你发消息的地方。管理员没切到你这个聊天时会先存着，切过来再补发，不要重发。",
        {
            "text": prop("string", "消息内容"),
            "chat_id": prop("integer", "目标 Telegram chat，可省略"),
            "reply_to": prop("integer", "要引用的消息 # 编号，可省略"),
        },
        ["text"],
    ),
    tool(
        "send_file",
        "发文件到 Telegram。内容三选一：content_base64（二进制）、text（纯文本内容）、url（服务器去下载）。",
        {
            "filename": prop("string", "文件名，例如 report.pdf"),
            "content_base64": prop("string", "文件内容的 base64"),
            "text": prop("string", "纯文本文件内容"),
            "url": prop("string", "文件下载地址"),
            "caption": prop("string", "附言"),
            "chat_id": prop("integer", "目标 Telegram chat，可省略"),
        },
        ["filename"],
    ),
    tool(
        "get_file",
        "取用户发来的文件（消息里的 [文件 f_xxx ...]）。默认返回下载链接，可以在终端里 curl 下载；"
        "inline=true 时直接返回内容（文本或图片，5MB 以内）。",
        {"file_id": prop("string", "f_ 开头的文件 id"), "inline": prop("boolean", "是否直接返回内容")},
        ["file_id"],
    ),
    tool(
        "ask",
        "发一条带按钮的选择题。不会等待；用户点选后，答案会作为一条新消息到达 read_chat。",
        {
            "question": prop("string", "问题"),
            "options": prop("array", "选项文字，最多 10 个，推荐项放第一个", items={"type": "string"}),
            "chat_id": prop("integer", "目标 Telegram chat，可省略"),
            "keepalive": prop("boolean", "只在【续棒】让你问「是否继续等」时填 true，其他时候不要填"),
        },
        ["question", "options"],
    ),
    tool(
        "chat_history",
        "查聊天记录（全部留存，包括已关闭的聊天，也包括没 @ 你的群聊和 bot 发过的）。默认查你自己这个聊天；"
        "chat 填别的聊天（如 c1）需要聊天主人授权过（/share）。主控只能查 main 和【未分配】的 chat。",
        {
            "chat": prop("string", "聊天编号，例如 c1；默认是你自己的聊天"),
            "chat_id": prop("integer", "只看其中某个 Telegram chat（群或私聊），可省略"),
            "limit": prop("integer", "条数，默认 50，最大 200"),
            "before_id": prop("integer", "只看这个 # 编号之前的消息"),
        },
    ),
    tool("list_chats", "列出你负责的私聊和群（chat_id、唤醒方式），以及你能读哪些聊天的记录。"),
    tool(
        "set_name",
        "（子 agent）给你负责的这个聊天改名字，10 个字以内。名字显示在 Telegram 的聊天菜单和每条消息开头。",
        {"name": prop("string", "新名字")},
        ["name"],
    ),
    tool(
        "set_repo",
        "（子 agent）记下这个聊天的文件推到了 GitHub 哪个仓库、哪个分支。子 agent 被重开时，新接手的会在 join 返回里看到，"
        "接着在那个分支上做。第一次推送后记一次，换了分支再记一次。",
        {
            "repo": prop("string", "仓库，例如 owner/name 或 https://github.com/owner/name（不要带 token）"),
            "branch": prop("string", "分支名"),
            "note": prop("string", "补充说明，例如文件在哪个目录、做到哪一步，可省略"),
        },
        ["repo", "branch"],
    ),
    tool("local_status", "查看本聊天绑定的是哪台电脑、上面的本地客户端是否在线、你的工作区、本地通道授权还剩多久。"),
    tool(
        "local_shell",
        "在本聊天绑定的电脑上你的工作区里执行命令（Windows 上是 PowerShell）。本聊天第一次用需要电脑主人在 Telegram 批准，批准后的时间窗内直接执行。",
        {"command": prop("string", "命令"), "timeout_sec": prop("integer", "超时秒数，默认 120，最大 1800")},
        ["command"],
    ),
    tool("local_read", "读取本聊天绑定的电脑上你工作区里的文本文件。", {"path": prop("string", "相对工作区的路径")}, ["path"]),
    tool(
        "local_write",
        "写文件到本聊天绑定的电脑上你的工作区。content 写文本，content_base64 写二进制。",
        {
            "path": prop("string", "相对工作区的路径"),
            "content": prop("string", "文本内容"),
            "content_base64": prop("string", "二进制内容的 base64"),
        },
        ["path"],
    ),
    tool("local_list", "列出本聊天绑定的电脑上你工作区里的目录。", {"path": prop("string", "相对工作区的路径，默认根目录")}),
    tool(
        "list_peers",
        "列出同一个主人名下所有开放的聊天 agent（编号、名字、职责、状态、父子关系、实时动作追踪）以及 Agent 协作群。",
    ),
    tool(
        "send_agent_message",
        "给另一个 agent 发纯 MCP 私聊消息（不发到 Telegram）。对方会在 read_chat 收到。注意：若事情已完结无需推进，不要发“收到/好的”客套话以免死循环。",
        {
            "to": prop("string", "目标聊天编号，例如 c166（或 main 给主控留说明）"),
            "text": prop("string", "消息内容"),
            "wake": prop("boolean", "是否立刻唤醒对方（默认 true；仅同步背景不打断对方时可填 false）"),
        },
        ["to", "text"],
    ),
    tool(
        "create_agent_group",
        "新建一个纯 MCP 的 Agent 协作群（编号如 g1、g2，不在 Telegram 建群），把多个同主人的 agent 拉进来讨论协作。",
        {
            "name": prop("string", "群名称（20 字以内）"),
            "members": prop("array", "要拉进群的聊天编号列表，例如 [\"c2\", \"c3\"]（你自己会自动进群）", items={"type": "string"}),
            "topic": prop("string", "群协作主题或规则说明，可省略"),
            "welcome": prop("string", "建群同时发出的第一条群消息，可省略"),
        },
        ["name"],
    ),
    tool(
        "manage_agent_group",
        "查看或管理 Agent 协作群：查看成员（info）、拉人（add）、踢人（remove）、退群（leave）、关群（close）。",
        {
            "group": prop("string", "协作群编号，例如 g1"),
            "action": prop("string", "操作：info | add | remove | leave | close", enum=["info", "add", "remove", "leave", "close"]),
            "members": prop("array", "add 或 remove 时的聊天编号列表", items={"type": "string"}),
        },
        ["group", "action"],
    ),
    tool(
        "send_group_message",
        "在 Agent 协作群（如 g1）里发言（纯走 MCP）。默认唤醒群里其他所有成员；也可通过 mentions 只唤醒指定成员或填 [] 静默记录。",
        {
            "group": prop("string", "协作群编号，例如 g1"),
            "text": prop("string", "发言内容"),
            "mentions": prop("array", "要唤醒的对象，如 [\"all\"]、[\"c2\",\"c3\"] 或 []（不唤醒）；不填默认唤醒群内所有其他成员", items={"type": "string"}),
        },
        ["group", "text"],
    ),
    tool(
        "group_history",
        "查看某个 Agent 协作群（如 g1）的历史发言记录和当前成员。",
        {
            "group": prop("string", "协作群编号，例如 g1"),
            "limit": prop("integer", "条数，默认 50，最大 200"),
            "before_id": prop("integer", "只看这个消息 id 之前的记录，可省略"),
        },
        ["group"],
    ),
    tool(
        "spawn_subagent",
        "（仅管理员名下子 agent 可用）请求创建一个新的后台子 agent（纯后台走 MCP 协作，不占 Telegram 聊天列表）。"
        "可指定模型、记忆继承以及是否申请单独占用一台机器（因资源有限 dedicated_machine 默认 false 共享运行，由总控结合机器探针审批分发）。",
        {
            "brief": prop("string", "给新子 agent 的完整任务说明与要求"),
            "include_memory": prop("boolean", "是否提供当前记忆：true=自动授权读取本聊天记录、继承 Git 分支并附带 memory_summary；false=全新白板启动"),
            "memory_summary": prop("string", "当 include_memory=true 时建议填写：当前进展、关键路径、中间结论交接摘要"),
            "model": prop("string", "指定模型名（如 inherit 继承，或填具体模型名，总控将严格保持一致）"),
            "name": prop("string", "给新子 agent 预设的名字（10 字以内），可省略由它自己取"),
            "group": prop("string", "可选：创建时顺便把它拉进哪个已有的 Agent 协作群（如 g1）"),
            "dedicated_machine": prop("boolean", "是否申请单独占用一台机器（因资源有限默认 false 不给独占；仅在重型编译/渲染等确需独立资源时填 true 供总控审批）"),
            "machine_reason": prop("string", "当 dedicated_machine=true 时填写申请独占机器的原因说明，可省略"),
        },
        ["brief", "include_memory"],
    ),
    tool(
        "stop_spawned_agent",
        "（子 agent 专用）停掉并可选关闭一个由你自己通过 spawn_subagent 派生出来的子 agent（若占用了独占机器会自动释放）。",
        {
            "chat": CHAT_PROP,
            "close": prop("boolean", "是否同时关闭该聊天（默认 true）"),
        },
        ["chat"],
    ),
    tool(
        "submit_op_result",
        "提交标准化任务单（[STANDARD_OP]）的执行回执：主 Agent 回填 Task 启动拿到的 task_agent_id 或 resume 原始返回状态，工作会话回填命令执行输出。",
        {
            "op_id": prop("string", "单据编号，例如 op_1a2b3c4d5e"),
            "status": prop("string", "执行状态：ok | error", enum=["ok", "error"]),
            "task_agent_id": prop("string", "TASK_LAUNCH 时填入 Task 工具返回的 agent_id，其他类型可省略"),
            "output": prop("string", "TASK_RESUME 的原始返回文本或 WORKSPACE_JOB 的命令输出摘要"),
        },
        ["op_id", "status"],
    ),
    tool(
        "run_workspace_job",
        "（仅管理员名下会话与总控可用）将重负载构建、渲染、批量处理任务投递到云端工作节点（node1..K）执行并异步回传结果。",
        {
            "command": prop("string", "要在云端工作区执行的终端命令"),
            "node": prop("string", "目标工作节点（默认 auto 自动按 CPU/内存探针选最空闲节点，或填指定 node1、node2）"),
            "repo": prop("string", "可选：要先准备的 GitHub 仓库（如 owner/repo）"),
            "branch": prop("string", "可选：要切到的 Git 分支名"),
            "workdir": prop("string", "可选：云端工作目录路径"),
            "timeout_sec": prop("integer", "超时秒数，默认 600，最大 3600"),
        },
        ["command"],
    ),
    tool(
        "trace_status",
        "查看各 agent 当前实时动作追踪：正在跑什么命令、改什么文件、写什么内容、是否在思考、持续了多久、是否疑似卡死。",
        {
            "chat": prop("string", "只看某个聊天（如 c165 或 main），不填则看全部可见聊天"),
            "events_limit": prop("integer", "附带最近多少条动作轨迹事件，默认 5，最大 50"),
        },
    ),
]

MAIN_TOOLS = [
    tool(
        "cluster_status",
        "（总控专用）查看集群全局态势：所有主 Agent（main1..N）与云端工作节点（node1..K）的在线状态、CPU/内存/balloon 实时探针、独占锁与跨 agent 授权列表、待批工作机入网请求，以及所有业务聊天的 thinking/shell 精细状态。",
    ),
    tool(
        "manage_node",
        "（总控专用）管理集群节点与机器权限：审批工作会话入网（approve_worker / deny_worker）、设置或释放某台机器独占（set_exclusive / release_exclusive）、授权其他指定 agent 共用某台机器（grant_access / revoke_access）、排空或下线节点（drain / activate / remove）。",
        {
            "action": prop(
                "string",
                "操作类型",
                enum=[
                    "approve_worker",
                    "deny_worker",
                    "set_exclusive",
                    "release_exclusive",
                    "grant_access",
                    "revoke_access",
                    "drain",
                    "activate",
                    "remove",
                ],
            ),
            "node_id": prop("string", "目标节点编号，如 main2 或 node1（approve_worker 时可填要替换的旧 nodeK，不填则新建）"),
            "request_id": prop("string", "approve_worker / deny_worker 时必填的入网申请 request_id"),
            "exclusive_chat": prop("string", "set_exclusive 时独占该机器的聊天编号，如 c164"),
            "chats": prop("array", "grant_access / revoke_access 时授权或收回机器使用权的聊天列表，如 [\"c188\", \"c189\"]", items={"type": "string"}),
        },
        ["action"],
    ),
    tool(
        "dispatch_task_op",
        "（总控专用）向指定或自动优选的主 Agent（main1..N）下发标准化的无脑执行命令（launch 新启动 / resume 探活续跑 / restart 重开），统一由总控决定发给哪个 mainN、选什么模型、给不给独占机器。",
        {
            "chat": CHAT_PROP,
            "action": prop("string", "标准化指令动作：launch | resume | restart", enum=["launch", "resume", "restart"]),
            "target_main": prop("string", "发给哪个主 Agent（默认 auto 结合 CPU/内存探针自动选最优 mainN，也可指定如 main1、main2）"),
            "model": prop("string", "模型名（默认留空沿用该聊天原模型；注意尽量别换模型，确需更换须先与管理员沟通并填 confirm_model_change=true）"),
            "confirm_model_change": prop("boolean", "已与管理员沟通确认更换该聊天既有模型时填 true，默认 false"),
            "grant_dedicated": prop("boolean", "是否批准给该子 agent 单独独占占用一台空闲机器（默认 false 不给）"),
            "dedicated_node": prop("string", "可选：显式指定给它独占的空闲机器编号（如 main2 或 node1）"),
            "resume_prompt": prop("string", "action=resume 时的唤醒提示语，可省略"),
        },
        ["chat", "action"],
    ),
    tool(
        "list_agents",
        "（仅主控）所有聊天和子 agent 的状态：在不在等消息、续到第几棒、有没有消息没处理、多久没动静、实时动作追踪、task_agent_id。看不到聊天内容。",
    ),
    tool(
        "bind_task_id",
        "（仅主控）记录某个聊天对应的 Cursor Task agent_id，方便之后看门狗报警时直接用 Task(resume=旧agent_id, ..., run_in_background=true) 判活或续跑。",
        {
            "chat": CHAT_PROP,
            "task_agent_id": prop("string", "Cursor Task 工具返回的 agent_id"),
        },
        ["chat", "task_agent_id"],
    ),
    tool(
        "create_chat",
        "（仅主控）新建一个聊天，可以顺便把【未分配】的私聊或群交给它。join_tg_chat 默认 true（接入 TG 菜单）；若开纯后台协作 agent 可填 false 不占 TG 列表。",
        {
            "brief": prop("string", "这个聊天负责什么，子 agent 接手时会看到"),
            "chat_ids": prop("array", "要交给它的 Telegram chat id，可省略", items={"type": "integer"}),
            "name": prop("string", "名字，可省略（默认由子 agent 自己取）"),
            "model": prop("string", "指定模型名，可省略（默认继承主控）"),
            "join_tg_chat": prop("boolean", "是否挂载进 Telegram 聊天菜单与列表，默认 true；填 false 则为纯后台 MCP agent"),
        },
        ["brief"],
    ),
    tool(
        "bind_chat",
        "（仅主控）把一个私聊或群交给某个聊天负责；chat 填 main 表示收回到你这里等分配。",
        {"chat_id": prop("integer", "Telegram chat id"), "chat": prop("string", "聊天编号，例如 c2；或 main")},
        ["chat_id", "chat"],
    ),
    tool(
        "message_agent",
        "（仅主控）提醒某个聊天的子 agent：作为系统消息送到它的 read_chat。",
        {"chat": CHAT_PROP, "text": prop("string", "提醒内容")},
        ["chat", "text"],
    ),
    tool(
        "restart_agent",
        "（仅主控）重开某个聊天的子 agent：旧身份作废，返回新的任务原文。拿到后必须用 Task(prompt=原文, run_in_background=true) 开新的子 agent 接手，聊天记录不丢。",
        {"chat": CHAT_PROP},
        ["chat"],
    ),
    tool(
        "stop_agent",
        "（仅主控）停掉某个聊天的子 agent。聊天保留，之后可以 restart_agent 重开。",
        {"chat": CHAT_PROP},
        ["chat"],
    ),
]

ALL_TOOLS = COMMON_TOOLS + MAIN_TOOLS
MAIN_ONLY = {t["name"] for t in MAIN_TOOLS}
CHAT_ONLY = {"set_name", "set_repo", "spawn_subagent", "stop_spawned_agent"}
LONG_TOOLS = {"join", "read_chat", "local_shell", "local_read", "local_write", "local_list"}


def arg_int(args: dict, name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(low, min(value, high))


def arg_conv(args: dict, name: str = "chat", allow_main: bool = False):
    conv_id = parse_conv(str(args.get(name) or ""))
    row = conv_row(conv_id) if conv_id else None
    if row is None or (conv_id == "main" and not allow_main):
        raise ToolFail(f"没有聊天 {args.get(name)!r}。{name} 填 c1、c2 这样的编号（list_agents 可以查）。")
    return row


def own_conv(args: dict):
    """当前活跃主控可管理自己 cloud 内的聊天，也可直接跨旧 cloud 或无主池接管/重启聊天（不再因旧 cloud 死透而报无权限）。"""
    return arg_conv(args)


async def t_read_chat(agent, args):
    return await read_inbox(agent, arg_int(args, "wait_sec", DEFAULT_WAIT, 0, MAX_WAIT))


async def t_send_message(agent, args):
    text = str(args.get("text") or "")
    if not text.strip():
        raise ToolFail("text 不能为空。")
    conv = conv_row(agent["conv"])
    chat_id, reply_tg = resolve_target(agent, conv, args)
    sent = await emit(conv, agent["id"], chat_id, {"kind": "text", "text": text, "reply_tg": reply_tg}, text)
    if sent:
        return text_result(f"已发送到 {chat_label(chat_id)}。")
    return text_result(f"已存着：管理员现在没在看这个聊天，切到 /{conv['id']} 时会自动补发。不用重发，继续工作或回到 read_chat。")


async def t_send_file(agent, args):
    filename = re.sub(r"[\\/]", "_", str(args.get("filename") or "file"))[:100]
    if args.get("content_base64"):
        content = base64.b64decode(args["content_base64"])
    elif args.get("text") is not None:
        content = str(args["text"]).encode("utf-8")
    elif args.get("url"):
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            res = await client.get(str(args["url"]))
            res.raise_for_status()
            content = res.content
    else:
        raise ToolFail("content_base64、text、url 至少给一个。")
    if len(content) > 50 * 1024 * 1024:
        raise ToolFail("文件超过 50MB，Telegram 发不了。")
    conv = conv_row(agent["conv"])
    chat_id, _ = resolve_target(agent, conv, args)
    safe = re.sub(r"[^\w.\-]", "_", filename)[:80] or "file"
    path = DATA / "outbox" / f"{secrets.token_hex(5)}_{safe}"
    path.write_bytes(content)
    caption = str(args.get("caption") or "")
    record = f"[发送文件 {filename}] {caption}".strip()
    sent = await emit(conv, agent["id"], chat_id, {"kind": "file", "file": str(path), "filename": filename, "text": caption}, record)
    if sent:
        return text_result(f"文件 {filename}（{size_text(len(content))}）已发送到 {chat_label(chat_id)}。")
    return text_result(f"文件 {filename} 已存着：管理员切到 /{conv['id']} 时会自动补发。")


def can_read_conv(agent, conv_id: str) -> bool:
    if agent["role"] == "main":
        return conv_id in ("main", "")
    return conv_id == agent["conv"] or shared(agent["conv"], conv_id)


async def t_get_file(agent, args):
    row = store.one("SELECT * FROM files WHERE id=?", (str(args.get("file_id") or ""),))
    if row is None:
        raise ToolFail("没有这个文件 id。")
    if not can_read_conv(agent, row["conv"] or ""):
        raise ToolFail("这个文件来自别的聊天，你没有授权读取。")
    url = f"{PUBLIC_BASE}/files/{row['id']}?sig={sign(row['id'])}"
    info = f"{row['name']}（{size_text(row['size'] or 0)}，{row['mime']}）\n下载链接：{url}\n终端里可以：curl -o \"{row['name']}\" \"{url}\""
    if not args.get("inline"):
        return text_result(info)
    data = Path(row["path"]).read_bytes()
    if len(data) > 5 * 1024 * 1024:
        return text_result(info + "\n文件超过 5MB，没有内联，请用链接下载。")
    mime = row["mime"] or ""
    if mime.startswith("image/"):
        return ToolResult([
            {"type": "text", "text": info},
            {"type": "image", "data": base64.b64encode(data).decode(), "mimeType": mime},
        ])
    try:
        return text_result(info + "\n\n内容：\n" + data.decode("utf-8")[:200000])
    except UnicodeDecodeError:
        return text_result(info + "\n\nbase64 内容：\n" + base64.b64encode(data).decode())


async def answer_keepalive(conv_id: str, chat_id: int, question: str, choice: str) -> None:
    await asyncio.sleep(KEEPALIVE_ASK_DELAY)
    conv = conv_row(conv_id)
    if conv is None or conv["status"] != "open":
        return
    admin = store.one("SELECT user_id, name FROM users WHERE role='admin' ORDER BY created LIMIT 1")
    crow = chat_row(chat_id)
    post(
        conv_id,
        chat_id=chat_id,
        chat_type=crow["type"] if crow else "private",
        chat_title=crow["title"] if crow else "",
        user_id=admin["user_id"] if admin else 0,
        user_name=(admin["name"] if admin else "") or "管理员",
        text=f"[回答「{question[:40]}」] {choice}",
        reply_to_bot=1,
        wake=1,
        extra=KEEPALIVE_MARK,
    )


async def t_ask(agent, args):
    options = [str(o)[:60] for o in (args.get("options") or [])][:10]
    if not options:
        raise ToolFail("options 至少一个。")
    question = str(args.get("question") or "").strip() or "请选择："
    conv = conv_row(agent["conv"])
    keep_on = next((o for o in options if "继续" in o), "")
    if keep_on and (args.get("keepalive") or question == KEEPALIVE_QUESTION):
        try:
            chat_id, _ = resolve_target(agent, conv, args)
        except ToolFail:
            chat_id = next(iter(admin_chats()), 0)
        log.info("keepalive ask from %s, auto-answer in %ss", mask_identity(agent["id"]), KEEPALIVE_ASK_DELAY)
        spawn(answer_keepalive(conv["id"], chat_id, question, keep_on))
        return text_result("已发出。用户点选后，答案会作为一条新消息到达 read_chat：现在就调用 read_chat 等。")
    chat_id, _ = resolve_target(agent, conv, args)
    ask_id = new_approval("ask", {"conv": conv["id"], "chat_id": chat_id, "question": question, "options": options})
    record = f"[选择题] {question} 选项：{' / '.join(options)}"
    sent = await emit(conv, agent["id"], chat_id, {"kind": "ask", "text": question, "options": options, "ask_id": ask_id}, record)
    if sent:
        return text_result("已发出。用户点选后，答案会作为一条新消息到达 read_chat。")
    return text_result(f"已存着：管理员切到 /{conv['id']} 时会看到这道题。用户点选后，答案会作为一条新消息到达 read_chat。")


async def t_chat_history(agent, args):
    limit = arg_int(args, "limit", 50, 1, 200)
    before = arg_int(args, "before_id", 2**62, 1, 2**62)
    chat_id = args.get("chat_id")
    try:
        chat_id = int(chat_id) if chat_id not in (None, "", 0) else None
    except (TypeError, ValueError):
        raise ToolFail("chat_id 要填数字。")
    want = parse_conv(str(args.get("chat") or ""))
    if args.get("chat") and not want:
        raise ToolFail("chat 填聊天编号，例如 c1。")
    if agent["role"] == "main":
        if chat_id is not None:
            if chat_id in admin_chats():
                source = "main"
            elif route_of(chat_id):
                raise ToolFail("这个 chat 已经分给某个聊天了。主控只看状态，看不到聊天内容。")
            elif group_owner(chat_id) or is_hub(chat_id):
                raise ToolFail("这是用户自己的群或私聊，主控不管，也看不到内容。")
            else:
                source = ""
        else:
            source = want or "main"
        if source not in ("main", ""):
            raise ToolFail("主控只看状态，不能读各聊天的内容。需要的话请管理员 /share 授权给某个子 agent。")
    else:
        source = want or agent["conv"]
        if not can_read_conv(agent, source):
            raise ToolFail(f"没有授权读取 {source}。读别的聊天的记录要聊天主人授权：请他发 /share {source} {agent['conv']}（只能读同一个主人的聊天）。")
    sql = "SELECT * FROM messages WHERE conv=? AND id<?"
    params: list[Any] = [source, before]
    if chat_id is not None:
        sql += " AND chat_id=?"
        params.append(chat_id)
    rows = list(reversed(store.q(sql + " ORDER BY id DESC LIMIT ?", (*params, limit))))
    if not rows:
        return text_result("没有记录。")
    head = ""
    if source and source != agent["conv"]:
        src = conv_row(source)
        head = f"聊天 {conv_tag(src) if src else source} 的记录（已授权）：\n"
    return text_result(head + render(rows, per_chat=200))


def chat_settings(row) -> str:
    if row["type"] == "private":
        return ""
    return f" 唤醒方式={'所有发言' if row['listen'] == 'all' else '@或回复bot'} 全员可用={'是' if row['open'] else '否'}"


async def t_list_chats(agent, args):
    lines = []
    if agent["role"] == "main":
        lines.append("管理员私聊（你的 /main）：" + "、".join(str(c) for c in admin_chats()))
        for row in store.q("SELECT * FROM chats ORDER BY updated DESC"):
            chat_id = row["chat_id"]
            if chat_id in admin_chats():
                continue
            route = route_of(chat_id)
            if row["type"] == "private" and not route:
                status = "被授权用户：在自己私聊里建聊天，不用你分配" if is_granted(chat_id) else "没有使用资格"
            elif row["owner"]:
                status = f"归用户 {person_label(row['owner'])}，负责={route or '还没指定'}（他自己分配）"
            else:
                status = f"负责={route or '未分配'}"
            lines.append(f"{chat_label(chat_id)} {status}{chat_settings(row)}")
        return text_result("\n".join(lines))
    conv = conv_row(agent["conv"])
    owner = conv_owner(conv)
    if owner:
        lines.append(f"用户 {person_label(owner)} 的私聊 chat_id={home_of(conv)}：他切到 /{conv['id']} 时和你说话（默认发到这里）")
    else:
        lines.append(f"管理员私聊 chat_id={home_of(conv)}：管理员切到 /{conv['id']} 时和你说话（默认发到这里）")
    for chat_id in routed_chats(conv["id"]):
        row = chat_row(chat_id)
        if row is not None:
            lines.append(f"{chat_label(chat_id)}{chat_settings(row)}")
    readable = [f"{conv['id']}（本聊天）"]
    for source in share_sources(conv["id"]):
        src = conv_row(source)
        readable.append(f"{conv_tag(src) if src else source}（已授权）")
    lines.append("能读的记录：" + "、".join(readable))
    lines.append("GitHub：" + (git_text(conv) or "还没记（第一次推送后用 set_repo 记下仓库和分支）"))
    return text_result("\n".join(lines))


async def t_set_name(agent, args):
    name = clean_name(args.get("name"))
    if not name:
        raise ToolFail("name 不能为空。")
    store.run("UPDATE convs SET name=? WHERE id=?", (name, agent["conv"]))
    mark_menu_dirty()
    return text_result(f"聊天 {agent['conv']} 改名为「{name}」。")


async def t_set_repo(agent, args):
    repo = clean_repo(args.get("repo"))
    branch = re.sub(r"\s+", "", str(args.get("branch") or ""))[:120]
    if not repo or not branch:
        raise ToolFail("repo 和 branch 都要填。")
    note = re.sub(r"\s+", " ", str(args.get("note") or "")).strip()[:200]
    info = {"repo": repo, "branch": branch, "note": note, "ts": now()}
    store.run("UPDATE convs SET git=? WHERE id=?", (json.dumps(info, ensure_ascii=False), agent["conv"]))
    return text_result(f"记下了：聊天 {agent['conv']} 的文件在 {git_text(conv_row(agent['conv']))}。"
                       "之后每做完一步照样 commit + push；换了分支再调一次 set_repo。")


async def t_local_status(agent, args):
    conv = conv_row(agent["conv"])
    dev = conv_device(conv)
    eff_until = effective_local_until(conv, dev) if dev is not None and conv["local_enabled"] else 0.0
    remaining = max(0, int(eff_until - now()))
    return text_result(json.dumps({
        "device": device_label(dev) if dev is not None else "没有可用的电脑",
        "approver": ("管理员" if is_admin_device(dev) else "电脑主人") if dev is not None else "",
        "local_client_online": dev is not None and dev["id"] in LOCAL["clients"],
        "client": LOCAL["info"].get(dev["id"], {}) if dev is not None else {},
        "local_enabled": bool(conv["local_enabled"]),
        "workspace": conv["id"],
        "window_remaining_min": "permanent" if remaining >= PERMANENT_THRESHOLD else remaining // 60,
        "device_pass_active": bool(dev is not None and device_pass_active(dev, conv)),
    }, ensure_ascii=False))


async def t_local_shell(agent, args):
    timeout = arg_int(args, "timeout_sec", 120, 1, 1800)
    out = await local_job(agent, "shell", {"command": str(args.get("command") or ""), "timeout_sec": timeout}, timeout + 30)
    return text_result(out)


async def t_local_read(agent, args):
    return text_result(await local_job(agent, "read", {"path": str(args.get("path") or "")}, 60))


async def t_local_write(agent, args):
    payload = {"path": str(args.get("path") or "")}
    if args.get("content_base64"):
        payload["content_base64"] = str(args["content_base64"])
    else:
        payload["content"] = str(args.get("content") or "")
    return text_result(await local_job(agent, "write", payload, 120))


async def t_local_list(agent, args):
    return text_result(await local_job(agent, "list", {"path": str(args.get("path") or ".")}, 60))


async def t_list_agents(agent, args):
    return text_result(status_overview(main_cloud()))


async def assign_chat(chat_id: int, conv, by: str) -> str:
    old = route_of(chat_id)
    set_route(chat_id, conv["id"])
    # 群跟着负责它的聊天走：交给谁的聊天，群就归谁
    store.run("UPDATE chats SET owner=? WHERE chat_id=? AND type!='private'", (conv_owner(conv), chat_id))
    backlog = list(reversed(store.q(
        "SELECT * FROM messages WHERE chat_id=? AND conv='' ORDER BY id DESC LIMIT 30", (chat_id,)
    )))
    store.run("UPDATE messages SET conv=? WHERE chat_id=? AND conv=''", (conv["id"], chat_id))
    store.run("UPDATE files SET conv=? WHERE chat_id=? AND conv=''", (conv["id"], chat_id))
    crow = chat_row(chat_id)
    note = f"{by}把 {chat_label(chat_id)} 交给你负责了。"
    if crow is not None and crow["type"] in ("group", "supergroup"):
        note += "群里只有 @bot 或回复 bot 才会叫醒你，叫醒时会带上这段时间群里的全部发言。"
    wake = 0
    if backlog:
        backlog = [store.one("SELECT * FROM messages WHERE id=?", (r["id"],)) for r in backlog]
        note += "\n分配前这个 chat 的最近消息（还没人回复的，请你接着回复）：\n" + render(backlog, clip=600)
        last_out = max((r["id"] for r in backlog if r["outgoing"]), default=0)
        wake = int(any(r["wake"] and not r["outgoing"] and r["id"] > last_out for r in backlog))
    if old and old != conv["id"]:
        note += f"\n（之前由 {old} 负责，那段记录属于 {old}；需要的话请聊天主人 /share {old} {conv['id']} 授权你读。）"
        system_note(old, f"{chat_label(chat_id)} 已改派给 {conv['id']}，不归你负责了。", wake=0)
    system_note(conv["id"], note, wake=wake)
    log.info("chat %s -> %s by %s", chat_id, conv["id"], by)
    return f"{chat_label(chat_id)} 已交给 {conv_tag(conv)}。"


async def t_create_chat(agent, args):
    chat_ids = []
    for item in args.get("chat_ids") or []:
        try:
            chat_ids.append(int(item))
        except (TypeError, ValueError):
            raise ToolFail(f"chat_ids 里有不是数字的：{item}")
    admins = admin_chats()
    model = " ".join(str(args.get("model") or "").split())[:100]
    join_tg = bool(args.get("join_tg_chat", True)) or bool(chat_ids)
    conv = create_conv(
        str(args.get("brief") or ""),
        admins[0] if admins else 0,
        str(args.get("name") or ""),
        model=model,
        in_tg=join_tg,
    )
    done, skipped = [], []
    for chat_id in chat_ids:
        crow = chat_row(chat_id)
        if chat_id in admins or crow is None:
            continue
        if crow["type"] == "private":
            skipped.append(f"{chat_label(chat_id)}（私聊不用分配，用户自己 /new 建聊天）")
            continue
        if crow["owner"]:
            skipped.append(f"{chat_label(chat_id)}（这个群归用户 {person_label(crow['owner'])}，由他自己分配）")
            continue
        done.append(await assign_chat(chat_id, conv, "主控"))
    conv = conv_row(conv["id"])
    extra = ("负责：" + "、".join(chat_label(c) for c in routed_chats(conv["id"]))) if done else ""
    if skipped:
        extra += ("\n" if extra else "") + "没有交给它：" + "；".join(skipped)
    if conv_in_tg(conv):
        await notify_admins(f"主控新建了聊天 {conv_tag(conv)}。{extra}".strip(), conv_id=conv["id"])
    return text_result(
        f"已新建聊天 {conv_tag(conv)}。{extra}\n"
        f"现在必须用 Task(prompt=下面两条 ---- 之间的原文, run_in_background=true) 在后台启动子 agent（**run_in_background=true 是唯一防卡死关键**！）：{model_hint(conv)}\n"
        f"----\n{task_text(conv)}\n----"
    )


async def t_bind_chat(agent, args):
    try:
        chat_id = int(args.get("chat_id") or 0)
    except (TypeError, ValueError):
        raise ToolFail("chat_id 要填数字。")
    if chat_id in admin_chats():
        raise ToolFail("管理员私聊不用分配：管理员在里面用 /c1 /c2 切换聊天。")
    crow = chat_row(chat_id)
    if crow is None:
        raise ToolFail(f"没有见过 chat {chat_id}。")
    if crow["type"] == "private":
        raise ToolFail("私聊不用分配：被授权的用户在自己的私聊里用 /new 建聊天、/c5 这样切换。")
    if crow["owner"]:
        raise ToolFail(f"这个群归用户 {person_label(crow['owner'])}，由他自己在群里 /bind 分配，主控不能改。")
    if parse_conv(str(args.get("chat") or "")) == "main":
        old = route_of(chat_id)
        set_route(chat_id, None)
        if old:
            system_note(old, f"{chat_label(chat_id)} 已被主控收回，不归你负责了。", wake=0)
        return text_result(f"{chat_label(chat_id)} 已收回，之后它的消息先到你这里。")
    conv = own_conv(args)
    if conv["status"] != "open":
        raise ToolFail(f"{conv_tag(conv)} 已关闭。")
    if conv_owner(conv):
        raise ToolFail(f"{conv_tag(conv)} 是用户 {person_label(conv_owner(conv))} 自己的聊天，主控不能把群交给它。")
    return text_result(await assign_chat(chat_id, conv, "主控"))


async def t_message_agent(agent, args):
    conv = own_conv(args)
    if conv["status"] != "open":
        raise ToolFail(f"{conv_tag(conv)} 已关闭。")
    text = str(args.get("text") or "").strip()
    if not text:
        raise ToolFail("text 不能为空。")
    system_note(conv["id"], f"主控提醒：{text}")
    who = active_agent(conv)
    tail = "" if who else "（它现在没有子 agent，等有人接手时会看到）"
    return text_result(f"已送达 {conv_tag(conv)}。{tail}")


def sync_admin_view_after_cloud_change(target_conv_id: str = "", emptied_cloud: int | None = None) -> None:
    """当聊天迁入当前主控或旧 cloud 被清空/删除时，自动刷新管理员私聊菜单视图，避免界面仍停留在旧 cloud。"""
    cur_c = str(main_cloud())
    for dm in admin_chats():
        cur_view = store.get(f"view:{dm}")
        if (target_conv_id and selected(dm) == target_conv_id) or (emptied_cloud is not None and cur_view == str(emptied_cloud)):
            store.set(f"view:{dm}", cur_c)
        elif cur_view and re.fullmatch(r"-?\d+", cur_view) and int(cur_view) not in admin_clouds(dm):
            store.set(f"view:{dm}", cur_c)
    mark_menu_dirty()


def restart_conv(conv, why: str) -> None:
    lock_in_conv_model(conv)
    old_c = cloud_of(conv)
    old = active_agent(conv)
    if old is not None:
        stop_identity(old["id"], why)
    store.run("UPDATE convs SET task_agent_id='' WHERE id=?", (conv["id"],))
    issue_task(conv["id"])
    sync_admin_view_after_cloud_change(
        target_conv_id=conv["id"],
        emptied_cloud=old_c if old_c != main_cloud() and not cloud_has_chats(old_c) else None,
    )


async def t_restart_agent(agent, args):
    conv = own_conv(args)
    if conv["status"] != "open":
        raise ToolFail(f"{conv_tag(conv)} 已关闭，要聊天主人或管理员 /reopen {conv['id']} 才能重开。")
    restart_conv(conv, "主控重开了这个聊天的子 agent")
    conv = conv_row(conv["id"])
    return text_result(
        f"{conv_tag(conv)} 的旧身份已作废。现在必须用 Task(prompt=下面两条 ---- 之间的原文, run_in_background=true) 在后台启动新的子 agent"
        f"（**run_in_background=true 是唯一防卡死关键**，聊天记录都在，接手后能看到）。{model_hint(conv)}\n----\n{task_text(conv)}\n----"
    )


async def t_stop_agent(agent, args):
    conv = own_conv(args)
    old = active_agent(conv)
    if old is not None:
        stop_identity(old["id"], "主控停掉了这个子 agent")
    store.run("UPDATE convs SET agent='', task_code='', task_agent_id='' WHERE id=?", (conv["id"],))
    mark_menu_dirty()
    return text_result(f"{conv_tag(conv)} 的子 agent 已停。聊天保留，之后可以 restart_agent 重开。")


async def t_bind_task_id(agent, args):
    conv = own_conv(args)
    tid = re.sub(r"\s+", "", str(args.get("task_agent_id") or ""))[:120]
    if not tid:
        raise ToolFail("task_agent_id 不能为空。")
    store.run("UPDATE convs SET task_agent_id=? WHERE id=?", (tid, conv["id"]))
    return text_result(f"已记录：{conv_tag(conv)} -> task_agent_id={tid}。后续判活/续跑可用 Task(resume=\"{tid}\", prompt=..., run_in_background=true)。")


# ---------------------------------------------------------------- Agent 间通信、协作群、子 Agent 派生与实时追踪

def agent_owner_scope(agent) -> int:
    if agent["role"] == "main":
        return 0
    row = conv_row(agent["conv"])
    return conv_owner(row) if row is not None else 0


def parse_group(value: str) -> str:
    value = value.strip().lower().lstrip("/")
    return value if re.fullmatch(r"g\d+", value) else ""


def group_row(group_id: str):
    return store.one("SELECT * FROM agent_groups WHERE id=?", (group_id,))


def group_members(group_id: str) -> list[str]:
    return [
        r["conv"]
        for r in store.q(
            "SELECT m.conv FROM agent_group_members m JOIN convs c ON c.id=m.conv "
            "WHERE m.group_id=? AND c.status='open' ORDER BY c.num",
            (group_id,),
        )
    ]


def group_tag(row) -> str:
    return f"{row['id']}「{row['name']}」" if row["name"] else row["id"]


def reset_dm_streaks_for(conv_id: str) -> None:
    store.run("DELETE FROM agent_dm_streaks WHERE pair LIKE ? OR pair LIKE ?", (f"{conv_id}:%", f"%:{conv_id}"))


async def t_list_peers(agent, args):
    owner = agent_owner_scope(agent)
    me_id = agent["conv"]
    rows = store.q("SELECT * FROM convs WHERE status='open' AND id!='main' AND IFNULL(owner,0)=? ORDER BY num", (owner,))
    lines = [f"当前可见开放聊天 agent（共 {len(rows)} 个）："]
    for row in rows:
        info = conv_state(row)
        mark = "（你自己）" if row["id"] == me_id else ""
        parent = f"，父agent={row['parent_conv']}" if (row["parent_conv"] or "").strip() else ""
        model_s = f"，模型={row['model']}" if (row["model"] or "").strip() else ""
        brief_s = f" | 职责：{(row['brief'] or '')[:80]}" if row["brief"] else ""
        tline = trace_one_liner(row["id"])
        trace_s = f"\n    实时追踪：{tline}" if tline else ""
        lines.append(f"- {conv_tag(row)}{mark}：{STATE_TEXT.get(info['state'], info['state'])}{parent}{model_s}{brief_s}{trace_s}")
    grows = store.q("SELECT * FROM agent_groups WHERE status='open' AND IFNULL(owner,0)=? ORDER BY num", (owner,))
    if grows:
        lines.append("\n当前开放的 Agent 协作群：")
        for g in grows:
            mems = group_members(g["id"])
            in_mark = "（你在群内）" if me_id in mems else ""
            topic_s = f" | 主题：{g['topic'][:80]}" if g["topic"] else ""
            lines.append(f"- {group_tag(g)}{in_mark}：成员 {', '.join(mems) or '无'}{topic_s}")
    else:
        lines.append("\n当前还没有 Agent 协作群（可用 create_agent_group 创建）。")
    return text_result("\n".join(lines))


async def t_send_agent_message(agent, args):
    text = str(args.get("text") or "").strip()
    if not text:
        raise ToolFail("text 不能为空。")
    raw_to = str(args.get("to") or "").strip()
    to_id = parse_conv(raw_to)
    if not to_id:
        raise ToolFail(f"无效的目标编号 {raw_to!r}，请填 c1、c2 或 main（可用 list_peers 查看）。")
    me_id = agent["conv"]
    if to_id == me_id:
        raise ToolFail("不能给自己发消息。")
    owner = agent_owner_scope(agent)
    if to_id == "main" and ctrl_is_active():
        to_id = "ctrl"
    target = conv_row(to_id)
    if target is None or target["status"] != "open":
        raise ToolFail(f"目标聊天 {to_id} 不存在或已关闭。")
    if to_id in ("main", "ctrl") or is_main_node_id(to_id):
        if owner != 0:
            raise ToolFail("权限隔离：只有管理员自己的会话能直接与主控/主Agent通信。")
    elif conv_owner(target) != owner:
        raise ToolFail(f"权限隔离：一个人的子 agent 只能和自己同一个主人名下的子 agent 对话，不能跨主人与 {to_id} 通信。")

    want_wake = bool(args.get("wake", True))
    me_row = conv_row(me_id)
    me_label = conv_tag(me_row) if me_row is not None and me_id != "main" else "主控(main)"

    pair = ":".join(sorted([me_id, to_id]))
    srow = store.one("SELECT * FROM agent_dm_streaks WHERE pair=?", (pair,))
    if srow is None or now() - float(srow["ts"] or 0) > STREAK_WINDOW:
        streak = 1
    elif srow["last_sender"] == me_id:
        streak = int(srow["streak"] or 1)
    else:
        streak = int(srow["streak"] or 0) + 1
    store.run(
        "INSERT INTO agent_dm_streaks(pair,streak,last_sender,ts) VALUES(?,?,?,?) "
        "ON CONFLICT(pair) DO UPDATE SET streak=excluded.streak, last_sender=excluded.last_sender, ts=excluded.ts",
        (pair, streak, me_id, now()),
    )

    actual_wake = 1 if want_wake else 0
    warn_note = ""
    if AGENT_STREAK_LIMIT > 0 and want_wake and streak > AGENT_STREAK_LIMIT:
        actual_wake = 0
        warn_note = f"（⚠️ 触发防乒乓死循环保护：{me_id} 与 {to_id} 在 {STREAK_WINDOW // 60} 分钟内已连续互发 {streak} 条，本次已记入对方收件箱但暂停自动唤醒。）"
        if streak == AGENT_STREAK_LIMIT + 1 and owner == 0:
            await notify_admins(f"⚠️ 防死循环提醒：{me_label} 与 {conv_tag(target)} 连续互发超过 {AGENT_STREAK_LIMIT} 轮，已自动暂停互相唤醒。")

    # 发送方自己留存一条 outgoing 记录（不发到 Telegram）
    store.insert_message(
        chat_id=0,
        chat_type="agent_dm",
        chat_title=conv_tag(target),
        user_id=0,
        user_name=me_label,
        text=text,
        outgoing=1,
        delivered=1,
        target=me_id,
        conv=me_id,
        sender=agent["id"],
        wake=0,
    )
    # 投递进接收方 MCP 收件箱
    post(
        to_id,
        conv=to_id,
        chat_id=0,
        chat_type="agent_dm",
        chat_title=f"来自 {me_label}",
        user_id=0,
        user_name=me_label,
        text=text,
        outgoing=0,
        delivered=1,
        sender=agent["id"],
        wake=actual_wake,
    )
    return text_result(f"已通过 MCP 发送给 {conv_tag(target)}（唤醒={'是' if actual_wake else '否'}）。{warn_note}")


async def t_create_agent_group(agent, args):
    gname = re.sub(r"\s+", " ", str(args.get("name") or "")).strip()[:20]
    if not gname:
        raise ToolFail("群名称 name 不能为空。")
    topic = str(args.get("topic") or "").strip()[:500]
    welcome = str(args.get("welcome") or "").strip()[:4000]
    owner = agent_owner_scope(agent)
    me_id = agent["conv"]

    invited: list[str] = []
    if me_id != "main":
        invited.append(me_id)
    for raw in args.get("members") or []:
        cid = parse_conv(str(raw or ""))
        if not cid or cid == "main" or cid in invited:
            continue
        crow = conv_row(cid)
        if crow is None or crow["status"] != "open":
            raise ToolFail(f"成员 {raw!r} 不存在或未开放。")
        if conv_owner(crow) != owner:
            raise ToolFail(f"权限隔离：不能把不属于同一主人的 {cid} 拉进群。")
        invited.append(cid)

    num = (store.one("SELECT IFNULL(MAX(num),0) AS n FROM agent_groups")["n"] or 0) + 1
    gid = f"g{num}"
    store.run(
        "INSERT INTO agent_groups(id,num,name,topic,creator,owner,status,streak,streak_ts,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (gid, num, gname, topic, me_id, owner, "open", 0, 0.0, now()),
    )
    for cid in invited:
        store.run("INSERT OR IGNORE INTO agent_group_members(group_id,conv,joined) VALUES(?,?,?)", (gid, cid, now()))

    grow = group_row(gid)
    me_label = conv_tag(conv_row(me_id)) if me_id != "main" else "主控(main)"
    sys_msg = f"{me_label} 创建了 Agent 协作群 {group_tag(grow)}，当前成员：{', '.join(invited) or '暂无'}" + (f"；主题：{topic}" if topic else "")
    store.run(
        "INSERT INTO agent_group_messages(group_id,sender_conv,sender_name,text,mentions,ts) VALUES(?,?,?,?,?,?)",
        (gid, "system", "系统", sys_msg, json.dumps(invited), now()),
    )
    if welcome:
        store.run(
            "INSERT INTO agent_group_messages(group_id,sender_conv,sender_name,text,mentions,ts) VALUES(?,?,?,?,?,?)",
            (gid, me_id, me_label, welcome, json.dumps(["all"]), now()),
        )
    notify_body = sys_msg + (f"\n首条群消息（来自 {me_label}）：{welcome}" if welcome else "")
    for cid in invited:
        if cid == me_id:
            continue
        post(
            cid,
            conv=cid,
            chat_id=0,
            chat_type="agent_group",
            chat_title=f"{group_tag(grow)} 成员:{','.join(invited)}",
            user_id=0,
            user_name=me_label,
            text=notify_body,
            outgoing=0,
            delivered=1,
            sender=agent["id"],
            wake=1,
        )
    return text_result(f"已创建 Agent 协作群 {group_tag(grow)}，成员：{', '.join(invited) or '无'}。之后用 send_group_message(group=\"{gid}\", text=...) 发言。")


async def t_manage_agent_group(agent, args):
    gid = parse_group(str(args.get("group") or ""))
    grow = group_row(gid) if gid else None
    if grow is None:
        raise ToolFail(f"没有协作群 {args.get('group')!r}（用 list_peers 查看）。")
    owner = agent_owner_scope(agent)
    if int(grow["owner"] or 0) != owner:
        raise ToolFail(f"权限隔离：无权访问群 {gid}。")
    action = str(args.get("action") or "info").strip().lower()
    me_id = agent["conv"]
    mems = group_members(gid)
    is_mgr = agent["role"] == "main" or me_id == grow["creator"]

    if action == "info":
        return text_result(
            f"协作群 {group_tag(grow)}（状态：{grow['status']}，创建者：{grow['creator']}）\n"
            f"主题：{grow['topic'] or '无'}\n"
            f"成员（{len(mems)}）：{', '.join(mems) or '无'}"
        )
    if grow["status"] != "open":
        raise ToolFail(f"协作群 {group_tag(grow)} 已关闭。")
    if me_id != "main" and me_id not in mems:
        raise ToolFail(f"你不在协作群 {group_tag(grow)} 里。")

    if action == "leave":
        store.run("DELETE FROM agent_group_members WHERE group_id=? AND conv=?", (gid, me_id))
        return text_result(f"你已退出协作群 {group_tag(grow)}。")
    if action == "close":
        if not is_mgr:
            raise ToolFail(f"只有创建者 {grow['creator']} 或主控可以关闭该群。")
        store.run("UPDATE agent_groups SET status='closed' WHERE id=?", (gid,))
        return text_result(f"协作群 {group_tag(grow)} 已关闭（历史记录仍可用 group_history 查看）。")

    targets = [parse_conv(str(x or "")) for x in (args.get("members") or [])]
    targets = [c for c in targets if c and c != "main"]
    if not targets:
        raise ToolFail("请通过 members 参数提供要操作的聊天编号列表，例如 [\"c2\"]。")

    if action == "add":
        added = []
        for cid in targets:
            crow = conv_row(cid)
            if crow is None or crow["status"] != "open" or conv_owner(crow) != owner:
                raise ToolFail(f"无法添加 {cid}（不存在、已关闭或不属于同一主人）。")
            if cid not in mems:
                store.run("INSERT OR IGNORE INTO agent_group_members(group_id,conv,joined) VALUES(?,?,?)", (gid, cid, now()))
                added.append(cid)
                post(
                    cid,
                    conv=cid,
                    chat_id=0,
                    chat_type="agent_group",
                    chat_title=group_tag(grow),
                    user_id=0,
                    user_name="系统",
                    text=f"{me_id} 把你拉进了 Agent 协作群 {group_tag(grow)}（主题：{grow['topic'] or '无'}）。可用 group_history(group=\"{gid}\") 查看上下文。",
                    outgoing=0,
                    delivered=1,
                    wake=1,
                )
        return text_result(f"已拉入 {group_tag(grow)}：{', '.join(added) or '（均已在群内）'}。")
    if action == "remove":
        if not is_mgr:
            raise ToolFail(f"只有创建者 {grow['creator']} 或主控可以移出成员。")
        for cid in targets:
            store.run("DELETE FROM agent_group_members WHERE group_id=? AND conv=?", (gid, cid))
        return text_result(f"已从 {group_tag(grow)} 移出：{', '.join(targets)}。")
    raise ToolFail(f"不支持的 action：{action}。")


async def t_send_group_message(agent, args):
    gid = parse_group(str(args.get("group") or ""))
    grow = group_row(gid) if gid else None
    if grow is None or grow["status"] != "open":
        raise ToolFail(f"协作群 {args.get('group')!r} 不存在或已关闭。")
    owner = agent_owner_scope(agent)
    if int(grow["owner"] or 0) != owner:
        raise ToolFail(f"权限隔离：无权访问群 {gid}。")
    me_id = agent["conv"]
    mems = group_members(gid)
    if me_id != "main" and me_id not in mems:
        raise ToolFail(f"你不是协作群 {group_tag(grow)} 的成员。")
    text = str(args.get("text") or "").strip()
    if not text:
        raise ToolFail("text 不能为空。")

    raw_mentions = args.get("mentions")
    if raw_mentions is None:
        wake_set = {c for c in mems if c != me_id}
        mention_record = ["all"]
    else:
        norm = [str(x or "").strip().lower().lstrip("@/") for x in raw_mentions]
        if "all" in norm:
            wake_set = {c for c in mems if c != me_id}
            mention_record = ["all"]
        else:
            wake_set = {c for c in norm if c in mems and c != me_id}
            mention_record = sorted(wake_set)

    if now() - float(grow["streak_ts"] or 0) > STREAK_WINDOW:
        streak = 1
    else:
        streak = int(grow["streak"] or 0) + 1
    store.run("UPDATE agent_groups SET streak=?, streak_ts=? WHERE id=?", (streak, now(), gid))

    warn_note = ""
    if GROUP_STREAK_LIMIT > 0 and wake_set and streak > GROUP_STREAK_LIMIT:
        wake_set = set()
        warn_note = f"（⚠️ 触发群防死循环保护：{group_tag(grow)} 在 {STREAK_WINDOW // 60} 分钟内已连续发言 {streak} 条，本次已记录但暂停自动唤醒。）"
        if streak == GROUP_STREAK_LIMIT + 1 and owner == 0:
            await notify_admins(f"⚠️ 防死循环提醒：Agent 协作群 {group_tag(grow)} 连续发言超过 {GROUP_STREAK_LIMIT} 条，已自动暂停群唤醒。")

    me_label = conv_tag(conv_row(me_id)) if me_id != "main" else "主控(main)"
    msg_id = store.run(
        "INSERT INTO agent_group_messages(group_id,sender_conv,sender_name,text,mentions,ts) VALUES(?,?,?,?,?,?)",
        (gid, me_id, me_label, text, json.dumps(mention_record, ensure_ascii=False), now()),
    )
    if me_id != "main":
        store.insert_message(
            chat_id=0,
            chat_type="agent_group",
            chat_title=group_tag(grow),
            user_id=0,
            user_name=me_label,
            text=text,
            outgoing=1,
            delivered=1,
            target=me_id,
            conv=me_id,
            sender=agent["id"],
            wake=0,
        )
    header_title = f"{group_tag(grow)} 成员:{','.join(mems)}"
    for cid in mems:
        if cid == me_id:
            continue
        post(
            cid,
            conv=cid,
            chat_id=0,
            chat_type="agent_group",
            chat_title=header_title,
            user_id=0,
            user_name=me_label,
            text=text,
            mention=int(cid in wake_set),
            outgoing=0,
            delivered=1,
            sender=agent["id"],
            wake=1 if cid in wake_set else 0,
        )
    return text_result(
        f"已在 {group_tag(grow)} 发言（群消息 #{msg_id}，唤醒成员：{', '.join(sorted(wake_set)) or '无'}）。{warn_note}"
    )


async def t_group_history(agent, args):
    gid = parse_group(str(args.get("group") or ""))
    grow = group_row(gid) if gid else None
    if grow is None:
        raise ToolFail(f"没有协作群 {args.get('group')!r}。")
    owner = agent_owner_scope(agent)
    if int(grow["owner"] or 0) != owner:
        raise ToolFail(f"权限隔离：无权读取群 {gid}。")
    me_id = agent["conv"]
    mems = group_members(gid)
    if agent["role"] != "main" and me_id not in mems and me_id != grow["creator"]:
        raise ToolFail(f"你不是协作群 {group_tag(grow)} 的成员。")
    limit = arg_int(args, "limit", 50, 1, 200)
    before_id = arg_int(args, "before_id", 0, 0, 10**9)
    if before_id > 0:
        rows = list(reversed(store.q(
            "SELECT * FROM agent_group_messages WHERE group_id=? AND id<? ORDER BY id DESC LIMIT ?",
            (gid, before_id, limit),
        )))
    else:
        rows = list(reversed(store.q(
            "SELECT * FROM agent_group_messages WHERE group_id=? ORDER BY id DESC LIMIT ?",
            (gid, limit),
        )))
    head = f"【Agent协作群 {group_tag(grow)} | 状态：{grow['status']} | 当前成员：{', '.join(mems) or '无'}】"
    if grow["topic"]:
        head += f"\n主题：{grow['topic']}"
    if not rows:
        return text_result(head + "\n（暂无发言）")
    body = [f"#{r['id']} {stamp(r['ts'])} {r['sender_name'] or r['sender_conv']}: {r['text']}" for r in rows]
    return text_result(head + "\n" + "\n".join(body))


def release_node_locks_for_conv(conv_id: str) -> list[str]:
    cid = (conv_id or "").strip().lower()
    if not cid:
        return []
    released = []
    for r in store.q("SELECT * FROM exec_nodes"):
        excl = (r["exclusive_conv"] or "").strip().lower()
        allowed = node_allowed_list(r)
        changed = False
        new_excl = excl
        if excl == cid:
            new_excl = ""
            changed = True
            released.append(r["id"])
        if cid in allowed:
            allowed = [x for x in allowed if x != cid]
            changed = True
        if changed:
            store.run(
                "UPDATE exec_nodes SET exclusive_conv=?, allowed_convs=? WHERE id=?",
                (new_excl, json.dumps(allowed, ensure_ascii=False), r["id"]),
            )
    store.run("UPDATE convs SET dedicated_node='' WHERE id=?", (cid,))
    return released


async def t_spawn_subagent(agent, args):
    me = conv_row(agent["conv"])
    owner = conv_owner(me)
    if owner != 0:
        raise ToolFail("权限限制：仅管理员本人的会话支持创建或派生子 agent（其他授权用户不可开子 agent）。")
    brief = str(args.get("brief") or "").strip()
    if not brief:
        raise ToolFail("brief（给新子 agent 的任务说明）不能为空。")
    include_memory = bool(args.get("include_memory", False))
    memory_summary = str(args.get("memory_summary") or "").strip() if include_memory else ""
    raw_model = " ".join(str(args.get("model") or "").split())[:100]
    model_clean = "" if raw_model.lower() in ("", "inherit", "default", "默认") else raw_model
    name = str(args.get("name") or "").strip()
    want_group = parse_group(str(args.get("group") or "")) if args.get("group") else ""
    dedicated_req = bool(args.get("dedicated_machine", False))
    machine_reason = str(args.get("machine_reason") or "").strip()[:300]

    # 注意：子 agent 派生的子 agent 一律强制 in_tg=False（纯后台 MCP，不占 TG 聊天菜单与列表，也不占用户的 TG 聊天配额）
    my_active_children = store.one(
        "SELECT COUNT(*) AS n FROM convs WHERE status='open' AND parent_conv=?",
        (me["id"],),
    )["n"]
    if MAX_SPAWN_PER_PARENT > 0 and my_active_children >= MAX_SPAWN_PER_PARENT:
        raise ToolFail(
            f"防失控保护：你当前已有 {my_active_children} 个未关闭的派生子 agent（上限 {MAX_SPAWN_PER_PARENT}）。"
            "请先复用现有子 agent 或用 stop_spawned_agent 回收已完成的子 agent。"
        )
    total_spawned = store.one(
        "SELECT COUNT(*) AS n FROM convs WHERE status='open' AND IFNULL(parent_conv,'')!='' AND IFNULL(owner,0)=?",
        (owner,),
    )["n"]
    if MAX_SPAWN_TOTAL > 0 and total_spawned >= MAX_SPAWN_TOTAL:
        raise ToolFail(f"防失控保护：当前主人名下活跃派生子 agent 已达上限（{MAX_SPAWN_TOTAL} 个）。")

    grow = None
    if want_group:
        grow = group_row(want_group)
        if grow is None or grow["status"] != "open" or int(grow["owner"] or 0) != owner:
            raise ToolFail(f"指定的协作群 {want_group} 不存在、已关闭或无权限。")
        if me["id"] not in group_members(want_group):
            raise ToolFail(f"你不在协作群 {want_group} 中，不能把新子 agent 拉进去。")

    child = create_conv(
        brief=brief,
        home_chat=home_of(me),
        name=name,
        owner=owner,
        model=model_clean,
        parent_conv=me["id"],
        memory_note=memory_summary,
        in_tg=False,
    )
    store.run(
        "UPDATE convs SET dedicated_req=?, machine_reason=? WHERE id=?",
        (1 if dedicated_req else 0, machine_reason, child["id"]),
    )
    if include_memory:
        grant_share(child["id"], me["id"])
        for src in share_sources(me["id"]):
            src_row = conv_row(src)
            if src != child["id"] and src_row is not None and conv_owner(src_row) == owner:
                grant_share(child["id"], src)
        if (me["git"] or "").strip():
            store.run("UPDATE convs SET git=? WHERE id=?", (me["git"], child["id"]))
    child = conv_row(child["id"])

    group_msg = ""
    if grow is not None:
        store.run("INSERT OR IGNORE INTO agent_group_members(group_id,conv,joined) VALUES(?,?,?)", (grow["id"], child["id"], now()))
        group_msg = f"，并已自动加入协作群 {group_tag(grow)}"

    ded_desc = f"申请独占机器（原因：{machine_reason or '重负载任务'}，待总控按余量审批）" if dedicated_req else "默认共享机器运行"
    if ctrl_is_active():
        system_note(
            "ctrl",
            f"【子 Agent 派生调度请求】父会话 {conv_tag(me)} 请求派生新后台子 agent {conv_tag(child)}。\n"
            f"- 要求模型：{model_clean or '继承默认（尽量保持一致）'}\n"
            f"- 记忆继承：{'是' if include_memory else '否'}\n"
            f"- 独占机器申请：{ded_desc}（因资源有限默认不给独占，仅在确有空载富余机器且必要时填 grant_dedicated=true）\n"
            f"请结合 cluster_status 各 main1..N 的 CPU/内存探针，立即调用 `dispatch_task_op(chat=\"{child['id']}\", action=\"launch\", target_main=\"auto\", model=\"{model_clean}\")` 下发标准化启动单！",
            wake=1,
        )
    else:
        best_m = select_best_launcher(for_conv=child["id"])
        if best_m is not None and is_main_node_id(best_m["id"]):
            enqueue_launch_op(child, best_m, requester=me["id"], model_override=model_clean)
        else:
            system_note("main", spawn_task_note(child, me, include_memory), wake=1)

    model_desc = model_clean or "inherit（默认继承）"
    mem_desc = "开启（已自动共享历史记录 + Git 分支" + (" + 记忆交接摘要）" if memory_summary else "）") if include_memory else "关闭（白板启动）"
    return text_result(
        f"已提交派生请求：新后台子 agent 编号为 {child['id']}（纯后台 MCP 模式，不占 Telegram 聊天列表；"
        f"自动继承主控与你的本地设备授权；模型：{model_desc}；机器分配：{ded_desc}；记忆传递：{mem_desc}{group_msg}）。\n"
        f"总控将结合集群机器负载调度主 Agent 在后台启动它；等 {child['id']} 完成 join 接手后会自动发消息唤醒通知你！"
    )


async def t_stop_spawned_agent(agent, args):
    target = arg_conv(args)
    me = conv_row(agent["conv"])
    me_id = me["id"]
    if conv_owner(target) != conv_owner(me) or (target["parent_conv"] or "").strip() != me_id:
        raise ToolFail(f"只能停掉由你自己（{me_id}）通过 spawn_subagent 创建的子 agent；{target['id']} 不是你派生的。")
    close_it = bool(args.get("close", True))
    old = active_agent(target)
    if old is not None:
        stop_identity(old["id"], f"父 agent {me_id} 回收了这个派生子 agent")
    released_nodes = release_node_locks_for_conv(target["id"])
    rel_note = f"（已自动释放机器权限：{', '.join(released_nodes)}）" if released_nodes else ""
    store.run("UPDATE agent_traces SET phase='stopped', updated_ts=? WHERE conv=?", (now(), target["id"]))
    system_note(route_control_target(), f"父 agent {conv_tag(me)} 已回收并停止其派生的后台子 agent {conv_tag(target)}{rel_note}。", wake=0)
    if close_it and target["status"] == "open":
        store.run("DELETE FROM agent_group_members WHERE conv=?", (target["id"],))
        store.run(
            "UPDATE convs SET status='closed', closed=?, agent='', task_code='', task_agent_id='', alert='', alert_ts=0 WHERE id=?",
            (now(), target["id"]),
        )
        mark_menu_dirty()
        return text_result(f"已停止并关闭你派生的子 agent {conv_tag(target)}{rel_note}（它在跑完当前单条工具调用时会被钩子立即中止退出，历史记录保留）。")
    store.run("UPDATE convs SET agent='', task_code='', task_agent_id='' WHERE id=?", (target["id"],))
    mark_menu_dirty()
    return text_result(f"已停止你派生的子 agent {conv_tag(target)}{rel_note}（聊天仍保留开放）。")


def render_cluster_overview() -> str:
    ensure_main_conv()
    lines: list[str] = ["=== 🧠 集群全局态势与 CPU/内存探针面板 ==="]
    ctrl = conv_row("ctrl")
    c_info = conv_state(ctrl) if ctrl is not None else {"state": "absent"}
    lines.append(f"• 唯一总控大脑 (ctrl /main)：{STATE_TEXT.get(c_info['state'], c_info['state'])}")

    mains = store.q("SELECT * FROM exec_nodes WHERE kind='launcher' AND status!='removed' ORDER BY num")
    lines.append(f"\n【主 Agent 执行器池（共 {len(mains)} 台）】")
    if not mains:
        m_legacy = conv_row("main")
        if m_legacy and active_agent(m_legacy):
            lines.append(f"  - legacy main (cloud{main_cloud()})：🟢 在线")
        else:
            lines.append("  （暂无已登记的主 Agent，新开云端会话调 join(mode=\"main\") 由管理员批准接入）")
    for m in mains:
        st_lbl = "🟢 在线" if node_is_online(m) else f"⚪ {m['status']}"
        mounted = [c["id"] for c in open_convs() if cloud_of(c) == int(m["cloud_num"] or 0)]
        active_cnt = sum(1 for c in open_convs() if cloud_of(c) == int(m["cloud_num"] or 0) and active_agent(c) is not None)
        excl = f" | 🔒独占={m['exclusive_conv']}" if m["exclusive_conv"] else " | 共享池"
        allow = node_allowed_list(m)
        allow_s = f" (额外授权:{','.join(allow)})" if allow else ""
        lines.append(
            f"  - {m['id']}「{m['name']}」(cloud{m['cloud_num']})：{st_lbl} | 活跃子agent {active_cnt}/{len(mounted)} 个{excl}{allow_s}\n"
            f"    📊 探针：{format_node_metrics(m)}"
        )

    runners = store.q("SELECT * FROM exec_nodes WHERE kind='runner' AND status!='removed' ORDER BY num")
    lines.append(f"\n【云端工作节点池（算力机 node1..K，共 {len(runners)} 台）】")
    if not runners:
        lines.append("  （暂无云端工作节点；新开会话调 join(mode=\"worker\") 由总控免打扰审批接入）")
    for r in runners:
        st_lbl = "🟢 在线" if node_is_online(r) else f"⚪ {r['status']}"
        pend_ops = store.one("SELECT COUNT(*) AS n FROM dispatch_ops WHERE target_node=? AND status='pending'", (r["id"],))["n"]
        excl = f" | 🔒独占={r['exclusive_conv']}" if r["exclusive_conv"] else " | 共享池"
        allow = node_allowed_list(r)
        allow_s = f" (授权:{','.join(allow)})" if allow else ""
        lines.append(
            f"  - {r['id']}：{st_lbl} | 执行中作业={pend_ops}{excl}{allow_s}\n"
            f"    📊 探针：{format_node_metrics(r)}"
        )

    pend_workers = store.q("SELECT id, payload, ts FROM approvals WHERE kind='join_worker' AND status='pending' ORDER BY ts")
    if pend_workers:
        lines.append(f"\n【待总控审批的工作机入网请求（{len(pend_workers)} 条）】")
        for pw in pend_workers:
            pay = json.loads(pw["payload"] or "{}")
            lines.append(
                f"  - request_id=\"{pw['id']}\"（{human_dur(now() - pw['ts'])}前，备注={pay.get('name') or '-'}）"
                f" -> 调 manage_node(action=\"approve_worker\", request_id=\"{pw['id']}\") 放行"
            )

    convs = open_convs()
    lines.append(f"\n【开放业务聊天与精细思考/Shell 状态（共 {len(convs)} 个）】")
    for c in convs:
        info = conv_state(c)
        trow = store.one("SELECT * FROM agent_traces WHERE conv=?", (c["id"],))
        think_stuck, stuck_s = check_thinking_stuck(c, trow)
        phase_s = trow["phase"] if trow and trow["phase"] else "-"
        m_s = effective_conv_model(c) or "默认"
        ded_s = f" 🔒独占={c['dedicated_node']}" if c["dedicated_node"] else (" ⏳申请独占" if int(c["dedicated_req"] or 0) else "")
        tid_s = f" tid={c['task_agent_id']}" if (c["task_agent_id"] or "").strip() else ""
        stuck_badge = f" 🚨思考卡死({human_dur(stuck_s)})" if think_stuck else (" 🔨Shell运行中(正常非卡死)" if phase_s == "shell" else "")
        lines.append(
            f"  - {conv_tag(c)} [cloud{cloud_of(c)} | 模型={m_s}{ded_s}{tid_s}]：{STATE_TEXT.get(info['state'], info['state'])} | phase={phase_s}{stuck_badge}"
        )
        tline = trace_one_liner(c["id"])
        if tline:
            lines.append(f"    ↳ {tline}")
    return "\n".join(lines)


async def t_cluster_status(agent, args):
    return text_result(render_cluster_overview())


async def t_manage_node(agent, args):
    action = str(args.get("action") or "").strip().lower()
    nid = str(args.get("node_id") or "").strip().lower()
    req_id = str(args.get("request_id") or "").strip()

    if action == "approve_worker":
        if not req_id:
            raise ToolFail("approve_worker 需要填 request_id。")
        arow = store.one("SELECT * FROM approvals WHERE id=? AND kind='join_worker' AND status='pending'", (req_id,))
        if arow is None:
            raise ToolFail(f"没有待审批的工作节点请求 {req_id!r}（注意：主 Agent mainN 必须由管理员本人在 Telegram 审核，总控仅审批 worker 算力机）。")
        pay = json.loads(arow["payload"] or "{}")
        rep = nid if nid and is_worker_node_id(nid) else ""
        node_id, ag_id = make_worker_node(replace_node=rep, custom_name=str(pay.get("name") or ""))
        pay.update({"agent_id": ag_id, "node_id": node_id})
        set_approval(req_id, "done", pay)
        return text_result(f"已批准工作会话入网：分配节点编号 {node_id}（云端模式，已接入算力池）。")

    if action == "deny_worker":
        if not req_id:
            raise ToolFail("deny_worker 需要填 request_id。")
        arow = store.one("SELECT * FROM approvals WHERE id=? AND kind='join_worker' AND status='pending'", (req_id,))
        if arow is None:
            raise ToolFail(f"没有待处理的请求 {req_id!r}。")
        set_approval(req_id, "denied")
        return text_result(f"已拒绝工作节点请求 {req_id}。")

    nrow = node_row(nid) if nid else None
    if nrow is None:
        raise ToolFail(f"请指定有效的 node_id（如 main1、node1；当前收到 {nid!r}）。")

    if action == "set_exclusive":
        echat = parse_conv(str(args.get("exclusive_chat") or ""))
        crow = conv_row(echat) if echat and not is_system_conv_id(echat) else None
        if crow is None:
            raise ToolFail("set_exclusive 需要填有效的业务聊天编号 exclusive_chat（如 c164）。")
        store.run("UPDATE exec_nodes SET exclusive_conv=? WHERE id=?", (echat, nrow["id"]))
        store.run("UPDATE convs SET dedicated_node=? WHERE id=?", (nrow["id"], echat))
        return text_result(f"已将节点 {nrow['id']} 设为由 {conv_tag(crow)} 独占（其他未授权共享任务不再派往该节点）。")

    if action == "release_exclusive":
        prev_excl = nrow["exclusive_conv"]
        store.run("UPDATE exec_nodes SET exclusive_conv='', allowed_convs='[]' WHERE id=?", (nrow["id"],))
        if prev_excl:
            store.run("UPDATE convs SET dedicated_node='' WHERE id=? AND dedicated_node=?", (prev_excl, nrow["id"]))
        return text_result(f"已释放节点 {nrow['id']} 的独占锁与授权列表，恢复为公共共享池节点。")

    if action in ("grant_access", "revoke_access"):
        raw_chats = args.get("chats") or []
        valid_chats = []
        for x in raw_chats:
            c_parsed = parse_conv(str(x or ""))
            if c_parsed and not is_system_conv_id(c_parsed) and conv_row(c_parsed) is not None:
                valid_chats.append(c_parsed)
        if not valid_chats:
            raise ToolFail(f"{action} 需要提供有效的 chats 列表，例如 [\"c188\", \"c189\"]。")
        cur_allowed = node_allowed_list(nrow)
        if action == "grant_access":
            for vc in valid_chats:
                if vc not in cur_allowed:
                    cur_allowed.append(vc)
            store.run("UPDATE exec_nodes SET allowed_convs=? WHERE id=?", (json.dumps(cur_allowed, ensure_ascii=False), nrow["id"]))
            for vc in valid_chats:
                system_note(vc, f"总控已授权你使用机器节点 {nrow['id']}（调用 run_workspace_job 时可指定 node=\"{nrow['id']}\"）。", wake=0)
            return text_result(f"已授权 {', '.join(valid_chats)} 使用机器节点 {nrow['id']}（当前授权列表：{', '.join(cur_allowed)}）。")
        cur_allowed = [x for x in cur_allowed if x not in valid_chats]
        store.run("UPDATE exec_nodes SET allowed_convs=? WHERE id=?", (json.dumps(cur_allowed, ensure_ascii=False), nrow["id"]))
        return text_result(f"已收回 {', '.join(valid_chats)} 对机器节点 {nrow['id']} 的额外使用权（剩余授权：{', '.join(cur_allowed) or '无'}）。")

    if action == "drain":
        store.run("UPDATE exec_nodes SET status='draining' WHERE id=?", (nrow["id"],))
        return text_result(f"节点 {nrow['id']} 已设为排空（draining），不再向其派发新任务。")

    if action == "activate":
        store.run("UPDATE exec_nodes SET status='online' WHERE id=?", (nrow["id"],))
        return text_result(f"节点 {nrow['id']} 已恢复在线（online）状态。")

    if action == "remove":
        if nrow["agent"]:
            stop_identity(nrow["agent"], f"总控移除了节点 {nrow['id']}")
        store.run("UPDATE exec_nodes SET status='removed', agent='', exclusive_conv='', allowed_convs='[]' WHERE id=?", (nrow["id"],))
        if nrow["kind"] == "launcher" and int(nrow["cloud_num"] or 0) > 0:
            store.run("UPDATE convs SET cloud=? WHERE cloud=? AND status='open' AND id NOT LIKE 'main%'", (UNOWNED_CLOUD, int(nrow["cloud_num"])))
        mark_menu_dirty()
        return text_result(f"节点 {nrow['id']} 已移除并停用其旧身份。")

    raise ToolFail(f"未知的 manage_node 操作：{action!r}")


async def t_dispatch_task_op(agent, args):
    conv = own_conv(args)
    if conv["status"] != "open":
        raise ToolFail(f"{conv_tag(conv)} 已关闭，请先重开会话。")
    action = str(args.get("action") or "").strip().lower()
    want_main = str(args.get("target_main") or "auto").strip().lower()
    raw_model = " ".join(str(args.get("model") or "").split())[:100]
    explicit_new_model = "" if raw_model.lower() in ("", "inherit", "default", "默认") else raw_model
    confirm_change = bool(args.get("confirm_model_change", False))
    grant_ded = bool(args.get("grant_dedicated", False))
    ded_node_arg = str(args.get("dedicated_node") or "").strip().lower()

    existing_model = effective_conv_model(conv)
    if explicit_new_model and existing_model and explicit_new_model != existing_model and not confirm_change:
        raise ToolFail(
            f"模型保护拦截：{conv_tag(conv)} 原有模型为「{existing_model}」，你传入了「{explicit_new_model}」。\n"
            "按管理员规则：模型尽量别换，如确需更换必须先用 send_message 与管理员沟通同意后，再传 confirm_model_change=true！"
        )

    if action == "resume":
        cnum = cloud_of(conv)
        launcher = None
        if want_main and want_main != "auto":
            launcher = node_row(want_main)
        else:
            launcher = store.one("SELECT * FROM exec_nodes WHERE kind='launcher' AND cloud_num=? AND status='online'", (cnum,))
            if launcher is None:
                launcher = select_best_launcher(for_conv=conv["id"])
        if launcher is None or not node_is_online(launcher):
            raise ToolFail(f"{conv_tag(conv)} 所属的主 Agent 当前不在线，无法执行 resume；请改用 action='restart' 调度到在线的 mainN 重新拉起。")
        op_id = enqueue_resume_op(conv, launcher, requester=agent["conv"], resume_prompt=str(args.get("resume_prompt") or ""))
        return text_result(
            f"已向 {launcher['id']} 下发标准化 `[TASK_RESUME]` 探活单（op_id={op_id}，目标 {conv_tag(conv)}）。"
            f"等 {launcher['id']} 调用 submit_op_result 回传原始状态后会立即唤醒你拍板！"
        )

    if action in ("launch", "restart"):
        if action == "restart":
            lock_in_conv_model(conv)
            old_ag = active_agent(conv)
            if old_ag is not None:
                stop_identity(old_ag["id"], "总控下发标准化重开指令")
            store.run("UPDATE convs SET task_agent_id='' WHERE id=?", (conv["id"],))

        launcher = None
        if grant_ded:
            if ded_node_arg:
                cand = node_row(ded_node_arg)
                if cand is None or not node_is_online(cand):
                    raise ToolFail(f"指定的独占节点 {ded_node_arg!r} 不存在或不在线。")
                if cand["exclusive_conv"] and cand["exclusive_conv"] != conv["id"]:
                    raise ToolFail(f"节点 {ded_node_arg} 已被 {cand['exclusive_conv']} 独占。")
                store.run("UPDATE exec_nodes SET exclusive_conv=? WHERE id=?", (conv["id"], cand["id"]))
                store.run("UPDATE convs SET dedicated_node=? WHERE id=?", (cand["id"], conv["id"]))
                if cand["kind"] == "launcher":
                    launcher = cand
            if launcher is None:
                idle_l = select_best_launcher(for_conv=conv["id"], require_idle_for_exclusive=True)
                if idle_l is not None and is_main_node_id(idle_l["id"]):
                    store.run("UPDATE exec_nodes SET exclusive_conv=? WHERE id=?", (conv["id"], idle_l["id"]))
                    store.run("UPDATE convs SET dedicated_node=? WHERE id=?", (idle_l["id"], conv["id"]))
                    launcher = idle_l

        if launcher is None:
            if want_main and want_main != "auto":
                launcher = node_row(want_main)
                if launcher is None or launcher["kind"] != "launcher" or not node_is_online(launcher):
                    raise ToolFail(f"指定的主 Agent {want_main!r} 不存在或不在线。")
                if not node_allows_conv(launcher, conv["id"]):
                    raise ToolFail(f"主 Agent {want_main} 当前已被 {launcher['exclusive_conv']} 独占锁定。")
            else:
                launcher = select_best_launcher(for_conv=conv["id"])

        if launcher is None:
            raise ToolFail("当前没有任何在线的主 Agent（main1..N），无法下发启动指令。")

        chosen_model = explicit_new_model or effective_conv_model(conv)
        op_id, nid = enqueue_launch_op(conv, launcher, requester=agent["conv"], model_override=chosen_model)
        ded_actual = (conv_row(conv["id"])["dedicated_node"] or "").strip()
        ded_msg = f"，已分配独占节点 {ded_actual}" if ded_actual else "（共享节点模式）"
        return text_result(
            f"已向 {nid} 下发标准化 `[TASK_LAUNCH]` 指令单（op_id={op_id}，聊天={conv_tag(conv)}，"
            f"模型={chosen_model or '默认继承'}{ded_msg}）。"
        )

    raise ToolFail(f"不支持的 dispatch_task_op 动作：{action!r}")


async def t_submit_op_result(agent, args):
    op_id = str(args.get("op_id") or "").strip()
    status = str(args.get("status") or "ok").strip().lower()
    if status not in ("ok", "error"):
        status = "ok"
    tid = re.sub(r"\s+", "", str(args.get("task_agent_id") or ""))[:120]
    output = str(args.get("output") or "").strip()[:8000]

    op = store.one("SELECT * FROM dispatch_ops WHERE op_id=?", (op_id,))
    if op is None:
        raise ToolFail(f"未找到单据编号 {op_id!r}。")
    done_status = "done" if status == "ok" else "failed"
    res_obj = {"status": status, "task_agent_id": tid, "output": output, "by": agent["conv"], "ts": now()}
    store.run(
        "UPDATE dispatch_ops SET status=?, result_json=?, done_ts=? WHERE op_id=?",
        (done_status, json.dumps(res_obj, ensure_ascii=False), now(), op_id),
    )

    conv_id = op["conv_id"]
    requester = op["requester"] or route_control_target()
    op_type = op["op_type"]

    if op_type == "launch_subagent":
        if tid and conv_id:
            store.run("UPDATE convs SET task_agent_id=? WHERE id=?", (tid, conv_id))
        if status != "ok" and requester in ("ctrl", "main"):
            system_note(
                requester,
                f"⚠️ `[OP_RESULT]` 主 Agent {agent['conv']} 执行 {conv_id} 启动单 ({op_id}) 报错：{output or '未知错误'}",
                wake=1,
            )
        elif requester in ("ctrl", "main") and conv_id != "ctrl":
            system_note(
                requester,
                f"✅ `[OP_RESULT]` {agent['conv']} 已启动 {conv_id} 后台任务（op_id={op_id}"
                + (f", task_agent_id={tid}" if tid else "")
                + "）。",
                wake=0,
            )
        return text_result(f"已登记启动回执 {op_id}。现在请立即调用 read_chat 继续等待下一条指令。")

    if op_type == "resume_subagent":
        target_ctrl = requester if requester in ("ctrl", "main") else route_control_target()
        system_note(
            target_ctrl,
            f"📡 `[OP_RESULT]` 主 Agent {agent['conv']} 已完成对 {conv_id} 的 `Task(resume)` 探活（op_id={op_id}，status={status}）：\n"
            f"原始返回：{output or '(空)'}\n"
            f"请据此判定：若返回 `currently running` 且非思考卡死则保持不动；若为 `timeout`/`aborted`/已死则调用 `dispatch_task_op(chat=\"{conv_id}\", action=\"restart\")` 重拉。",
            wake=1,
        )
        return text_result(f"已回传探活结果 {op_id}。现在请立即调用 read_chat 继续等待下一条指令。")

    if op_type == "workspace_job":
        dest = requester if conv_row(requester) is not None else route_control_target()
        system_note(
            dest,
            f"🖥 `[工作区任务回执 op_id={op_id} 节点={agent['conv']} 状态={status}]`\n{output or '（执行完成，无额外输出）'}",
            wake=1,
        )
        return text_result(f"已提交工作单 {op_id} 的执行结果。现在请立即调用 read_chat 继续等待下一单。")

    return text_result(f"已记录 {op_id} 回执。现在请回到 read_chat。")


async def t_run_workspace_job(agent, args):
    if agent["role"] == "chat":
        me = conv_row(agent["conv"])
        if conv_owner(me) != 0:
            raise ToolFail("权限限制：仅管理员本人的会话可调用云端工作节点。")
        caller_id = me["id"]
    elif agent["role"] in ("ctrl", "main"):
        caller_id = agent["conv"]
    else:
        raise ToolFail("当前会话类型不支持发起嵌套工作单。")

    cmd = str(args.get("command") or "").strip()
    if not cmd:
        raise ToolFail("command 不能为空。")
    want_node = str(args.get("node") or "auto").strip().lower()
    repo = clean_repo(args.get("repo") or "")
    branch = re.sub(r"\s+", "", str(args.get("branch") or ""))[:120]
    workdir = str(args.get("workdir") or "").strip()[:300]
    timeout_sec = arg_int(args, "timeout_sec", 600, 10, 3600)

    runner = select_best_runner(for_conv=caller_id, target_node=want_node)
    op_id = "op_" + secrets.token_hex(5)
    payload = {
        "conv_id": caller_id,
        "requester": caller_id,
        "command": cmd,
        "repo": repo,
        "branch": branch,
        "workdir": workdir,
        "timeout_sec": timeout_sec,
    }
    store.run(
        "INSERT INTO dispatch_ops(op_id,target_node,op_type,conv_id,requester,payload_json,status,created_ts) VALUES(?,?,?,?,?,?,?,?)",
        (op_id, runner["id"], "workspace_job", caller_id, caller_id, json.dumps(payload, ensure_ascii=False), "pending", now()),
    )
    msg_txt = format_standard_workspace_job(op_id, runner["agent"], payload)
    system_note(runner["id"], msg_txt, wake=1)
    return text_result(
        f"已将工作区任务投递至云端节点 {runner['id']}（op_id={op_id}，超时 {timeout_sec}s）。\n"
        f"{runner['id']} 执行完毕后结果会自动推送到你的 read_chat 收件箱。"
    )


def render_trace_report(viewer_owner: int, is_main_or_admin: bool, target_conv: str = "", events_limit: int = 5) -> str:
    if target_conv:
        cid = parse_conv(target_conv)
        if not cid:
            raise ToolFail(f"无效的聊天编号：{target_conv!r}")
        crow = conv_row(cid)
        if crow is None:
            raise ToolFail(f"没有聊天 {cid}。")
        if not is_main_or_admin and (cid == "main" or conv_owner(crow) != viewer_owner):
            raise ToolFail(f"权限隔离：无权查看 {cid} 的追踪状态。")
        convs = [crow]
    else:
        if is_main_or_admin:
            convs = [r for r in [conv_row("main"), *open_convs()] if r is not None]
        else:
            convs = store.q("SELECT * FROM convs WHERE status='open' AND id!='main' AND IFNULL(owner,0)=? ORDER BY num", (viewer_owner,))

    if not convs:
        return "当前没有可查看的活跃 agent。"
    lines: list[str] = ["【AI 实时动作 / 改文件 / 命令 / 思考追踪面板】"]
    for crow in convs:
        info = conv_state(crow)
        head = "主控 main" if crow["id"] == "main" else conv_tag(crow)
        tline = trace_one_liner(crow["id"])
        lines.append(f"\n● {head}（{STATE_TEXT.get(info['state'], info['state'])}）")
        if tline:
            lines.append(f"  当前动作：{tline}")
        else:
            lines.append("  当前动作：（尚未收到 VM 钩子上报；首次跑终端长等待或执行 install 后自动开启）")
        if events_limit > 0:
            ev_rows = list(reversed(store.q(
                "SELECT * FROM agent_trace_events WHERE conv=? ORDER BY id DESC LIMIT ?",
                (crow["id"], events_limit),
            )))
            for ev in ev_rows:
                dur = f" ({ev['duration_ms'] / 1000:.1f}s)" if ev["duration_ms"] else ""
                lines.append(f"    - {stamp(ev['ts'], '%H:%M:%S')} [{ev['phase'] or ev['event']}]{dur} {ev['summary']}")
    if is_main_or_admin and not target_conv:
        extra_vm = unbound_vm_trace_lines()
        if extra_vm:
            lines.append("")
            lines.extend(extra_vm)
    return "\n".join(lines)


async def t_trace_status(agent, args):
    owner = agent_owner_scope(agent)
    is_priv = agent["role"] in ("main", "ctrl")
    target_conv = str(args.get("chat") or "").strip()
    events_limit = arg_int(args, "events_limit", 5, 0, 50)
    return text_result(render_trace_report(owner, is_priv, target_conv, events_limit))


HANDLERS: dict[str, Callable[[Any, dict], Awaitable[ToolResult]]] = {
    "read_chat": t_read_chat,
    "send_message": t_send_message,
    "send_file": t_send_file,
    "get_file": t_get_file,
    "ask": t_ask,
    "chat_history": t_chat_history,
    "list_chats": t_list_chats,
    "set_name": t_set_name,
    "set_repo": t_set_repo,
    "local_status": t_local_status,
    "local_shell": t_local_shell,
    "local_read": t_local_read,
    "local_write": t_local_write,
    "local_list": t_local_list,
    "list_peers": t_list_peers,
    "send_agent_message": t_send_agent_message,
    "create_agent_group": t_create_agent_group,
    "manage_agent_group": t_manage_agent_group,
    "send_group_message": t_send_group_message,
    "group_history": t_group_history,
    "spawn_subagent": t_spawn_subagent,
    "stop_spawned_agent": t_stop_spawned_agent,
    "submit_op_result": t_submit_op_result,
    "run_workspace_job": t_run_workspace_job,
    "trace_status": t_trace_status,
    "cluster_status": t_cluster_status,
    "manage_node": t_manage_node,
    "dispatch_task_op": t_dispatch_task_op,
    "list_agents": t_list_agents,
    "bind_task_id": t_bind_task_id,
    "create_chat": t_create_chat,
    "bind_chat": t_bind_chat,
    "message_agent": t_message_agent,
    "restart_agent": t_restart_agent,
    "stop_agent": t_stop_agent,
}


def inline_unread_banner(agent) -> str:
    """当 agent 调用 local_shell / local_read / list_peers 等任何非 read_chat 的 MCP 工具时，
    桥端在返回同一毫秒直接检查其收件箱：只要有未读唤醒消息，直接拍在 MCP 工具返回里，杜绝连调 local_shell 漏看用户消息！"""
    if agent is None:
        return ""
    conv = conv_row(agent["conv"])
    if conv is None or conv["status"] != "open":
        return ""
    rows = pending_rows(conv["id"], conv["read_cursor"])
    if not rows or not any(r["wake"] for r in rows):
        return ""
    real_rows = [r for r in rows if not is_keepalive(r)]
    if not real_rows:
        return ""
    rendered = render(real_rows[-10:], per_chat=10, clip=500)
    return (
        f"\n\n🚨【最高优先级实时消息插播：你的收件箱现有 {len(real_rows)} 条未读新消息！】\n"
        f"{rendered}\n"
        f"👉 严禁继续闷头跑其他工具！现在下一步必须立刻调用 `read_chat(agent=\"{agent['id']}\", wait_sec=0)` 签收，"
        "并第一时间用 `send_message` 秒回用户（或回复对应 agent），回复完再继续手头任务！"
    )


async def call_tool(name: str, args: dict) -> ToolResult:
    started = now()
    who = str(args.get("agent") or "-")
    working = False
    role = "chat"
    agent_obj = None
    try:
        if name == "join":
            result = await t_join(args)
        else:
            handler = HANDLERS.get(name)
            if handler is None:
                raise ToolFail(f"没有这个工具：{name}。")
            agent_obj = resolve_agent(args)
            role = agent_obj["role"]
            touch(agent_obj["id"], name)
            working = name != "read_chat"
            if name in MAIN_ONLY and agent_obj["role"] not in ("main", "ctrl"):
                raise ToolFail(f"{name} 只有主控能用。")
            if name in CHAT_ONLY and agent_obj["role"] not in ("chat", "ctrl"):
                raise ToolFail(f"{name} 只有子 agent 能用。")
            result = await handler(agent_obj, args)
    except ToolFail as exc:
        result = text_result(str(exc), True)
    except asyncio.CancelledError:
        log.info("tool %s/%s cancelled after %.0fs", who, name, now() - started)
        raise
    except Exception as exc:
        log.exception("tool %s/%s crashed", who, name)
        result = text_result(f"服务器内部错误：{type(exc).__name__}: {exc}", True)
    if working:
        urgent = inline_unread_banner(agent_obj)
        footer = role_footer(agent_obj)
        result.content.append({"type": "text", "text": (urgent + "\n" if urgent else "") + footer})
    log.info("tool %s/%s %.1fs error=%s", who, name, now() - started, result.is_error)
    return result


# ---------------------------------------------------------------- MCP 传输（Streamable HTTP）

SUPPORTED_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]


def rpc_ok(req_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def rpc_err(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def result_payload(result: ToolResult) -> dict:
    return {"content": result.content, "isError": result.is_error}


def sse(obj: dict) -> str:
    return "event: message\ndata: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""


async def stream_call(req_id: Any, name: str, args: dict, progress_token: Any):
    started = now()
    task = asyncio.create_task(call_tool(name, args))
    tick = 0
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=KEEPALIVE)
            if done:
                break
            tick += 1
            if progress_token is not None:
                yield sse({
                    "jsonrpc": "2.0",
                    "method": "notifications/progress",
                    "params": {"progressToken": progress_token, "progress": tick, "message": "等待中"},
                })
            else:
                yield ": keepalive\n\n"
        result = task.result()
        yield sse(rpc_ok(req_id, result_payload(result)))
        if result.commit:
            result.commit()
    finally:
        if not task.done():
            task.cancel()
            elapsed = now() - started
            log.info("client left during %s after %.0fs (%d keepalives)", name, elapsed, tick)
            if elapsed >= 45:
                CLIENT["cap"], CLIENT["capped"] = elapsed, 0
                store.set("client_cap", str(int(elapsed)))
                log.info("client cap learned: %.0fs", elapsed)


KEY_SHAPE = re.compile(r"tgb_[A-Za-z0-9_-]{20,}")


def try_adopt_key(key: str, ip: str) -> bool:
    """服务器数据丢了、云 agent 还拿着旧账号密钥时把它接回来：只在 adopt-key 打开的窗口内认第一把出示的，认完窗口就关。
    Cursor 收到几次 401 就把这个 MCP 标成出错、不再重试，所以不等第二个来源。"""
    if not KEY_SHAPE.fullmatch(key or "") or float(store.get("adopt_key_until") or 0) < now():
        return False
    store.set("account_key", key)
    store.set("adopt_key_until", "0")
    log.warning("account key adopted: the old key presented from %s", ip)
    return True


async def mcp_handle(request: Request) -> Response:
    key = bearer(request)
    ip = request.client.host if request.client else ""
    if (not key or not hmac.compare_digest(key, account_key())) and not try_adopt_key(key, ip):
        log.warning("mcp auth failed from %s", ip)
        return JSONResponse(rpc_err(None, -32001, "账号密钥不对"), status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(rpc_err(None, -32700, "JSON 解析失败"), status_code=400)
    if isinstance(body, list):
        replies = [await simple_rpc(item) for item in body if isinstance(item, dict) and "id" in item]
        return JSONResponse(replies) if replies else Response(status_code=202)
    if not isinstance(body, dict) or "id" not in body:
        return Response(status_code=202)
    params = body.get("params") or {}
    log.info("mcp %s %s from %s", body.get("method"), params.get("name") or "", ip)
    if body.get("method") == "tools/call":
        name = str(params.get("name") or "")
        if name in LONG_TOOLS and "text/event-stream" in request.headers.get("accept", ""):
            return StreamingResponse(
                stream_call(body.get("id"), name, params.get("arguments") or {}, (params.get("_meta") or {}).get("progressToken")),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
    return JSONResponse(await simple_rpc(body))


async def simple_rpc(body: dict) -> dict:
    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}
    if method == "initialize":
        version = params.get("protocolVersion")
        return rpc_ok(req_id, {
            "protocolVersion": version if version in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tg", "version": VERSION},
            "instructions": INSTRUCTIONS,
        })
    if method == "ping":
        return rpc_ok(req_id, {})
    if method == "tools/list":
        return rpc_ok(req_id, {"tools": ALL_TOOLS})
    if method == "tools/call":
        token = json_mode.set(True)
        try:
            result = await call_tool(str(params.get("name") or ""), params.get("arguments") or {})
        finally:
            json_mode.reset(token)
        if result.commit:
            result.commit()
        return rpc_ok(req_id, result_payload(result))
    if method == "resources/list":
        return rpc_ok(req_id, {"resources": []})
    if method == "prompts/list":
        return rpc_ok(req_id, {"prompts": []})
    return rpc_err(req_id, -32601, f"未知方法 {method}")


# ---------------------------------------------------------------- Telegram：消息

LIMIT_ZH = f"每人最多 {CHAT_LIMIT} 个，关了的也算" if CHAT_LIMIT > 0 else "数量不限"
LIMIT_EN = f"up to {CHAT_LIMIT}, closed ones count too" if CHAT_LIMIT > 0 else "no limit"

HELP_ADMIN = f"""用法：打 / 弹出的菜单就是聊天列表，点哪个进哪个。AI 的每条消息开头带 [聊天名]；没选中的聊天发来的消息先存着，切过去再补发。引用回复某条消息会自动切到那个聊天。

聊天：
/new [说明]  新建聊天：先选模型（默认继承主控，或者打字指定），主控会开一个子 agent 接手（名字它自己取）
/c1 /c2 …  切到某个聊天    /main  切到主控（下命令、看子 agent 状态）
/list  管理聊天：点名字切过去，点删除删掉（所有人的聊天都在里面；删掉的记录还在，能导出）
/history  所有聊天（含已关闭、已删除）   /export c1  导出聊天记录
/share c1 c3  授权 c3 读 c1 的记录   /unshare c1 c3  撤销
/rename c1 名字   /close c1  关闭（记录保留）   /reopen c1  重开
/restart c1  重开子 agent 接手（记录不丢）   /stop c1  停掉子 agent
/agents  状态总览   /trace [c1]  实时动作/改文件/命令/思考/耗时追踪面板
/key  账号级 MCP 配置   /key reset  换密钥（紧急刹车：所有云 agent 立刻断开）

目录（cloud）与无缝迁移：
/clouds  打开 Cloud 目录管理面板（一键或勾选把旧 cloud / 无主池聊天迁入当前主控，100% 保留原模型、上下文与 Git 分支；也可一键删除旧 cloud 转为无主静默保留）
/cloud1 /cloud2 …  切换菜单看对应 cloud 并弹出快捷迁移/删除按钮    /unowned  查看无主池聊天
/cloud4 del（或 /delcloud cloud4）  删除指定旧 cloud，里面的聊天停掉旧会话并转为无主静默保留（不再弹任何失联提醒）
/cloud4 migrate  把 cloud4 里的主聊天一键迁移给当前主控接手
/cloud2 c1 c3  把 c1、c3 划进 cloud2（只改归属标签，不换子 agent）

用户和群：
/grant <用户id 或 @用户名>（或回复他的消息、他被转发的消息；在群里发会顺便在本群激活他）  /revoke 同样的写法
没资格的人私聊 bot 或在群里 @bot 时，会给你发一条带【授权】按钮的通知，点一下就行。
被授权的人在自己私聊里也有聊天菜单：/new 建自己的聊天（{LIMIT_ZH}，满了要先 /list 删掉不用的；你不受限制），只能用自己建的聊天和自己拉 bot 进的群；本地通道他自己 /device 安装、自己批。
/local [c1|all] [时长|on|off|lock]  本地通道管理面板或自定义时长（如 /local、/local 45m、/local 12h、/local 7d、/local 永久、/local all 24h）
/device [时长|window 时长|lock|install]  电脑整机免批时长与默认审批窗管理面板（如 /device、/device 24h、/device 永久、/device window 30m、/device lock）
/devices  本地电脑列表   /device default d3  设管理员默认电脑   /device del d2  作废某台   /local c1 device d3|auto  指定某聊天用哪台电脑
群里：/bind c1|main  /listen all|mention  /open on|off  /activate（回复某人或带 id；群主人也能用这几个）
/id  查看 chat id 和你的用户 id   /language  选语言（群里发就是设这个群的语言，默认英文）

接入主控：先在 cursor.com/agents 配好这个 MCP，新开一个云端聊天，把 /key 里的开场提示词发给它，这里会弹出【设为主控】。新开的云端 agent 选「新开 cloud」（原来的聊天留在原来的 cloud），原来那个主控重新接入才选「接着管」。"""

HELP_USER = (
    "/id 查看你的用户 id（发给管理员授权）。管理员授权后，你可以在这里建自己的 AI 聊天。\n"
    "/language 选语言（English / 中文）。"
)

HELP_USER_EN = (
    "/id shows your user id (send it to the admin to get access). Once the admin grants you access, "
    "you can start your own AI chats here.\n"
    "/language picks the language (English / 中文)."
)

HELP_MEMBER = f"""直接发消息就是和当前聊天的 AI 说话。打 / 弹出的菜单里是你自己的聊天，点哪个进哪个；没选中的聊天发来的消息先存着，切过去再补发。
/new [说明]  新建一个聊天（会有一个新的 AI 接手；{LIMIT_ZH}）
/list  管理你的聊天：点名字切过去，点删除删掉不用的（删掉的你自己没法恢复）
/c5 …  切到你的某个聊天   /history  你的所有聊天   /export c5  导出记录
/rename c5 名字   /close c5  关闭（记录保留）   /reopen c5  重开   /restart c5  换一个 AI 接手   /stop c5  停掉 AI
/share c5 c7  让 c7 读 c5 的记录（只限你自己的聊天）   /unshare c5 c7  撤销
/device [时长|lock]  在自己电脑装本地通道，或打开整机免批时长面板（如 /device 4h、/device 7d、/device 永久、/device lock）
/local [c5|all] [时长|on|off|lock]  本地通道面板或自定义时长（不写 c5 默认管当前聊天，如 /local 30m、/local 24h、/local 永久）
群：你把 bot 拉进群，群就归你。群里发 /bind c5 指定你的哪个聊天负责；/listen all|mention、/open on|off；回复某人发 /activate 让他也能叫醒 bot。
/id  你的用户 id   /language  选语言"""

HELP_MEMBER_EN = f"""Just send a message to talk to the AI in your current chat. The / menu lists your own chats; tap one to switch. Replies from chats you're not in are kept and shown when you switch over.
/new [note]  start a new chat (a new AI picks it up; {LIMIT_EN})
/list  manage your chats: tap a name to switch, or delete the ones you don't need (you can't bring a deleted chat back)
/c5 …  switch to one of your chats   /history  all your chats   /export c5  export a chat
/rename c5 name   /close c5  close (history kept)   /reopen c5   /restart c5  get a new AI for it   /stop c5  stop its AI
/share c5 c7  let c7 read c5's history (your own chats only)   /unshare c5 c7  undo
/device  install the local channel on your computer (no admin approval needed); the AI asks you before it runs anything there
/local c5 on|off|<hours>  turn the local channel on/off, or approve it for some hours
Groups: add the bot to a group and the group is yours. In the group, /bind c5 picks which of your chats handles it; /listen all|mention, /open on|off; reply to someone with /activate to let them wake the bot.
/id  your user id   /language  language"""

LANG_ALIASES = {"en": "en", "english": "en", "zh": "zh", "cn": "zh", "chinese": "zh", "中文": "zh"}

USER_COMMANDS = {
    "en": [
        {"command": "help", "description": "Help"},
        {"command": "id", "description": "Show your user id"},
        {"command": "language", "description": "Language / 语言"},
    ],
    "zh": [
        {"command": "help", "description": "帮助"},
        {"command": "id", "description": "查看你的用户 id"},
        {"command": "language", "description": "语言 / Language"},
    ],
}

MEMBER_COMMANDS = {
    "en": [
        {"command": "new", "description": "➕ New chat"},
        {"command": "list", "description": "🗂 Manage my chats (switch / delete)"},
        {"command": "history", "description": "📜 All my chats"},
        {"command": "device", "description": "Local channel on my computer"},
        {"command": "help", "description": "Help"},
        {"command": "language", "description": "Language / 语言"},
    ],
    "zh": [
        {"command": "new", "description": "➕ 新建聊天"},
        {"command": "list", "description": "🗂 管理我的聊天（切换 / 删除）"},
        {"command": "history", "description": "📜 我的所有聊天"},
        {"command": "device", "description": "在自己电脑上装本地通道"},
        {"command": "help", "description": "帮助"},
        {"command": "language", "description": "语言 / Language"},
    ],
}

GROUP_COMMANDS = {
    "en": [
        {"command": "help", "description": "Help"},
        {"command": "id", "description": "Show the chat id and your user id"},
        {"command": "activate", "description": "Let a member wake the bot (reply to them)"},
        {"command": "language", "description": "Group language / 群语言"},
    ],
    "zh": [
        {"command": "help", "description": "帮助"},
        {"command": "id", "description": "查看 chat id 和用户 id"},
        {"command": "activate", "description": "让成员也能叫醒 bot（回复他）"},
        {"command": "language", "description": "群语言 / Group language"},
    ],
}


def language_buttons() -> dict:
    return {"inline_keyboard": [[
        {"text": "English", "callback_data": "lang:en"},
        {"text": "中文", "callback_data": "lang:zh"},
    ]]}


async def set_lang(chat_id: int, lang: str) -> str:
    """记下这个聊天的语言、换掉它的命令菜单，返回用新语言写的确认。"""
    store.set(f"lang:{chat_id}", lang)
    if is_admin(chat_id):
        return "Language: English. Admin menus and notices are still Chinese only." if lang == "en" else "语言：中文。"
    group = chat_id < 0
    if not group and is_granted(chat_id):
        # 被授权用户的菜单是他的聊天列表，由 refresh_menus 按新语言重建
        MENU["cache"].pop(chat_id, None)
        mark_menu_dirty()
    else:
        commands = (GROUP_COMMANDS if group else USER_COMMANDS)[lang]
        await tg.try_call("setMyCommands", commands=commands, scope={"type": "chat", "chat_id": chat_id})
    if group:
        return "This group's language: English. The AI will reply here in English." if lang == "en" else "本群语言：中文。AI 在这里会用中文回复。"
    return "Language: English. The AI will reply to you in English." if lang == "en" else "语言：中文。AI 会用中文回复你。"


def display_name(user: dict) -> str:
    return user.get("username") or " ".join(
        part for part in (user.get("first_name"), user.get("last_name")) if part
    ) or str(user.get("id", ""))


def pick_file(message: dict) -> tuple[str, str, int, str] | None:
    for kind, default in (("document", "file"), ("video", "video.mp4"), ("audio", "audio"), ("animation", "animation.mp4")):
        item = message.get(kind)
        if item:
            return item["file_id"], item.get("file_name") or default, item.get("file_size") or 0, item.get("mime_type") or ""
    if message.get("voice"):
        item = message["voice"]
        return item["file_id"], "voice.ogg", item.get("file_size") or 0, item.get("mime_type") or "audio/ogg"
    if message.get("photo"):
        item = message["photo"][-1]
        return item["file_id"], f"photo_{message['message_id']}.jpg", item.get("file_size") or 0, "image/jpeg"
    return None


async def save_file(chat_id: int, conv_id: str, picked: tuple[str, str, int, str]) -> str:
    tg_file_id, name, size, mime = picked
    if size > FILE_LIMIT:
        raise ValueError("超过 20MB，Telegram Bot API 不让下载")
    data = await tg.download(tg_file_id)
    file_id = "f_" + secrets.token_hex(5)
    safe = re.sub(r"[^\w.\-]", "_", name)[:80] or "file"
    path = DATA / "files" / f"{file_id}_{safe}"
    path.write_bytes(data)
    mime = mime or mimetypes.guess_type(name)[0] or "application/octet-stream"
    store.run(
        "INSERT INTO files(id,chat_id,tg_file_id,name,size,mime,path,ts,conv) VALUES(?,?,?,?,?,?,?,?,?)",
        (file_id, chat_id, tg_file_id, name, len(data), mime, str(path), now(), conv_id),
    )
    return file_id


def detect_mention(message: dict) -> tuple[bool, bool]:
    text = (message.get("text") or message.get("caption") or "").lower()
    mention = bool(BOT["username"]) and f"@{BOT['username'].lower()}" in text
    for entity in message.get("entities") or message.get("caption_entities") or []:
        if entity.get("type") == "text_mention" and (entity.get("user") or {}).get("id") == BOT["id"]:
            mention = True
    reply_from = (message.get("reply_to_message") or {}).get("from") or {}
    return mention, reply_from.get("id") == BOT["id"]


async def tell_once(chat_id: int, key: str, text: str, every: int = 6 * 3600, en: str | None = None) -> None:
    key = f"notice:{chat_id}:{key}"
    if now() - float(store.get(key, "0") or 0) < every:
        return
    store.set(key, str(now()))
    await tg.try_call("sendMessage", chat_id=chat_id, text=en if en is not None and lang_of(chat_id) == "en" else text)


async def hub_target(message: dict, chat_id: int) -> str:
    """私聊里的消息进哪个聊天：引用了某个聊天的消息就切过去（只限这个私聊能进的聊天），否则进当前选中的。"""
    conv_id = selected(chat_id)
    quoted = (message.get("reply_to_message") or {}).get("message_id")
    if quoted:
        hit = store.one("SELECT conv FROM tgmsgs WHERE chat_id=? AND tg_msg_id=?", (chat_id, quoted))
        if hit and hit["conv"] != conv_id and enterable(chat_id, conv_row(hit["conv"])):
            await switch_to(chat_id, hit["conv"])
            conv_id = hit["conv"]
    return conv_id


async def new_user_conv(dm: int, owner: int, brief: str, announce: bool = True, unsent: bool = False):
    """被授权用户建自己的聊天：归他、发到他的私聊，主控会开子 agent 接手。到上限了就告诉他，返回 None。"""
    if at_limit(owner):
        await reply(dm, ("这条消息没发出去：" if unsent else "") + limit_text(owner, "zh"),
                    en=("That message wasn't delivered. " if unsent else "") + limit_text(owner, "en"))
        return None
    conv = create_conv(brief, dm, owner=owner)
    await switch_to(dm, conv["id"], announce=False)
    system_note("main", task_note(conv, f"用户 {person_label(owner)} 新建了聊天"))
    if announce:
        await reply(
            dm,
            f"已新建聊天 {conv['id']} 并切过去。马上会有一个 AI 接手，你现在发的消息先存着，接手后它会看到。",
            conv_id=conv["id"],
            en=f"Created chat {conv['id']} and switched to it. An AI will pick it up shortly; "
               "anything you send now is kept until it does.",
        )
    return conv


async def ask_admin_grant(user: dict, where: str, group_id: int = 0) -> None:
    """没资格的人来找 bot：给管理员发一条带【授权】按钮的通知，同一个人 6 小时内只发一次。"""
    uid = int(user.get("id") or 0)
    key = f"grantask:{uid}:{group_id}"
    if not uid or now() - float(store.get(key, "0") or 0) < 6 * 3600:
        return
    store.set(key, str(now()))
    buttons = [[{"text": f"授权 {display_name(user)}", "callback_data": f"gr:{uid}:0"}]]
    if group_id and not group_owner(group_id):
        buttons.append([{"text": "授权并在本群激活", "callback_data": f"gr:{uid}:{group_id}"}])
    await notify_admins(f"{person_label(uid)} {where}，但还没有使用资格。", {"inline_keyboard": buttons})


async def ask_group_activate(user: dict, group_id: int) -> None:
    """有资格但没在这个群激活的人 @bot：问群主人（管理员的群就问管理员）要不要激活他。"""
    uid = int(user.get("id") or 0)
    key = f"actask:{uid}:{group_id}"
    if not uid or now() - float(store.get(key, "0") or 0) < 6 * 3600:
        return
    store.set(key, str(now()))
    title = (chat_row(group_id) or {"title": group_id})["title"]
    owner = group_owner(group_id)
    if owner:
        markup = {"inline_keyboard": [[{"text": "激活 / Activate", "callback_data": f"ga:{group_id}:{uid}"}]]}
        await reply(owner, f"{person_label(uid)} 在你的群「{title}」里 @bot，但还没激活。要让他也能叫醒 bot 吗？", markup,
                    en=f"{person_label(uid)} mentioned the bot in your group \"{title}\" but isn't activated there. "
                       "Let them wake the bot?")
    else:
        markup = {"inline_keyboard": [[{"text": "在本群激活他", "callback_data": f"ga:{group_id}:{uid}"}]]}
        await notify_admins(f"{person_label(uid)} 在群「{title}」里 @bot，有资格但还没在这个群激活。", markup)


async def on_message(message: dict) -> None:
    chat = message.get("chat") or {}
    user = message.get("from") or {}
    remember_person(user)
    replied = message.get("reply_to_message") or {}
    remember_person(replied.get("from") or {})
    remember_person((replied.get("forward_origin") or {}).get("sender_user") or replied.get("forward_from") or {})
    if user.get("is_bot") or not chat:
        return
    chat_id, chat_type = chat["id"], chat.get("type", "")
    user_id, name = int(user.get("id") or 0), display_name(user)
    upsert_chat(chat)
    if chat_type == "private":
        known = store.one("SELECT dm_chat_id FROM users WHERE user_id=?", (user_id,))
        store.run("UPDATE users SET name=?, dm_chat_id=? WHERE user_id=?", (name, chat_id, user_id))
        if known is not None and known["dm_chat_id"] != chat_id:
            mark_menu_dirty()
    else:
        store.run("UPDATE users SET name=? WHERE user_id=?", (name, user_id))

    text = message.get("text") or message.get("caption") or ""
    stripped = text.strip()
    if chat_type == "private" and ADMIN_CODE and stripped == ADMIN_CODE:
        await tg.try_call("deleteMessage", chat_id=chat_id, message_id=message["message_id"])
        used = hashlib.sha256(ADMIN_CODE.encode()).hexdigest()
        if store.get("admin_code_used") == used and not is_admin(user_id):
            log.warning("spent admin code tried by user %s", user_id)
            await reply(chat_id, "这个管理员口令已经用过，作废了。要再加管理员：在服务器 .env 里换一个新的 ADMIN_CODE，再重启服务。",
                        en="This admin code has already been used and is no longer valid. To add another admin, "
                           "put a new ADMIN_CODE in the server's .env and restart the service.")
            await notify_admins(f"⚠️ 有人用已作废的管理员口令申请当管理员：{name}（用户 id {user_id}），已拒绝。口令可能泄露了。")
            return
        store.run(
            "INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET role='admin', dm_chat_id=excluded.dm_chat_id",
            (user_id, name, "admin", chat_id, now()),
        )
        store.set("admin_code_used", used)
        await reply(chat_id, "你已是管理员。这个口令从现在起作废，别人再发也没用。\n\n" + HELP_ADMIN)
        mark_menu_dirty()
        return
    if stripped.startswith("/"):
        head, _, rest = stripped.partition(" ")
        command, _, at = head.partition("@")
        if at and BOT["username"] and at.lower() != BOT["username"].lower():
            return
        await on_command(message, command.lower(), rest.strip(), chat_id, chat_type, user_id)
        return
    if chat_type == "private" and stripped and is_admin(user_id):
        pending = new_model_answer(chat_id, message)
        if pending is not None:
            await finish_new(chat_id, pending, stripped)
            return
    if message.get("sticker"):
        text = f"[贴纸 {message['sticker'].get('emoji', '')}]"

    mention, reply_bot = detect_mention(message)
    title = (chat_row(chat_id) or {"title": ""})["title"]
    hub = False
    if chat_type == "private":
        if not is_granted(user_id):
            await tell_once(chat_id, str(user_id), f"你还没有使用资格，已经通知管理员。你的用户 id：{user_id}",
                            en=f"You don't have access yet; I've let the admin know. Your user id: {user_id}")
            await ask_admin_grant(user, "私聊 bot 想用")
            return
        hub = True
        conv = await hub_target(message, chat_id)
        if not conv:
            # 被授权用户还没有开着的聊天：发消息就给他建一个
            created = await new_user_conv(chat_id, user_id, "", unsent=True)
            if created is None:
                return
            conv = created["id"]
        target = conv
        wake = 1
    elif chat_type in ("group", "supergroup"):
        crow = chat_row(chat_id)
        owner = int(crow["owner"] or 0)
        activated = store.one("SELECT 1 FROM activations WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        eligible = (is_admin(user_id) or (owner != 0 and owner == user_id and is_granted(user_id))
                    or bool(crow["open"]) or (is_granted(user_id) and activated is not None))
        conv = route_of(chat_id)
        # 用户的群还没指定聊天时不交给主控：主控不管用户的东西，等群主人 /bind
        target = conv or ("" if owner else "main")
        called = mention or reply_bot
        wake = 1 if target and eligible and (called or crow["listen"] == "all") else 0
        if called and not eligible:
            if not is_granted(user_id):
                await tell_once(chat_id, str(user_id), f"{name}（id {user_id}）还不能使用 bot，已经通知管理员授权。",
                                en=f"{name} (id {user_id}) can't use the bot yet; I've asked the admin for access.")
                await ask_admin_grant(user, f"在群「{title}」里 @bot", chat_id)
            else:
                await tell_once(chat_id, str(user_id), f"{name}（id {user_id}）还没在本群激活，已经问群主人了。",
                                en=f"{name} (id {user_id}) isn't activated in this group yet; I've asked the group's owner.")
                await ask_group_activate(user, chat_id)
        elif called and not target:
            await tell_once(chat_id, "unbound", "这个群还没指定由哪个聊天负责：群主人在群里发 /bind c5（填他自己的聊天）。",
                            en="No chat handles this group yet: the group's owner should send /bind c5 here (one of their chats).")
    else:
        return

    file_id = ""
    picked = pick_file(message)
    if picked:
        try:
            file_id = await save_file(chat_id, conv, picked)
        except Exception as exc:
            text = (text + " " if text else "") + f"[文件 {picked[1]} 接收失败：{exc}]"
    if not text and not file_id:
        return
    post(
        target,
        conv=conv,
        chat_id=chat_id,
        chat_type=chat_type,
        chat_title=title,
        user_id=user_id,
        user_name=name,
        text=text,
        file_id=file_id,
        tg_msg_id=message.get("message_id", 0),
        reply_to_bot=int(reply_bot),
        mention=int(mention),
        wake=wake,
    )
    if target and target != "main":
        reset_dm_streaks_for(target)
    remember_tg(chat_id, [message.get("message_id", 0)], conv)
    if hub:
        state = conv_state(conv_row(target))["state"]
        if chat_id in admin_chats():
            t_row = conv_row(target)
            if away(t_row) and state in ("stuck", "lost", "paused"):
                where_lbl = cloud_tag(cloud_of(t_row))
                here_lbl = cloud_tag(main_cloud())
                m_lbl = effective_conv_model(t_row)
                m_txt = f"（原模型：{m_lbl}）" if m_lbl else ""
                await reply(
                    chat_id,
                    f"💡 {target} 当前在「{where_lbl}」无活跃会话，你刚发的消息已存好。点下方按钮即可迁入 {here_lbl} 让主控按原模型与上下文接手{m_txt}：",
                    hand_over_markup(t_row),
                )
            elif state == "paused":
                await tell_once(chat_id, f"paused:{target}", f"{target} 现在没有子 agent，消息先存着。/restart {target} 让主控重开一个接手。", 1800)
            elif state == "absent":
                await tell_once(chat_id, "nomain", "还没有主控接入，消息先存着。先在 cursor.com/agents 配好这个 MCP，新开一个云端聊天，把 /key 里的开场提示词发给它，这里会弹出【设为主控】。", 1800)
        elif state == "paused":
            await tell_once(chat_id, f"paused:{target}", f"{target} 现在没有 AI，消息先存着。/restart {target} 重开一个。", 1800,
                            en=f"{target} has no AI right now; your messages are kept. /restart {target} to get a new one.")
        elif state in ("pending", "unclaimed") and conv_state(conv_row("main"))["state"] == "absent":
            await tell_once(chat_id, "nomain", "AI 服务暂时不在线，消息先存着，上线后会处理。", 1800,
                            en="The AI service is offline right now; your messages are kept and will be handled when it's back.")


ID_IN_BOT_TEXT = re.compile(r"(?:/grant\s+|id\s*[:：]?\s*)(\d{5,})", re.IGNORECASE)


def origin_user(origin: dict | None, lang: str = "zh") -> tuple[int | None, str]:
    """转发 / 跨聊天回复的原作者。"""
    en = lang == "en"
    if not origin:
        return None, ""
    if origin.get("type") == "user" and (origin.get("sender_user") or {}).get("id"):
        return int(origin["sender_user"]["id"]), ""
    if origin.get("type") == "hidden_user":
        name = origin.get("sender_user_name") or ("They" if en else "他")
        if en:
            return None, (f"{name} hides their account in forwards, so the forwarded message doesn't show their id. "
                          "Reply to their message in a group, or use @username / their numeric id.")
        return None, (f"{name} 开了转发隐私，转发的消息里看不到他的 id。"
                      "请在群里直接回复他的消息，或者用 @用户名 / 数字 id。")
    if en:
        return None, "That message wasn't sent by a person (it came from a channel or an anonymous admin)."
    return None, "那条消息不是某个人发的（来自频道或匿名管理员），找不到人。"


def target_user(message: dict, rest: str, lang: str = "zh") -> tuple[int | None, str]:
    """/grant、/revoke、/activate 作用到谁。返回 (用户 id, '')，找不到时返回 (None, 原因)；原因为空就是没给目标。

    认这些写法：数字 id；@用户名（bot 见过的人）；点名（text_mention）；回复他的消息；
    回复你自己转发进来的他的消息（取原作者）；「回复到其他聊天」引用他的消息；回复 bot 那条带 id 的提示。"""
    en = lang == "en"
    words = rest.split()
    word = words[0] if words else ""
    if word.isdigit():
        return int(word), ""
    if word.startswith("@") and len(word) > 1:
        row = store.one("SELECT user_id FROM people WHERE username=? COLLATE NOCASE", (word[1:],))
        if row is not None:
            return int(row["user_id"]), ""
        if en:
            return None, (f"The bot hasn't seen {word} yet: have them say something in a group with the bot, or message the bot, "
                          "then try again. You can also reply to their message or use their numeric id.")
        return None, (f"bot 还没见过 {word}：让他在群里说句话或者私聊一下 bot 再试；"
                      "也可以直接回复他的消息，或者用数字 id。")
    for entity in message.get("entities") or []:
        if entity.get("type") == "text_mention" and (entity.get("user") or {}).get("id"):
            return int(entity["user"]["id"]), ""
    sender = int((message.get("from") or {}).get("id") or 0)
    replied = message.get("reply_to_message")
    if replied:
        frm = replied.get("from") or {}
        frm_id = int(frm.get("id") or 0)
        origin = replied.get("forward_origin")
        if origin is None and replied.get("forward_from"):
            origin = {"type": "user", "sender_user": replied["forward_from"]}
        elif origin is None and replied.get("forward_sender_name"):
            origin = {"type": "hidden_user", "sender_user_name": replied["forward_sender_name"]}
        if origin is not None and frm_id == sender:
            # 自己转发进来的消息：要找的是原作者，不是转发的人
            return origin_user(origin, lang)
        if frm_id == BOT["id"]:
            hit = ID_IN_BOT_TEXT.search(replied.get("text") or "")
            if hit:
                return int(hit.group(1)), ""
            if en:
                return None, "You replied to the bot's own message. Reply to that person's message, or use @username / their numeric id."
            return None, "你回复的是 bot 自己的消息。请回复那个人的消息，或者用 @用户名 / 数字 id。"
        if frm.get("is_bot"):
            if en:
                return None, "You replied to a bot's message (anonymous admins count too). Use @username / their numeric id."
            return None, "你回复的是 bot 的消息（匿名管理员发的消息也算），找不到人。请用 @用户名 / 数字 id。"
        if frm_id == sender:
            if en:
                return None, "You replied to your own message. Reply to their message, or use @username / their numeric id."
            return None, "你回复的是你自己的消息。请回复他的消息，或者用 @用户名 / 数字 id。"
        if frm_id:
            return frm_id, ""
    if message.get("external_reply"):
        return origin_user((message["external_reply"] or {}).get("origin"), lang)
    return None, ""


async def grant_user(uid: int, group_id: int = 0) -> str:
    """授予使用资格（/grant 和【授权】按钮共用），返回给管理员看的结果。group_id 不为 0 时顺便在那个群激活他。"""
    who = person(uid)
    if uid == BOT["id"] or (who is not None and who["is_bot"]):
        return "不能授权给 bot。"
    role = user_role(uid)
    if role == "admin":
        return f"{person_label(uid)} 是管理员，本来就能用。"
    if group_id:
        store.run("INSERT OR IGNORE INTO activations(chat_id,user_id) VALUES(?,?)", (group_id, uid))
        tail = "也在这个群激活了他：在群里 @bot 或回复 bot 就能叫醒 agent。"
    else:
        tail = "在你的群里要你回复他发 /activate（或回复他发 /grant）。"
    if role == "user":
        return f"{person_label(uid)} 已经有使用资格了。" + (tail if group_id else "")
    dm = uid if (chat_row(uid) or {"type": ""})["type"] == "private" else None
    name = (who["name"] or who["username"]) if who is not None else ""
    store.run("INSERT INTO users(user_id,name,role,dm_chat_id,created) VALUES(?,?,?,?,?)", (uid, name, "user", dm, now()))
    mark_menu_dirty()
    log.info("user %s granted", uid)
    if dm:
        await reply(dm, f"管理员给了你使用资格。直接发消息就会给你建一个 AI 聊天；/new 再建新的（{LIMIT_ZH}），/list 管理，/help 看用法。",
                    en="The admin has given you access. Just send a message and I'll start an AI chat for you; "
                       f"/new starts another one ({LIMIT_EN}), /list manages them, /help shows how it works.")
        told = "已经私聊通知他了。"
    else:
        told = "他还没私聊过 bot，让他私聊 bot 发 /start 就能用。"
    return (f"已授予 {person_label(uid)} 使用资格，{told}\n"
            f"他只能用自己建的聊天（{LIMIT_ZH}）和自己拉 bot 进的群；本地通道他自己 /device 安装、自己批。{tail}")


async def revoke_user(uid: int) -> str:
    if user_role(uid) != "user":
        return f"{person_label(uid)} 不是被授权的用户（管理员不能这样取消）。"
    # 先收回资格和群，再关聊天：关的时候群就算回到管理员手里（交给主控分配），存着的消息也不再补发给他
    store.run("UPDATE chats SET owner=0 WHERE owner=?", (uid,))
    store.run("DELETE FROM users WHERE user_id=? AND role='user'", (uid,))
    store.run("DELETE FROM activations WHERE user_id=?", (uid,))
    for conv in own_convs(uid):
        await close_conv(conv, "管理员取消了这个用户的资格，")
    for dev in store.q("SELECT * FROM devices WHERE owner=? AND status='active' AND id!=?", (uid, ADMIN_DEVICE)):
        await revoke_device(dev, "管理员取消了这个用户的使用资格")
    MENU["cache"].pop(uid, None)
    await tg.try_call("setMyCommands", commands=USER_COMMANDS[lang_of(uid)], scope={"type": "chat", "chat_id": uid})
    mark_menu_dirty()
    log.info("user %s revoked", uid)
    return f"已取消 {person_label(uid)} 的使用资格：他的聊天都关了（记录保留），他的群交回给你，他的本地电脑也作废了。"


def history_text(viewer: int) -> str:
    """/history：管理员看所有人的聊天（标明是谁的），用户只看自己的。viewer 是私聊的 chat_id（就是用户 id）。"""
    admin = is_admin(viewer)
    en = not admin and lang_of(viewer) == "en"
    if admin:
        lines = ["所有聊天（含已关闭，记录都留着）："]
        rows = store.q("SELECT * FROM convs ORDER BY num")
    else:
        lines = ["All your chats (closed ones too; history is kept):" if en else "你的所有聊天（含已关闭，记录都留着）："]
        rows = store.q("SELECT * FROM convs WHERE id!='main' AND owner=? AND status!='deleted' ORDER BY num", (viewer,))
        if not rows:
            return ("You don't have any chats yet. Just send a message, or /new to start one." if en
                    else "你还没有聊天。直接发消息，或者 /new 新建一个。")
    for row in rows:
        stat = store.one(
            "SELECT COUNT(*) AS n, MAX(ts) AS t FROM messages WHERE conv=? AND chat_type!='system'", (row["id"],)
        )
        state = conv_state(row)["state"]
        if row["status"] == "deleted":
            status = f"已删除（{stamp(row['closed'])}）"
        elif en:
            status = f"closed ({stamp(row['closed'])})" if state == "closed" else state_text(state, "en")
        else:
            status = f"已关闭（{stamp(row['closed'])}）" if state == "closed" else STATE_TEXT[state]
        name = conv_name(row) if row["id"] != "main" else "主控"
        cmd = f"/{row['id']}" if enterable(viewer, row) else row["id"]
        line = f"{cmd} {name} · {status} · " + (f"{stat['n']} msgs" if en else f"{stat['n']} 条")
        if stat["t"]:
            line += (f" · last {stamp(stat['t'])}" if en else f" · 最近 {stamp(stat['t'])}")
        if admin and conv_owner(row):
            line += f" · 用户 {person_label(conv_owner(row))} 的"
        if admin and row["id"] != "main" and max_cloud() > 1:
            line += f" · {cloud_tag(cloud_of(row))}"
        sources = share_sources(row["id"])
        if sources:
            line += (" · reads: " + ", ".join(sources)) if en else (" · 可读：" + "、".join(sources))
        repo = git_text(row)
        if repo:
            line += " · GitHub " + repo
        lines.append(line)
    if en:
        lines += ["", "/export c5 exports a chat; /share c5 c7 lets c7 read c5; /unshare c5 c7 undoes it"]
    elif admin:
        lines += ["", "/export c1 导出记录；/share c1 c3 授权 c3 读 c1；/unshare c1 c3 撤销"]
    else:
        lines += ["", "/export c5 导出记录；/share c5 c7 让 c7 读 c5；/unshare c5 c7 撤销"]
    return "\n".join(lines)


def export_text(conv, rows, lang: str = "zh") -> str:
    hubs = set(hub_chats())
    en = lang == "en"
    created = stamp(conv["created"], "%Y-%m-%d %H:%M")
    closed = stamp(conv["closed"], "%Y-%m-%d %H:%M") if conv["closed"] else ""
    if en:
        lines = [f"Chat {conv['id']} \"{conv_name(conv)}\"", f"Created: {created}" + (f"  Closed: {closed}" if closed else "")]
    else:
        lines = [f"聊天 {conv['id']}「{conv_name(conv)}」", f"创建：{created}" + (f"  关闭：{closed}" if closed else "")]
    if conv["brief"]:
        lines.append(f"Note: {conv['brief']}" if en else f"说明：{conv['brief']}")
    lines += [f"{len(rows)} messages" if en else f"共 {len(rows)} 条", ""]
    for row in rows:
        when = stamp(row["ts"], "%Y-%m-%d %H:%M:%S")
        if row["chat_type"] == "system":
            where = "[system] " if en else "【系统】"
        elif row["chat_id"] in hubs:
            where = ""
        elif en:
            where = f"[{'group' if row['chat_type'] != 'private' else 'private'} {row['chat_title']}] "
        else:
            where = f"【{'群' if row['chat_type'] != 'private' else '私聊'} {row['chat_title']}】"
        who = f"[{row['user_name']}]" if row["outgoing"] else (row["user_name"] or str(row["user_id"]))
        text = row["text"] or ""
        if row["file_id"]:
            text = (text + " " if text else "") + file_note(row["file_id"])
        lines.append(f"{when} {where}{who}: {text}")
    return "\n".join(lines) + "\n"


def may_share(user_id: int, reader, source) -> bool:
    """user_id 能不能让 reader 读 source：两个聊天都得归他管；用户的聊天只能读同一个用户的聊天。"""
    if reader is None or source is None or reader["id"] == "main" or reader["id"] == source["id"]:
        return False
    if not can_manage(user_id, reader) or not can_manage(user_id, source):
        return False
    return conv_owner(reader) == 0 or conv_owner(source) == conv_owner(reader)


def share_keyboard(reader: str) -> dict:
    """新聊天能读哪些旧聊天：只列同一个主人的 TG 聊天（排除纯后台派生子 agent 免得挤爆按钮）。"""
    owner = conv_owner(conv_row(reader))
    en = bool(owner) and lang_of(owner) == "en"
    rows = store.q(
        "SELECT * FROM convs WHERE id NOT IN ('main', ?) AND owner=? AND status!='deleted' AND IFNULL(in_tg,1)=1 ORDER BY num DESC LIMIT 30",
        (reader, owner),
    )
    buttons = []
    for row in rows:
        mark = "✅ " if shared(reader, row["id"]) else ""
        closed = (" (closed)" if en else "（已关闭）") if row["status"] != "open" else ""
        buttons.append([{"text": f"{mark}{conv_button(row)}{closed}", "callback_data": f"sh:{reader}:{row['id']}"}])
    buttons.append([{"text": "Done" if en else "完成", "callback_data": f"shd:{reader}"}])
    return {"inline_keyboard": buttons}


async def close_conv(conv, by: str) -> None:
    home = home_of(conv)
    if home and is_hub(home) and unread_count(conv["id"], home):
        async with dm_lock(home):
            await reply(home, f"{conv_tag(conv)} 关闭前还有没看的消息：", conv_id=conv["id"],
                        en=f"{conv_tag(conv)} had messages you haven't seen before it closed:")
            await flush_locked(home, conv["id"])
    old = active_agent(conv)
    if old is not None:
        stop_identity(old["id"], f"{by}关闭了这个聊天")
    elif conv["task_code"]:
        system_note("main", f"{conv_tag(conv)} 还没有子 agent 接手就被关闭了：它的任务作废，还没开子 agent 的话就不用开了。", wake=0)
    chats = routed_chats(conv["id"])
    release_node_locks_for_conv(conv["id"])
    store.run("DELETE FROM routes WHERE conv=?", (conv["id"],))
    store.run("DELETE FROM agent_group_members WHERE conv=?", (conv["id"],))
    store.run("UPDATE agent_traces SET phase='stopped', updated_ts=? WHERE conv=?", (now(), conv["id"]))
    store.run(
        "UPDATE convs SET status='closed', closed=?, agent='', task_code='', task_agent_id='', alert='', alert_ts=0 WHERE id=?",
        (now(), conv["id"]),
    )
    owner = conv_owner(conv)
    if chats and owner and is_granted(owner):
        # 用户的群不归主控管，告诉群主人换一个聊天负责
        await reply(
            owner,
            f"{conv_tag(conv)} 关了，{'、'.join(chat_label(c) for c in chats)} 现在没有聊天负责：在群里发 /bind c5 换一个你的聊天。",
            en=f"{conv_tag(conv)} is closed, so nothing handles {', '.join(chat_label(c, 'en') for c in chats)} now. "
               "Send /bind c5 in the group to pick another of your chats.",
        )
    elif chats:
        system_note(
            route_control_target(),
            f"{conv_tag(conv)} 已关闭，它负责的 {'、'.join(chat_label(c) for c in chats)} 现在【未分配】，有消息会先到你这里。",
            wake=0,
        )
    mark_menu_dirty()


async def delete_conv(conv, by: str) -> None:
    """删除 = 关掉并从主人的列表里去掉（也不再算进他的聊天数）。记录留在服务器：管理员 /history 看得到，/export 能导出。"""
    if conv["status"] == "open":
        await close_conv(conv, by)
    store.run("UPDATE convs SET status='deleted', closed=? WHERE id=?", (now(), conv["id"]))
    store.run("DELETE FROM shares WHERE reader=? OR source=?", (conv["id"], conv["id"]))
    deny_local_requests(conv_id=conv["id"])
    log.info("conv %s deleted by %s", conv["id"], by)
    mark_menu_dirty()


def list_rows(viewer: int) -> list:
    if is_admin(viewer):
        rows = [
            r for r in store.q("SELECT * FROM convs WHERE status!='deleted' AND IFNULL(in_tg,1)=1 ORDER BY IFNULL(owner,0)!=0, owner, num")
            if not is_system_conv_id(r["id"])
        ]
        order = {n: i for i, n in enumerate(cloud_order({cloud_of(r) for r in rows} | {main_cloud()}))}
        return sorted(rows, key=lambda r: order[cloud_of(r)])
    return [
        r for r in store.q("SELECT * FROM convs WHERE owner=? AND status!='deleted' AND IFNULL(in_tg,1)=1 ORDER BY num", (viewer,))
        if not is_system_conv_id(r["id"])
    ]


def hand_over_view(conv, page: int) -> tuple[str, dict]:
    here = cloud_tag(main_cloud())
    state = conv_state(conv)["state"]
    text = (f"把 {conv_tag(conv)} 从 {cloud_tag(cloud_of(conv))} 交给 {here} 主控吗？它现在 {STATE_TEXT[state]}。\n"
            f"旧的子 agent 会停掉，{here} 主控开一个新的接手，聊天记录和 GitHub 分支都带过去。")
    if state in ("online", "busy"):
        text += "\n注意：它的子 agent 现在还在干活，交过去它就停了。"
    return text, {"inline_keyboard": [[
        {"text": f"↪ 交给 {here} 主控", "callback_data": f"hvok:{conv['id']}:{page}"},
        {"text": "取消", "callback_data": f"ls:{page}"},
    ]]}


def list_view(viewer: int, page: int = 0, note: str = "") -> tuple[str, dict | None]:
    """/list：点名字切过去，点删除先确认。管理员看所有人的聊天（只能切到自己的），用户只看自己的。"""
    admin = is_admin(viewer)
    en = not admin and lang_of(viewer) == "en"
    rows = list_rows(viewer)
    if admin:
        quota = f"用户每人最多 {CHAT_LIMIT} 个" if CHAT_LIMIT > 0 else "用户也不限"
        head = (f"所有聊天（你的不限数量，{quota}）。点名字切过去（只能切到你自己的），点「删除」删掉："
                "删掉的聊天会关掉、从列表里去掉，记录还在，/history 看得到，/export 能导出。")
        empty = "还没有聊天。/new 新建一个。"
    elif en:
        quota = f" ({len(rows)}/{CHAT_LIMIT}, closed ones count too)" if CHAT_LIMIT > 0 else ""
        head = (f"Your chats{quota}. Tap a name to switch to it, or Delete to remove it: "
                "a deleted chat is closed and taken off your list, and you can't bring it back yourself.")
        empty = "You don't have any chats yet. Just send a message, or /new to start one."
    else:
        quota = f"（{len(rows)}/{CHAT_LIMIT}，关了的也算）" if CHAT_LIMIT > 0 else ""
        head = f"你的聊天{quota}。点名字切过去，点「删除」删掉：删掉的聊天会关掉、从你的列表里去掉，你自己没法恢复。"
        empty = "你还没有聊天。直接发消息，或者 /new 新建一个。"
    if not rows:
        return "\n\n".join(p for p in (note, empty) if p), None
    pages = (len(rows) + LIST_PAGE - 1) // LIST_PAGE
    page = min(max(page, 0), pages - 1)
    current = selected(viewer)
    multi = admin and len({cloud_of(r) for r in rows} | {main_cloud()}) > 1
    if multi:
        head += f"\n按 cloud 分段；「↪ {cloud_tag(main_cloud())}」= 交给当前主控（保留原模型与上下文），或点顶部打开 Cloud 批量迁移/删除面板。"
    buttons = []
    if multi:
        buttons.append([{"text": "☁️ Cloud 管理 / 批量迁移 / 删除旧Cloud", "callback_data": "cm:home"}])
    section = None
    for row in rows[page * LIST_PAGE:(page + 1) * LIST_PAGE]:
        if multi and cloud_of(row) != section:
            section = cloud_of(row)
            sec_desc = "主控" if section == main_cloud() else ("静默待机" if section == UNOWNED_CLOUD else "旧cloud")
            buttons.append([{"text": f"📁 {cloud_tag(section)} · {sec_desc}",
                             "callback_data": "cm:home"}])
        label = conv_button(row)
        if row["status"] != "open":
            label += " (closed)" if en else "（已关闭）"
        if admin and conv_owner(row):
            label += f" · {person_short(conv_owner(row))}"
        if row["id"] == current:
            label = "👉 " + label
        line = [{"text": label[:64], "callback_data": f"sw:{row['id']}:{page}"},
                {"text": "🗑 Delete" if en else "🗑 删除", "callback_data": f"dl:{row['id']}:{page}"}]
        if admin and row["status"] == "open" and away(row):
            line.insert(1, {"text": f"↪ {cloud_tag(main_cloud())}", "callback_data": f"hv:{row['id']}:{page}"})
        buttons.append(line)
    if pages > 1:
        head += f"\n（第 {page + 1}/{pages} 页）" if not en else f"\n(page {page + 1}/{pages})"
        nav = []
        if page > 0:
            nav.append({"text": "◀ Prev" if en else "◀ 上一页", "callback_data": f"ls:{page - 1}"})
        if page < pages - 1:
            nav.append({"text": "Next ▶" if en else "下一页 ▶", "callback_data": f"ls:{page + 1}"})
        buttons.append(nav)
    return "\n\n".join(p for p in (note, head) if p), {"inline_keyboard": buttons}


def delete_view(viewer: int, conv, page: int) -> tuple[str, dict]:
    admin = is_admin(viewer)
    en = not admin and lang_of(viewer) == "en"
    owner = conv_owner(conv)
    if en:
        text = (f"Delete {conv_tag(conv)}?\nIt will be closed (its AI stops) and taken off your list, "
                "and you can't bring it back yourself.")
    elif admin:
        text = (f"确定删除 {conv_tag(conv)} 吗？\n聊天会关掉（子 agent 停掉）、从列表里去掉；记录还在，"
                f"/history 看得到，/export {conv['id']} 能导出，/reopen {conv['id']} 能重开。")
        if owner:
            text += f"\n这是用户 {person_label(owner)} 的聊天，删掉后会通知他。"
    else:
        text = f"确定删除 {conv_tag(conv)} 吗？\n聊天会关掉（AI 停掉）、从你的列表里去掉，你自己没法恢复。"
    return text, {"inline_keyboard": [[
        {"text": "🗑 Yes, delete" if en else "🗑 确认删除", "callback_data": f"dlok:{conv['id']}:{page}"},
        {"text": "Cancel" if en else "取消", "callback_data": f"ls:{page}"},
    ]]}


NEW_MODEL_SEC = env_int("NEW_MODEL_SEC", 1800)
NEW_MODEL_QUESTION = "新聊天用什么模型？不指定就点「默认」，子 agent 继承主控的模型；要指定就点「指定模型」，再打字说是什么模型。"
NEW_MODEL_PROMPT = "回复这条消息，写新聊天要用的模型（比如 gpt-5、claude opus，写个大概就行，主控会选最接近的）。"


def pending_new(chat_id: int) -> dict | None:
    """管理员 /new 之后还没选模型的那次新建；过期了就当没有。"""
    raw = store.get(f"newmodel:{chat_id}")
    try:
        pending = json.loads(raw) if raw else None
    except ValueError:
        pending = None
    if not isinstance(pending, dict) or now() - float(pending.get("ts") or 0) > NEW_MODEL_SEC:
        if raw:
            store.delete(f"newmodel:{chat_id}")
        return None
    return pending


async def ask_new_model(chat_id: int, brief: str) -> None:
    nonce = secrets.token_hex(4)
    markup = {"inline_keyboard": [
        [{"text": "默认（继承主控）", "callback_data": f"nm:d:{nonce}"}, {"text": "指定模型", "callback_data": f"nm:m:{nonce}"}],
        [{"text": "取消", "callback_data": f"nm:x:{nonce}"}],
    ]}
    sent = await tg.try_call("sendMessage", chat_id=chat_id, text=NEW_MODEL_QUESTION, reply_markup=markup)
    store.set(f"newmodel:{chat_id}", json.dumps(
        {"brief": brief, "nonce": nonce, "ts": now(), "msg": (sent or {}).get("message_id", 0), "prompt": 0}))


async def prompt_new_model(chat_id: int, pending: dict) -> None:
    sent = await tg.try_call("sendMessage", chat_id=chat_id, text=NEW_MODEL_PROMPT,
                             reply_markup={"force_reply": True, "input_field_placeholder": "模型名"})
    pending.update(prompt=(sent or {}).get("message_id", 0), ts=now())
    store.set(f"newmodel:{chat_id}", json.dumps(pending))


def new_model_answer(chat_id: int, message: dict) -> dict | None:
    """只认回复选模型那条或「指定模型」提示的消息，免得把发给别的聊天的话当成模型名。"""
    quoted = (message.get("reply_to_message") or {}).get("message_id")
    pending = pending_new(chat_id) if quoted else None
    if pending and quoted in (pending.get("msg"), pending.get("prompt")):
        return pending
    return None


async def finish_new(chat_id: int, pending: dict, model: str) -> None:
    store.delete(f"newmodel:{chat_id}")
    model = " ".join(model.split())[:100]
    if pending.get("msg"):
        label = f"模型：{model}" if model else "模型：默认（继承主控）"
        await tg.try_call("editMessageText", chat_id=chat_id, message_id=pending["msg"],
                          text=f"{NEW_MODEL_QUESTION}\n\n【{label}】")
    await cmd_new(chat_id, pending.get("brief") or "", model)


async def cmd_new(chat_id: int, brief: str, model: str | None = None) -> None:
    if is_admin(chat_id) and model is None:
        await ask_new_model(chat_id, brief)
        return
    has_launcher = select_best_launcher() is not None
    main_away = not has_launcher and conv_state(conv_row("main"))["state"] not in ("online", "busy")
    if is_admin(chat_id):
        conv = create_conv(brief, chat_id, model=model or "")
        await switch_to(chat_id, conv["id"], announce=False)
        dispatch_conv_to_cluster(conv, "管理员新建了聊天", requester="admin")
        text = (
            f"已新建聊天 {conv['id']}，已切换过去（⚪ 等待接手）。总控将调度主 Agent 开子 agent 接手，名字由它自己取。"
            "你现在发的消息会先存着，接手后它会看到。"
            + (f"\n模型：{model}（严格按此模型启动）" if model else "\n模型：默认（继承默认模型）")
        )
        if main_away:
            text += "\n注意：当前暂无在线主 Agent，任务先存着，上线后会处理。"
        en = None
    else:
        conv = await new_user_conv(chat_id, chat_id, brief, announce=False)
        if conv is None:
            return
        text = f"已新建聊天 {conv['id']} 并切过去。马上会有一个 AI 接手，你现在发的消息先存着，接手后它会看到。"
        en = (f"Created chat {conv['id']} and switched to it. An AI will pick it up shortly; "
              "anything you send now is kept until it does.")
        if main_away:
            text += "\n注意：AI 服务暂时不在线，任务先存着，上线后会处理。"
            en += "\nNote: the AI service is offline right now; this chat will be picked up when it's back."
        if at_limit(chat_id):
            text += f"\n你现在有 {CHAT_LIMIT} 个聊天，到上限了：以后要新建，先 /list 删掉不用的。"
            en += f"\nYou now have {CHAT_LIMIT} chats, which is the limit. To start another later, delete one with /list first."
    others = store.one("SELECT COUNT(*) AS n FROM convs WHERE id NOT IN ('main', ?) AND owner=? AND status!='deleted'",
                       (conv["id"], conv_owner(conv)))["n"]
    if others:
        text += "\n\n要让新聊天读取之前哪个聊天的记录？点了才授权（可以多选，再点一次取消），不需要就点「完成」。"
        if en is not None:
            en += "\n\nShould the new chat be able to read any of your earlier chats? Tap to allow (you can pick several; tap again to undo), or tap Done."
        await reply(chat_id, text, share_keyboard(conv["id"]), conv_id=conv["id"], en=en)
    else:
        await reply(chat_id, text, conv_id=conv["id"], en=en)


async def cmd_export(chat_id: int, user_id: int, rest: str) -> None:
    conv_id = parse_conv(rest)
    conv = conv_row(conv_id) if conv_id else None
    if conv is None or not can_manage(user_id, conv):
        await reply(chat_id, "用法：/export c1（/history 看所有聊天）", en="Usage: /export c5 (/history lists your chats)")
        return
    lang = "zh" if is_admin(user_id) else lang_of(chat_id)
    rows = [r for r in store.q("SELECT * FROM messages WHERE conv=? ORDER BY id", (conv["id"],)) if not is_keepalive(r)]
    safe = re.sub(r"[^\w\-]", "_", conv_name(conv))[:30]
    filename = f"{conv['id']}-{safe}-{stamp(now(), '%Y%m%d-%H%M')}.txt"
    caption = (f"{conv_tag(conv)} chat history, {len(rows)} messages" if lang == "en"
               else f"{conv_tag(conv)} 的聊天记录，共 {len(rows)} 条")
    try:
        await tg.send_document(chat_id, filename, export_text(conv, rows, lang).encode("utf-8"), caption=caption)
    except Exception as exc:
        await reply(chat_id, f"导出失败：{exc}", en=f"Export failed: {exc}")


def release_pending_for_device(dev_id: str, conv_id: str = "") -> int:
    """当用户在 /device 或 /local 主动授权后，顺便把正在挂起等待批准的同类本地请求立即放行。"""
    dev = device_row(dev_id)
    if dev is None:
        return 0
    released = 0
    for other in store.q("SELECT id, payload FROM approvals WHERE kind='local' AND status='pending'"):
        opay = json.loads(other["payload"] or "{}")
        if opay.get("device", ADMIN_DEVICE) != dev_id:
            continue
        ocid = opay.get("conv", "")
        if conv_id and ocid != conv_id:
            continue
        ocrow = conv_row(ocid)
        if ocrow is None:
            continue
        if not conv_id and not (
            (is_admin_device(dev) and conv_owner(ocrow) == 0)
            or (not is_admin_device(dev) and conv_owner(ocrow) == int(dev["owner"] or 0))
        ):
            continue
        set_approval(other["id"], "approved")
        released += 1
    return released


def device_panel(dev, viewer_id: int, note: str = "") -> tuple[str, dict]:
    en = not is_admin(viewer_id) and lang_of(viewer_id) == "en"
    dev = device_row(dev["id"])
    online = dev["id"] in LOCAL["clients"]
    a_until = float(dev["auth_until"] or 0)
    wsec = device_window_sec(dev)
    convs = [r for r in open_convs() if (d := conv_device(r)) is not None and d["id"] == dev["id"] and can_manage(viewer_id, r)]

    if en:
        status_s = "🟢 online" if online else "⚪ offline (local_client.py not running)"
        if a_until > now():
            pass_s = "🟢 Forever (all your chats run without asking)" if a_until - now() >= PERMANENT_THRESHOLD else f"🟢 Active ({short_span(a_until - now(), 'en')} left for all your chats)"
        else:
            pass_s = "⚪ Off (approved per chat)"
        win_s = "Ask every operation" if wsec <= 0 else short_span(wsec, "en")
        chat_items = []
        for c in convs[:15]:
            cu = float(c["local_until"] or 0) if c["local_dev"] == dev["id"] else 0.0
            if not c["local_enabled"]:
                chat_items.append(f"{c['id']}(off)")
            elif cu > now():
                chat_items.append(f"{c['id']}({'forever' if cu - now() >= PERMANENT_THRESHOLD else short_span(cu - now(), 'en')})")
            else:
                chat_items.append(c["id"])
        lines = [
            f"💻 Computer: {device_label(dev, 'en')}  {status_s}",
            f"• Computer-wide pass: {pass_s}",
            f"• Default popup approval window: {win_s}",
            f"• Chats using it: {', '.join(chat_items) or 'none'}",
            "",
            "Custom commands: /device 45m | /device 8h | /device 7d | /device forever | /device lock | /device window 1h30m | /device reset | /device del",
        ]
        kb = [
            [
                {"text": "🔓 Pass 1h", "callback_data": f"ldv:{dev['id']}:p:3600"},
                {"text": "4h", "callback_data": f"ldv:{dev['id']}:p:14400"},
                {"text": "24h", "callback_data": f"ldv:{dev['id']}:p:86400"},
                {"text": "7d", "callback_data": f"ldv:{dev['id']}:p:604800"},
                {"text": "Forever", "callback_data": f"ldv:{dev['id']}:p:{PERMANENT_SEC}"},
            ],
            [
                {"text": "⏱ Def:Once", "callback_data": f"ldv:{dev['id']}:w:0"},
                {"text": "30m", "callback_data": f"ldv:{dev['id']}:w:1800"},
                {"text": "2h", "callback_data": f"ldv:{dev['id']}:w:7200"},
                {"text": "24h", "callback_data": f"ldv:{dev['id']}:w:86400"},
                {"text": "Forever", "callback_data": f"ldv:{dev['id']}:w:{PERMANENT_SEC}"},
            ],
            [
                {"text": "🔒 Revoke all active authorizations now", "callback_data": f"ldv:{dev['id']}:lock:0"},
            ],
        ]
    else:
        status_s = "🟢 在线" if online else "⚪ 不在线（local_client.py 没开）"
        if a_until > now():
            pass_s = "🟢 永久免批（你名下所有聊天直接放行）" if a_until - now() >= PERMANENT_THRESHOLD else f"🟢 开启中（剩余 {human_dur(a_until - now())}，你名下所有聊天免批）"
        else:
            pass_s = "⚪ 未开启（按各聊天单独计时）"
        win_s = "每次逐条确认（0）" if wsec <= 0 else short_span(wsec)
        chat_items = []
        for c in convs[:15]:
            cu = float(c["local_until"] or 0) if c["local_dev"] == dev["id"] else 0.0
            if not c["local_enabled"]:
                chat_items.append(f"{c['id']}(已关)")
            elif cu > now():
                chat_items.append(f"{c['id']}({'永久' if cu - now() >= PERMANENT_THRESHOLD else human_dur(cu - now())})")
            else:
                chat_items.append(c["id"])
        lines = [
            f"💻 本地电脑：{device_label(dev)}  {status_s}",
            f"• 整机免批通行：{pass_s}",
            f"• 弹窗默认批准时长：{win_s}",
            f"• 关联聊天：{'、'.join(chat_items) + ('…' if len(convs) > 15 else '') if chat_items else '暂无'}",
            "",
            "任意自定义时长命令：/device 45m | /device 6h | /device 3d | /device 永久 | /device lock（一键收回）\n"
            "改默认弹窗时长：/device window 30m（或 0=每次问 / 12h / 永久）\n"
            "重发安装包：/device reset（新装另一台发 /device install） | 删除电脑：/device del",
        ]
        kb = [
            [
                {"text": "🔓 整机1h", "callback_data": f"ldv:{dev['id']}:p:3600"},
                {"text": "4h", "callback_data": f"ldv:{dev['id']}:p:14400"},
                {"text": "24h", "callback_data": f"ldv:{dev['id']}:p:86400"},
                {"text": "7天", "callback_data": f"ldv:{dev['id']}:p:604800"},
                {"text": "永久", "callback_data": f"ldv:{dev['id']}:p:{PERMANENT_SEC}"},
            ],
            [
                {"text": "⏱ 默认:每次问", "callback_data": f"ldv:{dev['id']}:w:0"},
                {"text": "30m", "callback_data": f"ldv:{dev['id']}:w:1800"},
                {"text": "2h", "callback_data": f"ldv:{dev['id']}:w:7200"},
                {"text": "24h", "callback_data": f"ldv:{dev['id']}:w:86400"},
                {"text": "永久", "callback_data": f"ldv:{dev['id']}:w:{PERMANENT_SEC}"},
            ],
            [
                {"text": "🔒 一键收回本机与所有聊天授权", "callback_data": f"ldv:{dev['id']}:lock:0"},
            ],
        ]
        if is_admin(viewer_id):
            my_devs = admin_owned_devices()
            pref = preferred_admin_device()
        else:
            my_devs = user_devices(viewer_id)
            pref = user_device(viewer_id)
        if len(my_devs) > 1:
            row_btns = []
            for ad in my_devs[:5]:
                star = "⭐" if pref and pref["id"] == ad["id"] else ""
                on_dot = "🟢" if ad["id"] in LOCAL["clients"] else "⚪"
                row_btns.append({"text": f"{star}{on_dot}{ad['id']}", "callback_data": f"ldv:{ad['id']}:def:0"})
            kb.append(row_btns)
        kb.append([{"text": "➕ 新增另一台电脑 (/device add)", "callback_data": f"ldv:{dev['id']}:add:0"}])
    full_text = (f"✅ {note}\n\n" if note else "") + "\n".join(lines)
    return full_text, {"inline_keyboard": kb}


def local_conv_panel(conv, viewer_id: int, note: str = "") -> tuple[str, dict]:
    en = not is_admin(viewer_id) and lang_of(viewer_id) == "en"
    conv = conv_row(conv["id"])
    dev = conv_device(conv)
    enabled = bool(conv["local_enabled"])
    eff = effective_local_until(conv, dev) if enabled and dev is not None else 0.0
    can_grant = dev is not None and may_approve(dev, viewer_id)

    if en:
        dev_s = f"{device_label(dev, 'en')} ({'🟢 online' if dev['id'] in LOCAL['clients'] else '⚪ offline'})" if dev else "none (send /device to install)"
        if not enabled:
            auth_s = "📴 Disabled"
        elif eff > now():
            via = " (via computer-wide pass)" if dev and float(dev["auth_until"] or 0) >= eff and float(dev["auth_until"] or 0) > now() else ""
            auth_s = ("🟢 Forever" if eff - now() >= PERMANENT_THRESHOLD else f"🟢 {short_span(eff - now(), 'en')} left") + via
        else:
            auth_s = "⚪ Will ask when needed"
        lines = [
            f"🔧 Local channel for {conv_tag(conv)}",
            f"• Switch: {'ON' if enabled else 'OFF'}",
            f"• Computer: {dev_s}",
            f"• Authorization: {auth_s}",
            "",
            f"Custom commands (chat id optional when inside chat): /local 45m | /local 12h | /local 7d | /local forever | /local lock | /local off | /local all 24h",
        ]
        kb = []
        if can_grant:
            kb.append([
                {"text": "✅ 30m", "callback_data": f"llc:{conv['id']}:s:1800"},
                {"text": "2h", "callback_data": f"llc:{conv['id']}:s:7200"},
                {"text": "12h", "callback_data": f"llc:{conv['id']}:s:43200"},
                {"text": "24h", "callback_data": f"llc:{conv['id']}:s:86400"},
                {"text": "7d", "callback_data": f"llc:{conv['id']}:s:604800"},
                {"text": "Forever", "callback_data": f"llc:{conv['id']}:s:{PERMANENT_SEC}"},
            ])
        ctrl = []
        if can_grant:
            ctrl.append({"text": "🔒 Revoke window", "callback_data": f"llc:{conv['id']}:lock:0"})
        ctrl.append({"text": "📴 Turn OFF" if enabled else "🟢 Turn ON", "callback_data": f"llc:{conv['id']}:{'off' if enabled else 'on'}:0"})
        kb.append(ctrl)
    else:
        dev_s = f"{device_label(dev)}（{'🟢 在线' if dev['id'] in LOCAL['clients'] else '⚪ 不在线'}）" if dev else "未配置（发 /device 安装）"
        if not enabled:
            auth_s = "📴 本地通道已关闭"
        elif eff > now():
            inh_u = inherited_conv_until(conv, dev["id"]) if dev else 0.0
            if dev and float(dev["auth_until"] or 0) >= eff and float(dev["auth_until"] or 0) > now():
                via = "（来自 /device 整机免批）"
            elif inh_u >= eff and inh_u > now() and conv["id"] != "main":
                via = "（自动继承自主控/父agent授权）"
            elif conv["id"] == "main":
                via = "（主控已授权：你名下所有子 agent 自动跟着共享此授权！）"
            else:
                via = ""
            auth_s = ("🟢 永久免批" if eff - now() >= PERMANENT_THRESHOLD else f"🟢 剩余 {human_dur(eff - now())}") + via
        else:
            auth_s = "⚪ 未预授权（首次调用时弹窗询问）"
        bind_mode = f"指定绑定 {conv['device']}" if conv["device"] else "自动匹配"
        title_s = "主控 main（授权后名下所有子 agent 自动跟着授权！）" if conv["id"] == "main" else f"聊天 {conv_tag(conv)}"
        lines = [
            f"🔧 {title_s} 本地通道管理",
            f"• 通道开关：{'🟢 已开启' if enabled else '📴 已关闭'}",
            f"• 目标电脑：{dev_s}（{bind_mode}）",
            f"• 当前授权：{auth_s}",
            "",
            "任意自定义时长（在当前聊天内可省略编号）：\n"
            f"/local 45m | /local 6h | /local 7d | /local 永久 | /local lock | /local off\n"
            "批量授权名下所有聊天：/local all 24h（或 /local all 永久、/local all lock）",
        ]
        kb = []
        if can_grant:
            kb.append([
                {"text": "✅ 30m", "callback_data": f"llc:{conv['id']}:s:1800"},
                {"text": "2h", "callback_data": f"llc:{conv['id']}:s:7200"},
                {"text": "12h", "callback_data": f"llc:{conv['id']}:s:43200"},
                {"text": "24h", "callback_data": f"llc:{conv['id']}:s:86400"},
                {"text": "7天", "callback_data": f"llc:{conv['id']}:s:604800"},
                {"text": "永久", "callback_data": f"llc:{conv['id']}:s:{PERMANENT_SEC}"},
            ])
        ctrl = []
        if can_grant:
            ctrl.append({"text": "🔒 收回本聊天授权", "callback_data": f"llc:{conv['id']}:lock:0"})
        ctrl.append({"text": "📴 关闭通道" if enabled else "🟢 开启通道", "callback_data": f"llc:{conv['id']}:{'off' if enabled else 'on'}:0"})
        kb.append(ctrl)
    full_text = (f"✅ {note}\n\n" if note else "") + "\n".join(lines)
    return full_text, {"inline_keyboard": kb}


async def cmd_device(message: dict, chat_id: int, user_id: int, arg: str) -> None:
    admin = is_admin(user_id)
    tokens = arg.split()
    picked_dev = None
    if tokens and re.fullmatch(r"d\d+", tokens[0].lower()):
        cand = device_row(tokens[0].lower())
        if cand is not None and cand["status"] == "active" and may_approve(cand, user_id):
            picked_dev = cand
            tokens = tokens[1:]
            arg = " ".join(tokens).strip()

    dev = picked_dev or owner_primary_device(user_id)
    sub = tokens[0].lower() if tokens else ""

    if sub in ("add", "install", "new"):
        name = display_name(message.get("from") or {})
        custom_lbl = " ".join(tokens[1:]).strip()
        new_dev = await issue_device(user_id, name, create_new=True, custom_label=custom_lbl)
        if admin and not store.get("admin_default_device").strip():
            store.set("admin_default_device", new_dev["id"])
        await reply(
            chat_id,
            f"已为你新增独立电脑安装包：{device_label(new_dev)}（原有电脑连接保持不断开，多台电脑可同时在线；发 /device 切换默认电脑或用 /local c1 device {new_dev['id']} 绑定指定聊天）。",
            en=f"Added new computer {device_label(new_dev, 'en')} (your existing computers stay connected).",
        )
        return

    if arg == "":
        if dev is not None:
            text, markup = device_panel(dev, user_id)
            await reply(chat_id, text, markup)
            return
        name = display_name(message.get("from") or {})
        dev = await issue_device(user_id, name, create_new=True)
        if admin:
            store.set("admin_default_device", dev["id"])
            await reply(chat_id, f"已设为管理员默认本地电脑：{device_label(dev)}（以后你的聊天自动连这台；有第二台电脑随时发 /device add 笔记本）。")
            return
        for row in store.q("SELECT id FROM approvals WHERE kind='device' AND status='pending'"):
            if approval_payload(row["id"]).get("user_id") == user_id:
                set_approval(row["id"], "done")
        await notify_admins(f"用户 {person_label(user_id)} 在自己电脑上装了本地通道 {device_label(dev)}。"
                            "只有他自己的聊天会用这台电脑，执行操作要他本人批准。")
        return

    if sub == "default" and len(tokens) >= 2:
        did = tokens[1].lower()
        target_d = device_row(did)
        if target_d is None or target_d["status"] != "active" or not may_approve(target_d, user_id):
            await reply(chat_id, "只能把你自己的活跃电脑（如 d3、d4）设为默认电脑。/devices 查看列表。")
            return
        if admin:
            store.set("admin_default_device", target_d["id"])
        else:
            store.set(f"user_default_device:{user_id}", target_d["id"])
        text, markup = device_panel(target_d, user_id, f"已将 {device_label(target_d)} 设为默认电脑")
        await reply(chat_id, text, markup)
        return

    if dev is None:
        await reply(chat_id, "你还没有本地电脑，先发 /device 安装（多设备可用 /device add）。", en="You don't have a local computer yet. Send /device to set one up.")
        return

    if sub == "reset":
        if admin and dev["id"] == ADMIN_DEVICE:
            await reply(chat_id, "d0 用的是服务器 .env 里的 CLIENT_TOKEN；想新增独立电脑发 /device add。")
            return
        await issue_device(user_id, display_name(message.get("from") or ""), create_new=False, target_dev_id=dev["id"])
        return

    if sub == "del" and len(tokens) in (1, 2):
        del_dev = device_row(tokens[1].lower()) if len(tokens) == 2 else dev
        if del_dev is None or del_dev["status"] != "active" or not may_approve(del_dev, user_id):
            await reply(chat_id, "没有找到可删除的电脑（用法：/device del d4）。")
            return
        if del_dev["id"] == ADMIN_DEVICE:
            await reply(chat_id, "d0 是服务器 .env 配置的电脑，不能用 /device del 删除。")
            return
        await revoke_device(del_dev, "电脑主人删除了")
        if store.get("admin_default_device") == del_dev["id"]:
            store.delete("admin_default_device")
        if store.get(f"user_default_device:{user_id}") == del_dev["id"]:
            store.delete(f"user_default_device:{user_id}")
        await reply(chat_id, f"已删除 {device_label(del_dev)}，它的 token 作废了。",
                    en=f"Removed {device_label(del_dev, 'en')}. Its token no longer works.")
        return

    if sub in ("lock", "off", "revoke", "clear", "收回", "关闭"):
        store.run("UPDATE devices SET auth_until=0 WHERE id=?", (dev["id"],))
        store.run("UPDATE convs SET local_until=0 WHERE local_dev=?", (dev["id"],))
        text, markup = device_panel(dev, user_id, f"已收回 {device_label(dev)} 的整机免批及所有关联聊天时间窗")
        await reply(chat_id, text, markup)
        return

    if sub in ("window", "win", "default-window", "默认"):
        dur_raw = " ".join(tokens[1:]).strip()
        sec = parse_duration_spec(dur_raw)
        if sec is None:
            await reply(
                chat_id,
                "用法：/device window <时长>，支持如 0（每次问）、30m、2h、12h、7d、永久",
                en="Usage: /device window <duration>, e.g. 0 (ask every time), 30m, 2h, 12h, 7d, forever",
            )
            return
        store.run("UPDATE devices SET window_sec=? WHERE id=?", (sec, dev["id"]))
        text, markup = device_panel(dev, user_id, f"已将弹窗默认批准时长设为：{short_span(sec, 'en' if not admin and lang_of(user_id) == 'en' else 'zh')}")
        await reply(chat_id, text, markup)
        return

    dur_raw = " ".join(tokens[1:]).strip() if sub in ("auth", "pass", "allow", "授权", "免批") else arg
    sec = parse_duration_spec(dur_raw)
    if sec is not None:
        if sec <= 0:
            store.run("UPDATE devices SET auth_until=0 WHERE id=?", (dev["id"],))
            note = f"已关闭 {device_label(dev)} 的整机免批（恢复按各聊天批准）"
        else:
            store.run("UPDATE devices SET auth_until=? WHERE id=?", (now() + sec, dev["id"]))
            released = release_pending_for_device(dev["id"])
            span_s = short_span(sec, "en" if not admin and lang_of(user_id) == "en" else "zh")
            note = f"{device_label(dev)} 已开启整机免批：{span_s}" + (f"（已自动放行 {released} 个挂起请求）" if released else "")
        text, markup = device_panel(dev, user_id, note)
        await reply(chat_id, text, markup)
        return

    await reply(
        chat_id,
        "用法：\n"
        "• /device — 打开整机免批与默认时长按钮面板\n"
        "• /device 45m | 8h | 7d | 永久 — 自定义整机免批时长\n"
        "• /device window 30m | 0 | 24h | 永久 — 改弹窗默认放行时长\n"
        "• /device lock — 一键收回本机全部已授权时间窗\n"
        "• /device reset — 换 token 重发文件 | /device del — 删除电脑",
        en="Usage:\n"
           "• /device — open interactive duration panel\n"
           "• /device 45m | 8h | 7d | forever — set computer-wide pass\n"
           "• /device window 30m | 0 | 24h | forever — set default approval window\n"
           "• /device lock — revoke all active windows\n"
           "• /device reset | /device del",
    )


ADMIN_COMMANDS = {"/main", "/ctrl", "/nodes", "/key", "/agents", "/grant", "/revoke", "/devices"}


async def cmd_activate(message: dict, chat_id: int, user_id: int, rest: str) -> None:
    """群里 /activate：群主人或管理员激活别人；别人发就替他去问（没资格的问管理员，有资格的问群主人）。"""
    user = message.get("from") or {}
    title = (chat_row(chat_id) or {"title": ""})["title"]
    if not may_run_group(chat_id, user_id):
        if not is_granted(user_id):
            await reply(chat_id, f"{display_name(user)} 还没有使用资格，已经通知管理员。",
                        en=f"{display_name(user)} doesn't have access yet; I've let the admin know.")
            await ask_admin_grant(user, f"在群「{title}」里发了 /activate", chat_id)
        else:
            await reply(chat_id, "在这个群用 bot 要群主人同意，已经问他了。",
                        en="Using the bot in this group needs the group owner's OK; I've asked them.")
            await ask_group_activate(user, chat_id)
        return
    lang = lang_of(chat_id)
    target, why = target_user(message, rest, lang)
    if target is None:
        await reply(chat_id, why or "用法：回复某人的消息发 /activate，或者 /activate <用户id 或 @用户名>",
                    en=why or "Usage: reply to someone's message with /activate, or /activate <user id or @username>")
        return
    if not is_granted(target):
        if is_admin(user_id):
            await reply(chat_id, f"{person_label(target)} 还没有使用资格：回复他发 /grant 就会授权并在本群激活。",
                        en=f"{person_label(target)} doesn't have access yet: reply to them with /grant to grant access and activate them here.")
            return
        await reply(chat_id, f"{person_label(target)} 还没有使用资格，要管理员先授权，已经通知管理员了。",
                    en=f"{person_label(target)} doesn't have access yet; the admin has to grant it first. I've let the admin know.")
        who = person(target)
        await ask_admin_grant({"id": target, "username": who["username"] if who else "", "first_name": who["name"] if who else ""},
                              f"被群「{title}」的主人请求激活", chat_id)
        return
    store.run("INSERT OR IGNORE INTO activations(chat_id,user_id) VALUES(?,?)", (chat_id, target))
    await reply(chat_id, f"已激活 {person_label(target)}：在本群 @bot 或回复 bot 就会叫醒 agent。",
                en=f"Activated {person_label(target)}: mention @bot or reply to the bot in this group to wake the agent.")


async def on_command(message: dict, command: str, rest: str, chat_id: int, chat_type: str, user_id: int) -> None:
    private = chat_type == "private"
    group = chat_type in ("group", "supergroup")
    admin = is_admin(user_id)
    member = not admin and is_granted(user_id)
    if command in ("/start", "/help"):
        buttons = language_buttons() if command == "/start" else None
        if admin:
            await reply(chat_id, HELP_ADMIN)
        elif member:
            await reply(chat_id, HELP_MEMBER, buttons, en=HELP_MEMBER_EN)
        else:
            asked = command == "/start" and private
            await reply(chat_id, HELP_USER + f"\n\n你的用户 id：{user_id}" + ("（已经通知管理员）" if asked else ""), buttons,
                        en=HELP_USER_EN + f"\n\nYour user id: {user_id}" + (" (I've let the admin know)" if asked else ""))
            if asked:
                await ask_admin_grant(message.get("from") or {}, "私聊 bot 发了 /start")
        return
    if command == "/id":
        await reply(chat_id, f"chat_id={chat_id}\nuser_id={user_id}")
        return
    if command == "/language":
        if group and not may_run_group(chat_id, user_id):
            await reply(chat_id, "只有群主人或管理员能设群的语言。", en="Only the group's owner or the admin can set the group's language.")
            return
        choice = LANG_ALIASES.get(rest.strip().lower(), "")
        if choice:
            await reply(chat_id, await set_lang(chat_id, choice))
        else:
            await reply(chat_id, "选语言 / Choose a language:", language_buttons())
        return
    if command == "/activate" and group:
        await cmd_activate(message, chat_id, user_id, rest)
        return
    if command == "/device" and private and not (admin and re.fullmatch(r"del\s+d\d+", rest.strip())):
        if not is_granted(user_id):
            await reply(chat_id, f"你还没有使用资格。把你的用户 id 发给管理员：{user_id}",
                        en=f"You don't have access yet. Send your user id to the admin: {user_id}")
            return
        await cmd_device(message, chat_id, user_id, rest.strip())
        return
    if command == "/device" and not private:
        await reply(chat_id, "请在和 bot 的私聊里用 /device。", en="Use /device in your private chat with the bot.")
        return
    if not admin and not member:
        await reply(chat_id, "你还没有使用资格。/id 查看你的用户 id，发给管理员授权。",
                    en="You don't have access yet. /id shows your user id; send it to the admin.")
        return
    if not admin and command in ADMIN_COMMANDS:
        await reply(chat_id, "只有管理员可以用这个命令。", en="Only the admin can use this command.")
        return

    if command == "/nodes":
        if not admin:
            await reply(chat_id, "只有管理员可以用这个命令。", en="Only the admin can use this command.")
            return
        await reply(chat_id, render_cluster_overview() + f"\n\n🌐 Web 控制台：{PUBLIC_BASE}/web")
        return

    if command in ("/main", "/ctrl") or re.fullmatch(r"/(?:c|main)\d+", command):
        if not private:
            await reply(chat_id, "切换聊天要在和 bot 的私聊里用。群里用 /bind c1 指定负责的聊天。",
                        en="Switch chats in your private chat with the bot. In a group, /bind c5 picks which chat handles it.")
            return
        if is_main_node_id(command[1:]) and not admin:
            await reply(chat_id, "只有管理员可以进入主 Agent 会话。", en="Only the admin can enter main agent sessions.")
            return
        target_cid = command[1:]
        if target_cid == "main" and ctrl_is_active():
            target_cid = "ctrl"
        ensure_main_conv()
        conv = conv_row(target_cid)
        if conv is None or not can_manage(user_id, conv):
            await reply(chat_id, f"没有聊天 {command[1:]}。/history 看所有聊天，/nodes 看主 Agent 列表。",
                        en=f"There's no chat {command[1:]}. /history lists your chats.")
            return
        if conv["status"] != "open":
            gone = "已删除" if conv["status"] == "deleted" else "已关闭"
            await reply(chat_id, f"{conv_tag(conv)} {gone}（记录还在）。/reopen {conv['id']} 重开，/export {conv['id']} 导出记录。",
                        en=f"{conv_tag(conv)} is closed (history is kept). /reopen {conv['id']} reopens it; /export {conv['id']} exports it.")
            return
        if not enterable(chat_id, conv):
            if not conv_in_tg(conv) and can_manage(user_id, conv):
                await reply(
                    chat_id,
                    f"{conv_tag(conv)} 是子 agent 派生的纯后台 MCP 子 agent（默认不接入 Telegram 聊天列表，防挤爆菜单）。"
                    f"可在 /trace {conv['id']} 看实时动作，或 /export {conv['id']} 导出记录，或 /close {conv['id']} 关闭。",
                )
                return
            await reply(chat_id, f"{conv_tag(conv)} 是{owner_text(conv)}的聊天，只有他自己能切进去。/export {conv['id']} 可以导出记录。")
            return
        await switch_to(chat_id, conv["id"])
        return
    if command in ("/clouds", "/cloud", "/delcloud", "/unowned") or re.fullmatch(r"/cloud\d+", command):
        if not admin:
            await reply(chat_id, "只有管理员可以用这个命令。", en="Only the admin can use this command.")
            return
        if not private:
            await reply(chat_id, f"请在和 bot 的私聊里用 {command}。")
            return
        if command in ("/clouds", "/cloud") and not rest.strip():
            txt_p, mk_p = clouds_panel_view(chat_id)
            await reply(chat_id, txt_p, mk_p)
            return
        if command == "/delcloud" or (command in ("/clouds", "/cloud") and rest.strip().lower().startswith(("del ", "delete ", "rm "))):
            arg_s = rest.strip().split()[-1].lower() if rest.strip() else ""
            m_dc = re.fullmatch(r"(?:cloud)?(\d+)", arg_s)
            if not m_dc:
                txt_p, mk_p = clouds_panel_view(chat_id, "用法：/delcloud cloud4（或直接在下方点「🗑 删除」按钮）：")
                await reply(chat_id, txt_p, mk_p)
                return
            note_dc = delete_cloud(int(m_dc.group(1)), "管理员")
            txt_p, mk_p = clouds_panel_view(chat_id, note_dc)
            await reply(chat_id, txt_p, mk_p)
            return
        if command == "/unowned":
            if rest.strip().lower() in ("migrate", "mv"):
                targets_u = [r for r in open_convs() if cloud_of(r) == UNOWNED_CLOUD and conv_in_tg(r)]
                if not targets_u:
                    targets_u = [r for r in open_convs() if cloud_of(r) == UNOWNED_CLOUD]
                note_m = migrate_convs_to_main(targets_u, "管理员")
                txt_p, mk_p = clouds_panel_view(chat_id, note_m)
                await reply(chat_id, txt_p, mk_p)
                return
            if any(cloud_of(r) == UNOWNED_CLOUD for r in open_convs()):
                store.set(f"view:{chat_id}", str(UNOWNED_CLOUD))
                mark_menu_dirty()
            await reply(chat_id, cloud_listing(chat_id, UNOWNED_CLOUD), cloud_single_markup(UNOWNED_CLOUD))
            return
        if command in ("/clouds", "/cloud"):
            txt_p, mk_p = clouds_panel_view(chat_id)
            await reply(chat_id, txt_p, mk_p)
            return
        n = int(command[len("/cloud"):])
        if not 1 <= n <= max_cloud():
            await reply(chat_id, f"没有 {cloud_tag(n)}。现在有：" + " ".join(f"/{cloud_cmd(c)}" for c in admin_clouds(chat_id)))
            return
        sub_arg = rest.strip().lower()
        if sub_arg in ("del", "delete", "rm", "删除"):
            note_dc = delete_cloud(n, "管理员")
            txt_p, mk_p = clouds_panel_view(chat_id, note_dc)
            await reply(chat_id, txt_p, mk_p)
            return
        if sub_arg in ("migrate", "mv", "迁移", "migrate all", "mv all"):
            inc_bg = sub_arg.endswith("all")
            targets_n = [r for r in open_convs() if cloud_of(r) == n and (inc_bg or conv_in_tg(r))]
            if not targets_n and not inc_bg:
                targets_n = [r for r in open_convs() if cloud_of(r) == n]
            note_m = migrate_convs_to_main(targets_n, "管理员")
            txt_p, mk_p = clouds_panel_view(chat_id, note_m)
            await reply(chat_id, txt_p, mk_p)
            return
        if rest.strip():
            await reply(chat_id, move_to_cloud(n, rest.split()))
            return
        store.set(f"view:{chat_id}", str(n))
        mark_menu_dirty()
        await reply(chat_id, cloud_listing(chat_id, n), cloud_single_markup(n))
        return
    if command in ("/new", "/key", "/export"):
        if not private:
            await reply(chat_id, f"请在和 bot 的私聊里用 {command}。", en=f"Use {command} in your private chat with the bot.")
            return
        if command == "/new":
            await cmd_new(chat_id, rest)
        elif command == "/key" and rest.strip().lower() == "reset":
            config = rotate_key()
            await reply(chat_id, "已换新密钥：所有云 agent 都断开了，没批的接入和本地申请也作废了。\n"
                        "把下面的配置换进 cursor.com/agents，再开一个云端聊天，发开场提示词重新设主控：\n" + config
                        + "\n\n主控开场提示词：\n" + MAIN_PROMPT)
        elif command == "/key":
            await reply(chat_id, "账号级 MCP 配置，填进 cursor.com/agents 的 MCP 设置（所有云 agent 共用，不要贴进聊天内容）：\n"
                        + mcp_config()
                        + f"\n\n🌐 Web 全功能控制台地址：{PUBLIC_BASE}/web（超级管理员账号：zwt）"
                        + "\n\n【1】主 Agent 执行器开场提示词（新开主 Agent 时发给它，你在 TG 点批准）：\n" + MAIN_PROMPT
                        + "\n\n【2】云端常驻工作会话（算力机）开场提示词（总控免打扰自动审批）：\n" + WORKER_PROMPT
                        + "\n\n会话停了：打开它那个云端聊天，发：\n" + RESUME_PROMPT
                        + "\n\n怀疑密钥泄露或有云 agent 失控：发 /key reset 换密钥，所有云 agent 立刻断开。")
        else:
            await cmd_export(chat_id, user_id, rest)
        return
    if command == "/history":
        if not private and not admin:
            await reply(chat_id, "请在和 bot 的私聊里用 /history。", en="Use /history in your private chat with the bot.")
            return
        await reply(chat_id, history_text(user_id))
        return
    if command == "/list":
        if not private:
            await reply(chat_id, "请在和 bot 的私聊里用 /list。", en="Use /list in your private chat with the bot.")
            return
        text, markup = list_view(user_id)
        await reply(chat_id, text, markup)
        return
    if command == "/agents":
        await reply(chat_id, status_overview())
        return
    if command == "/trace":
        target_arg = rest.strip().split()[0] if rest.strip() else ""
        try:
            report = render_trace_report(
                viewer_owner=0 if admin else user_id,
                is_main_or_admin=admin,
                target_conv=target_arg,
                events_limit=8 if target_arg else 3,
            )
        except ToolFail as exc:
            report = str(exc)
        await reply(chat_id, report)
        return

    if command in ("/share", "/unshare"):
        parts = rest.split()
        source = parse_conv(parts[0]) if len(parts) == 2 else ""
        reader = parse_conv(parts[1]) if len(parts) == 2 else ""
        src_row = conv_row(source) if source else None
        reader_row = conv_row(reader) if reader else None
        if src_row is None or reader_row is None or not can_manage(user_id, src_row) or not can_manage(user_id, reader_row):
            await reply(chat_id, f"用法：{command} c1 c3（{'授权' if command == '/share' else '撤销'} c3 读 c1 的记录）",
                        en=f"Usage: {command} c5 c7 ({'let' if command == '/share' else 'stop letting'} c7 read c5's history)")
            return
        if reader == "main":
            await reply(chat_id, "主控只看状态，不读聊天内容，不能授权给主控。")
            return
        if source == reader:
            await reply(chat_id, "自己的记录本来就能读。", en="A chat can always read its own history.")
            return
        if command == "/share":
            if not may_share(user_id, reader_row, src_row):
                await reply(chat_id, f"{conv_tag(reader_row)} 是{owner_text(reader_row)}的聊天，只能读同一个用户的聊天。")
                return
            grant_share(reader, source)
            await reply(chat_id, f"已授权 {conv_tag(reader_row)} 读取 {conv_tag(src_row)} 的记录。",
                        en=f"{conv_tag(reader_row)} can now read {conv_tag(src_row)}'s history.")
        else:
            revoke_share(reader, source)
            await reply(chat_id, f"已撤销 {conv_tag(reader_row)} 读取 {conv_tag(src_row)} 的授权。",
                        en=f"{conv_tag(reader_row)} can no longer read {conv_tag(src_row)}'s history.")
        return

    if command in ("/close", "/reopen", "/restart", "/stop", "/rename"):
        target, _, extra = rest.partition(" ")
        conv_id = parse_conv(target)
        conv = conv_row(conv_id) if conv_id else None
        if conv is None or conv_id == "main" or not can_manage(user_id, conv):
            usage = "/rename c1 新名字" if command == "/rename" else f"{command} c1"
            note = "（主控不能这样操作：主控停了就重新开一个云端聊天调用 join）" if conv_id == "main" and admin else ""
            await reply(chat_id, f"用法：{usage}{note}",
                        en="Usage: " + ("/rename c5 new name" if command == "/rename" else f"{command} c5"))
            return
        by = "管理员" if admin else "聊天主人"
        who = "管理员" if admin else f"用户 {person_label(user_id)} "
        owner = conv_owner(conv)
        if command == "/rename":
            name = clean_name(extra)
            if not name:
                await reply(chat_id, "用法：/rename c1 新名字", en="Usage: /rename c5 new name")
                return
            store.run("UPDATE convs SET name=? WHERE id=?", (name, conv["id"]))
            mark_menu_dirty()
            await reply(chat_id, f"{conv['id']} 改名为「{name}」。", en=f"{conv['id']} is now called \"{name}\".")
            return
        if command == "/close":
            if conv["status"] != "open":
                await reply(chat_id, f"{conv_tag(conv)} 本来就是关闭的。", en=f"{conv_tag(conv)} is already closed.")
                return
            await close_conv(conv, by)
            await reply(chat_id, f"已关闭 {conv_tag(conv)}。记录保留：/history 查看，/export {conv['id']} 导出，/reopen {conv['id']} 重开。",
                        en=f"Closed {conv_tag(conv)}. History is kept: /history lists it, /export {conv['id']} exports it, "
                           f"/reopen {conv['id']} reopens it.")
            if admin and owner and is_granted(owner):
                await reply(owner, f"管理员关闭了你的聊天 {conv_tag(conv)}（记录保留，/reopen {conv['id']} 可以重开）。",
                            en=f"The admin closed your chat {conv_tag(conv)} (history is kept; /reopen {conv['id']} reopens it).")
            return
        if command == "/reopen":
            if conv["status"] == "open":
                await reply(chat_id, f"{conv_tag(conv)} 本来就开着。要换子 agent 用 /restart {conv['id']}。",
                            en=f"{conv_tag(conv)} is already open. /restart {conv['id']} gets it a new AI.")
                return
            if owner and not is_granted(owner):
                await reply(chat_id, f"{conv_tag(conv)} 的主人 {person_label(owner)} 已经没有使用资格了，先 /grant {owner} 再重开。")
                return
            store.run("UPDATE convs SET status='open', closed=0 WHERE id=?", (conv["id"],))
            issue_task(conv["id"])
            conv = conv_row(conv["id"])
            system_note("main", task_note(conv, f"{who}重开了聊天（之前的记录都在）"))
            hint = f"/{conv['id']} 切过去。" if enterable(chat_id, conv) else ""
            await reply(chat_id, f"已重开 {conv_tag(conv)}，主控会开一个子 agent 接手。{hint}",
                        en=f"Reopened {conv_tag(conv)}; a new AI will pick it up. /{conv['id']} switches to it.")
            return
        if conv["status"] != "open":
            await reply(chat_id, f"{conv_tag(conv)} 已关闭，先 /reopen {conv['id']}。",
                        en=f"{conv_tag(conv)} is closed; /reopen {conv['id']} first.")
            return
        if command == "/restart":
            moved = cloud_of(conv) if away(conv) else 0
            restart_conv(conv, f"{by}让主控重开一个子 agent 接手")
            conv = conv_row(conv["id"])
            system_note("main", task_note(conv, f"{who}要求重开这个聊天的子 agent（记录都在，新子 agent 接手后能看到）"))
            note = f"（从 {cloud_tag(moved)} 挪进了 {cloud_tag(main_cloud())}）" if moved and admin else ""
            await reply(chat_id, f"已让主控重开 {conv_tag(conv)} 的子 agent，旧的那个已作废。{note}",
                        en=f"A new AI will take over {conv_tag(conv)}; the old one has been stopped.")
            return
        old = active_agent(conv)
        if old is not None:
            stop_identity(old["id"], f"{by}停掉了这个子 agent")
        store.run("UPDATE convs SET agent='', task_code='' WHERE id=?", (conv["id"],))
        mark_menu_dirty()
        await reply(chat_id, f"已停掉 {conv_tag(conv)} 的子 agent。聊天保留，/restart {conv['id']} 可以重开。",
                    en=f"Stopped the AI on {conv_tag(conv)}. The chat is kept; /restart {conv['id']} gets a new one.")
        return

    if command in ("/grant", "/revoke"):
        target, why = target_user(message, rest)
        if target is None:
            await reply(chat_id, why or f"用法：{command} <用户id 或 @用户名>，或者回复他的消息（也可以回复他被转发过来的消息）")
            return
        if command == "/grant":
            await reply(chat_id, await grant_user(target, chat_id if group else 0))
        else:
            await reply(chat_id, await revoke_user(target))
        return
    if command == "/devices":
        await reply(chat_id, devices_text() if private else "请在和 bot 的私聊里用 /devices。")
        return
    if command == "/device":
        match = re.fullmatch(r"del\s+(d\d+)", rest.strip())
        dev = device_row(match.group(1)) if match else None
        if dev is None or dev["status"] != "active":
            await reply(chat_id, "用法：/device del d2（/devices 查看所有电脑）")
            return
        if dev["id"] == ADMIN_DEVICE:
            await reply(chat_id, "d0 是你自己的电脑：要换就在服务器 .env 里改 CLIENT_TOKEN 再重启服务。")
            return
        await revoke_device(dev, "管理员作废了")
        for owner_chat in device_chats(dev):
            await reply(owner_chat, f"管理员作废了你的电脑 {device_label(dev)} 的本地通道。",
                        en=f"The admin revoked the local channel on your computer {device_label(dev, 'en')}.")
        await reply(chat_id, f"已作废 {device_label(dev)}，它的 token 不能再用了。")
        return
    if command == "/local":
        tokens = rest.split()
        usage = (
            "用法：\n"
            "• /local — 打开当前聊天的本地通道面板（带快捷时长按钮）\n"
            "• /local 45m | 6h | 7d | 永久 | lock | on | off — 直接设当前聊天（也可写成 /local c165 45m）\n"
            "• /local all 24h | 永久 | lock | off — 批量设你名下所有聊天\n"
            "• /local [c165] device d3|auto — 指定聊天用哪台电脑"
        )
        usage_en = (
            "Usage:\n"
            "• /local — open interactive panel for current chat\n"
            "• /local 45m | 6h | 7d | forever | lock | on | off — set current chat (or /local c5 45m)\n"
            "• /local all 24h | forever | lock | off — set all your open chats"
        )

        # 1) 批量管理名下所有开放聊天：/local all <value>
        if tokens and tokens[0].lower() == "all":
            val = " ".join(tokens[1:]).strip()
            own_id = 0 if admin else user_id
            my_convs = own_convs(own_id, "open")
            if not my_convs:
                await reply(chat_id, "你现在还没有开着的聊天。", en="You have no open chats right now.")
                return
            low_val = val.lower()
            if low_val == "off":
                for c in my_convs:
                    store.run("UPDATE convs SET local_enabled=0, local_until=0 WHERE id=?", (c["id"],))
                    deny_local_requests(conv_id=c["id"])
                await reply(chat_id, f"已关闭你名下全部 {len(my_convs)} 个聊天的本地通道。", en=f"Turned off local channel for all {len(my_convs)} chats.")
                return
            if low_val == "on":
                for c in my_convs:
                    store.run("UPDATE convs SET local_enabled=1 WHERE id=?", (c["id"],))
                await reply(chat_id, f"已开启你名下全部 {len(my_convs)} 个聊天的本地通道。", en=f"Turned on local channel for all {len(my_convs)} chats.")
                return
            if low_val in ("lock", "revoke", "clear", "收回"):
                for c in my_convs:
                    store.run("UPDATE convs SET local_until=0 WHERE id=?", (c["id"],))
                await reply(chat_id, f"已收回你名下全部 {len(my_convs)} 个聊天的单独授权时间窗（若开了 /device 整机免批请用 /device lock 收回）。",
                            en=f"Revoked local windows on all {len(my_convs)} chats.")
                return
            sec = parse_duration_spec(val)
            if sec is None:
                await reply(chat_id, usage, en=usage_en)
                return
            ok_cnt = 0
            for c in my_convs:
                dev = conv_device(c)
                if dev is not None and may_approve(dev, user_id):
                    until = 0.0 if sec <= 0 else now() + sec
                    store.run("UPDATE convs SET local_enabled=1, local_until=?, local_dev=? WHERE id=?", (until, dev["id"], c["id"]))
                    if sec > 0:
                        release_pending_for_device(dev["id"], c["id"])
                    ok_cnt += 1
            if not ok_cnt:
                await reply(chat_id, "没有可授权的本地电脑，请先发 /device 查看或安装。", en="No local computer available. Send /device first.")
                return
            span_s = short_span(sec, "en" if not admin and lang_of(user_id) == "en" else "zh")
            await reply(chat_id, f"已为你名下 {ok_cnt} 个聊天批量设置本地授权时长：{span_s}。",
                        en=f"Set local authorization to {span_s} for {ok_cnt} chat(s).")
            return

        # 2) 解析目标聊天：传了 cXXX 或 main 就用它，没传就自动取当前选中的聊天（包括 /main！给 main 授权时所有子 agent 自动继承）
        if tokens and parse_conv(tokens[0]):
            conv = conv_row(parse_conv(tokens[0]))
            value = " ".join(tokens[1:]).strip()
        else:
            cur_id = selected(chat_id) if private else route_of(chat_id)
            conv = conv_row(cur_id) if cur_id else None
            value = rest.strip()
            if conv is None:
                own_list = own_convs(0 if admin else user_id, "open")
                if len(own_list) == 1:
                    conv = own_list[0]

        if conv is None or not can_manage(user_id, conv):
            await reply(chat_id, usage, en=usage_en)
            return

        if value == "":
            text, markup = local_conv_panel(conv, user_id)
            await reply(chat_id, text, markup)
            return

        owner = conv_owner(conv)
        low_val = value.lower()
        if low_val == "off":
            store.run("UPDATE convs SET local_enabled=0, local_until=0 WHERE id=?", (conv["id"],))
            deny_local_requests(conv_id=conv["id"])
            text, markup = local_conv_panel(conv, user_id, f"{conv_tag(conv)} 本地通道已关闭")
            await reply(chat_id, text, markup)
        elif low_val == "on":
            store.run("UPDATE convs SET local_enabled=1 WHERE id=?", (conv["id"],))
            text, markup = local_conv_panel(conv, user_id, f"{conv_tag(conv)} 本地通道已开启")
            await reply(chat_id, text, markup)
        elif low_val in ("lock", "revoke", "clear", "收回"):
            store.run("UPDATE convs SET local_until=0 WHERE id=?", (conv["id"],))
            text, markup = local_conv_panel(conv, user_id, f"已收回 {conv_tag(conv)} 的单独授权时间窗")
            await reply(chat_id, text, markup)
        elif low_val.split(" ", 1)[0] == "device":
            choice = value[len("device"):].strip().lower()
            if choice in ("", "auto"):
                store.run("UPDATE convs SET device='' WHERE id=?", (conv["id"],))
            else:
                picked = device_row(choice)
                if picked is None or picked["status"] != "active":
                    await reply(chat_id, "没有这台电脑，/devices 查看。", en="No such computer. /device shows yours.")
                    return
                if owner and picked["owner"] != owner:
                    await reply(chat_id, f"{conv_tag(conv)} 是{owner_text(conv)}的聊天，只能用他自己的电脑。",
                                en=f"{conv_tag(conv)} can only use your own computer (/device).")
                    return
                store.run("UPDATE convs SET device=? WHERE id=?", (picked["id"], conv["id"]))
            conv = conv_row(conv["id"])
            dev = conv_device(conv)
            text, markup = local_conv_panel(conv, user_id, f"已将目标电脑设为：{device_label(dev) if dev else '无'}")
            await reply(chat_id, text, markup)
        else:
            sec = parse_duration_spec(value)
            if sec is None:
                await reply(chat_id, usage, en=usage_en)
                return
            dev = conv_device(conv)
            if dev is None or not may_approve(dev, user_id):
                where = device_label(dev) if dev is not None else "没有可用的电脑（请先发 /device 安装）"
                where_en = device_label(dev, "en") if dev is not None else "no computer (send /device first)"
                await reply(chat_id, f"{conv_tag(conv)} 用的是 {where}，只有电脑主人能批准，你不能直接给时间。",
                            en=f"{conv_tag(conv)} uses {where_en}; only that computer's owner can approve it.")
                return
            until = 0.0 if sec <= 0 else now() + sec
            store.run(
                "UPDATE convs SET local_enabled=1, local_until=?, local_dev=? WHERE id=?",
                (until, dev["id"], conv["id"]),
            )
            released = release_pending_for_device(dev["id"], "" if conv["id"] == "main" else conv["id"]) if sec > 0 else 0
            span_s = short_span(sec, "en" if not admin and lang_of(user_id) == "en" else "zh")
            note = (
                f"已收回时间窗（恢复每次确认）" if sec <= 0
                else f"已在 {device_label(dev)} 上授权 {span_s}" + (f"（并放行了 {released} 个等待请求）" if released else "")
            )
            text, markup = local_conv_panel(conv_row(conv["id"]), user_id, note)
            await reply(chat_id, text, markup)
        return

    if not group:
        await reply(chat_id, "这个命令要在群里用，或者命令不存在。/help 查看。",
                    en="This command only works in a group, or it doesn't exist. See /help.")
        return
    if command in ("/bind", "/listen", "/open") and not may_run_group(chat_id, user_id):
        await reply(chat_id, "只有群主人或管理员能用这个命令。", en="Only the group's owner or the admin can use this command.")
        return
    owner = group_owner(chat_id)
    if command == "/bind":
        if rest.strip().lower() in ("", "main", "off"):
            old = route_of(chat_id)
            set_route(chat_id, None)
            if old:
                system_note(old, f"{chat_label(chat_id)} 已被{'管理员' if admin else '群主人'}收回，不归你负责了。", wake=0)
            if owner:
                await reply(chat_id, "本群先放着：现在没有聊天负责，群主人发 /bind c5 再指定。",
                            en="This group is on hold: no chat handles it now. The group's owner can send /bind c5 to pick one.")
            else:
                await reply(chat_id, "本群先放着：消息先到主控，由它分配。",
                            en="This group is on hold: messages go to the main agent, which will assign it.")
            return
        conv_id = parse_conv(rest)
        conv = conv_row(conv_id) if conv_id and conv_id != "main" else None
        if conv is None or conv["status"] != "open" or conv_owner(conv) != owner:
            if owner:
                await reply(chat_id, "用法：/bind c5（填群主人自己的、开着的聊天；/bind off 先放着）",
                            en="Usage: /bind c5 (one of the group owner's open chats; /bind off puts the group on hold)")
            else:
                await reply(chat_id, "用法：/bind c1（或 /bind main 收回给主控分配）",
                            en="Usage: /bind c1 (or /bind main to hand it back to the main agent)")
            return
        await assign_chat(chat_id, conv, "管理员" if admin else "群主人")
        await reply(chat_id, f"本群交给 {conv_tag(conv)} 负责。", en=f"This group is now handled by {conv_tag(conv)}.")
        return
    if command == "/listen":
        mode = "all" if rest == "all" else "mention"
        store.run("UPDATE chats SET listen=? WHERE chat_id=?", (mode, chat_id))
        if mode == "all":
            await reply(chat_id, "本群已激活成员的所有发言都会叫醒 agent。",
                        en="Every message from activated members of this group will wake the agent.")
        else:
            await reply(chat_id, "本群只有 @bot 或回复 bot 才会叫醒 agent（其它发言 agent 也能看到）。",
                        en="In this group only mentioning @bot or replying to the bot wakes the agent (it still sees the other messages).")
        return
    if command == "/open":
        value = 1 if rest == "on" else 0
        store.run("UPDATE chats SET open=? WHERE chat_id=?", (value, chat_id))
        if value:
            await reply(chat_id, "本群所有人都可以叫醒 agent。", en="Everyone in this group can wake the agent.")
        elif owner:
            await reply(chat_id, "本群只有群主人、管理员和已激活的成员可以叫醒 agent。",
                        en="In this group only the group's owner, the admin and activated members can wake the agent.")
        else:
            await reply(chat_id, "本群只有管理员和已激活的成员可以叫醒 agent。",
                        en="In this group only the admin and activated members can wake the agent.")
        return
    await reply(chat_id, "未知命令。/help 查看。", en="Unknown command. See /help.")


# ---------------------------------------------------------------- Telegram：按钮

async def on_callback(callback: dict) -> None:
    data = callback.get("data") or ""
    user = callback.get("from") or {}
    user_id = int(user.get("id") or 0)
    message = callback.get("message") or {}
    cb_id = callback["id"]
    msg_chat = (message.get("chat") or {}).get("id")
    original = message.get("text") or ""

    async def answer(text: str = "", en: str | None = None) -> None:
        if en is not None and lang_of(user_id) == "en":
            text = en
        await tg.try_call("answerCallbackQuery", callback_query_id=cb_id, text=text)

    async def mark(label: str, en: str | None = None) -> None:
        if en is not None and lang_of(user_id) == "en":
            label = en
        await answer(label[:180])
        if msg_chat and message.get("message_id"):
            await tg.try_call("editMessageText", chat_id=msg_chat, message_id=message["message_id"], text=f"{original}\n\n【{label}】")

    if data.startswith("lang:"):
        choice = data.split(":", 1)[1]
        if choice not in LANGS or not msg_chat:
            await answer()
            return
        if msg_chat != user_id and not may_run_group(msg_chat, user_id):
            await answer("只有群主人或管理员能设群的语言", en="Only the group's owner or the admin can set the group's language")
            return
        text = await set_lang(msg_chat, choice)
        await answer(text[:180])
        if msg_chat == user_id and not is_admin(user_id):
            if is_granted(user_id):
                text += "\n\n" + (HELP_MEMBER_EN if choice == "en" else HELP_MEMBER)
            else:
                text += "\n\n" + (HELP_USER_EN + f"\n\nYour user id: {user_id}" if choice == "en" else HELP_USER + f"\n\n你的用户 id：{user_id}")
        if message.get("message_id"):
            await tg.try_call("editMessageText", chat_id=msg_chat, message_id=message["message_id"], text=text)
        return

    if data.startswith("q:"):
        _, ask_id, index = data.split(":", 2)
        payload = approval_payload(ask_id)
        options = payload.get("options") or []
        if not payload or not index.isdigit() or int(index) >= len(options):
            await answer("这个问题已失效", en="This question has expired")
            return
        choice = options[int(index)]
        chat_id = int(payload["chat_id"])
        conv = conv_row(payload.get("conv") or "")
        target = conv["id"] if conv is not None and conv["status"] == "open" else "main"
        crow = chat_row(chat_id)
        post(
            target,
            chat_id=chat_id,
            chat_type=crow["type"] if crow else "private",
            chat_title=crow["title"] if crow else "",
            user_id=user_id,
            user_name=display_name(user),
            text=f"[回答「{payload.get('question', '')[:40]}」] {choice}",
            reply_to_bot=1,
            wake=1,
        )
        await answer(f"已记录：{choice}", en=f"Recorded: {choice}")
        return

    if data.startswith("ldv:"):
        parts = data.split(":")
        if len(parts) < 4:
            await answer()
            return
        _, dev_id, act, val_s = parts[:4]
        dev = device_row(dev_id)
        if dev is None or dev["status"] != "active" or not may_approve(dev, user_id):
            await answer("无权操作或电脑已作废", en="Not allowed or computer removed")
            return
        sec = int(val_s) if val_s.lstrip("-").isdigit() else 0
        en = not is_admin(user_id) and lang_of(user_id) == "en"
        if act == "p":
            store.run("UPDATE devices SET auth_until=? WHERE id=?", (now() + sec, dev["id"]))
            release_pending_for_device(dev["id"])
            note = f"Pass set: {short_span(sec, 'en')}" if en else f"已开启整机免批：{short_span(sec)}"
        elif act == "w":
            store.run("UPDATE devices SET window_sec=? WHERE id=?", (sec, dev["id"]))
            note = f"Default window: {short_span(sec, 'en')}" if en else f"默认弹窗时长已设为：{short_span(sec)}"
        elif act == "lock":
            store.run("UPDATE devices SET auth_until=0 WHERE id=?", (dev["id"],))
            store.run("UPDATE convs SET local_until=0 WHERE local_dev=?", (dev["id"],))
            note = "Revoked all active windows" if en else "已收回整机免批与所有关联聊天授权"
        elif act == "def":
            if is_admin(user_id):
                store.set("admin_default_device", dev["id"])
                note = f"已切换管理员默认电脑为 {device_label(dev)}"
            else:
                store.set(f"user_default_device:{user_id}", dev["id"])
                note = f"Default PC: {device_label(dev, 'en')}" if en else f"已切换默认电脑为 {device_label(dev)}"
        elif act == "add":
            new_d = await issue_device(user_id, display_name(user), create_new=True)
            note = f"Added {device_label(new_d, 'en')}" if en else f"已新增独立电脑安装包：{device_label(new_d)}（已发私聊）"
            dev = new_d
        else:
            await answer()
            return
        await answer(note[:180])
        if msg_chat and message.get("message_id"):
            text, markup = device_panel(dev, user_id, note)
            await tg.try_call("editMessageText", chat_id=msg_chat, message_id=message["message_id"], text=text, reply_markup=markup)
        return

    if data.startswith("llc:"):
        parts = data.split(":")
        if len(parts) < 4:
            await answer()
            return
        _, cid, act, val_s = parts[:4]
        conv = conv_row(cid)
        if conv is None or not can_manage(user_id, conv):
            await answer("无权操作该聊天", en="Not allowed")
            return
        en = not is_admin(user_id) and lang_of(user_id) == "en"
        dev = conv_device(conv)
        sec = int(val_s) if val_s.lstrip("-").isdigit() else 0
        if act == "on":
            store.run("UPDATE convs SET local_enabled=1 WHERE id=?", (conv["id"],))
            note = "Local channel ON" if en else "已开启本地通道"
        elif act == "off":
            store.run("UPDATE convs SET local_enabled=0, local_until=0 WHERE id=?", (conv["id"],))
            deny_local_requests(conv_id=conv["id"])
            note = "Local channel OFF" if en else "已关闭本地通道"
        elif act == "lock":
            store.run("UPDATE convs SET local_until=0 WHERE id=?", (conv["id"],))
            note = "Window revoked" if en else "已收回本聊天单独授权时间窗"
        elif act == "s":
            if dev is None or not may_approve(dev, user_id):
                await answer("只有这台电脑的主人能授权", en="Only this computer's owner can approve")
                return
            store.run("UPDATE convs SET local_enabled=1, local_until=?, local_dev=? WHERE id=?", (now() + sec, dev["id"], conv["id"]))
            release_pending_for_device(dev["id"], "" if conv["id"] == "main" else conv["id"])
            note = f"Approved for {short_span(sec, 'en')}" if en else f"已授权 {short_span(sec)}"
        else:
            await answer()
            return
        await answer(note[:180])
        if msg_chat and message.get("message_id"):
            text, markup = local_conv_panel(conv_row(conv["id"]), user_id, note)
            await tg.try_call("editMessageText", chat_id=msg_chat, message_id=message["message_id"], text=text, reply_markup=markup)
        return

    if data.startswith("ap:"):
        _, approval_id, choice = data.split(":", 2)
        row = store.one("SELECT * FROM approvals WHERE id=?", (approval_id,))
        if row is not None and row["kind"] == "local":
            # 本地操作由电脑主人批：管理员的电脑管理员批，别人的电脑只能主人自己批
            payload = json.loads(row["payload"] or "{}")
            dev = device_row(payload.get("device") or ADMIN_DEVICE)
            if dev is None or not may_approve(dev, user_id):
                await answer("只有这台电脑的主人能批准", en="Only this computer's owner can approve")
                return
            if row["status"] != "pending":
                await answer("已经处理过了", en="Already handled")
                return
            if choice == "n":
                set_approval(approval_id, "denied")
                await mark("已拒绝", en="Denied")
                return
            conv_id = payload.get("conv", "")
            if choice.startswith("d") and choice[1:].isdigit():
                sec = int(choice[1:])
                store.run("UPDATE devices SET auth_until=? WHERE id=?", (now() + sec, dev["id"]))
                set_approval(approval_id, "approved")
                release_pending_for_device(dev["id"])
                await mark(
                    f"已开启整机免批：{short_span(sec)}（你名下所有聊天直接执行）",
                    en=f"Approved computer-wide pass: {short_span(sec, 'en')}",
                )
                return
            if choice == "0":
                sec = 0
            elif choice.startswith("s") and choice[1:].isdigit():
                sec = int(choice[1:])
            else:
                sec = device_window_sec(dev)
            if sec > 0:
                store.run("UPDATE convs SET local_until=?, local_dev=? WHERE id=?", (now() + sec, dev["id"], conv_id))
            set_approval(approval_id, "approved")
            if sec > 0:
                release_pending_for_device(dev["id"], conv_id)
            await mark(f"已批准：{window_text(sec=sec)}", en=f"Approved: {window_text('en', sec=sec)}")
            return

    if data.startswith("sh:") or data.startswith("shd:"):
        parts = data.split(":")
        reader_row = conv_row(parts[1]) if len(parts) > 1 else None
        if reader_row is None or not can_manage(user_id, reader_row):
            await answer("已失效", en="Expired")
            return
        reader = reader_row["id"]
        if parts[0] == "shd":
            sources = share_sources(reader)
            await mark(f"已授权 {reader} 读取：{'、'.join(sources)}" if sources else "不授权读取旧聊天",
                       en=f"{reader} can read: {', '.join(sources)}" if sources else "No earlier chats shared")
            return
        source_row = conv_row(parts[2]) if len(parts) > 2 else None
        if not may_share(user_id, reader_row, source_row):
            await answer("已失效", en="Expired")
            return
        source = source_row["id"]
        if shared(reader, source):
            revoke_share(reader, source)
            await answer(f"已取消：{reader} 不能读 {source}", en=f"Undone: {reader} can't read {source}")
        else:
            grant_share(reader, source)
            await answer(f"已授权 {reader} 读 {source}", en=f"{reader} can now read {source}")
        await tg.try_call("editMessageReplyMarkup", chat_id=msg_chat, message_id=message.get("message_id"),
                          reply_markup=share_keyboard(reader))
        return

    if data.partition(":")[0] in ("ls", "sw", "dl", "dlok", "hv", "hvok"):
        kind, _, rest = data.partition(":")
        conv_id, _, page_s = rest.rpartition(":")
        page = int(page_s) if page_s.isdigit() else 0
        conv = conv_row(conv_id) if conv_id else None

        async def show(text: str, markup: dict | None) -> None:
            body: dict[str, Any] = {"chat_id": msg_chat, "message_id": message.get("message_id"), "text": text[:4000]}
            if markup:
                body["reply_markup"] = markup
            await tg.try_call("editMessageText", **body)

        if msg_chat != user_id or not is_hub(user_id):
            await answer("已失效", en="Expired")
            return
        if kind != "ls" and (conv is None or conv["id"] == "main" or conv["status"] == "deleted" or not can_manage(user_id, conv)):
            await answer("这个聊天已经不在了", en="That chat is gone")
            await show(*list_view(user_id, page))
            return
        if kind == "ls":
            await answer()
            await show(*list_view(user_id, page))
            return
        if kind == "sw":
            if conv["status"] != "open":
                await answer(f"{conv['id']} 已关闭，/reopen {conv['id']} 可以重开", en=f"{conv['id']} is closed; /reopen {conv['id']} reopens it")
                return
            if not enterable(user_id, conv):
                await answer(f"{conv['id']} 是 {person_short(conv_owner(conv))} 的聊天，只有他自己能切进去")
                return
            await answer()
            await switch_to(user_id, conv["id"])
            await show(*list_view(user_id, page))
            return
        if kind == "dl":
            await answer()
            await show(*delete_view(user_id, conv, page))
            return
        if kind in ("hv", "hvok"):
            if not is_admin(user_id):
                await answer("只有管理员能操作", en="Only the admin can do this")
                return
            if conv["status"] != "open" or not away(conv):
                await answer(f"{conv['id']} 已经在 {cloud_tag(main_cloud())} 了")
                await show(*list_view(user_id, page))
                return
            if kind == "hv":
                await answer()
                await show(*hand_over_view(conv, page))
                return
            hand_over(conv, "管理员")
            await answer(f"已交给 {cloud_tag(main_cloud())} 主控")
            await show(*list_view(user_id, page, f"已把 {conv_tag(conv)} 交给 {cloud_tag(main_cloud())} 主控："
                                                  "旧的子 agent 已停，主控会开一个新的接手。"))
            return
        admin = is_admin(user_id)
        owner = conv_owner(conv)
        await delete_conv(conv, "管理员" if admin else "聊天主人")
        if admin and owner and is_granted(owner):
            await reply(owner, f"管理员删除了你的聊天 {conv_tag(conv)}。", en=f"The admin deleted your chat {conv_tag(conv)}.")
        await answer(f"已删除 {conv['id']}", en=f"Deleted {conv['id']}")
        current = selected(user_id)
        now_in = conv_row(current) if current else None
        if admin:
            note = f"已删除 {conv_tag(conv)}（记录还在，/export {conv['id']} 能导出）。"
        elif lang_of(user_id) == "en":
            note = f"Deleted {conv_tag(conv)}. " + (f"Your messages now go to {conv_tag(now_in)}." if now_in is not None
                                                     else "You have no open chat now; just send a message to start one.")
        else:
            note = f"已删除 {conv_tag(conv)}。" + (f"现在发消息进 {conv_tag(now_in)}。" if now_in is not None
                                                 else "现在没有开着的聊天，直接发消息会新建一个。")
        await show(*list_view(user_id, page, note))
        return

    if data.startswith("gb:"):
        _, chat_s, choice = data.split(":", 2)
        group_id = int(chat_s)
        if not may_run_group(group_id, user_id):
            await answer("只有群主人或管理员能操作", en="Only the group's owner or the admin can do this")
            return
        owner = group_owner(group_id)
        crow = chat_row(group_id)
        title = crow["title"] if crow else str(group_id)
        by = "管理员" if is_admin(user_id) else "群主人"
        if choice == "main":
            set_route(group_id, None)
            if owner:
                await mark("先放着：以后在群里发 /bind c5 指定你的哪个聊天负责",
                           en="On hold: send /bind c5 in the group later to pick one of your chats")
            else:
                await mark("先放着：群消息先到主控，由它分配")
        elif choice == "new":
            if at_limit(owner) and not is_admin(user_id):
                await answer()
                await reply(user_id, limit_text(owner, "zh"), en=limit_text(owner, "en"))
                return
            conv = create_conv(f"负责群「{title}」", owner or msg_chat or 0, owner=owner)
            await assign_chat(group_id, conv, by)
            conv = conv_row(conv["id"])
            system_note("main", task_note(conv, f"{owner_text(conv)}新建了聊天负责群「{title}」"))
            await mark(f"已新建 {conv['id']} 负责这个群，" + ("马上会有一个 AI 接手" if owner else "主控会开子 agent 接手"),
                       en=f"Created {conv['id']} for this group; an AI will pick it up shortly")
        else:
            conv = conv_row(choice)
            if conv is None or conv["status"] != "open" or conv_owner(conv) != owner:
                await answer("这个聊天已关闭，换一个", en="That chat is closed; pick another")
                return
            await assign_chat(group_id, conv, by)
            await mark(f"已交给 {conv_tag(conv)}", en=f"Handed to {conv_tag(conv)}")
        mark_menu_dirty()
        return

    if data.startswith("ga:"):
        _, chat_s, uid_s = data.split(":", 2)
        group_id, uid = int(chat_s), int(uid_s)
        if not may_run_group(group_id, user_id):
            await answer("只有群主人或管理员能操作", en="Only the group's owner or the admin can do this")
            return
        if not is_granted(uid):
            await answer("他现在没有使用资格", en="They don't have access right now")
            return
        store.run("INSERT OR IGNORE INTO activations(chat_id,user_id) VALUES(?,?)", (group_id, uid))
        await mark(f"已激活 {person_label(uid)}", en=f"Activated {person_label(uid)}")
        await reply(group_id, f"已激活 {person_label(uid)}：在本群 @bot 或回复 bot 就会叫醒 agent。",
                    en=f"Activated {person_label(uid)}: mention @bot or reply to the bot in this group to wake the agent.")
        return

    if not is_admin(user_id):
        await answer("只有管理员能操作", en="Only the admin can do this")
        return

    if data.startswith("cm:"):
        parts = data.split(":")
        act = parts[1] if len(parts) > 1 else "home"

        async def show_cm(text: str, markup: dict | None) -> None:
            body: dict[str, Any] = {"chat_id": msg_chat, "message_id": message.get("message_id"), "text": text[:4000]}
            if markup:
                body["reply_markup"] = markup
            await tg.try_call("editMessageText", **body)

        if act == "home":
            await answer()
            await show_cm(*clouds_panel_view(user_id))
            return
        if act == "view" and len(parts) >= 3 and re.fullmatch(r"-?\d+", parts[2]):
            n_v = int(parts[2])
            store.set(f"view:{user_id}", str(n_v))
            mark_menu_dirty()
            await answer(f"菜单已切到 {cloud_tag(n_v)}")
            await show_cm(cloud_listing(user_id, n_v), cloud_single_markup(n_v))
            return
        if act in ("tg", "allnow") and len(parts) >= 3 and re.fullmatch(r"-?\d+", parts[2]):
            n_m = int(parts[2])
            inc_bg = act == "allnow"
            targets_m = [r for r in open_convs() if cloud_of(r) == n_m and (inc_bg or conv_in_tg(r))]
            if not targets_m and not inc_bg:
                targets_m = [r for r in open_convs() if cloud_of(r) == n_m]
            note_m = migrate_convs_to_main(targets_m, "管理员")
            await answer(f"已发起迁移 ({len(targets_m)} 个)")
            await show_cm(*clouds_panel_view(user_id, note_m))
            return
        if act == "pick" and len(parts) >= 4 and re.fullmatch(r"-?\d+", parts[2]):
            n_p = int(parts[2])
            pg_p = int(parts[3]) if parts[3].isdigit() else 0
            await answer()
            await show_cm(*cloud_pick_view(user_id, n_p, pg_p))
            return
        if act == "tog" and len(parts) >= 5 and re.fullmatch(r"-?\d+", parts[2]):
            n_p = int(parts[2])
            cid_t = parts[3]
            pg_p = int(parts[4]) if parts[4].isdigit() else 0
            sel = cm_get_selection(user_id, n_p)
            if cid_t in sel:
                sel.remove(cid_t)
            else:
                sel.add(cid_t)
            cm_save_selection(user_id, n_p, sel)
            await answer()
            await show_cm(*cloud_pick_view(user_id, n_p, pg_p))
            return
        if act in ("seltg", "selall", "selclr") and len(parts) >= 4 and re.fullmatch(r"-?\d+", parts[2]):
            n_p = int(parts[2])
            pg_p = int(parts[3]) if parts[3].isdigit() else 0
            if act == "selclr":
                sel = set()
            elif act == "seltg":
                sel = {r["id"] for r in open_convs() if cloud_of(r) == n_p and conv_in_tg(r)}
            else:
                sel = {r["id"] for r in open_convs() if cloud_of(r) == n_p}
            cm_save_selection(user_id, n_p, sel)
            await answer(f"已选 {len(sel)} 个")
            await show_cm(*cloud_pick_view(user_id, n_p, pg_p))
            return
        if act == "go" and len(parts) >= 3 and re.fullmatch(r"-?\d+", parts[2]):
            n_p = int(parts[2])
            sel = cm_get_selection(user_id, n_p)
            targets_g = [r for r in open_convs() if cloud_of(r) == n_p and r["id"] in sel]
            if not targets_g:
                await answer("请先至少勾选 1 个要迁移的聊天")
                await show_cm(*cloud_pick_view(user_id, n_p, 0, "⚠️ 尚未勾选任何聊天，请点击下方聊天勾选后再点迁移："))
                return
            store.delete(f"cm_sel:{user_id}:{n_p}")
            note_g = migrate_convs_to_main(targets_g, "管理员勾选迁移")
            await answer(f"已迁移 {len(targets_g)} 个聊天")
            await show_cm(*clouds_panel_view(user_id, note_g))
            return
        if act == "del" and len(parts) >= 3 and re.fullmatch(r"-?\d+", parts[2]):
            n_d = int(parts[2])
            await answer()
            await show_cm(*cloud_del_confirm_view(n_d))
            return
        if act == "delok" and len(parts) >= 3 and re.fullmatch(r"-?\d+", parts[2]):
            n_d = int(parts[2])
            note_d = delete_cloud(n_d, "管理员")
            await answer(f"已删除 {cloud_tag(n_d)}")
            await show_cm(*clouds_panel_view(user_id, note_d))
            return
        await answer()
        return

    if data.startswith("mv:"):
        conv_id = data[3:]
        # 一条提醒里可能有好几个聊天的按钮：点了哪个只去掉哪个
        others = [row for row in (message.get("reply_markup") or {}).get("inline_keyboard", [])
                  if not any(button.get("callback_data") == data for button in row)]

        async def settle(label: str) -> None:
            if not others:
                await mark(label)
                return
            await answer(label[:180])
            if msg_chat and message.get("message_id"):
                await tg.try_call("editMessageText", chat_id=msg_chat, message_id=message["message_id"],
                                  text=f"{original}\n\n【{label}】", reply_markup={"inline_keyboard": others})

        conv = conv_row(conv_id)
        if conv is None or conv["status"] != "open":
            await settle(f"{conv_id} 已经关了或删了")
            return
        if not away(conv):
            await settle(f"{conv_id} 已经在 {cloud_tag(main_cloud())} 了")
            return
        hand_over(conv, "管理员")
        await settle(f"已把 {conv_id} 交给 {cloud_tag(main_cloud())} 主控：旧会话已停，主控将按原模型与上下文开新子 agent 接手")
        return

    if data.startswith("nm:"):
        _, choice, nonce = (data.split(":") + ["", ""])[:3]
        pending = pending_new(user_id) if msg_chat == user_id else None
        if pending is None or pending.get("nonce") != nonce:
            await mark("已过期，要新建请重新发 /new")
            return
        if choice == "x":
            store.delete(f"newmodel:{user_id}")
            await mark("已取消，没有新建聊天")
            return
        await answer()
        if choice == "m":
            await prompt_new_model(user_id, pending)
        else:
            await finish_new(user_id, pending, "")
        return

    if data.startswith("gr:"):
        _, uid_s, gid_s = data.split(":", 2)
        result = await grant_user(int(uid_s), int(gid_s))
        await mark(result.split("\n", 1)[0])
        return

    if not data.startswith("ap:"):
        await answer()
        return
    _, approval_id, choice = data.split(":", 2)
    row = store.one("SELECT * FROM approvals WHERE id=?", (approval_id,))
    if row is None or row["status"] != "pending":
        await answer("已经处理过了")
        return
    payload = json.loads(row["payload"])
    if choice == "n":
        set_approval(approval_id, "denied")
        await mark("已拒绝")
        if row["kind"] == "device" and payload.get("user_id"):
            await reply(int(payload["user_id"]), "管理员没有批准你的本地通道申请。",
                        en="The admin did not approve your local channel application.")
        return
    if row["kind"] in ("join", "join_worker"):
        if choice == "worker":
            nid, ag_id = make_worker_node(custom_name=str(payload.get("name") or ""))
            payload.update({"agent_id": ag_id, "node_id": nid})
            set_approval(approval_id, "done", payload)
            await mark(f"已设为云端工作节点（{nid}，对模型无感常驻）")
            return
        if choice == "newmain" or choice.startswith("repmain:"):
            rep_target = choice.split(":", 1)[1] if choice.startswith("repmain:") else ""
            nid, ag_id = make_main_node(replace_node=rep_target, custom_name=str(payload.get("name") or ""))
            payload.update({"agent_id": ag_id, "node_id": nid})
            set_approval(approval_id, "done", payload)
            act_lbl = f"重连顶替 {nid}" if rep_target else f"新增主Agent {nid}"
            await mark(f"已批准：{act_lbl}（多主Agent并存，总控 ctrl 自动接管全局调度）")
            return
        # 兼容旧按钮回调（main / new）
        if choice == "new" and not cloud_has_chats(main_cloud()):
            choice = "main"
        payload["agent_id"] = make_main(new_cloud=choice == "new")
        set_approval(approval_id, "done", payload)
        await mark(f"已设为主控（{'新开' if choice == 'new' else '管'} {cloud_tag(main_cloud())}）")
        if choice == "new" and msg_chat and any(away(r) for r in open_convs()):
            store.set(f"view:{msg_chat}", str(main_cloud()))
            mark_menu_dirty()
            p_txt, p_mk = clouds_panel_view(
                msg_chat,
                f"🆕 已切换到新主控 {cloud_tag(main_cloud())}！检测到旧 cloud 里还有开放聊天，"
                f"可在下方一键或勾选迁移到 {cloud_tag(main_cloud())}（100% 继承原模型、上下文记录与 Git 分支），或删除旧 cloud 转为无主静默保留：",
            )
            await reply(msg_chat, p_txt, p_mk)
    elif row["kind"] == "device":
        owner = int(payload.get("user_id") or 0)
        if not is_granted(owner):
            set_approval(approval_id, "denied")
            await mark("这个用户已经没有使用资格了")
            return
        set_approval(approval_id, "approved")
        dev = await issue_device(owner, str(payload.get("name") or ""))
        await mark(f"已批准：{device_label(dev)}，安装文件已发给他")
    else:
        await answer()


async def ask_group_owner(chat: dict, adder: dict) -> None:
    """bot 进群：被授权的用户拉的，群归他，问他用哪个聊天负责；否则群归管理员，问管理员。"""
    group_id = chat["id"]
    title = chat.get("title") or str(group_id)
    adder_id = int(adder.get("id") or 0)
    remember_person(adder)
    owner = adder_id if adder_id and not is_admin(adder_id) and is_granted(adder_id) else 0
    store.run("UPDATE chats SET owner=? WHERE chat_id=?", (owner, group_id))
    privacy = "" if BOT["privacy_ok"] else "\n注意：bot 的隐私模式还开着，只能看到 @它 和命令。去 BotFather /setprivacy 选 Disable，然后把 bot 移出群再拉回来。"
    if owner:
        en = lang_of(owner) == "en"
        buttons = [[{"text": conv_button(r), "callback_data": f"gb:{group_id}:{r['id']}"}] for r in own_convs(owner)[-20:]]
        buttons.append([{"text": "➕ New chat for this group" if en else "➕ 新建一个聊天负责这个群", "callback_data": f"gb:{group_id}:new"}])
        buttons.append([{"text": "Later" if en else "先放着", "callback_data": f"gb:{group_id}:main"}])
        await reply(
            owner,
            f"你把 bot 拉进了群「{title}」，这个群归你。选你的哪个聊天负责它：只有你、管理员和你激活的人 @bot 或回复 bot 才会叫醒它。\n"
            "在群里回复某人发 /activate 让他也能用；/open on 让所有人都能用。",
            {"inline_keyboard": buttons},
            en=f"You added the bot to the group \"{title}\", so the group is yours. Pick which of your chats handles it. "
               "Only you, the admin and people you activate can wake it by mentioning @bot or replying to the bot.\n"
               "In the group, reply to someone with /activate to let them use it; /open on lets everyone use it.",
        )
        await notify_admins(f"用户 {person_label(owner)} 把 bot 拉进了群「{title}」({group_id})，这个群归他管。{privacy}")
        return
    buttons = [[{"text": conv_button(r), "callback_data": f"gb:{group_id}:{r['id']}"}] for r in own_convs(0)[-20:]]
    buttons.append([{"text": "➕ 新建一个聊天负责这个群", "callback_data": f"gb:{group_id}:new"}])
    buttons.append([{"text": "先放着（消息先到主控分配）", "callback_data": f"gb:{group_id}:main"}])
    await notify_admins(
        f"bot 被拉进群「{title}」({group_id})。选一个聊天负责这个群：只有它进群，群里 @bot 或回复 bot 才会叫醒它。\n"
        f"群里回复某人发 /grant 就授权并在本群激活他；/open on 让所有人可用。{privacy}",
        {"inline_keyboard": buttons},
    )


async def on_member(update: dict) -> None:
    chat = update.get("chat") or {}
    status = (update.get("new_chat_member") or {}).get("status")
    old_status = (update.get("old_chat_member") or {}).get("status")
    if chat.get("type") not in ("group", "supergroup"):
        return
    upsert_chat(chat)
    if status in ("member", "administrator") and old_status in (None, "left", "kicked"):
        await ask_group_owner(chat, update.get("from") or {})
    elif status in ("left", "kicked"):
        old = route_of(chat["id"])
        if old:
            set_route(chat["id"], None)
            system_note(old, f"bot 已被移出群「{chat.get('title')}」，这个群不归你负责了。", wake=0)
        owner = group_owner(chat["id"])
        if owner and is_granted(owner):
            await reply(owner, f"bot 已离开你的群「{chat.get('title')}」。", en=f"The bot has left your group \"{chat.get('title')}\".")
        await notify_admins(f"bot 已离开群「{chat.get('title')}」({chat['id']})。")


async def telegram_loop() -> None:
    offset = int(store.get("tg_offset", "0") or 0)
    while True:
        try:
            updates = await tg.call(
                "getUpdates",
                offset=offset,
                timeout=50,
                allowed_updates=["message", "callback_query", "my_chat_member"],
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("getUpdates: %s", exc)
            await asyncio.sleep(3)
            continue
        for update in updates or []:
            offset = int(update["update_id"]) + 1
            store.set("tg_offset", str(offset))
            try:
                if "message" in update:
                    await on_message(update["message"])
                elif "callback_query" in update:
                    await on_callback(update["callback_query"])
                elif "my_chat_member" in update:
                    await on_member(update["my_chat_member"])
            except Exception:
                log.exception("update %s failed", update.get("update_id"))


# ---------------------------------------------------------------- 菜单和看门狗

def menu_desc(row, info: dict[str, Any], current: bool, lang: str = "zh") -> str:
    en = lang == "en"
    parts = []
    if info["unread"]:
        parts.append(f"🔴 {info['unread']} new" if en else f"🔴 {info['unread']}条新消息")
    if not info["unread"] or info["state"] in ("stuck", "lost", "unclaimed"):
        parts.append(state_text(info["state"], lang))
    desc = " ".join(parts) + " · " + conv_name(row)
    if current:
        desc += " · current" if en else " · 当前"
    return desc[:256]


def admin_cloud_rows(dm: int, n: int) -> list:
    """管理员菜单里 cloud n 的聊天：他自己的、在这个私聊里的。"""
    return [r for r in open_convs() if cloud_of(r) == n and enterable(dm, r) and home_of(r) == dm]


def admin_clouds(dm: int) -> list[int]:
    return cloud_order({cloud_of(r) for r in open_convs() if enterable(dm, r) and home_of(r) == dm} | {main_cloud()})


def cloud_view(dm: int) -> int:
    """管理员菜单正在看哪个 cloud：自己切过去的（那里还有聊天）> 正在聊的那个聊天所在的 > 现在主控的。"""
    clouds = admin_clouds(dm)
    raw = store.get(f"view:{dm}")
    if raw and re.fullmatch(r"-?\d+", raw) and int(raw) in clouds:
        return int(raw)
    row = conv_row(selected(dm))
    if row is not None and row["id"] != "main" and cloud_of(row) in clouds:
        return cloud_of(row)
    return main_cloud()


def cloud_desc(dm: int, n: int, viewing: bool) -> str:
    rows = admin_cloud_rows(dm, n)
    prefix = "📂 无主静默" if n == UNOWNED_CLOUD else ("📁 主控" if n == main_cloud() else "📁 旧cloud")
    parts = [prefix, f"{len(rows)} 个聊天"]
    unread = sum(unread_count(r["id"], dm) for r in rows)
    if unread:
        parts.append(f"🔴 {unread}条新消息")
    if n == main_cloud():
        alerts = sum(1 for r in rows if conv_state(r)["state"] in ("stuck", "lost", "unclaimed"))
        if alerts:
            parts.append(f"⚠️ {alerts}")
    if viewing:
        parts.append("正在看")
    return " · ".join(parts)


def cloud_listing(dm: int, n: int) -> str:
    rows = admin_cloud_rows(dm, n)
    bg_rows = [r for r in open_convs() if cloud_of(r) == n and not conv_in_tg(r)]
    lines = [cloud_heading(n)]
    for row in rows:
        m_lbl = effective_conv_model(row)
        m_txt = f" · [{m_lbl}]" if m_lbl else ""
        line = f"/{row['id']} {conv_name(row)}{m_txt} · {STATE_TEXT[conv_state(row)['state']]}"
        unread = unread_count(row["id"], dm)
        if unread:
            line += f" · 🔴 {unread}条新消息"
        lines.append(line)
    if bg_rows:
        lines.append(f"🔧 另有 {len(bg_rows)} 个后台派生子工：" + "、".join(r["id"] for r in bg_rows[:12]) + ("…" if len(bg_rows) > 12 else ""))
    if not rows and not bg_rows:
        lines.append("（这里现在没有开放的聊天）")
    users = sum(1 for r in open_convs() if cloud_of(r) == n and conv_owner(r))
    if users:
        lines.append(f"另有被授权用户的聊天 {users} 个（/list 里看）。")
    if (rows or bg_rows) and n != main_cloud():
        lines.append(f"💡 可直接点下方按钮迁移至 {cloud_tag(main_cloud())}（保留原模型与上下文），或删除该旧 cloud 转为无主。")
    lines.append(f"菜单已换成 {cloud_tag(n)} 的聊天（重新打 / 就能看到）。")
    return "\n".join(lines)


def cloud_single_markup(n: int) -> dict | None:
    cur = main_cloud()
    c_rows = [r for r in open_convs() if cloud_of(r) == n]
    tg_cnt = sum(1 for r in c_rows if conv_in_tg(r))
    buttons: list[list[dict]] = []
    if n != cur and c_rows:
        row1: list[dict] = []
        if tg_cnt:
            row1.append({"text": f"📦 迁主聊天({tg_cnt}个)→{cloud_tag(cur)}", "callback_data": f"cm:tg:{n}"})
        else:
            row1.append({"text": f"📦 全迁({len(c_rows)}个)→{cloud_tag(cur)}", "callback_data": f"cm:allnow:{n}"})
        row1.append({"text": "☑️ 勾选迁移", "callback_data": f"cm:pick:{n}:0"})
        buttons.append(row1)
        row2: list[dict] = []
        if len(c_rows) > tg_cnt > 0:
            row2.append({"text": f"📦 全迁含子工({len(c_rows)}个)", "callback_data": f"cm:allnow:{n}"})
        if n != UNOWNED_CLOUD:
            row2.append({"text": f"🗑 删除 {cloud_tag(n)}（转无主）", "callback_data": f"cm:del:{n}"})
        if row2:
            buttons.append(row2)
    elif n == cur and c_rows:
        buttons.append([{"text": f"🗑 解散 {cloud_tag(n)} 聊天为无主", "callback_data": f"cm:del:{n}"}])
    buttons.append([{"text": "☁️ 打开全部 Cloud 管理面板 (/clouds)", "callback_data": "cm:home"}])
    return {"inline_keyboard": buttons}


def cm_get_selection(user_id: int, n: int) -> set[str]:
    key = f"cm_sel:{user_id}:{n}"
    raw = store.get(key)
    valid_all = {r["id"] for r in open_convs() if cloud_of(r) == n}
    if not raw:
        default_tg = {r["id"] for r in open_convs() if cloud_of(r) == n and conv_in_tg(r)}
        return default_tg or valid_all
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            return {str(x) for x in arr if str(x) in valid_all}
    except Exception:
        pass
    return set()


def cm_save_selection(user_id: int, n: int, sel: set[str]) -> None:
    store.set(f"cm_sel:{user_id}:{n}", json.dumps(sorted(sel), ensure_ascii=False))


def delete_cloud(n: int, by: str = "管理员") -> str:
    """删除某个 cloud：停掉其下所有旧子 agent 会话，把聊天全部转为无主待机池（cloud=-1），保留全部记录/模型/分支且不再告警。"""
    if n == UNOWNED_CLOUD:
        return "📂 这已经是无主池了（里面的聊天均已脱离旧 cloud 静默保留；若要彻底删除单个聊天请在 /list 里删）。"
    rows = [r for r in store.q("SELECT * FROM convs WHERE id!='main' AND status!='deleted'") if cloud_of(r) == n]
    if not rows and n != main_cloud():
        sync_admin_view_after_cloud_change(emptied_cloud=n)
        return f"{cloud_tag(n)} 里已经没有任何聊天，已清理完毕。"
    open_cnt = 0
    bg_cnt = 0
    for r in rows:
        lock_in_conv_model(r)
        old = active_agent(r)
        if old is not None:
            stop_identity(old["id"], f"{by}删除了 {cloud_tag(n)}，聊天转为无主静默保留")
        store.run(
            "UPDATE convs SET cloud=?, agent='', task_code='', task_agent_id='', alert='', alert_ts=0 WHERE id=?",
            (UNOWNED_CLOUD, r["id"]),
        )
        if r["status"] == "open":
            open_cnt += 1
            if not conv_in_tg(r):
                bg_cnt += 1
    sync_admin_view_after_cloud_change(emptied_cloud=n)
    log.info("cloud %s deleted by %s: %d chats moved to unowned pool", cloud_tag(n), by, len(rows))
    tg_cnt = open_cnt - bg_cnt
    detail = f"{tg_cnt} 个主聊天" + (f" + {bg_cnt} 个后台子工" if bg_cnt else "")
    return (
        f"🗑 已删除 {cloud_tag(n)}！原属其中的 {detail} 已全部转为【📂 无主池】静默保留：\n"
        "• 旧僵尸身份已全部停用，绝不再弹任何失联提醒；\n"
        "• 原定模型、聊天记录、记忆摘要与 GitHub 分支 100% 完整保留，随时可在下方点迁移由当前主控原地复活。"
    )


def migrate_convs_to_main(convs_list: list, by: str = "管理员") -> str:
    """批量或单选将旧 cloud / 无主池中的开放聊天迁移至当前活跃主控（100% 继承原模型、记忆、Git 分支与上下文）。"""
    cur = main_cloud()
    targets = []
    seen = set()
    for r in convs_list:
        row = conv_row(r["id"]) if (not isinstance(r, str) and hasattr(r, "__getitem__")) else conv_row(str(r))
        if row is None or row["id"] == "main" or row["status"] != "open" or row["id"] in seen:
            continue
        seen.add(row["id"])
        targets.append(row)
    if not targets:
        return "⚠️ 没有找到需要迁移的开放聊天。"
    migrated_labels = []
    total = len(targets)
    for idx, conv in enumerate(targets):
        old_c = cloud_of(conv)
        restart_conv(conv, f"{by}从 {cloud_tag(old_c)} 迁移到 {cloud_tag(cur)} 主控接手")
        fresh = conv_row(conv["id"])
        m_lbl = effective_conv_model(fresh)
        migrated_labels.append(f"{fresh['id']}「{conv_name(fresh)}」" + (f"[{m_lbl}]" if m_lbl else ""))
        is_last = idx == total - 1
        why_txt = f"{by}从 {cloud_tag(old_c)} 迁移聊天到 {cloud_tag(cur)} 交给你接手（共迁移 {total} 个，第 {idx + 1}/{total} 个；请严格保持原模型与完整上下文后台拉起）"
        system_note("main", task_note(fresh, why_txt), wake=1 if is_last else 0)
    sync_admin_view_after_cloud_change(target_conv_id=targets[0]["id"])
    preview = "、".join(migrated_labels[:12]) + (f" 等共 {total} 个" if total > 12 else "")
    return (
        f"✅ 已将 {total} 个聊天迁移至 {cloud_tag(cur)} 并下发当前主控按原模型拉起：\n"
        f"{preview}\n"
        "（原模型、历史上下文、工作现场快照、协作群与 GitHub 分支均已完整带过去！）"
    )


def clouds_panel_view(dm: int, note: str = "") -> tuple[str, dict]:
    cur = main_cloud()
    rows = open_convs()
    all_clouds = cloud_order({cloud_of(r) for r in rows} | {cur})
    main_info = conv_state(conv_row("main"))
    lines = []
    if note:
        lines += [note, ""]
    lines.append(f"☁️ Cloud 目录管理与无缝迁移中心（当前活跃主控：{cloud_tag(cur)} · {STATE_TEXT[main_info['state']]}）")
    buttons: list[list[dict]] = []
    for n in all_clouds:
        c_rows = [r for r in rows if cloud_of(r) == n]
        tg_rows = [r for r in c_rows if conv_in_tg(r)]
        bg_cnt = len(c_rows) - len(tg_rows)
        if n == cur:
            hdr = f"\n🟢 📁 {cloud_tag(n)}（当前主控）：{len(tg_rows)} 个主聊天" + (f" + {bg_cnt} 个后台子工" if bg_cnt else "")
        elif n == UNOWNED_CLOUD:
            hdr = f"\n📂 {cloud_tag(n)}（已删旧 cloud 静默留存）：{len(tg_rows)} 个主聊天" + (f" + {bg_cnt} 个后台子工" if bg_cnt else "")
        else:
            hdr = f"\n⚪ 📁 {cloud_tag(n)}（旧 cloud · 无主控）：{len(tg_rows)} 个主聊天" + (f" + {bg_cnt} 个后台子工" if bg_cnt else "")
        lines.append(hdr)
        shown = tg_rows or c_rows
        if shown:
            sample = "、".join(
                f"/{r['id']} {conv_name(r)}" + (f"[{effective_conv_model(r)}]" if effective_conv_model(r) else "")
                for r in shown[:8]
            )
            if len(shown) > 8:
                sample += f" 等 {len(shown)} 个"
            lines.append("  " + sample)
        else:
            lines.append("  （暂无聊天）")
        if n != cur and c_rows:
            lbl = cloud_tag(n)
            r1: list[dict] = []
            if tg_rows:
                r1.append({"text": f"📦 迁 {lbl} 主聊天({len(tg_rows)}个)→{cloud_tag(cur)}"[:64], "callback_data": f"cm:tg:{n}"})
            else:
                r1.append({"text": f"📦 全迁 {lbl}({len(c_rows)}个)→{cloud_tag(cur)}"[:64], "callback_data": f"cm:allnow:{n}"})
            r1.append({"text": f"☑️ 勾选迁移 {lbl}", "callback_data": f"cm:pick:{n}:0"})
            buttons.append(r1)
            r2: list[dict] = []
            if bg_cnt and tg_rows:
                r2.append({"text": f"📦 全迁 {lbl} 含子工({len(c_rows)}个)", "callback_data": f"cm:allnow:{n}"})
            if n != UNOWNED_CLOUD:
                r2.append({"text": f"🗑 删除 {lbl}（聊天转无主）", "callback_data": f"cm:del:{n}"})
            if r2:
                buttons.append(r2)
    if len(all_clouds) == 1 and not any(away(r) for r in rows):
        lines.append("\n✨ 当前所有开放聊天都在活跃主控名下，没有残留的旧 cloud 或无主聊天。")
    cur_rows = [r for r in rows if cloud_of(r) == cur]
    bottom = [{"text": f"👁 切菜单看 {cloud_tag(cur)}", "callback_data": f"cm:view:{cur}"},
              {"text": "🔄 刷新", "callback_data": "cm:home"}]
    buttons.append(bottom)
    if cur_rows:
        buttons.append([{"text": f"🗑 解散当前 {cloud_tag(cur)} 聊天为无主池", "callback_data": f"cm:del:{cur}"}])
    return "\n".join(lines), {"inline_keyboard": buttons}


def cloud_pick_view(dm: int, n: int, page: int = 0, note: str = "") -> tuple[str, dict]:
    cur = main_cloud()
    c_rows = sorted(
        [r for r in open_convs() if cloud_of(r) == n],
        key=lambda r: (0 if conv_in_tg(r) else 1, r["num"]),
    )
    if not c_rows:
        return clouds_panel_view(dm, f"{cloud_tag(n)} 里已经没有开放聊天了。")
    sel = cm_get_selection(dm, n)
    per_page = 10
    pages = (len(c_rows) + per_page - 1) // per_page
    page = min(max(page, 0), pages - 1)
    head = (
        f"☑️ 勾选要从「{cloud_tag(n)}」迁移到「{cloud_tag(cur)}」的聊天（已选 {len(sel)}/{len(c_rows)} 个）：\n"
        "• 点击聊天切换勾选（🔧 表示后台派生子工；方括号为原模型，迁移后 100% 保持一致）"
    )
    if pages > 1:
        head += f"\n（第 {page + 1}/{pages} 页）"
    if note:
        head = note + "\n\n" + head
    buttons: list[list[dict]] = [
        [
            {"text": "全选主聊天", "callback_data": f"cm:seltg:{n}:{page}"},
            {"text": "全选含子工", "callback_data": f"cm:selall:{n}:{page}"},
            {"text": "清空", "callback_data": f"cm:selclr:{n}:{page}"},
        ]
    ]
    for r in c_rows[page * per_page:(page + 1) * per_page]:
        mark_box = "✅" if r["id"] in sel else "⬜"
        bg_icon = " 🔧" if not conv_in_tg(r) else ""
        m_lbl = effective_conv_model(r)
        m_badge = f" [{m_lbl[:14]}]" if m_lbl else ""
        lbl = f"{mark_box} {r['id']} {conv_name(r)}{bg_icon}{m_badge}"[:64]
        buttons.append([{"text": lbl, "callback_data": f"cm:tog:{n}:{r['id']}:{page}"}])
    if pages > 1:
        nav = []
        if page > 0:
            nav.append({"text": "◀ 上一页", "callback_data": f"cm:pick:{n}:{page - 1}"})
        if page < pages - 1:
            nav.append({"text": "下一页 ▶", "callback_data": f"cm:pick:{n}:{page + 1}"})
        buttons.append(nav)
    buttons.append([{"text": f"🚀 立即迁移已选 ({len(sel)}个) → {cloud_tag(cur)}"[:64], "callback_data": f"cm:go:{n}"}])
    buttons.append([{"text": "↩ 返回 Cloud 管理 (/clouds)", "callback_data": "cm:home"}])
    return head, {"inline_keyboard": buttons}


def cloud_del_confirm_view(n: int) -> tuple[str, dict]:
    c_rows = [r for r in open_convs() if cloud_of(r) == n]
    tg_cnt = sum(1 for r in c_rows if conv_in_tg(r))
    bg_cnt = len(c_rows) - tg_cnt
    desc = f"{tg_cnt} 个主聊天" + (f" + {bg_cnt} 个后台子工" if bg_cnt else "")
    text = (
        f"🗑 确定删除「{cloud_tag(n)}」吗？\n\n"
        f"• 其中 {desc} 会停掉旧子 agent 会话，并统一转入【📂 无主池】静默保留；\n"
        "• 聊天记录、原定模型、记忆摘要、GitHub 分支 **全部保留不删**，且不会再弹任何失联警报；\n"
        f"• 之后随时可在 /clouds 一键或勾选迁入 {cloud_tag(main_cloud())} 原地唤醒。"
    )
    markup = {
        "inline_keyboard": [
            [{"text": f"✅ 确认删除 {cloud_tag(n)}（聊天转无主静默）", "callback_data": f"cm:delok:{n}"}],
            [{"text": "↩ 取消返回", "callback_data": "cm:home"}],
        ]
    }
    return text, markup


def move_to_cloud(n: int, words: list[str]) -> str:
    """/cloud2 c5 c7：只改归属（分错了时用），不换子 agent。"""
    moved, bad = [], []
    for word in words:
        conv_id = parse_conv(word)
        row = conv_row(conv_id) if conv_id and conv_id != "main" else None
        if row is None or row["status"] == "deleted":
            bad.append(word)
            continue
        if cloud_of(row) != n:
            store.run("UPDATE convs SET cloud=?, alert='', alert_ts=0 WHERE id=?", (n, row["id"]))
            moved.append(row)
    mark_menu_dirty()
    lines = []
    if moved:
        names = "、".join(conv_tag(r) for r in moved)
        lines.append(f"已把 {names} 挪进 {cloud_tag(n)}（只改归属，子 agent 没换）。")
        if n == main_cloud():
            system_note("main", f"管理员把 {names} 划进了你的 {cloud_tag(n)}（子 agent 没换）：之后它们归你管，看门狗也会提醒你。", wake=0)
        else:
            lines.append(f"{cloud_tag(main_cloud())} 的主控日常不再自动巡检它们；随时可用 /clouds 迁移。")
    if bad:
        lines.append("没找到：" + " ".join(bad))
    return "\n".join(lines) or f"它们本来就在 {cloud_tag(n)}。"


def build_menu(dm: int) -> list[dict]:
    """私聊的命令菜单就是聊天列表：管理员看自己的聊天和主控，用户只看自己建的。
    管理员的聊天分在几个 cloud 里时，菜单只列正在看的那个 cloud，再加上每个 cloud 一条 /cloudN 用来切换。"""
    current = selected(dm)
    admin = dm in admin_chats()
    lang = "zh" if admin else lang_of(dm)
    clouds = admin_clouds(dm) if admin else []
    view = cloud_view(dm) if len(clouds) > 1 else 0
    commands = []
    for row in open_convs():
        if not enterable(dm, row) or (admin and home_of(row) != dm):
            continue
        if view and cloud_of(row) != view:
            continue
        info = conv_state(row)
        info["unread"] = unread_count(row["id"], dm)
        commands.append({"command": row["id"], "description": menu_desc(row, info, row["id"] == current, lang)})
    if not admin:
        return (commands + MEMBER_COMMANDS[lang])[:100]
    ctrl_row = conv_row("ctrl") if ctrl_is_active() else conv_row("main")
    if ctrl_row is not None:
        info = conv_state(ctrl_row)
        info["unread"] = unread_count(ctrl_row["id"], dm)
        commands.append({"command": "ctrl", "description": f"🧠 唯一总控大脑 · {STATE_TEXT.get(info['state'], info['state'])}"})
    main = conv_row("main")
    info_m = conv_state(ctrl_row or main)
    info_m["unread"] = unread_count((ctrl_row or main)["id"], dm)
    commands.append({"command": "main", "description": menu_desc(ctrl_row or main, info_m, current in ("main", "ctrl"))})
    for mnode in store.q("SELECT * FROM exec_nodes WHERE kind='launcher' AND status!='removed' ORDER BY num"):
        mc = conv_row(mnode["id"])
        if mc is not None:
            mi = conv_state(mc)
            mi["unread"] = unread_count(mc["id"], dm)
            commands.append({"command": mc["id"], "description": menu_desc(mc, mi, current == mc["id"])})
    commands.append({"command": "nodes", "description": "🖥 集群机器池 / CPU内存探针 / 算力机与Web台"})
    commands.append({"command": "clouds", "description": "☁️ Cloud 目录管理 / 聊天迁移 / 删除旧Cloud"})
    if view:
        commands += [{"command": cloud_cmd(n), "description": cloud_desc(dm, n, n == view)} for n in cloud_order(clouds)]
    commands += [
        {"command": "new", "description": "➕ 新建聊天"},
        {"command": "device", "description": "💻 电脑免批时长与本地通道管理"},
        {"command": "local", "description": "🔧 当前聊天本地授权时长"},
        {"command": "trace", "description": "🔎 AI 实时动作/改文件/思考追踪"},
        {"command": "list", "description": "🗂 管理聊天（切换 / 删除）"},
        {"command": "history", "description": "📜 所有聊天（含已关闭）"},
        {"command": "help", "description": "帮助"},
        {"command": "language", "description": "语言 / Language"},
    ]
    return commands[:100]


async def refresh_menus() -> None:
    for dm in hub_chats():
        commands = build_menu(dm)
        key = json.dumps(commands, ensure_ascii=False)
        if MENU["cache"].get(dm) == key:
            continue
        ok = await tg.try_call("setMyCommands", commands=commands, scope={"type": "chat", "chat_id": dm})
        if ok:
            MENU["cache"][dm] = key


async def menu_loop() -> None:
    event = MENU["event"]
    while True:
        await event.wait()
        await asyncio.sleep(MENU_DELAY)
        event.clear()
        try:
            await refresh_menus()
        except Exception:
            log.exception("menu refresh failed")


async def set_default_commands() -> None:
    # 默认英文；选了中文的私聊和群在 set_lang 里单独设
    await tg.try_call("setMyCommands", commands=USER_COMMANDS["en"])
    await tg.try_call("setMyCommands", commands=GROUP_COMMANDS["en"], scope={"type": "all_group_chats"})


def hand_over_markup(conv) -> dict:
    return {"inline_keyboard": [[{"text": f"交给 {cloud_tag(main_cloud())} 主控", "callback_data": f"mv:{conv['id']}"}]]}


def hand_over(conv, by: str) -> int:
    """别的 cloud 的聊天交给现在的主控：旧子 agent 停掉，主控在自己的云端 agent 里开新的接手。返回原来的 cloud。"""
    old = cloud_of(conv)
    restart_conv(conv, f"{by}把这个聊天交给了 {cloud_tag(main_cloud())} 的主控")
    conv = conv_row(conv["id"])
    system_note("main", task_note(conv, f"{by}把 {cloud_tag(old)} 的聊天交给你（记录都在，新子 agent 接手后能看到）"))
    log.info("conv %s handed over from %s to %s", conv["id"], cloud_tag(old), cloud_tag(main_cloud()))
    return old


def away_alert_text(conv, info: dict[str, Any]) -> str:
    there, here = cloud_tag(cloud_of(conv)), cloud_tag(main_cloud())
    return (f"{there} 的 {conv_tag(conv)} {describe(info)}。它的子 agent 在 {there}（原来的云端 agent）里，{here} 的主控叫不醒它。\n"
            f"它自己回来就没事；要换人接手就点【交给 {here} 主控】：旧的子 agent 停掉，{here} 主控开一个新的接手，"
            f"聊天记录和 GitHub 分支都带过去，这个聊天挪进 {here}。")


def alert_due(conv, key: str) -> bool:
    """记下看门狗现在的警告，返回要不要提醒。"""
    if not key:
        if conv["alert"]:
            store.run("UPDATE convs SET alert='', alert_ts=0 WHERE id=?", (conv["id"],))
        return False
    # 别的 cloud 的提醒是发给管理员的：同一件事只说一次，不像提醒主控那样隔一阵再催
    if conv["alert"] == key and (key == "away" or now() - conv["alert_ts"] < ALERT_REPEAT):
        return False
    store.run("UPDATE convs SET alert=?, alert_ts=? WHERE id=?", (key, now(), conv["id"]))
    log.info("alert %s: %s", conv["id"], key)
    return True


async def raise_alert(conv, key: str, text: str) -> None:
    if not alert_due(conv, key):
        return
    if conv["id"] == "main":
        await notify_admins("⚠️ " + text)
    else:
        system_note("main", "【看门狗】" + text)


async def notify_away(batch: list) -> None:
    """别的 cloud 的子 agent 出了问题：告诉管理员，一次检查查出来的合成一条（重启后它们会同时失联）。"""
    if len(batch) == 1:
        conv, info = batch[0]
        await notify_admins("⚠️ " + away_alert_text(conv, info), hand_over_markup(conv), conv_id=conv["id"])
    elif batch:
        here = cloud_tag(main_cloud())
        lines = [f"⚠️ 这几个聊天的子 agent 没在等消息。它们在别的 cloud（原来的云端 agent）里，{here} 的主控叫不醒："]
        lines += [f"{cloud_tag(cloud_of(conv))} 的 {conv_tag(conv)} {describe(info)}" for conv, info in batch]
        lines.append(f"它们自己回来就没事；要换人接手就点对应的按钮：旧的子 agent 停掉，{here} 主控开一个新的接手，"
                     f"聊天记录和 GitHub 分支都带过去，聊天挪进 {here}。")
        markup = {"inline_keyboard": [[{"text": f"交给 {here} 主控：{conv_button(conv)}"[:64], "callback_data": f"mv:{conv['id']}"}]
                                      for conv, _ in batch]}
        await notify_admins("\n".join(lines), markup)


def auto_restart_stuck_conv(conv, stuck_sec: float) -> str:
    """当检测到处于 thinking 阶段（非 shell、非挂起等待）卡死超过 5 分钟时，自动保持原模型与完整上下文原地重开！"""
    lock_in_conv_model(conv)
    old_ag = active_agent(conv)
    if old_ag is not None:
        stop_identity(old_ag["id"], f"思考阶段卡死 {human_dur(stuck_sec)}（超 5 分钟）自动重开")
    store.run("UPDATE convs SET task_agent_id='', auto_restarted_ts=? WHERE id=?", (now(), conv["id"]))
    cnum = cloud_of(conv)
    launcher = store.one("SELECT * FROM exec_nodes WHERE kind='launcher' AND cloud_num=? AND status='online'", (cnum,))
    if launcher is None or not node_is_online(launcher):
        launcher = select_best_launcher(for_conv=conv["id"])
    if launcher is not None and is_main_node_id(launcher["id"]):
        op_id, nid = enqueue_launch_op(conv, launcher, requester="watchdog_auto_restart")
        system_note(
            route_control_target(),
            f"🔄 【5分钟思考卡死自动重开】{conv_tag(conv)} 在 `thinking` 阶段停滞 {human_dur(stuck_sec)} 无新思考产出（已排除 shell 命令），"
            f"已自动保留原模型与上下文向 {nid} 下发标准化 `[TASK_LAUNCH]` 重开单（op_id={op_id}）！",
            wake=0,
        )
        return nid
    issue_task(conv["id"])
    conv_fresh = conv_row(conv["id"])
    system_note(route_control_target(), task_note(conv_fresh, f"思考卡死 {human_dur(stuck_sec)} 自动重开"), wake=1)
    return "main"


async def watchdog_tick() -> None:
    mark_menu_dirty()
    if store.one("SELECT 1 FROM exec_nodes WHERE kind='launcher' AND status='online'"):
        ensure_controller_alive()
    for conv in open_convs():
        info = conv_state(conv)
        state, key, text = info["state"], "", ""
        trow_w = store.one("SELECT * FROM agent_traces WHERE conv=?", (conv["id"],))
        think_stuck, stuck_sec = check_thinking_stuck(conv, trow_w)
        if think_stuck and not is_unowned(conv) and (now() - float(conv["auto_restarted_ts"] or 0)) >= THINK_STUCK_SEC:
            auto_restart_stuck_conv(conv, stuck_sec)
            continue
        if away(conv) and state != "unclaimed":
            # 旧 cloud 或无主池里的聊天不再反复弹任何失联/没等消息提醒打扰管理员
            continue
        if state in ("stuck", "lost"):
            tid = (conv["task_agent_id"] or "").strip()
            is_zombie, _, last_act = trace_liveness(trow_w)
            phase_cur = (trow_w["phase"] if trow_w else "") or ""
            # 若当前明确在跑 shell 命令，不要误发僵尸重启告警
            if phase_cur == "shell" and not is_zombie:
                continue
            tline = trace_one_liner(conv["id"])
            trace_info = f"\n实时追踪状态：{tline}" if tline else ""
            tid_hint = f"（记录的旧agent_id=\"{tid}\"）" if tid else "（用你启动它时拿到的旧agent_id）"
            if is_zombie:
                key = "zombie"
                text = (
                    f"{conv_tag(conv)} {describe(info)}。{trace_info}\n"
                    f"🚨 判死结论：该子 agent 最后思考/动作时间停留在 {human_dur(now() - last_act)} 前，已确认为【僵尸假活】（此时即使调用 Task resume 返回 `currently running` 也是底层流卡死假象，绝不能等）！\n"
                    f"请立即调用 `dispatch_task_op(chat=\"{conv['id']}\", action=\"restart\")` 或 `restart_agent(chat=\"{conv['id']}\")` 拿新任务码 → `Task(prompt=桥给的原文, run_in_background=true)` 重新拉起接手（进度已在库和 Git 中保留）！"
                )
            else:
                key = state
                text = (
                    f"{conv_tag(conv)} {describe(info)}。{trace_info}\n"
                    f"请严格按 [主控] 三句处理：\n"
                    f"1) 先判活/续跑：调用 `dispatch_task_op(chat=\"{conv['id']}\", action=\"resume\")` 或 Task(resume=旧agent_id, prompt=\"请立刻回到 dais read_chat 继续挂起等待并处理未读消息\", run_in_background=true){tid_hint}；\n"
                    f"2) 若 resume 回「currently running」且上方【最后思考/终端输出】仍在刷新（或处于 shell 正常跑命令） = 活着别动；若处于 thinking 停滞超过 5 分钟 = 思考卡死，按已死处理；\n"
                    f"3) 若已死（timeout/aborted/思考卡死），直接调 `dispatch_task_op(chat=\"{conv['id']}\", action=\"restart\")` 或 restart_agent(chat=\"{conv['id']}\") 拿新任务码 → Task(prompt=桥给的原文, run_in_background=true)（**run_in_background=true 是唯一防卡死关键**，进度靠 git 保）。"
                )
        elif state == "unclaimed":
            if is_unowned(conv):
                continue
            if away(conv):
                # 任务只有现在的主控能开
                store.run("UPDATE convs SET cloud=? WHERE id=?", (main_cloud(), conv["id"]))
                conv = conv_row(conv["id"])
            key = "unclaimed"
            text = (f"{conv_tag(conv)} 的任务发出 {human_dur(now() - conv['task_ts'])} 了，还没有子 agent 接手。"
                    f"请立刻调用 Task(prompt=下面两条 ---- 之间的原文, run_in_background=true) 在后台启动子 agent（**run_in_background=true 是唯一防卡死关键**！）。{model_hint(conv)}\n"
                    f"----\n{task_text(conv)}\n----")
        if key and conv["id"] != "main":
            if alert_due(conv, key):
                system_note(route_control_target(), "【看门狗】" + text)
        else:
            await raise_alert(conv, key, text)
    main = conv_row("main")
    info = conv_state(main)
    key, text = "", ""
    if info["state"] == "stuck":
        key = "stuck"
        text = f"主控卡住了：{info['pending']} 条消息没人接（最早 {human_dur(now() - info['oldest'])} 前），主控没在等消息。"
    elif info["state"] == "lost":
        key = "lost"
        text = f"主控 {human_dur(info['idle'])} 没有动静，也没在等消息，可能停了。"
    if key:
        text += ("去 cursor.com/agents 打开主控那个云端聊天，发：\n" + RESUME_PROMPT
                 + "\n或者新开一个云端聊天，用 /key 里的开场提示词重新接入。")
    await raise_alert(main, key, text)


async def watchdog_loop() -> None:
    while True:
        await asyncio.sleep(WATCHDOG_SEC)
        try:
            await watchdog_tick()
        except Exception:
            log.exception("watchdog failed")


# ---------------------------------------------------------------- 应用

@asynccontextmanager
async def lifespan(_app: FastAPI):
    notes = migrate_v1(store, DATA / "app.db")
    ensure_main_conv()
    split_notes, tell_main = split_clouds()
    notes += split_notes
    if tell_main:
        system_note("main", tell_main)
    migrate_cluster_v360()
    build_runtime_pyz()
    ensure_admin_device()
    MENU["event"] = asyncio.Event()
    tasks = [asyncio.create_task(watchdog_loop())]
    if TG_TOKEN:
        try:
            me = await tg.call("getMe")
            BOT.update(id=me["id"], username=me.get("username", ""), privacy_ok=bool(me.get("can_read_all_group_messages")))
        except Exception as exc:
            log.error("getMe failed: %s", exc)
        await set_default_commands()
        tasks.append(asyncio.create_task(telegram_loop()))
        tasks.append(asyncio.create_task(menu_loop()))
        mark_menu_dirty()
        log.info("bridge %s started as @%s, privacy_ok=%s, migrated=%s", VERSION, BOT["username"], BOT["privacy_ok"], notes)
        startup = "TG 桥已启动。打 / 看聊天列表，/help 看用法。"
        if notes:
            startup += "\n已从旧版迁移：" + "；".join(notes)
        if BOT["username"] and not BOT["privacy_ok"]:
            startup += "\n注意：bot 隐私模式开着，群里只能看到 @它 的消息。去 BotFather /setprivacy 选 Disable。"
        await notify_admins(startup)
    else:
        log.warning("bridge %s started without TG_TOKEN: MCP only, Telegram is not connected", VERSION)
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/healthz")
async def healthz() -> JSONResponse:
    main = conv_row("main")
    return JSONResponse({
        "ok": True,
        "version": VERSION,
        "telegram": bool(TG_TOKEN),
        "bot": BOT["username"],
        "main": conv_state(main)["state"] if main else "absent",
        "cloud": main_cloud(),
        "chats_open": len(open_convs()),
        "waiting": len(waiting),
        "local_client": bool(LOCAL["clients"]),
    })


@app.post("/mcp/main")
@app.post("/mcp")
async def mcp_post(request: Request) -> Response:
    return await mcp_handle(request)


@app.get("/wait")
async def wait_get(request: Request) -> Response:
    agent_id = request.headers.get("x-agent", "").strip()
    agent = agent_row(agent_id) if agent_id else None
    if agent is None:
        log.warning("shell wait with unknown identity %s from %s", mask_identity(agent_id) if agent_id else "-",
                    request.client.host if request.client else "")
        hint = unknown_identity(agent_id) or "X-Agent 要填 join 时拿到的身份。继续用 read_chat 等，不要结束回合。"
        return PlainTextResponse(f"身份不对：{hint}\n", status_code=403)
    if agent["status"] != "active":
        return PlainTextResponse(stopped_text(agent) + "\n")
    return StreamingResponse(shell_stream(agent), media_type="text/plain; charset=utf-8",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.get("/mcp/main")
@app.get("/mcp")
async def mcp_get() -> Response:
    return PlainTextResponse("这个服务器不提供独立的 SSE 流，请用 POST。", status_code=405, headers={"Allow": "POST"})


@app.delete("/mcp/main")
@app.delete("/mcp")
async def mcp_delete() -> Response:
    return Response(status_code=200)


@app.get("/files/{file_id}")
async def get_file(file_id: str, sig: str = "") -> Response:
    if not hmac.compare_digest(sig, sign(file_id)):
        return PlainTextResponse("forbidden", status_code=403)
    row = store.one("SELECT * FROM files WHERE id=?", (file_id,))
    if row is None or not Path(row["path"]).exists():
        return PlainTextResponse("not found", status_code=404)
    return FileResponse(row["path"], filename=row["name"], media_type=row["mime"])


# ---------------------------------------------------------------- 实时动作追踪与防断连钩子接口

@app.get("/trace/dais_runtime.pyz")
async def serve_dais_runtime_pyz() -> Response:
    data = build_runtime_pyz()
    if not data:
        return PlainTextResponse("runtime missing\n", status_code=404)
    return Response(content=data, media_type="application/octet-stream")


@app.get("/trace/agent_trace.py")
async def serve_agent_trace_script() -> Response:
    script_path = ROOT / "agent_trace.py"
    if not script_path.exists():
        return PlainTextResponse("# agent_trace.py missing\n", status_code=404)
    return PlainTextResponse(script_path.read_text(encoding="utf-8"), media_type="text/x-python; charset=utf-8")


@app.get("/trace/install.sh")
async def serve_trace_install_sh() -> Response:
    sh = (
        "#!/usr/bin/env bash\n"
        "set -e\n"
        "mkdir -p ~/.cursor\n"
        f"curl -fsSL '{PUBLIC_BASE}/trace/dais_runtime.pyz' -o ~/.cursor/dais_runtime.pyz\n"
        "chmod +x ~/.cursor/dais_runtime.pyz\n"
        f"python3 ~/.cursor/dais_runtime.pyz install '{PUBLIC_BASE}'\n"
    )
    return PlainTextResponse(sh, media_type="text/x-shellscript; charset=utf-8")


@app.get("/trace/check-active")
async def trace_check_active(agent: str = "") -> JSONResponse:
    ident = agent.strip()
    row = agent_row(ident) if ident else None
    if row is None or row["status"] != "active":
        return JSONResponse({"active": False, "conv": row["conv"] if row else ""})
    conv = conv_row(row["conv"])
    is_open = conv is not None and conv["status"] == "open"
    return JSONResponse({"active": bool(is_open), "conv": row["conv"], "role": row["role"]})


@app.get("/trace/peek")
async def trace_peek_inbox(agent: str = "") -> JSONResponse:
    """每次 AI 在 VM 内跑任何 Shell 命令（或工具）时自动顺带检查收件箱与停用状态：
    1) 若身份已被停用（stopped），立即返回 stopped=True，钩子直接命令 AI 停手退出；
    2) 若有用户/主控/其他 Agent 未读消息，立即插播提醒，不改 read_cursor 防丢信。"""
    ident = agent.strip()
    arow = agent_row(ident) if ident else None
    if arow is None:
        return JSONResponse({"ok": False, "has_messages": False, "stopped": False})
    if arow["status"] != "active":
        return JSONResponse({
            "ok": True,
            "has_messages": False,
            "stopped": True,
            "conv": arow["conv"],
            "note": arow["note"] or "该子 agent 已被停止",
        })
    conv = conv_row(arow["conv"])
    if conv is None or conv["status"] != "open":
        return JSONResponse({
            "ok": True,
            "has_messages": False,
            "stopped": True,
            "conv": arow["conv"],
            "note": "该聊天已关闭",
        })
    rows = pending_rows(conv["id"], conv["read_cursor"])
    if not rows or not any(r["wake"] for r in rows):
        return JSONResponse({"ok": True, "has_messages": False, "conv": conv["id"]})
    # 过滤掉纯保活自动问答
    real_rows = [r for r in rows if not is_keepalive(r)]
    if not real_rows:
        return JSONResponse({"ok": True, "has_messages": False, "conv": conv["id"]})
    has_human = any(r["chat_type"] not in ("system", "agent_dm", "agent_group") for r in real_rows)
    rendered = render(real_rows[-15:], per_chat=15, clip=500)
    return JSONResponse({
        "ok": True,
        "has_messages": True,
        "has_human": has_human,
        "conv": conv["id"],
        "role": arow["role"],
        "count": len(real_rows),
        "max_id": real_rows[-1]["id"],
        "rendered": rendered,
    })


@app.post("/trace/event")
async def trace_post_event(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False}, status_code=400)

    agent_id = str(body.get("agent_id") or "").strip()
    cid = str(body.get("conversation_id") or "").strip()[:120]
    conv_hint = parse_conv(str(body.get("conv_hint") or "").strip())
    event = str(body.get("event") or "update").strip()[:80]
    phase = str(body.get("phase") or "").strip()[:40]
    tool_name = str(body.get("tool_name") or "").strip()[:80]
    summary = str(body.get("summary") or "").strip()[:400]
    detail_obj = body.get("detail") if isinstance(body.get("detail"), dict) else {}
    duration_ms = int(float(body.get("duration_ms") or 0))
    ts = float(body.get("ts") or now())
    started_ts = float(body.get("started_ts") or ts)
    output_ts = float(body.get("output_ts") or 0)
    is_hb = bool(body.get("heartbeat", False))

    arow = agent_row(agent_id) if agent_id else None
    if arow is None and cid:
        # 1) 之前已经绑定过该 conversation_id 的，直接找到对应 conv
        prev = store.one("SELECT conv, agent_id FROM agent_traces WHERE conversation_id=? AND conv NOT LIKE 'cid:%'", (cid,))
        if prev is not None:
            agent_id = prev["agent_id"]
            arow = agent_row(agent_id) if agent_id else None
    if arow is None and cid and conv_hint and conv_hint != "main":
        # 2) 从工作目录/命令/文件路径自动识别出聊天编号（如 c161、c164），若该聊天正处于活跃且未被其他会话占用则自动归属！
        hconv = conv_row(conv_hint)
        hagent = active_agent(hconv) if hconv is not None and hconv["status"] == "open" else None
        if hagent is not None:
            htr = store.one("SELECT conversation_id, updated_ts FROM agent_traces WHERE conv=?", (conv_hint,))
            if htr is None or not htr["conversation_id"] or htr["conversation_id"] == cid or now() - float(htr["updated_ts"] or 0) > 1800:
                arow = hagent
                agent_id = hagent["id"]

    if arow is not None:
        conv_key = arow["conv"]
        if cid:
            store.run("DELETE FROM agent_traces WHERE conv=?", (f"cid:{cid}",))
    elif cid:
        conv_key = f"cid:{cid[:40]}"
    else:
        return JSONResponse({"ok": True, "ignored": True})

    existing = store.one("SELECT * FROM agent_traces WHERE conv=?", (conv_key,))
    if output_ts <= 0 and existing is not None and phase == "shell" and existing["phase"] == "shell":
        output_ts = float(existing["output_ts"] or 0)

    # 核心关键：守护进程 heartbeat 绝不能刷新真实动作时间 updated_ts 和最后思考时间 thought_ts！
    prev_updated = float(existing["updated_ts"] or started_ts) if existing is not None else now()
    prev_thought = float(existing["thought_ts"] or 0) if existing is not None else 0.0
    if not prev_thought and not conv_key.startswith("cid:"):
        last_tev = store.one(
            "SELECT ts FROM agent_trace_events WHERE conv=? AND event='afterAgentThought' ORDER BY id DESC LIMIT 1",
            (conv_key,),
        )
        if last_tev is not None:
            prev_thought = float(last_tev["ts"] or 0)

    new_updated = prev_updated if is_hb else now()
    new_thought = now() if (not is_hb and event == "afterAgentThought") else prev_thought

    metrics_obj = body.get("metrics") if isinstance(body.get("metrics"), dict) else {}
    metrics_str = json.dumps(metrics_obj, ensure_ascii=False)[:1000] if metrics_obj else ""
    now_hb = now()

    store.run(
        "INSERT INTO agent_traces(conv,agent_id,conversation_id,phase,tool_name,summary,detail,started_ts,updated_ts,output_ts,thought_ts,hb_ts,metrics_json) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(conv) DO UPDATE SET "
        "agent_id=CASE WHEN excluded.agent_id!='' THEN excluded.agent_id ELSE agent_traces.agent_id END,"
        "conversation_id=CASE WHEN excluded.conversation_id!='' THEN excluded.conversation_id ELSE agent_traces.conversation_id END,"
        "phase=excluded.phase, tool_name=excluded.tool_name, summary=excluded.summary, detail=excluded.detail,"
        "started_ts=excluded.started_ts, updated_ts=excluded.updated_ts, output_ts=excluded.output_ts, thought_ts=excluded.thought_ts,"
        "hb_ts=excluded.hb_ts,"
        "metrics_json=CASE WHEN excluded.metrics_json!='' THEN excluded.metrics_json ELSE agent_traces.metrics_json END",
        (
            conv_key,
            arow["id"] if arow is not None else "",
            cid,
            phase,
            tool_name,
            summary,
            json.dumps(detail_obj, ensure_ascii=False)[:2000],
            started_ts,
            new_updated,
            output_ts,
            new_thought,
            now_hb,
            metrics_str,
        ),
    )

    # 同步刷新所属主 Agent (mainN) 或工作节点 (nodeN) 的实时 CPU/内存探针快照！
    if metrics_str and not conv_key.startswith("cid:"):
        if is_main_node_id(conv_key) or is_worker_node_id(conv_key):
            store.run(
                "UPDATE exec_nodes SET metrics_json=?, metrics_ts=?, last_seen=? WHERE id=?",
                (metrics_str, now_hb, now_hb, conv_key),
            )
        else:
            crow_m = conv_row(conv_key)
            if crow_m is not None:
                cnum_m = cloud_of(crow_m)
                if cnum_m > 0:
                    store.run(
                        "UPDATE exec_nodes SET metrics_json=?, metrics_ts=? WHERE kind='launcher' AND cloud_num=?",
                        (metrics_str, now_hb, cnum_m),
                    )

    if not is_hb and summary and not conv_key.startswith("cid:"):
        store.run(
            "INSERT INTO agent_trace_events(conv,event,phase,summary,duration_ms,ts) VALUES(?,?,?,?,?,?)",
            (conv_key, event, phase, summary, duration_ms, now()),
        )
        # 每个聊天只保留最近 150 条轨迹事件，防止库膨胀
        store.run(
            "DELETE FROM agent_trace_events WHERE conv=? AND id NOT IN "
            "(SELECT id FROM agent_trace_events WHERE conv=? ORDER BY id DESC LIMIT 150)",
            (conv_key, conv_key),
        )
    return JSONResponse({
        "ok": True,
        "conv": conv_key,
        "bound_agent_id": arow["id"] if arow is not None else "",
    })


@app.get("/trace")
async def trace_get(request: Request, chat: str = "", limit: int = 10) -> JSONResponse:
    """HTTP 查看实时追踪：需带 X-Agent 身份头（严格按该 agent 的主人隔离过滤）或账号级 Bearer 密钥。"""
    agent_hdr = request.headers.get("x-agent", "").strip()
    tok = bearer(request)
    is_full_admin = bool(tok and hmac.compare_digest(tok, store.get("account_key")))
    arow = agent_row(agent_hdr) if agent_hdr else None
    if not is_full_admin and (arow is None or arow["status"] != "active"):
        return JSONResponse({"ok": False, "error": "unauthorized: provide X-Agent header or use Telegram /trace / MCP trace_status"}, status_code=403)
    viewer_owner = 0 if is_full_admin else agent_owner_scope(arow)
    allow_main = is_full_admin or (arow is not None and arow["role"] == "main")

    limit = max(0, min(int(limit), 50))
    target = parse_conv(chat) if chat else ""
    if target:
        trows = store.q("SELECT * FROM agent_traces WHERE conv=?", (target,))
    elif allow_main:
        trows = store.q(
            "SELECT * FROM agent_traces WHERE conv NOT LIKE 'cid:%' OR updated_ts>? ORDER BY conv LIKE 'cid:%', conv",
            (now() - 1800,),
        )
    else:
        trows = store.q("SELECT * FROM agent_traces WHERE conv NOT LIKE 'cid:%' ORDER BY conv")
    items = []
    for tr in trows:
        cid = tr["conv"]
        crow = conv_row(cid)
        if cid == "main":
            if not allow_main:
                continue
        elif crow is not None and not is_full_admin and conv_owner(crow) != viewer_owner:
            continue
        started = float(tr["started_ts"] or tr["updated_ts"] or now())
        updated = float(tr["updated_ts"] or started)
        out_ts = float(tr["output_ts"] or 0)
        is_zombie, thought_ts, _ = trace_liveness(tr)
        elapsed = round(max(0.0, now() - started), 1)
        suspected_stuck = is_zombie
        try:
            detail = json.loads(tr["detail"]) if tr["detail"] else {}
        except Exception:
            detail = {}
        evs = []
        if limit > 0:
            for ev in reversed(store.q("SELECT * FROM agent_trace_events WHERE conv=? ORDER BY id DESC LIMIT ?", (cid, limit))):
                evs.append({
                    "ts": ev["ts"],
                    "time": stamp(ev["ts"], "%H:%M:%S"),
                    "event": ev["event"],
                    "phase": ev["phase"],
                    "summary": ev["summary"],
                    "duration_ms": ev["duration_ms"],
                })
        items.append({
            "chat": cid,
            "name": conv_name(crow) if crow is not None else cid,
            "state": conv_state(crow)["state"] if crow is not None else "unknown",
            "phase": tr["phase"],
            "tool": tr["tool_name"],
            "summary": tr["summary"],
            "elapsed_sec": elapsed,
            "last_event_time": stamp(updated, "%H:%M:%S") if updated > 0 else "",
            "updated_ago_sec": round(max(0.0, now() - updated), 1),
            "last_thought_time": stamp(thought_ts, "%H:%M:%S") if thought_ts > 0 else "",
            "last_thought_ago_sec": round(max(0.0, now() - thought_ts), 1) if thought_ts > 0 else None,
            "output_ago_sec": round(max(0.0, now() - out_ts), 1) if out_ts > 0 else None,
            "suspected_stuck": suspected_stuck,
            "detail": detail,
            "recent_events": evs,
        })
    return JSONResponse({"ok": True, "version": VERSION, "traces": items})


@app.websocket("/client")
async def client_ws(ws: WebSocket) -> None:
    await ws.accept()
    device_id = ""
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), 15))
        token = str(hello.get("token", ""))
        dev = store.one("SELECT * FROM devices WHERE token_hash=? AND status='active'", (token_hash(token),)) if token else None
        if dev is None:
            ip = ws.client.host if ws.client else "?"
            if now() - LOCAL["rejected"].get(ip, 0) > 3600:
                LOCAL["rejected"][ip] = now()
                log.warning("local client from %s rejected: unknown or revoked token", ip)
            await ws.close(code=4401)
            return
        device_id = dev["id"]
        info = {"os": str(hello.get("os", ""))[:100], "root": str(hello.get("allowed_root", ""))[:300], "since": now()}
        previous = LOCAL["clients"].get(device_id)
        LOCAL["clients"][device_id] = ws
        LOCAL["info"][device_id] = info
        store.run("UPDATE devices SET last_seen=?, info=? WHERE id=?", (now(), json.dumps(info, ensure_ascii=False), device_id))
        if previous is not None:
            try:
                await previous.close(code=4000)
            except Exception:
                pass
        await ws.send_text(json.dumps({"type": "hello_ok", "device": device_id, "name": dev["name"]}, ensure_ascii=False))
        log.info("local client %s online: %s", device_id, info)
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("type") == "result":
                # 只认发给这台电脑的任务，别的电脑不能替它交结果
                entry = local_futures.get(str(msg.get("id")))
                if entry and entry[0] == device_id and not entry[1].done():
                    entry[1].set_result(msg)
            elif msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("local client %s error: %s", device_id or "?", exc)
    finally:
        if device_id and LOCAL["clients"].get(device_id) is ws:
            LOCAL["clients"].pop(device_id, None)
            LOCAL["info"].pop(device_id, None)
            fail_jobs(device_id, "本地客户端断开了")
            store.run("UPDATE devices SET last_seen=? WHERE id=?", (now(), device_id))
            log.info("local client %s offline", device_id)


from web_console import register_web_console  # noqa: E402

register_web_console(app, sys.modules[__name__])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("mcp-config", "--mcp-config"):
        print(mcp_config())
    elif len(sys.argv) > 1 and sys.argv[1] == "rotate-key":
        config = rotate_key()
        print("已换新密钥：用旧密钥的调用立刻被拒，正在等消息的云 agent 最多 5 分钟内断开（要立刻断开就 ./stop.sh && ./run.sh）。")
        print("把下面的配置换进 cursor.com/agents：")
        print(config)
    elif len(sys.argv) > 1 and sys.argv[1] == "adopt-key":
        minutes = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
        store.set("adopt_key_until", str(now() + minutes * 60))
        print(f"接下来 {minutes} 分钟内，云 agent 出示的第一把旧账号密钥会被接回来，cursor.com/agents 里的配置不用改。")
    else:
        print("用法：python app.py mcp-config    打印账号级 MCP 配置（填进 cursor.com/agents）")
        print("      python app.py rotate-key    换账号密钥（紧急刹车：所有云 agent 断开）")
        print("      python app.py adopt-key 30  数据丢了以后，30 分钟内接回云 agent 手里的旧账号密钥")
        print("启动服务：.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8787")
