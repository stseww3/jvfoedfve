#!/usr/bin/env python3
# m7_numcheck.py — 核对手写正文里的数：每一个数都要能在脚本产物（或复盘 JSON、模式表）里原样找到。
# 用法：python3 scripts/m7_numcheck.py [正文文件 …]      （默认 scripts/m7_src/*.md 和 scripts/m7_cards_src/*.md）
#   正文里的记号行（{{…}}）不查：那些是构建时从产物里原样拼进来的。
#   查的是「带小数、带百分号、带万 / 拍等单位、或 ≥3 位」的数；一两位的整数太常见，不查。
#   找不到的逐条印出来（文件:行号、数、所在的那一小段），退出码 1。
#   有三类数允许不在产物里：行号（L 开头）、版本和编号（A013、hub 0007、c116 …）、正文里明写「约」的概数——
#   这三类之外找不到的，都是抄错或者手算的，要回去改。
import sys, os, re, glob, json
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = ['out/m7/TABLES.md', 'out/m7/VERSIONS.md', 'out/m7/FUNNEL-BYTYPE.md', 'out/bundle_patterns.txt', 'out/bundle_cmdstream.txt', 'out/bundle_cmdstream_mine.txt', 'out/bundle_join.txt', 'out/bundle_humans.txt',
          'out/pattern_matrix.md', 'out/pattern_matrix.txt', 'out/pattern_evidence.txt', 'out/hub0007/m7_table.md', 'out/spawn_geometry.txt',
          'scripts/patterns_r04.json', 'out/m7/*.txt', 'out/*_all.txt', 'reviews/*.json', 'reports/M1-KNOWN-MECHANICS.md', 'reports/MECHANICS-B.md']
NUM = re.compile(r'(?<![\w.])[+\-−]?\d[\d,]*(?:\.\d+)?%?')
SKIP_BEFORE = re.compile(r'(?:[A-Za-z_#]|L|§|hub |统筹 |H|RFC-|TP|D|v)$')


def norm(tok):
    return tok.replace(',', '').replace('−', '-').lstrip('+')


def tokens(text):
    out = set()
    for m in NUM.finditer(text):
        out.add(norm(m.group(0)))
    return out


def main():
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not files:
        files = sorted(glob.glob(os.path.join(ROOT, 'scripts', 'm7_src', '*.md'))) + sorted(glob.glob(os.path.join(ROOT, 'scripts', 'm7_cards_src', '*.md')))
    corpus = set()
    for pat in CORPUS:
        for fp in glob.glob(os.path.join(ROOT, pat)):
            txt = open(fp, encoding='utf8').read()
            if fp.endswith('.json'):
                txt = txt.replace('\\n', '\n')
            corpus |= tokens(txt)
    plain = {t.rstrip('%') for t in corpus} | {t.lstrip('-') for t in corpus}
    bad = 0
    checked = 0
    for fp in files:
        for i, ln in enumerate(open(fp, encoding='utf8'), 1):
            if '{{' in ln:
                continue
            body = re.sub(r'`[^`]*`', ' ', ln)            # 代码、文件名、命令不查
            body = re.sub(r'^(#+\s*)\d+(?:\.\d+)*', r'\1', body)     # 标题开头的节号不查
            body = re.sub(r'\[[^\]]*\]\([^)]*\)', ' ', body)
            for m in NUM.finditer(body):
                tok = m.group(0)
                pre = body[max(0, m.start() - 6):m.start()]
                if SKIP_BEFORE.search(pre):
                    continue
                t = norm(tok)
                core = t.rstrip('%').lstrip('-')
                if '.' not in core and not t.endswith('%') and len(core) < 3:
                    continue
                if re.search(r'约\s*$', pre) or re.search(r'约\s*$', body[max(0, m.start() - 2):m.start()]):
                    continue
                checked += 1
                if t in corpus or (not t.endswith('%') and (t in plain or core in plain)):
                    continue
                bad += 1
                a, b = max(0, m.start() - 24), min(len(body), m.end() + 24)
                print('%s:%d  %s   …%s…' % (os.path.relpath(fp, ROOT), i, tok, body[a:b].strip()))
    print('# 查了 %d 个数，找不到出处的 %d 个' % (checked, bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
