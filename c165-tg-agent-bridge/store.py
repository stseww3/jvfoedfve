"""SQLite 存储。所有表结构和旧库迁移都在这里。

聊天记录全部留在 messages 表里，关闭的聊天也不删。
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

TABLES = """
CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY, v TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    name TEXT DEFAULT '',
    role TEXT NOT NULL,            -- admin | user
    dm_chat_id INTEGER,
    created REAL
);

CREATE TABLE IF NOT EXISTS activations(
    chat_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(chat_id, user_id)
);

-- Telegram 里的私聊和群
CREATE TABLE IF NOT EXISTS chats(
    chat_id INTEGER PRIMARY KEY,
    type TEXT,                     -- private | group | supergroup | channel
    title TEXT DEFAULT '',
    listen TEXT DEFAULT 'mention', -- mention | all
    open INTEGER DEFAULT 0,        -- 1 = 群里所有人都能唤醒 agent
    updated REAL
);

-- 聊天：main 是主控；c1、c2… 各由一个子 agent 负责。关闭的聊天连同记录都留着。
CREATE TABLE IF NOT EXISTS convs(
    id TEXT PRIMARY KEY,
    num INTEGER DEFAULT 0,
    name TEXT DEFAULT '',          -- 子 agent 自己取的名字
    brief TEXT DEFAULT '',         -- 管理员 /new 时写的说明
    status TEXT DEFAULT 'open',    -- open | closed
    agent TEXT DEFAULT '',         -- 当前接手的身份
    task_code TEXT DEFAULT '',     -- 一次性任务码，子 agent 用它接手，用过作废
    task_ts REAL DEFAULT 0,
    home_chat INTEGER DEFAULT 0,   -- 这个聊天所在的管理员私聊
    read_cursor INTEGER DEFAULT 0,
    local_enabled INTEGER DEFAULT 1,
    local_until REAL DEFAULT 0,
    alert TEXT DEFAULT '',         -- 看门狗当前的警告
    alert_ts REAL DEFAULT 0,
    created REAL,
    closed REAL DEFAULT 0
);

-- 身份：主控 m_…，子 agent a_…（随机长串，就是调用凭据）。一个聊天同一时间只有一个有效身份，重开时旧身份作废。
CREATE TABLE IF NOT EXISTS agents(
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,            -- main | chat
    conv TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- active | stopped
    note TEXT DEFAULT '',          -- 停用原因
    renew INTEGER DEFAULT 0,       -- 续到第几棒
    last_seen REAL DEFAULT 0,
    last_tool TEXT DEFAULT '',
    created REAL
);

-- 群和其他用户的私聊交给哪个聊天负责；没有记录的先到主控，由主控分配。
CREATE TABLE IF NOT EXISTS routes(
    chat_id INTEGER PRIMARY KEY,
    conv TEXT NOT NULL
);

-- 管理员授权：reader 聊天可以读 source 聊天的记录。
CREATE TABLE IF NOT EXISTS shares(
    reader TEXT,
    source TEXT,
    ts REAL,
    PRIMARY KEY(reader, source)
);

-- 跑 local_client.py 的电脑。d0 是管理员自己的（.env 里的 CLIENT_TOKEN），d1、d2… 是信任用户申请的。
-- 只存 token 的哈希；在哪台电脑上执行操作由电脑主人批准。
CREATE TABLE IF NOT EXISTS devices(
    id TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    owner INTEGER DEFAULT 0,       -- 主人的 Telegram 用户 id；d0 是 0（= 管理员）
    token_hash TEXT DEFAULT '',
    status TEXT DEFAULT 'active',  -- active | revoked
    created REAL,
    last_seen REAL DEFAULT 0,
    info TEXT DEFAULT ''           -- 上次连上时报的系统和工作区根目录
);

CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    chat_id INTEGER,
    chat_type TEXT,                -- private | group | supergroup | system
    chat_title TEXT DEFAULT '',
    user_id INTEGER DEFAULT 0,
    user_name TEXT DEFAULT '',
    text TEXT DEFAULT '',
    file_id TEXT DEFAULT '',
    tg_msg_id INTEGER DEFAULT 0,
    reply_to_bot INTEGER DEFAULT 0,
    mention INTEGER DEFAULT 0,
    outgoing INTEGER DEFAULT 0,
    target TEXT DEFAULT '',        -- 进哪个聊天的收件箱（main / c1 …）
    wake INTEGER DEFAULT 0
);

-- Telegram 消息 id -> 聊天，引用回复时用来切到对应聊天
CREATE TABLE IF NOT EXISTS tgmsgs(
    chat_id INTEGER,
    tg_msg_id INTEGER,
    conv TEXT,
    PRIMARY KEY(chat_id, tg_msg_id)
);

CREATE TABLE IF NOT EXISTS files(
    id TEXT PRIMARY KEY,
    chat_id INTEGER,
    tg_file_id TEXT,
    name TEXT,
    size INTEGER,
    mime TEXT,
    path TEXT,
    ts REAL
);

CREATE TABLE IF NOT EXISTS approvals(
    id TEXT PRIMARY KEY,
    kind TEXT,                     -- join | local | ask
    payload TEXT,
    status TEXT DEFAULT 'pending', -- pending | approved | denied | done
    ts REAL
);

-- bot 见过的所有 Telegram 用户（不管有没有资格），/grant @用户名 靠它找 id
CREATE TABLE IF NOT EXISTS people(
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    name TEXT DEFAULT '',
    is_bot INTEGER DEFAULT 0,
    updated REAL
);

-- Agent 协作群（纯 MCP 内部群，同 owner 隔离）
CREATE TABLE IF NOT EXISTS agent_groups(
    id TEXT PRIMARY KEY,
    num INTEGER DEFAULT 0,
    name TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    creator TEXT DEFAULT '',
    owner INTEGER DEFAULT 0,
    status TEXT DEFAULT 'open',    -- open | closed
    streak INTEGER DEFAULT 0,
    streak_ts REAL DEFAULT 0,
    created REAL
);

CREATE TABLE IF NOT EXISTS agent_group_members(
    group_id TEXT,
    conv TEXT,
    joined REAL,
    PRIMARY KEY(group_id, conv)
);

CREATE TABLE IF NOT EXISTS agent_group_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    sender_conv TEXT NOT NULL,
    sender_name TEXT DEFAULT '',
    text TEXT NOT NULL,
    mentions TEXT DEFAULT '',
    ts REAL
);

-- Agent 私聊连续轮次防死循环计数
CREATE TABLE IF NOT EXISTS agent_dm_streaks(
    pair TEXT PRIMARY KEY,
    streak INTEGER DEFAULT 0,
    last_sender TEXT DEFAULT '',
    ts REAL DEFAULT 0
);

-- AI 实时动作/改文件/命令/思考/耗时追踪快照与最近轨迹
CREATE TABLE IF NOT EXISTS agent_traces(
    conv TEXT PRIMARY KEY,
    agent_id TEXT DEFAULT '',
    conversation_id TEXT DEFAULT '',
    phase TEXT DEFAULT '',         -- idle_wait | thinking | shell | file_edit | file_read | mcp | tool | stopped
    tool_name TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    started_ts REAL DEFAULT 0,
    updated_ts REAL DEFAULT 0,
    output_ts REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_trace_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conv TEXT NOT NULL,
    event TEXT NOT NULL,
    phase TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    duration_ms INTEGER DEFAULT 0,
    ts REAL
);

-- 多主 Agent 启动器池（main1..N）与云端工作机池（node1..K）及 CPU/内存探针与独占/共享权限表
CREATE TABLE IF NOT EXISTS exec_nodes(
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,            -- launcher (mainN) | runner (nodeN)
    num INTEGER DEFAULT 0,
    cloud_num INTEGER DEFAULT 0,
    name TEXT DEFAULT '',
    agent TEXT DEFAULT '',
    status TEXT DEFAULT 'online',  -- online | offline | draining | removed
    exclusive_conv TEXT DEFAULT '',-- ''=共享池；cXXX=独占分配给该聊天
    allowed_convs TEXT DEFAULT '[]',-- JSON 数组：总控授权允许借用该机器的聊天列表
    metrics_json TEXT DEFAULT '{}',-- CPU/负载/内存/balloon探针快照
    metrics_ts REAL DEFAULT 0,
    last_seen REAL DEFAULT 0,
    created REAL DEFAULT 0,
    note TEXT DEFAULT ''
);

-- 标准化无脑执行指令单与回执队列表
CREATE TABLE IF NOT EXISTS dispatch_ops(
    op_id TEXT PRIMARY KEY,
    target_node TEXT NOT NULL,
    op_type TEXT NOT NULL,         -- launch_subagent | resume_subagent | workspace_job
    conv_id TEXT DEFAULT '',
    requester TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'pending', -- pending | done | failed | cancelled
    result_json TEXT DEFAULT '{}',
    created_ts REAL DEFAULT 0,
    done_ts REAL DEFAULT 0
);

-- Web 控制台用户表（zwt 为唯一超级管理员，首次访问自设密码，PBKDF2 加盐哈希存储）
CREATE TABLE IF NOT EXISTS web_users(
    username TEXT PRIMARY KEY,
    password_hash TEXT DEFAULT '',
    role TEXT NOT NULL DEFAULT 'user', -- superadmin (仅 zwt) | user
    tg_owner INTEGER DEFAULT 0,        -- 0=zwt管理员全局视图；非0=对应授权用户私聊隔离空间
    display_name TEXT DEFAULT '',
    disabled INTEGER DEFAULT 0,
    created REAL DEFAULT 0,
    last_login REAL DEFAULT 0
);

-- Web 登录会话表（仅存随机 session token 的 SHA-256 哈希）
CREATE TABLE IF NOT EXISTS web_sessions(
    token_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created REAL DEFAULT 0,
    expires REAL DEFAULT 0,
    ua TEXT DEFAULT ''
);
"""

COLUMNS = (
    ("messages", "conv", "TEXT DEFAULT ''"),          # 这条记录属于哪个聊天；'' = 还没分配
    ("messages", "sender", "TEXT DEFAULT ''"),        # 发出这条的身份
    ("messages", "delivered", "INTEGER DEFAULT 1"),   # AI 发给管理员的：0 = 管理员没切过来，先存着
    ("messages", "extra", "TEXT DEFAULT ''"),         # 存着的消息怎么补发（按钮 / 文件）
    ("files", "conv", "TEXT DEFAULT ''"),
    ("convs", "device", "TEXT DEFAULT ''"),           # 管理员指定这个聊天用哪台电脑；'' = 自动
    ("convs", "local_dev", "TEXT DEFAULT ''"),        # local_until 这个时间窗是哪台电脑的主人批的
    ("convs", "owner", "INTEGER DEFAULT 0"),          # 谁建的：0 = 管理员；否则是被授权用户的 id，只有他能用
    ("convs", "git", "TEXT DEFAULT ''"),              # 子 agent 用 set_repo 记下的 GitHub 仓库和分支（JSON）
    ("convs", "model", "TEXT DEFAULT ''"),            # 管理员或父 agent 指定的模型（原话）；'' = 子 agent 继承主控的模型
    ("convs", "cloud", "INTEGER DEFAULT 0"),          # 归哪个 cloud（目录）：开它子 agent 的主控在哪个云端 agent；main 这行记现在的主控管哪个；0 = 还没分
    ("convs", "parent_conv", "TEXT DEFAULT ''"),      # 哪个子 agent 请求创建的；'' = 人类或主控直接创建
    ("convs", "memory_note", "TEXT DEFAULT ''"),      # 父 agent 创建子 agent 时附带的当前记忆交接摘要
    ("convs", "spawn_notified", "INTEGER DEFAULT 0"), # 子 agent 首次 join 时是否已通知父 agent
    ("convs", "task_agent_id", "TEXT DEFAULT ''"),    # 主控记录的 Cursor Task agent_id，供 resume 判活/续跑
    ("chats", "owner", "INTEGER DEFAULT 0"),          # 群归谁：0 = 管理员；否则是把 bot 拉进群的被授权用户
    ("devices", "window_sec", "INTEGER DEFAULT -1"),  # 这台电脑点批准时的默认放行秒数；-1=沿用全局 LOCAL_WINDOW；0=每次都问
    ("devices", "auth_until", "REAL DEFAULT 0"),      # 整机免批截止时间戳；>now() 时该电脑主人名下所有开启本地通道的聊天直接放行
    ("convs", "in_tg", "INTEGER DEFAULT 1"),          # 1=接入Telegram聊天列表；0=纯后台MCP子agent（不进TG菜单/列表，不向TG发消息）
    ("agent_traces", "thought_ts", "REAL DEFAULT 0"), # 最后一次 afterAgentThought 真实思考完成时间戳（判死核心指标）
    ("agent_traces", "hb_ts", "REAL DEFAULT 0"),      # 最近一次 VM 探针心跳时间戳（区分单 agent 思考卡死 vs 整机探针离线）
    ("agent_traces", "metrics_json", "TEXT DEFAULT '{}'"),  # VM 实时 CPU / 内存探针快照
    ("convs", "dedicated_req", "INTEGER DEFAULT 0"),  # 创建时是否申请独占机器（默认 0 不独占）
    ("convs", "dedicated_node", "TEXT DEFAULT ''"),   # 总控实际批准绑定的独占机器（如 main2 / node1）
    ("convs", "machine_reason", "TEXT DEFAULT ''"),   # 申请独占机器的原因说明
    ("convs", "auto_restarted_ts", "REAL DEFAULT 0"), # 最近一次因 5 分钟思考卡死自动重开的时间戳（防抖保护）
)

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_messages_target ON messages(target, id);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conv, id);
CREATE INDEX IF NOT EXISTS idx_messages_unsent ON messages(chat_id, conv, delivered);
CREATE INDEX IF NOT EXISTS idx_people_username ON people(username COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_agent_group_msgs ON agent_group_messages(group_id, id);
CREATE INDEX IF NOT EXISTS idx_agent_group_members_conv ON agent_group_members(conv);
CREATE INDEX IF NOT EXISTS idx_agent_trace_events_conv ON agent_trace_events(conv, id);
CREATE INDEX IF NOT EXISTS idx_dispatch_ops_node ON dispatch_ops(target_node, status, created_ts);
CREATE INDEX IF NOT EXISTS idx_dispatch_ops_conv ON dispatch_ops(conv_id, created_ts);
"""


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._con = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA journal_mode=WAL")
        agent_columns = self.columns("agents")
        if agent_columns and "conv" not in agent_columns:
            # 上一版（认领码那套）的身份表，结构对不上，留作备份
            self._con.execute("ALTER TABLE agents RENAME TO agents_v2")
        self._con.executescript(TABLES)
        for table, column, decl in COLUMNS:
            if column not in self.columns(table):
                self._con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        self._con.executescript(INDEXES)

    def columns(self, table: str) -> set[str]:
        return {row[1] for row in self._con.execute(f"PRAGMA table_info({table})")}

    def q(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._con.execute(sql, args))

    def one(self, sql: str, args: tuple = ()) -> sqlite3.Row | None:
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def run(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            cur = self._con.execute(sql, args)
            return cur.lastrowid or 0

    def get(self, key: str, default: str = "") -> str:
        row = self.one("SELECT v FROM config WHERE k=?", (key,))
        return row["v"] if row else default

    def set(self, key: str, value: str) -> None:
        self.run(
            "INSERT INTO config(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (key, value),
        )

    def delete(self, key: str) -> None:
        self.run("DELETE FROM config WHERE k=?", (key,))

    def insert_message(self, **fields: Any) -> int:
        fields.setdefault("ts", time.time())
        cols = ",".join(fields)
        marks = ",".join("?" for _ in fields)
        return self.run(f"INSERT INTO messages({cols}) VALUES({marks})", tuple(fields.values()))


def migrate_v1(store: Store, old_path: Path) -> list[str]:
    """把旧版 app.db 里还有用的东西搬过来：管理员、授权、群激活、主会话密钥、没读的消息。"""
    if store.get("migrated_v1") or not old_path.exists():
        return []
    notes: list[str] = []
    old = sqlite3.connect(old_path)
    old.row_factory = sqlite3.Row
    now = time.time()

    def table_rows(name: str) -> list[sqlite3.Row]:
        try:
            return list(old.execute(f"SELECT * FROM {name}"))
        except sqlite3.Error:
            return []

    for row in table_rows("admins"):
        store.run(
            "INSERT OR IGNORE INTO users(user_id,role,dm_chat_id,created) VALUES(?,?,?,?)",
            (row["user_id"], "admin", row["chat_id"], now),
        )
    for row in table_rows("grants"):
        store.run(
            "INSERT OR IGNORE INTO users(user_id,role,created) VALUES(?,?,?)",
            (row["user_id"], "user", now),
        )
    for row in table_rows("group_active"):
        store.run("INSERT OR IGNORE INTO activations(chat_id,user_id) VALUES(?,?)", (row["chat_id"], row["user_id"]))

    for row in table_rows("sessions"):
        if row["role"] == "main" and row["key"]:
            store.set("account_key", row["key"])
            notes.append("账号密钥沿用旧版主会话密钥")

    for row in table_rows("messages"):
        store.insert_message(
            ts=now,
            chat_id=row["tg_chat_id"],
            chat_type="private" if row["kind"] == "dm" else "group",
            user_id=row["user_id"],
            user_name=row["user_name"],
            text=row["text"],
            target="main",
            conv="",
            wake=1,
        )
        notes.append(f"旧消息转给主控: {row['text'][:20]}")

    for row in table_rows("meta"):
        if row["k"] == "tg_offset":
            store.set("tg_offset", row["v"])

    old.close()
    store.set("migrated_v1", str(now))
    return notes
