#!/usr/bin/env bash
# light_battery.sh — 一局的轻量事实表一次跑完（全是读 tmp/truth、tmp/shadow 和对局包的 Python 脚本，不重放），写进 out/<局号>/。
# 用法：timeout 118 bash scripts/light_battery.sh <局号> truth|shadow [--ours id,id,…]
#   truth  ：只要 tmp/truth/<局号>/（engine_truth_all.sh 的产物）
#   shadow ：还要 tmp/shadow/<局号>/{rows.tsv（28 列）,intents.tsv,check.json}（shadow_all.sh 的产物）
# 每个脚本单独限时 25 秒；失败的只记一行，不中断。
cd "$(dirname "$0")/.." || exit 2
m=$1; part=$2; shift 2
O="out/$m"; mkdir -p "$O"
END=$(python3 -c "import json;print(json.load(open('tmp/truth/$m/meta.json'))['lastTick'])" 2>/dev/null || echo 6000)
WIN="0,630,1500,2100,3000,3600,4284,$END"
run() { # run <输出文件> <脚本> [参数…]
  local out=$1; shift
  if ! timeout 25 python3 "scripts/$1" "${@:2}" > "$O/$out" 2>&1; then echo "失败：$*（见 $O/$out）"; fi
}
if [ "$part" = truth ]; then
  run spawn_churn.txt        spawn_churn.py "$m" --fan "$@"
  run client_lag.txt         client_lag.py "$m"
  run max_per_tick.txt       max_per_tick.py "$m"
  run human_strikes.txt      human_strikes.py "$m" --list 80 "$@"
  run refund_strikes.txt     refund_strikes.py "$m" --list "$@"
  run allin_strikes.txt      allin_strikes.py "$m" --list "$@"
  run neutral_pickup.txt     neutral_pickup.py "$m" --list "$@"
  run fee_ledger.txt         fee_ledger.py "$m" "$@"
  run boat_list.txt          boat_list.py "$m" --all "$@"
  run quota_truth.txt        quota_truth.py "$m" --list 30 "$@"
  run donation_list.txt      donation_list.py "$m" "$@"
  run yield_check.txt        yield_check.py "$m" --list "$@"
  run team_donations.txt     team_donations.py "$m" --list
  run postkill_exposure.txt  postkill_exposure.py "$m" "$@"
  run thin_after_spend.txt   thin_after_spend.py "$m" "$@"
  run squad_ledger.txt       squad_ledger.py "$m" --win "$WIN" "$@"
  run squad_series.txt       squad_series.py "$m" 0 "$END" 300 --terr "$@"
  run squad_series_dens.txt  squad_series.py "$m" 0 "$END" 300 --dens "$@"
  run cap_time.txt           cap_time.py "$m" --win "$WIN" "$@"
  run interest_rate.txt      interest_rate.py "$m" --at 1500,2100,2400,3000,3600 --win 1500,2100,3000,3600,4284 "$@"
  run flat_windows.txt       flat_windows.py "$m"
  run hollow_rear.txt        hollow_rear.py "$m" "$@"
  run incoming_tally.txt     incoming_tally.py "$m" 0 "$END" --by-target "$@"
  run finish_ledger.txt      finish_ledger.py "$m" "$@"
  run enemy_ledger.txt       enemy_ledger.py "$m" --win "$WIN" "$@"
elif [ "$part" = shadow ]; then
  run exec_gap.txt           exec_gap.py "$m" --profile 300
  run batch_targets.txt      batch_targets.py "$m" --list
  run burst_runs.txt         burst_runs.py "$m" --list
  run same_tick.txt          same_tick.py "$m" --list
  run boat_gap.txt           boat_gap.py "$m"
  run blind_reorders.txt     blind_reorders.py "$m" --list 30 --lag "$@"
  run cmds_delta_check.txt        cmds_delta_check.py "$m"
  run floor_bind_tally.txt        floor_bind_tally.py "$m" 630 1500
  run pre_human_floor_tally.txt   pre_human_floor_tally.py "$m" 630 1500 --list 20
  run window_tally_630_1500.txt   window_tally.py "$m" 630 1500
  run core_gate_tally.txt         core_gate_tally.py "$m" 1500 3500 --by-target
  run core_gate_tally_ai.txt      core_gate_tally.py "$m" 1500 3500 --ai --by-target
  run nfs_blocked.txt             nfs_blocked.py "$m" --from 1500
  run idle_scan.txt               idle_scan.py "$m"
else
  echo "第二个参数要 truth 或 shadow"; exit 2
fi
ls "$O" | wc -l
