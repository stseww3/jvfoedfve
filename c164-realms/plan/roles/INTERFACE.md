# 接口：各包怎么接进总场景和总资源包

状态：**第二版，可用。** 拿合并钥匙的人（S2）维护。框架代码已在总装分支，`obs` 总场景能从头生成
（`build()` + 资源包 + 导出都通），`tools/check.py` 已可用。有异议在群里发【问题】点名 S2。

对接只靠四样，都由 S2 维护：**色板** `build/scenes/obs/common/palette.py`、**占用表** `common/blocks.py`、
**骨架** `common/skeleton.py`、**本接口**。要改前三样，群里提，A0 批。

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
- 数据包里的函数（`motion` 的循环）怎么交：等 `motion` 的细化稿出来再定，先别自己往数据包里写文件。

## 3. 怎么注册一个新包（不改共享列表，两个人各加一个包不冲突）

**加一个包 = 在类别文件夹里加一个模块。** 类别子包用 `common/assembly.py` **自动发现**本文件夹里的所有模块，
把它们的 `build/models/pack` 汇总。没有谁要改的“总列表”，所以两个人同时各加一个模块永不冲突。

- 包内顺序：两个包写同一格时后放的赢。要排在别的包后面，在模块顶上写 `ORDER = <数>`（不写是 50；先按 `ORDER`、再按模块名）。例：白模 `ORDER = 10`，立面 50，往壳子里搬的房间 `ORDER = 80`。
- 名字以 `_` 开头的模块（放共用工具，如 `props/_kit.py`、`sky/_lightkit.py`）和 `mood` 模块不参与自动发现。
- 类别子包的 `__init__.py` 是固定样板（`_cat = assembly.category(__name__)`，转发三个函数），别去改它，只加你的模块。

总场景 `scenes/obs/__init__.py` 的 `LINES` 是类别的铺设顺序：`materials`（不放方块）→ `site`（铺地）→ `main`（壳子）→ `machines` → `interiors` → `props` → `motion` → `sky`。**`sky` 最后**：它的隐形光源要等墙、玻璃、灯具都放完才知道落在哪一格，方块云要让开山体。所以测试场景想要光源，在自己的 `build()` 最后调一次 `scenes.obs.sky.build(c, origin)`。

总场景的 `build()` 依次调各类别的 `build(c, ORIGIN=(0,0,0))`；`build_models()` 合并各类别的模型（重名直接报错）；`write_pack()` 依次调各类别的 `pack()`。

光：生物群系只有一个，`obs.BIOME = "obs_blue"`。三个光线版本是同一条时间线上的三个时刻，靠 `shots.json` 里的 `time` 选：`14000`（A，默认，不写就是 A）、`18000`（B）、`12900`（C）。光的实现在 `sky/mood.py`，归 `sky/look` 这张卡（已合并）。
“不写就是 A”两个出图工具都照办：`build/render.py`（离线）和 `tools/shoot.py`（真机）对没有 `time` 的机位都按 14000 拍（11-14 前是正午）。要白天的图就写 `"time": "noon"`。

## 4. 不撞车（两个包不许写同一个文件；检查脚本会查）

- **模型名加类别前缀**：`materials`→`mat_`、`sky`→`sky_`、`main`→`bld_`、`props`→`prop_`、`site`→`site_`、`machines`→`mach_`、`interiors`→`int_`、`motion`→`mot_`。
  模型名唯一 ⇒ `assets/c164/…` 下的物品模型/贴图文件唯一；重名 `build_models()` 抛错，`check.py` 也查。
- **资源包里谁写哪**（`check.py` 里的 `OWNED` 表；写进别的类别的地盘判不过，写到表里没有的地方给警告，找 S2 加）：
  - `materials`：方块贴图和重定向——`assets/minecraft/*`（除了下面 `sky` 的）、`assets/c164/textures/block/*`、`assets/c164/models/block/*`。**只有它写这些，唯一的例外是云。**
  - `sky`：`assets/minecraft/textures/environment/*`、`assets/c164/textures/environment/*`（彗星、云、星）。光的 biome/timeline 在 `sky/mood.py`（那是数据包，驱动器单独处理，不在 `pack()` 里）。
    **云的五个方块（`B.CLOUD`）由 sky 画**（A0 批的例外：云色要和天光一起调）：它们的方块状态文件、模型文件夹 `assets/c164/models/block/<方块名>/`、名字以 `sky_` 开头的方块图 `assets/c164/textures/block/sky_*` 归 sky；照样走 `materials/_kit.py` 的 `paint` 和 `redirect`。
  - 占位：没人画的重画方块由 `materials/respack_redirect` 套上占位色（图名 `ph_` 开头）。占位写到别人地盘里不算越界；正式的包开始写同一个文件而占位没让开，判重复。
  - `motion`：`assets/c164/sounds/*`、`assets/c164/sounds.json`、`assets/c164/particles/*`、`assets/c164/textures/particle/*`。
  - 其余类别：`pack()` 一般不写文件，只用 `materials` 的方块和自己的展示实体模型。
- 要一种新方块材质/新色阶：群里点名 materials 的牵头人和 S2，A0 批，S2 改占用表/色板，再画。不自己占方块、不自己建色板。

## 5. 每个包的测试场景

一个包要能单独出图验收。命名按 `PIPELINE.md` 第 4.2 节：`obs_<缩写>_<包名>`，缩写 mat/sky/main/site/mach/props/int/mot。

```
build/scenes/obs_<缩写>_<包名>/
  __init__.py     def build(): 建 Canvas，调本包的 build(c,(0,0,0))（比选就并排调各版本），返回 c；BIOME = "obs_blue"
                  def write_pack(pack_dir): 调本包的 pack()；要用重画的方块就再调 scenes.obs.materials.pack(pack_dir)
  props.py        def build_models(): return <本包>.models()        # 有模型才写；场景里用到别的包的模型也并进来
  mood.py         from scenes.obs.sky.mood import BIOMES, TIMELINES    # 一行，复用总装的光
  shots.json      [{"name":.., "pos":[x,y,z], "look_at":[x,y,z], "time": 可省}]  视角至少含一远、一近、一和相邻东西同框
```

- 场景属于哪个类别，`check.py` 从名字里的缩写读；名字不按这个格式的测试场景在 `__init__.py` 里写一行 `CATEGORY = "props"`。没有模型的场景不用写 `props.py`，`makepack.py`、`render.py`、`check.py` 都当它没有模型。
- 机位正对着头顶或脚下（`look_at` 和 `pos` 只差 y）可以写：朝下拍时画面上边朝南。要别的朝向改用 `yaw`、`pitch` 写（`pitch` 90 朝下；`yaw` 180 时画面上边朝北、右边朝东）。`pos` 和 `look_at` 是同一点不行，`check.py` 判不过。
- 只想陈列模型、不摆场景：不写 `build()`，在 `props.py` 里再加 `GALLERY`（照 `scenes/skyobs/props.py`）；真机上的陈列由 S1 用 `gallery.py` 摆。`check.py` 对这种场景只查模型和资源包。
- **自查图在管理员电脑上出，回云端进 git。** 云端一律不出图（管理员定）：`build/render.py`、`tools/selfshots.py` 的出图和
  `--verify` 都不在云端跑。电脑上的规矩在 `COMMON.md` 第 3 节（每条命令先 `Set-Location …` 进共用工作区，只走 `bin\job.py`，
  只写自己的 `agents\<代号>\`）。一轮四步，前三步在电脑上，第四步在云端自己 worktree 的 `c164-realms/` 下：
  ```
  # 1 先在云端提交、push（分支要 merge 过 11-14 中午以后的总装，才有新的 tools/selfshots.py），再把分支同步到电脑
  .\venv\Scripts\python.exe bin\sync.py <你的分支> --to agents/<代号>
  # 2 出图（重任务，排队）。可以一次写几个场景；只重出几张：写一个场景，加 --only a,b
  .\venv\Scripts\python.exe bin\job.py <代号> --heavy --timeout 900 -- ..\tools\selfshots.py obs_<缩写>_<包名> --out '@out/shots'
  # 3 原样传回云端的收图夹（不加 --jpeg）
  .\venv\Scripts\python.exe bin\send.py "agents\<代号>\out\shots\obs_<缩写>_<包名>-*" --prefix <代号>-
  # 4 云端：核对、落位；然后提交、push
  /agent/realms-study/.venv/bin/python tools/selfshots.py obs_<缩写>_<包名> --take
  ```
  - 第 2 步按场景的 `shots.json` 出图（`build/render.py`，1280×720，每个机位按自己的 `time`），存成
    `agents\<代号>\out\shots\<场景名>-<机位>.png`；旁边的 `<场景名>-shots.txt` 记每张图的时刻、是哪个提交的代码出的
    （从同步过来的那份代码上读，不靠手抄）、图片文件的 SHA-256。十个机位的样板约半分钟。
  - 第 4 步先核对再落位：记录里的图是不是都到了、是不是原样（SHA-256）、记的提交在不在你的分支上。都对才放进
    `renders/<场景名>/<机位>.png`、更新 `shots.txt`；有一张不对就什么都不动，并说是哪张（没到的等一会儿或重传，再跑一次）。
    和已存的图逐像素一样的不换文件，只把记录改到新提交（历史里不多存一份）；它会说这一轮哪几张真的变了。
    机位从 `shots.json` 里删了，它的图也会被删掉。收图夹里同一个场景有几个人传的图时，加 `--prefix <代号>-`。
  - 桥上一条命令超过约 60 秒会报 “Request timed out”，电脑上其实还在跑：**不要重跑**。出图看 `agents\<代号>\logs\`
    里最新的日志；回传直接去跑第 4 步，它会说还差哪几张。
  - **图只在发【交付】前提交一次**，别每改一版都提交：每张 0.1–0.9 MB，进了历史删不掉。改到一半想先看一眼，照样走前三步，
    图在收图夹 `/agent/realms-study/inbox/<代号>-<场景名>-<机位>.png`，用读文件的工具直接看，不跑第 4 步就不进 git
    （收图夹随 VM 重启清空）。
  - 按 A0 #18530 的写法用 `render.py … --out '@out/rt/<提交前七位>'` 出好、传回的图不用重出：
    `tools/selfshots.py <场景名> --take --prefix <代号>-<提交前七位>-`。这种图没有随图的记录，“哪个提交出的”只凭文件名；
    两个场景有同名机位时还会互相覆盖（windows 的甲、乙两个场景就是）。所以以后都用第 2 步的写法。
- 真机图、把总场景摆进测试服：拿出图钥匙的人（S1）统一跑，各包别自己开游戏。地块的 y 一律 200（云的高度是世界坐标）。

## 6. 交付前自查，交付消息

交付前自己跑技术检查。在云端自己 worktree 的 `c164-realms/` 下（它不出图，一两秒，云端照常跑）：

```
/agent/realms-study/.venv/bin/python tools/check.py --scene obs_<缩写>_<包名> --shots build/scenes/obs_<缩写>_<包名>/shots.json
```

不用游戏、不出图，测试场景一两秒。每项给 PASS / WARN / FAIL，有 FAIL 就别交付（退出码 1）：

| 项 | 查什么 | 不过是 |
| --- | --- | --- |
| regen | 场景、模型、资源包、数据包、光能不能从头生成 | FAIL |
| conflicts | 两个包有没有写同一个文件；文件在不在本类别的地盘；模型名有没有类别前缀；文件名游戏认不认（只能有小写字母、数字和 `_ - . /`）。**测试场景也查**：场景所属类别的每个包照总场景的办法单独跑一遍，写进别人地盘、模型没前缀在这里就报，不用等合并 | FAIL（表里没有的地方、不是 .png 的图 WARN） |
| strays | 生成的每张贴图有没有色板外的颜色（列出颜色、像素数、最近的色板色；天空贴图是加色的，不查） | FAIL |
| refs | 资源包里的方块状态、物品定义、模型点到的模型和贴图，资源包或游戏里有没有（没有的话游戏里是紫黑格）；没人点到的模型和贴图 | 点到的不存在 FAIL；没人点到 WARN |
| repaint | 被替换的方块状态是不是都在占用表的重画名单里；替换原版模型/贴图有没有连带改了表外的方块 | FAIL |
| blocks | 放下的方块、`block_display` 展示的方块是不是都在占用表里 | WARN（找 S2 加表，或换表里的方块） |
| flatwall | 立面上有没有超过 5×5 的平墙（同一种方块状态、没有凹凸，连成比 5×5 大的实心方块；宽或高不超过 5 的条带不算）。materials、sky、props、motion 的测试场景是样板墙，跳过 | WARN（白模阶段本来就平；立面交付时要清掉） |
| entities | 每个展示实体的模型资源包里有没有；实体总数和类别预算；是不是 16 像素一格；沿一个方向拉长的件（`M.between`），贴图沿那个方向是不是均匀（不均匀会拉花），有没有被拉歪的斜件；直接展示原版物品的 | 缺模型、超预算 FAIL；其余 WARN |
| views | 按 `shots.json` 数每个视角里的展示实体（不算墙的遮挡），对照单视角上限；另报两个数：游戏实际要画的（没设宽高的展示实体在画面外也照画）、离机位水平超过 160 格的（服务器不发给玩家，那张图里看不到；这条是读游戏代码得的，真机待证实）。机位没有方向（`pos` 等于 `look_at`）判不过 | WARN；机位没方向 FAIL |

`--json <文件>` 另存一份机器可读的结果（明细不截短，views 带每个机位的数）；`--keep <目录>` 留下生成的资源包和数据包（那个目录会先被清空，所以只收新目录、空目录、或者上一次 `--keep` 留下的目录）。S2 合并前在“你的分支和总装合起来”的树上，对你的测试场景和总场景 `obs` 各复跑一次，所以交付前先 merge 一次总装分支再自查，省一轮。脚本查不了的（门能不能走人、层高、文字、被重画的方块有没有按原意用）由做技检的人看图看代码。

合并前 S2 还跑 `tools/delivery.py <类别>/<包名> <提交>`（只读 git，你也可以自己先跑）：改了谁的文件（本卡的、公共的、别的卡的、总监的）；有没有不该进仓库的文件；有没有像密钥的字符串；提交说明是不是 `c164-<代号>: ` 开头；本包的测试场景是不是每个机位都存了图、存的图是不是 `shots.txt` 里记的那个文件（SHA-256；出图以后被改过、换过的判不过）、记的提交在不在分支上、出图之后本卡的代码有没有再改（`pictures` 一项；不齐、没记 SHA-256 的旧图给警告）；能不能干净地合进总装。**二进制文件一律拦**，只放行图片（`renders/` 下的自查图、`plan/` 下的配图；代码树里的图片会被问来源，贴图都由代码画）和 `tools/win/helper/*.class`（A0 批的唯一例外，S2 会从并排的源码重编一遍逐字节比）。声音文件也拦，要加先问 A0。

过了按 `PIPELINE.md` 第 4.3 节发群，点名 S2（c188）：

```
【交付】<类别>/<包名> <分支> <提交前七位> 自查图：renders/<场景名>/（<张数> 张）
```

电脑排不上队、图一时出不了：可以先发【交付】，自查图写“图待补”（A0 #18142）；代码先过技检、合并，图补齐后再发一次【交付】。评审要看图，所以能出图就带图交。

S2 收到【交付】分两处查：

- 云端（不出图）：`delivery.py`；把你的分支和总装合起来，在合起来的树上对你的测试场景和总场景 `obs` 复跑 `check.py`。
- 管理员电脑（逐像素）：把合起来的那个提交同步到 `agents\s2`，跑 `..\tools\selfshots.py <场景名> --verify`，重出一遍和存的图
  逐像素比：存的图是不是合并以后的代码出的。对不上时再在你交付的提交上比一次，分清是图和你的代码对不上（退回），
  还是总装里别的包让它变了样（照合，【合并】里写明哪几张要重出）。

都过了合并进总装分支，发【合并】点名总监和一个交叉看的人，评审同时看图；不过发【技检】退回，写明原因和怎么复现，点名做包的人。
卡片和细化稿是纯文档，不用技检，推上去点名 S2 直接合。

合并之后总装里的 `renders/<场景名>/` 就是这个包交付时的样子。别的包后来合进来会让它变样（换了光、重画了它用到的方块）：
S2 合并后在电脑上对可能受影响的场景跑 `--verify`，在【合并】里写明哪些场景的哪几张变了；图由那个场景的作者下次交付时重出
（只重出那几张：`--only a,b`）。

## 7. 实体预算（骨架 `S.BUDGET`，R1 0.4）

全图 ≤ 3000，单看板视角 ≤ 600。室外道具 1100、室内 1000（每间 ≤250）、大型机械 400、总装留用 500。
单视角道具 ≤ 400；样板段（5 跨）≤ 120。`build()` 必须返回实体数，S2 据此盯预算。
