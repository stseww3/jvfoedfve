#!/usr/bin/env python3
"""alias_overlay.py — B 系对局包的「号名轮换」归一。

B 系（c110）客户端的日志前缀（号名）在一局中途会换（例：Cleopatra → Bismarck → Centurion 是同一个客户端、同一个玩家号），
results.csv 记的是最后一个名字，录像名单和 [HL-GAME-INIT] 里是第一个名字。按名字对账的脚本会把后半局的日志和结果行丢掉。

本脚本不改 c136-data：按 src/tools/identity-map-discovery.csv 的 nameChain 把这一局
  in_game.log（行首前缀 [名字] 和 [RESULT 名字]）、results.csv、以及带 bot 列的派生 CSV
里的后续名字改回链上的第一个名字，写到覆盖数据根 /tmp/c136-r05/overlay/bundles/<局>/（其余文件软链到原件，src 软链到原 src）。
之后用环境变量 C136_DATA=/tmp/c136-r05/overlay 跑各脚本（它们都认这个变量）。

独立校验（不依赖 identity map 的说法）：链上相邻两个名字——
  前一个名字的最后一条 [HL-TICK] 与后一个名字的第一条 [HL-TICK]：maxMs 相同、cmds 不减、拍号相接（差 ≤ 180 拍）；
  链上最后一个名字的结果行 meId = 第一个名字 [HL-GAME-INIT] 的 me。
用法：python3 scripts/alias_overlay.py <matchId> [...]
"""
import csv
import io
import os
import re
import sys

SRC = '/agent/repos/c136-data'
OUT = '/tmp/c136-r05/overlay'


def chains(mid):
    rows = list(csv.DictReader(open(f'{SRC}/src/tools/identity-map-discovery.csv', encoding='utf-8')))
    out = []
    for r in rows:
        if r['matchId'] != mid:
            continue
        names = [x for x in (r.get('nameChain') or '').split('→') if x]
        if len(names) > 1:
            out.append((int(r['me']) if r['me'] else None, names))
    return out


def build(mid):
    B = f'{SRC}/bundles/{mid}'
    D = f'{OUT}/bundles/{mid}'
    os.makedirs(D, exist_ok=True)
    if not os.path.islink(f'{OUT}/src'):
        os.symlink(f'{SRC}/src', f'{OUT}/src')
    ch = chains(mid)
    alias = {}
    for me, names in ch:
        for n in names[1:]:
            alias[n] = names[0]
    # ---- 校验 ----
    ticks, init, res = {}, {}, {}
    for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
        m = re.match(r'\d+\t\[([^\]]+)\] \[HL-TICK\] t=(\d+).*?cmds=(\d+).*?maxMs=([\d.]+)', ln)
        if m:
            ticks.setdefault(m.group(1), []).append((int(m.group(2)), int(m.group(3)), m.group(4)))
        m = re.match(r'\d+\t\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)', ln)
        if m:
            init[m.group(1)] = int(m.group(2))
    for r in csv.DictReader(open(f'{B}/results.csv', encoding='utf-8')):
        res[r['bot']] = int(r['meId']) if r.get('meId') else None
    ok = True
    for me, names in ch:
        notes = []
        for a, b in zip(names, names[1:]):
            ta, tb = ticks.get(a), ticks.get(b)
            if not ta or not tb:
                notes.append(f'{a}→{b}: 缺 [HL-TICK]')
                ok = False
                continue
            la, fb = ta[-1], tb[0]
            good = la[2] == fb[2] and fb[1] >= la[1] and 0 < fb[0] - la[0] <= 180
            ok &= good
            notes.append(f'{a}(t={la[0]} cmds={la[1]} maxMs={la[2]}) → {b}(t={fb[0]} cmds={fb[1]} maxMs={fb[2]}) {"相接" if good else "对不上"}')
        last = names[-1]
        if last in res:
            g = res[last] == init.get(names[0])
            ok &= g
            notes.append(f'结果行 {last} meId={res[last]} {"=" if g else "≠"} {names[0]} 的 me={init.get(names[0])}')
        print(f'   链 me={me}: ' + '；'.join(notes))
    # ---- 写覆盖 ----
    pat_tag = re.compile(r'^(\d+\t\[)([^\]]+)(\])')
    pat_res = re.compile(r'(\[RESULT )([^\]]+)(\])')
    n_log = 0
    with open(f'{D}/in_game.log.tmp', 'w', encoding='utf-8') as f:
        for ln in open(f'{B}/in_game.log', encoding='utf-8', errors='replace'):
            m = pat_tag.match(ln)
            if m and m.group(2) in alias:
                ln = m.group(1) + alias[m.group(2)] + m.group(3) + ln[m.end():]
                n_log += 1
            else:
                m2 = pat_res.search(ln)
                if m2 and m2.group(2) in alias:
                    ln = ln[:m2.start()] + m2.group(1) + alias[m2.group(2)] + m2.group(3) + ln[m2.end():]
                    n_log += 1
            f.write(ln)
    os.replace(f'{D}/in_game.log.tmp', f'{D}/in_game.log')
    n_csv = {}
    for fn in sorted(os.listdir(B)):
        src, dst = f'{B}/{fn}', f'{D}/{fn}'
        if fn == 'in_game.log':
            continue
        if fn.endswith('.csv'):
            rows = list(csv.reader(open(src, encoding='utf-8', newline='')))
            if rows and 'bot' in rows[0]:
                ci = rows[0].index('bot')
                k = 0
                for r in rows[1:]:
                    if len(r) > ci and r[ci] in alias:
                        r[ci] = alias[r[ci]]
                        k += 1
                buf = io.StringIO()
                csv.writer(buf, lineterminator='\n').writerows(rows)
                if os.path.islink(dst) or os.path.exists(dst):
                    os.remove(dst)
                open(dst, 'w', encoding='utf-8', newline='').write(buf.getvalue())
                n_csv[fn] = k
                continue
        if os.path.islink(dst) or os.path.exists(dst):
            if os.path.isdir(dst) and not os.path.islink(dst):
                continue
            os.remove(dst)
        os.symlink(src, dst)
    print(f'[号名归一] {mid}: 链 {len(ch)} 条（{"；".join("→".join(n) for _, n in ch) or "无"}）｜校验 {"通过" if ok else "未通过"}｜in_game.log 改 {n_log} 行｜CSV 改 ' + (', '.join(f'{k} {v} 行' for k, v in n_csv.items()) or '0') + f' → {D}')
    return ok


if __name__ == '__main__':
    bad = 0
    for mid in sys.argv[1:]:
        bad += 0 if build(mid) else 1
    sys.exit(1 if bad else 0)
