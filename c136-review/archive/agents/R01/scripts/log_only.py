#!/usr/bin/env python3
"""log_only.py — 只靠局内日志（in_game.log）做的事实表。用在“这批号所在的那个实例没有录像”的包上（A094 的 6 个号）。
用法：python3 log_only.py <matchId> [--bots a,b,..] [--section spawn|squad|idle|dispatch|results|drops|share|late|chain|all] [--every 90] [--t0 0 --t1 1e9]
  --bots 省略时 = 日志里有 [HL-GAME-INIT] 行的号。
输出 out/<matchId>/log_ticks.csv（每条 [HL-TICK]：t,bot,terr,bal,dens,nb,neut,cmds,boats,avgMs,maxMs,skip）和 log_squad.csv（每个快照拍的合计）。
各节：
  spawn    协调器求解次数（名单人数、间距下限）、每个号最后的计划位与角色
  squad    每个快照拍：有日志的号数、合计领土、占全图陆地 %、合计余额、密度
  idle     每个号连续的“cmds 不动”区间（至少 2 个快照间隔）：区间内 nb、neut 的取值范围，余额与密度的起止
  dispatch 每条 [HL-DISPATCH]：名义捐出 = floor(余额*(pct+1)/1024)，手续费 = floor(64*余额/1024)（引擎规则：手续费按捐出者整个余额收）；
           受赠者可收上限 = (150 - dAlly) * 受赠者领土（领土取最近一个快照，属估算）
  results  [RESULT] 行：阵亡/离场拍、当时各队领土
  share    --t0 指定的快照拍上各号的领土、余额占比（看兵堆在谁手里）
  late     发过指令的快照间隔：起止密度、进攻指令数（cmds 增量扣掉调度）、领土与余额变化；统计有多少进攻指令出在密度 >=95 的区间
  chain    调度是否到账：余额台阶按先发先到对回每条调度（本地拍；延迟大时调度会晚到、成批落地）
  drops    相邻两个快照之间余额下降超过 30% 的点，以及这段时间内该号的 cmds 增量和调度条数
日志的 t 是各客户端本地拍。没有录像，所以这里没有对手的任何数字。
"""
import argparse, csv, json, math, os, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
BUNDLES = '/agent/repos/c136-data/bundles'

TICK = re.compile(r'\[([a-z0-9_]+)\] \[HL-TICK\] t=(\d+) terr=(\d+)\([\d.]+%\) bal=(\d+) dens=([\d.]+) nb=(\d+) neut=(\d+) cmds=(\d+) boats=(\d+)(?: avgMs=([\d.]+) maxMs=([\d.]+) skip=(\d+))?')
DISP = re.compile(r'\[([a-z0-9_]+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\(\[APEX\] ([a-z0-9_]+)\) boxedIn=(\w+) myBal=(\d+) dMe=(\d+) dAlly=(\d+)')
INIT = re.compile(r'\[([a-z0-9_]+)\] \[HL-GAME-INIT\].*seeded=(\d+) me=(\d+)')
RES = re.compile(r'\[RESULT \[APEX\] ([a-z0-9_]+)\] result=(\w+) event=(\w+) place=(\d+) seeded=(\d+) aiBots=(\d+) alivePlayers=(\d+) peak=(\d+) team=(.*)$')


def load(mid, bots=None):
    ticks, disp, init, res = [], [], {}, {}
    with open(f'{BUNDLES}/{mid}/in_game.log', encoding='utf8') as f:
        for line in f:
            m = INIT.search(line)
            if m:
                init[m.group(1)] = {'seeded': int(m.group(2)), 'me': int(m.group(3))}
                continue
            m = TICK.search(line)
            if m:
                ticks.append({'bot': m.group(1), 't': int(m.group(2)), 'terr': int(m.group(3)), 'bal': int(m.group(4)), 'dens': float(m.group(5)),
                              'nb': int(m.group(6)), 'neut': int(m.group(7)), 'cmds': int(m.group(8)), 'boats': int(m.group(9)),
                              'avgMs': m.group(10) or '', 'maxMs': m.group(11) or '', 'skip': m.group(12) or ''})
                continue
            m = DISP.search(line)
            if m:
                disp.append({'bot': m.group(1), 't': int(m.group(2)), 'kind': m.group(3), 'pct': int(m.group(4)), 'ally': m.group(6),
                             'boxedIn': m.group(7), 'myBal': int(m.group(8)), 'dMe': int(m.group(9)), 'dAlly': int(m.group(10))})
                continue
            m = RES.search(line)
            if m:
                team = None
                try:
                    team = json.loads(m.group(9))
                except Exception:
                    pass
                res[m.group(1)] = {'result': m.group(2), 'event': m.group(3), 'place': int(m.group(4)), 'seeded': int(m.group(5)), 'aiBots': int(m.group(6)),
                                   'alivePlayers': int(m.group(7)), 'peak': int(m.group(8)), 'team': team}
    # 阵亡/离场拍在 results.csv
    rp = f'{BUNDLES}/{mid}/results.csv'
    if os.path.exists(rp):
        for r in csv.DictReader(open(rp, newline='')):
            if r['bot'] in res:
                res[r['bot']].update(tick=int(r['tick']), lastTerritory=int(r['lastTerritory'] or 0), balance=int(r['balance'] or 0), sent=int(r['sent'] or 0), accepted=int(r['accepted'] or 0))
    if bots is None:
        bots = sorted(init)
    bs = set(bots)
    global ALLTICKS
    ALLTICKS = ticks
    return [r for r in ticks if r['bot'] in bs], [d for d in disp if d['bot'] in bs], init, {b: v for b, v in res.items() if b in bs}, bots


ALLTICKS = []


def land_of(mid):
    return json.load(open(f'{BUNDLES}/{mid}/card.json'))['mapLand']


def squad_rows(ticks, land):
    by = defaultdict(list)
    for r in ticks:
        by[r['t']].append(r)
    out = []
    for t in sorted(by):
        rs = by[t]
        terr = sum(r['terr'] for r in rs); bal = sum(r['bal'] for r in rs)
        out.append({'t': t, 'n': len(rs), 'terr': terr, 'sharePct': round(100 * terr / land, 2), 'bal': bal, 'dens': round(bal / terr, 1) if terr else 0,
                    'nbMax': max(r['nb'] for r in rs), 'boxed': sum(1 for r in rs if r['nb'] == 0 and r['neut'] == 0)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mid'); ap.add_argument('--bots'); ap.add_argument('--section', default='all')
    ap.add_argument('--every', type=int, default=90); ap.add_argument('--t0', type=int, default=0); ap.add_argument('--t1', type=int, default=10**9)
    a = ap.parse_args()
    ticks, disp, init, res, bots = load(a.mid, a.bots.split(',') if a.bots else None)
    land = land_of(a.mid)
    os.makedirs(os.path.join(OUT, a.mid), exist_ok=True)
    with open(os.path.join(OUT, a.mid, 'log_ticks.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['t', 'bot', 'terr', 'bal', 'dens', 'nb', 'neut', 'cmds', 'boats', 'avgMs', 'maxMs', 'skip'])
        w.writeheader(); w.writerows(sorted(ticks, key=lambda r: (r['t'], r['bot'])))
    sq = squad_rows(ticks, land)
    with open(os.path.join(OUT, a.mid, 'log_squad.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['t', 'n', 'terr', 'sharePct', 'bal', 'dens', 'nbMax', 'boxed'])
        w.writeheader(); w.writerows(sq)
    sec = a.section
    inwin = lambda t: a.t0 <= t <= a.t1
    print(f'# {a.mid} 仅日志：号 {",".join(bots)}；陆地 {land}；HL-TICK {len(ticks)} 行，HL-DISPATCH {len(disp)} 行')
    if sec in ('squad', 'all'):
        print('== squad（t 号数 领土 占比% 余额 密度 无邻无中立的号数）')
        peak = max(sq, key=lambda r: r['terr']); pb = max(sq, key=lambda r: r['bal'])
        for r in sq:
            if inwin(r['t']) and r['t'] % a.every == 0:
                print(f"  {r['t']:>5} {r['n']} {r['terr']:>7} {r['sharePct']:>5} {r['bal']:>9} {r['dens']:>6} {r['boxed']}")
        print(f"  领土峰值 t={peak['t']} {peak['terr']} 格 {peak['sharePct']}%；余额峰值 t={pb['t']} {pb['bal']}")
    by = defaultdict(list)
    for r in sorted(ticks, key=lambda r: r['t']):
        by[r['bot']].append(r)
    if sec in ('idle', 'all'):
        print('== idle（cmds 连续不动的区间，≥2 个快照间隔）')
        for b in bots:
            rs = by[b]; i = 0
            while i < len(rs) - 1:
                j = i
                while j + 1 < len(rs) and rs[j + 1]['cmds'] == rs[i]['cmds']:
                    j += 1
                if j - i >= 2 and inwin(rs[i]['t']):
                    seg = rs[i:j + 1]
                    nbs = sorted({r['nb'] for r in seg}); nts = sorted({r['neut'] for r in seg}); tr = sorted({r['terr'] for r in seg})
                    print(f"  {b:<8} {seg[0]['t']:>5}–{seg[-1]['t']:<5} {seg[-1]['t'] - seg[0]['t']:>5} 拍 cmds={seg[0]['cmds']} nb={nbs[0]}..{nbs[-1]} neut={nts[0]}..{nts[-1]} "
                          f"领土 {tr[0]}..{tr[-1]} 余额 {seg[0]['bal']}→{seg[-1]['bal']} 密度 {seg[0]['dens']}→{seg[-1]['dens']}")
                i = max(j, i + 1)
        print('  各号 cmds 增量（按 900 拍窗口）：')
        for b in bots:
            rs = by[b]; cells = []
            for w0 in range(0, (rs[-1]['t'] // 900 + 1) * 900, 900):
                seg = [r for r in rs if w0 <= r['t'] <= w0 + 900]
                if len(seg) >= 2:
                    cells.append(f"{w0}:{seg[-1]['cmds'] - seg[0]['cmds']}")
            print(f"  {b:<8} " + ' '.join(cells))
    if sec in ('dispatch', 'all'):
        print('== dispatch（t 号 类型 pct →受赠者 余额 名义捐出 手续费 dMe dAlly 受赠者领土(最近快照) 可收上限(估) 能送到(估)）')
        tot = defaultdict(lambda: [0, 0, 0, 0]); clip = [0, 0, 0, 0]
        for d in disp:
            if not inwin(d['t']):
                continue
            nominal = d['myBal'] * (d['pct'] + 1) // 1024; fee = 64 * d['myBal'] // 1024
            ars = [r for r in ALLTICKS if r['bot'] == d['ally']]
            near = min(ars, key=lambda r: abs(r['t'] - d['t'])) if ars else None
            room = max(0, (150 - d['dAlly'])) * near['terr'] if near else None
            got = min(nominal, room) if room is not None else None
            print(f"  {d['t']:>5} {d['bot']:<7} {d['kind']:<18} {d['pct']:>3} →{d['ally']:<7} {d['myBal']:>9} {nominal:>8} {fee:>7} {d['dMe']:>3} {d['dAlly']:>3} "
                  f"{near['terr'] if near else '?':>6} {room if room is not None else '?':>8} {got if got is not None else '?':>8}")
            x = tot[d['bot']]; x[0] += 1; x[1] += nominal; x[2] += fee; x[3] += got or 0
            if room is not None and room < nominal:
                clip[0] += 1; clip[1] += nominal; clip[2] += got; clip[3] += fee
        for b, x in tot.items():
            print(f"  合计 {b:<7} {x[0]} 条 名义 {x[1]} 手续费 {x[2]} 能送到(估) {x[3]}")
        print(f"  合计 全部 {sum(x[0] for x in tot.values())} 条 名义 {sum(x[1] for x in tot.values())} 手续费 {sum(x[2] for x in tot.values())} 能送到(估) {sum(x[3] for x in tot.values())}")
        if clip[0]:
            print(f"  其中名义捐出超过受赠者可收上限的 {clip[0]} 笔：名义 {clip[1]}，能送到(估) {clip[2]}，手续费 {clip[3]}（手续费不随截断减少）")
        if a.t0 > 0 or a.t1 < 10**9:
            s0 = min(sq, key=lambda r: abs(r['t'] - a.t0)); s1 = min(sq, key=lambda r: abs(r['t'] - a.t1))
            fees = sum(x[2] for x in tot.values()); net = s1['bal'] - s0['bal']
            print(f"  编队余额 t={s0['t']} {s0['bal']} → t={s1['t']} {s1['bal']}（净变化 {net}）；区间内手续费 {fees}" + (f"，相当于净减少量的 {100 * fees / -net:.1f}%" if net < 0 else ''))
    if sec in ('results', 'all'):
        print('== results（号 结果 拍 最后领土 峰值 余额 存活玩家 各队领土）')
        for b, r in sorted(res.items(), key=lambda kv: kv[1].get('tick', 0)):
            tt = r['team']['totals'] if r.get('team') else None
            share = ' '.join(f"T{k}:{v}({100 * v / land:.1f}%)" for k, v in tt.items()) if tt else ''
            if tt:
                share += f" 未归属:{land - sum(tt.values())}"
            print(f"  {b:<8} {r['event']:<5} t={r.get('tick', '?'):>5} last={r.get('lastTerritory', '?'):>6} peak={r['peak']:>6} bal={r.get('balance', '?'):>8} alive={r['alivePlayers']:>3} "
                  f"sent={r.get('sent', '?')} accepted={r.get('accepted', '?')} mine={r['team']['mine'] if r.get('team') else '-'} {share}")
    if sec in ('share',):
        # --t0 指定的那个快照拍：各号领土/余额及占合计的比例，nb=0 的号单独合计
        t = min({r['t'] for r in ticks}, key=lambda x: abs(x - a.t0))
        rs = [r for r in ticks if r['t'] == t]
        T = sum(r['terr'] for r in rs); B = sum(r['bal'] for r in rs)
        print(f'== share t={t}：合计 {T} 格（{100 * T / land:.1f}%） {B} 兵')
        for r in sorted(rs, key=lambda r: -r['bal']):
            print(f"  {r['bot']:<8} 领土 {r['terr']:>7} ({100 * r['terr'] / T:4.1f}%) 余额 {r['bal']:>9} ({100 * r['bal'] / B:4.1f}%) 密度 {r['dens']:>6} nb={r['nb']} neut={r['neut']} cmds={r['cmds']}")
        z = [r for r in rs if r['nb'] == 0]
        print(f"  nb=0 的号 {len(z)} 个：领土 {sum(r['terr'] for r in z)} ({100 * sum(r['terr'] for r in z) / T:.1f}%) 余额 {sum(r['bal'] for r in z)} ({100 * sum(r['bal'] for r in z) / B:.1f}%)")
    if sec in ('late',):
        # 快照间隔里发了指令的区间：起止密度、指令增量（扣掉调度）、领土和余额变化
        print('== late（发过指令的快照间隔：号 t0→t1 密度起→止 进攻指令数 调度数 领土变化 余额变化）')
        tot = [0, 0]
        for b in bots:
            rs = by[b]; n = [0, 0, 0, 0]
            for x, y in zip(rs, rs[1:]):
                if not (inwin(x['t']) and inwin(y['t'])) or y['cmds'] == x['cmds']:
                    continue
                # 快照行在当拍决策之前打出：t 拍发的调度记在 [t, 下一个快照) 这一格的 cmds 增量里
                nd = sum(1 for d in disp if d['bot'] == b and x['t'] <= d['t'] < y['t'])
                na = y['cmds'] - x['cmds'] - nd
                hi = max(x['dens'], y['dens']) >= 95
                # 余额按上一格的涨幅外推，这一格内能不能越过 100 倍领土（over 分支的触发线）
                k = rs.index(x); g = x['bal'] - rs[k - 1]['bal'] if k else 0
                cross = x['bal'] > 100 * x['terr'] or (g > 0 and x['bal'] + g * (y['t'] - x['t']) / max(1, x['t'] - rs[k - 1]['t']) > 100 * x['terr'])
                if na > 0:
                    n[0] += na; n[1] += na if hi else 0; n[2] += 1; n[3] += 1 if cross else 0
                print(f"  {b:<8} {x['t']:>5}→{y['t']:<5} 密度 {x['dens']:>6}→{y['dens']:<6} 进攻 {na} 调度 {nd} 领土 {y['terr'] - x['terr']:+d} 余额 {y['bal'] - x['bal']:+d} nb={x['nb']}→{y['nb']}{' *' if hi and na > 0 else ''}{' 过线' if cross and na > 0 else ''}")
            print(f"  {b:<8} 小计：进攻指令 {n[0]} 条，其中所在区间起点或终点密度 >=95 的 {n[1]} 条；有进攻指令的区间 {n[2]} 个，其中按上一格涨幅外推、区间内余额能越过 100 倍领土的 {n[3]} 个")
            tot[0] += n[0]; tot[1] += n[1]
        nd = sum(max(0, (min(a.t1, by[b][-1]['t']) - max(a.t0, by[b][0]['t'])) // 5) for b in bots if by[b])
        print(f"  合计：进攻指令 {tot[0]} 条，其中密度 >=95 的区间里 {tot[1]} 条（{100 * tot[1] / max(1, tot[0]):.1f}%）；窗口内各号决策拍合计约 {nd} 个（每 5 拍一个）")
    if sec in ('chain',):
        # 调度有没有到账：把 [HL-TICK] 的余额和 [HL-DISPATCH] 的 myBal 按本地拍排成一列观测值，相邻两次观测之间余额掉了 >=20% 时，
        # 按先发先到找“落地了几条”：每条落地后余额乘 1 - (pct+1)/1024 - 64/1024（受赠者没顶上限时）。只适用于没有进攻支出的号（nb=0）。
        print('== chain（号 观测拍 来源 余额 | 相邻观测间按先发先到推出的落地条数、预测余额/实际余额）')
        for b in bots:
            ds = [d for d in disp if d['bot'] == b and inwin(d['t'])]
            if not ds:
                continue
            t0 = ds[0]['t']; t1 = max(a.t1 if a.t1 < 10**9 else 0, ds[-1]['t'] + 400)
            obs = [(r['t'], 'TICK', r['bal']) for r in by[b] if t0 - 90 <= r['t'] <= t1] + [(d['t'], 'DISP pct=%d' % d['pct'], d['myBal']) for d in ds]
            obs.sort(key=lambda o: (o[0], o[1] != 'TICK'))
            q = []; landed = 0; clipn = [0] * 9
            for i, o in enumerate(obs):
                line = f"  {b:<8} {o[0]:>5} {o[1]:<13} {o[2]:>9}"
                if i:
                    p = obs[i - 1]
                    if o[2] <= 0.8 * p[2] and q:
                        # 捐款之外没有别的支出时，实际余额只会比预测高（利息），所以取“预测 <= 实际”的最小条数
                        best = None; pred = p[2]
                        for k in range(1, len(q) + 1):
                            pred = pred * (1 - (q[k - 1]['pct'] + 1) / 1024 - 64 / 1024)
                            best = (0, k, pred)
                            if pred <= 1.03 * o[2]:
                                break
                        line += f" | 落地 {best[1]} 条（预测 {best[2]:.0f}，实际/预测 {o[2] / best[2]:.2f}）"
                        landed += best[1]; q = q[best[1]:]
                if o[1] != 'TICK':
                    d = next(d for d in ds if d['t'] == o[0])
                    q.append(d)
                    # 这条调度到下一次观测之间的余额差，扣掉手续费，就是到账额的下界（期间只有利息进账、没有别的支出时）；
                    # 上界再加上按最近一个“没发指令的快照间隔”的相对涨幅估的利息
                    later = [x for x in obs[i + 1:] if 20 <= x[0] - o[0] <= 95]
                    if later:
                        nx = later[0]; fee = 64 * d['myBal'] // 1024; nominal = d['myBal'] * (d['pct'] + 1) // 1024
                        ref = [(y['bal'] - x['bal']) / ((y['t'] - x['t']) * x['bal']) for x, y in zip(by[b], by[b][1:])
                               if y['t'] <= o[0] and y['cmds'] == x['cmds'] and y['bal'] > x['bal'] and x['bal'] > 0]
                        inc = int(ref[-1] * d['myBal'] * (nx[0] - o[0])) if ref else 0
                        lo = max(0, d['myBal'] - nx[2] - fee)
                        hi = min(nominal, max(0, d['myBal'] - nx[2] - fee + inc))
                        line += f" | 名义 {nominal} 手续费 {fee}；到 {nx[0]} 拍余额差推出到账 {lo}..{hi}（名义的 {100 * lo / nominal:.0f}%..{100 * hi / nominal:.0f}%）"
                        clipn[0] += 1; clipn[1] += nominal; clipn[2] += lo; clipn[3] += hi; clipn[4] += fee
                        if hi < 0.9 * nominal:
                            clipn[5] += 1; clipn[6] += nominal; clipn[7] += hi; clipn[8] += fee
                print(line)
            print(f"  {b:<8} 发出 {len(ds)} 条调度，按余额台阶推出落地 {landed} 条，观测窗口结束时还没看到落地的 {len(q)} 条")
            if clipn[0]:
                print(f"  {b:<8} 能用后一次观测估到账额的 {clipn[0]} 笔：名义 {clipn[1]}，到账 {clipn[2]}..{clipn[3]}，手续费 {clipn[4]}；其中到账上界不到名义 90% 的 {clipn[5]} 笔：名义 {clipn[6]}，到账至多 {clipn[7]}，手续费 {clipn[8]}")
    if sec in ('spawn', 'all'):
        # 协调器日志：每次求解的名单人数与间距下限；每个号最后一条 [HL-SPAWN-BACKEND]（计划位、角色、最近队友距离）；有没有 [HL-GAME-INIT]（seeded、席位）
        solves = defaultdict(int); names = set(); plan = {}; first = {}
        for line in open(f'{BUNDLES}/{a.mid}/in_game.log', encoding='utf8'):
            m = re.search(r'\[BACKEND-SPAWN-COORD\] Solved (\d+) bots .*minSep=(\d+)px, boss=(\w+)\): (.*)$', line)
            if m:
                solves[(int(m.group(1)), int(m.group(2)), m.group(3))] += 1
                names |= set(re.findall(r'\[APEX\] ([a-z0-9_]+)\(', m.group(4)))
                continue
            m = re.search(r'\[([a-z0-9_]+)\] \[HL-SPAWN-BACKEND\] me=(\d+) slot=(\d+) role=(\w+) -> \((\d+),(\d+)\) bossDist=(-?\d+) minAllyDist=(\d+)', line)
            if m:
                plan[m.group(1)] = {'me': int(m.group(2)), 'slot': int(m.group(3)), 'role': m.group(4), 'x': int(m.group(5)), 'y': int(m.group(6)), 'minAlly': int(m.group(8))}
                first.setdefault(m.group(1), 0); first[m.group(1)] += 1
        print('== spawn（协调器求解：名单人数/间距下限/boss → 次数）')
        for k, v in sorted(solves.items()):
            print(f"  名单 {k[0]} 人 minSep={k[1]} boss={k[2]}：{v} 次")
        print(f"  名单里出现过的名字 {len(names)} 个：{','.join(sorted(names))}；其中日志里没有任何 [HL-SPAWN-BACKEND] 行的：{','.join(sorted(names - set(plan))) or '无'}")
        for b, v in sorted(plan.items(), key=lambda kv: kv[1]['me']):
            ini = init.get(b)
            print(f"  {b:<8} 席位 {v['me']:>2} {'seeded=' + str(ini['seeded']) if ini else '无 GAME-INIT 行'} slot={v['slot']} {v['role']:<18} 计划位 ({v['x']},{v['y']}) 最近队友 {v['minAlly']}（共 {first[b]} 条排位行）")
        ma = [v['minAlly'] for v in plan.values()]
        print(f"  最近队友距离 {min(ma)}–{max(ma)}")
    if sec in ('drops', 'all'):
        print('== drops（相邻快照余额下降 >=30%：号 t0→t1 余额 领土变化 cmds 增量 期间调度条数 归类）')
        print('   归类只看日志能看到的特征：调度 = 区间内有本号的 HL-DISPATCH；挨打 = 领土减少 >=3%；积压落地 = 区间内 cmds 没动、领土没少（花掉的兵来自更早发出的指令）；进攻 = 其余')
        cnt = defaultdict(lambda: [0, 0])
        for b in bots:
            rs = by[b]
            for x, y in zip(rs, rs[1:]):
                if inwin(y['t']) and x['bal'] > 0 and y['bal'] <= 0.7 * x['bal']:
                    nd = sum(1 for d in disp if d['bot'] == b and x['t'] <= d['t'] < y['t'])
                    lab = '调度' if nd else '挨打' if y['terr'] < 0.97 * x['terr'] else '积压落地' if y['cmds'] == x['cmds'] else '进攻'
                    cnt[lab][0] += 1; cnt[lab][1] += x['bal'] - y['bal']
                    print(f"  {b:<8} {x['t']:>5}→{y['t']:<5} {x['bal']:>9}→{y['bal']:<9} ({100 * (y['bal'] - x['bal']) / x['bal']:.0f}%) 领土 {x['terr']}→{y['terr']} cmds +{y['cmds'] - x['cmds']} 调度 {nd} {lab}")
        print('  归类合计：' + '；'.join(f'{k} {v[0]} 次（余额共少 {v[1]}）' for k, v in sorted(cnt.items(), key=lambda kv: -kv[1][0])))


if __name__ == '__main__':
    main()
