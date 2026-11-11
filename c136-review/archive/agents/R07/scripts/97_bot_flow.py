#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""97_bot_flow.py — R07：每个号在每个时间段的余额流水，把「拍内正」拆开（利息地租 / 进攻结束退回的兵）。

背景：troop_flow*.txt 的 B 段只给「拍内正」「拍内负」两个合计，拍内正里混着利息地租和退回的兵；
      要说「某个号打出去的兵退回了多少」必须看拆开后的数，这个脚本把 67_troop_flow.mjs 已经算好的逐号拆分打印出来。
输入：out/<matchId>/troop_flow[_<tag>].json（67_troop_flow.mjs；perBot 每行带 eco / refund / giftIn / boatIn / hit）
用法（在 scripts/ 目录下）：
    python3 97_bot_flow.py <matchId> [--tag tp] [--span t0:t1]... [--bots a,b,c]
    --span 的两端必须落在 67_troop_flow 的切点上；不给 --span 就逐个阶段打印
输出：out/<matchId>/bot_flow[_<tag>].txt
  A. 逐号 × 阶段：余额 / 领土 两端，进攻 条 / 兵 / 费，利息地租，退回的兵，挨打掉，捐出（到账 / 费），收捐
  B. --span 给出的每一段：逐号合计（同样的栏目）+ 退回的兵 ÷ 这一段和之前 600 拍内发出的进攻兵
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def f(n):
    return f"{int(round(n)):,}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    tag = ''
    spans = []
    bots = None
    a = sys.argv[2:]
    i = 0
    while i < len(a):
        if a[i] == '--tag':
            tag = a[i + 1]; i += 2
        elif a[i] == '--span':
            x, y = a[i + 1].split(':'); spans.append((int(x), int(y))); i += 2
        elif a[i] == '--bots':
            bots = a[i + 1].split(','); i += 2
        else:
            raise SystemExit(f'未知参数 {a[i]}')
    out = os.path.join(HERE, '..', 'out', mid)
    src = os.path.join(out, f"troop_flow{'_' + tag if tag else ''}.json")
    d = json.load(open(src, encoding='utf-8'))
    per = d['perBot']
    names = [b for b in per if (bots is None or b in bots)]
    T = []
    P = T.append
    P(f"# {mid} 逐号流水拆分（97_bot_flow.py；来源 {os.path.basename(src)}，67_troop_flow.mjs 的逐号逐窗核对差全为 0 才可信）")
    bad = sum(1 for b in per for r in per[b] if r.get('resid') or r.get('resid2'))
    P(f"# 核对：逐号逐窗「期初 − 进攻 − 费 − 捐出 + 收捐 + 拍内正 − 拍内负 ≠ 期末」或「拍内分类合计 ≠ 拍内净变化」的行 {bad} 个")
    P('')
    P('A. 逐号 × 阶段')
    P('号\t阶段\t余额 期初→期末\t领土 期初→期末\t进攻 条/兵/费\t利息地租\t退回的兵\t挨打掉\t捐出 条/到账/费\t收捐 条/额')
    for b in names:
        for r in per[b]:
            if r['bal0'] == 0 and r['bal1'] == 0 and r['terr0'] == 0 and r['terr1'] == 0:
                continue
            P(f"{b}\t{r['t0']}~{r['t1']}\t{f(r['bal0'])}→{f(r['bal1'])}\t{f(r['terr0'])}→{f(r['terr1'])}\t{r['atkN']}/{f(r['atkTroops'])}/{f(r['atkFee'])}\t"
              f"{f(r['eco'])}\t{f(r['refund'])}\t{f(r['hit'])}\t{r['donN']}/{f(r['donAmt'])}/{f(r['donFee'])}\t{r['recvN']}/{f(r['recv'])}")
    if spans:
        cuts = sorted(set(r[k] for b in names for r in per[b] for k in ('t0', 't1')))
        P('')
        P('B. 指定时间段的逐号合计')
        for (t0, t1) in spans:
            if t0 not in cuts or t1 not in cuts:
                raise SystemExit(f'--span {t0}:{t1} 的端点不在切点上：{cuts}')
            P(f'## t={t0}~{t1}')
            P('号\t余额 期初→期末\t领土 期初→期末\t进攻 条/兵/费\t利息地租\t退回的兵\t挨打掉\t捐出 条/到账/费\t收捐 条/额')
            tot = dict(atkN=0, atkTroops=0, atkFee=0, eco=0, refund=0, hit=0, donN=0, donAmt=0, donFee=0, recvN=0, recv=0)
            for b in names:
                rows = [r for r in per[b] if r['t0'] >= t0 and r['t1'] <= t1]
                if not rows:
                    continue
                s = {k: sum(r[k] for r in rows) for k in tot}
                if rows[0]['bal0'] == 0 and rows[0]['terr0'] == 0 and all(v == 0 for v in s.values()):
                    continue
                for k in tot:
                    tot[k] += s[k]
                P(f"{b}\t{f(rows[0]['bal0'])}→{f(rows[-1]['bal1'])}\t{f(rows[0]['terr0'])}→{f(rows[-1]['terr1'])}\t{s['atkN']}/{f(s['atkTroops'])}/{f(s['atkFee'])}\t"
                  f"{f(s['eco'])}\t{f(s['refund'])}\t{f(s['hit'])}\t{s['donN']}/{f(s['donAmt'])}/{f(s['donFee'])}\t{s['recvN']}/{f(s['recv'])}")
            P(f"合计\t-\t-\t{tot['atkN']}/{f(tot['atkTroops'])}/{f(tot['atkFee'])}\t{f(tot['eco'])}\t{f(tot['refund'])}\t{f(tot['hit'])}\t"
              f"{tot['donN']}/{f(tot['donAmt'])}/{f(tot['donFee'])}\t{tot['recvN']}/{f(tot['recv'])}")
    dst = os.path.join(out, f"bot_flow{'_' + tag if tag else ''}.txt")
    open(dst, 'w', encoding='utf-8').write('\n'.join(T) + '\n')
    print('\n'.join(T))


if __name__ == '__main__':
    main()
