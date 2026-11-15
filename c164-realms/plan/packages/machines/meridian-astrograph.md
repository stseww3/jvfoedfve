# machines/meridian-astrograph 子午环和天体照相仪

- 类别：machines　优先级：P2　领卡：第 3 班 sdome（c328，节点 node42），总监助理 #55276 派，名单 8ec31549。没有前任，分支 `cursor/c164-sdome-astro-f3-1fe7` 从总装头开。评审 cr3（c347）。

## 目标
方案 §7.2「子午环、天体照相仪」，细化稿 A5 §2.9。子午仪小屋里的子午环：一架只会在子午面里俯仰的望远镜，星过地上那条黄铜线就过它的十字丝，轴上两只大刻度环读高度。小穹顶里的天体照相仪：短粗的铆接铁筒，一头是黄铜座里的照相物镜，一头是木头的底片匣，背上骑一支细的导星镜，今晚朝西对着彗头。两件和大折射镜（machines/refractor）是一套。视角：小屋近景、小穹顶室内近景、从露台和缝外看缝里的物镜。V11 里小穹顶的缝朝西，看不到仪器。

## 约束
- 位置都读骨架和壳的包，不自己定：
  - 子午环立在 `site.outbuildings.HUT_AXIS`（35.5, 2.0, −29.5），两墩在 `HUT_PIERS`（33, 0, −30）、（37, 0, −30）。小屋净空 x 32..38、z −33..−27，平顶底面高 3.5，子午线那一列（x 35）从南门到北山墙朝天敞开一格宽（outb c340 分支头 69b57fe8 的数；他的包进了总装，`meridian.check()` 逐项对）。
  - 照相仪立在小穹顶轴线（12.5, 30.5）上，地面 y 18；圆顶室 y 18..19 五格宽、y 20 以上七格宽，缝朝西一格宽，顶点 `S.SMALL_DOME_APEX` = 26。`astro.check()` 把每一件的每个角对着 `main.smalldome` 建出来的壳查。
- 指向：子午环对着北极星（正北，仰角等于纬度 `S.LATITUDE` = 45°），是夜里头一个读数，验轴还东西向不；照相仪对着彗头（正西，仰角读 `sky.comet.HEAD_ELEVATION`，41.05°），和大折射镜平行，极轴朝北仰 45°，筒在架的东侧，平衡重垂在西北下方。
- 尺寸（卡的原数在括号里）：子午环筒 ⌀0.8×3.75（×4；轴高 2.0，筒从轴到两头各 30 像素，翻过去不碰地）；刻度环 ⌀2.75（⌀3；小屋平顶底面 3.5，环顶 3.375）；墩 1×1，连叉臂上的读数显微镜到 3.09。照相仪筒 ⌀1.1×5.8（⌀1.2×6；物镜口离壳里皮 0.26，底片匣背离地 1.1）。
- 16 像素一格，`px = scale`：子午环的筒、环、墩 scale 2，提灯 scale 1；照相仪的筒 scale 2，机背、赤纬轴件、架 scale 1（⌀2.75 的环画成 scale 2，和筒一起转）。
- 料只用色板：筒板 `iron` 亮一级，铸件 `iron`、`iron_dark`，轴 `iron` 再亮一级，箍、环、物镜座 `brass`、`brass_dark`，机背 `dark_wood`，玻璃 `night_glass`，提灯的光 `glow`，转仪钟表盘 `cream`。母题照 scope（c344）的数：箍宽 3 压在每道搭接上、铆钉节距 3，纵缝节距 4、相邻两节错开一面，头一道箍黄铜，物镜座带一圈螺钉，刻度环六辐。
- 光：照相仪不带灯（换底片在黑里）。子午环西墩外侧一盏小黄铜提灯，牛眼对着空心轴照十字丝，是小屋里唯一的光：`_lightkit.suggest(canvas, (32, 2, −30), 4, "machines/meridian:lamp", rank=3)`，收不收、几级归 lights（c331）。所有件的显示亮度 `(10, 7)`，和大折射镜一样。
- 动：望远镜这一类这一版不动（`plan/parts/motion.md` §1），件照样拆好、锚点落在轴上：子午环的筒和两只环绕各自模型的 x 轴；照相仪的筒和机背绕赤纬轴，赤纬轴件绕极轴。没有向 motion 登记。
- 实体：子午环 6（两墩、筒、两环、提灯），照相仪 4（架、赤纬轴件、筒、机背），共 10；卡的预算约 25。`build()` 返回实体数。

## 件
| 模型 | scale | 是什么 |
|---|---|---|
| `mach_meridian_tube` | 2 | 中间一只铸铁方匣；两头各一节铆接铁板的锥筒，一头黄铜物镜座，一头测微目镜和两只小寻星环；两侧各半根轴，铸铁锥、黄铜领、钢轴颈 |
| `mach_meridian_circle` | 2 | 刻度环：带刻度的黄铜圈、里面一道加劲圈、六辐、毂。筒两侧各一只 |
| `mach_meridian_pier` | 2 | 墩：铸铁脚、三节角铁包边的铁壳、盖板、黄铜轴承；盖板上一副叉臂，各托一支读数显微镜到环的刻度圈上。东西各一只（同一个模型转半圈） |
| `mach_meridian_lamp` | 1 | 西墩外侧托架上的黄铜提灯：牛眼朝轴颈，朝门一道玻璃缝 |
| `mach_astro_tube` | 2 | 筒：露罩、照相物镜、带螺钉圈的黄铜座、三节铆接铁板和箍、尾锥；鞍座和两道抱箍；背上两只环托着导星镜；侧面一根微动杆和手轮 |
| `mach_astro_back` | 1 | 机背：包黄铜角的木匣、对焦螺旋、底片匣、抽出一半的遮光板 |
| `mach_astro_axis` | 1 | 赤纬轴件：极轴头、赤纬套筒、钢轴、赤纬度盘、两只平衡重 |
| `mach_astro_mount` | 1 | 架：铸铁脚、两节铁柱、头座和两片夹板夹着按纬度仰起的极轴套筒；极轴下端的时角度盘和蜗轮；柱西面的转仪钟和通到蜗杆的传动杆 |

## 交付物
- `build/scenes/obs/machines/meridian.py`：子午环（`build(canvas, origin, lamp, brightness)`、`models()`、`axis()`、`eyepiece()`、`objective()`、`sweep()`、`lamp_cell()`、`check()`）。两台仪器共用的画法也在这个文件里（`Draw`、`Riveted`、`Graduated`、`circle`、`upright`、`corner_irons`、`pose`、`put`、`corners`），`astro.py` 从这里读。卡上写的 `machines/_kit.py` 没有建：machines 没有牵头，带下划线的公用文件不是一张卡能占的，等有了牵头再搬。
- `build/scenes/obs/machines/astro.py`：照相仪（`build(canvas, origin, brightness)`、`models()`、`pivot()`、`head()`、`foot()`、`objective()`、`plate()`、`sweep()`、`check()`）。
- `python -m scenes.obs.machines.meridian`、`python -m scenes.obs.machines.astro`：打印各自的数和自查。
- 测试场景 `build/scenes/obs_mach_meridian_astrograph/`（`python -m scenes.obs_mach_meridian_astrograph` 重写 `shots.json`），三处：
  - 小屋：在前庭上它自己的位置。`site.outbuildings` 在树里就把它的壳另建一份、整格搬小屋那一块过来；不在树里用同样的数搭一个替身。
  - 小穹顶：`main.smalldome` 原样建在南端亭平屋面的替身上（y 17 一层板、门前一块铁板）。
  - 陈列台：两台仪器各再摆一份在平地上、一面素墙前，正午光，离开房间看件本身。
  - 机位 20 个：小屋 8（门口、东南角、西南角、西北角回看物镜、环和显微镜近看、目镜端近看、顺着筒从缝外看物镜、前庭上正对门）；小穹顶 7（西门口、南墙、北墙、底片匣近看、从底片匣旁顺筒看缝、缝外看物镜、露台上走向门）；陈列台 5。

## 验收
- 五项都看，重点「风格逻辑」（看得懂子午环只能南北摆、照相仪在拍；轴承、夹板、蜗轮、转仪钟各有去处）和「质感像素」（刻度环、筒、铆钉近看；和大折射镜成一套）。
- `python -m scenes.obs.machines.meridian check`、`python -m scenes.obs.machines.astro check` 都过；`tools/check.py --scene obs_mach_meridian_astrograph` 没有 FAIL。

## 版本
1 版。

## 依赖
- 依赖：骨架、色板；`site/outbuildings`（小屋和它的数）、`main/smalldome`（圆顶室）；`machines/refractor`（母题）；`sky/comet`（彗头仰角）、`sky/_lightkit`（报灯）。
- 被依赖：`main/smalldome` 的 slit、terrace、west_high 三张图（缝里要看到仪器）；motion（以后要动的话，件和轴都备好了）。

## 记录
### 第 1 班
- A5 领（牵头），只有这张卡的草稿，没有代码。默认：子午环东西轴、对小屋南北缝；照相仪在小穹顶朝缝。

### 第 3 班（c328，11-16，图都在 node42 上出）
- 接口，读对方第 3 班分支的代码核的：
  - outb（c340，`cursor/c164-outb-f3-f4b8` 头 69b57fe8）：`HUT_AXIS`、`HUT_PIERS` 和净空见“约束”。他的屋顶从坡顶改成了平顶（底面 3.5），刻度环因此从 ⌀3 收到 ⌀2.75。
  - scope（c344，`cursor/c164-scope-f3-eeae` 头 d8a0aa4c）：母题的数见“约束”；他的显示亮度 `(10, 7)`、灯 4 级 rank 3，照用。
  - 小穹顶是自己另一张卡（main/smalldome）：顶点 11-16 从 25 改成 26（总监 #57140），圆顶里高了一格，筒从 5.3 加长到 5.8。
- 卡上和做出来不一样的：刻度环 ⌀2.75 不是 ⌀3、scale 2 不是 1；照相仪筒 5.8 不是 6；没有建 `machines/_kit.py`；加了一盏提灯（卡上“可选”）；加了 `mach_astro_axis`（赤纬轴件单拆出来，才能绕极轴转）。
