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
def _flat(x):
    if isinstance(x, (list, tuple)):
        return [z for y in x for z in _flat(y)]
    return [str(x)]


def normalize(doc):
    """各局 decisions[] 的字段类型统一：bots 一律是字符串（多个号用顿号隔开），evidence 一律是字符串列表。"""
    for d in doc.get('decisions') or []:
        if isinstance(d.get('bots'), (list, tuple)):
            d['bots'] = '、'.join(_flat(d['bots']))
        if isinstance(d.get('evidence'), str):
            d['evidence'] = [d['evidence']]
    return doc


def dump(mid, doc):
    normalize(doc)
    json.dump(doc, open(f'{ROOT}/agents/R05/reviews/{mid}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写入', f'{ROOT}/agents/R05/reviews/{mid}.json', len(json.dumps(doc, ensure_ascii=False)), '字符')


def _rd(o):
    """把账本里的浮点数收一下：≥100 的取整，其余留 4 位。"""
    if isinstance(o, float):
        return int(round(o)) if abs(o) >= 100 else round(o, 4)
    if isinstance(o, dict):
        return {k: _rd(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_rd(v) for v in o]
    return o


def accounts(mid, work='/tmp/c136-r05/work'):
    """广播 0007 的三本账（延迟硬账 / 好地账 / 600–1500 决策拍三层归因），从脚本输出的 JSON 原样裁剪进复盘 JSON。
    生成：delay_account.py <局> --json <work>/<局>-delay.json；land_account.mjs <局> --json <work>/<局>-land.json；
          shadow.mjs <局> --quiet --tc 600:1500 --json <work>/<局>-shadow.json → tick_attrib.py <局> --json <work>/<局>-attrib.json"""
    import os
    out = {}
    p = f'{work}/{mid}-delay.json'
    if os.path.exists(p):
        D = json.load(open(p))
        sp = D.get('spawn') or {}
        out['delayAccount'] = _rd({
            'source': f'scripts/delay_account.py {mid}（口径见脚本头；延迟 = 录像里的执行拍 − 影子策略做出同一条决策的拍）',
            'spawnExecution': {k: sp.get(k) for k in ('solveRounds', 'distinctSolutions', 'phaseStart', 'verdicts', 'nearestAllyMedian', 'othersWithSpawnCmd', 'others')} | {
                'stackPairs': len(sp.get('stackPairs') or []),
                'bots': [{k: b.get(k) for k in ('bot', 'assignN', 'final', 'replaySpawnN', 'actual', 'verdict', 'distActualToFinal', 'localSendsApprox')} for b in sp.get('bots') or []]},
            'baselineTicks': D.get('baseline'),
            'delayByPeriod': D.get('delayByPeriod'),
            'delayBy300': D.get('delayBy300'),
            'lagByBotP50': {b: [x.get('p50') if x else None for x in v] for b, v in (D.get('lagByBot') or {}).items()},
            'funnel': D.get('funnel'),
            'funnelTotals': D.get('funnelTotals'),
            'selfReport': {k: (D.get('selfReport') or {}).get(k) for k in ('shadow', 'cmds', 'landed', 'executedAll')},
            'phantomDecisions': D.get('phantom'),
            'lateVoid': D.get('lateVoid'),
            'batches': D.get('batches'),
            'batchSizes': D.get('batchSizes'),
            'inflightRepeats': D.get('inflightRepeats'),
            'neverLanded': D.get('neverLanded'),
            'lastLocalTick': D.get('lastLocalTick'),
        })
    p = f'{work}/{mid}-land.json'
    if os.path.exists(p):
        L = json.load(open(p))
        out['landAccount'] = _rd({
            'source': f'scripts/land_account.mjs {mid}（每格陆地归离它最近的真人出生点；出生点 = 重放第 0 拍各人领地外接框中心）',
            'voronoi': L.get('voronoi'), 'capture': L.get('capture'), 'cellOwners': L.get('cellOwners'), 'botLand': L.get('botLand'),
            **{k: L[k] for k in ('multiTeam', 'squadTeams', 'botTeams') if k in L},
        })
    p = f'{work}/{mid}-attrib.json'
    if os.path.exists(p):
        A = json.load(open(p))
        out['tickAttribution'] = _rd({
            'source': f'scripts/shadow.mjs {mid} --quiet --tc 600:1500 → scripts/tick_attrib.py {mid}（每个决策拍归一类，类别互斥）',
            **{k: A.get(k) for k in ('window', 'rows', 'cats', 'layers', 'floorSetter', 'safeFiniteHalf', 'issuedByClass', 'byBot')},
            **{k: A[k] for k in ('exits', 'ptGates', 'gaExit', 'notSentSplit', 'sendRefused', 'noFullSendRows') if k in A},
        })
    p = f'{work}/{mid}-quota.json'
    if os.path.exists(p):
        Q = json.load(open(p))
        out['quotaGuard'] = _rd({
            'source': f'scripts/quota_guard.py {mid}（影子策略里 Policy.send 的调用数、没走到 return ok 的次数、isNoFullSend 被置位的拍）',
            **{k: Q.get(k) for k in ('ver', 'okLine', 'calls', 'refused', 'nfsAt', 'byPeriod', 'byBot')},
        })
    return out


def account_scripts(mid):
    """三本账的复现命令（写进复盘 JSON 的 scripts 字段）。"""
    w = '/tmp/c136-r05/work'
    return [
        f'scripts/replay_cmds.mjs {mid} → scripts/shadow.mjs {mid} --quiet --tc 600:1500 --json {w}/{mid}-shadow.json → scripts/atk_fate.mjs {mid} --json（三本账的输入；批量见 scripts/accounts_batch.sh、scripts/shadow_refresh.sh）',
        f'scripts/delay_account.py {mid} --json {w}/{mid}-delay.json --list-batches（延迟硬账：出生执行、分时段延迟、漏斗、迟到落空、同拍批、在途重复）；scripts/delay_detail.py {mid}（按号 × 300 拍摊开）',
        f'scripts/land_account.mjs {mid} --json {w}/{mid}-land.json（好地账：名下份额、实际地 ÷ 份额、机器人地去向）',
        f'scripts/tick_attrib.py {mid} --json {w}/{mid}-attrib.json --by-bot --exits（600–1500 拍每个决策拍归一类）；scripts/quota_guard.py {mid} --by-bot（Policy.send 拒发与 isNoFullSend 置位拍）',
        f'scripts/accounts_md.py {mid}（把三本账渲染成 .md 的 6b 节）',
    ]
