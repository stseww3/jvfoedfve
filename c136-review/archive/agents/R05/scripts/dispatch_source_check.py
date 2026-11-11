#!/usr/bin/env python3
# dispatch_source_check.py — 用全部 A 系日志里的 [HL-DISPATCH] 行，反过来检验「哪一份源码在跑」。
# 三份源码（c136-data/src/strategy/）里 tryDonateToTeammate 的门槛（行号 = v27-team-c116-vb.js，va/vc 同位置 ±1 行）：
#   Va  v27-team-c116-va.js : 余额>=30000；防守 reqD 内陆 30(有海岸 42)/前线 102；进攻·收益 reqD 内陆 82/前线 108；
#                             受援密度上限 内陆 140/前线 96；前线号还要 dMe>=dAlly+16；理想 pct 防守 260/190 进攻 225/170；pct<128 不发
#   Vb  v27-team-c116-vb.js : 余额>=30000；防守 30(42)/102；进攻·收益 58/108；上限 140/96；前线号 dMe>=dAlly+16；pct 380/240、320/220；<180 不发
#   Vc  v27-team-c116.js    : 余额>=35000；防守 58(68)/102 且 dAlly<85；进攻·收益 96/108；上限 94/88；所有号 dMe>=dAlly+15；pct 260/190、220/170；<150 不发
# 做法：把每一行日志分别套三份门槛，数违例条数。某个版本期的日志对「自己的源码」应当 0 违例（日志里的密度是四舍五入值，留 0.6 的余量）。
# 用法：python3 dispatch_source_check.py > out/dispatch-source-check.txt
import os, re, sys, collections

DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')
RE = re.compile(r'\[([^\]]+)\] \[HL-DISPATCH\] t=(\d+) (\w+) pct=(\d+)/1024 -> ally=(\d+)\(([^)]*)\) boxedIn=(true|false) myBal=(\d+) dMe=(-?\d+) dAlly=(-?\d+)')

RULES = {
    'Va': dict(minBal=30000, defReq=(30, 102), offReq=(82, 108), defMaxAlly=(142, 115), offMaxAlly=(140, 96), gapBoxed=None, gapFront=16, ideal={'D': (260, 190), 'O': (225, 170)}, minPct=128),
    'Vb': dict(minBal=30000, defReq=(30, 102), offReq=(58, 108), defMaxAlly=(142, 115), offMaxAlly=(140, 96), gapBoxed=None, gapFront=16, ideal={'D': (380, 240), 'O': (320, 220)}, minPct=180),
    'Vc': dict(minBal=35000, defReq=(58, 102), offReq=(96, 108), defMaxAlly=(85, 85), offMaxAlly=(94, 88), gapBoxed=15, gapFront=15, ideal={'D': (260, 190), 'O': (220, 170)}, minPct=150),
}
EPS = 0.6


def epoch(mid):
    n = int(mid[1:])
    return 'E1(A001-A017)' if n <= 17 else ('E2(A018-A095)' if n <= 95 else 'E3(A097-A099)')


def violations(rule, kind, boxed, pct, bal, dme, dally):
    v = []
    K = 'D' if kind.startswith('defense') else 'O'
    i = 0 if boxed else 1
    if bal < rule['minBal']:
        v.append('minBal')
    if pct > rule['ideal'][K][i]:
        v.append('pct>ideal')
    if pct < rule['minPct']:
        v.append('pct<min')
    req = (rule['defReq'] if K == 'D' else rule['offReq'])[i]
    if dme < req - EPS:
        v.append('dMe<reqD')
    mx = (rule['defMaxAlly'] if K == 'D' else rule['offMaxAlly'])[i]
    if K == 'D':
        if dally >= mx + EPS:
            v.append('dAlly>=max')
    elif dally > mx + EPS:
        v.append('dAlly>max')
    gap = rule['gapBoxed'] if boxed else rule['gapFront']
    if gap is not None and dme < dally + gap - 2 * EPS:
        v.append('dMe<dAlly+gap')
    return v


def main():
    rows = collections.defaultdict(list)
    for mid in sorted(os.listdir(os.path.join(DATA, 'bundles'))):
        if not mid.startswith('A'):
            continue
        p = os.path.join(DATA, 'bundles', mid, 'in_game.log')
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8', errors='replace') as f:
            for line in f:
                if '[HL-DISPATCH]' not in line:
                    continue
                m = RE.search(line)
                if not m:
                    continue
                rows[epoch(mid)].append((mid, m.group(3), m.group(7) == 'true', int(m.group(4)), int(m.group(8)), int(m.group(9)), int(m.group(10))))
    print('# [HL-DISPATCH] 日志行 × 三份源码门槛 的违例矩阵（行=对局所属时期，列=拿哪份源码去套）')
    print('时期\t日志行数\t套Va违例\t套Vb违例\t套Vc违例\t套Va的违例构成\t套Vb的违例构成\t套Vc的违例构成')
    for ep in sorted(rows):
        R = rows[ep]
        cells, comps = [], []
        for name in ('Va', 'Vb', 'Vc'):
            c = collections.Counter()
            bad = 0
            for (_, kind, boxed, pct, bal, dme, dally) in R:
                v = violations(RULES[name], kind, boxed, pct, bal, dme, dally)
                if v:
                    bad += 1
                    c.update(v)
            cells.append(str(bad))
            comps.append(' '.join(f'{k}:{n}' for k, n in c.most_common()) or '-')
        print('\t'.join([ep, str(len(R))] + cells + comps))
    print()
    print('# 各时期实测边界（kind×是否内陆 boxedIn）：条数 / 最小 dMe / 最大 dAlly / pct 众数(占比) / 最小 pct / 最小 myBal / dMe<dAlly 的条数（倒挂：捐出方密度低于受援方）')
    print('时期\tkind\tboxedIn\t条数\t最小dMe\t最大dAlly\tpct众数\t最小pct\t最小myBal\t倒挂条数\t倒挂占比')
    for ep in sorted(rows):
        G = collections.defaultdict(list)
        for r in rows[ep]:
            G[(r[1], r[2])].append(r)
        for (kind, boxed) in sorted(G):
            L = G[(kind, boxed)]
            pc = collections.Counter(x[3] for x in L).most_common(1)[0]
            inv = sum(1 for x in L if x[5] < x[6])
            print('\t'.join(map(str, [ep, kind, 'true' if boxed else 'false', len(L), min(x[5] for x in L), max(x[6] for x in L),
                                      f'{pc[0]}({100 * pc[1] // len(L)}%)', min(x[3] for x in L), min(x[4] for x in L), inv, f'{100 * inv / len(L):.1f}%'])))


if __name__ == '__main__':
    main()
