#!/usr/bin/env python3
"""cards_check.py — 把卡片 / 报告正文里的每个数字和它标注的出处表逐个核对，对不上的列出来。

「没有脚本的数字不收」的最后一道闸：卡片（cards/*.md）和手写报告里的数字都带出处标记，标记指向的表都是脚本生成的。
这个脚本不重算任何东西，只检查「正文里的这个数，在它标注的那张表里有没有原样出现」。

出处标记（方括号，写在一句话的后面）：
  [PS …]      reports/PATTERN-SCAN.md
  [DL …]      reports/DELAY-AND-LAND-ACCOUNT.md
  [CL …]      reports/CROSS-LEDGER.md
  [RO …]      reports/REVIEW-ROLLUP.md
  [tsv]       out/pattern-scan.tsv、out/pattern-scan2.tsv：数字必须出现在同一句里提到的那一局的那一行
  [复盘 局号…] reviews/<局>.md + reviews/<局>.json；只写 [复盘] 时取同一段里出现的局号，没有局号就取全部 13 局
一行按标记切成若干段：一个标记管它前面、上一个标记之后的那段文字；紧挨着的几个标记一起管同一段。
没有标记的文字（定义、机制、读法）对「全部出处」核对：四份表 + 13 局复盘 + scripts/ 源码 + 策略 / 协调器 / 引擎源码 + params-diff。

数字的切法：连续的数字（可带千分位逗号、小数点）加可选的后缀 % / M / k；千分位逗号去掉后按字符串比较。
不核对的：反引号里的内容（代码、文件名、模式键）、L 开头的行号、局号、标记本身、证据等级（E1×13）；[tsv] 段里的「a–b 拍」（窗口名）。
「17%（28/166）」这种写法直接验算（百分数 = 括号里两个数相除，四舍五入到整数）。

对不上的数字如果是「两格相除 / 相加 / 换单位」得到的，在 cards/CHECK-ALLOW.tsv 里登记一行（文件、数字、怎么来的），
脚本把它们单列为「登记过的派生数」，不算错。

用法：python3 scripts/cards_check.py [文件…] [--all]     不给文件时核对 cards/*.md；--all 再加上 reports/CROSS-MATCH-SUMMARY.md、
      reports/COUNCIL-PROPOSAL.md（如果有）。有对不上的数字时退出码 1。
      python3 scripts/cards_check.py [--all] --selftest   随机改数试验，量这个核对的检出率。

局限：只核对「这个数在出处表里出现过」，不核对它出现在哪一格；没有标记的文字对全部出处核对，更松。
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get('C136_DATA', '/agent/repos/c136-data')
MATCHES = ['A014', 'A017', 'A021', 'A026', 'A030', 'A034', 'A037', 'A043', 'A058', 'A065', 'A093', 'A095', 'B010']

NUM = re.compile(r'(?<![A-Za-z_\d.])(\d[\d,]*(?:\.\d+)?)(%|M|k)?(?![\d])')
TAG = re.compile(r'\[(PS|DL|CL|RO|tsv|复盘)([^\]]*)\]')
MID = re.compile(r'\b([AB]\d{3})\b')


def norm(num, unit):
    num = num.rstrip(',')
    return num.replace(',', '') + (unit or '')


def tokens(text):
    text = re.sub(r'`[^`]*`', ' ', text)
    text = re.sub(r'\bL\d+(?:[–-]\d+)?', ' ', text)
    text = re.sub(r'\bE\d(?:×\d+)?', ' ', text)
    text = re.sub(r'^#+\s*\d+(?:\.\d+)*\.?\s', ' ', text)          # 标题的节号
    text = re.sub(r'(?<![\d.,])0\d{2,}(?:-\d+)?(?![\d.,%])', ' ', text)   # 0003、0004-2 这类编号
    text = MID.sub(' ', text)
    text = text.replace('，', ', ').replace('、', ' ')
    out = []
    for m in NUM.finditer(text):
        out.append(norm(m.group(1), m.group(2)))
    return out


def corpus_tokens(text):
    text = MID.sub(' ', text)
    text = text.replace('，', ', ').replace('、', ' ')
    s = set()
    for m in NUM.finditer(text):
        s.add(norm(m.group(1), m.group(2)))
        s.add(norm(m.group(1), None))
    return s


def read(path):
    try:
        return open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return ''


_cache = {}


def corpus(key):
    if key in _cache:
        return _cache[key]
    if key == 'PS':
        s = corpus_tokens(read(f'{ROOT}/reports/PATTERN-SCAN.md'))
    elif key == 'DL':
        s = corpus_tokens(read(f'{ROOT}/reports/DELAY-AND-LAND-ACCOUNT.md'))
    elif key == 'CL':
        s = corpus_tokens(read(f'{ROOT}/reports/CROSS-LEDGER.md'))
    elif key == 'RO':
        s = corpus_tokens(read(f'{ROOT}/reports/REVIEW-ROLLUP.md'))
    elif key.startswith('REV:'):
        m = key[4:]
        s = corpus_tokens(read(f'{ROOT}/reviews/{m}.md')) | corpus_tokens(read(f'{ROOT}/reviews/{m}.json'))
    elif key == 'ALL':
        s = set()
        for k in ('PS', 'DL', 'CL', 'RO'):
            s |= corpus(k)
        for m in MATCHES:
            s |= corpus('REV:' + m)
        for f in glob.glob(f'{HERE}/*'):
            if f.endswith(('.py', '.mjs', '.cjs', '.sh')):
                s |= corpus_tokens(read(f))
        for f in glob.glob(f'{SRC}/src/strategy/*.js') + glob.glob(f'{SRC}/src/strategy/*.mjs') + [f'{SRC}/src/strategy/params-diff.txt', f'{SRC}/src/sim/sim/game.js']:
            s |= corpus_tokens(read(f))
    else:
        s = set()
    _cache[key] = s
    return s


_tsv = None


def tsv_rows():
    global _tsv
    if _tsv is None:
        _tsv = {}
        for f in ('pattern-scan.tsv', 'pattern-scan2.tsv'):
            p = f'{ROOT}/out/{f}'
            if not os.path.exists(p):
                continue
            for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
                mid = r.get('matchId') or r.get('match') or r.get('局')
                if mid:
                    _tsv.setdefault(mid, set()).update(corpus_tokens(' '.join(str(v) for v in r.values())))
    return _tsv


TICKS = re.compile(r'\d[\d,]*(?:[–-]\d[\d,]*)?\+? ?拍')
RATIO = re.compile(r'(\d+(?:\.\d+)?)%（(\d[\d,]*)\s*/\s*(\d[\d,]*)）')


def ratio_ok(seg, t):
    """「17%（28/166）」这种写法：百分数就是括号里两个数相除，直接验算。"""
    if not t.endswith('%'):
        return False
    for m in RATIO.finditer(seg):
        if m.group(1) + '%' == t:
            a, b = int(m.group(2).replace(',', '')), int(m.group(3).replace(',', ''))
            if b and round(100 * a / b) == round(float(m.group(1))):
                return True
    return False


def check_tsv(seg):
    """[tsv] 段：每个局号后面的数字必须出现在那一局的行里（「a–b 拍」是窗口名，不核对；「x%（a/b）」验算）。"""
    bad = []
    parts = re.split(r'\b([AB]\d{3})\b', seg)
    rows = tsv_rows()
    for i in range(1, len(parts), 2):
        mid, txt = parts[i], parts[i + 1]
        have = rows.get(mid, set())
        for t in tokens(TICKS.sub(' ', txt)):
            if t not in have and t.rstrip('%Mk') not in have and not ratio_ok(txt, t):
                bad.append((t, f'{mid} 的行'))
    return bad


def segments(line):
    """把一行切成 (文字, [标记…])；紧挨着的标记合并；最后一段没有标记。"""
    out, pos, pending = [], 0, None
    for m in TAG.finditer(line):
        text = line[pos:m.start()]
        if pending is not None and text.strip() == '':
            pending[1].append((m.group(1), m.group(2)))
        else:
            if pending is not None:
                out.append(tuple(pending))
            pending = [text, [(m.group(1), m.group(2))]]
        pos = m.end()
    if pending is not None:
        out.append(tuple(pending))
    tail = line[pos:]
    if tail.strip():
        out.append((tail, []))
    return out


def check_file(path, allow):
    rel = os.path.relpath(path, ROOT)
    bad, derived, n = [], [], 0
    in_code = False
    para_mids = []
    for ln, line in enumerate(read(path).split('\n'), 1):
        if line.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith('#') or not line.strip():
            para_mids = []
        para_mids = MID.findall(line) or para_mids
        for text, tags in segments(line):
            toks = tokens(text)
            if not toks:
                continue
            n += len(toks)
            if any(k == 'tsv' for k, _ in tags):
                miss = check_tsv(text)
                where = 'tsv'
            else:
                have = set()
                names = []
                for k, arg in tags:
                    if k == '复盘':
                        mids = MID.findall(arg) or MID.findall(text) or para_mids or MATCHES
                        for m in mids:
                            have |= corpus('REV:' + m)
                        names.append('复盘 ' + '、'.join(mids))
                        for extra in re.findall(r'\b(PS|DL|CL|RO)\b', arg):
                            have |= corpus(extra)
                    else:
                        have |= corpus(k)
                        names.append(k)
                        for extra in re.findall(r'\b(PS|DL|CL|RO)\b', arg):
                            have |= corpus(extra)
                        if '复盘' in arg:
                            mids = MID.findall(arg) or MID.findall(text) or para_mids or MATCHES
                            for m in mids:
                                have |= corpus('REV:' + m)
                            names.append('复盘 ' + '、'.join(mids))
                if not tags:
                    have = corpus('ALL')
                    names = ['全部出处']
                where = '＋'.join(names)
                miss = [(t, where) for t in toks if t not in have and not ratio_ok(text, t)]
            for t, w in miss:
                if (rel, t) in allow or (os.path.basename(rel), t) in allow:
                    derived.append((ln, t, allow.get((rel, t)) or allow.get((os.path.basename(rel), t))))
                else:
                    snippet = text.strip()
                    i = snippet.find(t.rstrip('%Mk')[:6])
                    snippet = snippet[max(0, i - 28): i + 34] if i >= 0 else snippet[:60]
                    bad.append((ln, t, w, snippet))
    return rel, n, bad, derived


def selftest(files, allow):
    """随机改数试验：在带出处标记的正文行里，把标记之前的一个 ≥3 位的数字加 1，看核对抓不抓得到。
    抓不到的 = 改完的数碰巧也在出处表里出现过（这个核对只看「出现过」，不看「出现在哪一格」）。"""
    import random
    import tempfile
    random.seed(7)
    tot = hit = 0
    pat = re.compile(r'(?<![\dA-Za-z_.,L])(\d{1,3}(?:,\d{3})+|\d{3,})(?![\d.,%Mk])')
    for f in files:
        if os.path.basename(f) == 'README.md':
            continue
        lines = read(f).split('\n')
        cand = []
        for i, l in enumerate(lines):
            if l.startswith('|') or not TAG.search(l):
                continue
            for m in pat.finditer(l):
                if TAG.search(l[m.end():]):
                    cand.append((i, m.start(), m.end()))
        random.shuffle(cand)
        for i, a, b in cand[:3]:
            l = lines[i]
            new = str(int(l[a:b].replace(',', '')) + 1)
            mut = list(lines)
            mut[i] = l[:a] + new + l[b:]
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, os.path.basename(f))
                open(p, 'w', encoding='utf-8').write('\n'.join(mut))
                _, _, bad, _ = check_file(p, allow)
            tot += 1
            hit += 1 if bad else 0
    print(f'随机改数试验：改了 {tot} 处，抓到 {hit} 处')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    files = [os.path.abspath(a) for a in args] or sorted(glob.glob(f'{ROOT}/cards/*.md'))
    if '--all' in sys.argv:
        for f in ('reports/CROSS-MATCH-SUMMARY.md', 'reports/COUNCIL-PROPOSAL.md'):
            if os.path.exists(f'{ROOT}/{f}'):
                files.append(f'{ROOT}/{f}')
    allow = {}
    ap = f'{ROOT}/cards/CHECK-ALLOW.tsv'
    if os.path.exists(ap):
        for r in csv.reader(open(ap, encoding='utf-8'), delimiter='\t'):
            if len(r) >= 3 and not r[0].startswith('#'):
                allow[(r[0], r[1])] = r[2]
    if '--selftest' in sys.argv:
        selftest(files, allow)
        return
    tot = totbad = totder = 0
    for f in files:
        if os.path.basename(f) in ('README.md',):
            continue
        rel, n, bad, derived = check_file(f, allow)
        tot += n
        totbad += len(bad)
        totder += len(derived)
        print(f'{rel}：数字 {n} 个，对不上 {len(bad)} 个，登记过的派生数 {len(derived)} 个')
        for ln, t, w, snip in bad:
            print(f'    第 {ln} 行  {t}  不在 [{w}] 里｜…{snip}…')
    print(f'合计：数字 {tot} 个，对不上 {totbad} 个，登记过的派生数 {totder} 个')
    sys.exit(1 if totbad else 0)


if __name__ == '__main__':
    main()
