#!/usr/bin/env python3
# truth_query.py — 在一局的真相表（tmp/truth/<局号>/）上做点查，供复盘时核对具体一段的事实。
#
# 用法：
#   python3 scripts/truth_query.py <局号> cmds <号名或编号> [t0 t1] [--id 1,2,3]   这个号被执行的指令（含真实出兵/到账）
#   python3 scripts/truth_query.py <局号> on   <号名或编号> [t0 t1]               别人打它 / 捐给它 / 船靠它 的事件
#   python3 scripts/truth_query.py <局号> bal  <号名或编号> t0 t1 [步长]           它的 领土/余额/在外兵/被攻兵 轨迹
#   python3 scripts/truth_query.py <局号> flow <号名或编号> t0 t1                  这段时间它的地从谁来、到谁去
#   python3 scripts/truth_query.py <局号> gain <t0> <t1>                          窗口内我方队伍谁净得地、地从谁来、丢给谁
#   python3 scripts/truth_query.py <局号> who  <t> [n]                           第 t 拍全场真人前 n 名（领土）
#   python3 scripts/truth_query.py <局号> team <t0> <t1> [步长]                   各队领土/余额序列
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_digest import Match, fmt

KIND = {0: '出生', 1: '陆攻', 2: '捐款', 3: '发船', 4: '追船/调船', 5: '撤兵/发起投票', 6: '表情', 7: '投票', 8: '离开', 9: '掉线', 10: '山'}


def pid(M, s):
    if s.isdigit():
        return int(s)
    for p, n in M.ours.items():
        if n.replace('[APEX] ', '') == s:
            return p
    for p in range(M.ku):
        if M.name[p] == s or s in M.name[p]:
            return p
    raise SystemExit('找不到这个号：' + s)


def main():
    a = sys.argv[1:]
    M = Match(a[0])
    sub = a[1]
    if sub == 'cmds':
        p = pid(M, a[2])
        rest = [x for x in a[3:] if not x.startswith('--')]
        t0, t1 = (int(rest[0]), int(rest[1])) if len(rest) >= 2 else (-1, 10**9)
        ids = set(int(x) for x in a[a.index('--id') + 1].split(',')) if '--id' in a else None
        for c in M.cmd:
            if c['p'] != p or not (t0 <= c['t'] <= t1) or c['sp'] >= 0:
                continue
            if ids and c['id'] not in ids:
                continue
            line = f'拍 {c["t"]:>5d} {KIND.get(c["id"], c["id"])} a={c["a"]} b={c["b"]} 余额 {c["bal0"]}→{c["bal1"]} 领土 {c["terr0"]}'
            if c['id'] == 2 and 'q' in c:
                got = c['balQ1'] - c['balQ0']
                line += f' → {M.nm(c["q"])} 到账 {got}（税 {c["bal0"]-c["bal1"]-got}；对方余额 {c["balQ0"]} 领土 {c["terrQ"]} 上限 {150*c["terrQ"]}；配额 {c["used0"]}→{c["used1"]}/{c["cap"]}）'
            for s in c['sub']:
                if s[0] == 'atk':
                    line += f' → 打 {M.nm(int(s[1]))} {s[2]} 兵'
                elif s[0] == 'boat':
                    line += f' → 船#{s[1]} 载 {s[2]} 兵'
            if c['id'] == 1 and not c['sub']:
                line += ' （没有产生进攻）'
            print(line)
    elif sub == 'on':
        p = pid(M, a[2])
        t0, t1 = (int(a[3]), int(a[4])) if len(a) >= 5 else (-1, 10**9)
        rows = []
        for c in M.cmd:
            if not (t0 <= c['t'] <= t1) or c['sp'] >= 0:
                continue
            if c['id'] == 2 and c.get('q') == p:
                rows.append((c['t'], f'{M.nm(c["p"])} 捐来 到账 {c["balQ1"]-c["balQ0"]}（对方余额 {c["bal0"]}→{c["bal1"]}）'))
            for s in c['sub']:
                if s[0] == 'atk' and int(s[1]) == p:
                    rows.append((c['t'], f'{M.nm(c["p"])} 陆攻 {s[2]} 兵（对方余额 {c["bal0"]}→{c["bal1"]} 领土 {c["terr0"]}）'))
        for (t, kind, pl, x, y, det) in M.ev:
            if not (t0 <= t <= t1):
                continue
            if kind == 'land' and (f'atk:{p}:' in det or f'give:{p}:' in det):
                rows.append((t, f'{M.nm(pl)} 的船靠岸（载 {y}）：{det.split("|")[1]}'))
            if kind == 'aiatk' and int(x) == p:
                rows.append((t, f'{M.nm(pl)} 出兵 {y}'))
            if kind == 'aigift' and int(x) == p:
                rows.append((t, f'{M.nm(pl)} 赠送 到账 {y}'))
        for t, s in sorted(rows):
            print(f'拍 {t:>5d} {s}')
    elif sub == 'bal':
        p = pid(M, a[2])
        t0, t1 = int(a[3]), int(a[4])
        st = int(a[5]) if len(a) > 5 else 10
        if p in M.our:
            for t in range(t0, t1 + 1, st):
                v = M.our[p].get(t)
                if v:
                    print(f'拍 {t:>5d} 领土 {v[0]:>6d} 余额 {v[1]:>8d} 密度 {v[1]/max(v[0],1):6.1f} 在外兵 {v[2]:>7d} 被攻兵 {v[3]:>7d}（{v[4]} 路） 船 {v[5]}')
        else:
            for t in range(M.at(t0), t1 + 1, max(st - st % M.step, M.step)):
                v = M.state.get(t, {}).get(p)
                if v:
                    print(f'拍 {t:>5d} 领土 {v[0]:>6d} 余额 {v[1]:>8d} 密度 {v[1]/max(v[0],1):6.1f} 在外兵 {v[2]:>7d} 被攻兵 {v[4]:>7d}（{v[5]} 路） 船 {v[6]} 状态 {v[8]}')
    elif sub == 'flow':
        p = pid(M, a[2])
        fl = M.flows(int(a[3]), int(a[4]))
        gain = collections.Counter(); lose = collections.Counter()
        for (x, y), px in fl.items():
            if y == p:
                gain[x] += px
            if x == p:
                lose[y] += px
        print('拿到：' + '；'.join(f'{M.nm(k)} {v}' for k, v in gain.most_common(10)))
        print('丢给：' + '；'.join(f'{M.nm(k)} {v}' for k, v in lose.most_common(10)))
    elif sub == 'gain':
        # 窗口内我方队伍每个成员的净得地（从敌方/无主地拿到 − 被拿走），以及全队从各敌方真人处拿到/丢掉的地
        t0, t1 = int(a[2]), int(a[3])
        fl = M.flows(t0, t1)
        tm = M.our_team
        inteam = lambda x: x < M.ku and M.team.get(x) == tm
        gain = collections.Counter(); lose = collections.Counter(); frm = collections.Counter(); to = collections.Counter()
        for (x, y), px in fl.items():
            if inteam(y) and not inteam(x):
                gain[y] += px; frm[x] += px
            if inteam(x) and not inteam(y):
                lose[x] += px; to[y] += px
        net = collections.Counter({p: gain[p] - lose[p] for p in set(gain) | set(lose)})
        print(f'窗口 ({t0},{t1}] 我方队 {tm}：从外面拿到 {sum(gain.values())}，被拿走 {sum(lose.values())}，净 {sum(gain.values())-sum(lose.values())}')
        print('净得地最多的成员：' + '；'.join(f'{M.nm(p)} {v:+d}（拿 {gain[p]} 丢 {lose[p]}）' for p, v in net.most_common(8)))
        print('净丢地最多的成员：' + '；'.join(f'{M.nm(p)} {v:+d}' for p, v in sorted(net.items(), key=lambda kv: kv[1])[:5] if v < 0))
        print('地从谁那里来：' + '；'.join(f'{M.nm(p)} {v}' for p, v in frm.most_common(8)))
        print('地丢给了谁：' + '；'.join(f'{M.nm(p)} {v}' for p, v in to.most_common(8)))
    elif sub == 'who':
        t = M.at(int(a[2])); n = int(a[3]) if len(a) > 3 else 12
        st = M.state[t]
        for p in sorted(range(M.ku), key=lambda q: -st[q][0])[:n]:
            v = st[p]
            print(f'{M.nm(p):28s} 领土 {v[0]:>6d} 余额 {fmt(v[1]):>7s} 密度 {v[1]/max(v[0],1):6.1f} 在外兵 {fmt(v[2])} 被攻兵 {fmt(v[4])} 状态 {v[8]}')
    elif sub == 'team':
        t0, t1 = int(a[2]), int(a[3]); st = int(a[4]) if len(a) > 4 else 300
        for t in range(M.at(t0), t1 + 1, st):
            ts = M.teamts.get(t)
            if ts:
                print(f'拍 {t:>5d} ' + ' | '.join(f'队{k} {100*v[0]/M.ke:4.1f}% {fmt(v[1])} {v[3]}人' for k, v in sorted(ts.items()) if k < 100))


if __name__ == '__main__':
    main()
