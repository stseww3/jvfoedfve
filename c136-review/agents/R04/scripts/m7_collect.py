#!/usr/bin/env python3
# m7_collect.py — 跨局汇总用：把同一个单局脚本对 13 局各跑一遍，只留它的汇总行，原样并排存到 out/m7/<名字>.txt。
# 用法：python3 scripts/m7_collect.py <名字> [局号 …]      名字见下面 JOBS；不给局号 = 13 局
#       python3 scripts/m7_collect.py --list
# 不算新数：每一行都是对应脚本自己印出来的（前面补上局号）。B034 自动带上 --ours（那一局只复盘 9 个号）。
# 单局脚本都只读 tmp/truth/<局号>/ 和 tmp/shadow/<局号>/ 的表，不重放。
import sys, os, re, subprocess
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MIDS = ['A013', 'A015', 'A022', 'A029', 'A038', 'A047', 'A073', 'A078', 'A081', 'A083', 'A086', 'A099', 'B034']
OURS = {'B034': '22,26,27,30,31,38,41,45,48'}
SKIP = {('quota_truth', 'A073'): '1v1，没有队友，没有捐款账', ('hollow_rear', 'A073'): '1v1，没有队友',
        ('pre_human_floor', 'A078'): 'A078 的影子表是早先的版本，没有 hbind 列；重跑影子两次都超过 110 秒被杀，这一格空着'}
# 名字: (脚本, 局号后面的参数, 认不认 --ours, 留哪些行)
JOBS = {
    'same_tick': ('same_tick.py', [], False, r'影子策略的意图|组内第 2 条'),
    'blind_reorders': ('blind_reorders.py', [], True, r'我方落地的陆攻|两类合计|用影子策略分|重复单按时段|串首执行前余额 ≥10 万的正常串'),
    'nfs_blocked': ('nfs_blocked.py', [], False, r'个号上过锁'),
    'nfs_blocked_1500': ('nfs_blocked.py', ['--from', '1500'], False, r'个号上过锁|拍以后'),
    'human_strikes': ('human_strikes.py', [], True, r'^  余额不超过|^  余额超过|^  over 的出手里'),
    'quota_truth': ('quota_truth.py', [], True, r'我方调度|^  [<≥\d][\d~]* +调度|合计没落地'),
    'hollow_rear': ('hollow_rear.py', [], True, r'^按 NEW-'),
    'boat_list': ('boat_list.py', [], True, r'^合计 |^手续费比载兵多|^有结果的|^登陆打敌方'),
    'fee_ledger': ('fee_ledger.py', [], True, r'^合计：'),
    'cap_time': ('cap_time.py', [], True, r'^合计（号·拍）|^号 \|'),
    'floor_bind': ('floor_bind_tally.py', ['630', '1500'], False, r'^合计|^号 '),
    'thin_after_spend': ('thin_after_spend.py', [], True, r'^合计'),
    'first_strike_lag': ('first_strike_lag.py', [], False, r'^合计|对数|中位'),
    'pre_human_floor': ('pre_human_floor_tally.py', [], False, r'^合计|^# '),
}


def main():
    a = sys.argv[1:]
    if not a or a[0] == '--list':
        for k, v in JOBS.items():
            print('%-18s %s %s' % (k, v[0], ' '.join(v[1])))
        return
    name = a[0]
    script, extra, ours_ok, keep = JOBS[name]
    mids = a[1:] or MIDS
    rx = re.compile(keep)
    out = ['# %s：python3 scripts/%s <局号> %s 的汇总行（每局原样；B034 带 --ours %s）' % (name, script, ' '.join(extra), OURS['B034'])]
    for m in mids:
        if (name, m) in SKIP:
            out.append('%s  （不适用：%s）' % (m, SKIP[(name, m)]))
            continue
        cmd = [sys.executable, os.path.join(HERE, script), m] + extra
        if ours_ok and m in OURS:
            cmd += ['--ours', OURS[m]]
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=100)
        except subprocess.TimeoutExpired:
            out.append('%s  （超时）' % m)
            continue
        if r.returncode != 0:
            out.append('%s  （脚本出错：%s）' % (m, (r.stderr.strip().splitlines() or ['?'])[-1][:160]))
            continue
        lines = [ln.rstrip() for ln in r.stdout.splitlines() if rx.search(ln)]
        if not lines:
            out.append('%s  （没有匹配的汇总行）' % m)
        for ln in lines:
            out.append('%s  %s' % (m, ln.strip()))
    os.makedirs(os.path.join(ROOT, 'out', 'm7'), exist_ok=True)
    fp = os.path.join(ROOT, 'out', 'm7', name + '.txt')
    with open(fp, 'w', encoding='utf8') as f:
        f.write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
