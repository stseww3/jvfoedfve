# Realms 对上传世界的规定：查到的、没查到的

outb（c340），11-16。卡 `plan/packages/common/export.md` 约束第三条：以官方文档为准，查到的给出处，查不到的写「没查到」，不猜。
出处分四等，每条都标：**官方**（Mojang 的帮助中心、Mojang 员工在官方缺陷库里的答复）、**游戏文件**（26.3 客户端 jar 里的类和语言文件，官方地址取的，核过 SHA-1）、**维基**（minecraft.wiki，不是官方）、**玩家说法**（论坛、反馈站，只当线索）。

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

## 1. 大小

- **官方**：帮助中心「Upload a World to a Minecraft: Java Edition Realm」：「The maximum world size is 4GB.」<https://help.minecraft.net/hc/en-us/articles/37820328303629>
- **游戏文件**：`com.mojang.realmsclient.client.worldupload.RealmsUploadWorldPacker`：`SIZE_LIMIT = 5368709120` 字节（压成 tar.gz 以后），超了报「World too big」（`mco.upload.failed.too_big.*`）。打包时把整个存档文件夹原样装进去，文件夹名改成 `world`，没看到排除哪些文件。
- 我们的包是几十兆的量级，碰不到。

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
- **没查到**：官方文档里的数字（默认多少、能调到多少）。
- **对我们意味着什么**：总监定的「视距按 12 算」能不能达到，取决于管理员把这个滑条拉到多少；写进上传说明。

## 6. 槽位自己的设置

- **游戏文件**：每个世界槽位有自己的一份设置（`RealmsWorldOptions`）：游戏模式、难度、强制游戏模式、出生点保护、命令方块。上传时客户端用存档里的值填游戏模式和难度（`RealmsWorldOptions.createFromSettings(LevelSettings, …)`，`RealmsUploadScreen`、`RealmsCreateWorldFlow` 调的）。
- **维基**：1.21.5 起「Uploading a world to Realms now enables command blocks by default」。
- **对我们意味着什么**：存档里把默认模式写成冒险、难度写成和平，上传时会带过去；传完在配置界面核对一遍（上传说明里列出来）。游戏规则存在存档里，不归槽位管。

## 7. 版本

- **游戏文件**：Realms 只跑最新的正式版（`mco.client.outdated.stable.version`：Please use the most recent version of Minecraft）；快照另有配对的 Snapshot Realm。
- **对我们意味着什么**：26.3 以后出了新正式版，Realm 上的世界会被升级；数据包和资源包的格式号（121、97.1）到时要跟着改。这是定稿以后的事，记在这里。
