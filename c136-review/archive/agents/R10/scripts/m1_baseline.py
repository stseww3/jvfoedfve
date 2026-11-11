#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m1_baseline.py — 用数据 A 把能算的基线算出来，带区间。（R10，M1）

输入：
  out/m1/rooms.json                 由 m1_games.py 生成
  <data>/tsb-team-results.jsonl     只用于核对结算字段的语义（与 page.js report() 的逻辑逐条比对）

输出：
  out/m1/baseline.json              全部数字（报告里引用的每个数都在这里）
  out/m1/baseline.md                人读的表
  out/m1/power-table.md             功效表（PLAN 0.3 要求的产出之一）

口径定义见 reports/METRICS.md。本脚本只做机械计算：
  - 「一局」= 至少一个我方的号 tick>0 的房间。
  - left 记录的三个子类：
        left_reload  why == "reload"                         （页面被重新加载，技术性离场）
        left_dead    why 为空 且 territory*10000 < land      （领土不到全图万分之一：事实上已出局）
        left_alive   why 为空 且 territory*10000 >= land     （还活着就离开：被人为撤出或断线）
  - 小队结局：
        won            至少一个号 result == "won"
        lost_observed  有号活到终局（event == "end"），终局时我方队伍领土不是第一
        lost_wiped     没有终局记录；按拍数最后一条记录是 died 或 left_dead（我方的号在终局前全部出局）
        censored       没有终局记录；按拍数最后一条记录是 left_reload 或 left_alive（结局没被观察到）
  - 基础期望 e = 1 / T，T 是开局时的真人队伍数（rooms.json 里的 T）。

用法：python3 m1_baseline.py [数据目录] [out 目录]
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats  # noqa: E402

DEAD_FRAC = 10000   # territory * DEAD_FRAC < land  →  事实上已出局


def left_subtype(rec: dict, land: int) -> str:
    if rec["event"] != "left":
        return rec["event"]
    if rec.get("why") == "reload":
        return "left_reload"
    if rec["territory"] * DEAD_FRAC < land:
        return "left_dead"
    return "left_alive"


def classify(room: dict) -> dict:
    land = room["land"]
    recs = sorted(room["records"], key=lambda r: (r["tick"], r["row"]))
    subs = [left_subtype(r, land) for r in recs]
    cnt = {k: subs.count(k) for k in ("died", "end", "left_reload", "left_dead", "left_alive")}
    if any(r["result"] == "won" for r in recs):
        outcome = "won"
    elif cnt["end"] > 0:
        outcome = "lost_observed"
    elif subs[-1] in ("died", "left_dead"):
        outcome = "lost_wiped"
    else:
        outcome = "censored"
    return {"outcome": outcome, "subtypes": cnt, "last_record_subtype": subs[-1],
            "per_record": [{"bot": r["bot"], "tick": r["tick"], "sub": s, "territory": r["territory"]} for r, s in zip(recs, subs)]}


def rate_block(k: int, n: int) -> dict:
    w = stats.wilson(k, n)
    c = stats.clopper_pearson(k, n)
    return {"k": k, "n": n, "p": (k / n) if n else None, "wilson95": list(w), "clopper_pearson95": list(c)}


def fmt_rate(b: dict) -> str:
    if not b["n"]:
        return "0/0"
    return (f"{b['k']}/{b['n']} = {100*b['p']:.1f}%（Wilson {100*b['wilson95'][0]:.1f}%~{100*b['wilson95'][1]:.1f}%；"
            f"C-P {100*b['clopper_pearson95'][0]:.1f}%~{100*b['clopper_pearson95'][1]:.1f}%）")


def check_semantics(res_path: str) -> list[dict]:
    """逐条核对结算记录是否符合 page.js report() 的逻辑（c99 分支 e923d6db7515 的 page.js 第 764~805 行）。"""
    rows = [json.loads(line) for line in open(res_path, encoding="utf-8") if line.strip()]
    out = []

    def add(name, bad):
        out.append({"name": name, "ok": len(bad) == 0, "violations": bad[:5], "n_checked": None})

    died = [r for r in rows if r["event"] == "died"]
    end = [r for r in rows if r["event"] == "end"]
    left = [r for r in rows if r["event"] == "left"]
    out.append({"name": "记录数：died / end / left", "ok": len(died) + len(end) + len(left) == len(rows),
                "violations": [], "n_checked": [len(died), len(end), len(left)]})
    add("died ⇒ result == lost", [r["game"] for r in died if r["result"] != "lost"])
    add("died ⇒ place == alivePlayers + 1", [r["game"] for r in died if r["place"] != r["alivePlayers"] + 1])
    add("died ⇒ 带 team 字段", [r["game"] for r in died if not r.get("team")])
    add("died ⇒ territory == 0 且 alive == false", [r["game"] for r in died if r["territory"] != 0 or r["alive"]])
    add("left ⇒ result == left 且不带 team 字段", [r["game"] for r in left if r["result"] != "left" or r.get("team")])
    bad = []
    for r in end:
        t = r.get("team")
        if not t:
            bad.append(r["game"])
            continue
        exp = "won" if t["best"] == t["mine"] else ("over" if r["alive"] else "lost")
        if r["result"] != exp:
            bad.append(r["game"])
    add("end ⇒ result == (best==mine ? won : alive ? over : lost)", bad)
    bad = []
    for r in rows:
        t = r.get("team")
        if t:
            tot = t["totals"]
            best = max(tot, key=lambda k: tot[k])
            # page.js 取第一个严格最大的键；并列时取先出现的键
            if str(t["best"]) != best and tot[str(t["best"])] != tot[best]:
                bad.append(r["game"])
            if sum(tot.values()) > r["land"]:
                bad.append(r["game"] + ":sum>land")
    add("team.best 是 totals 里领土最大的队；各队领土之和 <= land", bad)
    add("players == 512（房间总席位，含内置 AI）", [r["game"] for r in rows if r["players"] != 512])
    add("me.id < 真人数 H（我方的号都是真人席位）", [r["game"] for r in rows if not (0 <= r["me"]["id"] < len(r["humans"]))])
    add("humans[me.id] == 'me'", [r["game"] for r in rows if r["humans"][r["me"]["id"]] != "me"])
    add("mode == team", [r["game"] for r in rows if r["mode"] != "team"])
    return out


def main(argv: list[str]) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = argv[1] if len(argv) > 1 else "/tmp/c136-r10/c116-winrate/data"
    out_dir = argv[2] if len(argv) > 2 else os.path.join(here, "..", "out", "m1")
    rooms_doc = json.load(open(os.path.join(out_dir, "rooms.json"), encoding="utf-8"))
    rooms = rooms_doc["rooms"]

    sem = check_semantics(os.path.join(data_dir, "tsb-team-results.jsonl"))

    games = []
    for room in rooms:
        if room["kind"] != "played":
            continue
        c = classify(room)
        lg = room.get("log")
        T = room["T"] if room["T"] else None
        K = lg["n_bots_in_game"] if lg else room["n_records"]
        clan = room.get("clan_for_rule") if lg else None
        flags = []
        if lg and lg["n_error_lines"] > 0:
            flags.append("strategy-error")
        if lg and lg["hot_imports"]:
            flags.append("hot-import")
        if room["split"]:
            flags.append("split-teams")
        if K < 8:
            flags.append("short-handed")
        if c["subtypes"]["left_reload"] > 0:
            flags.append("reload")
        if c["subtypes"]["left_alive"] > 0:
            flags.append("pulled-out-alive")
        if not lg:
            flags.append("no-squad-log")
        games.append({
            "id": room["id"], "t0_utc": room["t0_utc"], "H": room["H"], "land": room["land"],
            "T": T, "T_nominal": room.get("T_nominal"), "T_obs": room["T_obs"], "T_source": room.get("T_source"),
            "K_records": room["n_records"], "K_in_game": K, "K_clan_tagged": clan,
            "team_humans_expected": (room["H"] / T) if T else None,
            "squad_weight_in_team": ((clan if clan is not None else K) / (room["H"] / T)) if T else None,
            "outcome": c["outcome"], "win": 1 if c["outcome"] == "won" else 0,
            "base": (1.0 / T) if T else None,
            "subtypes": c["subtypes"], "last_record_subtype": c["last_record_subtype"],
            "flags": flags, "max_tick": room["max_tick"], "last_view": room.get("last_view"),
            "snapshots": {k: {"squad_share": v["squad_share"], "n_with_snapshot": v["n_with_snapshot"], "n_missing": v["n_missing"]}
                          for k, v in (room.get("snapshots") or {}).items()},
            "death_ticks": sorted(r["tick"] for r in c["per_record"] if r["sub"] in ("died", "left_dead")),
            "per_record": c["per_record"],
        })

    def subset(pred):
        return [g for g in games if pred(g)]

    auto10 = subset(lambda g: g["id"].startswith("G"))
    dispatch9 = subset(lambda g: g["id"].startswith("G") and g["id"] != "G00")
    all13 = games
    determinable = subset(lambda g: g["outcome"] != "censored")
    clean = subset(lambda g: g["id"].startswith("G") and not ({"strategy-error", "hot-import", "split-teams", "short-handed"} & set(g["flags"])))

    def wl(gs):
        return sum(g["win"] for g in gs), len(gs)

    rates = {
        "A_dispatch_G01_G09": {"desc": "上一轮口径：DISPATCH.md 的 9 局（G01~G09）", "ids": [g["id"] for g in dispatch9], **rate_block(*wl(dispatch9))},
        "B_auto_session_G00_G09": {"desc": "自动挂机时段全部 10 局（G00~G09，日志里都有）", "ids": [g["id"] for g in auto10], **rate_block(*wl(auto10))},
        "C_all_played_censored_as_nonwin": {"desc": "结算文件里全部 13 个打过的房间，结局未被观察到的 2 局记为未赢", "ids": [g["id"] for g in all13], **rate_block(*wl(all13))},
        "D_all_played_determinable": {"desc": "同上但剔除结局未被观察到的 2 局（P1、P2）", "ids": [g["id"] for g in determinable], **rate_block(*wl(determinable))},
        "E_per_protocol_clean": {"desc": "自动时段里没有策略报错、热更新、拆队、缺员的局", "ids": [g["id"] for g in clean], **rate_block(*wl(clean))},
    }
    # 结局未被观察到的局的上下界（部分识别）：全部记为输 / 全部记为赢
    n_c = sum(1 for g in all13 if g["outcome"] == "censored")
    k_all, n_all = wl(all13)
    rates["C_bounds"] = {"desc": "13 局的胜率上下界：2 局未观察到的结局全算输 / 全算赢",
                         "lower": k_all / n_all, "upper": (k_all + n_c) / n_all, "censored": n_c}

    # 相对基础期望
    def excess(gs):
        gs = [g for g in gs if g["base"] is not None]
        wins = [g["win"] for g in gs]
        exps = [g["base"] for g in gs]
        et = stats.excess_test(wins, exps)
        ls = stats.logit_shift(wins, exps)
        return {"ids": [g["id"] for g in gs], "T": [g["T"] for g in gs], **et,
                "logit_shift": {k: (v if (isinstance(v, int) or (v == v and abs(v) != float("inf"))) else str(v)) for k, v in ls.items()}}

    excess_blocks = {
        "B_auto_session_G00_G09": excess(auto10),
        "A_dispatch_G01_G09": excess(dispatch9),
        "E_per_protocol_clean": excess(clean),
        "D_all_played_determinable": excess(determinable),
    }

    # 按队伍数分层
    strata = {}
    for g in auto10:
        key = "T=2" if g["T"] == 2 else ("T=3~4" if g["T"] in (3, 4) else "T>=5")
        s = strata.setdefault(key, {"ids": [], "k": 0, "n": 0, "base_sum": 0.0})
        s["ids"].append(g["id"])
        s["k"] += g["win"]
        s["n"] += 1
        s["base_sum"] += g["base"]
    for key, s in strata.items():
        s.update(rate_block(s["k"], s["n"]))
        s["mean_base"] = s["base_sum"] / s["n"]

    # 上一轮说法的重算
    legacy = {
        "auto_1_of_9": rate_block(1, 9),
        "c116_day_10_of_74": rate_block(10, 74),
        "c110_35_of_53": rate_block(35, 53),
        "diff_10of74_minus_1of9": dict(zip(("diff", "lo", "hi"), stats.newcombe_diff(1, 9, 10, 74))),
        "fisher_1of9_vs_10of74": stats.fisher_exact(1, 9, 10, 74),
        "bayes_P_10of74_gt_1of9": stats.prob_b_beats_a(1, 9, 10, 74),
        "diff_35of53_minus_10of74": dict(zip(("diff", "lo", "hi"), stats.newcombe_diff(10, 74, 35, 53))),
        "fisher_10of74_vs_35of53": stats.fisher_exact(10, 74, 35, 53),
    }

    # 队伍数上限随战队人数的变化（引擎分队规则的直接推论）：T_max = max(2, floor(H / K))
    def t_cap(H, K, t_nom):
        T = t_nom
        while T > 2 and K > H // T:
            T -= 1
        return T
    cap_table = []
    for K in (8, 10, 20):
        for H in (30, 40, 50, 60, 80, 100, 164):
            caps = [t_cap(H, K, tn) for tn in range(2, 9)]
            cap_table.append({"K": K, "H": H, "T_actual_for_nominal_2to8": caps,
                              "mean_base_if_nominal_uniform_2to8": sum(1.0 / c for c in caps) / len(caps)})

    # 存活曲线（号级，描述性；同一局的号不独立，不给区间）
    surv_ticks = [600, 1500, 3000, 4500, 6000]
    surv = []
    for g in auto10:
        row = {"id": g["id"], "K": g["K_in_game"]}
        for t in surv_ticks:
            alive = 0
            unknown = 0
            for r in g["per_record"]:
                if r["tick"] > t:
                    alive += 1
                elif r["sub"] in ("left_reload", "left_alive"):
                    unknown += 1      # 该拍之前已技术性离场，是否「存活」无意义
            row[str(t)] = {"in_game": alive, "left_technical_before": unknown,
                           "ended_before": (g["max_tick"] <= t) and g["outcome"] in ("won", "lost_observed"),
                           "squad_gone_before": (g["max_tick"] <= t) and g["outcome"] not in ("won", "lost_observed")}
        surv.append(row)

    payload = {
        "source": rooms_doc["source"], "semantics_checks": sem, "games": games, "rates": rates,
        "excess_vs_base": excess_blocks, "strata_by_T_auto10": strata, "legacy_recomputed": legacy,
        "team_cap_table": cap_table, "survival_auto10": surv,
        "plan_table": stats.plan_table(),
    }
    with open(os.path.join(out_dir, "baseline.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)

    L = []
    L.append("# 数据 A 基线（由 scripts/m1_baseline.py 生成，勿手改）\n")
    L.append("## 0. 结算字段语义核对（对照 page.js report()）\n")
    for c in sem:
        extra = f" {c['n_checked']}" if c.get("n_checked") else ""
        L.append(f"- {'PASS' if c['ok'] else 'FAIL'} {c['name']}{extra}" + (f" 违例：{c['violations']}" if c["violations"] else ""))
    L.append("\n## 1. 逐局\n")
    L.append("| 局 | H | 名义队数 | 实际队数 T | 基础期望 1/T | 进场号数 / 带标签 | 本队真人数≈H/T | 小队占本队比 | 小队结局 | died/end/left_dead/left_reload/left_alive | 标记 |")
    L.append("| :-: | --: | --: | --: | --: | :-: | --: | --: | :-- | :-: | :-- |")
    for g in games:
        s = g["subtypes"]
        L.append(f"| {g['id']} | {g['H']} | {g['T_nominal'] or '—'} | {g['T'] or '—'} | "
                 f"{('%.3f' % g['base']) if g['base'] else '—'} | {g['K_in_game']} / {g['K_clan_tagged'] if g['K_clan_tagged'] is not None else '—'} | "
                 f"{('%.1f' % g['team_humans_expected']) if g['team_humans_expected'] else '—'} | "
                 f"{('%.0f%%' % (100*g['squad_weight_in_team'])) if g['squad_weight_in_team'] else '—'} | {g['outcome']} | "
                 f"{s['died']}/{s['end']}/{s['left_dead']}/{s['left_reload']}/{s['left_alive']} | {', '.join(g['flags']) or '—'} |")
    L.append("\n## 2. 胜率（分析单位是局）\n")
    for key in ("A_dispatch_G01_G09", "B_auto_session_G00_G09", "C_all_played_censored_as_nonwin", "D_all_played_determinable", "E_per_protocol_clean"):
        b = rates[key]
        L.append(f"- **{key}** {b['desc']}：{fmt_rate(b)}　局：{' '.join(b['ids'])}")
    cb = rates["C_bounds"]
    L.append(f"- **C_bounds** {cb['desc']}：{100*cb['lower']:.1f}% ~ {100*cb['upper']:.1f}%（未观察到 {cb['censored']} 局）")
    L.append("\n## 3. 相对基础期望（每局 1/T）\n")
    L.append("| 口径 | 局数 | 实际胜 | 期望胜 Σ1/T | 超额胜率（每局） | P(胜局数 ≤ 实际) | P(胜局数 ≥ 实际) | 赔率比估计（95% 似然比区间） | 套回后的平均胜率（区间） | 平均基础期望 |")
    L.append("| :-- | --: | --: | --: | --: | --: | --: | :-- | :-- | --: |")
    for key, e in excess_blocks.items():
        ls = e["logit_shift"]
        def f(x):
            return x if isinstance(x, str) else f"{x:.2f}"
        L.append(f"| {key} | {e['n']} | {e['wins']} | {e['expected']:.2f} | {100*e['excess_per_game']:+.1f} 个百分点 | {e['p_lower']:.3f} | {e['p_upper']:.3f} | "
                 f"{f(ls['odds_ratio'])}（{f(ls['odds_ratio_lo'])} ~ {f(ls['odds_ratio_hi'])}） | "
                 f"{100*ls['mean_p_hat']:.1f}%（{100*ls['mean_p_lo']:.1f}% ~ {100*ls['mean_p_hi']:.1f}%） | {100*ls['mean_base']:.1f}% |")
    L.append("\n## 4. 按实际队伍数分层（自动时段 10 局）\n")
    L.append("| 分层 | 局 | 胜/局 | 胜率（Wilson 95%） | 平均基础期望 |")
    L.append("| :-- | :-- | :-: | :-- | --: |")
    for key in ("T=2", "T=3~4", "T>=5"):
        if key in strata:
            s = strata[key]
            L.append(f"| {key} | {' '.join(s['ids'])} | {s['k']}/{s['n']} | {100*s['p']:.0f}%（{100*s['wilson95'][0]:.0f}%~{100*s['wilson95'][1]:.0f}%） | {100*s['mean_base']:.1f}% |")
    L.append("\n## 5. 上一轮三个数字的重算\n")
    for key in ("auto_1_of_9", "c116_day_10_of_74", "c110_35_of_53"):
        L.append(f"- {key}: {fmt_rate(legacy[key])}")
    d = legacy["diff_10of74_minus_1of9"]
    L.append(f"- 10/74 − 1/9 = {100*d['diff']:+.1f} 个百分点（Newcombe 95%：{100*d['lo']:+.1f} ~ {100*d['hi']:+.1f}）；Fisher 双侧 p = {legacy['fisher_1of9_vs_10of74']:.3f}；P(后者真实胜率更高) = {legacy['bayes_P_10of74_gt_1of9']:.3f}")
    d = legacy["diff_35of53_minus_10of74"]
    L.append(f"- 35/53 − 10/74 = {100*d['diff']:+.1f} 个百分点（Newcombe 95%：{100*d['lo']:+.1f} ~ {100*d['hi']:+.1f}）；Fisher 双侧 p = {legacy['fisher_10of74_vs_35of53']:.2e}")
    L.append("\n## 6. 战队人数怎样压低队伍数（引擎分队规则的推论，不是实测）\n")
    L.append("实际队数 = 从名义队数往下减，直到 战队人数 <= floor(H / 队数)，最小 2。下表列出名义队数为 2~8 时各自的实际队数，")
    L.append("以及「名义队数在 2~8 上均匀」这个**假设**下的平均基础期望（真实的名义队数分布要用全量数据统计）。\n")
    L.append("| 战队人数 K | 房间真人数 H | 名义 2,3,4,5,6,7,8 队 → 实际队数 | 平均 1/T（假设名义队数均匀） |")
    L.append("| --: | --: | :-- | --: |")
    for r in cap_table:
        L.append(f"| {r['K']} | {r['H']} | {','.join(str(x) for x in r['T_actual_for_nominal_2to8'])} | {100*r['mean_base_if_nominal_uniform_2to8']:.1f}% |")
    L.append("\n## 7. 存活人数（自动时段 10 局；仍在场的号数，技术性离场的号单列）\n")
    L.append("| 局 | 进场 | " + " | ".join(f"t={t}" for t in surv_ticks) + " |")
    L.append("| :-: | --: | " + " | ".join("--:" for _ in surv_ticks) + " |")
    for row in surv:
        cells = []
        for t in surv_ticks:
            c = row[str(t)]
            if c["ended_before"]:
                cells.append("本局已结束")
            elif c["squad_gone_before"]:
                cells.append("0（我方已全部出局，对局仍在继续）")
            else:
                cells.append(f"{c['in_game']}" + (f"（另 {c['left_technical_before']} 个技术性离场）" if c["left_technical_before"] else ""))
        L.append(f"| {row['id']} | {row['K']} | " + " | ".join(cells) + " |")
    L.append("\n## 8. 我方各号领土之和占全图份额 与 结局（自动时段 10 局）\n")
    L.append("| 局 | T | 结局 | t≈630 | t≈1530 | t≈3060 | t≈4500 |")
    L.append("| :-: | --: | :-- | --: | --: | --: | --: |")
    for g in auto10:
        cells = []
        for t in ("630", "1530", "3060", "4500"):
            s = g["snapshots"][t]
            cells.append(f"{100*s['squad_share']:.1f}%" + (f"（缺 {s['n_missing']}）" if s["n_missing"] else ""))
        L.append(f"| {g['id']} | {g['T']} | {g['outcome']} | " + " | ".join(cells) + " |")
    L.append("")
    with open(os.path.join(out_dir, "baseline.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    # 功效表
    P = []
    P.append("# 功效表（由 scripts/m1_baseline.py 生成，勿手改）\n")
    P.append("双侧 5% 显著性、80% 功效。两臂等量、各局独立。「最小可检出」是正态近似解；括号里是在该点用 Fisher 精确检验时的实际功效（n ≤ 150 才算）。\n")
    P.append("## 表 1：每臂 n 局时，能分辨的最小胜率提升\n")
    ns = [30, 50, 75, 100, 150, 200, 300]
    bases = [0.10, 0.135, 0.20, 0.25, 0.50, 0.66]
    P.append("| 基线胜率 | " + " | ".join(f"n={n}" for n in ns) + " |")
    P.append("| --: | " + " | ".join("--:" for _ in ns) + " |")
    ptab = []
    for p1 in bases:
        cells = []
        for n in ns:
            m = stats.mde(p1, n)
            if m != m:
                cells.append("达不到")
                ptab.append({"p1": p1, "n": n, "mde": None})
                continue
            cell = f"{100*m:.1f}%（+{100*(m-p1):.1f}）"
            ex = None
            if n <= 150:
                ex = stats.power_exact(p1, m, n, n)
                cell += f" [{ex:.2f}]"
            ptab.append({"p1": p1, "n": n, "mde": m, "exact_fisher_power_at_mde": ex})
            cells.append(cell)
        P.append(f"| {100*p1:.1f}% | " + " | ".join(cells) + " |")
    P.append("\n## 表 2：想证明给定的提升，每臂需要多少局\n")
    P.append("| 基线 → 目标 | 未校正 | 连续性校正（对应 Fisher 精确检验） |")
    P.append("| :-- | --: | --: |")
    pairs = [(0.10, 0.25), (0.10, 0.40), (0.135, 0.25), (0.135, 0.30), (0.135, 0.40), (0.20, 0.35), (0.25, 0.40),
             (0.50, 0.65), (0.66, 0.71), (0.66, 0.80)]
    ntab = []
    for p1, p2 in pairs:
        a, b = stats.n_per_arm(p1, p2), stats.n_per_arm(p1, p2, continuity=True)
        ntab.append({"p1": p1, "p2": p2, "n_uncorrected": a, "n_continuity": b})
        P.append(f"| {100*p1:.1f}% → {100*p2:.1f}% | {a} | {b} |")
    P.append("\n## 表 3：单组对固定基础期望（「这支队是不是比随便一个队强」）\n")
    P.append("n 局、每局基础期望都是 e 时，单侧 5% 精确二项检验能以 80% 把握检出的最小真实胜率。\n")
    P.append("| 基础期望 e | " + " | ".join(f"n={n}" for n in (10, 20, 30, 50, 75, 100, 150)) + " |")
    P.append("| --: | " + " | ".join("--:" for _ in range(7)) + " |")
    one = []
    for e in (1 / 6, 0.2, 0.25, 1 / 3, 0.5):
        cells = []
        for n in (10, 20, 30, 50, 75, 100, 150):
            # 临界值：最小的 c 使 P(X >= c | e) <= 0.05
            c = next(c for c in range(n + 2) if stats.binom_sf(c, n, e) <= 0.05)
            if c > n:
                cells.append("达不到")
                one.append({"e": e, "n": n, "crit": None, "p_needed": None})
                continue
            lo, hi = e, 1.0
            for _ in range(60):
                mid = (lo + hi) / 2
                if stats.binom_sf(c, n, mid) < 0.80:
                    lo = mid
                else:
                    hi = mid
            one.append({"e": e, "n": n, "crit": c, "p_needed": hi})
            cells.append(f"{100*hi:.0f}%（需 ≥{c} 胜）")
        P.append(f"| {100*e:.1f}% | " + " | ".join(cells) + " |")
    P.append("")
    with open(os.path.join(out_dir, "power-table.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(P))
    with open(os.path.join(out_dir, "power-table.json"), "w", encoding="utf-8") as f:
        json.dump({"mde": ptab, "n_per_arm": ntab, "one_sample": one}, f, ensure_ascii=False, indent=1)

    bad = [c for c in sem if not c["ok"]]
    print(f"games={len(games)} semantics={len(sem)-len(bad)}/{len(sem)}")
    for c in bad:
        print("FAIL", c["name"], c["violations"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
