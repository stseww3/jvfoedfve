#!/usr/bin/env python3
"""xtruth.py — 发现集全部录像的「开局段真值」跨局计数（到 t=1800）：人均对照的走势、内置 AI 的地谁吃了、
陆攻落地后有没有生效、出生点几何、日志里发出的指令和录像里落地的指令对不对得上。

先出每局的压缩真值表（重计算闸；一局 0.3~4 秒，105 局合计约 2 分钟，分批跑）：
    bash c136-review/tools/run-heavy.sh node c136-review/agents/R08/scripts/xtruth.mjs <局> <局> …
    （指令流另见 xbatch.py 文件头的 replay_cmds.mjs 那一步）
再计数：
    python3 xtruth.py [--quiet]        → out/_cross/xtruth.txt、xtruth.json

只读 /agent/repos/c136-data/bundles/（发现集，局号取自 manifest.jsonl 里 split == "discovery" 的行）；验证集不碰。
out/_run/ 不入库，随时可以按上面两步重建。

席位分组和 xbatch.py 完全一样（own / [APEX] / 名字池 / 野人；机器号 = 前三组）。own 的认法：facts 里这支编队的号，
且录像里这个席位的名字以它的某个日志标签结尾。一局「对得上」= 重演出来的地 / 兵和 traj.csv 的快照逐行相等的 ≥90%
（至少 10 行）——对不上说明包里的录像是别的房间的，这局不进 own 的统计。

口径：
  · 人均对照 = 这一拍在线的 own 号的人均地 ÷ 在线的野人的人均地（两边各至少 3 / 5 个号才算）。在线 = 还有地、且还没离开；
    离开后的空壳由引擎的 AI 接管，不算任何一组的人头（两组一视同仁）。另给「按出生人数」口径
    （死掉的、离开的号按 0 算进分母），防「野人里死掉的不算」把对照抬高。
  · 掉队 = t=630 时人均对照 ≥0.90，且 t=1500 时 ≤ t=630 的 0.75 倍。
  · AI 的地 = (600,1500] 里真人从内置 AI 手里吃下的格（AI 之间互吃、AI 被淘汰后变无主地再被吃的不算）；
    份额对照 = own 吃到的份额 ÷ own 在 t=600 还有地的真人里的人头份额。
  · 无主地 = (0,600] 里真人吃下的无主地格；份额对照同上，人头按出生人数。
  · 陆攻落地后生效 = 录像里落地的陆攻指令，引擎真的派出了兵（没有因为目标没了 / 不接壤 / 兵不够被作废）。
  · 贴边 = 出生点离地图边 ≤ 短边的 12%。
  · 发出 vs 落地 = 日志 HL-TICK 的 cmds 计数增量（策略在自己视角里发出的条数） vs 录像里这个席位落地的指令，分三类对：
    陆攻（cmds 增量 − boats 增量 − 同段的捐款日志行 vs 录像的陆攻）、捐款（HL-DONATE / HL-DISPATCH 行 vs 录像的捐款）、
    船（boats 增量 vs 录像的发船；跳岛那条分支发船不记 cmds，所以船单列）。
    两边都按日志快照的拍切段（快照 90 拍一条），录像到哪算到哪。卡顿时落地会晚到下一段（1500~3000 的比值因此会超过 1），
    分段只看量级；600~3000 合起来的一行消掉了这种串段。
节：
  [XT-A] 覆盖与核对  [XT-B] 人均对照走势  [XT-C] AI 的地 / 无主地  [XT-D] 陆攻生效率  [XT-E] 出生点  [XT-F] 发出 vs 落地
  [XT-G] 1800 拍前出局 / 离开  [XT-H] 逐局  [XT-I] 接壤普查（挨着白给的内置 AI 出不出手；不跑策略）
  [XT-J] 买 AI 地规则重算（把 1500 拍前买内置 AI 地的规则照抄到每个样本上：放行 / 已在打 / 槽满 / 不值 / 留底三项）
  [XT-C] 里另有三张表（600~1500，和吃地账同一批席位）：
    · 地的收支：人均净增拆成 从内置 AI 吃 / 从无主地吃 / 从真人吃 / 被真人吃走 / 其余
    · 一条打内置 AI 的生效陆攻换回多少地：人均条数、每条派出的兵、每条吃到的格、烧掉 ÷ 派出
    · 逐对账：把每个号对同一个内置 AI 的生效陆攻合成一对——人均对几个 AI 下过手、每对几条、派出 ÷ 打垮价、
      吃到 ÷ 可吃、下手时 AI 有多大；按「独吃 / 和机器号同吃 / 和野人同吃」分
  [XT-I] 里另有无主地一栏：挨着无主地的样本，90 拍内有没有一条生效的陆攻落在无主地上
规则重算的口径（[XT-J]）：
  · 规则 = 1500 拍前（coreFrom = dpEnd = 1500）买非真人邻居的那条路：General.act → Style.pickTarget → V13.allow / floorFor0 →
    Policy.winFloor → minShare。只重算「对内置 AI 这一拍放不放行」，不重算打分和别的分支（打真人、扩无主地、船）。
  · 输入全部取自引擎状态（xtruth.mjs 在重演里每 30 拍记一次），不跑策略、不依赖日志；所以野人席位也能套同一把尺子当对照。
  · c110（squad20）的邻居表不含「受保护的队友」（名字池 / [NPL] / [NOPE]；analyze L440），dpKeep 里不算它们；
    c116 系（squad10）只排除同队。sb（threatOf）两档都不排除任何人。
  · 核对：几乎不卡的局里，规则放行的样本 90 拍内出手的比例应当接近 100%（放行了就该发得出去）——见 [XT-J] 的分开看。
"""
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facts  # noqa: E402
import r08lib as L  # noqa: E402
from xbatch import name_pool, discovery_ids, MINE  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "xtruth")
STREAMS = os.path.join(OUT, "_run", "streams")
CP = [300, 600, 630, 900, 1260, 1500, 1800]
GROUPS = ("own", "apex", "pool", "wild")
GROUP_CN = dict(own="本编队", apex="[APEX]", pool="名字池", wild="野人", bot="机器号")
LOGPER = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000+", 3000, 10 ** 9), ("600~3000", 600, 3000)]
COHORTS = ("squad10", "squad20", "squad8")


# 1500 拍前买内置 AI 地的规则用到的参数（dump_params.mjs 核过：c110 / c116 / c116-va / c116-vb 这几项取值相同）
RULE = dict(winR=0.002, minSend=0.2141, botMax=60, idleCap=1.25, feeK=4, maxTargets=4, maxCost=338.1478)
RULE_CLASSES = ("allowed", "again", "engaged", "slot", "worth", "px", "dp", "sb", "other")
RULE_CN = dict(allowed="规则放行（有新目标）", again="规则放行，但放行的都是已经压着兵的 AI（续兵）", engaged="挨着的 AI 都已在打、按 L1200 跳过", slot="进攻槽 / 目标数占满",
               worth="AI 的地不值（allow 不过）", px="留底·地价项", dp="留底·防真人项 dpKeep", sb="留底·AI 仇恨项 sb", other="其它")
SRC_GROUPS = ("own", "apex", "pool", "wild", "shell", "ai", "none")
SRC_CN = dict(own="本编队的号", apex="[APEX]", pool="名字池", wild="野人", shell="离开者的空壳", ai="内置 AI", none="无")


def med(v):
    return statistics.median(v) if v else None


def rule_eval(rw, protected, engaged_rule):
    """把 1500 拍前买内置 AI 地的规则照抄到一个样本上（不跑策略，只用引擎状态）。
    代码位置（c110；别的档对应行见 out/_cross/codemap.txt）：General.act L804-846 → Style.pickTarget L1180-1214 →
    V13.allow L2147-2156（botOk L2499-2505、price L1141-1143）→ V13.floorFor0 L2270-2276 → Policy.winFloor L4542-4550
    （dpKeep L2491-2496、safeFinite L2532-2542 / threatOf L464-491）→ minShare L2131-2134 / minCmd L521-523。
    engaged_rule：pickTarget L1200「已经在打的非真人目标跳过（除非它在反打我、且我压上去的兵还不到 0.35·need）」只有 c110 有；
    c116 / c116-va / c116-vb / g09 的 pickTarget 没有这一行（codemap.txt [CM-C]），已经在打的 AI 每个决策拍都重新当候选。
    返回 (类别, 细节)：
      allowed  至少有一个还没压兵的内置 AI 通过全部条件（这一拍规则会对一个新目标发兵）
      again    有通过全部条件的 AI，但都是已经压着兵的（规则会再发一条到同一个 AI 上）
      engaged  （只 c110）候选全被 L1200 跳过：挨着的、还打得动的 AI 都已经在打
      slot     进攻槽满，或同时在打的非无主地目标数到了 maxTargets
      worth    挨着的内置 AI 都过不了 allow（botPx > winWorth 或 price > botMax，且余额没到 idle 线）
      px / dp / sb  过了 allow，但 avail = 余额 − max(地价项, dpKeep, sb) 不超过余额的 minSend（21.41%）；按三项里最大的那一项归类
      other    挨着的 AI 的 need 都 ≤ 0（已经压够了兵）
    """
    t, _p, _free, _afford, _hit, bal, L, sb, sb_src, slot_free, active, persons, ais = rw
    dp_src, m = -1, 0
    for q, v in persons:
        if q not in protected:
            dp_src, m = q, v
            break
    dp = max(0.0, (m - 1.5 * L) / 1.78)
    min_cmd = RULE["feeK"] * (12 * bal // 1024)
    idle = bal >= RULE["idleCap"] * 100 * L
    worth = RULE["winR"] * t * bal / max(1, L)
    det = dict(dp=dp, dpSrc=dp_src, sb=sb, sbSrc=sb_src, eng=any(a[4] > 0 for a in ais))
    cands = []
    skipped = 0
    for q, px100, pr100, need, mine, theirs, _cnt, _tq, _bq in ais:
        if need <= 0:
            continue
        if engaged_rule and mine > 0 and (theirs == 0 or mine >= 0.35 * need):
            skipped += 1
            continue
        cands.append((q, px100 / 100, pr100 / 100, mine))
    new_ok = bool(slot_free) and active < RULE["maxTargets"]
    ok_slot = [c for c in cands if c[3] > 0 or new_ok]
    ok_allow = [c for c in ok_slot if ((c[1] <= worth and c[2] <= RULE["botMax"]) or idle) and c[2] <= RULE["maxCost"]]
    passes = lambda a: a > RULE["minSend"] * bal and a >= min_cmd
    best = None
    fire_new = fire_again = False
    for c in ok_allow:
        px_floor = c[1] * L / (RULE["winR"] * max(1, t))
        avail = bal - max(px_floor, dp, sb)
        if passes(avail):
            if c[3] > 0:
                fire_again = True
            else:
                fire_new = True
        if best is None or avail > best[0]:
            best = (avail, px_floor)
    if fire_new:
        return "allowed", det
    if fire_again:
        return "again", det
    if not cands:
        return ("engaged" if skipped else "other"), det
    if not ok_slot:
        return "slot", det
    if not ok_allow:
        return "worth", det
    avail, px_floor = best
    terms = dict(px=px_floor, dp=dp, sb=sb)
    top = max(("sb", "dp", "px"), key=lambda k: terms[k])
    det["over"] = avail <= 0
    rest = max(v for k, v in terms.items() if k != top)
    det["sole"] = passes(bal - rest)
    return top, det


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(a, b):
    return "—" if not b else f"{100 * a / b:.0f}%"


def scan(mid, row, pool):
    p = os.path.join(RUN, f"{mid}.json")
    if not os.path.exists(p):
        return None
    X = json.load(open(p, encoding="utf-8"))
    if "error" in X:
        return dict(matchId=mid, error=X["error"])
    H = X["H"]
    names = [str(x).strip() for x in X["names"]] + [""] * H
    low = [x.lower() for x in names]
    F = facts.full(mid)
    own = {}
    for me, b in F["bots"].items():
        mr = b.get("meReal") if b.get("meReal") is not None else me
        if mr is not None and 0 <= mr < H and any(low[mr].endswith(lab.lower()) for lab in b["labels"]):
            own[mr] = b
    v = X["validate"]
    spawn_only = X["endTick"] <= 1
    valid = bool(own) and ((v["rows"] >= 10 and v["bothExact"] >= 0.9 * v["rows"]) or (spawn_only and len(own) >= 5))
    if not valid:
        own = {}
    grp = {}
    for q in range(H):
        if q in own:
            grp[q] = "own"
        elif "[apex]" in low[q]:
            grp[q] = "apex"
        elif low[q] in pool or re.sub(r"^\[[^\]]*\]\s*", "", low[q]) in pool:
            grp[q] = "pool"
        else:
            grp[q] = "wild"
    # 出生点：最后一条落地的选点；一条选点都没落地的号用开局那一拍它那块地外接框的中心（引擎替它定的位置）
    sb = X.get("startBox") or [None] * H
    xy = [X["spawnXY"][q] or ([(sb[q][0] + sb[q][2]) // 2, (sb[q][1] + sb[q][3]) // 2] if sb[q] else None) for q in range(H)]
    spawned = [q for q in range(H) if xy[q]]
    oc = row.get("outcome") or {}
    rec = dict(matchId=mid, cohort=row.get("cohort"), mode=row.get("mode"), won=bool(oc.get("primaryTeamWon")), label=oc.get("resultLabel"),
               H=H, land=X["land"], endTick=X["endTick"], valid=valid, spawnOnly=spawn_only, rows=v["rows"], exact=v["bothExact"],
               size={g: sum(1 for q in spawned if grp[q] == g) for g in GROUPS}, nTeams=X["nTeams"])

    # ---- 人均对照 ----
    # 在线 = 这一拍还有地、且还没离开（离开后的空壳由引擎的 AI 接管，不算任何一组的人头）
    left_t = X["leftT"]

    def online(q, t, c):
        return c["terr"][q] > 0 and not (0 <= left_t[q] <= t)

    ph = {}
    for t in CP:
        c = X["cp"].get(str(t))
        if not c:
            continue
        cell = {}
        for g in GROUPS + ("bot",):
            sel = [q for q in spawned if (grp[q] == g if g != "bot" else grp[q] != "wild")]
            alive = [q for q in sel if online(q, t, c)]
            cell[g] = dict(n=len(alive), spawned=len(sel), land=sum(c["terr"][q] for q in alive), bal=sum(c["bal"][q] for q in alive))
        ai = X["aiAt"].get(str(t))
        cell["aiLand"] = sum(a[1] for a in ai) if ai is not None else None
        cell["aiN"] = len(ai) if ai is not None else None
        # 分布口径：把每个还有地的真人的地除以「全体还有地的真人的人均地」，再看 own / 野人各自的分位
        allv = [c["terr"][q] for q in spawned if online(q, t, c)]
        if allv:
            mean_all = sum(allv) / len(allv)
            dist = {}
            for g in ("own", "wild"):
                v = sorted(c["terr"][q] / mean_all for q in spawned if grp[q] == g and online(q, t, c))
                if v:
                    dist[g] = dict(n=len(v), q25=v[len(v) // 4], q50=statistics.median(v), q75=v[(3 * len(v)) // 4], q90=v[min(len(v) - 1, (9 * len(v)) // 10)], max=v[-1],
                                   ge2=sum(1 for x in v if x >= 2), lt05=sum(1 for x in v if x < 0.5))
            wv = sorted((c["terr"][q] for q in spawned if grp[q] == "wild" and online(q, t, c)), reverse=True)
            if wv:
                k = max(1, len(wv) // 10)
                dist["wildTop10Share"] = sum(wv[:k]) / sum(wv)
                wmed = statistics.median(wv)
                ov = [c["terr"][q] for q in spawned if grp[q] == "own" and online(q, t, c)]
                dist["ownAboveWildMedian"] = sum(1 for x in ov if x > wmed)
                dist["ownN"] = len(ov)
                # own 的号在全体真人里的名次：前 10% / 前 25% 里有几个
                ranked = sorted(((c["terr"][q], grp[q]) for q in spawned if online(q, t, c)), reverse=True)
                top10, top25 = ranked[:max(1, len(ranked) // 10)], ranked[:max(1, len(ranked) // 4)]
                dist["ownInTop10"] = sum(1 for _, g2 in top10 if g2 == "own")
                dist["top10N"] = len(top10)
                dist["ownInTop25"] = sum(1 for _, g2 in top25 if g2 == "own")
                dist["top25N"] = len(top25)
                dist["aliveN"] = len(ranked)
            cell["dist"] = dist
        ph[t] = cell
    rec["ph"] = ph

    def ratio(t, g, basis="alive"):
        c = ph.get(t)
        if not c:
            return None
        a, w = c[g], c["wild"]
        if a["n"] < 3 or w["n"] < 5:
            return None
        if basis == "alive":
            return (a["land"] / a["n"]) / (w["land"] / w["n"])
        return (a["land"] / a["spawned"]) / (w["land"] / w["spawned"])

    rec["ratio"] = {g: {t: ratio(t, g) for t in CP} for g in ("own", "apex", "pool", "bot")}
    rec["ratioSpawned"] = {g: {t: ratio(t, g, "spawned") for t in CP} for g in ("own", "bot")}
    rec["densRatio"] = {}
    for t in CP:
        c = ph.get(t)
        if c and c["own"]["n"] >= 3 and c["wild"]["n"] >= 5 and c["own"]["land"] and c["wild"]["land"]:
            rec["densRatio"][t] = (c["own"]["bal"] / c["own"]["land"]) / (c["wild"]["bal"] / c["wild"]["land"])

    # ---- 吃地 ----
    win = X["win"]
    gain = X["gain"]

    def harvest(k_list, col):
        # 只算到窗末还没离开的席位（离开后空壳吃的地不算这个组的）
        end = win[max(k_list) + 1]
        return {g: sum(gain[k][q][col] for k in k_list for q in spawned if grp[q] == g and not (0 <= left_t[q] <= end)) for g in GROUPS}

    def heads_at(t0, end):
        c0 = X["cp"].get(str(t0))
        return {g: sum(1 for q in spawned if grp[q] == g and not (0 <= left_t[q] <= end) and (c0["terr"][q] > 0 if c0 else True)) for g in GROUPS}

    rec["heads600_1500"] = heads_at(600, 1500) if X["endTick"] >= 1500 else None
    rec["heads0_600"] = {g: sum(1 for q in spawned if grp[q] == g and not (0 <= left_t[q] <= 600)) for g in GROUPS} if X["endTick"] >= 600 else None

    rec["neutral0_600"] = harvest([0], 2) if X["endTick"] >= 600 else None
    rec["ai600_1500"] = harvest([1, 2, 3], 0) if X["endTick"] >= 1500 else None
    rec["aiBurn600_1500"] = harvest([1, 2, 3], 1) if X["endTick"] >= 1500 else None
    rec["human600_1500"] = harvest([1, 2, 3], 4) if X["endTick"] >= 1500 else None
    rec["lostToHuman600_1500"] = harvest([1, 2, 3], 6) if X["endTick"] >= 1500 else None
    rec["ai1500_1800"] = harvest([4], 0) if X["endTick"] >= 1800 else None
    # 地的收支（600 → 1500，同一批席位：600 拍还有地、到 1500 拍没离开；中途出局的号按 0 格算）
    bd = None
    c6, c15 = X["cp"].get("600"), X["cp"].get("1500")
    if X["endTick"] >= 1500 and c6 and c15:
        bd = {}
        for g in GROUPS:
            sel = [q for q in spawned if grp[q] == g and not (0 <= left_t[q] <= 1500) and c6["terr"][q] > 0]
            bd[g] = dict(heads=len(sel), t600=sum(c6["terr"][q] for q in sel), t1500=sum(c15["terr"][q] for q in sel),
                         b600=sum(c6["bal"][q] for q in sel), b1500=sum(c15["bal"][q] for q in sel),
                         ai=sum(gain[k][q][0] for k in (1, 2, 3) for q in sel), neutral=sum(gain[k][q][2] for k in (1, 2, 3) for q in sel),
                         human=sum(gain[k][q][4] for k in (1, 2, 3) for q in sel), lost=sum(gain[k][q][6] for k in (1, 2, 3) for q in sel),
                         dead=sum(1 for q in sel if c15["terr"][q] <= 0))
    rec["budget600_1500"] = bd

    # ---- 陆攻生效 ----
    per = X["per"]
    cm = []
    for k in range(len(per) - 1):
        if X["endTick"] < per[k + 1]:
            cm.append(None)
            continue
        cell = {}
        for g in GROUPS:
            sel = [q for q in spawned if grp[q] == g]
            cell[g] = dict(seats=len(sel), land=sum(X["cmds"][k][q][0] for q in sel), ok=sum(X["cmds"][k][q][1] for q in sel),
                           t512=sum(X["cmds"][k][q][2] for q in sel), boats=sum(X["cmds"][k][q][3] for q in sel),
                           don=sum(X["cmds"][k][q][4] for q in sel), donOk=sum(X["cmds"][k][q][5] for q in sel))
        cm.append(cell)
    rec["cmds"] = cm
    # 生效陆攻的出手量，按目标分三类：每类 [条数, 派出的兵, Σ 派出 ÷ 发令前余额]
    szs = []
    for k in range(len(per) - 1):
        if X["endTick"] < per[k + 1] or not X.get("size"):
            szs.append(None)
            continue
        cell = {}
        for g in GROUPS:
            acc = [0.0] * 9
            for q in spawned:
                if grp[q] == g:
                    for i in range(9):
                        acc[i] += X["size"][k][q][i]
            cell[g] = acc
        szs.append(cell)
    rec["atkSize"] = szs
    # 一条打内置 AI 的生效陆攻换回多少地（600~1500；和吃地账同一批席位：600 拍还有地、到 1500 拍没离开）
    yl = None
    if X["endTick"] >= 1500 and X.get("size"):
        c0 = X["cp"].get("600")
        yl = {}
        for g in GROUPS:
            sel = [q for q in spawned if grp[q] == g and not (0 <= left_t[q] <= 1500) and (c0["terr"][q] > 0 if c0 else True)]
            yl[g] = dict(heads=len(sel), n=sum(X["size"][1][q][0] for q in sel), troops=sum(X["size"][1][q][1] for q in sel),
                         share=sum(X["size"][1][q][2] for q in sel),
                         cells=sum(gain[k][q][0] for k in (1, 2, 3) for q in sel), burnt=sum(gain[k][q][1] for k in (1, 2, 3) for q in sel),
                         nN=sum(X["size"][1][q][3] for q in sel), troopsN=sum(X["size"][1][q][4] for q in sel),
                         cellsN=sum(gain[k][q][2] for k in (1, 2, 3) for q in sel), burntN=sum(gain[k][q][3] for k in (1, 2, 3) for q in sel))
    rec["yield600_1500"] = yl
    # 逐对账：真人 → 内置 AI（600~1500 里落地的生效陆攻按 [攻方, AI] 合并；同一批席位）
    #   每类 [对数, 生效条数, 派出的兵, 烧掉的兵, 吃到的格, 可吃的格（AI 的地 − 它最大地的 1/4）, 按策略 elimCost 公式估的打垮价, AI 的地, 第一条落在 600~900 / 900~1260 / 1260~1500 的对数]
    #   alone = 这段时间没有别的真人对它下过生效陆攻；mate = 有，而且其中有机器号（本编队 / [APEX] / 名字池）；wild = 有，全是野人
    pr = None
    if X.get("pairs") is not None and X["endTick"] >= 1500:
        c0 = X["cp"].get("600")
        keep = {q for q in spawned if not (0 <= left_t[q] <= 1500) and (c0["terr"][q] > 0 if c0 else True)}
        by_q = defaultdict(list)
        for e in X["pairs"]:
            by_q[e[1]].append(e)
        pr = {g: {c: [0] * 14 for c in ("alone", "mate", "wild")} for g in GROUPS}
        for e in X["pairs"]:
            a_, q, n, sent, t0, t1, cells, burnt, T0, B0q, peak0, _gone = e[:12]
            if a_ not in keep:
                continue
            co = [o for o in by_q[q] if o[0] != a_ and o[4] <= t1 + 90 and o[5] >= t0 - 90]
            cls = "alone" if not co else ("mate" if any(grp.get(o[0]) != "wild" for o in co) else "wild")
            x = min(1, (peak0 // 4) / max(T0, 1))
            acc = pr[grp[a_]][cls]
            for i, v in enumerate((1, n, sent, burnt, cells, max(0, T0 - peak0 // 4), 2 * B0q * (1 - x ** 1.6) + 2 * T0 * (1 - x), T0)):
                acc[i] += v
            acc[8 + (0 if t0 < 900 else 1 if t0 < 1260 else 2)] += 1
            # [11] 续兵条数（落地时已有兵压在这个 AI 身上）；[12] 和上一条同拍落地的条数；[13] 续兵那些条派出的兵
            if len(e) >= 15:
                acc[11] += e[12]
                acc[12] += e[13]
                acc[13] += e[14]
    rec["pairs"] = pr

    # ---- 出生点 ----
    W, Hh = X["W"], X["Hh"]
    lim = round(0.12 * min(W, Hh))
    sp = {g: dict(n=0, nearEdge=0, edge=[], nnBot=0, nnOwn=0, nn=[], picks=[], noPick=0) for g in GROUPS}
    for q in spawned:
        x, y = xy[q]
        e = min(x, y, W - 1 - x, Hh - 1 - y)
        best, bq = None, None
        for r in spawned:
            if r == q:
                continue
            d = math.hypot(xy[r][0] - x, xy[r][1] - y)
            if best is None or d < best:
                best, bq = d, r
        s = sp[grp[q]]
        s["n"] += 1
        s["edge"].append(e)
        s["picks"].append(X["nPicks"][q])
        if X["nPicks"][q] == 0:
            s["noPick"] += 1
        if e <= lim:
            s["nearEdge"] += 1
        if bq is not None:
            s["nn"].append(round(best))
            if grp[bq] != "wild":
                s["nnBot"] += 1
            if grp[bq] == "own":
                s["nnOwn"] += 1
    rec["spawn"] = {g: dict(n=s["n"], nearEdge=s["nearEdge"], edgeMed=med(s["edge"]), nnBot=s["nnBot"], nnOwn=s["nnOwn"], nnMed=med(s["nn"]), picksMed=med(s["picks"]), noPick=s["noPick"]) for g, s in sp.items()}
    rec["edgeLimit"] = lim

    # ---- 出生指派（日志）vs 引擎落点 ----
    # spawn.csv = 日志里 [HL-SPAWN]（本地兜底选点，role 以 RANK_ 开头）和 [HL-SPAWN-BACKEND]（后端协调器）的全部指派行，按日志行号排
    sa = None
    sp_csv = os.path.join(L.DATA, "bundles", mid, "spawn.csv")
    if own and os.path.exists(sp_csv):
        import csv
        seqs = defaultdict(list)
        with open(sp_csv, encoding="utf-8", errors="replace") as f:
            for rw in csv.DictReader(f):
                try:
                    me_i, x_i, y_i, ln = int(rw["me"]), int(rw["x"]), int(rw["y"]), int(rw["line"])
                except (TypeError, ValueError):
                    continue
                b = own.get(me_i)
                if b is None or rw["bot"] not in b["labels"]:
                    continue
                seqs[me_i].append((ln, x_i, y_i, not str(rw.get("role", "")).startswith("RANK_")))
        sa = dict(seats=0, withAssign=0, assigns=0, backend=0, lastExec=0, stale=0, notInLog=0, noPick=0, sameLast=0, lastBackend=0, lastBackendExec=0)
        lasts = []
        for q in own:
            if not xy[q]:
                continue
            sa["seats"] += 1
            seq = sorted(seqs.get(q, []))
            if not seq:
                continue
            sa["withAssign"] += 1
            sa["assigns"] += len(seq)
            sa["backend"] += sum(1 for z in seq if z[3])
            eng = tuple(X["spawnXY"][q]) if X["spawnXY"][q] else None
            last = (seq[-1][1], seq[-1][2])
            lasts.append(last)
            if seq[-1][3]:
                sa["lastBackend"] += 1
            if eng is None:
                sa["noPick"] += 1
            elif eng == last:
                sa["lastExec"] += 1
                if seq[-1][3]:
                    sa["lastBackendExec"] += 1
            elif any((z[1], z[2]) == eng for z in seq):
                sa["stale"] += 1
            else:
                sa["notInLog"] += 1
        cnt = Counter(lasts)
        sa["sameLast"] = sum(v for v in cnt.values() if v >= 2)
    rec["spawnAssign"] = sa

    # ---- 接壤普查 ----
    rc = None
    if X.get("reach"):
        rc = []
        for k in range(len(X["reach"])):
            cell = {}
            for g in GROUPS:
                acc = [0] * 14
                for q in spawned:
                    if grp[q] == g:
                        for i in range(len(X["reach"][k][q])):
                            acc[i] += X["reach"][k][q][i]
                cell[g] = acc
            rc.append(cell)
    rec["reach"] = rc

    # ---- 买 AI 地规则重算（接壤普查里挨着内置 AI 的样本）----
    rule = None
    if X.get("locks") is not None:
        c110 = row.get("cohort") == "squad20"
        is_prot = [grp.get(q) in ("own", "pool") or "[npl]" in low[q] or "[nope]" in low[q] for q in range(H)]

        def src_group(q, t):
            if q is None or q < 0:
                return "none"
            if q >= H:
                return "ai"
            if 0 <= left_t[q] <= t:
                return "shell"
            return grp.get(q, "wild")

        rule = {g: dict(cls={c: [0] * 6 for c in RULE_CLASSES}, sbSrc={k: 0 for k in SRC_GROUPS}, dpSrc={k: 0 for k in SRC_GROUPS},
                        over=dict(px=0, dp=0, sb=0), sole=dict(px=0, dp=0, sb=0), sbShare=[], eng={c: 0 for c in RULE_CLASSES},
                        win=[{c: [0, 0] for c in RULE_CLASSES} for _ in range(3)],
                        # 挨着的内置 AI 有多大（每窗）：[样本, 平均地之和, 最大的那个的地之和, 打垮最便宜的那个的地之和, 挨着的 AI 个数之和（最多记 6 个）, 本号的地之和, 本号的兵之和]
                        adj=[[0] * 7 for _ in range(3)]) for g in GROUPS}
        for rw in X["locks"]:
            t, q = rw[0], rw[1]
            if not xy[q]:
                continue
            g = grp[q]
            if rw[12]:
                av = rule[g]["adj"][0 if t < 900 else 1 if t < 1260 else 2]
                lands = [a[7] for a in rw[12]]
                av[0] += 1
                av[1] += sum(lands) / len(lands)
                av[2] += max(lands)
                av[3] += rw[12][0][7]
                av[4] += len(lands)
                av[5] += rw[6]
                av[6] += rw[5]
            # c110（squad20）的邻居表不含「受保护的队友」（analyze L440 / isProtectedSquadMate L3993-3996）；c116 系只排除同队（引擎那一侧已排除）
            protected = {o for o, _ in rw[11] if is_prot[o]} if (g == "own" and c110) else ()
            # 同一局里各组用同一把尺子（这一局主编队那一档的规则）
            cls, det = rule_eval(rw, protected, c110)
            a = rule[g]["cls"][cls]
            a[0] += 1
            a[1] += rw[4]
            if rw[2]:
                a[2] += 1
                a[3] += rw[4]
                wv = rule[g]["win"][0 if t < 900 else 1 if t < 1260 else 2][cls]
                wv[0] += 1
                wv[1] += rw[4]
            if rw[3]:
                a[4] += 1
                a[5] += rw[4]
            if rw[2] and det["eng"]:
                rule[g]["eng"][cls] += 1
            if rw[2] and cls in ("px", "dp", "sb"):
                rule[g]["over"][cls] += 1 if det["over"] else 0
                rule[g]["sole"][cls] += 1 if det["sole"] else 0
                if cls == "sb":
                    rule[g]["sbSrc"][src_group(det["sbSrc"], t)] += 1
                if cls == "dp":
                    rule[g]["dpSrc"][src_group(det["dpSrc"], t)] += 1
            if rw[2] and g == "own" and rw[5] > 0:
                rule[g]["sbShare"].append(round(det["sb"] / rw[5], 3))
    rec["rule"] = rule

    # ---- 1800 拍前出局 / 离开 ----
    ex = {}
    for g in GROUPS:
        sel = [q for q in spawned if grp[q] == g]
        ex[g] = dict(n=len(sel), dead=sum(1 for q in sel if 0 < X["deathT"][q] <= X["endTick"]), left=sum(1 for q in sel if 0 < X["leftT"][q] <= X["endTick"]),
                     dead900=sum(1 for q in sel if 0 < X["deathT"][q] <= 900))
    rec["exits"] = ex

    # ---- 发出 vs 落地（日志 vs 录像）----
    sp_path = os.path.join(STREAMS, f"{mid}.json")
    fl = []
    if own and os.path.exists(sp_path) and not spawn_only:
        S = json.load(open(sp_path, encoding="utf-8"))
        last = S["meta"]["lastTick"]
        by = defaultdict(list)
        for t, cid, pl, _dx, _dz in S["cmds"]:
            if cid in (1, 2, 3) and pl in own:
                by[pl].append((t, cid))
        don_lines = defaultdict(list)
        for d in F.get("dons", []):
            don_lines[d["donor"]].append(d["t"])
        me_of = {q: me for me, b in F["bots"].items() for q in [b.get("meReal") if b.get("meReal") is not None else me]}
        for name, a, z in LOGPER:
            c = dict(period=name, bots=0, issued=0, boatsLog=0, donLines=0, land=0, don=0, boat=0)
            for q, b in own.items():
                tk = [s for s in b["ticks"] if s["t"] <= min(z, last)]
                if not tk:
                    continue
                s1 = tk[-1]
                s0 = [s for s in tk if s["t"] <= a]
                t0, c0, b0 = (s0[-1]["t"], s0[-1]["cmds"], s0[-1]["boats"]) if s0 else (0, 0, 0)
                if s1["t"] <= t0:
                    continue
                c["bots"] += 1
                c["issued"] += s1["cmds"] - c0
                c["boatsLog"] += s1["boats"] - b0
                c["donLines"] += sum(1 for t in don_lines[me_of.get(q, q)] if t0 < t <= s1["t"])
                for t, cid in by[q]:
                    if t0 < t <= s1["t"]:
                        c["land" if cid == 1 else "don" if cid == 2 else "boat"] += 1
            c["atkIssued"] = c["issued"] - c["boatsLog"] - c["donLines"]
            fl.append(c)
    rec["flow"] = fl
    return rec


def main():
    quiet = "--quiet" in sys.argv
    pool = name_pool()
    ids = discovery_ids()
    recs, failed, noreplay = [], [], 0
    for mid, row in ids:
        if not os.path.exists(os.path.join(L.DATA, "bundles", mid, "replay.txt")):
            noreplay += 1
            continue
        r = scan(mid, row, pool)
        if r is None or "error" in r:
            failed.append((mid, (r or {}).get("error", "没有压缩真值表")))
            continue
        recs.append(r)
    out = []
    P = out.append
    val = [r for r in recs if r["valid"]]
    full = [r for r in val if not r["spawnOnly"]]

    def calm_of(r):
        c = r["cmds"][1] if len(r["cmds"]) > 1 else None
        return bool(c and c["own"]["land"] >= 20 and 1 - c["own"]["ok"] / c["own"]["land"] <= 0.05)

    P(f"[XT-A] 覆盖与核对：发现集 {len(ids)} 局，其中没有录像 {noreplay} 局；有录像 {len(ids) - noreplay} 局里重演成功 {len(recs)} 局、失败 {len(failed)} 局"
      + ("（" + "；".join(f"{m}：{e[-40:]}" for m, e in failed) + "）" if failed else ""))
    P(f"  对得上（重演的地 / 兵和日志快照逐行相等 ≥90%，至少 10 行；或者录像只有出生期而按名字认出 ≥5 个号）：{len(val)} 局；"
      f"其中录像只有出生期（lastTick ≤1）{sum(1 for r in val if r['spawnOnly'])} 局")
    P(f"  对不上、不进 own 统计的：{'、'.join(r['matchId'] + '（' + str(r['exact']) + '/' + str(r['rows']) + '）' for r in recs if not r['valid']) or '无'}")
    rows_t = sum(r["rows"] for r in full)
    exact_t = sum(r["exact"] for r in full)
    P(f"  对得上且有对局段的 {len(full)} 局：日志快照合计 {rows_t} 行，重演的地和兵都逐位相等 {exact_t} 行（{100 * exact_t / max(1, rows_t):.2f}%）")
    P("  录像覆盖到哪一拍（对得上且有对局段的局数）：" + "；".join(f"≥{t} 拍 {sum(1 for r in full if r['endTick'] >= t)} 局" for t in (600, 900, 1260, 1500, 1800)))
    P("  按编队档：" + "；".join(f"{c} 对得上 {sum(1 for r in val if r['cohort'] == c)} 局（到 1500 拍的 {sum(1 for r in full if r['cohort'] == c and r['endTick'] >= 1500)} 局）" for c in COHORTS))
    P(f"  席位合计（出过生的真人）：" + "；".join(f"{GROUP_CN[g]} {sum(r['size'][g] for r in recs)}" for g in GROUPS))

    # ---- [XT-B] ----
    P("")
    P("[XT-B] 人均对照走势（真值；own 还有地的号的人均地 ÷ 野人的人均地）")
    P("  拍 | 局数 | 中位 | 下四分位 ~ 上四分位 | <0.70 的局 | <1.00 的局 || squad10 中位（局数） | squad20 中位（局数） | squad8 中位（局数） || 主队赢的局 中位（局数） | 没赢的局 中位（局数）")
    agg_b = {}
    for t in CP:
        vals = [(r, r["ratio"]["own"][t]) for r in full if r["ratio"]["own"].get(t) is not None]
        if not vals:
            continue
        xs = sorted(v for _, v in vals)
        q1, q3 = xs[len(xs) // 4], xs[(3 * len(xs)) // 4]
        by_c = []
        for c in COHORTS:
            cv = [v for r, v in vals if r["cohort"] == c]
            by_c.append(f"{fmt(med(cv))}（{len(cv)}）")
        wv = [v for r, v in vals if r["won"]]
        lv = [v for r, v in vals if not r["won"]]
        P(f"  {t:>5} | {len(xs)} | {med(xs):.2f} | {q1:.2f} ~ {q3:.2f} | {sum(1 for v in xs if v < 0.7)} | {sum(1 for v in xs if v < 1.0)} || " + " | ".join(by_c)
          + f" || {fmt(med(wv))}（{len(wv)}） | {fmt(med(lv))}（{len(lv)}）")
        agg_b[t] = dict(n=len(xs), median=med(xs), q1=q1, q3=q3, below07=sum(1 for v in xs if v < 0.7), below1=sum(1 for v in xs if v < 1.0),
                        byCohort={c: dict(n=sum(1 for r, v in vals if r["cohort"] == c), median=med([v for r, v in vals if r["cohort"] == c])) for c in COHORTS},
                        won=dict(n=len(wv), median=med(wv)), lost=dict(n=len(lv), median=med(lv)))
    P("  同一张表，按出生人数口径（死掉的号按 0 算）：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratioSpawned']['own'][t] for r in full if r['ratioSpawned']['own'].get(t) is not None]))}" for t in CP))
    P("  机器号合计（own + [APEX] + 名字池）÷ 野人，全部重演成功的局：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratio']['bot'][t] for r in recs if r['ratio']['bot'].get(t) is not None]))}（{sum(1 for r in recs if r['ratio']['bot'].get(t) is not None)} 局）" for t in CP))
    P("  [APEX] 席位（不在 own 里的）÷ 野人：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratio']['apex'][t] for r in recs if r['ratio']['apex'].get(t) is not None]))}（{sum(1 for r in recs if r['ratio']['apex'].get(t) is not None)} 局）" for t in CP))
    P("  名字池席位（不在 own 里的）÷ 野人：" + "；".join(
        f"t={t} 中位 {fmt(med([r['ratio']['pool'][t] for r in recs if r['ratio']['pool'].get(t) is not None]))}（{sum(1 for r in recs if r['ratio']['pool'].get(t) is not None)} 局）" for t in CP))
    P("  兵密度对照（own 的兵 ÷ 地，再 ÷ 野人的同口径）：" + "；".join(
        f"t={t} 中位 {fmt(med([r['densRatio'][t] for r in full if t in r['densRatio']]))}" for t in CP))
    # 分布口径
    P("  分布口径（每个号的地 ÷ 全体还有地的真人的人均地；逐局取分位，再取各局的中位）：拍 | 局数 | own 下四分位 / 中位 / 上四分位 / 九成位 / 最大 | 野人 同口径 | 野人里最大的一成号占野人地的比例 | own 的号高过野人中位的比例 | 前 10% 名次里 own 的占比（own 的人头占比） | 前 25% 里 own 的占比")
    agg_dist = {}
    for t in CP:
        sel = [r for r in full if r["ph"].get(t) and "own" in (r["ph"][t].get("dist") or {}) and "wild" in r["ph"][t]["dist"] and r["ph"][t]["own"]["n"] >= 3 and r["ph"][t]["wild"]["n"] >= 5]
        if not sel:
            continue
        mo = lambda g, k: med([r["ph"][t]["dist"][g][k] for r in sel])  # noqa: E731
        above = sum(r["ph"][t]["dist"]["ownAboveWildMedian"] for r in sel)
        own_n = sum(r["ph"][t]["dist"]["ownN"] for r in sel)
        t10 = sum(r["ph"][t]["dist"]["ownInTop10"] for r in sel)
        t10n = sum(r["ph"][t]["dist"]["top10N"] for r in sel)
        t25 = sum(r["ph"][t]["dist"]["ownInTop25"] for r in sel)
        t25n = sum(r["ph"][t]["dist"]["top25N"] for r in sel)
        alive = sum(r["ph"][t]["dist"]["aliveN"] for r in sel)
        P(f"  {t:>5} | {len(sel)} | {mo('own', 'q25'):.2f} / {mo('own', 'q50'):.2f} / {mo('own', 'q75'):.2f} / {mo('own', 'q90'):.2f} / {mo('own', 'max'):.2f} | "
          f"{mo('wild', 'q25'):.2f} / {mo('wild', 'q50'):.2f} / {mo('wild', 'q75'):.2f} / {mo('wild', 'q90'):.2f} / {mo('wild', 'max'):.2f} | "
          f"{100 * med([r['ph'][t]['dist']['wildTop10Share'] for r in sel]):.0f}% | {pct(above, own_n)} | {pct(t10, t10n)}（{pct(own_n, alive)}） | {pct(t25, t25n)}")
        agg_dist[t] = dict(n=len(sel), ownQ50=mo("own", "q50"), wildQ50=mo("wild", "q50"), ownQ90=mo("own", "q90"), wildQ90=mo("wild", "q90"), ownMax=mo("own", "max"), wildMax=mo("wild", "max"),
                           wildTop10Share=med([r["ph"][t]["dist"]["wildTop10Share"] for r in sel]), ownAboveWildMedian=above, ownN=own_n,
                           ownInTop10=t10, top10N=t10n, ownInTop25=t25, top25N=t25n, aliveN=alive)
    big = sum(r["ph"][1500]["dist"]["own"]["ge2"] for r in full if r["ph"].get(1500) and "own" in (r["ph"][1500].get("dist") or {}))
    bign = sum(r["ph"][1500]["dist"]["own"]["n"] for r in full if r["ph"].get(1500) and "own" in (r["ph"][1500].get("dist") or {}))
    wbig = sum(r["ph"][1500]["dist"]["wild"]["ge2"] for r in full if r["ph"].get(1500) and "wild" in (r["ph"][1500].get("dist") or {}))
    wbign = sum(r["ph"][1500]["dist"]["wild"]["n"] for r in full if r["ph"].get(1500) and "wild" in (r["ph"][1500].get("dist") or {}))
    sm = sum(r["ph"][1500]["dist"]["own"]["lt05"] for r in full if r["ph"].get(1500) and "own" in (r["ph"][1500].get("dist") or {}))
    wsm = sum(r["ph"][1500]["dist"]["wild"]["lt05"] for r in full if r["ph"].get(1500) and "wild" in (r["ph"][1500].get("dist") or {}))
    P(f"  t=1500：地 ≥ 全体人均 2 倍的号——own {big}/{bign}（{pct(big, bign)}），野人 {wbig}/{wbign}（{pct(wbig, wbign)}）；地 < 全体人均一半的号——own {sm}/{bign}（{pct(sm, bign)}），野人 {wsm}/{wbign}（{pct(wsm, wbign)}）")
    # 掉队
    both = [r for r in full if r["ratio"]["own"].get(630) is not None and r["ratio"]["own"].get(1500) is not None]
    drop = [r for r in both if r["ratio"]["own"][630] >= 0.9 and r["ratio"]["own"][1500] <= 0.75 * r["ratio"]["own"][630]]
    fall = [r for r in both if r["ratio"]["own"][1500] < r["ratio"]["own"][630]]
    low630 = [r for r in both if r["ratio"]["own"][630] < 0.9]
    P(f"  掉队（t=630 时 ≥0.90 且 t=1500 时 ≤ 630 时的 0.75 倍）：两拍都有数的 {len(both)} 局里 {len(drop)} 局命中；t=1500 比 t=630 低的 {len(fall)} 局；"
      f"t=630 时就 <0.90 的 {len(low630)} 局")
    P("    按编队档：" + "；".join(f"{c} {sum(1 for r in drop if r['cohort'] == c)}/{sum(1 for r in both if r['cohort'] == c)}" for c in COHORTS)
      + f"｜主队赢的局 {sum(1 for r in drop if r['won'])}/{sum(1 for r in both if r['won'])}，没赢的局 {sum(1 for r in drop if not r['won'])}/{sum(1 for r in both if not r['won'])}")
    rr = [r["ratio"]["own"][1500] / r["ratio"]["own"][630] for r in both]
    P(f"    t=1500 ÷ t=630 的比值：中位 {fmt(med(rr))}，下四分位 {fmt(sorted(rr)[len(rr) // 4]) if rr else '—'}，上四分位 {fmt(sorted(rr)[(3 * len(rr)) // 4]) if rr else '—'}；"
      f"没掉的局（比值 ≥1）：{'、'.join(r['matchId'] for r in both if r['ratio']['own'][1500] >= r['ratio']['own'][630]) or '无'}")
    by_h = []
    for lo, hi, nm in ((0, 30, "≤30 席"), (31, 60, "31~60 席"), (61, 90, "61~90 席"), (91, 999, "≥91 席")):
        sel = [r for r in both if lo <= r["H"] <= hi]
        by_h.append(f"{nm} {sum(1 for r in sel if r in drop)}/{len(sel)}（1500 拍中位 {fmt(med([r['ratio']['own'][1500] for r in sel]))}）")
    P("    按房间真人数：" + "；".join(by_h))

    # ---- [XT-C] ----
    P("")
    P("[XT-C] 地是谁吃的（真值）")
    hv = [r for r in full if r["ai600_1500"] is not None and r["heads600_1500"]["own"] >= 3 and r["heads600_1500"]["wild"] >= 5]
    tot = {g: sum(r["ai600_1500"][g] for r in hv) for g in GROUPS}
    heads = {g: sum(r["heads600_1500"][g] for r in hv) for g in GROUPS}
    burn = {g: sum(r["aiBurn600_1500"][g] for r in hv) for g in GROUPS}
    allc, allh = sum(tot.values()), sum(heads.values())
    P(f"  (600,1500] 真人从内置 AI 手里吃下的格（{len(hv)} 局合计 {allc} 格；人头 = t=600 还有地、到 1500 拍没离开的真人 {allh} 个；中途离开的席位连人带地都不算）：")
    for g in GROUPS:
        P(f"    {GROUP_CN[g]}：{tot[g]} 格（{pct(tot[g], allc)}）｜人头 {heads[g]}（{pct(heads[g], allh)}）｜人均 {tot[g] / max(1, heads[g]):.0f} 格｜每格烧 {burn[g] / max(1, tot[g]):.1f} 兵")
    sr = []
    for r in hv:
        a = sum(r["ai600_1500"].values())
        h = sum(r["heads600_1500"][g] for g in GROUPS)
        if a > 0:
            sr.append((r, (r["ai600_1500"]["own"] / a) / (r["heads600_1500"]["own"] / h)))
    xs = sorted(v for _, v in sr)
    P(f"  逐局的份额对照（own 的份额 ÷ own 的人头份额）：{len(xs)} 局，中位 {fmt(med(xs))}，下四分位 {fmt(xs[len(xs) // 4]) if xs else '—'}，上四分位 {fmt(xs[(3 * len(xs)) // 4]) if xs else '—'}；"
      f"<0.70 的 {sum(1 for v in xs if v < 0.7)} 局，<1.00 的 {sum(1 for v in xs if v < 1.0)} 局")
    P("    按编队档：" + "；".join(f"{c} 中位 {fmt(med([v for r, v in sr if r['cohort'] == c]))}（{sum(1 for r, v in sr if r['cohort'] == c)} 局）" for c in COHORTS)
      + f"｜主队赢的局 中位 {fmt(med([v for r, v in sr if r['won']]))}（{sum(1 for r, v in sr if r['won'])}），没赢的局 {fmt(med([v for r, v in sr if not r['won']]))}（{sum(1 for r, v in sr if not r['won'])}）")
    hu = {g: sum(r["human600_1500"][g] for r in hv) for g in GROUPS}
    lo = {g: sum(r["lostToHuman600_1500"][g] for r in hv) for g in GROUPS}
    P("  同窗真人之间：" + "；".join(f"{GROUP_CN[g]} 从真人手里吃 {hu[g]} 格、被真人吃走 {lo[g]} 格（人均净 {(hu[g] - lo[g]) / max(1, heads[g]):+.0f}）" for g in GROUPS))
    nv = [r for r in full if r["neutral0_600"] is not None and r["heads0_600"]["own"] >= 3 and r["heads0_600"]["wild"] >= 5]
    ntot = {g: sum(r["neutral0_600"][g] for r in nv) for g in GROUPS}
    nheads = {g: sum(r["heads0_600"][g] for r in nv) for g in GROUPS}
    P(f"  (0,600] 真人吃下的无主地（{len(nv)} 局；人头 = 出过生、到 600 拍没离开的真人）：" + "；".join(
        f"{GROUP_CN[g]} {ntot[g]} 格（{pct(ntot[g], sum(ntot.values()))}）/ 人头 {nheads[g]}（{pct(nheads[g], sum(nheads.values()))}）/ 人均 {ntot[g] / max(1, nheads[g]):.0f}" for g in GROUPS))
    ai_left = [(r["ph"][t]["aiLand"] / r["land"]) for r in full for t in (600,) if r["ph"].get(t) and r["ph"][t]["aiLand"] is not None]
    ai_left15 = [(r["ph"][1500]["aiLand"] / r["land"]) for r in full if r["ph"].get(1500) and r["ph"][1500]["aiLand"] is not None]
    P(f"  内置 AI 的地占全图陆地：t=600 中位 {100 * med(ai_left):.1f}%（{len(ai_left)} 局），t=1500 中位 {100 * med(ai_left15):.1f}%（{len(ai_left15)} 局）")

    # 地的收支
    bsel = [r for r in full if r.get("budget600_1500")]
    P(f"  地的收支（600 → 1500，人均；{len(bsel)} 局；人头 = t=600 还有地、到 1500 拍没离开的席位，中途出局的按 0 格算）：")
    P("    范围 | 组 | 人头 | t=600 人均地 | t=1500 人均地 | 净增 | 从内置 AI 吃 | 从无主地吃 | 从真人吃 | 被真人吃走 | 其余（被 AI 吃走、出局时变成无主地等） | t=600 人均兵 | t=1500 人均兵 | 这批人里 1500 拍前出局的")
    agg_bd = {}
    for nm, sel in (("全部", bsel), ("几乎不卡的局", [r for r in bsel if calm_of(r)]), ("其余的局", [r for r in bsel if not calm_of(r)]),
                    ("squad10", [r for r in bsel if r["cohort"] == "squad10"]), ("squad20", [r for r in bsel if r["cohort"] == "squad20"])):
        for g in ("own", "wild"):
            a = {k: sum(r["budget600_1500"][g][k] for r in sel) for k in ("heads", "t600", "t1500", "b600", "b1500", "ai", "neutral", "human", "lost", "dead")}
            h = a["heads"]
            if not h:
                continue
            net = a["t1500"] - a["t600"]
            rest = net - (a["ai"] + a["neutral"] + a["human"] - a["lost"])
            P(f"    {nm} | {GROUP_CN[g]} | {h} | {a['t600'] / h:.0f} | {a['t1500'] / h:.0f} | {net / h:+.0f} | {a['ai'] / h:.0f} | {a['neutral'] / h:.0f} | {a['human'] / h:.0f} | {-a['lost'] / h:.0f} | {rest / h:+.0f} | "
              f"{a['b600'] / h:.0f} | {a['b1500'] / h:.0f} | {a['dead']}（{pct(a['dead'], h)}）")
            agg_bd[f"{nm}|{g}"] = a
        o, w = agg_bd.get(f"{nm}|own"), agg_bd.get(f"{nm}|wild")
        if o and w:
            go = (o["t1500"] - o["t600"]) / o["heads"]
            gw = (w["t1500"] - w["t600"]) / w["heads"]
            parts = []
            for k, kn in (("ai", "内置 AI"), ("neutral", "无主地"), ("human", "从真人吃"), ("lost", "被真人吃走")):
                dv = (w[k] / w["heads"] - o[k] / o["heads"]) * (-1 if k == "lost" else 1)
                parts.append(f"{kn} {dv:+.0f}（{100 * dv / (gw - go):.0f}%）" if gw != go else f"{kn} {dv:+.0f}")
            P(f"      {nm}：野人人均净增比 own 多 {gw - go:.0f} 格，拆开：" + "；".join(parts))
        # 逐局口径（上面是各局人头相加；大地图小房间的局人均地大，会把合计往上带）
        pmb = []
        for r in sel:
            o, w = r["budget600_1500"]["own"], r["budget600_1500"]["wild"]
            if o["heads"] < 3 or w["heads"] < 5:
                continue
            go = (o["t1500"] - o["t600"]) / o["heads"]
            gw = (w["t1500"] - w["t600"]) / w["heads"]
            if gw <= 0:
                continue
            dai = w["ai"] / w["heads"] - o["ai"] / o["heads"]
            dn = w["neutral"] / w["heads"] - o["neutral"] / o["heads"]
            dh = (w["human"] - w["lost"]) / w["heads"] - (o["human"] - o["lost"]) / o["heads"]
            pmb.append((go / gw, (gw - go) / gw, dai / gw, dn / gw, dh / gw, (o["ai"] / o["heads"]) / max(1e-9, w["ai"] / w["heads"]),
                        (o["neutral"] / o["heads"]) / max(1e-9, w["neutral"] / w["heads"])))
        if pmb:
            P(f"      {nm}·逐局（own ≥3 人头、野人 ≥5 人头的 {len(pmb)} 局；每局先各自算人均，再取各局的中位）：own 人均净增 ÷ 野人人均净增 中位 {med([x[0] for x in pmb]):.2f}；"
              f"差额占野人净增 中位 {100 * med([x[1] for x in pmb]):.0f}%，其中 内置 AI {100 * med([x[2] for x in pmb]):.0f}%、无主地 {100 * med([x[3] for x in pmb]):.0f}%、真人之间的净额 {100 * med([x[4] for x in pmb]):.0f}%；"
              f"own 人均从内置 AI 吃到的 ÷ 野人的 中位 {med([x[5] for x in pmb]):.2f}（<1 的 {sum(1 for x in pmb if x[5] < 1)} 局）；从无主地吃到的 ÷ 野人的 中位 {med([x[6] for x in pmb]):.2f}（<1 的 {sum(1 for x in pmb if x[6] < 1)} 局）")
            agg_bd[f"{nm}|perMatch"] = dict(n=len(pmb), gainRatio=med([x[0] for x in pmb]), gapShare=med([x[1] for x in pmb]), ai=med([x[2] for x in pmb]),
                                           neutral=med([x[3] for x in pmb]), human=med([x[4] for x in pmb]), aiRatio=med([x[5] for x in pmb]), neutralRatio=med([x[6] for x in pmb]))

    # 一条陆攻换回多少地
    ysel = [r for r in full if r.get("yield600_1500")]
    P(f"  一条打内置 AI 的生效陆攻换回多少地（600~1500；{len(ysel)} 局；和上面吃地账同一批席位）：组 | 人头 | 人均生效条数 | 每条派出的兵 | 每条派出占余额 | 每条吃到的格 | 人均派出的兵 | 派出的兵 ÷ 吃到的格 | 烧掉的兵 ÷ 吃到的格 | 烧掉 ÷ 派出")
    agg_y = {}
    for g in GROUPS:
        a = {k: sum(r["yield600_1500"][g][k] for r in ysel) for k in ("heads", "n", "troops", "share", "cells", "burnt", "nN", "troopsN", "cellsN", "burntN")}
        if not a["heads"] or not a["n"]:
            continue
        P(f"    {GROUP_CN[g]} | {a['heads']} | {a['n'] / a['heads']:.1f} | {a['troops'] / a['n']:.0f} | {100 * a['share'] / a['n']:.1f}% | {a['cells'] / a['n']:.0f} | {a['troops'] / a['heads']:.0f} | "
          f"{a['troops'] / max(1, a['cells']):.1f} | {a['burnt'] / max(1, a['cells']):.1f} | {pct(a['burnt'], a['troops'])}")
        agg_y[g] = a
    P("  同一批席位打无主地（600~1500）：组 | 人均生效条数 | 每条派出的兵 | 每条吃到的格 | 派出的兵 ÷ 吃到的格 | 烧掉 ÷ 派出")
    for g in GROUPS:
        a = agg_y.get(g)
        if a and a["nN"]:
            P(f"    {GROUP_CN[g]} | {a['nN'] / a['heads']:.1f} | {a['troopsN'] / a['nN']:.0f} | {a['cellsN'] / a['nN']:.0f} | {a['troopsN'] / max(1, a['cellsN']):.1f} | {pct(a['burntN'], a['troopsN'])}")
    pmy = []
    for r in ysel:
        o, w = r["yield600_1500"]["own"], r["yield600_1500"]["wild"]
        if o["heads"] >= 3 and w["heads"] >= 5 and o["n"] >= 20 and w["n"] >= 20:
            pmy.append((r, (o["n"] / o["heads"]) / (w["n"] / w["heads"]), (o["cells"] / o["n"]) / (w["cells"] / w["n"]), (o["troops"] / o["n"]) / (w["troops"] / w["n"]),
                        (o["burnt"] / max(1, o["troops"])), (w["burnt"] / max(1, w["troops"]))))
    P(f"  逐局（own 和野人各 ≥20 条的 {len(pmy)} 局），own ÷ 野人：人均生效条数 中位 {med([x[1] for x in pmy]):.2f}（<1 的 {sum(1 for x in pmy if x[1] < 1)} 局）；"
      f"每条吃到的格 中位 {med([x[2] for x in pmy]):.2f}（<1 的 {sum(1 for x in pmy if x[2] < 1)} 局）；每条派出的兵 中位 {med([x[3] for x in pmy]):.2f}（<1 的 {sum(1 for x in pmy if x[3] < 1)} 局）；"
      f"烧掉 ÷ 派出：own 中位 {100 * med([x[4] for x in pmy]):.0f}%，野人 中位 {100 * med([x[5] for x in pmy]):.0f}%")
    for nm, sel in (("几乎不卡的局", [x for x in pmy if calm_of(x[0])]), ("其余的局", [x for x in pmy if not calm_of(x[0])])):
        if sel:
            P(f"    {nm}（{len(sel)} 局）：人均生效条数 中位 {med([x[1] for x in sel]):.2f}；每条吃到的格 中位 {med([x[2] for x in sel]):.2f}；每条派出的兵 中位 {med([x[3] for x in sel]):.2f}；"
              f"烧掉 ÷ 派出：own 中位 {100 * med([x[4] for x in sel]):.0f}%，野人 中位 {100 * med([x[5] for x in sel]):.0f}%")

    # 逐对账
    psel = [r for r in full if r.get("pairs") and r.get("yield600_1500")]
    P(f"  逐对账（600~1500；{len(psel)} 局；把每个号对同一个内置 AI 的生效陆攻合成一对）：")
    P("    组 | 类 | 对数 | 人均对数 | 每对条数 | 每对派出的兵 | 派出 ÷ 打垮价（elimCost 公式按第一条落地前的 AI 状态估） | 烧掉 ÷ 派出 | 每对吃到的格 | 吃到 ÷ 可吃 | 第一条落地前 AI 的地")
    agg_p = {}
    PCN = dict(alone="独吃", mate="和机器号同吃", wild="和野人同吃", all="合计")

    def pair_sum(sel, g, c):
        cs = ("alone", "mate", "wild") if c == "all" else (c,)
        return [sum(r["pairs"][g][k][i] for r in sel for k in cs) for i in range(14)]

    def pair_rows(nm, sel, groups=GROUPS, classes=("alone", "mate", "wild", "all")):
        for g in groups:
            heads = sum(r["yield600_1500"][g]["heads"] for r in sel)
            for c in classes:
                a = pair_sum(sel, g, c)
                if not a[0] or not heads:
                    continue
                P(f"    {nm}{GROUP_CN[g]} | {PCN[c]} | {a[0]} | {a[0] / heads:.2f} | {a[1] / a[0]:.2f} | {a[2] / a[0]:.0f} | {a[2] / max(1, a[6]):.2f} | {pct(a[3], a[2])} | {a[4] / a[0]:.0f} | {pct(a[4], a[5])} | {a[7] / a[0]:.0f}")
                agg_p[f"{nm}{g}|{c}"] = dict(heads=heads, pairs=a[0], cmds=a[1], sent=a[2], burnt=a[3], cells=a[4], capturable=a[5], need=round(a[6]), aiLand=a[7], byWin=a[8:11])

    pair_rows("", psel)
    P("    分开看（合计行）：")
    pair_rows("几乎不卡的局·", [r for r in psel if calm_of(r)], ("own", "wild"), ("all",))
    pair_rows("其余的局·", [r for r in psel if not calm_of(r)], ("own", "wild"), ("all",))
    pair_rows("squad10·", [r for r in psel if r["cohort"] == "squad10"], ("own", "wild"), ("all",))
    pair_rows("squad20·", [r for r in psel if r["cohort"] == "squad20"], ("own", "wild"), ("all",))
    P("    续兵和同拍重复（打内置 AI 的生效陆攻）：组 | 条数 | 落地时已有兵压在这个 AI 身上的（续兵）| 续兵派出的兵占全部派出 | 和这一对的上一条同拍落地的 | 每对里第 2 条起的条数占比")
    for nm, sel in (("", psel), ("几乎不卡的局·", [r for r in psel if calm_of(r)]), ("其余的局·", [r for r in psel if not calm_of(r)]),
                    ("squad10·", [r for r in psel if r["cohort"] == "squad10"]), ("squad20·", [r for r in psel if r["cohort"] == "squad20"])):
        for g in (GROUPS if not nm else ("own", "wild")):
            a = pair_sum(sel, g, "all")
            if a[1]:
                P(f"    {nm}{GROUP_CN[g]} | {a[1]} | {a[11]}（{pct(a[11], a[1])}）| {pct(a[13], a[2])} | {a[12]}（{pct(a[12], a[1])}）| {pct(a[1] - a[0], a[1])}")
                agg_p[f"dup|{nm}{g}"] = dict(cmds=a[1], reinforce=a[11], reinforceTroops=a[13], sent=a[2], sameTick=a[12], pairs=a[0])
    P("    第一条落在哪一段（人均对数）：组 | 600~900 | 900~1260 | 1260~1500")
    for g in ("own", "wild"):
        heads = sum(r["yield600_1500"][g]["heads"] for r in psel)
        a = pair_sum(psel, g, "all")
        P(f"    {GROUP_CN[g]} | {a[8] / heads:.2f} | {a[9] / heads:.2f} | {a[10] / heads:.2f}")
    pmp = []
    for r in psel:
        ho, hw = r["yield600_1500"]["own"]["heads"], r["yield600_1500"]["wild"]["heads"]
        o, w = pair_sum([r], "own", "all"), pair_sum([r], "wild", "all")
        if ho >= 3 and hw >= 5 and o[0] >= 10 and w[0] >= 10:
            pmp.append((r, (o[0] / ho) / (w[0] / hw), (o[4] / o[0]) / (w[4] / w[0]), (o[7] / o[0]) / (w[7] / w[0]), o[1] / o[0], w[1] / w[0]))
    P(f"    逐局（own 和野人各 ≥10 对的 {len(pmp)} 局），own ÷ 野人：人均对数 中位 {med([x[1] for x in pmp]):.2f}（<1 的 {sum(1 for x in pmp if x[1] < 1)} 局）；每对吃到的格 中位 {med([x[2] for x in pmp]):.2f}"
      f"（<1 的 {sum(1 for x in pmp if x[2] < 1)} 局）；下手时 AI 的地 中位 {med([x[3] for x in pmp]):.2f}（<1 的 {sum(1 for x in pmp if x[3] < 1)} 局）；每对条数 own 中位 {med([x[4] for x in pmp]):.2f}、野人 中位 {med([x[5] for x in pmp]):.2f}")

    # ---- [XT-D] ----
    P("")
    P("[XT-D] 陆攻落地后有没有生效（真值；录像里落地的陆攻指令）：时段 | 组 | 局数 | 落地 | 生效 | 没生效占比 | 目标 512 占比 | 每席位落地条数")
    agg_d = {}
    for k, nm in enumerate(("0~600", "600~1500", "1500~1800")):
        for g in GROUPS:
            sel = [r for r in (full if g == "own" else recs) if r["cmds"][k] is not None and r["cmds"][k][g]["seats"] > 0]
            land = sum(r["cmds"][k][g]["land"] for r in sel)
            ok = sum(r["cmds"][k][g]["ok"] for r in sel)
            t512 = sum(r["cmds"][k][g]["t512"] for r in sel)
            seats = sum(r["cmds"][k][g]["seats"] for r in sel)
            P(f"  {nm} | {GROUP_CN[g]} | {len(sel)} | {land} | {ok} | {pct(land - ok, land)} | {pct(t512, land)} | {land / max(1, seats):.1f}")
            agg_d[f"{nm}|{g}"] = dict(matches=len(sel), landed=land, effective=ok, t512=t512, seats=seats)
    pm = []
    for r in full:
        c = r["cmds"][1]
        if c and c["own"]["land"] >= 20 and c["wild"]["land"] >= 20:
            pm.append((r, 1 - c["own"]["ok"] / c["own"]["land"], 1 - c["wild"]["ok"] / c["wild"]["land"]))
    P(f"  逐局（600~1500，own 和野人各 ≥20 条陆攻的 {len(pm)} 局）：own 没生效占比 中位 {100 * med([a for _, a, _ in pm]):.0f}%，野人 中位 {100 * med([b for _, _, b in pm]):.0f}%；"
      f"own 比野人高的 {sum(1 for _, a, b in pm if a > b)} 局；own ≥20% 的 {sum(1 for _, a, _ in pm if a >= 0.2)} 局，野人 ≥20% 的 {sum(1 for _, _, b in pm if b >= 0.2)} 局")
    P("    按编队档（own 没生效占比的中位）：" + "；".join(f"{c} {fmt(100 * med([a for r, a, _ in pm if r['cohort'] == c]) if [a for r, a, _ in pm if r['cohort'] == c] else None, 0)}%（{sum(1 for r, _, _ in pm if r['cohort'] == c)} 局）" for c in COHORTS))

    P("  生效的陆攻每条派多少（真值）：时段 | 组 | 打内置 AI：条数 / 每条派出占余额的平均 / 每条平均兵 | 打无主地：同口径 | 打真人：同口径 | 三类条数之比")
    agg_sz = {}
    for k, nm in enumerate(("0~600", "600~1500", "1500~1800")):
        for g in GROUPS:
            sel = [r for r in (full if g == "own" else recs) if r["atkSize"][k] is not None]
            acc = [sum(r["atkSize"][k][g][i] for r in sel) for i in range(9)]
            if not (acc[0] + acc[3] + acc[6]):
                continue
            cells = []
            for o in (0, 3, 6):
                cells.append(f"{acc[o]:.0f} / {100 * acc[o + 2] / max(1, acc[o]):.1f}% / {acc[o + 1] / max(1, acc[o]):.0f}")
            tot_n = acc[0] + acc[3] + acc[6]
            P(f"  {nm} | {GROUP_CN[g]} | " + " | ".join(cells) + f" | {100 * acc[0] / tot_n:.0f} : {100 * acc[3] / tot_n:.0f} : {100 * acc[6] / tot_n:.0f}")
            agg_sz[f"{nm}|{g}"] = dict(ai=acc[0:3], neutral=acc[3:6], human=acc[6:9])
    szm = []
    for r in full:
        c = r["atkSize"][1] if len(r["atkSize"]) > 1 else None
        if c and c["own"][0] >= 20 and c["wild"][0] >= 20:
            szm.append((r, c["own"][2] / c["own"][0], c["wild"][2] / c["wild"][0]))
    P(f"  逐局（600~1500，own 和野人各 ≥20 条打 AI 的生效陆攻，{len(szm)} 局）：每条派出占余额——own 中位 {100 * med([a for _, a, _ in szm]):.1f}%，野人 中位 {100 * med([b for _, _, b in szm]):.1f}%；own 比野人小的 {sum(1 for _, a, b in szm if a < b)} 局")

    # ---- [XT-E] ----
    P("")
    P("[XT-E] 出生点（真值落点；全部重演成功的局，own 只算对得上的局）：组 | 席位 | 贴边（≤ 短边 12%） | 最近的真人是机器号 | 最近的真人是 own | 离边中位的中位 | 最近真人距离中位的中位 | 选点条数中位的中位 | 一条选点都没落地的席位")
    agg_e = {}
    for g in GROUPS:
        sel = [r for r in recs if r["spawn"][g]["n"] > 0]
        n = sum(r["spawn"][g]["n"] for r in sel)
        ne = sum(r["spawn"][g]["nearEdge"] for r in sel)
        nb = sum(r["spawn"][g]["nnBot"] for r in sel)
        no = sum(r["spawn"][g]["nnOwn"] for r in sel)
        P(f"  {GROUP_CN[g]} | {n}（{len(sel)} 局） | {ne}（{pct(ne, n)}） | {nb}（{pct(nb, n)}） | {no}（{pct(no, n)}） | {fmt(med([r['spawn'][g]['edgeMed'] for r in sel]), 0)} | "
          f"{fmt(med([r['spawn'][g]['nnMed'] for r in sel if r['spawn'][g]['nnMed'] is not None]), 0)} | {fmt(med([r['spawn'][g]['picksMed'] for r in sel]), 1)} | "
          f"{sum(r['spawn'][g]['noPick'] for r in sel)}（{pct(sum(r['spawn'][g]['noPick'] for r in sel), n)}；{sum(1 for r in sel if r['spawn'][g]['noPick'])} 局）")
        agg_e[g] = dict(seats=n, matches=len(sel), nearEdge=ne, nnBot=nb, nnOwn=no, noPick=sum(r["spawn"][g]["noPick"] for r in sel))
    for c in COHORTS:
        sel = [r for r in val if r["cohort"] == c and r["spawn"]["own"]["n"] > 0]
        n = sum(r["spawn"]["own"]["n"] for r in sel)
        ne = sum(r["spawn"]["own"]["nearEdge"] for r in sel)
        no = sum(r["spawn"]["own"]["nnBot"] for r in sel)
        wn = sum(r["spawn"]["wild"]["n"] for r in sel)
        we = sum(r["spawn"]["wild"]["nearEdge"] for r in sel)
        P(f"    {c}：own {n} 席（{len(sel)} 局）贴边 {pct(ne, n)}、最近的真人是机器号 {pct(no, n)}｜同局野人 {wn} 席贴边 {pct(we, wn)}")
    more = [r for r in val if r["spawn"]["own"]["n"] >= 3 and r["spawn"]["wild"]["n"] >= 5]
    P(f"  逐局（own ≥3 席、野人 ≥5 席的 {len(more)} 局）：own 贴边比例高过同局野人的 {sum(1 for r in more if r['spawn']['own']['nearEdge'] / r['spawn']['own']['n'] > r['spawn']['wild']['nearEdge'] / r['spawn']['wild']['n'])} 局；"
      f"own 的最近真人距离中位比野人小的 {sum(1 for r in more if (r['spawn']['own']['nnMed'] or 0) < (r['spawn']['wild']['nnMed'] or 0))} 局")
    # 贴边和 1500 拍人均对照
    e_hi = [r["ratio"]["own"][1500] for r in both if r["spawn"]["own"]["n"] and r["spawn"]["own"]["nearEdge"] / r["spawn"]["own"]["n"] >= 0.5]
    e_lo = [r["ratio"]["own"][1500] for r in both if r["spawn"]["own"]["n"] and r["spawn"]["own"]["nearEdge"] / r["spawn"]["own"]["n"] < 0.5]
    P(f"  own 贴边 ≥50% 的局：t=1500 人均对照中位 {fmt(med(e_hi))}（{len(e_hi)} 局）；<50% 的局：{fmt(med(e_lo))}（{len(e_lo)} 局）")

    P("  出生指派（日志 spawn.csv）vs 引擎落点（own 席位）：档 | 局 | 有指派的席位 | 人均指派条数（其中后端协调器的占比） | 最后一条指派被执行 | 落点是更早的某条指派 | 落点不在指派里 | 一条选点都没落地 | 最后一条指派和别的编队号撞同一个点的席位")
    agg_sa = {}
    for nm, sel in (("全部", val), ("squad10", [r for r in val if r["cohort"] == "squad10"]), ("squad20", [r for r in val if r["cohort"] == "squad20"]),
                    ("主队赢的局", [r for r in val if r["won"]]), ("没赢的局", [r for r in val if not r["won"]])):
        sel = [r for r in sel if r.get("spawnAssign") and r["spawnAssign"]["withAssign"]]
        if not sel:
            continue
        a = {k: sum(r["spawnAssign"][k] for r in sel) for k in sel[0]["spawnAssign"]}
        w = a["withAssign"]
        P(f"  {nm} | {len(sel)} | {w} | {a['assigns'] / max(1, w):.1f}（{pct(a['backend'], a['assigns'])}） | {a['lastExec']}（{pct(a['lastExec'], w)}） | {a['stale']}（{pct(a['stale'], w)}） | "
          f"{a['notInLog']}（{pct(a['notInLog'], w)}） | {a['noPick']}（{pct(a['noPick'], w)}） | {a['sameLast']}（{pct(a['sameLast'], w)}）")
        agg_sa[nm] = a
    pme = [(r, r["spawnAssign"]["lastExec"] / r["spawnAssign"]["withAssign"]) for r in val if r.get("spawnAssign") and r["spawnAssign"]["withAssign"] >= 3]
    P(f"  逐局（有指派的 own 席位 ≥3 的 {len(pme)} 局）：最后一条指派被执行的比例 中位 {100 * med([v for _, v in pme]):.0f}%；全部执行的 {sum(1 for _, v in pme if v >= 0.999)} 局；不到一半的 {sum(1 for _, v in pme if v < 0.5)} 局")
    hi = [r["ratio"]["own"].get(1500) for r, v in pme if v >= 0.5 and r["ratio"]["own"].get(1500) is not None]
    lo2 = [r["ratio"]["own"].get(1500) for r, v in pme if v < 0.5 and r["ratio"]["own"].get(1500) is not None]
    P(f"  最后一条指派执行 ≥50% 的局：t=1500 人均对照中位 {fmt(med(hi))}（{len(hi)} 局）；<50% 的局：{fmt(med(lo2))}（{len(lo2)} 局）")
    hi = [r["ratio"]["own"].get(630) for r, v in pme if v >= 0.5 and r["ratio"]["own"].get(630) is not None]
    lo2 = [r["ratio"]["own"].get(630) for r, v in pme if v < 0.5 and r["ratio"]["own"].get(630) is not None]
    P(f"  同上，t=630 人均对照中位：执行 ≥50% 的局 {fmt(med(hi))}（{len(hi)} 局）；<50% 的局 {fmt(med(lo2))}（{len(lo2)} 局）")

    # ---- [XT-F] ----
    P("")
    P("[XT-F] 发出 vs 落地（日志 vs 录像，own 席位）")
    P("  陆攻：日志 = cmds 增量 − boats 增量 − 同段的捐款日志行；录像 = 落地的陆攻指令")
    P("  时段 | 局数 | 号 | 日志发出的陆攻 | 录像落地的陆攻 | 落地 ÷ 发出 | 逐局比值的中位 | <0.70 的局 | >1.00 的局 || squad10 | squad20 || 主队赢的局 | 没赢的局")
    agg_f = {}

    def ratio_of(sel, i, num, den):
        return pct(sum(r["flow"][i][num] for r in sel), sum(r["flow"][i][den] for r in sel))

    for i, (nm, _, _) in enumerate(LOGPER):
        sel = [r for r in full if len(r["flow"]) > i and r["flow"][i]["atkIssued"] >= 20]
        iss = sum(r["flow"][i]["atkIssued"] for r in sel)
        lan = sum(r["flow"][i]["land"] for r in sel)
        rs = [r["flow"][i]["land"] / r["flow"][i]["atkIssued"] for r in sel]
        P(f"  {nm} | {len(sel)} | {sum(r['flow'][i]['bots'] for r in sel)} | {iss} | {lan} | {pct(lan, iss)} | {fmt(med(rs))} | {sum(1 for v in rs if v < 0.7)} | {sum(1 for v in rs if v > 1.0)} || "
          + " | ".join(f"{ratio_of([r for r in sel if r['cohort'] == c], i, 'land', 'atkIssued')}（{sum(1 for r in sel if r['cohort'] == c)} 局）" for c in COHORTS[:2])
          + f" || {ratio_of([r for r in sel if r['won']], i, 'land', 'atkIssued')}（{sum(1 for r in sel if r['won'])} 局） | {ratio_of([r for r in sel if not r['won']], i, 'land', 'atkIssued')}（{sum(1 for r in sel if not r['won'])} 局）")
        agg_f[nm] = dict(matches=len(sel), atkIssued=iss, atkLanded=lan, medianRatio=med(rs), below07=sum(1 for v in rs if v < 0.7))
    P("  捐款：日志 = HL-DONATE / HL-DISPATCH 行；录像 = 落地的捐款指令")
    P("  时段 | 有捐款日志的局 | 日志行 | 录像落地 | 落地 ÷ 日志行 || squad10 | squad20")
    for i, (nm, _, _) in enumerate(LOGPER):
        sel = [r for r in full if len(r["flow"]) > i and r["flow"][i]["donLines"] > 0]
        dl = sum(r["flow"][i]["donLines"] for r in sel)
        dn = sum(r["flow"][i]["don"] for r in sel)
        if not sel:
            continue
        P(f"  {nm} | {len(sel)} | {dl} | {dn} | {pct(dn, dl)} || "
          + " | ".join(f"{sum(r['flow'][i]['don'] for r in sel if r['cohort'] == c)}/{sum(r['flow'][i]['donLines'] for r in sel if r['cohort'] == c)}"
                       f"（{ratio_of([r for r in sel if r['cohort'] == c], i, 'don', 'donLines')}；{sum(1 for r in sel if r['cohort'] == c)} 局）" for c in COHORTS[:2]))
        agg_f[nm].update(donLines=dl, donLanded=dn, donMatches=len(sel))
    P("  船：日志 = boats 增量；录像 = 落地的发船指令")
    P("  时段 | 日志 | 录像落地 | 落地 ÷ 日志")
    for i, (nm, _, _) in enumerate(LOGPER):
        sel = [r for r in full if len(r["flow"]) > i]
        bl = sum(r["flow"][i]["boatsLog"] for r in sel)
        bn = sum(r["flow"][i]["boat"] for r in sel)
        P(f"  {nm} | {bl} | {bn} | {pct(bn, bl)}")
        agg_f[nm].update(boatsLog=bl, boatsLanded=bn)

    # ---- [XT-I] ----
    P("")
    P("[XT-I] 接壤普查（真值；600~1500 每 30 拍一个样本，全部在线真人；不跑策略，只看引擎状态）")
    P("  「白给」= 挨着的内置 AI 里最便宜的那个，推到出局线要的兵（策略自己的 elimCost 公式）≤ 这个号余额的 10%；「买得起」= ≤25%；")
    P("  「出手」= 之后 90 拍里这个号有一条生效的陆攻落在内置 AI 身上。")
    P("  窗 | 组 | 局数 | 样本 | 挨着 AI | 挨着无主地 | 只剩真人 || 白给的样本 | 其中 90 拍内出手 | 买得起的样本 | 其中出手 | 挨着 AI 的样本里出手")
    RWN = ("600~900", "900~1260", "1260~1500", "600~1500")
    agg_i = {}

    def reach_sum(sel, k, g):
        acc = [0] * 14
        for r in sel:
            ks = range(3) if k == 3 else [k]
            for kk in ks:
                for i in range(14):
                    acc[i] += r["reach"][kk][g][i]
        return acc

    for k, nm in enumerate(RWN):
        for g in GROUPS:
            sel = [r for r in (full if g == "own" else recs) if r.get("reach")]
            a = reach_sum(sel, k, g)
            sel_n = sum(1 for r in sel if reach_sum([r], k, g)[0] > 0)
            if not a[0]:
                continue
            P(f"  {nm} | {GROUP_CN[g]} | {sel_n} | {a[0]} | {pct(a[1], a[0])} | {pct(a[2], a[0])} | {pct(a[3], a[0])} || {a[4]} | {pct(a[5], a[4])} | {a[6]} | {pct(a[7], a[6])} | {pct(a[8], a[1])}")
            agg_i[f"{nm}|{g}"] = dict(matches=sel_n, samples=a[0], hasAi=a[1], hasNeutral=a[2], locked=a[3], free=a[4], freeHit=a[5], cheap=a[6], cheapHit=a[7], aiHit=a[8], aiLandAdj=a[9], aiLandCheap=a[10])
    P("  无主地（挨着无主地的样本里，之后 90 拍内有一条生效的陆攻落在无主地上）：窗 | 组 | 挨着无主地的样本 | 其中 90 拍内打了无主地 | 只挨无主地、不挨内置 AI 的样本 | 其中打了无主地")
    for k, nm in enumerate(RWN):
        for g in ("own", "wild"):
            sel = [r for r in (full if g == "own" else recs) if r.get("reach")]
            a = reach_sum(sel, k, g)
            if a[2]:
                P(f"    {nm} | {GROUP_CN[g]} | {a[2]} | {pct(a[11], a[2])} | {a[12]} | {pct(a[13], a[12])}")
                agg_i[f"neutral|{nm}|{g}"] = dict(hasNeutral=a[2], hitNeutral=a[11], onlyNeutral=a[12], onlyNeutralHit=a[13])
    for nm, sel in (("几乎不卡的局", [r for r in full if calm_of(r)]), ("其余的局", [r for r in full if not calm_of(r)])):
        for g in ("own", "wild"):
            a = reach_sum([r for r in sel if r.get("reach")], 3, g)
            if a[2]:
                P(f"    600~1500·{nm} | {GROUP_CN[g]} | {a[2]} | {pct(a[11], a[2])} | {a[12]} | {pct(a[13], a[12])}")
                agg_i[f"neutral|{nm}|{g}"] = dict(hasNeutral=a[2], hitNeutral=a[11], onlyNeutral=a[12], onlyNeutralHit=a[13])
    P("  分开看（600~1500 合计）：组 | 局 | 白给的样本 | 其中 90 拍内出手 | 买得起的样本 | 其中出手 | 只剩真人的样本占比")
    splits = [("squad10 的局", [r for r in full if r["cohort"] == "squad10"]), ("squad20 的局", [r for r in full if r["cohort"] == "squad20"]),
              ("几乎不卡的局（own 600~1500 陆攻没生效 ≤5%）", [r for r in full if calm_of(r)]), ("其余的局", [r for r in full if not calm_of(r)]),
              ("主队赢的局", [r for r in full if r["won"]]), ("没赢的局", [r for r in full if not r["won"]])]
    for nm, sel in splits:
        sel = [r for r in sel if r.get("reach")]
        for g in ("own", "wild"):
            a = reach_sum(sel, 3, g)
            if not a[0]:
                continue
            P(f"  {nm} | {GROUP_CN[g]} | {sum(1 for r in sel if reach_sum([r], 3, g)[0] > 0)} | {a[4]} | {pct(a[5], a[4])} | {a[6]} | {pct(a[7], a[6])} | {pct(a[3], a[0])}")
            agg_i[f"split|{nm}|{g}"] = dict(samples=a[0], free=a[4], freeHit=a[5], cheap=a[6], cheapHit=a[7], locked=a[3])
    pmr = []
    for r in full:
        if not r.get("reach"):
            continue
        a, w = reach_sum([r], 3, "own"), reach_sum([r], 3, "wild")
        if a[4] >= 20 and w[4] >= 20:
            pmr.append((r, a[5] / a[4], w[5] / w[4], a[3] / a[0], w[3] / w[0]))
    P(f"  逐局（own 和野人各 ≥20 个白给样本的 {len(pmr)} 局）：白给样本里 90 拍内出手的比例——own 中位 {100 * med([x[1] for x in pmr]):.0f}%，野人 中位 {100 * med([x[2] for x in pmr]):.0f}%；"
      f"own 比野人低的 {sum(1 for x in pmr if x[1] < x[2])} 局；只剩真人的样本占比——own 中位 {100 * med([x[3] for x in pmr]):.0f}%，野人 中位 {100 * med([x[4] for x in pmr]):.0f}%")
    calm_pm = [x for x in pmr if calm_of(x[0])]
    P(f"    其中几乎不卡的 {len(calm_pm)} 局：own 中位 {fmt(100 * med([x[1] for x in calm_pm]) if calm_pm else None, 0)}%，野人 中位 {fmt(100 * med([x[2] for x in calm_pm]) if calm_pm else None, 0)}%；"
      f"own 比野人低的 {sum(1 for x in calm_pm if x[1] < x[2])} 局")

    # ---- [XT-J] ----
    P("")
    P("[XT-J] 买 AI 地规则重算（真值；[XT-I] 里挨着内置 AI 的样本，逐个把 1500 拍前买内置 AI 地的规则照抄一遍；不跑策略，只用引擎状态）")
    P("  规则（c110 行号）：pickTarget L1180-1212 对每个挨着的 AI q：allow L2147-2150 = (botPx(q) ≤ winWorth 且 price(q) ≤ botMax=60) 或余额 ≥ 125 兵/格；")
    P("    avail = 余额 − max( botPx(q)·我的地 ÷ (winR·t)，dpKeep，sb )（floorFor0 L2270-2276 → winFloor L4542-4550）；avail ≤ minSend(21.41%)·余额 就跳过（L1197）；")
    P("    dpKeep L2491-2496 = (最强的邻居真人的余额 + 它压在我身上的兵 − 1.5·我的地) ÷ 1.78；sb = safeFinite L2532-2541 = 我挨着的 AI 里，")
    P("    「它别的邻居中最弱的那个的余额」的最大值（低于它，AI 下一手就会挑我）。参数 winR=0.002、minSend=0.2141、botMax=60、maxTargets=4、feeK=4，各档相同。")
    P("  两档规则只差一行：c110（squad20）的 pickTarget L1200 把已经在打的 AI 跳过（除非它在反打、且我压上去的兵不到 0.35·need）；")
    P("    c116 系（squad10）没有这一行，已经在打的 AI 每个决策拍（period=5）都重新当候选——所以多一类「规则放行，但放行的都是已经压着兵的 AI」。")
    P("  类别互斥，按这个顺序判：有新目标放行 → 只有续兵放行 → 候选全被 L1200 跳过（只 c110）→ 槽满 → AI 的地不值 → 留底三项里最大的那一项。")
    P("  野人不跑这套规则，野人那几行是「同一把尺子量出来的对照」：同样的处境下，不受这条规则约束的人出不出手。")
    agg_j = {}

    def rule_sum(sel, g):
        acc = {c: [0] * 6 for c in RULE_CLASSES}
        extra = dict(sbSrc={k: 0 for k in SRC_GROUPS}, dpSrc={k: 0 for k in SRC_GROUPS}, over=dict(px=0, dp=0, sb=0), sole=dict(px=0, dp=0, sb=0),
                     eng={c: 0 for c in RULE_CLASSES})
        for r in sel:
            ru = (r.get("rule") or {}).get(g)
            if not ru:
                continue
            for c in RULE_CLASSES:
                for i in range(6):
                    acc[c][i] += ru["cls"][c][i]
            for k in ("sbSrc", "dpSrc", "over", "sole", "eng"):
                for kk, v in ru[k].items():
                    extra[k][kk] += v
        return acc, extra

    def rule_table(nm, sel, g, col=2):
        acc, extra = rule_sum(sel, g)
        tot = sum(acc[c][col] for c in RULE_CLASSES)
        hit = sum(acc[c][col + 1] for c in RULE_CLASSES)
        if not tot:
            return None
        P(f"  {nm} | {GROUP_CN[g]} | 样本 {tot} | 90 拍内出手 {pct(hit, tot)} || " + " | ".join(
            f"{RULE_CN[c]} {acc[c][col]}（{pct(acc[c][col], tot)}；出手 {pct(acc[c][col + 1], acc[c][col])}）" for c in RULE_CLASSES if acc[c][col]))
        agg_j[f"{nm}|{g}|{'free' if col == 2 else 'afford' if col == 4 else 'all'}"] = dict(
            total=tot, hit=hit, cls={c: dict(n=acc[c][col], hit=acc[c][col + 1]) for c in RULE_CLASSES}, **extra)
        return acc, extra, tot, hit

    with_rule = [r for r in full if r.get("rule")]
    with_rule_all = [r for r in recs if r.get("rule")]
    P("  白给的样本（600~1500）：范围 | 组 | 样本 | 出手 || 类别 样本（占比；其中 90 拍内出手）")
    res_own = rule_table("全部", with_rule, "own")
    res_wild = rule_table("全部", with_rule_all, "wild")
    for nm, sel in (("squad10 的局", [r for r in with_rule if r["cohort"] == "squad10"]), ("squad20 的局", [r for r in with_rule if r["cohort"] == "squad20"]),
                    ("几乎不卡的局", [r for r in with_rule if calm_of(r)]), ("其余的局", [r for r in with_rule if not calm_of(r)]),
                    ("主队赢的局", [r for r in with_rule if r["won"]]), ("没赢的局", [r for r in with_rule if not r["won"]])):
        rule_table(nm, sel, "own")
        if nm == "几乎不卡的局":
            rule_table(nm, sel, "wild")
    P("  买得起的样本（≤25%；600~1500）：")
    rule_table("全部", with_rule, "own", 4)
    rule_table("全部", with_rule_all, "wild", 4)
    if res_own:
        acc, extra, tot, hit = res_own
        idle_n = tot - hit
        P(f"  own 白给样本里 90 拍内没出手的 {idle_n} 个，按类别：" + "；".join(
            f"{RULE_CN[c]} {acc[c][2] - acc[c][3]}（{pct(acc[c][2] - acc[c][3], idle_n)}）" for c in RULE_CLASSES if acc[c][2] - acc[c][3]))
        blocked = sum(acc[c][2] for c in ("px", "dp", "sb"))
        P(f"  own 白给样本里被留底挡住的 {blocked} 个（{pct(blocked, tot)}）：" + "；".join(
            f"{RULE_CN[c]} {acc[c][2]}（其中留底已超过余额 {extra['over'][c]}、只差这一项就放行 {extra['sole'][c]}）" for c in ("sb", "dp", "px")))
        P("  own 白给样本里，这个号当时已经有兵压在某个挨着的内置 AI 身上的：" + "；".join(
            f"{RULE_CN[c]} {extra['eng'][c]}/{acc[c][2]}（{pct(extra['eng'][c], acc[c][2])}）" for c in RULE_CLASSES if acc[c][2]))
        sbn = acc["sb"][2]
        P(f"  AI 仇恨项挡住的 {sbn} 个样本里，sb 取的是谁的余额（那个 AI 别的邻居里最弱的）：" + "；".join(
            f"{SRC_CN[k]} {v}（{pct(v, sbn)}）" for k, v in extra["sbSrc"].items() if v))
        dpn = acc["dp"][2]
        P(f"  防真人项挡住的 {dpn} 个样本里，最强的邻居真人是谁：" + "；".join(f"{SRC_CN[k]} {v}（{pct(v, dpn)}）" for k, v in extra["dpSrc"].items() if v))
        allv = sorted(x for r in with_rule for x in r["rule"]["own"]["sbShare"])
        if allv:
            qv = lambda f: allv[min(len(allv) - 1, int(f * len(allv)))]
            P(f"  own 白给样本的 sb ÷ 余额：25/50/75/90 分位 {qv(0.25):.2f} / {qv(0.5):.2f} / {qv(0.75):.2f} / {qv(0.9):.2f}；≥0.7859（= 1 − minSend，单这一项就挡住）的 {sum(1 for x in allv if x >= 0.7859)} 个（{pct(sum(1 for x in allv if x >= 0.7859), len(allv))}）；"
              f"sb = 0 的 {sum(1 for x in allv if x == 0)} 个（{pct(sum(1 for x in allv if x == 0), len(allv))}）")
    P("  白给的样本按窗：窗 | 组 | 样本 | 有新目标放行（出手） | 只有续兵放行（出手） | 都已在打、跳过（出手） | 不值 | 留底·地价 | 留底·防真人 | 留底·AI 仇恨（出手）")
    for k, nm in enumerate(("600~900", "900~1260", "1260~1500")):
        for g, sel in (("own", with_rule), ("wild", with_rule_all)):
            w = {c: [sum(r["rule"][g]["win"][k][c][i] for r in sel) for i in range(2)] for c in RULE_CLASSES}
            tot = sum(w[c][0] for c in RULE_CLASSES)
            if not tot:
                continue
            P(f"    {nm} | {GROUP_CN[g]} | {tot} | {pct(w['allowed'][0], tot)}（{pct(w['allowed'][1], w['allowed'][0])}） | {pct(w['again'][0], tot)}（{pct(w['again'][1], w['again'][0])}） | {pct(w['engaged'][0], tot)}（{pct(w['engaged'][1], w['engaged'][0])}） | "
              f"{pct(w['worth'][0], tot)} | {pct(w['px'][0], tot)} | {pct(w['dp'][0], tot)} | {pct(w['sb'][0], tot)}（{pct(w['sb'][1], w['sb'][0])}）")
            agg_j[f"win|{nm}|{g}"] = dict(total=tot, cls={c: dict(n=w[c][0], hit=w[c][1]) for c in RULE_CLASSES})
    P("  挨着的内置 AI 有多大（挨着内置 AI 的全部样本；每个样本最多记 6 个、按打垮价从小到大）：窗 | 组 | 样本 | 挨着的 AI 平均地 | 其中最大的那个 | 打垮最便宜的那个 | 记到的 AI 个数 | 这个号自己的地 | 自己的兵")
    for k, nm in enumerate(("600~900", "900~1260", "1260~1500")):
        for g, sel in (("own", with_rule), ("wild", with_rule_all)):
            a = [sum(r["rule"][g]["adj"][k][i] for r in sel) for i in range(7)]
            if a[0]:
                P(f"    {nm} | {GROUP_CN[g]} | {a[0]} | {a[1] / a[0]:.0f} | {a[2] / a[0]:.0f} | {a[3] / a[0]:.0f} | {a[4] / a[0]:.1f} | {a[5] / a[0]:.0f} | {a[6] / a[0]:.0f}")
                agg_j[f"adj|{nm}|{g}"] = dict(n=a[0], mean=a[1] / a[0], largest=a[2] / a[0], cheapest=a[3] / a[0], count=a[4] / a[0], terr=a[5] / a[0], bal=a[6] / a[0])
    pma = []
    for r in with_rule:
        o = [sum(r["rule"]["own"]["adj"][k][i] for k in range(3)) for i in range(7)]
        w = [sum(r["rule"]["wild"]["adj"][k][i] for k in range(3)) for i in range(7)]
        if o[0] >= 20 and w[0] >= 20:
            pma.append(((o[1] / o[0]) / (w[1] / w[0]), (o[2] / o[0]) / (w[2] / w[0]), (o[3] / o[0]) / (w[3] / w[0])))
    if pma:
        P(f"    逐局（own 和野人各 ≥20 个样本的 {len(pma)} 局），own ÷ 野人：挨着的 AI 平均地 中位 {med([x[0] for x in pma]):.2f}（<1 的 {sum(1 for x in pma if x[0] < 1)} 局）；"
          f"最大的那个 中位 {med([x[1] for x in pma]):.2f}（<1 的 {sum(1 for x in pma if x[1] < 1)} 局）；打垮最便宜的那个 中位 {med([x[2] for x in pma]):.2f}（<1 的 {sum(1 for x in pma if x[2] < 1)} 局）")
        agg_j["adj|perMatch"] = dict(n=len(pma), mean=med([x[0] for x in pma]), largest=med([x[1] for x in pma]), cheapest=med([x[2] for x in pma]))
    pmj = []
    for r in with_rule:
        acc, _ = rule_sum([r], "own")
        tot = sum(acc[c][2] for c in RULE_CLASSES)
        if tot >= 20:
            r["gateShare"] = sum(acc[c][2] for c in ("px", "dp", "sb")) / tot
            r["sbShare"] = acc["sb"][2] / tot
            fire_n, fire_h = acc["allowed"][2] + acc["again"][2], acc["allowed"][3] + acc["again"][3]
            r["allowedHit"] = (fire_h / fire_n) if fire_n >= 10 else None
            pmj.append(r)
    P(f"  逐局（own ≥20 个白给样本的 {len(pmj)} 局）：被留底挡住的占比 中位 {100 * med([r['gateShare'] for r in pmj]):.0f}%"
      f"（四分位 {100 * sorted(r['gateShare'] for r in pmj)[len(pmj) // 4]:.0f}%~{100 * sorted(r['gateShare'] for r in pmj)[(3 * len(pmj)) // 4]:.0f}%）；"
      f"其中 AI 仇恨项 中位 {100 * med([r['sbShare'] for r in pmj]):.0f}%；规则放行（含续兵）的样本里 90 拍内出手 中位 {100 * med([r['allowedHit'] for r in pmj if r['allowedHit'] is not None]):.0f}%")
    for nm, sel in (("squad10", [r for r in pmj if r["cohort"] == "squad10"]), ("squad20", [r for r in pmj if r["cohort"] == "squad20"]),
                    ("几乎不卡的局", [r for r in pmj if calm_of(r)]), ("其余的局", [r for r in pmj if not calm_of(r)]),
                    ("主队赢", [r for r in pmj if r["won"]]), ("没赢", [r for r in pmj if not r["won"]])):
        if sel:
            P(f"    {nm}（{len(sel)} 局）：被留底挡住 中位 {100 * med([r['gateShare'] for r in sel]):.0f}%；AI 仇恨项 中位 {100 * med([r['sbShare'] for r in sel]):.0f}%；"
              f"放行样本出手 中位 {fmt(100 * med([r['allowedHit'] for r in sel if r['allowedHit'] is not None]) if any(r['allowedHit'] is not None for r in sel) else None, 0)}%")

    # ---- [XT-G] ----
    P("")
    P("[XT-G] 录像前 1800 拍里出局 / 离开（真值；录像不到 1800 拍的算到录像末）：组 | 席位 | 出局 | 其中 900 拍前 | 离开")
    for g in GROUPS:
        sel = [r for r in (full if g == "own" else [x for x in recs if not x["spawnOnly"]])]
        n = sum(r["exits"][g]["n"] for r in sel)
        d = sum(r["exits"][g]["dead"] for r in sel)
        d9 = sum(r["exits"][g]["dead900"] for r in sel)
        lf = sum(r["exits"][g]["left"] for r in sel)
        P(f"  {GROUP_CN[g]} | {n} | {d}（{pct(d, n)}） | {d9}（{pct(d9, n)}） | {lf}（{pct(lf, n)}）")

    # ---- [XT-H] ----
    P("")
    P("[XT-H] 逐局：局 | 档 | 真人 | own/[APEX]/名字池/野人 | 录像到 | 核对 | 人均对照 @300/630/900/1260/1500/1800 | AI 地份额对照 (600,1500] | 600~1500 陆攻没生效 own / 野人 | own 贴边 | 600~1500 陆攻 落地/发出 | 主队赢")
    for r in recs:
        if not r["valid"]:
            P(f"  {r['matchId']} | {r['cohort']} | {r['H']} | —/{r['size']['apex']}/{r['size']['pool']}/{r['size']['wild']} | {r['endTick']} | {r['exact']}/{r['rows']} 对不上 | 不进 own 统计")
            continue
        rt = "/".join(fmt(r["ratio"]["own"].get(t)) for t in (300, 630, 900, 1260, 1500, 1800))
        srv = next((v for x, v in sr if x is r), None)
        c = r["cmds"][1] if len(r["cmds"]) > 1 else None
        ne = (f"{1 - c['own']['ok'] / c['own']['land']:.0%}" if c and c["own"]["land"] else "—") + " / " + (f"{1 - c['wild']['ok'] / c['wild']['land']:.0%}" if c and c["wild"]["land"] else "—")
        fl = r["flow"][1] if len(r["flow"]) > 1 and r["flow"][1]["atkIssued"] > 0 else None
        P(f"  {r['matchId']} | {r['cohort']} | {r['H']} | {r['size']['own']}/{r['size']['apex']}/{r['size']['pool']}/{r['size']['wild']} | {r['endTick']} | {r['exact']}/{r['rows']} | {rt} | {fmt(srv)} | {ne} | "
          f"{r['spawn']['own']['nearEdge']}/{r['spawn']['own']['n']} | {(str(fl['land']) + '/' + str(fl['atkIssued'])) if fl else '—'} | {'赢' if r['won'] else '—'}")

    for r in recs:
        for g in GROUPS:
            ((r.get("rule") or {}).get(g) or {}).pop("sbShare", None)
    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    with open(os.path.join(OUT, "_cross", "xtruth.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(OUT, "_cross", "xtruth.json"), "w", encoding="utf-8") as f:
        json.dump(dict(replays=len(recs), valid=len(val), full=len(full), failed=failed, perHead=agg_b, dist=agg_dist, drop=dict(both=len(both), hit=[r["matchId"] for r in drop]),
                       aiHarvest=dict(matches=len(hv), cells=tot, heads=heads, burnt=burn), cmdEffect=agg_d, attackSize=agg_sz, spawn=agg_e, spawnAssign=agg_sa, flow=agg_f, reach=agg_i, rule=agg_j, aiYield=agg_y, aiPairs=agg_p, budget=agg_bd,
                       matches=[{k: v for k, v in r.items()} for r in recs]), f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        print("\n".join(out))


if __name__ == "__main__":
    main()
