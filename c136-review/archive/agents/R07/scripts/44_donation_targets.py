#!/usr/bin/env python3
"""44_donation_targets.py — 每笔捐款的「捐方密度 vs 收方密度」与收方当时状态（R07 v2.0）。

用法：python3 44_donation_targets.py <matchId> [--print]
对 events.csv 的每笔 DONATE/DISPATCH：捐方 myBal/dMe（日志原值）、收方在该拍之前最近一个 HL-TICK 快照的 terr/bal/dens/nb/neut、
收方快照距今多少拍（>90 说明收方策略当时没有在跑＝停摆/已死）、收方在之后 90 拍内的 dCmds（有没有把兵用出去）。
汇总：收方密度高于捐方的笔数、收方停摆（快照过期）的笔数、收方之后 90 拍内零指令的笔数，以及对应的名义到账与手续费。
输出 out/<mid>/donation_targets.txt/.json
"""
import json
import os
import sys
from r07lib import load_events, load_traj, donate_quote, ensure_out


def main():
    mid = sys.argv[1]
    traj = load_traj(mid)
    ev = [e for e in load_events(mid) if e["type"] in ("DONATE", "DISPATCH") and isinstance(e.get("myBal"), (int, float))]
    rows = []
    for e in ev:
        nm = str(e.get("targetName") or "")
        rb = next((b for b in traj if nm.endswith(b)), None)
        amt, fee = donate_quote(int(e["myBal"]), int(e["pct"]))
        r = {"t": e["t"], "donor": e["bot"], "kind": e.get("kind"), "pct": int(e["pct"]), "dMe": e.get("dMe"), "myBal": int(e["myBal"]),
             "amt": amt, "fee": fee, "recv": rb or nm, "recvSquad": rb is not None}
        if rb:
            before = [x for x in traj[rb] if x["t"] <= e["t"]]
            after = [x for x in traj[rb] if x["t"] > e["t"]]
            if before:
                s = before[-1]
                r.update({"recvSnapT": s["t"], "recvAge": e["t"] - s["t"], "recvTerr": s["terr"], "recvBal": s["bal"], "recvDens": s["dens"],
                          "recvNb": s["nb"], "recvNeut": s["neut"]})
                if after and after[0]["t"] - s["t"] <= 90:
                    r["recvDCmdsNext"] = after[0]["cmds"] - s["cmds"]
                    r["recvDTerrNext"] = after[0]["terr"] - s["terr"]
        rows.append(r)
    out = ensure_out(mid)
    lines = [f"# {mid} 捐款去向：t 捐方(dMe,myBal) → 收方(快照拍/过期拍数, terr, bal, dens, nb) 之后90拍 dCmds/dTerr | 到账/费"]
    for r in rows:
        lines.append(f"{r['t']} {r['donor']}(d{r['dMe']},{r['myBal']}) {r['kind']} pct={r['pct']} → {r['recv']}"
                     + (f"(snap{r['recvSnapT']}/age{r['recvAge']}, terr{r['recvTerr']}, bal{r['recvBal']}, d{r['recvDens']}, nb{r['recvNb']})" if "recvSnapT" in r else "(无快照)")
                     + (f" 之后: dCmds={r['recvDCmdsNext']} dTerr={r['recvDTerrNext']:+d}" if "recvDCmdsNext" in r else " 之后: 无连续快照")
                     + f" | {r['amt']}/{r['fee']}")

    def agg(sel):
        return {"n": len(sel), "amt": sum(r["amt"] for r in sel), "fee": sum(r["fee"] for r in sel)}

    fresh = [r for r in rows if r.get("recvAge") is not None and r["recvAge"] <= 90]
    summary = {
        "all": agg(rows),
        "recvSnapshotFresh": agg(fresh),
        "recvDenserThanDonor": agg([r for r in fresh if isinstance(r.get("dMe"), (int, float)) and r["recvDens"] > r["dMe"]]),
        "recvDens>=60": agg([r for r in fresh if r["recvDens"] >= 60]),
        "recvStale(>90拍无快照=停摆)": agg([r for r in rows if r.get("recvAge") is not None and r["recvAge"] > 90]),
        "recvZeroCmdsNext90": agg([r for r in rows if r.get("recvDCmdsNext") == 0]),
        "recvNonSquadOrUnknown": agg([r for r in rows if not r["recvSquad"]]),
    }
    lines.append("")
    lines.append("## 汇总（笔数 / 名义到账 / 手续费）")
    for k, v in summary.items():
        lines.append(f"  {k}: {v['n']} 笔 / {v['amt']} / {v['fee']}")
    open(os.path.join(out, "donation_targets.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"rows": rows, "summary": summary}, open(os.path.join(out, "donation_targets.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--print" in sys.argv:
        print("\n".join(lines))
    else:
        print("\n".join(lines[-9:]))


if __name__ == "__main__":
    main()
