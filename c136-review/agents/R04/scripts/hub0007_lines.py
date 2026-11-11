#!/usr/bin/env python3
# hub0007_lines.py — 把一局的「延迟账」「好地账」压成两行，贴进 reviews/<局号>.md 的「## 5 对账」末尾（「## 6」之前）。
# 数字全部来自 tmp/latency/<局号>.json（latency_ledger.py）、tmp/land/<局号>/good_land.json（good_land.mjs）、tmp/attrib/<局号>.json（capture_attrib.py）。
# review-src/<局号>.json 里的 hub0007Notes: {latency: '…', land: '…'} 是人工写的解读，接在两行各自的末尾。
# 用法：python3 scripts/hub0007_lines.py <局号> [--inject]      不带 --inject 只打印；带了就改写 md（已有的同名两行先删掉再插）。
import sys, os, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
M1 = '- **延迟账（hub 0007）**'
M2 = '- **好地账（hub 0007）**'


def wan(v):
    return '%.1f 万' % (v / 1e4) if abs(v) >= 1e4 else format(int(v), ',')


def load(mid):
    lat = json.load(open(os.path.join(ROOT, 'tmp', 'latency', mid + '.json'), encoding='utf8'))
    land = json.load(open(os.path.join(ROOT, 'tmp', 'land', mid, 'good_land.json'), encoding='utf8'))
    att = json.load(open(os.path.join(ROOT, 'tmp', 'attrib', mid + '.json'), encoding='utf8'))
    return lat, land, att


def lines(mid):
    lat, land, att = load(mid)
    sp = lat['spawn']
    c = sp['classes']
    n = sum(c.values())
    s1 = '出生——协调器求解 %d 轮（点位最后一次变动在第 %s 轮），%d 个号里落在最后一轮点上 %d 个' % (sp['solves'], sp['lastChange'] or 1, n, c.get('落在最后一轮的点上', 0))
    for k in ('停在旧坐标', '一条出生指令都没落地', '哪一轮的点都不是', '协调器日志里没有它的点'):
        if c.get(k):
            s1 += '、%s %d 个' % (k, c[k])
    if sp['lastStepMin'] is None:
        s1 += '、两号同点 %d 对，选点阶段（共 %s 步）没有一条出生指令落地' % (sp['samePoint'], sp['steps'])
    else:
        s1 += '、两号同点 %d 对，最后一条出生指令落地在第 %s~%s 步（共 %s 步）' % (sp['samePoint'], sp['lastStepMin'], sp['lastStepMax'], sp['steps'])
    d = lat['delay']
    s2 = '执行拍 − 决策拍 P50/P90/Max（宽配对；括号里是严配对）：' + '，'.join(
        '%s 拍 %s/%s/%s（%s/%s/%s）' % (k, v['p50'], v['p90'], v['max'], v['strictP50'], v['strictP90'], v['strictMax']) for k, v in d.items() if v['landed'])
    f = lat['funnel']
    s3 = '漏斗（影子想发 → 桥受理 → 录像落地）：' + '，'.join('%s %d→%d→%d' % (k, v['want'], v['accepted'], v['landed']) for k, v in f.items() if k not in ('total', 'perBot')) + \
        '，合计 %d→%d→%d（落地 ÷ 受理 %.0f%%）' % (f['total']['want'], f['total']['accepted'], f['total']['landed'], 100.0 * f['total']['landed'] / max(1, f['total']['accepted']))
    cl = lat['clientLag']
    worst = sorted(((v['max'] or 0, b) for b, v in cl.items()), reverse=True)
    lagging = [(m, b) for m, b in worst if m >= 180]
    s4 = '客户端落后（相对最快的队友）：' + ('、'.join('%s 最大 %d 拍' % (b, m) for m, b in lagging[:4]) if lagging else '各号最大都不到 180 拍')
    lw = lat['lateWrong'].get('600~1499')
    s5 = ''
    if lw:
        s5 = '晚到打错（600~1499 拍落地）：目标已出局被改成无主地 %d 条，当初想出 %s 兵（占落地的「瞄 AI/真人」单的 %.0f%%），改打无主地实出 %s 兵、手续费 %s，没产生进攻 %d 条' % (
            lw['retargeted'], wan(lw['wantTroops']), 100.0 * lw['wantTroops'] / max(1, lw['aimedTroops']), wan(lw['toNeutralTroops']), wan(lw['toNeutralFee']), lw['noAttackN'])
        lw2 = lat['lateWrong'].get('1500~2999')
        if lw2 and lw2['retargeted']:
            s5 += '（1500~2999 拍 %d 条、想出 %s 兵）' % (lw2['retargeted'], wan(lw2['wantTroops']))
    rp = lat['repeat']
    s6 = '重复单（上一条还没生效又下的）全局 %d 条 %s 兵 = 打人/AI 出征兵的 %.0f%%' % (rp['total']['n'], wan(rp['total']['troops']), rp['total']['sharePct'])
    dr = lat['drain']
    parts = ['%s 拍 %d 批 %d 条（第 2 条起出 %s 兵，抽到四成以下 %d 批）' % (k, v.get('批', 0), v.get('条', 0), wan(v.get('第2条起的兵', 0)), v.get('抽到四成以下', 0)) for k, v in dr.items() if k != 'sizes']
    s7 = '清仓批（同号同拍落地 ≥3 条陆攻）：' + ('，'.join(parts) if parts else '没有')
    s8 = s9 = ''
    rp_ = os.path.join(ROOT, 'tmp', 'rate', mid + '.json')
    if os.path.exists(rp_):
        r = json.load(open(rp_, encoding='utf8'))
        f = r.get('squadFine') or {}
        lo = [f[k] for k in ('1~3', '4~6', '7~9', '10~12') if k in f]
        hi = [f[k] for k in ('16~20', '21~30') if k in f]
        top = f.get('≥31')
        if lo:
            s8 = '延迟跟着编队的下单密度走（50 拍窗口内全部我方号的意图条数）：≤12 条时 P50 %s 拍' % '/'.join(str(x['p50']) for x in lo)
            if hi:
                s8 += '，16~30 条时 %s 拍' % '/'.join(str(x['p50']) for x in hi)
            if top:
                s8 += '，≥31 条时 %s 拍（落地率 %.0f%%）' % (top['p50'], 100.0 * top['landed'] / max(1, top['n']))
    sp_ = os.path.join(ROOT, 'tmp', 'slow', mid + '.json')
    if os.path.exists(sp_):
        sl = json.load(open(sp_, encoding='utf8'))
        if sl.get('lines'):
            worst = sorted(sl['bots'].items(), key=lambda kv: -kv[1]['n'])[:3]
            s9 = '慢拍（[HL-SLOW-TICK]，一次决策 ≥25 毫秒）%d 行：' % sl['lines'] + '、'.join('%s %d 行（%d 拍起，中位 %.0f 最大 %.0f 毫秒）' % (b, v['n'], v['first'], v['med'], v['max']) for b, v in worst)
            if sl.get('lagIn', {}).get('n'):
                s9 += '；决策拍落在慢拍密集段里的指令延迟 P50 %s 拍，段外 %s 拍' % (sl['lagIn']['p50'], sl['lagOut']['p50'])
    s10 = s11 = ''
    cp_ = os.path.join(ROOT, 'tmp', 'chunks', mid + '.json')
    if os.path.exists(cp_):
        ck = json.load(open(cp_, encoding='utf8'))
        if ck.get('big'):
            tails = sum(v.get('tailSum', 0) for v in ck['bands'].values())
            s10 = '成批落地的前后（`burst_chunks.py`）：装满的批（8~9 条）%d 个里 %d 个后面紧跟着的意图一条没落地（合计 %d 条），不到 8 条的批 %d 个里 %d 个' % (
                ck['big']['n'], ck['big']['withTail'], tails, ck['small']['n'], ck['small']['withTail'])
            b6 = ck['bands'].get('600~1499')
            if b6 and b6.get('matched'):
                s10 += '；600~1499 拍每补完一截离落地拍还差 中位 %s 拍' % b6['shortP50']
    wp_ = os.path.join(ROOT, 'tmp', 'wall', mid + '.json')
    if os.path.exists(wp_):
        wl = json.load(open(wp_, encoding='utf8'))
        late = sorted([x for x in wl['bots'] if x['lag'] >= 35], key=lambda x: -x['lag'])
        if late:
            s11 = '墙上时钟（results.csv 的 at）：报告出局时客户端落后服务器 ≥35 拍的号 %d 个（%s）' % (len(late), '、'.join(
                '%s %d 拍' % (x['bot'], round(x['lag'])) + ('〔另一局〕' if x.get('group') == 'rep=N' else '')
                + ('，它最后几条指令晚 %d 拍' % x['lastCmdDelayP50'] if 'lastCmdDelayP50' in x else '') for x in late[:5]))
        else:
            s11 = '墙上时钟（results.csv 的 at）：%d 个号报告出局时客户端都跟得上服务器（最大落后 %d 拍）' % (wl['n'], round(wl['max']))
    notes = {}
    hp = os.path.join(ROOT, 'review-src', mid + '.json')
    if os.path.exists(hp):
        notes = json.load(open(hp, encoding='utf8')).get('hub0007Notes', {})
    L1 = M1 + '：' + '；'.join(x for x in (s1, s2, s3, s4, s8, s9, s10, s11, s5, s6, s7) if x) + '。' + (notes.get('latency', '') or '')

    ve, vl = land['voronoi']['euclid'], land['voronoi']['landpath']
    g1 = '天然地盘（按出生点把陆地分给最近的真人）我方 %s 格 = 全图陆地的 %.1f%%，人头占到场真人的 %.1f%% → 人均天然地盘是全场人均的 %.2f 倍（只走陆路的口径 %.2f 倍）；单号中位 %s 格，其他真人中位 %s 格' % (
        format(int(ve['ourPx']), ','), ve['ourSharePct'], ve['headSharePct'], ve['ourSharePct'] / ve['headSharePct'], vl['ourSharePct'] / vl['headSharePct'],
        format(int(ve['ourMedian']), ','), format(int(ve['otherMedian']), ','))
    caps = []
    for t in sorted(land['capture'], key=int):
        if int(t) not in (630, 1500, 1800, 3000):
            continue
        g = land['capture'][t]['groups']
        if '全部其他真人' in g:
            caps.append('%s 拍 %.2f 对 %.2f' % (t, g['我方']['ratioE'], g['全部其他真人']['ratioE']))
        else:
            caps.append('%s 拍 %.2f' % (t, g['我方']['ratioE']))
    solo = not any('全部其他真人' in land['capture'][t]['groups'] for t in land['capture'])
    if solo:
        # 到场的真人全是我方（A073）：没有「其他真人」这一栏
        g1 = '到场的真人全是我方（%d 个），天然地盘（按出生点把陆地分给最近的真人）就是全图陆地 %s 格；只走陆路能到的 %s 格 = 全图的 %.1f%%' % (
            land['ours'], format(int(ve['ourPx']), ','), format(int(vl['ourPx']), ','), vl['ourSharePct'])
    g2 = ('实际领土 ÷ 天然地盘（我方；没有其他真人可比）：' if solo else '实际领土 ÷ 天然地盘（我方 对 其他真人）：') + '，'.join(caps)
    a0 = land['aiFate'].get('t0', {})
    g3 = ''
    if a0.get('px'):
        px = a0['px']
        fs = []
        for t in ('1500', '1800', '3000'):
            o = land['aiFate'].get(t, {}).get('owners')
            if not o:
                continue
            ai = o.get('原来那个AI', 0) + o.get('别的AI', 0) + o.get('同队AI', 0)
            fs.append('%s 拍 我方 %.0f%%、同队其他真人 %.0f%%、敌方真人 %.0f%%、还在 AI 手里 %.0f%%' % (
                t, 100.0 * o.get('我方', 0) / px, 100.0 * o.get('同队其他真人', 0) / px, 100.0 * o.get('敌方真人', 0) / px, 100.0 * ai / px))
        g3 = '%d 拍身边的内置 AI（接壤或过半在我方天然地盘里）%d 个 %s 格的去向：' % (land['t0'], a0['n'], format(px, ',')) + '；'.join(fs)
    ws = []
    for k, w in att['windows'].items():
        det = sorted(w['lockDetail'].items(), key=lambda kv: -kv[1])[:3]
        ws.append('%s 拍 出生 %.0f%%、策略闸门 %.0f%%（贴着内置 AI 的 %d 个号·决策拍里卡住 %d 个：%s）、迟到 %.0f%%（受理后落地 %.2f、到站时目标还在 %.2f）' % (
            k, w['shareSpawn'], w['shareLock'], w['adjTicks'], w['locked'], '，'.join('%s %d' % kv for kv in det) or '无', w['shareLate'], w['f3a'], w['f3b']))
    g4 = '三层归因（机会折扣的对数占比，不是反事实）：' + '；'.join(ws)
    L2 = M2 + '：' + '；'.join(x for x in (g1, g2, g3, g4) if x) + '。' + (notes.get('land', '') or '')
    return L1, L2


def main():
    mid = sys.argv[1]
    L1, L2 = lines(mid)
    if '--inject' not in sys.argv:
        print(L1)
        print(L2)
        return
    mp = os.path.join(ROOT, 'reviews', mid + '.md')
    src = open(mp, encoding='utf8').read().split('\n')
    src = [x for x in src if not (x.startswith(M1) or x.startswith(M2))]
    i = next((k for k, x in enumerate(src) if x.startswith('## 6')), None)
    if i is None:
        sys.exit('md 里没有「## 6」这一节')
    j = i
    while j > 0 and src[j - 1].strip() == '':
        j -= 1
    src[j:j] = [L1, L2]
    open(mp, 'w', encoding='utf8').write('\n'.join(src))
    print('%s.md：已写入两行（现在 %d 个换行）' % (mid, '\n'.join(src).count('\n')))


if __name__ == '__main__':
    main()
