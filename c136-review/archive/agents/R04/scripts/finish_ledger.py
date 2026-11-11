#!/usr/bin/env python3
# finish_ledger.py — 「领先之后收口」账：某个我方号（组队局按本队）占全图陆地 ≥ S% 且自己的余额 ≥ R × 场上最大的
# 敌方真人余额之后，到对局结束（或敌方真人全部出局）为止，它出的兵去了哪里。
#
# 用法：python3 scripts/finish_ledger.py <局号> [--share 75] [--ratio 3] [--until 拍] [--ours id,id,…]
#   --until 拍：窗口只算到这一拍为止（默认到对局结束或敌方真人全部出局）
# 口径（都来自真引擎重放 tmp/truth/<局号>/）：
#   过线拍 t* = state.tsv 里第一行同时满足「份额 ≥ S%」「余额 ≥ R×敌方真人里最大的余额」的快照拍（步长 10）；
#   份额：不分队的模式用这个号自己的领土 ÷ 陆地总格数，组队模式用本队全部真人的领土之和；
#   陆攻 = cmd.tsv id=1 且产生了进攻的指令（sub 里 atk:<目标>:<兵>），按目标分 敌方真人 / 内置 AI / 无主地；
#   船   = cmd.tsv id=3（sub 里 boat:<船号>:<载兵>:<终点>），结果取 ev.tsv 同船号的 land 事件：
#          登陆敌方真人 / 登陆内置 AI / 登陆无主地 / 回到自己地上（或移交队友）/ 没有结果；
#   手续费 = 指令前后余额差 − 出兵（陆攻按余额 12/1024、发船按 32/1024 收）；
#   得地 = flow.tsv 窗口内这个号从各类对象净流入的像素。
import sys, os, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    S = float(a[a.index('--share') + 1]) if '--share' in a else 75.0
    R = float(a[a.index('--ratio') + 1]) if '--ratio' in a else 3.0
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    until = int(a[a.index('--until') + 1]) if '--until' in a else None
    M = Match(mid, ours)
    land = M.meta['info']['ke']
    ku = M.ku
    print('# %s 领先之后的出兵去向（过线 = 份额 ≥ %g%% 且余额 ≥ %g×敌方真人里最大的余额；陆地 %d 格，录像到第 %d 拍）' % (mid, S, R, land, M.last))

    def mates(p):
        tm = M.team.get(p, 0)
        return [q for q in range(ku) if tm > 0 and M.team.get(q, 0) == tm] or [p]

    def klass(p, o):
        if o >= 512 or o < 0:
            return '无主地'
        if o >= ku:
            return '内置AI'
        return '队友' if (o in mates(p) and o != p) else ('自己' if o == p else '敌方真人')

    ends = {}
    for (t, kind, pl, x, y, det) in M.ev:
        if kind in ('land', 'sunk', 'boatend'):
            ends.setdefault((pl, int(x)), (t, kind, det))
    found = False
    for p in M.our_ids:
        tstar = None
        for t in M.samples:
            st = M.state[t]
            if p not in st or st[p][0] <= 0:
                continue
            share = 100.0 * sum(st[q][0] for q in mates(p) if q in st) / land
            foes = [q for q in range(ku) if q not in mates(p) and q in st and st[q][0] > 0]
            if not foes:
                continue
            if share >= S and st[p][1] >= R * max(st[q][1] for q in foes):
                tstar = t
                break
        if tstar is None:
            print('  %-8s 没有过线' % M.nm(p))
            continue
        found = True
        st0 = M.state[tstar]
        foes = [q for q in range(ku) if q not in mates(p) and q in st0 and st0[q][0] > 0]
        tend = M.last
        dead_at = {}
        for q in foes:
            for t in M.samples:
                if t > tstar and (q not in M.state[t] or M.state[t][q][0] <= 0):
                    dead_at[q] = t
                    break
        if foes and all(q in dead_at for q in foes):
            tend = max(dead_at.values())
        if until is not None:
            tend = min(tend, until)
        last_s = max(t for t in M.samples if t <= tend)
        stE = M.state[last_s]
        share0 = 100.0 * sum(st0[q][0] for q in mates(p) if q in st0) / land
        print('  %-8s 过线拍 %d：份额 %.1f%%，领土 %d，余额 %s；敌方真人 %s' % (
            M.nm(p), tstar, share0, st0[p][0], fmt(st0[p][1]),
            '，'.join('%s %d 格 / %s 兵' % (M.nm(q), st0[q][0], fmt(st0[q][1])) for q in foes)))
        print('           到第 %d 拍（%d 拍后）：%s；自己 %d 格 / %s 兵' % (
            last_s, last_s - tstar,
            '，'.join(('%s 在第 %d 拍出局' % (M.nm(q), dead_at[q])) if q in dead_at and dead_at[q] <= tend
                      else ('%s 还在场 %d 格 / %s 兵' % (M.nm(q), stE[q][0] if q in stE else 0, fmt(stE[q][1] if q in stE else 0))) for q in foes),
            stE[p][0] if p in stE else 0, fmt(stE[p][1] if p in stE else 0)))
        atk = collections.Counter(); atk_n = collections.Counter(); fee_l = 0; noatk = 0
        boat = collections.Counter(); boat_n = collections.Counter(); fee_b = 0
        for c in M.cmd:
            if c['p'] != p or not (tstar <= c['t'] <= tend):
                continue
            if c['id'] == 1:
                subs = [s for s in c['sub'] if s and s[0] == 'atk']
                if not subs:
                    noatk += 1
                    continue
                tr = sum(int(s[2]) for s in subs)
                k = klass(p, int(subs[0][1]))
                atk[k] += tr; atk_n[k] += 1
                fee_l += max(0, c['bal0'] - c['bal1'] - tr)
            elif c['id'] == 3:
                for s in c['sub']:
                    if not s or s[0] != 'boat':
                        continue
                    bid, tr = int(s[1]), int(s[2])
                    fee_b += max(0, c['bal0'] - c['bal1'] - tr)
                    e = ends.get((p, bid))
                    k = '没有结果'
                    if e:
                        te, kind, det = e
                        tail = det.split('|', 1)[1] if '|' in det else ''
                        if kind == 'land' and tail.startswith('atk:'):
                            k = '登陆' + klass(p, int(tail.split(':')[1]))
                        elif kind == 'land' and tail.startswith('give:'):
                            k = '移交队友'
                        elif kind == 'land':
                            k = '回到自己地上'
                        else:
                            k = '沉没/消失'
                    boat[k] += tr; boat_n[k] += 1
        gain = collections.Counter()
        for (t, frm, to, px) in M.flow:
            if tstar <= t <= tend:
                if to == p and frm != p:
                    gain[klass(p, frm)] += px
                if frm == p and to != p:
                    gain[klass(p, to)] -= px
        tot = sum(atk.values()) + sum(boat.values())
        foe_tr = atk['敌方真人'] + boat['登陆敌方真人']
        print('           陆攻 %d 条 %s 兵（另有 %d 条没产生进攻）：%s；陆攻手续费 %s' % (
            sum(atk_n.values()), fmt(sum(atk.values())), noatk,
            '，'.join('%s %d 条 %s' % (k, atk_n[k], fmt(v)) for k, v in atk.most_common()) or '无', fmt(fee_l)))
        print('           船 %d 条 %s 兵：%s；船手续费 %s' % (
            sum(boat_n.values()), fmt(sum(boat.values())),
            '，'.join('%s %d 条 %s' % (k, boat_n[k], fmt(v)) for k, v in boat.most_common()) or '无', fmt(fee_b)))
        print('           出兵合计 %s，其中落在敌方真人身上（陆攻 + 登陆）%s = %.0f%%；手续费合计 %s' % (
            fmt(tot), fmt(foe_tr), 100.0 * foe_tr / tot if tot else 0, fmt(fee_l + fee_b)))
        print('           窗口内净得地：%s' % ('，'.join('%s %+d' % (k, v) for k, v in gain.most_common()) or '无'))
    if not found:
        print('  没有号过线')


if __name__ == '__main__':
    main()
