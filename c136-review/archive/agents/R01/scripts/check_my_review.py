#!/usr/bin/env python3
"""check_my_review.py — 用 c136-review/tools/collect-reviews.py 里的 check_review 在本地预检我的复盘。
用法: python3 check_my_review.py [matchId ...]   （不给参数 = reviews/ 下全部）
"""
import importlib.util, json, os, sys, glob
sys.dont_write_bytecode = True  # 不往 c136-review/tools/__pycache__ 里写东西（那不是我的目录）
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'tools', 'collect-reviews.py'))
spec = importlib.util.spec_from_file_location('collect_reviews', TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
RV = os.path.join(HERE, '..', 'reviews')
ids = sys.argv[1:] or sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(RV, '*.json')))
bad = 0
for mid in ids:
    jp = os.path.join(RV, mid + '.json'); mp = os.path.join(RV, mid + '.md')
    try:
        doc = json.load(open(jp))
    except Exception as e:
        print(f'{mid}: JSON 解析失败 {e}'); bad += 1; continue
    md = open(mp).read() if os.path.exists(mp) else None
    fails, stats = mod.check_review(doc, md)
    lines = md.count('\n') if md else 0
    print(f"{mid}: {'全过' if not fails else '未过: ' + '；'.join(fails)} | timeline={stats['timeline']} tp={stats['turningPoints']} deaths={stats['deaths']} "
          f"decisions={stats['decisions']} verdicts={stats['verdicts']} newPatterns={stats['newPatterns']} mdLines={lines} proposalHints={stats['proposalHints']}")
    bad += bool(fails) or bool(stats['proposalHints'])
sys.exit(1 if bad else 0)
