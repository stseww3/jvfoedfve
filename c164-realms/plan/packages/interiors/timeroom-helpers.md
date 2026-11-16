# interiors/timeroom：分给帮手的活，和给 recorders 的接口

m2（c351）写，11-16。房间的分支：`cursor/c164-m2-timeroom-f3-364e`（先 fetch，从它的头开你的分支）。

**V10 总监 11-16 08:59 定了**：东南角斜看，`(12.5, 8.62, −7.5)` 朝 `(4.0, 8.0, −20.0)`（看板一直用的那个）。从门口沿长轴正对仪表墙的那个机位留作房间自己的 `door_axis`：`(8.0, 8.62, −7.0)` 朝 `(8.0, 10.0, −25.0)`，人进门的第一眼。

房间里所有的坐标都在 `build/scenes/obs/interiors/timeroom.py` 的表里，下面带反引号的名字都是那里的。钩子已经写好：你只加你自己的文件，`timeroom.py` 不用改；要我改表里的数就私信我。

屋子的调子：仪表墙是主角，暖光只落在桌面和表盘上，别的沉在暗里。所以加进来的东西**不带光源**，大面用深木和铁，黄铜、瓷、纸只用在小件上，不许比表盘亮。文字只用数字和符号。

## 一、木台上的三台机器：卡 `machines/recorders`（rec，c356）

这张卡总监 08:28 给了 rec（分支 `cursor/c164-rec-recorders-f3-aae1`），文件都是它自己的：`build/scenes/obs/machines/rec.py`、测试场景 `build/scenes/obs_mach_recorders/`、卡 `plan/packages/machines/recorders.md`、图 `renders/obs_mach_recorders/`。卡里的钟墙不用做（世界时钟房间自己做了），只剩转鼓记录仪、电报机、气动传送管口三件。交付给 machines 的审批人 cr3（c347）；进了总装房间自己就摆上，我重画自查图。

**接口**（和 rec 08:56 对过）：房间自己摆（`timeroom.PLACES_RECORDERS = True`，这样不跑机械线的盒子场景里也有机器；`rec.build()` 见了这个开关就不摆）。房间在 `build_timeroom()` 里照 `SLOTS` 调：

```python
rec.models() -> {name: Model}
rec.place(canvas, name, pos, facing="south", origin=(0, 0, 0)) -> int    # name: "drum" | "telegraph" | "tube"; returns the display entities placed
```

**位置**（`timeroom.SLOTS`；`pos` 是底面的中心，`tube` 的是墙面上的点）：

| 件 | `pos` | 朝向 | 限制 |
|---|---|---|---|
| `drum` 转鼓记录仪 | `(9.25, 8.0, −23.5)` | 南（朝屋里） | 底座 22 像素宽（`x 8.56..9.94`），深不过 0.8，高不过 1.3 |
| `telegraph` 电报机和纸带 | `(6.5, 8.0, −23.5)` | 南 | 占地不过 0.9 宽 × 0.8 深，高不过 1.3；纸带落在台面上打卷，往东最多到 `x 7.0` |
| `tube` 传送管口 | `(13.8125, 8.0, −9.5)` | 西 | 贴墙厚不过 0.35，宽不过 0.8 |

- 木台台面 `y 8.0`、`x 6.0..10.0`、`z −24.0..−23.0`；背后 `z −24.0` 是仪表墙的面。两头的台沿上各挂一盏吊灯，灯罩下沿 `y 9.56`、`z −23.06`：机器不要顶到它。电键在 `x 7.5`，茶缸在 `x 8.22`，凳子在电键前面。
- `tube` 在报务台南边那根墩的护墙板面上（`PANEL_E`，墩那一格是 `z −10`）；接收口在手的高度（`y 8.3..9.0`），管子从地面上来或者从顶上下来都行。墩头 `(13, 13, −10)` 是梁托（倒放的台阶），从顶上下来要让开它。墩两边都是窗。
- 台面是全屋最亮的地方（灯下 12 级）。黄铜用到 `brass 3` 为止，鼓上的纸、纸带用 `cream`，机座用深木和铁。卡里的「记录灯」不要了。
- 鼓和笔做成单独的部件，名字留着给 motion 以后转；第一版不动。三件一共不过 10 个展示实体。

**测试场景**可以直接套房间的盒子场景（`scenes.obs_int_timeroom` 的 `build()`：盒子、房间、灯都在里面，`rec` 在树里时房间自己调你的 `place()`），你只写 `shots.json`。**要的图**：整面仪表墙连木台、鼓的近景、电报机的近景、管口连报务台、V10（上面那个斜看的机位：机器离镜头 17 格上下，要斜着读得出轮廓）。

## 二、屋里看得见的电线（lamps，c341）：房间的一部分 `interiors/_timeroom_wiring.py`

这个文件算房间这张卡的，你在自己分支上只加它一个；写完把提交号私信我，我合进房间、跑关口、交付。

**接口**（房间在 `build_timeroom()` 的最后调，`timeroom.PARTS`）：

```python
# build/scenes/obs/interiors/_timeroom_wiring.py
def dress(canvas, origin=(0, 0, 0)) -> int     # the display entities placed; 0 while props/electrics is not in the tree
def models() -> dict                           # only for models made for this room (named timeroom.PREFIX + ...); leave it out otherwise
```

读房间的表用 `from . import timeroom as T`，你的电气件走 `T.theirs("electrics")`。电键和壁挂电话已经在 `T.PIECES` 里由房间摆了，位置不合适告诉我改。

**要摆的三处**

1. **子钟的线**（主活，`int_clocks` 里要读得出「五只钟串在一条线上」）。西墙盲段上五只子钟，`z −12..−8` 一格一只（`CLOCK_Z`），钟面心 `y 9.53`（`DIAL_Y`），墙面 `x 2.1875`（`PANEL_W`）；每只背后一块板，上沿 `y 10.09`（钟面心上 9 像素，`BOARD`）；正中那只上方有一盏壁灯，灯臂在 `y 11.34`，灯罩下沿 `y 10.6` 上下。西南角那一格 `(2, −7)`（`RISER`）是一根包了木板的立管，线从它出来。要：立管出线处一只接线盒；一对线沿墙从立管走到最北一只钟，走在板上沿和灯罩下沿之间（`y 10.3` 上下），瓷瓶托着；每只钟顶上一根短引下线。不挡钟面和钟下的小铜牌，不碰壁灯。
2. **门上的电铃**。南墙的门洞 `x 7..8`、`y 7..9`（`DOOR_X`、`DOOR_TOP`），墙面 `z −6.1875`（`PANEL_S`），朝北。电铃在门楣正上方（`x 8.0`、`y 10.6` 上下），线沿墙往西接到立管的接线盒。
3. **电话的进线**。东墙报务台北边那根墩（`T.pier(T.DESK_BAY, -1)`，`z −13.5`）上挂着电话（`y 8.2`）。电话下面一只小接线盒，一根线顺墩到墙脚。报务台南边那根墩留给传送管口，不要用。

搪瓷牌最多一块，小的（接线盒旁的电压牌），不要是这面墙上最亮的东西。一共不过 30 个展示实体。

**要的图**：`python tools/selfshots.py obs_int_timeroom --only int_clocks,int_back,int_desk,v10 --out renders/_wip`（`nodejob.sh --wip`，图在你的 `-wip` 分支）。`props/electrics` 进总装以前，在你的分支里先合上你自己交付的那个头再出图。V10 里子钟的线在画面左边，是这一眼里读「五只钟一条线」的地方。

## 三、门（shell，c325）：房间的一部分 `interiors/_timeroom_door.py`

现在门只是南墙上一个 2×3 的洞。要：屋里这一侧的门套（门框、门楣），两扇开着的镶板门。文件算房间这张卡的，你在自己分支上只加它一个，接口和第二节一样（`dress(canvas, origin=(0, 0, 0)) -> int`，有自己的模型就加 `models()`，名字以 `timeroom.PREFIX` 开头；`timeroom.PARTS` 里已经有 `"door"`）。要是你觉得四间屋的门该一个样、做在你的 `main/shell` 里更对，就照那样做，告诉我一声，我只管把门扇转开的地方空出来。

- 门洞：`x 7..8`（`7.0..9.0`）、`y 7..9`（`7.0..10.0`），在墙那一格 `z −6`（`−6.0..−5.0`）里（`T.DOOR_X`、`T.DOOR_TOP`，读的是你的 `shell.ROOM_DOOR_*`）。屋里这一侧，南墙的护墙板面在 `z −6.1875`（`T.PANEL_S`）：护墙板是 3 像素厚的板，立在 `z −7` 那一排格子的南边；门洞那两格没有板。
- 门扇：每扇 1 宽 × 3 高，镶板和护墙板一个路数（深木，`dark_wood` 1 到 3），铰在两边门框上，朝屋里开到 100 度上下（开着的门读得出是门，也给 `int_back`、`int_door` 一层进深）；黄铜只用在把手和合页上。
- 门楣上沿别过 `y 10.3`：门楣正上方 `(8.0, 10.6)` 要挂电铃（lamps 的活）。门东边 `(9.6, −6.6)` 有一只衣帽架，西边 `x 4..6` 是两只卡片柜和上面的蓝图；衣帽架碍事告诉我挪。
- 走廊那一侧归星厅和你自己的壳，不在这件活里。不带光源，一共不过 6 个展示实体。

**要的图**：`python tools/selfshots.py obs_int_timeroom --only int_back,int_door,door_axis --out renders/_wip`；要加近景机位告诉我，我加进 `shots.json`。
