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

## 注意到的细节

- RCON：服务端每次 socket 读只处理一个包，命令不能连发，要等上一条的回复。`tools/rcon.py` 已按这个写。
- `forceload` 之后马上用选择器找实体，可能只找到一部分（实体区块是异步加载的），隔几 tick 再查就全了。
- 旧格式升级来的告示牌多了一个 `allow_op_features: 1b`，原生 26.3 的告示牌没有。和告示牌点击执行命令的权限有关，用到时要查清楚。
- 26.3 的命令列表里有 `/dialog`、`/posteffect`、`/stopwatch`、`/waypoint`、`/swing`、`/compute`、`/test`、`/fetchprofile`、`/rotate`、`/transfer`。
- 负载高时会出现 “Can't keep up”，是这台共用 VM 的 CPU 被占满造成的，测时序相关的逻辑时要留意。

## 还没验证

- 需要真实玩家才能触发的逻辑（trigger、对话框、掉线重进、进度）。需要一个能连 26.3 的无头客户端或机器人。
- 画面。云端没有显卡，看不到游戏里的实际效果。
- 资源包。
- Realms 上的行为（没有 OP、小游戏槽位重置等）。

## 复现

```
python verify/make_test_pack.py /agent/realms-study/server26/world/datapacks/c164test
# 启动服务端后
python tools/rcon.py --pw-file /agent/realms-study/server26/.rcon_pw "function c164:build" "save-all flush"
python tools/census.py /agent/realms-study/server26/world
```
