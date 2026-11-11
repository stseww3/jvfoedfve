#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把两份全量计数（out/bundle_patterns.txt、out/bundle_cmdstream.txt）里「按编队 × 版本」「按结果」的行
摘成两张横向对比表，写到标准输出（M7 报告 §7、§8 用）。只做摘抄和排版，不重新计数。

用法：python3 scripts/m7_version_table.py > out/m7/VERSIONS.md
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def blocks(path, section):
    """返回 {块名: [行...]}；section 是 '## 1' 这样的节头前缀。"""
    out, cur, on = {}, None, False
    for ln in open(path, encoding='utf8'):
        ln = ln.rstrip('\n')
        if ln.startswith('## '):
            on = ln.startswith(section + ' ')
            cur = None
            continue
        if not on:
            continue
        if ln.startswith('  ') and not ln.startswith('    '):
            name = ln.strip().split('：')[0].strip()
            cur = out.setdefault(name, [])
            cur.append(ln.strip())
        elif cur is not None:
            cur.append(ln.strip())
    return out


def pick(lines, pat, fmt, default='—'):
    for ln in lines or []:
        g = re.search(pat, ln)
        if g:
            return fmt.format(*g.groups())
    return default


def emit(title, cols, names, rows):
    print('### %s\n' % title)
    print('| 指标 | ' + ' | '.join(names) + ' |')
    print('| :-- |' + ' --: |' * len(cols))
    for lab, cells in rows:
        print('| ' + lab + ' | ' + ' | '.join(cells) + ' |')
    print()


def build(sec_p, sec_c, sec_base, sec_stack, cols, names, title, extra_rows=()):
    bp = os.path.join(ROOT, 'out', 'bundle_patterns.txt')
    bc = os.path.join(ROOT, 'out', 'bundle_cmdstream.txt')
    P = blocks(bp, sec_p)
    C = blocks(bc, sec_c)
    B = blocks(bp, sec_base) if sec_base else {}
    S = blocks(bp, sec_stack) if sec_stack else {}
    D = blocks(bc, '## 3')

    def key(d, c):
        for k in d:
            if k == c or k.startswith(c + '（') or k.replace(' ', '') == c.replace(' ', ''):
                return d[k]
        return None

    spec = [
        ('局数 / 号数（快照侧）', P, r'：(\d+) 局，号 (\d+) 个', '{0} / {1}'),
        ('主队赢 / 按「1 ÷ 队数」基准应赢', B, r'主队赢 (\d+) 局（(\d+%)）；按基准应赢 ([\d.]+) 局（(\d+%)）', '{0}（{1}）/ {2}（{3}）'),
        ('拆队后别的队里有号赢', B, r'拆队后别的队里有号赢 (\d+) 局', '{0}'),
        ('SPLIT：编队被拆进 ≥2 支队的局', P, r'SPLIT：(\d+) 局拆队（(\d+%)）', '{0}（{1}）'),
        ('LEFT：有提前离场的号的局 / 离场的号', P, r'LEFT：(\d+) 局有提前离场的号（(\d+%)），共 (\d+) 个', '{0}（{1}）/ {2}'),
        ('LAG180：各号时钟相差 ≥180 拍的局 / 可算的局', P, r'LAG180：可算的 (\d+) 局里 (\d+) 局有落后 ≥180 拍的号（(\d+%)）', '{1} / {0}（{2}）'),
        ('各局最大时钟差的中位（拍）', P, r'各局最大落后量的中位 (\d+) 拍', '{0}'),
        ('SPAWNGAP：想去的点到最近我方号 ÷ rCell（中位）', P, r'SPAWNGAP：可算的 \d+ 局，想去的点到最近我方号的距离 ÷ rCell 中位 ([\d.]+)', '{0}'),
        ('SHARE1530：1530 拍「占地 ÷ 人头」中位', P, r'SHARE1530：可算的 \d+ 局，「占地 ÷ 人头」中位 ([\d.]+)', '{0}'),
        ('1530 拍编队密度中位', P, r'编队密度中位 ([\d.]+)', '{0}'),
        ('SEALED：1500 拍后没有邻居也没有无主地的快照', P, r'SEALED：1500 拍后快照里没有邻居也没有无主地的 \d+ 行（(\d+%)）', '{0}'),
        ('OVER100：1500 拍后密度 ≥100 的快照', P, r'OVER100：1500 拍后快照 \d+ 行里密度 ≥100 的 \d+ 行（(\d+%)）', '{0}'),
        ('CAP150：有号顶在硬上限 ≥450 拍的局', P, r'CAP150：(\d+) 局有顶住 ≥450 拍的号（(\d+%)）', '{0}（{1}）'),
        ('REJ：调度 / 捐款行里标成被拒的', P, r'REJ：调度 / 捐款 (\d+) 行，likelyRejected (\d+) 行（(\d+%)）', '{1} / {0}（{2}）'),
        ('COLLAPSE：600 拍内出局 ≥ 一半号的局', P, r'COLLAPSE：(\d+) 局（(\d+%)）', '{0}（{1}）'),
        ('STACK70：90 拍内余额掉到 30% 以下的事件 / 其后 600 拍内出局', P, r'STACK70：.*?共 (\d+) 次.*?600 拍内出局 (\d+) 次（(\d+%)）', '{0} / {1}（{2}）'),
        ('　其中自己打出去的 / 其后 600 拍内出局', P, r'自己打出去的 (\d+) 次里 (\d+) 次（(\d+%)）', '{0} / {1}（{2}）'),
        ('　同局同拍对照：对数 / 其后 600 拍内出局', S, r'同局同拍对照 (\d+) 对里 (\d+) 对（(\d+%)）', '{0} / {1}（{2}）'),
        ('有完整录像的局 / 我方号 / 同局其他真人', C, r'有录像的 (\d+) 局；我方号 (\d+) 个、其他真人 (\d+) 个', '{0} / {1} / {2}'),
        ('BATCH3：同号同拍 ≥3 条的批占陆攻，我方', C, r'我方 BATCH3：陆攻 (\d+) 条，同号同拍 ≥3 条的批 (\d+) 个 / (\d+) 条（占陆攻 (\d+%)）', '{3}（{2} / {0} 条）'),
        ('　同局其他真人', C, r'其他真人 BATCH3：陆攻 (\d+) 条，同号同拍 ≥3 条的批 (\d+) 个 / (\d+) 条（占陆攻 (\d+%)）', '{3}（{2} / {0} 条）'),
        ('　600~1499 拍：我方 / 其他真人', C, r'600~1499 (\d+%) \| (\d+%)', '{0} / {1}'),
        ('　1500~2999 拍：我方 / 其他真人', C, r'1500~2999 (\d+%) \| (\d+%)', '{0} / {1}'),
        ('　3000 拍以后：我方 / 其他真人', C, r'3000\+ (\d+%) \| (\d+%)', '{0} / {1}'),
        ('　各局占比的中位（最小~最大）：我方', D, r'我方中位 (\d+%)（最小 (\d+%)，最大 (\d+%)', '{0}（{1}~{2}）'),
        ('REPEAT：打真人 / AI 的陆攻里的重复单，我方', C, r'我方 REPEAT：打真人 / 内置 AI 的陆攻 (\d+) 条，重复单 (\d+) 条（(\d+%)', '{2}（{1} / {0} 条）'),
        ('　同局其他真人', C, r'其他真人 REPEAT：打真人 / 内置 AI 的陆攻 (\d+) 条，重复单 (\d+) 条（(\d+%)', '{2}（{1} / {0} 条）'),
        ('SPAWN：每号落地的出生指令中位，我方 / 其他真人', C, None, None),
        ('DONLAND：调度发出 → 落地，2142 拍前', C, r'<2142 (\d+) → (\d+)（([\d%—]+)）', '{0} → {1}（{2}）'),
        ('　2142~3212 拍', C, r'2142~3212 (\d+) → (\d+)（([\d%—]+)）', '{0} → {1}（{2}）'),
        ('　3213~4283 拍', C, r'3213~4283 (\d+) → (\d+)（([\d%—]+)）', '{0} → {1}（{2}）'),
        ('　4284 拍以后', C, r'≥4284 (\d+) → (\d+)（([\d%—]+)）', '{0} → {1}（{2}）'),
    ]
    rows = []
    for lab, src, pat, fmt in spec:
        cells = []
        for c in cols:
            ls = key(src, c)
            if pat is None:
                a = pick(ls, r'我方 SPAWN：每号落地的出生指令中位 ([\d.]+) 条', '{0}')
                b = pick(ls, r'其他真人 SPAWN：每号落地的出生指令中位 ([\d.]+) 条', '{0}')
                cells.append('—' if a == '—' else '%s / %s' % (a, b))
            else:
                cells.append(pick(ls, pat, fmt))
        if any(x != '—' for x in cells):
            rows.append((lab, cells))
    emit(title, cols, names, rows)


def main():
    build('## 1', '## 1', '## 0', '## 3',
          ['squad10 Va', 'squad10 Vb', 'squad10 Vc', 'squad20 c110', 'squad8 g09', '全部'],
          ['Va（A001~A017）', 'Vb（A018~A095）', 'Vc（A097~A099）', 'c110（B 组）', 'g09（G 组）', '全部'],
          'V1 按版本：全量对局包上的机械计数（bundle_patterns.py 123 局；录像侧 bundle_cmdstream.py 99 局）')
    build('## 2', '## 2', None, '## 4',
          ['squad10 W', 'squad10 L', 'squad20 W', 'squad20 S', 'squad20 L', 'squad8 W', 'squad8 L'],
          ['squad10 赢', 'squad10 输', 'squad20 赢', 'squad20 拆队后别的队赢', 'squad20 输', 'squad8 赢', 'squad8 输'],
          'V2 按结果：同样的计数分到赢的局和输的局')
    print('两张表只是摘抄 `out/bundle_patterns.txt` 和 `out/bundle_cmdstream.txt` 的对应行。录像侧的行只算有完整录像的 99 局（squad8 没有录像，B 组 38 局里 24 局）。'
          '「主队」按对局卡的 primaryTeam；squad20 的「拆队后别的队赢」是编队被拆开后，赢的那支队里也有本方的号。')


if __name__ == '__main__':
    sys.exit(main())
