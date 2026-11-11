#!/usr/bin/env python3
# 同队的非编队真人离我方出生点有多近、谁先选的点。
# 用法：python3 scripts/spawn_allies.py [局号…]（不给局号 = tmp/truth 下全部）
# 口径：出生点 = meta.json 里每个玩家最终出生方块的中心；rCell = sqrt(陆地像素 /(π×真人数))；
#   选点步数 = cmd.tsv 里 id=0 的行（每条出生指令的 spawnStep）；
#   「先到」= 这个队友最后一条出生指令的步数 < 我方该号第一条出生指令的步数；
#   「同时」= 介于我方该号第一条与最后一条之间；「后到」= 晚于我方该号最后一条。
#   一对（我方号, 队友）只在距离 ≤ 1.0×rCell 时列出；同时给出 1.5×rCell 内的对数。
# 后果（跑过影子策略的局才有）：我方各号第一次「没有任何非队友陆上邻居、也没有无主地」的拍（rows.tsv）。
import csv
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from match_digest import Match  # noqa: E402

OURS_B034 = [38, 27, 26, 22, 30, 48, 45, 31, 41]


def first_boxed(mid):
    p = os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv')
    if not os.path.exists(p):
        return {}
    out = {}
    for r in csv.DictReader(open(p, encoding='utf8'), delimiter='\t'):
        if r['bot'] in out:
            continue
        if int(r['terr']) > 0 and int(r['nb']) == 0 and int(r['neut']) == 0 and int(r['t']) >= 300:
            out[r['bot']] = int(r['t'])
    return out


def main():
    base = os.path.join(ROOT, 'tmp', 'truth')
    ms = [a for a in sys.argv[1:] if not a.startswith('--')] or sorted(os.listdir(base))
    for m in ms:
        mp = os.path.join(base, m, 'meta.json')
        if not os.path.exists(mp):
            continue
        M = Match(m, OURS_B034 if m == 'B034' else None)
        meta = json.load(open(mp, encoding='utf8'))
        info = meta['info']
        hum = info['ku']
        rc = math.sqrt(info['ke'] / (math.pi * hum))
        pl = {x['p']: x for x in meta['players'] if x['p'] < hum}
        ok = lambda p: p in pl and pl[p]['box'][0] <= pl[p]['box'][2]
        ours = [p for p in M.our_ids if ok(p)]
        if not ours:
            continue
        team = pl[ours[0]]['team']
        steps = {}
        for r in csv.DictReader(open(os.path.join(base, m, 'cmd.tsv'), encoding='utf8'), delimiter='\t'):
            if r['id'] != '0':
                continue
            steps.setdefault(int(r['p']), []).append(int(r['spawnStep']))
        allies = [q for q in pl if ok(q) and pl[q]['team'] == team and q not in ours]
        near, n15 = [], 0
        for p in ours:
            x, y = pl[p]['spawn']
            for q in allies:
                d = math.hypot(x - pl[q]['spawn'][0], y - pl[q]['spawn'][1])
                if d <= 1.5 * rc:
                    n15 += 1
                if d > 1.0 * rc:
                    continue
                sp, sq = steps.get(p, []), steps.get(q, [])
                if not sp or not sq:
                    order = '步数不详'
                elif max(sq) < min(sp):
                    order = '先到（早 %d 步）' % (min(sp) - max(sq))
                elif max(sq) > max(sp):
                    order = '后到（晚 %d 步）' % (max(sq) - max(sp))
                else:
                    order = '同时（它最后一条在第 %d 步，我方第一条 %d、最后一条 %d）' % (max(sq), min(sp), max(sp))
                near.append((d, M.nm(p), pl[q]['name'], q, order))
        fb = first_boxed(m)
        print('%s：我方 %d 个号，同队的非编队真人 %d 个，rCell=%.1f；离我方某号 ≤1.0×rCell 的（我方号, 队友）%d 对，≤1.5×rCell 的 %d 对'
              % (m, len(ours), len(allies), rc, len(near), n15))
        for d, b, nm, q, order in sorted(near):
            print('    %s ← %s#%d：%.0f 像素（%.2f×rCell），%s' % (b, nm, q, d, d / rc, order))
        if fb:
            print('    我方各号第一次封死（没有非队友陆上邻居、没有无主地）的拍：%s'
                  % '，'.join('%s %d' % (M.nm(p), fb[M.nm(p)]) if M.nm(p) in fb else '%s 没有' % M.nm(p) for p in ours))


if __name__ == '__main__':
    main()
