#!/usr/bin/env python3
"""g0_lists.py — 生成保真度验收用的运行清单（只有历史旧策略：每一局跑它当年线上那一版）。

读：sim-v2/packs/index.json（入库各局的录像长度、我方席位、各席位出局拍）、sim-v2/traces/<局>.json（实录阶梯覆盖到哪一拍）、
    sim-v2/calib/live/<局>.json（--mode live 算的实盘签名：630~1530 拍的同拍批占比，用来分「不卡 / 卡顿」）、
    sim-v2/tools/g0_list.txt（最早那 60 次断面运行，原样保留）、sim-v2/tools/arena_calib_list20.txt（核心 20 局）
写：sim-v2/tools/verify_list.txt    入库的全部局（--mode verify）
    sim-v2/tools/g0_list_more.txt   核心 20 局：把 630 / 1530 两个断面补齐成「各局 × C0 / C1 / C2 / C3」的整张表（去掉 g0_list.txt 里已有的）
    sim-v2/tools/g0_list_ext.txt    为覆盖 Va / Vc 新接进来的局：630 断面 × C0 / C1 / C2 / C3，加 1530 断面的 C2
    sim-v2/tools/g0_list_ext_more.txt 新接进来的局：1530 断面余下的 C0 / C1 / C3（排在最后跑）
    sim-v2/tools/attr_list.txt      核心 20 局的通道延迟归因：断面 t0 = 0 / 630 / 1500 / 4284，窗口 0~630、630~1530、1500~2400、4284~5184，
                                     C0、C1、C2、C2:pagedeath=0（有页面中途停摆的局）、C3（不卡的局），种子 1。
                                     630 这个断面的 C0 / C1 / C2 / C3（种子 1）与上面那张整表里的运行是同一次运行（同一局、同一断面、同一窗口、
                                     同一通道、同一种子），不重复跑：tools/g0_report.mjs 直接从 calib/g0/ 取；这里只列它没有的 C2:pagedeath=0
    sim-v2/tools/attr_list_ext.txt  新接进来的局：同上
    sim-v2/tools/attr_list_seeds.txt 核心 20 局在卡顿波所在的两个断面（630 / 1500）的 C1、C2 换种子 2 再跑一遍（量随机种子带来的波动）
    sim-v2/tools/fill_list.txt      C2 已知点之间的另外三种补法（linear / nearest / burst；auto 就是整张表里的 C2）在 630~1530 的对照
                                     （核心 20 局里卡过的局；不卡的局不跑）

清单每行：<标签> <局> <t0> <len> <策略> <通道> [其余开关]，交给 tools/g0_batch.mjs（或 tools/g0_run.sh）跑。
用法（在 c136-review/agents/R06 下；先跑完 --mode live）：python3 sim-v2/tools/g0_lists.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SIMV2 = os.path.dirname(HERE)
PK = json.load(open(os.path.join(SIMV2, 'packs', 'index.json')))
MIN_WIN = 300          # 窗口至少要有这么多拍，不然不跑
CORE = [l.split()[0] for l in open(os.path.join(HERE, 'arena_calib_list20.txt')) if l.strip() and not l.startswith('#')]


def batch_share(mid):
    # 这一局当年 630~1530 拍的同拍批占比（--mode live 的第一个窗口）
    f = os.path.join(SIMV2, 'calib', 'live', mid + '.json')
    if not os.path.exists(f):
        raise SystemExit(f'缺 {f}：先跑 --mode live（tools/g0_all.sh live）')
    r = json.load(open(f))
    if r.get('error') or not r.get('windows'):
        raise SystemExit(f'{f} 里没有窗口结果：{r.get("error")}')
    return r['windows'][0]['batchShare']


def cohort(mid):
    n = int(mid[1:])
    if mid[0] == 'A':
        return 'va' if n <= 17 else 'vb' if n <= 95 else 'vc'
    return 'c110'


def replay_last(mid):
    return int(PK[mid]['replayLast'])


def trace_max(mid):
    f = os.path.join(SIMV2, 'traces', mid + '.json')
    if not os.path.exists(f):
        return -1
    t = json.load(open(f))
    return max((max(r[0] for r in rows) if rows else -1) for rows in t['seats'].values())


def has_doomed(mid):
    # 有没有「席位还活着页面就停摆」的席位：粗判（精确的名单由 match.mjs 现算），只用来决定要不要多跑一条 pagedeath=0
    f = os.path.join(SIMV2, 'traces', mid + '.json')
    if not os.path.exists(f):
        return False
    t = json.load(open(f))
    last = int(PK[mid]['replayLast'])
    dt = PK[mid].get('deathT') or {}
    for p, ll in (t.get('lastLog') or {}).items():
        d = dt.get(p, -1)
        if ll >= 0 and ll + 1 < (d if d >= 0 else last - 90):
            return True
    return False


MIDS = sorted(PK.keys())
CLEAN = [m for m in MIDS if batch_share(m) < 0.15]     # 分档与 tools/live_table.mjs 的 lagClass 相同：< 15% 不卡，≥ 50% 卡顿
open(os.path.join(HERE, 'verify_list.txt'), 'w').write('# 入库的全部局：--mode verify\n' + '\n'.join(f'{m} {cohort(m)}' for m in MIDS) + '\n')
old = set()
for line in open(os.path.join(HERE, 'g0_list.txt')):
    line = line.strip()
    if line and not line.startswith('#'):
        old.add(line.split()[0])

EXT = [m for m in MIDS if m not in CORE]
COREM = [m for m in MIDS if m in CORE]

# ---- 630 / 1530 整张表
n_more = 0
for fname, mids, what, pick in (
        ('g0_list_more.txt', COREM, '核心 20 局：把 630 / 1530 两个断面补齐成 各局 × C0 / C1 / C2 / C3（g0_list.txt 已有的不重复）', lambda t0, ch: True),
        ('g0_list_ext.txt', EXT, '新接进来的局（Va / Vc）：630 断面 × C0 / C1 / C2 / C3，加 1530 断面的 C2', lambda t0, ch: t0 == 630 or ch == 'C2'),
        ('g0_list_ext_more.txt', EXT, '新接进来的局（Va / Vc）：1530 断面余下的 C0 / C1 / C3', lambda t0, ch: not (t0 == 630 or ch == 'C2'))):
    more = [f'# {what}', '# <标签> <局> <t0> <len> <策略> <通道>']
    for t0, ln in ((630, 900), (1530, 1680)):
        for ch in ('C2', 'C1', 'C0', 'C3'):
            if not pick(t0, ch):
                continue
            for mid in mids:
                if replay_last(mid) - 1 - t0 < MIN_WIN:
                    continue
                s = cohort(mid)
                tag = f'{mid}-{t0:04d}-{s}-{ch}'
                if tag not in old:
                    more.append(f'{tag} {mid} {t0} {ln} {s} {ch}')
    open(os.path.join(HERE, fname), 'w').write('\n'.join(more) + '\n')
    n_more += len(more) - 2

# ---- 通道延迟归因
# 窗口：前两个断面跑到下一个断面；1500 拍以后其余真人的指令大半指向真人，照录像重放失效得快（会审提案 §1.2 的边界），只跑 900 拍
CPS = ((0, 630), (630, 900), (1500, 900), (4284, 900))
head = ['# 通道延迟反事实归因：attr_list.txt（种子 1，核心 20 局）、attr_list_ext.txt（种子 1，新接进来的局）、attr_list_seeds.txt（种子 2、3，核心 20 局，量随机种子带来的波动）',
        '# <标签> <局> <t0> <len> <策略> <通道> [--seed n]']
n_attr = 0
for fname, seeds, mids in (('attr_list.txt', (1,), COREM), ('attr_list_ext.txt', (1,), EXT), ('attr_list_seeds.txt', (2,), COREM)):
    attr = []
    # 清单里的先后就是跑的先后。机器挤、队排不完的时候，要先有的是「每个断面、每一局都有的那几条臂」：
    # 先按臂排（C2 原样复现 → C1 → C0 → 关掉页面停摆的 C2 → C3），同一条臂里按断面排（1500 → 0 → 4284 → 630），再按局
    for t0, ln in sorted(CPS, key=lambda c: (1500, 0, 4284, 630).index(c[0])):
        for mid in mids:
            if replay_last(mid) - 1 - t0 < MIN_WIN:
                continue
            s = cohort(mid)
            tmax = trace_max(mid)
            c2 = tmax >= t0 + 60                      # 实录阶梯在窗口里还有已知点，C2 才有意义
            many = t0 in (630, 1500)                  # 卡顿波所在的两个断面：换种子再跑一遍
            grid = t0 == 630                          # 这个断面的 C0 / C1 / C2 / C3（种子 1）就是 630 / 1530 整表里的运行，不重复列
            for k in seeds:
                if k != 1 and not many:
                    continue
                if k == 1 and not grid:
                    attr.append(f'{mid}-{t0:04d}-C0 {mid} {t0} {ln} {s} C0')
                if not (k == 1 and grid):
                    attr.append(f'{mid}-{t0:04d}-C1-s{k} {mid} {t0} {ln} {s} C1 --seed {k}')
                if c2 and not (k == 1 and grid):
                    attr.append(f'{mid}-{t0:04d}-C2-s{k} {mid} {t0} {ln} {s} C2 --seed {k}')
                if k == 1 and c2 and has_doomed(mid):
                    attr.append(f'{mid}-{t0:04d}-C2nd-s1 {mid} {t0} {ln} {s} C2:pagedeath=0 --seed 1')
                if k == 1 and mid in CLEAN and many and not grid:
                    attr.append(f'{mid}-{t0:04d}-C3-s1 {mid} {t0} {ln} {s} C3 --seed 1')
    arm_rank = lambda line: ('C2-', 'C1-', 'C0', 'C2nd-', 'C3-').index(next(a for a in ('C2nd-', 'C2-', 'C1-', 'C3-', 'C0') if line.split()[0].split('-', 2)[2].startswith(a)))
    attr = [l for _, l in sorted(enumerate(attr), key=lambda il: (arm_rank(il[1]), il[0]))]
    tmp = os.path.join(HERE, fname + '.tmp')
    open(tmp, 'w').write('\n'.join(head + attr) + '\n')
    os.replace(tmp, os.path.join(HERE, fname))
    n_attr += len(attr)

# ---- C2 的补法对照
fill = ['# C2 已知点之间的补法对照（630~1530；auto 补法就是 g0 整张表里的 C2）。只跑核心 20 局里卡过的局（不卡的局不跑）']
for mid in COREM:
    if replay_last(mid) - 1 - 630 < MIN_WIN or mid in CLEAN:
        continue
    s = cohort(mid)
    for f in ('linear', 'nearest', 'burst'):
        fill.append(f'{mid}-0630-{f} {mid} 630 900 {s} C2:fill={f}')
open(os.path.join(HERE, 'fill_list.txt'), 'w').write('\n'.join(fill) + '\n')

print(f'入库 {len(MIDS)} 局，其中不卡的 {len(CLEAN)} 局：{" ".join(CLEAN)}')
print(f'verify_list.txt {len(MIDS)} 行；g0_list_more.txt + g0_list_ext.txt + g0_list_ext_more.txt {n_more} 行；attr_list.txt + attr_list_ext.txt + attr_list_seeds.txt {n_attr} 行；fill_list.txt {len(fill) - 1} 行')
