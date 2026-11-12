#!/usr/bin/env python3
"""m6_boats.py — 15 局的船账和敌方登陆账（跨局对比用），只读已有产物：
  out/<局>/boat_trace.csv   （boat_trace.mjs：本队每条船 出海拍、装兵、出海手续费、到岸剩几成、落在谁的地上、海上被打掉多少）
  out/<局>/sea_landings.csv （sea_landings.mjs：别人的船在本队号的岸上登陆：拍、谁、带多少兵、登陆前和这个号接不接壤）
先跑（统一口径，一局几秒）：bash scripts/batch_loop.sh scripts/steps/m6-boats.txt /tmp/r01_m6c.log

引擎事实（src/sim/sim/boats.js；boat_trace.mjs 里逐条对过重演）：
  出海手续费 = 出海那一拍余额的 32/1024，和装多少兵无关（game.js quote(p, pct, 32) L1239–1248；陆攻是 12/1024，捐兵是 64/1024）。
    表里的 fee = 出海前余额 − 出海后余额 − 船上的兵；和 floor(出海前余额×32/1024) 差 2 以内的船是干净的（A075、A055、A054、A009、A023、A003 六局 77/77 条全等）。
    差得多的船 = 同一拍还有别的过期指令先落地（A019 2 条、B039 13 条、B043 1 条），这些船的手续费量不准：单列条数，不计入手续费合计，也不计入“装兵比手续费少”；
  船在海上每 5 拍掉 max(1, 兵>>7)；靠自己的岸 = 兵回余额；靠队友的岸 = 当捐兵转给队友（受配额和 150 倍上限约束，过不了整船作废，landAt L262–287）；
  靠无主地 / AI / 敌岸 = 开一条进攻线；海上会被别人的船拦截（hitLoss）。
每局输出：
  船数、装兵合计、手续费合计、手续费 ÷（装兵+手续费）、装兵比手续费还少的船数；
  去向（条数 / 装兵 → 到岸）：敌岸、AI、无主地、自己岸、队友岸（队友实际到账）、沉没、收场时还在海上；
  海上被拦截打掉的兵；
  别人登陆本队：次数 / 带的兵；其中登陆前不接壤的次数 / 兵。
用法：python3 scripts/m6_boats.py [局号 ...] [--md]
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
MIDS = 'A075 A057 A059 A094 A055 A054 A031 A019 A009 A023 A050 A003 A005 B039 B043'.split()
DEST = ('enemy', 'ai', 'neutral', 'self', 'mate', 'sunk', 'still-at-sea')


def rd(mid, name):
    p = os.path.join(R, 'out', mid, name)
    return list(csv.DictReader(open(p, encoding='utf8'))) if os.path.exists(p) else None


def main():
    argv = sys.argv[1:]
    mids = [x for x in argv if not x.startswith('--')] or MIDS
    md = '--md' in argv
    num = lambda x: float(x) if x not in ('', None) else 0.0
    w = lambda x: f'{x / 1e4:.1f} 万' if x else '0'
    bar, end = ('| ', ' |') if md else ('', '')
    print(bar + ' | '.join(['局', '船数 · 装兵 · 手续费（占装兵+手续费的）', '装兵比手续费少的船', '打敌岸 / AI / 无主地：条数（装兵 → 到岸）', '回自己岸', '靠队友岸：条数（到岸 → 队友到账）',
                            '沉没 / 收场还在海上（装兵）', '海上被拦截打掉', '别人登陆本队：次数 · 兵（其中登陆前不接壤的）']) + end)
    if md:
        print('|---' * 9 + '|')
    T = dict(n=0, load=0.0, fee=0.0, small=0, mate=0, mateArr=0.0, mateGot=0.0, sunk=0, sunkLoad=0.0, hit=0.0, land=0, landTroops=0.0, far=0, farTroops=0.0)
    for m in mids:
        B, S = rd(m, 'boat_trace.csv'), rd(m, 'sea_landings.csv')
        B = B or []
        load = sum(num(r['troops0']) for r in B)
        clean = [r for r in B if abs(num(r.get('fee')) - int(num(r['balBefore']) * 32 / 1024)) <= 2]
        dirty = len(B) - len(clean)
        fee = sum(num(r.get('fee')) for r in clean)
        small = [r for r in clean if num(r['troops0']) < num(r.get('fee'))]
        by = {k: [r for r in B if r['landedOn'] == k] for k in DEST}
        other = [r for r in B if r['landedOn'] not in DEST]
        seg = lambda L: f"{len(L)}（{w(sum(num(r['troops0']) for r in L))} → {w(sum(num(r['troopsArr']) for r in L))}）" if L else '0'
        mate = by['mate']
        ms = f"{len(mate)}（{w(sum(num(r['troopsArr']) for r in mate))} → {w(sum(num(r['mateGot']) for r in mate))}）" if mate else '0'
        hit = sum(num(r.get('hitLoss')) for r in B)
        if S is None:
            sl = '—'
        else:
            far = [r for r in S if r['hadLandBorder'] == '0']
            sl = f"{len(S)} · {w(sum(num(r['troops']) for r in S))}（{len(far)} · {w(sum(num(r['troops']) for r in far))}）"
            T['land'] += len(S); T['landTroops'] += sum(num(r['troops']) for r in S); T['far'] += len(far); T['farTroops'] += sum(num(r['troops']) for r in far)
        cload = sum(num(r['troops0']) for r in clean)
        cells = [m, (f"{len(B)} · {w(load)} · {w(fee)}（{100 * fee / (cload + fee):.0f}%）" + (f"；另有 {dirty} 条同拍混批不计费" if dirty else '')) if B else '0', str(len(small)) + (f"（手续费 {w(sum(num(r['fee']) for r in small))}）" if small else ''),
                 ' / '.join(seg(by[k]) for k in ('enemy', 'ai', 'neutral')), seg(by['self']), ms,
                 f"{len(by['sunk'])}（{w(sum(num(r['troops0']) for r in by['sunk']))}） / {len(by['still-at-sea'])}（{w(sum(num(r['troops0']) for r in by['still-at-sea']))}）"
                 + (f" · 其他 {len(other)}" if other else ''), w(hit), sl]
        print(bar + ' | '.join(cells) + end)
        T['n'] += len(B); T['load'] += load; T['fee'] += fee; T['small'] += len(small); T['mate'] += len(mate); T['cload'] = T.get('cload', 0.0) + cload; T['dirty'] = T.get('dirty', 0) + dirty
        T['mateArr'] += sum(num(r['troopsArr']) for r in mate); T['mateGot'] += sum(num(r['mateGot']) for r in mate)
        T['sunk'] += len(by['sunk']); T['sunkLoad'] += sum(num(r['troops0']) for r in by['sunk']); T['hit'] += hit
    print(bar + ' | '.join(['合计', f"{T['n']} · {w(T['load'])} · {w(T['fee'])}（{100 * T['fee'] / (T['cload'] + T['fee']):.0f}%）；{T['dirty']} 条不计费", str(T['small']), '', '',
                            f"{T['mate']}（{w(T['mateArr'])} → {w(T['mateGot'])}）", f"{T['sunk']}（{w(T['sunkLoad'])}）", w(T['hit']),
                            f"{T['land']} · {w(T['landTroops'])}（{T['far']} · {w(T['farTroops'])}）"]) + end)


if __name__ == '__main__':
    main()
