#!/usr/bin/env python3
"""quota_table.py — 由规格书 B 的公式直接算出的三张小表（公式与线上原文的一致性见 live-donation-check.cjs）。
  表 1：不同捐款比例下，税 ÷ 到账。
  表 2：指定地图陆地格数下，各时刻“从未收过款的人单笔最多能收多少兵”。
  表 3：配额上限每 100 拍的增量，折合成多少兵。
用法：cd c136-review/agents/R04 && timeout 60 python3 scripts/quota_table.py > out/quota-table.txt
"""
def g0(a, b):
    return int((a + 0.5) // b)

def cap_at(t):
    cap = 15
    for k in range(99, t, 100):
        cap += 4 if k < 1071 else 6 if k < 2142 else 8 if k < 3213 else 10
    return cap

def cost(t, v, ke, land):
    if t >= 3213:
        return 4 + g0(100 * v, min(100 * land, 10 ** 9))
    uv = 1 + g0(ke, 300)
    m = 1 if t < 357 else 4 if t < 714 else 10 if t < 1071 else 30 if t < 2142 else 100
    return 2 + g0(100 * v, m * uv)

def max_single(t, ke, land):
    cap = cap_at(t)
    lo, hi = 0, 10 ** 10
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if cost(t, mid, ke, land) <= cap:
            lo = mid
        else:
            hi = mid - 1
    return lo

print('表 1  税 ÷ 到账（收款方空间充足；到账 = (pct+1)/1024 × 余额，税 = 64/1024 × 余额）')
for pct in (129, 145, 155, 180, 220, 260, 320, 380):
    print(f'  pct={pct}: 到账 {100 * (pct + 1) / 1024:.2f}% 余额，税 ÷ 到账 = {64 / (pct + 1):.3f}')
print('表 2  从未收过款的人单笔最多到账（兵）')
for ke in (423950, 480957, 492822, 517334, 546152, 664497):
    row = []
    for t in (1070, 2141, 2200, 3200):
        row.append(f't={t} 上限 {cap_at(t)} → {max_single(t, ke, 20000)}')
    for land in (2000, 20000):
        row.append(f't=3213 上限 {cap_at(3213)} 领土 {land} → {max_single(3213, ke, land)}')
    print(f'  陆地 {ke}: ' + '；'.join(row))
print('表 3  上限每 100 拍的增量折合多少兵（陆地 664497，uv=2215；t>=3213 按收款人领土 2 万格）')
ke = 664497
uv = 1 + g0(ke, 300)
for name, inc, den in (('714<=t<1071', 4, 10 * uv), ('1071<=t<2142', 6, 30 * uv), ('2142<=t<3213', 8, 100 * uv), ('3213<=t<4284', 10, 100 * 20000)):
    print(f'  {name}: 每 100 拍 +{inc} 点 ≈ {inc * den // 100} 兵')
