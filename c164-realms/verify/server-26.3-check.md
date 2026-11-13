# 26.3 服务端验证记录（c164）

日期：2026-11-13。机器：云端 VM（4 核、16 GB，和别的聊天共用，当时负载 10 左右）。

## 环境

- Java 25：Temurin JRE 25.0.5+8，解压到 `/agent/realms-study/jdk/`，没有装进系统（VM 是共用的，不改默认 java）。
- 服务端：官方 `server.jar` 26.3（sha1 `33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c`），放在 `/agent/realms-study/server26/`，不进仓库。
- 启动需要 `eula=true`（同意 Mojang 的 EULA）。
- `server.properties`：`server-ip=127.0.0.1`（只监听本机）、`online-mode=false`、端口 25599、RCON 25598、虚空超平坦、`pause-when-empty-seconds=-1`、`white-list=false`。RCON 密码在 `server26/.rcon_pw`，不进仓库。
- tmux 会话名 `c164-mc-server`。堆内存上限 2 GB，`nice -n 10`。

启动命令：

```
cd /agent/realms-study/server26
nice -n 10 /agent/realms-study/jdk/jdk-25.0.5+8-jre/bin/java -Xms512M -Xmx2G -jar server.jar nogui
```

## 已验证

1. 26.3 服务端能在这台 VM 上跑。从启动到可用大约 20 到 30 秒（当时 VM 负载很高），日志里世界准备阶段是 0.6 到 3.7 秒。
2. `version.json`（服务端 jar 里）：world_version 5023，protocol 777，数据包格式 121.0，资源包格式 97.1，Java 25。
3. 数据包 `min_format/max_format = 121` 自动加载；`#minecraft:load`、`#minecraft:tick` 正常；没有玩家时也在 tick（前提是关掉 `pause-when-empty-seconds`，默认 60 秒后暂停）。
4. pack.mcmeta 的 `filter.block`（`minecraft` / `advancement`）生效：日志从 “Loaded 1866 advancements” 变成 “Loaded 0 advancements”。
5. 26.3 没有出生点常加载区块。对没加载的位置 `setblock` 会报 “That position is not loaded”，要先 `forceload add`。
6. 结构模板：
   - 26.3 原生格式是 `{size, entities, blocks, palette, DataVersion: 5023}`，palette 条目是 `{id, properties}`（小写）。来源：服务端 jar 里的原版模板。
   - 用 `tools/mcstructure.py` 生成的原生格式模板，`place template` 正常。
   - 同一个房间按 26.1.2 的写法（`{Name, Properties}`，DataVersion 4790）生成，26.3 也能加载，游戏会自动升级。
   - 方块状态、方块实体（告示牌文字、木桶里的物品）、实体（marker、item_display）都对。
7. `save-all flush` 之后用 `tools/census.py` 读存档：404 个非空气方块、2 个木桶、2 个告示牌、2 个 marker、2 个 item_display，和生成脚本的预期完全一致。

结论：“Python 生成模板和函数，真服务端摆放并写存档，再用脚本读回来核对”这条路在云端走通了，不需要带显卡的电脑。

## 假玩家（已验证）

现成的机器人库不支持 26.3：minecraft-protocol 1.68.0 和 mineflayer 4.39.0 最高到 26.1。所以自己写了一个最小客户端 `tools/mcbot.py`（离线模式登录，协议 777）：

- 包编号来自官方数据生成器的报告（`java -DbundlerMainClass=net.minecraft.data.Main -jar server.jar --reports`），精简后存在 `tools/data/packets-777.json`。
- 包的字段布局直接读服务端 jar。26.x 的 jar 没有混淆，系统自带的 `javap`（Java 21）就能看类名和字段。
- 26.3 里 `accept_teleportation` 变了：除了传送编号，还要回传坐标和朝向（id、x、y、z、yRot、xRot）。照旧版只发编号会被踢。
- 假玩家不模拟物理。悬空不动几秒会被踢（“floating too long”），所以要站在方块上，或者测试服开 `allow-flight`。

`verify/player_logic_check.py` 的 10 项检查全部通过：

1. 假玩家能加入并保持在线。
2. 没有 OP 的玩家用不了 `/gamemode`（和 Realms 小游戏里的条件一致）。
3. `/trigger` 在 enable 之前被拒绝，enable 之后能改分数。
4. `tellraw`、`title`、动作栏、`dialog show` 都能送到玩家，假玩家能读到文字内容。
5. 断线重连后 `custom:leave_game` 计分加 1。

所以需要玩家在场的逻辑也可以在云端自动测，不用真人上线。

## 云端出图（已验证）

云端没有显卡，但官方客户端可以用软件渲染跑起来，能看到真实的游戏画面：

- `tools/fetch_client.py 26.3 <目录> --skip-music`：从 Mojang 官方地址下载客户端、依赖库和资源（约 320 MB），逐个校验 SHA-1。不进仓库。
- `tools/run_client.sh`：在 Xvfb 虚拟显示器上以离线模式启动客户端，直接连本机测试服。
- 26.3 的客户端用 SDL 开窗口，有 OpenGL 和 Vulkan 两个渲染后端。在 Xvfb 下 OpenGL 后端失败（“Couldn't find matching GLX visual”），自动换成 Vulkan，由 Mesa 的 llvmpipe 软件实现渲染。日志：“Using graphics backend Vulkan … llvmpipe Mesa 25.2.8”。
- `tools/shoot.py`：用 RCON 把镜头玩家切到旁观模式并 `/tp` 到指定机位，等几秒，再抓 X 显示器的画面存成 PNG。
- 客户端启动时会向 Mojang 的登录和 Realms 接口发请求，令牌无效所以返回 401，不影响进本机服务器。
- 镜头不动时客户端自己会降帧，CPU 占用大约 20%（nice 10）。

所以“生成、摆放、出图、看图”整个循环都能在云端完成。

## 注意到的细节

- RCON：服务端每次 socket 读只处理一个包，命令不能连发，要等上一条的回复。`tools/rcon.py` 已按这个写。
- `forceload` 之后马上用选择器找实体，可能只找到一部分（实体区块是异步加载的），隔几 tick 再查就全了。
- 旧格式升级来的告示牌多了一个 `allow_op_features: 1b`，原生 26.3 的告示牌没有。和告示牌点击执行命令的权限有关，用到时要查清楚。
- 26.3 的命令列表里有 `/dialog`、`/posteffect`、`/stopwatch`、`/waypoint`、`/swing`、`/compute`、`/test`、`/fetchprofile`、`/rotate`、`/transfer`。
- 负载高时会出现 “Can't keep up”，是这台共用 VM 的 CPU 被占满造成的，测时序相关的逻辑时要留意。

## 还没验证

- 假玩家目前不会移动、不会点击实体、不会用物品、不会点对话框里的按钮。这些要用到时再加。
- 资源包。
- Realms 上的真实行为（小游戏槽位重置、延迟等）。本地只能模拟“没有 OP”这一条。
- 真人玩起来好不好玩。

## 复现

```
python verify/make_test_pack.py /agent/realms-study/server26/world/datapacks/c164test
# 启动服务端后
python tools/rcon.py --pw-file /agent/realms-study/server26/.rcon_pw "function c164:build" "save-all flush"
python tools/census.py /agent/realms-study/server26/world
python verify/player_logic_check.py --pw-file /agent/realms-study/server26/.rcon_pw
```
