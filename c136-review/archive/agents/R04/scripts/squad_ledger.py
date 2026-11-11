#!/usr/bin/env python3
# 我方编队的兵力流水：每个时段的兵从哪来、花到哪去。
# 用法：python3 scripts/squad_ledger.py <局号> [--win t0,t1,…] [--bot 名字] [--ours id,id,…]
#   默认窗口：0,630,1500,3000,4284,终局。--bot 只看一个号。
# 口径（全部来自真引擎重放的 cmd.tsv / state.tsv）：
#   出征兵   = 陆攻指令进攻槽里登记的兵，按目标分 无主地 / 内置AI / 敌方真人；
#   陆攻手续费 = 每条陆攻另扣的 余额×12/1024；
#   装船兵 / 船手续费 = 发船指令装上船的兵 / 另扣的 余额×32/1024；
#   捐款：到账（给编队内 / 给编队外的队友）、税（捐款人余额的 6.25%）、收到（来自编队外）；
#   残差 = 期末余额 − 期初余额 + 全部支出 − 全部收入 ≈ 利息 + 船兵回岸 + 吃地缴获 − 挨打损失（这几项录像里分不开）。
import sys, collections
sys.dont_write_bytecode = True
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from match_digest import Match, fmt


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    last = M.samples[-1]
    edges = [int(x) for x in a[a.index('--win') + 1].split(',')] if '--win' in a else [0, 630, 1500, 3000, 4284, last]
    edges = [min(e, last) for e in edges]
    only = None
    if '--bot' in a:
        nmw = a[a.index('--bot') + 1]
        only = [p for p in M.our_ids if M.nm(p) == nmw]
    ids = only if only else M.our_ids
    idset = set(ids)
    print('# %s 兵力流水（%s）；单位 兵' % (mid, '只看 ' + M.nm(ids[0]) if only else '我方 %d 个号合计' % len(ids)))
    hdr = '时段 | 期初余额→期末余额 | 出征：无主地 / 内置AI / 敌方真人 | 陆攻手续费 | 装船兵 / 船手续费 | 捐款：给编队内到账 / 给编队外到账 / 税 | 收到编队外 | 残差(≈利息−挨打损失) | 期末领土'
    print(hdr)
    tot = collections.Counter()
    for i in range(len(edges) - 1):
        t0, t1 = edges[i], edges[i + 1]
        S0 = M.state[M.at(t0)]; S1 = M.state[M.at(t1)]
        b0 = sum(S0[p][1] for p in ids if p in S0); b1 = sum(S1[p][1] for p in ids if p in S1)
        l1 = sum(S1[p][0] for p in ids if p in S1)
        c = collections.Counter()
        for x in M.cmd:
            if not (t0 < x['t'] <= t1):
                continue
            if x['id'] == 1 and x['p'] in idset:
                tr = sum(int(s[2]) for s in x['sub'] if s and s[0] == 'atk')
                if tr <= 0:
                    continue
                q = x['b']
                cls = 'neu' if q >= 512 or q < 0 else ('ai' if q >= M.ku else 'hum')
                c['atk_' + cls] += tr
                c['fee'] += x['bal0'] - x['bal1'] - tr
            elif x['id'] == 3 and x['p'] in idset:
                tr = sum(int(s[2]) for s in x['sub'] if s and s[0] == 'boat')
                if tr <= 0:
                    continue
                c['boat'] += tr
                c['boatfee'] += x['bal0'] - x['bal1'] - tr
                c['boatn'] += 1
            elif x['id'] == 2 and 'q' in x:
                cred = x['balQ1'] - x['balQ0']
                if cred <= 0:
                    continue
                if x['p'] in idset:
                    tax = x['bal0'] - x['bal1'] - cred
                    c['tax'] += tax
                    if x['q'] in idset:
                        c['don_in_squad'] += cred
                    else:
                        c['don_out'] += cred
                    c['donn'] += 1
                elif x['q'] in idset:
                    c['recv'] += cred
        spend = c['atk_neu'] + c['atk_ai'] + c['atk_hum'] + c['fee'] + c['boat'] + c['boatfee'] + c['tax'] + c['don_out']
        if only:
            spend += c['don_in_squad']
        income = c['recv']
        resid = b1 - b0 + spend - income
        c['resid'] = resid
        for k, v in c.items():
            tot[k] += v
        print('(%d,%d] | %s→%s | %s / %s / %s | %s | %s（%d 条）/ %s | %s / %s / %s（%d 笔） | %s | %s | %d' % (
            t0, t1, fmt(b0), fmt(b1), fmt(c['atk_neu']), fmt(c['atk_ai']), fmt(c['atk_hum']), fmt(c['fee']),
            fmt(c['boat']), c['boatn'], fmt(c['boatfee']), fmt(c['don_in_squad']), fmt(c['don_out']), fmt(c['tax']), c['donn'],
            fmt(c['recv']), fmt(resid), l1))
    print('合计 | 出征 %s / %s / %s | 陆攻手续费 %s | 装船 %s（%d 条）/ 船手续费 %s | 捐款 给编队内 %s / 给编队外 %s / 税 %s（%d 笔） | 收到编队外 %s | 残差 %s' % (
        fmt(tot['atk_neu']), fmt(tot['atk_ai']), fmt(tot['atk_hum']), fmt(tot['fee']), fmt(tot['boat']), tot['boatn'], fmt(tot['boatfee']),
        fmt(tot['don_in_squad']), fmt(tot['don_out']), fmt(tot['tax']), tot['donn'], fmt(tot['recv']), fmt(tot['resid'])))
    burn = tot['fee'] + tot['boatfee'] + tot['tax']
    used = tot['atk_neu'] + tot['atk_ai'] + tot['atk_hum'] + tot['boat']
    print('白交的（陆攻手续费 + 船手续费 + 捐款税）合计 %s，相当于全部出征兵与装船兵 %s 的 %.0f%%' % (fmt(burn), fmt(used), 100.0 * burn / max(1, used)))


if __name__ == '__main__':
    main()
