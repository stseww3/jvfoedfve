#!/usr/bin/env python3
"""STATUS.md, the batch of 11-16 07:20: run in c164-realms/. Nothing is written unless every anchor is
found exactly once.

    python3 /tmp/c164_s2/status_edit6.py <values.py> [--write]

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
LOOP2, COMET2, STAIR2, V6C = V["LOOP2"], V["COMET2"], V["STAIR2"], V["V6C"]

# ---- the bullets at the top ------------------------------------------------------------------------
P10 = "- 第 3 班到现在进总装的，都过了关口，照进来的先后："
swap(P10, "；`main/dome` 二次交付（地图用乙）2a26eeaa。s2 自己改的公共文件：",
     "；`main/dome` 二次交付（地图用乙）2a26eeaa；`materials/board` f005ba2d；`props/lamps` 补交 8956db05；`materials/iron` 打磨轮 "
     "200e405b；`motion/loop` 跟进 " + LOOP2 + "；`sky/comet` 打磨轮 " + COMET2 + "；`site/stair` 补图 " + STAIR2
     + "。s2 自己改的公共文件：")
swap(P10, "占用表的屏障 d0e71efd；", "占用表的屏障 d0e71efd；骨架 `V6` 的看向 " + V6C + "；")
swap(P10, "总装到 2a26eeaa（11-16 06:27）：46 个场景 check.py 0 失败。",
     "总装到 " + HEAD + "（" + WHEN + "）：" + SCENES + " 个场景 check.py 0 失败。")
after("- 总装是 `cursor/c164-assembly-fable-a9f5`", [
    "- **头号风险（总监 11-16 06:54）：成品进不进得了 Realms，还没有答案。** 蓝调的天靠两个注册表文件（自定义生物群系、时间线），存档因此带"
    "「实验性」标记，Realms 不支持；自己上传的存档，资源包 Realms 发不发给进来的人也不知道。outb c340 做两个试传存档请管理员传，"
    "a2 c322 备一套不带注册表文件的天（`sky/safe-look`）。**管理员没答以前两条路都留着，设计的天照常做。** 全文在“总监定过的 / 11-16”"
    "和总监桌上（`roles/A0-director.md` 第 5 节第 0 条）。",
])
P31 = "- 第 3 班新到的交付，照到的先后，"
swap(P31, "；`main/dome` 二次交付 2a26eeaa（ad0c352b）。",
     "；`main/dome` 二次交付 2a26eeaa（ad0c352b）；`materials/board` f005ba2d（07bf4808）；`props/lamps` 补交 8956db05（066ecfab）；"
     "`materials/iron` 打磨轮 200e405b（99dc8afa）；`motion/loop` 跟进 " + LOOP2 + "（10055417）；`sky/comet` 打磨轮 " + COMET2
     + "（a5ddf7bd）；`site/stair` 补图 " + STAIR2 + "（769e2fb5）。")
drop("- **已交付、排在这一批后面**")
swap("- 待领（5 张，找总监助理 c320 领；", "第一批的 `machines/switchboard-boiler` 06:11 派给了 mast c346。",
     "第一批的 `machines/switchboard-boiler` 06:11 派给了 mast c346。总监 06:54 另加一张 `sky/safe-look`（a2 c322，见头号风险）。")
print("top done")

# ---- the rows --------------------------------------------------------------------------------------
row("common", "skeleton（骨架）", commit=V6C,
    front="11-16 06:52 总监定 **`V6` 的看向往右转四度半**（review c332 评审 #20 第 3 处；总监桌上 4883c5a7）：站位不动，看 (74.4, 8.0, 33.2)"
          "（原来 (76.5, 8.0, 32.5)）。原来切在左边框上的是下平台 (79.5, 10.5) 那盏路灯；现在它的球罩和托盘在框外，烟囱完整，沿口 (60, 18) "
          "墩帽上的灯还在画里（" + V6C + "；看板机位表 `tools/win/shots/obs-board.json` 和两个读它的场景的 `shots.json` 跟着改了；"
          + V["V6_PICS"] + "）。电力房测试场景的 `stair_south` 是包里写死的数，没跟着动，power c339 下次交付改成读 `S.V6`。")
row("materials", "board", state="已出图", commit="f005ba2d",
    pics="`renders/obs_mat_board/`（35 张）、`obs_mat_board_ashlar_a/`、`_ashlar_c/`（各 9 张）、`obs_mat_board_windows_b/`（10 张），"
         "离线图，交付时关口核过，合进总装时 4、0、0、0 张对（蓝调的天先进的）",
    front="11-16 合并 f005ba2d（合的是 07bf4808；关口过：delivery 八项没有黄，63 张和交付的提交对得上）。交叉看 ashlar c353（等）；"
          "评审 review c332 在看。",
    swap=[("排在这一批后面过关口。", "")])
row("materials", "iron", commit="200e405b",
    pics="`renders/obs_mat_iron/`（14 张，离线图，打磨轮的，node6 出，交付时关口核过，合进总装时 1 张对）",
    front="打磨轮 11-16 合并 200e405b（合的是 99dc8afa，分支 `cursor/c164-m5-iron-f3-b9c1`；关口过：14 张和交付的提交对得上）：评审 #15 留的"
          "那一条办了，铆接板（`IRON_RIVETED`）的拉丝痕手排，六个变体（原来三个），痕迹离铆钉和边框各留两像素；测试场景的 `write_pack` "
          "加了 `sky.pack`。**评审 c332 #21 过**（#63284：质感 4、风格 4，没有红线）；交叉看 m3 c342 过（#63464：和铁艺件的板、铆钉同色"
          "同大小，铁艺件没有直接用这个方块）。")
row("sky", "comet", commit=COMET2,
    pics="`renders/obs_sky_comet/`（甲，16 张）、`obs_sky_comet_b/`（乙，15 张）、`obs_sky_comet_c/`（丙，15 张），离线图，打磨轮时在带蓝调的天的"
         "总装上重画的，" + V["COMET_PICS"],
    front="打磨轮 11-16 合并 " + COMET2 + "（合的是 a5ddf7bd，分支 `cursor/c164-comet-f3-793d`；" + V["COMET_GATE"] + "）：评审 cr2-#4 第 2 条办了，"
          "甲的尘尾在前、向北弯，离子尾更淡、笔直；尘尾收细，离桅杆灯仍是 2.1°；`under_head()` 按半格量；46 张重画。**定版甲（总监 "
          "#56164），光线锁 blue（#56751）。** 离线图上三种光里彗核都是天上最亮的一点（blue：彗核 1.00、紧挨的彗发 0.77、最亮的星 0.60；"
          "deep：1.00、0.84、0.76；glow：0.93、0.69，没有看得见的星；星图转角 133 以后彗头 6.8° 内没有星；comet #63356），真机 deep 等 "
          "s1 的图再核。")
row("sky", "look",
    front="交叉看 comet c330 过（#63356：对彗星没有妨碍）。")
row("site", "stair", commit=STAIR2,
    pics="`renders/obs_site_stair/`（12 张）、`obs_site_stair_noband/`（5 张）、`obs_site_stair_nolamps/`（5 张），离线图，补图时在总装 18c28fb9 "
         "上重画的，" + V["STAIR2_PICS"],
    front="补图 11-16 合并 " + STAIR2 + "（合的是 769e2fb5：代码没动，22 张在总装 18c28fb9 上重画；" + V["STAIR2_GATE"] + "）。交叉看 cable c338 "
          "在量和缆车站的接缝（#62910）。")
row("site", "mastbase",
    front="交叉看 mast c346 过（#63001：座顶 `TOP` 就是桅杆的 `BASE_Y`，四腿落在 `LEGS` 四格中心，拉索下端读 `GUY_ANCHORS`，馈线读 "
          "`ANTENNA_HOOK`；柱和锚都低于 V1 的视线）。")
row("site", "outbuildings",
    front="交叉看 lamps c341 过（#63113：小屋、水塔两处灯位和他的表对得上，各 7 级；另两点不属灯位：`tower_near`、`v1_arrival` 里有游戏"
          "自带的日月方块，`write_pack` 没加 `sky.pack`，补图时改）。")
row("main", "shell",
    front="交叉看 hall c348 过（#64022：梁、母钟座、墩脚篦子、回廊灯、环梯的外栏板和吊杆都和星厅的东西让得开；两件不归壳：东墙三扇"
          "大窗从屋里看还是亮橙，等 chart c350 的窗衬；门洞 (16, 1, 0) 的替身源由 lights 的 d78e4151 撤，和 hall 的交付同一次合）。")
row("main", "dome",
    front="二次交付评审 c332 看过重画的 `v1`、`v2_axis`：和 #14 看过的乙一样，结论不变，不另打分（#63284）。")
row("motion", "loop", commit=LOOP2,
    pics="`renders/obs_mot_loop/`（24 张）、`obs_mot_load/`（4 张），离线图，跟进时在总装 5959264e 上重画的，" + V["LOOP_PICS"] + "；会动的等真机看",
    front="跟进 11-16 合并 " + LOOP2 + "（合的是 10055417，分支 `cursor/c164-a2-loop-f3-695d`；" + V["LOOP_GATE"] + "）：真机验收脚本"
          "（`motion/_onreal.py` 和两个场景的 `onreal.py`，给 s1 出真机图时的 `--after` 用；离线 14 项自检）；`MK.crank` 加 `start=`"
          "（dome c326 的配汽偏心杆等它；不写 `start` 时输出逐字节不变）。",
    swap=[("跟进在新分支 `cursor/c164-a2-loop-f3-695d`（aide #62203）；", "")])
row("props", "lamps", state="已过审", commit="8956db05",
    pics="`renders/obs_props_lamps/`（26 张）、`obs_props_lamps_site/`（16 张）、`obs_props_lamps_site_nearpair/`（6 张），离线图，补交时重画的，"
         "交付时关口核过，合进总装时 1、0、0 张对",
    front="补交 11-16 合并 8956db05（合的是 066ecfab；关口过：48 张和交付的提交对得上）：V6 定在大台阶南半边以后，沿口矮灯 (60, 26) 的球"
          "压在管桥弯头上，撤了（`BRIDGE_CLEAR = 7`），场地共 25 盏；台阶脚的灯座随 stair 改到 y −3.0；场景加 `v6` 机位。**评审 review "
          "c332 #20 过**（#62770：4/4/3/4/4，没有红线，甲比乙好；记录 `S3-reviews-v4.md` #20）。留给下一轮、不卡合并的两条：乳白球罩在"
          "游戏里不亮（总监 06:52：a6 c334 先改入口两盏壁灯做试验件，看了再定全族）；地上没有光圈（归 lights 和 cr2）。交叉看 power c339（等）。")
lo, hi = section("sky")
after("| ridges | ", [
    "| safe-look | P1 | 制作中 | a2 c322 | — | — | 总监 11-16 06:54 加，头号风险的备用方案，在 a2 手上排最前：一套 Realms 能用的天，"
    "不带任何注册表文件——原版生物群系（`fillbiome`）、锁住的原版时间和天气、资源包、块光。先交一页方案（彗星在正西 41° 要锁在哪一刻，"
    "原版里大约是 20800，深夜；两三个候选各要 s1 的真机 V1、V2；丢了什么、拿什么补）。卡片文件还没有，规格在总监桌上第 5 节第 0 条"
    "（4883c5a7）。设计的天照常做。 |",
], lo, hi)
print("rows done")

# ---- the director's rulings --------------------------------------------------------------------------
lo, hi = section("总监定过的")
after("- 06:08 **成品地图的设置九条**", [
    "- 06:40 前后 **头号风险：成品进不进得了 Realms**（outb c340 查出来的，还没有答案；全文在总监桌上第 5 节第 0 条，4883c5a7）。蓝调的天"
    "写在两个注册表文件里：自定义生物群系 `obs_blue`（天色、雾色、云、星的亮度、天光和块光的颜色）和时间线 `obs_looks`（月亮的角度"
    "和月相；彗星就是月亮的贴图，定在正西 41°）。26.3 里不是原版包带来的注册表文件会让存档带「实验性」标记，Realms 不支持实验性功能；"
    "上传会被拒还是传上去不生效，没人试过。第二个不知道：自己上传的存档，资源包（`resources.zip`）Realms 发不发给进来的人，不发的话"
    "整套贴图和模型都没有。在做的三件：outb 做两个最小的试传存档（T1 带两个注册表文件，T2 一个不带；放 `cursor/c164-dist-<后缀>`），"
    "总监转给管理员各传一次；导出工具留一个不带这两个文件出包的开关；a2 c322 备一套 Realms 能用的天（`sky/safe-look`）。问过管理员："
    "甲 成品上 Realms、天用备用的那一套；乙 保住设计的天、成品是可下载的存档或自己的服务器。**他没答以前两条路都留着，设计的天照常做。**",
    "- 06:48 **洗墙灯定 10 级**（cr2 c333 问；lights c331 的 8、10、12 三张并排）：8 级时两翼的三道竖光带在 V3 里看不出来，12 级和亮窗"
    "窗后一样亮、墙和窗糊成一片。立面上的三级是门洞 14、亮窗窗后 12、洗墙 10；卡上的上限从 8 改到 10，不许再高。",
    "- 06:52 **乳白球罩在游戏里不亮：先做试验件**（review c332 评审 #20）。真机 V3、V4 里球罩 0.39 到 0.52，它照的墙 0.30 到 0.38；原因是"
    "游戏给展示实体按朝向打暗（朝上 ×1、南北 ×0.74、东西 ×0.50、朝下 ×0.40），贴图救不了。a6 c334 先改入口两盏壁灯：球罩从哪一面看"
    "都是一个亮度，0.75 上下，高过旁边被照亮的墙一倍；真机 V2、V3、V4 和现在并排，总监看了再定全族；排在 a6 的 furniture 交付之后。"
    "三条路让 a6 比：球罩改方块模型、压扁建模让面烘焙成「上」、`text_display` 加圆球字形。同一份评审的“地上没有光圈”归 lights 和 "
    "cr2：光源降到杆的中段或灯脚旁加一格，灯脚旁要比两对灯中间亮一倍半以上。",
    "- 06:52 **V6 的看向往右转四五度**（评审 #20 第 3 处）：站位不动，看点 (76.5, 8.0, 32.5) → (74.4, 8.0, 33.2)；切在左边框上的那盏路灯"
    "整个让出去，烟囱不许被切，右边露台墩帽上那盏灯留在画里；以出图为准，cr2 核图。s2 改了骨架（" + V6C + "）。",
], lo, hi)

lo, hi = section("成品地图交付清单")
after("存档导出成成品地图时要带上的设置", [
    "",
    "**头号风险（总监 11-16 06:40 前后）：成品进不进得了 Realms、资源包 Realms 发不发，都还不知道**（见“总监定过的 / 11-16”；等管理员试传 "
    "T1、T2）。下表“时间”“sky 的收尾”两行靠的就是那两个注册表文件；要是走备用的天，这两行跟着 `sky/safe-look` 改。",
], lo, hi)

lo, hi = section("等总监定的")
after("## 等总监定的", [
    "",
    "- **成品上 Realms（天用备用的那一套）还是保住设计的天（成品是可下载的存档或自己的服务器）**：等管理员答；要看的是他试传 T1、T2 的"
    "结果、a2 的一页方案和 s1 的真机 V1、V2（06:54）。",
    "- 乳白球罩：入口两盏壁灯的试验件过不过、全族改不改（a6 c334；真机 V2、V3、V4 和现在并排；评审 #20）。",
])
i = find("- 东缘要不要单开稀栅杆的角色")
if i is not None and lines[i - 1] == "" and lines[i - 2].startswith("- 乳白球罩"):
    del lines[i - 1]
swap("11-16 定掉、从这里拿走的（全文在“总监定过的 / 11-16”）：", "V6 的站位、",
     "V6 的站位和看向（06:52，左边那盏路灯让出画面）、洗墙灯（10 级）、")

lo, hi = section("等各线报的")
line("- 等交叉看：",
     "- 等交叉看：ashlar 打磨轮（facade c321，补图时看）、lamps 灯链（a4 c323，重画时看）、radiomast（outb c340）、clocks（tower c327）、"
     "stair（cable c338，在量接缝）、dome 的默认乙（shell c325）、board（ashlar c353）、lamps 补交（power c339）。11-16 早上到了的："
     "mastbase（mast c346 过）、outbuildings（lamps c341 过）、shell（hall c348 过）、sky/look（comet c330 过）、iron 打磨轮（m3 c342 过）。"
     "等评审：review c332：board；cr2 c333：mastbase、outbuildings、stair 第二版、look 的蓝调改动、comet 打磨轮、loop、tones（正式评）、"
     "改了看向的 `v6`（两张）；powerhouse 在 `FIRE` 打开以后照 V6 复评（到时报 cr2）。", lo, hi)
swap("- 说了要交、等着的：", "lights c331 的洗墙轮、两翼 12 级、`OPEN_HALL` 和门后的临时光源（和 facade 撤墙同一批）；",
     "lights c331 的洗墙轮（洗墙 10 级）、两翼 12 级、`OPEN_HALL` 和门后的临时光源（和 facade 撤墙同一批）；门洞替身源的撤除（lights 的 "
     "d78e4151）和 hall c348 的星厅同一次合；")
print("tail done")

# ---- the pictures ------------------------------------------------------------------------------------
lo, hi = section("图的现状")
line("| `obs_main_shell` | 29 |", "| `obs_main_shell` | 29 | 交付时都对；合进总装时 17 张对、12 张过期，蓝调的天以后更少 | shell c325 |", lo, hi)
line("| `obs_site_stair`、`_noband`、`_nolamps` | 12、5、5 |",
     "| `obs_site_stair`、`_noband`、`_nolamps` | 12、5、5 | 补图（769e2fb5）在总装 18c28fb9 上重画的；" + V["STAIR2_TABLE"] + " | — |", lo, hi)
line("| `obs_props_lamps`、`_site`、`_site_nearpair` | 26、15、6 |",
     "| `obs_props_lamps`、`_site`、`_site_nearpair` | 26、16、6 | 补交（066ecfab）时都对；合进总装时 1、0、0 张对；`_site` 的 `v6` s2 "
     "随骨架重画了 | lamps c341 |", lo, hi)
line("| `obs_sky_comet`、`_b`、`_c` | 16、15、15 |",
     "| `obs_sky_comet`、`_b`、`_c` | 16、15、15 | 打磨轮（a5ddf7bd）在带蓝调的天的总装上重画的；" + V["COMET_TABLE"] + " | — |", lo, hi)
line("| `obs_mat_panels`、`obs_mat_iron` | 10、14 |",
     "| `obs_mat_panels` | 10 | a494bb19 时都对 | — |", lo, hi)
after("| `obs_mat_panels` | 10 |", [
    "| `obs_mat_iron` | 14 | 打磨轮（99dc8afa）时都对；合进总装时 1 张对 | m5 c352 |",
    "| `obs_mat_board`、`_ashlar_a`、`_ashlar_c`、`_windows_b` | 35、9、9、10 | 交付（07bf4808）时都对；合进总装时 4、0、0、0 张对 | a1 c324 |",
    "| `obs_mot_loop`、`obs_mot_load` | 24、4 | 跟进（10055417）在总装 5959264e 上重画的；" + V["LOOP_TABLE"] + " | — |",
], lo, hi)
lo, hi = section("图的现状")
drop("| `obs_mot_loop`、`obs_mot_load` | 24、4 | 全部过期", lo, hi)
lo, hi = section("图的现状")
swap("**11-16 这一批以后，拍到天或者大穹顶的存图全部过期。**", "总装现在存着 46 个场景的图。", "总装现在存着 49 个场景的图。")
print("pictures done")

# ---- the count -------------------------------------------------------------------------------------
states = ["待领", "制作中", "已交付", "已合并", "已出图", "暂过", "已过审", "退回"]
count = {s: 0 for s in states}
cards = 0
for ln in lines:
    m = re.match(r"^\| [^|]+ \| [^|]+ \| ([^| ]+) \| ", ln)
    if m and m.group(1) in count:
        count[m.group(1)] += 1
        cards += 1
i = find("**汇总（s2 c318 更新，")
if i is not None:
    lines[i] = ("**汇总（s2 c318 更新，" + WHEN + "）：共 " + str(cards) + " 张卡 —— "
                + "，".join(f"{s} {count[s]}" for s in states) + "。**")
print("cards", cards, count)
if cards != 67:
    errors.append(f"{cards} cards counted, not 67")

if errors:
    print("NOT WRITTEN:")
    for e in errors:
        print("  ", e)
    sys.exit(1)
if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(lines))
    print("written")
else:
    print("dry run: all anchors found")
