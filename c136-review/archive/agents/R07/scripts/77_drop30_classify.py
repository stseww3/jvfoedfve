#!/usr/bin/env python3
"""77_drop30_classify.py — R07：把 67_troop_flow.mjs 对好账的 DROP30 窗口按「最大的一项流出」分类。

输入：out/<mid>/drop30_recon.txt（每行一个窗口：进攻(兵+费) / 捐出(到账+费) / 发船(兵+费) / 挨打掉，全部是引擎重演的整数）
分类：一个窗口里四项流出谁最大就归谁（进攻再按最大的目标分：真人 / 内置 AI / 无主地）。
输出：out/<mid>/drop30_class.txt（按类别的条数、流出合计；t<1500 与 t>=1500 分开；逐条一行）

用法：python3 77_drop30_classify.py <matchId>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def num(s):
    return int(s.replace(',', ''))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    out = os.path.join(HERE, '..', 'out', mid)
    rows = []
    for ln in open(os.path.join(out, 'drop30_recon.txt'), encoding='utf-8'):
        m = re.match(r'^(\w+)@(\d+)~(\d+)\t([\d,]+)→([\d,]+)，领土 ([\d,]+)→([\d,]+)：(.*)$', ln.rstrip('\n'))
        if not m:
            continue
        bot, t0, t1, b0, b1, l0, l1, rest = m.groups()
        flows = {'进攻': 0, '捐出': 0, '发船': 0, '挨打': 0}
        tgt = ''
        a = re.search(r'进攻 (\d+) 条共 ([\d,]+) 兵 \+ 费 ([\d,]+)（([^）]*)）', rest)
        if a:
            flows['进攻'] = num(a.group(2)) + num(a.group(3))
            first = a.group(4).split('、')[0]
            tgt = '无主地' if first.startswith('无主地') else '内置 AI' if first.startswith('AI#') else '真人'
        dn = re.search(r'捐出 (\d+) 笔到账 ([\d,]+) \+ 费 ([\d,]+)', rest)
        if dn:
            flows['捐出'] = num(dn.group(2)) + num(dn.group(3))
        bt = re.search(r'发船 (\d+) 条带兵 ([\d,]+) \+ 费 ([\d,]+)', rest)
        if bt:
            flows['发船'] = num(bt.group(2)) + num(bt.group(3))
        h = re.search(r'挨打掉 ([\d,]+) 兵', rest)
        if h:
            flows['挨打'] = num(h.group(1))
        top = max(flows, key=lambda k: flows[k])
        cls = '说不清' if flows[top] == 0 else (f'自己进攻（打{tgt}）' if top == '进攻' else '捐给队友' if top == '捐出' else '发船' if top == '发船' else '挨打掉兵')
        rows.append({'bot': bot, 't0': int(t0), 't1': int(t1), 'b0': num(b0), 'b1': num(b1), 'l0': num(l0), 'l1': num(l1), 'cls': cls, 'flows': flows})
    L = []
    P = L.append
    P(f'# {mid} DROP30 分类（{len(rows)} 条；按窗口里最大的一项流出归类；数字来自 drop30_recon.txt）')
    for name, sel in (('全部', rows), ('t<1500', [r for r in rows if r['t0'] < 1500]), ('t>=1500', [r for r in rows if r['t0'] >= 1500])):
        P(f'\n{name}：{len(sel)} 条')
        cats = {}
        for r in sel:
            c = cats.setdefault(r['cls'], [0, 0, 0, 0])
            c[0] += 1
            c[1] += r['b0'] - r['b1']
            c[2] += r['flows']['进攻'] + r['flows']['捐出'] + r['flows']['发船'] + r['flows']['挨打']
            c[3] += r['l1'] - r['l0']
        for k, c in sorted(cats.items(), key=lambda kv: -kv[1][0]):
            P(f"  {k}：{c[0]} 条（{100 * c[0] / max(1, len(sel)):.1f}%），余额净跌合计 {c[1]:,}，四项流出合计 {c[2]:,}，窗口内领土合计 {c[3]:+,}")
    P('\n逐条：号@窗口 | 类别 | 余额 | 领土 | 进攻 / 捐出 / 发船 / 挨打')
    for r in sorted(rows, key=lambda r: r['t0']):
        f = r['flows']
        P(f"  {r['bot']}@{r['t0']}~{r['t1']} | {r['cls']} | {r['b0']:,}→{r['b1']:,} | {r['l0']:,}→{r['l1']:,} | {f['进攻']:,} / {f['捐出']:,} / {f['发船']:,} / {f['挨打']:,}")
    open(os.path.join(out, 'drop30_class.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L[:24]))


if __name__ == '__main__':
    main()
