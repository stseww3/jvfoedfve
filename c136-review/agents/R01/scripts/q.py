#!/usr/bin/env python3
"""q.py — 对 out/<mid>/ 下任意一张 CSV 做一次性的筛选与汇总，让复盘里的零散数字都有一行可复现的命令。
用法：python3 q.py <matchId> <表名(不带 .csv)> [--where "python 表达式"] [--agg count,min:col,max:col,sum:col,med:col,uniq:col] [--by col] [--show col1,col2,.. [--limit N]]
表达式里直接用列名（列名是 python 关键字时加下划线，如 from_）；数字列自动转成数，其余是字符串。例：
  python3 q.py A059 dispatch_audit --where "t<2142" --agg count,min:cost,max:cost,min:cap,max:cap,min:maxByQuota,max:maxByQuota
  python3 q.py A059 shadow_cmds --where "bot=='zexos1' and ok==1 and 1500<=t<=2105 and kind=='attack'" --agg count --by targetName
"""
import csv, os, statistics, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def num(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v.strip('"')


def main():
    a = sys.argv[1:]
    mid, table = a[0], a[1]
    opt = lambda k, d=None: a[a.index('--' + k) + 1] if '--' + k in a else d
    rows = [{k: num(v) for k, v in r.items()} for r in csv.DictReader(open(os.path.join(HERE, '..', 'out', mid, table + '.csv'), encoding='utf8'))]
    import keyword
    for r in rows:   # 列名是 python 关键字（如 from）时，表达式里用 from_ 引用
        for k in [k for k in r if keyword.iskeyword(k)]:
            r[k + '_'] = r[k]
    w = opt('where')
    if w:
        code = compile(w, 'where', 'eval')
        rows = [r for r in rows if eval(code, {}, r)]
    by = opt('by')
    groups = defaultdict(list)
    for r in rows:
        groups[r[by] if by else 'all'].append(r)
    aggs = (opt('agg') or 'count').split(',')
    for g, rs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        out = []
        for ag in aggs:
            if ag == 'count':
                out.append(f'count={len(rs)}')
                continue
            f, c = ag.split(':')
            vals = [r[c] for r in rs if r[c] != '']
            if f == 'uniq':
                out.append(f'uniq:{c}={sorted(set(vals), key=str)}')
            elif not vals:
                out.append(f'{f}:{c}=-')
            else:
                v = {'min': min, 'max': max, 'sum': sum, 'med': statistics.median}[f](vals)
                out.append(f'{f}:{c}={v}')
        print(f'{g}: ' + ' '.join(out))
    show = opt('show')
    if show:
        cols = show.split(',')
        print(','.join(cols))
        for r in rows[: int(opt('limit', '40'))]:
            print(','.join(str(r[c]) for c in cols))


if __name__ == '__main__':
    main()
