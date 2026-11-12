#!/usr/bin/env python3
"""export_traces.py — 导出 C2 通道用的实录阶梯。

读（R06 本机，未入库）：out/<局>/probe.json（strat_probe.mjs：当年那版策略作影子，每个我方席位逐拍想发的指令）、
                       out/<局>/sim_state.json（eng_replay.cjs：真引擎重放里我方席位实际执行的指令）
用 scripts/latency.py 的 align()（影子下令 ↔ 录像执行：同席位、同种类、同目标、比例相同或相近、执行拍 ≥ 下令拍）配对。
写（入库）：sim-v2/traces/<局>.json
    seats[席位] = [[下令拍 τ, 执行拍 E, 种类(0 陆攻 / 1 发船 / 2 捐款), 影子下令时的目标(发船 = -1), 是否生效, 录像里记的目标(陆攻；512 = 落地时目标已出局)], …]
                  只收配上的；teamgate-v2 的 C2 档据此还原每个席位的 S(τ) = max(τ, E − 14)，checkpoint 模式据此算真局的重复单占比
    lastLog[席位] = 这个席位日志最后一条快照的拍 + 89（之后页面没再算过）

用法：python3 export_traces.py [局号…]（缺省：有 probe.json 的全部局）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIMV2 = os.path.dirname(HERE)
R06 = os.path.dirname(SIMV2)
sys.path.insert(0, os.path.join(R06, 'scripts'))
import latency  # noqa: E402
from r06lib import OUT  # noqa: E402


def main():
    mids = sys.argv[1:]
    if not mids:
        mids = sorted(m for m in os.listdir(OUT) if os.path.exists(os.path.join(OUT, m, 'probe.json')) and os.path.exists(os.path.join(OUT, m, 'sim_state.json')))
    os.makedirs(os.path.join(SIMV2, 'traces'), exist_ok=True)
    for mid in mids:
        X = latency.load(mid)
        if not X.probe or not X.sim or not X.sim.get('squadCmds'):
            print(f"{mid}: 跳过（缺影子流水或真引擎重放）")
            continue
        rows, lost = latency.align(X)
        seats = {}
        n = 0
        for r in rows:
            if r['tau'] is None:
                continue
            kind = {'atk': 0, 'boat': 1, 'don': 2}[r['k']]
            raw = int(r.get('raw', r.get('to', -1))) if kind == 0 else -1
            seats.setdefault(str(r['me']), []).append([int(r['tau']), int(r['t']), kind, int(r['sTo']) if kind != 1 else -1, 1 if r['ok'] else 0, raw])
            n += 1
        for v in seats.values():
            v.sort()
        last_log = {str(me): (b.traj[-1]['t'] + 89 if b.traj else -1) for me, b in X.M.bots.items()}
        d = [r[1] - r[0] for v in seats.values() for r in v]
        d.sort()
        out = dict(matchId=mid, strategy=X.probe.get('strategy'), rows=n, unmatched=sum(1 for r in rows if r['tau'] is None), lost=len(lost), last=X.last, seats=seats, lastLog=last_log)
        json.dump(out, open(os.path.join(SIMV2, 'traces', mid + '.json'), 'w'), separators=(',', ':'))
        q = (lambda p: d[min(len(d) - 1, int(p * len(d)))]) if d else (lambda p: None)
        print(f"{mid}: {len(seats)} 个席位，配上 {n} 条（进录像但配不上 {out['unmatched']}，影子发了没进录像 {len(lost)}），执行拍 − 下令拍 P25/中位/P75/P90 = {q(.25)}/{q(.5)}/{q(.75)}/{q(.9)}")


if __name__ == '__main__':
    main()
