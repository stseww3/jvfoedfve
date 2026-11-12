#!/usr/bin/env python3
"""make_packs.py — 把 R06 本机核过的对局输入压成 sim-v2 能随目录带走的小文件。

读（R06 本机，未入库）：out/<局>/sim_in.json（sim_prep.py：录像来源、我方席位）、out/<局>/sim_state.json（eng_replay.cjs：真引擎重放的真值）
写（入库）：
  sim-v2/packs/index.json     每局：录像取自哪个包、我方席位、内置 AI 的名字（真引擎起的名；策略按名字认编队号，撞名 AI 要保留）、终局拍
  sim-v2/truth/<局>.json      真引擎重放的指纹：每 30 拍一个 32 位 FNV-1a（全体真人的 领土、兵力），teamgate-v2 --mode verify 用它核对物理底座

用法：python3 make_packs.py [局号…]（缺省：有 sim_in.json 和 sim_state.json 的全部局）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIMV2 = os.path.dirname(HERE)
OUT = os.path.join(os.path.dirname(SIMV2), 'out')


def fnv(vals):
    h = 0x811C9DC5
    for v in vals:
        v &= 0xFFFFFFFF
        for k in range(4):
            h ^= (v >> (8 * k)) & 0xFF
            h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def main():
    mids = sys.argv[1:]
    if not mids:
        mids = sorted(m for m in os.listdir(OUT) if os.path.exists(os.path.join(OUT, m, 'sim_in.json')) and os.path.exists(os.path.join(OUT, m, 'sim_state.json')))
    idx_path = os.path.join(SIMV2, 'packs', 'index.json')
    os.makedirs(os.path.dirname(idx_path), exist_ok=True)
    os.makedirs(os.path.join(SIMV2, 'truth'), exist_ok=True)
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    for mid in mids:
        inp = json.load(open(os.path.join(OUT, mid, 'sim_in.json')))
        st = json.load(open(os.path.join(OUT, mid, 'sim_state.json')))
        if not str(st.get('producer') or '').startswith('engine-') or not inp.get('replayLast'):
            print(f"{mid}: 跳过（没有真引擎重放的真值，或这局没有可用录像）")
            continue
        H = inp['humans']
        names = st.get('allNames') or []
        ai = {str(p): names[p] for p in range(H, len(names)) if names[p]}
        index[mid] = dict(replay=inp['replayPath'].split('/')[-2], humans=H, squad=inp['squad'], nTeams=inp['nTeams'], botTeams=inp['botTeams'],
                          teams=inp['teams'], endTick=inp['endTick'], replayLast=inp['replayLast'], aiNames=ai)
        hs = []
        for i, t in enumerate(st['ticks']):
            vals = []
            for p in range(H):
                tt = st['hum'][p]['terr'][i]
                tb = st['hum'][p]['bal'][i]
                vals.append(tt)
                vals.append(tb if tt > 0 else 0)
            hs.append(fnv(vals))
        json.dump(dict(matchId=mid, humans=H, ticks=st['ticks'], hash=hs, endT=st.get('endT'), producer=st.get('producer')),
                  open(os.path.join(SIMV2, 'truth', mid + '.json'), 'w'), separators=(',', ':'))
        print(f"{mid}: 录像 {index[mid]['replay']}，真人 {H}，我方 {len(inp['squad'])} 席，{inp['nTeams']} 队（AI 分队={inp['botTeams']}），真值采样 {len(hs)} 拍到 t={st['ticks'][-1]}")
    json.dump(index, open(idx_path, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f"写入 {os.path.relpath(idx_path, SIMV2)}（{len(index)} 局）")


if __name__ == '__main__':
    main()
