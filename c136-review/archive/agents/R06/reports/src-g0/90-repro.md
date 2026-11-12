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
| lists | `python3 sim-v2/tools/g0_lists.py` | `sim-v2/tools/{verify_list,g0_list_more,g0_list_ext,g0_list_ext_more,attr_list,attr_list_ext,attr_list_seeds,fill_list}.txt` |
| core | `node sim-v2/tools/g0_batch.mjs verify verify sim-v2/tools/arena_calib_list20.txt`；`node sim-v2/tools/g0_batch.mjs checkpoint g0 sim-v2/tools/g0_list.txt` | 任务卡点名的两样：核心 20 局的 `sim-v2/calib/verify/<局>.json`，60 次断面 `sim-v2/calib/g0/<局>-<t0>-<版本>-<通道>.json` |
| plan | `node sim-v2/tools/g0_batch.mjs plan sim-v2/tools/g0_plan.txt`（每批之前先 `python3 sim-v2/tools/hold_list.py`） | 见下表 |
| tail | `node sim-v2/tools/verify_tail.mjs` | `sim-v2/calib/verify-tail.json` |
| delay | `node sim-v2/tools/opening_delay.mjs --live-clean sim-v2/calib/live --json sim-v2/calib/opening-delay.json` | `sim-v2/calib/opening-delay.json` |
| old | `bash sim-v2/tools/old_vs_new.sh` | `sim-v2/calib/old-vs-new.json`（1.6 节：与旧提交里入库的结果逐字段核对） |
| oldcode | `bash sim-v2/tools/old_code_arena.sh` | `sim-v2/calib/old-code-arena.json`（1.6 节：把旧提交的代码取到临时目录，重跑两个闭环房间，与现在的结果核对） |
| profile | `bash sim-v2/tools/profile_check.sh` | `sim-v2/calib/human-profile-check.json`（1.6 节：对手模型的参数文件从录像重算，与入库的那份逐字节比） |
| tables | `node sim-v2/tools/g0_report.mjs` | `sim-v2/calib/report/` |

`plan` 阶段把其余的运行排成一份带先后的计划（`tools/g0_plan.txt`，一行一张清单）。每排到一次重计算槽位，一个进程从计划的头上接着往下跑，到闸门的时间上限为止；已有结果的跳过。清单和产物：

| 计划里的一行 | 清单 | 产物 |
|---|---|---|
| `checkpoint g0` | `g0_list.txt`、`g0_list_more.txt`（核心 20 局补齐四档通道）、`g0_list_ext.txt`、`g0_list_ext_more.txt`（新接的 Va / Vc 局） | `sim-v2/calib/g0/<局>-<t0>-<版本>-<通道>.json` |
| `checkpoint hold` | `hold_list.txt`（`tools/hold_list.py` 从 C2 的结果里按规则挑） | `sim-v2/calib/hold/<局>-<t0>-{hold,cut}.json` |
| `arena arena-acc20` | `arena_calib_list20.txt`，开关 `--len 4300 --channel C2 --squad-fate real` | `sim-v2/calib/arena-acc20/<局>.json` |
| `arena batchcheck/arena-rerun` | `batchcheck_arena_list.txt`（两个房间，次序和上一行相反），开关同上 | `sim-v2/calib/batchcheck/arena-rerun/<局>.json`（1.6 节「两种跑法」的闭环抽查） |
| `checkpoint attr` | `attr_list.txt`（种子 1）、`attr_list_seeds.txt`（种子 2）、`attr_list_ext.txt`（新接的局） | `sim-v2/calib/attr/<局>-<t0>-<臂>[-s<种子>].json` |
| `verify verify` | `verify_list.txt`（入库的全部局） | `sim-v2/calib/verify/<局>.json` |
| `checkpoint fill` | `fill_list.txt` | `sim-v2/calib/fill/<局>-0630-<补法>.json` |
| `arena arena-rp1530` | `arena_calib_list20.txt`，再加 `--others-replay-until 1530` | `sim-v2/calib/arena-rp1530/<局>.json` |

630~1530 拍这个归因窗口的 C0 / C1 / C2 / C3 四条臂就是 `calib/g0/` 里的断面运行，不在 `attr_list.txt` 里重复。

1.6 节「两种跑法」的断面抽查另有一张清单，不在队列里，单独跑：

```
G="bash ../../tools/run-heavy.sh timeout 120 node --max-old-space-size=700"
$G sim-v2/tools/g0_batch.mjs checkpoint batchcheck/g0-batched sim-v2/tools/batchcheck_list.txt
timeout 60 node sim-v2/tools/same_result.mjs sim-v2/calib/batchcheck/g0-batched sim-v2/calib/g0
```

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

`g0_build.mjs` 在拼报告之前会核对正文模板里写下的数量关系（模板里的 `assert` 行，这一版核对了 {{v:build.asserts}} 条）。数据重跑之后，正文里哪句话不再成立，在这一步就报错，不会写出报告。模板里还有按数据到没到齐分两种写法的段落（`if` / `else` 行）：某一组运行没有跑完时，正文写的是「没有跑完」，不是空着或者用半截数据下结论。

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
| `sim-v2/calib/human-profile.json` | 对手模型的参数来源：核心 20 局真局里其余真人的出手统计（`tools/human_profile.mjs --matches <核心 20 局>`；从头重算见 `tools/profile_check.sh`） |
| `sim-v2/calib/{verify,live,g0,attr,fill,hold,arena-acc20,arena-rp1530,batchcheck}/`、`verify-tail.json`、`opening-delay.json`、`live-bands.json` | 本报告用到的全部运行结果 |
| `sim-v2/calib/report/tables/`、`values.json`、`notes.txt` | `g0_report.mjs` 生成的表、数字、提醒 |
| `sim-v2/calib/old-vs-new.json`、`old-code-arena.json`、`human-profile-check.json` | 1.6 节的三项核对（`tools/old_vs_new.sh`、`old_code_arena.sh`、`profile_check.sh`） |
| `sim-v2/tools/g0_all.sh`、`g0_batch.mjs`、`g0_plan.txt`、`g0_lists.py`、`hold_list.py`、各张 `*_list*.txt` | 队列、计划、清单 |
| `sim-v2/tools/g0_report.mjs`、`g0_build.mjs`、`same_result.mjs`、`old_vs_new.sh`、`old_code_arena.sh`、`profile_check.sh`、`verify_tail.mjs`、`opening_delay.mjs`、`live_table.mjs`、`human_profile.mjs` | 汇总、拼报告、核对 |
| `reports/src-g0/*.md` | 本报告的正文模板 |
