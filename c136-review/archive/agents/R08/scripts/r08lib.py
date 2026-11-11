#!/usr/bin/env python3
"""r08lib.py — R08 v2.0 公共库：读标准化对局包、日志标签→局内玩家号的身份还原、引擎公式。

数据只读自 /agent/repos/c136-data/bundles/<matchId>/（可用环境变量 C136_DATA 改根目录）。
所有行号都是 in_game.log 每行开头的原始日志行号。

身份还原（B 组必需）：20 号编队的日志前缀名（label）会在一局中途整体轮换，
同一个局内玩家（HL-GAME-INIT 的 me=）前后会用不同的 label 打日志。
这里按 HL-TICK 里的工作进程统计量（maxMs、cmds、boats、skip 单调不减）把 label 串回同一个玩家。
有全场真值（out/<局>/resim.json，见 resim_r08.mjs）时改用「指纹」：一条 HL-TICK 的 (拍, 领土, 余额)
在该拍全体真人里只对得上一个玩家，就直接认这个玩家；结算行（RESULT）按 results.csv 的 meId 列认。
"""
import csv
import json
import math
import os
import re
from collections import defaultdict

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

TICK_RE = re.compile(
    r"\[HL-TICK\] t=(\d+) terr=(\d+)\(([\d.]+)%\) bal=(-?\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)"
    r"(?: avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+))?")
LINE_RE = re.compile(r"^(\d+)\t(.*)$")
LABEL_RE = re.compile(r"^\[([^\]]+)\] \[(HL-[A-Z-]+)\] ?(.*)$")
RESULT_RE = re.compile(r"^\[RESULT (.+?)\] result=(\w+) event=(\w+) place=(\d+) peak=(\d+) team=(.*)$")
INIT_RE = re.compile(r"mode=(\d+) map=(\d+) mapSeed=(\d+) seeded=(\d+) me=(\d+)")
OPEN_RE = re.compile(r"t=(\d+) cyc=(\d+) DP expand rings=(\d+) spend=(\d+)/(\d+) terr=(\d+)")

# 同一个 label 在一局里先后被两个号用过（整体轮换名字时，一个号接了另一个号刚腾出来的名字）：
# 按日志行号切开，行号 >= 第二个数的那一段换成带 @2 的标签。依据写在右边。
LABEL_SPLITS = {
    # B027：L8600929 以前的 [Aztec] 是 32 号（maxMs=74.3、cmds=69）；L8600953 起的 [Aztec] 是 35 号
    #（maxMs=44.0、cmds=40、boats=3，接的是 [DemonHunter] t=5310 那一条），32 号同时改叫 [Croissant]。
    "B027": [("Aztec", 8600953, "Aztec@2")],
}
# 统筹的房间表把一个号的名字链断成两截（后半截被当成另一个房间的号）时，在这里接上。
ROOM_FIXES = {
    "B027": dict(names={32: ["player_007", "Aztec", "Croissant", "Starbucks"],
                        35: ["Raeder", "DemonHunter", "Aztec@2", "Ashoka"]},
                 dropRooms=[1], forceLabelMap=True),
}


def split_label(mid, label, line):
    for lab, from_line, new in LABEL_SPLITS.get(mid, ()):
        if label == lab and line >= from_line:
            return new
    return label


def bundle_dir(mid):
    for sub in ("bundles", "validation_bundles"):
        d = os.path.join(DATA, sub, mid)
        if os.path.isdir(d):
            return d
    raise FileNotFoundError(mid)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except ValueError:
        return v
    return int(f) if f == int(f) and re.fullmatch(r"-?\d+", str(v)) else f


def load_card(mid):
    with open(os.path.join(bundle_dir(mid), "card.json"), encoding="utf-8") as f:
        return json.load(f)


def load_results(mid):
    rows = read_csv(os.path.join(bundle_dir(mid), "results.csv"))
    out = []
    for r in rows:
        o = {k: num(v) for k, v in r.items()}
        tt = r.get("teamTotals")
        o["teamTotals"] = json.loads(tt) if tt else None
        out.append(o)
    return out


def parse_log(mid):
    """返回逐行解析结果列表：{line, label, tag, body, raw}（RESULT 行 tag='RESULT'）。"""
    out = []
    path = os.path.join(bundle_dir(mid), "in_game.log")
    with open(path, encoding="utf-8") as f:
        for idx, raw in enumerate(f):
            raw = raw.rstrip("\n")
            m = LINE_RE.match(raw)
            if not m:
                continue
            line, rest = int(m.group(1)), m.group(2)
            rec = {"line": line, "idx": idx, "raw": rest, "label": None, "tag": None, "body": rest}
            mr = RESULT_RE.match(rest)
            if mr:
                team = None
                try:
                    team = json.loads(mr.group(6))
                except Exception:  # noqa: BLE001
                    team = None
                rec.update(label=mr.group(1).replace("[Nope] ", ""), tag="RESULT", result=mr.group(2), event=mr.group(3),
                           place=int(mr.group(4)), peak=int(mr.group(5)), team=team)
            else:
                ml = LABEL_RE.match(rest)
                if ml:
                    rec.update(label=ml.group(1), tag=ml.group(2), body=ml.group(3))
                elif rest.startswith("[BACKEND-SPAWN-COORD]"):
                    rec["tag"] = "BACKEND-SPAWN-COORD"
                elif rest.startswith("[OPENING-CHECK"):
                    rec["tag"] = "OPENING-CHECK"
            if rec["label"] is not None and mid in LABEL_SPLITS:
                rec["label"] = split_label(mid, rec["label"], line)
            if rec["tag"] == "HL-TICK":
                mt = TICK_RE.search(rest)
                if mt:
                    g = mt.groups()
                    rec["tick"] = dict(t=int(g[0]), terr=int(g[1]), pct=float(g[2]), bal=int(g[3]), dens=float(g[4]),
                                       nb=int(g[5]), neut=int(g[6]), cmds=int(g[7]), boats=int(g[8]),
                                       avgMs=float(g[9]) if g[9] else None, maxMs=float(g[10]) if g[10] else None,
                                       skip=int(g[11]) if g[11] else None)
            elif rec["tag"] == "HL-GAME-INIT":
                mi = INIT_RE.search(rest)
                if mi:
                    rec["init"] = dict(mode=int(mi.group(1)), map=int(mi.group(2)), mapSeed=int(mi.group(3)),
                                       seeded=int(mi.group(4)), me=int(mi.group(5)))
            out.append(rec)
    return out


def load_truth(mid):
    """读 out/<mid>/resim.json（没有就返回 None）。"""
    path = os.path.join(OUT, mid, "resim.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fingerprints(R):
    """{拍: {(领土, 余额): [玩家号...]}}，只收真人。"""
    fp = {}
    H = R["H"]
    for i, t in enumerate(R["snapT"]):
        d = fp.setdefault(t, {})
        terr, bal = R["snapTerr"][i], R["snapBal"][i]
        for p in range(H):
            if terr[p] > 0:
                d.setdefault((terr[p], bal[p]), []).append(p)
    return fp


class Track:
    """一个局内玩家（一个工作进程）的全部日志。"""

    def __init__(self, me, label):
        self.me = me
        self.labels = [label]
        self.ticks = []      # HL-TICK dict（附 line、label）
        self.lines = []      # 全部归属的日志记录
        self.result = None
        self.last = None     # 最近一条 HL-TICK
        self.closed = False

    @property
    def name(self):
        return self.labels[0]


def _consistent(tr, s):
    """s（新的 HL-TICK）能否接在轨迹 tr 的最近一条 HL-TICK 后面。"""
    l = tr.last
    if l is None:
        return True
    if s["t"] <= l["t"]:
        return False
    if s["cmds"] < l["cmds"] or s["boats"] < l["boats"]:
        return False
    if s["maxMs"] is not None and l["maxMs"] is not None and s["maxMs"] < l["maxMs"] - 1e-9:
        return False
    if s["skip"] is not None and l["skip"] is not None and s["skip"] < l["skip"]:
        return False
    return True


def _dist(tr, s):
    l = tr.last
    if l is None:
        return 1e6
    d = 0.0
    if s["maxMs"] is not None and l["maxMs"] is not None:
        d += 50.0 * abs(s["maxMs"] - l["maxMs"])
    d += 2.0 * (s["cmds"] - l["cmds"]) + 5.0 * (s["boats"] - l["boats"])
    d += 0.02 * abs(s["t"] - l["t"] - 90)
    d += 0.5 * abs(math.log((s["terr"] + 50) / (l["terr"] + 50))) * 100
    return d


ROOMS_JSON = os.path.join(DATA, "src", "tools", "rooms-discovery.json")
_ROOMS_CACHE = {}


def load_rooms(mid):
    """统筹分发的房间拆分表（rooms-discovery.json）里这一局的记录；没有就返回 None。"""
    if "all" not in _ROOMS_CACHE:
        try:
            with open(ROOMS_JSON, encoding="utf-8") as f:
                _ROOMS_CACHE["all"] = {m["matchId"]: m for m in json.load(f)}
        except OSError:
            _ROOMS_CACHE["all"] = {}
    m = _ROOMS_CACHE["all"].get(mid)
    fx = ROOM_FIXES.get(mid)
    if m and fx and not m.get("_fixed"):
        m = json.loads(json.dumps(m))
        m["rooms"] = [r for r in m["rooms"] if r["roomIdx"] not in fx.get("dropRooms", ())]
        for r in m["rooms"]:
            for b in r["bots"]:
                if b.get("me") in fx["names"]:
                    b["names"] = list(fx["names"][b["me"]])
            r["nBots"] = len(r["bots"])
        m["nRooms"] = len(m["rooms"])
        m["nBots"] = sum(len(r["bots"]) for r in m["rooms"])
        m["forceLabelMap"] = bool(fx.get("forceLabelMap"))
        m["_fixed"] = True
        _ROOMS_CACHE["all"][mid] = m
    return m


def _fix_rooms_by_replay(mid, rooms, main):
    """房间表（统筹按日志推的）和录像头对不上时，以录像头为准改主房间的成员。

    录像头的 names[号] 是这个房间里每个玩家号的真名。主房间里某个号的名字链不含录像里这个号的名字时：
    别的房间有同一个玩家号、名字对得上的号就换进来（原来那个换过去）；没有可换的（录像里这个号不是编队号）
    就把它挪到非主房间。返回 (新的房间表, 改动说明列表)；没有重演产物或不用改时原样返回。
    """
    tr = load_truth(mid)
    if not tr or (tr.get("replayFrom") or mid) != mid:
        return rooms, []
    names = [str(x).strip().lower() for x in tr["names"]]
    rooms = json.loads(json.dumps(rooms))
    by_idx = {r["roomIdx"]: r for r in rooms}
    if main not in by_idx:
        return rooms, []
    has = lambda b, nm: any(nm.endswith(str(x).strip().lower()) for x in b["names"])
    mr = by_idx[main]
    # 录像头和主房间至少有 2 个号对得上才动手（否则录像多半属于别的房间）
    if sum(1 for b in mr["bots"] if b.get("me") is not None and b["me"] < len(names) and has(b, names[b["me"]])) < 2:
        return rooms, []
    fixes = []
    for b in list(mr["bots"]):
        me = b.get("me")
        if me is None or me >= len(names) or has(b, names[me]):
            continue
        swap = None
        for r in rooms:
            if r["roomIdx"] == main:
                continue
            for b2 in r["bots"]:
                if b2.get("me") == me and has(b2, names[me]):
                    swap = (r, b2)
                    break
            if swap:
                break
        mr["bots"].remove(b)
        if swap:
            r, b2 = swap
            r["bots"].remove(b2)
            mr["bots"].append(b2)
            r["bots"].append(b)
            fixes.append(f"玩家号 {me}：房间表写 {b['names'][0]}，录像头是 {tr['names'][me]}；按录像把 {b2['names'][0]} 换进主房间")
        else:
            others = [r for r in rooms if r["roomIdx"] != main]
            dest = next((r for r in others if all(x.get("me") != me for x in r["bots"])), others[0] if others else None)
            if dest is not None:
                dest["bots"].append(b)
            fixes.append(f"玩家号 {me}：房间表写 {b['names'][0]}，录像头是 {tr['names'][me]}（不是编队号）；把 {b['names'][0]} 挪出主房间")
    return rooms, fixes


def room_label_map(mid):
    """一个对局包里混了几个物理房间（或某个房间没有 HL-GAME-INIT 行）时，按名字链表把 label 直接定到号。

    返回 (label_map, info)；不需要（单房间且每个号都有 init 行）时返回 (None, None)。
      label_map: {label: key}；info: {key: dict(room, me, names, team, land, seeded, pseudo)}
      key = 玩家号；房间表里没有玩家号的号（没有结算行也没有 init 行）用 1000+100×房间号+序号；
            不同房间撞玩家号时，非主房间的号 key = 10000×房间号 + 玩家号。
    同一个 label 出现在两个号的名字链里时，这个 label 不进 label_map（留给连续性判断），并记在 info['_collide']。
    """
    m = load_rooms(mid)
    if not m:
        return None, None
    if m.get("nRooms", 1) <= 1 and m.get("nInitNames", 0) >= m.get("nBots", 0) and not m.get("forceLabelMap"):
        return None, None
    main = m.get("mainRoom", 0)
    info, owner, collide = {}, {}, set()
    used = set()
    rooms, fixes = _fix_rooms_by_replay(mid, m["rooms"], main)
    order = sorted(rooms, key=lambda r: (r["roomIdx"] != main, r["roomIdx"]))
    for r in order:
        k = 0
        for b in r["bots"]:
            me = b.get("me")
            if me is None:
                k += 1
                key = 1000 + 100 * r["roomIdx"] + k
            else:
                key = me if me not in used else 10000 * r["roomIdx"] + me
            used.add(key)
            info[key] = dict(room=r["roomIdx"], me=me, names=list(b["names"]), team=b.get("team"), land=r.get("land"),
                             seeded=r.get("seeded"), pseudo=me is None)
            for nm in b["names"]:
                if nm in owner and owner[nm] != key:
                    collide.add(nm)
                owner[nm] = key
    for nm in collide:
        owner.pop(nm, None)
    info["_collide"] = sorted(collide)
    info["_main"] = main
    info["_replayFixes"] = fixes
    info["_rooms"] = {r["roomIdx"]: dict(land=r.get("land"), seeded=r.get("seeded"), nBots=r.get("nBots"), startUtc=r.get("startUtc"),
                                         lastTick=r.get("lastTick"), init=r.get("initKey"), winner=r.get("winner"),
                                         physRoom=r.get("physRoom")) for r in m["rooms"]}
    return owner, info


def resolve_identities(recs, fp=None, res_me=None, label_map=None):
    """把日志记录按玩家归并。返回 (tracks: {me: Track}, notes: [str], unresolved: [rec])。

    fp：fingerprints() 的结果（有全场真值时）；res_me：{结算行的 label: 玩家号}（results.csv 的 meId 列）；
    label_map：room_label_map() 的 {label: key}（多房间的包）。在表里的 label 直接归到那个号，
    只用 HL-TICK 的连续性做核对（不连续记进 notes），不再走指纹和连续性猜测。
    """
    tracks = {}
    cur = {}          # label -> me（当前绑定）
    pending = defaultdict(list)   # label -> 还没归属的记录
    notes = []
    unresolved = []
    if label_map:
        for r in recs:
            label, tag = r["label"], r["tag"]
            if label is None:
                continue
            key = label_map.get(label)
            if key is None:
                unresolved.append(r)
                continue
            tr = tracks.get(key)
            if tr is None:
                tr = tracks[key] = Track(key, label)
            elif tr.labels[-1] != label:
                notes.append(f"line {r['line']}: 号 {key} 的 label {tr.labels[-1]} -> {label}（名字链表）")
                tr.labels.append(label)
            if tag == "HL-TICK" and "tick" in r:
                s = r["tick"]
                if not _consistent(tr, s):
                    notes.append(f"line {r['line']}: 名字链表把 '{label}' t={s['t']} 归到号 {key}，但与它上一条 HL-TICK（t={tr.last['t']}）不连续")
                rec = dict(s)
                rec["line"] = r["line"]
                rec["label"] = label
                tr.ticks.append(rec)
                tr.last = rec
            elif tag == "RESULT":
                tr.result = r
                tr.closed = True
            tr.lines.append(r)
        return tracks, notes, unresolved

    def bind(label, me, why, line):
        old = cur.get(label)
        if old is not None and old != me:
            notes.append(f"line {line}: label '{label}' 由玩家 {old} 改绑到玩家 {me}（{why}）")
        for lab, m in list(cur.items()):
            if m == me and lab != label:
                del cur[lab]
        cur[label] = me
        tr = tracks[me]
        if tr.labels[-1] != label:
            tr.labels.append(label)
            notes.append(f"line {line}: 玩家 {me} 的 label {tr.labels[-2]} -> {label}（{why}）")
        for r in pending.pop(label, []):
            tr.lines.append(r)

    for r in recs:
        tag, label = r["tag"], r["label"]
        if tag == "HL-GAME-INIT" and "init" in r:
            me = r["init"]["me"]
            if me not in tracks:
                tracks[me] = Track(me, label)
            bind(label, me, "init", r["line"])
            tracks[me].lines.append(r)
            continue
        if label is None:
            continue
        mm = re.search(r"\bme=(\d+)\b", r["raw"]) if tag in ("HL-SPAWN", "HL-SPAWN-BACKEND") else None
        if mm:
            me = int(mm.group(1))
            if me not in tracks:
                tracks[me] = Track(me, label)
            if cur.get(label) != me:
                bind(label, me, "spawn me=", r["line"])
            tracks[me].lines.append(r)
            continue
        if tag == "HL-TICK" and "tick" in r:
            s = r["tick"]
            me = cur.get(label)
            cands_fp = (fp.get(s["t"], {}).get((s["terr"], s["bal"])) if fp else None) or []
            me_fp = None
            if len(cands_fp) == 1:
                me_fp = cands_fp[0]
            elif len(cands_fp) > 1:
                if me in cands_fp:
                    me_fp = me
                else:
                    ok = [c for c in cands_fp if c in tracks and not tracks[c].closed and _consistent(tracks[c], s)]
                    me_fp = ok[0] if len(ok) == 1 else None
            if me_fp is not None:
                if me_fp not in tracks:
                    tracks[me_fp] = Track(me_fp, label)
                if cur.get(label) != me_fp:
                    bind(label, me_fp, "指纹", r["line"])
                me = me_fp
            elif me is not None and not tracks[me].closed and _consistent(tracks[me], s):
                # label 当前绑定且连续
                pass
            else:
                cands = [tr for tr in tracks.values() if not tr.closed and _consistent(tr, s)
                         and (tr.last is None or tr.last["t"] < s["t"])]
                # 已经在本拍用别的 label 打过点的轨迹排除（由 _consistent 的 t 判断保证）
                if me is not None:
                    cands = [tr for tr in cands if tr.me != me] or cands
                if not cands:
                    unresolved.append(r)
                    continue
                cands.sort(key=lambda tr: _dist(tr, s))
                best = cands[0]
                if len(cands) > 1 and _dist(cands[1], s) - _dist(best, s) < 1.0:
                    notes.append(f"line {r['line']}: label '{label}' t={s['t']} 归属有歧义："
                                 f"{best.me}({_dist(best, s):.1f}) vs {cands[1].me}({_dist(cands[1], s):.1f})")
                bind(label, best.me, "HL-TICK 连续性", r["line"])
                me = best.me
            tr = tracks[me]
            rec = dict(s)
            rec["line"] = r["line"]
            rec["label"] = label
            tr.ticks.append(rec)
            tr.last = rec
            tr.lines.append(r)
            continue
        if tag == "RESULT":
            me = cur.get(label)
            if res_me and res_me.get(label) is not None and res_me[label] in tracks:
                me = res_me[label]
                if cur.get(label) != me:
                    bind(label, me, "results.csv meId", r["line"])
            elif me is None or tracks[me].closed:
                # 轮换后还没打过 HL-TICK 就结算：按 peak 与最后领土匹配
                cands = [tr for tr in tracks.values() if not tr.closed]
                best = None
                for tr in cands:
                    mx = max([x["terr"] for x in tr.ticks], default=0)
                    if mx <= r["peak"] and (best is None or mx > best[0]):
                        best = (mx, tr)
                if best is None:
                    unresolved.append(r)
                    continue
                me = best[1].me
                notes.append(f"line {r['line']}: RESULT '{label}' 按 peak={r['peak']} 归到玩家 {me}"
                             f"（该玩家日志峰值 {best[0]}）")
                bind(label, me, "RESULT peak 匹配", r["line"])
            tr = tracks[me]
            tr.result = r
            tr.lines.append(r)
            tr.closed = True
            continue
        me = cur.get(label)
        if me is None or tracks[me].closed:
            pending[label].append(r)
        else:
            tracks[me].lines.append(r)
    for label, rs in pending.items():
        unresolved.extend(rs)
    return tracks, notes, unresolved


# ---------------- 引擎公式（engine-evidence.txt 的编号） ----------------

def g0(a, b):
    """[C2] 整数除法 floor((a+0.5)/b)。"""
    return math.floor((a + 0.5) / b)


def isqrt_engine(n):
    """[C3] 牛顿迭代的整数开方（迭代 9 次，与 E3 的 aMh(x, 9) 一致）。"""
    if n <= 0:
        return 0
    ej = g0(n + 1, 2)
    for _ in range(9):
        if ej == 0:
            break
        ej = g0(ej + g0(n, ej), 2)
    return ej


def interest_rate(terr, land, bal, t):
    """[E3..E7] 每 10 拍利息率（万分之一）。"""
    i = g0(511 * terr, land)
    r = 100 + isqrt_engine(g0(i * 25600, 508))
    if t < 1920:
        r = max(g0(100 * (13440 - 6 * t), 1920), r)
    cap = min(100 * terr, 10 ** 9)
    if cap > 0 and bal > cap:
        r -= g0(2 * r * (bal - cap), cap)
    return min(max(r, 0), 700)


def donate_quote(bal, pct):
    """[B1] 捐款：到账（对方有空间时）与手续费。"""
    fee = g0(64 * bal, 1024)
    amt = min(g0(bal * (pct + 1), 1024), bal - fee)
    return max(amt, 0), fee


def attack_quote(bal, pct, k=12):
    """[A2] 陆攻报价：兵、费。k=32 为发船。"""
    fee = g0(k * bal, 1024)
    troops = min(g0(bal * (pct + 1), 1024), bal - fee)
    return max(troops, 0), fee


def quota_cap(t):
    """[B3] 全场受捐额度 aOY 在第 t 拍的值（t%100==99 时递增）。t>=4284 起不检查。"""
    cap = 15
    k = 99
    while k <= t:
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
        k += 100
    return cap


def quota_points(t, amount, land, recv_terr):
    """[B4] 一笔到账 amount 消耗的受捐点数。"""
    if t >= 3213:
        return 4 + g0(100 * amount, min(100 * max(recv_terr, 1), 10 ** 9))
    uv = 1 + g0(land, 300)
    den = uv if t < 357 else 4 * uv if t < 714 else 10 * uv if t < 1071 else 30 * uv if t < 2142 else 100 * uv
    return 2 + g0(100 * amount, den)


def def_per_px(bal, terr):
    """[X11] 每格防御量（cnt=1）。"""
    return g0(bal, 1 + g0(10 * terr, 16))


def elim_cost(bal, terr, peak):
    """策略 elimCost：把目标从当前领土压到 peak/4 需要的兵。"""
    left = peak // 4
    x = min(1.0, left / max(terr, 1))
    return 2 * bal * (1 - x ** 1.6) + 2 * terr * (1 - x)


def win_ratio(t):
    """策略 winRatio（winT=[[1500,3],[2000,2.85],[2500,1.8]]，winR=0.002）。"""
    T = [(1500, 3.0), (2000, 2.85), (2500, 1.8)]
    if t < T[0][0]:
        return 0.002 * max(1, t)
    for i in range(1, len(T)):
        if t <= T[i][0]:
            return T[i - 1][1] + (T[i][1] - T[i - 1][1]) * (t - T[i - 1][0]) / (T[i][0] - T[i - 1][0])
    return T[-1][1]
