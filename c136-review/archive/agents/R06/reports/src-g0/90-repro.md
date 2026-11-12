## 9. 复算办法

全部命令在 `c136-review/agents/R06/` 下执行。队列里的每个 node 都经重计算闸门（`../../tools/run-heavy.sh`）排队，node 命令上带 `timeout 120`（从拿到槽位起算；闸门自己另有 110 秒的上限），槽位数写死为 2。写报告时反复执行的几个只读脚本（`g0_report.mjs`、`g0_build.mjs`、`same_result.mjs`、`run_prov.py`，只读结果文件，一秒上下）是直接跑的，不占槽位。

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
| prov | `python3 sim-v2/tools/run_prov.py`，再 `node sim-v2/tools/g0_batch.mjs plan sim-v2/tools/provcheck_plan.txt` | `sim-v2/calib/run-prov.json`、`sim-v2/calib/batchcheck/prov/<目录>/`（下面「运行的出处」一段） |
| old | `bash sim-v2/tools/old_vs_new.sh` | `sim-v2/calib/old-vs-new.json`（1.6 节：与旧提交里入库的结果逐字段核对） |
| oldcode | `bash sim-v2/tools/old_code_arena.sh` | `sim-v2/calib/old-code-arena.json`（1.6 节：把旧提交的代码取到临时目录，重跑两个闭环房间，与现在的结果核对） |
| profile | `bash sim-v2/tools/profile_check.sh` | `sim-v2/calib/human-profile-check.json`（1.6 节：对手模型的参数文件从录像重算，与入库的那份逐字节比） |
| tables | `node sim-v2/tools/g0_report.mjs` | `sim-v2/calib/report/` |

`plan` 阶段把其余的运行排成一份带先后的计划（`tools/g0_plan.txt`，一行一张清单）。每排到一次重计算槽位，一个进程从计划的头上接着往下跑，到闸门的时间上限为止；已有结果的跳过。机器很挤的时候，经闸门的进程（优先级 19）只分得到一成上下的 CPU，重的运行（闭环房间、长窗口）给足一个槽位也跑不完；`g0_batch.mjs` 开跑前先量一下眼下分得到多少 CPU，估计跑不完的这一批先放下、去跑后面跑得完的，不白占槽位（被放下的过后重排时再试）。清单和产物：

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

**运行的出处：有一部分结果不是 R06 的队列跑出来的。**

11 月 12 日 {{v:prov.strayStart}} 到 {{v:prov.strayLast}}（UTC），有别的进程在 R06 的工作区里直接执行 `tools/g0_batch.mjs`，不经闸门（进程优先级 0，几个进程并行），把清单上排在后面的运行跑掉了一大批。不是 R06 启动的；是谁启动的，R06 没有查到（当时发了 alert：`outbox/0022-gate-bypass-in-r06-workdir.md`）。同一时刻 R06 工作区里闸门脚本的缺省槽位数被从 2 改成了 4；R06 把自己工作区里的改回去了，R06 的队列也一直写死 2 个槽位。

这些运行用的是 R06 工作区里的模拟器（`teamgate-v2.mjs`、`lib/`，当时与入库的一致）和清单，模拟又是确定性的，结果理应和经闸门跑的一样。R06 没有直接采信，做了三件事：

1. 从 17:06 起，`g0_batch.mjs` 每跑完一次运行就往 `calib/run-log.jsonl` 记一行（结果目录、标签、时刻、进程优先级），以后每个结果是不是经闸门跑的都有据可查。
2. 全部 {{v:prov.total}} 个结果，逐个把结果文件里自己记的局、断面、窗口长度、通道写法、种子、策略文件的内容散列，和清单上那一行对一遍。
3. 没经闸门跑的 {{v:prov.ungated}} 个里，{{v:prov.sample}} 个由 R06 自己的队列经闸门重跑到 `calib/batchcheck/prov/`，与原结果逐字段核对（计时字段除外）。其中 verify 的 {{v:prov.dir.verify.sample}} 局和闭环的 {{v:prov.dir.arena-acc20.sample}} 个房间是全部重跑（verify 是 G0 第 1 项的依据；第 7 节每个数都是 20 个房间合起来的，一个房间就占二十分之一）；断面运行（`attr/`、`hold/`）按固定规则抽 {{v:prov.sample.hash}} 个：按「目录/标签」的散列每 {{v:prov.every}} 个抽 1 个，另加点名的 {{v:prov.sample.always}} 个（B041、A049 的截断对照）。
<!-- assert: n('prov.dir.verify.sample') === n('prov.dir.verify.ungated') && n('prov.dir.arena-acc20.sample') === n('prov.dir.arena-acc20.ungated') && n('prov.sample.full') === n('prov.dir.verify.sample') + n('prov.dir.arena-acc20.sample') && n('prov.sample.hash') + n('prov.sample.full') === n('prov.sample') && n('prov.sample.always') === 2 -->

{{T:prov}}

<!-- assert: n('prov.describe.ok') === n('prov.describe.n') && n('prov.describe.n') === n('prov.total') && n('prov.check.bad') === 0 && n('prov.check.same') === n('prov.check.n') -->
- 自述核对：{{v:prov.describe.n}} 个里 {{v:prov.describe.ok}} 个与清单一致。
- 顺带的一项交叉核对：断面运行的结果里有一半是「历史」（这一局这个窗口的录像重放出来的真值，与挂哪条通道无关），同一局同一窗口的各个结果里这一半应当逐字段相同。{{v:prov.hist.windows}} 个窗口、{{v:prov.hist.results}} 个结果，窗口内不一致的 {{v:prov.hist.bad}} 个。没经闸门的断面结果有 {{v:prov.hist.ungated}} 个，其中 {{v:prov.hist.anchored}} 个所在的窗口里有经闸门跑出来的结果（原结果或抽查重跑），历史那一半与之相同；其余的窗口里只有没经闸门的结果互相对得上。这一项只管得到「历史」那一半，各条通道自己那一半靠下一条的抽查重跑。
<!-- assert: n('prov.hist.bad') === 0 && n('prov.hist.results') > 300 && n('prov.hist.anchored') <= n('prov.hist.ungated') -->
<!-- if: n('prov.done') === 1 -->
- 重跑核对：要重跑的 {{v:prov.sample}} 个全部经闸门重跑完，{{v:prov.check.same}} 个与原结果逐字段相同（共 {{v:prov.check.leaves}} 个字段）。
<!-- else -->
- 重跑核对：要重跑的 {{v:prov.sample}} 个里，到这一版为止经闸门重跑完 {{v:prov.check.n}} 个，{{v:prov.check.same}} 个与原结果逐字段相同（共 {{v:prov.check.leaves}} 个字段）；其余 {{v:prov.check.pending}} 个还在排队，跑完之后再执行 `python3 sim-v2/tools/run_prov.py` 就能看到结果。
<!-- endif -->
- 「没经闸门」是从严算的：记流水之前那几分钟里写出来的结果，分不清是谁跑的，一律算没经闸门。
- 没经闸门的结果集中在 `attr/`（0 / 1500 / 4284 三个断面的归因和换种子）：第 6 节除 630 断面以外的数，底下的运行绝大部分是这样来的。5.7 节的三种假定对照（`hold/`）、第 7 节的闭环（`arena-acc20/`）和新接的 Va / Vc 局的 verify 各有一部分。第 2 节核心 20 局的 verify、第 5 节的断面整表（`g0/`）全部是 R06 的队列经闸门跑的。

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
| `sim-v2/calib/old-vs-new.json`、`old-code-arena.json`、`human-profile-check.json` | 1.6 节的几项核对（`tools/old_vs_new.sh`、`old_code_arena.sh`、`profile_check.sh`） |
| `sim-v2/calib/run-log.jsonl`、`run-prov.json`、`batchcheck/prov/` | 运行流水、出处分类、抽查重跑的结果（`tools/run_prov.py`；抽查清单在 `tools/provcheck/`、`tools/provcheck_plan.txt`） |
| `sim-v2/tools/g0_all.sh`、`g0_batch.mjs`、`g0_plan.txt`、`g0_lists.py`、`hold_list.py`、各张 `*_list*.txt` | 队列、计划、清单 |
| `sim-v2/tools/g0_report.mjs`、`g0_build.mjs`、`same_result.mjs`、`run_prov.py`、`old_vs_new.sh`、`old_code_arena.sh`、`profile_check.sh`、`verify_tail.mjs`、`opening_delay.mjs`、`live_table.mjs`、`human_profile.mjs` | 汇总、拼报告、核对 |
| `reports/src-g0/*.md` | 本报告的正文模板 |
