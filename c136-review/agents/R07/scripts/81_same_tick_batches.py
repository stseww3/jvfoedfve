#!/usr/bin/env python3
"""81_same_tick_batches.py — R07：同一个号在同一拍落地 ≥3 条指令的「批」（卡顿后一起到的指令）。

背景：策略每 5 拍决策一次，正常情况下一个号相邻两条指令的落地拍至少差 5 拍左右。
      同一拍落地 3 条以上，说明前面几个决策拍发的指令都堵在路上、一起到了；
      堵着的这段时间里策略看不到自己已经发出去的兵（余额没扣、在途进攻为 0），每个决策拍都会按同一份余额再下一单。
输入：out/<mid>/cmd_effect.tsv（67_troop_flow.mjs：引擎里每条指令落地时的真实扣款）、
      out/<mid>/shadow_cmds.tsv（65_shadow.mjs：影子策略每个决策拍想发的指令；用来找这一批是哪几拍发的）
用法：python3 81_same_tick_batches.py <matchId> [--min 3]
输出：out/<mid>/same_tick_batches.txt / .json
  A. 每个号：批数、批里的指令条数、花掉的兵、手续费、其中「第 2 条起」的兵和手续费
  B. 逐批：落地拍、条数、目标、花掉的兵 / 手续费、落地前余额 → 落地后余额（花掉的比例）、对应的发令拍范围（影子）
  B2. 按 pct 序列配对的发令拍（B 里取「最近几条」只是延迟的下限；这里找 pct 逐条对得上的那一段）
  C. 按 300 拍一档的批数（看卡顿集中在哪一段）
  D. 落地拍 mod 7；别的真人（humans_cmd.tsv，74_side_flow.mjs）同一拍 ≥3 条的批，按 300 拍一档
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    mid = sys.argv[1]
    mn = 3
    if '--min' in sys.argv:
        mn = int(sys.argv[sys.argv.index('--min') + 1])
    out = os.path.join(HERE, '..', 'out', mid)
    rows = list(csv.DictReader(open(os.path.join(out, 'cmd_effect.tsv'), encoding='utf-8'), delimiter='\t'))
    by = defaultdict(list)
    for r in rows:
        by[(int(r['t']), r['bot'])].append(r)
    shadow = defaultdict(list)
    sp = os.path.join(out, 'shadow_cmds.tsv')
    if os.path.exists(sp):
        for r in csv.DictReader(open(sp, encoding='utf-8'), delimiter='\t'):
            shadow[r['bot']].append(r)
    used = defaultdict(set)
    used2 = defaultdict(set)
    batches = []

    def pct_window(bot, t, L):
        """按 pct 序列配对：影子里这个号在落地前 150 拍内、还没被前面的批按这个办法用掉的同类指令里，
        找连续的 len(L) 条，使「排好序的 pct」和落地的这一批差得最少（差一样时取最早的一段：先发的先到）。"""
        kinds = set(r['kind'] for r in L)
        cand = [(i, s) for i, s in enumerate(shadow.get(bot, [])) if t - 150 <= int(s['t']) < t and i not in used2[bot] and s['kind'] in kinds]
        n = len(L)
        if len(cand) < n:
            return None
        want = sorted(int(r['pct']) for r in L)
        wins = []
        for k in range(0, len(cand) - n + 1):
            win = cand[k:k + n]
            d = sum(abs(a - b) for a, b in zip(want, sorted(int(s['pct']) for _, s in win)))
            wins.append((d, win))
        d = min(w[0] for w in wins)
        same = [w[1] for w in wins if w[0] == d]
        win = same[0]
        for i, _ in win:
            used2[bot].add(i)
        ts = [int(s['t']) for _, s in win]
        tl = [int(s['t']) for _, s in same[-1]]
        return dict(t0=min(ts), t1=max(ts), dist=d, lagMin=t - max(ts), lagMax=t - min(ts), nSame=len(same), lastT0=min(tl), lastT1=max(tl))

    for (t, bot), L in sorted(by.items()):
        if len(L) < mn:
            continue
        pw = pct_window(bot, t, L)
        b0 = int(L[0]['b0']); b1 = int(L[-1]['b1'])
        spent = sum(int(r['spent']) for r in L); fee = sum(int(r['fee']) for r in L); troops = sum(int(r['troops']) for r in L)
        live = [r for r in L if int(r['spent']) > 0]
        tg = defaultdict(int)
        for r in L:
            tg[(r['kind'], r['tname'])] += 1
        # 对应的发令拍：影子里这个号在落地拍之前 120 拍内、同类同目标、还没被别的批用掉的指令，取最近的 len(L) 条
        # （目标可能对不上：发令时打的是某个内置 AI，落地时它已经没了，引擎把这条改成打无主地）
        kinds = set(r['kind'] for r in L)
        cand = [(i, s) for i, s in enumerate(shadow.get(bot, [])) if t - 120 <= int(s['t']) < t and i not in used[bot] and s['kind'] in kinds]
        cand = cand[-len(L):]
        for i, _ in cand:
            used[bot].add(i)
        ts = [int(s['t']) for _, s in cand]
        first = live[0] if live else L[0]
        batches.append(dict(t=t, bot=bot, n=len(L), live=len(live), b0=b0, b1=b1, spent=spent, fee=fee, troops=troops,
                            extraTroops=troops - int(first['troops']), extraFee=fee - int(first['fee']),
                            targets=[dict(kind=k, target=n, n=v) for (k, n), v in sorted(tg.items(), key=lambda kv: -kv[1])],
                            pcts=[int(r['pct']) for r in L], issueT0=min(ts) if ts else None, issueT1=max(ts) if ts else None, issueN=len(ts),
                            issueTargets=sorted(set(s.get('targetName', '') for _, s in cand)), issuePcts=[int(s['pct']) for _, s in cand], pctWindow=pw))
    T = []
    P = T.append
    P(f'# {mid} 同一拍落地 ≥{mn} 条指令的批（81_same_tick_batches.py）：{len(batches)} 批，{sum(b["n"] for b in batches)} 条指令；全场我方生效指令 {len(rows)} 条')
    P('# 「第 2 条起」= 这一批里除了第一条生效指令以外的部分；发令拍来自影子运行（落地前 120 拍内同类同目标的最近几条）')
    P('')
    P('A. 每个号')
    P('号\t批数\t指令条数\t花掉的兵\t手续费\t第 2 条起：兵 / 费\t单批花掉余额最多')
    per = defaultdict(list)
    for b in batches:
        per[b['bot']].append(b)
    for bot, L in sorted(per.items()):
        mx = max(L, key=lambda b: (b['b0'] - b['b1']) / max(1, b['b0']))
        P(f"{bot}\t{len(L)}\t{sum(b['n'] for b in L)}\t{sum(b['troops'] for b in L):,}\t{sum(b['fee'] for b in L):,}\t{sum(b['extraTroops'] for b in L):,} / {sum(b['extraFee'] for b in L):,}\t"
          f"t={mx['t']} {mx['n']} 条，余额 {mx['b0']:,}→{mx['b1']:,}（{100 * (mx['b0'] - mx['b1']) / max(1, mx['b0']):.0f}%）")
    P(f"合计\t{len(batches)}\t{sum(b['n'] for b in batches)}\t{sum(b['troops'] for b in batches):,}\t{sum(b['fee'] for b in batches):,}\t{sum(b['extraTroops'] for b in batches):,} / {sum(b['extraFee'] for b in batches):,}\t")
    P('')
    P('B. 逐批（落地拍 号 条数（其中扣了款的）| 目标 | 花掉的兵 / 手续费 | 落地前余额 → 落地后（花掉比例）| pct 依次 | 影子里对应的发令拍）')
    for b in batches:
        tg = '、'.join(f"{x['kind']}→{x['target']}×{x['n']}" for x in b['targets'])
        iss = (f"{b['issueT0']}~{b['issueT1']}（{b['issueN']} 条，最早一条在路上 {b['t'] - b['issueT0']} 拍；发令时的目标 {'、'.join(b['issueTargets'][:4])}；pct {'/'.join(str(x) for x in b['issuePcts'])}）"
               if b['issueT0'] is not None else '影子里没找到')
        P(f"  t={b['t']} {b['bot']} {b['n']} 条（{b['live']}）| {tg} | {b['troops']:,} / {b['fee']:,} | {b['b0']:,}→{b['b1']:,}（{100 * (b['b0'] - b['b1']) / max(1, b['b0']):.0f}%）| "
          f"{'/'.join(str(x) for x in b['pcts'])} | {iss}")
    P('')
    P('B2. 按 pct 序列配对的发令拍（影子里落地前 150 拍内连续的同样条数、排好序的 pct 和落地这一批差得最少的一段；「pct 差」= 各条 pct 之差的绝对值合计，0 = 逐条相同）')
    P('    B 里的「最近几条」只给延迟的下限；一批指令的 pct 和影子某一段逐条相同时，这里的发令拍才是这一批真正的发令拍')
    for b in batches:
        pw = b.get('pctWindow')
        if not pw:
            P(f"  t={b['t']} {b['bot']} {b['n']} 条：影子里这段时间同类指令不够 {b['n']} 条")
            continue
        amb = '' if pw['nSame'] == 1 else f"；同样对得上的一共 {pw['nSame']} 段（这里取最早的一段，最晚的一段是 {pw['lastT0']}~{pw['lastT1']}，在路上 {b['t'] - pw['lastT1']}~{b['t'] - pw['lastT0']} 拍）"
        P(f"  t={b['t']} {b['bot']} {b['n']} 条：发令 {pw['t0']}~{pw['t1']}，在路上 {pw['lagMin']}~{pw['lagMax']} 拍，pct 差 {pw['dist']}{amb}")
    ex = [b for b in batches if b.get('pctWindow') and b['pctWindow']['dist'] == 0 and b['pctWindow']['nSame'] == 1]
    if ex:
        P(f"  逐条相同、只有一段对得上的 {len(ex)} 批：在路上最短 {min(b['pctWindow']['lagMin'] for b in ex)} 拍、最长 {max(b['pctWindow']['lagMax'] for b in ex)} 拍")
    P('')
    P('C. 每 300 拍一档的批数 / 指令条数')
    bk = defaultdict(lambda: [0, 0])
    for b in batches:
        k = b['t'] // 300 * 300
        bk[k][0] += 1; bk[k][1] += b['n']
    P('  ' + '；'.join(f"{k}~{k + 299}: {v[0]} 批 {v[1]} 条" for k, v in sorted(bk.items())))
    # D. 落地拍对 7 取余（服务器 7 拍一个回合）；别的真人同一拍 ≥mn 条的批（看这段卡顿是不是全场都有）
    P('')
    P('D. 落地拍 mod 7 与别的真人的对照')
    mod = defaultdict(int)
    for r in rows:
        mod[int(r['t']) % 7] += 1
    P('  我方指令落地拍 mod 7：' + '、'.join(f'{k}: {v}' for k, v in sorted(mod.items())))
    hp = os.path.join(out, 'humans_cmd.tsv')
    hum = None
    if os.path.exists(hp):
        H = [r for r in csv.DictReader(open(hp, encoding='utf-8'), delimiter='\t') if r.get('squad', '') not in ('1', 'true', 'True')]
        hmod = defaultdict(int); hby = defaultdict(list)
        for r in H:
            hmod[int(r['t']) % 7] += 1
            hby[(int(r['t']), r['p'])].append(r)
        P(f'  别的真人 {len(H)} 条指令的落地拍 mod 7：' + '、'.join(f'{k}: {v}' for k, v in sorted(hmod.items())))
        hb = defaultdict(lambda: [0, 0, 0]); allc = defaultdict(int)
        for r in H:
            allc[int(r['t']) // 300 * 300] += 1
        for (t, p), L in hby.items():
            if len(L) >= mn:
                k = t // 300 * 300
                hb[k][0] += 1; hb[k][1] += len(L); hb[k][2] = max(hb[k][2], len(L))
        P(f'  别的真人同一拍 ≥{mn} 条的批（每 300 拍：批数 / 条数 / 最大一批；括号里是这一档别的真人的全部指令数）：')
        P('    ' + '；'.join(f"{k}~{k + 299}: {hb[k][0]} / {hb[k][1]} / {hb[k][2]}（{allc[k]}）" for k in sorted(allc) if hb[k][0]))
        ours = defaultdict(int)
        for r in rows:
            ours[int(r['t']) // 300 * 300] += 1
        P('  我方每 300 拍：批数 / 条数（全部生效指令数）：' + '；'.join(f"{k}~{k + 299}: {bk[k][0]} / {bk[k][1]}（{ours[k]}）" for k in sorted(bk)))
        hum = dict(mod7=dict(hmod), buckets={k: v for k, v in hb.items()})
    open(os.path.join(out, 'same_tick_batches.txt'), 'w', encoding='utf-8').write('\n'.join(T) + '\n')
    json.dump(dict(n=len(batches), batches=batches, mod7=dict(mod), humans=hum), open(os.path.join(out, 'same_tick_batches.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('\n'.join(T))


if __name__ == '__main__':
    main()
