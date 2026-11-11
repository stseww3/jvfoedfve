#!/usr/bin/env python3
# window_tally.py — 某个拍段里，我方每个号的「决策拍」按处境分类计数（来自影子策略的逐拍记录 rows.tsv），
# 另给出我方号合计领土/余额、各队占比在窗口两端的值。用来给转折窗口配机械口径的数字。
# 用法：python3 scripts/window_tally.py <局号> <t0> <t1>
#   先要有 tmp/shadow/<局号>/rows.tsv（bash scripts/shadow_all.sh <局号>）和 tmp/truth/<局号>/（engine_truth_all.sh）。
# 分类（每个决策拍只进一类，按下面的先后）：
#   出手          这一拍影子策略给出了至少一条指令
#   封死          没有非队友陆上邻居、也没有无主地
#   只贴真人       有非队友邻居但全是真人（没有内置 AI、没有无主地），这一拍没出手
#   贴弱AI被底线卡住  贴着「兵比地少」的内置 AI，没出手，且打 AI 要守的底线 > 自己的余额
#   贴AI没出手     还贴着内置 AI，没出手（底线没超过余额，或贴的 AI 不弱）
#   其他没出手     只剩无主地可占等
import sys, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        raise SystemExit('用法：python3 scripts/window_tally.py <局号> <t0> <t1>')
    mid, t0, t1 = a[0], int(a[1]), int(a[2])
    cats = ['出手', '封死', '只贴真人', '贴弱AI被底线卡住', '贴AI没出手', '其他没出手']
    st = collections.defaultdict(collections.Counter)
    weak = collections.Counter()
    order = []
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv'), encoding='utf8') as f:
        for l in f:
            x = l.rstrip('\n').split('\t')
            if x[0] == 't':
                continue
            t, b = int(x[0]), x[1]
            if not (t0 <= t < t1):
                continue
            terr, bal, nb, nAI, nAIw, wl, nHum, neut, coast, ints, floor, nfs, atk = [float(v) for v in x[2:15]]
            if b not in st:
                order.append(b)
            c = st[b]
            c['n'] += 1
            if ints > 0:
                k = '出手'
            elif nb == 0 and neut == 0:
                k = '封死'
            elif nAI == 0 and neut == 0 and nHum > 0:
                k = '只贴真人'
            elif nAIw > 0 and floor > bal:
                k = '贴弱AI被底线卡住'
                weak[b] += wl
            elif nAI > 0:
                k = '贴AI没出手'
            else:
                k = '其他没出手'
            c[k] += 1
    print(f'# {mid} 拍段 [{t0},{t1}) 我方各号的决策拍分类（每 5 拍一个决策拍）')
    print('号       决策拍 | ' + ' | '.join(cats) + ' | 被卡住时贴着的弱AI地（平均）')
    tot = collections.Counter()
    for b in order:
        c = st[b]
        for k, v in c.items():
            tot[k] += v
        avg = weak[b] / c['贴弱AI被底线卡住'] if c['贴弱AI被底线卡住'] else 0
        print(f'{b:8s} {c["n"]:5d} | ' + ' | '.join(f'{c[k]:4d}' for k in cats) + f' | {avg:7.0f}')
    n = max(1, tot['n'])
    print(f'合计     {tot["n"]:5d} | ' + ' | '.join(f'{tot[k]:4d}（{100 * tot[k] / n:.0f}%）' for k in cats))

    # 窗口两端：我方号合计、各队占比
    sys.path.insert(0, HERE)
    sys.dont_write_bytecode = True
    from match_digest import Match, fmt
    M = Match(mid)
    land = M.ke

    def near(t):
        return min(M.samples, key=lambda s: abs(s - t))

    for t in (t0, t1):
        s = near(t)
        terr = sum(M.state[s][p][0] for p in M.our_ids if p in M.state[s])
        bal = sum(M.state[s][p][1] for p in M.our_ids if p in M.state[s])
        alive = sum(1 for p in M.our_ids if p in M.state[s] and M.state[s][p][0] > 0)
        ts = '；'.join(f'{"内置AI" if k >= 100 else "队" + str(k)} {100 * v[0] / land:.1f}% {fmt(v[1])}' for k, v in sorted(M.teamts[s].items()) if k > 0)
        print(f'拍 {s}：我方号 {terr} 格（{100 * terr / land:.1f}%）{fmt(bal)} 兵，有地的号 {alive} 个；{ts}')


if __name__ == '__main__':
    main()
