#!/usr/bin/env python3
"""r07md.py — 把 reviews/<matchId>.json 渲染成叙述版 reviews/<matchId>.md（R07 v2.0）。

叙述段落（oneLine / narrative）是手写的，放在 review_src/<matchId>.py 的 SRC 里；表格部分直接取自 JSON，保证两边数字一致。
行数控制在 80~158 行（collect-reviews.py 的上限是 160 个换行）。
"""

VERDICT_CN = {"error": "错", "good": "对", "unclear": "不确定"}
KIND_CN = {"spawn": "出生", "expand": "扩张", "attack": "进攻", "keep": "留兵", "donate": "捐款", "assist": "协防", "boat": "船", "idle": "不动", "other": "其他"}
ST_CN = {"observed": "观察", "inferred": "推断", "guess": "猜测"}


def pct(x, nd=2):
    return "—" if x is None else f"{100 * x:.{nd}f}%"


def num(x):
    return "—" if x is None else f"{x:,}"


def cell(s):
    return str(s).replace("|", "／").replace("\n", " ")


def render(doc, src):
    c = doc["context"]
    o = doc["outcome"]
    L = []
    res_cn = {"won": "赢", "lost": "输", "over": "未分胜负"}.get(o["result"], o["result"])
    L.append(f"# {doc['matchId']} 复盘（R07）— {c['squad']} · {res_cn} · 分型 `{doc['lossArchetype']}`")
    L.append("")
    L.append(f"> {src.get('oneLine', '')}")
    L.append("")
    L.append("## 1. 对局背景")
    L.append(f"- 时间 {c['time']}；地图 {c['map']}（陆地 {num(c['mapLand'])} 格）；名义 {c.get('nominalTeams')} 队 / 实际 {c['teams']} 队，{c['humans']} 名真人位；"
             f"我方 {c['bots']} 个号，队伍分布 {c.get('teamSplitCounts')}，主队 T{c['ourTeam']}。")
    L.append(f"- 结果：{res_cn}；终局拍 {o['endTick']}；我方主队最终份额 {pct(o.get('ourFinalShare'))}（第 {o.get('ourTeamRank')} 名），"
             f"全队（有快照的号）领土峰值 {pct(o.get('peakSquadLandShare'))}，主队份额峰值（结算快照里见到的）{pct(o.get('peakPrimaryTeamShareSeen'))}；当时第一名 T{o.get('winnerTeam')}。")
    L.append(f"- 策略：{c['strategyVersion']}。")
    if c.get("contamination"):
        L.append("- 污染/执行类问题：" + "；".join(c["contamination"]) + "。")
    if c.get("notes"):
        L.append(f"- 数据边界：{c['notes']}")
    L.append("")
    L.append("## 2. 时间线")
    L.append("| 拍 | 未结算 | 有快照 | 我方号份额 | 我方兵力 | 密度 | 围死 | 主队份额(名次) | 最强敌队 | 备注 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for p in doc["timeline"]:
        team = "—" if p.get("teamLandShare") is None else f"{pct(p['teamLandShare'])}(第{p['teamRank']})@{p.get('teamSnapshotAt')}"
        enemy = "—" if p.get("topEnemyTeam") is None else f"T{p['topEnemyTeam']} {pct(p['topEnemyShare'])}"
        L.append(f"| {p['t']} | {p['alive']} | {p['logging']} | {pct(p['squadLandShare'])} | {num(p['squadTroops'])} | {p['squadDensity'] if p['squadDensity'] is not None else '—'} | {p['boxedBots']} | {team} | {enemy} | {cell(p.get('note', ''))} |")
    L.append("")
    L.append("## 3. 经过")
    for para in src.get("narrative", []):
        L.append(f"- {para}")
    L.append("")
    L.append("## 4. 转折点")
    for i, tp in enumerate(doc["turningPoints"], 1):
        L.append(f"**转折点 {i}（t={tp['t0']}~{tp['t1']}，份额 {pct(tp.get('shareBefore'))}→{pct(tp.get('shareAfter'))}，{ST_CN.get(tp['statementType'], tp['statementType'])}）** {tp['what']}")
        for e in tp["evidence"][:5]:
            L.append(f"- 证据：{e}")
        for pd in tp["priorDecisions"]:
            L.append(f"- 之前的决策（t={pd.get('t')} {pd.get('bot')}）：{pd.get('action')} ⇒ 代码：{pd.get('codePath')}")
        L.append(f"- 换个做法会怎样：{tp.get('alternatives', '')} 把握：{tp.get('confidence', '')}")
    L.append("")
    L.append("## 5. 阵亡链")
    if doc["deaths"]:
        L.append("| 号 | 阵亡拍 | 名次 | 领土峰值 | 死时余额 | 死前500拍 收到/捐出 | 死因链 |")
        L.append("|---|---|---|---|---|---|---|")
        for d in doc["deaths"]:
            di = d.get("donIn500") or {}
            do = d.get("donOut500") or {}
            L.append(f"| {d['bot']} | {d.get('t')} | {d.get('place')} | {num(d.get('peakTerr'))} | {num(d.get('balanceAtDeath'))} | "
                     f"{di.get('n', 0)} 笔≈{num(di.get('amt', 0))} / {do.get('n', 0)} 笔 | {cell(d['cause'])} |")
    else:
        L.append("本局我方没有号阵亡。")
    L.append("")
    L.append("## 6. 决策实例")
    L.append("| 拍 | 号 | 类 | 判定 | 当时状态 → 为什么 | 代码路径 | 代价 | 模式 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for d in doc["decisions"]:
        L.append(f"| {d['t']} | {cell(d['bot'])} | {KIND_CN.get(d['kind'], d['kind'])} | {VERDICT_CN.get(d['verdict'], d['verdict'])} | {cell(d['state'])} → {cell(d['why'])} | "
                 f"{cell(d['codePath'])} | {cell(d.get('estCost', ''))} | {d['patternId'].replace('NEW:', '')} |")
    L.append("")
    L.append("## 7. 六项机制核实")
    names = {"1_quotaRejections": "防喂兵配额拒绝", "2_donationTax": "6.25% 捐款税", "3_inlandStagnation": "内陆后排囤兵",
             "4_spawnOpening": "出生阵型与开局", "5_frontlineFloors": "前线消耗与保底", "6_teamSplit": "分队",
             "7_lagBatches": "卡顿与清仓批（广播 0003-③）", "8_noFullSendLock": "isNoFullSend 误锁（广播 0003-④）",
             "9_invertedFeeding": "低密向高密输血（广播 0003-⑤）", "10_spawnRecompute": "出生点重算（广播 0003-⑥）",
             "11_winFloorMateLock": "t<1500 打内置 AI 的留底互锁（广播 0004-①）", "12_oneCmdPerTick": "每个决策拍只发出一条指令（广播 0004-②）",
             "13_inflightRepeat": "未生效就重复下单（广播 0004-③）", "14_capTruncPingPong": "硬上限截断与来回倒手（广播 0004 审计②）",
             "15_lateAiFloors": "t≥1500 吃内置 AI 的留底与门槛（广播 0005-①②）", "16_overSkipsPrice": "过软上限后不比价（广播 0005-③）",
             "17_yieldDispatch": "调度的利息账（广播 0005-④）", "18_doomedPocket": "弃子判定（广播 0005-⑤）", "19_boatVoyage": "船的损耗（广播 0005-⑥）"}
    for k, v in (doc.get("mechanismChecks") or {}).items():
        L.append(f"- **{names.get(k, k)}**：{v}")
    L.append("")
    L.append("## 8. 赢家、做对的、还不知道的")
    L.append(f"- **赢家**：{doc['winnerNotes']}")
    L.append("- **做对的**：" + "；".join(doc.get("wentWell") or []) + "。")
    unk = doc.get("unknowns") or []
    L.append("- **还不知道的**：" + "；".join(f"（{i}）{u}" for i, u in enumerate(unk, 1)) + "。")
    mq = doc.get("mechanicsQuestions") or []
    if mq:
        L.append("- **机制疑问**：" + " ".join(f"（{i}）{q}" for i, q in enumerate(mq, 1)))
    L.append("")
    L.append("## 9. 复现")
    L.append(f"- 在 `c136-review/agents/R07/scripts/` 下依次运行：`python3 40_game_digest.py {doc['matchId']}`、`python3 30_donation_ledger.py {doc['matchId']}`、"
             f"`python3 42_patterns.py {doc['matchId']}`、`python3 44_donation_targets.py {doc['matchId']}`、`python3 50_build_review.py {doc['matchId']}`"
             + ("；本局另用 " + "、".join(f"`{s}`" for s in src.get("extraCommands", [])) if src.get("extraCommands") else "") + "。")
    L.append(f"- 把握：{doc['confidenceOverall']}")
    return "\n".join(L) + "\n"
