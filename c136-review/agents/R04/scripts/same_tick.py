#!/usr/bin/env python3
# same_tick.py — 核对「同一个决策拍里出两条指令，后一条会不会被挤掉」（总部广播 0004 的第 2 条）。
#
# 用法：python3 scripts/same_tick.py <局号> [--list]
#   先要有 tmp/truth/<局号>/cmd.tsv（engine_truth.cjs）和 tmp/shadow/<局号>/intents.tsv（shadow.mjs）。
# 做法：
#   1) 影子策略的意图按（号, 决策拍）分组，挑出同一拍 ≥2 条的组（陆攻 / 捐款 / 发船 都算）；
#   2) 组里每条意图看它「分不分得清」：同一个号在前后 150 拍内没有别的意图和它 同类 + 同比例 + 同目标，才算分得清
#      （落地的指令只带 类别、比例、目标，同参数的意图连着发时，分不出落地的是哪一条；
#        分不清的另外给出「前后 150 拍同参数的意图几条、落地几条」，落地的比意图少就说明其中有被丢掉的）；
#   3) 分得清的意图：录像里这个号在 [决策拍, 决策拍+600] 内有没有 同类 + 同比例 的落地指令
#      （目标也要相同；目标已出局时录像记成无主地 512，也算）。有就是落地，没有就是没落地；
#   4) 统计：组内第 1 条 / 第 2 条 各自 落地、没落地、分不清 的次数，分时段；没落地的第 2 条想出的兵合计。
# 读法：如果线上一拍只能发一条指令，那么分得清的第 2 条应当全部没落地，第 1 条基本都落地。
import sys, os, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exec_gap import load, NAME

KIND_ID = {'attack': 1, 'donate': 2, 'boat': 3}


def band(t):
    return '<630' if t < 630 else '630~1499' if t < 1500 else '1500~2999' if t < 3000 else '3000~4283' if t < 4284 else '≥4284'


def desc(x):
    if x['kind'] == 'attack':
        return '陆攻 %s 比例 %d 兵 %d' % ('无主地' if x['target'] == 512 else '#%d' % x['target'], x['pct'], x['troops'])
    return '%s →#%d 比例 %d 兵 %d' % (NAME.get(x['kind'], x['kind']), x['target'], x['pct'], x['troops'])


def main():
    a = sys.argv[1:]
    mid = a[0]
    intents, cmds, check = load(mid)
    by_bot = collections.defaultdict(list)
    for x in intents:
        by_bot[x['p']].append(x)
    cmd_by = collections.defaultdict(list)
    for c in cmds:
        cmd_by[(c['p'], c['id'])].append(c)
    groups = collections.defaultdict(list)
    for x in intents:
        groups[(x['bot'], x['t'])].append(x)
    multi = {k: v for k, v in groups.items() if len(v) >= 2}

    def same_sig(x, y):
        # 落地指令只带 类别、比例、目标；目标已出局时录像里记成无主地 512，所以「一方是无主地」也算可能混淆
        if y['kind'] != x['kind'] or y['pct'] != x['pct']:
            return False
        return x['kind'] != 'attack' or y['target'] == x['target'] or y['target'] == 512 or x['target'] == 512

    def cmd_hit(x, c):
        return c['a'] == x['pct'] and (c['b'] == x['target'] or (x['kind'] == 'attack' and c['b'] == 512) or x['kind'] == 'boat')

    def status(x):
        if x['kind'] not in KIND_ID:
            return '分不清', None
        twins = [y for y in by_bot[x['p']] if y is not x and same_sig(x, y) and abs(y['t'] - x['t']) <= 150]
        cc = cmd_by.get((x['p'], KIND_ID[x['kind']]), [])
        if twins:
            ts = [y['t'] for y in twins] + [x['t']]
            n_cmd = sum(1 for c in cc if min(ts) <= c['t'] <= max(ts) + 150 and cmd_hit(x, c))
            return '分不清（前后 150 拍同参数的意图 %d 条，落地 %d 条）' % (len(ts), n_cmd), None
        for c in cc:
            if x['t'] <= c['t'] <= x['t'] + 600 and cmd_hit(x, c):
                return '落地', c['t']
        return '没落地', None

    print('%s：影子策略的意图 %d 条，分在 %d 个号·拍里；同一个决策拍出 ≥2 条的有 %d 个号·拍（%d 条意图），按时段 %s' % (
        mid, len(intents), len(groups), len(multi), sum(len(v) for v in multi.values()),
        dict(sorted(collections.Counter(band(k[1]) for k in multi).items()))))
    kinds = collections.Counter()
    for k, v in multi.items():
        kinds['；'.join(('无主地' if (x['kind'] == 'attack' and x['target'] == 512) else '内置AI' if (x['kind'] == 'attack' and x['target'] >= len(by_bot) and x['target'] > 60) else NAME.get(x['kind'], x['kind'])) for x in v)] += 1
    print('  组内的指令（按发出顺序；陆攻的目标只分 无主地 / 内置AI / 其他）：%s' % dict(kinds.most_common()))
    res = {}
    for pos in (0, 1):
        cnt = collections.Counter()
        lost = collections.defaultdict(int)
        lostn = collections.Counter()
        for k, v in multi.items():
            if pos >= len(v):
                continue
            st, tc = status(v[pos])
            res[(k, pos)] = (st, tc)
            cnt[st[:3]] += 1
            if st == '没落地':
                lost[band(k[1])] += v[pos]['troops']
                lostn[band(k[1])] += 1
        print('  组内第 %d 条：落地 %d，没落地 %d，分不清 %d' % (pos + 1, cnt['落地'], cnt['没落地'], cnt['分不清'])
              + ('；没落地的按时段（次数 / 想出的兵）：%s' % '，'.join('%s %d 次 %d 兵' % (b, lostn[b], lost[b]) for b in sorted(lostn)) if lostn else ''))
    if '--list' in a:
        for k in sorted(multi, key=lambda k: (k[1], k[0])):
            print('    拍 %5d %-7s ' % (k[1], k[0]) + '；'.join(
                '%s → %s%s' % (desc(x), res.get((k, i), status(x))[0], (' 拍 %d' % res[(k, i)][1]) if res.get((k, i), (None, None))[1] else '') for i, x in enumerate(multi[k])))


if __name__ == '__main__':
    main()
