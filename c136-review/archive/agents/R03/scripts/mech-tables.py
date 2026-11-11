#!/usr/bin/env python3
"""mech-tables.py — MECHANICS-A.md 里用到的速查表，全部由 c136lib 的引擎整数公式直接算出。

用法：python3 mech-tables.py > ../out/mech-tables.txt
"""
import math

import c136lib as L


def main():
    print("== 1. 利息表（每 10 拍一次，单位：万分之一）==")
    print("  下标 i = floor((511·领土 + 0.5)/全图陆地)；表值 = 100 + isqrt(floor((25600·i + 0.5)/508))")
    for share in (0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50, 1.0):
        i = L.g0(int(511 * share * 1_000_000), 1_000_000)
        print(f"  领土占全图 {share * 100:5.1f}% → i={i:3d} → 利率 {L.INTEREST_TABLE[i]}")
    print("  开局下限（t<1920）：floor((100·(13440−6t) + 0.5)/1920)")
    for t in (9, 99, 309, 609, 909, 1209, 1509, 1709, 1809, 1909, 1919):
        print(f"  t={t:4d} → {L.g0(100 * (13440 - 6 * t), 1920)}")

    print("\n== 2. 软上限以上的利率衰减（r = r0 − floor(2·r0·(B−cap)/cap)，cap = 100×领土）==")
    for r0 in (110, 150):
        row = []
        for x in (1.0, 1.05, 1.10, 1.20, 1.25, 1.30, 1.40, 1.50):
            cap = 100 * 10000
            bal = int(x * cap)
            r = r0 - L.g0(2 * r0 * (bal - cap), cap) if bal > cap else r0
            r = max(0, r)
            row.append(f"x={x:.2f}:{r}（每格 {r * x / 100:.3f} 兵/10拍）")
        print(f"  r0={r0}: " + "  ".join(row))
    print("  每格每 10 拍的利息 = r·x/100；x=1.00 时最大，x=1.25 时只剩 62.5%，x≥1.5 为 0。")

    print("\n== 3. 手续费占比 ==")
    print("  陆攻：兵 = floor(B·(pct+1)/1024)，费 = floor(12·B/1024)（按全额余额的 1.17% 收，与发多少无关）")
    for pct in (0, 11, 23, 47, 82, 102, 122, 204, 366, 511, 1011, 1023):
        troops, fee = L.quote_attack(1_000_000, pct, 12)
        print(f"    pct={pct:4d}: 发出 {troops / 10000:6.2f}%B，费 {fee / 10000:.2f}%B，费/兵 = {fee / max(1, troops) * 100:7.1f}%")
    print("  捐款：到账 = min(floor(B·(pct+1)/1024), B−费)，费 = floor(64·B/1024)（全额余额的 6.25%）")
    for pct in (102, 128, 150, 180, 220, 240, 260, 320, 380, 511, 959, 1023):
        amount, fee = L.quote_donate(1_000_000, pct)
        print(f"    pct={pct:4d}: 到账 {amount / 10000:6.2f}%B，费 {fee / 10000:.2f}%B，费/到账 = {fee / max(1, amount) * 100:6.1f}%，捐方共少 {(amount + fee) / 10000:6.2f}%B")
    print("  同一回合连发 n 条同样 pct 的指令（逐条按当时余额重新报价）后余额剩下的比例：")
    for cid, name, pcts in ((L.CMD_ATTACK, "陆攻", (47, 122, 204, 366)), (L.CMD_DONATE, "捐款", (220, 320, 380))):
        for pct in pcts:
            f = L.frac_left(cid, pct)
            print(f"    {name} pct={pct:4d}: " + "  ".join(f"n={n}:{f ** n * 100:5.1f}%" for n in (1, 2, 3, 5, 9)))

    print("\n== 4. 推进节拍 ==")
    print("  发令在回放拍 S 执行 → 第 S+7 拍走第一圈 → 之后每 k 拍一圈：")
    for terr in (500, 999, 1000, 9999, 10000, 59999, 60000):
        print(f"    领土 {terr:6d}: 每 {L.step_interval(terr)} 拍一圈")

    print("\n== 5. 每圈成本（打玩家）==")
    print("  攻方一圈 gV 格：成本 = 2·gV + 2·防御 + 对攻兵；防御 = floor((gV·B防 + 0.5)/(1 + floor((10·L防 + 0.5)/16)))")
    print("  防守方每圈另从余额里扣 防御 这么多兵（[X15]：对攻兵先 1:1 抵消，其余的一半从余额扣）")
    for dens in (10, 30, 50, 80, 100, 125, 150):
        terr = 5000
        bal = dens * terr
        d = L.defense(100, bal, terr)
        print(f"    守方密度 {dens:3d}（领土 {terr}）: 100 格一圈 防御={d}，攻方成本={2 * 100 + 2 * d}（每格 {(2 * 100 + 2 * d) / 100:.1f} 兵），守方掉 {d}（每格 {d / 100:.1f} 兵）")
    print("  等效指数 k（余额 ∝ 领土^k）：单圈吃掉守方领土的比例 x → k = ln(1−1.6x)/ln(1−x)")
    for x in (0.01, 0.05, 0.10, 0.20, 0.30, 0.40):
        print(f"    x={x:.2f} → k={math.log(1 - 1.6 * x) / math.log(1 - x):.2f}")

    print("\n== 6. 受捐额度（防喂养）==")
    print("  全场上限 aOY：初值 15，每逢 t%100==99：t<1071 +4，<2142 +6，<3213 +8，之后 +10；t≥4284 不再限制")
    for t in (1499, 1500, 1999, 2141, 2142, 2499, 2999, 3212, 3213, 3499, 3999, 4283):
        print(f"    t={t:4d}: 上限 {L.quota_cap(t)}")
    print("  一笔捐款扣受捐方的点数（每个受捐者一本账，所有捐方共用）：")
    for land in (374820, 517334, 664497):
        uv = 1 + L.g0(land, 300)
        print(f"   全图陆地 {land}（uv={uv}）：")
        for t, label in ((1500, "k=30"), (2142, "k=100"), (3213, "按受捐方软上限")):
            row = []
            for amount in (20000, 50000, 100000, 200000, 400000):
                pts = L.quota_points(t, amount, land, 5000)
                row.append(f"{amount // 1000}k→{pts}")
            print(f"    t={t}（{label}，受捐方领土 5000）: " + "  ".join(row) + f"   当时上限 {L.quota_cap(t)}")
    print("  一个从没收过捐款的受捐方（领土 5000），在第 t 拍一共最多还能收多少兵（= 单笔能过检查的最大到账）：")
    for land in (374820, 517334, 664497):
        row = []
        for t in (1500, 1800, 2141, 2142, 2500, 3000, 3212, 3213, 3600, 4000, 4283):
            row.append(f"t={t}:{L.max_fit_amount(t, land, 5000) // 1000}k")
        print(f"    陆地 {land}: " + "  ".join(row))
    print("  t<3213 时点数只看到账金额和全图陆地，与受捐方大小无关；t≥3213 改成 4 + floor(100·到账/软上限)，")
    print("  即一笔捐款把受捐方密度抬高 1 就扣 1 点（外加固定 4 点）。")


if __name__ == "__main__":
    main()
