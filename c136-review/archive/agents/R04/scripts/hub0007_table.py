#!/usr/bin/env python3
# hub0007_table.py — 把若干局的「延迟账 / 好地账 / 三层归因」并排成一张 markdown 表（行 = 指标，列 = 局）。
# 用法：python3 scripts/hub0007_table.py <局号> [<局号> …] [--tsv]
#   数据：tmp/latency/<局号>.json、tmp/land/<局号>/good_land.json、tmp/attrib/<局号>.json（先跑 bash scripts/hub0007_all.sh <局号>）。
#   --tsv：另外打印一份制表符分隔的原始数（跨局汇总的机械计数用）。
import sys, os, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def wan(v):
    return '%.1f 万' % (v / 1e4) if abs(v) >= 1e4 else format(int(v), ',')


def load(mid):
    try:
        lat = json.load(open(os.path.join(ROOT, 'tmp', 'latency', mid + '.json'), encoding='utf8'))
        land = json.load(open(os.path.join(ROOT, 'tmp', 'land', mid, 'good_land.json'), encoding='utf8'))
        att = json.load(open(os.path.join(ROOT, 'tmp', 'attrib', mid + '.json'), encoding='utf8'))
    except FileNotFoundError as e:
        sys.exit('%s 缺数据：%s（先跑 hub0007_all.sh）' % (mid, e.filename))
    return lat, land, att


def cells(mid):
    lat, land, att = load(mid)
    ve, vl = land['voronoi']['euclid'], land['voronoi']['landpath']
    c = {}
    c['到场真人 / 我方号'] = '%d / %d' % (land['humansPresent'], land['ours'])
    c['天然地盘占全图 ÷ 人头占比 = 倍数（欧氏）'] = '%.1f%% ÷ %.1f%% = %.2f' % (ve['ourSharePct'], ve['headSharePct'], ve['ourSharePct'] / ve['headSharePct'])
    c['同上，只走陆路的口径'] = '%.2f' % (vl['ourSharePct'] / vl['headSharePct'])
    if ve['otherMedian']:
        c['单号天然地盘中位：我方 / 其他真人'] = '%s / %s（%.2f 倍）' % (format(int(ve['ourMedian']), ','), format(int(ve['otherMedian']), ','), ve['ourMedian'] / max(1, ve['otherMedian']))
    else:
        c['单号天然地盘中位：我方 / 其他真人'] = '%s / 无' % format(int(ve['ourMedian']), ',')
    for t in ('630', '1500', '1800', '3000'):
        g = land['capture'].get(t, {}).get('groups')
        if g and '全部其他真人' not in g:
            # 到场的真人全是我方（A073）
            c['实际 ÷ 天然，%s 拍：我方 / 其他真人' % t] = '%.2f / 无' % g['我方']['ratioE']
            continue
        c['实际 ÷ 天然，%s 拍：我方 / 其他真人' % t] = ('%.2f / %.2f' % (g['我方']['ratioE'], g['全部其他真人']['ratioE'])) if g else '—'
    a0 = land['aiFate'].get('t0', {})
    px = a0.get('px', 0)
    c['630 拍身边的内置 AI：个 / 格'] = '%d / %s' % (a0.get('n', 0), format(px, ','))
    for t in ('1500', '1800', '3000'):
        o = land['aiFate'].get(t, {}).get('owners')
        if o and px:
            ai = o.get('原来那个AI', 0) + o.get('别的AI', 0) + o.get('同队AI', 0)
            c['这些格 %s 拍在谁手里：我方 / 同队其他真人 / 敌方真人 / 内置 AI' % t] = '%.0f%% / %.0f%% / %.0f%% / %.0f%%' % (
                100.0 * o.get('我方', 0) / px, 100.0 * o.get('同队其他真人', 0) / px, 100.0 * o.get('敌方真人', 0) / px, 100.0 * ai / px)
        else:
            c['这些格 %s 拍在谁手里：我方 / 同队其他真人 / 敌方真人 / 内置 AI' % t] = '—'
    sp = lat['spawn']
    k = sp['classes']
    c['协调器求解轮数 / 点位最后一次变动的轮'] = '%d / %s' % (sp['solves'], sp['lastChange'] or 1)
    c['出生：落在最后一轮的点上 / 停在旧坐标 / 没落地 / 其他；同点对数'] = '%d / %d / %d / %d；%d' % (
        k.get('落在最后一轮的点上', 0), k.get('停在旧坐标', 0), k.get('一条出生指令都没落地', 0),
        k.get('哪一轮的点都不是', 0) + k.get('协调器日志里没有它的点', 0), sp['samePoint'])
    for b, v in lat['delay'].items():
        c['执行拍 − 决策拍 P50/P90/Max，%s 拍' % b] = ('%s / %s / %s' % (v['p50'], v['p90'], v['max'])) if v['landed'] else '—'
    f = lat['funnel']
    for b in ('630~1530', '1530~3060', '>3060'):
        v = f.get(b)
        c['想发 → 受理 → 落地，%s 拍' % b] = ('%d → %d → %d' % (v['want'], v['accepted'], v['landed'])) if v else '—'
    c['全局 落地 ÷ 受理'] = '%.0f%%' % (100.0 * f['total']['landed'] / max(1, f['total']['accepted']))
    cl = lat['clientLag']
    worst = sorted(((v['max'] or 0, b) for b, v in cl.items()), reverse=True)
    c['客户端落后最大（相对最快的队友）'] = ('%s %d 拍' % (worst[0][1], worst[0][0])) if worst and worst[0][0] > 0 else '各号都是 0'
    lw = lat['lateWrong'].get('600~1499')
    c['600~1499 拍落地时目标已出局：条 / 想出的兵 / 占瞄 AI、真人落地单'] = ('%d / %s / %.0f%%' % (lw['retargeted'], wan(lw['wantTroops']), 100.0 * lw['wantTroops'] / max(1, lw['aimedTroops']))) if lw else '—'
    c['600~1499 拍瞄 AI、真人的意图 → 打到原目标'] = ('%d → %d（%.0f%%）' % (lw['aimedIntents'], lw['onTarget'], 100.0 * lw['onTarget'] / max(1, lw['aimedIntents']))) if lw else '—'
    rp = lat['repeat']['total']
    c['重复单：条 / 兵 / 占打人和 AI 的出征兵'] = '%d / %s / %.0f%%' % (rp['n'], wan(rp['troops']), rp['sharePct'])
    dr = lat['drain']
    for b in ('600~1499', '1500~2999', '3000+'):
        v = dr.get(b)
        c['清仓批 %s 拍：批 / 条 / 第 2 条起的兵' % b] = ('%d / %d / %s' % (v.get('批', 0), v.get('条', 0), wan(v.get('第2条起的兵', 0)))) if v else '0'
    rp_ = os.path.join(ROOT, 'tmp', 'rate', mid + '.json')
    if os.path.exists(rp_):
        r = json.load(open(rp_, encoding='utf8'))
        f = r.get('squadFine') or {}
        for k in ('1~3', '4~6', '7~9', '10~12', '13~15', '16~20', '21~30', '≥31'):
            v = f.get(k)
            c['编队 50 拍内下单 %s 条时：延迟 P50 / P90（落地率）' % k] = ('%s / %s（%.0f%%）' % (v['p50'], v['p90'], 100.0 * v['landed'] / max(1, v['n']))) if v else '—'
        bg = r.get('batchGap') or {}
        c['同一个号相邻两批相隔（中位拍数）：<1500 / 1500~2999 / 3000+'] = ' / '.join(str(bg.get(k, {}).get('p50', '—')) for k in ('<1500', '1500~2999', '3000+'))
    sp_ = os.path.join(ROOT, 'tmp', 'slow', mid + '.json')
    if os.path.exists(sp_):
        sl = json.load(open(sp_, encoding='utf8'))
        mx = max([v['max'] for v in sl['bots'].values()], default=0)
        c['慢拍行数（一次决策 ≥25 毫秒）/ 最大毫秒'] = '%d / %.0f' % (sl['lines'], mx)
    cp_ = os.path.join(ROOT, 'tmp', 'chunks', mid + '.json')
    if os.path.exists(cp_):
        ck = json.load(open(cp_, encoding='utf8'))
        if ck.get('big'):
            c['装满的批（8~9 条）：个数 / 后面紧跟着丢掉意图的'] = '%d / %d' % (ck['big']['n'], ck['big']['withTail'])
            c['不到 8 条的批：个数 / 后面紧跟着丢掉意图的'] = '%d / %d' % (ck['small']['n'], ck['small']['withTail'])
            for nm in ('600~1499', '1500~2999'):
                v = ck['bands'].get(nm)
                c['%s 每补完一截离落地拍还差（中位 / P90 拍）' % nm] = ('%s / %s' % (v['shortP50'], v['shortP90'])) if v and v.get('matched') else '—'
    wp_ = os.path.join(ROOT, 'tmp', 'wall', mid + '.json')
    if os.path.exists(wp_):
        wl = json.load(open(wp_, encoding='utf8'))
        c['墙上时钟：报告出局时落后服务器 ≥35 拍 / ≥90 拍的号（共几个号）；最大'] = '%d / %d（%d）；%d 拍' % (wl['ge35'], wl['ge90'], wl['n'], round(wl['max']))
    for b, w in att['windows'].items():
        c['三层归因 %s 拍：出生 / 策略闸门 / 迟到（对数占比）' % b] = '%.0f%% / %.0f%% / %.0f%%' % (w['shareSpawn'], w['shareLock'], w['shareLate'])
        c['同上的四个折扣：出生 × 没被锁 × 受理后落地 × 到站时目标还在'] = c.get('同上的四个折扣：出生 × 没被锁 × 受理后落地 × 到站时目标还在', '') + ('%s：%.2f × %.2f × %.2f × %.2f = %.3f　' % (
            b, att['f1'], w['f2'], w['f3a'], w['f3b'], w['product']))
        c['贴着内置 AI 的号·决策拍 %s 拍：总数 / 出手 / 被闸门卡住' % b] = '%d / %d / %d' % (w['adjTicks'], w['acted'], w['locked'])
    return c


def main():
    mids = [a for a in sys.argv[1:] if not a.startswith('--')]
    cols = [cells(m) for m in mids]
    keys = []
    for c in cols:
        for k in c:
            if k not in keys:
                keys.append(k)
    print('| | ' + ' | '.join(mids) + ' |')
    print('| :-- | ' + ' | '.join('--:' for _ in mids) + ' |')
    for k in keys:
        print('| %s | ' % k + ' | '.join(c.get(k, '—').strip() for c in cols) + ' |')
    if '--tsv' in sys.argv:
        print()
        print('指标\t' + '\t'.join(mids))
        for k in keys:
            print(k + '\t' + '\t'.join(c.get(k, '—').strip() for c in cols))


if __name__ == '__main__':
    main()
