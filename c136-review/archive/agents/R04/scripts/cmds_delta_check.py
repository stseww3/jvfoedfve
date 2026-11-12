#!/usr/bin/env python3
# cmds_delta_check.py — 影子策略和真实日志的「发令数」差在哪些时段，是不是正好落在「同一个决策拍出两条指令」的地方。
#
# 用法：python3 scripts/cmds_delta_check.py <局号>
#   先要有 tmp/shadow/<局号>/logs.txt、intents.tsv（shadow.mjs 的输出）。
# 做法：
#   真实日志 in_game.log 里每个号每 90 拍一行 [HL-TICK] … cmds=N（策略自己数的「被受理的指令数」）；
#   影子策略的日志 logs.txt 里是同样的行，但影子里每条指令都算被受理。
#   影子日志没有号名，按（拍, 领土, 余额）和真实日志对上号。
#   对每个号相邻两行算 cmds 的增量：真实 vs 影子（日志行是在当拍出手之前打印的，所以一段是 [t0, t1)）。
#   列出不相等的段，并标出这一段里影子策略有没有
#   「同一个决策拍出 ≥2 条陆攻」的号·拍（intents.tsv）。
# 读法：如果线上同一拍的第 2 条指令不被受理（g.attack 返回 false，cmds 不加），
#   那么影子比真实多出来的条数应当等于这一段里同拍第 2 条的条数。
import sys, os, re, csv, collections
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = '/agent/repos/c136-data/bundles'
PAT = re.compile(r'\[HL-TICK\] t=(\d+) terr=(\d+)\([^)]*\) bal=(-?\d+) .* cmds=(\d+) boats=(\d+)')


def main():
    mid = sys.argv[1]
    # B 组的影子表用引擎编号当号的标签，日志用号名（还会中途换名）：号名先归到影子的标签上（log_alias.py）
    labels = set()
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            labels.add(r['bot'])
    al = {}
    if labels and all(x.isdigit() for x in labels):
        sys.path.insert(0, HERE)
        import log_alias
        al = {k: str(v) for k, v in log_alias.alias(mid).items()}

    def canon(nm):
        return al.get(nm, nm)
    real = collections.defaultdict(dict)
    with open(os.path.join(DATA, mid, 'in_game.log'), encoding='utf8', errors='replace') as f:
        for L in f:
            if 'HL-TICK' not in L:
                continue
            m = PAT.search(L)
            b = re.search(r'\[([^\]]+)\] \[HL-TICK\]', L)
            if m and b:
                real[canon(b.group(1))][int(m.group(1))] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    shadow = collections.defaultdict(list)
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'logs.txt'), encoding='utf8', errors='replace') as f:
        for L in f:
            m = PAT.search(L)
            if m:
                shadow[int(m.group(1))].append((int(m.group(2)), int(m.group(3)), int(m.group(4))))
    extra = collections.defaultdict(list)
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv'), encoding='utf8') as f:
        seen = collections.Counter()
        for r in csv.DictReader(f, delimiter='\t'):
            if r['kind'] != 'attack':
                continue
            k = (r['bot'], int(r['t']))
            seen[k] += 1
            if seen[k] >= 2:
                extra[r['bot']].append(int(r['t']))
    n = same = 0
    diffs = []
    unmatched = 0
    for b, snaps in real.items():
        ts = sorted(snaps)
        sh = {}
        for t in ts:
            terr, bal, _ = snaps[t]
            c = [x for x in shadow.get(t, []) if x[0] == terr and x[1] == bal]
            if len(c) == 1:
                sh[t] = c[0][2]
            else:
                unmatched += 1
        for t0, t1 in zip(ts, ts[1:]):
            if t0 not in sh or t1 not in sh:
                continue
            d_real = snaps[t1][2] - snaps[t0][2]
            d_sh = sh[t1] - sh[t0]
            n += 1
            if d_real == d_sh:
                same += 1
            else:
                k = sum(1 for t in extra.get(b, []) if t0 <= t < t1)
                diffs.append((b, t0, t1, d_real, d_sh, k))
    print('%s：能和影子日志对上号的相邻快照 %d 段（对不上号的快照 %d 个）；发令数增量相同 %d 段，不同 %d 段' % (mid, n, unmatched, same, len(diffs)))
    expl = sum(1 for d in diffs if d[4] - d[3] == d[5] and d[5] > 0)
    print('  不同的段里，「影子多出来的条数 = 这一段里同拍第 2 条陆攻的条数」的有 %d 段；其余 %d 段' % (expl, len(diffs) - expl))
    tot_extra = sum(len(v) for v in extra.values())
    in_same = 0
    for b, v in extra.items():
        ts = sorted(real.get(b, {}))
        for t in v:
            seg = [(t0, t1) for t0, t1 in zip(ts, ts[1:]) if t0 <= t < t1]
            if seg and not any(d[0] == b and d[1] == seg[0][0] for d in diffs):
                in_same += 1
    print('  影子策略同拍第 2 条陆攻共 %d 条；其中落在「发令数增量相同」的段里的 %d 条（如果有，说明那一条在线上被受理了）' % (tot_extra, in_same))
    for b, t0, t1, dr, ds, k in sorted(diffs, key=lambda d: (d[1], d[0])):
        print('    %-7s [%d,%d)：真实 +%d，影子 +%d；这一段里同拍第 2 条陆攻 %d 条' % (b, t0, t1, dr, ds, k))


if __name__ == '__main__':
    main()
