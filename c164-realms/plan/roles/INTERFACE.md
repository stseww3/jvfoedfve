# 接口：各包怎么接进总场景和总资源包

状态：**第二版，可用。** 拿合并钥匙的人（S2）维护。框架代码已在总装分支，`obs` 总场景能从头生成
（`build()` + 资源包 + 导出都通），`tools/check.py` 已可用。有异议私信 S2（现在是谁看 `plan/ROSTER.md`）。

对接只靠四样，都由 S2 维护：**色板** `build/scenes/obs/common/palette.py`、**占用表** `common/blocks.py`、
**骨架** `common/skeleton.py`、**本接口**。要改前三样，私信 S2 提，A0 批。

第二版相对第一版的改动（都不破坏已写的代码）：加了 `motion` 类别；`sky` 挪到最后铺；包内顺序用 `ORDER`；
`build()` 可以带有默认值的额外参数（`version=`）；检查脚本的用法和查什么（第 6 节）；光线版本靠时间选（第 3 节）。

11-14 补充（也不破坏已写的代码）：格和点的约定（第 2 节）；materials 和 props 的公用底座已在总装，例子换成真的包（第 2 节）；
云的五个方块归 sky 画、占位怎么算（第 4 节）；合并前 S2 还跑 `tools/delivery.py`，二进制文件一律拦（第 6 节）。

11-14 第二次补充（已交付的包不用改）：没写时间的机位，离线和真机两个出图工具都按 14000 拍（第 3 节）；测试场景也查地盘和前缀，
名字不合格式的可以写 `CATEGORY`，没有模型的场景不用写 `props.py`，正俯视的机位怎么写（第 5 节）；检查脚本加了 refs、flatwall 两项，
entities、views 多报几样（第 6 节）。

11-14 第三次补充（A0 的 v4，群 #17613、#17696）：自查图放 `renders/<场景名>/`，跟着分支进 git（第 5、6 节）。

11-14 第四次补充（管理员定，A0 #18142、#18472、#18530）：**出图只在管理员电脑上，云端一律不出图。** 图在电脑上用
`tools/selfshots.py --out` 出，经收图夹回云端，`--take` 落进自己分支的 `renders/<场景名>/`（第 5 节）；合并关口的逐像素核对
也在电脑上跑，云端只做不出图的检查（第 6 节）。已经在 git 里的图照用：电脑和云端出的是同一份像素（两边逐像素比过）。
（这一条 11-16 起作废，见下面 11-16 的补充。）

11-15 补充（A0 #304、#357、#365）：骨架里 `S.V1` 抬头，多了锁定机位 `S.V2`、`S.V7`；测试场景拍这几个机位照骨架的数写，
`check.py` 的 views 会点出站在锁定机位上、却看别处的机位（第 5、6 节）。V1 的取景规矩换了：“棚可以占画面上面八分之一”
（`V1_FRAME`）作废，改成车站让出一块视野 `S.V1_CLEAR`，`check.py` 的 sight 照新的量（第 6 节）。行星仪环面降到 y 7.5。
雪（`SNOW`、`SNOW_LAYER`）从原版名单挪进重画名单，色阶 `snow`。

11-15 第二次补充（A0 #388、#442、11-15 19:10 两条拍板）：车站让出的视野改了，`S.V1_CLEAR` 从 55° 抬到 **61°**（画面正上方的边），
不再留半度；北边另加彗星那一块 `S.V1_COMET`（正西偏北 15° 以内、仰角 35° 到 61°），两块里有车站的东西都判 FAIL；
主楼南端到偏南 70° 之间（画面左边三分之一）雨棚底下不立通高的柱，sight 报 WARN（第 6 节）。`S.in_v1_clear(x, y, z)`
两块都算。骨架多两个数：纬度 `S.LATITUDE = 45`（大望远镜、子午仪、浑天仪的极轴读它），全场的钟点 `S.CLOCK = (7, 55)`
（塔钟、母钟读它，世界时钟从它推时差；报时球在半杆）。环梯从帽的北面出来、逆时针转：`S.RING_STAIR` 里的 `turn`、`exit`。

11-15 第三次补充（总监 20:47 拍板）：全场一个风向，北风，从北往南吹。骨架里三个名字：`S.WIND_FROM = "north"`（风从哪边来）、
`S.WIND_TO = "south"`（往哪边吹，和 `facing` 用的是同一套词）、`S.WIND = (0, 0, 1)`（顺风走一格的 (dx, dy, dz)）。
风向标的尾朝 `WIND_TO`，旗和风向袋往 `WIND_TO` 飘，烟和汽往 `WIND_TO` 偏一点；风杯怎么转不管风向。各包读这三个名字，不自己写方向。

11-16 补充（第 3 班；总监的 `COMMON.md` 第 0 节）：**离线图各人在自己的节点上出**，管理员的电脑不再用，第 5 节出图的四步、
第 6 节“在电脑上逐像素核”都换成了节点上的做法。关口成了一条命令 `tools/gate.sh`，交付以前可以自己先跑；`tools/delivery.py`
多了第一项 `shift`（历史里有第 2 班的提交就退回，`tools/provenance.sh`）；多了两个一趟跑完的工具：`tools/checkall.py`
（全部场景的 check.py）、`tools/keptshots.py`（存的图哪些已经不是现在的代码画的）。消息一律私信（第 6 节）。已交付的包不用改。

11-16 第二次补充（`motion/loop` 进总装带来的）：`tools/check.py` 多了 `motion` 一项（第 6 节的表），`build/place.py` 摆完场景就启动
它登记的循环（`scenes/obs/motion/_kit.py`）。没登记会动的东西的场景这一项报 nothing moves，别的不变，已交付的包不用改。
S2 一次合几个交付的时候用 `tools/gatestack.sh`：每个交付还是在它自己合进去的那棵树上过关口，后合的包让先合的图变样不算先合的账。

11-16 第三次补充（公共文件的四处改动）：
- 骨架多了锁定机位 `S.V6`（总监 #55097：大台阶南半边看发电房，`site/powerhouse` 场景里的 `stair_south`）。看板的清单
  `tools/win/shots/obs-board.json` 跟着重出了，`v06_power`、`v07_hall` 两条现在都是骨架的数（`v07_hall` 以前还留着出图岗的提案）。
- 骨架 `SMALL_DOME_APEX` 从 25 改成 **26**（总监 #57140：25 读成扣在铁箍上的一顶扁盖，26 读成半球）。`main/smalldome.py`
  照骨架算，不用改；`check.py` 的天际线、彗星场景里的替身跟着变。拍到小穹顶的图都要重画。
- **测试场景用地图的时刻（`mood.py` 那一行）的，`write_pack` 要把天空的包也带上**：
  `return list(materials.pack(d) or []) + list(sky.pack(d) or [])`。只带 `materials.pack` 的，游戏自带的太阳没被涂黑，
  朝西、地平线敞开的图里天上有一块白心黄边的方块（lamps c341 #56843 查的，总装里 9 个场景的 14 张图有）。
  `check.py` 的 `views` 一项对这样的场景给 WARN；下一次交付时改这一行、重画。
- **离线图的星星调暗了，和游戏一样**（comet c330 #56134 查的）：游戏画星星是颜色 (b, b, b)、透明度 b，加到天上的是 b 的平方；
  `artkit/gamescene.py` 原来加的是 b。真机图量的也是平方：blue（b 0.60）星比天亮 92/255，原来的离线图是 153；glow（b 0.15）
  真机看不见星，原来的离线图亮 38；deep（b 1.0）不变。**这之前出的带星的离线图，blue 的星亮了约 1.7 倍，glow 的亮了约 6.7 倍**，
  看图定星星、彗星、天色的时候要算上这一条。留档图不追着重画：各包下一次交付时合了总装重画，急用的走【交付·补图】（第 6 节）。

11-16 第四次补充（占用表多了屏障，总监 05:07，记在 #457 第 4 条下面）：`B.BARRIER`（`barrier`，照原版用，看不见，只给碰撞）。
**只许一种用法**：用模型做的、关着的门和栅门，在门扇所在的那一层放屏障，高两格，不超出门扇的宽；看得见的关着的门能穿过去，
比屏障更破坏道理。别处照旧不许（掉下去就出不来的地方先报总监，不用栏杆也不用屏障）。头一处是入口两侧拱的栅门，共 12 格
（`props/ironwork` 的 `doors()` 放）。`check.py` 的 `blocks` 一项跟着管：屏障竖着超过两格 FAIL；一格屏障三格以内没有展示实体
（门扇的模型）给 WARN；合规矩的在 PASS 那一行报格数和范围。离线图不画屏障，它也不挡光，不用改。

11-16 第五次补充（屏障的第二种用法，总监 09:11）：**屏障只许放在看得见的实心模型里面**，让碰撞和看见的一致。关着的模型门是一种；
第二种是人能走进去的、实心的大件模型，头一处是出生点索道站台上停着的车厢（展示模型没有碰撞，人能穿过车厢走上栈桥、下到山坡
回不来）：车厢占的格子里放屏障，高两格，(90..91, −4..−3, −34..−32) 共 12 格，随 `machines/cablecar-winch` 进总装（cable 放）。
两条线不变：屏障一格也不出模型的轮廓，竖着不过两格；模型旁边还剩人挤得过去的缝，用看得见的东西堵（挡车的铁杆、链子、栅门），
不用屏障补。`check.py` 的 `blocks` 一项照旧管（三格以内要有展示实体）。别处照旧不许。

---

## 1. 目录和类别

```
build/scenes/obs/
  __init__.py      总场景：build() / build_models() / write_pack()（S2）
  mood.py          转发 sky 的光（S2；改光改 sky/mood.py）
  common/          palette.py  blocks.py  skeleton.py  assembly.py（S2）
  materials/ site/ main/ machines/ interiors/ props/ motion/ sky/     每个类别一个子包
```

- 八个类别子包，和 `PIPELINE.md` 第 4.2 节一致：`materials`（方块材质）、`site`（场地）、`main`（主楼）、`machines`（大型机械）、`interiors`（室内）、`props`（道具）、`motion`（动态和声音）、`sky`（光与天空）。
- 一个工作包 = 类别子包里的**一个模块**，模块名就是卡片的包名（`props/lamps.py`、`materials/ashlar.py`、`interiors/starhall.py`；包名里的 `-` 写成 `_`）。
- 只改自己领的卡对应的模块。公共四样和类别子包的 `__init__.py` 找 S2。代码和注释用英文。

## 2. 一个工作包实现三个函数（都可选）

```python
def build(canvas, origin=(0, 0, 0)) -> int:
    """把本包的方块和展示实体放进 canvas。坐标用 skeleton 的场景坐标，整体平移 origin。
       返回这次放了多少展示实体（给实体预算）。只放方块就返回 0。"""

def models() -> dict:            # {name: artkit.models.Model}
    """本包的自绘展示实体模型。键就是模型名，必须以本类别前缀开头（§4），不许和别人重名。没有就不定义。"""

def pack(pack_dir) -> list:      # 一行行的说明文字
    """把本包自己的资源包文件写进 pack_dir，只写本类别的地盘（§4）。
       展示实体的物品模型不在这里写（由 models() 统一出）。没有就不定义。"""
```

- `canvas` 是 `artkit.canvas.Canvas`：`canvas.set(x,y,z,state)` 放方块（state 是方块状态串或 `(x,y,z)->串`）；
  `canvas.add_entity(x,y,z, M.display(model, scale=, yaw=, turns=, brightness=))` 放展示实体。
- **额外参数随便加，但要有默认值**：总场景只调 `build(canvas, origin)`。要比选的包写成 `build(canvas, origin=(0,0,0), version="a")`，测试场景里并排调各版本；评审定了哪一版，就把默认值改成那一版。内部想拆成 `build_<room>(c, origin, roles, *, version=...)` 这样的函数随意，模块级的 `build()` 调它就行。
- 放方块只认占用表角色名：`from scenes.obs.common import blocks as B` → `B.ASHLAR_FINE.block`、`B.IRON_RIVETED.slab + "[type=top]"`、`B.PANELS["dial"]`。不直接写被重画方块的原名。
- 取坐标只认骨架：`from scenes.obs.common import skeleton as S` → `S.pilaster_z(j)`、`S.WINDOW`、`S.DOME_CENTRE`、`S.east_wall_x(bay)`、`S.BUDGET`。
- **格和点别混**：骨架里的数都是“格”（方块的整数坐标，第 k 格占 k 到 k+1）；展示实体摆在“点”上（实数坐标），第 k 格的正中是 k+0.5。主楼关于 z=0 这一排方块的正中对称，所以入口、星厅、穹顶的轴线是 **z=0.5**（`S.AXIS_Z`），穹顶的轴是 `S.DOME_AXIS=(4.5, 0.5)`。几格的正中用 `S.mid(a, b)`（等于 (a+b+1)/2）。把模型摆在 z=0 会偏北半格。
- 取颜色只认色板：`from scenes.obs.common import palette as P` → `P.mat("iron")`、`P.colour("brass", 3)`。缺颜色群里向 A0 提，不自定义。
- 例子：`props/lamps.py`（14 个模型，两版比选，`place()` 给别的类别调，`build()` 在总场景里摆 4 个）和它的测试场景 `scenes/obs_props_lamps/`；`materials/respack_redirect.py` 和 `scenes/obs_mat_redirect/`。`main/massing.py`（白模）、`site/ground.py` 还是框架的演示，对应的卡交付时由做卡的人替换或删掉。
- 类别的公用底座（名字以 `_` 开头，归类别牵头人管，缺什么找他加，别在自己分支上改）：
  - `materials/_kit.py`：`K.paint(pack_dir, 图名, 图)` 写方块图（自动查尺寸和色板外颜色），`K.redirect(pack_dir, 方块, {原版图: 图名})` 让一个方块换图而不动和它共用文件的方块；模块顶上 `BLOCKS = K.blocks(B.<角色>)` 写明自己画了哪些方块，占位就自动让开。要读游戏的 jar（`MC_JAR` 或 `MC_ROOT`，管理员电脑上 `job.py` 已带）。用法见文件头和 c176 的公告。
  - `props/_kit.py`：三种挂法（floor / wall / ceiling）、`K.put()` 摆放、道具用的几档材质、铆钉、玻璃、`K.offer_lights()` 把光源交给 sky。每个道具包对外给 `place(canvas, kind, pos, facing=, origin=)`。
- 数据包里的函数（`motion` 的循环）只由 `motion/_kit.py` 写，各包不自己往数据包里写文件（细化稿 `plan/parts/motion.md`，c177，11-15）。会动的件由做件的人在 `build()` 里登记，一个件一行，紧跟在摆它的那一行后面：`MK.spin`、`MK.swing`、`MK.crank`、`MK.slide`、`MK.blink`，周期取 `MK` 里的节拍表（细化稿第 4、6 节）。现在就能照着做的：会动的部分单拆一个模型、一个实体；锚点取在转轴上；摆下去的姿态就是静止姿态，离线图和循环没开时看到的都是它。`motion/loop` 这张卡进总装以前 `_kit.py` 不在树里，登记那一行等它进了再加（c177 到时逐个包发）。驱动脚本（`build/place.py`、`tools/check.py`）调 `_kit.write()`、加 `motion` 一项检查，归 S2，和 `motion/loop` 的交付一起进。

## 3. 怎么注册一个新包（不改共享列表，两个人各加一个包不冲突）

**加一个包 = 在类别文件夹里加一个模块。** 类别子包用 `common/assembly.py` **自动发现**本文件夹里的所有模块，
把它们的 `build/models/pack` 汇总。没有谁要改的“总列表”，所以两个人同时各加一个模块永不冲突。

- 包内顺序：两个包写同一格时后放的赢。要排在别的包后面，在模块顶上写 `ORDER = <数>`（不写是 50；先按 `ORDER`、再按模块名）。例：白模 `ORDER = 10`，立面 50，往壳子里搬的房间 `ORDER = 80`。
- 名字以 `_` 开头的模块（放共用工具，如 `props/_kit.py`、`sky/_lightkit.py`）和 `mood` 模块不参与自动发现。
- 类别子包的 `__init__.py` 是固定样板（`_cat = assembly.category(__name__)`，转发三个函数），别去改它，只加你的模块。

总场景 `scenes/obs/__init__.py` 的 `LINES` 是类别的铺设顺序：`materials`（不放方块）→ `site`（铺地）→ `main`（壳子）→ `machines` → `interiors` → `props` → `motion` → `sky`。**`sky` 最后**：它的隐形光源要等墙、玻璃、灯具都放完才知道落在哪一格，方块云要让开山体。所以测试场景想要光源，在自己的 `build()` 最后调一次 `scenes.obs.sky.build(c, origin)`。

总场景的 `build()` 依次调各类别的 `build(c, ORIGIN=(0,0,0))`；`build_models()` 合并各类别的模型（重名直接报错）；`write_pack()` 依次调各类别的 `pack()`。

光：生物群系只有一个，`obs.BIOME = "obs_blue"`（不带冒号的名字要是 `mood.py` 的 BIOMES 里的一个；带命名空间的原样用，比如没有注册表文件的世界里的 `minecraft:the_void`，`place.py` 和 `check.py` 都这样认）。三个光线版本是同一条时间线上的三个时刻，靠 `shots.json` 里的 `time` 选：`14000`（A，默认，不写就是 A）、`18000`（B）、`12900`（C）。光的实现在 `sky/mood.py`，归 `sky/look` 这张卡（已合并）。
“不写就是 A”两个出图工具都照办：`build/render.py`（离线）和 `tools/shoot.py`（真机）对没有 `time` 的机位都按 14000 拍（11-14 前是正午）。要白天的图就写 `"time": "noon"`。
11-16 起天由资源包带（Realms 不收注册表文件）：`sky/mood.py` 的 `BIOMES` 是 `artkit.mood.Carried`，场景照旧写 `BIOME = "obs_blue"`、照旧带那一行 `mood.py`，什么都不用改。驱动替每个带 `mood.py` 的场景做四件事：数据包里不写群系和时间线；场景的范围填游戏自己的 `minecraft:the_void`；场景的资源包写完后加上天色的 10 个着色器文件（`assets/minecraft/shaders/`，场景和别的包不许再写这几个文件）；钟停在 `20370`。**真机上只有这一个时刻**：`tools/shoot.py --clock 20370` 每张都拍它，不看机位的 `time`（`place.py` 把这个数记在 `<scene>.placed.json` 的 `clock` 里）。`shots.json` 和看板清单里的 `time` 不用改：离线出图照旧按它选 A、B、C，留着两个时刻的场景（比如 `obs_sky_lights` 的 blue、deep）离线图不变，真机上都是 A。B、C 要上真机，得各出一套着色器包，还没做。

## 4. 不撞车（两个包不许写同一个文件；检查脚本会查）

- **模型名加类别前缀**：`materials`→`mat_`、`sky`→`sky_`、`main`→`bld_`、`props`→`prop_`、`site`→`site_`、`machines`→`mach_`、`interiors`→`int_`、`motion`→`mot_`。
  模型名唯一 ⇒ `assets/c164/…` 下的物品模型/贴图文件唯一；重名 `build_models()` 抛错，`check.py` 也查。
- **资源包里谁写哪**（`check.py` 里的 `OWNED` 表；写进别的类别的地盘判不过，写到表里没有的地方给警告，找 S2 加）：
  - `materials`：方块贴图和重定向——`assets/minecraft/*`（除了下面 `sky` 的）、`assets/c164/textures/block/*`、`assets/c164/models/block/*`。**只有它写这些，唯一的例外是云。**
  - `sky`：`assets/minecraft/textures/environment/*`、`assets/c164/textures/environment/*`（彗星、云、星）。光的 biome/timeline 在 `sky/mood.py`（那是数据包，驱动器单独处理，不在 `pack()` 里）。
    **云的五个方块（`B.CLOUD`）由 sky 画**（A0 批的例外：云色要和天光一起调）：它们的方块状态文件、模型文件夹 `assets/c164/models/block/<方块名>/`、名字以 `sky_` 开头的方块图 `assets/c164/textures/block/sky_*` 归 sky；照样走 `materials/_kit.py` 的 `paint` 和 `redirect`。
    **核心着色器 `assets/minecraft/shaders/*` 也归 sky**（11-16，materials 让出这个文件夹）：Realms 不收注册表文件，天、雾、光色改由资源包的着色器带；着色器只有 a2 那一套，生成器是 `sky/_shaders.py`，数仍只在 `sky/mood.py`。别的类别不写这个文件夹。
  - 占位：没人画的重画方块由 `materials/respack_redirect` 套上占位色（图名 `ph_` 开头）。占位写到别人地盘里不算越界；正式的包开始写同一个文件而占位没让开，判重复。
  - `motion`：`assets/c164/sounds/*`、`assets/c164/sounds.json`、`assets/c164/particles/*`、`assets/c164/textures/particle/*`。
  - 其余类别：`pack()` 一般不写文件，只用 `materials` 的方块和自己的展示实体模型。
- 要一种新方块材质/新色阶：群里点名 materials 的牵头人和 S2，A0 批，S2 改占用表/色板，再画。不自己占方块、不自己建色板。

## 5. 每个包的测试场景

一个包要能单独出图验收。命名按 `PIPELINE.md` 第 4.2 节：`obs_<缩写>_<包名>`，缩写 mat/sky/main/site/mach/props/int/mot。

```
build/scenes/obs_<缩写>_<包名>/
  __init__.py     def build(): 建 Canvas，调本包的 build(c,(0,0,0))（比选就并排调各版本），返回 c；BIOME = "obs_blue"
                  def write_pack(pack_dir): 调本包的 pack()；要用重画的方块就再调 scenes.obs.materials.pack(pack_dir)；
                                            用地图的时刻（下面的 mood.py）就再调 scenes.obs.sky.pack(pack_dir)，不然天上有游戏自带的太阳
  props.py        def build_models(): return <本包>.models()        # 有模型才写；场景里用到别的包的模型也并进来
  mood.py         from scenes.obs.sky.mood import BIOMES, TIMELINES    # 一行，复用总装的光
  shots.json      [{"name":.., "pos":[x,y,z], "look_at":[x,y,z], "time": 可省}]  视角至少含一远、一近、一和相邻东西同框
```

- 场景属于哪个类别，`check.py` 从名字里的缩写读；名字不按这个格式的测试场景在 `__init__.py` 里写一行 `CATEGORY = "props"`。没有模型的场景不用写 `props.py`，`makepack.py`、`render.py`、`check.py` 都当它没有模型。
- 机位正对着头顶或脚下（`look_at` 和 `pos` 只差 y）可以写：朝下拍时画面上边朝南。要别的朝向改用 `yaw`、`pitch` 写（`pitch` 90 朝下；`yaw` 180 时画面上边朝北、右边朝东）。`pos` 和 `look_at` 是同一点不行，`check.py` 判不过。
- 骨架锁定的机位（`common/skeleton.py` 里的 `V1`、`V2`、`V6`、`V7`、`V11`）：测试场景拍这几个机位时，`pos` 和 `look_at` 照骨架现在的数写，不抄旧图、旧场景上的数（A0 #304）。同一个站位换时刻可以写几个机位（`v1_blue`、`v1_deep`）。站在锁定机位上、方向却不是骨架的，`check.py` 给 WARN。星厅门洞里那个副机位叫 `v7_in`（A0 #365）。
- 只想陈列模型、不摆场景：不写 `build()`，在 `props.py` 里再加 `GALLERY`（照 `scenes/skyobs/props.py`）；真机上的陈列由 S1 用 `gallery.py` 摆。`check.py` 对这种场景只查模型和资源包。
- **自查图在你自己的节点上出，跟着分支进 git**（`COMMON.md` 第 0 节第 2 条、第 2.2 节）。合用机上不出图；管理员的电脑不再用。
  代码先提交、push，然后往自己的节点投（`run_workspace_job`，命令照在 `c164-realms/` 下手敲的样子写）：
  ```
  # 整套，进仓库：图落进 renders/<场景名>/，节点替你提交、推回你的分支，你再 git pull
  bash c164-realms/tools/nodejob.sh python tools/selfshots.py obs_<缩写>_<包名>
  # 只重出几张
  bash c164-realms/tools/nodejob.sh python tools/selfshots.py obs_<缩写>_<包名> --only a,b
  # 改到一半看一眼，不进你的分支：推到草稿分支 <你的分支>-wip，一次不超过 4 张
  bash c164-realms/tools/nodejob.sh --wip python tools/selfshots.py obs_<缩写>_<包名> --only a,b --out renders/_wip
  # 存的图还是不是现在的代码画出来的（什么都不写、不提交）
  bash c164-realms/tools/nodejob.sh --no-push python tools/selfshots.py obs_<缩写>_<包名> --verify
  ```
  - 按场景的 `shots.json` 出图（`build/render.py`，1280×720，每个机位按自己的 `time`），存成 `renders/<场景名>/<机位>.png`；
    旁边的 `shots.txt` 记每张图的时刻、是哪个提交的代码出的（从检出的那份代码上读，不靠手抄）、图片文件的 SHA-256。
    `build/` 下有没提交的改动就不给出（要看一眼用 `--out`）。二十五个机位约四十秒。
  - 机位从 `shots.json` 里删了，下一次出整套时它的图也会被删掉；文件夹里别的图（对比用的拼图）不动。
  - **整套图在发【交付】前出一次**，别每改一版都出整套：每张 0.1–0.9 MB，进了历史删不掉。
  - 节点上出的图和别处出的逐像素一样，所以关口能在它自己的节点上重画你的图来核（第 6 节）。
- 真机图、把总场景摆进测试服：拿出图钥匙的人（S1）统一跑，各包别自己开游戏；要真机图私信他一条【真机】，写场景、机位、提交号。地块的 y 一律 200（云的高度是世界坐标）。

## 6. 交付前自查，交付消息

交付前自己跑技术检查。单个测试场景的 `check.py` 一两秒，合用机上可以跑；别的重活都投到自己的节点（`COMMON.md` 第 2.2 节）。在 `c164-realms/` 下：

```
python tools/check.py --scene obs_<缩写>_<包名> --shots build/scenes/obs_<缩写>_<包名>/shots.json
```

不用游戏、不出图。每项给 PASS / WARN / FAIL，有 FAIL 就别交付（退出码 1）：

| 项 | 查什么 | 不过是 |
| --- | --- | --- |
| regen | 场景、模型、资源包、数据包、光能不能从头生成 | FAIL |
| conflicts | 两个包有没有写同一个文件；文件在不在本类别的地盘；模型名有没有类别前缀；文件名游戏认不认（只能有小写字母、数字和 `_ - . /`）。**测试场景也查**：场景所属类别的每个包照总场景的办法单独跑一遍，写进别人地盘、模型没前缀在这里就报，不用等合并 | FAIL（表里没有的地方、不是 .png 的图 WARN） |
| strays | 生成的每张贴图有没有色板外的颜色（列出颜色、像素数、最近的色板色；天空贴图是加色的，不查） | FAIL |
| refs | 资源包里的方块状态、物品定义、模型点到的模型和贴图，资源包或游戏里有没有（没有的话游戏里是紫黑格）；没人点到的模型和贴图 | 点到的不存在 FAIL；没人点到 WARN |
| repaint | 被替换的方块状态是不是都在占用表的重画名单里；替换原版模型/贴图有没有连带改了表外的方块 | FAIL |
| blocks | 放下的方块、`block_display` 展示的方块是不是都在占用表里；屏障（`B.BARRIER`）只当关着的模型门的碰撞 | WARN（找 S2 加表，或换表里的方块；屏障旁边三格以内没有模型）；FAIL（屏障竖着超过两格） |
| flatwall | 立面上有没有超过 5×5 的平墙（同一种方块状态、没有凹凸，连成比 5×5 大的实心方块；宽或高不超过 5 的条带不算）。materials、sky、props、motion 的测试场景是样板墙，跳过 | WARN（白模阶段本来就平；立面交付时要清掉） |
| entities | 每个展示实体的模型资源包里有没有；实体总数和类别预算；是不是 16 像素一格；沿一个方向拉长的件（`M.between`），贴图沿那个方向是不是均匀（不均匀会拉花），有没有被拉歪的斜件；直接展示原版物品的 | 缺模型、超预算 FAIL；其余 WARN |
| views | 按 `shots.json` 数每个视角里的展示实体（不算墙的遮挡），对照单视角上限；另报两个数：游戏实际要画的（没设宽高的展示实体在画面外也照画）、离机位水平超过 160 格的（服务器不发给玩家，那张图里看不到；这条是读游戏代码得的，真机待证实）。机位没有方向（`pos` 等于 `look_at`）判不过。站在骨架锁定的机位上、方向却不是骨架的也点出来 | WARN；机位没方向 FAIL |
| sight | 到达机位 `S.V1` 的视线，不出图，照方块和展示实体的形状算。查总场景，和有机位站在 V1 上的测试场景。三样：① 画面必须露出来的：天际线（两个穹顶、钟塔、报时球杆）和彗头一条视线都不许挡；立面 y 4 以上报被挡多少，基座层被挡过半、一跨大窗被挡过半判不过。② **车站让出的视野**（A0 #442），从 V1 的眼睛看有两块，里面不许有车站的东西，棚、梁、柱、缆都算：主楼南北两端之间（正西偏北 1.2° 到偏南 44.2°）从眼高到 `S.V1_CLEAR` = 61°；彗星那一块（`S.V1_COMET`），从主楼北端往北到正西偏北 15°、仰角 35° 到 61°（35° 以下不管，候车室在那里当画面右边的边框）。每 0.25° 一条视线，只跟到车站脚印外 6 格，量到 61° 整，不留余量。自己先量用 `S.in_v1_clear(x, y, z)`；底面在 y 的东西，离眼睛的水平距离不超过 (y + 2.38) ÷ tan 61°（y 4 是 3.54 格，y 5 是 4.09 格）。③ 画面左边三分之一（主楼南端到正西偏南 70°）：雨棚的角可以进画面，通高的柱不行；同一列格子里被看到的部分上下超过 40° 就点出来。④ sky/comet 画出来的整颗彗星（`comet.seen()`）：要是有哪一部分画到两块以外又被车站挡住，另报 | ①② FAIL；一跨大窗被挡四分之一到一半、③④ WARN |
| motion | 场景登记的会动的东西（`scenes/obs/motion/_kit.py`：转、摆、曲柄、滑、闪、声音、粒子）排成的循环在不在预算里：最忙的一刻不超过 40 条命令、平均每刻不超过 10 条、一个场景的函数文件不超过 3000 个、一条链不超过 720 个函数；闪的灯要换的那个模型场景里有没有、自己的声音事件在不在资源包的 `sounds.json` 里；同名的两个件不站在同一点。什么都没登记的场景报 nothing moves | 超预算、缺模型、缺声音事件、排不成循环 FAIL；手定步数、场景自己改上限（负载测试）WARN |

`--json <文件>` 另存一份机器可读的结果（明细不截短，views 带每个机位的数）；`--keep <目录>` 留下生成的资源包和数据包（那个目录会先被清空，所以只收新目录、空目录、或者上一次 `--keep` 留下的目录）。S2 合并前在“你的分支和总装合起来”的树上把全部场景复跑一遍（`tools/checkall.py`，总场景 `obs` 和别的包的测试场景都在里面），所以交付前先 merge 一次总装分支再自查，省一轮。脚本查不了的（门能不能走人、层高、文字、被重画的方块有没有按原意用）由做技检的人看图看代码。

合并前 S2 还跑 `tools/delivery.py <类别>/<包名> <提交>`（只读 git，重，投到节点；你也可以自己先跑）。八项：**来源**（`shift` 一项：提交的历史里有没有第 2 班的东西，就是 `tools/provenance.sh <提交>`；有就退回，那张卡从第 1 班的有效头重新做，`HANDOVER.md` 第 0 节）；改了谁的文件（本卡的、公共的、别的卡的、总监的）；有没有不该进仓库的文件；有没有像密钥的字符串；有没有提到授权、素材站；提交说明是不是 `c164-<代号>: ` 开头；本包的测试场景是不是每个机位都存了图、存的图是不是 `shots.txt` 里记的那个文件（SHA-256；出图以后被改过、换过的判不过）、记的提交在不在分支上、出图之后本卡的代码有没有再改（`pictures` 一项；不齐、没记 SHA-256 的旧图给警告）；能不能干净地合进总装。**二进制文件一律拦**，只放行图片（`renders/` 下的自查图、`plan/` 下的配图；代码树里的图片会被问来源，贴图都由代码画）和 `tools/win/helper/*.class`（A0 批的唯一例外，S2 会从并排的源码重编一遍逐字节比；现在存的那一个是 javac 25.0.5 编的，别的版本编出来字节不同，动它的人用同一个版本）。声音文件也拦，要加先问 A0。

**关口是一条命令**，S2 用它，你交付以前也可以在自己的节点上先跑一遍，省一轮来回：

```
# 先把总装合进你的分支、push，再投到你的节点；<总装头> 是你合进来的那个总装提交
bash c164-realms/tools/nodejob.sh --wip --always --tail 80 bash tools/gate.sh <类别>/<包名> <提交> --base <总装头>
```

它在合起来的树上做三件事，每一步说的原话写进 `renders/_wip/gate/<包名>/`（`summary.txt` 是总结，`--wip` 把这个文件夹推到你的草稿分支），最后一行是 `result: PASS` 或 `result: FAIL`：

1. `tools/delivery.py`，上一段的八项。
2. `tools/checkall.py`：全部场景的 `check.py`（二十来个场景十秒上下）。
3. 你这次交付动到的测试场景里存的图，`tools/selfshots.py <场景名> --verify` 重画一遍逐像素比：存的图是不是合起来以后的代码画的。对不上时再在你交付的提交上比一次，分清是图和你的代码对不上（退回），还是总装里别的包让它变了样（照合，【合并】里写明哪几张要重出）。

过了按 `PIPELINE.md` 第 4.3 节**私信** S2 和管你这个类别的评审（现在各是谁看 `plan/ROSTER.md`）：

```
【交付】<类别>/<包名> <分支> <提交前七位> 自查图：renders/<场景名>/（<张数> 张）
```

带图交：整套图在自己的节点上出好、推上去再发。图一时出不齐可以先发【交付】，自查图写“图待补”，代码先过关口、合并，图补齐后再发一次【交付·补图】；评审要看图，所以能出图就带图交。

S2 收到【交付】：先看 `tools/provenance.sh <提交>`，再把这个提交合进自己的分支（和总装同头）、推上去，在自己的节点上跑 `tools/gate.sh`。过了才推总装，发【合并】私信做包的人、评审和一个交叉看的人，每批告诉拿出图钥匙的人一次；不过发【技检】退回，写明原因和怎么复现，私信做包的人，总装不动。卡片和细化稿是纯文档，不用技检，推上去私信 S2 直接合。

合并之后总装里的 `renders/<场景名>/` 就是这个包交付时的样子。别的包后来合进来会让它变样（换了光、重画了它用到的方块、换了立面）：S2 每合完一批在节点上跑 `tools/keptshots.py`，把总装里存的图全部重画一遍，哪些场景的哪几张已经不是现在的代码画的，记进 `plan/STATUS.md` 的“图的现状”，私信那个场景的作者。图由作者下次交付时重出（只重出那几张：`--only a,b`），急着给评审看的单独发一次【交付·补图】。自己查：`python tools/keptshots.py <场景名>`（投到节点）。

## 7. 实体预算（骨架 `S.BUDGET`，R1 0.4）

全图 ≤ 3000，单看板视角 ≤ 600。室外道具 1100、室内 1000（每间 ≤250）、大型机械 400、总装留用 500。
单视角道具 ≤ 400；样板段（5 跨）≤ 120。`build()` 必须返回实体数，S2 据此盯预算。
