#!/usr/bin/env python3
"""m6_build_report.py — 把 reports/m6-data/SUMMARY.tmpl.md（手写的正文）和 reports/m6-data/ 下机器生成的表拼成 reports/CROSS-MATCH-SUMMARY.md。

模板里的占位符（独占一行）：
  {{tables:<节名>#<n>}}     reports/m6-data/tables.md 里 “### <节名>” 下的第 n 个表（从 1 数）；节名 = overview / delay / land / ai / attrib / spawn / verdict
  {{patterns:min=<k>}}      reports/m6-data/patterns.md 的模式表里局数 ≥ k 的行
  {{patterns:families}}     同一文件的家族小计表
  {{file:<文件名>#<n>}}      reports/m6-data/<文件名> 里的第 n 个表（donations.md、boats.md）
  {{lines:<文件名>:<正则>}}  reports/m6-data/<文件名> 里匹配正则的行，原样放进代码块；正则后面加 @@N 只取前 N 行
这样表里的数字只有一个出处（scripts/m6_run_all.sh 生成的文件），正文手写的数字用 --check 核对：
  --check   把正文里出现的、带千分位或不带的 ≥4 位整数逐个在 reports/m6-data/ 的全部文件和 reviews/*.md 里找一遍，列出找不到的（人工看是不是笔误）。
用法：python3 scripts/m6_build_report.py [--check]
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..')
D = os.path.join(R, 'reports', 'm6-data')


def tables_of(text):
    """把一段 markdown 切成表（连续的以 | 开头的行）。"""
    out, cur = [], []
    for ln in text.split('\n'):
        if ln.startswith('|'):
            cur.append(ln)
        else:
            if cur:
                out.append('\n'.join(cur))
                cur = []
    if cur:
        out.append('\n'.join(cur))
    return out


def section(text, name):
    m = re.search(r'^### ' + re.escape(name) + r'\s*$', text, re.M)
    if not m:
        raise SystemExit(f'tables.md 里没有节 {name}')
    rest = text[m.end():]
    n = re.search(r'^### ', rest, re.M)
    return rest[:n.start()] if n else rest


def main():
    tmpl = open(os.path.join(D, 'SUMMARY.tmpl.md'), encoding='utf8').read()
    tables = open(os.path.join(D, 'tables.md'), encoding='utf8').read()
    patterns = open(os.path.join(D, 'patterns.md'), encoding='utf8').read()

    def repl(m):
        kind, arg = m.group(1), m.group(2)
        if kind == 'tables':
            name, n = arg.split('#')
            return tables_of(section(tables, name))[int(n) - 1]
        if kind == 'patterns':
            T = tables_of(patterns)
            if arg == 'families':
                return T[1]
            k = int(arg.split('=')[1])
            rows = T[0].split('\n')
            keep = rows[:2] + [r for r in rows[2:] if int(r.split('|')[3].strip()) >= k]
            return '\n'.join(keep)
        if kind == 'file':
            fn, n = arg.split('#')
            return tables_of(open(os.path.join(D, fn), encoding='utf8').read())[int(n) - 1]
        if kind == 'lines':
            fn, rx = arg.split(':', 1)
            lim = None
            if '@@' in rx:
                rx, lim = rx.rsplit('@@', 1)
                lim = int(lim)
            L = [ln.rstrip() for ln in open(os.path.join(D, fn), encoding='utf8') if re.search(rx, ln)][:lim]
            if not L:
                raise SystemExit(f'{fn} 里没有匹配 {rx} 的行')
            return '```\n' + '\n'.join(L) + '\n```'
        raise SystemExit(f'不认识的占位符 {m.group(0)}')

    out = re.sub(r'^\{\{(\w+):(.+?)\}\}[ \t]*$', repl, tmpl, flags=re.M)
    left = re.findall(r'\{\{.*?\}\}', out)
    if left:
        raise SystemExit(f'还有没展开的占位符：{left[:5]}')
    dst = os.path.join(R, 'reports', 'CROSS-MATCH-SUMMARY.md')
    open(dst, 'w', encoding='utf8').write(out)
    print(f'已写 {os.path.relpath(dst, R)}：{len(out.splitlines())} 行，{len(out)} 字符')

    if '--check' in sys.argv:
        hay = ''
        for f in glob.glob(os.path.join(D, '*')) + glob.glob(os.path.join(R, 'reviews', '*.md')) + glob.glob(os.path.join(R, 'notes', '*.md')):
            if f.endswith('SUMMARY.tmpl.md'):
                continue
            hay += open(f, encoding='utf8', errors='replace').read()
        hay_digits = set(re.findall(r'\d+', hay.replace(',', '')))
        prose = re.sub(r'^\{\{.*$', '', tmpl, flags=re.M)
        prose = re.sub(r'`[^`]*`', '', prose)          # 路径、命令里的数字不查
        miss = sorted({x for x in re.findall(r'(?<![\d.])\d{4,}(?![\d.])', prose.replace(',', '')) if x not in hay_digits}, key=int)
        print(f'正文里 ≥4 位的整数 {len(set(re.findall(r"(?<![0-9.])[0-9]{4,}(?![0-9.])", prose.replace(",", ""))))} 个，在数据文件和逐局报告里找不到的 {len(miss)} 个：{" ".join(miss)}')


if __name__ == '__main__':
    main()
