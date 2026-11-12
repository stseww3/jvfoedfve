#!/usr/bin/env python3
"""donflow.py — 输血账（录像真值）：我方号捐出的每一笔，按千分比档、收款人收款时的状态、收款后 300 拍做了什么分桶。
单局产物，给 crossmatch.py donflow 读。每笔捐款的原始行来自 simdigest.don_rows（eng_replay.cjs 在引擎里逐笔记下的
到账 / 手续费 / 收款人当时的地和兵 / 正在打收款人的人 / 配额）。

引擎规则（机制笔记 B4~B6）：手续费 = floor(64×捐款人余额/1024)，与 pct 无关；
到账 = min(floor(余额×(pct+1)/1024), 余额−手续费, 收款人离硬上限的余量 150×地−兵)。

用法：python3 donflow.py <matchId> [json]        json = 写 out/<id>/donflow.json
分桶（只算我方号捐出、已执行的）：
  pct 档           <64（到账本来就不高于手续费）/ 64~149 / 150~199（c110 的 153、155、185）/ 200~299（240、280）/ >=300
  收款人           我方在场号 / 我方空壳（已离开，内置 AI 托管）/ 外人
  收款时密度       <50 / 50~100 / 100~125 / >=125（只算在场的我方号）
  被截断           到账 < 名义值 floor(余额×(pct+1)/1024) 的 90%（被收款人余量或「余额−手续费」截断）；到账 = 0 的单列
  收款时正被人打   onRecv 非空
  收款后 300 拍    阵亡 / 没有任何陆攻或发船指令进录像 / 又捐出 >= 到账的一半 / 战斗耗兵 >= 到账的一半（都只算在场的我方号；可以同时成立）
  捐款人           捐款后 300 拍内阵亡
  对倒             A→B 之后 150 拍内 B→A（两笔都执行）
  代码分支         由 pct 反推 tryDonateToTeammate 走的是哪一支（L4369-4499）：153 = 盈余捐款、不被围（L4489）；185 / 280 = 盈余捐款、被围（boxedIn，L4489）；
                   155 = 救援（L4437）；240 = 救援、纯内陆（isPureInlandSafe，L4437）；<155 的其他值 = 救援被 maxSafePct 钳小（L4388、L4437）；
                   156~239 的其他值 = 纯内陆救援被钳。「后排」= 被围或纯内陆的捐款人（185 / 280 / 240 / 156~239）。153 也可能是钳出来的，分不开，算盈余。
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
from r06lib import OUT  # noqa: E402

PCT_BANDS = [('<64', 0, 64), ('64~149', 64, 150), ('150~199', 150, 200), ('200~299', 200, 300), ('>=300', 300, 10 ** 9)]
DENS_BANDS = [('<50', 0, 50), ('50~100', 50, 100), ('100~125', 100, 125), ('>=125', 125, 10 ** 9)]
T_BANDS = [('<2142', 0, 2142), ('2142~3213', 2142, 3213), ('3213~4284', 3213, 4284), ('>=4284', 4284, 10 ** 9)]


def band(v, bands):
    for name, lo, hi in bands:
        if lo <= v < hi:
            return name
    return bands[-1][0]


def acc():
    return dict(n=0, delivered=0, fee=0)


BRANCHES = ['盈余·不被围（153）', '盈余·被围（185 / 280）', '救援（155）', '救援·纯内陆（240）', '救援·被钳小（<155）', '救援·纯内陆被钳（156~239）', '其他']
REAR = ('盈余·被围（185 / 280）', '救援·纯内陆（240）', '救援·纯内陆被钳（156~239）')


def branch(pct):
    if pct == 153:
        return BRANCHES[0]
    if pct in (185, 280):
        return BRANCHES[1]
    if pct == 155:
        return BRANCHES[2]
    if pct == 240:
        return BRANCHES[3]
    if pct < 155:
        return BRANCHES[4]
    if 156 <= pct < 240:
        return BRANCHES[5]
    return BRANCHES[6]


def bacc():
    return dict(n=0, delivered=0, fee=0, truncN=0, short=0, husk=0, huskFee=0, fAll=0, fSpent=0, fDonOut=0, fNoCmd=0, fDead=0, donorDens=[], recvDens=[], fire=0, live=0, up=0, upDelivered=0, upFee=0, recv100=0, recv100Fee=0)


def put(d, key, r):
    a = d.setdefault(key, acc())
    a['n'] += 1
    a['delivered'] += r['delivered']
    a['fee'] += r['fee']


def build(mid):
    X = SD.Sim(mid)
    rows = SD.don_rows(X)
    ok = [r for r in rows if r['ok']]
    out = [r for r in ok if r['from'] in X.squad]
    doc = dict(matchId=mid, endT=X.endT, n=len(out), delivered=sum(r['delivered'] for r in out), fee=sum(r['fee'] for r in out),
               pct={}, to={}, dens={}, trunc=acc(), zero=acc(), underFire=acc(), tband={}, follow={}, donorDead=acc(), pingpong=dict(pairs=0, fee=0, back=0), pctTop=[])
    doc['trunc']['short'] = 0
    bp = defaultdict(int)
    live = []
    BR = doc['branch'] = {}
    for r in out:
        q, t = r['to'], r['t']
        b = BR.setdefault(branch(r['pct']), bacc())
        b['n'] += 1
        b['delivered'] += r['delivered']
        b['fee'] += r['fee']
        b['donorDens'].append(round(r['B0'] / max(1, r.get('fromTerr') or 1), 1))
        if r.get('onRecv'):
            b['fire'] += 1
        nom = r['B0'] * (r['pct'] + 1) // 1024
        if r['delivered'] < 0.9 * nom:
            b['truncN'] += 1
            b['short'] += nom - r['delivered']
        if r['toLeft']:
            b['husk'] += 1
            b['huskFee'] += r['fee']
        elif q in X.squad:
            b['recvDens'].append(round(r['toDens'], 1))
            b['live'] += 1
            if r['toDens'] > r['B0'] / max(1, r.get('fromTerr') or 1):
                b['up'] += 1
                b['upDelivered'] += r['delivered']
                b['upFee'] += r['fee']
            if r['toDens'] >= 100:
                b['recv100'] += 1
                b['recv100Fee'] += r['fee']
            if t + 300 <= X.endT:
                b['fAll'] += 1
                if r['toAlive300'] is False:
                    b['fDead'] += 1
                if r['toCmds300'] == 0:
                    b['fNoCmd'] += 1
                if r['delivered'] > 0 and r.get('toDonOut300', 0) >= 0.5 * r['delivered']:
                    b['fDonOut'] += 1
                if r['delivered'] > 0 and r.get('toSpent300', 0) >= 0.5 * r['delivered']:
                    b['fSpent'] += 1
        put(doc['pct'], band(r['pct'], PCT_BANDS), r)
        put(doc['tband'], band(t, T_BANDS), r)
        bp[r['pct']] += 1
        kind = '我方空壳' if (q in X.squad and r['toLeft']) else '我方在场号' if q in X.squad else ('外人空壳' if r['toLeft'] else '外人')
        put(doc['to'], kind, r)
        nominal = r['B0'] * (r['pct'] + 1) // 1024
        if r['delivered'] == 0:
            doc['zero']['n'] += 1
            doc['zero']['fee'] += r['fee']
        elif r['delivered'] < 0.9 * nominal:
            doc['trunc']['n'] += 1
            doc['trunc']['delivered'] += r['delivered']
            doc['trunc']['fee'] += r['fee']
            doc['trunc']['short'] += nominal - r['delivered']
        if r.get('onRecv'):
            doc['underFire']['n'] += 1
            doc['underFire']['delivered'] += r['delivered']
            doc['underFire']['fee'] += r['fee']
        fd = X.deathT[r['from']]
        if fd >= 0 and fd <= t + 300:
            doc['donorDead']['n'] += 1
            doc['donorDead']['delivered'] += r['delivered']
            doc['donorDead']['fee'] += r['fee']
        if kind == '我方在场号':
            live.append(r)
            put(doc['dens'], band(r['toDens'], DENS_BANDS), r)
    # 收款后 300 拍，逐笔打标（在场的我方号；录像末拍之前不足 300 拍的不计）。一笔可以同时挂几个标；金额列只是「挂这个标的那些笔的到账合计」。
    F = doc['follow']
    for k in ('all', 'dead', 'noCmd', 'donOut', 'spent', 'none'):
        F[k] = acc()
    for r in live:
        if r['t'] + 300 > X.endT:
            continue
        put(F, 'all', r)
        hit = False
        if r['toAlive300'] is False:
            put(F, 'dead', r)
            hit = True
        if r['toCmds300'] == 0:
            put(F, 'noCmd', r)
        if r.get('toDonOut300', 0) >= 0.5 * r['delivered'] and r['delivered'] > 0:
            put(F, 'donOut', r)
            hit = True
        if r.get('toSpent300', 0) >= 0.5 * r['delivered'] and r['delivered'] > 0:
            put(F, 'spent', r)
            hit = True
        if not hit:
            put(F, 'none', r)
    # 收款窗口（不重复计数）：同一个收款人相隔 <=300 拍的几笔并成一个窗口 [第一笔, 最后一笔+300]；
    # 窗口内收到 R、战斗耗兵 S（账本按 100 拍一格，边上的格整格算进来，所以是上限）、又捐出 O（到账）及其手续费、得地 G。
    W = doc['windows'] = dict(n=0, recv=0, spentCap=0, donOutCap=0, donOutFee=0, gain=0, noCmd=dict(n=0, recv=0), dead=dict(n=0, recv=0), spentLtTenth=dict(n=0, recv=0))
    by_q = defaultdict(list)
    for r in live:
        by_q[r['to']].append(r)
    for q, rs in by_q.items():
        rs.sort(key=lambda r: r['t'])
        wins = []
        for r in rs:
            if wins and r['t'] <= wins[-1][1]:
                wins[-1][1] = r['t'] + 300
                wins[-1][2] += r['delivered']
            else:
                wins.append([r['t'], r['t'] + 300, r['delivered']])
        for w0, w1, recv in wins:
            if w1 > X.endT:
                continue
            S = max(0, X.led_sum(q, 'spent', w0, w1))
            outs = [y for y in X.S['donations'] if y['from'] == q and y['ok'] and w0 < y['t'] <= w1]
            O = sum(y['delivered'] for y in outs)
            cm = sum(1 for c in X.M.cmds if c['player'] == q and w0 < c['t'] <= w1 and c['id'] in (1, 3))
            dead = X.deathT[q] >= 0 and X.deathT[q] <= w1
            W['n'] += 1
            W['recv'] += recv
            W['spentCap'] += min(recv, S)
            W['donOutCap'] += min(recv, O)
            W['donOutFee'] += sum(y['fee'] for y in outs)
            W['gain'] += max(0, X.led_sum(q, 'gain', w0, w1))
            if cm == 0:
                W['noCmd']['n'] += 1
                W['noCmd']['recv'] += recv
            if dead:
                W['dead']['n'] += 1
                W['dead']['recv'] += recv
            if S < 0.1 * recv:
                W['spentLtTenth']['n'] += 1
                W['spentLtTenth']['recv'] += recv
    # 对倒
    for i, a in enumerate(ok):
        for b in ok[i + 1:]:
            if b['t'] - a['t'] > 150:
                break
            if b['from'] == a['to'] and b['to'] == a['from']:
                doc['pingpong']['pairs'] += 1
                doc['pingpong']['fee'] += a['fee'] + b['fee']
                doc['pingpong']['back'] += b['delivered']
                break
    doc['pctTop'] = sorted(bp.items(), key=lambda kv: -kv[1])[:8]
    return doc


def pc(a, b):
    return f'{100 * a / b:.1f}%' if b else '—'


def wan(x):
    x = int(round(x))
    if abs(x) < 10000:
        return f'{x:,}'
    if abs(x) < 100000000:
        return f'{x / 1e4:,.1f} 万'
    return f'{x / 1e8:.2f} 亿'


def line(name, a):
    return f"{name} {a['n']} 笔 / 到账 {wan(a['delivered'])} / 手续费 {wan(a['fee'])}（损耗率 {pc(a['fee'], a['fee'] + a['delivered'])}）"


def show(d):
    print(f"{d['matchId']}：我方号捐出、已执行 {d['n']} 笔，到账 {wan(d['delivered'])}，手续费 {wan(d['fee'])}（损耗率 {pc(d['fee'], d['fee'] + d['delivered'])}）。录像只记已执行的指令，被拒的捐款见 simdigest.py probe。")
    if not d['n']:
        return
    print('  按 pct 档：' + '；'.join(line(k, d['pct'][k]) for k, _, _ in PCT_BANDS if k in d['pct']))
    print('  最常见的 pct：' + '、'.join(f"{k}‰×{v}" for k, v in d['pctTop']))
    print('  按拍：' + '；'.join(line(k, d['tband'][k]) for k, _, _ in T_BANDS if k in d['tband']))
    print('  按收款人：' + '；'.join(line(k, v) for k, v in sorted(d['to'].items(), key=lambda kv: -kv[1]['n'])))
    print('  收款时密度（在场的我方号）：' + '；'.join(line(k, d['dens'][k]) for k, _, _ in DENS_BANDS if k in d['dens']))
    print(f"  被截断（到账 < 名义值的 90%）：{line('', d['trunc'])}，少到账 {wan(d['trunc']['short'])}；到账 = 0 的 {d['zero']['n']} 笔、手续费 {wan(d['zero']['fee'])}")
    print(f"  收款时正被人打：{line('', d['underFire'])}")
    print(f"  捐款人 300 拍内阵亡：{line('', d['donorDead'])}")
    F = d['follow']
    if F['all']['n']:
        print(f"  收款后 300 拍，逐笔打标（在场的我方号，{F['all']['n']} 笔；一笔可挂几个标）：收款人阵亡 {F['dead']['n']} 笔；没有任何陆攻 / 发船指令进录像 {F['noCmd']['n']} 笔（{pc(F['noCmd']['n'], F['all']['n'])}）；"
              f"又捐出 >= 到账的一半 {F['donOut']['n']} 笔（{pc(F['donOut']['n'], F['all']['n'])}）；战斗耗兵 >= 到账的一半 {F['spent']['n']} 笔（{pc(F['spent']['n'], F['all']['n'])}）；阵亡 / 又捐出 / 耗兵都不沾 {F['none']['n']} 笔")
    W = d.get('windows')
    if W and W['n']:
        print(f"  收款窗口（同一收款人相隔 <=300 拍的并成一个，不重复计数）：{W['n']} 个窗口共收到 {wan(W['recv'])}；窗口内战斗耗兵至多抵掉 {wan(W['spentCap'])}（{pc(W['spentCap'], W['recv'])}），"
              f"又捐出去至多 {wan(W['donOutCap'])}（{pc(W['donOutCap'], W['recv'])}，这些再捐又付手续费 {wan(W['donOutFee'])}）；窗口内得地 {W['gain']:,} 格")
        print(f"      窗口内没有任何陆攻 / 发船指令的 {W['noCmd']['n']} 个（收到 {wan(W['noCmd']['recv'])}，{pc(W['noCmd']['recv'], W['recv'])}）；战斗耗兵不到收到的一成的 {W['spentLtTenth']['n']} 个（收到 {wan(W['spentLtTenth']['recv'])}，{pc(W['spentLtTenth']['recv'], W['recv'])}）；"
              f"收款人在窗口内阵亡的 {W['dead']['n']} 个（收到 {wan(W['dead']['recv'])}）")
    if d.get('branch'):
        print('  按代码分支（由 pct 反推）：')
        for k in BRANCHES:
            b = d['branch'].get(k)
            if not b:
                continue
            md = lambda v: (sorted(v)[len(v) // 2] if v else 0)
            print(f"      {k}：{b['n']} 笔 / 到账 {wan(b['delivered'])} / 手续费 {wan(b['fee'])}（损耗率 {pc(b['fee'], b['fee'] + b['delivered'])}）；被截断 {b['truncN']} 笔、少到账 {wan(b['short'])}；给空壳 {b['husk']} 笔；"
                  f"捐款人密度中位 {md(b['donorDens'])}、收款人密度中位 {md(b['recvDens'])}；收款人比捐款人还密 {b['up']}/{b['live']} 笔（到账 {wan(b['upDelivered'])}、费 {wan(b['upFee'])}）；收款人密度 >=100 {b['recv100']} 笔；收款时正被打 {b['fire']} 笔；"
                  f"之后 300 拍（{b['fAll']} 笔有读数）：耗兵 >= 一半 {b['fSpent']}、又捐出 >= 一半 {b['fDonOut']}、零指令 {b['fNoCmd']}、阵亡 {b['fDead']}")
    p = d['pingpong']
    print(f"  对倒（150 拍内原路捐回）：{p['pairs']} 组，两头手续费 {wan(p['fee'])}，回流 {wan(p['back'])}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    mid = sys.argv[1]
    doc = build(mid)
    show(doc)
    if len(sys.argv) > 2 and sys.argv[2] == 'json':
        p = os.path.join(OUT, mid, 'donflow.json')
        json.dump(doc, open(p, 'w'), ensure_ascii=False)
        print('写入', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
