## 9. 复算办法

全部命令在 `c136-review/agents/R06/` 下执行。每个 node 都经重计算闸门（`../../tools/run-heavy.sh`）排队，node 命令上带 `timeout 120`（从拿到槽位起算；闸门自己另有 110 秒的上限）。

**整条队列（按顺序跑完本报告用到的全部运行，已有结果的跳过）：**

```
bash sim-v2/tools/g0_all.sh
```

它依次做的事，和各自的产物：

| 阶段 | 命令（节选） | 产物 |
|---|---|---|
| live | `node sim-v2/teamgate-v2.mjs --mode live --cohort all` | `sim-v2/calib/live/<局>.json` |
| bands | `node sim-v2/tools/live_table.mjs` | `sim-v2/calib/live-bands.json` |
| lists | `python3 sim-v2/tools/g0_lists.py` | `sim-v2/tools/{verify_list,g0_list_more,g0_list_ext,attr_list,attr_list_ext,attr_list_seeds,fill_list}.txt` |
| g0、g0x | `node sim-v2/tools/g0_batch.mjs checkpoint g0 <清单>` | `sim-v2/calib/g0/<局>-<t0>-<版本>-<通道>.json` |
| arena | `node sim-v2/tools/g0_batch.mjs arena arena-acc20 sim-v2/tools/arena_calib_list20.txt --len 4300 --channel C2 --squad-fate real` | `sim-v2/calib/arena-acc20/<局>.json` |
| arena-rp | 同上，加 `--others-replay-until 1530` | `sim-v2/calib/arena-rp1530/<局>.json` |
| attr、attrx、seeds | `node sim-v2/tools/g0_batch.mjs checkpoint attr <清单>` | `sim-v2/calib/attr/<局>-<t0>-<臂>[-s<种子>].json` |
| delay | `node sim-v2/tools/opening_delay.mjs --live-clean sim-v2/calib/live --json sim-v2/calib/opening-delay.json` | `sim-v2/calib/opening-delay.json` |
| verify | `node sim-v2/tools/g0_batch.mjs verify verify sim-v2/tools/verify_list.txt` | `sim-v2/calib/verify/<局>.json` |
| tail | `node sim-v2/tools/verify_tail.mjs` | `sim-v2/calib/verify-tail.json` |
| fill | `node sim-v2/tools/g0_batch.mjs checkpoint fill sim-v2/tools/fill_list.txt` | `sim-v2/calib/fill/<局>-0630-<补法>.json` |
| hold | `python3 sim-v2/tools/hold_list.py`，再 `node sim-v2/tools/g0_batch.mjs checkpoint hold sim-v2/tools/hold_list.txt` | `sim-v2/calib/hold/<局>-<t0>-hold.json` |
| batchcheck | `bash sim-v2/tools/g0_run.sh batchcheck/attr-single < 抽出的清单`，再 `node sim-v2/tools/same_result.mjs …` | `sim-v2/calib/batchcheck/` |

**单独跑一次（不经批量）：**

```
G="bash ../../tools/run-heavy.sh timeout 120 node --max-old-space-size=700"
$G sim-v2/teamgate-v2.mjs --mode verify --match B021
$G sim-v2/teamgate-v2.mjs --mode checkpoint --match A021 --t0 630 --len 900 --baseline vb --channel C2
$G sim-v2/teamgate-v2.mjs --mode arena --room B021 --baseline c110 --channel C2 --len 4300 --squad-fate real
```

`--baseline` 只接受这一局当年线上那一版（`va` / `vb` / `vc` / `c110`）；给别的版本、别的文件，或者任何已停用的开关（候选臂、策略参数覆盖等），模拟器报错并以退出码 3 结束。

**从运行结果到这份报告：**

```
timeout 120 node sim-v2/tools/g0_report.mjs       # 全部表和数字 → sim-v2/calib/report/（只读结果文件，一两秒）
timeout 120 node sim-v2/tools/g0_build.mjs        # 拼成 reports/SIM-V2-CALIBRATION-G0.md
```

`g0_build.mjs` 在拼报告之前会核对正文模板里写下的数量关系（模板里的 `assert` 行，一共 {{v:build.asserts}} 条）。数据重跑之后，正文里哪句话不再成立，在这一步就报错，不会写出报告。

**接一局新的历史对局进来（录像、策略日志在数据包里的）：**

```
bash sim-v2/tools/add_match.sh <c110|c116-vb|c116-va|c116> <局号…>
```

它依次做：录像解码 → 真引擎重放两遍（得到逐拍指纹）→ 当年那一版策略作影子重演（得到下令拍）→ 入库（`packs/index.json`、`truth/`、`traces/`）。

**文件清单：**

| 路径 | 内容 |
|---|---|
| `sim-v2/teamgate-v2.mjs`、`sim-v2/lib/*.mjs` | 模拟器 |
| `sim-v2/packs/index.json`、`sim-v2/truth/`、`sim-v2/traces/`、`sim-v2/maps/` | 入库各局的输入：我方席位与内置 AI 名字、真引擎指纹、实录配对、地图 |
| `sim-v2/calib/human-profile.json` | 对手模型的参数来源：20 局真局里其余真人的出手统计（`tools/human_profile.mjs`） |
| `sim-v2/calib/{verify,live,g0,attr,fill,hold,arena-acc20,arena-rp1530,batchcheck}/`、`verify-tail.json`、`opening-delay.json`、`live-bands.json` | 本报告用到的全部运行结果 |
| `sim-v2/calib/report/tables/`、`values.json`、`notes.txt` | `g0_report.mjs` 生成的表、数字、提醒 |
| `sim-v2/tools/g0_*.{sh,py,mjs}`、`hold_list.py`、`same_result.mjs`、`verify_tail.mjs`、`opening_delay.mjs`、`live_table.mjs` | 队列、清单、汇总、核对 |
| `reports/src-g0/*.md` | 本报告的正文模板 |
