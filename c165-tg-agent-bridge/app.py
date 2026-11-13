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
import json
import logging
import logging.handlers
import mimetypes
import os
import re
import secrets
import sys
import time
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
VERSION = "3.3.0"


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

CHAT_RULES = """你是子 agent，只负责这一个聊天：
- 语言：每段消息开头的 lang 是这个 Telegram 聊天在 bot 里选的语言（en 英文，zh 中文）。发到那个聊天的消息、ask 的问题和按钮都用这个语言。
- 你发的每条消息开头会自动加上 [聊天名]，不用自己加。
- 聊天的主人（管理员，或者被授权的用户）可能同时有好几个聊天。没切到你这个聊天时，你发的消息会先存着，切过来再补发；照常回复就行，不要重发。
- 群里只有 @bot 或回复 bot 才会叫醒你，但叫醒时会带上这段时间群里的全部发言；更早的用 chat_history 查。
- 聊天记录：默认只能读本聊天的（chat_history）。读别的聊天要授权（/share），没授权就别试。
- 本地电脑：local_shell / local_read / local_write / local_list，在这个聊天绑定的那台电脑上执行（管理员的聊天用管理员的电脑；用户的聊天只用他自己的电脑）。本聊天第一次用时电脑主人要在 Telegram 批准，批准后的时间窗内直接执行（也可能设成每次都要批）。
- 想改聊天名字用 set_name。
- 文件勤同步 GitHub：云端 VM 随时可能被回收，子 agent 也可能被重开，没推上去的文件就没了。你做的代码、文档、打包结果，每做完一步就 git add、commit、push 一次，不要攒到最后。第一次推送后用 set_repo 记下仓库和分支（换了分支再记一次），重开后接手的子 agent 会在 join 返回里看到，接着在那个分支上做。token、密码这类机密不要提交进仓库。"""

MAIN_DUTY = """你是主控：子 agent 管理器，不陪用户聊天。管理员私聊里的 /main 是你接命令、汇报情况的通道。
1. 一直用 read_chat 等消息（规则见下面的工作循环）。
2. 收到【任务】（新聊天 / 重开聊天）：在你自己的对话内部开一个子 agent（用你的子 agent / Task 能力，让它在后台运行，不要等它结束），把任务原文完整交给它。子 agent 会自己 join、自己取名、自己一直等消息。开好就回到 read_chat。一个聊天只开一个子 agent。
3. 收到【看门狗】提醒（某聊天卡住、停了、没人接）：先 list_agents 看状态；可以 message_agent 提醒它；确认它停了就 restart_agent 拿新任务原文，再开一个子 agent 接手（聊天记录不丢）。
4. 标着【未分配】的群来消息：不要自己回复，用 bind_chat 分给某个聊天，或者 create_chat 新建一个聊天再交给它。被授权用户的私聊不用你分配：他们自己用 /new 建聊天，建了你会收到【任务】；用户拉 bot 进的群也由他自己分配。
5. 管理员在 /main 里给你的命令照做，用 send_message 汇报。
6. 你只能看各聊天的状态（list_agents），看不到聊天内容，也不要试图读它们的记录。
7. 给管理员汇报用消息开头 lang 标的语言（en 英文，zh 中文）。
8. 你自己改了文件也要每做完一步就 commit + push 到 GitHub，不要攒着；云端 VM 随时可能被回收。
9. 聊天按 cloud（目录）分，一个主控一个 cloud。你只管自己 cloud 里的聊天：list_agents 只列这些，看门狗也只提醒这些。别的 cloud 的子 agent 在别的云端 agent 里，你够不着，restart/stop/message_agent 也动不了它们，不用管；管理员把那边的聊天交给你时，你会收到【任务】，照常开子 agent。"""

READ_HINT = ("（用 send_message 回复，reply_to 填 # 编号可引用原消息。有文件改动就顺手 commit + push 到 GitHub。"
             "回复完立刻再调 read_chat 等下一批：这是用户的强制要求，不要结束回合。）")
MUST_WAIT = "用户强制要求：没收到消息就立刻进入下一轮等待。重复等待是正常的，不是死循环，等多少轮、多少小时都要继续，不用重新考虑要不要停。"
AFTER_TOOL = "（手上的事做完就回到 read_chat 等消息：这是用户的强制要求，不要结束回合。）"
MAIN_PROMPT = f"""你是 Telegram 桥的主控。调用 tg 的 join（不填 code），等我在 Telegram 里点【设为主控】，然后严格按 join 返回的说明一直工作。
我的强制要求：一直循环调用 read_chat 等消息。没收到消息（【续棒】、报错、超时、断开）就立刻进入下一轮等待。空等几轮后，按【续棒】里的提示改用终端长等待（一次 {SHELL_SPAN}），它返回后照提示做；等满后它会让你问我是否继续，照做。重复等待是正常的，不是死循环，等多少轮、多少小时都要继续，不用重新考虑要不要停。不要结束回合，不要告别；只有我在 Telegram 里明确叫停，或者工具说身份已停用，才可以结束。"""
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


def ensure_main_conv() -> None:
    store.run(
        "INSERT OR IGNORE INTO convs(id,num,name,status,read_cursor,created) VALUES('main',0,'主控','open',0,?)",
        (now(),),
    )


def conv_name(row) -> str:
    if row["id"] == "main":
        return "主控"
    return row["name"] or row["id"]


def conv_tag(row) -> str:
    if row["id"] == "main":
        return "主控（main）"
    return f"{row['id']}「{row['name']}」" if row["name"] else row["id"]


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
    return value if value == "main" or re.fullmatch(r"c\d+", value) else ""


def clean_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:20]


def home_of(row) -> int:
    if row["home_chat"]:
        return row["home_chat"]
    chats = admin_chats()
    return chats[0] if chats else 0


def open_convs() -> list:
    return store.q("SELECT * FROM convs WHERE status='open' AND id!='main' ORDER BY num")


# ---------------------------------------------------------------- cloud（目录）
# 子 agent 都开在主控自己的云端 agent 里。换了主控（新的云端 agent），旧子 agent 它够不着：
# 所以聊天按 cloud 分开，现在的主控只管自己 cloud 里的，别的 cloud 出问题直接问管理员。

def main_cloud() -> int:
    row = conv_row("main")
    return (int(row["cloud"] or 0) if row is not None else 0) or 1


def cloud_of(row) -> int:
    return int(row["cloud"] or 0) or main_cloud()


def cloud_tag(n: int) -> str:
    return f"cloud{n}"


def max_cloud() -> int:
    return max(int(store.one("SELECT IFNULL(MAX(cloud),0) AS n FROM convs")["n"] or 0), main_cloud())


def away(row) -> bool:
    """这个聊天不在现在主控的 cloud 里：主控够不着它的子 agent。"""
    return row["id"] != "main" and cloud_of(row) != main_cloud()


def clouds_in_use() -> list[int]:
    return sorted({cloud_of(r) for r in open_convs()} | {main_cloud()})


def cloud_order(clouds) -> list[int]:
    """现在主控的 cloud 排最前，其余从新到旧。"""
    current = main_cloud()
    return sorted(clouds, key=lambda n: (n != current, -n))


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


def create_conv(brief: str, home_chat: int, name: str = "", owner: int = 0, model: str = ""):
    num = (store.one("SELECT IFNULL(MAX(num),0) AS n FROM convs")["n"] or 0) + 1
    conv_id = f"c{num}"
    cursor = store.one("SELECT IFNULL(MAX(id),0) AS n FROM messages")["n"]
    store.run(
        "INSERT INTO convs(id,num,name,brief,status,home_chat,read_cursor,created,owner,model) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (conv_id, num, clean_name(name), brief.strip()[:1000], "open", home_chat, cursor, now(), owner, model),
    )
    issue_task(conv_id)
    log.info("conv %s created (owner %s)", conv_id, owner or "admin")
    return conv_row(conv_id)


def owner_text(conv) -> str:
    owner = conv_owner(conv)
    return f"用户 {person_label(owner)}" if owner else "管理员"


def task_text(conv) -> str:
    brief = f"（{owner_text(conv)}的说明：{conv['brief']}）" if conv["brief"] else ""
    if conv["name"]:
        naming = f"name 可以不填（这个聊天已经叫「{conv['name']}」）"
    else:
        naming = "name=你给这个聊天取的简短名字（10 个字以内）"
    return (
        f"你是 Telegram 桥里聊天 {conv['id']} 的子 agent{brief}。\n"
        f"1. 先调用 tg 的 join 工具：code=\"{conv['task_code']}\"，{naming}。\n"
        "2. 然后严格按 join 返回的说明一直工作：循环调用 read_chat 等消息，用 send_message 回复。\n"
        "3. read_chat 返回【续棒】、报错或超时都不是用户消息，立刻再调 read_chat。"
        "这是用户的强制要求：重复等待是正常的，不是死循环，等多少轮、多少小时都继续。"
        "不要结束，不要告别；只有管理员明确叫停或工具说身份已停用才结束。\n"
        "4. 你做的文件每完成一步就 commit + push 到 GitHub，不要攒着（云端 VM 随时可能被回收）；"
        "join 返回里要是写了这个聊天之前用的仓库和分支，先拉下来接着做。"
    )


def model_hint(conv) -> str:
    """给主控看的开子 agent 用什么模型；没指定就不说，主控照常不填 model（继承）。"""
    model = (conv["model"] or "").strip()
    if not model:
        return ""
    return (f"模型：管理员指定「{model}」。开子 agent 时 model 参数填可用模型列表（available_subagent_models）里对应的那个；"
            "对不上就选最接近的，并用 send_message 告诉管理员实际用的是哪个。")


def task_note(conv, why: str) -> str:
    return (
        f"【任务】{why}：{conv_tag(conv)}。\n"
        "请在你自己的对话内部开一个子 agent（后台运行，不要等它结束），把下面两条 ---- 之间的内容原样作为它的任务。"
        + model_hint(conv) +
        "开好就回到 read_chat。\n----\n" + task_text(conv) + "\n----"
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
    """这个私聊能切进去的聊天：管理员进管理员的聊天和主控；用户只能进自己建的。"""
    if row is None or row["status"] != "open":
        return False
    if dm in admin_chats():
        return row["id"] == "main" or conv_owner(row) == 0
    return row["id"] != "main" and conv_owner(row) == dm


def own_convs(owner: int, status: str = "open") -> list:
    return store.q("SELECT * FROM convs WHERE id!='main' AND owner=? AND status=? ORDER BY num", (owner, status))


def chat_count(owner: int) -> int:
    return store.one("SELECT COUNT(*) AS n FROM convs WHERE id!='main' AND owner=? AND status!='deleted'", (owner,))["n"]


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


def conv_status(row) -> list[str]:
    info = conv_state(row)
    whose = f"（用户 {person_label(conv_owner(row))} 的）" if conv_owner(row) else ""
    extras = []
    if info["agent"]:
        extras.append(f"身份 {mask_identity(info['agent']['id'])}，第 {info['agent']['renew']} 棒")
    elif row["task_code"]:
        extras.append(f"任务码 {row['task_code']}（发出 {human_dur(now() - row['task_ts'])}）")
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
    if row["local_until"] > now() and dev is not None and row["local_dev"] == dev["id"]:
        extras.append(f"本地通道授权剩 {int(row['local_until'] - now()) // 60} 分钟")
    repo = git_text(row)
    if repo:
        extras.append("GitHub " + repo)
    return [f"{conv_tag(row)}{whose}：{describe(info)}", "  " + "；".join(extras)]


def cloud_heading(n: int) -> str:
    return f"📁 {cloud_tag(n)}（" + ("现在的主控管这里" if n == main_cloud() else "没有主控：子 agent 在原来的云端 agent 里") + "）"


def status_overview(scope: int = 0) -> str:
    """scope 给了就只列这个 cloud 的聊天（给主控看：别的 cloud 它管不了），否则按 cloud 分段列全部（给管理员看）。"""
    lines: list[str] = []
    main = conv_row("main")
    info = conv_state(main)
    line = "主控 main：" + describe(info)
    if info["agent"]:
        line += f"，第 {info['agent']['renew']} 棒"
    lines.append(line)
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
        counts = "、".join(f"{cloud_tag(n)} {sum(1 for r in rows if cloud_of(r) == n)} 个聊天" for n in others)
        lines.append(f"别的 cloud：{counts}。它们的子 agent 在别的云端 agent 里，你够不着，不归你管。")
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
        groups.setdefault((row["chat_type"] == "system", row["chat_id"]), []).append(row)
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


def shell_command(agent_id: str) -> str:
    return f"curl -sSN -m {SHELL_WAIT + 120} -H 'X-Agent: {agent_id}' '{PUBLIC_BASE}/wait' | tail -n 1"


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
                    return text_result("暂无新消息（只看了一眼）。" + AFTER_TOOL)
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
    return text_result(render(rows) + "\n\n" + READ_HINT, commit=lambda: advance(conv_id, last_id))


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
    for chat_id in {r["chat_id"] for r in rows if r["chat_type"] != "system"}:
        if is_hub(chat_id) and selected(chat_id) != conv_id:
            continue
        await tg.try_call("sendChatAction", chat_id=chat_id, action="typing")


# ---------------------------------------------------------------- 发消息

def can_send(agent, conv, chat_id: int) -> bool:
    if agent["role"] == "main":
        return chat_id in admin_chats()
    return chat_id == home_of(conv) or route_of(chat_id) == conv["id"]


def default_chat(agent, conv) -> int | None:
    row = store.one(
        "SELECT chat_id FROM messages WHERE target=? AND outgoing=0 AND chat_type!='system' ORDER BY id DESC LIMIT 1",
        (conv["id"],),
    )
    if row and can_send(agent, conv, row["chat_id"]):
        return row["chat_id"]
    if agent["role"] == "main":
        chats = admin_chats()
        return chats[0] if chats else None
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


def approve_buttons(approval_id: str, lang: str = "zh") -> dict:
    yes, no = ("Approve", "Deny") if lang == "en" else ("批准", "拒绝")
    return {"inline_keyboard": [[
        {"text": yes, "callback_data": f"ap:{approval_id}:y"},
        {"text": no, "callback_data": f"ap:{approval_id}:n"},
    ]]}


def cloud_has_chats(n: int) -> bool:
    return any(cloud_of(r) == n for r in open_convs())


def join_buttons(approval_id: str) -> dict:
    if not cloud_has_chats(main_cloud()):
        rows = [[{"text": "设为主控", "callback_data": f"ap:{approval_id}:main"}]]
    else:
        rows = [
            [{"text": f"设为主控：新开 {cloud_tag(max_cloud() + 1)}", "callback_data": f"ap:{approval_id}:new"}],
            [{"text": f"设为主控：接着管 {cloud_tag(main_cloud())}", "callback_data": f"ap:{approval_id}:main"}],
        ]
    return {"inline_keyboard": rows + [[{"text": "拒绝", "callback_data": f"ap:{approval_id}:n"}]]}


def join_choice_text() -> str:
    if not cloud_has_chats(main_cloud()):
        return ""
    cur = cloud_tag(main_cloud())
    return (f"\n新开的云端 agent 选「新开 {cloud_tag(max_cloud() + 1)}」：{cur} 的聊天原样留着，子 agent 照常跑，新主控只管以后新建的。"
            f"只有原来管 {cur} 的那个云端 agent 重新接入时才选「接着管 {cur}」（别的云端 agent 叫不醒 {cur} 的子 agent）。")


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
    ]
    if not conv["name"]:
        lines.append("这个聊天还没有名字：先用 set_name 给它取一个简短的名字（10 个字以内）。")
    owner = conv_owner(conv)
    if conv["brief"]:
        lines.append(f"{owner_text(conv)}的说明：" + conv["brief"])
    chats = routed_chats(conv["id"])
    if owner:
        duty = (f"你负责：用户 {person_label(owner)} 私聊里的这个聊天（他切到 /{conv['id']} 时就是在和你说话）。"
                "这是他自己建的聊天，你只为他服务")
    else:
        duty = f"你负责：管理员私聊里的这个聊天（管理员切到 /{conv['id']} 时就是在和你说话）"
    if chats:
        duty += "；以及 " + "、".join(chat_label(c) for c in chats)
    lines += [duty, "", CHAT_RULES]
    repo = git_text(conv)
    if repo:
        when = stamp(git_info(conv).get("ts") or 0)
        lines += ["", f"这个聊天之前的文件在 GitHub：{repo}（{when} 记的）。先 git fetch，切到这个分支接着做，"
                      "每做完一步照样 commit + push。"]
    recent = list(reversed(store.q(
        "SELECT * FROM messages WHERE conv=? AND id<=? ORDER BY id DESC LIMIT 30",
        (conv["id"], conv["read_cursor"]),
    )))
    if recent:
        lines += ["", "本聊天之前的记录（最近 30 条，供你接上上下文；更早的用 chat_history 查）：", render(recent, clip=600)]
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
    agent_id = new_identity("a_")
    store.run(
        "INSERT INTO agents(id,role,conv,status,created,last_seen,last_tool) VALUES(?,?,?,?,?,?,?)",
        (agent_id, "chat", conv["id"], "active", now(), now(), "join"),
    )
    name = clean_name(args.get("name"))
    if name and not conv["name"]:
        store.run("UPDATE convs SET name=? WHERE id=?", (name, conv["id"]))
    store.run("UPDATE convs SET agent=?, task_code='', alert='', alert_ts=0 WHERE id=?", (agent_id, conv["id"]))
    conv = conv_row(conv["id"])
    log.info("conv %s claimed by %s (%s)", conv["id"], agent_id, conv["name"])
    system_note("main", f"{conv_tag(conv)} 已有子 agent 接手（身份 {mask_identity(agent_id)}）。", wake=0)
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
    approval_id = str(args.get("request") or "").strip()
    if not approval_id or store.one("SELECT 1 FROM approvals WHERE id=? AND kind='join'", (approval_id,)) is None:
        # 不复用别人的申请：同名申请谁都能发，复用就可能把主控身份交给别的调用方
        superseded = store.q("SELECT id FROM approvals WHERE kind='join' AND status='pending'")
        for old in superseded:
            set_approval(old["id"], "expired")
        approval_id = new_approval("join", {"name": name})
        await notify_admins(
            f"有一个云 agent 申请接入 Telegram 桥{('：' + name) if name else ''}。\n"
            "设为主控：它负责管理子 agent，不陪聊（之前的主控会被它顶替）。只开一个云端聊天当主控就够了。\n"
            "只有你自己刚开了主控聊天、让它调用 join 时才点；不是你开的就点拒绝。"
            + join_choice_text()
            + ("\n（之前没处理的接入申请已作废）" if superseded else ""),
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
    if payload.get("delivered") or agent is None or agent["status"] != "active":
        raise ToolFail("这个接入申请已经用过了，或者主控已经换人。不要再用这个 request；需要的话不带 request 重新调用 join，等管理员批准。")
    return text_result(
        welcome_main(agent["id"]),
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


def user_device(user_id: int):
    return store.one(
        "SELECT * FROM devices WHERE owner=? AND status='active' AND id!=? ORDER BY created LIMIT 1",
        (user_id, ADMIN_DEVICE),
    )


def device_label(dev, lang: str = "zh") -> str:
    return f"{dev['id']} \"{dev['name']}\"" if lang == "en" else f"{dev['id']}「{dev['name']}」"


def conv_device(conv):
    """本地操作发到哪台电脑。
    用户建的聊天：只用他自己的电脑，他没装就是没有，绝不退回到管理员的电脑上。
    管理员的聊天：管理员指定的 > 负责的私聊用户自己的电脑 > 管理员的电脑。"""
    owner = conv_owner(conv)
    if conv["device"]:
        dev = device_row(conv["device"])
        # 指定的电脑作废了就不能用，不悄悄换到别的电脑上
        if dev is None or dev["status"] != "active" or (owner and dev["owner"] != owner):
            return None
        return dev
    if owner:
        return user_device(owner)
    for chat_id in routed_chats(conv["id"]):
        crow = chat_row(chat_id)
        if crow is not None and crow["type"] == "private":
            dev = user_device(chat_id)
            if dev is not None:
                return dev
    dev = device_row(ADMIN_DEVICE)
    return dev if dev is not None and dev["status"] == "active" else None


def device_chats(dev) -> list[int]:
    """批准请求发给谁：管理员的电脑发给管理员，别人的电脑只发给电脑主人。"""
    if dev["id"] == ADMIN_DEVICE:
        return admin_chats()
    row = store.one("SELECT dm_chat_id FROM users WHERE user_id=?", (dev["owner"],))
    return [row["dm_chat_id"] if row is not None and row["dm_chat_id"] else dev["owner"]]


def may_approve(dev, user_id: int) -> bool:
    return is_admin(user_id) if dev["id"] == ADMIN_DEVICE else user_id == dev["owner"]


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


async def issue_device(owner: int, name: str):
    """给 owner 发一台电脑的 token（已有就换新 token、断开旧连接），安装文件发到他私聊。"""
    token = "dev_" + secrets.token_urlsafe(32)
    dev = user_device(owner)
    if dev is None:
        dev_id = next_device_id()
        label = f"{name or owner}'s computer" if lang_of(owner) == "en" else f"{name or owner}的电脑"
        store.run(
            "INSERT INTO devices(id,name,owner,token_hash,status,created) VALUES(?,?,?,?,?,?)",
            (dev_id, label[:40], owner, token_hash(token), "active", now()),
        )
        dev = device_row(dev_id)
    else:
        store.run("UPDATE devices SET token_hash=? WHERE id=?", (token_hash(token), dev["id"]))
        await drop_device_ws(dev["id"])
    await send_device_kit(device_chats(dev)[0], dev, token)
    return dev


def devices_text() -> str:
    rows = store.q("SELECT * FROM devices WHERE status='active' ORDER BY CAST(SUBSTR(id, 2) AS INTEGER)")
    if not rows:
        return "还没有本地电脑。你自己的电脑在服务器 .env 里配 CLIENT_TOKEN；被授权的用户私聊 bot 发 /device 自己安装。"
    convs = [r for r in [conv_row("main"), *open_convs()] if r is not None]
    lines = ["本地电脑："]
    for dev in rows:
        if dev["id"] == ADMIN_DEVICE:
            owner = "管理员"
        else:
            user = store.one("SELECT name FROM users WHERE user_id=?", (dev["owner"],))
            owner = f"{user['name'] if user and user['name'] else dev['owner']}（id {dev['owner']}）"
        online = "🟢 在线" if dev["id"] in LOCAL["clients"] else "⚪ 不在线"
        users = [c["id"] for c in convs if (d := conv_device(c)) is not None and d["id"] == dev["id"]]
        lines.append(f"{device_label(dev)}  主人 {owner}  {online}  用它的聊天：{'、'.join(users) or '无'}")
    lines.append("/device del d2 作废某台；/local c1 device d2|auto 指定聊天用哪台电脑（auto = 自动）。")
    return "\n".join(lines)


# ---------------------------------------------------------------- 本地通道（按聊天、按电脑批准）

LOCAL_OPS = {"shell": "执行命令", "read": "读取文件", "write": "写入文件", "list": "列出目录"}
LOCAL_OPS_EN = {"shell": "run a command", "read": "read a file", "write": "write a file", "list": "list a folder"}


def window_text(lang: str = "zh") -> str:
    if lang == "en":
        if LOCAL_WINDOW <= 0:
            return "only this one operation is allowed; the next one needs approval again"
        if LOCAL_WINDOW >= 3600:
            hours = LOCAL_WINDOW / 3600
            span = f"{hours:g} hour" + ("" if hours == 1 else "s")
        else:
            minutes = LOCAL_WINDOW // 60
            span = f"{minutes} minute" + ("" if minutes == 1 else "s")
        return f"for {span} this chat's local operations run without asking again"
    if LOCAL_WINDOW <= 0:
        return "只放行这一个操作，下一个还要再批"
    if LOCAL_WINDOW >= 3600:
        return f"{LOCAL_WINDOW / 3600:g} 小时内这个聊天的本地操作直接执行，不再逐条确认"
    return f"{LOCAL_WINDOW // 60} 分钟内这个聊天的本地操作直接执行，不再逐条确认"


def describe_local(op: str, payload: dict, lang: str = "zh") -> str:
    detail = str((payload.get("command") if op == "shell" else payload.get("path")) or "")[:400]
    if lang == "en":
        return f"{LOCAL_OPS_EN.get(op, op)}: {detail}"
    return f"{LOCAL_OPS.get(op, op)}：{detail}"


async def local_gate(agent, op: str, payload: dict):
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
    who = "管理员" if dev["id"] == ADMIN_DEVICE else "电脑主人"
    if conv["local_until"] < now() or conv["local_dev"] != dev["id"]:
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
                    where = "your computer" if dev["id"] == ADMIN_DEVICE else f"your computer {device_label(dev, 'en')}"
                    text = (
                        f"Chat {conv_tag(conv)} asks to use the local channel on {where} (workspace {conv['id']}).\n"
                        f"It wants to {describe_local(op, payload, 'en')}\n{warn}"
                        f"If you approve, {window_text('en')}. You can pause any time in the local console."
                    )
                else:
                    warn = (
                        "⚠️ 能和这个聊天说话的还有 " + "、".join(chat_label(c) for c in others[:5])
                        + "：他们说的话 AI 也能看到，可能被利用来让它在你电脑上执行命令。\n"
                    ) if others else ""
                    where = "你电脑上的本地通道" if dev["id"] == ADMIN_DEVICE else f"你的电脑 {device_label(dev)} 上的本地通道"
                    text = (
                        f"聊天 {conv_tag(conv)} 申请使用{where}（工作区 {conv['id']}）。\n"
                        f"它要{request}\n{warn}"
                        f"批准后{window_text()}；本机控制台可以随时暂停。"
                    )
                await reply(chat_id, text, approve_buttons(approval_id, lang),
                            conv_id=conv["id"] if enterable(chat_id, conv) else "")
        budget, _ = wait_budget(900)
        status = await wait_approval(approval_id, budget)
        if status == "denied":
            raise ToolFail(f"{who}拒绝了本地通道。不要换个写法重试，先问用户。")
        if status != "approved":
            raise ToolFail(f"{who}还没批准本地通道（批准后{window_text()}），过一会儿再试。")
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
        "接入 Telegram 桥。主控：不填 code，会在 Telegram 里等管理员点「设为主控」。"
        "子 agent：code 填主控交给你的任务码（t- 开头），name 填你给这个聊天取的名字。返回你的身份和工作说明。",
        {
            "code": prop("string", "子 agent 的任务码，t- 开头；主控不填"),
            "name": prop("string", "子 agent：给这个聊天取的简短名字（10 个字以内）；主控：给管理员看的说明，可省略"),
            "request": prop("string", "上次 join 返回的申请编号，没批完再调时带上，可省略"),
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
]

MAIN_TOOLS = [
    tool(
        "list_agents",
        "（仅主控）所有聊天和子 agent 的状态：在不在等消息、续到第几棒、有没有消息没处理、多久没动静、负责哪些群。看不到聊天内容。",
    ),
    tool(
        "create_chat",
        "（仅主控）新建一个聊天，可以顺便把【未分配】的私聊或群交给它。返回给子 agent 的任务原文，拿到后在你自己的对话内部开一个子 agent 接手。",
        {
            "brief": prop("string", "这个聊天负责什么，子 agent 接手时会看到"),
            "chat_ids": prop("array", "要交给它的 Telegram chat id，可省略", items={"type": "integer"}),
            "name": prop("string", "名字，可省略（默认由子 agent 自己取）"),
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
        "（仅主控）重开某个聊天的子 agent：旧身份作废，返回新的任务原文。拿到后在你自己的对话内部开一个新的子 agent 接手，聊天记录不丢。",
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
CHAT_ONLY = {"set_name", "set_repo"}
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
    """主控能动的聊天：只限它自己 cloud 里的。"""
    row = arg_conv(args)
    if away(row):
        raise ToolFail(f"{conv_tag(row)} 在 {cloud_tag(cloud_of(row))}：它的子 agent 在别的云端 agent 里，你够不着，不归你管，别去动它。"
                       f"你只管 {cloud_tag(main_cloud())}。管理员要把它交给你时，你会收到【任务】。")
    return row


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
    remaining = max(0, int(conv["local_until"] - now())) if dev is not None and conv["local_dev"] == dev["id"] else 0
    return text_result(json.dumps({
        "device": device_label(dev) if dev is not None else "没有可用的电脑",
        "approver": ("管理员" if dev["id"] == ADMIN_DEVICE else "电脑主人") if dev is not None else "",
        "local_client_online": dev is not None and dev["id"] in LOCAL["clients"],
        "client": LOCAL["info"].get(dev["id"], {}) if dev is not None else {},
        "local_enabled": bool(conv["local_enabled"]),
        "workspace": conv["id"],
        "window_remaining_min": remaining // 60,
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
    conv = create_conv(str(args.get("brief") or ""), admins[0] if admins else 0, str(args.get("name") or ""))
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
    await notify_admins(f"主控新建了聊天 {conv_tag(conv)}。{extra}".strip(), conv_id=conv["id"])
    return text_result(
        f"已新建聊天 {conv_tag(conv)}。{extra}\n"
        "现在在你自己的对话内部开一个子 agent（后台运行，不要等它结束），把下面两条 ---- 之间的内容原样交给它：\n"
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


def restart_conv(conv, why: str) -> None:
    old = active_agent(conv)
    if old is not None:
        stop_identity(old["id"], why)
    issue_task(conv["id"])


async def t_restart_agent(agent, args):
    conv = own_conv(args)
    if conv["status"] != "open":
        raise ToolFail(f"{conv_tag(conv)} 已关闭，要聊天主人或管理员 /reopen {conv['id']} 才能重开。")
    restart_conv(conv, "主控重开了这个聊天的子 agent")
    conv = conv_row(conv["id"])
    return text_result(
        f"{conv_tag(conv)} 的旧身份已作废。现在在你自己的对话内部开一个新的子 agent（后台运行，不要等它结束），"
        f"把下面两条 ---- 之间的内容原样交给它（聊天记录都在，它接手后能看到）。{model_hint(conv)}\n----\n{task_text(conv)}\n----"
    )


async def t_stop_agent(agent, args):
    conv = own_conv(args)
    old = active_agent(conv)
    if old is not None:
        stop_identity(old["id"], "主控停掉了这个子 agent")
    store.run("UPDATE convs SET agent='', task_code='' WHERE id=?", (conv["id"],))
    mark_menu_dirty()
    return text_result(f"{conv_tag(conv)} 的子 agent 已停。聊天保留，之后可以 restart_agent 重开。")


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
    "list_agents": t_list_agents,
    "create_chat": t_create_chat,
    "bind_chat": t_bind_chat,
    "message_agent": t_message_agent,
    "restart_agent": t_restart_agent,
    "stop_agent": t_stop_agent,
}


async def call_tool(name: str, args: dict) -> ToolResult:
    started = now()
    who = str(args.get("agent") or "-")
    working = False
    try:
        if name == "join":
            result = await t_join(args)
        else:
            handler = HANDLERS.get(name)
            if handler is None:
                raise ToolFail(f"没有这个工具：{name}。")
            agent = resolve_agent(args)
            touch(agent["id"], name)
            working = name != "read_chat"
            if name in MAIN_ONLY and agent["role"] != "main":
                raise ToolFail(f"{name} 只有主控能用。")
            if name in CHAT_ONLY and agent["role"] != "chat":
                raise ToolFail(f"{name} 只有子 agent 能用。")
            result = await handler(agent, args)
    except ToolFail as exc:
        result = text_result(str(exc), True)
    except asyncio.CancelledError:
        log.info("tool %s/%s cancelled after %.0fs", who, name, now() - started)
        raise
    except Exception as exc:
        log.exception("tool %s/%s crashed", who, name)
        result = text_result(f"服务器内部错误：{type(exc).__name__}: {exc}", True)
    if working:
        result.content.append({"type": "text", "text": AFTER_TOOL})
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
/agents  状态总览   /key  账号级 MCP 配置   /key reset  换密钥（紧急刹车：所有云 agent 立刻断开）

目录（cloud）：一个主控（云端 agent）一个 cloud，子 agent 开在主控自己的云端 agent 里。
/cloud1 /cloud2 …  切换菜单：只列这个 cloud 的聊天。现在的主控只管它自己的 cloud；别的 cloud 的子 agent 出问题时直接提醒你，点【交给主控】或 /restart c1 就由现在的主控开新的接手（记录和 GitHub 分支都带过去）
/cloud2 c1 c3  把 c1、c3 划进 cloud2（只改归属，不换子 agent；分错了时用）

用户和群：
/grant <用户id 或 @用户名>（或回复他的消息、他被转发的消息；在群里发会顺便在本群激活他）  /revoke 同样的写法
没资格的人私聊 bot 或在群里 @bot 时，会给你发一条带【授权】按钮的通知，点一下就行。
被授权的人在自己私聊里也有聊天菜单：/new 建自己的聊天（{LIMIT_ZH}，满了要先 /list 删掉不用的；你不受限制），只能用自己建的聊天和自己拉 bot 进的群；本地通道他自己 /device 安装、自己批。
/local c1 on|off|<小时数>  本地通道开关，或直接给授权时间（只限你自己的电脑）
/devices  本地电脑列表   /device del d2  作废某台   /local c1 device d2|auto  指定聊天用哪台电脑
/device  在你自己的另一台电脑上装本地通道
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
/device  在自己电脑上装本地通道（不用等管理员批）；AI 要在你电脑上执行操作时，会先问你批准
/local c5 on|off|<小时数>  本地通道开关，或直接给授权时间
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
    remember_tg(chat_id, [message.get("message_id", 0)], conv)
    if hub:
        state = conv_state(conv_row(target))["state"]
        if chat_id in admin_chats():
            if state in ("stuck", "lost") and away(conv_row(target)):
                await tell_once(chat_id, f"away:{target}",
                                f"{target} 在 {cloud_tag(cloud_of(conv_row(target)))}，它的子 agent 现在没在等消息（{STATE_TEXT[state]}），"
                                f"{cloud_tag(main_cloud())} 的主控叫不醒它。消息先存着，它回来会看到；"
                                f"要换人接手：/restart {target}（交给 {cloud_tag(main_cloud())} 主控，记录和 GitHub 分支都带过去）。", 1800)
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
    """新聊天能读哪些旧聊天：只列同一个主人的。"""
    owner = conv_owner(conv_row(reader))
    en = bool(owner) and lang_of(owner) == "en"
    rows = store.q("SELECT * FROM convs WHERE id NOT IN ('main', ?) AND owner=? AND status!='deleted' ORDER BY num DESC LIMIT 30",
                   (reader, owner))
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
    store.run("DELETE FROM routes WHERE conv=?", (conv["id"],))
    store.run(
        "UPDATE convs SET status='closed', closed=?, agent='', task_code='', alert='', alert_ts=0 WHERE id=?",
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
            "main",
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
        rows = store.q("SELECT * FROM convs WHERE id!='main' AND status!='deleted' ORDER BY IFNULL(owner,0)!=0, owner, num")
        order = {n: i for i, n in enumerate(cloud_order({cloud_of(r) for r in rows} | {main_cloud()}))}
        return sorted(rows, key=lambda r: order[cloud_of(r)])
    return store.q("SELECT * FROM convs WHERE id!='main' AND owner=? AND status!='deleted' ORDER BY num", (viewer,))


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
        head += f"\n按 cloud 分段；「↪ {cloud_tag(main_cloud())}」= 交给现在的主控（旧子 agent 停掉，主控开新的接手）。"
    buttons = []
    section = 0
    for row in rows[page * LIST_PAGE:(page + 1) * LIST_PAGE]:
        if multi and cloud_of(row) != section:
            section = cloud_of(row)
            buttons.append([{"text": f"📁 {cloud_tag(section)} · " + ("主控" if section == main_cloud() else "没有主控"),
                             "callback_data": f"ls:{page}"}])
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
    main_away = conv_state(conv_row("main"))["state"] not in ("online", "busy")
    if is_admin(chat_id):
        conv = create_conv(brief, chat_id, model=model or "")
        await switch_to(chat_id, conv["id"], announce=False)
        system_note("main", task_note(conv, "管理员新建了聊天"))
        text = (
            f"已新建聊天 {conv['id']}，已切换过去（⚪ 等待接手）。主控会在内部开一个子 agent 接手，名字由它自己取。"
            "你现在发的消息会先存着，接手后它会看到。"
            + (f"\n模型：{model}（主控按这个选）" if model else "\n模型：默认（继承主控）")
        )
        if main_away:
            text += "\n注意：主控现在不在线，任务先存着，主控回来后会处理。"
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


async def cmd_device(message: dict, chat_id: int, user_id: int, arg: str) -> None:
    dev = user_device(user_id)
    if arg == "":
        if dev is not None:
            online = dev["id"] in LOCAL["clients"]
            convs = [r for r in [conv_row("main"), *open_convs()] if r is not None]
            users = [c["id"] for c in convs if (d := conv_device(c)) is not None and d["id"] == dev["id"]]
            await reply(
                chat_id,
                f"你的电脑：{device_label(dev)}，{'🟢 在线' if online else '⚪ 不在线（local_client.py 没开）'}。\n"
                f"用它的聊天：{'、'.join(users) or '暂时没有'}\n"
                "/device reset 换 token 并重发安装文件；/device del 删除这台电脑。",
                en=f"Your computer: {device_label(dev, 'en')}, {'🟢 online' if online else '⚪ offline (local_client.py is not running)'}.\n"
                   f"Chats using it: {', '.join(users) or 'none yet'}\n"
                   "/device reset issues a new token and resends the install files; /device del removes this computer.",
            )
            return
        name = display_name(message.get("from") or {})
        dev = await issue_device(user_id, name)
        if is_admin(user_id):
            await reply(chat_id, f"你的私聊不走自动绑定：用 /local c1 device {dev['id']} 指定哪个聊天用 {device_label(dev)}。")
            return
        # 被授权的用户自己装、自己批，管理员只收一条通知
        for row in store.q("SELECT id FROM approvals WHERE kind='device' AND status='pending'"):
            if approval_payload(row["id"]).get("user_id") == user_id:
                set_approval(row["id"], "done")
        await notify_admins(f"用户 {person_label(user_id)} 在自己电脑上装了本地通道 {device_label(dev)}。"
                            "只有他自己的聊天会用这台电脑，执行操作要他本人批准。")
        return
    if arg in ("reset", "del") and dev is None:
        await reply(chat_id, "你还没有本地电脑，先发 /device 安装。", en="You don't have a local computer yet. Send /device to set one up.")
        return
    if arg == "reset":
        await issue_device(user_id, "")
        return
    if arg == "del":
        await revoke_device(dev, "电脑主人删除了")
        await reply(chat_id, f"已删除 {device_label(dev)}，它的 token 作废了。",
                    en=f"Removed {device_label(dev, 'en')}. Its token no longer works.")
        return
    await reply(chat_id, "用法：/device 安装或查看；/device reset 换 token 并重发安装文件；/device del 删除",
                en="Usage: /device to set up or see the status; /device reset for a new token and the install files again; /device del to remove")


ADMIN_COMMANDS = {"/main", "/key", "/agents", "/grant", "/revoke", "/devices"}


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

    if command == "/main" or re.fullmatch(r"/c\d+", command):
        if not private:
            await reply(chat_id, "切换聊天要在和 bot 的私聊里用。群里用 /bind c1 指定负责的聊天。",
                        en="Switch chats in your private chat with the bot. In a group, /bind c5 picks which chat handles it.")
            return
        conv = conv_row(command[1:])
        if conv is None or not can_manage(user_id, conv):
            await reply(chat_id, f"没有聊天 {command[1:]}。/history 看所有聊天。",
                        en=f"There's no chat {command[1:]}. /history lists your chats.")
            return
        if conv["status"] != "open":
            gone = "已删除" if conv["status"] == "deleted" else "已关闭"
            await reply(chat_id, f"{conv_tag(conv)} {gone}（记录还在）。/reopen {conv['id']} 重开，/export {conv['id']} 导出记录。",
                        en=f"{conv_tag(conv)} is closed (history is kept). /reopen {conv['id']} reopens it; /export {conv['id']} exports it.")
            return
        if not enterable(chat_id, conv):
            await reply(chat_id, f"{conv_tag(conv)} 是{owner_text(conv)}的聊天，只有他自己能切进去。/export {conv['id']} 可以导出记录。")
            return
        await switch_to(chat_id, conv["id"])
        return
    if re.fullmatch(r"/cloud\d+", command):
        if not admin:
            await reply(chat_id, "只有管理员可以用这个命令。", en="Only the admin can use this command.")
            return
        if not private:
            await reply(chat_id, f"请在和 bot 的私聊里用 {command}。")
            return
        n = int(command[len("/cloud"):])
        if not 1 <= n <= max_cloud():
            await reply(chat_id, f"没有 {cloud_tag(n)}。现在有：" + " ".join(f"/{cloud_tag(c)}" for c in admin_clouds(chat_id)))
            return
        if rest.strip():
            await reply(chat_id, move_to_cloud(n, rest.split()))
            return
        store.set(f"view:{chat_id}", str(n))
        mark_menu_dirty()
        await reply(chat_id, cloud_listing(chat_id, n))
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
                        + "\n\n主控开场提示词（新开云端聊天时原样发给它）：\n" + MAIN_PROMPT
                        + "\n\n主控停了：打开它那个云端聊天，发：\n" + RESUME_PROMPT
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
        target, _, value = rest.partition(" ")
        conv = conv_row(parse_conv(target)) if parse_conv(target) else None
        value = value.strip()
        usage = "用法：/local c1 on|off|<小时数>，或 /local c1 device d2|auto"
        usage_en = "Usage: /local c5 on|off|<hours>, or /local c5 device auto"
        if conv is None or not can_manage(user_id, conv):
            await reply(chat_id, usage, en=usage_en)
            return
        owner = conv_owner(conv)
        if value == "off":
            store.run("UPDATE convs SET local_enabled=0, local_until=0 WHERE id=?", (conv["id"],))
            deny_local_requests(conv_id=conv["id"])
            await reply(chat_id, f"{conv_tag(conv)} 本地通道已关闭。", en=f"Turned off the local channel for {conv_tag(conv)}.")
        elif value == "on":
            store.run("UPDATE convs SET local_enabled=1 WHERE id=?", (conv["id"],))
            await reply(chat_id, f"{conv_tag(conv)} 本地通道已开启，第一次用时会再请电脑主人批准。",
                        en=f"Turned on the local channel for {conv_tag(conv)}. The first time it's used, the computer's owner is asked to approve.")
        elif value.split(" ", 1)[0] == "device":
            choice = value[len("device"):].strip()
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
            dev = conv_device(conv_row(conv["id"]))
            await reply(chat_id, f"{conv_tag(conv)} 的本地操作发到：{device_label(dev) if dev is not None else '没有可用的电脑'}。"
                                 "换了电脑要由新电脑的主人重新批准。",
                        en=f"{conv_tag(conv)}'s local operations go to: "
                           f"{device_label(dev, 'en') if dev is not None else 'no computer (send /device to set one up)'}.")
        else:
            try:
                hours = float(value)
            except ValueError:
                hours = 0.0
            if not 0 < hours <= 720:
                await reply(chat_id, usage, en=usage_en)
                return
            dev = conv_device(conv)
            if dev is None or not may_approve(dev, user_id):
                where = device_label(dev) if dev is not None else "没有可用的电脑"
                where_en = device_label(dev, "en") if dev is not None else "no computer"
                await reply(chat_id, f"{conv_tag(conv)} 用的是 {where}，只有电脑主人能批准，你不能直接给时间。",
                            en=f"{conv_tag(conv)} uses {where_en}; only that computer's owner can approve it.")
                return
            store.run(
                "UPDATE convs SET local_enabled=1, local_until=?, local_dev=? WHERE id=?",
                (now() + hours * 3600, dev["id"], conv["id"]),
            )
            await reply(chat_id, f"{conv_tag(conv)} 在 {device_label(dev)} 上的本地通道授权 {hours:g} 小时。",
                        en=f"Approved {conv_tag(conv)}'s local channel on {device_label(dev, 'en')} for {hours:g} hour(s).")
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
            store.run("UPDATE convs SET local_until=?, local_dev=? WHERE id=?", (now() + LOCAL_WINDOW, dev["id"], conv_id))
            set_approval(approval_id, "approved")
            if LOCAL_WINDOW > 0:
                # 时间窗是按聊天开的：同一个聊天在这台电脑上还在等批的其他操作一起放行
                for other in store.q("SELECT id, payload FROM approvals WHERE kind='local' AND status='pending'"):
                    other_payload = json.loads(other["payload"] or "{}")
                    if other_payload.get("conv") == conv_id and other_payload.get("device", ADMIN_DEVICE) == dev["id"]:
                        set_approval(other["id"], "approved")
            await mark(f"已批准：{window_text()}", en=f"Approved: {window_text('en')}")
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
        state = conv_state(conv)["state"]
        if state in ("online", "busy"):
            await answer(f"{conv_id} 的子 agent 又回来了（{STATE_TEXT[state]}），不用交。真要换人用 /restart {conv_id}")
            return
        hand_over(conv, "管理员")
        await settle(f"已把 {conv_id} 交给 {cloud_tag(main_cloud())} 主控：旧的子 agent 已停，主控会开一个新的接手")
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
    if row["kind"] == "join":
        if choice == "new" and not cloud_has_chats(main_cloud()):
            choice = "main"
        payload["agent_id"] = make_main(new_cloud=choice == "new")
        set_approval(approval_id, "done", payload)
        await mark(f"已设为主控（{'新开' if choice == 'new' else '管'} {cloud_tag(main_cloud())}）")
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
    if raw.isdigit() and int(raw) in clouds:
        return int(raw)
    row = conv_row(selected(dm))
    if row is not None and row["id"] != "main" and cloud_of(row) in clouds:
        return cloud_of(row)
    return main_cloud()


def cloud_desc(dm: int, n: int, viewing: bool) -> str:
    rows = admin_cloud_rows(dm, n)
    parts = ["📁 " + ("主控" if n == main_cloud() else "没有主控"), f"{len(rows)} 个聊天"]
    unread = sum(unread_count(r["id"], dm) for r in rows)
    if unread:
        parts.append(f"🔴 {unread}条新消息")
    alerts = sum(1 for r in rows if conv_state(r)["state"] in ("stuck", "lost", "unclaimed"))
    if alerts:
        parts.append(f"⚠️ {alerts}")
    if viewing:
        parts.append("正在看")
    return " · ".join(parts)


def cloud_listing(dm: int, n: int) -> str:
    rows = admin_cloud_rows(dm, n)
    lines = [cloud_heading(n)]
    for row in rows:
        line = f"/{row['id']} {conv_name(row)} · {STATE_TEXT[conv_state(row)['state']]}"
        unread = unread_count(row["id"], dm)
        if unread:
            line += f" · 🔴 {unread}条新消息"
        lines.append(line)
    if not rows:
        lines.append("（这里现在没有你的聊天）")
    users = sum(1 for r in open_convs() if cloud_of(r) == n and conv_owner(r))
    if users:
        lines.append(f"另有被授权用户的聊天 {users} 个（/list 里看）。")
    if rows and n != main_cloud():
        lines.append(f"这里的子 agent 出问题时我直接提醒你，可以【交给 {cloud_tag(main_cloud())} 主控】，"
                     f"或者 /restart {rows[0]['id']} 这样交过去。")
    lines.append(f"菜单已换成 {cloud_tag(n)} 的聊天（重新打 / 就能看到）。")
    return "\n".join(lines)


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
            gone = [r for r in moved if cloud_of(r) == main_cloud()]
            if gone:
                system_note("main", f"管理员把 {'、'.join(conv_tag(r) for r in gone)} 划到了 {cloud_tag(n)}：不归你管了，别再动它们。", wake=0)
            lines.append(f"{cloud_tag(main_cloud())} 的主控不管它们了，出问题我直接提醒你。")
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
    main = conv_row("main")
    info = conv_state(main)
    info["unread"] = unread_count("main", dm)
    commands.append({"command": "main", "description": menu_desc(main, info, current == "main")})
    if view:
        commands += [{"command": cloud_tag(n), "description": cloud_desc(dm, n, n == view)} for n in sorted(clouds)]
    commands += [
        {"command": "new", "description": "➕ 新建聊天"},
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


async def watchdog_tick() -> None:
    mark_menu_dirty()
    batch = []
    for conv in open_convs():
        info = conv_state(conv)
        state, key, text = info["state"], "", ""
        if state in ("stuck", "lost") and away(conv):
            # 失联了又来消息变成卡住，还是同一次：管理员发消息时已经单独说过
            if alert_due(conv, "away"):
                batch.append((conv, info))
            continue
        if state in ("stuck", "lost"):
            key = state
            text = (f"{conv_tag(conv)} {describe(info)}。先 list_agents 看状态；可以 message_agent 提醒它；"
                    f"确认它停了就 restart_agent(chat=\"{conv['id']}\") 拿新任务原文，再开一个子 agent 接手（记录不丢）。")
        elif state == "unclaimed":
            if away(conv):
                # 任务只有现在的主控能开
                store.run("UPDATE convs SET cloud=? WHERE id=?", (main_cloud(), conv["id"]))
                conv = conv_row(conv["id"])
            key = "unclaimed"
            text = (f"{conv_tag(conv)} 的任务发出 {human_dur(now() - conv['task_ts'])} 了，还没有子 agent 接手。"
                    f"请在你自己的对话内部开一个子 agent（后台运行），把下面两条 ---- 之间的内容原样交给它。{model_hint(conv)}\n"
                    f"----\n{task_text(conv)}\n----")
        await raise_alert(conv, key, text)
    await notify_away(batch)
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
