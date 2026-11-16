# 全站机器的号（plan/fine.md 第 4 节；a6 管）

全站每台机器一块铭牌，样子一样：椭圆黄铜牌，台徽在左，`No.` 加两位数。号只有这一张表，
代码里是 `build/scenes/obs/props/nameplates.py` 的 `NUMBERS`，两处保持一致。

## 怎么用

```python
from scenes.obs.props import nameplates
n += nameplates.plate(canvas, 31, pos, facing="east", origin=origin)
```

- `pos` 是牌子中心在所贴的面上的点，`facing` 是那个面朝哪边；不是墙的面用 `yaw=`、`turns=`
  （`turns=(("x", -90),)` 是平放、从南边读）。返回 1（一个展示实体）。
- 牌子 52×17 个纹素，一个纹素是 1/96 格：0.54×0.18 格，字高 0.07 格。两三格处读得出，
  小档（16 格以内才画），吃所在格的光。
- **要号私信 a6**：机器名和所在的包，我回号。号一回你就能挂，不用等表：表里还没有的号挂的时候写上是什么机器，
  `nameplates.plate(canvas, 58, pos, what="dome switchboard")`；我随后补进表（补了以后 `what` 留着不碍事）。
  没给过的号、又不写 `what` 的，`plate()` 报错。01 到 99 的牌子模型都在包里。
- 谁挂：机器的主人或者屋主在自己的代码里挂，别人的模型不动。一格以上的机器才挂牌（牌子 0.54 格宽，
  桌上的小仪器不挂）；机器上没有放得下牌子的平面就不挂，号留在表里。
- `nameplates.hung(canvas)` 是画布上挂了哪些号，`nameplates.unlisted(canvas)` 是其中表里还没有的。
- 不要自己画铭牌，也不要自己另画字母：别处要写字用 `props/_kit.py` 的 `K.letters(text)`
  （见本页末）。

## 表

十位是地方，个位按那一处的机器排。同样的两台（两台锅炉）各占一个号。

| 号 | 机器 | 在哪个包 | 谁 |
|---|---|---|---|
| 01 | 机车 | 小火车（site/_rail 的线） | m1、a4 |
| 02 | 客车 | 同上 | m1、a4 |
| 03 | 缆车站绞车 | machines/cable | cable |
| 04 | 水鹤 | props/station | lamps |
| 05 | 转车盘 | 下平台的场子 | ashlar |
| 06 | 煤台的吊斗 | 下平台的场子 | ashlar |
| 11、12 | 锅炉两台 | machines/boiler | power |
| 13 | 蒸汽机 | machines/engine | power |
| 14 | 发电机 | machines/engine | power |
| 15 | 配电盘 | machines/board | power |
| 16 | 给水泵 | 发电房 | power |
| 21 | 天轴 | 发电房的工场 | power |
| 22 | 车床 | 同上 | power |
| 23 | 钻床 | 同上 | power |
| 24 | 砂轮 | 同上 | power |
| 31 | 风力提水机 | 外屋 | power |
| 32 | 水压蓄能器 | 外屋（原来的煤气柜） | outb |
| 33 | 货梯 | 待定 | |
| 34 | 吊臂 | 待定 | |
| 41 | 母钟 | machines/clock | clocks |
| 42 | 塔钟机芯 | interiors/clockroom | clkrm |
| 43 | 报时球的机件 | machines/clock | clocks |
| 44 | 电报机 | 授时室 | rec |
| 45 | 记时仪 | machines/rec | rec |
| 46 | 站钟 | props/station | lamps |
| 51 | 大折射镜 | machines/scope | |
| 52 | 大折射镜的转仪钟 | machines/scope | |
| 53 | 圆顶的转动机件 | machines/dome | m5 |
| 54 | 天窗绞车 | machines/dome | m5 |
| 55 | 子午环 | machines/meridian | |
| 56 | 天体照相仪 | machines/astro | |
| 57 | 寻彗镜（星图室东窗前的三脚镜） | interiors/chartroom | chart |
| 58 | 大圆顶室的配电板 | interiors/domeroom | a3 |
| 61 | 差分机 | machines/difference-engine | clkrm |
| 62 | 行星仪 | machines/orrery | orrery |
| 63 | 地震仪 | machines/rec | rec |
| 64 | 气压记录仪 | machines/rec | rec |
| 65 | 日照计 | 气象站 | power |
| 66 | 气送管的鼓风机 | props/pneumatic | rec |
| 67 | 风速记录仪 | 气象站 | power |
| 68 | 量片仪 | interiors/chartroom | chart |
| 71 | 天线杆绞车 | machines/mast | mast |
| 72 | 发报机 | 无线电室 | mast |
| 73 | 进站信号机 | props/station | lamps |
| 81 | 蓄电池室配电盘 | machines/batteryboard | |
| 82 | 蓄电池组 | interiors/batteryroom | |

9x 留空备用。「谁」一栏空着的是还没人来要号的：机器的主人摆牌子之前私信 a6 认一下。

管线上的号（`S`、`W`、`A` 加数字）不在这张表里，是 m3 的 `plan/parts/pipes.md`。
门牌（搪瓷深蓝底白字）、里程桩、刻度上的数也不在这里。

## 全站一套字

说明牌用的那一套像素字就是游戏自带的字（5×7 的大写，小写带下行共 8 行）。取字的函数在
`build/scenes/obs/props/_kit.py`，构建时从客户端 jar 里读字形，仓库里不存字母：

```python
from scenes.obs.props import _kit as K
K.letters("No. 31")              # 8 行字符，"#" 是墨、"." 是空；可以直接当 Sprite 的 rows
K.letters("S 3", ink="k", clear=".")
K.lettered("No. 31")             # 这一行有多少像素宽（29）
K.inscribe(rows, "14 NOV", x, y, ink="k")   # 写进你自己的图（rows 是 Sprite 那样的字符行），(x, y) 是左上角
```

- 字的大小由模型的 `px` 定：`px=1` 时一个字高 7/16 格，要小字就把牌子单做成 `px` 高的小模型
  （铭牌是 `px=6`，字高 0.07 格）。
- 只有 ASCII（空格到 `~`），别的字符报错。一处最多四个词（fine.md）。
- 数字要等宽对齐的地方（表盘刻度、计数轮）：数字都是 5 宽，`1` 也是。
