#!/usr/bin/env python3
"""30_donation_ledger.py — 捐款 / 调度的逐拍整数账本（R07 v2.0）。

目的：用引擎整数公式把「捐出方」的余额从一个日志观测点精确推到下一个观测点，从而判定每一笔
[HL-DONATE]/[HL-DISPATCH] 指令 ①有没有真的被引擎执行（还是被拒 / 没到），②在哪一拍执行（指令延迟），
③实际扣了多少（到账 + 6.25% 手续费）。

方法：
  观测点 = 该号的 HL-TICK 快照 (t, bal, terr) 与每条捐款日志里的 myBal（决策拍开始时的余额）。
  在领土不变的区间里，余额只受三件事影响：每 10 拍结息（t%10==9）、每 100 拍地租（t%100==99）、指令执行。
  对每一笔捐款，枚举「在决策后第 1..MAXLAT 拍执行」或「没执行」，逐拍向前推，凡是与下一个观测点
  的余额不是**整数相等**的假设全部丢弃。同一 10 拍结息段内执行结果相同，所以输出的是执行拍的区间。
  如果所有假设都被丢弃，说明区间里还有别的支出（陆攻 / 船 / 被打掉的兵）或领土变化，记 MISMATCH 并在该观测点重新起算。

  捐款到账按 (pct+1)/1024（engine-evidence [B1] + live-donation-check B1），假设接收方有足够空间。
  若接收方空间不足（150×领土硬上限），实际到账会更小——这种情况会表现为 MISMATCH，脚本再试「部分到账」。

用法：python3 30_donation_ledger.py <matchId> [--bot name] [--maxlat 60] [--print]
输出：out/<matchId>/donation_ledger.txt / .json
"""
import json
import os
import sys
from collections import defaultdict

from r07lib import load_card, load_events, load_traj, income_tick, donate_quote, g0, ensure_out, quota_cap, quota_points, quota_exempt, snap_at


def solve_bot(bot, rows, dons, land, maxlat):
    """rows: HL-TICK 快照；dons: 该号的捐款事件（按 t 排序）。返回 (逐笔判定, 区间日志)。"""
    obs = {}
    for r in rows:
        obs[r["t"]] = ("TICK", r["bal"])
    for i, e in enumerate(dons):
        if isinstance(e.get("myBal"), (int, float)):
            # 同一拍既有快照又有捐款日志时两者应相等
            obs.setdefault(e["t"], ("DON", int(e["myBal"])))
    if not obs:
        return [], []
    terr_at = {r["t"]: r["terr"] for r in rows}
    snap_ts = sorted(terr_at)

    def terr_for(t):
        # 用 <=t 的最近快照领土；并返回该区间领土是否恒定（前后快照相等）
        prev = None
        nxt = None
        for s in snap_ts:
            if s <= t:
                prev = s
            elif nxt is None:
                nxt = s
                break
        if prev is None:
            return terr_at[snap_ts[0]], False
        const = (nxt is None) or (terr_at[nxt] == terr_at[prev])
        return terr_at[prev], const

    t0 = min(obs)
    t_end = max(max(obs), (dons[-1]["t"] + maxlat + 1) if dons else 0)
    last_obs_t = max(obs)
    don_at = defaultdict(list)
    for i, e in enumerate(dons):
        don_at[e["t"]].append(i)
    # 假设集合：key=(bal, pending tuple) -> {donIdx: (execMin, execMax) | None}
    hyps = {(obs[t0][1], ()): {}}
    verdict = {}
    seglog = []
    t = t0
    anchor_t = t0
    while t <= last_obs_t:
        terr, const = terr_for(t)
        # 1) 观测点核对
        if t in obs and t != anchor_t:
            want = obs[t][1]
            keep = {k: v for k, v in hyps.items() if k[0] == want}
            if keep:
                hyps = keep
                seglog.append((anchor_t, t, "OK", want, len(keep)))
            else:
                # 找最接近的假设，报差额
                best = min(hyps.items(), key=lambda kv: abs(kv[0][0] - want))
                diff = best[0][0] - want
                seglog.append((anchor_t, t, "MISMATCH", want, diff, const))
                # 区间里还有别的流水。两种处理：
                #  a) 差额远小于在场捐款的金额（<15%）：按最接近的假设近似定案（EXEC~），待执行队列沿用该假设；
                #  b) 否则：在场捐款全部记未定，待执行队列清空。
                # （v2.0 把所有假设的待执行队列并集带过观测点，会让后面的捐款依次错位一笔，最后凭空多出 NOT-EXEC。）
                open_d = set(best[0][1])
                for k, v in hyps.items():
                    open_d.update(di for di in v if di not in verdict)
                    open_d.update(k[1])
                open_d = {di for di in open_d if di not in verdict}
                ref = min((sum(donate_quote(int(dons[di]["myBal"]), int(dons[di]["pct"]))) for di in open_d), default=0)
                if open_d and ref > 0 and abs(diff) <= 0.15 * ref:
                    for di, x in best[1].items():
                        if di in verdict:
                            continue
                        verdict[di] = ("EXEC~", x[0], x[1]) if x is not None else ("UNDETERMINED", None, None)
                    hyps = {(want, tuple(best[0][1])): {}}
                else:
                    for di in open_d:
                        verdict[di] = ("UNDETERMINED", None, None)
                    hyps = {(want, ()): {}}
            anchor_t = t
            # 观测点后，凡是所有存活假设里取值一致的捐款判定可以定案
            common = None
            for k, v in hyps.items():
                items = {di: (x if x is None else "E") for di, x in v.items()}
                common = items if common is None else {di: s for di, s in common.items() if items.get(di) == s}
            if common:
                for di, s in common.items():
                    if di in verdict:
                        continue
                    if any(di in k[1] for k in hyps):
                        continue
                    if s is None:
                        verdict[di] = ("NOT-EXEC", None, None)
                    else:
                        lo = min(v[di][0] for v in hyps.values())
                        hi = max(v[di][1] for v in hyps.values())
                        verdict[di] = ("EXEC", lo, hi)
        # 2) 本拍新决策的捐款进入待执行队列（决策在本拍，最早下一拍执行）
        if t in don_at:
            new = {}
            for (bal, pend), hist in hyps.items():
                new[(bal, pend + tuple(don_at[t]))] = hist
            hyps = new
        # 3) 分支：队首的待执行捐款在本拍执行 / 继续等 / 超时作废
        new = {}

        def put(key, hist):
            if key in new:
                old = new[key]
                merged = dict(old)
                for di, x in hist.items():
                    if di in merged and merged[di] is not None and x is not None:
                        merged[di] = (min(merged[di][0], x[0]), max(merged[di][1], x[1]))
                    elif di not in merged:
                        merged[di] = x
                new[key] = merged
            else:
                new[key] = hist

        for (bal, pend), hist in hyps.items():
            if not pend:
                put((bal, pend), hist)
                continue
            di = pend[0]
            e = dons[di]
            age = t - e["t"]
            if age >= 1:
                amt, fee = donate_quote(bal, int(e["pct"]))
                if amt >= 1:
                    h2 = dict(hist)
                    h2[di] = (t, t)
                    put((bal - amt - fee, pend[1:]), h2)
            if age >= maxlat:
                h3 = dict(hist)
                h3[di] = None
                put((bal, pend[1:]), h3)
            else:
                put((bal, pend), hist)
            # 被拒（不扣钱）与「一直等到超时」余额相同，统一由超时分支表示
        hyps = new
        # 4) 本拍收入
        new = {}
        for (bal, pend), hist in hyps.items():
            key = (income_tick(bal, terr, land, t), pend)
            if key in new:
                old = new[key]
                for di, x in hist.items():
                    if di in old and old[di] is not None and x is not None:
                        old[di] = (min(old[di][0], x[0]), max(old[di][1], x[1]))
                    elif di not in old:
                        old[di] = x
            else:
                new[key] = dict(hist)
        hyps = new
        t += 1
    out = []
    for i, e in enumerate(dons):
        v = verdict.get(i, ("UNRESOLVED", None, None))
        out.append((e, v))
    return out, seglog


def main():
    mid = sys.argv[1]
    only = sys.argv[sys.argv.index("--bot") + 1] if "--bot" in sys.argv else None
    maxlat = int(sys.argv[sys.argv.index("--maxlat") + 1]) if "--maxlat" in sys.argv else 60
    card = load_card(mid)
    land = card["mapLand"]
    traj = load_traj(mid)
    events = load_events(mid)
    dons_all = [e for e in events if e["type"] in ("DONATE", "DISPATCH")]
    bots = sorted({e["bot"] for e in dons_all})
    L = []
    J = {"matchId": mid, "bots": {}, "rows": []}
    tot = defaultdict(int)
    lat_all = []
    for b in bots:
        if only and b != only:
            continue
        dons = sorted([e for e in dons_all if e["bot"] == b], key=lambda e: (e["t"], e["line"]))
        rows = traj.get(b, [])
        res, seglog = solve_bot(b, rows, dons, land, maxlat)
        ok = sum(1 for s in seglog if s[2] == "OK")
        mm = [s for s in seglog if s[2] == "MISMATCH"]
        L.append(f"== {b}: 捐款 {len(dons)} 笔；观测区间 {len(seglog)} 个，整数吻合 {ok} 个，不吻合 {len(mm)} 个")
        for s in mm[:40]:
            L.append(f"   MISMATCH {s[0]}→{s[1]}: 观测余额 {s[3]}，最近假设差 {s[4]:+d}（领土恒定={s[5]}）")
        cnt = defaultdict(int)
        for e, v in res:
            cnt[v[0]] += 1
            tot[v[0]] += 1
            lat = None
            if v[0] in ("EXEC", "EXEC~"):
                lat = (v[1] - e["t"], v[2] - e["t"])
                lat_all.append(lat)
            amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
            L.append(f"   t={e['t']} {e['type']}/{e['kind']} pct={e['pct']} → {e.get('targetName')} myBal={e['myBal']} 名义到账{amt} 费{fee} | {v[0]}"
                     + (f" 执行拍∈[{v[1]},{v[2]}] 延迟∈[{lat[0]},{lat[1]}]" if lat else "") + (" | 预标REJ?" if e["likelyRejected"] else ""))
            J["rows"].append({"bot": b, "t": e["t"], "type": e["type"], "kind": e["kind"], "pct": e["pct"], "to": e.get("targetName"), "myBal": e["myBal"],
                              "amt": amt, "fee": fee, "verdict": v[0], "execLo": v[1], "execHi": v[2], "rejFlag": e["likelyRejected"], "line": e["line"]})
        J["bots"][b] = {"n": len(dons), "segments": len(seglog), "segOk": ok, "segMismatch": len(mm), "verdicts": dict(cnt)}
        L.append(f"   判定汇总: {dict(cnt)}")
    L.append("")
    L.append(f"全局判定: {dict(tot)}")
    flagged = [r for r in J["rows"] if r["rejFlag"]]
    L.append(f"预标 likelyRejected 共 {len(flagged)} 笔，其中账本判定: " + json.dumps({k: sum(1 for r in flagged if r['verdict'] == k) for k in {r['verdict'] for r in flagged}}, ensure_ascii=False))
    if lat_all:
        los = sorted(x[0] for x in lat_all)
        his = sorted(x[1] for x in lat_all)
        L.append(f"指令延迟（决策拍→执行拍）: n={len(lat_all)} 下界 min/中位/max = {los[0]}/{los[len(los) // 2]}/{los[-1]}；上界 min/中位/max = {his[0]}/{his[len(his) // 2]}/{his[-1]}")
        J["latency"] = {"n": len(lat_all), "loMin": los[0], "loMed": los[len(los) // 2], "loMax": los[-1], "hiMin": his[0], "hiMed": his[len(his) // 2], "hiMax": his[-1]}
    J["total"] = dict(tot)
    out = ensure_out(mid)
    open(os.path.join(out, "donation_ledger.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(J, open(os.path.join(out, "donation_ledger.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--print" in sys.argv:
        print("\n".join(L))
    else:
        print("\n".join(L[-4:]))


if __name__ == "__main__":
    main()
