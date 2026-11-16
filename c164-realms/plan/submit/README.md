# 投稿用的一页（给管理员）

总监 11-16 11:55 写的。管理员要把这张图投 Realms 的内容库（Java Realms Content Creator Program）。这一页是他投稿时要用的东西：怎么投、要填的字、要附的图、我们对着官方规矩查过的结果。规矩的原文和出处在 `plan/reviews/export/realms-rules.md` 第 8 节（outb 摘的，官方 Atlas 的 Realms Map Guidelines，2026-11-03 版）。

**现在还是草稿**：名字和署名等管理员定；成品是哪一版（A8 还是更后面的）定了再把哈希填进来。

## 1. 怎么投（官方的路）

1. 头一次投稿不走 Atlas，走 Reddit 的 r/realms：发一个帖子，里面是地图的下载链接。**链接只能放 Google Drive、OneDrive 或 Dropbox**（别的网盘会被拒）。
2. 一个人同一时间只能有一个投稿在排队。
3. Mojang 的内容协调员审。多数 Reddit 投稿第一次会被退回，退回的大多带修改意见，改了可以再投（协调员 2026-09 在 r/realms 上自己说的）。审核可能要几周到几个月。
4. 通过以后才给 Atlas 的账号，再在 Atlas 上正式投这张图，过了全审排进下一次内容更新。发布以后不能改，只能投新版本。
5. 帖子的格式以 r/realms 置顶的投稿说明为准（我没能读到那一页，投之前请照它核一遍下面的字段有没有缺的）。

## 2. 要传的文件

- 成品：`cursor/c164-dist-f4b8` 分支，`c164-realms/dist/A<n>/c164-A<n>.zip`（现在最新是 A7；A8 起带导览）。解开就是一个存档文件夹，里面有 `level.dat`、`datapacks/c164art/`、`resourcepacks/resources.zip`。传网盘的就是这个 zip。
- 备用：同一文件夹的 `c164-A<n>-plain.zip`，资源包里不带着色器（天是原版的夜空）。带着色器的那个在评审的机器上要是加载失败，换这个。
- 投稿前改名：zip 和里面的文件夹改成地图的名字（定名以后 outb 导出时直接出对的名字）。

## 3. 要填的字（英文，可以直接贴）

| 字段 | 内容 |
| --- | --- |
| Map name | `Blue Hour Observatory`（占位，等管理员定） |
| Category | Experience |
| Creator(s) | 等管理员给（最多三个主创） |
| Minecraft version | Java Edition 26.3 |
| Players | 1–11（任何人数；人随时进出） |
| Play time | 15–25 minutes |
| Resource pack | Included in the world (`resourcepacks/resources.zip`, 1.7 MB) |

**一句话简介：**

> A mountaintop observatory above a sea of clouds, on the evening a comet sets behind the sun.

**正文：**

> Blue Hour Observatory is a walk-through build for one to eleven players. You arrive by cable car at dusk. The comet hangs over the dome, the lamps are lit and every clock is running.
>
> Inside you will find a star hall with an orrery geared to the planets' true periods, a time room, a chart room, a plate vault, a power house with its steam engine, and under the great dome a refractor turned on the comet. Nothing is asked of you: walk, look, and take your time. Those who look closely may find six star charts along the way.
>
> The map is vanilla: one data pack with functions only, and a resource pack bundled in the world. No third-party assets are used: the textures and custom models were made for this map, apart from six recoloured vanilla textures, the vanilla block shapes they sit on and the game's own sky shaders, which the pack modifies. Adventure mode, peaceful, no chat messages. Players who fall off the mountain are put back at the station.

（a1 11-16 12:10 核过，细账在第 5 节表下面。原来写的是「All textures and models were made for this map」，照原样不成立：有 6 张贴图是原版贴图改色，方块模型用的是原版的形状，着色器以原版为底。上面是照实的说法，措辞总监可以再改，事实以第 5 节为准。）

## 4. 要附的图

- 规矩：截图和预告片里不能出现 Steve 或 Alex（默认皮肤的人）。我们的图里没有人，也没有界面。
- 用成品那一版的存档图（s1 进导出的存档拍的，`cursor/c164-s1-render-f3-fd9c` 的 `c164-realms/renders/real-save/c164-A<n>/`）。建议五张：`v01_arrival`（下缆车第一眼）、`v02_axis`（正面，彗星在穹顶上方）、`v07_hall`（星厅：太阳系仪和母钟）、`v08_dome_room`（大折射镜对着穹顶缝里的彗星）、`v12_aerial`（整座岛和晚霞）。
- 成品定了以后 s1 把这五张按 1920×1080 重拍一遍放 `renders/submit/`（现在的是 1280×720）。
- 预告片：没有，那一栏不填（规矩：没有预告片就不要放别的链接）。

## 5. 对着规矩查过的

| 规矩 | 我们 | 谁查的 |
| --- | --- | --- |
| 不带实验性设置 | 数据包里只有函数和标签，没有注册表文件（A7：函数 371、标签 3） | outb 的验证，我每版核 |
| 视距固定 10 | 按 10 做的：远景不靠 160 格以外的方块；验证时服务端视距设 10 | outb、s1 |
| 最多 11 人，人随时进出、掉线 | 函数按「每个人、每次进服」写；验证里有「离开再进来」；导览的状态都在玩家自己身上；s1 多个客户端同时在线试 | outb、s1 |
| 资源包不超过 250 MB | 1.7 MB | outb |
| 进度和配方的提示要关 | 数据包 `pack.mcmeta` 的 `filter` 把原版的进度和配方挡掉 | outb |
| 不该刷怪的地方别刷怪 | 和平难度（`load` 函数每次开服都设）加 `spawn_mobs false`、不来商人、不来巡逻队和幻翼 | outb |
| 不留给作者占便宜的命令和测试工具 | 导出时去掉搭建用的函数、结构文件和记录；成品里只有运动循环、进服、掉落和导览的函数 | outb |
| 让建筑自己说话，少用牌子和书 | 说明牌十二块，每块两行；没有书；没有聊天栏消息 | 卡 `motion/guide` |
| 不滥用副标题和首领栏 | 标题只在头一次进来放一次；不用首领栏 | 卡 `motion/guide` |
| 署名可以有，要克制；不给别人打广告 | 一块署名牌，不写网址 | 卡 `motion/guide` |
| 名字：不重名、不带 Minecraft、不用 mine、craft、block、cube、pixel | 已发布的图里没有带 Observatory 的（维基的清单，11-16 查）；**不叫 Comet Observatory**（任天堂的地名） | 我 |
| 烟、酒、药 | 没有（全部场景代码扫过：瓶子只有暗房的药水瓶、蓄电池室的量杯、桅杆的瓷瓶） | 我 11-16 11:09 |
| 真人、真实机构和地名 | 没有（没有一个真实的人名、地名、厂名） | 我 11-16 11:09 |
| 宗教的标志 | 没有；工程里本来就有「任何地方不许出现十字」的规矩（风向标、辐条、桅杆都避开了） | 我 11-16 11:09 |
| 真实国家及其标志、枪、坦克、血 | 没有。旗是这座台自己的：蓝底、米白的环和星 | 我 11-16 11:09 |
| 别人的版权 | **没有第三方的素材；来自游戏本身（Mojang）的有三样，列在表下面**。贴图 707 张里 701 张完全由我们的代码画出，6 张是游戏自带的贴图改色；模型 1006 个里 568 个物品模型是我们的代码拼的，438 个方块模型是游戏自带的形状改了贴图指向；着色器 10 个里 1 个全新，9 个以游戏原文为底。声音只用原版的事件（两个 `sounds.json`，资源包里没有声音文件）；没有字体文件，贴图上的字出自代码里的点阵表 | a1 11-16 12:10（A7 的包，读代码并逐张比过）；着色器 a2 |
| 「体验」类不能有故事和计时 | 没有故事，没有计时；六张星图是彩蛋，进场不交代 | 卡 `motion/guide` |

**「别人的版权」那一行的细账**（a1，11-16 12:10；对象是 A7 的 `resourcepacks/resources.zip`，2393 个文件，代码是总装 1a0f1af9）：

- 怎么查的：读了全部往资源包里写东西的代码。构建目录里没有一张图片文件，代码不从网上取任何图；能把外面的像素带进包的只有一处，`materials/_kit.py` 的 `vanilla_picture()`，它从游戏客户端的 jar 里读原版贴图，调用它的只有下面 6 张。另外把包里 707 张图同 26.3 客户端自带的 3964 张逐张比过：没有一张照搬。代码和包里都没有署名、许可证、网址一类的字样。
- **来自游戏本身的 ① 6 张贴图**（都在 `assets/c164/textures/block/`，做法是保留原图的镂空和明暗层次，颜色换成我们的色阶）：
  - `iron_lantern.png` 和它的 `iron_lantern.png.mcmeta`：原版 `block/oxidized_copper_lantern`（`materials/iron.py` 的 `_recolour`）；
  - `brass_shelf.png`：原版 `block/bamboo_shelf`（`materials/brass_oldcopper_small.py` 的 `_tone`）；
  - `brass_sign.png`、`brass_hanging_sign.png`：原版 `block/bamboo_sign`、`block/bamboo_hanging_sign`；`enamel_sign.png`、`enamel_hanging_sign.png`：原版 `block/oak_sign`、`block/oak_hanging_sign`（同一文件的 `_sheet`：牌面、边和立柱是我们画的，镂空和吊牌的横杆、链子取自原图）。
  - 要一张都不沾原图：这 6 张改成代码直接画（灯笼归 iron，其余归 brass），是小改，但要重出图、重跑检查；现在没有做。
- **来自游戏本身的 ② 529 个 JSON**：`assets/c164/models/block/` 的 438 个方块模型和 `assets/minecraft/blockstates/` 的 91 个方块状态文件，是游戏自带的文件改了贴图和模型的指向（`artkit/respack.py` 的 `redirect`），形状是原版方块的形状。资源包给原版方块换贴图只能这样做。
- **来自游戏本身的 ③ 9 个着色器文件**（`assets/minecraft/shaders/`，`sky/_shaders.py` 写的。我拿包里的成品同 26.3 的原文逐行比过，a2 12:08、12:09 两条回话确认并补了数）：
  - 原文整篇留着、只动几处的四个，构建时从客户端 jar 里读原文再改，仓库里没有原文：`core/clouds.vsh`（106 行改 1 行）、`core/item.vsh`（59 行改 1 行）、`core/rendertype_beacon_beam.vsh`（19 行全留，加 2 行）、`core/lightmap.fsh`（67 行，换 4 处式子、加 4 个常数）。
  - 整份由我们的模板写出的五个，模板里留着原文 68 行（不计空行），所以**仓库里也有这 68 行原文**：`include/fog.glsl`（原文 35 行留 33 行：`Fog` 块和五个函数，`FogColor` 改名 `GameFogColor`，`total_fog_value` 的返回改写；另加约 140 行新写的 `c164_` 函数）；`core/sky.vsh`、`core/sky.fsh`、`core/stars.vsh`、`core/stars.fsh`（原文 13、10、8、7 行，留 13、9、7、6 行：版本行、引用、输入输出的声明，`sky.vsh` 原 `main` 的三行；`main` 的其余是新写的）。
  - `include/c164_layers.glsl`（196 行）全新，游戏里没有这个文件。山脊那一段是 `sky/ridges.py` 出的一张数表加查表。
  - 新写的 GLSL（`c164_` 开头的）全部是 a2 这一班自己写的，照游戏自己的画法和 `sky/mood.py` 的算式；没有噪声函数，没有取过别人的着色器包或网上的代码（a2 的原话；我在十个文件里也搜过，没有署名、许可证、网址，没有常见的现成噪声函数的痕迹）。
- 不进包、只在构建时用的一处通行写法：Python 里撒颗粒、烘数表用的整数散列是网上通行的三行写法（常数 374761393、668265263、1274126177，见 `artkit/pixelart.py`、`artkit/canvas.py`、`sky/ridges.py` 等）。它只是几个质数和移位，成品里没有这段代码，记在这里备查。
- 完全是我们自己的：`assets/c164/textures/item/` 的 568 张（每个物品模型一张，`artkit/models.py` 按色阶画的）和 568 个物品模型、568 个物品定义；`assets/c164/textures/block/` 其余 123 张和 7 个 `.mcmeta`；`assets/minecraft/textures/environment/` 的 10 张：月亮八个相位的位置上是彗星（`sky/comet.py` 算出来的；其中 `celestial/moon/new_moon.png` 现在是一张测试卡，是我们自己的，换天色做法之前留下来看贴图朝向的，不是有意留给成品的：钟锁在 20370、月相是 `full_moon`，玩家看不到它，除非有人改时间。去掉是 `sky/comet.py` 一行，a2 写好推在自己的分支上，进不进 A8 听总监）、`celestial/sun.png` 全黑（不画太阳）、`clouds.png` 全透明（不画原版的云）。
- 所以第 3 节正文里原来那句「All textures and models were made for this map」照原样不成立，已改成照实的说法；6 张图要是重画了，可以改回更干脆的一句。

## 6. 要照实告诉评审的

- 天（晚霞、彗星、雾和光的颜色）是资源包里的十个核心着色器文件画的。我们在 Vulkan 和 OpenGL（Mesa）上都验过，画面一致；厂商显卡的驱动没有条件验。游戏升级以后着色器可能要跟着改；不带着色器的备用包随时能出。
- 这张图是为 26.3 做的。
