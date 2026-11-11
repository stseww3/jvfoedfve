#!/usr/bin/env python3
# 选点阶段：策略先后「想去」的每一个点，哪些在录像里真的落地了、落在第几步。
# 用法：python3 scripts/spawn_first_cmd.py [局号 …] [--list]      不给局号 = tmp/truth 下全部
# 数据：
#   想去的点 = 对局包 in_game.log 里各号的 "[HL-SPAWN] me=… -> (x,y)"（本地兜底选点）和
#              "[HL-SPAWN-BACKEND] me=… -> (x,y)"（协调器给的点；策略只在点位移动 >4 像素时才打这一行，chooseSpawn L4034）；
#              按日志的入库顺序排。
#   落地的点 = 真引擎重放 cmd.tsv 里的出生指令（指令号 0，a = y×地图宽 + x，spawnStep = 选点阶段第几步）。
#   引擎只在 qj.i0 三个条件都满足时才把出生指令写进录像（选点阶段、玩家有效、像素在图内），所以录像里没有 = 服务器的回合包里没有。
# 口径：落地指令与想去的点相距 ≤2 像素算同一个点。
# 输出：每局 —— 各号想去的点数、落地条数、第一个想去的点落没落地、只打过一行日志（点位从没变过）的号落没落地；
#       --list 逐号打印序列。合计行写 tmp/spawn_first/_all.json。
import sys, os, re, json, csv, math, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLES = '/agent/repos/c136-data/bundles'
PAT = re.compile(r'\[(HL-SPAWN|HL-SPAWN-BACKEND)\] me=(\d+) .*?-> \((-?\d+),(-?\d+)\)')


def one(mid, show):
    tdir = os.path.join(ROOT, 'tmp', 'truth', mid)
    meta = json.load(open(os.path.join(tdir, 'meta.json')))
    ours = {int(k): v for k, v in meta['ours'].items()} if isinstance(meta['ours'], dict) else {int(p): str(p) for p in meta['ours']}
    W = None
    for line in open(os.path.join(BUNDLES, mid, 'in_game.log'), encoding='utf-8', errors='replace'):
        m = re.search(r'map=(\d+)x(\d+)', line)
        if m:
            W = int(m.group(1))
            break
    if W is None:
        info = meta.get('info') or {}
        W = info.get('W') or info.get('w')
    wanted = collections.defaultdict(list)
    for line in open(os.path.join(BUNDLES, mid, 'in_game.log'), encoding='utf-8', errors='replace'):
        m = PAT.search(line)
        if not m:
            continue
        kind, p, x, y = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if p in ours:
            wanted[p].append((kind, x, y))
    landed = collections.defaultdict(list)
    others_first = []
    seen_other = {}
    for r in csv.DictReader(open(os.path.join(tdir, 'cmd.tsv')), delimiter='\t'):
        s = int(r['spawnStep'])
        if s < 0 or int(r['id']) != 0:
            continue
        p, a = int(r['p']), int(r['a'])
        if p in ours:
            landed[p].append((s, a % W, a // W))
        elif p not in seen_other:
            seen_other[p] = s
    rows = []
    for p in sorted(ours):
        w, l = wanted[p], landed[p]
        hit = []
        for (kind, x, y) in w:
            steps = [s for (s, lx, ly) in l if math.hypot(lx - x, ly - y) <= 2]
            hit.append(min(steps) if steps else None)
        stray = [(s, lx, ly) for (s, lx, ly) in l if not any(math.hypot(lx - x, ly - y) <= 2 for (_, x, y) in w)]
        nb = [i for i, (kind, _, _) in enumerate(w) if kind == 'HL-SPAWN-BACKEND']
        rows.append(dict(p=p, name=ours[p], wanted=w, landed=l, hit=hit, stray=len(stray),
                         firstAny=(hit[0] if hit else None), firstBackend=(hit[nb[0]] if nb else None), nBackend=len(nb),
                         lastBackend=(hit[nb[-1]] if nb else None), nLanded=len(l)))
    n = len(rows)
    with_w = [r for r in rows if r['wanted']]
    first_any = sum(1 for r in with_w if r['firstAny'] is not None)
    with_b = [r for r in rows if r['nBackend']]
    first_b = sum(1 for r in with_b if r['firstBackend'] is not None)
    last_b = sum(1 for r in with_b if r['lastBackend'] is not None)
    single = [r for r in with_b if r['nBackend'] == 1]
    single_hit = sum(1 for r in single if r['firstBackend'] is not None)
    multi = [r for r in with_b if r['nBackend'] >= 2]
    later_pts = sum(r['nBackend'] - 1 for r in multi)
    later_hit = sum(1 for r in multi for i, (kind, _, _) in enumerate(r['wanted'])
                    if kind == 'HL-SPAWN-BACKEND' and i != [j for j, (k, _, _) in enumerate(r['wanted']) if k == 'HL-SPAWN-BACKEND'][0] and r['hit'][i] is not None)
    none = sum(1 for r in rows if r['nLanded'] == 0)
    first_steps = sorted(min(s for (s, _, _) in r['landed']) for r in rows if r['landed'])
    of = sorted(seen_other.values())
    med = lambda v: v[len(v) // 2] if v else None
    print(f'{mid}：选点阶段 {meta.get("spawnSteps")} 步；我方 {n} 个号，有选点日志的 {len(with_w)} 个')
    print(f'  第一个想去的点（不分兜底 / 协调器）落地的号：{first_any} / {len(with_w)}；协调器给的第一个点落地的号：{first_b} / {len(with_b)}；协调器给的最后一个点落地的号：{last_b} / {len(with_b)}')
    print(f'  协调器点位从没变过（只有 1 行）的号 {len(single)} 个：落地 {single_hit} 个；点位变过的号 {len(multi)} 个：后来换的点共 {later_pts} 个、落地 {later_hit} 个')
    print(f'  一条出生指令都没落地的号 {none} 个；我方各号第一条落地的出生指令在第几步：最早 {first_steps[0] if first_steps else "—"}、中位 {med(first_steps) if first_steps else "—"}；'
          f'其他玩家第一条落地：最早 {of[0] if of else "—"}、中位 {med(of) if of else "—"}（{len(of)} 人）')
    if show:
        for r in rows:
            seq = '；'.join(f'{"兜底" if k == "HL-SPAWN" else "协调器"}({x},{y})→{"第 %d 步" % h if h is not None else "没落地"}' for (k, x, y), h in zip(r['wanted'], r['hit']))
            ld = ' '.join(f'{s}:({x},{y})' for (s, x, y) in r['landed'][:8]) + (' …' if len(r['landed']) > 8 else '')
            print(f'    {r["name"].replace("[APEX] ", ""):8s} 想去 {len(r["wanted"])} 个点：{seq[:420]} | 落地 {r["nLanded"]} 条（对不上任何日志点的 {r["stray"]} 条）：{ld}')
    return dict(match=mid, bots=n, withLog=len(with_w), firstAny=first_any, withBackend=len(with_b), firstBackend=first_b, lastBackend=last_b,
                single=len(single), singleHit=single_hit, multi=len(multi), laterPts=later_pts, laterHit=later_hit, none=none,
                firstStepMin=(first_steps[0] if first_steps else None), firstStepMed=(med(first_steps) if first_steps else None),
                otherFirstMin=(of[0] if of else None), otherFirstMed=(med(of) if of else None))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    show = '--list' in sys.argv
    mids = args or sorted(d for d in os.listdir(os.path.join(ROOT, 'tmp', 'truth')) if os.path.exists(os.path.join(ROOT, 'tmp', 'truth', d, 'meta.json')))
    out = []
    for mid in mids:
        out.append(one(mid, show))
    if len(out) > 1:
        s = lambda k: sum(o[k] or 0 for o in out)
        print(f'合计 {len(out)} 局 {s("bots")} 个号：协调器给的第一个点落地 {s("firstBackend")} / {s("withBackend")}；点位从没变过的号 {s("single")} 个里落地 {s("singleHit")} 个；'
              f'后来换的点 {s("laterPts")} 个里落地 {s("laterHit")} 个；一条都没落地的号 {s("none")} 个')
    os.makedirs(os.path.join(ROOT, 'tmp', 'spawn_first'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'tmp', 'spawn_first', '_all.json' if len(out) > 1 else out[0]['match'] + '.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
