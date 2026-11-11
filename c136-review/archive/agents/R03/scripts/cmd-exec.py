#!/usr/bin/env python3
"""cmd-exec.py — 号“以为自己发了什么” vs 回放里“服务器实际执行了什么”。

用法：
  python3 cmd-exec.py                 # R03 的 14 局汇总表
  python3 cmd-exec.py A051 --detail   # 单局明细（成批落地、捐款配对、清仓批次）
  python3 cmd-exec.py --all           # bundles/ 下所有已解出回放的局（M7 用）

输入：对局包 traj.csv / events.csv / results.csv + out/cache/<局>-replay.json（replay-cmds.mjs 解出）。
口径：
  本地指令数 = traj.csv 里 cmds 的最大值（g.attack/g.donate 返回 true 就 +1）。
  实际执行数 = 回放里该号的 id 1/2/3/4/10 指令条数（回放只记通过引擎校验的指令，捐款还要过受捐额度）。
  成批 = 同一个号在同一拍（同一个服务器回合）执行的指令；清仓批 = 这一批把余额打到剩 <20%。
  捐款配对 = 把日志里的 HL-DISPATCH（本地决策拍、pct、对象）和回放里的捐款（执行拍）按
            “同号、同对象、同 pct、批内逆序”配对，延迟 = 执行拍 - 决策拍。
"""
import sys
from collections import Counter, defaultdict

import c136lib as L

SPEND = L.SPEND_CMDS
frac_left, batches_of, match_donations = L.frac_left, L.batches_of, L.match_donations


def analyze(mid, detail=False, out=sys.stdout):
    rep = L.load_replay(mid)
    card = L.load_card(mid)
    res = L.load_results(mid)
    if rep is None:
        print(f"{mid}: 回放没有局内指令流（只有出生阶段或未解码），跳过", file=out)
        return None
    traj = L.load_traj(mid)
    events = L.load_events(mid)
    names = rep["names"]
    H = rep["humans"]

    def nm(p):
        if p >= L.NEUTRAL:
            return "中立"
        if p < H:
            return names[p].split("] ")[-1] if names[p].startswith("[") else names[p]
        return f"AI#{p}"

    squad = L.squad_map(mid, rep)
    foreign = L.foreign_bots(mid, rep)
    res = [r for r in res if r["meId"] in squad and squad[r["meId"]] == r["bot"]]
    tot_local = tot_exec = tot_in_batch = 0
    n_dump = 0
    dump_ticks = []
    hist = Counter()
    delays = []
    log_don = exec_don = 0
    lines = []
    for r in res:
        pid, bot = r["meId"], r["bot"]
        rows = traj.get(bot, [])
        local = max((x["cmds"] for x in rows), default=0)
        bs = batches_of(rep, pid)
        n_exec = sum(len(c) for _, c in bs)
        n_atk = sum(1 for _, c in bs for x in c if x[0] == L.CMD_ATTACK)
        n_don = sum(1 for _, c in bs for x in c if x[0] == L.CMD_DONATE)
        n_boat = sum(1 for _, c in bs for x in c if x[0] in (L.CMD_BOAT, L.CMD_CHASE))
        in_batch = sum(len(c) for _, c in bs if len(c) >= 4)
        for _, c in bs:
            hist[len(c)] += 1
        dumps = []
        for S, c in bs:
            left = 1.0
            for cid, a, b in c:
                left *= frac_left(cid, a)
            if left < 0.2 and len(c) >= 2:
                dumps.append((S, len(c), left, c))
        logged = sorted((e["t"], e["pct"], e["target"]) for e in events
                        if e["bot"] == bot and e["type"] in ("DISPATCH", "DONATE") and e["pct"] is not None)
        pairs, _ = match_donations(logged, bs)
        for S, tmin, tmax, pct, tgt in pairs:
            if tmax is not None:
                delays.append((S - tmax, S - tmin if tmin is not None else None, bot, S))
        log_don += len(logged)
        exec_don += n_don
        tot_local += local
        tot_exec += n_exec
        tot_in_batch += in_batch
        n_dump += len(dumps)
        dump_ticks.extend(S for S, _, _, _ in dumps)
        left_lag = ""
        if r["event"] == "left":
            dc = [t for t, cid, p, a, b in rep["cmds"] if p == pid and cid in (L.CMD_SURRENDER, L.CMD_DISCONNECT)]
            if dc:
                left_lag = f" 离场:本地拍{r['tick']}→服务器拍{dc[0]}(落后{dc[0] - r['tick']}拍)"
        lines.append(f"  {bot:8s} 本地指令{local:4d} 实际执行{n_exec:4d}"
                     f"(攻{n_atk} 捐{n_don} 船{n_boat}) 执行率{100 * n_exec / max(local, 1):3.0f}%"
                     f" ≥4条成批占{100 * in_batch / max(n_exec, 1):3.0f}% 清仓批{len(dumps)}"
                     f" 捐款日志{len(logged)}→执行{n_don}{left_lag}")
        if detail:
            for S, n, left, c in dumps:
                kinds = "".join("攻" if x[0] == 1 else "捐" if x[0] == 2 else "船" for x in c)
                tg = Counter(nm(x[2]) if x[0] in (1, 2) else "海" for x in c).most_common(2)
                lines.append(f"      清仓批 拍{S} {n}条[{kinds}] pct={[x[1] for x in c]} 余额剩{100 * left:.1f}% 对象{tg}")
            for S, tmin, tmax, pct, tgt in pairs:
                amb = "" if tmin == tmax else f"（最早可能 {tmin}）"
                lines.append(f"      捐款 执行拍{S} ← 决策拍{tmax}{amb} pct={pct} →{nm(tgt)} 延迟≥{S - tmax if tmax is not None else '?'}")
    sq_names = set(squad.values())
    oth = Counter()
    per = defaultdict(int)
    for t, cid, p, a, b in rep["cmds"]:
        if t >= 0 and cid in SPEND and p not in squad:
            per[(p, t)] += 1
    for v in per.values():
        oth[v] += 1
    d_lo = sorted(d[0] for d in delays)
    med = d_lo[len(d_lo) // 2] if d_lo else None
    if foreign:
        print(f"{mid}: 注意 {foreign} 不在这局回放里（results.csv 里是别的对局的号），已剔除", file=out)
    print(f"{mid} H={H} 队数={rep['numberTeams']} 结果={card['outcome']['resultLabel']} 终局拍={card['outcome']['endTick']}"
          f" | 本队本地指令{tot_local} 实际执行{tot_exec}（{100 * tot_exec / max(tot_local, 1):.0f}%）"
          f" ≥4条成批占{100 * tot_in_batch / max(tot_exec, 1):.0f}% 清仓批{n_dump}"
          f" | 捐款日志{log_don}→执行{exec_don}"
          f" 延迟下界中位{med} 最大{d_lo[-1] if d_lo else None}"
          f" | 本队批大小{sorted(hist.items())} 他人批大小{sorted(oth.items())}", file=out)
    if detail:
        for ln in lines:
            print(ln, file=out)
    return dict(mid=mid, local=tot_local, execd=tot_exec, in_batch=tot_in_batch, dumps=n_dump,
                log_don=log_don, exec_don=exec_don, delay_med=med, result=card["outcome"]["resultLabel"],
                hist=hist, oth=oth, dump_ticks=dump_ticks)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    detail = "--detail" in sys.argv
    mids = args or (L.all_match_ids() if "--all" in sys.argv else L.R03_MATCHES)
    rows = []
    for mid in mids:
        r = analyze(mid, detail)
        if r:
            rows.append(r)
    if len(rows) > 1:
        hist, oth = Counter(), Counter()
        for r in rows:
            hist.update(r["hist"])
            oth.update(r["oth"])
        loc, ex = sum(r["local"] for r in rows), sum(r["execd"] for r in rows)
        print(f"合计 {len(rows)} 局：本队本地指令 {loc}，回放执行 {ex}（{100 * ex / max(loc, 1):.0f}%）；清仓批 {sum(r['dumps'] for r in rows)}；"
              f"捐款日志 {sum(r['log_don'] for r in rows)} → 执行 {sum(r['exec_don'] for r in rows)}")
        dt = [t for r in rows for t in r["dump_ticks"]]
        edges = [0, 900, 1500, 2400, 3000, 10 ** 9]
        print("合计 清仓批落地拍分布：" + "，".join(
            f"{'≥' + str(a) if b > 10 ** 8 else str(a) + '~' + str(b - 1)}: {sum(1 for t in dt if a <= t < b)}"
            for a, b in zip(edges, edges[1:])) + (f"；最早 {min(dt)}，最晚 {max(dt)}" if dt else ""))
        print(f"合计 本队批大小 {sorted(hist.items())}（4~8 条共 {sum(v for k, v in hist.items() if 4 <= k <= 8)} 批）；"
              f"他人批大小 {sorted(oth.items())}；全体最大批 {max(list(hist) + list(oth))} 条")


if __name__ == "__main__":
    main()
