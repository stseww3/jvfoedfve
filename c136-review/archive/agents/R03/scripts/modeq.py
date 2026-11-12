#!/usr/bin/env python3
# 用法：python3 scripts/modeq.py [mode ...]
# 读 c136-data/manifest.jsonl（每局一行的卡片摘要），按 页面 mode × nominalTeams × actualTeams 数局数，
# 并列出指定 mode（默认 7、8：卡片把 nominalTeams/actualTeams 填成默认值 2 的那两种）的每一局。
# 只读 manifest 一个文件，不扫 bundles。
# 已核对过的对应关系（我复盘的 14 局的录像头）：mode 0→2 队、1→3 队、2→4 队、4→6 队、6→8 队、7→自由混战（录像头 gameMode=0、numberTeams=0）。
import collections
import json
import os
import sys

DATA = os.environ.get("C136_DATA", "/agent/repos/c136-data")


def main():
    want = [int(a) for a in sys.argv[1:]] or [7, 8]
    rows = [json.loads(ln) for ln in open(os.path.join(DATA, "manifest.jsonl"), encoding="utf-8") if ln.strip()]
    print(f"# manifest.jsonl 共 {len(rows)} 局；页面 mode × 卡片 nominalTeams × actualTeams → 局数（modeq.py）")
    by_mode = collections.Counter(r.get("mode") for r in rows)
    cnt = collections.Counter((r.get("mode"), r.get("nominalTeams"), r.get("actualTeams")) for r in rows)
    for m in sorted(by_mode, key=lambda x: (x is None, x)):
        parts = [f"名义 {k[1]} 队/实际 {k[2]} 队 × {v}" for k, v in sorted(cnt.items(), key=lambda kv: str(kv[0])) if k[0] == m]
        print(f"  mode={m}: {by_mode[m]} 局（" + "；".join(parts) + "）")
    for m in want:
        sel = [r for r in rows if r.get("mode") == m]
        print(f"  -- mode={m} 的 {len(sel)} 局：")
        for r in sel:
            oc = r.get("outcome") or {}
            print(f"     {r['matchId']} {r.get('cohort')} 图 {r.get('mapId')} 真人 {r.get('seededPlayers')} | 卡片 名义 {r.get('nominalTeams')} 队 实际 {r.get('actualTeams')} 队 "
                  f"baseWinExpectation={r.get('baseWinExpectation')} ourPrimaryTeam={r.get('ourPrimaryTeam')} distinctSquadTeams={r.get('distinctSquadTeams')} | "
                  f"结果 {oc.get('resultLabel')} anyBotWon={oc.get('anyBotWon')} endTick={oc.get('endTick')} peakSquadLandShare={oc.get('peakSquadLandShare')}")


if __name__ == "__main__":
    main()
