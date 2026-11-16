# Realms 对上传世界的规定：查到的、没查到的

outb（c340），11-16。卡 `plan/packages/common/export.md` 约束第三条：以官方文档为准，查到的给出处，查不到的写「没查到」，不猜。
出处分五等，每条都标：**官方**（Mojang 的帮助中心、内容创作者计划的投稿站 Atlas、Mojang 员工在官方缺陷库里的答复）、**游戏文件**（26.3 客户端 jar 里的类和语言文件，官方地址取的，核过 SHA-1）、**节点上验的**（`tools/export.py` 在节点上起 26.3 服务端看到的，记录在 `cursor/c164-dist-f4b8` 的 `c164-realms/dist/`）、**维基**（minecraft.wiki，不是官方）、**玩家说法**（论坛、反馈站，只当线索）。

## 0. 最要紧的一条：我们的世界是「实验性设置」的世界，Realms 说不支持

**事实一（游戏文件，确定）。** 26.3 的 `net.minecraft.resources.ResourceManagerRegistryLoadTask` 里，注册表条目的来历只分两种：出自原版自带的包记作 stable，别的一律记作 experimental（`REGISTRATION_INFO_CACHE`：`KnownPack.isVanilla` → `Lifecycle.stable()`，否则 `Lifecycle.experimental()`）。我们的数据包里有 `data/c164art/worldgen/biome/obs_blue.json` 和 `data/c164art/timeline/obs_looks.json`（整场的天色、雾、光色、星月都靠这两个文件，`build/artkit/mood.py` 写的），所以这个世界的 `worldGenSettingsLifecycle` 是 experimental。单机打开它，`WorldOpenFlows` 每次都弹一屏：

> Worlds using Experimental Settings are not supported
> This world uses experimental settings that could stop working at any time. We cannot guarantee it will load or work. Here be dragons!

（语言文件 `selectWorld.backupQuestion.experimental`、`selectWorld.backupWarning.experimental`。）管理员在自己电脑上打开导出的世界就会看到这一屏；点「我知道我在做什么」能进。

**事实二（官方）。** Mojang 的缺陷库 REALMS-5322「Custom world generation or dimensions from data packs don't work in Java Realms」，结论 Works As Intended，Mojang 的 Adrian Östergård 2021-05-19 答复：

> This is working as intended. We do not support experimental features on Realms.

同一条下面挂着 REALMS-5290「Custom Worldgen files are removed from data pack when uploading world to Minecraft Realms」、REALMS-8880「World Generation And Custom Structure Data Packs Do Not Work On Realms」等九条，都并到这一条。出处：<https://mojira.dev/REALMS-5322>（官方缺陷库 bugs.mojang.com 的镜像）。

**事实三（维基）。**
- Realms 条目，Java 版的限制一栏：「Worlds on Realms cannot use experimental settings. This applies to all user-uploaded worlds, as well as maps published through the Java Realms Content Creator Program.」<https://minecraft.wiki/w/Realms>
- Data pack 条目：「worlds using experimental settings cannot be played on Realms: Attempting to upload such a world to Realms results in a server error.」带星号的文件夹里有 `timeline*` 和 `worldgen*`（`biome` 在它下面）。<https://minecraft.wiki/w/Data_pack>

**没查到的。**
- 2026 年的 Realms（26.3）碰到带自定义生物群系和时间线的世界，到底是整个拒收、把这些文件从数据包里拿掉、还是放行：官方文档里没查到。事实二是 2021 年的答复，说的是自定义地形生成和维度；时间线是 26.x 才有的，没有任何官方说法。
- 内容创作者计划的投稿（不是自己上传，是 Mojang 那边装进内容库）对这类文件怎么处理：官方文档里没查到。
- 调研过的四张已上线地图（`study/published-maps-study.md`）帮不上忙：没有一张用自定义生物群系或时间线；公开版里有带星号的东西（The Masquerade 的 `chat_type`、War Games 的 `dialog` 和 `minecraft` 命名空间下的 `worldgen`），但公开版和 Realms 版可能不一样（The Masquerade 的 level.dat 里启用的包叫 `ww_datapack_realms`，公开包里的文件夹叫 `ww_datapack`），得不出结论。

**对我们意味着什么。** 如果 Realms 拒收或者拿掉这两个文件：上传失败；或者传上去了，区块里记着的生物群系 `c164art:obs_blue` 不存在，天色、雾、光色、星月全部回到原版的样子。这不是导出工具能绕过去的，是整场「靠数据包调色」这条路在 Realms 上走不走得通的问题。能下结论的只有两个办法：管理员拿空跑的包真传一次；或者向内容创作者计划问清楚。

**定了（总监 #64343，11-16 07:24；公告 #1196，07:53；COMMON.md 第 5 节第 5 条）。** 成品的数据包不带注册表文件：天、雾、光色改由资源包的着色器来带，a2 牵头（`sky/safe-look`），样子不变；着色器只有 a2 那一套。依据是第 8 节的官方准则和第 9 节我们自己的调研（四张已上线地图三张带核心着色器）。数据包里能放的只有函数、标签、结构、进度、战利品表、谓词、配方、物品修饰器；`tools/check.py` 的 regen 一项和 `tools/export.py` 都照这张单子拦。导出工具默认不带那两个文件，开关 `--look on` 留着，只给试传用。生物群系用哪个原版的、时间锁在哪一刻，等 a2 定。

**试传（总监 #62652）。** 两个半兆的存档 T1（带 `obs_blue`、`obs_looks`）和 T2（不带）在 `cursor/c164-dist-f4b8` 的 `c164-realms/dist/trial/`，连同给管理员的一页步骤。要管理员回答的只剩两件：自己上传的存档 Realms 发不发资源包（第 3 节）；带注册表文件的存档是不是真被拒（本节「没查到的」第一条）。结果回来记在这里。

## 1. 大小

- **官方**：帮助中心「Upload a World to a Minecraft: Java Edition Realm」：「The maximum world size is 4GB.」<https://help.minecraft.net/hc/en-us/articles/37820328303629>
- **游戏文件**：`com.mojang.realmsclient.client.worldupload.RealmsUploadWorldPacker`：`SIZE_LIMIT = 5368709120` 字节（压成 tar.gz 以后），超了报「World too big」（`mco.upload.failed.too_big.*`）。打包时把整个存档文件夹原样装进去，文件夹名改成 `world`，没看到排除哪些文件。
- **官方**（Atlas 的准则，见第 8 节）：「The maximum allowed size of resource packs is 250 MB.」
- 我们的存档是几兆到几十兆的量级，资源包现在不到 1 兆（`materials.pack` 加 `sky.pack` 673 个文件，压成 zip 0.36 兆），都碰不到。

## 2. 上传的步骤

- **官方**（同一篇帮助中心）：Minecraft Realms → 自己的 Realm 点 Configure → 选一个世界槽位 → Reset World → Upload World → 选单机存档 → Upload → Done。
- **游戏文件**：选的是「单机存档」（`mco.upload.select.world.subtitle`：Please select a singleplayer world to upload），所以 zip 要先解到管理员电脑的 `saves/` 里。极限模式的存档不让传（`mco.upload.hardcore`）；客户端这一头没有对实验性存档的拦截（Realms 的类里没有 `isExperimental`），拦不拦在服务端。

## 3. 资源包

- **游戏文件**：存档里的资源包位置是 `resourcepacks/resources.zip`（`LevelResource`）；单机打开存档会自动用它。进 Realm 时服务端可以给一个资源包地址和校验值（`RealmsJoinInformation` 的 `resourcePackUrl`、`resourcePackHash`），客户端问「You need a custom resource pack to play on this Realm. Do you want to download it and play?」（`mco.configure.world.resourcepack.question`）。就是说 Realms 有给全服发资源包的机制。
- **没查到**：自己上传的世界里的 `resources.zip`，Realms 会不会拿去发给进服的人。官方文档里没有。
- **玩家说法，互相矛盾**：反馈站 2022-08「if the world file has a "resources.zip" file the realm will just ignore it」<https://feedback.minecraft.net/hc/en-us/community/posts/8088198156941>；反馈站 2026-05 的提案里写「it is not possible to set a resourcepack for worlds on Realms」<https://feedback.minecraft.net/hc/en-us/community/posts/45815151907213>；r/realms 2023-07 有人实测后说只有内容库里的地图能带资源包；一家服务器商 2026-10 的文章说带 `resources.zip` 上传后进服的人会被问要不要下载。
- **对我们意味着什么**：内容库里的地图带资源包没有问题（四张已上线的都带）。管理员自己上传到自己的 Realm 试看时，资源包多半不会自动发：进服的人要自己装同一个包，不然看到的是原版贴图（重画的方块、展示实体的模型都没有）。真传一次才知道。上传说明里两种情况都写。

## 4. 数据包

- **玩家说法**：存档 `datapacks/` 里的数据包跟着上传的世界走，在 Realm 上生效（反馈站 2022-08 同一帖：「any datapacks on the world will work in the realm」）；实验性的部分除外，见第 0 节。
- **维基**（Realms 条目的更新史）：1.13.3 修过「Realms would delete zipped data packs and functions from unzipped data packs」。
- **没查到**：帮助中心里专讲数据包和 Realms 的文章。

## 5. 视距

- **游戏文件**：26.3 的 Realm 配置界面有两个滑条：「Render Distance Limit」（The maximum distance visible to Realm members. Higher values may impact performance.）和「Simulation Distance」（`mco.configure.world.renderDistance`、`mco.configure.world.simulationDistance`；`RealmsSettingsTab`、`RealmsClient.updateRenderDistance`）。就是说视距上限由 Realm 的主人在配置里定，不在存档里。
- **维基**：Java Realms 的渲染距离和模拟距离上限都是 25、可调；26.3 的 snap9 加的这两个滑条。同一页另一处又写「The render distance is always set to 25 chunks」，两处不一致。
- **官方**（Atlas 的准则，见第 8 节）：「View distance is set to 10. This cannot be altered.」这是对内容库里的地图说的。
- 两处对不上的地方：游戏文件里 Realm 的主人有滑条可调，准则说改不了。按最严的算：**视距 10**，人周围 160 格以外没有方块（总监公告 #1196 已经按这个通知了有关的包）。
- **对我们意味着什么**：远景不能靠 160 格以外的方块；导出工具起的服务端视距也设成 10，复验时假玩家看到的范围和 Realms 上一样。

## 6. 槽位自己的设置

- **游戏文件**：每个世界槽位有自己的一份设置（`RealmsWorldOptions`）：游戏模式、难度、强制游戏模式、出生点保护、命令方块。上传时客户端用存档里的值填游戏模式和难度（`RealmsWorldOptions.createFromSettings(LevelSettings, …)`，`RealmsUploadScreen`、`RealmsCreateWorldFlow` 调的）。
- **维基**：1.21.5 起「Uploading a world to Realms now enables command blocks by default」。
- **节点上验的**：服务端每次启动都拿自己的设置定「新玩家的游戏模式」和难度，不看存档。同一个存档（`level.dat` 里是冒险、和平），服务端设置写生存、简单时：`difficulty` 报 Easy，新进来的假玩家不是冒险模式；设置写冒险、和平时才是。Realms 上「服务端自己的设置」就是槽位这一份。
- **节点上验的**：默认游戏模式是冒险时，26.3 把新玩家放在世界出生点上、再让他沉到第一个托得住他的东西上；那一刻出生点的区块还没加载，结果落在世界最底（y −63）。出生点那一格区块设成常加载以后，落点就是出生点（y 201，朝向也对）。
- **对我们意味着什么**：
  - 存档里把默认模式写成冒险、难度写成和平，上传时会带过去；传完在配置界面核对一遍（上传说明里列出来）。游戏规则存在存档里（`data/minecraft/game_rules.dat`），不归槽位管。
  - 不能只靠这份设置：函数在每个人每次进服时设冒险模式；成品的 `load` 函数里有一句 `difficulty peaceful`（每次开服都跑）。试传存档故意不设难度，好看 Realms 给的是什么。
  - 导出的存档留一个常加载区块（出生点那一格），这样函数没跑的那一拍人也站在平台上。

## 7. 版本

- **游戏文件**：Realms 只跑最新的正式版（`mco.client.outdated.stable.version`：Please use the most recent version of Minecraft）；快照另有配对的 Snapshot Realm。
- **对我们意味着什么**：26.3 以后出了新正式版，Realm 上的世界会被升级；数据包和资源包的格式号（121、97.1）到时要跟着改。这是定稿以后的事，记在这里。

## 8. 内容创作者计划的准则（Atlas）

**官方**：「Realms Map Guidelines」，<https://atlas.minecraft.net/guidelines/>，页上写 Last updated: November 3rd, 2026；11-16 全文读过。和我们有关的都摘在下面，原话加我们该怎么做。

**投稿的路。** 先把图发到 Realms 的 subreddit 过一次审（文件放 Google Drive、OneDrive 或 Dropbox），过了才能登录 Atlas 投稿；「Once a map is published to Realms you can no longer edit the map, but you can submit an updated version for review.」

**技术上的四条。**
- 「Realms is a Minecraft server for 1-10 concurrent players, however, a slot is reserved for the owner」：最多 11 个人同时在。
- 「View distance is set to 10. This cannot be altered.」（第 5 节）
- 「The maximum allowed size of resource packs is 250 MB.」（第 1 节）
- 「Realms always runs on the latest version of Minecraft.」（第 7 节）

**我们算哪一类。** 「Experiences are a category of loosely-defined maps mostly without a specific intended goal, where the player's purpose might be to explore, experience, or observe.」观景的图是 Experiences；加了故事就成了 Adventures（「an added story would make it an adventure」）。Adventures 一类写明「do not reset when the Realm is inactive」；Experiences 没写重置不重置。

**对地图本身的要求。**
- 「If not used in your map, advancements and recipe notifications should be disabled.」我们不用：数据包的 `pack.mcmeta` 用 `filter` 把原版的进度和配方整个挡掉（导出工具写的；复验里假玩家进服没有收到任何提示）。
- 「Let your build convey your ideas, rather than signs or books.」和红线第 3 条（地图里的文字只用数字、符号和少量英文）一致。
- 「Any minigame or adventures designed for a single player should be able to handle several players logging in.」「The map should also be able, to the best of your ability, handle players logging in and out, or dropping their connection.」我们的函数按「每个人、每次进服」写的（`leave_game` 计数），几个人同时在也各管各的；复验里有「离开再进来」一项。
- 不许带「commands or tools used for creating or testing that may give certain players an advantage, such as a back-door admin command」。导出时把只为搭建用的东西从数据包里去掉：结构文件，`place`、`clear`、`forceload` 三个函数，搭建时的记录文件；留下的只有运动循环和进服、掉落两件事的函数。
- 「Where appropriate …, light up your builds so that hostile mobs don't spawn where are not intended.」我们是和平难度加 `spawn_mobs false`，不靠照明。
- 广告：不许给别的公司、服务器、玩家做广告；自己的署名可以有，要克制（「Don't double up on ads」）。我们现在没有署名牌；要加的话只加一处。

**内容上不许有的**（原文是一张单子，和我们沾得上边的）：真实的枪和坦克、真实国家及其标志出现在军事冲突里、粗话、没经同意的真人（已故的历史人物可以，要有分寸）、「Specific religious displays or symbolism」、性别上的不平等、「Tobacco, tobacco products, or paraphernalia」、「Alcohol products or other intoxicants」、药品、没有授权的知识产权。**提醒做道具和室内的人**：烟斗、烟灰缸、雪茄盒、酒瓶、酒杯、酒柜都不能有；星图和仪器上不要出现十字架一类的宗教符号；不要出现真实的人名、机构名、牌子（红线第 3 条已有）。

**名字。** 不能只是一个类别名，不能带「Minecraft」，不能和已上线的图重名；建议不用 mine、craft、block、cube、pixel 这些词。

**投稿材料。** 「Screenshots and trailers cannot contain Steve or Alex」：宣传图里不能出现默认皮肤的人物（我们的截图本来就不带人）。链接要直接，不许用短链接；视频链接只能放预告片。

**没查到的。** 准则里没有一句提到数据包、实验性设置、着色器、存档大小、游戏规则；这些只能看第 0 节和第 9 节。

## 9. 已上线地图里的着色器（我们自己的调研）

`study/raw/survey_*.txt`（`tools/survey.py` 对四张已上线地图的公开版跑出来的）里，资源包带核心着色器的有三张：

| 地图 | 资源包里的着色器文件 |
|---|---|
| The Masquerade | `core/lightmap.fsh`、`include/fog.glsl`、`core/item.vsh`、`core/entity.vsh`、`core/entity.fsh`、`core/text.vsh` |
| Mossholder | `core/gui.vsh` |
| Spelling Bee | `core/rendertype_text.vsh` |
| War Games | 没有 |

（路径都在 `assets/minecraft/shaders/` 下。）The Masquerade 改的正是光照图和雾，和我们要的是同一类东西。这说明带核心着色器的资源包进得了内容库；说明不了的是公开版和 Realms 版的资源包是不是同一个（第 0 节说过公开版和 Realms 版的数据包名字不一样）。
