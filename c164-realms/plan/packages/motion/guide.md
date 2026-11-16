# motion/guide 导览：进场标题、说明牌、六张星图

总监 11-16 11:05 开的卡。管理员要把这张图投 Realms 的内容评审，类别「体验」（Experience）。11:00 查 A6 的存档：里面一个字都没有，没有标题、署名、说明牌，也没有任何要人动手的事，评审容易当它只是建筑展示。这张卡补一层轻的：让人知道这是什么、每件东西是什么、有一件事可做、做完有个收尾。**不挡 11:30 的候选版；第一版 11:50 前交，随 12:00 的整包。**

## 目标

三样，三个人并着做，各交各的：

### 甲 进场标题和署名（`common/export` 的进服函数里挂一个钩子，outb；文字和函数在本包）

- 新来的人被打上 `c164.in` 的那一刻，对他一个人：
  - 标题 `THE COMET OBSERVATORY`，副标题 `An evening above the clouds`（淡入 20、停 80、淡出 30 tick）。
  - 标题退了以后，动作栏一行：`Six star charts are hidden in the observatory. Find them, then look through the great telescope.`（停 8 秒）。
- 再进服的人（已有 `c164.in`）不再放标题，只在动作栏报进度（`Star charts: 3 of 6`）。
- 署名牌一块，在站台出口右手边的墙上（和乙的牌同一个样子）：`THE COMET OBSERVATORY` / `Built by <名字>`。名字等管理员给，先写 `c164`，写成一个常量。

### 乙 说明牌（props 类，审批 a6）

- 做法：`text_display`，固定朝向、贴墙或立在矮座上、朝着人来的方向；底色搪瓷蓝（方案的 `#172c57`，不透明），字米白（`#f2ead6`），第一行是件的名字（全大写），下面一两句；行宽让一块牌不超过四行；亮度写死（夜里读得清，不发亮成灯）。有现成的搪瓷铭牌边框（`sign_nameplate`）就套上，没有就不要边框，不新做模型。
- 十二块，文字先用下面的（做的人可以改得更准，改了在记录里写原因；只许英文，不许出现真实的人名、年份、机构）：

| 牌 | 放哪 | 文字 |
| --- | --- | --- |
| CABLE STATION | 站台，出口旁 | The only way up. The car climbs through the cloud to the summit. |
| THE MERIDIAN LINE | 前庭，子午线东端 | Brass, set true north and south. Every clock in the building is checked against it. |
| ARMILLARY SPHERE | 前庭，浑天仪座 | A model of the great circles of the sky. Sight along the rings to see where a star will rise. |
| THE ORRERY | 星厅，进门右手 | Six planets on brass arms, geared to keep their true periods around the sun. |
| THE MASTER CLOCK | 星厅，母钟旁 | One pendulum. Every dial in the observatory follows it. |
| TIME ROOM | 授时室，进门 | The hour goes out from here by wire and by radio, to every town below the cloud. |
| CHART ROOM | 星图室，进门 | Each clear night is drawn here by hand, star by star. |
| PLATE VAULT | 底片库，进门 | Glass plates of the sky, one for every clear night since the dome first opened. |
| THE GREAT REFRACTOR | 穹顶室，台阶口 | A lens two feet across. Tonight it is turned on the comet. |
| TIME BALL | 钟塔脚 | It drops once a day, on the second, so the town below can set its clocks. |
| POWER HOUSE | 发电房门口 | Steam turns the dynamo. The dynamo lights the lamps and turns the dome. |
| SUNSET TERRACE | 落日平台入口 | The comet sets in the west, an hour behind the sun. Take a seat. |

- 位置读各包导出的常量；牌不挡路（走查的站位上不许多出碰撞，`text_display` 本来没有碰撞）；一个机位里看得见的牌不超过两块，V1 到 V12 的十二张看板图里牌不抢主角（牌面在画面里的亮度不过 0.35）。

### 丙 六张星图（motion 类，审批 cr2）

- 六张星图，一处一张：发电房（配电盘前的桌上）、授时室、星图室长桌、底片库、钟塔脚或蓄电池室（二选一，做的人定）、落日平台三脚架望远镜旁。用现成的星图模型（`props/instruments` 或星图室的卷图），不新做；旁边每两秒一小点微光粒子，让人看得见该走近。
- 人走到一张图 1.6 格以内、而且还没拿过这一张：给他记上这一张（玩家身上的标签 `c164.c1` 到 `c164.c6`），只对他放一声轻的提示音（用 `motion/sound` 表里现成的事件或原版的风铃声，不加声音文件），动作栏 `Star chart 3 of 6`。图不消失（别的人还要拿）。
- 收尾：六张齐了的人站到大折射镜目镜前的那一级台阶上（位置读 `machines/scope`）：标题 `THE COMET, IN FOCUS`，副标题 `Thank you for visiting.`，一声钟，穹顶缝里十秒钟往上飘的光点；给他打 `c164.done`，以后再站上去只在动作栏说 `The comet is in focus.`。没齐的人站上去：动作栏 `The lens is clouded. Find the six star charts (3 of 6).`。
- 全是每个人自己的状态（玩家身上的标签），没有全局状态：多人同时玩互不影响，退了再进接着来。留一个给 Realm 主人用的函数 `c164art:guide/reset`（清所有人的这些标签）。

## 约束

- 纯原版、只用函数和标签：不加进度、战利品表、谓词、任何注册表文件（`check.py` 现在见到就 FAIL）；计分板用函数里的命令建。不发聊天栏消息（标题和动作栏不算），不给物品，不改游戏模式。
- 每刻的命令走 `motion/loop` 的登记（a2 的 `_kit.py`）；走近检测每 4 tick 一次，本包平均每秒不超过 40 条命令，和 a2 对一句预算。
- 全英文。字用游戏默认字体，不加字体文件。
- 开关：主场景里一个常量 `GUIDE = True`；outb 的导出加一个 `--no-guide`，能出不带这一层的包。
- outb 的验证里「quiet」那一项（进服以后什么都没说）改成：聊天栏里什么都没有；标题和动作栏按这张卡核。

## 验收

- `check.py` 过；导出的冷启动验证过；数据包里还是只有函数和标签。
- s1 用真客户端进导出的存档走一遍：标题出现一次；十二块牌每块读得清、不穿墙、不挡路；六张图都拿得到，计数对；齐了以后目镜前的收尾出现；退了再进进度还在；两个客户端同时在线互不影响（s1 有四台真机）。
- 看板十二张图的分不因为牌掉下去。

## 人

aide 从手空的人里派，11:10 前定下来告诉我：甲一个人（和 outb 对钩子），乙两个人（一人六块，按楼的东西两半分），丙两个人（一人写走近检测和收尾，一人摆六张图和粒子）。做丙的人里要有一个写过 `motion/loop` 登记的（sound 或 smoke）。

## 记录

（做的人写在下面。）
