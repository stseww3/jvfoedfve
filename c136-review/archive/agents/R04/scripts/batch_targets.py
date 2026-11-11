#!/usr/bin/env python3
# batch_targets.py — 晚到的陆攻指令落地时，打的还是不是当初瞄的那个目标。
#
# 引擎规则（live_game_js.js，bD.gv.rk）：陆攻指令执行时如果目标玩家已经不在场（ah.nU[目标]===0），
#   目标被改成 512（无主地），比例不变；录像里记的是改过之后的目标（qj.i6 里 bC.rg.rh(1,player,jC,bR.fV[0])）。
#   改成无主地之后：贴着无主地就按「比例 × 落地时的余额」出兵去占无主地；不贴无主地就不产生进攻、也不扣手续费。
#
# 用法：python3 scripts/batch_targets.py <局号> [--list] [--t0 630 --t1 1500]
#   先要有 tmp/truth/<局号>/cmd.tsv（engine_truth.cjs）和 tmp/shadow/<局号>/intents.tsv（shadow.mjs）；
#   有 tmp/truth/<局号>/ai_life.tsv（ai_life.mjs）时，另外给出「目标 AI 出局拍 → 指令落地拍」隔了几拍。
# 做法：
#   1) 成批落地的（同号同拍 ≥3 条陆攻）：用 burst_runs.py 的办法把这一批倒序对到一段连续的意图上，逐条比目标；
#   2) 零散落地的（同号同拍 1~2 条）：在此前 400 拍内找比例相同、还没被配走的最近一条意图，逐条比目标；配不上的另计。
#   3) 每条落地指令分成：目标没变 / 意图瞄的是内置 AI 或真人、落地时变成了无主地（= 目标已出局）/ 其他不一致；
#      变成无主地的再分：产生了进攻（出了多少兵、付了多少手续费）/ 没产生进攻。
#   4) 汇总：按时段（--t0~--t1，默认 630~1500）给条数与兵；另给「意图总条数 → 落在原目标上的条数」。
import sys, os, csv, collections, statistics
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from burst_runs import find_run  # noqa: E402

NEUTRAL = 512


def load(mid):
    intents = collections.defaultdict(list)
    names = {}
    with open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'intents.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            names[int(r['p'])] = r['bot']
            if r['kind'] == 'attack':
                intents[int(r['p'])].append((int(r['t']), int(r['pct']), int(r['target']), int(r['troops'])))
    cmds = collections.defaultdict(list)
    with open(os.path.join(ROOT, 'tmp', 'truth', mid, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if int(r['spawnStep']) >= 0 or int(r['id']) != 1:
                continue
            sent = 0
            for part in (r['sub'] or '').split(';'):
                x = part.split(':')
                if x[0] == 'atk' and len(x) >= 3:
                    sent += int(x[2])
            cmds[(int(r['p']), int(r['t']))].append((int(r['a']), int(r['b']), int(r['bal0']), int(r['bal1']), sent))
    life = {}
    lp = os.path.join(ROOT, 'tmp', 'truth', mid, 'ai_life.tsv')
    if os.path.exists(lp):
        with open(lp, encoding='utf8') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                life[int(r['p'])] = int(r['dead'])
    ku = None
    import json
    meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    ku = meta['info']['ku'] if 'info' in meta and 'ku' in meta['info'] else len(meta['players'])
    return names, intents, cmds, life, ku


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mid = args[0]
    lst = '--list' in sys.argv
    t0 = int(sys.argv[sys.argv.index('--t0') + 1]) if '--t0' in sys.argv else 630
    t1 = int(sys.argv[sys.argv.index('--t1') + 1]) if '--t1' in sys.argv else 1500
    names, intents, cmds, life, ku = load(mid)
    kind = lambda q: '无主地' if q >= NEUTRAL else ('内置AI' if q >= ku else '真人')
    S = collections.Counter()
    gaps, lags_same, lags_conv = [], [], []
    per_bot = collections.defaultdict(collections.Counter)
    rows = []
    n_int = n_int_ai = 0
    for p in sorted(names):
        ints = intents[p]
        n_int += sum(1 for x in ints if t0 <= x[0] < t1)
        n_int_ai += sum(1 for x in ints if t0 <= x[0] < t1 and x[2] < NEUTRAL)
        used = set()
        ticks = sorted(t for (q, t) in cmds if q == p)
        pairs = []   # (落地拍, 指令, 意图 或 None, 是否成批)
        for T in ticks:
            cs = cmds[(p, T)]
            if len(cs) >= 3:
                seq = [c[0] for c in cs]
                r = find_run(seq, ints, T, False) or find_run(seq, ints, T, True)
                if r is None:
                    for c in cs:
                        pairs.append((T, c, None, True))
                    continue
                i0, i1, sk = r
                idx = [i for i in range(i1, i0 - 1, -1) if i != sk]
                for c, i in zip(cs, idx):
                    used.add(i)
                    pairs.append((T, c, ints[i], True))
            else:
                for c in cs:
                    best = None
                    for i in range(len(ints) - 1, -1, -1):
                        if ints[i][0] > T or i in used:
                            continue
                        if T - ints[i][0] > 400:
                            break
                        if ints[i][1] == c[0]:
                            best = i
                            break
                    if best is None:
                        pairs.append((T, c, None, False))
                    else:
                        used.add(best)
                        pairs.append((T, c, ints[best], False))
        for (T, c, it, batch) in pairs:
            if not (t0 <= T < t1):
                continue
            a, b, bal0, bal1, sent = c
            fee = max(0, bal0 - bal1 - sent)
            tag = '成批' if batch else '零散'
            S[tag + ' 落地'] += 1
            if it is None:
                S[tag + ' 配不上意图'] += 1
                continue
            lag = T - it[0]
            if b == it[2]:
                S[tag + ' 目标没变'] += 1
                S[tag + ' 目标没变 兵'] += sent
                if it[2] < NEUTRAL:
                    S['落在原来瞄的AI或真人上'] += 1
                    S['落在原来瞄的AI或真人上 兵'] += sent
                lags_same.append(lag)
            elif b >= NEUTRAL and it[2] < NEUTRAL:
                k = kind(it[2])
                S[tag + ' 变成无主地'] += 1
                S['变成无主地（原来瞄的是' + k + '）'] += 1
                per_bot[names[p]]['变成无主地'] += 1
                lags_conv.append(lag)
                if sent > 0:
                    S['变成无主地 产生进攻'] += 1
                    S['变成无主地 产生进攻 兵'] += sent
                    S['变成无主地 产生进攻 手续费'] += fee
                    per_bot[names[p]]['改打无主地的兵'] += sent
                else:
                    S['变成无主地 没产生进攻'] += 1
                    S['变成无主地 没产生进攻 当初想出的兵'] += it[3]
                d = life.get(it[2], None)
                if d is not None and d >= 0:
                    gaps.append(T - d)
                if lst:
                    rows.append(f'  拍 {T:5d} {names[p]:7s} {tag} 比例 {a:4d}：意图拍 {it[0]}（晚 {lag} 拍）瞄 {k}#{it[2]}'
                                + (f'（它在拍 {d} 出局）' if d is not None and d >= 0 else '')
                                + (f' → 改打无主地 {sent} 兵，手续费 {fee}' if sent > 0 else ' → 没产生进攻'))
            else:
                S[tag + ' 其他不一致'] += 1
                if lst:
                    rows.append(f'  拍 {T:5d} {names[p]:7s} {tag} 比例 {a:4d}：意图拍 {it[0]} 瞄 {kind(it[2])}#{it[2]}，录像目标 {kind(b)}#{b}')
    print(f'# {mid} 拍段 [{t0},{t1}) 我方陆攻指令落地时的目标（引擎规则：目标已出局 → 改成无主地，比例不变）')
    print(f'影子策略的陆攻意图 {n_int} 条（其中瞄内置 AI 或真人的 {n_int_ai} 条）')
    for tag in ('成批', '零散'):
        print(f'{tag}落地 {S[tag + " 落地"]} 条：目标没变 {S[tag + " 目标没变"]} 条（出兵 {S[tag + " 目标没变 兵"]}）、'
              f'变成无主地 {S[tag + " 变成无主地"]} 条、其他不一致 {S[tag + " 其他不一致"]} 条、配不上意图 {S[tag + " 配不上意图"]} 条')
    conv = S['成批 变成无主地'] + S['零散 变成无主地']
    print(f'落在原来瞄的内置 AI / 真人身上的 {S["落在原来瞄的AI或真人上"]} 条，出兵 {S["落在原来瞄的AI或真人上 兵"]}'
          + (f'（= 瞄 AI/真人的意图的 {100 * S["落在原来瞄的AI或真人上"] / n_int_ai:.0f}%）' if n_int_ai else ''))
    print(f'变成无主地的 {conv} 条（原来瞄内置 AI 的 {S["变成无主地（原来瞄的是内置AI）"]} 条、瞄真人的 {S["变成无主地（原来瞄的是真人）"]} 条）：'
          f'产生进攻 {S["变成无主地 产生进攻"]} 条，出兵 {S["变成无主地 产生进攻 兵"]}、手续费 {S["变成无主地 产生进攻 手续费"]}；'
          f'没产生进攻 {S["变成无主地 没产生进攻"]} 条（当初想出的兵合计 {S["变成无主地 没产生进攻 当初想出的兵"]}）')
    if lags_same:
        print(f'延迟（意图拍 → 落地拍）：目标没变的 中位 {statistics.median(lags_same):.0f} 拍；变成无主地的 中位 {statistics.median(lags_conv):.0f} 拍' if lags_conv else
              f'延迟（意图拍 → 落地拍）：目标没变的 中位 {statistics.median(lags_same):.0f} 拍')
    if gaps:
        print(f'变成无主地的指令里，目标 AI 的出局拍已知的 {len(gaps)} 条：出局后隔 中位 {statistics.median(gaps):.0f} 拍落地（最小 {min(gaps)}、最大 {max(gaps)}）；'
              f'出局后 ≤28 拍就落地的 {sum(1 for g in gaps if g <= 28)} 条')
    if per_bot:
        print('按号（变成无主地的条数 / 改打无主地的兵）：' + '；'.join(f'{b} {c["变成无主地"]} / {c["改打无主地的兵"]}' for b, c in sorted(per_bot.items(), key=lambda kv: -kv[1]['变成无主地'])))
    if lst:
        print('\n'.join(sorted(rows)))


if __name__ == '__main__':
    main()
