#!/usr/bin/env python3
# check_reviews.py — 用总部的 collect-reviews.py 里同一个 check_review() 在本地检查我的复盘文件，只读不写。
# 用法：python3 scripts/check_reviews.py [局号…]（默认 reviews/ 下全部）
import sys
sys.dont_write_bytecode = True  # 不往总部的 tools/__pycache__ 里写东西
import os, json, importlib.util, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(ROOT, '..', '..', 'tools', 'collect-reviews.py')


def main():
    spec = importlib.util.spec_from_file_location('collect_reviews', TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ids = sys.argv[1:] or sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'reviews', '*.json')))
    bad = 0
    for mid in ids:
        jp = os.path.join(ROOT, 'reviews', mid + '.json')
        mp = os.path.join(ROOT, 'reviews', mid + '.md')
        try:
            doc = json.load(open(jp, encoding='utf8'))
        except Exception as e:
            print(f'{mid}: JSON 读不了 {e}')
            bad += 1
            continue
        md = open(mp, encoding='utf8').read() if os.path.exists(mp) else None
        fails, stats = mod.check_review(doc, md)
        nl = md.count('\n') if md else 0
        print(f'{mid}: {"通过" if not fails else "未过 " + "；".join(fails)} | 时间线 {stats.get("timeline")} 转折 {stats.get("turningPoints")} 出局 {stats.get("deaths")} 决策 {stats.get("decisions")} {stats.get("verdicts")} 新模式 {stats.get("newPatterns")} md {nl} 行')
        bad += 1 if fails else 0
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
