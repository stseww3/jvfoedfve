#!/usr/bin/env python3
# log_alias.py — 日志里的号名 → 引擎编号。
# B 组（c110，没有队标）的日志行只带号名，而且同一个号的号名中途会换（B034：Kilwa → Ganondorf → Nelson）；
# 影子表（tmp/shadow/<局号>/）在 B 组用引擎编号当号的标签。两边要对上，只能靠内容：
#   对局包 traj.csv 的每一行（号名, 拍, 领土, 余额）去真引擎状态表 tmp/truth/<局号>/state.tsv 里找「同一拍、领土和余额都相同」的真人位，
#   一个号名的各行投票，票最多的编号就是它（开局 90 拍大家都是 12 格 / 同样的兵，这种多解的行不计票）。
#   [HL-GAME-INIT] … me=N 的行直接给出开局号名的编号，用来核对。
# 用法：python3 scripts/log_alias.py <局号>            打印号名表
#       python3 scripts/log_alias.py <局号> --check    再拿影子表 rows.tsv 核对：日志快照的 领土 / 余额 / 邻居数 / 无主地边数 与影子同拍的值是否相同
# 其他脚本用：import log_alias; log_alias.alias(mid) → {号名: 引擎编号}
import sys, os, re, csv, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')


def _state(mid):
    st = collections.defaultdict(dict)
    with open(os.path.join(ROOT, 'tmp', 'truth', mid, 'state.tsv'), encoding='utf8') as f:
        rd = csv.reader(f, delimiter='\t')
        next(rd)
        for r in rd:
            st[int(r[0])][int(r[1])] = (int(r[2]), int(r[3]))
    return st


def _traj(mid):
    rows = []
    fp = os.path.join(DATA, 'bundles', mid, 'traj.csv')
    if not os.path.exists(fp):
        return rows
    with open(fp, encoding='utf8') as f:
        for r in csv.DictReader(f):
            try:
                rows.append(dict(bot=r['bot'], t=int(r['t']), terr=int(r['terr']), bal=int(r['bal']), nb=int(r['nb']), neut=int(r['neut']), cmds=int(r['cmds'])))
            except (ValueError, KeyError):
                pass
    return rows


def alias(mid, detail=False):
    st = _state(mid)
    votes = collections.defaultdict(collections.Counter)
    nrows = collections.Counter()
    for r in _traj(mid):
        nrows[r['bot']] += 1
        hit = [p for p, v in st.get(r['t'], {}).items() if v == (r['terr'], r['bal'])]
        if len(hit) == 1:
            votes[r['bot']][hit[0]] += 1
    init = {}
    rx = re.compile(r'\[([^\]]+)\] \[HL-GAME-INIT\].* me=(\d+)')
    lp = os.path.join(DATA, 'bundles', mid, 'in_game.log')
    if os.path.exists(lp):
        with open(lp, encoding='utf8', errors='replace') as f:
            for line in f:
                m = rx.search(line)
                if m:
                    init[m.group(1)] = int(m.group(2))
    out, info = {}, {}
    for b in set(nrows) | set(init):
        v = votes.get(b)
        best = v.most_common(1)[0] if v else None
        p = best[0] if best else init.get(b)
        if p is None:
            continue
        out[b] = p
        info[b] = dict(p=p, rows=nrows[b], votes=best[1] if best else 0, init=init.get(b), other=sum(v.values()) - best[1] if best else 0)
    return (out, info) if detail else out


def first_names(mid):
    """{后来换上的号名: 录像里这个号的名字}。一个号只有一个号名的局（A 组）返回 {}，调用方不用区分。"""
    try:
        al = alias(mid)
        meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    except Exception:
        return {}
    name = {p['p']: p['name'] for p in meta['players']}
    byp = collections.defaultdict(set)
    for b, p in al.items():
        byp[p].add(b)
    if not any(len(v) > 1 for v in byp.values()):
        return {}
    return {b: name[p] for b, p in al.items() if p in name and b != name[p]}


def main():
    a = sys.argv[1:]
    mid = a[0]
    al, info = alias(mid, True)
    meta = json.load(open(os.path.join(ROOT, 'tmp', 'truth', mid, 'meta.json'), encoding='utf8'))
    name = {p['p']: p['name'] for p in meta['players']}
    byp = collections.defaultdict(list)
    for b, p in al.items():
        byp[p].append(b)
    print('# %s 日志号名 → 引擎编号（traj.csv 的行按「同拍、领土和余额都相同」去 state.tsv 里认）' % mid)
    first = {}
    for r in _traj(mid):
        first.setdefault(r['bot'], r['t'])
        first[r['bot']] = min(first[r['bot']], r['t'])
    for p in sorted(byp):
        bs = sorted(byp[p], key=lambda b: first.get(b, 0))
        print('  #%d（录像里的名字 %s）：%s' % (p, name.get(p, '?'), ' → '.join(
            '%s（%d 行，认出 %d 行%s%s）' % (b, info[b]['rows'], info[b]['votes'], '，另有 %d 行指到别的号' % info[b]['other'] if info[b]['other'] else '',
                                     '，GAME-INIT me=%d' % info[b]['init'] if info[b]['init'] is not None else '') for b in bs)))
    bad = [b for b in info if info[b]['init'] is not None and info[b]['votes'] and info[b]['init'] != info[b]['p']]
    print('  和 GAME-INIT 对不上的号名：%s' % ('、'.join(bad) or '无'))
    if '--check' in a:
        fp = os.path.join(ROOT, 'tmp', 'shadow', mid + '.all', 'rows.tsv')
        if not os.path.exists(fp):
            fp = os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv')
        sh = {}
        with open(fp, encoding='utf8') as f:
            rd = csv.reader(f, delimiter='\t')
            h = next(rd)
            ix = {k: i for i, k in enumerate(h)}
            for r in rd:
                sh[(int(r[ix['bot']]) if r[ix['bot']].isdigit() else r[ix['bot']], int(r[ix['t']]))] = (int(r[ix['terr']]), int(r[ix['bal']]), int(r[ix['nb']]), int(r[ix['neut']]))
        same = diff = miss = 0
        dl = []
        for r in _traj(mid):
            p = al.get(r['bot'])
            v = sh.get((p, r['t'])) or sh.get((r['bot'], r['t']))
            if v is None:
                miss += 1
                continue
            if v == (r['terr'], r['bal'], r['nb'], r['neut']):
                same += 1
            else:
                diff += 1
                if len(dl) < 8:
                    dl.append('%s t=%d 日志 %s 影子 %s' % (r['bot'], r['t'], (r['terr'], r['bal'], r['nb'], r['neut']), v))
        print('  影子核对（%s）：日志快照 %d 行里，影子同拍有记录的 %d 行：领土 / 余额 / 邻居数 / 无主地边数 全相同 %d 行，不同 %d 行；影子没有这一拍记录的 %d 行（出局那一拍之后或非行动拍）' % (
            os.path.relpath(fp, ROOT), same + diff + miss, same + diff, same, diff, miss))
        for x in dl:
            print('    ' + x)


if __name__ == '__main__':
    main()
