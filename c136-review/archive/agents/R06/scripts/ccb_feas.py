#!/usr/bin/env python3
"""ccb_feas.py — 「历史真局断面反事实重演」的可行性账（只读已有产物，不重放）

回答三件事（有对局录像的 9 局）：
  A. 每局哪些断面能用：录像到第几拍；干净 JS 模拟器（策略能跑在上面的那个）与真引擎逐拍一致到第几拍
     （probe.json 的 simVsEngine.lastOkT，由 strat_probe.mjs 产出）；各断面当时场上还有多少个我方号、空壳、外人真人、内置 AI。
  B. 外人真人的历史指令里，有多少是「不看对象」的（打无主地），有多少指向玩家：前者在我方换了打法以后照旧能执行，
     后者的对象可能已经不在、不相邻。按执行拍分段。
  C. 外人指向玩家的陆攻里，对象是我方号的占多少（我方一变，这部分最先失真）。

用法：python3 scripts/ccb_feas.py            产物：out/_cross/ccb_feas.txt
局限：B / C 只是指令构成，不是「开环重放能撑多久」的实测；实测要在模拟器里真的分叉以后数被引擎拒绝的历史指令。
"""
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simdigest as SD  # noqa: E402
import team_assign as TA  # noqa: E402
from r06lib import OUT, PEER_REPLAY  # noqa: E402

IDS = ['B010', 'B017', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041']
CPS = [0, 630, 1500, 3000, 4284]
HORIZON = 600
BANDS = [(0, 630, '<630'), (630, 1500, '630~1500'), (1500, 3000, '1500~3000'), (3000, 4284, '3000~4284'), (4284, 10 ** 9, '>=4284')]


def main():
    out = []
    out.append('**A. 断面可用性**（「一致到」= 干净 JS 模拟器与真引擎逐拍一致的最后一拍；断面可用 = 断面拍 + 600 拍 <= min(录像末拍, 一致到)）')
    out.append('')
    out.append('| 局 | 录像末拍 | 模拟器一致到 | ' + ' | '.join(f't={c}：我方在场 / 空壳 / 外人真人 / 内置 AI' for c in CPS) + ' |')
    out.append('|---|---|---|' + '---|' * len(CPS))
    usable = Counter()
    mix = {b[2]: Counter() for b in BANDS}
    per_match_mix = defaultdict(lambda: defaultdict(Counter))
    for mid in IDS:
        X = SD.Sim(mid)
        S = X.S
        pj = json.load(open(os.path.join(OUT, mid, 'probe.json')))
        ok_to = pj['simVsEngine']['lastOkT']
        end = X.endT
        squad = set(X.squad)
        cells = []
        for c in CPS:
            if c + HORIZON > min(end, ok_to):
                cells.append('—（不够长）')
                continue
            usable[c] += 1
            i = X.ix(c)
            ours = husk = foes = 0
            for p in range(X.H):
                terr = X.hum[p]['terr'][i]
                left = p in X.leave and X.leave[p]['t'] <= c
                if c == 0:
                    alive = not (p in X.leave and X.leave[p]['t'] <= 0)
                else:
                    alive = terr > 0
                if not alive:
                    continue
                if p in squad:
                    if left:
                        husk += 1
                    else:
                        ours += 1
                elif not left:
                    foes += 1
            ai = S['aiAlive'][i]
            cells.append(f"{ours} / {husk} / {foes} / {ai}")
        out.append(f"| {mid} | {end:,} | {ok_to:,} | " + ' | '.join(cells) + ' |')
        # B / C：外人真人的指令构成
        dec = TA.load_decoded(PEER_REPLAY.get(mid, mid))   # B038 / B039 的整局录像在同一场的 A057 / A058 包里，玩家号相同
        for c in dec['cmds']:
            if c.get('phase') != 'game':
                continue
            p = c['player']
            if p >= X.H or p in squad:
                continue
            if p in X.leave and X.leave[p]['t'] <= c['t']:
                continue
            t = c['t']
            band = next(b[2] for b in BANDS if b[0] <= t < b[1])
            k = None
            if c['id'] == 1:
                to = c['dZ']
                if to >= 512:
                    k = '陆攻·无主地'
                elif to >= X.H:
                    k = '陆攻·内置AI'
                elif to in squad:
                    k = '陆攻·我方号'
                else:
                    k = '陆攻·别的真人'
            elif c['id'] == 3:
                k = '发船'
            elif c['id'] == 2:
                k = '捐款'
            else:
                continue
            mix[band][k] += 1
            per_match_mix[mid][band][k] += 1
    out.append('')
    out.append('可用局数：' + '、'.join(f"t={c} {usable[c]}/9" for c in CPS))
    out.append('')
    out.append('**B. 外人真人（不含已离场的）的历史指令构成，按执行拍**（9 局合计）')
    out.append('')
    kinds = ['陆攻·无主地', '陆攻·内置AI', '陆攻·我方号', '陆攻·别的真人', '发船', '捐款']
    out.append('| 执行拍 | 指令 | ' + ' | '.join(kinds) + ' | 指向玩家的陆攻里对象是我方号 |')
    out.append('|---|---|' + '---|' * (len(kinds) + 1))
    for _, _, name in BANDS:
        m = mix[name]
        n = sum(m.values())
        if not n:
            continue
        pl = m['陆攻·内置AI'] + m['陆攻·我方号'] + m['陆攻·别的真人']
        out.append(f"| {name} | {n:,} | " + ' | '.join(f"{m[k]:,}（{100 * m[k] / n:.1f}%）" for k in kinds)
                   + f" | {m['陆攻·我方号']:,}/{pl:,}（{100 * m['陆攻·我方号'] / max(1, pl):.1f}%） |")
    out.append('')
    out.append('**各局 <630 拍：外人指令里打无主地的占比**：' + '、'.join(
        f"{mid} {100 * per_match_mix[mid]['<630']['陆攻·无主地'] / max(1, sum(per_match_mix[mid]['<630'].values())):.0f}%" for mid in IDS))
    out.append('**各局 630~1500 拍：外人指令里打无主地 / 打内置 AI 的占比**：' + '、'.join(
        f"{mid} {100 * per_match_mix[mid]['630~1500']['陆攻·无主地'] / max(1, sum(per_match_mix[mid]['630~1500'].values())):.0f}% / "
        f"{100 * per_match_mix[mid]['630~1500']['陆攻·内置AI'] / max(1, sum(per_match_mix[mid]['630~1500'].values())):.0f}%" for mid in IDS))
    txt = '\n'.join(out) + '\n'
    os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
    open(os.path.join(OUT, '_cross', 'ccb_feas.txt'), 'w').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
