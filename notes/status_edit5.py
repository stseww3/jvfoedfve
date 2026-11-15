#!/usr/bin/env python3
"""STATUS.md, the batch of 11-16 05:30: run in c164-realms/. Nothing is written unless every anchor is
found exactly once.

    python3 /tmp/c164_s2/status_edit5.py <values.py> [--write]

<values.py> gives the values that are only known when the gate has spoken (see V below)."""
import re
import sys

P = "plan/STATUS.md"
V = {}
exec(open(sys.argv[1], encoding="utf-8").read(), V)
lines = open(P, encoding="utf-8").read().split("\n")
errors = []


def find(prefix, lo=0, hi=None):
    hits = [i for i in range(lo, len(lines) if hi is None else hi) if lines[i].startswith(prefix)]
    if len(hits) != 1:
        errors.append(f"{len(hits)} lines start with {prefix!r}")
        return None
    return hits[0]


def section(title):
    i = find("## " + title)
    if i is None:
        return 0, 0
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    return i, j


def row(sec, name, state=None, who=None, commit=None, pics=None, front="", swap=(), prio=None):
    lo, hi = section(sec)
    i = find(f"| {name} | ", lo, hi)
    if i is None:
        return
    parts = lines[i].split(" | ", 6)
    if len(parts) != 7:
        errors.append(f"row {sec}/{name}: {len(parts)} columns")
        return
    for k, new in ((1, prio), (2, state), (3, who), (4, commit), (5, pics)):
        if new is not None:
            parts[k] = new
    note = parts[6]
    for old, new in swap:
        if note.count(old) != 1:
            errors.append(f"row {sec}/{name}: {note.count(old)} times {old!r}")
        note = note.replace(old, new)
    parts[6] = front + note
    lines[i] = " | ".join(parts)


def line(prefix, new, lo=0, hi=None):
    i = find(prefix, lo, hi)
    if i is not None:
        lines[i] = new


def after(prefix, new, lo=0, hi=None):
    i = find(prefix, lo, hi)
    if i is not None:
        lines[i + 1:i + 1] = list(new)


def drop(prefix, lo=0, hi=None):
    i = find(prefix, lo, hi)
    if i is not None:
        del lines[i]


def swap(prefix, old, new):
    i = find(prefix)
    if i is None:
        return
    if lines[i].count(old) != 1:
        errors.append(f"line {prefix!r}: {lines[i].count(old)} times {old!r}")
    lines[i] = lines[i].replace(old, new)


HEAD, WHEN, SCENES = V["HEAD"], V["WHEN"], V["SCENES"]
CARD, BARRIER, STAIR = V["CARD"], V["BARRIER"], V["STAIR"]
G = V.get("STACK", "merged") == "gate"      # the six deliveries and the barrier wait at the gate, off the assembly


def pick(merged, gate):
    return gate if G else merged


BARRIER_AT = pick(BARRIER, "s2 的分支上 " + BARRIER + "，在关口上，还没进总装")

# ---- the bullets at the top ------------------------------------------------------------------------
line("- 第 3 班到现在进总装的，都过了关口：",
     "- 第 3 班到现在进总装的，都过了关口，照进来的先后：公共文件 c8e3bba4；`materials/brass-oldcopper-small` bd7f25f9"
     "（补图 e67687ac，打磨轮 ed7fd0c2）；`sky/lights` b574cf75（补图 1a530b6b，入口 B 下重出的图 5ba3b4b6）；"
     "`common/plots-shuttle` 78d0e548；`main/facade` 534dc9b6（打磨轮第一批 167260ee）；`materials/panels` 打磨轮 a52bd566；"
     "`sky/comet` 2d7c1c7d；`materials/iron` 二次交付 c992a3ae（补图 c676a8eb，三次交付 3387d99c）；`main/smalldome` 825ec1ef；"
     "`site/terrain` 三稿和 `site/court` 打磨轮 8b7735eb；`motion/loop` 和 `sky/tones` 40e27461；`materials/snow` 3be01d94；"
     "`site/powerhouse` ff8ea061（二次交付 4b538dbe）；`main/dome` ec9ac975；`materials/ashlar` 打磨轮 a494bb19；"
     "`props/lamps` 场地灯链 b5faa03a"
     + pick("；`site/mastbase` 和 `site/outbuildings` 064dbc57；`machines/radiomast` 3b87af9d（二次交付 " + V["MAST2"] + "）；"
            "`machines/clocks` 7acc80db；`main/shell` f54bf237；`site/stair` " + STAIR + "；`sky/look` 的蓝调改动 " + V["LOOK"]
            + "；`main/dome` 二次交付（地图用乙）" + V["DOME2"], "")
     + "。s2 自己改的公共文件：`motion/loop` 要的三处 fc997791；骨架 `V6` e8af28a3、小穹顶顶点 26 8db6e43c；`check.py` 的太阳一条 "
       "c4829ad1；离线的星星 3a3c6efc；" + pick("占用表的屏障 " + BARRIER + "；", "") + "`tools/gatestack.sh` 225421af、8a5a9eaf。"
     + pick("总装到 " + HEAD + "（" + WHEN + "）：" + SCENES + " 个场景 check.py 0 失败。",
            "总装的代码最后一次全量检查在 8e55cfe1（11-16 04:51）：36 个场景 check.py 0 失败；之后进总装的只有文档、卡和 "
            "`tools/nodejob.sh` 的时限（总监 de71fb58）。**在关口上、还没进总装的**（来源都干净，叠着合在 s2 的分支 "
            "`cursor/c164-s2-fable-89df` 上，一个交付一个合并提交）：`site/mastbase` 和 `site/outbuildings` 69b57fe8（卡 5c2b6ec9）、"
            "`machines/radiomast` cffdf4e7、`machines/clocks` 1269f914、`main/shell` 4336bc18、`site/stair` 8e302456，和占用表的屏障 "
            + BARRIER + "。技检投过两次（04:55 node33、05:38 node39），节点都停了，没有回执；" + V["NODE_NOW"]))
line("- 机器：合用机只做轻活",
     "- 机器：合用机只做轻活（git、读写文件）；check.py、render.py、selfshots.py、delivery.py 一律投到各自的节点（`tools/nodejob.sh`）。"
     "每一单有时限（默认 1700 秒，到点自己停、回执照发；总监 de71fb58）。自查图各家在自己的节点上出，跟分支进 git。"
     "真机图归 s1（c319）：云端的游戏 11-16 03:15 在 node34 上跑通了，每批合并以后离线、真机各出一套看板图，评审要哪个机位找他。"
     + V["NODES"])
line("- 关口是一条命令，",
     "- 关口是一条命令，`tools/gate.sh <类别>/<包名> <提交>`，做包的人交付以前可以自己先跑（加 `--base <总装头>`）："
     "`tools/delivery.py` 八项（第一项 `shift` 就是 `tools/provenance.sh`，历史里有第 2 班的提交就退回）、`tools/checkall.py`"
     "（全部场景的 check.py）、动到的测试场景存的图逐像素核（`selfshots.py --verify`）。s2 一次合几个交付用 `tools/gatestack.sh`："
     "每个交付在它自己合进去的那棵树上过关口；图和交付的提交对得上、合进总装时已经被先进来的包改掉的，算过，记在“图的现状”，"
     "不算这个交付的账。交付的提交自己的图和自己的代码对不上的不收（不收只有代码、图以后补的交付）。一批合完以后跑 "
     "`tools/keptshots.py`：总装里存的图哪些已经不是现在的代码画出来的，点名重出。s2 合每个交付以前先把总装头合进自己的分支："
     "`delivery.py` 的 `scope` 拿交付和基比，基里没有交付的分支合过的总装提交，那些公共文件就算到交付头上（`machines/radiomast` "
     "二次交付头一回 `scope` 红就是这么来的；对着他合过的总装 53770c19 重核，过）。做包的人交付以前也先合总装头。")
line("- 待领（9 张，找总监助理 c320 领）：",
     "- 待领（5 张，找总监助理 c320 领；派卡的次序总监 05:24 定的：先第一批剩下的，再走查两张和导出一张，然后本人那一包照评审意见"
     "和真机看板打磨，最后第二批的四间房）：`machines/recorders`（总监让留给下一个交卡的机器岗）；"
     "`interiors/platevault`、`clockroom`（P3）；`interiors/astroroom`（P3，留给 sdome c328，照相仪交了再开）；"
     "`common/offline-sky`（P3，记在 s1 名下，做不做待定）。第二批七张是总监 11-16 05:24 立的，卡在 `plan/packages/`；其中走查两张、"
     "`sky/ridges`（05:29）、导出（05:46）和蓄电池室（06:03）派出去了（facade c321、a4 c323、comet c330、outb c340、stair c337）；"
     "第一批的 `machines/switchboard-boiler` 06:11 派给了 mast c346。")

# ---- the queue -------------------------------------------------------------------------------------
line("4. `main/shell`：",
     pick("4. `main/shell`：**已合并** f54bf237（合的是 4336bc18，顶替 70a1966a）。shell c325 把有效头 15b6cf2e 上没跑过的跑通，"
          "出了 29 个机位的图，在总装 8fcb3c0e 上面交。第 1 班留下的七条到这里都了了。",
          "4. `main/shell`：**已交付** 4336bc18（顶替 70a1966a；评审 c332 #16 过）。shell c325 把有效头 15b6cf2e 上没跑过的跑通，"
          "出了 29 个机位的图，在总装 8fcb3c0e 上面交。在关口上（叠着合在 s2 的分支上，f54bf237），技检等节点；它进了总装，"
          "第 1 班留下的七条就都了了。"))
line("- 第 3 班新到的交付，照到的先后：",
     "- 第 3 班新到的交付，照到的先后，" + pick("全部 **已合并**", "**已合并** 的") + "（括号里是合的那个提交）：`materials/panels` 打磨轮 a52bd566（b437a380）；"
     "`materials/brass-oldcopper-small` 打磨轮 ed7fd0c2（e0e4658d）；`materials/iron` 二次交付 c992a3ae（8567371a），补图 c676a8eb"
     "（4a6542c3）；`main/smalldome` 825ec1ef（ab28afba）；`site/terrain` 三稿和 `site/court` 打磨轮 8b7735eb（ca810cc1，一个提交两张卡）；"
     "`motion/loop` 和 `sky/tones` 40e27461（a7493ed5，一个提交两张卡）；`materials/snow` 3be01d94（eb997a4e）；`main/facade` 打磨轮第一批 "
     "167260ee（51947080）；`site/powerhouse` ff8ea061（5a0158ba）；`main/dome` ec9ac975（4734497f），卡 b1ee550e（529f72e9）；"
     "`materials/ashlar` 打磨轮 a494bb19（d308767b）；`props/lamps` 场地灯链 b5faa03a（546c070e）；`materials/iron` 三次交付 3387d99c"
     "（6a5cb30d）；`site/powerhouse` 二次交付 4b538dbe（a863dc2e）"
     + pick("；`site/mastbase` 和 `site/outbuildings` 064dbc57（69b57fe8，一个提交两张卡），卡 " + CARD + "（5c2b6ec9）；"
            "`machines/radiomast` 3b87af9d（cffdf4e7）；`machines/clocks` 7acc80db（1269f914）；`main/shell` f54bf237（4336bc18）；"
            "`site/stair` " + STAIR + "（8e302456）；`machines/radiomast` 二次交付 " + V["MAST2"] + "（d98865b7）；`sky/look` 的蓝调改动 "
            + V["LOOK"] + "（41e88d9d）；`main/dome` 二次交付 " + V["DOME2"] + "（ad0c352b）。", "。"))
if G:
    after("- 第 3 班新到的交付，照到的先后，", [
        "- **在关口上** 的，照到的先后（交付的提交来源都干净；已经叠着合在 s2 的分支上，技检过了一次推进总装，哪个不过退哪个）："
        "`site/mastbase` 和 `site/outbuildings` 69b57fe8（一个提交两张卡；卡上一处改动 5c2b6ec9）、`machines/radiomast` cffdf4e7、"
        "`machines/clocks` 1269f914、`main/shell` 4336bc18、`site/stair` 8e302456（他自己在 node4 上跑过关口，PASS）；"
        "s2 的占用表屏障 " + BARRIER + " 同一批。",
    ])
line("- 等【交付】再合：",
     "- 等【交付】再合："
     "`main/smalldome` 顶点 26、按环分层、素皮（sdome c328）、`site/powerhouse` 的两行小改"
     "（power c339：`build()` 不再自己挂炉火窗的内衬；先于窗的补件）、`materials/windows` 的内衬和炉火窗（chart c350，af4e2107 等上一条）、"
     "`site/terrain` 和 `site/court` 评审点的打磨（a4 c323，一次合、一次重画）、`main/facade` 的补图和撤占位墙（facade c321）、"
     "`sky/lights` 洗墙轮、两翼窗后 12 级、`OPEN_HALL` 和门后的临时光源（lights c331）、`props/ironwork` 打磨轮带入口两侧栅门的屏障"
     "（m3 c342）、`machines/clocks` 的小修和重出的 `v1_tower`、`tower_far`（clocks c345）、"
     "`site/cablecar`（cable c338）、`main/tower`（tower c327）、`motion/smoke`（a2 c322）。")
if not G:
    after("- 等【交付】再合：", [
        "- **已交付、排在这一批后面**：`materials/board` 07bf4808（a1 c324，11-16 06:30，分支 `cursor/c164-a1-board-f3-09d2`；来源干净；"
        "`renders/obs_mat_board/` 35 张，比选的 `obs_mat_board_ashlar_a`、`_ashlar_c` 各 9 张、`_windows_b` 10 张；他自己的关口 PASS，"
        "基 e5d14d2a）；`props/lamps` 的补交 066ecfab（lamps c341，06:33，分支 `cursor/c164-lamps-chain-f3-0dde`；来源干净；沿口矮灯 "
        "(60, 26) 压在管桥弯头上、撤了，场地共 25 盏；台阶脚的灯座随 stair 改到 y −3.0；场景加 V6 机位；48 张重画；他自己的关口 PASS，"
        "基 116c2e49）。",
    ])
line("- `motion/loop`（a2 c322）交付的时候 s2 一起改三处",
     "- `motion/loop` 交付的时候 s2 要改的三处 11-16 改了（fc997791，照 a2 给的补丁 `plan/packages/motion/loop-drivers.patch`）："
     "`build/place.py` 摆完场景就启动它登记的循环；`tools/check.py` 的 regen 里同样调一次，加 `motion` 一项；INTERFACE 第 2 节那一条。")
line("  - `main/massing.py`：",
     "  - `main/massing.py`：小穹顶的那一段 11-16 随 825ec1ef 删了，总装里只剩报时塔的白模（check.py 的 flatwall 黄就是它）；"
     "tower c327 的分支合过这个头（7ece55c8），他交付以后是空的 `build()`（A0 #359 第四条，总监试合过）。`site/ground.py` 11-16 "
     "随山体三稿删了（8b7735eb）。")
line("  - `props/instruments` 和 `site/outbuildings` 都进总装以后",
     "  - `site/outbuildings` " + pick("11-16 进了总装（064dbc57）", "11-16 交付了（69b57fe8，在关口上）")
     + "，带着气象站自己的 3 个展示实体。`props/instruments` 进来以后 outb c340 "
     "的平台上再摆 3 件（望远镜、百叶箱、日照计，模型是 props 的），他重出图；`obs_site_terrain` 的 `LINES` 带不带 props，"
     "三稿（8b7735eb）已经照 c229 #452、#469 和 c221 #497 说的加上了。")
line("  - 铁件和壳：",
     "  - 铁件和壳：c198 把 `IRON_HATCH` 改成只有一张盖板（5705d3a7，#513），壳的环梯栏板、钟室的百叶、缆车站的 `TIE`、"
     "子午仪小屋的盖板都跟着变，代码不用动。iron 二次、三次交付都进了总装（c992a3ae、3387d99c），壳的 29 张图是在 8fcb3c0e 上面出的。")
line("  - `site/mastbase`（c229）要先于",
     pick("  - `site/mastbase` 和 `machines/radiomast` 11-16 同一批进的总装，石座 064dbc57 在前，桅杆 3b87af9d 在后（c239 #520）。",
          "  - `site/mastbase` 和 `machines/radiomast` 11-16 都交付了，同一批过关口，石座合在前、桅杆合在后（c239 #520）。"))
line("  - 场地灯、管件、室外家具各有一个 `DRESS` 开关",
     "  - `lamps.DRESS` 11-16 开了（b5faa03a，总监 04:14）：总装里场地灯是摆着的，各包的测试场景不要再自己调 `lamps.site()`"
     "（同一处叠两件，c241 #530）。铁艺的 `ironwork.DRESS` 还关着；管件、室外家具进来的时候各带一个开关（`pipes.DRESS`、"
     "`furniture.DRESS`，默认关），测试场景要看就自己调 `pipes.fittings()`、`furniture.site()`，调之前看开关，开着就不再调。")
after("  - `lamps.DRESS` 11-16 开了", [
    "  - 门后的占位亮墙（`facade.SCREEN`，规矩在 `facade.screened()`）：" + pick("壳 11-16 进了总装，墙", "壳 11-16 在关口上；进了总装以后墙")
    + "照总监 03:44 的 D 留到 lights 给出 "
    "`OPEN_HALL`；撤墙（facade c321）和门后的临时光源（lights c331：墩东面前、两条侧廊，不加看得见的灯具）同一批进，"
    "只进一边门里是黑洞。星厅搬进来的时候 hall c348 把门洞那一处替身源 (16, 1, 0) 撤掉、换成自己的灯，同一次交付（总监 05:05）。",
    "  - 窗的内衬和电力房：`powerhouse.build()` 见到 `windows.line` 就自己挂炉火窗的内衬，别的包的局部场景不带 `mat_` 模型，"
    "十个场景 FAIL（chart c350 #58343）。power c339 的两行小改先进，再进窗的补件（总装里炉火窗改由 `windows.build()` 衬，"
    "同一块玻璃只衬一次）。",
    "  - 屏障（`B.BARRIER`，" + BARRIER_AT + "）只当关着的模型门的碰撞；头一处是入口两侧栅门的 12 格，随 m3 c342 的铁艺打磨轮进，"
    "他清 facade 的占位铁栏、放门扇、放屏障是同一步。",
])
print("top and queue done")

for part in ("status_edit5_rows.py", "status_edit5_tail.py"):
    exec(open("/tmp/c164_s2/" + part, encoding="utf-8").read())
