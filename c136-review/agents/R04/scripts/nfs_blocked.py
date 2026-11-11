#!/usr/bin/env python3
# isNoFullSend 误锁之后被 Policy.send（L3844~3862）的守卫拦掉的出兵：各号的上锁拍、被拦次数、想出的兵，以及全队合计。
# 用法：python3 scripts/nfs_blocked.py <局号> [<局号> …] [--from 拍]（--from：另外按号列出这一拍以后被拦的次数、想出的兵、目标编号）
# 数据：tmp/shadow/<局号>/check.json（shadow_all.sh 产出；blocked = [拍, 目标编号, 想出的兵]）。
import sys, os, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def fmt(n):
    return f'{n / 1e4:.1f} 万' if n >= 1e4 else str(int(n))


FROM = int(sys.argv[sys.argv.index('--from') + 1]) if '--from' in sys.argv else None
MIDS = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] != '--from']

for mid in MIDS:
    c = json.load(open(os.path.join(HERE, '..', 'tmp', 'shadow', mid, 'check.json'), encoding='utf-8'))
    bots = c['bots']
    items = list(bots.items()) if isinstance(bots, dict) else [(str(b.get('bot', b.get('p', i))), b) for i, b in enumerate(bots)]
    n = tr = 0
    locks = []
    parts = []
    for name, b in items:
        bl = b.get('blocked') or []
        s = sum(x[2] for x in bl)
        n += len(bl); tr += s
        if b.get('lockAt') is not None:
            locks.append(b['lockAt'])
        if bl:
            parts.append((s, f'{name} {len(bl)} 次 {fmt(s)}（{bl[0][0]}~{bl[-1][0]} 拍）'))
    parts.sort(reverse=True)
    print(f'{mid}：{len(locks)}/{len(items)} 个号上过锁（上锁拍 {min(locks) if locks else "-"}~{max(locks) if locks else "-"}）；被守卫拦掉的出兵 {n} 次，想出的兵合计 {fmt(tr)}')
    print('  按号：' + '；'.join(p[1] for p in parts))
    if FROM is not None:
        late = []
        for name, b in items:
            bl = [x for x in (b.get('blocked') or []) if x[0] >= FROM]
            if bl:
                tg = sorted({x[1] for x in bl})
                late.append((sum(x[2] for x in bl), f'{name} {len(bl)} 次 {fmt(sum(x[2] for x in bl))}（{bl[0][0]}~{bl[-1][0]} 拍，目标编号 {"、".join(map(str, tg))}）'))
        late.sort(reverse=True)
        print(f'  其中 {FROM} 拍以后：' + ('；'.join(p[1] for p in late) or '没有'))

