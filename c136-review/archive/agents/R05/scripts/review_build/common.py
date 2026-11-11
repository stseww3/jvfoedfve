# common.py — 复盘 JSON 组装的公共部分：读 review_skel.py 的骨架、挑时间线点、用 collect-reviews.py 的规则自检。
# 每局一个 <matchId>.py：机械数字取自骨架，分析文字写在脚本里，运行后生成 reviews/<matchId>.json 并自检。
import json, sys, importlib.util
sys.dont_write_bytecode = True   # 不往 c136-review/tools/__pycache__ 里写东西（只读区）
ROOT = '/agent/repos/c136-r05/c136-review'
def skel(mid):
    return json.load(open(f'/tmp/c136-r05/skel/{mid}.json'))
def pick_timeline(S, notes):
    out = []
    for r in S['timeline']:
        if r['t'] in notes:
            x = dict(r); x['note'] = notes[r['t']]; out.append(x)
    return out
def check(mid):
    spec = importlib.util.spec_from_file_location('cr', f'{ROOT}/tools/collect-reviews.py')
    cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
    doc = json.load(open(f'{ROOT}/agents/R05/reviews/{mid}.json'))
    try:
        md = open(f'{ROOT}/agents/R05/reviews/{mid}.md', encoding='utf-8').read()
    except FileNotFoundError:
        md = None
    fails, stats = cr.check_review(doc, md)
    print('未过项:', fails)
    print('统计:', json.dumps(stats, ensure_ascii=False))
    if md is not None:
        print('md 行数:', md.count('\n'))
def dump(mid, doc):
    json.dump(doc, open(f'{ROOT}/agents/R05/reviews/{mid}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写入', f'{ROOT}/agents/R05/reviews/{mid}.json', len(json.dumps(doc, ensure_ascii=False)), '字符')
