#!/usr/bin/env python3
# shadow_merge.py — 把 shadow_chunk.sh 分几次跑出来的影子结果合成 tmp/shadow/<局号>/{intents.tsv,rows.tsv,logs.txt,check.json}。
# 用法：python3 scripts/shadow_merge.py <局号> [--keep]
#   各份在 tmp/shadow/<局号>.chunk-<第一个号>/；还有号没跑到、或者同一个号出现在两份里，就报错退出，不写结果。
#   行的顺序和 shadow_all.sh 一次跑完的相同：先按拍，同一拍按我方号在 meta.json 里的顺序。
#   check.json：bots 按同一顺序拼起来，cmp 里的计数相加。合成后默认删掉各份目录（--keep 保留）。
import sys, os, json, re, shutil, glob
sys.dont_write_bytecode = True
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def main():
    a = sys.argv[1:]
    mid = a[0]
    keep = '--keep' in a
    meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json')))
    ours = meta['ours']
    order = [str(p) for p in ours] if mid[0] == 'B' else [v.replace('[APEX] ', '') for v in ours.values()]
    rank = {b: i for i, b in enumerate(order)}
    parts = sorted(glob.glob(os.path.join(ROOT, 'tmp', 'shadow', f'{mid}.chunk-*')))
    seen = {}
    for p in parts:
        for f in ('intents.tsv', 'rows.tsv', 'logs.txt', 'check.json'):
            if not os.path.exists(os.path.join(p, f)):
                print(f'缺 {os.path.relpath(os.path.join(p, f), ROOT)}')
                return 1
        for b in json.load(open(os.path.join(p, 'check.json')))['bots']:
            if b['bot'] in seen:
                print(f'{b["bot"]} 同时出现在 {os.path.basename(seen[b["bot"]])} 和 {os.path.basename(p)} 里')
                return 1
            seen[b['bot']] = p
    lack = [b for b in order if b not in seen]
    if lack:
        print(f'{mid}：还有 {len(lack)} 个号没跑到：{lack}（已有 {len(parts)} 份）')
        return 1
    # 按第一个号在 meta.json 里的顺序排各份（同一拍内的行序只看号的顺序，这里只是为了日志行的先后稳定）
    parts.sort(key=lambda p: min(rank.get(b, 99) for b, q in seen.items() if q == p))
    n = len(parts)
    out = os.path.join(ROOT, 'tmp', 'shadow', mid)
    os.makedirs(out, exist_ok=True)

    def merge_tsv(name, bot_col):
        head, rows = None, []
        for pi, p in enumerate(parts):
            with open(os.path.join(p, name), encoding='utf8') as f:
                lines = f.read().split('\n')
            if head is None:
                head = lines[0]
            elif lines[0] != head:
                raise SystemExit(f'{name} 表头不一致')
            for li, l in enumerate(lines[1:]):
                if not l:
                    continue
                c = l.split('\t')
                rows.append((int(c[0]), rank.get(c[bot_col], 99), pi, li, l))
        rows.sort(key=lambda r: r[:4])
        with open(os.path.join(out, name), 'w', encoding='utf8') as f:
            f.write(head + '\n' + '\n'.join(r[4] for r in rows) + '\n')
        return len(rows)

    n_int = merge_tsv('intents.tsv', 2)
    n_rows = merge_tsv('rows.tsv', 1)
    # 日志行：按行里的 t= 排（没有 t= 的行跟着上一行），同一拍按份的顺序
    logs = []
    tre = re.compile(r'\bt=(\d+)')
    for pi, p in enumerate(parts):
        last = 0
        with open(os.path.join(p, 'logs.txt'), encoding='utf8', errors='replace') as f:
            for li, l in enumerate(f.read().split('\n')):
                if not l:
                    continue
                mm = tre.search(l)
                if mm:
                    last = int(mm.group(1))
                logs.append((last, pi, li, l))
    logs.sort(key=lambda r: r[:3])
    with open(os.path.join(out, 'logs.txt'), 'w', encoding='utf8') as f:
        f.write('\n'.join(r[3] for r in logs) + '\n')
    checks = [json.load(open(os.path.join(p, 'check.json'))) for p in parts]
    base = dict(checks[0])
    for c in checks[1:]:
        for k in ('match', 'ver', 'from', 'to', 'ku'):
            if c[k] != base[k]:
                raise SystemExit(f'check.json 的 {k} 不一致：{c[k]} / {base[k]}')
    bots = [b for c in checks for b in c['bots']]
    bots.sort(key=lambda b: rank.get(b['bot'], 99))
    cmp = {}
    for c in checks:
        for k, v in c['cmp'].items():
            cmp[k] = cmp.get(k, 0) + v
    base['bots'] = bots
    base['cmp'] = cmp
    base['mergedFrom'] = n
    with open(os.path.join(out, 'check.json'), 'w', encoding='utf8') as f:
        f.write(json.dumps(base, ensure_ascii=False, indent=1) + '\n')
    if not keep:
        for p in parts:
            shutil.rmtree(p)
    miss = [b for b in order if b not in {x['bot'] for x in bots}]
    print(f'{mid}：合成 {n} 份 → 号 {len(bots)} 个（缺 {miss if miss else "无"}），意图 {n_int} 条，行动拍 {n_rows} 行，日志 {len(logs)} 行')
    print(f'# 自检：相邻快照之间的发令数增量 一致 {cmp.get("dcSame", 0)} / 差 1 以内 {cmp.get("dcNear", 0)} / 不一致 {cmp.get("dcBad", 0)}（共 {cmp.get("dc", 0)} 段）')
    print(f'# 自检：nb/neut 与真实日志一致 {cmp.get("nbOk", 0)} 点，不一致 {cmp.get("nbBad", 0)} 点；调度同拍都有 {cmp.get("disBoth", 0)}（其中对象和比例完全相同 {cmp.get("disSame", 0)}），只有影子有 {cmp.get("disOnlyShadow", 0)}，只有真实日志有 {cmp.get("disOnlyReal", 0)}')
    for b in bots:
        if b.get('errs'):
            print(f'# {b["bot"]} 策略运行报错 {b["errs"]} 次')
    return 0


if __name__ == '__main__':
    sys.exit(main())
