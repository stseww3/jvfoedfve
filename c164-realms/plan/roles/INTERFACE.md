# 接口：各包怎么接进总场景和总资源包

状态：**第一版，可用。** 拿合并钥匙的人（S2）维护。框架代码已在总装分支，`obs` 总场景能从头生成
（`build()` + 资源包 + 导出都通）。有异议在群里发【问题】点名 S2。

对接只靠四样，都由 S2 维护：**色板** `build/scenes/obs/common/palette.py`、**占用表** `common/blocks.py`、
**骨架** `common/skeleton.py`、**本接口**。要改前三样，群里提，A0 批。

---

## 1. 目录和类别

```
build/scenes/obs/
  __init__.py      总场景：build() / build_models() / write_pack()（S2）
  mood.py          转发 A2 的光（S2；改光改 sky/mood.py）
  common/          palette.py  blocks.py  skeleton.py  assembly.py（S2）
  materials/ sky/ main/ site/ machines/ props/ interiors/     每个类别一个子包
```

- 七个类别子包：`materials`（方块材质）、`sky`（光与天空）、`main`（主楼）、`site`（场地）、`machines`（大型机械）、`props`（道具）、`interiors`（室内）。
- 一个工作包 = 类别子包里的**一个模块**（`main/order.py`、`props/lamps.py`、`materials/stone.py` 这样）。
- `motion`（动态和声音，A8）不进这七个子包：它是数据包函数加动画贴图，走 A1 的贴图和它自己的数据包。
- 只改自己领的卡对应类别的文件夹。公共四样找 S2。代码和注释用英文。

## 2. 一个工作包实现三个函数（都可选）

```python
def build(canvas, origin=(0, 0, 0)) -> int:
    """把本包的方块和展示实体放进 canvas。坐标用 skeleton 的场景坐标，整体平移 origin。
       返回这次放了多少展示实体（给实体预算）。只放方块就返回 0。"""

def models() -> dict:            # {name: artkit.models.Model}
    """本包的自绘展示实体模型。名字必须以本类别前缀开头（§4），不许和别人重名。没有就不定义。"""

def pack(pack_dir) -> list:      # 一行行的说明文字
    """把本包自己的资源包文件写进 pack_dir，只写本类别命名空间/子目录下的（§4）。
       展示实体的物品模型不在这里写（由 models() 统一出）。没有就不定义。"""
```

- `canvas` 是 `artkit.canvas.Canvas`：`canvas.set(x,y,z,state)` 放方块（state 是方块状态串或 `(x,y,z)->串`）；
  `canvas.add_entity(x,y,z, M.display(model, scale=, yaw=, turns=, brightness=))` 放展示实体。
- 放方块只认占用表角色名：`from scenes.obs.common import blocks as B` → `B.ASHLAR_FINE.block`、`B.IRON_RIVETED.slab + "[type=top]"`、`B.PANELS["dial"]`。不直接写被重画方块的原名。
- 取坐标只认骨架：`from scenes.obs.common import skeleton as S` → `S.pilaster_z(j)`、`S.WINDOW`、`S.DOME_CENTRE`、`S.east_wall_x(bay)`、`S.BUDGET`。
- 取颜色只认色板：`from scenes.obs.common import palette as P` → `P.mat("iron")`、`P.colour("brass", 3)`。缺颜色群里向 A0 提，不自定义。
- 最小例子：`props/lamps.py`（一个模型 + `build()` 摆两个）、`main/massing.py`（白模）、`materials/stone.py`（`pack()` 重画方块）。

## 3. 怎么注册一个新包（不改共享列表，两个人各加一个包不冲突）

**加一个包 = 在类别文件夹里加一个模块。** 类别子包用 `common/assembly.py` **自动发现**本文件夹里的所有模块，
把它们的 `build/models/pack` 汇总。没有谁要改的“总列表”，所以两个人同时各加一个模块永不冲突。

- 模块按名字排序执行；要排在别的包后面就把名字起靠后（如 `10_ground.py`、`20_walls.py`），或牵头人在细化稿里写明。
- 名字以 `_` 开头的模块（放共用 helper，如 `props/_kit.py`）和 `mood` 模块不参与自动发现。
- 类别子包的 `__init__.py` 是固定样板（`_cat = assembly.category(__name__)`，转发三个函数），别去改它，只加你的模块。

总场景 `scenes/obs/__init__.py` 的 `LINES` 列出七个类别，按铺设顺序（材质、天空不放方块；场地先铺地，再主楼壳子，机械、室内，最后道具）。它的 `build()` 依次调各类别的 `build(c, ORIGIN=(0,0,0))`；`build_models()` 合并七个类别的模型（重名直接报错）；`write_pack()` 依次调各类别的 `pack()`。光在 `sky/mood.py`，`obs.BIOME` 默认 `obs_blue`（另有 `obs_deep`、`obs_glow`）。

## 4. 不撞车（两个包不许写同一个文件；检查脚本会查）

- **模型名加类别前缀**：`materials`→`mat_`、`sky`→`sky_`、`main`→`bld_`、`props`→`prop_`、`site`→`site_`、`machines`→`mach_`、`interiors`→`int_`。
  模型名唯一 ⇒ `assets/c164/…` 下的物品模型/贴图文件唯一；重名 `build_models()` 抛错，`check.py` 也查。
- **资源包里谁写哪**：
  - `materials`(A1)：方块贴图和重定向——`assets/minecraft/blockstates/*`、`assets/minecraft/models/block/*`、`assets/c164/textures/block/*`、替换的原版贴图。**只有 A1 写这些。**
  - `sky`(A2)：`assets/minecraft/textures/environment/*`（彗星、云、星）。光的 biome/timeline 在 `sky/mood.py`（那是数据包，驱动器单独处理，不在 `pack()` 里）。
  - 其余五个类别：`pack()` 一般不写文件，只用 A1 的方块和自己的展示实体模型。
- 要一种新方块材质/新色阶：群里点名 A1 和 S2，S2 改占用表/色板、A1 画。不自己占方块、不自己建色板。

## 5. 每个包的测试场景

一个包要能单独出图验收。约定（`PIPELINE.md` 4.2 的命名 `obs_<类别缩写>_<包名>`，缩写 mat/sky/main/site/mach/props/int）：

```
build/scenes/obs_<缩写>_<包名>/
  __init__.py     def build(): 建 Canvas，调本包的 build(c,(0,0,0))（或本类别的），返回 c；设 BIOME="obs_blue"
  mood.py         from scenes.obs.sky.mood import BIOMES, TIMELINES    # 一行，复用总装的光
  shots.json      [{"name":.., "pos":[x,y,z], "look_at":[x,y,z], "time": 可省}]  视角至少含一远、一近、一和相邻东西同框
  props.py        （可选，要出模型陈列时）def build_models(): return <本包>.models()；GALLERY 照 scenes/skyobs/props.py
```

- 离线出图（自查，谁都能跑；**在管理员电脑上**经 `bin/job.py`，云端那台 4 核机只改代码，不出图不生成大场景）：
  `render.py obs_<缩写>_<包名> --shots scenes/obs_<缩写>_<包名>/shots.json --out '@out/...'`。
- 真机图、把总场景摆进测试服：拿出图钥匙的人（S1）统一跑，各包别自己开游戏。
- 材质板、入口样板段、各房间盒子场景都按这个来；和 S2 对齐后建。

## 6. 交付前自查，交付消息

交付前自己先跑技术检查（`tools/check.py`，在管理员电脑上经 `bin/job.py`；云端只做语法级轻检）：

```
python3 tools/check.py --scene obs                       # 从头生成、色板外颜色、资源包文件冲突、实体预算
python3 tools/check.py --scene obs_<缩写>_<包名>          # 查你的包
```

过了按 `PIPELINE.md` 4.3 发群，点名 S2：

```
【交付】<类别>/<包名> <分支> <提交前七位> 自查图：<文件名>
```

S2 复跑检查，过了合并进总装分支、发【合并】点名出图工位和一个交叉看的人；不过发【技检】退回写明原因，点名做包的人。

## 7. 实体预算（骨架 `S.BUDGET`，R1 0.4）

全图 ≤ 3000，单看板视角 ≤ 600。室外道具 1100、室内 1000（每间 ≤250）、大型机械 400、总装留用 500。
单视角道具 ≤ 400；样板段（5 跨）≤ 120。`build()` 必须返回实体数，S2 据此盯预算。
