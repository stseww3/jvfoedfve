#!/usr/bin/env python3
"""crossmatch.py — R06 的 15 局跨局汇总表。只读已经落盘的单局产物，不重放、不重算单局：
    reviews/<id>.json（make_review.py）、out/<id>/latency.json（latency.py json）、out/<id>/landcap.json（landcap.py json）、
    out/<id>/logdigest.json（logdigest.py json）、out/<id>/digest.json（digest.py json）。
每一段打印一张 markdown 表；`json` 把全部行写进 out/_cross/crossmatch.json。

用法：python3 crossmatch.py <段> [matchId ...]        （不给对局号 = R06 的 15 局）
  struct     结构：地图、队数、真人数、席位、拆队、去向、终局、分型、录像覆盖
  split      拆队账：编队合计的地与兵（t≈1530 与峰值）对最强的非我方集团
  spawn      选点执行延迟：下发 / 落地、最后一版是不是出生点、撞点、延迟下界
  delay      指令延迟（下令拍 → 执行拍）分位数，按下令拍分 4 段；没有对局录像的局给日志侧墙上时钟读数
  course     延迟的时间过程：每 150 拍一格的中位
  funnel     漏斗：影子下令 → 进录像 → 生效；丢了 / 还在路上；日志 cmds 与结算行 sent / accepted
  void       迟到落空 / 打错目标；打内置 AI 的进攻线被改挂
  dups       确认窗内重复下单；同拍批与清仓批
  land       好地账：Voronoi 天然份额、实抢 ÷ 天然份额
  ai         身边 AI 地的去向
  layers     没抢到 AI 地的三层归因
  gates      核心期（t>=1500）影子策略对真人 / 非真人报价的出口；被真人打的拍有没有还手（读 out/<id>/coregates.json，coregates.py <id> json 写的）
  donflow    输血账（录像真值）：捐款按千分比档 / 收款人状态 / 收款后 300 拍的去向（读 out/<id>/donflow.json，donflow.py <id> json 写的）
  foes       对手画像（录像真值）：外人对我方号的打击（目标 / 出手方密度、兵力比、千分比）、围攻与还手、登陆、外人之间的捐款（读 out/<id>/foeprofile.json）
  boats      船账（录像真值）：我方发船的条数、船上兵、手续费、靠岸去向、小船 / 空船、被围时发的船（读 out/<id>/boatflow.json）
  money      兵力账：利息、顶格少拿、手续费、捐款损耗（录像真值）+ 日志侧估算（15 局同口径）
  logside    只靠日志的计数：sent / accepted、骤降、垮着还捐、零指令时段、满仓不动、缺快照、没开局的席位
  patterns   15 局 JSON 里的模式名：出现在几局、多少实例
  decisions  决策审计：按种类 × 判定；判为错的决策落在哪些函数
  deaths     阵亡：按时段；死前 900 拍的地被谁拿走；清地前手里还有多少兵
  relate     并排看：各局的延迟、站位、闸、实抢率，以及与延迟的秩相关
  spawnfx    单号口径：天然份额（按真实出生点）与 t≈1500 的领土、与早亡；出生时最近的玩家是不是我方号
  json       全部段的行写进 out/_cross/crossmatch.json
  all        依次打印全部段
"""
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'out')
REV = os.path.join(ROOT, 'reviews')
IDS = ['B001', 'B002', 'B003', 'B010', 'B014', 'B017', 'B018', 'B021', 'B022', 'B023', 'B025', 'B038', 'B039', 'B041', 'B045']
BANDS = ['0~600', '600~1500', '1500~3000', '3000+']
FUNCS = ['chooseSpawn', 'buyLand', 'tryDonateToTeammate', 'safeFinite', 'winFloor', 'safeAt', 'isProtectedSquadMate', 'hasWildOutsidersAlive', 'isOurSquadBot',
         'boatOut', 'idleBoats', 'pickTarget', 'minCmd', 'dpKeep', 'dpNeutral', 'Policy.act', 'General.act', 'offers', 'Strategy.send', 'threatOf', 'votePeace', 'bridgehead']


def jl(p):
    return json.load(open(p)) if os.path.exists(p) else None


class M:
    def __init__(self, mid):
        self.id = mid
        self.R = jl(os.path.join(REV, mid + '.json')) or {}
        self.L = jl(os.path.join(OUT, mid, 'latency.json')) or {}
        self.C = jl(os.path.join(OUT, mid, 'landcap.json')) or {}
        self.G = jl(os.path.join(OUT, mid, 'logdigest.json')) or {}
        self.D = jl(os.path.join(OUT, mid, 'digest.json')) or {}
        self.K = jl(os.path.join(OUT, mid, 'coregates.json')) or {}
        self.F = jl(os.path.join(OUT, mid, 'donflow.json')) or {}
        self.P = jl(os.path.join(OUT, mid, 'foeprofile.json')) or {}
        self.B = jl(os.path.join(OUT, mid, 'boatflow.json')) or {}
        self.ctx = self.R.get('context', {})
        self.oc = self.R.get('outcome', {})
        te = self.ctx.get('truthEnd')
        self.full = 'delay' in self.L
        self.replay = '无' if not te and not self.L.get('spawn', {}).get('per') else ('只有选点' if not self.full else f"到 t={self.L.get('replayLast')}")


def wan(x):
    if x is None:
        return '—'
    x = int(round(x))
    if abs(x) < 10000:
        return f"{x:,}"
    if abs(x) < 1000000:
        return f"{x / 1e4:.1f} 万"
    if abs(x) < 100000000:
        return f"{x / 1e4:,.0f} 万"
    return f"{x / 1e8:.2f} 亿"


def pc(a, b, d=1):
    if not b:
        return '—'
    return f"{100 * a / b:.{d}f}%"


def med(v):
    v = [x for x in v if x is not None]
    return statistics.median(v) if v else None


def table(head, rows, note=None):
    print('| ' + ' | '.join(head) + ' |')
    print('|' + '|'.join(['---'] * len(head)) + '|')
    for r in rows:
        print('| ' + ' | '.join('—' if c is None else str(c) for c in r) + ' |')
    if note:
        print()
        print(note)
    print()


# ------------------------------------------------------------------ 各段
def sec_struct(ms):
    print('### 结构与结果（reviews/*.json 的 context / outcome）')
    rows, out = [], []
    for m in ms:
        c, o = m.ctx, m.oc
        sp = sorted((c.get('teamSplitTrue') or {}).values(), reverse=True)
        pr = c.get('presence') or {}
        seats = c.get('bots') or sum(sp)
        rows.append([m.id, f"{c.get('map')} / {wan(c.get('mapLand'))}", f"{c.get('teams')} 队 / {c.get('humans')} 人", seats, '/'.join(str(x) for x in sp), pc(sp[0], sum(sp), 0) if sp else None,
                     f"{pr.get('died', 0)} / {pr.get('left', 0)} / {pr.get('end', 0)} / {len(c.get('neverPlayed') or [])}", o.get('endTick'), o.get('winnerTeam'), o.get('resultLabel'),
                     pc(o.get('peakSquadLandShare') or 0, 1), f"{m.R.get('lossArchetype')} / {m.R.get('secondaryArchetype')}", m.replay])
        out.append(dict(id=m.id, map=c.get('map'), land=c.get('mapLand'), teams=c.get('teams'), humans=c.get('humans'), seats=seats, split=sp, died=pr.get('died', 0), left=pr.get('left', 0),
                        end=pr.get('end', 0), silent=pr.get('silent', 0), neverPlayed=len(c.get('neverPlayed') or []), endTick=o.get('endTick'), winnerTeam=o.get('winnerTeam'), label=o.get('resultLabel'),
                        peakSquadShare=o.get('peakSquadLandShare'), archetype=m.R.get('lossArchetype'), secondary=m.R.get('secondaryArchetype'), replay=m.replay))
    table(['局', '地图 / 陆地', '队 / 真人', '席位', '拆队（各队我方号数）', '最大一队占席位', '阵亡 / 离开 / 活到终局 / 没开局', '终局拍', '赢家队', '卡片标签', '编队领土峰值', '分型 / 次分型', '对局录像'], rows)
    n = len(out)
    lab = Counter(x['label'] for x in out)
    arch = Counter(x['archetype'] for x in out)
    sec = Counter(x['secondary'] for x in out)
    print(f"合计 {n} 局：席位 {sum(x['seats'] for x in out)} 个；我方号被拆进 >=2 支队的 {sum(1 for x in out if len(x['split']) >= 2)} 局、>=3 支队的 {sum(1 for x in out if len(x['split']) >= 3)} 局；"
          f"最大一队占席位的中位 {pc(med([x['split'][0] / sum(x['split']) for x in out if x['split']]), 1, 0)}。卡片标签：" + '、'.join(f"{k} {v}" for k, v in lab.most_common())
          + '。分型：' + '、'.join(f"{k} {v}" for k, v in arch.most_common()) + '；次分型：' + '、'.join(f"{k} {v}" for k, v in sec.most_common()) + '。')
    print(f"去向合计：阵亡 {sum(x['died'] for x in out)}、离开 {sum(x['left'] for x in out)}、活到终局 {sum(x['end'] for x in out)}、日志无声（没有结算行）{sum(x['silent'] for x in out)}；其中没开局的席位 {sum(x['neverPlayed'] for x in out)} 个。")
    # 开过局、之后被登记离开的号：登记离开时的服务器拍（context.leftTicks 去掉 neverPlayed）
    lt = []
    for m in ms:
        nv = set(m.ctx.get('neverPlayed') or [])
        lt += [(m.id, n, t) for n, t in (m.ctx.get('leftTicks') or {}).items() if n not in nv]
    if lt:
        bands = [(0, 600, '<600'), (600, 2100, '600~2100'), (2100, 4284, '2100~4284'), (4284, 10 ** 9, '>=4284')]
        by = Counter(m for m, _, _ in lt if True)
        print(f"开过局、之后被登记离开、有离开拍的号 {len(lt)} 个：按登记离开的服务器拍 " + '、'.join(f"{n} {sum(1 for _, _, t in lt if a <= t < b)} 个" for a, b, n in bands)
              + '；各局 ' + '、'.join(f"{k} {v}" for k, v in sorted(by.items())) + '。（没开局的席位都在 t<600 被登记离开，不计在内。）')
    print()
    return out


def sec_split(ms):
    print('### 拆队账：编队合计的地与兵，对「最强的非我方集团」（reviews/*.json 的 timeline；allTeams 只有有对局录像的局有）')
    print('   非我方集团 = 某个队去掉我方号之后剩下的地 / 兵（外人真人 + 该队的空壳）。合计 ÷ 最强非我方集团 > 1 = 20 个号要是在一个队里，按地算已经是全场第一。')
    rows, out = [], []
    for m in ms:
        tl = m.R.get('timeline') or []
        land = m.ctx.get('mapLand')
        if not tl or not land:
            continue
        humans = m.ctx.get('humans') or 0
        seats = m.ctx.get('bots') or 0
        near = min(tl, key=lambda r: abs(r['t'] - 1530))
        peak = max(tl, key=lambda r: r.get('squadLandShare') or 0)

        def cut(r):
            pt = {k: v for k, v in (r.get('perTeam') or {}).items() if v.get('land')}
            s_land = sum(v['land'] for v in pt.values())
            s_tr = sum(v['troops'] for v in pt.values())
            big = max(pt.items(), key=lambda kv: kv[1]['land']) if pt else None
            o = dict(t=r['t'], share=s_land / land, troops=s_tr, nTeams=len(pt), parts={k: v['land'] / land for k, v in pt.items()}, bigTeam=big[0] if big else None, bigShare=big[1]['land'] / land if big else 0,
                     alive=r.get('alive'))
            at = r.get('allTeams')
            if at:
                rest = {k: (v['landShare'] - (pt.get(k, {}).get('land', 0) / land), v['troops'] - pt.get(k, {}).get('troops', 0)) for k, v in at.items()}
                k = max(rest, key=lambda k: rest[k][0])
                o.update(restTeam=k, restShare=rest[k][0], restTroops=rest[k][1], ratio=o['share'] / rest[k][0] if rest[k][0] > 0 else None,
                         winShare=(at.get(str(m.oc.get('winnerTeam'))) or {}).get('landShare'), topShare=max(v['landShare'] for v in at.values()))
            return o
        a, b = cut(near), cut(peak)
        head = seats / humans if humans else None
        o = dict(id=m.id, head=head, near=a, peak=b, winner=m.oc.get('winnerTeam'))
        out.append(o)
        parts = ' / '.join(f"队{k} {100 * v:.1f}%" for k, v in sorted(b['parts'].items(), key=lambda kv: -kv[1]))
        rows.append([m.id, '/'.join(str(x) for x in sorted((m.ctx.get('teamSplitTrue') or {}).values(), reverse=True)), pc(head or 0, 1),
                     f"t={a['t']}：{pc(a['share'], 1)}（÷人头 {a['share'] / head:.2f}）" if head else None,
                     f"t={b['t']}：{pc(b['share'], 1)}，{wan(b['troops'])}兵，在场 {b['alive']} 个", f"{b['nTeams']} 个队：{parts}",
                     f"队{b['restTeam']} {pc(b['restShare'], 1)}，{wan(b['restTroops'])}兵" if 'restTeam' in b else None,
                     f"{b['ratio']:.2f}（兵 {b['troops'] / b['restTroops']:.2f}）" if b.get('ratio') and b.get('restTroops') else None,
                     f"队{m.oc.get('winnerTeam')}" + (f"：当时 {pc(b['winShare'], 1)}" if b.get('winShare') is not None else '')])
    table(['局', '拆队', '人头占比', 't≈1530 编队合计领土份额', '编队合计份额的峰值', '峰值时我方地分在', '峰值时最强的非我方集团', '合计 ÷ 最强非我方集团：地（兵）', '终局赢家队'], rows)
    hi = [o for o in out if o['peak']['share'] >= 0.40]
    ge1 = [o for o in out if o['peak'].get('ratio') and o['peak']['ratio'] > 1 and o['peak']['t'] >= 1500]
    early = [o for o in out if o['peak'].get('ratio') and o['peak']['t'] < 1500]
    r15 = sorted((o['near']['share'] / o['head'], o['id']) for o in out if o['head'])
    print(f"   峰值 >=40% 的局：{'、'.join(o['id'] + ' ' + pc(o['peak']['share'], 1, 0) for o in hi)}；有对局录像、峰值在 t>=1500 的局里，峰值时合计 > 最强非我方集团的：{'、'.join(o['id'] + ' ' + format(o['peak']['ratio'], '.2f') + ' 倍' for o in ge1) or '无'}")
    print(f"   峰值落在 t<1500 的局（{'、'.join(o['id'] for o in early)}）：峰值是开局阶段的读数（之后编队份额一路往下，或录像到此为止），那一格的比值不代表「合起来能赢」。")
    print(f"   t≈1530 编队份额 ÷ 人头占比：{' / '.join(f'{i[1]} {i[0]:.2f}' for i in r15)}（中位 {med([i[0] for i in r15]):.2f}；<1 的 {sum(1 for i in r15 if i[0] < 1)} 局）。"
          '分母是全图陆地，t≈1530 时内置 AI 和无主地还没分完，人头里也含没开局 / 已离开的席位，所以这个比值天然低于 1；与其他真人的人均对比见 ai 段的「人均净增」。')
    print()
    return out


def sec_spawn(ms):
    print('### 选点执行延迟（latency.py spawn；录像真值）')
    rows, out = [], []
    for m in ms:
        s = m.L.get('spawn') or {}
        if 'per' not in s:
            rows.append([m.id, None, s.get('logged'), None, None, None, None, None, None, s.get('backendLines')])
            out.append(dict(id=m.id, logged=s.get('logged'), backendLines=s.get('backendLines'), replay=False))
            continue
        n = len(s['per'])
        rows.append([m.id, s['steps'], s['logged'], f"{s['landed']}（{pc(s['landed'], s['logged'], 0)}）", f"{s['lastOk']}/{n}", f"{s['late']}（{s['late1']} / {s['late2']} / {s['late3']}）", s['zero'],
                     f"{s['near']}（{s['samePixel']}）", f"{s['lbP50']}/{s['lbP90']}/{s['lbMax']}", s['backendLines']])
        out.append(dict(id=m.id, replay=True, n=n, **{k: v for k, v in s.items() if k != 'per'}))
    table(['局', '选点步数', 'HL-SPAWN 下发行', '进录像（占下发）', '最后一版 = 出生点', '停在更早一版（差 1 / 2 / >=3 条）', '随机落位', '<80 格的对数（同像素）', '延迟下界 P50/P90/Max（步）', '后端协调行'], rows)
    rp = [x for x in out if x['replay']]
    if rp:
        print(f"有选点录像的 {len(rp)} 局合计：{sum(x['n'] for x in rp)} 个号里最后一版就是出生点的 {sum(x['lastOk'] for x in rp)} 个（{pc(sum(x['lastOk'] for x in rp), sum(x['n'] for x in rp))}），"
              f"停在更早一版的 {sum(x['late'] for x in rp)} 个（差 1 条 {sum(x['late1'] for x in rp)}、2 条 {sum(x['late2'] for x in rp)}、>=3 条 {sum(x['late3'] for x in rp)}），随机落位 {sum(x['zero'] for x in rp)} 个；"
              f"下发 {sum(x['logged'] for x in rp):,} 行、进录像 {sum(x['landed'] for x in rp):,} 条（{pc(sum(x['landed'] for x in rp), sum(x['logged'] for x in rp))}）；<80 格 {sum(x['near'] for x in rp)} 对、其中同像素 {sum(x['samePixel'] for x in rp)} 对；"
              f"后端协调行 15 局合计 {sum((x.get('backendLines') or 0) for x in out)} 行。")
        print()
    return out


def wall_checks(m, lo=600, hi=2100):
    """日志侧墙上时钟读数：结算行落盘时其余在场号的日志位置落后（下界 ~ 上界，取各号中位）。"""
    w = (m.G.get('wallms') or {}).get('rows') or []
    out = []
    for r in w:
        st = r.get('serverTick')
        if st is None or not (lo <= st < hi) or not r.get('after'):
            continue
        aft, bef = sorted(r['after']), sorted(r['before'])
        out.append(dict(t=round(st), n=len(aft), lb=round(st - aft[len(aft) // 2]), ub=round(st - bef[len(bef) // 2]), event=r.get('event')))
    return sorted(out, key=lambda x: x['t'])


def sec_delay(ms):
    print('### 指令延迟：影子策略下令拍 → 录像执行拍（latency.py delay；拍；每格 = 配上的条数 P50/P90/Max）')
    rows, out = [], []
    for m in ms:
        if not m.full:
            wc = wall_checks(m)
            txt = '；'.join(f"≈{x['t']}：{x['n']} 个号 {x['lb']:+d}~{x['ub']:+d}" for x in wc) if wc else '这一段没有结算行可对表'
            rows.append([m.id, None, None, None, None, None, f"（{m.replay}）日志侧 t=600~2100：{txt}"])
            out.append(dict(id=m.id, replay=False, wall=wc))
            continue
        d = {x['band']: x for x in m.L['delay']}
        pb = sorted((v['bands']['600~1500'][1], v['name']) for v in m.L.get('bots', []) if v.get('bands', {}).get('600~1500'))
        cell = lambda b: f"{d[b]['n']}：{d[b]['p50']}/{d[b]['p90']}/{d[b]['max']}" if b in d else None
        rows.append([m.id] + [cell(b) for b in BANDS] + [f"{pb[0][0]}~{pb[-1][0]}（{sum(1 for x in pb if x[0] >= 90)}/{len(pb)} 个号 >=90）" if pb else None, m.replay])
        out.append(dict(id=m.id, replay=True, bands={b: dict(n=d[b]['n'], p50=d[b]['p50'], p90=d[b]['p90'], max=d[b]['max'], ge35=d[b]['ge35'], ge90=d[b]['ge90']) for b in d},
                        botMin=pb[0][0] if pb else None, botMax=pb[-1][0] if pb else None, botGe90=sum(1 for x in pb if x[0] >= 90), bots=len(pb)))
    table(['局', '0~600', '600~1500', '1500~3000', '3000+', '各号 600~1500 的中位范围', '对局录像 / 日志侧读数'], rows)
    rp = [x for x in out if x['replay']]
    for b in BANDS:
        v = [x['bands'][b]['p50'] for x in rp if b in x['bands']]
        v9 = [x['bands'][b]['p90'] for x in rp if b in x['bands']]
        if v:
            print(f"   {b}：{len(v)} 局的 P50 = " + ' / '.join(str(x) for x in sorted(v)) + f"（各局 P50 的中位 {med(v):g}；各局 P90 的中位 {med(v9):g}）")
    lag = [x['id'] for x in rp if x['bands'].get('600~1500', {}).get('p50', 0) >= 90]
    print(f"   600~1500 的 P50 >=90 拍（约 5 秒）的局：{len(lag)}/{len(rp)}（{'、'.join(lag)}）；不到 35 拍的局：" + ('、'.join(x['id'] for x in rp if x['bands'].get('600~1500', {}).get('p50', 999) < 35) or '无'))
    wl = [x for x in out if not x['replay']]
    hit = [x['id'] for x in wl if any(c['lb'] >= 90 for c in x['wall'])]
    inwin = [x['id'] for x in wl if x['id'] not in hit and any(900 <= c['t'] <= 1650 for c in x['wall'])]
    none = [x['id'] for x in wl if x['id'] not in hit and x['id'] not in inwin]
    for x in wl:
        x['wallClass'] = 'lag' if x['id'] in hit else ('nolag' if x['id'] in inwin else 'unknown')
    print(f"   没有对局录像的 {len(wl)} 局（日志侧，结算行的墙上时钟对表）：有读数且日志位置至少落后 90 拍的 {len(hit)} 局（{'、'.join(hit) or '无'}）；"
          f"t=900~1650（有录像的落后局都在落后的那一段）有读数、不落后的 {'、'.join(inwin) or '无'}；这一段没有读数、看不出来的 {'、'.join(none) or '无'}。")
    print()
    return out


def sec_course(ms):
    print('### 延迟的时间过程（latency.py delay 的「每 150 拍一格」；格里是这一格下令的指令的延迟中位，拍）')
    ticks = list(range(300, 2551, 150))
    rows, out = [], []
    for m in ms:
        if not m.full:
            continue
        c = {x[0]: x for x in m.L.get('cells', [])}
        rows.append([m.id] + [c[t][2] if t in c else None for t in ticks])
        out.append(dict(id=m.id, cells={t: c[t][2] for t in ticks if t in c}, n={t: c[t][1] for t in ticks if t in c}))
    rows.append(['各局中位'] + [(f"{med([o['cells'].get(t) for o in out]):g}" if any(t in o['cells'] for o in out) else None) for t in ticks])
    table(['局 \\ 下令拍'] + [str(t) for t in ticks], rows)
    for o in out:
        ge = [t for t in ticks if o['cells'].get(t, 0) >= 90]
        pk = max(o['cells'].items(), key=lambda kv: kv[1]) if o['cells'] else None
        o['first90'] = ge[0] if ge else None
        o['last90'] = ge[-1] if ge else None
        o['peak'] = pk
    print('   各局：中位第一次 >=90 拍的格 / 最后一次 >=90 拍的格 / 峰值（格：拍）：' + '；'.join(f"{o['id']} {o['first90']} / {o['last90']} / {o['peak'][0]}：{o['peak'][1]}" if o['peak'] else o['id'] for o in out))
    print()
    return out


def sec_funnel(ms):
    print('### 漏斗（latency.py funnel；条）：影子下令 → 进录像 → 生效。「在打印」= 只算下令时本号日志还在打印的（客户端还在跑）')
    rows, out = [], []
    for m in ms:
        sc = m.G.get('sentchk') or []
        sent = sum((x.get('sent') or 0) for x in sc)
        acc = sum((x.get('accepted') or 0) for x in sc)
        cs = sum((x.get('cmds') or 0) + (x.get('spawnLines') or 0) for x in sc)
        o = dict(id=m.id, replay=m.full, sent=sent, accepted=acc, cmdsPlusSpawn=cs, sentBots=len(sc))
        if not m.full:
            rows.append([m.id, None, None, None, None, None, f"{sent:,} / {acc:,} / {cs:,}"])
            out.append(o)
            continue
        fb = {b['band']: b for b in m.L['funnel']['bands']}
        fi = m.L['fidelity']

        def cell(b):
            f = fb.get(b)
            if not f:
                return None, None
            return (f"{f['shadow']}→{f['landed']}（{pc(f['landed'], f['shadow'], 0)}）→{f['ok']}（{pc(f['ok'], f['shadow'], 0)}）",
                    f"{f['lost']} / {f['pending']}（{f.get('pendingLive', '?')}）")
        a1, a2 = cell('600~1500')
        b1, b2 = cell('1500~3000')
        rows.append([m.id, a1, a2, b1, b2, f"{fi['logCmds']:,} / {fi['shadowCmds']:,} / {fi['landed']:,}", f"{sent:,} / {acc:,} / {cs:,}"])
        o.update(bands=fb, fidelity=fi)
        out.append(o)
    table(['局', '600~1500：影子→进录像→生效', '丢了或多想 / 末拍还在路上（在打印）', '1500~3000：影子→进录像→生效', '丢了或多想 / 末拍还在路上（在打印）', '日志 cmds / 影子 / 进录像', '结算行 sent / accepted / 日志 cmds+选点行'], rows)
    rp = [x for x in out if x['replay']]
    for b in ('0~600', '600~1500', '1500~3000', '3000+'):
        v = [x['bands'][b] for x in rp if b in x['bands']]
        if v:
            sh, la, ok = sum(x['shadow'] for x in v), sum(x['landed'] for x in v), sum(x['ok'] for x in v)
            print(f"   {b}（{len(v)} 局合计）：影子下令 {sh:,} → 进录像 {la:,}（{pc(la, sh)}）→ 生效 {ok:,}（{pc(ok, sh)}）；丢了或影子多想 {sum(x['lost'] for x in v):,}（{pc(sum(x['lost'] for x in v), sh)}）；"
                  f"重放末拍还在路上 {sum(x['pending'] for x in v):,}，其中下令时日志还在打印的 {sum(x.get('pendingLive', 0) for x in v):,}")
    print(f"   结算行（15 局、{sum(x['sentBots'] for x in out)} 个有结算行的号）：sent {sum(x['sent'] for x in out):,}、accepted {sum(x['accepted'] for x in out):,}（差 {sum(x['sent'] - x['accepted'] for x in out):,}）、日志 cmds + 选点行 {sum(x['cmdsPlusSpawn'] for x in out):,}")
    print()
    return out


def sec_void(ms):
    print('### 迟到落空 / 打错目标（latency.py void；陆攻，按执行拍分段）与打内置 AI 的进攻线（按开线拍分段）')
    rows, out = [], []
    for m in ms:
        if not m.full:
            continue
        ex = {v['band']: v for v in m.L['void'] if 'cls' not in v}
        ai = {v['band']: v for v in m.L['void'] if v.get('cls') == 'ai'}
        neu = {v['band']: v for v in m.L['void'] if v.get('cls') == 'neu'}

        def cell(b):
            v = ex.get(b)
            if not v or not v['atk']:
                return None
            return f"{v['atk']} / {v['void']}（{pc(v['void'], v['atk'], 0)}）/ {v['a1']} / {v['a2']} / {v['b']}（{wan(v['bSent'])}）"

        def cell_ai(b):
            v = ai.get(b)
            if not v or not v['sent']:
                return None
            return f"{wan(v['sent'])} / {wan(v['moved'])}（{pc(v['moved'], v['sent'], 0)}）"

        def cell_neu(b):
            v = neu.get(b)
            if not v or not v['sent']:
                return None
            return f"{wan(v['sent'])} / {wan(v['ret'])}（{pc(v['ret'], v['sent'], 0)}）"
        rows.append([m.id, cell('600~1500'), cell('1500~3000'), cell_ai('600~1500'), cell_ai('1500~3000'), cell_neu('600~1500'), cell_neu('1500~3000')])
        out.append(dict(id=m.id, exec=ex, ai=ai, neu=neu))
    table(['局', '执行拍 600~1500：陆攻 / 没生效 / 其中目标已出局 / 身边已没有无主地 / 打错（兵）', '执行拍 1500~3000：同左', '打 AI 的线 600~1500：出兵 / 目标出局后被改挂到无主地线', '打 AI 的线 1500~3000', '打无主地的线 600~1500：出兵 / 退回余额', '打无主地的线 1500~3000'], rows)
    for b in ('600~1500', '1500~3000', '3000+'):
        v = [o['exec'][b] for o in out if b in o['exec']]
        a = [o['ai'][b] for o in out if b in o['ai']]
        u = [o['neu'][b] for o in out if b in o['neu']]
        if v:
            atk = sum(x['atk'] for x in v)
            print(f"   执行拍 {b}（{len(v)} 局合计）：陆攻 {atk:,} 条，没生效 {sum(x['void'] for x in v):,}（{pc(sum(x['void'] for x in v), atk)}）= 目标已出局 {sum(x['a1'] for x in v):,}（想发 {wan(sum(x['a1Amt'] for x in v))}兵）"
                  f" + 身边已没有无主地 {sum(x['a2'] for x in v):,} + 已不接壤 {sum(x['a3'] for x in v):,} + 配不上影子 {sum(x['a0'] for x in v):,}；打错 {sum(x['b'] for x in v):,} 条（{wan(sum(x['bSent'] for x in v))}兵进了无主地线）")
        if a:
            print(f"      开线拍 {b} 打内置 AI 的线：{sum(x['lines'] for x in a):,} 条线、出兵 {wan(sum(x['sent'] for x in a))}、打掉 {wan(sum(x['spent'] for x in a))}、得地 {sum(x['gain'] for x in a):,} 格；"
                  f"目标出局后被改挂 {wan(sum(x['moved'] for x in a))}（{pc(sum(x['moved'] for x in a), sum(x['sent'] for x in a))}）")
        if u:
            print(f"      开线拍 {b} 打无主地的线：出兵 {wan(sum(x['sent'] for x in u))}、打掉 {wan(sum(x['spent'] for x in u))}、得地 {sum(x['gain'] for x in u):,} 格、线结束时退回余额 {wan(sum(x['ret'] for x in u))}（{pc(sum(x['ret'] for x in u), sum(x['sent'] for x in u))}）")
    rd = [(m.id, v) for m in ms if m.full for v in m.L['void'] if v.get('cls') == 'redir']
    if rd:
        s = lambda k: sum(v[k] for _, v in rd)
        print(f"   被改挂出来的无主地线（整局，{len(rd)} 局合计）：{s('lines'):,} 条，挂上去 {wan(s('sent'))}兵，之后打掉 {wan(s('spent'))}、得地 {s('gain'):,} 格、退回余额 {wan(s('ret'))}（{pc(s('ret'), s('sent'))}）；"
              f"挂着的拍数各局中位 = " + ' / '.join(f"{i} {v['durMed']}" for i, v in rd) + f"；最长 {max(v['durMax'] for _, v in rd)} 拍")
        for o in out:
            o['redir'] = next((v for i, v in rd if i == o['id']), None)
    print()
    return out


def sec_dups(ms):
    print('### 确认窗内重复下单（latency.py dups；按下令拍）与同拍批（latency.py batches；按执行拍）')
    rows, out = [], []
    for m in ms:
        if not m.full:
            continue
        du = {(v['band'], v['kind']): v for v in m.L['dups']}
        bt = {v['band']: v for v in m.L['batches']['bands']}

        def cd(b, k='atk'):
            v = du.get((b, k))
            return f"{v['dups']}/{v['base']}（{pc(v['dups'], v['base'], 0)}）" if v and v['base'] else None

        def cb(b):
            v = bt.get(b)
            return f"{v['batches']} / {v['cmds']} / {v['allVoid']} / {v['drain']}（{wan(v['drainCost'])}）" if v and v['batches'] else None
        boat = [v for (b, k), v in du.items() if k == 'boat' and b != '0~600']
        don = [v for (b, k), v in du.items() if k == 'don' and b != '0~600']
        rows.append([m.id, cd('600~1500'), cd('1500~3000'), cd('3000+'), f"{sum(v['dups'] for v in boat)}/{sum(v['base'] for v in boat)}" if boat else None,
                     f"{sum(v['dups'] for v in don)}/{sum(v['base'] for v in don)}" if don else None, cb('600~1500'), cb('1500~3000'), cb('3000+')])
        out.append(dict(id=m.id, dups={f"{b}|{k}": v for (b, k), v in du.items()}, batches=bt))
    table(['局', '陆攻重复 600~1500', '陆攻重复 1500~3000', '陆攻重复 3000+', '发船重复（t>=600）', '捐款重复（t>=600）', '同拍批 600~1500：批 / 条 / 整批没生效 / 清仓批（兵）', '同拍批 1500~3000', '同拍批 3000+'], rows)
    for b in ('600~1500', '1500~3000', '3000+'):
        v = [o['dups'][f"{b}|atk"] for o in out if f"{b}|atk" in o['dups']]
        w = [o['batches'][b] for o in out if b in o['batches']]
        if v:
            st = [sum(x['stack'][i] for x in v) for i in range(4)]
            print(f"   下令拍 {b}（{len(v)} 局合计）：配上的陆攻 {sum(x['base'] for x in v):,} 条里重复 {sum(x['dups'] for x in v):,} 条（{pc(sum(x['dups'] for x in v), sum(x['base'] for x in v))}）：生效 {sum(x['ok'] for x in v):,} 条、"
                  f"实发 {wan(sum(x['sent'] for x in v))}兵、手续费 {wan(sum(x['fee'] for x in v))}；没生效 {sum(x['void'] for x in v):,} 条；下令时已有 1 / 2 / 3 / >=4 条同目标在途：{st[0]} / {st[1]} / {st[2]} / {st[3]}")
        if w:
            print(f"      执行拍 {b} 同拍批：{sum(x['batches'] for x in w):,} 批 {sum(x['cmds'] for x in w):,} 条；整批没生效 {sum(x['allVoid'] for x in w)} 批；清仓批（抽走批前余额 >=50%）{sum(x['drain'] for x in w)} 批、共 {wan(sum(x['drainCost'] for x in w))}兵；第 2 条起多发 {wan(sum(x['extra'] for x in w))}兵")
    print()
    return out


def played_rates(C):
    f = C.get('flow')
    if not f:
        return None
    vor = {b['me']: b['vor'] for b in C['voronoi']['bots']}
    idle = [r for r in f['rows'] if r['t0'] < 150]
    live = [r for r in f['rows'] if r['t0'] >= 150]
    v_live = sum(vor.get(r['me'], 0) for r in live)
    return dict(idle=len(idle), idleNames=[r['name'].lstrip('*') for r in idle], idleVor=sum(vor.get(r['me'], 0) for r in idle), live=len(live),
                r0=sum(r['t0'] for r in live) / v_live if v_live else None, r1=sum(r['t1'] for r in live) / v_live if v_live else None, t0=f['t0'], t1=f['t1'])


def sec_land(ms):
    print('### 好地账 1：天然份额（陆路 Voronoi，按真实出生点）与实抢 ÷ 天然份额（landcap.py voronoi / capture）')
    rows, out = [], []
    for m in ms:
        v = m.C.get('voronoi')
        if not v:
            rows.append([m.id] + [None] * 8 + ['没有录像：出生点真值没有'])
            out.append(dict(id=m.id, replay=False))
            continue
        cap = m.C.get('capture') or []
        o = dict(id=m.id, replay=True, squad=v['squad'], humans=v['humans'], squadVor=v['squadVor'], reach=v['reach'], ratio=v['squadVor'] / v['reach'] / (v['squad'] / v['humans']),
                 squadMed=v['squadMed'], otherMed=v['otherMed'], small=v['small'], bottom=v['bottom16'], top=v['top16'], capture=cap, played=played_rates(m.C), logCapture=(m.C.get('logCapture') or {}).get('ticks'))
        c0 = cap[0] if cap else None
        c1 = cap[1] if len(cap) > 1 else None
        fmt = lambda c: f"t={c['t']}：{100 * c['squadRate']:.1f}%（{100 * c['squadMedRate']:.1f}%）对 {100 * c['otherRate']:.1f}%（{100 * c['otherMedRate']:.1f}%）" if c else None
        note = ''
        if o['played'] and o['played']['idle']:
            p = o['played']
            note = f"去掉没扩张的 {p['idle']} 个号：{100 * p['r0']:.1f}% → {100 * p['r1']:.1f}%"
        if not cap and o['logCapture']:
            note = '只有日志快照：' + '；'.join(f"t={t['t']} {t['haveSnap']} 个号 {100 * t['haveRate']:.1f}%（中位 {100 * t['medRate']:.1f}%）" for t in o['logCapture'])
        rows.append([m.id, f"{v['squad']}/{v['humans']}", f"{v['squadVor']:,}（{100 * v['squadVor'] / v['reach']:.1f}%）", f"{100 * v['squad'] / v['humans']:.1f}%", f"{o['ratio']:.2f}",
                     f"{v['squadMed']:,} / {v['otherMed']:,}", f"{v['small']} / {v['bottom16']} / {v['top16']}", fmt(c0), fmt(c1), note])
        out.append(o)
    table(['局', '席位 / 真人', '我方天然份额 格（占可达陆地）', '人头占比', '÷人头', '单号中位：我方 / 其他真人', '不到人均一半 / 后四分之一 / 前四分之一（个）', '实抢率 ①：我方（单号中位）对其他真人（单号中位）', '实抢率 ②', '备注'], rows)
    rp = [x for x in out if x['replay']]
    print(f"   有出生点真值的 {len(rp)} 局：÷人头 = " + ' / '.join(f"{x['ratio']:.2f}" for x in sorted(rp, key=lambda x: x['ratio'])) + f"（中位 {med([x['ratio'] for x in rp]):.2f}）；<1 的 {sum(1 for x in rp if x['ratio'] < 1)} 局、<0.8 的 {sum(1 for x in rp if x['ratio'] < 0.8)} 局；"
          f"单号中位比其他真人低的 {sum(1 for x in rp if x['squadMed'] < x['otherMed'])} 局；{sum(x['squad'] for x in rp)} 个席位里天然份额不到全场人均一半的 {sum(x['small'] for x in rp)} 个、排在全场后四分之一的 {sum(x['bottom'] for x in rp)} 个、前四分之一的 {sum(x['top'] for x in rp)} 个")
    fc = [x for x in rp if len(x['capture']) > 1]
    if fc:
        print(f"   有对局网格的 {len(fc)} 局：第一断面（t=630）合计实抢率我方高于其他真人的 {sum(1 for x in fc if x['capture'][0]['squadRate'] > x['capture'][0]['otherRate'])} 局；"
              f"第二断面（t=1500，录像不够长的取末拍）我方高于其他真人的 {sum(1 for x in fc if x['capture'][1]['squadRate'] > x['capture'][1]['otherRate'])} 局（" + '、'.join(x['id'] for x in fc if x['capture'][1]['squadRate'] > x['capture'][1]['otherRate']) + '）；'
              f"单号中位我方高于其他真人的 {sum(1 for x in fc if x['capture'][1]['squadMedRate'] > x['capture'][1]['otherMedRate'])} 局")
    print()
    return out


def sec_ai(ms):
    print('### 好地账 2：身边的内置 AI 地去了哪（landcap.py ai / flow）。身边 = t=630 与我方接壤、或一半以上的格在我方天然份额里')
    rows, out = [], []
    for m in ms:
        a = m.C.get('ai')
        f = m.C.get('flow')
        if not a:
            continue
        lat = {x['t']: x for x in a['later']}
        ts = [t for t in (900, 1200, 1500, 1800) if t in lat]
        if 1500 not in lat:
            ts = [x['t'] for x in a['later'] if x['t'] <= 1800]
        ref = [x for x in a['later'] if x['t'] <= 1500][-1]
        ns = len(f['rows'])
        o = dict(id=m.id, n=a['n'], cells=a['cells'], allCells=a['allCells'], later={x['t']: dict(squad=x['near']['squad'] / x['near']['n'] if x['near']['n'] else None, other=x['near']['other'] / x['near']['n'] if x['near']['n'] else None,
                                                                                     restSquad=x['rest']['squad'] / x['rest']['n'] if x['rest']['n'] else None, restOther=x['rest']['other'] / x['rest']['n'] if x['rest']['n'] else None) for x in a['later']},
                 refT=ref['t'], perCapAi=[f['squad']['g_ai'] // max(1, ns), f['other']['fromAi'] // max(1, f['other']['n'])],
                 perCapNet=[(f['squad']['t1'] - f['squad']['t0']) // max(1, ns), (f['other']['t1'] - f['other']['t0']) // max(1, f['other']['n'])], flowT=[f['t0'], f['t1']])
        rows.append([m.id, f"{a['n']} 个 / {a['cells']:,} 格（{pc(a['cells'], a['allCells'], 0)}）", ' / '.join(str(t) for t in ts), ' / '.join(pc(lat[t]['near']['squad'], lat[t]['near']['n'], 0) for t in ts),
                     ' / '.join(pc(lat[t]['near']['other'], lat[t]['near']['n'], 0) for t in ts), f"t={ref['t']}：{pc(ref['rest']['squad'], ref['rest']['n'])} / {pc(ref['rest']['other'], ref['rest']['n'])}",
                     f"{o['perCapAi'][0]:,} / {o['perCapAi'][1]:,}", f"{o['perCapNet'][0]:,} / {o['perCapNet'][1]:,}"])
        out.append(o)
    table(['局', '身边的 AI：个数 / 格（占全场 AI 地）', '断面拍', '→ 我方', '→ 其他真人', '其余 AI 地 → 我方 / 其他真人', 't=630→1500 人均从 AI 手里拿到：我方 / 其他真人（格）', '人均净增：我方 / 其他真人（格）'], rows)
    f15 = [o for o in out if 1500 in o['later']]
    if f15:
        print(f"   录像到 t=1500 的 {len(f15)} 局：身边 AI 地到 t=1500 我方拿到的比例 = " + ' / '.join(f"{o['id']} {100 * o['later'][1500]['squad']:.0f}%" for o in sorted(f15, key=lambda o: o['later'][1500]['squad']))
              + f"（中位 {100 * med([o['later'][1500]['squad'] for o in f15]):.0f}%）；其他真人拿走的中位 {100 * med([o['later'][1500]['other'] for o in f15]):.0f}%；"
              f"其余 AI 地我方拿到的中位 {100 * med([o['later'][1500]['restSquad'] for o in f15]):.1f}%、其他真人 {100 * med([o['later'][1500]['restOther'] for o in f15]):.0f}%")
    print(f"   人均从 AI 手里拿到的地我方 < 其他真人的 {sum(1 for o in out if o['perCapAi'][0] < o['perCapAi'][1])}/{len(out)} 局；我方 ÷ 其他真人 = " + ' / '.join(f"{o['id']} {o['perCapAi'][0] / max(1, o['perCapAi'][1]):.2f}" for o in out))
    rn = [(o['id'], o['perCapNet'][0] / max(1, o['perCapNet'][1])) for o in out]
    print(f"   人均净增（同一段的全部来源：无主地 + AI + 真人 − 丢的）我方 < 其他真人的 {sum(1 for _, r in rn if r < 1)}/{len(rn)} 局；我方 ÷ 其他真人 = " + ' / '.join(f"{i} {r:.2f}" for i, r in rn)
          + f"（中位 {med([r for _, r in rn]):.2f}）")
    print()
    return out


def sec_layers(ms):
    print('### 好地账 3：t=600~1500 没抢到内置 AI 地的三层归因（landcap.py layers；三层不互斥、不相加）')
    rows, out = [], []
    for m in ms:
        y = m.C.get('layers')
        if not y or 'gates' not in y:
            continue
        sp, g, la = y['spawn'], y['gates'], y.get('late') or {}
        diff = sp['squadVor'] - sp['par']
        o = dict(id=m.id, spawnDiff=diff / sp['par'], n=g['n'], ok=g['ok'] / g['n'], botOk=g['botOk'] / g['n'], sf=g['safeFinite'] / g['n'], sfSquad=g['safeFiniteSquad'] / g['n'], sfNoPass=g['safeFiniteNoPass'] / g['n'],
                 winR=g['winR'] / g['n'], dpKeep=g['dpKeep'] / g['n'], atk=la.get('atk'), a1=la.get('a1'), a1Amt=la.get('a1Amt'), b=la.get('b'), bSent=la.get('bSent'), aiSent=la.get('aiSent'), aiMoved=la.get('aiMoved'))
        rows.append([m.id, f"{100 * o['spawnDiff']:+.1f}%", f"{g['n']:,}", pc(g['ok'], g['n']), pc(g['botOk'], g['n']), f"{pc(g['safeFinite'], g['n'])}（{pc(g['safeFiniteSquad'], g['n'])}）", pc(g['safeFiniteNoPass'], g['n']), pc(g['winR'], g['n']), pc(g['dpKeep'], g['n']),
                     la.get('atk'), f"{la.get('a1')}（{pc(la.get('a1', 0), la.get('atk'))}）", f"{la.get('b')}（{wan(la.get('bSent'))}）", pc(la.get('aiMoved', 0), la.get('aiSent'))])
        out.append(o)
    table(['局', '① 天然份额比按人头', '② 有 AI 邻居的决策拍', '可出兵', '卡在地价闸', '底线取 safeFinite、去掉就能出兵（其中参照我方号或空壳）', 'safeFinite 去掉也不够', '底线取 winR', '底线取 dpKeep', '③ 陆攻（执行拍 600~1500）', '落空：目标已出局', '打错（兵）', '打 AI 的兵被改挂'], rows)
    if out:
        tot = sum(o['n'] for o in out)
        w = lambda k: sum(o[k] * o['n'] for o in out) / tot
        print(f"   ② {len(out)} 局合计 {tot:,} 个决策拍：可出兵 {100 * w('ok'):.1f}%、地价闸 {100 * w('botOk'):.1f}%、safeFinite 去掉就能出兵 {100 * w('sf'):.1f}%（参照我方号或空壳 {100 * w('sfSquad'):.1f}%）、safeFinite 去掉也不够 {100 * w('sfNoPass'):.1f}%、"
              f"winR {100 * w('winR'):.1f}%、dpKeep {100 * w('dpKeep'):.1f}%")
        print(f"   ③ {len(out)} 局合计：陆攻 {sum(o['atk'] for o in out):,} 条，落空 {sum(o['a1'] for o in out):,}（{pc(sum(o['a1'] for o in out), sum(o['atk'] for o in out))}；想发 {wan(sum(o['a1Amt'] for o in out))}兵）、"
              f"打错 {sum(o['b'] for o in out):,} 条（{wan(sum(o['bSent'] for o in out))}兵）；打 AI 的线出兵 {wan(sum(o['aiSent'] for o in out))}、被改挂 {wan(sum(o['aiMoved'] for o in out))}（{pc(sum(o['aiMoved'] for o in out), sum(o['aiSent'] for o in out))}）")
        print('   ① 各局：' + ' / '.join(f"{o['id']} {100 * o['spawnDiff']:+.0f}%" for o in sorted(out, key=lambda o: o['spawnDiff'])))
    print()
    return out


GATE_BANDS = ['1500~3000', '3000~4284', '4284+']
HUM_KEYS = [('send', '出兵'), ('price', '地价闸 L5267'), ('dpKeep', '保底线 dpKeep L5361'), ('sbOurs', '保底线 safeFinite·我方号 L5361'), ('sbOther', '保底线 safeFinite·别人 L5361'),
            ('chunk', '买不起整笔 L5528'), ('sole', '唯一真人缓冲 L5271'), ('crowded', 'crowdedHard L5280'), ('siege', 'siegeShrink L5345'), ('inflight', '在途兵已够'), ('pulse', 'pulse 太小'),
            ('later', '前一个报价已 break'), ('other', '其他')]
AI_KEYS = [('send', '出兵'), ('minCmd', '单太小 < minCmd L5367'), ('chunk', '买不起整笔 L5367'), ('dpKeep', '保底线 dpKeep L5361'), ('sbOursPass', 'safeFinite·我方号、去掉就能出兵'),
           ('sbOther', 'safeFinite·其余'), ('already', '已在打它 L5364'), ('price', '地价闸 L5267'), ('later', '前一个报价已 break'), ('other', '其他')]


def sec_gates(ms):
    print('### 核心期（t>=1500）有兵不出手：影子策略每个决策拍从 buyLand 的哪一行出去（coregates.py；录像到 t>=1500 的局）')
    print('   影子 = 策略源码跑在录像重演的真实局面上，指令只记不执行。真人报价的决策拍 = offers 里至少有一个真人邻居；这一拍对真人出了兵记「出兵」，否则记排第一的真人报价的出口。')
    out = []
    ks = [m for m in ms if m.K.get('bands')]
    add = lambda d, e: [d.__setitem__(k, d.get(k, 0) + v) for k, v in e.items()]
    for title, side, keys in (('真人报价', 'hum', HUM_KEYS), ('非真人报价（内置 AI / 空壳）', 'ai', AI_KEYS)):
        rows = []
        tot_b = {b: {} for b in GATE_BANDS}
        n_b = {b: 0 for b in GATE_BANDS}
        for m in ks:
            ex, n = {}, 0
            for b in GATE_BANDS:
                y = (m.K['bands'].get(b) or {}).get(side)
                if not y or not y['n']:
                    continue
                add(ex, y['exits'])
                add(tot_b[b], y['exits'])
                n += y['n']
                n_b[b] += y['n']
            if not n:
                continue
            rows.append([m.id, f"{n:,}"] + [pc(ex.get(k, 0), n) if ex.get(k) else '0' for k, _ in keys])
            out.append(dict(id=m.id, side=side, n=n, exits=ex))
        for b in GATE_BANDS:
            if n_b[b]:
                rows.append([f"合计 {b}", f"{n_b[b]:,}"] + [pc(tot_b[b].get(k, 0), n_b[b]) if tot_b[b].get(k) else '0' for k, _ in keys])
        allx = {}
        for b in GATE_BANDS:
            add(allx, tot_b[b])
        na = sum(n_b.values())
        if na:
            rows.append(['合计 t>=1500', f"{na:,}"] + [pc(allx.get(k, 0), na) if allx.get(k) else '0' for k, _ in keys])
            out.append(dict(id='ALL', side=side, n=na, exits=allx, byBand={b: dict(n=n_b[b], exits=tot_b[b]) for b in GATE_BANDS}))
        print(f"**{title}的决策拍：出口占比**")
        table(['局', '决策拍'] + [t for _, t in keys], rows)
    # 被打不还手、超软上限出不出手、地价闸上的报价
    rows = []
    T = dict(onMe=0, onMeNoSend=0, overN=0, overSend=0, underN=0, underSend=0, noSendDon=0)
    TB = {b: dict(T) for b in GATE_BANDS}
    om_all = {}
    for m in ks:
        s = dict(onMe=0, onMeNoSend=0, overN=0, overSend=0, underN=0, underSend=0, noSendDon=0)
        om = {}
        pg = []
        for b in GATE_BANDS:
            h = (m.K['bands'].get(b) or {}).get('hum')
            if not h or not h['n']:
                continue
            for k in s:
                s[k] += h.get(k, 0)
                TB[b][k] += h.get(k, 0)
            add(om, h.get('onMeNoSendExits') or {})
            g = h.get('priceGate') or {}
            if g.get('n'):
                pg.append(f"{b}：{g['hcMed']:.0f} / {g['worthMed']:.0f} / {g['ratioMed']:.2f} / {g['densMed']:.0f}")
        for k in s:
            T[k] += s[k]
        add(om_all, om)
        top = '、'.join(f"{dict(HUM_KEYS).get(k, k).split(' L')[0]} {v}" for k, v in sorted(om.items(), key=lambda kv: -kv[1])[:4])
        rows.append([m.id, f"{s['onMe']:,}", f"{s['onMeNoSend']:,}（{pc(s['onMeNoSend'], s['onMe'])}）", top, f"{s['overN']:,}：{pc(s['overSend'], s['overN'])}", f"{s['underN']:,}：{pc(s['underSend'], s['underN'])}",
                     s['noSendDon'], '；'.join(pg)])
        out.append(dict(id=m.id, side='onMe', **s, onMeNoSendExits=om))
    table(['局', '正被真人打的决策拍', '其中这一拍没有对任何真人出兵', '这些拍卡在哪（前 4）', '超软上限的拍：出兵比例', '没超软上限的拍：出兵比例', '没对真人出兵、同拍影子发了捐款', '地价闸上的拍：最低真人报价 / worth / 报价÷worth / 自己密度（中位）'], rows)
    if T['onMe']:
        top = '、'.join(f"{dict(HUM_KEYS).get(k, k)} {v:,}（{pc(v, T['onMeNoSend'])}）" for k, v in sorted(om_all.items(), key=lambda kv: -kv[1])[:6])
        print(f"   {len(ks)} 局合计：正被真人打的决策拍 {T['onMe']:,}，其中这一拍没有对任何真人出兵 {T['onMeNoSend']:,}（{pc(T['onMeNoSend'], T['onMe'])}）；卡在：{top}")
        print(f"   超软上限的决策拍 {T['overN']:,}，出兵 {T['overSend']:,}（{pc(T['overSend'], T['overN'])}）；没超软上限的 {T['underN']:,}，出兵 {T['underSend']:,}（{pc(T['underSend'], T['underN'])}）；"
              f"没对真人出兵而同拍影子发了捐款的 {T['noSendDon']:,} 拍")
        for b in GATE_BANDS:
            x = TB[b]
            if x['onMe'] or x['overN'] or x['underN']:
                print(f"      {b}：被打 {x['onMe']:,}、没还手 {x['onMeNoSend']:,}（{pc(x['onMeNoSend'], x['onMe'])}）；超软上限 {x['overN']:,}、出兵 {pc(x['overSend'], x['overN'])}；没超 {x['underN']:,}、出兵 {pc(x['underSend'], x['underN'])}")
        out.append(dict(id='ALL', side='onMe', **T, onMeNoSendExits=om_all, byBand=TB))
    print('   口径：一个决策拍只记一个出口（排第一的真人报价）；「没出兵」是策略在真实局面上当拍的决定，不是录像里有没有指令落地。同一个号的相邻决策拍高度相关，占比只作描述。')
    print()
    return out


def sec_donflow(ms):
    print('### 输血账（录像真值，donflow.py）：我方号捐出、已执行的每一笔，按千分比档、收款人、收款后 300 拍做了什么')
    print('   手续费 = 捐款人余额的 6.25%，与 pct 无关；到账 = min(余额×(pct+1)/1024, 余额−手续费, 收款人离硬上限的余量)。损耗率 = 手续费 ÷ (手续费 + 到账)。')
    ds = [m.F for m in ms if m.F.get('n')]
    if not ds:
        print('   （没有 donflow.json）')
        print()
        return []
    f = lambda a: f"{a['n']} / {wan(a['delivered'])} / {wan(a['fee'])}（{pc(a['fee'], a['fee'] + a['delivered'], 0)}）" if a and a.get('n') else '0'
    z = lambda: dict(n=0, delivered=0, fee=0)

    def addacc(a, b):
        if b:
            for k in ('n', 'delivered', 'fee'):
                a[k] += b.get(k, 0)
        return a
    pk = ['<64', '64~149', '150~199', '200~299', '>=300']
    rows = []
    tot = dict(all=z(), pct={k: z() for k in pk}, husk=z(), trunc=z(), short=0, zero_n=0, zero_fee=0)
    for d in ds:
        husk = addacc(addacc(z(), d['to'].get('我方空壳')), d['to'].get('外人空壳'))
        rows.append([d['matchId'], f(d)] + [f(d['pct'].get(k)) for k in pk] + [f(husk), f"{f(d['trunc'])}，少到账 {wan(d['trunc']['short'])}", f"{d['zero']['n']} 笔 / 费 {wan(d['zero']['fee'])}"])
        addacc(tot['all'], d)
        for k in pk:
            addacc(tot['pct'][k], d['pct'].get(k))
        addacc(tot['husk'], husk)
        addacc(tot['trunc'], d['trunc'])
        tot['short'] += d['trunc']['short']
        tot['zero_n'] += d['zero']['n']
        tot['zero_fee'] += d['zero']['fee']
    rows.append(['合计', f(tot['all'])] + [f(tot['pct'][k]) for k in pk] + [f(tot['husk']), f"{f(tot['trunc'])}，少到账 {wan(tot['short'])}", f"{tot['zero_n']} 笔 / 费 {wan(tot['zero_fee'])}"])
    table(['局', '已执行：笔 / 到账 / 手续费（损耗率）', 'pct <64', '64~149', '150~199', '200~299', '>=300', '给空壳', '被截断（到账 < 名义值的 90%）', '到账 = 0'], rows)
    # 收款人状态与之后 300 拍
    dk = ['<50', '50~100', '100~125', '>=125']
    rows = []
    T = dict(dens={k: z() for k in dk}, fire=z(), ddead=z(), W=dict(n=0, recv=0, spentCap=0, donOutCap=0, donOutFee=0, gain=0, noCmd=0, noCmdRecv=0, lt=0, ltRecv=0, dead=0, deadRecv=0), pp=dict(pairs=0, fee=0, back=0),
             F=dict(all=0, noCmd=0, donOut=0, spent=0, dead=0, none=0))
    for d in ds:
        W = d.get('windows') or {}
        F = d.get('follow') or {}
        rows.append([d['matchId']] + [f(d['dens'].get(k)) for k in dk] + [f(d['underFire']), f(d['donorDead']),
                    f"{W.get('n', 0)} 个 / {wan(W.get('recv', 0))}", f"{wan(W.get('spentCap', 0))}（{pc(W.get('spentCap', 0), W.get('recv', 0), 0)}）",
                    f"{wan(W.get('donOutCap', 0))}（{pc(W.get('donOutCap', 0), W.get('recv', 0), 0)}）；再付 {wan(W.get('donOutFee', 0))}",
                    f"{W.get('spentLtTenth', {}).get('n', 0)} 个 / {wan(W.get('spentLtTenth', {}).get('recv', 0))}（{pc(W.get('spentLtTenth', {}).get('recv', 0), W.get('recv', 0), 0)}）",
                    f"{W.get('noCmd', {}).get('n', 0)} 个 / {wan(W.get('noCmd', {}).get('recv', 0))}",
                    f"{d['pingpong']['pairs']} 组 / 费 {wan(d['pingpong']['fee'])}"])
        for k in dk:
            addacc(T['dens'][k], d['dens'].get(k))
        addacc(T['fire'], d['underFire'])
        addacc(T['ddead'], d['donorDead'])
        for k in ('n', 'recv', 'spentCap', 'donOutCap', 'donOutFee', 'gain'):
            T['W'][k] += W.get(k, 0)
        T['W']['noCmd'] += W.get('noCmd', {}).get('n', 0)
        T['W']['noCmdRecv'] += W.get('noCmd', {}).get('recv', 0)
        T['W']['lt'] += W.get('spentLtTenth', {}).get('n', 0)
        T['W']['ltRecv'] += W.get('spentLtTenth', {}).get('recv', 0)
        T['W']['dead'] += W.get('dead', {}).get('n', 0)
        T['W']['deadRecv'] += W.get('dead', {}).get('recv', 0)
        for k in T['pp']:
            T['pp'][k] += d['pingpong'][k]
        for k in T['F']:
            T['F'][k] += (F.get(k) or {}).get('n', 0)
    W = T['W']
    rows.append(['合计'] + [f(T['dens'][k]) for k in dk] + [f(T['fire']), f(T['ddead']), f"{W['n']} 个 / {wan(W['recv'])}", f"{wan(W['spentCap'])}（{pc(W['spentCap'], W['recv'], 0)}）",
                f"{wan(W['donOutCap'])}（{pc(W['donOutCap'], W['recv'], 0)}）；再付 {wan(W['donOutFee'])}", f"{W['lt']} 个 / {wan(W['ltRecv'])}（{pc(W['ltRecv'], W['recv'], 0)}）", f"{W['noCmd']} 个 / {wan(W['noCmdRecv'])}",
                f"{T['pp']['pairs']} 组 / 费 {wan(T['pp']['fee'])}"])
    table(['局', '收款时密度 <50（在场的我方号）', '50~100', '100~125', '>=125', '收款时正被人打', '捐款人 300 拍内阵亡', '收款窗口：个 / 收到', '窗口内战斗耗兵至多抵掉', '窗口内又捐出去至多；这些再捐的手续费', '窗口内战斗耗兵不到收到的一成', '窗口内没有任何陆攻 / 发船指令', '对倒（150 拍内原路捐回）'], rows)
    Fa = T['F']
    print(f"   逐笔打标（在场的我方号收款、之后还有 300 拍录像的 {Fa['all']:,} 笔；一笔可挂几个标）：收款人 300 拍内没有任何陆攻 / 发船指令进录像 {Fa['noCmd']:,}（{pc(Fa['noCmd'], Fa['all'])}）；"
          f"又捐出 >= 到账的一半 {Fa['donOut']:,}（{pc(Fa['donOut'], Fa['all'])}）；战斗耗兵 >= 到账的一半 {Fa['spent']:,}（{pc(Fa['spent'], Fa['all'])}）；收款人阵亡 {Fa['dead']:,}（{pc(Fa['dead'], Fa['all'])}）；三样都不沾 {Fa['none']:,}")
    print('   收款窗口 = 同一个收款人相隔 <=300 拍的几笔并成一个 [第一笔, 最后一笔+300]，窗口之间不重叠。「至多」= min(收到, 窗口内的战斗耗兵 / 又捐出)：收款人自己的利息也在花，所以是上限。')
    # 按代码分支（由 pct 反推 tryDonateToTeammate 走的哪一支）；后排 = 被围或纯内陆的捐款人
    BRN = ['盈余·不被围（153）', '盈余·被围（185 / 280）', '救援（155）', '救援·纯内陆（240）', '救援·被钳小（<155）', '救援·纯内陆被钳（156~239）', '其他']
    REAR = ('盈余·被围（185 / 280）', '救援·纯内陆（240）', '救援·纯内陆被钳（156~239）')
    keys = ('n', 'delivered', 'fee', 'truncN', 'short', 'husk', 'huskFee', 'fAll', 'fSpent', 'fDonOut', 'fNoCmd', 'fDead', 'fire', 'live', 'up', 'upDelivered', 'upFee', 'recv100', 'recv100Fee')
    BT = {k: dict({x: 0 for x in keys}, donorDens=[], recvDens=[]) for k in BRN + ['后排合计', '前排合计']}
    for d in ds:
        for k, v in (d.get('branch') or {}).items():
            for tgt in (k, '后排合计' if k in REAR else '前排合计'):
                for x in keys:
                    BT[tgt][x] += v.get(x, 0)
                BT[tgt]['donorDens'] += v.get('donorDens', [])
                BT[tgt]['recvDens'] += v.get('recvDens', [])
    if any(BT[k]['n'] for k in BRN):
        print()
        print('**按代码分支（由 pct 反推 `tryDonateToTeammate` L4369-4499 走的哪一支）。后排 = 捐款时被围（boxedIn）或纯内陆（isPureInlandSafe）的捐款人**')
        rows = []
        md = lambda v: (f"{sorted(v)[len(v) // 2]:.0f}" if v else '—')
        for k in BRN + ['后排合计', '前排合计']:
            v = BT[k]
            if not v['n']:
                continue
            rows.append([k, f"{v['n']}", wan(v['delivered']), f"{wan(v['fee'])}（{pc(v['fee'], v['fee'] + v['delivered'])}）", f"{v['truncN']} 笔 / 少到账 {wan(v['short'])}", f"{v['husk']} 笔 / 费 {wan(v['huskFee'])}",
                         md(v['donorDens']), md(v['recvDens']), f"{v['up']}/{v['live']}（{pc(v['up'], v['live'], 0)}）：到账 {wan(v['upDelivered'])}、费 {wan(v['upFee'])}", f"{v['recv100']}（{pc(v['recv100'], v['live'], 0)}）", f"{v['fire']}（{pc(v['fire'], v['n'], 0)}）",
                         f"{v['fSpent']}/{v['fAll']}（{pc(v['fSpent'], v['fAll'], 0)}）", f"{v['fDonOut']}/{v['fAll']}（{pc(v['fDonOut'], v['fAll'], 0)}）", f"{v['fNoCmd']}/{v['fAll']}（{pc(v['fNoCmd'], v['fAll'], 0)}）", f"{v['fDead']}/{v['fAll']}"])
        table(['分支', '笔', '到账', '手续费（损耗率）', '被截断', '给空壳', '捐款人密度中位', '收款人密度中位（在场的我方号）', '收款人比捐款人还密', '收款人密度 >=100', '收款时正被人打', '之后 300 拍战斗耗兵 >= 到账的一半', '又捐出 >= 一半', '零陆攻 / 发船指令', '阵亡'], rows)
        print('   153 也可能是救援捐款被 maxSafePct 钳出来的，分不开，全算盈余。任务卡里的 ECO_BANK 是后端选点协调器（spawn-coordinator-c110.mjs）分配的出生角色：15 局里 HL-SPAWN-BACKEND 0 行，没有号被分到过角色，局内代码也不读角色；这里的「后排」按捐款时的局面定义。')
    print()
    return [dict(id=d['matchId'], n=d['n'], delivered=d['delivered'], fee=d['fee'], pct=d['pct'], to=d['to'], dens=d['dens'], trunc=d['trunc'], zero=d['zero'], underFire=d['underFire'],
                 windows=d.get('windows'), follow=d.get('follow'), pingpong=d['pingpong']) for d in ds] + [dict(id='ALL', tot=tot, T=T)]


def sec_foes(ms):
    print('### 对手画像（录像真值，foeprofile.py）：外人真人对「在场的我方号」的陆攻、围攻、登陆，和外人之间的捐款')
    print('   打击 = 外人真人对在场我方号（异队、没离开）生效的陆攻指令。目标密度 = 目标当拍 兵 ÷ 地；出手方密度 = 出手前余额 ÷ 它的地；兵力比 = 出手前余额 ÷ 目标的兵。'
          '刚清过仓 = 目标当拍的兵不到之前 150 拍最高值的一半、而领土没掉 10%。')
    ps = [m.P for m in ms if m.P.get('hits') and m.P['endT'] >= 1500]
    if not ps:
        print('   （没有 foeprofile.json）')
        print()
        return []
    g = lambda d, k, f='troops': (d.get(k) or {}).get(f, 0)
    rows = []
    T = dict(n=0, troops=0, lowN=0, lowT=0, midT=0, hiT=0, a90=0, r2=0, dN=0, dT=0, p100=0, p200=0, p900=0)
    for d in ps:
        h = d['hits']
        low_n, low_t = g(h['tdens'], '<35', 'n'), g(h['tdens'], '<35')
        mid_t = g(h['tdens'], '60~100')
        hi_t = g(h['tdens'], '>=100')
        a90 = g(h['adens'], '90~110') + g(h['adens'], '>=110')
        r2 = g(h['ratio'], '2~4') + g(h['ratio'], '>=4')
        p100, p200, p900 = g(h['pct'], '100~199'), g(h['pct'], '200~399'), g(h['pct'], '>=900')
        rows.append([d['matchId'], f"{h['n']} / {wan(h['troops'])}", f"{pc(low_n, h['n'], 0)} / {pc(low_t, h['troops'])}", pc(mid_t, h['troops'], 0), pc(hi_t, h['troops'], 0), h['tdensMed'], pc(a90, h['troops'], 0), h['adensMed'],
                     pc(r2, h['troops'], 0), f"{h['pctMed']:.0f}‰：{pc(p100, h['troops'], 0)} / {pc(p200, h['troops'], 0)} / {pc(p900, h['troops'], 0)}", f"{h['dumped']['n']}（{pc(h['dumped']['n'], h['n'], 0)}）/ {pc(h['dumped']['troops'], h['troops'])}"])
        for k, v in (('n', h['n']), ('troops', h['troops']), ('lowN', low_n), ('lowT', low_t), ('midT', mid_t), ('hiT', hi_t), ('a90', a90), ('r2', r2), ('dN', h['dumped']['n']), ('dT', h['dumped']['troops']),
                     ('p100', p100), ('p200', p200), ('p900', p900)):
            T[k] += v
    rows.append(['合计', f"{T['n']:,} / {wan(T['troops'])}", f"{pc(T['lowN'], T['n'], 0)} / {pc(T['lowT'], T['troops'])}", pc(T['midT'], T['troops'], 0), pc(T['hiT'], T['troops'], 0), None, pc(T['a90'], T['troops'], 0), None, pc(T['r2'], T['troops'], 0),
                 f"{pc(T['p100'], T['troops'], 0)} / {pc(T['p200'], T['troops'], 0)} / {pc(T['p900'], T['troops'], 0)}", f"{T['dN']}（{pc(T['dN'], T['n'], 0)}）/ {pc(T['dT'], T['troops'])}"])
    table(['局', '打击：条 / 兵', '目标密度 <35：条占比 / 兵占比', '目标密度 60~100：兵占比', '目标密度 >=100：兵占比', '目标密度中位（按条）', '出手方密度 >=90：兵占比', '出手方密度中位（按条）', '兵力比 >=2：兵占比',
           '千分比中位：100~199 / 200~399 / >=900 的兵占比', '目标刚清过仓：条（占比）/ 兵占比'], rows)
    rows = []
    S = dict(n=0, troops=0, mine=0, others=0, zero=0, died=0, half=0, bigL=0, bigLT=0, fdN=0, fdD=0, fdHiN=0, fdHiD=0)
    for d in ps:
        s, ld, f = d['sieges'], d['landings'], d['foeDon']
        top = f['top'][0] if f['top'] else None
        win = next((m.oc.get('winnerTeam') for m in ms if m.id == d['matchId']), None)
        rows.append([d['matchId'], f"{s['n']} / {wan(s['troops'])}", s['tdensMed'], s['fdensMed'], s['ratioMed'], f"{wan(s['mine'])}（{pc(s['mine'], s['troops'], 0)}）", f"{s['zeroBack']}/{s['n']}", wan(s['others']),
                     f"{s['died']}/{s['n']}", f"{s['lostHalf']}/{s['n']}", f"{ld['big']} / {wan(ld['bigTroops'])}", f"{f['n']} / {wan(f['delivered'])}", f"{f['hiN']} / {wan(f['hiDelivered'])}",
                     f"{top['name']}（队{top['team']}{'·赢家队' if top['team'] == win else ''}）{wan(top['delivered'])}，峰值 {top['peakTerr']:,} 格" if top else None])
        for k, v in (('n', s['n']), ('troops', s['troops']), ('mine', s['mine']), ('others', s['others']), ('zero', s['zeroBack']), ('died', s['died']), ('half', s['lostHalf']), ('bigL', ld['big']), ('bigLT', ld['bigTroops']),
                     ('fdN', f['n']), ('fdD', f['delivered']), ('fdHiN', f['hiN']), ('fdHiD', f['hiDelivered'])):
            S[k] += v
    rows.append(['合计', f"{S['n']} / {wan(S['troops'])}", None, None, None, f"{wan(S['mine'])}（{pc(S['mine'], S['troops'], 0)}）", f"{S['zero']}/{S['n']}", wan(S['others']), f"{S['died']}/{S['n']}", f"{S['half']}/{S['n']}",
                 f"{S['bigL']} / {wan(S['bigLT'])}", f"{S['fdN']} / {wan(S['fdD'])}", f"{S['fdHiN']} / {wan(S['fdHiD'])}", None])
    table(['局', '围攻（>=20 万兵的组）：组 / 兵', '第一条时目标密度中位', '出手方密度中位', '兵力比中位', '目标自己还手（占对方出兵）', '一兵没还的组', '别的我方号同期打这个外人', '末条后 600 拍内阵亡', '末条后 100 拍领土不到开打时一半',
           '大登陆（>= 目标兵的一半且 >=2 万）：次 / 兵', '外人之间的捐款：笔 / 到账', '其中 pct>=900：笔 / 到账', '收得最多的外人'], rows)
    print('**每局对我方出兵最多的 3 个外人**')
    rows = []
    for d in ps:
        for t in d['top'][:3]:
            rows.append([d['matchId'], f"{t['name']}（队{t['team']}）", t['fate'], f"{t['peakTerr']:,}", ' / '.join(f"{x:,}" if x is not None else '—' for x in t['terr']), f"{t['n']} / {wan(t['troops'])}", ' '.join(f"{k}‰×{v}" for k, v in t['pctTop']),
                         f"{t['modePct']}‰ 占 {pc(t['modeShare'], 1, 0)}（{t['distinctPct']} 种）", t['adensMed'], t['tdensMed'], t['ratioMed'], f"{t['targets']} 个，主目标 {pc(t['mainShare'], 1, 0)}，同时 {t['atOnce']}",
                         t['boats'], f"{t['donIn']} 笔 / {wan(t['donInTroops'])}"])
    table(['局', '外人', '结局', '峰值领土', 't=630 / 1500 / 3000 领土', '对我方：条 / 兵', '对我方最常用的千分比', '整局陆攻最常用的千分比（种数）', '出手时自己密度中位', '目标密度中位', '兵力比中位', '打过几个我方号', '登陆我方', '收到捐款'], rows)
    o_n = sum(d['ours']['n'] for d in ps)
    o_t = sum(d['ours']['troops'] for d in ps)
    op = lambda k: sum(d['ours']['pct'][k]['troops'] for d in ps)
    print(f"   对照｜我方号对外人真人的陆攻（{len(ps)} 局）：{o_n:,} 条、{wan(o_t)}兵；千分比 <100 / 100~199 / 200~399 / 400~899 / >=900 的兵占比 = "
          f"{pc(op('<100'), o_t, 0)} / {pc(op('100~199'), o_t, 0)} / {pc(op('200~399'), o_t, 0)} / {pc(op('400~899'), o_t, 0)} / {pc(op('>=900'), o_t, 0)}；各局千分比中位 {' / '.join(str(d['ours']['pctMed']) for d in ps)}")
    print('   同一局里的打击互相关联（同一个外人连着打同一个号），合计占比只作描述。出手方密度按「出手前余额 ÷ 当拍领土」，连续出兵的人这个值会一路走低。')
    print()
    return [dict(id=d['matchId'], hits={k: v for k, v in d['hits'].items()}, sieges={k: v for k, v in d['sieges'].items() if k != 'rows'}, landings=d['landings'], foeDon=d['foeDon'], top=d['top'], ours=d['ours']) for d in ps] + [dict(id='ALL', hits=T, sieges=S)]


def sec_boats(ms):
    print('### 船账（录像真值，boatflow.py）：我方号发出的每条船，带多少兵、交多少手续费、最后靠在谁的岸上')
    print('   手续费 = 发船那一拍余额的 3.125%，与船上带多少兵无关。小船 = 船上的兵不到发船时余额的 5%；空船 = 千分比 0。被围 = 发船那一拍影子策略眼里 nb=0 且 neut=0。')
    bs = [m.B for m in ms if m.B.get('n')]
    if not bs:
        print('   （没有 boatflow.json）')
        print()
        return []
    DEST = ['自己的岸', '无主地', '内置AI', '敌方真人', '敌方真人（空壳）', '异队我方号的岸', '同队的岸（移交）', '无空槽白损', '沉没', '消失（主人阵亡等）', '终局还在海上']
    g = lambda d, k, f='n': (d.get(k) or {}).get(f, 0)
    rows = []
    for d in bs:
        rows.append([d['matchId'], f"{d['n']}（{d['bots']} 个号）", wan(d['sent']), f"{wan(d['fee'])}（{pc(d['fee'], d['sent'], 0)}；{pc(d['fee'], d['inc'])}）",
                     f"{g(d['size'], '<5%')} / {wan(g(d['size'], '<5%', 'sent'))} / {wan(g(d['size'], '<5%', 'fee'))}", f"{d['zero']['n']} / {wan(d['zero']['fee'])}",
                     f"{g(d['box'], '被围')} / {wan(g(d['box'], '被围', 'sent'))} / {wan(g(d['box'], '被围', 'fee'))}", f"{d['big']['n']} / {wan(d['big']['sent'])}", f"{wan(d['sea']['decay'])} / {wan(d['sea']['hit'])}",
                     f"{d['aim']['aimHumanLandedOnIt']}/{d['aim']['aimHuman']}"])
    T = lambda k: sum(d[k] for d in bs)
    S2 = lambda a, k, f='n': sum(g(d[a], k, f) for d in bs)
    rows.append(['合计', f"{T('n'):,}", wan(T('sent')), f"{wan(T('fee'))}（{pc(T('fee'), T('sent'), 0)}；{pc(T('fee'), T('inc'))}）", f"{S2('size', '<5%')} / {wan(S2('size', '<5%', 'sent'))} / {wan(S2('size', '<5%', 'fee'))}",
                 f"{sum(d['zero']['n'] for d in bs)} / {wan(sum(d['zero']['fee'] for d in bs))}", f"{S2('box', '被围')} / {wan(S2('box', '被围', 'sent'))} / {wan(S2('box', '被围', 'fee'))}",
                 f"{sum(d['big']['n'] for d in bs)} / {wan(sum(d['big']['sent'] for d in bs))}", f"{wan(sum(d['sea']['decay'] for d in bs))} / {wan(sum(d['sea']['hit'] for d in bs))}",
                 f"{sum(d['aim']['aimHumanLandedOnIt'] for d in bs)}/{sum(d['aim']['aimHuman'] for d in bs)}"])
    table(['局', '发船（条）', '船上兵', '手续费（÷船上兵；÷实得利息）', '小船（<5% 余额）：条 / 船上 / 手续费', '空船：条 / 手续费', '被围时发的：条 / 船上 / 手续费', '>=10 万兵的大船：条 / 兵', '海上自然损耗 / 被敌船打掉', '瞄准敌方真人的船靠上了那个人的岸'], rows)
    rows = []
    for d in bs:
        rows.append([d['matchId']] + [f"{g(d['dest'], k)} / {wan(g(d['dest'], k, 'sent'))}" if g(d['dest'], k) else '0' for k in DEST])
    rows.append(['合计'] + [f"{S2('dest', k)} / {wan(S2('dest', k, 'sent'))}（{pc(S2('dest', k), T('n'), 0)} / {pc(S2('dest', k, 'sent'), T('sent'), 0)}）" for k in DEST])
    table(['局（靠岸：条 / 船上兵）'] + DEST, rows)
    bigd = defaultdict(lambda: [0, 0])
    for d in bs:
        for k, v in d['big']['dest'].items():
            bigd[k][0] += v['n']
            bigd[k][1] += v['sent']
    print('   >=10 万兵的大船去了哪（合计）：' + '；'.join(f"{k} {v[0]} 条 / {wan(v[1])}" for k, v in sorted(bigd.items(), key=lambda kv: -kv[1][1])))
    tb = ['<600', '600~1500', '1500~3000', '3000~4284', '>=4284']
    print('   按发船拍（合计）：' + '；'.join(f"{k} {S2('tband', k)} 条 / 船上 {wan(S2('tband', k, 'sent'))} / 费 {wan(S2('tband', k, 'fee'))}" for k in tb))
    print('   按船上兵占余额（合计）：' + '；'.join(f"{k} {S2('size', k)} 条 / 船上 {wan(S2('size', k, 'sent'))} / 费 {wan(S2('size', k, 'fee'))}" for k in ('<5%', '5~20%', '20~50%', '>=50%')))
    print('   被围与否（合计）：' + '；'.join(f"{k} {S2('box', k)} 条 / 船上 {wan(S2('box', k, 'sent'))} / 费 {wan(S2('box', k, 'fee'))}" for k in ('被围', '不被围', '未知')))
    print('   船靠上异队我方号的岸，引擎按进攻结算；靠上同队的岸，兵直接归对方（不收捐款手续费，但发船手续费照收）。')
    print()
    return bs


def sec_money(ms):
    print('### 兵力账（录像真值：reviews/*.json 的 truthSummary；单位 兵）')
    keys = ['利息+地租', '顶格少拿', '出兵手续费', '捐款手续费', '捐出到账', '回兵溢出', '空壳少拿', '船兵交接蒸发', '海上损失', '其它白损', '战斗耗兵', '被打掉兵', '得地', '失地']
    rows, out = [], []
    for m in ms:
        ts = m.R.get('truthSummary') or {}
        lt = ts.get('ledgerTotals') or {}
        if not lt:
            continue
        s = {k: sum((v.get(k) or 0) for v in lt.values()) for k in keys}
        dn = ts.get('donationsExecuted') or {}
        o = dict(id=m.id, replay=m.replay, **s, don=dn)
        rows.append([m.id, m.replay, wan(s['利息+地租']), f"{wan(s['顶格少拿'])}（{pc(s['顶格少拿'], s['利息+地租'] + s['顶格少拿'], 0)}）", f"{wan(s['出兵手续费'])}（{pc(s['出兵手续费'], s['利息+地租'], 0)}）",
                     f"{dn.get('n', 0)} / {wan(dn.get('delivered'))} / {wan(dn.get('fee'))}（{pc(dn.get('fee', 0), (dn.get('fee', 0) + dn.get('delivered', 0)))}）" if dn.get('n') else '0',
                     f"{dn.get('toHuskN', 0)} / {wan(dn.get('toHuskDelivered'))}" if dn.get('toHuskN') else '0', f"{dn.get('smallPctN', 0)} / {wan(dn.get('smallPctFee'))}" if dn.get('smallPctN') else '0',
                     wan(s['回兵溢出']), wan(s['空壳少拿']), wan(s['船兵交接蒸发'] + s['海上损失']), wan(s['战斗耗兵']), wan(s['被打掉兵']), f"{s['得地']:,} / {s['失地']:,}"])
        out.append(o)
    table(['局', '录像', '利息+地租', '顶格少拿（占应得 = 少拿 ÷ (实得 + 少拿)）', '出兵手续费（÷实得利息）', '捐款：笔 / 到账 / 手续费（损耗率）', '给空壳：笔 / 到账', '小额 pct（<150‰）：笔 / 手续费', '回兵溢出', '空壳少拿', '船兵交接蒸发 + 海上损失', '战斗耗兵', '被打掉兵', '得地 / 失地（格）'], rows)
    if out:
        I = sum(o['利息+地租'] for o in out)
        fee_d = sum(o['don'].get('fee', 0) for o in out)
        del_d = sum(o['don'].get('delivered', 0) for o in out)
        print(f"   {len(out)} 局合计：利息+地租 {wan(I)}；顶格少拿 {wan(sum(o['顶格少拿'] for o in out))}（占应得 {pc(sum(o['顶格少拿'] for o in out), I + sum(o['顶格少拿'] for o in out))}）；出兵手续费 {wan(sum(o['出兵手续费'] for o in out))}（{pc(sum(o['出兵手续费'] for o in out), I)}）；"
              f"捐款 {sum(o['don'].get('n', 0) for o in out)} 笔、到账 {wan(del_d)}、手续费 {wan(fee_d)}（损耗率 {pc(fee_d, fee_d + del_d)}；÷利息 {pc(fee_d, I)}）；给空壳 {sum(o['don'].get('toHuskN', 0) for o in out)} 笔、到账 {wan(sum(o['don'].get('toHuskDelivered', 0) for o in out))}、手续费 {wan(sum(o['don'].get('toHuskFee', 0) for o in out))}；"
              f"小额 pct {sum(o['don'].get('smallPctN', 0) for o in out)} 笔、到账 {wan(sum(o['don'].get('smallPctDelivered', 0) for o in out))}、手续费 {wan(sum(o['don'].get('smallPctFee', 0) for o in out))}；回兵溢出 {wan(sum(o['回兵溢出'] for o in out))}；空壳少拿 {wan(sum(o['空壳少拿'] for o in out))}；"
              f"战斗耗兵 {wan(sum(o['战斗耗兵'] for o in out))}、被打掉兵 {wan(sum(o['被打掉兵'] for o in out))}；得地 {sum(o['得地'] for o in out):,} 格、失地 {sum(o['失地'] for o in out):,} 格")
    print()
    print('### 兵力账（日志侧估算，15 局同口径：logdigest.py overcap / donlog）')
    rows2, out2 = [], []
    for m in ms:
        ov = m.G.get('overcap') or []
        dl = m.G.get('donlog') or []
        ex = [x for x in dl if x.get('exec')]
        o = dict(id=m.id, overLost=sum(x.get('lost', 0) for x in ov), overGot=sum(x.get('got', 0) for x in ov), n100=sum(x.get('n100', 0) for x in ov), n125=sum(x.get('n125', 0) for x in ov), n149=sum(x.get('n149', 0) for x in ov),
                 snaps=sum(x.get('n', 0) for x in ov), donLines=len(dl), donExec=len(ex), donFee=sum(x.get('fee', 0) or 0 for x in ex), donSpend=sum(x.get('spend', 0) or 0 for x in ex),
                 kinds=dict(Counter(x.get('kind') for x in ex)))
        rows2.append([m.id, f"{o['snaps']:,}", f"{o['n100']:,}（{pc(o['n100'], o['snaps'])}）", f"{o['n125']:,}", f"{o['n149']:,}", f"{wan(o['overLost'])}（{pc(o['overLost'], o['overLost'] + o['overGot'])}）",
                      f"{o['donLines']} / {o['donExec']}", wan(o['donFee']), '、'.join(f"{k} {v}" for k, v in sorted(o['kinds'].items(), key=lambda kv: -kv[1]))])
        out2.append(o)
    table(['局', '快照数', '密度 >100 的快照', '>125', '>=149', '估算少拿的利息（占应得）', 'HL-DONATE 行 / 判为已执行', '已执行的手续费（估）', '已执行的捐款按日志类别'], rows2)
    print(f"   15 局合计：快照 {sum(o['snaps'] for o in out2):,} 条，密度 >100 的 {sum(o['n100'] for o in out2):,} 条（{pc(sum(o['n100'] for o in out2), sum(o['snaps'] for o in out2))}）、>125 的 {sum(o['n125'] for o in out2):,}、>=149 的 {sum(o['n149'] for o in out2):,}；"
          f"估算少拿利息 {wan(sum(o['overLost'] for o in out2))}（占应得 {pc(sum(o['overLost'] for o in out2), sum(o['overLost'] + o['overGot'] for o in out2))}）；HL-DONATE {sum(o['donLines'] for o in out2):,} 行、判为已执行 {sum(o['donExec'] for o in out2):,}、手续费（估）{wan(sum(o['donFee'] for o in out2))}")
    print()
    return dict(truth=out, log=out2)


def sec_logside(ms):
    print('### 只靠日志的计数（logdigest.py sentchk / zerodrop / dondying / silent / capidle / stale / gaps；15 局同口径）')
    rows, out = [], []
    for m in ms:
        G = m.G
        sc = G.get('sentchk') or []
        z = G.get('zerodrop') or []
        dd = G.get('dondying') or []
        si = G.get('silent') or []
        ci = G.get('capidle') or []
        st = G.get('stale') or []
        gp = G.get('gaps') or []
        o = dict(id=m.id, sent=sum((x.get('sent') or 0) for x in sc), accepted=sum((x.get('accepted') or 0) for x in sc), cmdsPlusSpawn=sum((x.get('cmds') or 0) + (x.get('spawnLines') or 0) for x in sc), sentBots=len(sc),
                 zerodrop=len(z), zerodropBots=len(set(x['me'] for x in z)), dondying=len(dd), dondyingFee=sum(x.get('fee', 0) or 0 for x in dd), silent=len(si), silentBots=len(set(x['me'] for x in si)),
                 silentTicks=sum(x.get('len', 0) for x in si), capidle=len(ci), capidleBots=len(set(x['me'] for x in ci)), stale=len(st), staleBots=len(set(x['me'] for x in st)),
                 gaps=sum(len(x.get('miss') or []) for x in gp), gapBots=sum(1 for x in gp if x.get('miss')), neverPlayed=len(m.ctx.get('neverPlayed') or []))
        rows.append([m.id, f"{o['sent']:,} / {o['accepted']:,} / {o['cmdsPlusSpawn']:,}", o['sent'] - o['accepted'], f"{o['zerodrop']} / {o['zerodropBots']}", f"{o['dondying']} / {wan(o['dondyingFee'])}",
                     f"{o['silent']} / {o['silentBots']} / {o['silentTicks']:,}", f"{o['capidle']} / {o['capidleBots']}", f"{o['stale']} / {o['staleBots']}", f"{o['gaps']} / {o['gapBots']}", o['neverPlayed']])
        out.append(o)
    table(['局', '结算行 sent / accepted / 日志 cmds+选点行', 'sent − accepted', '余额骤降且这一段零指令：段 / 号', '垮着还在捐：笔 / 手续费', '零指令 >=450 拍：段 / 号 / 合计拍', '满仓不动随后被吃：段 / 号', '发令不见效→集中清仓：段 / 号', '缺的快照：条 / 号', '没开局的席位'], rows)
    print(f"   15 局合计：sent {sum(o['sent'] for o in out):,}、accepted {sum(o['accepted'] for o in out):,}、sent − accepted {sum(o['sent'] - o['accepted'] for o in out):,}；骤降零指令 {sum(o['zerodrop'] for o in out)} 段（{sum(1 for o in out if o['zerodrop'])} 局）；"
          f"垮着还捐 {sum(o['dondying'] for o in out)} 笔、手续费 {wan(sum(o['dondyingFee'] for o in out))}（{sum(1 for o in out if o['dondying'])} 局）；零指令 >=450 拍 {sum(o['silent'] for o in out)} 段、{sum(o['silentTicks'] for o in out):,} 个号·拍（{sum(1 for o in out if o['silent'])} 局）；"
          f"满仓不动随后被吃 {sum(o['capidle'] for o in out)} 段（{sum(1 for o in out if o['capidle'])} 局）；发令不见效→清仓 {sum(o['stale'] for o in out)} 段（{sum(1 for o in out if o['stale'])} 局）；缺快照 {sum(o['gaps'] for o in out)} 条；没开局的席位 {sum(o['neverPlayed'] for o in out)} 个（{sum(1 for o in out if o['neverPlayed'])} 局）")
    print()
    return out


def sec_patterns(ms):
    print('### 15 局 JSON 里的模式名（reviews/*.json 的 newPatterns；同名 = 同一条定义）')
    by = defaultdict(lambda: dict(matches=[], instances=0, definition=''))
    for m in ms:
        for p in m.R.get('newPatterns') or []:
            nm = p.get('name', '').replace('NEW:', '')
            b = by[nm]
            b['matches'].append(m.id)
            b['instances'] += len(p.get('instances') or [])
            if not b['definition']:
                b['definition'] = p.get('definition', '')
    rows = sorted(by.items(), key=lambda kv: (-len(kv[1]['matches']), kv[0]))
    table(['模式', '局数', '实例数', '哪些局', '定义（第一次写下时的原文，截 90 字）'],
          [[k, len(v['matches']), v['instances'], ' '.join(x[1:] for x in v['matches']), v['definition'][:90].replace('|', '/').replace('\n', ' ')] for k, v in rows if len(v['matches']) >= 3])
    pre = Counter(k.split('-')[0] for k, v in rows)
    print(f"   不同的模式名 {len(rows)} 个：出现在 >=3 局的 {sum(1 for k, v in rows if len(v['matches']) >= 3)} 个、2 局的 {sum(1 for k, v in rows if len(v['matches']) == 2)} 个、只在 1 局的 {sum(1 for k, v in rows if len(v['matches']) == 1)} 个。"
          '按前缀：' + '、'.join(f"{k} {v}" for k, v in pre.most_common()))
    print()
    return [dict(name=k, matches=v['matches'], instances=v['instances'], definition=v['definition']) for k, v in rows]


def sec_decisions(ms):
    print('### 决策审计（reviews/*.json 的 decisions）')
    kv = Counter()
    fn = defaultdict(lambda: dict(n=0, matches=set(), pat=Counter()))
    pat = defaultdict(lambda: dict(n=0, matches=set(), verdicts=Counter()))
    tot = Counter()
    for m in ms:
        for d in m.R.get('decisions') or []:
            kv[(d.get('kind'), d.get('verdict'))] += 1
            tot[d.get('verdict')] += 1
            pid = (d.get('patternId') or '').replace('NEW:', '')
            if pid:
                pat[pid]['n'] += 1
                pat[pid]['matches'].add(m.id)
                pat[pid]['verdicts'][d.get('verdict')] += 1
            if d.get('verdict') == 'error':
                cp = d.get('codePath') or ''
                for f in FUNCS:
                    if f in cp:
                        fn[f]['n'] += 1
                        fn[f]['matches'].add(m.id)
                        if pid:
                            fn[f]['pat'][pid] += 1
    kinds = sorted(set(k for k, _ in kv), key=lambda k: -sum(v for (kk, _), v in kv.items() if kk == k))
    table(['种类', '错', '对', '不确定', '合计'], [[k, kv.get((k, 'error'), 0), kv.get((k, 'good'), 0), kv.get((k, 'unclear'), 0), sum(v for (kk, _), v in kv.items() if kk == k)] for k in kinds]
          + [['合计', tot.get('error', 0), tot.get('good', 0), tot.get('unclear', 0), sum(tot.values())]])
    print('判为「错」的决策，代码位置（codePath 字段）里点到的函数（一条决策可以点到多个函数）：')
    table(['函数', '判错的决策数', '局数', '哪些局', '这些决策挂的模式（前 4 个）'],
          [[f, v['n'], len(v['matches']), ' '.join(x[1:] for x in sorted(v['matches'])), '、'.join(f"{k}×{c}" for k, c in v['pat'].most_common(4))] for f, v in sorted(fn.items(), key=lambda kv: (-len(kv[1]['matches']), -kv[1]['n']))])
    print('决策挂的模式（patternId），出现在 >=3 局的：')
    table(['模式', '决策数', '局数', '错 / 对 / 不确定', '哪些局'],
          [[k, v['n'], len(v['matches']), f"{v['verdicts'].get('error', 0)} / {v['verdicts'].get('good', 0)} / {v['verdicts'].get('unclear', 0)}", ' '.join(x[1:] for x in sorted(v['matches']))]
           for k, v in sorted(pat.items(), key=lambda kv: (-len(kv[1]['matches']), -kv[1]['n'])) if len(v['matches']) >= 3])
    return dict(kinds={f"{k}|{v}": c for (k, v), c in kv.items()}, funcs={f: dict(n=v['n'], matches=sorted(v['matches'])) for f, v in fn.items()},
                patterns={k: dict(n=v['n'], matches=sorted(v['matches']), verdicts=dict(v['verdicts'])) for k, v in pat.items()})


def sec_deaths(ms):
    print('### 阵亡（reviews/*.json 的 deaths；死前 900 拍的地被谁拿走只有有录像的局有）')
    edges = [0, 1500, 3000, 4284, 10 ** 9]
    names = ['<1500', '1500~3000', '3000~4284', '>=4284']
    rows, out = [], []
    cls_all, top_all = Counter(), Counter()
    pat = defaultdict(lambda: dict(n=0, matches=set()))
    for m in ms:
        ds = m.R.get('deaths') or []
        bd = [0, 0, 0, 0]
        cls, top = Counter(), Counter()
        rich, bal, dens = 0, 0, []
        for d in ds:
            t = d.get('t') if d.get('t') is not None else d.get('tLog')
            if t is not None:
                for i in range(4):
                    if edges[i] <= t < edges[i + 1]:
                        bd[i] += 1
            tk = (d.get('truth') or {}).get('landTakenLast900') or []
            for x in tk:
                cls[x.get('cls')] += x.get('cells', 0)
            if tk:
                top[max(tk, key=lambda x: x.get('cells', 0)).get('cls')] += 1
            b, l = d.get('balanceBeforeClear'), d.get('landBeforeClear')
            if b is not None and l:
                bal += b
                dens.append(b / l)
                if b / l >= 100:
                    rich += 1
            for p in d.get('patternIds') or []:
                p = p.replace('NEW:', '')
                pat[p]['n'] += 1
                pat[p]['matches'].add(m.id)
        cls_all.update(cls)
        top_all.update(top)
        o = dict(id=m.id, deaths=len(ds), bands=bd, takenBy=dict(cls), topTaker=dict(top), balBeforeClear=bal, richDeaths=rich, densBeforeClear=dens)
        rows.append([m.id, len(ds), ' / '.join(str(x) for x in bd), '、'.join(f"{k} {v:,}" for k, v in cls.most_common()) or None, '、'.join(f"{k} {v}" for k, v in top.most_common()) or None,
                     wan(bal) if dens else None, f"{med(dens):.0f}" if dens else None, rich if dens else None])
        out.append(o)
    table(['局', '阵亡条数', '按时段：' + ' / '.join(names), '死前 900 拍的地被谁拿走（格）', '拿走最多的是谁（按阵亡号计）', '清地前一拍手里的兵（合计）', '清地前密度中位', '清地前密度 >=100 的号'], rows)
    tot = [sum(o['bands'][i] for o in out) for i in range(4)]
    print(f"   15 局合计阵亡条目 {sum(o['deaths'] for o in out)}：" + '、'.join(f"{names[i]} {tot[i]}" for i in range(4)) + '。'
          '有录像的局：死前 900 拍被拿走的地 ' + '、'.join(f"{k} {v:,} 格（{pc(v, sum(cls_all.values()))}）" for k, v in cls_all.most_common())
          + '；拿走最多的一方：' + '、'.join(f"{k} {v} 个号" for k, v in top_all.most_common())
          + f"；清地前一拍手里还有的兵合计 {wan(sum(o['balBeforeClear'] for o in out))}，密度 >=100 的 {sum(o['richDeaths'] for o in out)} 个号（共 {sum(len(o['densBeforeClear']) for o in out)} 个有读数）")
    print('阵亡条目上挂的模式，出现在 >=3 局的：')
    table(['模式', '阵亡号数', '局数', '哪些局'], [[k, v['n'], len(v['matches']), ' '.join(x[1:] for x in sorted(v['matches']))] for k, v in sorted(pat.items(), key=lambda kv: (-len(kv[1]['matches']), -kv[1]['n'])) if len(v['matches']) >= 3])
    return dict(matches=out, patterns={k: dict(n=v['n'], matches=sorted(v['matches'])) for k, v in pat.items()})


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 4:
        return None, len(pairs)
    rx, ry = rank([a for a, _ in pairs]), rank([b for _, b in pairs])
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return (num / den if den else None), len(pairs)


def sec_relate(ms):
    print('### 并排看：延迟、站位、闸、实抢（有对局录像的局；每局一行，全部取自上面各段）')
    rows, out = [], []
    for m in ms:
        if not m.full or 'capture' not in m.C:
            continue
        d = {x['band']: x for x in m.L['delay']}
        v = m.C['voronoi']
        cap = m.C['capture']
        c1 = cap[1] if len(cap) > 1 else cap[0]
        g = m.C['layers']['gates']
        f = m.C['flow']
        ex = {x['band']: x for x in m.L['void'] if 'cls' not in x}.get('600~1500') or {}
        du = {(x['band'], x['kind']): x for x in m.L['dups']}.get(('600~1500', 'atk')) or {}
        fb = {b['band']: b for b in m.L['funnel']['bands']}.get('600~1500') or {}
        pr = played_rates(m.C)
        ns = len(f['rows'])
        a_s, a_o = f['squad']['g_ai'] / max(1, ns), f['other']['fromAi'] / max(1, f['other']['n'])
        o = dict(id=m.id, humans=v['humans'], seats=v['squad'], lagP50=d['600~1500']['p50'], lagP90=d['600~1500']['p90'], natRatio=v['squadVor'] / v['reach'] / (v['squad'] / v['humans']),
                 ok=g['ok'] / g['n'], sfSquad=g['safeFiniteSquad'] / g['n'], capT=c1['t'], capRatio=c1['squadRate'] / c1['otherRate'] if c1['otherRate'] else None,
                 capMedRatio=c1['squadMedRate'] / c1['otherMedRate'] if c1['otherMedRate'] else None, capPlayed=(pr['r1'] / c1['otherRate'] if pr and pr['r1'] and c1['otherRate'] else None),
                 aiRatio=a_s / a_o if a_o else None, voidPct=ex.get('void', 0) / ex['atk'] if ex.get('atk') else None, dupPct=du.get('dups', 0) / du['base'] if du.get('base') else None,
                 landedPct=fb.get('landed', 0) / fb['shadow'] if fb.get('shadow') else None, squadLandShare=m.oc.get('peakSquadLandShare'))
        rows.append([m.id, f"{o['seats']}/{o['humans']}", f"{o['lagP50']} / {o['lagP90']}", f"{o['natRatio']:.2f}", f"{100 * o['ok']:.0f}%", f"{100 * o['sfSquad']:.0f}%", f"{100 * o['landedPct']:.0f}%" if o['landedPct'] is not None else None,
                     f"{100 * o['voidPct']:.0f}%" if o['voidPct'] is not None else None, f"{100 * o['dupPct']:.0f}%" if o['dupPct'] is not None else None,
                     f"t={o['capT']}：{o['capRatio']:.2f}（{o['capMedRatio']:.2f}）", f"{o['capPlayed']:.2f}" if o['capPlayed'] else None, f"{o['aiRatio']:.2f}"])
        out.append(o)
    out_sorted = sorted(zip(out, rows), key=lambda t: t[0]['lagP50'])
    table(['局（按延迟排）', '席位 / 真人', '600~1500 延迟 P50 / P90', '天然份额 ÷ 人头', '② 可出兵', '② safeFinite 参照我方', '影子下令进录像的比例', '陆攻没生效', '陆攻重复下单', '实抢率之比：我方 ÷ 其他真人（单号中位之比）', '同左，去掉没扩张的号', '人均从 AI 拿到：我方 ÷ 其他真人'],
          [r for _, r in out_sorted])
    lag = [o['lagP50'] for o in out]
    print('   与「600~1500 延迟 P50」的 Spearman 秩相关（n 很小，只当描述；不是因果）：')
    for k, nm in (('voidPct', '陆攻没生效比例'), ('dupPct', '陆攻重复下单比例'), ('landedPct', '影子下令进录像的比例'), ('capRatio', '实抢率之比（合计）'), ('capMedRatio', '实抢率之比（单号中位）'), ('capPlayed', '实抢率之比（去掉没扩张的号）'),
                  ('aiRatio', '人均从 AI 拿到之比'), ('natRatio', '天然份额 ÷ 人头'), ('sfSquad', 'safeFinite 参照我方的比例'), ('humans', '全场真人数')):
        rho, n = spearman(lag, [o[k] for o in out])
        print(f"      {nm}：ρ = {rho:+.2f}（n={n}）" if rho is not None else f"      {nm}：样本不够")
    for k, nm in (('natRatio', '天然份额 ÷ 人头'), ('sfSquad', 'safeFinite 参照我方的比例'), ('ok', '可出兵比例')):
        rho, n = spearman([o[k] for o in out], [o['capMedRatio'] for o in out])
        print(f"   「{nm}」与「实抢率之比（单号中位）」：ρ = {rho:+.2f}（n={n}）" if rho is not None else '')
    print()
    return out


def sign_p(a, b):
    n = a + b
    if not n:
        return None
    k = min(a, b)
    from math import comb
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def pfmt(p):
    return 'p 算不了' if p is None else ('p<0.001' if p < 0.001 else f"p={p:.3f}")


def sec_spawnfx(ms):
    print('### 单号口径：天然份额（陆路 Voronoi，按真实出生点）→ t≈1500 的领土 / 早亡（landcap.json 的 voronoi.bots + flow.rows 或 logCapture.bots；reviews 的 deaths）')
    print('   挤 = 天然份额不到全场人均（可达陆地 ÷ 真人数）的一半。t≈1500 的领土：有对局网格的局取录像 t=1500（不够长的取末拍），只有选点录像的局取日志 t=1530 的快照（没有快照的号不计）。')
    rows, out = [], []
    for m in ms:
        v = m.C.get('voronoi')
        if not v:
            continue
        par = v['reach'] / v['humans']
        land, tcut = {}, None
        if m.C.get('flow'):
            tcut = m.C['flow']['t1']
            land = {r['me']: r['t1'] for r in m.C['flow']['rows']}
        elif m.C.get('logCapture'):
            tcut = 1530
            land = {b['me']: b.get('t1530') for b in m.C['logCapture'].get('bots', [])}
        died = {d['me']: d['t'] for d in m.R.get('deaths', []) if d.get('me') is not None and d.get('t') is not None}
        bots = []
        for b in v['bots']:
            bots.append(dict(me=b['me'], vor=b['vor'], rel=b['vor'] / par, small=b['vor'] < par / 2, kind=b['nearestKind'], near=b['nearest'], own=b['nearestKind'].startswith('我方'),
                             land=land.get(b['me']), early=(died.get(b['me'], 10 ** 9) < 3000)))
        have = [b for b in bots if b['land'] is not None]
        rho, n = spearman([b['vor'] for b in have], [b['land'] for b in have])
        sm, bg = [b for b in have if b['small']], [b for b in have if not b['small']]
        ow, ot = [b for b in bots if b['own']], [b for b in bots if not b['own']]
        o = dict(id=m.id, t=tcut, n=len(bots), have=len(have), rho=rho, small=len([b for b in bots if b['small']]), smallLand=med([b['land'] for b in sm]), bigLand=med([b['land'] for b in bg]),
                 smallEarly=sum(1 for b in bots if b['small'] and b['early']), bigEarly=sum(1 for b in bots if not b['small'] and b['early']), big=len([b for b in bots if not b['small']]),
                 own=len(ow), ownRel=med([b['rel'] for b in ow]), otherRel=med([b['rel'] for b in ot]), ownLand=med([b['land'] for b in ow if b['land'] is not None]), otherLand=med([b['land'] for b in ot if b['land'] is not None]),
                 ownDiffTeam=sum(1 for b in ow if b['kind'] == '我方异队'), ownNear=med([b['near'] for b in ow]), otherNear=med([b['near'] for b in ot]), bots=bots)
        f = lambda x: f"{x:,.0f}" if x is not None else '—'
        rows.append([m.id, f"t={tcut}", f"{len(have)}/{len(bots)}", f"{rho:+.2f}" if rho is not None else None, f"{o['small']}：{f(o['smallLand'])}", f"{o['big']}：{f(o['bigLand'])}",
                     f"{o['smallEarly']}/{o['small']}", f"{o['bigEarly']}/{o['big']}", f"{o['own']}（异队 {o['ownDiffTeam']}）", f"{o['ownRel']:.2f} / {o['otherRel']:.2f}" if o['ownRel'] is not None and o['otherRel'] is not None else None,
                     f"{f(o['ownLand'])} / {f(o['otherLand'])}"])
        out.append(o)
    table(['局', '领土断面', '有读数的号', '天然份额 与 断面领土 的秩相关', '挤的号：个数：断面领土中位', '不挤的号：个数：中位', '挤的号 t<3000 阵亡', '不挤的号 t<3000 阵亡',
           '出生时最近的玩家是我方号的', '天然份额 ÷ 全场人均（中位）：最近是我方号 / 最近是别人', '断面领土中位：最近是我方号 / 最近是别人'], rows)
    pos = sum(1 for o in out if o['rho'] is not None and round(o['rho'], 2) > 0)
    neg = sum(1 for o in out if o['rho'] is not None and round(o['rho'], 2) < 0)
    zero = sum(1 for o in out if o['rho'] is not None and round(o['rho'], 2) == 0)
    lo = sum(1 for o in out if o['smallLand'] is not None and o['bigLand'] is not None and o['smallLand'] < o['bigLand'])
    hi = sum(1 for o in out if o['smallLand'] is not None and o['bigLand'] is not None and o['smallLand'] > o['bigLand'])
    allb = [b for o in out for b in o['bots']]
    sm, bg = [b for b in allb if b['small']], [b for b in allb if not b['small']]
    ow, ot = [b for b in allb if b['own']], [b for b in allb if not b['own']]
    e_hi = sum(1 for o in out if o['small'] and o['big'] and o['smallEarly'] / o['small'] > o['bigEarly'] / o['big'])
    e_lo = sum(1 for o in out if o['small'] and o['big'] and o['smallEarly'] / o['small'] < o['bigEarly'] / o['big'])
    r_lo = sum(1 for o in out if o['ownRel'] is not None and o['otherRel'] is not None and o['ownRel'] < o['otherRel'])
    r_hi = sum(1 for o in out if o['ownRel'] is not None and o['otherRel'] is not None and o['ownRel'] > o['otherRel'])
    l_lo = sum(1 for o in out if o['ownLand'] is not None and o['otherLand'] is not None and o['ownLand'] < o['otherLand'])
    l_hi = sum(1 for o in out if o['ownLand'] is not None and o['otherLand'] is not None and o['ownLand'] > o['otherLand'])
    print(f"   {len(out)} 局、{len(allb)} 个席位。局内秩相关为正的 {pos} 局、为负的 {neg} 局、为零的 {zero} 局（符号检验双侧 {pfmt(sign_p(pos, neg))}）；各局 ρ 的中位 {med([o['rho'] for o in out if o['rho'] is not None]):+.2f}。")
    print(f"   挤的号 {len(sm)} 个、不挤的 {len(bg)} 个：断面领土中位 挤的低于不挤的 {lo} 局、高于 {hi} 局（{pfmt(sign_p(lo, hi))}）；"
          f"t<3000 阵亡 挤的 {sum(1 for b in sm if b['early'])}/{len(sm)}（{pc(sum(1 for b in sm if b['early']), len(sm))}）对 不挤的 {sum(1 for b in bg if b['early'])}/{len(bg)}（{pc(sum(1 for b in bg if b['early']), len(bg))}），"
          f"按局 挤的比例更高 {e_hi} 局、更低 {e_lo} 局（{pfmt(sign_p(e_hi, e_lo))}）。")
    kc = Counter(b['kind'] for b in allb)
    print(f"   出生时最近的玩家：" + '、'.join(f"{k} {n}" for k, n in kc.most_common()) + f"；最近是我方号的 {len(ow)} 个（{pc(len(ow), len(allb))}），距离中位 {med([b['near'] for b in ow]):.0f} 格，最近是别人的距离中位 {med([b['near'] for b in ot]):.0f} 格。")
    print(f"   天然份额 ÷ 全场人均：最近是我方号的中位 {med([b['rel'] for b in ow]):.2f}、最近是别人的 {med([b['rel'] for b in ot]):.2f}；按局前者更低 {r_lo} 局、更高 {r_hi} 局（{pfmt(sign_p(r_lo, r_hi))}）。"
          f"断面领土中位：按局前者更低 {l_lo} 局、更高 {l_hi} 局（{pfmt(sign_p(l_lo, l_hi))}）。")
    print('   同一局的号互相关联，合计的比例只作描述；推断看按局的符号检验。早亡与站位的关系没有扣掉「分在哪个队、挨着谁」。')
    print()
    for o in out:
        o.pop('bots')
    return out


SECS = dict(relate=sec_relate, struct=sec_struct, split=sec_split, spawn=sec_spawn, delay=sec_delay, course=sec_course, funnel=sec_funnel, void=sec_void, dups=sec_dups, land=sec_land, ai=sec_ai, layers=sec_layers,
            gates=sec_gates, donflow=sec_donflow, foes=sec_foes, boats=sec_boats, money=sec_money, logside=sec_logside, patterns=sec_patterns, decisions=sec_decisions, deaths=sec_deaths, spawnfx=sec_spawnfx)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    sec = sys.argv[1]
    ids = sys.argv[2:] or IDS
    ms = [M(i) for i in ids]
    if sec in SECS:
        SECS[sec](ms)
        return 0
    if sec in ('all', 'json'):
        doc = dict(ids=ids)
        for k, f in SECS.items():
            doc[k] = f(ms)
        if sec == 'json':
            os.makedirs(os.path.join(OUT, '_cross'), exist_ok=True)
            p = os.path.join(OUT, '_cross', 'crossmatch.json')
            json.dump(doc, open(p, 'w'), ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
            print('写入', p)
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
