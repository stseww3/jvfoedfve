#!/usr/bin/env python3
# run_prov.py — 本报告用到的每一个运行结果，是不是经重计算闸门（run-heavy.sh）跑出来的；没经闸门的抽一部分出来重跑核对。
#
# 背景：11 月 12 日 16:59（UTC）起，有别的进程在 R06 的工作区里不经闸门直接执行 tools/g0_batch.mjs，把清单上的运行跑掉了一大批
#（不是 R06 启动的，见 outbox/0022）。模拟是确定性的，结果应当和经闸门跑的一样，但 R06 不直接采信：这里把这些运行找出来，
# 每 EVERY 个抽 1 个（再加上 ALWAYS 里点名的），由 R06 自己的队列经闸门重跑到 calib/batchcheck/prov/<目录>/，再逐字段核对。
#
# 怎么判断一个结果是不是经闸门跑的：
#   1. calib/run-log.jsonl 里有它的流水（g0_batch.mjs 每跑完一次记一行，带进程的 nice 值）：nice = 19 是经闸门，其余不是；
#   2. 没有流水的（记流水之前跑的）：文件时间早于 STRAY_START 的是 R06 的队列经闸门跑的（那之前没有别的进程在跑）；
#      晚于它的不是（16:36 之后到开始记流水为止，R06 的队列没有排到过槽位，队列日志可以核对）。
#      这一条的结果已经定格在 calib/run-prov-base.json 里（11 月 12 日 17:50 的分类）：工作区在 20:53 被整个清掉、重新检出过，
#      文件时间从那以后不可信，列在定格文件里的结果按定格的分类算。
#
# 抽哪些：ALL_DIRS 里的目录（verify、闭环房间）没经闸门的全部重跑；其余目录按「目录/标签」的 sha1 取模，余数是 0 的抽中
#（清单后来变长了，原先抽中的还是抽中的），再加上 ALWAYS 里点名的。
# 核对：重跑的结果只有流水里 nice = 19 的才算数（别的进程要是把抽查清单也代跑了，那几个不算，等 R06 的队列重跑）。
#
# 产物：
#   sim-v2/calib/run-prov.json            每个结果目录：总数、经闸门的、没经闸门的；没经闸门的清单；抽查清单；核对结果
#   sim-v2/tools/provcheck/<目录>.txt      抽查清单（原清单里的原样行）
#   sim-v2/tools/provcheck_plan.txt        抽查的计划文件（g0_batch.mjs plan 的格式），结果写到 calib/batchcheck/prov/<目录>/
# 用法（在 c136-review/agents/R06 下）：python3 sim-v2/tools/run_prov.py
import hashlib, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SIMV2 = os.path.dirname(HERE)
CALIB = os.path.join(SIMV2, 'calib')
STRAY_START = datetime(2026, 11, 12, 16, 59, 40, tzinfo=timezone.utc).timestamp()
WIPE_AT = '2026-11-12T20:54:00'      # 工作区和数据包被清掉的时刻（20:53 UTC）之后的第一个整分；与流水里的 at（ISO 时刻）按字符串比
EVERY = 8
ALWAYS = {('hold', 'B041-0630-cut'), ('hold', 'A049-1530-cut')}
# 这两个目录里没经闸门的结果不抽样，全部重跑：闭环 20 个房间（第 7 节每个数都是 20 个房间合起来的）、verify（G0 第 1 项的依据）
ALL_DIRS = ['verify', 'arena-acc20']

def plan_lines():
    out = []
    for line in open(os.path.join(HERE, 'g0_plan.txt'), encoding='utf8'):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        p = s.split()
        out.append({'kind': p[0], 'dir': p[1], 'list': p[2], 'flags': p[3:]})
    return out

def list_rows(path, kind):
    rows = {}
    full = os.path.join(SIMV2, '..', path)
    if not os.path.exists(full):
        return rows
    for line in open(full, encoding='utf8'):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        rows[s.split()[0]] = s          # 三种清单的第一栏都是结果文件名（标签或局号）
    return rows

def strategy_shas():
    # lib/sandbox.mjs 里四个历史策略文件的内容散列（白名单）
    import re
    src = open(os.path.join(SIMV2, 'lib', 'sandbox.mjs'), encoding='utf8').read()
    return {m.group(1): m.group(2) for m in re.finditer(r"^\s*(va|vb|vc|c110): \['[^']+', '([0-9a-f]{64})'\]", src, re.M)}

def describe_check(kind, row, flags, path, shas):
    # 结果文件里自己记的「跑的是什么」，和清单上那一行对不对：局、断面、窗口长度、通道写法、种子、策略文件的内容散列。
    # 不重跑，只读文件；对全部结果都做（不只是抽查的那些）。返回不一致的字段名列表。
    try:
        r = json.load(open(path, encoding='utf8'))
    except ValueError:
        return ['读不出来']
    p = row.split()
    bad = []
    def want(name, got, exp):
        if got != exp:
            bad.append('%s：结果里是 %r，清单上是 %r' % (name, got, exp))
    def arm_shas():
        return sorted({a.get('sha256') for a in (r.get('arms') or {}).values() if isinstance(a, dict)})
    if kind == 'checkpoint':
        tag, mid, t0, ln, ver, chan = p[:6]
        seed = int(p[p.index('--seed') + 1]) if '--seed' in p else 1
        want('模式', r.get('mode'), 'checkpoint'); want('局', r.get('match'), mid); want('断面', r.get('t0'), int(t0))
        want('窗口长度', r.get('lenAsked'), int(ln)); want('通道', r.get('channelSpec'), chan); want('种子', r.get('seed'), seed)
        want('策略文件散列', arm_shas(), [shas.get(ver)])
    elif kind == 'arena':
        mid, ver = p[:2]
        fl = flags
        want('模式', r.get('mode'), 'arena'); want('局', (r.get('room') or {}).get('match'), mid)
        if '--len' in fl:
            want('长度', r.get('lenAsked'), int(fl[fl.index('--len') + 1]))
        if '--channel' in fl:
            want('通道', r.get('channelSpec'), fl[fl.index('--channel') + 1])
        want('策略文件散列', arm_shas(), [shas.get(ver)])
    elif kind == 'verify':
        want('局', r.get('match'), p[0])
    return bad

def main():
    log = {}
    stray_last = None
    stray_logged = 0
    lf = os.path.join(CALIB, 'run-log.jsonl')
    if os.path.exists(lf):
        for line in open(lf, encoding='utf8'):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            log[(r['dir'], r['tag'])] = r          # 同一个结果跑过几次的，以最后一次为准
            if r.get('nice') != 19:
                stray_logged += 1
                if stray_last is None or r['at'] > stray_last:
                    stray_last = r['at']
    # 定格的分类：工作区在 11 月 12 日 20:53（UTC）被整个清掉、重新检出过，文件的修改时间从那以后不可信。
    # 清掉之前最后一次提交里的分类（当时文件时间还是原样的）存成 calib/run-prov-base.json，这里列出的结果按它算，不再看文件时间。
    base_gated, base_ungated = set(), set()
    bf = os.path.join(CALIB, 'run-prov-base.json')
    if os.path.exists(bf):
        b = json.load(open(bf, encoding='utf8'))
        base_gated, base_ungated = set(b.get('gated', [])), set(b.get('ungated', []))
    plan = plan_lines()
    dirs = []
    for p in plan:
        if p['dir'].startswith('batchcheck/prov/'):
            continue
        if p['dir'] not in dirs:
            dirs.append(p['dir'])
    for d in ['verify', 'g0']:                      # core 阶段跑的两张清单不在计划文件里
        if d not in dirs:
            dirs.insert(0, d)
    prov = {'strayStart': datetime.fromtimestamp(STRAY_START, timezone.utc).isoformat(), 'every': EVERY, 'dirs': {}, 'ungated': [], 'sample': []}
    ungated = []
    for d in dirs:
        full = os.path.join(CALIB, d)
        if not os.path.isdir(full):
            continue
        tot = gated = 0
        for f in sorted(os.listdir(full)):
            if not f.endswith('.json'):
                continue
            tag = f[:-5]
            tot += 1
            r = log.get((d, tag))
            key = '%s/%s' % (d, tag)
            if r is not None:
                ok = r.get('nice') == 19
            elif key in base_gated:
                ok = True                     # 定格的分类（calib/run-prov-base.json）：当时按文件时间判定是经闸门跑的
            elif key in base_ungated:
                ok = False
            else:
                ok = os.path.getmtime(os.path.join(full, f)) < STRAY_START
            if ok:
                gated += 1
            else:
                ungated.append((d, tag))
        prov['dirs'][d] = {'total': tot, 'gated': gated, 'ungated': tot - gated}
    prov['ungated'] = ['%s/%s' % x for x in ungated]
    def picked(x):
        if x[0].startswith('batchcheck/'):          # 本身就是核对用的重跑，不再抽
            return False
        return x[0] in ALL_DIRS or x in ALWAYS or int(hashlib.sha1(('%s/%s' % x).encode()).hexdigest(), 16) % EVERY == 0
    sample = [x for x in ungated if picked(x)]
    prov['sampleFull'] = sum(1 for x in sample if x[0] in ALL_DIRS)        # 整个目录全部重跑的
    prov['sampleHash'] = len(sample) - prov['sampleFull']                  # 按散列抽的（含点名的）
    prov['always'] = len([x for x in sample if x in ALWAYS])
    prov['allDirs'] = ALL_DIRS
    prov['sample'] = ['%s/%s' % x for x in sample]
    prov['total'] = sum(v['total'] for v in prov['dirs'].values())
    prov['ungatedN'] = len(ungated)
    prov['sampleN'] = len(sample)

    # 抽查清单：从原清单里把原样的行找出来；同一个结果目录的并成一张
    os.makedirs(os.path.join(HERE, 'provcheck'), exist_ok=True)
    plan_out = ['# 没经闸门跑的运行的抽查（tools/run_prov.py 生成）：每行 = 类型 结果目录 清单 [开关]。结果写到 calib/batchcheck/prov/<原目录>/']
    by_dir = {}
    for d, tag in sample:
        by_dir.setdefault(d, []).append(tag)
    # 计划里的先后：抽样的目录在前，全部重跑的目录在后（闭环房间一次要占满一个槽位，放最后）
    by_dir = dict(sorted(by_dir.items(), key=lambda kv: ALL_DIRS.index(kv[0]) + 1 if kv[0] in ALL_DIRS else 0))
    missing = []
    for d, tags in by_dir.items():
        src = [p for p in plan if p['dir'] == d]
        if d == 'verify':
            src = src or [{'kind': 'verify', 'dir': 'verify', 'list': 'sim-v2/tools/verify_list.txt', 'flags': []}]
        if d == 'g0':
            src = src or [{'kind': 'checkpoint', 'dir': 'g0', 'list': 'sim-v2/tools/g0_list.txt', 'flags': []}]
        rows = {}
        for p in src:
            for k, v in list_rows(p['list'], p['kind']).items():
                rows.setdefault(k, v)
        lines = []
        for tag in tags:
            if tag in rows:
                lines.append(rows[tag])
            else:
                missing.append('%s/%s' % (d, tag))
        slug = d.replace('/', '_')
        tmp = os.path.join(HERE, 'provcheck', slug + '.txt.tmp')
        with open(tmp, 'w', encoding='utf8') as fh:
            fh.write('# %s 里没经闸门跑的运行的抽查清单（tools/run_prov.py 生成；每行是原清单里的原样行）\n' % d)
            fh.write('\n'.join(lines) + '\n')
        os.replace(tmp, os.path.join(HERE, 'provcheck', slug + '.txt'))
        flags = ' '.join(src[0]['flags']) if src else ''
        plan_out.append(('%-10s batchcheck/prov/%s sim-v2/tools/provcheck/%s.txt %s' % (src[0]['kind'], d, slug, flags)).rstrip())
    prov['sampleMissing'] = missing

    # 全量的自述核对：每个结果文件里记的局、断面、长度、通道、种子、策略文件散列，和清单上那一行一致不一致
    shas = strategy_shas()
    desc = {'n': 0, 'ok': 0, 'noRow': 0, 'bad': []}
    for d in list(prov['dirs'].keys()):
        full = os.path.join(CALIB, d)
        if not os.path.isdir(full):
            continue
        src = [p for p in plan if p['dir'] == d]
        if d == 'verify':
            src = src or [{'kind': 'verify', 'dir': 'verify', 'list': 'sim-v2/tools/verify_list.txt', 'flags': []}]
        if d == 'g0' and not any(p['list'].endswith('g0_list.txt') for p in src):
            src = [{'kind': 'checkpoint', 'dir': 'g0', 'list': 'sim-v2/tools/g0_list.txt', 'flags': []}] + src
        rows = {}
        for p in src:
            for k, v in list_rows(p['list'], p['kind']).items():
                rows.setdefault(k, (p['kind'], v, p['flags']))
        dn = dok = 0
        for f in sorted(os.listdir(full)):
            if not f.endswith('.json'):
                continue
            tag = f[:-5]
            if tag not in rows:
                desc['noRow'] += 1
                continue
            kind, row, flags = rows[tag]
            b = describe_check(kind, row, flags, os.path.join(full, f), shas)
            desc['n'] += 1; dn += 1
            if b:
                desc['bad'].append('%s/%s：%s' % (d, tag, '；'.join(b)))
            else:
                desc['ok'] += 1; dok += 1
        prov['dirs'][d]['described'] = dn; prov['dirs'][d]['describedOk'] = dok
    prov['describe'] = desc
    prov['strayLast'] = stray_last          # 流水里最后一次不是经闸门的运行的结束时刻
    prov['strayLogged'] = stray_logged
    prov['strategyShas'] = len(shas)

    # 核对：抽查清单里已经由 R06 的队列经闸门重跑出来的（流水里 nice = 19），对原结果逐字段比（tools/same_result.mjs，计时字段除外）
    # beforeWipe / afterRestore：工作区和数据包 11 月 12 日 20:53（UTC）被清掉过一次，数据包后来又回到原处。
    # 重跑按流水里的时刻分成「清掉之前跑的」和「数据包回来之后跑的」两拨，后一拨与原结果相同 = 恢复回来的数据包对这些运行给出的结果和原来一样。
    chk = {'n': 0, 'same': 0, 'leaves': 0, 'pending': 0, 'notGated': 0, 'redo': 0, 'bad': [],
           'beforeWipe': 0, 'afterRestore': 0, 'afterRestoreMatches': 0, 'afterRestoreSame': 0}
    after_tags, after_matches = [], set()
    def trunc_only_rerun(rerun, orig):
        try:
            a = json.load(open(rerun, encoding='utf8')); b = json.load(open(orig, encoding='utf8'))
        except (ValueError, OSError):
            return False
        return bool(a.get('truncated')) and not b.get('truncated')
    for d, tags in by_dir.items():
        rdir = os.path.join(CALIB, 'batchcheck', 'prov', d)
        tmp = tempfile.mkdtemp(prefix='r06-prov-')
        try:
            k = 0
            for tag in tags:
                f = os.path.join(rdir, tag + '.json')
                r = log.get(('batchcheck/prov/' + d, tag))
                if os.path.exists(f) and trunc_only_rerun(f, os.path.join(CALIB, d, tag + '.json')):
                    # 重跑的这一次被时间预算截断了、原结果没有截断：两个结果停在不同的拍上，不能比。删掉，留给队列下一批重跑。
                    os.remove(f)
                    chk['redo'] += 1
                if not os.path.exists(f):
                    chk['pending'] += 1
                elif r is None or r.get('nice') != 19:
                    chk['notGated'] += 1
                else:
                    shutil.copy(f, os.path.join(tmp, tag + '.json'))
                    k += 1
                    if str(r.get('at', '')) < WIPE_AT:
                        chk['beforeWipe'] += 1
                    else:
                        chk['afterRestore'] += 1
                        after_tags.append('%s/%s' % (d, tag))
                        after_matches.add(tag.split('-')[0])
            dv = prov['dirs'].setdefault(d, {})
            dv['sample'] = len(tags); dv['checked'] = 0; dv['same'] = 0
            if k:
                out = subprocess.run(['node', os.path.join(HERE, 'same_result.mjs'), '--json', os.path.join(CALIB, d), tmp],
                                     capture_output=True, text=True, timeout=100).stdout.strip().split('\n')
                j = json.loads(out[-1])
                chk['n'] += j['n']; chk['same'] += j['same']; chk['leaves'] += j['leaves']
                chk['bad'] += ['%s/%s' % (d, x) for x in out[:-1]]
                dv['checked'] = j['n']; dv['same'] = j['same']
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    chk['afterRestoreMatches'] = len(after_matches)
    bad_tags = {x.split()[0] for x in chk['bad']}
    chk['afterRestoreSame'] = sum(1 for x in after_tags if (x + '.json') not in bad_tags)     # bad 里每条以「目录/文件名.json」开头
    prov['check'] = chk

    # 同一局同一窗口的各个结果里，「历史」那一半（录像重放得到的真值，与挂哪条臂无关）应当逐字段相同。
    # 没经闸门的结果，若同一窗口里有经闸门跑出来的结果（原结果或抽查重跑），它的历史那一半就有了经闸门的对照。
    ungated_set = set(ungated)
    wins = {}
    def hist_of(path):
        try:
            r = json.load(open(path, encoding='utf8'))
        except (ValueError, OSError):
            return None
        h = r.get('history')
        if h is None or 'match' not in r or 't0' not in r or 't1' not in r:
            return None
        return (r['match'], r['t0'], r['t1']), hashlib.sha1(json.dumps(h, sort_keys=True, ensure_ascii=False).encode('utf8')).hexdigest()
    for d in prov['dirs'].keys():
        full = os.path.join(CALIB, d)
        if not os.path.isdir(full):
            continue
        for f in sorted(os.listdir(full)):
            if not f.endswith('.json'):
                continue
            x = hist_of(os.path.join(full, f))
            if x is None:
                continue
            wins.setdefault(x[0], []).append({'dir': d, 'tag': f[:-5], 'h': x[1], 'gated': (d, f[:-5]) not in ungated_set, 'rerun': False})
        rdir = os.path.join(CALIB, 'batchcheck', 'prov', d)
        if os.path.isdir(rdir):
            for f in sorted(os.listdir(rdir)):
                if not f.endswith('.json'):
                    continue
                r = log.get(('batchcheck/prov/' + d, f[:-5]))
                if r is None or r.get('nice') != 19:
                    continue
                x = hist_of(os.path.join(rdir, f))
                if x is not None and x[0] in wins:
                    wins[x[0]].append({'dir': d, 'tag': f[:-5], 'h': x[1], 'gated': True, 'rerun': True})
    hist = {'windows': len(wins), 'results': 0, 'badWindows': [], 'ungated': 0, 'anchored': 0, 'anchoredWindows': 0, 'ungatedWindows': 0}
    for key, items in sorted(wins.items()):
        orig = [x for x in items if not x['rerun']]
        hist['results'] += len(orig)
        if len({x['h'] for x in items}) > 1:
            hist['badWindows'].append('%s t0=%s t1=%s' % key)
        ung = [x for x in orig if not x['gated']]
        anchors = {x['h'] for x in items if x['gated']}
        hist['ungated'] += len(ung)
        if ung:
            hist['ungatedWindows'] += 1
            if anchors:
                hist['anchoredWindows'] += 1
        hist['anchored'] += sum(1 for x in ung if x['h'] in anchors)
    prov['history'] = hist
    tmp = os.path.join(HERE, 'provcheck_plan.txt.tmp')
    with open(tmp, 'w', encoding='utf8') as fh:
        fh.write('\n'.join(plan_out) + '\n')
    os.replace(tmp, os.path.join(HERE, 'provcheck_plan.txt'))
    tmp = os.path.join(CALIB, 'run-prov.json.tmp')
    with open(tmp, 'w', encoding='utf8') as fh:
        json.dump(prov, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(CALIB, 'run-prov.json'))
    print('结果 %d 个：没经闸门的 %d 个，抽查 %d 个（清单里找不到原样行的 %d 个）；已经经闸门重跑并核对 %d 个，逐字段相同 %d 个，还没重跑 %d 个，重跑了但不是经闸门的 %d 个'
          % (prov['total'], prov['ungatedN'], prov['sampleN'], len(missing), chk['n'], chk['same'], chk['pending'], chk['notGated']))
    for b in chk['bad']:
        print('  不同：' + b[:200])
    print('自述核对（结果文件里记的局 / 断面 / 长度 / 通道 / 种子 / 策略文件散列 对清单）：%d 个里 %d 个一致；清单里没有对应行的 %d 个' % (desc['n'], desc['ok'], desc['noRow']))
    for b in desc['bad'][:20]:
        print('  不一致：' + b[:300])
    print('历史那一半：%d 个窗口、%d 个结果，窗口内不一致的 %d 个；没经闸门的 %d 个结果里，%d 个所在窗口有经闸门的对照且相同（%d / %d 个窗口）'
          % (hist['windows'], hist['results'], len(hist['badWindows']), hist['ungated'], hist['anchored'], hist['anchoredWindows'], hist['ungatedWindows']))
    for b in hist['badWindows'][:20]:
        print('  历史不一致：' + b)
    for d, v in prov['dirs'].items():
        print('  %-24s 总数 %4d  经闸门 %4d  没经闸门 %4d' % (d, v['total'], v['gated'], v['ungated']))

if __name__ == '__main__':
    main()
