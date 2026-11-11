#!/usr/bin/env python3
# 选点阶段的换点流水：协调器每次整体求解给了谁哪个点、各号实际执行了哪些出生指令、最后落点离最后一次求解的点多远。
# 用法：python3 scripts/spawn_churn.py <局号> [--ours id,id,…] [--seq] [--fan]
#   --fan：把每一种不同的点位集合拿去套协调器「角落扇形阵」的几何（1 个顶点 + 内弧 + 外弧），看是不是这个分支排出来的。
# 数据：
#   协调器日志 = 对局包 in_game.log 里的 "[BACKEND-SPAWN-COORD] Solved …" 行（每行一轮求解：每个号的点位、点位最小间距）；
#   实际执行  = 真引擎重放 cmd.tsv 里的出生指令（指令号 0，参数 a = y×地图宽 + x，spawnStep = 选点阶段的第几步）；
#   最后落点  = meta.json 里该号最终出生方块的中心。
# 输出：求解轮数、阵型中心的移动、相邻两轮之间换了点的号数、各号出生指令条数 / 跳动 ≥80 像素的次数 / 最后一条所在步、
#       最后落点离最后一轮求解给它的点多远、离倒数各轮里最近的点多远；加 --seq 打印每个号的出生指令序列。
import sys, os, re, json, math, collections
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match

BUNDLES = '/agent/repos/c136-data/bundles'


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def fan_radii(rcell):
    # spawn-coordinator-c116-vb.mjs L1074~1077
    sep = clamp(round(0.95 * rcell), 42, 68)
    r0 = clamp(round(0.48 * rcell), 28, 46)
    r1 = clamp(round(1.12 * rcell), max(66, r0 + sep), 108)
    r2 = clamp(round(1.88 * rcell), max(122, r1 + sep), 182)
    return sep, r0, r1, r2


def fan_specs(ax, ay, phi, r0, r1, r2, K):
    # 同文件 L1135~1170：1 个顶点（r0）、innerCount 个内弧点（r1，±0.82×fanHalf）、其余外弧点（r2，±fanHalf）
    half = math.pi / 3.2
    inner = min(3, max(2, int((K - 1) * 0.34)))
    outer = max(1, K - 1 - inner)
    pts = [(ax + r0 * math.cos(phi), ay + r0 * math.sin(phi))]
    for i in range(inner):
        fr = 0.5 if inner == 1 else i / (inner - 1)
        g = phi - half * 0.82 + fr * (2 * half * 0.82)
        pts.append((ax + r1 * math.cos(g), ay + r1 * math.sin(g)))
    for j in range(outer):
        fr = 0.5 if outer == 1 else j / (outer - 1)
        g = phi - half + fr * (2 * half)
        pts.append((ax + r2 * math.cos(g), ay + r2 * math.sin(g)))
    return pts


def fan_fit(solves, land, meta):
    # 每一种不同的点位集合，试着用「角落扇形阵」的几何去套：枚举（顶点, 中间内弧点）这一对来反推锚点和朝向，
    # 再数 10 个标称点位里有几个在 10 像素内对得上日志里的点。半径取「已选点真人数」从 8 到（本局真人数+12）时代码会算出的各组 (r0, r1, r2)。
    nh = int(meta['info'].get('ku') or 36)
    triples = {}
    for h in range(8, max(41, nh + 12)):
        rc = math.sqrt(max(10000, land) / (math.pi * h))
        triples.setdefault(fan_radii(rc)[1:], []).append(h)
    seen = []
    print('  扇形阵拟合（--fan）：本局 %d 个真人时 rCell=%.1f → 点位最小间距、r0、r1、r2 = %s' % (
        nh, math.sqrt(land / (math.pi * nh)), fan_radii(math.sqrt(land / (math.pi * nh)))))
    for i, (sep, pts) in enumerate(solves):
        P = sorted(pts.values())
        last = (i == len(solves) - 1)
        if any(len(P) == len(Q) and all(math.hypot(p[0] - q[0], p[1] - q[1]) <= 12 for p, q in zip(P, Q)) for Q, _ in seen) and not last:
            continue
        seen.append((P, i + 1))
        K = len(P)
        best = None
        for (r0, r1, r2), hs in triples.items():
            for p in P:
                for q in P:
                    if p == q:
                        continue
                    dd = math.hypot(q[0] - p[0], q[1] - p[1])
                    if abs(dd - (r1 - r0)) > 12:
                        continue
                    ux, uy = (q[0] - p[0]) / dd, (q[1] - p[1]) / dd
                    ax, ay = p[0] - r0 * ux, p[1] - r0 * uy
                    phi = math.atan2(uy, ux)
                    spec = fan_specs(ax, ay, phi, r0, r1, r2, K)
                    errs = [min(math.hypot(s[0] - t[0], s[1] - t[1]) for t in P) for s in spec]
                    ok = sum(1 for e in errs if e <= 10)
                    key = (ok, -sum(sorted(errs)[:ok]) if ok else 0)
                    if best is None or key > best[0]:
                        best = (key, (round(ax), round(ay)), round(math.degrees(phi)), (r0, r1, r2), (min(hs), max(hs)), [round(e) for e in errs])
        if best:
            print('    第 %2d 轮的点位：标称 %d 个点里 %d 个在 10 像素内对上；锚点≈%s 朝向 %d°（0°=正东，90°=正南）半径 %s（真人数 %d~%d 时的取值）；各标称点的偏差 %s' % (
                i + 1, K, best[0][0], best[1], best[2], best[3], best[4][0], best[4][1], best[5]))
            if last:
                # 扇形面积 = 0.5×r2²×张角（张角 = 2×π/3.2 = 112.5°）；人均地盘 = 陆地像素 / 本局真人数；
                # 锚点到最近地图角落的距离（角落取 (24,24)、(W-25,24)、(W-25,H-25)、(24,H-25)，与代码 L1078~1083 一致）
                area = 0.5 * best[3][2] ** 2 * (2 * math.pi / 3.2)
                W, H = meta['info']['w'], meta['info']['h']
                dc = min(math.hypot(best[1][0] - cx, best[1][1] - cy) for cx in (24, W - 25) for cy in (24, H - 25))
                print('    最后一轮：扇形（外圈半径 %d、张角 112.5°）面积 ≈ %d 格 = %.2f 个人均地盘（%d 格）；外弧相邻点的标称间距 %d 像素；锚点离最近的地图角落 %d 像素' % (
                    best[3][2], area, area / (land / nh), land / nh,
                    round(2 * best[3][2] * math.sin((2 * math.pi / 3.2) / max(1, (K - 1 - min(3, max(2, int((K - 1) * 0.34))) - 1)) / 2)), dc))
        else:
            print('    第 %2d 轮的点位：套不上扇形阵' % (i + 1))


def main():
    a = sys.argv[1:]
    mid = a[0]
    ours = [int(x) for x in a[a.index('--ours') + 1].split(',')] if '--ours' in a else None
    M = Match(mid, ours)
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta = json.load(open(os.path.join(here, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    W = meta['info']['w']
    steps = meta.get('spawnSteps')
    names = {M.nm(p): p for p in M.our_ids}
    solves = []
    log = os.path.join(BUNDLES, mid, 'in_game.log')
    if os.path.exists(log):
        with open(log, encoding='utf8', errors='replace') as f:
            for line in f:
                if '[BACKEND-SPAWN-COORD] Solved' not in line:
                    continue
                ms = re.search(r'minSep=(\d+)px', line)
                pts = {}
                for m in re.finditer(r'(?:\[[^\]]*\]\s*)?([^\s|(\[\]]+)\([A-Z_]+\)->\((\d+),(\d+)\)', line):
                    pts[m.group(1)] = (int(m.group(2)), int(m.group(3)))
                if pts:
                    solves.append((int(ms.group(1)) if ms else -1, pts))
    print('%s：选点阶段 %s 步；协调器整体求解 %d 轮' % (mid, steps, len(solves)))
    if solves:
        cents = []
        for sep, pts in solves:
            xs = [v[0] for v in pts.values()]; ys = [v[1] for v in pts.values()]
            cents.append((round(sum(xs) / len(xs)), round(sum(ys) / len(ys))))
        runs = []
        for i, c in enumerate(cents):
            if not runs or math.hypot(c[0] - runs[-1][0][0], c[1] - runs[-1][0][1]) > 15:
                runs.append([c, i + 1, i + 1])
            else:
                runs[-1][2] = i + 1
        print('  阵型中心（各号点位的平均）：' + ' → '.join('(%d,%d)[第 %d%s 轮]' % (c[0], c[1], i0, ('~%d' % i1) if i1 != i0 else '') for c, i0, i1 in runs))
        print('  点位最小间距：%s' % dict(collections.Counter(s for s, _ in solves)))
        moved = []
        swaps = collections.Counter()
        for i in range(1, len(solves)):
            p0, p1 = solves[i - 1][1], solves[i][1]
            ch = [b for b in p1 if b in p0 and math.hypot(p1[b][0] - p0[b][0], p1[b][1] - p0[b][1]) > 20]
            moved.append(len(ch))
            for b in ch:
                for c in ch:
                    if b < c and math.hypot(p1[b][0] - p0[c][0], p1[b][1] - p0[c][1]) <= 20 and math.hypot(p1[c][0] - p0[b][0], p1[c][1] - p0[b][1]) <= 20:
                        swaps[(b, c)] += 1
        print('  相邻两轮之间点位变了（>20 像素）的号数：%s' % ' '.join(str(x) for x in moved))
        if swaps:
            print('  相邻两轮之间互换点位的号对：' + '，'.join('%s↔%s %d 次' % (k[0], k[1], v) for k, v in swaps.most_common()))
    if solves and '--fan' in a:
        fan_fit(solves, meta['info']['ke'], meta)
    final = {x['p']: tuple(x['spawn']) for x in meta['players'] if x['p'] in M.ours}
    print('  号 | 出生指令条数 | 跳动≥80像素的次数 | 最后一条在第几步 | 最后落点 | 离最后一轮求解的点 | 离此前各轮里最近的点（第几轮）')
    for p in M.our_ids:
        seq = [(c['sp'], c['a'] % W, c['a'] // W) for c in M.cmd if c['id'] == 0 and c['p'] == p]
        jumps = sum(1 for i in range(1, len(seq)) if math.hypot(seq[i][1] - seq[i - 1][1], seq[i][2] - seq[i - 1][2]) >= 80)
        fx, fy = final.get(p, (None, None))
        nm = M.nm(p)
        d_last = near = None
        if solves and fx is not None:
            if nm in solves[-1][1]:
                t = solves[-1][1][nm]
                d_last = math.hypot(fx - t[0], fy - t[1])
            best = None
            for i, (sep, pts) in enumerate(solves[:-1]):
                for b, t in pts.items():
                    d = math.hypot(fx - t[0], fy - t[1])
                    if best is None or d <= best[0]:
                        best = (d, i + 1, b)
            near = best
        print('  %-7s | %2d | %2d | %s | %s | %s | %s' % (
            nm, len(seq), jumps, seq[-1][0] if seq else '—', ('(%d,%d)' % (fx, fy)) if fx is not None else '—',
            ('%.0f' % d_last) if d_last is not None else '—',
            ('%.0f（第 %d 轮给 %s 的点）' % near) if near else '—'))
        if '--seq' in a:
            print('      ' + ' '.join('%d:(%d,%d)' % s for s in seq))


if __name__ == '__main__':
    main()
