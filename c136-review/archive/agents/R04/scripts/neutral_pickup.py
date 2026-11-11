#!/usr/bin/env python3
# 中后期「捡无主地」的账：别的号出局后留下的无主地，我方号用 expandNeutral 去捡，一条指令至少出 feeK×手续费（约余额的 4.6%），
# 手续费按余额的 12/1024 收、不退。余额几百万时，捡几百格地也要付几万兵的手续费；指令还没生效时又会连下两三条。
# 用法：python3 scripts/neutral_pickup.py <局号> [--from 1500] [--gap 14] [--post 150] [--list] [--ours id,id,…]
# 数据：tmp/truth/<局号>/cmd.tsv（真引擎重放的每条指令：指令号 1 = 陆攻，b = 512 是无主地；sub 里 atk:512:N 是实际出征的兵）、
#       flow.tsv（地块流动：from=512 → to=我方号 的格数）。
# 口径：同一个号相邻两条打无主地的陆攻相隔 ≤ gap 拍算一轮；一轮的「捡到的地」= 这一轮第一条到最后一条之后 post 拍内，
#       从无主地流到这个号的格数（同一段里两轮重叠时会重复计，合计行按号把窗口并起来只算一次）。
#       手续费 = 指令前后余额差 − 实际出征的兵。出征的兵打完无主地后剩下的会退回余额，所以真正白花的是手续费。
# 输出：按时段（--from 起每 1500 拍一段）的轮数、条数、出征兵、手续费、捡到的地、每格地摊到的手续费；一轮 ≥2 条的轮数。
import sys, os, csv, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def main():
    mid = sys.argv[1]
    t_from = int(arg('--from', 1500))
    gap = int(arg('--gap', 14))
    post = int(arg('--post', 150))
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json')))
    if '--ours' in sys.argv:
        ours = {int(x): str(x) for x in arg('--ours', '').split(',')}
    else:
        ours = {int(k): v.replace('[APEX] ', '') for k, v in meta['ours'].items()} if isinstance(meta['ours'], dict) else {int(p): str(p) for p in meta['ours']}
    cmds = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(tdir, 'cmd.tsv')), delimiter='\t'):
        if int(r['spawnStep']) >= 0 or int(r['id']) != 1 or int(r['b']) != 512:
            continue
        p, t = int(r['p']), int(r['t'])
        if p not in ours or t < t_from:
            continue
        out = 0
        for part in (r.get('sub') or '').split('|'):
            if part.startswith('atk:512:'):
                out += int(part.split(':')[2])
        spent = int(r['bal0']) - int(r['bal1'])
        cmds[p].append(dict(t=t, pct=int(r['a']), bal=int(r['bal0']), out=out, fee=max(0, spent - out), terr=int(r['terr0'])))
    gain = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(tdir, 'flow.tsv')), delimiter='\t'):
        if int(r['from']) == 512 and int(r['to']) in ours:
            gain[int(r['to'])].append((int(r['t']), int(r['px'])))
    rounds = []
    for p, lst in cmds.items():
        lst.sort(key=lambda c: c['t'])
        cur = []
        for c in lst:
            if cur and c['t'] - cur[-1]['t'] > gap:
                rounds.append((p, cur))
                cur = []
            cur.append(c)
        if cur:
            rounds.append((p, cur))
    rows = []
    for p, cur in rounds:
        t0, t1 = cur[0]['t'], cur[-1]['t'] + post
        px = sum(n for (t, n) in gain[p] if t0 <= t <= t1)
        rows.append(dict(p=p, bot=ours[p], t0=t0, n=len(cur), out=sum(c['out'] for c in cur), fee=sum(c['fee'] for c in cur),
                         bal=cur[0]['bal'], terr=cur[0]['terr'], px=px, pct=[c['pct'] for c in cur], noatk=sum(1 for c in cur if c['out'] == 0)))
    rows.sort(key=lambda r: r['t0'])

    def union_px(sel):
        tot = 0
        by = collections.defaultdict(list)
        for r in sel:
            by[r['p']].append((r['t0'], r['t0'] + (r['n'] - 1) * 7 + post))
        for p, wins in by.items():
            wins.sort()
            merged = []
            for a, b in wins:
                if merged and a <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], b)
                else:
                    merged.append([a, b])
            for a, b in merged:
                tot += sum(n for (t, n) in gain[p] if a <= t <= b)
        return tot

    last = int(meta.get('lastTick') or 0)
    print(f'# {mid} 捡无主地的账（拍 ≥{t_from}；同号相隔 ≤{gap} 拍算一轮；捡到的地 = 这一轮之后 {post} 拍内从无主地流到这个号的格数）')
    edges = list(range(t_from, max(last, t_from) + 1500, 1500))
    summary = []
    for a, b in zip(edges, edges[1:]):
        sel = [r for r in rows if a <= r['t0'] < b]
        if not sel:
            continue
        n, out, fee = sum(r['n'] for r in sel), sum(r['out'] for r in sel), sum(r['fee'] for r in sel)
        px = union_px(sel)
        multi = sum(1 for r in sel if r['n'] >= 2)
        big = [r for r in sel if r['bal'] >= 1_000_000]
        print(f'  [{a},{b})：{len(sel)} 轮 {n} 条（一轮 ≥2 条的 {multi} 轮），出征 {out:,} 兵，手续费 {fee:,}；捡到 {px:,} 格 → 每格摊手续费 {fee / max(1, px):.1f} 兵；'
              f'其中出手时余额 ≥100 万的 {len(big)} 轮 {sum(r["n"] for r in big)} 条，手续费 {sum(r["fee"] for r in big):,}，捡到 {union_px(big):,} 格')
        summary.append(dict(t0=a, t1=b, rounds=len(sel), cmds=n, multi=multi, out=out, fee=fee, px=px,
                            bigRounds=len(big), bigCmds=sum(r['n'] for r in big), bigFee=sum(r['fee'] for r in big), bigPx=union_px(big)))
    tot_fee = sum(r['fee'] for r in rows)
    print(f'  合计：{len(rows)} 轮 {sum(r["n"] for r in rows)} 条，出征 {sum(r["out"] for r in rows):,} 兵，手续费 {tot_fee:,}，捡到 {union_px(rows):,} 格')
    by = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        by[r['bot']][0] += r['n']
        by[r['bot']][1] += r['fee']
    print('  按号（条 / 手续费）：' + '；'.join(f'{b} {v[0]} / {v[1]:,}' for b, v in sorted(by.items(), key=lambda kv: -kv[1][1])))
    if '--list' in sys.argv:
        for r in rows:
            print(f'    拍 {r["t0"]:5d} {r["bot"]:8s} {r["n"]} 条（比例 {"/".join(map(str, r["pct"]))}，没产生进攻 {r["noatk"]} 条）余额 {r["bal"]:,} 地 {r["terr"]:,} → 出征 {r["out"]:,}、手续费 {r["fee"]:,}；随后 {post} 拍捡到 {r["px"]:,} 格')
    os.makedirs(os.path.join(ROOT, 'tmp', 'neutral'), exist_ok=True)
    json.dump(dict(match=mid, tFrom=t_from, bands=summary, rounds=len(rows), cmds=sum(r['n'] for r in rows), fee=tot_fee, px=union_px(rows)),
              open(os.path.join(ROOT, 'tmp', 'neutral', mid + '.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
