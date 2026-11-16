# motion/guide 导览：进场标题、说明牌、六张星图

总监 11-16 11:02 开的卡，**11:13 照官方的投稿规矩改过一遍（改的地方标了「改」）**。管理员要把这张图投 Realms 的内容评审，类别「体验」（Experience）。10:56 查 A6 的存档：里面一个字都没有，没有标题、署名、说明牌，也没有任何要人动手的事。这张卡补一层轻的。**不挡 11:30 的候选版；第一版 11:50 前交，随 12:00 的整包。**

## 规矩里和这张卡有关的（官方 Atlas 的 Realms Map Guidelines，2026-11-03 版；outb 逐条摘过，在 `plan/reviews/export/realms-rules.md` 第 8 节；和红线第 3 条「地图里的文字只用数字、符号和少量英文」一致）

- 「体验」类是「没有特定目标、让人逛、体验、观看」的图；**加了故事就成了「冒险」**，加了计时就成了「小游戏」。所以这一层不能把图变成一个有任务的图：星图是彩蛋，不是任务。
- 「让建筑自己说话，少用牌子和书。」牌子要少、要短。
- 「不要滥用副标题和首领栏，不要一条接一条地刷消息。」标题只放一次，动作栏只在人做了事的时候出。
- 可以在图里给自己和合作者署名（一处，得体）；不能给别人、给服务器、给公司打广告。
- 名字不能和已发布的图重名，不能带 Minecraft，不要用 mine、craft、block、cube、pixel 这些词。**不叫 Comet Observatory**（任天堂《超级马力欧银河》里的地名）。
- Realms 上最多 11 个人同时在线（10 个加主人），人随时进出、掉线。
- 不能留给作者占便宜的后门命令和测试工具。

## 目标

三样，各交各的：

### 甲 进场标题和署名（mast c346；钩子在 outb 的 `c164map:first`，文字和函数在本包）

- 第一次进来的人（`c164map:first` 那一刻），对他一个人：标题 `MAP_TITLE`，副标题 `An evening above the clouds`（淡入 20、停 80、淡出 30 tick）。**改：进场不再用动作栏交代星图的事。**
- 再进服的人不放标题，什么都不说。**改。**
- `MAP_TITLE` 是一个常量，现在写 `BLUE HOUR OBSERVATORY`（占位；管理员定名以后只改这一处，导出的存档名、资源包说明都从它来，和 outb 对）。
- 署名牌一块，在站台出口右手边的墙上（和乙的牌同一个样子）：第一行 `MAP_TITLE`，第二行 `Built by <名字>`。名字是常量 `MAP_CREDIT`，等管理员给，先写 `c164`。全图只有这一处署名，不写网址。

### 乙 说明牌（rec c356、ashlar c353；props 类，审批 a6）

- 做法：`text_display`，固定朝向、贴墙或立在矮座上、朝着人来的方向；底色搪瓷蓝（方案的 `#172c57`，不透明），字米白（`#f2ead6`）；亮度写死（夜里读得清，不发亮成灯）。有现成的搪瓷铭牌边框（`sign_nameplate`）就套上，没有就不要边框，不新做模型。
- **改：一块牌两行，第一行是件的名字（全大写），第二行一句，不超过九个词。**十二块，文字用下面的（做的人可以改得更准，只许更短；只许英文，不许出现真实的人名、年份、机构、地名）：

| 牌 | 放哪 | 第二行 |
| --- | --- | --- |
| CABLE STATION | 站台，出口旁 | The only way up the mountain. |
| THE MERIDIAN LINE | 前庭，子午线东端 | Brass, laid true north and south. |
| ARMILLARY SPHERE | 前庭，浑天仪座 | The great circles of the sky, in brass. |
| THE ORRERY | 星厅，进门右手 | Six planets, geared to their true periods. |
| THE MASTER CLOCK | 星厅，母钟旁 | One pendulum. Every dial here follows it. |
| TIME ROOM | 授时室，进门 | The hour goes out from here by wire. |
| CHART ROOM | 星图室，进门 | Each clear night is drawn here by hand. |
| PLATE VAULT | 底片库，进门 | A glass plate for every clear night. |
| THE GREAT REFRACTOR | 穹顶室，台阶口 | Tonight it is turned on the comet. |
| TIME BALL | 钟塔脚 | It drops once a day, on the second. |
| POWER HOUSE | 发电房门口 | Steam turns the dynamo that lights the lamps. |
| SUNSET TERRACE | 落日平台入口 | The comet sets an hour behind the sun. |

- 位置读各包导出的常量；牌不挡路（`text_display` 没有碰撞）；一个机位里看得见的牌不超过两块，V1 到 V12 的十二张看板图里牌不抢主角（牌面在画面里的亮度不过 0.35，不在画面正中三分之一里）。

### 丙 六张星图，是彩蛋（smoke c357 写走近检测和收尾，cloud c329 摆图和粒子；motion 类，审批 cr2）

- 六张星图，一处一张：发电房（配电盘前的桌上）、授时室、星图室长桌、底片库、钟塔脚或蓄电池室（二选一，做的人定）、落日平台三脚架望远镜旁。用现成的星图模型，不新做；旁边每两秒一小点微光粒子，让人看得见该走近。
- 人走到一张图 1.6 格以内、而且还没拿过这一张：给他记上这一张（玩家身上的标签 `c164.c1` 到 `c164.c6`），只对他放一声轻的提示音（`motion/sound` 表里现成的事件或原版的风铃声，不加声音文件），动作栏 `Star chart 3 of 6`。图不消失（别的人还要拿）。**改：没有人先告诉他要找；拿到第一张，动作栏的「1 of 6」就是全部的提示。**
- 收尾：六张齐了的人站到大折射镜目镜前的那一级台阶上（位置读 `machines/scope`）：标题 `THE COMET, IN FOCUS`（**改：没有副标题，不说谢谢，不讲故事**），一声钟，穹顶缝里十秒钟往上飘的光点；给他打 `c164.done`，以后再站上去什么都不出。没齐的人站上去：拿过至少一张的，动作栏 `Star charts: 3 of 6`；一张都没拿过的，什么都不出。
- 全是每个人自己的状态（玩家身上的标签），没有全局状态：十一个人同时玩互不影响，退了再进接着来，掉线不坏。
- **改：不留 `reset` 这类给主人用的函数**（规矩不许留测试工具；要重来的人让主人重置世界位）。

## 约束

- 纯原版、只用函数和标签：不加进度、战利品表、谓词、任何注册表文件（`check.py` 见到就 FAIL）；计分板用函数里的命令建。不发聊天栏消息，不给物品，不改游戏模式。不用首领栏。
- 每刻的命令走 `motion/loop` 的登记（a2 的 `_kit.py`）；走近检测每 4 tick 一次，本包平均每秒不超过 40 条命令，和 a2 对一句预算。
- 全英文。字用游戏默认字体，不加字体文件。
- 开关：主场景里一个常量 `GUIDE = True`；outb 的导出加一个 `--no-guide`，能出不带这一层的包。丙单独还有一个 `GUIDE_CHARTS = True`，可以只关星图。
- outb 的验证里「quiet」那一项（进服以后什么都没说）改成：聊天栏里什么都没有；标题和动作栏按这张卡核。成品的数据包里只有运动循环、进服、掉落和这一层的函数（outb 导出时已经把搭建用的去掉了），这一层不带任何只为测试用的函数。

## 验收

- `check.py` 过；导出的冷启动验证过；数据包里还是只有函数和标签。
- s1 用真客户端进导出的存档走一遍：标题出现一次；十二块牌每块读得清、不穿墙、不挡路；六张图都拿得到，计数对；齐了以后目镜前的收尾出现；退了再进进度还在；四个客户端同时在线互不影响（s1 有四台真机）。
- 看板十二张图的分不因为牌掉下去。

## 人

aide 11:07 派的：甲 mast；乙 rec、ashlar（一人六块，楼的东西两半自己分）；丙 smoke、cloud。手上给 11:30 版的短活先交完，最迟 11:20 动手。

## 记录

（做的人写在下面。）

### 甲 进场标题和署名牌（mast c346；包名 `motion/guide-title`，分支 `cursor/c164-mast-guide-f3-fc27`）

- 文件：`build/scenes/obs/motion/guide_title.py`，测试场景 `build/scenes/obs_mot_guide_title/`。主场景 `scenes/obs/__init__.py` 加了两行开关 `GUIDE`、`GUIDE_CHARTS`（s2 11:22 同意随这一包带，只加不改）。
- 名字只写在一处：`guide_title.MAP_TITLE = ("BLUE HOUR", "OBSERVATORY")`（占位）和 `MAP_CREDIT = "c164"`。`MAP_NAME` 是两段拼成的一行，outb 的存档名和两个包的说明读它，署名牌也用它。管理员定名只改这两行。
- 标题为什么分两行（总监 11:30 定）：游戏把标题放大四倍画，不换行也不缩小，超宽的部分两头被屏幕切掉。界面自动比例下 16:9 的屏幕宽 427（720p、1440p、4K）或 480（1080p），标题槽只容 106 个字体像素，约 17 个大写字母。`BLUE HOUR OBSERVATORY` 写成一行是 121。现在第一段进标题槽（51 像素），第二段进副标题那一号字（65 像素）；`An evening above the clouds` 不要了。
- 宽度的校验：`guide_title.misfits()` 量两段；上段超过 106、下段超过 149 像素，`functions()` 报错，带导览的场景搭不起来，`check.py` 的 regen 就是 FAIL。改名的人不会在不知情的时候得到一个被切掉的标题。
- 数据包里三个函数，由 a2 的 `MK.function` 写，outb 的函数标签 `#c164map:first`、`#c164map:join` 点名：
  - `c164art:guide/first`：新来的人，一次。给他打标签 `c164.new`，排 40 tick 以后发标题。
  - `c164art:guide/join`：每次进服。只有身上还带着 `c164.new` 的人重排一次（掉线在那两秒里的人，回来补发）；别人什么都不出。
  - `c164art:guide/title`：到点。对带标签又在线的人发 `title … times 20 80 30`、副标题、标题各一条，摘标签。
- 延后 40 tick 是 outb 提的：`first` 跑的那一刻真客户端还在「载入地形」的画面，标题会在那张画面后面耗掉。排程用游戏的 replace：两秒之内又来一个新人，两个人的标题一起挪到后一个人进来之后两秒。
- 预算（和 a2 对过，11:32 他记了账）：没有每刻的命令，不上循环。新来一个人前后 7 条，别人每次进服 1 条。
- 字：两行都是铭牌的米白 `#f2ead6`，游戏默认字体，没有字体文件。
- 署名牌：用 a6 的 `props/plaques.sign()`，一块，`BLUE HOUR OBSERVATORY` / `Built by c164`。挂在候车室正面（朝南那面墙）门东边的墙墩上，牌心 (84.5, −2.5, −36.0)，比眼睛低一点；人从车里出来往西走，它在右手，脚下是那堆行李。V1 里没有它（牌面那个高度上，正面只有 x 82.4 以西进画面，牌在 84 到 85 之间）；别的看板机位离它都在 39 格以外，牌 16 格外不画。ashlar 的 CABLE STATION 不挂这面墙（11:36 告诉了他）。
- 依赖：`props/plaques` 11:43 进了总装（404dcc3e），这条分支并了它，署名牌在测试场景里挂上了（4 个 `text_display`）。树里没有它的时候只有标题、没有牌。带着 a2 的 81dffccf（`MK.function`）。
- 离线图里既没有标题也没有牌：标题画在玩家的屏幕上，离线渲染器不画 `text_display`。两样都要在真机上看：outb 的 verify 数标题的包，s1 用真客户端走一遍。
- 开关：主场景 `GUIDE = False`（导出 `--no-guide`）时不登记函数、不挂牌，数据包里没有 `guide/` 这个文件夹。
- 跑过的（节点池断着，没有整套关口，也没有离线留图）：
  - 本场景的 check（lights 在 node7 代投，op_28196c17bc，提交 725d12cd）：`result: PASS (0 failed, 1 with warnings)`，444 个实体；motion 一项 10 条命令的最忙一刻、平均每刻 4.1 条，都是烟和声音的，标题不在循环上。剩的一条 WARN 是 V1 里浑天仪挡大窗，不是这一包的。
  - 进游戏的验证（outb，node4，提交 ca2e7516 加他的钩子分支，试跑分支 `cursor/c164-outb-hooktest-f4b8` 64acc11a）：47 项全过。新来的人收到标题 BLUE HOUR、副标题 OBSERVATORY 各一次；再进服标题、副标题、动作栏都没有；聊天栏空；控制台 0 警告；存档名和两个包的说明是 BLUE HOUR OBSERVATORY。那一份存档里还没有牌（当时树里没有 `props/plaques`）。
- 还要在真机上看的：标题两行在屏幕上的样子（s1 的四台真机）；署名牌读不读得清、离行李和门的距离顺不顺眼、夜里亮不亮过墙（牌的亮度和视距是 `props/plaques` 的常量，跟着十二块牌走）。
