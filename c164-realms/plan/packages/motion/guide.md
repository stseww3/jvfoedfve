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

### 丙·走近检测和收尾（smoke，c357；分支 `cursor/c164-smoke-guide-f3-e07b`）

- **文件**：`build/scenes/obs/motion/guide.py`（检测、收尾、登记；cr2 #80365 定的分工），测试场景 `build/scenes/obs_mot_guide/`（台架）。图、图的位置表和微光是 cloud 的 `motion/_guide_charts.py`；`guide.build()` 调它的 `build(canvas, origin)` 一次，读它的 `CHARTS`（六行：名字、图面中心、脚底 y，顺序就是 c1 到 c6）。它不在树里，或者开关没开，`guide.build()` 什么都不登记。
- **开关**：主场景的 `GUIDE` 和 `GUIDE_CHARTS`，由 mast 的 `motion/guide-title` 带进 `scenes/obs/__init__.py`（s2 #81892）；没有这两行的时候当关着。测试场景自己直接调 `guide.quest()`。
- **玩家身上的东西**：标签 `c164.c1` 到 `c164.c6`、`c164.done`；两个计分板（函数里的命令建的）：`c164g` 是他有几张，每次要显示时从标签重数；`c164f` 是收尾的光点还剩几拍。没有全局状态。中途掉线的人回来接着数，光点放到一半掉线的回来看完剩下的。
- **检测**（`motion/_kit` 的 `MK.run`，a2 为这张卡开的口，他的 81dffccf）：一条 8 刻的链。第 0 刻六条，每张图一条：`execute positioned <图前的地面> as @a[distance=..1.6,tag=!c164.cN] run function c164art:guide/cN`——选择器量的是人的脚，中心是 `(x, 脚底y, z)`，不是桌面。第 4 刻两条：目镜（`scope.OBSERVER[scope.VERSION]`，1.0 格以内，没有 `c164.done` 的人）和光点的计时（`@a[scores={c164f=1..}]`）。没人在附近时函数一个都不跑。
- **函数**（`MK.function`，写成 `c164art:guide/…`，十个）：`c1`…`c6`（打标签、数一遍、一声风铃、动作栏 `Star chart 3 of 6`）、`count`、`lens`（六张齐了转 `done`；有一到五张的动作栏 `Star charts: 3 of 6`，站着就一直有，走开三秒后自己消失；一张没有的什么都不出）、`done`（`c164.done`、标题 `THE COMET, IN FOCUS`、一声钟、光点 25 拍）、`glow`。没有 `reset`，没有只为测试用的函数。
- **声音**：`motion/sound` 的表里没有风铃也没有钟（只有钟摆、机器、汽、电报、风），所以两声直接用原版事件，不加文件、不动 `sounds.json`：拿图 `minecraft:block.note_block.chime`（音量 0.6、音高 1.2），收尾 `minecraft:block.bell.use`（1.0、0.8）；都只发给那一个人，走 `master` 音量。cr2 要的是“表里现成的”，表里没有，这一条请 cr2 定：要进表就请 sound 加两行，我改成读表。
- **光点**：`end_rod`，带观众参数只给那一个人看，`force`（粒子设成“最少”的客户端也看得见）。沿穹顶缝（朝西，`S.DOME_AXIS`、`S.DOME_SPRING`、半径 `S.DOME_R`）从缝脚上方（起拱线以上 14 度）一拍一拍升到缝头下面（78 度），每拍三粒、横着错开，各自沿弧往上飘一格左右；十秒 25 拍共 75 粒，一粒活 3 到 3.6 秒，同时最多 27 粒（cr2 的线是 40）。从 26.3 的类文件里核的 `end_rod`（`EndRodParticle`、`SimpleAnimatedParticle`）：活 60 到 71 刻，给的速度照用、每刻乘 0.91（所以每刻 0.10 格的初速一共走 1.1 格），微微下沉，自己发亮，`move` 被改写成只挪位置——不算碰撞，穿得过方块。位置都在缝的格子里（`main/_dome` 的缝：x 到 2 为止、z 从 -2 到 2、25 行以上全空）。
- **预算，和 a2 对过**（a2 #80785、#81586）：卡上写每 4 刻查一次；**改成 8 刻，a2 同意的**。理由：冲刺每秒 5.6 格，穿过一张图 3.2 格的检测球最少要 11 刻，8 刻一查漏不了走过或跑过的人，停下来的人 0.4 秒内拿到；4 刻要多花一倍的命令。这条链每 8 刻 11 条命令（守卫 1、调度 2、图 6、目镜 1、计时 1），合每秒 27.5 条；加上 cloud 的微光每秒 3 条，丙一共每秒 30 条上下（卡的线是 40）。a2 算的全场：每刻平均 6.7 条（限 10），最忙一刻不过 21 条（限 40）。只有丙的画布上 `MK.check` 是 PASS（最忙一刻 9 条，平均每刻 1.5 条）。
- **还没验的**：节点池 10:57 起断着，`check.py` 和真机都没跑过；上面的数是登记以后在合用机上只算计划（不出图、不跑检查）得到的。真机上要看的四件事写在 `obs_mot_guide` 的开头。命令的写法照 `tools/export.py` 已经在 26.3 上跑过的那几种（`title … actionbar [{text:…},{score:…}]`、`return run function`）。从 26.3 的类文件和声音表里核过的：`particle` 命令有观众参数（`ParticleCommand`：name、pos、delta、speed、count、force|normal、viewers），`title` 有 `times`，两个声音事件都在。
