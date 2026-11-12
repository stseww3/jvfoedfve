#!/usr/bin/env python3
# m7_report_build.py — 把手写的正文（scripts/m7_src/*.md，按文件名顺序）和脚本排出来的表拼成 reports/CROSS-MATCH-SUMMARY.md。
# 表和单局证据不手抄：正文里单独一行的记号会被换成对应产物里的原文。
#   {{T:n}}            out/m7/TABLES.md 的第 n 张表（scripts/m7_totals.py 排的）
#   {{T:n+note}}       同上，连表后面那句脚本算的合计说明一起
#   {{OVERVIEW}}       out/pattern_matrix.md 的「对局一览」表（scripts/pattern_matrix.py --md）
#   {{MATRIX}}         out/pattern_matrix.md 的「模式 × 对局」表
#   {{EV:局:Dnn}}      reviews/<局>.json 里那条决策的 what 原文（一条列表项）
#   {{TP:局}}          reviews/<局>.json 的转折点标题（一条列表项，几个转折点用「→」连起来）
#   {{WHERE:模式}}     这个模式出现在哪些局、各判了什么（从 reviews/*.json 数）
#   {{CODE:模式}}      scripts/patterns_r04.json 里这个模式的代码位置
#   {{FILE:路径}}      把另一个脚本排好的 markdown 原样放进来（三级标题换成「表 …」的题注）
# {{T:n}} 会在表前面加一行题注「表 n　<TABLES.md 里的标题>」，正文里说「表 n」指的就是它。
# 用法：python3 scripts/m7_report_build.py [目标文件]
import sys, os, re, json, glob
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LET = {'error': '判错', 'good': '判对', 'unclear': '不明'}
SHORT = {'error': 'E', 'good': 'G', 'unclear': 'U'}


def sections(path, level):
    out, cur, title = {}, None, {}
    for ln in open(path, encoding='utf8'):
        ln = ln.rstrip('\n')
        m = re.match(r'^%s (\d+) (.*)$' % ('#' * level), ln)
        if m:
            cur = int(m.group(1))
            out[cur] = []
            title[cur] = m.group(2).strip()
        elif cur is not None:
            out[cur].append(ln)
    return out, title


def table_of(lines, note=False, caption=None):
    tab = [l for l in lines if l.startswith('|')]
    head = ['**%s**' % caption, ''] if caption else []
    if note:
        rest = [l for l in lines if l.strip() and not l.startswith('|')]
        return head + tab + ([''] + rest if rest else [])
    return head + tab


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'reports', 'CROSS-MATCH-SUMMARY.md')
    T, TT = sections(os.path.join(ROOT, 'out', 'm7', 'TABLES.md'), 3)
    M, _ = sections(os.path.join(ROOT, 'out', 'pattern_matrix.md'), 2)
    lib = json.load(open(os.path.join(ROOT, 'scripts', 'patterns_r04.json'), encoding='utf8'))
    revs = {}
    for fp in sorted(glob.glob(os.path.join(ROOT, 'reviews', '*.json'))):
        d = json.load(open(fp, encoding='utf8'))
        revs[d['matchId']] = d
    out = []
    srcs = sorted(glob.glob(os.path.join(ROOT, 'scripts', 'm7_src', '*.md')))
    if not srcs:
        raise SystemExit('scripts/m7_src/ 下没有正文')
    for src in srcs:
        for ln in open(src, encoding='utf8'):
            ln = ln.rstrip('\n')
            s = ln.strip()
            m = re.match(r'^\{\{T:(\d+)(\+note)?\}\}$', s)
            if m:
                n = int(m.group(1))
                if n not in T:
                    raise SystemExit('out/m7/TABLES.md 里没有第 %d 张表' % n)
                out += table_of(T[n], bool(m.group(2)), '表 %d　%s' % (n, TT[n]))
                continue
            m = re.match(r'^\{\{FILE:([\w./-]+)\}\}$', s)
            if m:
                p = os.path.join(ROOT, m.group(1))
                if not os.path.exists(p):
                    raise SystemExit('没有这个文件：' + m.group(1))
                body = open(p, encoding='utf8').read().rstrip('\n').split('\n')
                out += [re.sub(r'^### (.*)$', r'**表 \1**', l) for l in body]
                continue
            if s == '{{OVERVIEW}}':
                out += table_of(M[1])
                continue
            if s == '{{MATRIX}}':
                out += table_of(M[2])
                continue
            m = re.match(r'^\{\{EV:(\w+):(D\d+)\}\}$', s)
            if m:
                mid, did = m.groups()
                x = [x for x in revs[mid]['decisions'] if x['id'] == did]
                if len(x) != 1:
                    raise SystemExit('%s 里没有 %s' % (mid, did))
                x = x[0]
                out.append('- **%s %s**（%s 拍；%s；%s）：%s' % (mid, did, x['t'], x['bot'], LET[x['verdict']], x['what']))
                continue
            m = re.match(r'^\{\{TP:(\w+)\}\}$', s)
            if m:
                d = revs[m.group(1)]
                tps = [tp.get('what') or tp.get('title') for tp in d['turningPoints']]
                out.append('- **%s**（%s，%s）：%s' % (d['matchId'], d['outcome']['result'], d['lossArchetype'], ' → '.join(tps)))
                continue
            m = re.match(r'^\{\{WHERE:([\w-]+)\}\}$', s)
            if m:
                pid = m.group(1)
                hit = []
                for mid in sorted(revs):
                    v = [SHORT[x['verdict']] for x in revs[mid]['decisions'] if x['patternId'] == pid]
                    if v:
                        hit.append('%s %s' % (mid, '/'.join(v)))
                if not hit:
                    raise SystemExit('没有局用到 ' + pid)
                ne = sum(1 for h in hit if 'E' in h.split(' ')[1])
                out.append('- `%s`（%s）：%d 局出现、%d 局判错 —— %s。' % (pid, lib[pid]['name'], len(hit), ne, '、'.join(hit)))
                continue
            m = re.match(r'^\{\{CODE:([\w-]+)\}\}$', s)
            if m:
                out.append('代码位置（`%s`）：%s' % (m.group(1), lib[m.group(1)]['codePath']))
                continue
            if '{{' in ln:
                raise SystemExit('认不出的记号：' + ln)
            out.append(ln)
        out.append('')
    with open(dst, 'w', encoding='utf8') as f:
        f.write('\n'.join(out).rstrip('\n') + '\n')
    print('写出 %s：%d 行（正文 %d 个文件）' % (os.path.relpath(dst, ROOT), len(out), len(srcs)))


if __name__ == '__main__':
    main()
