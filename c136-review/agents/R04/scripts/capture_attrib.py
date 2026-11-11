#!/usr/bin/env python3
# capture_attrib.py — 「好地为什么没拿到」的三层归因（hub 0007 第 3 节）。是机会折扣的记账，不是反事实推演。
# 用法：python3 scripts/capture_attrib.py <局号>
#   先要有：tmp/land/<局号>/good_land.json（good_land.mjs）、tmp/shadow/<局号>/rows.tsv（shadow_all.sh）、tmp/latency/<局号>.json（latency_ledger.py）。
# 口径（两个时段分别算：开局后段 600~1499 拍、核心期前半 1500~2999 拍）：
#   ① 出生（天然份额）  f1 = 我方人均天然地盘 ÷ 全场人均陆地 = 我方天然地盘占全图的比例 ÷ 我方人头占到场真人的比例（欧氏口径；>1 记 1）
#   ② 策略底线锁        f2 = 贴着内置 AI 的号·决策拍里，没被出兵底线卡住的比例。
#        600~1499：rows.tsv 的 bind 列（floor_bind_tally.py 的口径）——项1 价格项（t1）、项2（dp）、项3 safeFinite（sb，按参照对象分）、peopleFloor（pf）；
#        1500~2999：rows.tsv 的 gateAI 列（core_gate_tally.py --ai 的口径）——floor/sf（safeAt→safeFinite，按参照对象分）、floor/dp、floor/keep，
#                   以及 price（Policy.buyLand 的单价闸：单价 ≥ worth、不便宜、余额没过 100×地 → 整张报价单到此为止）。
#   ③ 动手了但迟到      f3a = 这一段桥受理的指令里在录像中落地的比例（latency_ledger 的漏斗，快照对齐分段）；
#                        f3b = 落地的「瞄 AI/真人」陆攻单里，到站时目标还在场的那部分（按当初想出的兵）；
#   三个折扣连乘 = f1 × f2 × f3a × f3b；各层占比 = ln(1/f) 在三层合计里的比例（层内再按条数/兵数拆）。
#   最后对一下结果：时段末 我方 实际领土 ÷ 天然地盘 对 其他真人；630 拍身边内置 AI 的地到时段末的归属。
import sys, os, csv, json, math, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def pct(a, b):
    return '%.0f%%' % (100.0 * a / b) if b else '—'


def main():
    mid = sys.argv[1]
    land = json.load(open(os.path.join(ROOT, 'tmp', 'land', mid, 'good_land.json'), encoding='utf8'))
    lat = json.load(open(os.path.join(ROOT, 'tmp', 'latency', mid + '.json'), encoding='utf8'))
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'tmp', 'shadow', mid, 'rows.tsv'), encoding='utf8'), delimiter='\t'))
    ve, vl = land['voronoi']['euclid'], land['voronoi']['landpath']
    f1 = min(1.0, ve['ourSharePct'] / ve['headSharePct'])
    f1l = min(1.0, vl['ourSharePct'] / vl['headSharePct'])
    out = dict(match=mid, f1=round(f1, 3), f1Landpath=round(f1l, 3), windows={})
    print('# %s 好地为什么没拿到：三层归因（机会折扣，不是反事实）' % mid)
    print('① 出生：我方天然地盘（欧氏）占全图陆地 %.1f%%、人头占到场真人 %.1f%% → 人均天然地盘是全场人均的 %.2f 倍（陆路口径 %.2f 倍）；单号中位 %s 格，其他真人中位 %s 格（%.2f 倍）' % (
        ve['ourSharePct'], ve['headSharePct'], ve['ourSharePct'] / ve['headSharePct'], vl['ourSharePct'] / vl['headSharePct'],
        format(int(ve['ourMedian']), ','), format(int(ve['otherMedian']), ','), ve['ourMedian'] / max(1, ve['otherMedian'])))
    ticks = sorted(int(t) for t in land['capture'])
    for (t0, t1, lab, snap, band, endt) in ((600, 1500, '600~1499', '630~1530', '600~1499', 1500), (1500, 3000, '1500~2999', '1530~3060', '1500~2999', 3000)):
        n = act = lock = free = 0
        det = collections.Counter()
        fdet = collections.Counter()
        for r in rows:
            t = int(r['t'])
            if not (t0 <= t < t1) or int(float(r['nAI'] or 0)) <= 0:
                continue
            n += 1
            acted = int(r['intents']) > 0
            if t < 1500:
                b = r.get('bind', '')
                if acted:
                    act += 1
                elif b in ('t1', 'dp', 'sb', 'pf'):
                    lock += 1
                    if b == 'sb':
                        det['项3 safeFinite/' + {'squad': '编队号', 'ally': '同队真人', 'enemy': '外队真人', 'ai': '另一个AI'}.get((r.get('sbRef') or '?:').split(':')[0], '?')] += 1
                    else:
                        det[{'t1': '项1 价格项', 'dp': '项2 dpKeep', 'pf': 'peopleFloor'}[b]] += 1
                else:
                    free += 1
                    fdet['底线没卡住（目标数已满、在途兵已够等）'] += 1
            else:
                ga = r.get('gateAI', '') or ''
                parts = ga.split(':')
                if acted:
                    act += 1
                elif parts[0] == 'floor':
                    lock += 1
                    d = ':'.join(parts[2:]) if len(parts) > 2 else '?'
                    kind = d.split('/')[0]
                    if 'sf' in kind:
                        who = d.split('/')[1].split(':')[0] if '/' in d else '?'
                        det[('safeAt→safeFinite/' if kind == 'sf' else '截到 oppFloorCap 后仍不够/') + {'squad': '编队号', 'ally': '同队真人', 'enemy': '外队真人', 'ai': '另一个AI'}.get(who, who)] += 1
                    else:
                        det[{'dp': 'safeAt 的 dpKeep', 'keep': '价格预算要留的兵'}.get(kind, kind)] += 1
                elif parts[0] == 'price':
                    lock += 1
                    det['单价闸（单价 ≥ worth 且余额没过 100×地）'] += 1
                else:
                    free += 1
                    fdet[{'covered': '在途的兵已够', 'behind': '排在前面的报价先结束', 'chunk': '不够一次吃掉且 <20% 余额', 'slots': '没有空槽', 'nobuy': 'buyLand 没走到',
                          'send': '过了闸但被 isNoFullSend 守卫拦掉', '': '没有记录'}.get(parts[0], parts[0])] += 1
        if n == 0:
            print('%s：没有贴着内置 AI 的决策拍' % lab)
            continue
        f2 = 1.0 - lock / n
        fu = lat.get('funnel', {}).get(snap, {})
        f3a = min(1.0, fu.get('landed', 0) / max(1, fu.get('accepted', 0))) if fu.get('accepted') else 1.0
        lw = lat.get('lateWrong', {}).get(band, {})
        on_t = lw.get('onTargetTroops', 0)
        conv_t = lw.get('wantTroops', 0)
        aimed_t = lw.get('aimedTroops', 0)
        f3b = 1.0 - conv_t / aimed_t if aimed_t > 0 else 1.0
        logs = [math.log(1 / max(1e-9, f1)), math.log(1 / max(1e-9, f2)), math.log(1 / max(1e-9, f3a)) + math.log(1 / max(1e-9, f3b))]
        s = sum(logs) or 1.0
        print('## %s 拍' % lab)
        print('② 策略闸门：贴着内置 AI 的号·决策拍 %d 个：出手 %d（%s），被出兵底线 / 单价闸卡住 %d（%s），没卡住也没出手 %d（%s）→ 没被锁住的比例 %.2f；卡住的拆开：%s；没卡住也没出手的拆开：%s' % (
            n, act, pct(act, n), lock, pct(lock, n), free, pct(free, n), f2,
            '，'.join('%s %d（%s）' % (k, v, pct(v, n)) for k, v in det.most_common()) or '无',
            '，'.join('%s %d' % (k, v) for k, v in fdet.most_common()) or '无'))
        print('③ 迟到：桥受理 %s 条 → 录像落地 %s 条（%.2f）；落地的「瞄 AI/真人」陆攻 %s 条（当初想出 %s 兵）里，打到原目标 %s 条（实出 %s 兵），到站时目标已出局被改成无主地 %s 条（当初想出 %s 兵；实际改打无主地 %s 兵、没产生进攻 %s 条）→ 到站时目标还在的比例（按当初想出的兵）%.2f' % (
            fu.get('accepted', '—'), fu.get('landed', '—'), f3a, lw.get('aimed', 0), format(int(aimed_t), ','), lw.get('onTarget', 0), format(int(on_t), ','), lw.get('retargeted', 0),
            format(int(conv_t), ','), format(int(lw.get('toNeutralTroops', 0)), ','), lw.get('noAttackN', 0), f3b))
        print('连乘：%.2f × %.2f × %.2f × %.2f = %.3f；各层在折扣里的占比（对数）：出生 %s，策略闸门 %s，迟到 %s（其中没落地 %s、到站目标已亡 %s）' % (
            f1, f2, f3a, f3b, f1 * f2 * f3a * f3b, pct(logs[0], s), pct(logs[1], s), pct(logs[2], s),
            pct(math.log(1 / max(1e-9, f3a)), s), pct(math.log(1 / max(1e-9, f3b)), s)))
        te = max([t for t in ticks if t <= endt], default=None)
        res = {}
        if te is not None:
            cap = land['capture'][str(te)]['groups']
            me, ot = cap.get('我方'), cap.get('全部其他真人')
            line = '结果（拍 %d）：我方 实际 ÷ 天然地盘 = %.2f（单号中位 %.2f），其他真人 %.2f（中位 %.2f）' % (te, me['ratioE'], me['medE'], ot['ratioE'], ot['medE'])
            fate = land['aiFate'].get(str(te))
            if fate:
                px = land['aiFate']['t0']['px']
                o = fate['owners']
                line += '；%d 拍身边内置 AI 的 %s 格：我方 %s，同队其他真人 %s，敌方真人 %s，还在内置 AI 手里 %s，无主 %s' % (
                    land['t0'], format(px, ','), pct(o.get('我方', 0), px), pct(o.get('同队其他真人', 0), px), pct(o.get('敌方真人', 0), px),
                    pct(o.get('原来那个AI', 0) + o.get('别的AI', 0) + o.get('同队AI', 0), px), pct(o.get('无主', 0), px))
                res = dict(tick=te, ourRatio=me['ratioE'], otherRatio=ot['ratioE'], aiOurPct=round(100.0 * o.get('我方', 0) / max(1, px), 1),
                           aiAllyPct=round(100.0 * o.get('同队其他真人', 0) / max(1, px), 1), aiEnemyPct=round(100.0 * o.get('敌方真人', 0) / max(1, px), 1))
            print(line)
        out['windows'][lab] = dict(adjTicks=n, acted=act, locked=lock, free=free, lockDetail=dict(det), f2=round(f2, 3), f3a=round(f3a, 3), f3b=round(f3b, 3),
                                   product=round(f1 * f2 * f3a * f3b, 4), shareSpawn=round(100 * logs[0] / s, 1), shareLock=round(100 * logs[1] / s, 1),
                                   shareLate=round(100 * logs[2] / s, 1), result=res)
    d = os.path.join(ROOT, 'tmp', 'attrib')
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, mid + '.json'), 'w', encoding='utf8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
