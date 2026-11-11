#!/usr/bin/env python3
"""sim_prep.py — 给 sim_replay.mjs 准备输入：分队表（引擎算法重算）+ 日志快照（用来核对重演是否与实况一致）。

用法：python3 sim_prep.py <matchId>      → 写 out/<matchId>/sim_in.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r06lib import OUT, load_match, PEER_REPLAY  # noqa: E402


def main():
    mid = sys.argv[1]
    M = load_match(mid)
    if not M.replay or not M.teamInfo:
        print(f"{mid}: 没有录像头，不能重演")
        return 1
    ti = M.teamInfo
    src = M.replaySrc or mid
    # 核对点 = 日志里每一条 HL-TICK 原始行（不带身份）：重演时按 (拍, 领土, 兵力) 在全体真人里找对得上的玩家
    checks = [dict(line=r['line'], name=r['name'], t=r['t'], terr=r['terr'], bal=r['bal']) for r in M.tickRows]
    doc = dict(matchId=mid, replayPath=f"/agent/repos/c136-data/bundles/{src}/replay.txt", humans=M.humans,
               teams=[int(ti['team'][p]) for p in range(M.humans)], nTeams=int(ti['teams']), botTeams=bool(ti['botsTeamed']), lH=[int(x) for x in ti['lH']],
               squad=list(M.squad), names=[(M.names.get(q) if isinstance(M.names, dict) else M.names[q]) for q in range(M.humans)], endTick=M.endTick, replayLast=M.replayLast, checks=checks)
    os.makedirs(os.path.join(OUT, mid), exist_ok=True)
    with open(os.path.join(OUT, mid, 'sim_in.json'), 'w') as f:
        json.dump(doc, f, ensure_ascii=False)
    print(f"写入 out/{mid}/sim_in.json：真人 {M.humans}，{ti['teams']} 队，AI 入队={ti['botsTeamed']}，核对点 {len(checks)} 个，录像 {src} 到 t={M.replayLast}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
