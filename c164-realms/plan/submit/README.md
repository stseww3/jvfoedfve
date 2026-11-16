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
> The map is vanilla: one data pack with functions only, and a resource pack bundled in the world. All textures and models were made for this map. Adventure mode, peaceful, no chat messages. Players who fall off the mountain are put back at the station.

（「All textures and models were made for this map」这一句要 a1 确认以后才能用，见第 5 节。）

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
| 别人的版权 | 贴图 707 张、模型 1006 个、着色器 10 个都是我们的代码生成的；声音只用原版的事件（资源包里没有声音文件）；没有字体文件。**等 a1 确认没有外来素材** | a1 |
| 「体验」类不能有故事和计时 | 没有故事，没有计时；六张星图是彩蛋，进场不交代 | 卡 `motion/guide` |

## 6. 要照实告诉评审的

- 天（晚霞、彗星、雾和光的颜色）是资源包里的十个核心着色器文件画的。我们在 Vulkan 和 OpenGL（Mesa）上都验过，画面一致；厂商显卡的驱动没有条件验。游戏升级以后着色器可能要跟着改；不带着色器的备用包随时能出。
- 这张图是为 26.3 做的。
