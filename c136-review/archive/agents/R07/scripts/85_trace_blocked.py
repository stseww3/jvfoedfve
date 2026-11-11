#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""85_trace_blocked.py — 从影子决策明细里数「目标便宜、却被留底挡住」的决策拍。R07

用法（在 scripts/ 目录下）：
    python3 85_trace_blocked.py <matchId> <号:t0:t1> [<号:t0:t1> ...] [--dens 10] [--any]

输入：out/<matchId>/shadow_trace_<号>_<t0>_<t1>.txt（65_shadow.mjs --trace 号:t0:t1 的输出，不带抽样间隔，每个决策拍一段）。
口径：一个决策拍算「便宜目标被留底挡住」，要同时满足
    ① 报价单里排第一的目标是真人；
    ② 它的每格成本 c 低于自己的出价 worth（不是嫌贵）；
    ③ 它当拍的密度（余额 ÷ 领土）不超过 --dens（默认 10）；
    ④ 这一行的结论是「无可用(avail<=0)」，且本拍没有指令。
按目标分组，列出拍数、拍号范围、自己的余额 / 密度、目标的领土 / 余额、c、need、safe、safe ÷ 自己的领土、avail 的范围，
以及这一组之后第一条打它的影子指令。
--any：条件 ① 放宽成「报价单里任意一条真人报价」（取每拍第一条满足 ②③④ 的）。用在排第一的是内置 AI、
    后面跟着便宜真人的情形（留底同一个数，两条报价一起被挡）。输出文件名加 _any，不覆盖默认口径的输出。
输出：out/<matchId>/trace_blocked_<号>_<t0>_<t1>.txt（--any 时 trace_blocked_any_<号>_<t0>_<t1>.txt）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

HEAD = re.compile(r'^t=(\d+) (\S+) B=(-?\d+) L=(\d+) d=([\d.]+).*?worth=([\d.]+).*?over=(\d)')
OFFER = re.compile(r'^\s+→ (.+?) terr=(\d+) bal=(-?\d+) dq=([\d.]+).*?\| c=([\d.]+).*?need=(-?\d+)(.*?)\| safe=(-?\d+) keep=(\S+) avail=(\S+)(.*)$')


def fmt(x):
    return f"{int(round(x)):,}"


def rng(xs, f=fmt):
    return f"{f(min(xs))}~{f(max(xs))}"


def parse(path):
    ticks = []
    cur = None
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            m = HEAD.match(line)
            if m:
                cur = {'t': int(m.group(1)), 'B': int(m.group(3)), 'L': int(m.group(4)), 'd': float(m.group(5)),
                       'worth': float(m.group(6)), 'over': int(m.group(7)), 'offers': [], 'cmd': None}
                ticks.append(cur)
                continue
            if cur is None:
                continue
            m = OFFER.match(line.rstrip('\n'))
            if m:
                avail = m.group(10)
                cur['offers'].append({'name': m.group(1), 'terr': int(m.group(2)), 'bal': int(m.group(3)), 'dq': float(m.group(4)),
                                      'c': float(m.group(5)), 'need': int(m.group(6)), 'flags': m.group(7), 'safe': int(m.group(8)),
                                      'avail': None if 'Inf' in avail else int(avail), 'tail': m.group(11)})
                continue
            s = line.strip()
            if s.startswith('⇒'):
                cur['cmd'] = s
    return ticks


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    mid = args[0]
    dens = 10.0
    any_offer = False
    specs = []
    i = 1
    while i < len(args):
        if args[i] == '--dens':
            dens = float(args[i + 1]); i += 2
        elif args[i] == '--any':
            any_offer = True; i += 1
        else:
            specs.append(args[i]); i += 1
    out_dir = os.path.join(HERE, '..', 'out', mid)
    for spec in specs:
        bot, t0, t1 = spec.split(':')[:3]
        path = os.path.join(out_dir, f'shadow_trace_{bot}_{t0}_{t1}.txt')
        ticks = parse(path)
        L = [f'# {mid} {bot} t={t0}~{t1}：便宜目标被留底挡住的决策拍（85_trace_blocked.py；输入 shadow_trace_{bot}_{t0}_{t1}.txt，共 {len(ticks)} 个决策拍）',
             f"# 口径：{'报价单里任意一条' if any_offer else '排第一的报价是'}真人{'报价' if any_offer else ''}、c < worth、对方密度 ≤ {dens:g}、结论是「无可用(avail<=0)」、本拍没有指令"]
        groups = {}
        for k in ticks:
            if not k['offers']:
                continue
            if k['cmd'] and '没有指令' not in k['cmd']:
                continue
            for o in (k['offers'] if any_offer else k['offers'][:1]):
                if ' 人' not in o['flags'] and '人 ' not in o['flags']:
                    continue
                if not (o['c'] < k['worth'] and o['dq'] <= dens and '无可用' in o['tail'] and o['avail'] is not None):
                    continue
                groups.setdefault(o['name'], []).append((k, o))
                break
        if not groups:
            L.append('没有这样的决策拍')
        for name, rows in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            ks = [k for k, _ in rows]
            os_ = [o for _, o in rows]
            L.append('')
            L.append(f"## 目标 {name}：{len(rows)} 个决策拍（t={ks[0]['t']}~{ks[-1]['t']}）")
            L.append(f"   自己：余额 {rng([k['B'] for k in ks])}，领土 {rng([k['L'] for k in ks])}，密度 {min(k['d'] for k in ks):.1f}~{max(k['d'] for k in ks):.1f}，出价 worth {min(k['worth'] for k in ks):.1f}~{max(k['worth'] for k in ks):.1f}")
            L.append(f"   目标：领土 {rng([o['terr'] for o in os_])}，余额 {rng([o['bal'] for o in os_])}，密度 {min(o['dq'] for o in os_):.1f}~{max(o['dq'] for o in os_):.1f}，每格成本 c {min(o['c'] for o in os_):.1f}~{max(o['c'] for o in os_):.1f}，吃光要的兵 need {rng([o['need'] for o in os_])}")
            ratio = [o['safe'] / max(1, k['L']) for k, o in rows]
            L.append(f"   留底：safe {rng([o['safe'] for o in os_])}（safe ÷ 自己的领土 = {min(ratio):.1f}~{max(ratio):.1f}），可用兵 avail {rng([o['avail'] for o in os_])}")
            flags = {}
            for o in os_:
                for f in ('nearCollapse', 'bleeding', 'onMe'):
                    if f in o['flags']:
                        flags[f] = flags.get(f, 0) + 1
            L.append('   报价标记：' + ('、'.join(f'{k} {v} 拍' for k, v in flags.items()) or '无'))
            after = [k for k in ticks if k['t'] > ks[-1]['t'] and k['cmd'] and name.split('#')[0] in k['cmd'] and '影子指令' in k['cmd']]
            if after:
                k = after[0]
                L.append(f"   之后第一条打它的影子指令：t={k['t']}（余额 {fmt(k['B'])}，密度 {k['d']:.1f}，over={k['over']}）{k['cmd'][:120]}")
            else:
                L.append('   之后区间内没有打它的影子指令')
            for k, o in rows[::max(1, len(rows) // 6)]:
                L.append(f"     t={k['t']} B={fmt(k['B'])} L={fmt(k['L'])} d={k['d']:.1f} worth={k['worth']:.1f} | 目标 {fmt(o['terr'])} 格 / {fmt(o['bal'])} 兵 c={o['c']:.1f} need={fmt(o['need'])} | safe={fmt(o['safe'])} avail={fmt(o['avail'])}")
        out = os.path.join(out_dir, f"trace_blocked_{'any_' if any_offer else ''}{bot}_{t0}_{t1}.txt")
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(L) + '\n')
        print('\n'.join(L))


if __name__ == '__main__':
    main()
