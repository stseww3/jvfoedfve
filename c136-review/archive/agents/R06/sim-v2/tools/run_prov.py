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
#
# 抽哪些：按「目录/标签」的 sha1 取模，余数是 0 的抽中（清单后来变长了，原先抽中的还是抽中的），再加上 ALWAYS 里点名的。
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
EVERY = 8
ALWAYS = {('hold', 'B041-0630-cut'), ('hold', 'A049-1530-cut')}

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

def main():
    log = {}
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
            if r is not None:
                ok = r.get('nice') == 19
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
        return x in ALWAYS or int(hashlib.sha1(('%s/%s' % x).encode()).hexdigest(), 16) % EVERY == 0
    sample = [x for x in ungated if picked(x)]
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

    # 核对：抽查清单里已经由 R06 的队列经闸门重跑出来的（流水里 nice = 19），对原结果逐字段比（tools/same_result.mjs，计时字段除外）
    chk = {'n': 0, 'same': 0, 'leaves': 0, 'pending': 0, 'notGated': 0, 'bad': []}
    for d, tags in by_dir.items():
        rdir = os.path.join(CALIB, 'batchcheck', 'prov', d)
        tmp = tempfile.mkdtemp(prefix='r06-prov-')
        try:
            k = 0
            for tag in tags:
                f = os.path.join(rdir, tag + '.json')
                r = log.get(('batchcheck/prov/' + d, tag))
                if not os.path.exists(f):
                    chk['pending'] += 1
                elif r is None or r.get('nice') != 19:
                    chk['notGated'] += 1
                else:
                    shutil.copy(f, os.path.join(tmp, tag + '.json'))
                    k += 1
            if k:
                out = subprocess.run(['node', os.path.join(HERE, 'same_result.mjs'), '--json', os.path.join(CALIB, d), tmp],
                                     capture_output=True, text=True, timeout=100).stdout.strip().split('\n')
                j = json.loads(out[-1])
                chk['n'] += j['n']; chk['same'] += j['same']; chk['leaves'] += j['leaves']
                chk['bad'] += ['%s/%s' % (d, x) for x in out[:-1]]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    prov['check'] = chk
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
    for d, v in prov['dirs'].items():
        print('  %-24s 总数 %4d  经闸门 %4d  没经闸门 %4d' % (d, v['total'], v['gated'], v['ungated']))

if __name__ == '__main__':
    main()
