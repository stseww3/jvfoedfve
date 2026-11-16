# props/nameplates 机器铭牌、全站的号、全站一套字

**来历**：管理员 11-16 12:40 的方向（「再加 10 倍细节……一定要细和贴合地图」），总监的 `plan/fine.md` 第 4 节把设定收在一处：机器铭牌全站一个样（椭圆黄铜牌，台徽在左，`No.` 加两位数），号一张表归 a6（`plan/parts/numbers.md`）；全站一套字，a6 发取字的函数；报时球的说明牌改成 `It drops on the hour, to the second.`。a6 做，自己批（props 的审批人）。

**是什么**
- 铭牌 `prop_nameplate_NN`（`build/scenes/obs/props/nameplates.py`）：一块两头半圆的长圆黄铜片，52×17 个纹素、一个纹素 1/96 格（0.54×0.18 格，离面 1/64 格）。边一圈深黄铜，面上沿亮一级、下沿暗一级；刻进去的填黑：左端台徽（13 纹素：圆环、竖着穿过并两头出头的子午线、右上环内不碰线的星点，照 `props/signs` 定的缩小规矩），右边 `No. NN`（字高 7 纹素 = 0.07 格）。
- 每个号一个模型（01 到 99 都有），只画朝外的一面。小档 `M.SMALL`（16 格内才画），不发光，吃所在格的光。
- 取字的函数在 `props/_kit.py`：`K.letters(text, ink="#", clear=".")`（8 行字符，可直接进 Sprite）、`K.lettered(text)`（宽）、`K.inscribe(rows, text, x, y, ink)`（写进自己的图）。字形是游戏自带的那一套（说明牌的文字展示实体用的就是它），构建时从客户端 jar 读，仓库里不存字母。
- 说明牌 `plaques.TEXT["time_ball"]` 的句子换成 `It drops on the hour, to the second.`。

**接口**
- `nameplates.plate(canvas, number, pos, facing="south", origin=(0, 0, 0), yaw=None, what=None, **opts)`：`pos` 是牌子中心在所贴面上的点；返回 1。表里还没有的号要写 `what="是什么机器"`（a6 回了号就能挂，不等表），不写报错。
- `nameplates.hung(canvas)`：挂了哪些号；`nameplates.unlisted(canvas)`：其中表里还没有的（a6 补表用）。
- `nameplates.NUMBERS`：号 → 机器；`nameplates.words(number)`：牌上的字；`nameplates.picture(number)`：牌面的字符行（别的包要把铭牌画进自己的贴图时用，不另画）。
- 这个模块自己不往主场景里摆东西（`build` 没有）：牌子由机器的主人摆。

**花费**：一台机器一个展示实体，小档；没有命令。

**测试场景** `obs_props_nameplates`：一面朝南的墙，三格铁板、三格细琢石；眼睛高度一排六块（01、13、31、41、61、73），铁板上低处一块（14，像贴在机座上）。机位 `one`、`two`、`three`、`stone_two`：离墙一、二、三格和石头上的二格。

**近景机位（给 s1）**：等第一批机器摆上牌子以后，随各自的卡给。

## 记录

1. 11-16 13:15（a6）：头一版，b93397c7。node48 上 `check.py --scene obs_props_nameplates` PASS（7 个实体，views 7，没有会动的）；`obs_props_plaques`、`obs_props_plaques_site` 改句子以后也 PASS。四张自查图 f77471d7（`renders/obs_props_nameplates/`）：字不反，二格处 `No. 13`、`No. 31` 读得出，三格处认得出是号牌，台徽在一格处看得清环、线、星。
   - 检查里有一条提醒：`prop_nameplate_NN: 96/96/96 pixels to the block ... not 16`。是有意的：要在两格处读的字做不到 16 像素一格（`plan/fine.md` 的近层就是字和痕迹；说明牌的文字展示实体更细）。别的包用 `K.letters` 做小字牌也会有这一条。
   - 牌子是一张片：没有螺钉头（左端是台徽，放不下）。近层再要的话加在上下沿中间。
2. 11-16 13:25（a6）：要号的人多，每个号都等我合一次表太慢。改成：01 到 99 的牌子模型都在包里；我私信回了号，主人挂的时候写 `what=`，不等表；`hung()`、`unlisted()` 给我补表用。表里补了 58（大圆顶室配电板，a3）、68（量片仪，chart），57 定给星图室那台三脚镜。
