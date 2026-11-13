# 已上线 Java Realms 地图拆解记录（c164）

日期：2026-11-13。目的：弄清 Realms Mapmaker 披风要求的地图实际是什么规模、用了哪些做法，给后续制作定方向。

用途限制：这些地图是各自作者的作品（The Masquerade 仓库没有许可证，默认保留全部权利）。只用来学习做法、统计规模、以后做盲测参考图。不复制其中的代码、结构、贴图、音效，地图文件不进仓库、不转发。

## 1. Realms 内容库怎么获取

- Java 客户端只向 `https://pc.realms.minecraft.net/worlds/templates/{MINIGAME|ADVENTUREMAP|EXPERIENCE|NORMAL|INSPIRATION}` 要一份列表（id、名字、作者、封面、预告片链接）。选中后由 Realms 服务器加载，地图文件不发给客户端。接口要带正版账号的会话 cookie，且账号要有 Realm（订阅或 30 天试用）。来源：wiki.vg 的 Realms API 文档，没有用真账号实测。
- 拿到文件的官方途径：把图加载进自己 Realm 的世界槽位，再用“下载最新备份”（`GET /worlds/{id}/slot/{1-4}/download`）。Minigame 槽位能否下载未验证。需要账号本人操作。
- 不需要账号的途径：作者自己公开发布的版本。本次用的是这条路。

## 2. 下载来源

| 地图 | 类别 / Realms 上线 | 来源 | 版本 | sha256 |
| --- | --- | --- | --- | --- |
| The Masquerade（Gamemode 4） | Minigame / 2026-10-30 | github.com/Gamemode4Dev/The_Masquerade release 1.1.3 | 26.3 | ecc0508c…a9005 |
| The Masquerade 资源包 | 同上 | github.com/Gamemode4Dev/The_Masquerade_RP release 1.1.3 | 26.3 | 70243ea0…d013c |
| Spelling Bee（zedfff 等 3 人） | Minigame / 2026-05-29 | mapverse.net/map/spelling-bee（作者开放下载） | 1.1，26.1.2 | c760031f…7eb2 |
| War Games（TheWorfer27 等 3 人） | Minigame / 2026-04-24 | mapverse.net/map/war-games（作者开放下载） | 1.21.8 | ae7fb36d…b035 |
| Mossholder（TEHEK，1 人） | Adventure / 2026-09-28 | mapverse.net/map/mossholder（作者开放下载） | 1.0.1，26.1.2 | aa7ef11a…50f0 |

没拿到的：Armada（作者在 MapVerse 关闭了下载，没有绕）；Codenames、Snack Attack、Tightrope Rider（没找到作者公开的下载）；gm4.co 和 minecraftmaps.com 对云端机器返回 403，没有绕。

注意：公开版和 Realms 上的版本可能不同，没法对比。War Games 的公开版还停在 1.21.8，而 Realms 只跑最新版，所以 Realms 上的应当是更新过的版本。

## 3. 规模对比

| 项目 | Mossholder | Spelling Bee | War Games | The Masquerade |
| --- | --- | --- | --- | --- |
| 函数文件 | 150 | 524（353 个是 Animated Java 生成的） | 39 | 1,400 |
| 命令条数 | 666 | 10,953（6,430 条是词表数据，2,965 条是动画插件生成，手写逻辑约 1,550） | 数据包 1,465；主体逻辑在 3,360 个命令方块里，共约 44.7 万字符 | 11,165 |
| 结构模板 | 10 个房间 | 18 个（其中 12 张 25×37 的小场地） | 无 | 无 |
| 存档里的非空气方块 | 805（只有 1 个区块，放着起始房间） | 154,629（333 种） | 2,380 万（81% 是石头和砂岩填充，313 种） | 632,087（563 种；蜘蛛网、氧化切制铜、深色橡树叶三种占 45 万） |
| 模板里的方块 | 23,721（41 种，前 8 种占 80%） | 每张场地 2 千到 8 千 | — | — |
| 实体 | 模板里 1,119 个 marker，展示实体只有 6 个 | item_display 1,072，text_display 119，interaction 22 | item_display 1,891，interaction 1,806 | item_display 1,819 |
| 计分板项 | 8 | 20 | 82 | 189 |
| 资源包文件数 | 24 | 2,324 | 3,560 | 5,299 |
| 资源包内容 | 17 张小贴图（主要是替换 HUD 图标）、1 个后期滤镜、1 个着色器、语言文件 | 2,012 个语音文件（1,965 个单词）、约 120 个模型、1 个着色器 | 约 2,890 个物品定义、458 张贴图、138 个语言文件、12 个字体文件、24 个音效 | 约 2,840 个模型、约 1,500 张贴图、223 个音效、181 个字体文件、6 个着色器文件 |

结论：过审的图规模相差两个数量级。最小的一张（Mossholder）全部内容是 666 条命令、10 个 15×15 的房间模板（高 5 到 48 格）、24 个资源包文件，整座“无尽设施”是运行时用模板拼出来的。

Mossholder 的来历要注意：它是 2026 Java Realms Creators MapJam 的第 2 名（72 小时，61 份投稿，一个人做的）。MapJam 自 2024 年起前三名会上 Realms，所以它不是走普通 Reddit 队列进来的。来源：Minecraft Wiki “Java Realms Content Creator Program”。

## 4. 这些图的共同做法

- 屏蔽原版进度（4/4）和配方（3/4）：在 pack.mcmeta 里写 `filter.block`，命名空间 `minecraft`，路径 `advancement`、`recipe`。对应准则“没用到就关掉进度和配方提示”。
- 检测玩家重进：计分板 `custom:leave_game`（4/4）。
- 非 OP 玩家的输入（Realms 小游戏里没有人有 OP）：`trigger` 计分板（The Masquerade 9 个，War Games 1 个）、`dialog` 对话框、`interaction` 实体接点击、胡萝卜钓竿或诡异菌钓竿的右键统计（3/4）、“准星看向某处”的 predicate。
- 场地用 structure 模板加 `place` 命令运行时摆放和重置（Mossholder、Spelling Bee）。
- 自制模型和装饰用 item_display；自制界面用 font 位图；整体画风靠后期滤镜或核心着色器。
- 主循环：`#minecraft:tick` 标签，或 `schedule function … 1t` 自己续（The Masquerade）。
- gamerule：四张图都把时间、天气定住，随机刻设 0，关自然刷怪。关摔落伤害 3/4，关 locator_bar 3/4。命令回显、死亡消息、进度消息各只有 2/4 关掉。
- 同一份代码里用一个开关区分 Realms 版和公开版（The Masquerade 的 `$environment.realms`）。
- 开发工具痕迹：The Masquerade 和 Mossholder 的 level.dat 里有 Axiom 模组（建筑工具）的数据包；Spelling Bee 用 Animated Java（Blockbench 插件）；War Games 的存档带 Bukkit 系服务端的数据包。

## 5. Mojang 审核实际要求改的内容

The Masquerade 的 changelog 有一段专门标注 REALMS 的修改：

- 断头台换成铁砧，删掉活人被斩首的画面，删掉配音里提到断头台的句子。
- 措辞：executed 改 banished，murdered 改 eliminated，saint 改 heir。
- 删掉幻灯片里调侃 Mojang 的内容。
- Realms 上关闭通过资源包实现的聊天功能；取消“玩满 2 局才解锁”的限制。

说明暴力和宗教相关的措辞审得很细，要在设计阶段就避开。

## 6. 26.x 存档和包格式（生成存档时要用）

- The Masquerade 26.3：DataVersion 5023，数据包 `min_format/max_format` 121，资源包 97。
- 26.1.2：DataVersion 4790，数据包格式 101.1。1.21.8：DataVersion 4440。
- 26.x 存档目录：`dimensions/minecraft/overworld/{region,entities,poi}`、`data/minecraft/game_rules.dat`（规则名是 `minecraft:show_advancement_messages` 这种带命名空间的蛇形命名）、`data/<命名空间>/command_storage.dat`、`data/minecraft/scoreboard.dat`；level.dat 用 `spawn`、`difficulty_settings` 复合标签。1.21.8 还是旧布局（根目录 `region/`，gamerule 在 level.dat 里，驼峰命名）。
- 区块调色板在 26.3 又变了：条目是纯字符串 id（NBT 里包成 `{"": id}`）或 `{id, properties}`；26.1.2 及以前是 `{Name, Properties}`。
- 所以生成存档最稳的办法是让真服务端通过命令和结构模板写，不要自己拼区块二进制。26.1.2 的结构模板 `.nbt` 是 `{size, palette[{Name,Properties}], blocks, entities, DataVersion}`；26.3 的模板格式手上没有样本，要用真服务端导出一个确认。

## 7. 对我们方案的影响

- 可行的方向是 Mossholder 这一类：一个核心机制、少量模块化房间、统一的小配色、一个滤镜。这个体量 agent 做得出来，而且逻辑占比高。
- The Masquerade 那一档（上千模型、几百种方块的手工建筑）不在可行范围内。
- 代码写得漂亮不是门槛（Spelling Bee 的数据包比较随意），体验完整才是。
- 这些存档以后可以在带显卡的机器上按同样的镜头规则截图，作为盲测的参考图。

没验证的：这几张图实际玩起来的手感（没有进游戏）；公开版和 Realms 版的差别；普通 Reddit 队列对画面的实际要求（四张里只有 Mossholder 知道入选途径）。

## 8. 复现

```
python3 -m venv .venv && . .venv/bin/activate && pip install -r tools/requirements.txt
python tools/survey.py <解压后的存档目录>     # level.dat、数据包、资源包、区域文件概况
python tools/census.py <解压后的存档目录>     # 方块、方块实体、实体统计
```

原始输出在 `study/raw/`。
