#!/usr/bin/env python3
"""coregates.py — t>=1500 影子策略每个决策拍「对真人报价 / 对非真人报价」从 buyLand 的哪一行出去，按时段汇总。
单局产物，给 crossmatch.py gates 读。

影子 = 策略源码（c110）跑在录像重演的真实局面上，指令只记不执行
（strat_probe.mjs <id> --me squad --json --tally 写的 out/<id>/probe.json 的 tally，每个决策拍每个号一行）。
分类口径与 simdigest.py gates 完全相同（直接调 simdigest.gate_rows）：
  真人报价的决策拍 = offers 里至少有一个真人邻居；出口 = 这一拍对真人出了兵就记「出兵」，否则记排第一的真人报价的出口行号。
  非真人报价的决策拍 = offers 里至少有一个内置 AI / 空壳；出口同理。
这里只是按时段切开、把行号并成几类，再补几项（被真人打的拍卡在哪、地价闸上报价与 worth 的中位）。

用法：python3 coregates.py <matchId> [json]        json = 写 out/<id>/coregates.json
时段：1500~3000 / 3000~4284 / 4284+（4284 = 引擎不再检查捐款配额的拍）。
"""
import json
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
from r06lib import OUT  # noqa: E402

BANDS = [('1500~3000', 1500, 3000), ('3000~4284', 3000, 4284), ('4284+', 4284, 10 ** 9)]

HUM_CLASS = [
    ('send', '出兵', lambda g: g == 'send'),
    ('price', '地价闸 L5267（报价 >= worth 且没超软上限）', lambda g: g == 'L5267'),
    ('dpKeep', '保底线 = dpKeep >= 余额 L5361', lambda g: g == 'L5361:dpKeep'),
    ('sbOurs', '保底线 = safeFinite 取到我方号 / 我方空壳的兵 L5361', lambda g: g.startswith('L5361:sb:我方')),
    ('sbOther', '保底线 = safeFinite 取到别人的兵 L5361', lambda g: g.startswith('L5361:sb:')),
    ('chunk', '买不起整笔且不足 chunk L5528', lambda g: g == 'L5528'),
    ('sole', '唯一真人缓冲 L5271', lambda g: g == 'L5271'),
    ('crowded', 'crowdedHard L5280', lambda g: g == 'L5280'),
    ('siege', 'siegeShrink L5345', lambda g: g == 'L5345'),
    ('inflight', '本机看到的在途兵已够 L5490 / L5504 / L5511', lambda g: g in ('L5490', 'L5504', 'L5511')),
    ('pulse', 'pulse 太小 L5498 / L5506 / L5520', lambda g: g in ('L5497', 'L5498', 'L5506', 'L5520')),
    ('later', '排在前面的报价已 break', lambda g: g == 'later'),
]
AI_CLASS = [
    ('send', '出兵', lambda g: g == 'send'),
    ('minCmd', '单太小：x < minCmd（余额的 4.7%）L5367', lambda g: g == 'L5367a'),
    ('chunk', '买不起整笔且不足 chunk L5367', lambda g: g == 'L5367b'),
    ('dpKeep', '保底线 = dpKeep >= 余额 L5361', lambda g: g == 'L5361:dpKeep'),
    ('sbOursPass', '保底线 = safeFinite 取到我方号 / 空壳的兵、去掉就能出兵 L5361', lambda g: g.startswith('L5361:sb:我方') and '不够' not in g),
    ('sbOther', '保底线 = safeFinite（别人的兵，或去掉也不够）L5361', lambda g: g.startswith('L5361:sb:')),
    ('already', '已在打它 L5364', lambda g: g == 'L5364'),
    ('price', '地价闸 L5267', lambda g: g == 'L5267'),
    ('later', '排在前面的报价已 break', lambda g: g == 'later'),
]


def classify(g, classes):
    for key, _txt, fn in classes:
        if fn(g):
            return key
    return 'other'


def med(v):
    return round(statistics.median(v), 2) if v else None


def band_doc(X, D, t0, t1):
    R = SD.gate_rows(X, t0, t1)
    _early, core, extra, coreai = R
    hum = defaultdict(int)
    raw_h = defaultdict(int)
    ai = defaultdict(int)
    raw_a = defaultdict(int)
    for p, c in core.items():
        for g, v in c.items():
            hum[classify(g, HUM_CLASS)] += v
            raw_h[g] += v
    for p, c in coreai.items():
        for g, v in c.items():
            ai[classify(g, AI_CLASS)] += v
            raw_a[g] += v
    te = defaultdict(int)
    for p, e in extra.items():
        for k, v in e.items():
            if not k.startswith('humNoSendDon:'):
                te[k] += v
    # 补充：直接扫 tally（与 gate_rows 同一个筛选：在场、没离开、t0<=t<t1、有真人报价）
    on_me = defaultdict(int)
    over_n = over_send = under_n = under_send = 0
    hc, worth, ratio, dens = [], [], [], []
    for r in D['tally']:
        p, t = r['p'], r['t']
        if t < 1500 or not (t0 <= t < t1) or r.get('hum', 0) <= 0 or not X.alive_active(p, t):
            continue
        hg = (r.get('hg') or '?').split(',')
        sent = 'send' in hg
        first = 'send' if sent else hg[0]
        if first == 'L5361':
            first = 'L5361:sb:' + r.get('sbKind', '?') if r.get('h5361') == 'sb' else 'L5361:dpKeep'
        if r.get('over'):
            over_n += 1
            over_send += sent
        else:
            under_n += 1
            under_send += sent
        if r.get('onMe', 0) > 0 and not sent:
            on_me[classify(first, HUM_CLASS)] += 1
        if first == 'L5267' and r.get('hc') is not None and r.get('worth'):
            hc.append(r['hc'])
            worth.append(r['worth'])
            ratio.append(r['hc'] / r['worth'])
            dens.append(r['B'] / max(1, r['L']))
    return dict(
        hum=dict(n=sum(hum.values()), bots=len(core), exits=dict(hum), raw=dict(raw_h), over=te.get('humOver', 0), onMe=te.get('humOnMe', 0), onMeNoSend=te.get('humOnMeNoSend', 0),
                 onMeNoSendExits=dict(on_me), noSendDon=te.get('humNoSendDon', 0), overN=over_n, overSend=over_send, underN=under_n, underSend=under_send,
                 priceGate=dict(n=len(hc), hcMed=med(hc), worthMed=med(worth), ratioMed=med(ratio), densMed=med(dens))),
        ai=dict(n=sum(ai.values()), bots=len(coreai), exits=dict(ai), raw=dict(raw_a)))


def build(mid):
    X = SD.Sim(mid)
    D = SD.shadow_load(X)
    if not D or not D.get('tally'):
        raise SystemExit(f'{mid}: 没有 probe.json 的 tally（先跑 strat_probe.mjs {mid} --me squad --json --tally）')
    doc = dict(matchId=mid, to=D.get('to'), endT=X.endT, bands={})
    for name, t0, t1 in BANDS:
        if (D.get('to') or 0) <= t0:
            continue
        doc['bands'][name] = band_doc(X, D, t0, t1)
    return doc


def pc(a, b):
    return f'{100 * a / b:.1f}%' if b else '—'


def show(doc):
    print(f"{doc['matchId']}：影子策略 t>=1500 的出口（录像到 t={doc['to']}）")
    for name, b in doc['bands'].items():
        h, a = b['hum'], b['ai']
        if h['n']:
            parts = '，'.join(f"{txt} {h['exits'].get(k, 0)}（{pc(h['exits'].get(k, 0), h['n'])}）" for k, txt, _ in HUM_CLASS if h['exits'].get(k))
            if h['exits'].get('other'):
                parts += f"，其他 {h['exits']['other']}"
            print(f"  {name}｜真人报价的决策拍 {h['n']}（{h['bots']} 个号）：{parts}")
            print(f"      超软上限的拍 {h['overN']}，其中出兵 {h['overSend']}（{pc(h['overSend'], h['overN'])}）；没超的拍 {h['underN']}，其中出兵 {h['underSend']}（{pc(h['underSend'], h['underN'])}）")
            om = '，'.join(f"{txt.split(' L')[0]} {h['onMeNoSendExits'].get(k, 0)}" for k, txt, _ in HUM_CLASS if h['onMeNoSendExits'].get(k))
            print(f"      正被真人打的拍 {h['onMe']}，其中没有对任何真人出兵 {h['onMeNoSend']}（{pc(h['onMeNoSend'], h['onMe'])}）：{om}")
            g = h['priceGate']
            if g['n']:
                print(f"      地价闸上的 {g['n']} 拍：最低真人报价中位 {g['hcMed']}、worth 中位 {g['worthMed']}、报价 ÷ worth 中位 {g['ratioMed']}、自己密度中位 {g['densMed']}")
            print(f"      没对真人出兵、同拍影子发了捐款的拍 {h['noSendDon']}")
        if a['n']:
            parts = '，'.join(f"{txt} {a['exits'].get(k, 0)}（{pc(a['exits'].get(k, 0), a['n'])}）" for k, txt, _ in AI_CLASS if a['exits'].get(k))
            if a['exits'].get('other'):
                parts += f"，其他 {a['exits']['other']}"
            print(f"  {name}｜非真人报价（内置 AI / 空壳）的决策拍 {a['n']}（{a['bots']} 个号）：{parts}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    doc = build(mid)
    show(doc)
    if len(sys.argv) > 2 and sys.argv[2] == 'json':
        p = os.path.join(OUT, mid, 'coregates.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
