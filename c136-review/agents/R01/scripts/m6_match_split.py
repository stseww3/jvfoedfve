#!/usr/bin/env python3
"""m6_match_split.py — 一个对局包里的页面是不是都在同一场对局里。

背景：A043 的 results.csv 里，8 个号（席位 0–7）4587 拍前全部阵亡，当时的 teamTotals 只有 1、2 两个队；另外 2 个号（席位 18、19）
7436–7510 拍才阵亡，teamTotals 是 1、3、4、5 四个队。录像头里只有后 2 个号的名字，席位 0–7 是别的真人。
也就是这个包里是同一张图、同一个种子、几乎同时开局的两场平行对局（20 人房满了以后剩下的页面进了下一间）。
这种包的“编队领土占比”“好地账”“落地/放行”都是把两场混在一起算的，不能进跨局分组。

三条互相独立的证据（只读对局包和 out/<局号>/replay_meta.json，不模拟）：
  E1 开局时刻：results.csv 每行的 at − seconds = 这个页面的对局开始时刻。同一场的页面多数相差 ≤ 1 秒，个别页面晚 2 秒上下
     （B007 的 Cheese 晚 2.1 秒、B029 的 Kuban 晚 1.3 秒，它们的 teamTotals 和同局别的页面逐拍接得上，是同一场）。
     相邻两个页面相差 ≥ GAP 秒（默认 3.0）才单凭这一条算两场。只有有 RESULT 行的页面能用。
  E2 名字：日志里 `[号] … me=N` 给出每个页面的席位号 N；录像头的名单里 N 号席位的名字应当是这个号。
     c116/g09（名字固定带 [APEX] 前缀）：不相等 = 这个页面不在录像这一场。
     c110（名字从池子里抽；同一个页面的日志标签在一局里会换，B029 的 29 号席位前面叫 Marlborough、后面叫 Leclerc）：
     录像里 N 号席位的名字既不等于标签、也不是池子里的名字（`isOurSquadBot` 的判据：在 SQUAD_POOL_SET 里，或带 [NPL]/[NOPE]）
     = 不在录像这一场；在池子里但不等于标签的只记数（relabel）。席位号 ≥ 录像头的人数也算不在这一场。
     E2 不受 GAP 限制：A086（差 2.4 秒）、B050（差 1.9 秒）靠这一条判出。
  E3 队伍：results.csv 的 teamTotals 里出现过的队号集合，按 E1 的分组列出，作旁证（A043：一组只见过 1、2 队，另一组见过 1、3、4、5 队）。
  E4 收场拍：一场对局只有一个收场拍；RESULT 行里 event=end 的拍号不止一个的包末尾单列（A025：3 个页面 6952 拍收场，4 个页面 14689 拍）。
另外沿用原来的“先后两场”判据（seq）：同一个号先后对上两个席位、开局行参数不止一种、card.seededPlayers 和录像头人数不同、
某个号的快照拍号倒退、seededPlayers < 10。

输出：每个包一行；kind = single / parallel（平行两场）/ seq（先后两场，或录像不是日志这一场）；pages = 有席位号的页面数（c110 按席位号数，不按标签数）；
      main = 页面最多的那一组的页面数，foreign = 其余页面数。
用法：python3 scripts/m6_match_split.py [局号 ...] [--csv] [--gap 3.0] [--all]
      --csv 写 out/_all/match_split.csv（mid,cohort,kind,pages,main,foreign,gap,e1,e2,relabel,teams,foreignBots）；--all 连 single 也列出
其他全量脚本用 load_split() 读这张表：kind != single 的包不进跨局分组。
"""
import csv, datetime, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'out')
DATA = '/agent/repos/c136-data/bundles'
C110 = '/agent/repos/c136-data/src/strategy/v27-team-c110.js'
PAT_ME = re.compile(r'^\d+\t\[([^\]]+)\] \[HL-(?:GAME-INIT|SPAWN|SPAWN-BACKEND)\].*?\bme=(\d+)')
PAT_INIT = re.compile(r'\[HL-GAME-INIT\] mode=(\d+) map=(\d+) mapSeed=(\d+) seeded=(\d+)')


def pool():
    try:
        head = open(C110, encoding='utf8').readline()
        return set(json.loads(head[head.index('['):head.index(']') + 1]))
    except Exception:
        return set()


def ts(s):
    return datetime.datetime.strptime(s.replace('Z', '+0000'), '%Y-%m-%dT%H:%M:%S.%f%z').timestamp()


def one(mid, POOL, gap):
    card = json.load(open(os.path.join(DATA, mid, 'card.json')))
    r = {'mid': mid, 'cohort': card['cohort'], 'kind': 'single', 'pages': 0, 'main': 0, 'foreign': 0, 'gap': None,
         'e1': '', 'e2': '', 'relabel': 0, 'teams': '', 'foreignBots': '', 'resTicks': '', 'endTicks': ''}
    # —— 日志：席位号、开局行 ——
    seats, inits, seq = {}, set(), []
    for line in open(os.path.join(DATA, mid, 'in_game.log'), errors='replace'):
        g = PAT_INIT.search(line)
        if g:
            inits.add(g.groups())
        m = PAT_ME.match(line)
        if m:
            b, p = m.group(1), int(m.group(2))
            if b in seats and seats[b] != p and 'seat' not in seq:
                seq.append('seat')
            seats.setdefault(b, p)
    if len(inits) > 1:
        seq.append('init')
    if (card.get('seededPlayers') or 0) < 10:
        seq.append('seeded<10')
    last = {}
    tp = os.path.join(DATA, mid, 'traj.csv')
    if os.path.exists(tp):
        for x in csv.DictReader(open(tp)):
            try:
                t = int(x['t'])
            except ValueError:
                continue
            if x['bot'] in last and t < last[x['bot']] and 'back' not in seq:
                seq.append('back')
            last[x['bot']] = t
    res_seats = {}
    res_tick = {}
    ends = set()

    # —— E1 开局时刻 ——
    foreign = set()
    groups = []
    st = []
    rp = os.path.join(DATA, mid, 'results.csv')
    if os.path.exists(rp):
        for x in csv.DictReader(open(rp)):
            try:
                keys = tuple(sorted(k for k in json.loads(x['teamTotals']) if k != '0')) if x.get('teamTotals') else None
                st.append((ts(x['at']) - float(x['seconds']), x['bot'], keys))
                res_seats[x['bot']] = int(x['meId'])
                res_tick[x['bot']] = (int(float(x['tick'])), x.get('event') or '')
                if x.get('event') == 'end':
                    ends.add(int(float(x['tick'])))
            except (ValueError, KeyError):
                pass
    st.sort()
    # c110 的标签会换：页面按席位号数。c116 的标签固定，没有 me= 行的页面（只有快照）也算一个页面。
    r['pages'] = len(set(seats.values()) | set(res_seats.values())) if card['cohort'] == 'squad20' else len(set(seats) | set(last) | set(res_seats))
    if st:
        groups = [[st[0]]]
        for x in st[1:]:
            if x[0] - groups[-1][-1][0] >= gap:
                groups.append([x])
            else:
                groups[-1].append(x)
        if len(st) > 1:
            r['gap'] = round(max(st[i + 1][0] - st[i][0] for i in range(len(st) - 1)), 1)
    e1_foreign = set()
    if len(groups) > 1:
        groups.sort(key=len, reverse=True)
        for g in groups[1:]:
            e1_foreign |= {b for _, b, _ in g}
        r['e1'] = '+'.join(str(len(g)) for g in groups)
    # E3：每组见过的队号（E1 没分开时，按 1.2 秒的细分组列出，只作旁证）
    fine = []
    for x in st:
        if fine and x[0] - fine[-1][-1][0] < 1.2:
            fine[-1].append(x)
        else:
            fine.append([x])
    if len(fine) > 1:
        fine.sort(key=len, reverse=True)
        r['teams'] = ' | '.join(','.join(sorted({k for _, _, ks in g if ks for k in ks})) or '-' for g in fine)

    # —— E2 名字 ——
    e2_foreign, e2_ok, pool_only = set(), set(), set()
    mp = os.path.join(OUT, mid, 'replay_meta.json')
    if os.path.exists(mp):
        meta = json.load(open(mp))
        names, H = meta['names'], meta['humans']
        if card.get('seededPlayers') != H and 'humans' not in seq:
            seq.append('humans')
        c110 = card['cohort'] == 'squad20'
        for b, p in seats.items():
            n = names[p] if p < min(H, len(names)) else None
            if n is None:
                e2_foreign.add(b)
            elif c110:
                up = n.upper()
                if n == b:
                    e2_ok.add(b)
                elif n.lower() in POOL or '[NPL]' in up or '[NOPE]' in up:
                    r['relabel'] += 1
                    e2_ok.add(b)
                    pool_only.add(b)
                else:
                    e2_foreign.add(b)
            else:
                if n.replace('[APEX] ', '') == b and n.startswith('[APEX]'):
                    e2_ok.add(b)
                else:
                    e2_foreign.add(b)
        # c110：录像里这个席位的名字只是“在池子里”（不等于标签）时，可能是撞名的路人（B009 的 12 号席位在录像那一场是 Russian Empire）。
        # 有 E1 分组时按席位号核一遍：这个席位所在的 E1 组里有对不上的席位、没有一个名字全等的席位 → 它也不在录像这一场。
        if c110 and pool_only and e2_foreign and len(groups) > 1:
            seat_group = {}
            for gi, g in enumerate(groups):
                for _, b, _ in g:
                    if b in res_seats:
                        seat_group[res_seats[b]] = gi
            foreign_seats = {seats[b] for b in e2_foreign}
            exact_seats = {seats[b] for b in e2_ok - pool_only}
            for b in sorted(pool_only):
                gi = seat_group.get(seats[b])
                if gi is None:
                    continue
                members = {q for q, x in seat_group.items() if x == gi}
                if members & foreign_seats and not (members & exact_seats):
                    e2_ok.discard(b); e2_foreign.add(b); r['relabel'] -= 1
        if e2_foreign:
            r['e2'] = f'{len(e2_ok)}+{len(e2_foreign)}'

    # —— 合并：录像这一场 = E2 对得上的页面；没有录像时主组 = E1 里页面最多的一组 ——
    if e2_foreign and e2_ok:
        # 录像可能是页面少的那一组录的：主组 = 页面多的一组
        foreign = e2_foreign if len(e2_foreign) <= len(e2_ok) else e2_ok
    elif e2_foreign:
        if 'replay' not in seq:
            seq.append('replay')     # 没有一个页面对得上：录像不是日志这一场
    if e1_foreign and not foreign:
        foreign = e1_foreign
    # 先后两场的判据优先：这些包的日志或录像本身就跨了两场（A094 的录像是第二场），名字对不上是结果不是原因
    if seq:
        r['kind'] = 'seq'
    elif foreign:
        r['kind'] = 'parallel'
    if seq:
        r['e2'] = (r['e2'] + ' ' if r['e2'] else '') + 'seq:' + '/'.join(seq)
    r['foreign'] = len(foreign)
    r['main'] = r['pages'] - r['foreign']
    r['foreignBots'] = ' '.join(sorted(foreign))
    r['endTicks'] = ' '.join(str(t) for t in sorted(ends))
    if foreign and res_tick:
        # 两组各自的 RESULT 行：拍号范围和 event 计数（另一间房的页面收场的拍和主组不同）
        def grp(bots):
            tk = [res_tick[b][0] for b in bots if b in res_tick]
            ev = {}
            for b in bots:
                if b in res_tick:
                    ev[res_tick[b][1]] = ev.get(res_tick[b][1], 0) + 1
            return (f"{min(tk)}–{max(tk)} " + '/'.join(f'{k}×{v}' for k, v in sorted(ev.items()))) if tk else '-'
        # c110 的标签会换：RESULT 行按席位号归组
        fs = {seats[b] for b in foreign if b in seats} if card['cohort'] == 'squad20' else set()
        isf = lambda b: b in foreign or res_seats.get(b) in fs
        r['resTicks'] = grp([b for b in res_tick if not isf(b)]) + ' | ' + grp([b for b in res_tick if isf(b)])
    return r


def load_split():
    """{局号: kind}，只含 kind != single 的包。给其他全量脚本用；表不存在时现算。"""
    f = os.path.join(OUT, '_all', 'match_split.csv')
    if os.path.exists(f):
        return {x['mid']: x['kind'] for x in csv.DictReader(open(f, encoding='utf8')) if x['kind'] != 'single'}
    P = pool()
    out = {}
    for m in sorted(os.listdir(DATA)):
        r = one(m, P, 3.0)
        if r['kind'] != 'single':
            out[m] = r['kind']
    return out


def main():
    a = sys.argv[1:]
    gap = float(a[a.index('--gap') + 1]) if '--gap' in a else 3.0
    ids = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--gap')] or sorted(os.listdir(DATA))
    P = pool()
    rows = [one(m, P, gap) for m in ids]
    print('局 | 编队 | 判定 | 页面数 = 主组 + 另一场 | 开局时刻最大间隔(秒) | E1 分组 | E2 名字 对上+对不上 | c110 换名 | 各组见过的队号 | 不在主组的号 | RESULT 行的拍号范围和 event：主组 | 另一场')
    for r in rows:
        if r['kind'] == 'single' and '--all' not in a:
            continue
        print(f"{r['mid']} | {r['cohort']} | {r['kind']} | {r['pages']} = {r['main']} + {r['foreign']} | {'-' if r['gap'] is None else r['gap']} | {r['e1'] or '-'} | {r['e2'] or '-'} | {r['relabel']} | {r['teams'] or '-'} | {r['foreignBots'] or '-'} | {r['resTicks'] or '-'}")
    if '--csv' in a:
        od = os.path.join(OUT, '_all')
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, 'match_split.csv'), 'w', newline='', encoding='utf8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f'# 已写 out/_all/match_split.csv（{len(rows)} 个包）')
    for co in sorted({r['cohort'] for r in rows}):
        L = [r for r in rows if r['cohort'] == co]
        par = [r for r in L if r['kind'] == 'parallel']
        sq = [r for r in L if r['kind'] == 'seq']
        print(f"# {co}：{len(L)} 个包；平行两场 {len(par)} 个（{' '.join(r['mid'] for r in par) or '-'}），页面 {sum(r['pages'] for r in par)} 个里不在主组的 {sum(r['foreign'] for r in par)} 个；"
              f"先后两场或录像对不上 {len(sq)} 个（{' '.join(r['mid'] for r in sq) or '-'}）；"
              f"c110 页面标签和进图名字不同的席位 {sum(r['relabel'] for r in L)} 个")
    # E4：一场对局只有一个收场拍
    me = [r for r in rows if len(r['endTicks'].split()) > 1]
    print(f"# E4 旁证：RESULT 行里 event=end 的拍号不止一个的包 {len(me)} 个：" + '；'.join(f"{r['mid']}（{r['endTicks']}，判定 {r['kind']}）" for r in me))
    # 20 人房
    seeded = {m: json.load(open(os.path.join(DATA, m, 'card.json'))).get('seededPlayers') for m in ids}
    r20 = [r for r in rows if seeded[r['mid']] == 20]
    if r20:
        print(f"# card.seededPlayers = 20 的包 {len(r20)} 个，其中平行两场 {sum(1 for r in r20 if r['kind'] == 'parallel')} 个；"
              f"平行两场的包里 seededPlayers 不是 20 的：{' '.join(r['mid'] + '=' + str(seeded[r['mid']]) for r in rows if r['kind'] == 'parallel' and seeded[r['mid']] != 20) or '无'}")


if __name__ == '__main__':
    main()
