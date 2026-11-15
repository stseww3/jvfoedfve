"""One-off: STATUS.md after the batch of 11-16 03:30..03:50 (comet, brass polish, iron second delivery,
lights reviewed, domegear taken). Run from c164-realms/. Every swap must hit exactly once."""
import sys

PATH = "plan/STATUS.md"
with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

SWAPS = [
    # summary
    ("**汇总（s2 c318 更新，11-16 03:30）：共 59 张卡 —— 待领 9，制作中 28，已交付 2，已合并 9，已出图 2，暂过 2，已过审 4，退回 3。**",
     "**汇总（s2 c318 更新，11-16 03:50）：共 59 张卡 —— 待领 9，制作中 28，已交付 1，已合并 8，已出图 3，暂过 3，已过审 5，退回 2。**"),
    # what the third shift merged
    ("；`sky/lights` 在入口 B 下重出的图 5ba3b4b6。总装头 3c0f8e17（11-16 03:27）：21 个场景 check.py 0 失败。",
     "；`sky/lights` 在入口 B 下重出的图 5ba3b4b6；`sky/comet` 2d7c1c7d；`materials/brass-oldcopper-small` 打磨轮 ed7fd0c2；"
     "`materials/iron` 二次交付 c992a3ae，补图 c676a8eb。总装到 c676a8eb（11-16 03:46）：24 个场景 check.py 0 失败。"),
    # queue
    ("5. `sky/lights`：**已合并** b574cf75（合的是 8972aa88）；25 张图 1a530b6b（lights c331 补的）；交叉看 facade c321 过。"
     "立面换了入口以后 25 张全部重出，5ba3b4b6（合的是 a09556c5）。",
     "5. `sky/lights`：**已合并** b574cf75（合的是 8972aa88）；25 张图 1a530b6b（lights c331 补的）；交叉看 facade c321 过。"
     "立面换了入口以后 25 张全部重出，5ba3b4b6（合的是 a09556c5）。评审 cr2 c333 过（暂评）。"),
    ("7. `sky/comet`：等 comet c330 重新【交付】（跑过有效头 b3950eb4，出图）；7b7e168 不单独合。",
     "7. `sky/comet`：**已合并** 2d7c1c7d。comet c330 把有效头 b3950eb4 上没跑过的跑通、出了三个场景的 46 张图，"
     "重新交付 3493001a，顶替 7b7e168；交叉看 dome c326 过。"),
    ("- 第 3 班新到的交付，照到的先后：`materials/panels` 打磨轮 **已合并** a52bd566（合的是 b437a380）。",
     "- 第 3 班新到的交付，照到的先后：`materials/panels` 打磨轮 **已合并** a52bd566（合的是 b437a380）；"
     "`materials/brass-oldcopper-small` 打磨轮 **已合并** ed7fd0c2（合的是 e0e4658d）；"
     "`materials/iron` 二次交付 **已合并** c992a3ae（合的是 8567371a），补图 c676a8eb（合的是 4a6542c3）。"),
    ("、`materials/iron` 二次交付（m5 c352）、`materials/snow`（snow c336）",
     "、`materials/snow`（snow c336）"),
    ("先合哪个都行，图要在 iron 进来以后重出。",
     "先合哪个都行，图要在 iron 进来以后重出。iron 二次交付 11-16 进了总装（c992a3ae），壳在它上面出图。"),
    # rows
    ("| iron | P2 | 已合并 | m5 c352（接 c198） | 9f09b11 | `m5-b8436a3b-*.jpg`（9 张，离线图，旧，文件已清） | "
     "铸铁 11 角色 13 方块，场景 `obs_mat_iron`。二次交付 c198 在做",
     "| iron | P2 | 已出图 | m5 c352（接 c198） | c992a3ae | `renders/obs_mat_iron/`（14 张，离线图，node12 出，关口核过） | "
     "二次交付 11-16 合并（合的是 8567371a，关口过；补图 c676a8eb，合的是 4a6542c3：`plates_b` 里拍到旧铜，"
     "黄铜打磨轮刚把旧铜降了一级，重出这一张；14 张逐像素一致）：有效头 3c2120de 上停机期间写的那些 m5 c352 头一回跑通、出了图，"
     "对着图又改五处：细管一格一节、两头法兰；门的舷窗逐格重画、加铰链带；铸花板改成实心的钻石尖；舱盖去掉刷纹，侧边读成亮唇；"
     "格栅的交点降一级。用到铁件的各家代码不用改，拍到铁件的旧图过期（见“图的现状”）。细节在卡片“第三班”一节。"
     "交叉看点了 m3 c342，评审 c332 还没评。第一次交付 9f09b11 是第 1 班合并的。下面是第 1 班的记录："
     "铸铁 11 角色 13 方块，场景 `obs_mat_iron`。二次交付 c198 在做"),
    ("| brass-oldcopper-small | P1 | 退回 | m1 c335（接 c194） | 95e21ea8 | `renders/obs_mat_brass/`（25 张，离线图，node49 出，关口核过） | "
     "11-16 合并 bd7f25f9（合的是 a2370b00，关口过）",
     "| brass-oldcopper-small | P1 | 暂过 | m1 c335（接 c194） | ed7fd0c2 | `renders/obs_mat_brass/`（25 张，离线图，打磨轮的，node49 出，关口核过） | "
     "打磨轮 11-16 合并 ed7fd0c2（合的是 e0e4658d；关口过，25 张重出、逐像素一致）：评审 #8 退的三处改了，旧铜照总监定的甲降了一级。"
     "交叉看 a6 c334 过（#54802：黄铜板面是色阶第 3 级、亮边 4、暗边 1，和 props 模型的 `K.BRASS` 同一级；吊牌的链第 2 级；"
     "旧铜板面降到第 1 级，就是 props 的 `K.COPPER_D`；灯具、铁艺的小铜件照总监 #53866 留在第 2 级；没有要改的），"
     "评审 c332 复评还没回。第一轮：11-16 合并 bd7f25f9（合的是 a2370b00，关口过）"),
    ("| lights | P1 | 暂过 | lights c331（接 c220） | b574cf75 | `renders/obs_sky_lights/`（25 张，离线图，node45 出，入口 B 下重出的，关口核过） | "
     "11-16 合并（合的是 8972aa88，关口过）；",
     "| lights | P1 | 已过审 | lights c331（接 c220） | b574cf75 | `renders/obs_sky_lights/`（25 张，离线图，node45 出，入口 B 下重出的，关口核过） | "
     "评审 cr2 c333 过（暂评，#54984，11-16 03:47；记录在 `cursor/c164-cr2-f3-ccff` 583f4ebb，`S3-reviews-v4-cr2.md` cr2-#3）："
     "明暗光色 4，没有红线，`DRESS` 可以开。最弱三处：入口中拱的挡板比柱墩暗（12→14）；两翼窗后的 10 级照不暖石头（10→12，请总监定）；"
     "洗墙读不出（洗墙轮改成照壁柱）。待真机：窗后的光、洗墙。11-16 合并（合的是 8972aa88，关口过）；"),
    ("挪到了正对中拱），评审 cr2 c333 还没评。洗墙轮另交。",
     "挪到了正对中拱）。洗墙轮另交。"),
    ("| comet | P2 | 已交付 | comet c330（接 c230） | 7b7e168 | 图待补（三个场景 46 个机位） | "
     "第 3 班：7b7e168 不单独合，comet c330 把有效头 b3950eb4 跑过、出了图再重新【交付】。下面是第 1 班的记录：",
     "| comet | P2 | 暂过 | comet c330（接 c230） | 2d7c1c7d | `renders/obs_sky_comet/`（甲，16 张）、`obs_sky_comet_b/`（乙，15 张）、"
     "`obs_sky_comet_c/`（丙，15 张），离线图，node44 出，关口核过 | "
     "11-16 合并（合的是 3493001a，顶替 7b7e168；关口过，三个场景 46 张逐像素一致）：停机期间写的都跑通，卡上手算的数换成量的；"
     "V1、V2 读骨架；乙照预审重画成平顶截面；只动本卡的文件。`sight` 现在照 `comet.seen()` 核：整颗彗星都在车站让出的两块视野里。"
     "交叉看 dome c326 过（#54889：白模的大穹顶和缝是他现在的数；V2 里穹顶的肩线他量 36.6°，彗头 41.05°，高出 4.4°，"
     "和卡上的 36.6°、4.5° 对得上，下面第 1 班记的 36.1°、4.9° 作废；`comet.under_head()` 把半砖当整格，拿去量真穹顶会读成 36.9°，"
     "量白模不受影响；缝里 z 0.2..2.5 看得到整颗），评审 cr2 c333 还没评。三版选哪个等真机图，默认甲。下面是第 1 班的记录："),
    ("| domegear | P2 | 制作中 | m5 c352（接 c196；交了 iron 再开） | c7045d80（有效头） | — | 领卡 #345",
     "| domegear | P2 | 制作中 | m5 c352（接 c196） | 3f9b4142 | — | 第 3 班：m5 c352 11-16 03:39 领卡（#54689），"
     "分支 `cursor/c164-m5-domegear-f3-b9c1`，从有效头 c7045d80 起。下面是第 1 班的记录：领卡 #345"),
    # pictures
    ("下表是它说的（总装 42d7ef66，11-16 03:09：15 个场景 207 张，94 张还是现在的代码画出来的，113 张不是）。",
     "下表是它说的（总装 c992a3ae，11-16 03:43：19 个场景 267 张，123 张还是现在的代码画出来的，144 张不是；"
     "`obs_mat_iron` 的那一张随后补了，c676a8eb）。合进来一个包，拍到它的别家的图就过期：彗星重画以后天上有彗星的图都变，"
     "铁件、旧铜一改，拍到真楼的图都变。过期的图由作者下次交付时重出，评审等着看的单独补（INTERFACE 第 6 节）；"
     "评审评的是这个包自己，图是它交付时的样子，过期不耽误评。"),
    ("| `obs_main_facade`、`_a`、`_c`、`_nocrown` | 8、4、4、5 | 都对 | — |\n"
     "| `obs_mat_brass` | 25 | 都对 | — |\n"
     "| `obs_mat_panels` | 10 | 都对（打磨轮的） | — |\n"
     "| `obs_sky_lights` | 25 | 都对：42d7ef66 上有 20 张过期（立面换了入口），lights c331 全部重出，5ba3b4b6 进总装，关口核过 | — |\n",
     "| `obs_sky_comet`、`_b`、`_c` | 16、15、15 | 都对 | — |\n"
     "| `obs_mat_panels` | 10 | 都对（打磨轮的） | — |\n"
     "| `obs_mat_iron` | 14 | 都对（`plates_b` 在旧铜降级以后重出，c676a8eb，关口核过） | — |\n"
     "| `obs_mat_brass` | 25 | 18 张对；7 张过期（铁件二次交付进来以后）：`plates_a`、`plates_b`、`copper_twins`、`emblem`、"
     "`emblem_walk`、`emblem_close`、`roof_gutter` | m1 c335，评审要看再补 |\n"
     "| `obs_main_facade`、`_a`、`_c`、`_nocrown` | 8、4、4、5 | 全部过期（彗星、旧铜、铁件进来以后；交付时 21 张都对） | facade c321，下次交付或者评审要看的时候 |\n"
     "| `obs_sky_lights` | 25 | 3 张对；22 张过期（彗星、旧铜、铁件进来以后；5ba3b4b6 进总装时 25 张都对） | lights c331，随洗墙轮 |\n"),
    ("| `obs_props_ironwork` | 14 | 全部过期（画的是退回的旧件） | m3 c342，随打磨轮 |",
     "| `obs_props_ironwork` | 14 | 全部过期（画的是退回的旧件；铁件二次交付也进来了） | m3 c342，随打磨轮 |"),
    ("- 图待补（各家在节点上出，随【交付】进来）：彗星三个场景（46）、`obs_main_shell`（22）、`obs_site_stair`、`obs_mat_iron`、`obs_mat_snow`，"
     "以及各机械、道具、室内的测试场景。",
     "- 图待补（各家在节点上出，随【交付】进来）：`obs_main_shell`（22）、`obs_site_stair`、`obs_mat_snow`，"
     "以及各机械、道具、室内的测试场景。"),
    # waiting for the director
    ("- 入口三联里借给橙窗的那四格光留不留（`_lightkit.LENDS`，c220 #521，出图以后定）。",
     "- 入口三联里借给橙窗的那四格光留不留（`_lightkit.LENDS`，c220 #521，出图以后定）。\n"
     "- 两翼窗后的光（10 级）照不暖石头，升不升到 12（cr2 c333 评 lights，#54984，11-16）。"),
    # waiting for the lines
    ("到现在跑过并且交付了的：facade 入口轮、panels 打磨轮。",
     "到现在跑过并且交付了的：facade 入口轮、panels 打磨轮、comet、iron 二次交付、brass 打磨轮。"),
    ("- 等重新【交付】：`main/shell`（shell c325）、`sky/comet`（comet c330）。",
     "- 等重新【交付】：`main/shell`（shell c325）。"),
    ("- 等交叉看：`materials/brass-oldcopper-small`（a6 c334）、`materials/panels` 打磨轮（m3 c342）。"
     "等评审：panels 打磨轮、facade（review c332），lights（cr2 c333）。等打磨轮：brass（m1 c335：旧铜两种、整格嵌板、吊牌的链）。",
     "- 等交叉看：`materials/panels` 打磨轮、`materials/iron` 二次交付（都是 m3 c342）。"
     "等评审：panels 打磨轮、facade、brass 打磨轮（复评）、iron 二次交付（review c332），comet（cr2 c333）。"
     "lights 评审过了（暂评），洗墙轮在做（lights c331）。"),
]

for old, new in SWAPS:
    n = text.count(old)
    if n != 1:
        sys.exit(f"{n} times, not once: {old[:70]}")
    text = text.replace(old, new)

with open(PATH, "w", encoding="utf-8") as fh:
    fh.write(text)
print(f"{len(SWAPS)} swaps done")
