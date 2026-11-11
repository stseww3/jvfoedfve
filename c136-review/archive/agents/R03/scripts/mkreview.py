#!/usr/bin/env python3
"""mkreview.py — 合成一局的复盘 JSON，并用联络分支的 check_review 自检。

机械事实（脚本算的，不手抄）：
    out/dossier/<mid>-facts.json          dossier.py：时间线、阵亡号死前 500 拍账、DROP30 对账、捐款审计、成批落地
    out/dossier/<mid>-shadow-facts.json   shadow-digest.py：执行层（发令/成交/延迟）、落地错位、isNoFullSend 翻转
    out/cache/<mid>-freeze.json           freeze-scan.mjs：开局 safeFinite 冻结计数（没有就跳过）
    /agent/repos/c136-data/bundles/<mid>/card.json
手写判断（逐局读卷宗后写的）：
    scripts/notes/<mid>.py 里的 NOTES 字典：phases / turningPoints / deaths(cause) / decisions / newPatterns /
    lossArchetype / winnerNotes / wentWell / unknowns / mechanicsQuestions / confidenceOverall …

用法：python3 mkreview.py <mid> [--check-only]
产出：reviews/<mid>.json（只在自检全过或 --force 时覆盖）
"""
import importlib.util
import json
import os
import sys

# 自检要 import 联络分支的 tools/collect-reviews.py；不让 Python 往 tools/__pycache__ 里写字节码（那不是本人的目录）
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO_TOOLS = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "tools")
sys.path.insert(0, HERE)
from c136lib import load_card  # noqa: E402

STRATEGY_FILE = {"Va": "v27-team-c116-va.js", "Vb": "v27-team-c116-vb.js", "Vc": "v27-team-c116.js",
                 "B": "v27-team-c110.js", "G": "v27-team-g09.js"}
COMMON_SCRIPTS = [
    "scripts/resim.mjs（整局精确重放，traj 逐行核对）",
    "scripts/shadow.mjs（影子策略：同一份源码在重放状态上逐拍运行，对日志计数器与录像成交）",
    "scripts/dossier.py（卷宗：各队走势、逐号分段账、DROP30 对账、捐款审计、整局兵力去向总账、全场捐款网络）",
    "scripts/shadow-digest.py（决策串、执行层延迟、落地错位、isNoFullSend 翻转、未成交就重发的串）",
    "scripts/freeze-scan.mjs（t<1500：safeFinite 冻结计数与反事实；t≥1500：buyLand 每个决策拍为什么没出手的九类计数）",
    "scripts/donate-why.mjs（tryDonateToTeammate 每次调用卡在哪一道闸；照抄判定与真调用逐次对账）",
    "scripts/dbg/act-trace.mjs（逐决策拍打印各分支的输入与返回值）",
    "scripts/delay-ledger.py（延迟账：选点落地、发令→落地延迟分段、漏斗、目标已死改道、落地前重发与同拍成批落地）",
    "scripts/land-ledger.mjs（抢地账：出生份额 Voronoi、各拍 实际领土÷出生份额、名下范围归谁、身边内置 AI 的地去向）",
    "scripts/ledger-brief.py（两套账的摘要与 600~1500 拍三层对账恒等式）",
    "scripts/mkreview.py（合成本文件并自检）",
]


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _site(stack):
    """调用栈里最深的非 send 帧，例如 buyLand:5616。"""
    frames = [p for p in str(stack).split(">") if not p.startswith("send:")]
    return frames[-1] if frames else str(stack)


def _import(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(mid):
    notes = _import(os.path.join(HERE, "notes", f"{mid}.py"), f"notes_{mid}").NOTES
    card = load_card(mid)
    facts = _load(os.path.join(ROOT, "out", "dossier", f"{mid}-facts.json")) or {}
    sfacts = _load(os.path.join(ROOT, "out", "dossier", f"{mid}-shadow-facts.json")) or {}
    freeze = _load(os.path.join(ROOT, "out", "cache", f"{mid}-freeze.json"))
    shadow = _load(os.path.join(ROOT, "out", "cache", f"{mid}-shadow.json")) or {}
    oc = card.get("outcome", {})
    my_team = facts.get("myTeam", card.get("ourPrimaryTeam"))
    ver = facts.get("version")

    deaths_f = facts.get("deaths", [])
    presence = {}
    for d in deaths_f:
        presence[d["event"]] = presence.get(d["event"], 0) + 1
    in_room = facts.get("squadInRoom", [])
    survivors = [b for b in in_room if b not in {d["bot"] for d in deaths_f}]
    if survivors:
        presence["end"] = len(survivors)

    context = {
        "time": card.get("timeUtc"), "squad": card.get("cohort"), "bots": len(in_room) or card.get("squadBots"),
        "strategyVersion": f"{ver}（{STRATEGY_FILE.get(ver, '?')}）" if ver else None,
        "map": card.get("mapId"), "mapSeed": card.get("mapSeed"), "mapLand": card.get("mapLand"),
        "teams": facts.get("nTeams", card.get("actualTeams")), "teamsInReplayHeader": facts.get("nTeamsHeader"),
        "teamSizes": facts.get("teamSizes"), "humans": facts.get("humans", card.get("seededPlayers")),
        "ourTeam": my_team, "teamSplitCard": card.get("teamSplitCounts"),
        "baseWinExpectation": card.get("baseWinExpectation"), "sameMatchPeer": card.get("sameMatchPeer"),
        "presence": presence,
        "leftTicks": {d["bot"]: d["leftServerTick"] for d in deaths_f if d.get("leftServerTick")},
        "dataCompleteness": {
            "replay": bool(card.get("dataCompleteness", {}).get("replay")),
            "resimTrajCheck": shadow.get("validate"),
            "shadowCheck": sfacts.get("check"),
        },
    }
    context.update(notes.get("context", {}))

    tl = []
    tnotes = {int(k): v for k, v in (notes.get("timelineNotes") or {}).items()}
    for p in facts.get("timeline", []):
        q = dict(p)
        if q["t"] in tnotes:
            q["note"] = tnotes.pop(q["t"])
        tl.append(q)
    for extra in notes.get("timelineExtra", []):
        tl.append(extra)
    tl.sort(key=lambda p: p["t"])

    final_share = None
    if tl and my_team is not None:
        last = [p for p in tl if isinstance(p.get("teamSharePct"), dict)]
        if last:
            final_share = round(last[-1]["teamSharePct"].get(f"T{my_team}", 0) / 100, 4)
    result = notes.get("result") or ("won" if oc.get("primaryTeamWon") else "lost")
    outcome = {
        "result": result, "resultLabel": oc.get("resultLabel"), "winnerTeam": oc.get("winnerTeam"),
        "endTick": oc.get("endTick"), "ourFinalShare": final_share,
        "peakSquadLandShare": oc.get("peakSquadLandShare"),
        "peakPrimaryTeamShareSeen": oc.get("peakPrimaryTeamShareSeen"),
        "anyBotWon": oc.get("anyBotWon"),
    }
    outcome.update(notes.get("outcome", {}))

    me_of = {b: v.get("me") for b, v in (shadow.get("bots") or {}).items()}
    dnotes = notes.get("deaths", {})
    deaths = []
    for d in deaths_f:
        n = dnotes.get(d["bot"], {})
        l5 = d.get("last500") or {}
        deaths.append({
            "bot": d["bot"], "me": me_of.get(d["bot"]), "event": d["event"],
            "t": d.get("deathServerTick"), "localStopTick": d.get("localTick"), "leftServerTick": d.get("leftServerTick"),
            "peakLand": d.get("peakTerr"), "peakTick": d.get("peakTick"),
            "landAtDeath": d.get("terrAtDeath"), "balanceAtDeath": d.get("balAtDeath"),
            "killers": [f"{a['who']}（压在身上 {a['troops']}）" for a in d.get("attackersAtDeath", [])],
            "last500": {
                "land0": l5.get("terr0"), "bal0": l5.get("bal0"), "tilesLost": l5.get("tilesLost"),
                "balLostDefending": l5.get("balLostDefending"),
                "lostTo": [f"{x['who']} {x['tiles']}格/{x['bal']}兵" for x in l5.get("lostTo", [])],
                "donatedOut": l5.get("donatedOut"), "donationTax": l5.get("donationTax"),
                "received": l5.get("received"), "attackSent": l5.get("attackSent"),
            },
            "cause": n.get("cause", ""), "patternIds": n.get("patternIds", []),
        })
    for extra in notes.get("deathsExtra", []):
        deaths.append(extra)

    exec_layer = None
    if sfacts:
        exec_layer = {
            "teamWindows": [{"t0": w[0], "issued": w[1], "executed": w[2], "lagMedian": w[3], "lagMax": w[4] if len(w) > 4 else None}
                            for w in sfacts.get("teamExec", [])],
            "perBot": {b: {k: v["exec"].get(k) for k in ("issued", "executed", "dropped", "lagMedian", "lagMax")}
                       for b, v in sfacts.get("bots", {}).items()},
            "misfire": sfacts.get("misfire"),
            "nfsFlips": {b: {"t": v["nfs"]["flip"]["t"], "blockedSends": v["nfs"].get("blocked", 0)}
                         for b, v in sfacts.get("bots", {}).items() if v.get("nfs") and v["nfs"].get("flip")},
            "sendSites": [{"site": s[0], "n": s[1]} for s in sfacts.get("sites", [])],
        }
        if sfacts.get("reissue"):
            exec_layer["reissueBeforeExec"] = sfacts["reissue"]
        stops = {b: v["stop"] for b, v in sfacts.get("bots", {}).items() if v.get("stop")}
        if stops:
            exec_layer["pageStops"] = stops
    fz = None
    core = None
    if freeze:
        fz = {"window": [freeze["from"], freeze["to"]], "team": freeze["team"],
              "perBot": {b: {k: v[k] for k in ("ticks", "target", "neutral", "noai", "frozen", "frozenWould", "other", "frozenBy", "binders", "B0", "B1", "L0", "L1")}
                         for b, v in freeze["bots"].items()}}
        post = freeze.get("post")
        if post and post["team"]["ticks"]:
            cls = ("sent", "slotTaken", "noOffer", "blocked", "frozenSF", "frozenKeep", "pricedHigh", "pulseWait", "pricedOther")
            core = {
                "from": post["from"],
                "classes": {
                    "sent": "buyLand 发了令", "slotTaken": "同一拍前面已有指令被受理（每拍只收 1 条）", "noOffer": "没有任何陆上邻居（被围）",
                    "blocked": "走到 send 被 Policy.send 守卫或适配层拒掉", "frozenSF": "只把 safeFinite 当 0 就会出手",
                    "frozenKeep": "把整个 safeAt 当 0 才会出手（对真人邻居的留底）", "pricedHigh": "最便宜的报价 ≥ worth 且没过软上限（L5359 break）",
                    "pulseWait": "有报价进了循环，但对它已有在途兵", "pricedOther": "其余不出手",
                },
                "team": post["team"],
                "perBot": {b: dict({k: v[k] for k in ("ticks",) + cls}, t0=v["t0"], t1=v["t1"], binders=v["binders"],
                                   safeFiniteSpans=v["spans"][:6], keepSpans=v["keepSpans"][:5], boxedSpans=v["noOfferSpans"][:6], pricedHighSpans=v["highSpans"][:6])
                           for b, v in post["bots"].items() if v["ticks"]},
            }

    donwhy = _load(os.path.join(ROOT, "out", "cache", f"{mid}-donwhy.json"))
    donate_gates = None
    if donwhy:
        donate_gates = {
            "calls": donwhy["calls"], "replicaAgrees": donwhy["agree"], "total": donwhy["total"],
            "perBot": {b: {"calls": v["calls"], "stops": v["stops"], "byBand": v["byBand"], "sentTo": v["sentTo"]}
                       for b, v in donwhy["per"].items()},
            "legend": "围/边 = 源码 L4355 的 boxedIn 真/假；· = 算到 boxedIn 之前就返回。闸名见 scripts/donate-why.mjs 文件头",
        }

    drops = facts.get("drops", [])
    by_main = {}
    for d in drops:
        by_main[d["main"]] = by_main.get(d["main"], 0) + 1

    # 同一拍第二条指令被页面拒收（每拍只收 1 条）：按「先发并被受理的发令点 → 被挤掉的发令点」计数
    crowd = {}
    crowd_human = 0
    humans = facts.get("humans") or 0
    for b, v in (shadow.get("bots") or {}).items():
        by_t = {}
        for c in v.get("cmds", []):
            by_t.setdefault(c[0], []).append(c)
        for t, cs in by_t.items():
            acc = [c for c in cs if c[4] == 1]
            if not acc:
                continue
            for c in cs:
                if c[4] == 0:
                    key = f"{_site(acc[0][7])} → {_site(c[7])}"
                    crowd[key] = crowd.get(key, 0) + 1
                    if c[3] < humans:
                        crowd_human += 1
    if exec_layer is not None:
        exec_layer["sameTickRejected"] = {"byPair": crowd, "total": sum(crowd.values()), "withHumanTarget": crowd_human}
    lb = _import(os.path.join(HERE, "ledger-brief.py"), "ledger_brief")
    brief_txt, ledgers = lb.brief(mid)
    latency_land = None
    if ledgers.get("delay") or ledgers.get("land"):
        latency_land = {
            "brief": [ln for ln in brief_txt.splitlines()[1:] if ln.strip()],
            "threeLayer": ledgers.get("threeLayer"),
            "notes": notes.get("ledgerNotes"),
            "delay": ledgers.get("delay"),
            "land": ledgers.get("land"),
            "legend": "延迟 = 服务器处理拍 − 页面发令拍；名下 = 每格陆地归直线最近的真人出生点（Voronoi）后落到该号头上的格数；"
                      "三层对账恒等式：编队人均地÷其他真人人均地 = 出生份额（人均名下之比）× 转化（地÷名下 之比）。详见 scripts/ledger-brief.py 文件头",
        }
    doc = {
        "matchId": mid, "reviewer": "R03", "protocol": "v2.0",
        "context": context, "outcome": outcome, "timeline": tl,
        "phases": notes["phases"], "turningPoints": notes["turningPoints"], "deaths": deaths,
        "decisions": notes["decisions"], "newPatterns": notes.get("newPatterns", []),
        "lossArchetype": notes["lossArchetype"], "winnerNotes": notes["winnerNotes"],
        "wentWell": notes.get("wentWell", []), "unknowns": notes.get("unknowns", []),
        "mechanicsQuestions": notes.get("mechanicsQuestions", []),
        "execLayer": exec_layer, "openingFreeze": fz, "coreDecisionTicks": core,
        "drop30": {"count": len(drops), "countInCard": facts.get("drop30CountCard"), "byMainCause": by_main, "list": drops},
        "squadLedger": facts.get("squadLedger"),
        "boatHandovers": facts.get("boatHandovers"),
        "donationNetwork": facts.get("donationNetwork"),
        "donationAudit": dict(facts.get("donations") or {}, **(notes.get("donationAudit") or {})),
        "donateGates": donate_gates,
        "teamFall": facts.get("teamFall"),
        "interestEfficiency": facts.get("interest"),
        "dumpBatches": [b for b in facts.get("dumpBatches", []) if b.get("dump")],
        "latencyAndLand": latency_land,
        "scripts": COMMON_SCRIPTS + notes.get("scripts", []),
        "confidenceOverall": notes["confidenceOverall"],
    }
    return doc


def main():
    args = sys.argv[1:]
    mid = args[0]
    doc = build(mid)
    md_path = os.path.join(ROOT, "reviews", f"{mid}.md")
    md = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else None
    cr = _import(os.path.join(REPO_TOOLS, "collect-reviews.py"), "collect_reviews")
    fails, stats = cr.check_review(doc, md)
    print(f"{mid}: 自检 {'全过' if not fails else '未过：' + '；'.join(fails)}")
    print("  统计：" + json.dumps(stats, ensure_ascii=False))
    if "--check-only" in args:
        return 0
    os.makedirs(os.path.join(ROOT, "reviews"), exist_ok=True)
    out = os.path.join(ROOT, "reviews", f"{mid}.json")
    with open(out, "w", encoding="utf-8", errors="replace") as f:
        s = json.dumps(doc, ensure_ascii=False, indent=1)
        f.write(s.encode("utf-16", "surrogatepass").decode("utf-16", "replace"))
    print(f"  已写 {out}（{os.path.getsize(out)} 字节）")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
