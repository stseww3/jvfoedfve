#!/usr/bin/env python3
"""replay_summary.py — 对一批对局：解码录像，核对“引擎规则预测的队伍”与结算记录里的队号，并统计指令数。

用法：cd c136-review/agents/R04 && timeout 120 python3 scripts/replay_summary.py A022 A038 ... > out/replay-summary.txt
      不带参数 = 我名下 13 局。
每局输出一段：
  录像头（真人数 ku、总人数、名义队数）、预测的队数/每队上限/各队人数、我方各号的预测队号 vs results.csv 的 teamMine、
  card.json 的 actualTeams（供对照）、全场与我方的指令计数（按指令号）。
只读 /agent/repos/c136-data/bundles/<局>/{replay.txt,results.csv,card.json}。
"""
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_lib import load_replay, TEAM_COLOUR_NAMES  # noqa: E402

BUNDLES = '/agent/repos/c136-data/bundles'
MINE = ['A022', 'A038', 'A029', 'A073', 'A047', 'A083', 'A099', 'A078', 'A015', 'A081', 'A086', 'A013', 'B034']
CMD = {0: '出生', 1: '陆攻', 2: '捐款', 3: '发船', 4: '追/召回', 5: '撤攻/发起投票', 6: '表情', 7: '投票', 8: '认输', 9: '离场', 10: '越山'}


def main(ids):
    ok_all = 0
    n_all = 0
    for mid in ids:
        d = os.path.join(BUNDLES, mid)
        rp = os.path.join(d, 'replay.txt')
        card = json.load(open(os.path.join(d, 'card.json')))
        if not os.path.exists(rp):
            print(f'== {mid}: 没有 replay.txt')
            continue
        r = load_replay(rp)
        vu = r['vu']
        res = list(csv.DictReader(open(os.path.join(d, 'results.csv'), encoding='utf8')))
        print(f"== {mid}  ku={r['H']} 总人数={r['P']} 名义队数={vu['numberTeams']} gameMode={vu['gameMode']} battleRoyaleMode={vu['battleRoyaleMode']} "
              f"contest={vu['isContest']} 录像拍数={r['ticks']} (card.endTick={card['outcome'].get('endTick')}) 录像完整位={r['bits']['bitsUsed']}/{r['bits']['bitsTotal']}")
        t = r['teams']
        if t:
            print(f"   预测：参与分配 {t['teams']} 队，每队上限 {t['cap']}，各队人数 {t['size'][1:]}，队色 {[TEAM_COLOUR_NAMES[c] for c in t['rank'][1:t['teams'] + 1]]}；"
                  f"card.actualTeams={card.get('actualTeams')} card.nominalTeams={card.get('nominalTeams')}")
            clans = sorted(((len(v), k) for k, v in t['clans'].items()), reverse=True)[:6]
            print('   最大的几个战队标签：' + ', '.join(f'{k}×{n}' for n, k in clans))
        else:
            print('   非团队局（无队伍分配）')
        # 我方
        rows = []
        for x in res:
            me = int(x['meId'])
            pred = t['fX'][me] if t and me < r['H'] else None
            obs = x.get('teamMine')
            obs = int(obs) if obs not in (None, '') else None
            name = r['names'][me] if me < r['H'] else '?'
            match = (pred == obs) if (pred is not None and obs is not None) else None
            rows.append((x['bot'], me, name, pred, obs, match))
        good = sum(1 for x in rows if x[5])
        tot = sum(1 for x in rows if x[5] is not None)
        ok_all += good
        n_all += tot
        print(f'   我方 {len(rows)} 个号：预测队号=结算 teamMine 的 {good}/{tot}')
        for bot, me, name, pred, obs, match in rows:
            flag = '' if match else ('  <-- 不一致' if match is False else '  (无法比对)')
            print(f'     {bot:10s} me={me:3d} 名字={name!r} 预测队={pred} 结算队={obs}{flag}')
        allc = Counter(x[2] for x in r['rows'])
        ours = {int(x['meId']) for x in res}
        ourc = Counter(x[2] for x in r['rows'] if x[3] in ours)
        print('   全场指令：' + ' '.join(f'{CMD.get(k, k)}={v}' for k, v in sorted(allc.items())))
        print('   我方指令：' + ' '.join(f'{CMD.get(k, k)}={v}' for k, v in sorted(ourc.items())))
    print(f'# 合计：我方号预测队号与结算一致 {ok_all}/{n_all}')


if __name__ == '__main__':
    main(sys.argv[1:] or MINE)
