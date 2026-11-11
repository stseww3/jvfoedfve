#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""99_quota_checks.py — R07：isNoFullSend 的影子配额是被哪条指令清零的、清零之后挡掉了什么。

输入（都在 out/<matchId>/）：
  shadow_quota_checks.tsv   65_shadow.mjs：Policy.updateShadowQuota 末尾每一次「出兵后核对余额」的结果
                            （过期 / 扣减 / 清零；判定按源码条件在脚本里重算，sq1 是策略对象里核对后的配额）
  shadow_nofull.tsv         65_shadow.mjs：被 isNoFullSend 挡掉 / 改成 1 兵试探的指令
  humans_cmd.tsv            60_truth.cjs：录像里真号实际落地的指令（落地拍、发兵、手续费）

源码（Vb）：发令后记下 {发令时余额 bal0、手续费 fee、想发 want}；之后第 1~7 拍里只要余额 < bal0 − fee 就核对一次：
  落差 = bal0 − 当拍余额 − fee；want ≥ 1.12×落差 → isNoFullSend 置真、影子配额归零；否则配额减去落差。
  落差里混着：这条指令真实落地扣的兵（如果已经落地）、同段入账的利息地租（把落差抹小）、挨打掉的兵和别的指令（把落差撑大）。

用法：python3 99_quota_checks.py <matchId> [--t0 1500] [--win 60]
输出：out/<matchId>/shadow_quota_checks.txt
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def opt(k, d):
    a = sys.argv[2:]
    return a[a.index(k) + 1] if k in a else d


def fmt(x):
    return f"{int(round(x)):,}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    t0 = int(opt('--t0', '1500'))
    win = int(opt('--win', '60'))
    out = os.path.join(HERE, '..', 'out', mid)
    f_qc = os.path.join(out, 'shadow_quota_checks.tsv')
    if not os.path.exists(f_qc):
        print('缺 shadow_quota_checks.tsv：先跑 65_shadow.mjs')
        sys.exit(1)
    rows = []
    with open(f_qc, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if not r.get('t'):
                continue
            for k in ('t', 'issueT', 'want', 'bal0', 'fee', 'bal', 'sq0', 'sq1', 'noFull0', 'terr'):
                r[k] = int(float(r[k])) if r[k] not in ('', None) else 0
            r['actual'] = int(float(r['actual'])) if r['actual'] not in ('', None) else None
            rows.append(r)
    blocks = []
    f_nf = os.path.join(out, 'shadow_nofull.tsv')
    if os.path.exists(f_nf):
        with open(f_nf, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if r['event'] in ('挡掉', '改成1兵试探'):
                    blocks.append({'t': int(r['t']), 'bot': r['bot'], 'event': r['event'], 'target': r['detail_or_target'],
                                   'want': int(float(r['wantTroops'] or 0)), 'sq': int(float(r['shadowQuota'] or 0))})
    landed = {}
    f_h = os.path.join(out, 'humans_cmd.tsv')
    if os.path.exists(f_h):
        with open(f_h, encoding='utf-8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if r['squad'] != '1' or r['kind'] not in ('attack', 'boat', 'boatTo', 'donate'):
                    continue
                bot = r['name'].split('] ')[-1].strip()
                landed.setdefault(bot, []).append({'t': int(r['t']), 'kind': r['kind'], 'tt': r['tt'], 'troops': int(float(r['troops'] or 0)),
                                                   'fee': int(float(r['fee'] or 0)), 'pct': r['pct']})

    L = [f"# {mid} 影子：isNoFullSend 的影子配额每一次出兵后核对的结果（99_quota_checks.py；输入 shadow_quota_checks.tsv / shadow_nofull.tsv / humans_cmd.tsv）",
         "# 清零 = 想发 ≥ 1.12×落差（落差 = 发令时余额 − 核对拍余额 − 手续费）→ isNoFullSend 置真、配额归零；扣减 = 配额减去落差；过期 = 发令后 7 拍内余额没有少过手续费，不核对。",
         "# 影子看到的余额就是录像里真号的余额：真号那条指令落地之前，落差是别的事造成的（挨打掉兵、更早的指令落地）；落地之后，同段入账的利息地租会把落差抹小。",
         ""]
    bad = sum(1 for r in rows if r['outcome'] == '清零' and r['sq1'] != 0)
    L.append(f"## A. 各号合计（清零按被核对的指令分：打无主地 / 打内置 AI / 打真人）〔自检：判成清零的 {sum(1 for r in rows if r['outcome'] == '清零')} 次里，策略对象里的配额当拍不是 0 的 {bad} 次〕")
    per = {}
    for r in rows:
        o = per.setdefault(r['bot'], dict(exp=0, ded=0, zero=0, zN=0, zA=0, zH=0, lost=0, after=0))
        if r['outcome'] == '过期':
            o['exp'] += 1
        elif r['outcome'] == '扣减':
            o['ded'] += 1
        else:
            o['zero'] += 1
            if r['target'] == '无主地':
                o['zN'] += 1
            elif r['target'].startswith('AI#'):
                o['zA'] += 1
            else:
                o['zH'] += 1
            o['lost'] += r['sq0']
            o['after'] += r['noFull0']
    tot = dict(exp=0, ded=0, zero=0, zN=0, zA=0, zH=0, lost=0, after=0)
    for b, o in per.items():
        for k in tot:
            tot[k] += o[k]
        L.append(f"  {b}: 核对 {o['exp'] + o['ded'] + o['zero']} 次 | 过期 {o['exp']} | 扣减 {o['ded']} | 清零 {o['zero']}（无主地 {o['zN']} / 内置 AI {o['zA']} / 真人 {o['zH']}；其中锁上之后 {o['after']} 次）| 清零时作废的配额合计 {fmt(o['lost'])}")
    L.append(f"  合计: 核对 {tot['exp'] + tot['ded'] + tot['zero']} 次 | 过期 {tot['exp']} | 扣减 {tot['ded']} | 清零 {tot['zero']}（无主地 {tot['zN']} / 内置 AI {tot['zA']} / 真人 {tot['zH']}；其中锁上之后 {tot['after']} 次）| 清零时作废的配额合计 {fmt(tot['lost'])}")

    zs = [r for r in rows if r['outcome'] == '清零' and r['t'] >= t0]
    bl = [b for b in blocks if b['t'] >= t0]
    # 每条被挡的指令归到它之前 win 拍内最近的一次清零
    owner = {}
    orphan = []
    for b in bl:
        cand = [r for r in zs if r['bot'] == b['bot'] and r['t'] <= b['t'] <= r['t'] + win]
        if cand:
            z = max(cand, key=lambda r: r['t'])
            owner.setdefault((z['bot'], z['t']), []).append(b)
        else:
            orphan.append(b)
    L += ["", f"## B. t≥{t0} 的清零（核对拍 号 | 被核对的指令：发令拍 → 目标 pct，想发 | 发令时余额 − 手续费 − 核对拍余额 = 落差（÷想发）| 真号在 [发令拍, 核对拍) 生效的指令（影子下一拍才看得到）| 配额 清零前 → 0 | 之后 {win} 拍里被挡 / 改成 1 兵试探）"]
    n_land = n_noland = 0
    lost = 0
    for r in zs:
        # 录像里第 T 拍生效的指令，影子在 g.t = T+1 才看得到（影子在每拍结算之后决策）
        ld = [c for c in landed.get(r['bot'], []) if r['issueT'] <= c['t'] < r['t']]
        if ld:
            n_land += 1
            s_tr = sum(c['troops'] for c in ld)
            s_fee = sum(c['fee'] for c in ld)
            net_in = s_tr + s_fee - (r['bal0'] - r['bal'])
            ld_txt = f"落地 {len(ld)} 条（发兵 {fmt(s_tr)} + 手续费 {fmt(s_fee)}；余额只少 {fmt(r['bal0'] - r['bal'])}，同段其他净入账 {fmt(net_in)}）"
        else:
            n_noland += 1
            ld_txt = f"没有落地（余额少的 {fmt(r['bal0'] - r['bal'])} 不是这条指令扣的）"
        lost += r['sq0']
        ob = owner.get((r['bot'], r['t']), [])
        if ob:
            nb = sum(1 for b in ob if b['event'] == '挡掉')
            npk = len(ob) - nb
            tg = ' / '.join(dict.fromkeys(b['target'] for b in ob))
            a_txt = f"挡掉 {nb} 条、试探 {npk} 条（t={ob[0]['t']}~{ob[-1]['t']}，{tg}；想发 {fmt(sum(b['want'] for b in ob))}）"
        else:
            a_txt = "无"
        ratio = (r['actual'] or 0) / max(1, r['want'])
        L.append(f"  t={r['t']} {r['bot']} | {r['issueT']} → {r['target']} pct={r['pct']}，想发 {fmt(r['want'])} | {fmt(r['bal0'])} − {fmt(r['fee'])} − {fmt(r['bal'])} = {fmt(r['actual'] or 0)}（{ratio:.2f}）| {ld_txt} | {fmt(r['sq0'])} → 0 | {a_txt}")
    n_own = sum(len(v) for v in owner.values())
    n_own_blk = sum(1 for v in owner.values() for b in v if b['event'] == '挡掉')
    L.append(f"  小计：t≥{t0} 清零 {len(zs)} 次——核对时真号那条指令还没落地的 {n_noland} 次、已经落地的 {n_land} 次；作废的配额合计 {fmt(lost)}；"
             f"t≥{t0} 被挡 / 改成试探的 {len(bl)} 条里 {n_own} 条（挡掉 {n_own_blk}、试探 {n_own - n_own_blk}，想发 {fmt(sum(b['want'] for v in owner.values() for b in v))}）前 {win} 拍内有一次清零，{len(orphan)} 条没有")
    if orphan:
        L.append("  前面没有清零的：" + '；'.join(f"t={b['t']} {b['bot']} → {b['target']}（{b['event']}，想发 {fmt(b['want'])}，配额 {fmt(b['sq'])}）" for b in orphan))

    L += ["", f"## C. t≥{t0} 的扣减与过期（各号：扣减 次 / 落差合计；过期 次）"]
    for b in per:
        d = [r for r in rows if r['bot'] == b and r['t'] >= t0 and r['outcome'] == '扣减']
        e = [r for r in rows if r['bot'] == b and r['t'] >= t0 and r['outcome'] == '过期']
        if d or e:
            L.append(f"  {b}: 扣减 {len(d)} 次 / {fmt(sum(r['actual'] or 0 for r in d))}；过期 {len(e)} 次")
    with open(os.path.join(out, 'shadow_quota_checks.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L[4:6 + len(per)]))
    print(L[[i for i, x in enumerate(L) if x.startswith('  小计')][0]])


if __name__ == '__main__':
    main()
