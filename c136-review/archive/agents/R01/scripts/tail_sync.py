#!/usr/bin/env python3
"""tail_sync.py — 一局收尾时各号客户端的本地拍、墙上时间、服务器拍三者怎么对。
读：对局包的 in_game.log（行的先后 = 写入先后）、results.csv（RESULT 行的 at / tick / seconds）、
    out/<mid>/replay_cmds.csv（录像里的 leave 拍、每个席位最后一条落地指令）、out/<mid>/shadow_match.csv（落地指令的决策拍，可缺）。
用法: python3 tail_sync.py <matchId> [--from T]
  --from T   只看本地拍 >= T 的日志行（默认 = 最早一条 RESULT(left) 的 tick − 100）
输出三段：
  1. 逐号：RESULT 的 tick / at / seconds；这一拍按“正常的钟”（tick_clock.py 的全量拟合）该在第几秒；差几秒；
     日志里这个号最后一行 HL-TICK、HL-DISPATCH 的本地拍；录像里的 leave 拍；最后一条落地指令的拍（及其决策拍）。
  2. 快进下限：把日志行按先后排，夹在两条 RESULT 行之间的 HL 行，其写入时刻落在这两条 RESULT 的 at 之间。
     对每个号取“最早可能时刻的最大本地拍”和“最晚可能时刻的最小本地拍”，得出 拍数 ÷ 秒 的下限，对照正常速度。
  3. 停拍之后：各号在停拍后写下的决策（HL-DISPATCH）条数，录像里落地了几条。
"""
import csv, os, re, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_clock  # noqa: E402

DATA = '/agent/repos/c136-data/bundles'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')


def ts(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    argv = sys.argv[1:]
    mid = argv[0]
    res = list(csv.DictReader(open(os.path.join(DATA, mid, 'results.csv'))))
    by_bot = {r['bot']: r for r in res}
    left = [r for r in res if r['event'] == 'left']
    t_from = int(argv[argv.index('--from') + 1]) if '--from' in argv else int(min(float(r['tick']) for r in left)) - 100
    a, b, _, _ = tick_clock.fit()
    t_base = min(ts(r['at']) - float(r['seconds']) for r in res)  # 开局时刻（seconds 取整，取最早的）

    pat_hl = re.compile(r'^(\d+)\t\[([^\]]+)\] \[(HL-TICK|HL-DISPATCH)\] t=(\d+)')
    pat_res = re.compile(r'^(\d+)\t\[RESULT (?:\[[^\]]*\] )?([^\]]+)\]')
    seq = []  # (行序, 类型, 号, 本地拍)
    last_tick, last_disp = {}, {}
    for i, line in enumerate(open(os.path.join(DATA, mid, 'in_game.log'), errors='replace')):
        m = pat_hl.match(line)
        if m:
            bot, kind, t = m.group(2), m.group(3), int(m.group(4))
            if kind == 'HL-TICK':
                last_tick[bot] = t
            else:
                last_disp[bot] = t
            seq.append((i, kind, bot, t))
            continue
        m = pat_res.match(line)
        if m:
            seq.append((i, 'RESULT', m.group(2).strip(), -1))

    leave, last_cmd = {}, {}
    rp = os.path.join(OUT, mid, 'replay_cmds.csv')
    name_of = {}
    if os.path.exists(rp):
        for r in csv.DictReader(open(rp)):
            nm = r['pname']
            if r['kind'] == 'leave':
                leave[nm] = int(r['tick'])
            elif r['kind'] in ('attack', 'donate', 'boat'):
                last_cmd[nm] = int(r['tick'])
    dec_of = {}
    sp = os.path.join(OUT, mid, 'shadow_match.csv')
    if os.path.exists(sp):
        for r in csv.DictReader(open(sp)):
            if r.get('tDecide') not in (None, '', '-1'):
                dec_of[(r['bot'], int(float(r['tick'])))] = int(float(r['tDecide']))

    def seat_name(bot):
        for nm in list(leave) + list(last_cmd):
            if nm == bot or nm.endswith(' ' + bot):
                return nm
        return bot

    print(f'== {mid} 收尾对钟：正常的钟 seconds = {a:.1f} + {b * 1000:.2f} 毫秒 × tick（全量非 left 行拟合）')
    print('   号       RESULT tick  at(时:分:秒)   seconds  该拍正常秒数  晚了几秒 | 日志最后 HL-TICK / HL-DISPATCH | 录像 leave 拍 | 最后落地指令拍(决策拍)')
    order = sorted(res, key=lambda r: ts(r['at']))
    for r in order:
        bot = r['bot']; t = int(float(r['tick'])); s = ts(r['at']) - t_base
        nom = a + b * t
        nm = seat_name(bot)
        lc = last_cmd.get(nm)
        dec = dec_of.get((bot, lc)) if lc is not None else None
        print(f"   {bot:8s} {r['event']:5s} {t:5d}  {r['at'][11:23]}  {s:7.1f}  {nom:9.1f}  {s - nom:7.1f} | {last_tick.get(bot, '-')} / {last_disp.get(bot, '-')} | {leave.get(nm, '无')} | {lc if lc is not None else '-'}({dec if dec is not None else '?'})")
    ats = [ts(r['at']) for r in order]
    print(f"   RESULT 行首尾相隔 {ats[-1] - ats[0]:.1f} 秒；leave 拍按正常的钟在第 " + ', '.join(sorted({f'{a + b * v:.1f}' for v in leave.values() if any(seat_name(r['bot']) == k for k in leave for r in res if leave[k] == v)})) + ' 秒')

    # 2. 快进下限
    print('== 快进下限（日志行先后 + RESULT 的 at）')
    res_at = {r['bot']: ts(r['at']) for r in res}
    marks = [(i, bot) for i, kind, bot, t in seq if kind == 'RESULT']
    def window(i):
        lo = max([res_at[bt] for j, bt in marks if j < i and bt in res_at], default=None)
        hi = min([res_at[bt] for j, bt in marks if j > i and bt in res_at], default=None)
        return lo, hi
    first_res = min(j for j, _ in marks) if marks else 10 ** 9
    per = {}
    for i, kind, bot, t in seq:
        if kind == 'RESULT' or t < t_from:
            continue
        lo, hi = window(i)
        per.setdefault(bot, []).append((t, lo, hi, i < first_res))
    norm_rate = 1.0 / b
    for bot, xs in per.items():
        xs.sort()
        # 最早一条：它最早不早于 lo（没有 lo 就不知道）；最晚一条：不晚于 hi
        firsts = [x for x in xs if x[1] is not None]
        lasts = [x for x in xs if x[2] is not None]
        before = [x[0] for x in xs if x[3]]
        line = f"   {bot:8s} 停拍后日志行的本地拍 {xs[0][0]}…{xs[-1][0]}（{len(xs)} 行；其中写在第一条 RESULT 之前的 {len(before)} 行" + (f"，到 {max(before)} 拍" if before else '') + '）'
        best = None
        for f in firsts:
            for l in lasts:
                if l[0] > f[0] and l[2] > f[1]:
                    rate = (l[0] - f[0]) / (l[2] - f[1])
                    if best is None or rate > best[0]:
                        best = (rate, f[0], l[0], l[2] - f[1])
        if best:
            line += f"；{best[1]}→{best[2]} 拍（{best[2] - best[1]} 拍）用时不超过 {best[3]:.2f} 秒 = 每秒至少 {best[0]:.0f} 拍（正常 {norm_rate:.1f}）"
        if bot in by_bot:
            rt = int(float(by_bot[bot]['tick']))
            if before and bot in res_at:
                first_at = min(res_at.values())
                if res_at[bot] > first_at and rt >= max(before):
                    line += f"；第一条 RESULT 之后到自己的 RESULT 相隔 {res_at[bot] - first_at:.1f} 秒，本地拍只从 ≥{max(before)} 走到 {rt}"
        print(line)

    # 3. 停拍之后的决策
    print('== 停拍之后写下的调度（HL-DISPATCH，本地拍 >= 最早 RESULT tick）与录像')
    t_stall = int(min(float(r['tick']) for r in left))
    don_land = {}
    if os.path.exists(rp):
        for r in csv.DictReader(open(rp)):
            if r['kind'] == 'donate' and int(r['tick']) >= t_stall:
                don_land[r['pname']] = don_land.get(r['pname'], 0) + 1
    cnt = {}
    for i, kind, bot, t in seq:
        if kind == 'HL-DISPATCH' and t >= t_stall:
            cnt.setdefault(bot, []).append(t)
    tot = 0
    for bot, tt in cnt.items():
        tot += len(tt)
        print(f"   {bot:8s} {len(tt)} 条（本地拍 {min(tt)}…{max(tt)}）；录像里 {t_stall} 拍后该席位落地的捐款 {don_land.get(seat_name(bot), 0)} 条")
    all_last = max(last_cmd.get(seat_name(r['bot']), -1) for r in res)
    print(f"   合计 {tot} 条；本队全部席位在录像里最后一条落地指令 t={all_last}；录像最后一拍见 replay_meta.json")

    # 4. 行序：最后一个全队都写了的 HL-TICK 拍之后，日志行是交替出现还是一个号连着补
    ticks_by_t = {}
    for i, kind, bot, t in seq:
        if kind == 'HL-TICK':
            ticks_by_t.setdefault(t, set()).add(bot)
    n_bots = len({bot for _, kind, bot, _ in seq if kind == 'HL-TICK'})
    full = [t for t, bs in ticks_by_t.items() if len(bs) == n_bots]
    t_full = max(full) if full else None
    print(f'== 行序：最后一个 {n_bots} 个号都写了快照的本地拍 = {t_full}；之后的日志行按写入先后（同一个号连着的行合并）')
    if t_full is not None:
        i_full = max(i for i, kind, bot, t in seq if kind == 'HL-TICK' and t == t_full)
        runs = []
        for i, kind, bot, t in seq:
            if i <= i_full:
                continue
            tag = 'RESULT' if kind == 'RESULT' else ('快照' if kind == 'HL-TICK' else '调度')
            if runs and runs[-1][0] == bot and runs[-1][1] == tag and tag != 'RESULT':
                runs[-1][2].append(t)
            else:
                runs.append([bot, tag, [t]])
        out = []
        for bot, tag, tt in runs:
            out.append(f'{bot} RESULT' if tag == 'RESULT' else f"{bot} {tag} {','.join(str(x) for x in tt)}")
        for k in range(0, len(out), 6):
            print('   ' + ' | '.join(out[k:k + 6]))
        silent = sorted(b for b in {bot for _, kind, bot, _ in seq if kind == 'HL-TICK'} if last_tick.get(b) == t_full)
        print(f"   {t_full} 拍之后再没有快照的号：{len(silent)} 个（{' '.join(silent)}）")

    # 5. 决策耗时：停拍前最后一行与日志最后一行的 avgMs / maxMs
    pat_ms = re.compile(r'\[([^\]]+)\] \[HL-TICK\] t=(\d+) .*avgMs=([\d.]+) maxMs=([\d.]+)')
    ms = {}
    for line in open(os.path.join(DATA, mid, 'in_game.log'), errors='replace'):
        m = pat_ms.search(line)
        if m:
            ms.setdefault(m.group(1), []).append((int(m.group(2)), float(m.group(3)), float(m.group(4))))
    print(f'== 策略决策耗时（HL-TICK 的 avgMs / maxMs，maxMs 是开局以来的最大值）：{t_full} 拍那一行 → 日志最后一行')
    for bot, xs in sorted(ms.items()):
        pre = [x for x in xs if x[0] <= (t_full or 0)]
        if not pre or xs[-1][0] <= pre[-1][0]:
            continue
        print(f"   {bot:8s} t={pre[-1][0]} avgMs={pre[-1][1]} maxMs={pre[-1][2]} → t={xs[-1][0]} avgMs={xs[-1][1]} maxMs={xs[-1][2]}")
    print(f"   全队全场 avgMs 最大 {max(x[1] for xs in ms.values() for x in xs)}，maxMs 最大 {max(x[2] for xs in ms.values() for x in xs)}")

    # 6. 录像里停拍之后落地的指令：本队席位 / 其他席位
    if os.path.exists(rp):
        squad_names = {seat_name(r['bot']) for r in res}
        cs, co, first_o = {}, {}, []
        for r in csv.DictReader(open(rp)):
            tk = int(r['tick'])
            if tk <= all_last:
                continue
            d = cs if r['pname'] in squad_names else co
            d[r['kind']] = d.get(r['kind'], 0) + 1
            if r['pname'] not in squad_names and len(first_o) < 6 and tk not in first_o:
                first_o.append(tk)
        print(f'== 录像里 {all_last} 拍之后落地的指令：本队席位 {cs or "无"}；其他席位 {co or "无"}（最早的几拍 {first_o}）')
        same = [(r['pname'], r['kind'], r['tname']) for r in csv.DictReader(open(rp)) if t_stall <= int(r['tick']) <= t_stall + 7 and r['pname'] not in squad_names]
        print(f'   {t_stall}–{t_stall + 7} 拍其他席位的指令：' + '；'.join(f"{a_} {k_}{('→' + t_) if t_ else ''}" for a_, k_, t_ in same))


if __name__ == '__main__':
    main()
