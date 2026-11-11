#!/usr/bin/env bash
# m6_run_all.sh — 把 M6 跨局汇总用到的全部表按顺序重新生成一遍，输出落在 reports/m6-data/（进 git；out/ 不进 git）。
# 只跑轻量的 python（每个脚本几秒）。node 的重演产物要先有：
#   bash scripts/batch_loop.sh scripts/steps/m6-replays.txt     /tmp/r01_m6b.log   # 其余 91 个包的录像指令表（replay_cmds）
#   bash scripts/batch_loop.sh scripts/steps/m6-a.txt           /tmp/r01_m6a.log   # 13 局好地账 + 9 局实际出生点
#   bash scripts/batch_loop.sh scripts/steps/m6-boats.txt       /tmp/r01_m6c.log   # 15 局船账、登陆账
#   bash scripts/batch_loop.sh scripts/steps/m6-voronoi-all.txt /tmp/r01_m6d.log   # 其余 83 个包的好地账
# 我复盘的 15 局的逐局产物（lag_periods.json、attrib3.json、spawn_layouts.json 等）由各局的 scripts/steps/*.txt 和 reviews/<局>.md 末尾的复现命令生成。
# 用法（在 c136-review/agents/R01 下）：bash scripts/m6_run_all.sh
set -u
cd "$(dirname "$0")/.."
D=reports/m6-data
mkdir -p "$D"
run() { local out=$1; shift; timeout 110 "$@" > "$D/$out" 2>&1 || echo "FAILED: $*" >&2; }

# —— 全量（123 个对局包）——
run all_pages.txt     python3 scripts/m6_all_pages.py --csv
run all_replay.txt    python3 scripts/m6_all_replay.py --csv
run all_traj.txt      python3 scripts/m6_all_traj.py --csv
run all_outcomes.txt  python3 scripts/m6_all_outcomes.py --csv
run all_land.txt      python3 scripts/m6_all_land.py --csv --list
run all_outcomes.txt  python3 scripts/m6_all_outcomes.py --csv     # land.csv 不参与 joined，但再跑一遍保证次序无关
cp out/_all/pages.csv out/_all/replay_facts.csv out/_all/traj.csv out/_all/joined.csv out/_all/land.csv "$D/"

# —— 我复盘的 15 局 ——
for m in A075 A057 A059 A055 A054 A031 A019 A009 A023 A050 A003 A005; do
  timeout 60 python3 scripts/spawn_layouts.py "$m" --brief --json > "out/$m/spawn_layouts.txt" 2>&1 || echo "FAILED spawn_layouts $m" >&2
done
timeout 60 python3 scripts/spawn_layouts.py A094 --brief --json > out/A094/spawn_layouts.txt 2>&1 || echo "FAILED spawn_layouts A094" >&2
run tables.md         python3 scripts/m6_tables.py all
run patterns.md       python3 scripts/m6_patterns.py --md
run donations.md      python3 scripts/m6_donations.py --md
run boats.md          python3 scripts/m6_boats.py --md
ls -la "$D"
