#!/usr/bin/env python3
# review_write.py — 把「数字骨架」（review_base.py 从真相表算出来的 context/outcome/timeline/deaths）
# 和人工写的判断部分（review-src/<局号>.json）合并成 reviews/<局号>.json，并用总部的 check_review() 当场检查。
# 用法：python3 scripts/review_write.py <局号> [--ours 1,2,3]
# 人工部分里：
#   - 顶层键直接覆盖骨架；context / outcome 是「补充」而不是覆盖（同名键以人工为准）。
#   - deathCauses: { "号名": "死因" }，按号名填进骨架 deaths[].cause；骨架里有而这里没写死因的会报错。
#   - timelineNotes: { "拍号": "一句话" }，贴到时间线最近的那个点的 note 字段。
#   - decisions[].patternId 用 scripts/patterns_r04.json 里的编号；本局用到的模式定义自动抄进 newPatterns。
import sys
sys.dont_write_bytecode = True  # 不往总部的 tools/__pycache__ 里写东西
import os, json, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    a = sys.argv[1:]
    mid = a[0]
    cmd = [sys.executable, os.path.join(HERE, 'review_base.py'), mid]
    if '--ours' in a:
        cmd += ['--ours', a[a.index('--ours') + 1]]
    base = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    hand = json.load(open(os.path.join(ROOT, 'review-src', mid + '.json'), encoding='utf8'))
    pats = json.load(open(os.path.join(HERE, 'patterns_r04.json'), encoding='utf8'))
    doc = dict(base)
    for k in ('context', 'outcome'):
        doc[k] = dict(base[k]); doc[k].update(hand.get(k, {}))
    causes = hand.get('deathCauses', {})
    for d in doc['deaths']:
        d['cause'] = causes.get(d['bot'], '')
        if not d['cause']:
            sys.exit(f'{mid}: 出局号 {d["bot"]} 没写死因')
    for d in hand.get('extraDeaths', []):
        doc['deaths'].append(d)
    notes = hand.get('timelineNotes', {})
    for t, s in notes.items():
        t = int(t)
        best = min(doc['timeline'], key=lambda r: abs(r['t'] - t))
        best['note'] = (best.get('note', '') + ' ' + s).strip()
    for k, v in hand.items():
        if k in ('context', 'outcome', 'deathCauses', 'timelineNotes', 'extraDeaths'):
            continue
        doc[k] = v
    used = []
    for d in doc.get('decisions', []):
        pid = d.get('patternId')
        if pid and pid not in used:
            used.append(pid)
    np_ = []
    for pid in used:
        if pid not in pats:
            sys.exit(f'{mid}: 模式编号 {pid} 不在 scripts/patterns_r04.json 里')
        p = dict(pats[pid]); p['id'] = pid
        np_.append(p)
    doc['newPatterns'] = np_ + list(hand.get('newPatterns', []))
    order = ['matchId', 'reviewer', 'protocol', 'context', 'outcome', 'lossArchetype', 'confidenceOverall', 'phases', 'timeline', 'turningPoints', 'deaths', 'decisions', 'newPatterns', 'winnerNotes', 'wentWell', 'unknowns', 'mechanicsQuestions', 'scripts']
    out = {k: doc[k] for k in order if k in doc}
    for k in doc:
        if k not in out:
            out[k] = doc[k]
    jp = os.path.join(ROOT, 'reviews', mid + '.json')
    with open(jp, 'w', encoding='utf8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    spec = importlib.util.spec_from_file_location('collect_reviews', os.path.join(ROOT, '..', '..', 'tools', 'collect-reviews.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mp = os.path.join(ROOT, 'reviews', mid + '.md')
    md = open(mp, encoding='utf8').read() if os.path.exists(mp) else None
    fails, stats = mod.check_review(out, md)
    print(f'{mid}: 写出 {jp}（{os.path.getsize(jp)} 字节）；检查 {"通过" if not fails else "未过：" + "；".join(fails)}；{stats}')


if __name__ == '__main__':
    main()
