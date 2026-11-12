#!/usr/bin/env python3
"""foeprofile.py — 对手画像（录像真值）：打我方号的外人真人是怎么出手的。单局产物，给 crossmatch.py foes 读。

数据：eng_replay.cjs 写的 out/<id>/sim_state.json（外人对我方号的每条陆攻带出兵数、出手前余额、双方当时的地和兵；
每条登陆；每笔捐款；每 30 拍一个采样的地 / 兵）+ 录像原始指令（id 1 陆攻 / 2 捐款 / 3 发船，dX = 千分比，dZ = 目标）。

用法：python3 foeprofile.py <matchId> [json]        json = 写 out/<id>/foeprofile.json
口径：
  打击 = 外人真人（出手时没离开）对「在场的我方号」（没离开、异队）生效的陆攻指令，一条算一次；兵 = 这条指令实际出的兵。
  目标密度 = 目标当拍 兵 ÷ 地；出手方密度 = 出手前余额 ÷ 它当拍的地；兵力比 = 出手前余额 ÷ 目标当拍的兵。
  目标刚清过仓 = 目标当拍的兵 < 之前 150 拍内（30 拍一个采样）最高兵的一半，而同期领土没掉 10% 以上（兵是自己花掉 / 捐掉的，不是被打掉地丢的）。
  围攻 = 同一个（外人, 我方号）的陆攻 + 登陆，相邻两条隔 900 拍以上拆开；只算外人合计 >= 20 万兵的组（simdigest.siege_rows）。
  登陆 = 外人的船靠上在场我方号的岸；大登陆 = 船上兵 >= 目标当时兵的 50% 且 >= 2 万。
  外人之间的捐款 = 捐款人、收款人都不是我方号。
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

TD = [('<35', 0, 35), ('35~60', 35, 60), ('60~100', 60, 100), ('>=100', 100, 10 ** 9)]
AD = [('<60', 0, 60), ('60~90', 60, 90), ('90~110', 90, 110), ('>=110', 110, 10 ** 9)]
RT = [('<1', 0, 1), ('1~2', 1, 2), ('2~4', 2, 4), ('>=4', 4, 10 ** 9)]
PC = [('<100', 0, 100), ('100~199', 100, 200), ('200~399', 200, 400), ('400~899', 400, 900), ('>=900', 900, 10 ** 9)]
TB = [('<1500', 0, 1500), ('1500~3000', 1500, 3000), ('3000~4284', 3000, 4284), ('>=4284', 4284, 10 ** 9)]


def band(v, bands):
    for name, lo, hi in bands:
        if lo <= v < hi:
            return name
    return bands[-1][0]


def med(v):
    v = [x for x in v if x is not None]
    return round(statistics.median(v), 2) if v else None


def left_at(X, p, t):
    return p in X.leave and t >= X.leave[p]['t']


def build(mid):
    X = SD.Sim(mid)
    S = X.S
    hits = []
    for c in S['squadCmds']:
        if c['k'] != 'atk' or not c.get('ok') or c.get('to') not in X.squad or c['p'] in X.squad or c['p'] >= X.H:
            continue
        p, q, t = c['p'], c['to'], c['t']
        if X.team[p] == X.team[q] or left_at(X, p, t) or left_at(X, q, t) or not c.get('sent'):
            continue
        tb = c.get('toBal') or 0
        tt = c.get('toTerr') or 0
        prev = [X.bal(q, t - k) for k in (30, 60, 90, 120, 150) if t - k >= 0]
        terr_prev = X.terr(q, max(0, t - 150))
        dumped = bool(prev) and tb < 0.5 * max(prev) and tt >= 0.9 * (terr_prev or 0)
        hits.append(dict(t=t, p=p, q=q, sent=c['sent'], pct=c['pct'], tdens=tb / tt if tt else 0, adens=c['B0'] / c['myTerr'] if c.get('myTerr') else 0,
                         ratio=c['B0'] / tb if tb else 99, dumped=dumped))

    def split(key, bands):
        d = {}
        for h in hits:
            a = d.setdefault(band(h[key], bands), dict(n=0, troops=0))
            a['n'] += 1
            a['troops'] += h['sent']
        return d
    doc = dict(matchId=mid, endT=X.endT, hits=dict(n=len(hits), troops=sum(h['sent'] for h in hits), tdens=split('tdens', TD), adens=split('adens', AD), ratio=split('ratio', RT), pct=split('pct', PC),
                                                     tband=split('t', TB), dumped=dict(n=sum(1 for h in hits if h['dumped']), troops=sum(h['sent'] for h in hits if h['dumped'])),
                                                     tdensMed=med([h['tdens'] for h in hits]), adensMed=med([h['adens'] for h in hits]), pctMed=med([h['pct'] for h in hits])))
    # 围攻
    R = [r for r in SD.siege_rows(X) if not r['husk']]
    sg = []
    for r in R:
        f = r['first']
        tb, tt = f.get('toBal') or 0, f.get('toTerr') or 0
        died = r['death'] >= 0 and r['death'] <= r['t1'] + 600
        sg.append(dict(foe=r['foeName'], me=r['name'], t0=r['t0'], t1=r['t1'], troops=r['troops'] + r['boatTroops'], n=r['n'], boats=r['boats'], tdens=tb / tt if tt else 0,
                       ratio=(r['foeBal0'] or 0) / tb if tb else None, fdens=(r['foeBal0'] or 0) / r['foeTerr0'] if r['foeTerr0'] else None,
                       mine=r['mineTroops'], others=r['othersTroops'], donIn=r['donIn'], donOut=r['donOut'], died=died, terr0=tt, terr1=r['terrAfter']))
    doc['sieges'] = dict(n=len(sg), troops=sum(s['troops'] for s in sg), mine=sum(s['mine'] for s in sg), others=sum(s['others'] for s in sg), zeroBack=sum(1 for s in sg if s['mine'] == 0),
                         died=sum(1 for s in sg if s['died']), tdensMed=med([s['tdens'] for s in sg]), ratioMed=med([s['ratio'] for s in sg]), fdensMed=med([s['fdens'] for s in sg]),
                         donOut=sum(s['donOut'] for s in sg), donIn=sum(s['donIn'] for s in sg), lenMed=med([s['t1'] - s['t0'] for s in sg]), nMed=med([s['n'] for s in sg]),
                         lostHalf=sum(1 for s in sg if s['terr0'] and s['terr1'] is not None and s['terr1'] < 0.5 * s['terr0']), rows=sg)
    # 登陆
    lands = [b for b in S['boatLands'] if b['to'] in X.squad and b['p'] not in X.squad and b['p'] < X.H and not b.get('friend') and X.team[b['p']] != X.team[b['to']]
             and not left_at(X, b['to'], b['t']) and not left_at(X, b['p'], b['t'])]
    big = [b for b in lands if b['troops'] >= 20000 and b['troops'] >= 0.5 * (b.get('toBal') or 0)]
    doc['landings'] = dict(n=len(lands), troops=sum(b['troops'] for b in lands), big=len(big), bigTroops=sum(b['troops'] for b in big),
                           tband={k: sum(1 for b in big if band(b['t'], TB) == k) for k, _, _ in TB})
    # 外人之间的捐款
    fd = [x for x in S['donations'] if x.get('ok') and x['from'] not in X.squad and x['to'] not in X.squad and x['from'] < X.H and x['to'] < X.H]
    hi = [x for x in fd if x['pct'] >= 900]
    recv = defaultdict(int)
    for x in fd:
        recv[x['to']] += x['delivered']
    top = sorted(recv.items(), key=lambda kv: -kv[1])[:3]
    doc['foeDon'] = dict(n=len(fd), delivered=sum(x['delivered'] for x in fd), fee=sum(x['fee'] for x in fd), hiN=len(hi), hiDelivered=sum(x['delivered'] for x in hi),
                         late=sum(1 for x in fd if x['t'] >= 3213), pctMed=med([x['pct'] for x in fd]),
                         top=[dict(name=X.name(p), team=X.team[p], delivered=v, peakTerr=max(X.hum[p]['terr'])) for p, v in top],
                         squadN=sum(1 for x in S['donations'] if x.get('ok') and x['from'] in X.squad))
    # 对我方出兵最多的 5 个外人
    tot = defaultdict(int)
    for h in hits:
        tot[h['p']] += h['sent']
    game = [c for c in X.M.cmds if c.get('phase') == 'game' and c['player'] < X.H]
    tops = []
    for p, v in sorted(tot.items(), key=lambda kv: -kv[1])[:5]:
        hs = [h for h in hits if h['p'] == p]
        cnt = defaultdict(int)
        for h in hs:
            cnt[h['pct']] += 1
        allc = [c for c in game if c['player'] == p and c['id'] == 1]
        ac = defaultdict(int)
        for c in allc:
            ac[c['dX']] += 1
        mode = max(ac.items(), key=lambda kv: kv[1]) if ac else (None, 0)
        tg = defaultdict(int)
        for h in hs:
            tg[h['q']] += h['sent']
        # 同时打几个：每条打击前后 150 拍内它打的我方号个数
        conc = med([len({g['q'] for g in hs if abs(g['t'] - h['t']) <= 150}) for h in hs])
        don_out = [x for x in S['donations'] if x.get('ok') and x['from'] == p]
        don_in = [x for x in S['donations'] if x.get('ok') and x['to'] == p]
        tops.append(dict(name=X.name(p), team=X.team[p], troops=v, n=len(hs), pctTop=sorted(cnt.items(), key=lambda kv: -kv[1])[:3], adensMed=med([h['adens'] for h in hs]), tdensMed=med([h['tdens'] for h in hs]),
                         ratioMed=med([h['ratio'] for h in hs]), targets=len(tg), mainShare=max(tg.values()) / v if v else 0, atOnce=conc, cmdsAll=len(allc), modePct=mode[0], modeShare=mode[1] / len(allc) if allc else 0,
                         distinctPct=len(ac), boats=sum(1 for b in lands if b['p'] == p), donOut=len(don_out), donIn=len(don_in), donInTroops=sum(x['delivered'] for x in don_in),
                         fate='活到终局' if X.deathT[p] < 0 and p not in X.leave else (f"离开 t={X.leave[p]['t']}" if p in X.leave else f"阵亡 t={X.deathT[p]}"), peakTerr=max(X.hum[p]['terr']),
                         terr=[X.terr(p, min(t, X.endT)) for t in (630, 1500, 3000)], t0=min(h['t'] for h in hs), t1=max(h['t'] for h in hs)))
    doc['top'] = tops
    # 我方号自己的陆攻千分比（对照）：对真人
    ours = [c for c in S['squadCmds'] if c['k'] == 'atk' and c.get('ok') and c['p'] in X.squad and c.get('to') is not None and c['to'] < X.H and c['to'] not in X.squad and c.get('sent')]
    doc['ours'] = dict(n=len(ours), troops=sum(c['sent'] for c in ours), pctMed=med([c['pct'] for c in ours]),
                       pct={k: dict(n=sum(1 for c in ours if band(c['pct'], PC) == k), troops=sum(c['sent'] for c in ours if band(c['pct'], PC) == k)) for k, _, _ in PC})
    return doc


def pc(a, b):
    return f'{100 * a / b:.1f}%' if b else '—'


def wan(x):
    x = int(round(x or 0))
    if abs(x) < 10000:
        return f'{x:,}'
    if abs(x) < 100000000:
        return f'{x / 1e4:,.1f} 万'
    return f'{x / 1e8:.2f} 亿'


def dist(d, bands, tot):
    return '；'.join(f"{k} {pc(d.get(k, {}).get('troops', 0), tot)}（{d.get(k, {}).get('n', 0)} 条）" for k, _, _ in bands)


def show(d):
    h = d['hits']
    print(f"{d['matchId']}：外人真人对在场我方号的陆攻 {h['n']} 条、{wan(h['troops'])}兵（录像到 t={d['endT']}）")
    if h['n']:
        print(f"  按目标当拍密度（兵占比）：{dist(h['tdens'], TD, h['troops'])}；中位 {h['tdensMed']}")
        print(f"  按出手方密度：{dist(h['adens'], AD, h['troops'])}；中位 {h['adensMed']}")
        print(f"  按兵力比（出手方余额 ÷ 目标兵）：{dist(h['ratio'], RT, h['troops'])}")
        print(f"  按千分比：{dist(h['pct'], PC, h['troops'])}；中位 {h['pctMed']}‰")
        print(f"  按拍：{dist(h['tband'], TB, h['troops'])}")
        print(f"  目标刚清过仓的：{h['dumped']['n']} 条、{wan(h['dumped']['troops'])}兵（{pc(h['dumped']['troops'], h['troops'])}）")
    s = d['sieges']
    if s['n']:
        print(f"  围攻（>=20 万兵的组）{s['n']} 组、{wan(s['troops'])}兵：第一条时目标密度中位 {s['tdensMed']}、出手方密度中位 {s['fdensMed']}、兵力比中位 {s['ratioMed']}；每组陆攻条数中位 {s['nMed']}、持续中位 {s['lenMed']} 拍；"
              f"目标自己还手 {wan(s['mine'])}（{pc(s['mine'], s['troops'])}），一兵没还的 {s['zeroBack']} 组；别的我方号同期打这个外人 {wan(s['others'])}；目标同期捐出 {wan(s['donOut'])}、收到 {wan(s['donIn'])}；"
              f"末条后 600 拍内阵亡 {s['died']} 组，末条后 100 拍领土不到开打时一半的 {s['lostHalf']} 组")
    ld = d['landings']
    print(f"  登陆：{ld['n']} 次、{wan(ld['troops'])}兵；大登陆（>= 目标兵的 50% 且 >=2 万）{ld['big']} 次、{wan(ld['bigTroops'])}兵，按拍 {ld['tband']}")
    f = d['foeDon']
    print(f"  外人之间的捐款：{f['n']} 笔、到账 {wan(f['delivered'])}、手续费 {wan(f['fee'])}（损耗率 {pc(f['fee'], f['fee'] + f['delivered'])}）；pct>=900 的 {f['hiN']} 笔、到账 {wan(f['hiDelivered'])}；t>=3213 的 {f['late']} 笔；千分比中位 {f['pctMed']}；"
          f"收得最多：{'、'.join(x['name'] + '（队' + str(x['team']) + '）' + wan(x['delivered']) for x in f['top']) or '—'}。对照：我方号捐出 {f['squadN']} 笔")
    for t in d['top']:
        print(f"  {t['name']}（队{t['team']}，{t['fate']}，峰值 {t['peakTerr']:,} 格；t=630/1500/3000 领土 {t['terr']}）：对我方 {t['n']} 条 {wan(t['troops'])}兵，t={t['t0']}~{t['t1']}；千分比 {' '.join(f'{k}:{v}' for k, v in t['pctTop'])}；"
              f"出手时自己密度中位 {t['adensMed']}、目标密度中位 {t['tdensMed']}、兵力比中位 {t['ratioMed']}；打过 {t['targets']} 个我方号、主目标占 {pc(t['mainShare'], 1)}、前后 150 拍内同时打 {t['atOnce']} 个；"
              f"整局陆攻 {t['cmdsAll']} 条、{t['distinctPct']} 种千分比、最常用 {t['modePct']}‰ 占 {pc(t['modeShare'], 1)}；登陆我方 {t['boats']} 次；捐出 {t['donOut']} 笔、收到 {t['donIn']} 笔（{wan(t['donInTroops'])}）")
    o = d['ours']
    print(f"  对照｜我方号对外人真人的陆攻 {o['n']} 条、{wan(o['troops'])}兵，千分比中位 {o['pctMed']}：" + '；'.join(f"{k} {pc(o['pct'][k]['troops'], o['troops'])}（{o['pct'][k]['n']} 条）" for k, _, _ in PC))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    doc = build(mid)
    show(doc)
    if len(sys.argv) > 2 and sys.argv[2] == 'json':
        p = os.path.join(OUT, mid, 'foeprofile.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
