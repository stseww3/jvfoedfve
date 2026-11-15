# 出图在云端：这台机器怎么装、怎么跑

11-15 夜起管理员电脑不再用，真机图在 s1 自己的云端机器上出。这份记的是**从一台空机器重装一遍**的完整做法，照抄即可。机器：4 核、16 GB、无显卡（软件渲染），Ubuntu 24.04。

代号 s1。工作树 `/agent/repos/c164-s1`（分支 `cursor/c164-s1-render-9df7`）。游戏文件都在 `/agent/realms-study/`，不进仓库。

## 0. 一句话流程

```
cloud_setup.sh  →  cloud_game.sh（以下第 1 到 4 节都是它做的）
→  server-up  →  place.py（摆两次）  →  makepack.py  →  client-up  →  shoot.py  →  down
```

**`tools/cloud_game.sh` 一条命令把这台机器装到能开游戏**，跟 `cloud_setup.sh` 一个写法，重跑无害：

```
cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-realms-map-b59c \
  && git show FETCH_HEAD:c164-realms/tools/cloud_game.sh | bash -s --
```

它装第 2 节那四个系统包、做 JRE 软链、取客户端和服务端、写服务端的几个文件，最后用
`--check-only` 自查一遍。**`bash tools/cloud_game.sh --check-only` 可以单独跑**：不装东西，只说
什么不在，缺东西时退出码 1。下面第 1 到 4 节还是留着——它是这个脚本在做的事，手工重装或者
它坏了的时候照着做。

## 1. 基础（cloud_setup.sh 做的）

```
cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-realms-map-b59c \
  && git show FETCH_HEAD:c164-realms/tools/cloud_setup.sh | bash -s -- s1 cursor/c164-s1-render-9df7
```

最后一行必须是 `ready`。它给 `/agent/realms-study/.venv`（numpy、Pillow、nbtlib、numba，**不许加包**）和 26.3 客户端 jar（`client26/versions/26.3/26.3.jar`，核对过 SHA-1）。

## 2. 系统包（只有这一件事允许装）

只在这一步装系统包；Python 的 venv 照旧不加包。

```
sudo apt-get install -y openjdk-25-jdk-headless mesa-vulkan-drivers mesa-utils vulkan-tools imagemagick
```

四个都必需，缺一个的后果：

| 包 | 缺了会怎样 |
| --- | --- |
| `openjdk-25-jdk-headless` | 26.3 要 Java 25（`javaVersion.majorVersion = 25`）。系统自带的 21 起不来 |
| `mesa-vulkan-drivers` | Xvfb 下 OpenGL 后端失败（`Couldn't find matching GLX visual`），游戏要退到 Vulkan；没有 `lvp_icd.json` 就是 `Installed Vulkan doesn't implement the VK_KHR_surface extension`，两个后端都失败，客户端直接崩 |
| `mesa-utils` / `vulkan-tools` | 只用于自查（`glxinfo -B`、`vulkaninfo --summary`），可以不要，装了几秒钟 |
| `imagemagick` | `tools/shoot.py` 在 Linux 上用 `import -display :164 -window root` 抓屏，没有这个命令就 `FileNotFoundError: 'import'` |

四个都由 `tools/cloud_game.sh` 装。

Java 25 装完是 `/usr/lib/jvm/java-25-openjdk-amd64`。仓库脚本默认找 `/agent/realms-study/jdk/jdk-25.0.5+8-jre/bin/java`（Windows 路径的写法），做一个软链即可，不用改脚本：

```
mkdir -p /agent/realms-study/jdk
ln -sfn /usr/lib/jvm/java-25-openjdk-amd64 /agent/realms-study/jdk/jdk-25.0.5+8-jre
```

## 3. 客户端和服务端文件（只从 Mojang 官方地址取）

```
mkdir -p /agent/realms-study/server26
cd /agent/repos/c164-s1/c164-realms/tools
/agent/realms-study/.venv/bin/python fetch_client.py 26.3 /agent/realms-study/client26 \
    --skip-music --server /agent/realms-study/server26
```

- 取 5124 个文件，约 50 秒；每个都按元数据里的 SHA-1 核对。输出一行 JSON，`downloaded` 应该是 5123 上下、`server_downloaded: true`。
- 不进仓库。`--skip-music` 省掉音乐资源。
- 26.3 的元数据：`javaVersion.majorVersion = 25`，`mainClass = net.minecraft.client.main.Main`，资源索引 34，114 个库。

## 4. 服务端配置

`tools/winmc.py` 的 `setup()` 是 Windows 的（`import deskstate` 会 `ctypes.WinDLL` 挂掉），Linux 上直接手写这几个文件。在 `/agent/realms-study/server26/`：

- `.rcon_pw`：`secrets.token_hex(16)`，权限自己看。**机密，不进仓库、不打日志。**
- `eula.txt`：`eula=true`
- `server.properties`：照 `tools/winmc.py` 的 `SERVER_PROPERTIES` 抄，全部都是要的：
  - `server-ip=127.0.0.1`（**测试服只监听本机**，这是唯一还留着的对管理员电脑那条规矩）
  - `online-mode=false`、`server-port=25599`、`rcon.port=25598`、`enable-rcon=true`
  - 虚空世界：`level-type=minecraft:flat` + `generator-settings={"biome":"minecraft:the_void","layers":[{"block":"minecraft:air","height":1}]}`
  - `allow-flight=true`、`pause-when-empty-seconds=-1`、`max-tick-time=-1`、`sync-chunk-writes=false`
  - `gamemode=spectator`、`force-gamemode=true`、`view-distance=14`、`simulation-distance=6`

## 5. 起服务端

```
cd /agent/repos/c164-s1/c164-realms && MC_SERVER_HEAP=2G bash tools/mc.sh server-up
```

tmux 会话 `c164-mc-server`。实测 **0.5 秒** 起来（虚空世界，没有地形要生成），RCON 在 `127.0.0.1:25598`。`niceness 10`，OOM 时先杀我们（`oom_score_adj 600`）。

## 6. 摆场景

```
cd build
python place.py obs --world /agent/realms-study/server26/art \
    --pw-file /agent/realms-study/server26/.rcon_pw --at 0 200 0
```

**要摆两次。** 第一次会写 biome/timeline 进数据包，服务端要先重启才认：

```
mc.sh server-down && mc.sh server-up && 再跑一遍 place.py
```

判据：第一次 `fillbiome` 报 `Can't find element 'c164art:obs_blue'`、最后一行 `biome ...: 0 cells set`；重启后再跑没有报错，最后一行 `biome c164art:obs_blue: 557424 cells set in 4 boxes`。**看到 0 cells set 就是没生效**，那样天空和雾是错的。

实测：68597 方块 + 4 个展示实体，生成加摆放 0.4 到 0.5 秒，`0 failed`。

## 7. 资源包

```
cd build && python makepack.py obs --out /agent/realms-study/client26/game/resourcepacks/c164art
```

`options.txt` 里要有 `resourcePacks:["vanilla","file/c164art"]`。这台机器上 `options.txt` 是手写的（照 `tools/winmc.py` 的 `OPTIONS` 抄），关键几项：`renderDistance:14`、`particles:0`、`graphicsPreset:"custom"`、`guiScale:2`、`pauseOnLostFocus:false`、`soundCategory_master:0.0`、`maxFps:60`、`fullscreen:false`、`fov:0.0`。

## 8. 起客户端

```
cd /agent/repos/c164-s1/c164-realms && MC_SERVER_HEAP=2G bash tools/mc.sh client-up
```

`tools/run_client.sh` 自己起 Xvfb（`:164`，1280x720x24，`-nolisten tcp`），设 `LIBGL_ALWAYS_SOFTWARE=1`、`GALLIUM_DRIVER=llvmpipe`、`LP_NUM_THREADS=3`、`SDL_VIDEODRIVER=x11`、`ALSOFT_DRIVERS=null`，离线模式登录 `C164Cam`，nice 10，堆 2 GB。

日志 `/agent/realms-study/client26/client.log`。**成功的样子**（这两行都要有）：

```
Failed to create backend OpenGL / Couldn't find matching GLX visual       <- 正常，Xvfb 下必然失败
Using graphics backend Vulkan, using drivers: 1.4.318 llvmpipe Mesa 25.2.8-0ubuntu0.24.04.4 (LLVM 20.1.2)
```

看到 `Vulkan is not supported: Installed Vulkan doesn't implement the VK_KHR_surface extension` 就是缺 `mesa-vulkan-drivers`（第 2 节）。

`Download-2/ERROR: Failed to fetch user properties ... 401` 和 `Realms feature flags` 报错都是**正常**的：离线登录没有令牌。不影响进本机服务器。`mc.sh client-up` 最后打印 `C164Cam is online` 才算成，**实测约 10 秒**。

## 9. 出图

```
python tools/shoot.py <shots.json> --pw-file /agent/realms-study/server26/.rcon_pw \
    --out <目录> --origin 0 200 0 --settle 6 --first-settle 20
```

- `--origin 0 200 0`：机位是场景坐标，摆放位置是 `0 200 0`。
- 抓屏走 `import -display :164 -window root`，抓的是整个 1280x720 虚拟屏。
- `shoot.py` 自己会 `gamemode spectator`、`gamerule advance_time false`（时钟停住，否则等几秒画面就变天）、按 `time` 设到 14000。

**实测时间**（12 个看板视角，4 核，服务端和客户端同时在线）：

| | 秒 |
| --- | --- |
| 第一个镜头（含区块加载，`--first-settle 20`） | 20 |
| 之后每个镜头（`--settle 6`） | 约 6.5 |
| **12 个镜头一共** | **92 秒**（1 分 32 秒） |
| 只拍 V1、V2 两个 | 34 秒 |

## 10. 收工

```
MC_SERVER_HEAP=2G bash tools/mc.sh down
```

先关客户端再关服务端。游戏常开占两块内存（客户端 2 GB + 服务端 2 GB），这台 16 GB 的机器同时开服务端、客户端、离线渲染会很紧（实测同时在线时 `available` 只剩 2.4 GB），所以**攒一批再开，拍完就关**。

## 11. 和离线图差在哪儿（真机才有）

同一机位 V2，左离线右真机（`renders/board/<提交>-real/v02_axis-side.png`）看得很清楚，天空整片色调不同：离线 `(23,29,67)`，真机 `(44,36,60)`。这是**已知的**：`plan/parts/sky.md` 第 92 行写着离线渲染器不画余晖扇面、朝西的雾色、原版云，天空以真机为准。

真机才有、离线没有的：

- **云海**（v12_aerial 里整片紫色云层，离线是空的）
- 余晖扇面、朝西的雾色、天空的渐变
- 粒子、方块实体、原版云

所以**评审判发光、天空、云、玻璃反光、模型远看，要看真机图**，离线图判不了。

## 12. 省时间：换资源包不用重启客户端

改了资源包（换彗星版本、改贴图）以后，给游戏窗口发 **F3+T** 重载资源，约 25 到 32 秒，客户端不用重开：

```
export DISPLAY=:164
WID=$(xdotool search --class "minecraft" | tail -1)
xdotool key --clearmodifiers keydown F3 key t keyup F3
```

重载完等 30 秒再拍。实测：换彗星三版（甲、乙、丙）都用这个，一次都没重启客户端。

**换彗星版本的做法**（总监 11-16 要的三版比选）：
1. 改 `build/scenes/obs/sky/comet.py` 的 `DEFAULT_STYLE`：`"a"` 甲 柔光长尾、`"b"` 乙 硬像素、`"c"` 丙 宽扇尾。
2. `cd build && python makepack.py obs --out /agent/realms-study/client26/game/resourcepacks/c164art`（约 0.8 秒，输出里会写 `comet (b) -> ...`，看这个字确认切对了）。
3. F3+T，等 30 秒，`shoot.py`。
4. **改完把文件恢复原样**（`git status` 要干净），别把切版留在分支上。

三版在同一座整楼、同一对机位下拍的，差别主要在彗星本身和它投的光：V1 里甲和乙有 1.47% 的像素不同、甲和丙 1.43%，差异散布在整幅画面上（彗星的亮部也在动），不只是彗星那一小块。


## 13. 云和视距：两个必须记住的数（11-16 夜量出来的）

**`cloudRange` 的上限是 128。** 写 512 客户端会报
`Error parsing option value 512 for option Cloud Distance: Value 512 outside of range [2:129]`，
然后**用自己的默认值**——也就是说你以为设到最大，实际没设上。写 128。

**`renderDistance` 默认 12，范围 2 到 32。** 这两个不是一回事：
- `cloudRange`（云距离）最大 128，决定原版云层画多远。
- `renderDistance`（视距）决定方块画多远。26.3 默认 **12**，也就是 192 格外**方块云不画**。

所以：**看板真机图一律视距 12**（总监 11-16 定：玩家实际看到的样子）。视距 32 拍的图不能代表玩家看到的东西——192 格外的方块云在 12 里根本不存在，云层边界露不露完全不一样（实测 v12 那一个机位，视距 12 下 D384 和现状差 23.9%，和视距 32 下的数完全不同）。

`shots.txt` 里要记上视距和 `cloudRange`。

改这两处要同时改客户端和服务端：

```
# 客户端 /agent/realms-study/client26/game/options.txt
renderClouds:"true"      # 高品质；"fast" 流畅；"false" 关
cloudRange:128           # 上限就是 128
renderDistance:12        # 玩家默认

# 服务端 /agent/realms-study/server26/server.properties
view-distance=12
```

两份都改完要**重启客户端**（options.txt 只在启动时读），服务端改 view-distance 也要重启。
服务端视距开到 32 时堆要给到 3 GB（`MC_SERVER_HEAP=3G`）。

**核过的方式**：`grep "Error parsing option value" client.log` 应该是空的；有这一行就说明某个值被系统拒了、游戏在用默认值。

## 14. 踩过的坑

1. `tools/winmc.py` 不能在这台机器上 `import`：`tools/win/deskstate.py` 第 18 行 `ctypes.WinDLL` 只有 Windows 有。Linux 上照第 4 节手写配置，不要绕着改它。
2. `place.py` 第一次跑一定 biome 失败，要重启服务端再摆一遍（第 6 节）。
3. Xvfb 下 OpenGL 后端必然失败，靠的是 Vulkan llvmpipe；`mesa-vulkan-drivers` 装不装是分水岭。
4. `shoot.py` 要 `import` 命令，即 `imagemagick`。
5. 时钟：`shoot.py` 会 `advance_time false`。手动查图时如果自己 `tp`，记得也关，否则等 6 秒画面就换了天。
