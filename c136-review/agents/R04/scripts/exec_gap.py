#!/usr/bin/env python3
# exec_gap.py — 「想发的」对「落地的」：影子策略逐拍给出的发令意图（tmp/shadow/<局号>/intents.tsv，
# 已与真实日志的调度逐条相同、发令数增量逐段相同）对照录像里真正被执行的指令（tmp/truth/<局号>/cmd.tsv）。
#
# 用法：python3 scripts/exec_gap.py <局号> [--bot 名字] [--list t0 t1]
#   先要有：bash scripts/engine_truth_all.sh <局号>；node scripts/shadow.mjs <局号> --bots <全部我方号> --quiet --out tmp/shadow/<局号>
# 输出：
#   1) 每个号：发出/落地 的条数（陆攻、捐款、发船），落地率；落地指令的延迟（拍）中位/九成位/最大
#   2) 按时段（<630、<1500、<3000、≥3000）的落地率
#   3) 连续「发了但一条都没落地」最长的几段（哪一拍到哪一拍、发了多少条、想打谁）
# 配对规则：同一个号、同一类指令、比例（pct）相同、目标相同（目标已死时录像里记成无主地 512，按比例配）；
#   落地拍 ≥ 发令拍，取离落地拍最近的一条未配对意图。捐款被配额拒绝的不会进录像，算「没落地」。
import sys, os, csv, json, collections, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(mid):
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    sdir = os.path.join(ROOT, 'tmp', 'shadow', mid)
    intents = []
    with open(os.path.join(sdir, 'intents.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            intents.append(dict(t=int(r['t']), p=int(r['p']), bot=r['bot'], kind=r['kind'], pct=int(r['pct']), target=int(r['target']), troops=int(r['troops'])))
    cmds = []
    with open(os.path.join(tdir, 'cmd.tsv'), encoding='utf8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if int(r['spawnStep']) >= 0:
                continue
            cmds.append(dict(t=int(r['t']), id=int(r['id']), p=int(r['p']), a=int(r['a']), b=int(r['b']), bal0=int(r['bal0']), bal1=int(r['bal1']), sub=r['sub']))
    check = json.load(open(os.path.join(sdir, 'check.json')))
    return intents, cmds, check


KIND_ID = {'attack': 1, 'donate': 2, 'boat': 3, 'chase': 4, 'retreat': 5}
NAME = {'attack': '陆攻', 'donate': '捐款', 'boat': '发船', 'chase': '追船', 'retreat': '撤兵', 'recall': '召回'}


def match(intents, cmds):
    """返回 (pairs, unmatched_intents, unmatched_cmds)。pairs: (intent, cmd)"""
    by = collections.defaultdict(list)
    for x in intents:
        by[(x['p'], x['kind'])].append(x)
    used = set()
    pairs, lone = [], []
    for c in cmds:
        kind = {1: 'attack', 2: 'donate', 3: 'boat', 4: 'chase', 5: 'retreat'}.get(c['id'])
        if kind is None:
            continue
        cand = by.get((c['p'], kind), [])
        best = None
        for x in reversed(cand):
            if id(x) in used or x['t'] > c['t']:
                continue
            if c['t'] - x['t'] > 900:
                break
            if kind in ('attack', 'donate'):
                if x['pct'] != c['a']:
                    continue
                if kind == 'donate' and x['target'] != c['b']:
                    continue
                if kind == 'attack' and x['target'] != c['b'] and c['b'] != 512:
                    continue
            elif kind == 'boat':
                if x['pct'] != c['a']:
                    continue
            best = x
            break
        if best is None:
            lone.append(c)
        else:
            used.add(id(best))
            pairs.append((best, c))
    rest = [x for x in intents if id(x) not in used]
    return pairs, rest, lone


def q(v, p):
    if not v:
        return None
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))]


def main():
    a = sys.argv[1:]
    mid = a[0]
    only = a[a.index('--bot') + 1] if '--bot' in a else None
    intents, cmds, check = load(mid)
    ours = {b['p']: b['bot'] for b in check['bots']}
    cmds = [c for c in cmds if c['p'] in ours]
    pairs, rest, lone = match(intents, cmds)
    print(f'# {mid} 想发的 vs 落地的（影子策略 {check["ver"]}；自检：{json.dumps(check["cmp"], ensure_ascii=False)}）')
    print('号        陆攻 发/落(率)      捐款 发/落(率)      发船 发/落(率)     延迟(拍) 中位/九成/最大   没配上的落地指令')
    tot = collections.Counter()
    for p, b in ours.items():
        if only and b != only:
            continue
        row = [f'{b:8s}']
        for kind in ('attack', 'donate', 'boat'):
            e = sum(1 for x in intents if x['p'] == p and x['kind'] == kind)
            l = sum(1 for (x, c) in pairs if x['p'] == p and x['kind'] == kind)
            tot[kind + 'e'] += e; tot[kind + 'l'] += l
            row.append(f'{e:4d}/{l:4d}({(100*l/e if e else 0):3.0f}%)   ')
        lags = [c['t'] - x['t'] for (x, c) in pairs if x['p'] == p]
        row.append(f'{q(lags, .5)}/{q(lags, .9)}/{max(lags) if lags else None}'.ljust(22))
        row.append(str(sum(1 for c in lone if c['p'] == p and c['id'] in (1, 2, 3))))
        print(' '.join(row))
    print('合计：' + '；'.join(f'{NAME[k]} 发 {tot[k+"e"]} 落 {tot[k+"l"]}（{100*tot[k+"l"]/max(1,tot[k+"e"]):.0f}%）' for k in ('attack', 'donate', 'boat')))
    # 按时段
    print('按时段的落地率（陆攻 / 捐款）：')
    for lo, hi, lab in ((0, 630, '<630'), (630, 1500, '630~1499'), (1500, 3000, '1500~2999'), (3000, 4284, '3000~4283'), (4284, 10**9, '≥4284')):
        s = []
        for kind in ('attack', 'donate'):
            e = [x for x in intents if x['kind'] == kind and lo <= x['t'] < hi and (not only or x['bot'] == only)]
            l = [1 for (x, c) in pairs if x['kind'] == kind and lo <= x['t'] < hi and (not only or x['bot'] == only)]
            s.append(f'{NAME[kind]} {len(e)}→{len(l)}（{100*len(l)/max(1,len(e)):.0f}%）')
        lags = [c['t'] - x['t'] for (x, c) in pairs if lo <= x['t'] < hi and (not only or x['bot'] == only)]
        print(f'  {lab:10s} ' + '；'.join(s) + f'；延迟中位 {q(lags, .5)} 九成位 {q(lags, .9)}')
    # 最长的「发了但没落地」的连续段（只看陆攻）
    print('连续发了陆攻却一条都没落地的最长几段：')
    segs = []
    paired = set(id(x) for (x, c) in pairs)
    for p, b in ours.items():
        if only and b != only:
            continue
        cur = []
        for x in [y for y in intents if y['p'] == p and y['kind'] == 'attack']:
            if id(x) in paired:
                if len(cur) >= 5:
                    segs.append((b, cur))
                cur = []
            else:
                cur.append(x)
        if len(cur) >= 5:
            segs.append((b, cur))
    segs.sort(key=lambda s: -len(s[1]))
    for b, cur in segs[:10]:
        tg = collections.Counter('无主地' if x['target'] == 512 else ('AI' if x['target'] >= check.get('ku', 10**6) else f'#{x["target"]}') for x in cur)
        tr = sum(x['troops'] for x in cur)
        print(f'  {b:8s} 拍 {cur[0]["t"]}~{cur[-1]["t"]}：{len(cur)} 条，目标 ' + '，'.join(f'{k}×{v}' for k, v in tg.most_common(3)) + f'；每条想出的兵 {cur[0]["troops"]}~{cur[-1]["troops"]}')
    if '--list' in a:
        i = a.index('--list'); t0, t1 = int(a[i + 1]), int(a[i + 2])
        pm = {id(x): c for (x, c) in pairs}
        for x in intents:
            if t0 <= x['t'] <= t1 and (not only or x['bot'] == only):
                c = pm.get(id(x))
                print(f'  拍 {x["t"]} {x["bot"]} {NAME.get(x["kind"], x["kind"])} 目标 {x["target"]} {x["pct"]}/1024 想出 {x["troops"]} → ' + (f'落地于 {c["t"]}（晚 {c["t"]-x["t"]} 拍），余额 {c["bal0"]}→{c["bal1"]}' if c else '没落地'))


if __name__ == '__main__':
    main()
