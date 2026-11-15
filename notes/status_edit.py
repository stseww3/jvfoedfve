#!/usr/bin/env python3
"""One-off: bring plan/STATUS.md to the third shift (run once, from the work tree's c164-realms/)."""
import sys

PATH = "plan/STATUS.md"
with open(PATH, encoding="utf-8") as fh:
    text = fh.read()
lines = text.split("\n")


def at(prefix):
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]


HEAD = """# 状态表：任务池总览

只有拿合并钥匙的人（s2，聊天 c318，接第 1 班的 c188）改。依据是私信里的固定格式消息（【领卡】【放回】【交付】【技检】【合并】【评审】），每处理一批更新一次。发现和事实不符，私信 c318，写哪一行、该是什么。

**汇总（s2 c318 更新，11-16 03:15）：共 59 张卡 —— 待领 9，制作中 28，已交付 2，已合并 9，已出图 4，暂过 1，已过审 4，退回 2。**

- 三班人。第 1 班（聊天 c176 到 c246）11-15 21:37 停，东西全部有效。第 2 班（c258 到 c297，11-15 23:38 到 11-16 01:55）跑的是别的模型，管理员定了他们做的东西一律不收（`roles/HANDOVER.md` 第 0 节）：不 merge、不 cherry-pick、不拷文件、不拷图、不照着改写；他们的聊天 02:26 全部停了。第 3 班（c318 到 c353，36 个岗位）11-16 凌晨上线，各自从第 1 班的「有效头」开新分支。谁是谁、新分支、节点、有效头在 `plan/ROSTER.md`（总监助理 c320 维护），本表不重抄。
- 总装是 `cursor/c164-assembly-fable-a9f5`：第 1 班的成果、总监的文档和脚本、第 3 班过了关口的交付。旧总装 `cursor/c164-realms-map-b59c` 封存了（封存告示 0ef4b284 压在第 2 班的历史上面，谁也不合它）。
- 各行的备注是第 1 班停机时（11-15 21:05，c188）的记录，照原样留着，第 3 班的事写在备注最前面。备注里的聊天号（c176 到 c246）都停了，现在是谁看「谁」一栏；备注里的旧分支名只当记录，那些分支的头是第 2 班的，不许用；备注里写“没跑过”的提交，接手的人在自己的节点上跑过才算数。
- 第 3 班到现在进总装的，都过了关口：公共文件 c8e3bba4；`materials/brass-oldcopper-small` bd7f25f9，补图 e67687ac；`sky/lights` b574cf75，补图 1a530b6b；`common/plots-shuttle` 78d0e548；`main/facade` 534dc9b6；`materials/panels` 打磨轮 a52bd566。总装头 42d7ef66（11-16 03:06）：21 个场景 check.py 0 失败。
- 机器：合用机只做轻活（git、读写文件）；check.py、render.py、selfshots.py、delivery.py 一律投到各自的节点（`tools/nodejob.sh`）。自查图各家在自己的节点上出，跟分支进 git。真机图等 s1（c319）把云端的游戏跑通。
- 关口是一条命令，`tools/gate.sh <类别>/<包名> <提交>`，做包的人交付以前可以自己先跑（加 `--base <总装头>`）：`tools/delivery.py` 八项（第一项 `shift` 就是 `tools/provenance.sh`，历史里有第 2 班的提交就退回）、`tools/checkall.py`（全部场景的 check.py）、动到的测试场景存的图逐像素核（`selfshots.py --verify`）。一批合完以后跑 `tools/keptshots.py`：总装里存的图哪些已经不是现在的代码画出来的，点名重出（结果在“图的现状”）。
- 待领（9 张，找总监助理 c320 领）：`common/offline-sky`（P3，记在 s1 名下，做不做待定）、`sky/ridges`（P3）、`machines/engine-dynamo`、`machines/switchboard-boiler`、`machines/meridian-astrograph`、`machines/recorders`、`interiors/powerhouse`、`motion/sound`、`motion/smoke`（后两张等 `motion/loop`）。
- 第 1 班停机以前的过程在本文件的上一版（提交 8f626b20）；11-14 中午以前的细节在更早的一版（提交 `d7b3f33d`）。

状态：待领 → 制作中 → 已交付 → 已合并 → 已出图 → 已过审；旁路：退回（回到制作中）、暂过（交叉看过了、评审还没评）。第 3 班的“已出图”是代码合并了、自查图也在总装里、关口核过，等评审。
“提交”一栏：制作中、退回写第 3 班新分支的头（11-16 03:10 按 git 查的；标“有效头”的是还没开工，等前一张卡交付），已交付写交付的提交，合并以后写总装上的合并提交。“图”一栏：自查图（离线图）在仓库 `renders/<场景名>/`。备注里的消息号有两种写法：三位数的是第 1 班群里的顺序号，五位数的是桥上的总号；本表照原话引。
"""

QUEUE = """## 排队（s2 照这个顺序做）

第 1 班留下的七条，到 11-16 03:10：

1. 公共文件（色板 `snow`、占用表的 SNOW、SNOW_LAYER 和炉火窗 `WINDOW_FURNACE`、骨架、check.py、INTERFACE、main 和 materials 两个类别开头的说明）：**进总装了，c8e3bba4**。在 node33 上跑了 `check.py --scene obs`、`obs_site_terrain` 和带 V1 机位的场景，代码一处没改就过；六条排队的交付叠在一起也试过一次（24 个场景 0 失败）。
2. `materials/brass-oldcopper-small`：**已合并** bd7f25f9（合的是 a2370b00）；25 张图 e67687ac（m1 c335 补的）。
3. `main/facade`：**已合并** 534dc9b6。facade c321 把有效头上没跑过的四样跑过，重新交付 f6da24f5，顶替 9ad51d24。
4. `main/shell`：等 shell c325 重新【交付】（先跑有效头 15b6cf2e 上没跑过的提交，出 22 个机位的图）；70a1966a 不单独合。facade 已经在总装里，他在 42d7ef66 上面交。
5. `sky/lights`：**已合并** b574cf75（合的是 8972aa88）；25 张图 1a530b6b（lights c331 补的）；交叉看 facade c321 过。
6. `common/plots-shuttle`：**已合并** 78d0e548（合的是 ecf454dd）。
7. `sky/comet`：等 comet c330 重新【交付】（跑过有效头 b3950eb4，出图）；7b7e168 不单独合。

- 第 3 班新到的交付，照到的先后：`materials/panels` 打磨轮 **已合并** a52bd566（合的是 b437a380）。
- 等【交付】再合：`sky/tones`（a2 c322）、`materials/ashlar` 新台徽和细琢面的长短石（ashlar c353）、`materials/board`（a1 c324）、`props/ironwork` 打磨轮（m3 c342）、`props/lamps` 场地灯链（lamps c341）、`sky/lights` 洗墙轮和窗后光源挪到玻璃外侧（lights c331，总监同意现在并）、`materials/iron` 二次交付（m5 c352）、`materials/snow`（snow c336）、`materials/windows` 的内衬和炉火窗（chart c350）、`site/stair`（stair c337）、`site/terrain` 三稿（a4 c323：交付前别拿它试合）、`site/cablecar`（cable c338）。
- `motion/loop`（a2 c322）交付的时候 s2 一起改三处（c177 #502 第三段，细化稿 `plan/parts/motion.md` 第 5 节）：`build/place.py` 导出以后调 `_kit.write()`、摆完跑它返回的命令；`tools/check.py` 的 regen 里同样调一次，加 `motion` 一项；INTERFACE 第 2 节那一条（已经在总装里）。
- 不合：`machines/scope` 的旧草稿（生成不出来，scope c344 接着重写）。
"""

BRANCHES = """## 分支

第 3 班各岗位的新分支、节点和「有效头」都在 `plan/ROSTER.md`（总监助理 c320 维护），本表不重抄。规矩在 `roles/HANDOVER.md` 第 0 节、`roles/COMMON.md` 第 2.1 节：

- 总装 `cursor/c164-assembly-fable-a9f5`：代码只有 s2（c318）推；总监（c164）和总监助理（c320）往上推文档和名单。谁也不强推。
- s2 自己的：`cursor/c164-s2-fable-89df`（和总装同头；关口的试合先推到这一条上，过了才推总装）；`cursor/c164-s2-wip-89df`（节点回传的报告：`renders/_wip/gate/<包名>/`、`renders/_wip/check/`、`renders/_wip/kept/`，不合进任何地方）；`cursor/c164-s2-trial-89df`（11-16 把六条排队的交付叠在一起试的那一次，不进总装）。
- 各家的新分支叫 `cursor/c164-<代号>-<包名>-f3…`，从第 1 班的有效头开；名字里带 `-wip` 的是各家节点回传报告用的，不交付。
- 第 1 班的旧分支（不带 `-f3` 的 `cursor/c164-…`）和旧总装 `cursor/c164-realms-map-b59c`：头是第 2 班的，不许 merge、cherry-pick、拷文件、拷图。`tools/provenance.sh <提交>` 说一个提交的历史里有没有第 2 班的东西（11-15 13:40 到 17:58 UTC 之间的提交，加 `plan/shift2-commits.txt` 里列的五个）；`tools/delivery.py` 的第一项查的就是它，关口上过不去。
- 真机位：s1（c319，接 c189）。第 1 班先后派过的 c232、c234、c244、c245 都作废了（A0 #294）。
"""

DECIDED = """### 11-16（第 3 班）

- 第 2 班的东西一律不收（管理员定的，`roles/HANDOVER.md` 第 0 节）：他们的提交只当存档，不 merge、不 cherry-pick、不拷文件、不拷图，也不照他们的实现改写；每张卡从第 1 班的有效头重新做起。
- 消息默认私信，三百字以内，写结论、提交号、要对方做什么；g2 只发【公告】和拿合并钥匙的人改公共文件的通知（`roles/COMMON.md`）。只为两件事找总监：要他拍板，或者报告卡住了；名单上的事找总监助理 c320。
- 第 2 班的聊天 02:26 全部停掉关闭；g2 里只有 c164 和 c318 到 c353（总监 #53059）。
- `plan/shift2-commits.txt`（ebaee520）：时间窗以外的五个第 2 班提交（旧 scope 分支两个，旧 lights 的人把新总装合进旧分支的三个），`tools/provenance.sh`、`tools/cloud_setup.sh` 都读它。哪条旧分支再动，告诉总监补名单（#53059）。
- 旧总装封存（0ef4b284：FROZEN.md，README 和 STATUS 顶上各一段）；那个提交在第 2 班的历史上面，谁也不合它（#53059）。
"""

PICTURES = """## 图的现状

自查图各家在自己的节点上出、跟分支进 git。关口合并前在 node33 上重画、逐像素核（`selfshots.py --verify`）；一批合完以后 `tools/keptshots.py` 把总装里存的图全部重画一遍，下表是它说的（总装 42d7ef66，11-16 03:09：15 个场景 207 张，94 张还是现在的代码画出来的，113 张不是）。

| 场景 | 存的图 | 现状 | 谁重出 |
| --- | --- | --- | --- |
| `obs_main_facade`、`_a`、`_c`、`_nocrown` | 8、4、4、5 | 都对 | — |
| `obs_mat_brass` | 25 | 都对 | — |
| `obs_mat_panels` | 10 | 都对（打磨轮的） | — |
| `obs_sky_lights` | 25 | 5 张对；20 张过期，立面换了入口：`blue_` 八张、`deep_` 七张、`glow_front`、`glow_axis`、`glow_v1`、`glow_slant`、`glow_surround` | lights c331，已点（#53332：`blue_door`、`deep_door` 建议挪到正对中拱） |
| `obs_mat_ashlar`、`_b`、`_c` | 17、17、17 | 各 11 张对；各 6 张过期：`walls_graze`、`coursed_course`、`coursed_lit`、`coursed_lit_dusk`、`lit_front`、`lit_lamp` | ashlar c353，随打磨轮 |
| `obs_mat_windows`、`_b` | 22、22 | 全部过期（灰白石换成真贴图 3380299e 以后没重出过） | chart c350，随窗的补件 |
| `obs_props_ironwork` | 14 | 全部过期（画的是退回的旧件） | m3 c342，随打磨轮 |
| `obs_site_court` | 9 | 全部过期 | a4 c323，随打磨轮；`v2_axis` 换成读骨架的机位 |
| `obs_site_terrain` | 8 | 全部过期（都是一稿的） | a4 c323，随三稿 |

- 图待补（各家在节点上出，随【交付】进来）：彗星三个场景（46）、`obs_main_shell`（22）、`obs_site_stair`、`obs_mat_iron`、`obs_mat_snow`，以及各机械、道具、室内的测试场景。
- 月亮位贴图方向改过以后（142f3079），之前有彗星入画的离线图都过期。
- 整座的看板图（12 个机位，`tools/boardshots.py`）归 s1（c319），每批合并以后对新的总装出。真机图等云端的游戏跑通。
"""

WAITING = """## 等各线报的

- 第 3 班 36 个岗位都上线、都推了新分支（ROSTER 121b7c4a）。接手的人先把有效头上“停机期间写的、没跑过”的提交在自己的节点上跑通，再出图，再【交付】；各行备注里写着“没跑过”的都要这样过一遍。到现在跑过并且交付了的：facade 入口轮、panels 打磨轮。
- 等重新【交付】：`main/shell`（shell c325）、`sky/comet`（comet c330）。等补图：`sky/lights` 过期的 20 张（lights c331）。
- 等交叉看：`materials/brass-oldcopper-small`（a6 c334）、`main/facade`（a4 c323）、`materials/panels` 打磨轮（m3 c342）。等评审：brass、panels 打磨轮、facade（review c332），lights（cr2 c333，等新图）。
- 第 1 班留下、接手的人要办的（原话在各行备注里）：cable c338 用 `S.in_v1_clear` 量缆车站第二版，卷扬机的钢缆和导轮同样不进那两块；orrery c343 把 `orrery.SUN_LIGHT` 从 10 改成 12（c243 #531，c220 #559 第 6 条）；读风向的各线（outb c340 气象站风杆上的风向标、a6 c334 的旗和风向袋、a2 c322 的烟和汽）读骨架的 `S.WIND_TO`、`S.WIND`（总监 #569；这三个名字已经在总装里，兜底的那一句可以去掉）；a4 c323 的 `obs_site_court` 机位 `v2_axis` 站在 `S.V2` 上却看旧的 (17, 11, 0.5)，check.py 的 views 给黄，打磨轮里改成读骨架。
- 两条“待证实”、铁轨落地自己转向、月亮位贴图方向、方块交互距离设成 0 管不管得住活板门、Realms 的服务器视距（c239 #556：只有 8 的话 V12 里桅杆会丢件）：等真机（s1 c319）。
"""

# ---- whole sections, by their headings ----
q, c = at("## 排队"), at("## common")
care = at("- 合的时候要留神的：")
assert q < care < c
kept_care = lines[care:c]                      # the list of what to mind when merging, kept
b, d = at("## 分支"), at("## 总监定过的")
p, f = at("## 图的现状"), at("## 成品地图交付清单")
w = at("## 等各线报的")
assert q < c < b < d < p < f < w
new = (HEAD.split("\n") + QUEUE.rstrip("\n").split("\n") + kept_care + lines[c:b]
       + BRANCHES.split("\n") + [lines[d], ""] + DECIDED.rstrip("\n").split("\n") + lines[d + 1:p]
       + PICTURES.split("\n") + lines[f:w] + WAITING.rstrip("\n").split("\n") + [""])
text = "\n".join(new)

# ---- single places: each must be there exactly once ----
SWAPS = [
    # what to mind when merging
    ("总装里 `DRESS` 关着，先合哪个都行。",
     "总装里 `DRESS` 关着，先合哪个都行；封口默认开的那一版 11-16 已经进了总装（534dc9b6）。"),
    ("那两句已经先改了（4116b04b，在 S2 分支上）：", "那两句已经先改了（4116b04b，11-16 进了总装）："),
    ("  - `main/_order.py`：c206 改了线脚的朝向（6 行，#561），随他这一轮交付进来，不单独合；进来以后鼓座托檐那一道（c222）、照南端墙搭的样板墙（c241）跟着变，图要重出。",
     "  - `main/_order.py`：线脚的朝向改了（6 行，#561），11-16 随 facade 的 f6da24f5 进了总装；鼓座托檐那一道（dome c326）、照南端墙搭的样板墙（pipes，m3 c342）跟着变，图照新总装出。"),
    # headings
    ("## common（牵头 c188）", "## common（牵头 s2 c318）"),
    ("## materials（牵头 c176；", "## materials（牵头 a1 c324；"),
    ("## sky（牵头 c177；", "## sky（牵头 a2 c322；"),
    ("## main（牵头 c206；", "## main（牵头 facade c321；"),
    ("## site（牵头 c221 接 c192，代号 a4；", "## site（牵头 a4 c323；"),
    ("## machines（原牵头 c193 不在岗；", "## machines（没有牵头；评审 cr3 c347；"),
    ("## props（牵头 c179；", "## props（牵头 a6 c334；"),
    ("## interiors（原牵头 c191 不在岗；", "## interiors（没有牵头；评审 cr3 c347；"),
    ("## motion（牵头 c177；", "## motion（牵头 a2 c322；"),
    # common
    ("| interface（接口说明 + 总场景框架） | P1 | 已合并 | c188 | 68d6797c |",
     "| interface（接口说明 + 总场景框架） | P1 | 已合并 | s2 c318（接 c188） | c8e3bba4 |"),
    ("11-15 的两次补充在 S2 分支上（0dd67cb9、e566a981、0d8a00fd，还没进总装）：",
     "11-15 的补充（0dd67cb9、e566a981、0d8a00fd）11-16 进了总装 c8e3bba4："),
    ("| skeleton（骨架） | P1 | 已合并 | c188 | 29e3ad25 |", "| skeleton（骨架） | P1 | 已合并 | s2 c318（接 c188） | c8e3bba4 |"),
    ("总装里是 11-14 中午那一版（东侧标高、四块台地、V11、墩和环梯、鼓座和大圆顶室的门）。11-15 的改动在 S2 分支上（8652ebd0、ec33a908、e566a981、0d8a00fd、2f9df9f3，没跑过，还没进总装）：",
     "底子是 11-14 中午那一版（东侧标高、四块台地、V11、墩和环梯、鼓座和大圆顶室的门）。11-15 的改动（8652ebd0、ec33a908、e566a981、0d8a00fd、2f9df9f3）11-16 在 node33 上跑过，进了总装 c8e3bba4："),
    ("| check（检查脚本） | P1 | 已合并 | c188 | d7bbdbd5 |", "| check（检查脚本） | P1 | 已合并 | s2 c318（接 c188） | c8e3bba4 |"),
    ("11-15 的改动在 S2 分支上（8652ebd0、e566a981，没跑过）：", "11-15 的改动（8652ebd0、e566a981）11-16 在 node33 上跑过，进了总装 c8e3bba4："),
    ("两条“待证实”（展示实体 160 格外不发、没设宽高的展示实体画面外照画）等真机 |",
     "两条“待证实”（展示实体 160 格外不发、没设宽高的展示实体画面外照画）等真机。第 3 班加的，都在总装里：`tools/checkall.py` 一趟查全部场景；`tools/gate.sh` 关口一条命令；delivery.py 的第一项 `shift` 查来源（`tools/provenance.sh`）；`tools/keptshots.py` 查存的图过没过期 |"),
    ("| status（状态表） | P1 | 已合并 | c188 | — |", "| status（状态表） | P1 | 已合并 | s2 c318（接 c188） | — |"),
    ("评审两人：c219 管 materials、main、props",
     "第 3 班评审三人：review c332（接 c219）管 materials、main、props，cr2 c333（接 c235）管 site、sky、motion，cr3 c347（新岗位）管 machines、interiors，分支在 ROSTER。第 1 班是两人：c219 管 materials、main、props"),
    ("| plots-shuttle（地块表和班车脚本） | P1 | 已交付 | c189 | ecf454d |",
     "| plots-shuttle（地块表和班车脚本） | P1 | 已合并 | s1 c319（接 c189） | 78d0e548 |"),
    ("| 工具卡，没有测试场景 | 分支 `cursor/c164-s1-render-9df7`。",
     "| 工具卡，没有测试场景 | 11-16 合并（合的是 ecf454dd，关口过）。`CamHelper.class` 是 javac 25.0.5 编的，javac 21 重编出来同样 8072 字节、内容不同：关口用 node33 上的 Temurin jdk-25.0.5+8（`$MC_ROOT/jdk`，`tools/gate.sh` 自己找，别处用环境变量 `JAVAC` 指）。有效头 9cbe672b 比交付多的（彗星三个场景的地块、看板 V6 的新朝向）s1 c319 跑过再交。下面是第 1 班的记录：分支 `cursor/c164-s1-render-9df7`。"),
    # materials
    ("| respack-redirect | P1 | 已过审 | c176 | 873f40f |", "| respack-redirect | P1 | 已过审 | a1 c324（接 c176） | 873f40f |"),
    ("占位由 `_standin._ROLES` 新加的几行带上（在 S2 分支上，没跑过）", "占位由 `_standin._ROLES` 新加的几行带上（11-16 进了总装 c8e3bba4）"),
    ("| board | P1 | 已合并 | c176 | c3b75f9a |", "| board | P1 | 已合并 | a1 c324（接 c176） | c3b75f9a |"),
    ("| ashlar | P1 | 已过审 | c204 | 3380299e |", "| ashlar | P1 | 已过审 | ashlar c353（接 c204） | 3380299e |"),
    ("| windows | P1 | 已过审 | c205 | 39bcd249 |", "| windows | P1 | 已过审 | chart c350（接 c205） | 39bcd249 |"),
    ("| iron | P2 | 已合并 | c198 | 9f09b11 |", "| iron | P2 | 已合并 | m5 c352（接 c198） | 9f09b11 |"),
    ("| panels | P2 | 已过审 | c194 | 09b1a6ef |", "| panels | P2 | 已出图 | m1 c335（接 c194） | a52bd566 |"),
    ("| `renders/obs_mat_panels/`（10 张，离线图） | 16 块面板；",
     "| `renders/obs_mat_panels/`（10 张，离线图，打磨轮的，node49 出，关口核过） | 打磨轮 11-16 合并（合的是 b437a380；m1 c335 在 node49 上跑过、出了图；关口过，10 张逐像素一致）：dial 两个读数、patch_panel、counter 的隔条、nameplate 换标准台徽、knife_switch 拉开的闸刀画直，BAY 新排法，`faults()` 导入时查；方块、朝向、`B.PANELS`、`WIDE`、`HIGH`、`bay()` 不变。交叉看点了 m3 c342，评审 c332 复看。第一版 09b1a6ef 是过了审的。下面是第 1 班的记录：16 块面板；"),
    ("| brass-oldcopper-small | P1 | 已交付 | c194 | a2370b0 |", "| brass-oldcopper-small | P1 | 已出图 | m1 c335（接 c194） | bd7f25f9 |"),
    ("| 图待补（25 个机位） | 分支 `cursor/c164-m1-brass-fa68`，场景 `obs_mat_brass`。",
     "| `renders/obs_mat_brass/`（25 张，离线图，node49 出，关口核过） | 11-16 合并（合的是 a2370b00，关口过）；图是 m1 c335 补的（e67687ac，25 张逐像素一致）；交叉看点了 a6 c334，评审 c332 还没评。下面是第 1 班的记录：分支 `cursor/c164-m1-brass-fa68`，场景 `obs_mat_brass`。"),
    ("| snow | — | 制作中 | c194 | 51f2fd69 |", "| snow | — | 制作中 | snow c336（接 c194） | ce0bd453 |"),
    ("| — | A0 #330（11-15）新开，派单没写优先级",
     "| — | 公共文件 11-16 进了总装（c8e3bba4：色阶 `snow`，SNOW 和 SNOW_LAYER 进重画），可以并了。下面是第 1 班的记录：A0 #330（11-15）新开，派单没写优先级"),
    # sky
    ("| look | P1 | 已合并 | c177 | ec29851a |", "| look | P1 | 已合并 | a2 c322（接 c177） | ec29851a |"),
    ("| lights | P1 | 已交付 | c220 | 8972aa8 |", "| lights | P1 | 暂过 | lights c331（接 c220） | b574cf75 |"),
    ("| 图待补（25 个机位） | 分支 `cursor/c164-lights-007c`，场景 `obs_sky_lights`。",
     "| `renders/obs_sky_lights/`（25 张，离线图，node45 出，关口核过；立面换了入口以后 20 张过期，在重出） | 11-16 合并（合的是 8972aa88，关口过）；图是 lights c331 补的（1a530b6b，25 张逐像素一致）；交叉看 facade c321 过（#53332：亮窗表和立面用的一格不差；入口三处光源和立面的占位逐格相同；图里的真楼还是旧入口，要重出，`blue_door`、`deep_door` 建议挪到正对中拱）；评审 cr2 c333 等新图。洗墙轮另交。下面是第 1 班的记录：分支 `cursor/c164-lights-007c`，场景 `obs_sky_lights`。"),
    ("| comet | P2 | 已交付 | c230 | 7b7e168 |", "| comet | P2 | 已交付 | comet c330（接 c230） | 7b7e168 |"),
    ("| 图待补（三个场景 46 个机位） | 分支 `cursor/c164-comet-986f`，3 版比选",
     "| 图待补（三个场景 46 个机位） | 第 3 班：7b7e168 不单独合，comet c330 把有效头 b3950eb4 跑过、出了图再重新【交付】。下面是第 1 班的记录：分支 `cursor/c164-comet-986f`，3 版比选"),
    ("| cloudsea | P2 | 制作中 | c227 | a18c8d13 |", "| cloudsea | P2 | 制作中 | cloud c329（接 c227） | c4935195 |"),
    ("| tones | P2 | 制作中 | c177 | 90cd8757 |", "| tones | P2 | 制作中 | a2 c322（接 c177） | 7868464f |"),
    # main
    ("| facade | P1 | 已交付 | c206 | 9ad51d24 |", "| facade | P1 | 已出图 | facade c321（接 c206） | 534dc9b6 |"),
    ("| `renders/obs_main_facade/`（B，8 张）、`obs_main_facade_a/`（4 张）、`obs_main_facade_c/`（4 张），离线图，画的是代码 af97672c，在分支上 | 分支 `cursor/c164-facade-229b`。",
     "| `renders/obs_main_facade/`（B，8 张）、`obs_main_facade_a/`（4 张）、`obs_main_facade_c/`（4 张）、`obs_main_facade_nocrown/`（5 张），离线图，node35 出，关口核过 | 11-16 合并（合的是 f6da24f5，顶替 9ad51d24；关口过，四个场景 21 张逐像素一致）：停机期间写的四样（拱头封口、素面台徽座、转角窗龛、线脚先朝墙）facade c321 头一回跑，代码没改就过；sky/lights 接走入口的光源，和占位逐格逐级相同；`_order.py` 线脚的朝向随这次进来（端墙压顶和腰线 48 格、鼓座托檐 28 格换朝向，别处不变）。交叉看点了 a4 c323，评审 c332 还没评。下面是第 1 班的记录：分支 `cursor/c164-facade-229b`。"),
    ("| dome | P1 | 制作中 | c222 | ecda0e1e |", "| dome | P1 | 制作中 | dome c326（接 c222） | c7c8bd2d |"),
    ("| tower | P1 | 制作中 | c223 | 951a1877 |", "| tower | P1 | 制作中 | tower c327（接 c223） | ecfdb001 |"),
    ("| smalldome | P1 | 制作中 | c224 | 98d469e8 |", "| smalldome | P1 | 制作中 | sdome c328（接 c224） | 76f3c9f2 |"),
    ("| shell | P1 | 已交付 | c231 | 70a1966a |", "| shell | P1 | 已交付 | shell c325（接 c231） | 70a1966a |"),
    ("| 图待补（22 个机位） | 分支 `cursor/c164-shell-f063`，场景 `obs_main_shell`：",
     "| 图待补（22 个机位） | 第 3 班：70a1966a 不单独合，shell c325 把有效头 15b6cf2e 跑过、出了图，在总装 42d7ef66（facade 已经在里面）上面重新【交付】。下面是第 1 班的记录：分支 `cursor/c164-shell-f063`，场景 `obs_main_shell`："),
    # site
    ("| court | P1 | 已过审 | c221 | 793d9f1e |", "| court | P1 | 已过审 | a4 c323（接 c221） | 793d9f1e |"),
    ("| terrain | P2 | 退回 | c221 | 793d9f1e |", "| terrain | P2 | 退回 | a4 c323（接 c221） | ba846850 |"),
    ("| stair | P2 | 制作中 | c225 | 36220ac4 |", "| stair | P2 | 制作中 | stair c337（接 c225） | 021e2636 |"),
    ("| powerhouse | P2 | 制作中 | c228 | 5ae1738e |", "| powerhouse | P2 | 制作中 | power c339（接 c228） | 6c661b0d |"),
    ("| cablecar | P2 | 制作中 | c226 | 246a2de5 |", "| cablecar | P2 | 制作中 | cable c338（接 c226） | 732ffa06 |"),
    ("| outbuildings | P2 | 制作中 | c229 | 6d320dd0 |", "| outbuildings | P2 | 制作中 | outb c340（接 c229） | e89c1403 |"),
    ("| mastbase | P3 | 制作中 | c229 | 6d320dd0 |", "| mastbase | P3 | 制作中 | outb c340（接 c229） | e89c1403 |"),
    # machines
    ("| orrery | P1 | 制作中 | c236 | f3a7e462 |", "| orrery | P1 | 制作中 | orrery c343（接 c236） | f3ba4da5 |"),
    ("| refractor | P1 | 制作中 | c237 | de4ef23a |", "| refractor | P1 | 制作中 | scope c344（接 c237） | 1d91a9dd |"),
    ("| clocks | P2 | 制作中 | c238 | abfd8079 |", "| clocks | P2 | 制作中 | clocks c345（接 c238） | 684eeda6 |"),
    ("| domegear | P2 | 制作中 | c196 | 30d769b5 |", "| domegear | P2 | 制作中 | m5 c352（接 c196；交了 iron 再开） | c7045d80（有效头） |"),
    ("| cablecar-winch | P2 | 制作中 | c240 | 76d5f9bd |", "| cablecar-winch | P2 | 制作中 | cable c338（接 c240；交了 cablecar 再开） | 5a6186cc（有效头） |"),
    ("| radiomast | P2 | 制作中 | c239 | ffcb474c |", "| radiomast | P2 | 制作中 | mast c346（接 c239） | 4dceb7b6 |"),
    ("| armillary | — | 制作中 | c246 | 560b1a44 |", "| armillary | — | 制作中 | ashlar c353（接 c246；交了 ashlar 再开） | 724d26be（有效头） |"),
    # props
    ("| lamps | P1 | 已出图 | c179（模型）、c220（位置表） | eba8e5cc |",
     "| lamps | P1 | 已出图 | a6 c334（模型，接 c179）、lamps c341（位置表和场地灯链，接 c220） | eba8e5cc |"),
    ("| pipes | P1 | 制作中 | c241 | c2bb7183 |", "| pipes | P1 | 制作中 | m3 c342（接 c241；交了 ironwork 再开） | c2bb7183（有效头） |"),
    ("| ironwork | P1 | 退回 | c218 | 0eaa777a |", "| ironwork | P1 | 退回 | m3 c342（接 c218） | 1f577be2 |"),
    ("| electrics-signs | P1 | 制作中 | c242 | 7fa7d16b |", "| electrics-signs | P1 | 制作中 | lamps c341（接 c242；交了 lamps 再开） | 5ff667a1（有效头） |"),
    ("| instruments | P2 | 制作中 | c199 | 97398871 |", "| instruments | P2 | 制作中 | m1 c335（接 c199） | cd190e36 |"),
    ("| furniture | P2 | 制作中 | c179 | ac64182c |", "| furniture | P2 | 制作中 | a6 c334（接 c179） | 0ef2a9f2 |"),
    ("| paper | P2 | 制作中 | c197 | b3ff0866 |", "| paper | P2 | 制作中 | snow c336（接 c197；交了 snow 再开） | b3ff0866（有效头） |"),
    # interiors
    ("| starhall | P2 | 制作中 | c243 | 192d7102 |", "| starhall | P2 | 制作中 | hall c348（接 c243） | d54199d0 |"),
    ("| domeroom | P2 | 制作中 | c178 | 95106dce |", "| domeroom | P2 | 制作中 | a3 c349（接 c178） | 909b0ca1 |"),
    ("| chartroom | P2 | 制作中 | c205 | fb9b2ecb |", "| chartroom | P2 | 制作中 | chart c350（接 c205；交了窗的补件再开） | fb9b2ecb（有效头） |"),
    ("| timeroom | P2 | 制作中 | c195 | b25b4a7c |", "| timeroom | P2 | 制作中 | m2 c351（接 c195） | a5801479 |"),
    # motion
    ("| loop | P2 | 制作中 | c177 | 90cd8757 |", "| loop | P2 | 制作中 | a2 c322（接 c177） | 7868464f |"),
    # the list for the finished map
    ("谁要加一条，群里点名 c188。", "谁要加一条，私信 s2（c318）。"),
]
for old, new_ in SWAPS:
    n = text.count(old)
    if n != 1:
        sys.exit(f"{n} times, not once: {old[:60]}")
    text = text.replace(old, new_)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
print("ok", len(lines), "->", text.count("\n") + 1, "lines")
