#!/usr/bin/env python3
"""build_review.py — 由手写的 analysis/<matchId>.json 生成 reviews/<matchId>.json 与 reviews/<matchId>.md。
用法: python3 build_review.py <matchId> [...]
analysis 文件就是复盘 JSON 本体（字段同 reviews/*.json），另外允许:
  timelineSpec: [{t, note}]   时间线只写拍和备注，数字由本脚本从整局重演表 (out/<id>/resim_players.csv, resim_teams.csv) 填:
                              alive(未离场存活)、husk(离场壳)、dead、sqTerr、sqSharePct、sqBal、sqDens、teamSharePct{队:占比}
  summary: [..]               md 第 0 节的结论句
  reconcile: [..]             md 第 5 节的兵力对账句
  repro: [..]                 md 第 10 节的复现命令
  timelineSpecB: [{t, note}] + timelineBTitle   包里还有第二个实例且它有录像时：按 timelineSpec 的办法另填一张表（存为 timelineB）
  timelineLog: {bots, points:[{t, note, teamSharePct?}]}  这批号所在实例没有录像时用：数字取自日志 [HL-TICK]（log_only.py 写的 log_ticks.csv）
这样时间线上的数字不经手抄。
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
VERD = {'error': '错', 'good': '对', 'unclear': '不清'}


def load_csv(mid, name):
    p = os.path.join(ROOT, 'out', mid, name)
    if not os.path.exists(p):
        return []
    with open(p, newline='') as f:
        return list(csv.DictReader(f))


def fill_timeline(mid, spec):
    meta = json.load(open(os.path.join(ROOT, 'out', mid, 'resim_meta.json')))
    prefix = spec and spec[0].get('_prefix') or ''
    sq = {p for b, p in meta['squad'].items() if (b.startswith(prefix) if prefix else ':' not in b)}
    land = meta['land']
    players = load_csv(mid, 'resim_players.csv'); teams = load_csv(mid, 'resim_teams.csv')
    ticks = sorted({int(r['t']) for r in teams})
    pb = defaultdict(list); tb = defaultdict(dict)
    for r in players:
        if int(r['p']) in sq:
            pb[int(r['t'])].append(r)
    for r in teams:
        tb[int(r['t'])][r['team']] = float(r['sharePct'])
    out = []
    for s in spec:
        t = min(ticks, key=lambda x: abs(x - s['t']))
        rows = pb[t]
        alive = [r for r in rows if r['alive'] == '1' and r['state'] != '2']
        husk = [r for r in rows if r['alive'] == '1' and r['state'] == '2']
        terr = sum(int(r['terr']) for r in alive); bal = sum(int(r['bal']) for r in alive)
        out.append({'t': t, 'alive': len(alive), 'husk': len(husk), 'dead': len(rows) - len(alive) - len(husk), 'sqTerr': terr,
                    'sqSharePct': round(100 * terr / land, 2), 'sqBal': bal, 'sqDens': round(bal / terr, 1) if terr else 0,
                    'teamSharePct': {('T' + k): v for k, v in sorted(tb[t].items())}, 'note': s.get('note', '')})
    return out


def fill_timeline_log(mid, spec):
    """没有录像的实例：时间线数字取自日志的 [HL-TICK] 行（先跑 log_only.py 写出 out/<id>/log_ticks.csv）。
    spec = {bots: [...], points: [{t, note, teamSharePct?}]}。alive = 该拍有快照的号数；dead 列 = 名单里日志已经停了的号数（离场和阵亡分不开，见备注）。"""
    bots = set(spec['bots'])
    land = json.load(open(f'/agent/repos/c136-data/bundles/{mid}/card.json'))['mapLand']
    by = defaultdict(list); last = {}
    for r in load_csv(mid, 'log_ticks.csv'):
        if r['bot'] in bots:
            by[int(r['t'])].append(r); last[r['bot']] = max(last.get(r['bot'], 0), int(r['t']))
    ticks = sorted(by)
    out = []
    for s in spec['points']:
        t = min(ticks, key=lambda x: abs(x - s['t']))
        rows = by[t]
        terr = sum(int(r['terr']) for r in rows); bal = sum(int(r['bal']) for r in rows)
        out.append({'t': t, 'alive': len(rows), 'husk': 0, 'dead': sum(1 for b in bots if last.get(b, 0) < t), 'sqTerr': terr,
                    'sqSharePct': round(100 * terr / land, 2), 'sqBal': bal, 'sqDens': round(bal / terr, 1) if terr else 0,
                    'teamSharePct': s.get('teamSharePct', ''), 'note': s.get('note', '')})
    return out


def md_escape(s):
    return str(s).replace('|', '\\|').replace('\n', ' ')


def render_md(r):
    L = []
    c = r['context']; o = r['outcome']
    L.append(f"# {r['matchId']} 逐局复盘（{r['reviewer']}）")
    L.append('')
    L.append(f"{c.get('cohort','')}，地图 {c.get('map','')}，{c.get('teams','')} 队，人类席位 {c.get('seededHumans','')}，本队 {c.get('ourTeam','')}；结果 `{o['result']}`，endTick={o['endTick']}，归类 `{r['lossArchetype']}`。{c.get('versionNote','')}")
    L.append('')
    L.append('## 0. 结论'); L.append('')
    for i, s in enumerate(r.get('summary', []), 1):
        L.append(f"{i}. {s}")
    L.append('')
    L.append('## 1. 时间线'); L.append('')
    L.append('| t | 存活/壳/死 | 领土 | 占比% | 兵力 | 密度 | 各队占比% | 备注 |')
    L.append('| --: | :-- | --: | --: | --: | --: | :-- | :-- |')
    for p in r['timeline']:
        ts = p.get('teamSharePct')
        tss = ' '.join(f"{k}:{v}" for k, v in ts.items()) if isinstance(ts, dict) else (str(ts) if ts is not None else '')
        ahd = f"{p.get('alive','')}/{p.get('husk','-')}/{p.get('dead','-')}"
        L.append(f"| {p['t']} | {ahd} | {p.get('sqTerr','')} | {p.get('sqSharePct','')} | {p.get('sqBal','')} | {p.get('sqDens','')} | {tss} | {md_escape(p.get('note',''))} |")
    if r.get('timelineB'):
        L.append('')
        L.append(r.get('timelineBTitle', '另一实例') + '：')
        L.append('')
        L.append('| t | 存活/壳/死 | 领土 | 占比% | 兵力 | 密度 | 各队占比% | 备注 |')
        L.append('| --: | :-- | --: | --: | --: | --: | :-- | :-- |')
        for p in r['timelineB']:
            ts = p.get('teamSharePct')
            tss = ' '.join(f"{k}:{v}" for k, v in ts.items()) if isinstance(ts, dict) else str(ts or '')
            L.append(f"| {p['t']} | {p.get('alive','')}/{p.get('husk','-')}/{p.get('dead','-')} | {p.get('sqTerr','')} | {p.get('sqSharePct','')} | {p.get('sqBal','')} | {p.get('sqDens','')} | {tss} | {md_escape(p.get('note',''))} |")
    L.append('')
    L.append('## 2. 四阶段'); L.append('')
    for ph in r['phases']:
        L.append(f"**{ph['name']}（{ph['t0']}–{ph['t1']}）** " + ' '.join(ph.get('facts', [])))
        if ph.get('problems'):
            L.append('问题：' + ' '.join(ph['problems']))
        L.append('')
    L.append('## 3. 转折点'); L.append('')
    for i, tp in enumerate(r['turningPoints'], 1):
        L.append(f"**TP{i}（{tp['t0']}–{tp['t1']}，{tp.get('shareBefore','')}%→{tp.get('shareAfter','')}%，{tp['statementType']}）** {tp['what']}")
        L.append('证据：' + '；'.join(tp['evidence']))
        L.append('此前决策：' + '；'.join(f"t={d['t']} {d['bot']}：{d['what']}（`{d['codePath']}`）" for d in tp['priorDecisions']))
        L.append('')
    L.append('## 4. 阵亡链'); L.append('')
    L.append('| 号 | 事件 | t | 原因 | 类型 |')
    L.append('| :-- | :-- | --: | :-- | :-- |')
    for d in r['deaths']:
        L.append(f"| `{d['bot']}` | {d.get('event','')} | {d.get('t','')} | {md_escape(d['cause'])} | {d.get('statementType','')} |")
    L.append('')
    L.append('## 5. 兵力对账'); L.append('')
    for s in r.get('reconcile', []):
        L.append(f"- {s}")
    L.append('')
    L.append('## 6. 决策审计'); L.append('')
    L.append('| # | t | 号 | 决策 | 代码路径与分支 | 判定 | 模式 |')
    L.append('| :-- | --: | :-- | :-- | :-- | :-- | :-- |')
    for d in r['decisions']:
        L.append(f"| {d['id']} | {d['t']} | {md_escape(d['bot'])} | {md_escape(d['what'])} | `{md_escape(d['codePath'])}`：{md_escape(d.get('branch',''))} | {VERD[d['verdict']]} | {d['patternId'].replace('NEW-R01-','')} |")
    L.append('')
    for d in r['decisions']:
        if d.get('mdNote'):
            L.append(f"{d['id']} 证据：{d['evidence']}")
    L.append('')
    L.append('## 7. 赢家与对手'); L.append('')
    L.append(r['winnerNotes'])
    if r.get('wentWell'):
        L.append(''); L.append('做对的：' + '；'.join(r['wentWell']))
    L.append('')
    L.append('## 8. 机制问题'); L.append('')
    for s in r.get('mechanicsQuestions', []):
        L.append(f"- {s}")
    L.append('')
    L.append('## 9. 没弄清的'); L.append('')
    for s in r.get('unknowns', []):
        L.append(f"- {s}")
    L.append('')
    L.append('## 10. 复现'); L.append('')
    L.append('```')
    for s in r.get('repro', []):
        L.append(s)
    L.append('```')
    return '\n'.join(L) + '\n'


def main():
    for mid in sys.argv[1:]:
        src = os.path.join(ROOT, 'analysis', mid + '.json')
        r = json.load(open(src))
        if 'timelineSpec' in r:
            r['timeline'] = fill_timeline(mid, r.pop('timelineSpec'))
        if 'timelineLog' in r:
            r['timeline'] = fill_timeline_log(mid, r.pop('timelineLog'))
        if 'timelineSpecB' in r:
            r['timelineB'] = fill_timeline(mid, r.pop('timelineSpecB'))
        json.dump(r, open(os.path.join(ROOT, 'reviews', mid + '.json'), 'w'), ensure_ascii=False, indent=1)
        md = render_md(r)
        open(os.path.join(ROOT, 'reviews', mid + '.md'), 'w').write(md)
        print(f"{mid}: timeline={len(r['timeline'])} decisions={len(r['decisions'])} md_lines={md.count(chr(10))}")


if __name__ == '__main__':
    main()
