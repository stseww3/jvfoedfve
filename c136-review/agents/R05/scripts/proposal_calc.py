#!/usr/bin/env python3
"""proposal_calc.py — COUNCIL-PROPOSAL.md 里用到的算例：只做算术，不读录像、不跑引擎。

提案里凡是「按引擎公式代入」得到的数（配额时刻表、公平间距、救援缺口、费率、样本量），都从这里出，
这样提案正文里的每个数仍然能在一张脚本生成的表里找到（出处标记 [PC §n]）。

输入：
  reviews/<局>.json 的 landAccount.voronoi（land_account.mjs 的输出：全图陆地格数、真人数、各我方号的最终出生点）
  out/pattern-scan.tsv 的 result 列（A 组的输赢）
  引擎常数抄自 /agent/repos/c136-data/src/sim/sim/game.js（行号写在各节标题里；脚本启动时用正则核对源码里还是这些值）
  个案的输入抄自复盘卡，逐条写明出处行

各节：
  §1 捐兵配额时刻表      game.js L124（donCap 初值 15）、L348–357（donationCost）、L379–383（每 100 拍涨一次）
  §2 出生间距            公平半径 rFair = sqrt(land ÷ (π × 真人数))；等面积六边形排布的间距 = sqrt(2 × land ÷ (√3 × 真人数)) ≈ 1.905 × rFair；
                         对照协调器 L1074 的 minReqSep = clamp(round(0.95 × rCell), 42, 68) 和录像里我方号的最近队友距离
  §3 救援缺口            dpKeep（策略 L2463）：守得住的留底 = (m − 1.5 × 地) ÷ 1.78，m = 最强的真人邻居的存兵 + 它已打过来的兵
  §4 连发 n 条之后的存兵  game.js L1239–1248：每条取当拍存兵的 (pct+1)/1024，另收 12/1024 手续费 → 连乘
  §5 固定费率            捐兵税 = 捐出方全部存兵的 64/1024（L390）；船费 32/1024（boats.js L786）；陆攻 12/1024（L1230、L1239–1248）
  §6 超软上限的利息折扣  game.js L744：n1 −= 2 × n1 × (存兵 − 软上限) ÷ 软上限
  §7 胜率的样本量        两个比例之差的双侧检验（α = 0.05，功效 0.8），正态近似

用法：python3 scripts/proposal_calc.py [--out reports/PROPOSAL-CALC.md]
"""
import csv
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get('C136_DATA', '/agent/repos/c136-data')
MATCHES = ['A014', 'A017', 'A021', 'A026', 'A030', 'A034', 'A037', 'A043', 'A058', 'A065', 'A093', 'A095', 'B010']
LAG = {'A017', 'A021', 'A026', 'A034', 'A058', 'A065', 'A093', 'B010'}
# 这一盘的出生点是怎么来的（抄自复盘卡的「出生」一节）；没列的 = 后端协调器的扇形阵
FORM = {
    'A017': '拆盘，这一盘只有 1 个号',
    'A043': '拆盘，这一盘只有 2 个号',
    'A026': '8 个号的出生指令没进录像，引擎随机落子',
    'B010': 'c110，没有后端协调，各号自己选点',
}


def fmt(n):
    return f'{n:,.0f}'


def kfmt(v):
    if v >= 1e6:
        return f'{v / 1e6:.2f}M'
    if v >= 1e3:
        return f'{v / 1e3:.1f}k'
    return f'{v:.0f}'


def check_engine():
    """核对抄下来的引擎常数还在源码里；对不上就退出，不出表。"""
    p = os.path.join(SRC, 'src/sim/sim/game.js')
    s = open(p, encoding='utf-8').read()
    need = [
        r'this\.donCap = 15;',
        r'this\.donCap \+= t < 1071 \? 4 : t < 2142 \? 6 : t < 3213 \? 8 : 10;',
        r'if \(t >= 3213\) return 4 \+ iV\(100 \* v, Math\.max\(this\.softCap\(q\), 1\)\);',
        r'const uw = 1 \+ iV\(this\.land, 300\);',
        r'if \(t < 357\) return 2 \+ iV\(100 \* v, uw\);',
        r'if \(t < 714\) return 2 \+ iV\(100 \* v, 4 \* uw\);',
        r'if \(t < 1071\) return 2 \+ iV\(100 \* v, 10 \* uw\);',
        r'if \(t < 2142\) return 2 \+ iV\(100 \* v, 30 \* uw\);',
        r'return 2 \+ iV\(100 \* v, 100 \* uw\);',
        r'return this\.t >= 4284 \|\| this\.isBot\(q\);',
        r'const fee = iV\(64 \* B, 1024\);',
        r'if \(this\.bal\[p\] > cap\) n1 -= iV\(2 \* n1 \* \(this\.bal\[p\] - cap\), cap\);',
        r'return Math\.min\(100 \* this\.terr\[p\], 1e9\);',
    ]
    miss = [n for n in need if not re.search(n, s)]
    b = open(os.path.join(SRC, 'src/sim/sim/boats.js'), encoding='utf-8').read()
    if not re.search(r'this\.quote\(p, pct, 32\)', b):
        miss.append('boats.js quote(p, pct, 32)')
    v = open(os.path.join(SRC, 'src/strategy/v27-team-c116-vb.js'), encoding='utf-8').read()
    if not re.search(r'return Math\.max\(0, \(m - 1\.5 \* g\.terr\[me\]\) / 1\.78\);', v):
        miss.append('dpKeep')
    c = open(os.path.join(SRC, 'src/strategy/spawn-coordinator-c116-vb.mjs'), encoding='utf-8').read()
    if not re.search(r'const minReqSep = clamp\(Math\.round\(0\.95 \* scales\.rCell\), 42, 68\);', c):
        miss.append('minReqSep')
    if miss:
        sys.exit('引擎 / 策略源码和脚本里抄的常数对不上：' + '；'.join(miss))


def don_cap(t):
    """第 t 拍开头的配额上限（点）：初值 15，每逢 t % 100 == 99 涨一次。"""
    cap = 15
    for u in range(99, t, 100):
        cap += 4 if u < 1071 else 6 if u < 2142 else 8 if u < 3213 else 10
    return cap


def k_of(t):
    return 1 if t < 357 else 4 if t < 714 else 10 if t < 1071 else 30 if t < 2142 else 100


def vmax_before_3213(t, land, used=0):
    """额度用掉 used 点的受赠方，第 t 拍单笔最多能收多少兵：2 + floor(100v ÷ (k×uw)) ≤ cap − used。"""
    uw = 1 + land // 300
    room = don_cap(t) - used - 2
    if room < 0:
        return 0
    return ((room + 1) * k_of(t) * uw - 1) // 100


def vmax_after_3213(t, terr, used=0):
    room = don_cap(t) - used - 4
    if room < 0:
        return 0
    return ((room + 1) * 100 * terr - 1) // 100


def voronoi(mid):
    j = json.load(open(os.path.join(ROOT, 'reviews', mid + '.json'), encoding='utf-8'))
    return j['landAccount']['voronoi']


def main():
    out = None
    a = sys.argv[1:]
    if '--out' in a:
        out = a[a.index('--out') + 1]
    check_engine()
    L = []
    w = L.append
    w('# PROPOSAL-CALC — 议会提案里的算例（只做算术）')
    w('')
    w('> 本文件由 `python3 scripts/proposal_calc.py --out reports/PROPOSAL-CALC.md` 生成，不手改。')
    w('> 引擎常数抄自 `game.js`、`boats.js`，脚本启动时逐条和源码核对；个案的输入抄自复盘卡，出处写在各节里。')
    w('')

    vor = {m: voronoi(m) for m in MATCHES}
    lands = sorted(v['land'] for v in vor.values())
    lmin, lmed, lmax = lands[0], int(statistics.median(lands)), lands[-1]

    # ---------------------------------------------------------------- §1
    w('## 1. 捐兵配额时刻表（game.js L124、L348–357、L379–383）')
    w('')
    w('每个受赠方有一个累计的已用点数（只增不减），一笔捐兵要的点数 = 基础点 + 100 × 兵 ÷ 计价基数；已用点数 + 这一笔 ≤ 上限才收。')
    w('上限全场共用：初值 15，每 100 拍涨一次（1071 拍前每次 4 点，2142 拍前 6 点，3213 拍前 8 点，之后 10 点）。4284 拍起不限；受赠方是内置 AI（含离场的号）时也不限。')
    w(f'3213 拍前计价基数 = k × (1 + 全图陆地 ÷ 300)，k = 1（<357 拍）、4（<714）、10（<1071）、30（<2142）、100（<3213）；基础点 2。下表按我复盘的 13 局的全图陆地取最小 {fmt(lmin)}、中位 {fmt(lmed)}、最大 {fmt(lmax)} 格。')
    w('')
    w('| 拍 | 上限（点） | 每点买多少兵：最小图 | 中位图 | 最大图 | 额度没用过的受赠方单笔最多收：最小图 | 中位图 | 最大图 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: |')
    for t in [400, 800, 1100, 1500, 1800, 2100, 2200, 2500, 2800, 3200]:
        per = [k_of(t) * (1 + ld // 300) / 100 for ld in (lmin, lmed, lmax)]
        vm = [vmax_before_3213(t, ld) for ld in (lmin, lmed, lmax)]
        w(f'| {t} | {don_cap(t)} | {fmt(per[0])} | {fmt(per[1])} | {fmt(per[2])} | {kfmt(vm[0])} | {kfmt(vm[1])} | {kfmt(vm[2])} |')
    w('')
    w('「单笔最多收」也是这个受赠方到这一拍为止累计能收的上限（分成 n 笔还要多扣 2 × (n − 1) 点基础点）。')
    w('')
    w('3213–4283 拍：计价基数 = 受赠方的软上限（100 × 地），所以每点买的兵 = 受赠方的地；基础点 4。')
    w('')
    w('| 拍 | 上限（点） | 额度没用过的受赠方单笔最多收：5,000 格的号 | 10,000 格的号 | 20,000 格的号 | 同一个号的硬上限（150 × 地）：5,000 格 | 10,000 格 | 20,000 格 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: |')
    for t in [3213, 3500, 3900, 4200]:
        vm = [vmax_after_3213(t, x) for x in (5000, 10000, 20000)]
        w(f'| {t} | {don_cap(t)} | {kfmt(vm[0])} | {kfmt(vm[1])} | {kfmt(vm[2])} | {kfmt(750000)} | {kfmt(1500000)} | {kfmt(3000000)} |')
    w('')
    w('- 读法：2142 拍前，一个受赠方累计最多收几万兵（中位图：1100 拍 '
      f'{kfmt(vmax_before_3213(1100, lmed))}，2100 拍 {kfmt(vmax_before_3213(2100, lmed))}）；2142–3212 拍是二三十万（中位图 2200 拍 {kfmt(vmax_before_3213(2200, lmed))}，3200 拍 {kfmt(vmax_before_3213(3200, lmed))}）；'
      '3213 拍起配额按受赠方的地计价，额度比硬上限还大，实际不再受限。')
    used = don_cap(3213) - 89
    w(f'- 对照复盘卡：A037 的 zexos1 在 3213 拍还剩 89 点、24,256 格地（reviews/A037.md「配额切换」）；按上式单笔最多收 {kfmt(vmax_after_3213(3213, 24256, used))}。')
    w('')

    # ---------------------------------------------------------------- §2
    w('## 2. 出生间距：按人数该隔多远 对 实际隔多远')
    w('')
    w('公平半径 rFair = sqrt(全图陆地 ÷ (π × 真人数))：把陆地按人头平分，每人一块圆的半径。两个号各占这样一块，圆心要隔开 2 × rFair；')
    w('按等面积六边形排满，间距 = sqrt(2 × 陆地 ÷ (√3 × 真人数)) ≈ 1.905 × rFair。')
    w('协调器 L836–838 的 rCell 用同一个式子（分母只数已落子的真人，下限 8）；L1074 的队友最小间距 = clamp(round(0.95 × rCell), 42, 68)：')
    w('拿半径当间距用，而且封顶 68 格。下表的「代码间距」按 rCell = rFair（真人全部落子）算。实际间距 = 各我方号最终出生点到最近的我方号的距离。')
    w('')
    w('| 局 | 出生点怎么来的 | 全图陆地 | 真人数 | 我方号 | rFair | 公平间距（六边形） | 代码间距 | 实际间距：中位 | 最小 | 实际 ÷ 公平 | 出生份额 | 我方号按人数该得（格） |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    ratios, shares, fairs, acts, dues = [], [], [], [], []
    fan_share, other_share = [], []
    for m in MATCHES:
        v = vor[m]
        land, n = v['land'], v['humans']
        rf = math.sqrt(land / (math.pi * n))
        hexd = math.sqrt(2 * land / (math.sqrt(3) * n))
        code = min(68, max(42, round(0.95 * rf)))
        pts = [(b['x'], b['y']) for b in v['perBot'] if b.get('x') is not None and b['x'] >= 0]
        nn = []
        for i, p in enumerate(pts):
            ds = [math.hypot(p[0] - q[0], p[1] - q[1]) for j, q in enumerate(pts) if j != i]
            if ds:
                nn.append(min(ds))
        tag = '＊' if m in LAG else ''
        due = v['squad'] * land / n
        form = FORM.get(m, '扇形阵')
        is_fan = m not in FORM
        (fan_share if is_fan else other_share).append((m, v['ratio']))
        if nn:
            med, mn = statistics.median(nn), min(nn)
            if is_fan:
                dues.append(due)
                ratios.append(med / hexd)
                acts.append(med)
                fairs.append(hexd)
            w(f'| {m}{tag} | {form} | {fmt(land)} | {n} | {len(pts)} | {rf:.0f} | {hexd:.0f} | {code} | {med:.0f} | {mn:.0f} | {med / hexd:.2f} | {v["ratio"]:.2f} | {fmt(due)} |')
        else:
            w(f'| {m}{tag} | {form} | {fmt(land)} | {n} | {len(pts)} | {rf:.0f} | {hexd:.0f} | {code} | – | – | – | {v["ratio"]:.2f} | {fmt(due)} |')
        shares.append(v['ratio'])
    w('')
    fs = sorted(x for _, x in fan_share)
    w(f'- 扇形阵的 {len(fan_share)} 局：公平间距的中位 {statistics.median(fairs):.0f} 格（{min(fairs):.0f}–{max(fairs):.0f}）；实际间距中位的中位 {statistics.median(acts):.0f} 格（{min(acts):.0f}–{max(acts):.0f}）；实际 ÷ 公平的中位 {statistics.median(ratios):.2f}（{min(ratios):.2f}–{max(ratios):.2f}）；出生份额的中位 {statistics.median(fs):.2f}（{fs[0]:.2f}–{fs[-1]:.2f}）。')
    w('- 不是扇形阵的 4 局的出生份额：' + '、'.join(f'{m} {x:.2f}（{FORM[m]}）' for m, x in other_share) + '。')
    w('- 间距是公平间距的 x 倍时，排在阵内的号名下的地是按人数该得的 x² 倍：x = 0.5 是四分之一，x = 0.6 是 36%，x = 0.8 是 64%。外圈的号朝外的一侧不受这个限制。')
    fan = math.pi * 182 ** 2 / 4
    w(f'- 扇形阵的占地：外墙半径的上限是 182 格（L1077），90 度扇形的面积最多 π × 182² ÷ 4 = {fmt(fan)} 格。扇形阵的 {len(dues)} 局里，我方号按人数该得 {fmt(min(dues))}–{fmt(max(dues))} 格，中位 {fmt(statistics.median(dues))} 格；扇形的面积是它的 {100 * fan / max(dues):.0f}%–{100 * fan / min(dues):.0f}%（中位 {100 * fan / statistics.median(dues):.0f}%）。阵外朝外的地还能算到外墙号名下，所以出生份额比这个比例高。')
    w('- ＊ = 延迟波局。出生份额抄自 `reviews/<局>.json`（= DELAY-AND-LAND-ACCOUNT 第 5 节）。')
    w('')

    # ---------------------------------------------------------------- §3
    w('## 3. 救援缺口：按 dpKeep 的式子代入个案')
    w('')
    w('`dpKeep`（策略 L2459–2464）：最强的真人邻居连同它已经打过来的兵记作 m，自己的留底不低于 (m − 1.5 × 地) ÷ 1.78 才守得住。')
    w('缺口 = 这个留底 − 现有存兵。输入抄自复盘卡。')
    w('')
    w('| 个案 | 对方打过来 m | 这个号的存兵 | 这个号的地 | 守得住要的留底 | 缺口 | 缺口 ÷ 存兵 | 逐拍重放里实际差多少 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: |')
    m_att, ratio, terr = 513000, 2.08, 3158
    bal = m_att / ratio
    keep = (m_att - 1.5 * terr) / 1.78
    gap = keep - bal
    w(f'| A037 leo_tx，2590 拍 | 513k | {kfmt(bal)} | {fmt(terr)} | {kfmt(keep)} | {kfmt(gap)} | {100 * gap / bal:.0f}% | 2589 拍多 25k 就不被除名，多 20k 不够 |')
    w('')
    w('- 输入出处：reviews/A037.md 第 5 节「kakoscsiga … 2590 全仓 513k（＝leo_tx 存兵的 2.08 倍）」、leo_tx 一行的地 3,158 格、「差多少兵」一条（`whatif_bal.mjs`）。存兵 = 513k ÷ 2.08。')
    w(f'- 现在的弃子线（L4455）：挨打量 > 1.65 × 存兵 就不救；这里是 2.08 倍，所以被判弃子。按缺口算，只差存兵的 {100 * gap / bal:.0f}%。')
    cap2589 = don_cap(2589)
    w(f'- 配额放不放得下：2589 拍上限 {cap2589} 点，leo_tx 此前没有收过捐兵；这张图（陆地 {fmt(vor["A037"]["land"])} 格）每点买 {fmt(100 * (1 + vor["A037"]["land"] // 300) / 100)} 兵，单笔最多收 {kfmt(vmax_before_3213(2589, vor["A037"]["land"]))}，放得下。')
    w('')

    # ---------------------------------------------------------------- §4
    w('## 4. 同一个决定连发 n 条：全部落地之后还剩多少存兵（game.js L1239–1248）')
    w('')
    w('每条陆攻取执行那一刻存兵的 (pct+1)/1024，另收 12/1024 手续费；n 条都落地后剩下的比例 = (1 − (pct + 1 + 12) ÷ 1024)^n，与落地次序无关。')
    w('')
    w('| 单条的千分比 pct | 单条取走（含费） | 2 条后剩 | 3 条后剩 | 5 条后剩 | 7 条后剩 | 9 条后剩 |')
    w('| --: | --: | --: | --: | --: | --: | --: |')
    for pct in [100, 126, 190, 210, 234, 300]:
        x = (pct + 1 + 12) / 1024
        w(f'| {pct} | {100 * x:.1f}% | ' + ' | '.join(f'{100 * (1 - x) ** n:.0f}%' for n in (2, 3, 5, 7, 9)) + ' |')
    w('')
    want, bal0, n = 54859, 239647, 7
    pct = math.ceil(want * 1024 / bal0) - 1
    x = (pct + 1 + 12) / 1024
    w(f'- 对照录像：A095 的 kaito9 t=1530 有 239,647 兵，决定打出 54,859（`Strategy.send` L482 算出 pct = {pct}）；这条指令落地了 7 条。按上式 7 条后剩 {100 * (1 - x) ** n:.1f}%，也就是打出 {100 * (1 - (1 - x) ** n):.1f}%；复盘卡记的是 205k = 86%（reviews/A095.md）。')
    w('- 3 条、每条 pct ≤ 190：全部同拍落地也还剩一半以上（上表 52%）。')
    w('')

    # ---------------------------------------------------------------- §5
    w('## 5. 固定费率：费 ÷ 送出去的兵')
    w('')
    w('捐兵税 = 捐出方全部存兵的 64/1024（game.js L390），船费 = 32/1024（boats.js L786），都与这一条送多少无关；送出去的兵 = 存兵 × (pct+1)/1024。')
    w('')
    w('| 千分比 pct | 送出去占存兵 | 捐兵：税 ÷ 送出 | 船：船费 ÷ 送出 |')
    w('| --: | --: | --: | --: |')
    for pct in [102, 180, 204, 220, 255, 320, 380, 511, 767]:
        w(f'| {pct} | {100 * (pct + 1) / 1024:.0f}% | {100 * 64 / (pct + 1):.0f}% | {100 * 32 / (pct + 1):.0f}% |')
    w('')
    w('- 现在捐兵的最小千分比是 180（策略 L4506），理想值 220–380（L4500–4505）。税 ÷ 送出 ≤ 25% 要 pct ≥ 255。')
    w('- 船带存兵的两成（pct 204）时船费 ÷ 送出 = 16%；海上每 5 拍再少 1/128（boats.js L360–366）。')
    w('')

    # ---------------------------------------------------------------- §6
    w('## 6. 超软上限以后的利息（game.js L739–746）')
    w('')
    w('存兵超过软上限（100 × 地）以后，利率按 2 × (存兵 − 软上限) ÷ 软上限 的比例扣；到硬上限（150 × 地）为 0。')
    w('')
    w('| 密度（存兵 ÷ 地） | 100 | 105 | 110 | 115 | 120 | 125 | 135 | 150 |')
    w('| --: | --: | --: | --: | --: | --: | --: | --: | --: |')
    w('| 拿到的利息 | ' + ' | '.join(f'{max(0, 100 - 2 * (d - 100)):.0f}%' for d in (100, 105, 110, 115, 120, 125, 135, 150)) + ' |')
    w('')

    # ---------------------------------------------------------------- §7
    w('## 7. 用胜率分辨新旧策略要多少局')
    w('')
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'out', 'pattern-scan.tsv'), encoding='utf-8'), delimiter='\t'))
    a_rows = [r for r in rows if r['matchId'].startswith('A')]
    wins = sum(1 for r in a_rows if r['result'].lower().startswith('w'))
    p1 = wins / len(a_rows)
    w(f'A 组（`out/pattern-scan.tsv`）{len(a_rows)} 局赢 {wins} 局，胜率 {100 * p1:.1f}%。两个比例之差的双侧检验（α = 0.05，功效 0.8，正态近似），每一边要的局数：')
    w('')
    w('| 新策略的胜率 | 每一边要的局数 |')
    w('| --: | --: |')
    za, zb = 1.959964, 0.841621
    for p2 in (0.15, 0.20, 0.25, 0.30):
        pb = (p1 + p2) / 2
        n = (za * math.sqrt(2 * pb * (1 - pb)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p2 - p1) ** 2
        w(f'| {100 * p2:.0f}% | {math.ceil(n):,} |')
    w('')
    w('- 这是独立对局的算法。检查点场景来自同一批录像，彼此不独立，实际要的更多。')
    w('')

    text = '\n'.join(L) + '\n'
    if out:
        with open(os.path.join(ROOT, out) if not os.path.isabs(out) else out, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'写出 {out}（{len(L)} 行）')
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
