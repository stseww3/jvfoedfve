#!/usr/bin/env python3
"""namepool.py — 「名字池误认」的真相口径账（squad20 = c110 的局；整局重演）。

c110 的互保是按名字认人的（v27-team-c110.js L3973-3996）：名字在 SQUAD_POOL_SET 里（或带 [NPL] / [NOPE]）的席位，只要场上还有
「占地 ≥80 格、名字不在池里、g.isBot 为假的真人席位」活着，就不列为邻居、不打（发船选目标的一处也跳过，L3396）；引擎的敌我却只看队伍。
两套口径对不上的席位有四种：
    跨队的我方号（引擎把编队分到了几个队里）｜离开以后的我方号（空壳，引擎按内置 AI 的打法接管，名字还在池里）｜
    名字在池里、包里却没有它的日志的席位（可能是没留下日志的我方号，也可能是撞名的外人——数据里分不开）｜这些席位离开后的空壳
本脚本只量历史上这四种席位和我方在线的号之间实际发生了什么（挨着、互相吃地、发了什么指令、互相捐兵），不改任何规则、不跑任何策略。

原料：namepool.mjs → out/_run/namepool/<局>.json（整局重演；只读 /agent/repos/c136-data 发现集）
    python3 namepool.py [--quiet]     → out/_cross/namepool.txt、namepool.json
录像：同一个房间出了两份包、自己的录像又短的局，用同房另一份包更长的录像重演（roompairs.py；本包的号按名字认）。
      模拟器的重演中途和真引擎对不上的录像（fidabl.txt [FA-E]），只算到对不上的那一拍之前。

口径：
  · 我方号 = 对局包里有它的日志、席位和名字都对得上的号（facts.py 的席位表）∪ 重演器按 traj / results 认出来的号。
  · 「在线」= 还没发过离开指令；「空壳」= 发过离开指令以后（引擎按内置 AI 接管）。按窗 / 样本的起点算。
  · 保护开着（主口径）= 场上还有占地 ≥80 格、名字不在池里、没离开的真人席位（模拟器的 isBot 对离开的真人返回真，game.js L215-217）。
    线上那一层给策略的 g.isBot 怎么算，数据镜像里没有那段代码；所以另给「宽口径」= 离开的池外席位也算。两种口径只在 [NP-G] 里分得开。
  · 「受保护的引擎敌人」（下面简称 PE）= 名字在池里、和这个我方号不在一个队（自由混战里人人都不在一个队）的席位，且当时保护开着。
  · 地的流水来自重演里每一次进攻结算（谁从谁手里吃了几格），300 拍一窗；接触来自每 90 拍一次的边界扫描（每个号接触格数最多的 12 个对象；
    只有重演器认出来的我方号有这份扫描——差的那几个号都在 336 拍以前离开了）。

节：
  [NP-A] 名册：每局我方号几个、分在几个队、多少个中途离开；名字在池里而没有日志的席位；保护什么时候解除。
  [NP-B] 接触：我方在线的号 × 90 拍样本里，贴着 PE 的占比；只剩 PE 可打（没有无主地、没有内置 AI、没有不受保护的真人）的占比。
  [NP-C] 地的流水：我方在线的号被谁吃走了多少格、从谁手里吃到多少格（按对方的种类；保护开着 / 解除以后）。
  [NP-D] 我方在线的号发的指令：陆攻按目标的种类、发船按目的地的种类、船靠岸按靠岸那一格是谁的。
  [NP-E] 保护开着时我方在线的号从 PE 手里吃到的地，是怎么来的（有没有对它发过陆攻、有没有船靠在它的地上）。
  [NP-F] 捐兵：我方在线的号捐给谁，空壳把余额给了谁。
  [NP-G] 两种保护口径分得开的窗：池外真人只剩空壳的时候，我方在线的号有没有对池里的跨队席位发陆攻。
  [NP-I] 名字在池里、包里没有日志的席位自己怎么打：对我方号发不发陆攻（发了就不是跑这份规则的号）。
  [NP-H] 逐局一行。
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xbatch as XB  # noqa: E402
import facts  # noqa: E402
import roompairs as RP  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RUN = os.path.join(OUT, "_run", "namepool")
PERIODS = [("0~600", 0, 600), ("600~1500", 600, 1500), ("1500~3000", 1500, 3000), ("3000~4284", 3000, 4284), ("4284+", 4284, 10 ** 9)]
KINDS = ["neutral", "AI", "wild_on", "wild_shell", "apex_on", "apex_shell", "ownx_on", "ownx_shell", "ulx_on", "ulx_shell",
         "ownteam_on", "ownteam_shell", "ulteam_on", "ulteam_shell", "mate_on", "mate_shell", "boss"]
KIND_CN = dict(neutral="无主地", AI="内置 AI", wild_on="野人（在线）", wild_shell="野人的空壳", apex_on="[APEX] 号（在线）", apex_shell="[APEX] 的空壳",
               ownx_on="跨队的我方号（在线）", ownx_shell="跨队的我方空壳", ulx_on="池名无日志席位·跨队（在线）", ulx_shell="池名无日志席位·跨队的空壳",
               ownteam_on="同队的我方号（在线）", ownteam_shell="同队的我方空壳", ulteam_on="池名无日志席位·同队（在线）", ulteam_shell="池名无日志席位·同队的空壳",
               mate_on="同队的池外真人（在线）", mate_shell="同队的池外真人的空壳", boss="Boss 名字的席位")
PE_KINDS = ("ownx_on", "ownx_shell", "ulx_on", "ulx_shell")
WILD_KINDS = ("wild_on", "wild_shell", "apex_on", "apex_shell")
BOSS_PAT = ("kazerd", "auouf")


def pct(a, b, nd=0):
    return "–" if not b else f"{100 * a / b:.{nd}f}%"


def period_of(t):
    for i, (_, a, z) in enumerate(PERIODS):
        if a <= t < z:
            return i
    return len(PERIODS) - 1


def facts_own(mid, H, low):
    """对局包里有日志、席位和名字都对得上的我方号（和 xtruth.seat_groups 同一条规则）。"""
    F = facts.build(mid)
    own = set()
    for me, b in F["bots"].items():
        mr = b.get("meReal") if b.get("meReal") is not None else me
        if mr is not None and 0 <= mr < H and any(low[mr].endswith(lab.lower()) for lab in b["labels"]):
            own.add(mr)
    return own


def is_boss(low_name):
    import re
    stripped = re.sub(r"\[[^\]]*\]", "", low_name).strip()
    return stripped == "npl" or low_name == "[npl]npl" or any(k in low_name for k in BOSS_PAT)


def main():
    quiet = "--quiet" in sys.argv
    pool = XB.name_pool()
    cohort = {mid: card.get("cohort") for mid, card in XB.discovery_ids()}
    lines = []
    J = {"matches": {}}

    def P(s=""):
        lines.append(s)

    files = sorted(glob.glob(os.path.join(RUN, "*.json")))
    rows = []
    tot_contact = [Counter() for _ in PERIODS]
    tot_lost = {True: Counter(), False: Counter()}
    tot_gain = {True: Counter(), False: Counter()}
    tot_lost_p = [Counter() for _ in PERIODS]
    tot_atk = {True: Counter(), False: Counter()}
    tot_boat = {True: Counter(), False: Counter()}
    tot_land = {True: Counter(), False: Counter()}
    tot_origin = Counter()
    tot_origin_tiles = Counter()
    tot_don = Counter()
    tot_don_amt = Counter()
    tot_husk = Counter()
    tot_husk_amt = Counter()
    tot_gap = Counter()
    unlogged = []
    ul_rows = []
    tot_xfight = Counter()
    old = []
    for fp in files:
        R = json.load(open(fp, encoding="utf-8"))
        mid = R["matchId"]
        if cohort.get(mid) != "squad20":
            continue
        if "lands" not in R:
            old.append(mid)
            continue
        H = R["H"]
        names = [str(x).strip() for x in R["names"]]
        low = [x.lower() for x in names]
        teams = R["teams"]
        team_game = R["gameMode"] != 0
        left = R["leftT"]
        sq = set(i for i in R["squad"].values() if i >= 0)
        own_set = sq | facts_own(mid, H, low)
        own = sorted(own_set)
        if not own:
            continue
        rec = R.get("replayFrom") or mid
        cut, _checked = RP.cut_of(rec)
        end = R["endTick"]
        if cut is not None and cut < end:
            # 模拟器和引擎从 cut 这一拍起对不上：快照、流水（300 拍一窗，整窗都在 cut 之前的才留）、指令、靠岸、捐兵都只留 cut 之前的
            n_ok = sum(1 for t in R["snapT"] if t < cut)
            R["snapT"], R["terr"] = R["snapT"][:n_ok], R["terr"][:n_ok]
            R["flows"] = [f for f in R["flows"] if f[0] + 300 < cut]
            R["nb"] = {k: [x for x in v if x[0] < cut] for k, v in R["nb"].items()}
            R["atk"] = [a for a in R["atk"] if a[0] + 300 <= cut]
            for key in ("boats", "lands", "dons", "husk"):
                R[key] = [x for x in R[key] if x[0] < cut]
            end = cut
        else:
            cut = None
        in_pool = [low[s] in pool or "[npl]" in low[s] or "[nope]" in low[s] for s in range(H)]
        boss = [is_boss(low[s]) and not in_pool[s] for s in range(H)]
        apex = ["[apex]" in low[s] for s in range(H)]
        ul = [s for s in range(H) if in_pool[s] and s not in own_set]
        outsiders = [s for s in range(H) if not in_pool[s] and not boss[s]]
        snapT, terr = R["snapT"], R["terr"]
        for s in ul:
            unlogged.append((mid, s, names[s], left[s], max(tr[s] for tr in terr), teams[s] if team_game else None,
                             sorted(set(teams[o] for o in own)) if team_game else None))

        # 保护开着：strict = 占地 ≥80 的池外真人里还有没离开的；loose = 离开的也算
        strict = [any(tr[s] >= 80 and not (0 <= left[s] <= snapT[i]) for s in outsiders) for i, tr in enumerate(terr)]
        loose = [any(tr[s] >= 80 for s in outsiders) for tr in terr]

        def snap_i(t):
            i = min(len(snapT) - 1, max(0, t // 90))
            while i > 0 and snapT[i] > t:
                i -= 1
            return i

        def prot_at(t):
            return strict[snap_i(t)]

        # 第一个「保护不在」的快照（90 拍以后：开局各家还没长到 80 格）
        t_off = next((snapT[i] for i in range(len(snapT)) if snapT[i] >= 90 and not strict[i]), None)
        t_off_loose = next((snapT[i] for i in range(len(snapT)) if snapT[i] >= 90 and not loose[i]), None)

        def same_team(a, b):
            return team_game and teams[a] == teams[b] and teams[a] != 0

        def online(q, t):
            return not (0 <= left[q] <= t)

        def kind(me, q, t):
            if q >= 512 or q < 0:
                return "neutral"
            if q >= H:
                return "AI"
            sfx = "_on" if online(q, t) else "_shell"
            if q in own_set:
                return ("ownteam" if same_team(me, q) else "ownx") + sfx
            if in_pool[q]:
                return ("ulteam" if same_team(me, q) else "ulx") + sfx
            if boss[q]:
                return "boss"
            if same_team(me, q):
                return "mate" + sfx
            return ("apex" if apex[q] else "wild") + sfx

        # [NP-B] 接触
        m_contact = [Counter() for _ in PERIODS]
        for me_s, series in R["nb"].items():
            me = int(me_s)
            for t, lst in series:
                if not online(me, t):
                    continue
                i = snap_i(t)
                if terr[i][me] <= 0:
                    continue
                pi = period_of(t)
                on = strict[i]
                ks = [kind(me, q, t) for q, _ in lst]
                c = m_contact[pi]
                c["samples"] += 1
                pe = [k for k in ks if k in PE_KINDS]
                if on and pe:
                    c["touchPE"] += 1
                    for k in set(pe):
                        c["touch_" + k] += 1
                    if not any(k in ("neutral", "AI") or k in WILD_KINDS for k in ks):
                        c["onlyPE"] += 1
                if not on:
                    c["protOff"] += 1
                if loose[i] and not strict[i]:
                    c["gap"] += 1
                    if pe:
                        c["gapTouch"] += 1
        for i in range(len(PERIODS)):
            tot_contact[i].update(m_contact[i])

        # [NP-C] 地的流水（主体 = 窗起点还在线的我方号）
        lost = {True: Counter(), False: Counter()}
        gain = {True: Counter(), False: Counter()}
        gain_pairs = defaultdict(int)       # (我方在线号, PE 席位) → 保护开着时吃到的格
        for b, p, q, tiles, burnt, dB in R["flows"]:
            if p != q and p in own_set and q in own_set and not same_team(p, q):
                # 我方号打我方号（跨队）：两边烧掉的兵都是编队自己的
                kk = "on" if prot_at(b) else "off"
                tot_xfight[kk + "|tiles"] += max(0, tiles)
                tot_xfight[kk + "|burnt"] += burnt
                tot_xfight[kk + "|dB"] += dB
                tot_xfight[kk + "|rows"] += 1
            if tiles <= 0 or p == q:
                continue
            on = prot_at(b)
            if q in own_set and online(q, b):
                k = kind(q, p, b)
                lost[on][k] += tiles
                tot_lost_p[period_of(b)][k] += tiles
            if p in own_set and online(p, b) and q < 512:
                k = kind(p, q, b)
                gain[on][k] += tiles
                if on and k in PE_KINDS:
                    gain_pairs[(p, q)] += tiles
        for on in (True, False):
            tot_lost[on].update(lost[on])
            tot_gain[on].update(gain[on])

        # [NP-D] 指令（主体 = 发指令那一窗 / 那一拍还在线的我方号）
        atk = {True: Counter(), False: Counter()}
        atk_pair = defaultdict(int)
        gap_atk = Counter()
        for b, p, q, n, ok, troops in R["atk"]:
            if p not in own_set or not online(p, b):
                continue
            on = prot_at(b)
            k = kind(p, q, b)
            atk[on][k] += n
            atk[on][k + "|ok"] += ok
            if q < H:
                atk_pair[(p, q)] += n
            i = snap_i(b)
            if loose[i] and not strict[i] and k in PE_KINDS:
                gap_atk["atk"] += n
        boat = {True: Counter(), False: Counter()}
        for t, p, dest, ok, troops in R["boats"]:
            if p not in own_set or not online(p, t) or not ok:
                continue
            on = prot_at(t)
            k = kind(p, dest, t)
            boat[on][k] += 1
            boat[on][k + "|troops"] += troops
        landc = {True: Counter(), False: Counter()}
        land_pair = defaultdict(int)
        for t, p, q, troops, got in R["lands"]:
            if p not in own_set or not online(p, t):
                continue
            on = prot_at(t)
            k = "noland" if q < 0 else kind(p, q, t)
            landc[on][k] += 1
            landc[on][k + "|troops"] += troops
            if 0 <= q < H:
                land_pair[(p, q)] += 1
        for on in (True, False):
            tot_atk[on].update(atk[on])
            tot_boat[on].update(boat[on])
            tot_land[on].update(landc[on])

        # [NP-E] 保护开着时从 PE 手里吃到的地是怎么来的
        origin = Counter()
        origin_tiles = Counter()
        for (p, q), tiles in gain_pairs.items():
            a, l = atk_pair.get((p, q), 0), land_pair.get((p, q), 0)
            k = "陆攻和靠岸都有" if a and l else ("只有船靠岸" if l else ("只有陆攻指令" if a else "两样都没有"))
            origin[k] += 1
            origin_tiles[k] += tiles
        tot_origin.update(origin)
        tot_origin_tiles.update(origin_tiles)

        # [NP-F] 捐兵
        don = Counter()
        don_amt = Counter()
        for t, p, q, ok, got, fee, b0 in R["dons"]:
            if p not in own_set or q >= H or not online(p, t):
                continue
            shell = not online(q, t)
            if not same_team(p, q):
                k = "跨队（引擎不收）"
            elif q in own_set:
                k = "同队我方空壳" if shell else "同队我方"
            elif in_pool[q]:
                k = "同队·池名无日志席位" + ("（空壳）" if shell else "")
            else:
                k = "同队的池外真人" + ("（空壳）" if shell else "")
            don[k] += 1
            don[k + "|ok"] += ok
            don_amt[k + "|got"] += got
            don_amt[k + "|fee"] += fee
        tot_don.update(don)
        tot_don_amt.update(don_amt)
        husk = Counter()
        husk_amt = Counter()
        for t, p, q, b0, got in R["husk"]:
            if p >= H or p not in own_set:
                continue                           # 只看我方号离开后的空壳
            if q >= H:
                k = "给内置 AI"
            elif q in own_set:
                k = "给我方在线的号" if online(q, t) else "给我方的另一个空壳"
            elif in_pool[q]:
                k = "给池名无日志席位"
            else:
                k = "给队里的池外真人" + ("" if online(q, t) else "（空壳）")
            husk[k] += 1
            husk_amt[k + "|gave"] += b0
            husk_amt[k + "|got"] += got
        tot_husk.update(husk)
        tot_husk_amt.update(husk_amt)
        # [NP-I] 池名无日志席位自己怎么打（c110 的号在保护开着时不对池里的名字发陆攻；发了，就不是跑这份规则的号）
        for s in ul:
            c = Counter()
            for b_, p, q, n, ok, troops in R["atk"]:
                if p != s:
                    continue
                if q in own_set:
                    c["own_on" if prot_at(b_) else "own_off"] += n
                    c["own_ok"] += ok
                    c["own_troops"] += troops
                elif q >= 512 or q < 0:
                    c["neutral"] += n
                elif q >= H:
                    c["AI"] += n
                elif in_pool[q]:
                    c["ul"] += n
                else:
                    c["outsider"] += n
            for b_, p, q, tiles, burnt, dB in R["flows"]:
                if tiles <= 0:
                    continue
                if p == s and q in own_set:
                    c["took_on" if online(q, b_) else "took_shell"] += tiles
                if q == s and p in own_set:
                    c["gave"] += tiles
            for t, p, q, troops, got in R["lands"]:
                if p == s and q in own_set:
                    c["landOwn"] += 1
            ul_rows.append((mid, s, names[s], left[s], c))

        gap_n = sum(1 for i in range(len(snapT)) if loose[i] and not strict[i])
        tot_gap["snaps"] += gap_n
        tot_gap["matches"] += 1 if gap_n else 0
        tot_gap["atk"] += gap_atk["atk"]

        own_teams = Counter(teams[s] for s in own) if team_game else Counter({0: len(own)})
        samples = sum(c["samples"] for c in m_contact)
        early = sum(1 for s in own if 0 <= left[s] <= 400)
        row = dict(mid=mid, H=H, teamGame=team_game, nTeams=R["nTeams"], end=end, rec=rec, cut=cut, exact=R.get("exact"), mismT=R.get("mismT"), own=len(own), ownSq=len(sq), ownTeams=len(own_teams), ownLargest=max(own_teams.values()),
                   ul=len(ul), outsiders=len(outsiders), ownLeft=sum(1 for s in own if left[s] >= 0), ownLeftEarly=early, tOff=t_off, tOffLoose=t_off_loose, gapSnaps=gap_n,
                   samples=samples, touchPE=sum(c["touchPE"] for c in m_contact), onlyPE=sum(c["onlyPE"] for c in m_contact),
                   lostPE=sum(lost[True][k] for k in PE_KINDS), lostPEoff=sum(lost[False][k] for k in PE_KINDS),
                   lostAll=sum(v for on in (True, False) for k, v in lost[on].items() if k != "neutral"),
                   lostWild=sum(lost[on][k] for on in (True, False) for k in WILD_KINDS),
                   lostAI=sum(lost[on]["AI"] for on in (True, False)),
                   gainPE_on=sum(gain[True][k] for k in PE_KINDS), gainPE_off=sum(gain[False][k] for k in PE_KINDS),
                   atkPE_on=sum(atk[True][k] for k in PE_KINDS), atkPE_off=sum(atk[False][k] for k in PE_KINDS),
                   boatPE_on=sum(boat[True][k] for k in PE_KINDS), landPE_on=sum(landc[True][k] for k in PE_KINDS),
                   donX=don["跨队（引擎不收）"], donAll=sum(v for k, v in don.items() if "|" not in k))
        rows.append(row)
        J["matches"][mid] = row

    n_used = len(rows)
    try:
        extra = [r[0] for r in json.load(open(os.path.join(OUT, "_run", "fid_extra.json"), encoding="utf-8")) if r[2] == "squad20"]
    except Exception:
        extra = []
    have_extra = [x for x in extra if x in J["matches"]]
    miss_extra = [x for x in extra if x not in J["matches"]]
    borrowed = [r for r in rows if r["rec"] != r["mid"]]
    cut_rows = [r for r in rows if r["cut"] is not None]
    P(f"namepool.py — 「名字池误认」的真相口径账：squad20（c110）有对局段且重演对得上的 {n_used} 局（整局重演）" + (f"；另有 {len(old)} 局的原料还是旧版、没算进来：{' '.join(old)}" if old else ""))
    P()
    P("[NP-A] 名册")
    P(f"  {n_used} 局里，自己的录像有对局段的 {n_used - len(have_extra)} 局"
      + (f"，自己的录像只有出生期、用同房另一份包的录像重演的 {len(have_extra)} 局（{' '.join(have_extra)}）" if have_extra else "")
      + (f"；还在后台排队的 {len(miss_extra)} 局（{' '.join(miss_extra)}）" if miss_extra else ""))
    P(f"  用同房另一份包更长的录像重演的 {len(borrowed)} 局（roompairs.py）"
      + ("：" + "；".join(f"{r['mid']} ← {r['rec']}（日志逐行核对 {r['exact'][0]} / {r['exact'][1]}" + (f"，第一次对不上在 {r['mismT']} 拍" if r["mismT"] is not None else "") + "）" for r in borrowed) if borrowed else ""))
    P(f"  模拟器的重演中途和真引擎对不上、只算到那一拍之前的 {len(cut_rows)} 局" + ("：" + "；".join(f"{r['mid']}（录像 {r['rec']}）算到 {r['cut']} 拍" for r in cut_rows) if cut_rows else ""))
    tg = [r for r in rows if r["teamGame"]]
    n_own = sum(r["own"] for r in rows)
    P(f"  组队局 {len(tg)}、自由混战 {len(rows) - len(tg)}；我方号合计 {n_own} 个（重演器认出来的 {sum(r['ownSq'] for r in rows)} 个 + 只在对局包席位表里的 {n_own - sum(r['ownSq'] for r in rows)} 个）；"
      f"中途离开的 {sum(r['ownLeft'] for r in rows)} 个，其中 400 拍以前就离开的 {sum(r['ownLeftEarly'] for r in rows)} 个")
    P("  每局进到同一个房间的我方号个数：" + " ".join(str(x) for x in sorted(r["own"] for r in rows)))
    if tg:
        P("  组队局里我方号分在几个队：" + "；".join(f"{k} 个队 {v} 局" for k, v in sorted(Counter(r['ownTeams'] for r in tg).items()))
          + f"；最大的一块占我方号的比例 中位 {sorted(r['ownLargest'] / r['own'] for r in tg)[len(tg) // 2]:.2f}")
    P(f"  名字在池里、包里没有日志的席位：有的局 {sum(1 for r in rows if r['ul'])} / {len(rows)}，合计 {len(unlogged)} 个席位：")
    for mid, s, nm, lt, mx, tm, ot in unlogged:
        P(f"    {mid} #{s} {nm}｜{'没离开' if lt < 0 else f'{lt} 拍离开'}｜整局最大 {mx} 格" + ("" if tm is None else f"｜在第 {tm} 队（我方号所在的队：{ot}）"))
    off = [r for r in rows if r["tOff"] is not None]
    P(f"  保护解除（主口径：场上不再有占地 ≥80、没离开的池外真人）发生过的局 {len(off)} / {len(rows)}" + ("：" + "；".join(f"{r['mid']} 在 {r['tOff']} 拍（录像 {r['end']} 拍）" for r in off) if off else ""))
    offl = [r for r in rows if r["tOffLoose"] is not None]
    P(f"  宽口径（离开的池外席位也算）下解除过的局 {len(offl)} / {len(rows)}" + ("：" + "；".join(f"{r['mid']} 在 {r['tOffLoose']} 拍" for r in offl) if offl else ""))
    J["roster"] = dict(matches=n_used, own=n_own, ownLeft=sum(r["ownLeft"] for r in rows), ownLeftEarly=sum(r["ownLeftEarly"] for r in rows), unlogged=len(unlogged),
                       protOffMatches=[r["mid"] for r in off], protOffLooseMatches=[r["mid"] for r in offl])
    P()
    P("[NP-B] 接触：我方在线、有地的号 × 每 90 拍一个样本")
    P("  时段 | 样本 | 贴着 PE（受保护的引擎敌人）的 | 其中 PE 是：跨队我方在线 / 跨队我方空壳 / 池名无日志在线 / 池名无日志空壳 | 只剩 PE 可打的（没有无主地、内置 AI、不受保护的真人）| 保护已解除的样本")
    for i, (cn, _, _) in enumerate(PERIODS):
        c = tot_contact[i]
        n = c["samples"]
        P(f"  {cn} | {n} | {c['touchPE']}（{pct(c['touchPE'], n)}）| {c['touch_ownx_on']} / {c['touch_ownx_shell']} / {c['touch_ulx_on']} / {c['touch_ulx_shell']} | {c['onlyPE']}（{pct(c['onlyPE'], n)}）| {c['protOff']}")
    n = sum(c["samples"] for c in tot_contact)
    tp = sum(c["touchPE"] for c in tot_contact)
    op = sum(c["onlyPE"] for c in tot_contact)
    P(f"  合计 | {n} | {tp}（{pct(tp, n)}）| {sum(c['touch_ownx_on'] for c in tot_contact)} / {sum(c['touch_ownx_shell'] for c in tot_contact)} / {sum(c['touch_ulx_on'] for c in tot_contact)} / {sum(c['touch_ulx_shell'] for c in tot_contact)} | {op}（{pct(op, n)}）| {sum(c['protOff'] for c in tot_contact)}")
    J["contact"] = dict(samples=n, touchPE=tp, onlyPE=op, byPeriod=[dict(c) for c in tot_contact])
    P()
    P("[NP-C] 地的流水（格）：我方在线的号被谁吃走、从谁手里吃到")
    P("  对方的种类 | 保护开着：我方被吃走 / 我方吃到 | 保护解除以后：我方被吃走 / 我方吃到")
    for k in KINDS:
        if k == "neutral":
            continue
        a, b, c, d = tot_lost[True][k], tot_gain[True][k], tot_lost[False][k], tot_gain[False][k]
        if a + b + c + d == 0:
            continue
        P(f"  {KIND_CN[k]} | {a} / {b} | {c} / {d}")
    lost_all = sum(v for on in (True, False) for k, v in tot_lost[on].items() if k != "neutral")
    lost_pe = sum(tot_lost[True][k] for k in PE_KINDS)
    gain_pe = sum(tot_gain[True][k] for k in PE_KINDS)
    lost_pe_off = sum(tot_lost[False][k] for k in PE_KINDS)
    gain_pe_off = sum(tot_gain[False][k] for k in PE_KINDS)
    lost_wild = sum(tot_lost[on][k] for on in (True, False) for k in WILD_KINDS)
    lost_ai = sum(tot_lost[on]["AI"] for on in (True, False))
    rest = lost_all - lost_ai - lost_wild - lost_pe - lost_pe_off
    P(f"  合计：我方在线的号被别的玩家吃走 {lost_all} 格 = 内置 AI {lost_ai}（{pct(lost_ai, lost_all)}）+ 野人和 [APEX]（含空壳）{lost_wild}（{pct(lost_wild, lost_all)}）"
      f"+ 保护开着时的 PE {lost_pe}（{pct(lost_pe, lost_all, 1)}）+ 保护解除后的池内跨队席位 {lost_pe_off}（{pct(lost_pe_off, lost_all, 1)}）+ 其它 {rest}")
    P(f"  保护开着时：我方在线的号被 PE 吃走 {lost_pe} 格，从 PE 手里吃到 {gain_pe} 格；被 PE 吃走的按对方：" + "；".join(f"{KIND_CN[k]} {tot_lost[True][k]}" for k in PE_KINDS))
    P("  我方在线的号被池内跨队席位吃走的格按时段（不分保护开没开）：" + "；".join(
        f"{cn} {sum(tot_lost_p[i][k] for k in PE_KINDS)}（同段被野人和 [APEX] 吃走 {sum(tot_lost_p[i][k] for k in WILD_KINDS)}，被内置 AI {tot_lost_p[i]['AI']}）" for i, (cn, _, _) in enumerate(PERIODS)))
    P(f"  跨队的我方号之间的战损（进攻方、被打方都是我方号，不论在线还是空壳）：保护开着时换手 {tot_xfight['on|tiles']} 格，进攻方烧掉 {tot_xfight['on|burnt']} 兵，被打方掉了 {tot_xfight['on|dB']} 余额；"
      f"保护解除以后换手 {tot_xfight['off|tiles']} 格，进攻方烧掉 {tot_xfight['off|burnt']} 兵，被打方掉了 {tot_xfight['off|dB']} 余额")
    J["xfight"] = dict(tot_xfight)
    J["flow"] = dict(lostAll=lost_all, lostAI=lost_ai, lostWild=lost_wild, lostPE=lost_pe, gainPE=gain_pe, lostPEoff=lost_pe_off, gainPEoff=gain_pe_off,
                     lostOn={k: tot_lost[True][k] for k in KINDS}, gainOn={k: tot_gain[True][k] for k in KINDS},
                     lostOff={k: tot_lost[False][k] for k in KINDS}, gainOff={k: tot_gain[False][k] for k in KINDS})
    P()
    P("[NP-D] 我方在线的号发的指令（录像里落地的）按对方的种类")
    P("  对方的种类 | 陆攻条数（其中生效的）：保护开着 / 解除以后 | 发成的船（发船那一拍目的地那一格是谁的）：保护开着 / 解除以后 | 船靠岸（靠岸那一格是谁的）：保护开着 / 解除以后")
    for k in KINDS + ["noland"]:
        vals = [tot_atk[True][k], tot_atk[False][k], tot_boat[True][k], tot_boat[False][k], tot_land[True][k], tot_land[False][k]]
        if not any(vals):
            continue
        P(f"  {KIND_CN.get(k, '靠在不能占的格上')} | {vals[0]}（{tot_atk[True][k + '|ok']}）/ {vals[1]}（{tot_atk[False][k + '|ok']}）| {vals[2]} / {vals[3]} | {vals[4]} / {vals[5]}")
    atk_pe_on = sum(tot_atk[True][k] for k in PE_KINDS)
    boat_pe_on = sum(tot_boat[True][k] for k in PE_KINDS)
    land_pe_on = sum(tot_land[True][k] for k in PE_KINDS)
    land_pe_troops = sum(tot_land[True][k + "|troops"] for k in PE_KINDS)
    P(f"  保护开着时对 PE：陆攻 {atk_pe_on} 条；发船时目的地是 PE 的地 {boat_pe_on} 艘；靠岸时那一格是 PE 的地 {land_pe_on} 艘（船上 {land_pe_troops} 兵）")
    land_changed = max(0, land_pe_on - boat_pe_on)
    P(f"  靠岸数减去发船数 = {land_changed}：靠在 PE 地上的船里至少这么多艘，发船那一拍目的地那一格还不是 PE 的（途中换了主人）；"
      f"同一时期靠在同队我方号地上的船 {tot_land[True]['ownteam_on']} 艘（引擎把船上的兵交给地的主人），发船那一拍目的地已经是同队我方号的地的 {tot_boat[True]['ownteam_on']} 艘")
    J["cmd"] = dict(atkOn={k: tot_atk[True][k] for k in KINDS}, atkOff={k: tot_atk[False][k] for k in KINDS},
                    boatOn={k: tot_boat[True][k] for k in KINDS}, boatOff={k: tot_boat[False][k] for k in KINDS},
                    landOn={k: tot_land[True][k] for k in KINDS}, landOff={k: tot_land[False][k] for k in KINDS},
                    atkPEon=atk_pe_on, boatPEon=boat_pe_on, landPEon=land_pe_on, landPEonTroops=land_pe_troops)
    P()
    P("[NP-E] 保护开着时我方在线的号从 PE 手里吃到的地是怎么来的（按「我方号 → PE 席位」这一对整局有没有陆攻指令、有没有船靠在它的地上）")
    for k in ("只有船靠岸", "陆攻和靠岸都有", "只有陆攻指令", "两样都没有"):
        P(f"  {k} | {tot_origin[k]} 对 | {tot_origin_tiles[k]} 格（{pct(tot_origin_tiles[k], sum(tot_origin_tiles.values()))}）")
    J["origin"] = dict(pairs=dict(tot_origin), tiles=dict(tot_origin_tiles))
    P()
    P("[NP-F] 捐兵（录像里落地的指令；重演结算）")
    P("  我方在线的号捐给谁 | 条数 | 成交 | 到账 | 损耗")
    for k in ("同队我方", "同队我方空壳", "同队·池名无日志席位", "同队·池名无日志席位（空壳）", "同队的池外真人", "同队的池外真人（空壳）", "跨队（引擎不收）"):
        if tot_don[k]:
            P(f"  {k} | {tot_don[k]} | {tot_don[k + '|ok']} | {tot_don_amt[k + '|got']} | {tot_don_amt[k + '|fee']}")
    P("  我方号离开后的空壳把余额给了谁（引擎的内置 AI 逻辑：没有可打的目标就把余额交给队友）| 次数 | 交出去的余额 | 对方到账")
    for k in ("给我方在线的号", "给我方的另一个空壳", "给池名无日志席位", "给队里的池外真人", "给队里的池外真人（空壳）", "给内置 AI"):
        if tot_husk[k]:
            P(f"  {k} | {tot_husk[k]} | {tot_husk_amt[k + '|gave']} | {tot_husk_amt[k + '|got']}")
    J["don"] = {k: v for k, v in tot_don.items()}
    J["donAmt"] = {k: v for k, v in tot_don_amt.items()}
    J["husk"] = {k: v for k, v in tot_husk.items()}
    J["huskAmt"] = {k: v for k, v in tot_husk_amt.items()}
    P()
    P("[NP-G] 两种保护口径分得开的地方：池外真人里占地 ≥80 的只剩空壳（主口径 = 保护已解除，宽口径 = 保护还开着）")
    gs = sum(c["gap"] for c in tot_contact)
    gt = sum(c["gapTouch"] for c in tot_contact)
    P(f"  这样的 90 拍快照 {tot_gap['snaps']} 个，分布在 {tot_gap['matches']} 局；落在里面的我方在线接触样本 {gs} 个，其中贴着池内跨队席位的 {gt} 个；"
      f"这些窗里我方在线的号对池内跨队席位的陆攻 {tot_gap['atk']} 条")
    J["gap"] = dict(snaps=tot_gap["snaps"], matches=tot_gap["matches"], samples=gs, touch=gt, atk=tot_gap["atk"])
    P()
    P("[NP-I] 名字在池里、包里没有日志的席位自己怎么打（c110 的号在保护开着时不对池里的名字发陆攻；所以对我方号发过陆攻的席位，跑的不是这份规则）")
    P("  局 席位 名字 | 陆攻条数：对我方号（保护开着 / 解除后；其中生效；出兵）/ 对别的池名席位 / 对池外真人 / 对内置 AI / 对无主地 | 船靠在我方号的地上 | 从我方号手里吃到的格：在线的 / 空壳的 | 被我方号吃走的格")
    hit = []
    for mid, s, nm, lt, c in ul_rows:
        P(f"  {mid} #{s} {nm} | {c['own_on']} / {c['own_off']}（生效 {c['own_ok']}；出兵 {c['own_troops']}）/ {c['ul']} / {c['outsider']} / {c['AI']} / {c['neutral']} | {c['landOwn']} | {c['took_on']} / {c['took_shell']} | {c['gave']}")
        if c["own_on"]:
            hit.append((mid, s, nm, c))
    n_cmd = sum(1 for _, _, _, _, c in ul_rows if c["own_on"] + c["own_off"] + c["ul"] + c["outsider"] + c["AI"] + c["neutral"])
    P(f"  合计 {len(ul_rows)} 个席位，录像里有过陆攻指令的 {n_cmd} 个；保护开着时对我方号发过陆攻的 {len(hit)} 个，共 {sum(c['own_on'] for _, _, _, c in hit)} 条"
      f"（生效 {sum(c['own_ok'] for _, _, _, c in hit)} 条，出兵 {sum(c['own_troops'] for _, _, _, c in hit)}），从我方在线的号手里吃到 {sum(c['took_on'] for _, _, _, c in hit)} 格；"
      f"同一批席位被我方号吃走 {sum(c['gave'] for _, _, _, c in hit)} 格")
    rest = [(mid, s, nm, c) for mid, s, nm, lt, c in ul_rows if not c["own_on"]]
    P(f"  保护开着时没有对我方号发过陆攻的 {len(rest)} 个席位：从我方在线的号手里吃到 {sum(c['took_on'] for _, _, _, c in rest)} 格（船靠在我方号的地上 {sum(c['landOwn'] for _, _, _, c in rest)} 艘），被我方号吃走 {sum(c['gave'] for _, _, _, c in rest)} 格")
    J["unloggedBehaviour"] = [dict(mid=mid, seat=s, name=nm, left=lt, **{k: int(v) for k, v in c.items()}) for mid, s, nm, lt, c in ul_rows]
    P()
    P("[NP-J] 组队局和自由混战分开（保护开着时的量；逐局数字加起来）")
    P("  房间 | 局 | 接触样本 | 贴着 PE | 只剩 PE 可打 | 我方在线的号被别的玩家吃走的格 | 其中保护开着时被 PE 吃走 | 保护开着时从 PE 吃到 | 保护开着时对 PE 的陆攻 | 保护开着时船靠在 PE 的地上 | 保护解除过的局")
    J["byMode"] = {}
    mode_table = []
    for label, sel in (("组队局", lambda r: r["teamGame"]), ("自由混战", lambda r: not r["teamGame"])):
        rs = [r for r in rows if sel(r)]
        if not rs:
            continue
        d = {k: sum(r[k] for r in rs) for k in ("samples", "touchPE", "onlyPE", "lostAll", "lostPE", "gainPE_on", "atkPE_on", "landPE_on")}
        d["matches"] = len(rs)
        d["off"] = sum(1 for r in rs if r["tOff"] is not None)
        cells = [str(len(rs)), str(d["samples"]), f"{d['touchPE']}（{pct(d['touchPE'], d['samples'])}）", f"{d['onlyPE']}（{pct(d['onlyPE'], d['samples'])}）", str(d["lostAll"]),
                 f"{d['lostPE']}（{pct(d['lostPE'], d['lostAll'], 1)}）", str(d["gainPE_on"]), str(d["atkPE_on"]), str(d["landPE_on"]), str(d["off"])]
        P(f"  {label} | " + " | ".join(cells))
        mode_table.append(f"| {label} | " + " | ".join(cells) + " |")
        J["byMode"][label] = d
    P()
    P("[NP-H] 逐局：局 | 真人 | 队数 | 算到哪一拍（录像取自别的包 / 截短的另注）| 我方号（分在几个队 / 最大一块）| 离开的我方号（400 拍以前）| 池名无日志席位 | 保护解除的拍 主口径 / 宽口径 | 接触样本 | 贴着 PE | 只剩 PE 可打 | "
      "我方在线的号被吃走的格：全部 / 内置 AI / 野人 / 保护开着时的 PE / 解除后的池内跨队席位 | 保护开着时从 PE 吃到 | 保护开着时对 PE：陆攻 / 靠岸 | 解除后对池内跨队席位的陆攻 | 跨队捐兵 / 全部捐兵")
    for r in sorted(rows, key=lambda r: r["mid"]):
        note = (f"（录像取自 {r['rec']}）" if r["rec"] != r["mid"] else "") + ("（截短）" if r["cut"] is not None else "")
        P(f"  {r['mid']} | {r['H']} | {r['nTeams'] if r['teamGame'] else '混战'} | {r['end']}{note} | {r['own']}（{r['ownTeams']} / {r['ownLargest']}）| {r['ownLeft']}（{r['ownLeftEarly']}）| {r['ul']} | "
          f"{r['tOff'] if r['tOff'] is not None else '–'} / {r['tOffLoose'] if r['tOffLoose'] is not None else '–'} | {r['samples']} | {pct(r['touchPE'], r['samples'])} | {pct(r['onlyPE'], r['samples'])} | "
          f"{r['lostAll']} / {r['lostAI']} / {r['lostWild']} / {r['lostPE']} / {r['lostPEoff']} | {r['gainPE_on']} | {r['atkPE_on']} / {r['landPE_on']} | {r['atkPE_off']} | {r['donX']} / {r['donAll']}")

    # 会审稿用的填空（council_fill.py 读）：每一项都和上面打印出来的写法一模一样
    late_c = tot_contact[len(PERIODS) - 1]
    all_tiles = sum(tot_origin_tiles.values())
    J["report"] = {
        "NP_N": str(n_used), "NP_OLD_N": str(len(old)), "NP_OLD": " ".join(old), "NP_ALL": str(n_used + len(old)),
        "NP_COVER": (f"squad20 自己的录像有对局段、重演对得上的 {n_used - len(have_extra) + len(old)} 局" + (f"里的 {n_used - len(have_extra)} 局" if old else "")
                     + (f"，加上 {len(have_extra)} 局自己的录像只有出生期、用同房另一份包的录像重演的（{' '.join(have_extra)}），合计 {n_used} 局" if have_extra else "")
                     + f"：组队局 {len(tg)}、自由混战 {len(rows) - len(tg)}"
                     + (f"；另外 {len(old + miss_extra)} 局（{' '.join(old + miss_extra)}）的重演还在后台排队，没算进来" if old or miss_extra else "")
                     + (f"。用同房另一份包更长的录像重演的 {len(borrowed)} 局（" + "；".join(f"{r['mid']} ← {r['rec']}" for r in borrowed) + "）" if borrowed else "")
                     + ("。" + "；".join(f"{r['mid']} 用的那份录像（{r['rec']}）模拟器从 {r['cut']} 拍起和真引擎对不上，只算到那一拍" for r in cut_rows) if cut_rows else "")),
        "NP_MODE_TABLE": "\n".join(mode_table),
        "NP_LAND_MATE": str(tot_land[True]["ownteam_on"]), "NP_BOAT_MATE": str(tot_boat[True]["ownteam_on"]), "NP_LAND_CHANGED": str(land_changed),
        "NP_TEAM_N": str(len(tg)), "NP_FFA_N": str(len(rows) - len(tg)),
        "NP_OWN": str(n_own), "NP_OWN_LEFT": str(sum(r["ownLeft"] for r in rows)),
        "NP_SAMPLES": str(n), "NP_TOUCH": f"{tp}（{pct(tp, n)}）", "NP_ONLY": f"{op}（{pct(op, n)}）",
        "NP_ONLY_LATE": f"{late_c['onlyPE']}（{pct(late_c['onlyPE'], late_c['samples'])}）", "NP_LATE_SAMPLES": str(late_c["samples"]),
        "NP_TOUCH_BY": " / ".join(pct(c["touchPE"], c["samples"]) for c in tot_contact),
        "NP_ONLY_BY": " / ".join(pct(c["onlyPE"], c["samples"]) for c in tot_contact),
        "NP_OFF": f"{len(off)} / {len(rows)}" + ("（" + "；".join(f"{r['mid']} 在 {r['tOff']} 拍" for r in off) + "）" if off else ""),
        "NP_ATK": str(atk_pe_on), "NP_BOAT": str(boat_pe_on), "NP_LAND": str(land_pe_on), "NP_LAND_TROOPS": str(land_pe_troops),
        "NP_GAIN_PE": str(gain_pe), "NP_ORIGIN_PAIRS": str(tot_origin["只有船靠岸"]), "NP_ORIGIN_TILES": str(tot_origin_tiles["只有船靠岸"]),
        "NP_ORIGIN_PCT": pct(tot_origin_tiles["只有船靠岸"], all_tiles),
        "NP_X_TILES": str(tot_xfight["on|tiles"]), "NP_X_BURNT": str(tot_xfight["on|burnt"]), "NP_X_DB": str(tot_xfight["on|dB"]),
        "NP_XOFF_TILES": str(tot_xfight["off|tiles"]), "NP_XOFF_BURNT": str(tot_xfight["off|burnt"]),
        "NP_LOST_ALL": str(lost_all), "NP_LOST_PE": str(lost_pe), "NP_LOST_PE_PCT": pct(lost_pe, lost_all, 1),
        "NP_LOST_PEOFF": str(lost_pe_off), "NP_LOST_PEOFF_PCT": pct(lost_pe_off, lost_all, 1),
        "NP_LOST_AI_PCT": pct(lost_ai, lost_all), "NP_LOST_WILD_PCT": pct(lost_wild, lost_all),
        "NP_LOST_OWNX": str(tot_lost[True]["ownx_on"]), "NP_LOST_SHELL": str(tot_lost[True]["ownx_shell"]), "NP_GAIN_SHELL": str(tot_gain[True]["ownx_shell"]),
        "NP_LOST_UL": str(tot_lost[True]["ulx_on"] + tot_lost[True]["ulx_shell"]),
        "NP_UL": str(len(ul_rows)), "NP_UL_M": f"{sum(1 for r in rows if r['ul'])} / {len(rows)}",
        "NP_UL_HIT": str(len(hit)), "NP_UL_ATK": str(sum(c["own_on"] for _, _, _, c in hit)), "NP_UL_TROOPS": str(sum(c["own_troops"] for _, _, _, c in hit)),
        "NP_UL_TOOK": str(sum(c["took_on"] for _, _, _, c in hit)), "NP_UL_GAVE": str(sum(c["gave"] for _, _, _, c in hit)),
        "NP_UL_REST": str(len(rest)), "NP_UL_REST_TOOK": str(sum(c["took_on"] for _, _, _, c in rest)),
    }

    os.makedirs(os.path.join(OUT, "_cross"), exist_ok=True)
    open(os.path.join(OUT, "_cross", "namepool.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump(J, open(os.path.join(OUT, "_cross", "namepool.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
