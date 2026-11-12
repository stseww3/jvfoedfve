#!/usr/bin/env python3
# council_attrcheck.py — 议会提案的「归属核对」：m7_numcheck.py 只保证每个数在产物里出现过，
# 这个脚本再查一层：正文里一行（或表格的一行）如果点了局号，这一行里的数是不是出现在「这几局自己的」产物里。
# 用法：python3 scripts/council_attrcheck.py [正文文件]      （默认 reports/COUNCIL-PROPOSAL.md）
#   每局自己的产物 = reviews/<局>.json、reviews/<局>.md、out/<局>/ 下的文本、out/digest/<局>.txt、
#   以及各张合计表（out/m7/*.md、out/m7/*.txt、out/*_all.txt、out/hub0007/m7_table.md、out/hub-resim-check.txt、
#   out/engine-replay-check.txt、out/spawn_geometry.txt）里以这个局号开头的行。
#   一行里点了几个局，数只要在其中一局的产物里就算对上。
#   对不上的逐条印出来：它可能是全量的数（不属于哪一局，正常），也可能是张冠李戴，要人看。
#   查的数和 m7_numcheck.py 同一个口径（带小数、带百分号、或三位以上；代码体里的不查）。
#   --strict：每局自己的产物只算复盘（reviews/<局>.json、.md）和合计表里这一局的行，不算 out/<局>/ 下的大文件。
#   大文件里三位数很容易碰巧出现；严格档对不上的更多，用来列一张人工复核的单子。
import sys, os, re, glob
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUM = re.compile(r'(?<![\w.])[+\-−]?\d[\d,]*(?:\.\d+)?%?')
SKIP_BEFORE = re.compile(r'(?:[A-Za-z_#]|L|§|hub |统筹 |H|RFC-|TP|D|v)$')
MID = re.compile(r'(?<![A-Za-z0-9])([AB]\d{3})(?![0-9])')
SHARED = ['out/m7/*.md', 'out/m7/*.txt', 'out/*_all.txt', 'out/hub0007/m7_table.md', 'out/hub-resim-check.txt',
          'out/engine-replay-check.txt', 'out/spawn_geometry.txt', 'out/pattern_evidence.txt']


STRICT = '--strict' in sys.argv


def norm(tok):
    return tok.replace(',', '').replace('−', '-').lstrip('+')


def tokens(text):
    return {norm(m.group(0)) for m in NUM.finditer(text)}


def wanted(text):
    out = []
    text = re.sub(r'`[^`]*`', ' ', text)
    for m in NUM.finditer(text):
        tok = m.group(0)
        if SKIP_BEFORE.search(text[:m.start()][-6:]):
            continue
        n = norm(tok)
        core = n.rstrip('%').lstrip('-')
        if '.' not in core and not n.endswith('%') and len(core) < 3:
            continue
        out.append(n)
    return out


def corpus_for(mid, cache={}):
    if mid in cache:
        return cache[mid]
    toks = set()
    files = [f'reviews/{mid}.json', f'reviews/{mid}.md']
    if not STRICT:
        files += [f'out/digest/{mid}.txt'] + sorted(glob.glob(os.path.join(ROOT, 'out', mid, '*')))
    for fp in files:
        fp = fp if os.path.isabs(fp) else os.path.join(ROOT, fp)
        if not os.path.isfile(fp) or os.path.getsize(fp) > 30_000_000:
            continue
        try:
            txt = open(fp, encoding='utf8').read()
        except UnicodeDecodeError:
            continue
        if fp.endswith('.json'):
            txt = txt.replace('\\n', '\n')
        toks |= tokens(txt)
    for pat in SHARED:
        for fp in glob.glob(os.path.join(ROOT, pat)):
            for line in open(fp, encoding='utf8'):
                s = line.lstrip('|# ').lstrip()
                if s.startswith(mid):
                    toks |= tokens(line)
    cache[mid] = toks
    return toks


def main():
    files = [a for a in sys.argv[1:] if not a.startswith('--')] or ['reports/COUNCIL-PROPOSAL.md']
    checked = missing = 0
    for f in files:
        fp = f if os.path.isabs(f) else os.path.join(ROOT, f)
        for ln, line in enumerate(open(fp, encoding='utf8'), 1):
            # 一句一句查：句子里点了局号，才查这一句里的数。
            # 表格的一行：第一格点的局号管这一整行（别的格里的句子再各自加上自己点的局号）。
            row_mids, segs = [], []
            if line.startswith('|'):
                cells = [c for c in line.strip().strip('|').split('|')]
                row_mids = MID.findall(cells[0]) if cells else []
                for c in cells:
                    segs += re.split(r'(?<=[。；])', c)
            else:
                segs = re.split(r'(?<=[。；])', line)
            for seg in segs:
                mids = sorted(set(MID.findall(seg)) | set(row_mids))
                if not mids:
                    continue
                want = wanted(seg)
                if not want:
                    continue
                have = set()
                for m in mids:
                    have |= corpus_for(m)
                for n in want:
                    checked += 1
                    if n not in have:
                        missing += 1
                        print(f'{os.path.basename(f)}:{ln} [{",".join(mids)}] {n}  ←  {seg.strip()[:150]}')
    print(f'# 归属核对：点了局号的句子里查了 {checked} 个数，在所点的局自己的产物里找不到的 {missing} 个')


if __name__ == '__main__':
    main()
