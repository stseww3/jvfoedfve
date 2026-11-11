#!/usr/bin/env python3
"""donation_ledger.py — 逐笔捐款对账：名义捐额、6.25% 余额税、估算的实际到账。
引擎公式（engine-evidence.txt / live_game_js.js rD、a6a、gy、aMi）：
  税 fee = floor(64*B/1024)；名义额 v = min(floor(B*(pct+1)/1024), B-fee)；
  实际到账 X = min(v, 受赠者余量)，余量 = min(150*terr_R - bal_R, 1.5e9 - bal_R)；X<1 整笔作废（不扣税、不进录像）；
  X>=1 时捐出方仍按“全额余额”扣 fee —— 受赠者快满时，捐出方付满额税却只送出零头。
  利息：每 t%10==9，r = 100+isqrt(25600*i/508)，i=floor(511*terr/land)；B>100*terr 时 r -= floor(2r(B-cap)/cap)，夹 0..700；
        入账 max(floor(r*B/1e4),1) 且不超过 150*terr；领土收入：每 t%100==99 加 terr。
估算法：捐出方在两次“观测点”（HL-DISPATCH 的 myBal@t，或 HL-TICK 的 bal@t）之间只有这一笔捐款、
        且没有陆攻/收款/领土变化时，按上面公式逐拍推进，二分求 X 使推算余额 = 下一个观测点余额。
        窗口不干净（有陆攻、领土变了、窗口里多笔捐款）的标 dirty，不给估算值。
用法: python3 donation_ledger.py <matchId> [--replay <otherMatchId>]   （先跑 lag_probe.py）
输出: out/<matchId>/donation_ledger.csv + 汇总
"""
import csv, json, math, os, sys, collections
mid = sys.argv[1]
rmid = mid
for i, a in enumerate(sys.argv):
    if a == '--replay': rmid = sys.argv[i + 1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out', mid)
ROUT = os.path.join(HERE, '..', 'out', rmid)
B = f'/agent/repos/c136-data/bundles/{mid}'
card = json.load(open(os.path.join(B, 'card.json')))
LAND = card['mapLand']
def isqrt_e(h):
    if h < 1: return 0
    a = (h + 1) // 2
    for _ in range(9):
        a = (a + h // a) // 2
    return a
TABLE = [100 + isqrt_e((25600 * i) // 508) for i in range(512)]
def rate(t, terr, bal):
    r = TABLE[min(511, (511 * terr) // LAND)]
    if t < 1920:
        r = max((100 * (13440 - 6 * t)) // 1920, r)
    cap = min(100 * terr, 10 ** 9)
    if bal > cap and cap > 0:
        r -= (2 * r * (bal - cap)) // cap
    return min(max(r, 0), 700)
def gain(bal, terr, g):
    g = min(g, terr * 150 - bal, int(1.5e9) - bal)
    return bal + max(g, 0)
def step_to(bal, terr, t0, t1, don=None):
    """advance from state at tick t0 (before tick t0's updates) to tick t1; don=(T,pct,X) applied at tick T before that tick's income"""
    fee = 0
    for t in range(t0, t1):
        if don and t == don[0]:
            fee = (64 * bal) // 1024
            v = min((bal * (don[1] + 1)) // 1024, bal - fee)
            x = min(v, don[2])
            bal = bal - fee - x
        if t % 10 == 9:
            bal = gain(bal, terr, max((rate(t, terr, bal) * bal) // 10000, 1))
        if t % 100 == 99:
            bal = gain(bal, terr, terr)
    return bal, fee
rows = list(csv.DictReader(open(os.path.join(OUT, 'lag_probe.csv'))))
disp = [r for r in rows if r['kind'] != 'OPENING']
traj = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(B, 'traj.csv'))):
    traj[r['bot']].append((int(r['t']), int(r['bal']), int(r['terr'])))
rep = list(csv.DictReader(open(os.path.join(ROUT, 'replay_cmds.csv'))))
me = {}
for line in open(os.path.join(B, 'in_game.log'), errors='replace'):
    if '[HL-GAME-INIT]' in line:
        bot = line.split('\t', 1)[1].split(']')[0].strip('[')
        me[bot] = int(line.rsplit('me=', 1)[1].split()[0])
out = []
for bot in sorted(set(r['bot'] for r in disp)):
    pid = me[bot]
    ds = sorted([r for r in disp if r['bot'] == bot], key=lambda r: int(r['t']))
    obs = sorted(traj[bot])
    my_atk = sorted(int(r['tick']) for r in rep if int(r['player']) == pid and r['kind'] in ('attack', 'boat'))
    my_rcv = sorted(int(r['tick']) for r in rep if r['kind'] == 'donate' and int(r['dZ']) == pid)
    for k, r in enumerate(ds):
        t = int(r['t']); Bal = int(r['myBal']) if r['myBal'] else None; pct = int(r['pct'])
        if Bal is None:
            continue
        fee = (64 * Bal) // 1024
        nominal = min((Bal * (pct + 1)) // 1024, Bal - fee)
        row = dict(bot=bot, t=t, kind=r['kind'], pct=pct, target=r['targetName'], truth=r['truth'], replayTick=r['replayTick'], myBal=Bal, dMe=r['dMe'], dAlly=r['dAlly'],
                   nominal=nominal, feeAtLog=fee, estDelivered='', estFee='', clampedPct='', window='', note='')
        if r['truth'] == 'accepted':
            T = int(r['replayTick'])
            # next observation: next dispatch log of this bot or next HL-TICK snapshot, whichever first, strictly after T
            cands = [(int(x['t']), int(x['myBal'])) for x in ds[k + 1:] if x['myBal'] and int(x['t']) > T]
            cands += [(tt, bb) for tt, bb, _ in obs if tt > T]
            if cands:
                t1, B1 = min(cands)
                terr0 = [te for tt, bb, te in obs if tt <= t]
                terr1 = [te for tt, bb, te in obs if tt >= t1]
                terr_a = terr0[-1] if terr0 else None
                terr_b = terr1[0] if terr1 else terr_a
                other_don = [x for x in ds if x is not r and x['truth'] == 'accepted' and t <= int(x['replayTick']) < t1]
                dirty = []
                if terr_a is None or terr_a != terr_b: dirty.append('terr-changed')
                if any(t <= a < t1 for a in my_atk): dirty.append('own-attack')
                if any(t <= a < t1 for a in my_rcv): dirty.append('received-donation')
                if other_don: dirty.append('multi-donation')
                row['window'] = f'{t}->{t1}'
                if dirty:
                    row['note'] = 'dirty:' + '+'.join(dirty)
                else:
                    lo, hi = 0, nominal
                    full, f_exec = step_to(Bal, terr_a, t, t1, (T, pct, 10 ** 12))
                    none, _ = step_to(Bal, terr_a, t, t1, (T, pct, 0))
                    if B1 <= full:
                        x = nominal; note = 'full'
                    elif B1 >= none:
                        x = 0; note = 'fee-only(<=0 delivered)'
                    else:
                        for _ in range(40):
                            midx = (lo + hi) // 2
                            b, _ = step_to(Bal, terr_a, t, t1, (T, pct, midx))
                            if b > B1: lo = midx + 1
                            else: hi = midx
                        x = lo; note = 'solved'
                    row['estDelivered'] = x; row['estFee'] = f_exec
                    row['clampedPct'] = round(100 * (1 - x / max(1, nominal)), 1)
                    row['note'] = note + f' (pred full={full} none={none} obs={B1})'
        out.append(row)
fields = list(out[0].keys()) if out else []
with open(os.path.join(OUT, 'donation_ledger.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
acc = [r for r in out if r['truth'] == 'accepted']
est = [r for r in acc if r['estDelivered'] != '']
print(f"== {mid}: dispatches logged={len(out)} accepted={len(acc)} rejected={sum(1 for r in out if r['truth']=='rejected')} | clean-window estimates={len(est)}")
print(f"   accepted: sum nominal={sum(r['nominal'] for r in acc)} sum fee(at log bal)={sum(r['feeAtLog'] for r in acc)}")
if est:
    sn = sum(r['nominal'] for r in est); sx = sum(r['estDelivered'] for r in est); sf = sum(r['estFee'] for r in est)
    cl = [r for r in est if r['clampedPct'] >= 10]
    print(f"   clean windows: nominal={sn} estDelivered={sx} ({100*sx/max(1,sn):.1f}% of nominal) fee={sf} (fee/delivered={100*sf/max(1,sx):.1f}%) clamped>=10%: {len(cl)}/{len(est)}")
for r in out:
    print(f"   {r['bot']:8s} t={r['t']:6d} {r['kind'][9:]:20s} ->{r['target']:8s} {r['truth']:9s} srv={r['replayTick']:>6s} myBal={r['myBal']:8d} dMe={r['dMe']:>4s} dAlly={r['dAlly']:>4s} nominal={r['nominal']:7d} fee={r['feeAtLog']:6d} "
          f"estDelivered={str(r['estDelivered']):>7s} clamped%={str(r['clampedPct']):>5s} {r['note']}")
