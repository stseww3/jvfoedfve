# 出图站（s1）：节点上的离线看板和真机图

出图岗位（代号 s1，拿出图钥匙）自己的文档。岗位职责在 `plan/roles/S1-render.md`，这里写三件事：要图的人怎么要、图回到哪儿；站是怎么搭的；接手的人怎么用、有哪些坑。第 3 班（c319，11-16）写。

## 1. 要图的人看这一节

私信 s1 一条【真机】，写四样：

- **场景**：测试场景的名字（`obs_mat_snow`），或者整座（`obs`）。
- **机位**：场景 `shots.json` 里的名字；不写就是全部。
- **代码**：总装的提交号，或者「分支 @ 提交」。你分支上的提交不必先合并，站会把它检出来拍；但历史里有第 2 班提交的不拍（`tools/provenance.sh`）。
- **要看什么**：一两句。s1 看图的时候照这个看，回话里答这个。

还能要这些（写在同一条里）：

| 要什么 | 说法 | 得到什么 |
| --- | --- | --- |
| 会动的东西 | 「x 机位隔 2.5 秒再拍一张」 | `x.jpg` 和 `x_again.jpg`，同一个位置隔几秒的两张 |
| 细线走动时闪不闪 | 「x 机位向右挪半格再拍一张」 | `x.jpg` 和 `x_step.jpg`。是两张静止的图，不是录像：线在两张里断得不一样，走动时就会闪 |
| 几个光照版本 | 「blue、deep、glow 各拍」，或者 sky 的试验版本的名字 | 每个版本把场景按它的亮窗表重摆一遍再拍，外加一张拼图，一行一个机位、一列一个版本 |
| 两个版本并排 | 「甲乙并排」 | 两个场景同名的机位排成一张，一列一个场景 |
| 挑几张拼一张 | 「这四张拼一张，两个一行」 | `renders/real/_sheets/<名字>.jpg` |
| 拍完在服务端跑一段脚本 | 给脚本在你 `build/` 下的路径 | 脚本打印的东西存成 `after.txt`（见第 5 节） |
| 几套图同一批机位并排 | 「这几个机位，甲那套和乙那套并排」 | `renders/real/_sheets/<名字>.jpg`，一行一个机位、一列一套（哪个提交、哪个视距写在每格的标题里） |

图回到 s1 的分支 `cursor/c164-s1-render-f3-fd9c`，回话里有提交号和路径。图不进总装，要进由拿合并钥匙的人定。

| 拍的是什么 | 路径（都在 `c164-realms/` 下） |
| --- | --- |
| 总装的整座，12 个看板机位 | `renders/real/obs/`，另有 `sheet.jpg`（12 张一页）和 `compare.jpg`（离线和真机左右并排，两套是同一个提交才有） |
| 测试场景 | `renders/real/<场景>/` |
| 某条分支上的整座 | `renders/real-branch/<提交前七位>/obs/`（不顶替看板的图） |
| 光照版本 | 总装的在 `renders/real-looks/<提交>/<版本>/<场景>/`，分支的在 `renders/real-branch/<提交>/looks/<版本>/<场景>/`，拼图 `<场景>-looks.jpg` 在版本文件夹旁边 |
| 客户端视距不是 12 的 | `renders/real-view<n>/<场景>/`（只用来查放远了坏不坏，不当看板图） |
| 服务端视距不是 10 的 | `renders/real-server<n>/<场景>/`（两样都不是标准的是 `renders/real-view<n>-server<m>/`） |
| 并排、拼图 | `renders/real/_beside/<名字>.jpg`、`renders/real/_sheets/<名字>.jpg` |
| 每一趟的日志 | `renders/real/_trips/<时间>-<提交>.log` |
| 离线看板 | `renders/board/<总装提交前七位>/`：12 张 png、`board.json`、`shots.txt`、`sheet.jpg` |

每个场景文件夹里的 `real.txt` 一行一张图：机位、tick、图里的代码是哪个提交、图文件 SHA-256 的前 16 位、拍的时间、客户端视距、服务端视距和云的范围（`view12,server10,clouds128`；按光照版本摆的再加 `windows-<版本>`，开了建筑自己的灯的加 `dressed`）。11-16 07:20 以前的行没有 `server<n>`，那时服务端和客户端一样是 12。一个文件夹里的图可以来自不同的提交，以这一行为准，不以文件夹为准。

图是游戏自己的截图（1280×720），存成 JPEG 90。画面是 Mesa 在处理器上画的，和显卡画的是同一个画面，只是慢。

## 2. 站是怎么搭的

管理员的电脑第 3 班不再用，游戏开在 s1 的节点上（4 核，没有显卡）。一单节点任务从头做到尾：起服务端、摆场景、开游戏、拍、关，图由 `tools/nodejob.sh` 推回分支。节点上不留开着的游戏。

`tools/nodemc.py setup` 在一台新节点上装这些，装过的不动：

- 系统包（`sudo apt-get install`）：`xvfb`、`libvulkan1`、`mesa-vulkan-drivers`、`vulkan-tools`，和 SDL 开窗要的几个 X 库（`libx11-6`、`libxext6`、`libxcursor1`、`libxi6`、`libxrandr2`、`libxfixes3`、`libxss1`、`libxkbcommon0`）。前三个缺了就出不了图，装不上这一趟就停。
- Java 25：节点上没有就从 Adoptium 取 Temurin 的 JRE，核过 SHA-256，放 `$MC_ROOT/jdk/`。
- 游戏文件：`tools/fetch_client.py` 只从 Mojang 的官方地址取，逐个核 SHA-1。客户端在 `$MC_ROOT/client26/`，服务端在 `$MC_ROOT/server26/`。
- 设置：服务端只监听 127.0.0.1，离线模式，虚空平地，RCON 密码随机生成放 `server26/.rcon_pw`（只在节点上，不进仓库、不进消息、日志里遮成 `***`）；客户端离线启动，只连这台服务端。客户端视距 12、服务端视距 10、云的范围 128 每一趟都重新写一遍。
- 视距为什么是两个数：Realms 的服务端视距是 10，改不了（官方的 Realms 地图准则），玩家自己的客户端可以开到 12 以上。所以测试服 `view-distance=10`、客户端 `renderDistance=12`，和 Realms 上一样。服务端 10 意味着：离玩家 10 个区块以外的方块不发给客户端，展示实体离玩家超过 160 格也不发。站位离建筑远的机位（V11、V12）要特别看这一条。

`$MC_ROOT` 就是各岗位 `cloud_setup.sh` 用的 `/agent/realms-study`。

为什么是 Vulkan：26.3 用 SDL 开窗，有 OpenGL 和 Vulkan 两个后端。Xvfb 下 OpenGL 后端找不到它认的 GLX 视觉，游戏自己退到 Vulkan，由 Mesa 的 lavapipe 在处理器上画。游戏日志里是 `Failed to create backend OpenGL` 然后 `Using graphics backend Vulkan ... llvmpipe`，这是正常的，不是故障。站把 Vulkan 的驱动限定成 lavapipe 一个（`VK_DRIVER_FILES`），免得 Mesa 包里给显卡用的驱动先被挑上。

截图：游戏带着一个小助手启动（`tools/win/CamHelper.java`，编好的 class 在仓库里），`tools/shoot.py` 通过它让游戏自己存截图；助手不在或者存不了，就从 X 显示上抓。每张图等画面静下来才算：隔几秒再拍一张，连续两张一样为止（`--still`），日志里每张图后面写着等了几秒、两张之间动了百分之几。

地块：每个场景在测试世界里占一块，间隔 1000 格，表在 `tools/win/plots.json`，整座在 0 号。表里没有的场景，班车给下一个空号，记在节点的测试世界里，日志里有一行 `new plots, to be added to tools/win/plots.json`，s1 事后补进表。号不重用、不重排。换了节点，测试世界是新的，所以表要及时补，否则同一个场景在两台节点上会得到不同的号。

## 3. 一单怎么投

都是 `run_workspace_job`，`repo="stseww3/jvfoedfve"`，`branch` 是 s1 的分支，`node` 是 s1 当前的节点。先把自己的提交推上去，节点只看 GitHub。命令里不要有引号和带空格的值。

```
# 离线看板 12 张（25 秒上下）
bash c164-realms/tools/nodejob.sh python tools/boardrender.py --at <总装提交>

# 真机看板 12 张（4 分钟上下）
bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --at <总装提交>

# 测试场景，只拍点名的机位
bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --at <总装提交> <场景> [<场景> ...] --only <场景>=a,b

# 别人分支上的代码
bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --branch <分支> --at <提交> <场景> --only <场景>=a,b

# 几个光照版本
bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --at <总装提交> --looks blue,deep,glow --only obs=v01_arrival,v02_axis

# 服务端视距 12（老标准）下的三张，放 renders/real-server12/obs/，不顶替看板的图
bash c164-realms/tools/nodejob.sh --always --tail 40 python tools/nodetrip.py --at <总装提交> obs --server-view 12 --only obs=v01_arrival,v11_lookout,v12_aerial

# 几套图同一批机位并排（不开游戏，总监机上跑；文件夹从 renders/ 算起，离线看板的 png 也行）
bash c164-realms/tools/a0job.sh python tools/realshots.py --columns <名字> --shots v01_arrival,v11_lookout server12=real-server12/obs server10=real/obs
```

`--at <总装提交>` 是图的名字：总装头上常常压着只改名单、不改 `build/` 的提交，图要用「`build/` 和现在的总装头一样的最早那个提交」来叫，也就是合并岗在【合并】里报的那个。s1 的分支先合进总装头，自己的 `build/` 和它逐文件一样才画；不一样工具会停下说明。

其余选项在 `tools/nodetrip.py` 和 `tools/win/shuttle.py` 开头：`--again`、`--step`、`--after`、`--apart`、`--beside`、`--sheet`、`--across`、`--view`、`--server-view`、`--clouds`、`--no-place`、`--budget`。

一趟里的场景合用一个资源包、一种光照。两个场景要在包里同一个名字下放不同的文件（同一样东西的两个版本），用 `--apart`，一个场景跑一遍班车。光照文件（生物群系、时间线）变了，班车自己重启服务端。

收图：回执到了以后

```
git fetch -q origin <s1 的分支> && git merge --ff-only FETCH_HEAD
```

本地还有没推的提交时用 `git merge -m "c164-s1: take in the node's pictures (...)" FETCH_HEAD`，不要用 `git pull`（它的合并说明不带 `c164-s1:`）。节点推的时候分支要是动过，`nodejob.sh` 会自己合并再推，所以一单在跑的时候照样可以往分支上推工具。

## 4. 时限

三层，从里到外，里面的先到：

1. `nodetrip.py --budget`（默认 1500 秒）：这一趟总共的时间。最后 120 秒留给收图和关门，所以班车在「时限减 120 秒」的时候被叫停。被叫停的班车不是一刀切断：拍完的图照样整理好带回来（一个场景拍到一半，就带回拍完的那几张，`real.txt` 里只有这几行），游戏由它自己关掉；这一趟算失败，日志里写着拍到了几张。一张图要等它拍完、静下来才得到自己的名字，所以带回来的不会有半张的图。
2. `nodejob.sh --limit`（默认 1700 秒）：到点把命令连同它起的进程停掉，15 秒后杀掉，回执照发，`exit=124`。到了这一步图就不带回来了，只保证关门：`nodemc.py down` 一旦开始，没人听它说话也会做完。
3. `run_workspace_job` 的 `timeout_sec`（最长 3600）：比 `--limit` 至少大 100 秒。

所以 `--budget` 必须小于 `--limit`：让这一趟自己收摊，而不是被外面掐断。排 node12 的时候一单不超过 12 分钟：`nodejob.sh --limit 680 ... nodetrip.py --budget 600`，`timeout_sec=900`。更长的一趟两处都写明：`--limit 3400` 加 `--budget 3200`，`timeout_sec=3600`。

每一趟开头先 `nodemc.py down`，把上一单可能留下的服务端、游戏、显示都停掉（只停从 `$MC_ROOT` 起的、命令行对得上的进程，不认 pid 文件里的数）。

## 5. 拍完跑脚本（`--after`）

有些东西图上看不出来：计分板的数、命令方块链走到哪一步。`--after <场景>=<脚本>` 在这个场景的图拍完以后、场景还摆着、服务端和游戏都开着的时候，跑被拍的那份代码里的一个脚本（路径从它的 `build/` 算起）：

```
python <脚本> --pw-file <文件> --port <端口> --origin X Y Z
```

`PYTHONPATH` 里有 `build/` 和 `tools/`（`rcon.py` 可以直接 import）。限时 300 秒（`--after-budget`）。脚本打印的东西存成 `renders/real/<场景>/after.txt`，开头记着脚本、提交、地块、用时、退出码；退出码不是 0 这一趟算失败。脚本不许关服务端。密码在打印和存下来的文件里都遮成 `***`。

## 6. 测到的数字（node34，4 核，11-16）

node12（11-16 06:20 起）上的数和 node34 差不多：看板 12 张一单 245 到 252 秒；blue、deep 两个版本各 4 个机位一单 253 秒；桅杆 7 张 196 秒；24 张带脚本 300 秒。服务端起来 6 秒，游戏进服约 23 秒，一张 13 到 18 秒。

- 新节点装一遍（node34 上 Xvfb 和 X 库本来就有，只缺 Mesa 的 Vulkan 驱动和 `vulkan-tools`）：系统包 5 秒，Java 2 秒，游戏文件 5124 个 14 秒。
- 服务端起来 10 秒，游戏起来、相机进服再 10 秒；一趟从开始到能拍约 25 秒。
- 整座（约 10 万方块）摆一次 6 秒。
- 真机看板 12 张：一趟 245 秒，其中拍 217 秒，一张 18 秒上下（第一张多等 60 秒让区块画完）。
- 光照版本：每个版本 3 张约 97 秒（场景要重摆）。
- 离线看板 12 张：22 到 26 秒。
- 游戏在两遍班车之间不关，前提是资源包没变。

## 7. 规矩

- 看板的真机图一律客户端视距 12、服务端视距 10、云的范围 128（总监 11-16 07:20；以前服务端也是 12）。别的视距的图另放，不混。
- 游戏只开在节点上，合用机上不开。服务端只监听本机，客户端离线、只连它。
- 游戏文件只从 Mojang 的官方地址取。
- 一台节点一次一单，上一单的回执没到不投下一单。真机的单占满 4 核，合用节点时同时不能有别人的单。
- RCON 密码、`server.properties` 不进仓库、不进消息。
- 第 2 班拍的图、改的脚本一律不用；别人分支的提交先过 `tools/provenance.sh` 才拍。

## 8. 坑

- 看图的工具按路径缓存。同一个路径的图换过以后（`renders/real/obs/sheet.jpg` 每批都换），先拷到一个新名字再看，否则看到的是旧图。
- `v06_power` 等五个机位（V1、V2、V6、V7、V11）是骨架锁定的，`tools/boardshots.py` 只是照抄；另外七个是出图站的提案。骨架改了机位，`boardshots.py --check` 会说存的清单和骨架对不上。
- 测试场景常常把整条 main 线摆出来（大穹顶的场景和整座差不多大），摆和拍的时间按整座算。
- 回执是桥转述的，数字以 `renders/real/_trips/` 里的日志为准。
- `compare.jpg` 由离线看板和真机看板里后到的那一套来画，两套的提交一样才画。真机先到、离线还没出的时候，文件夹里上一批的 `compare.jpg` 会被这一趟删掉，等离线那套出来再画（`boardrender.py` 末尾）。
- `--no-place`（不重摆，接着上一趟摆好的拍）有三件事要知道。一，班车每一趟摆场景之前都 `forceload remove all`，所以上一个场景自己加的强制加载到下一趟已经没了。二，会动的场景靠计分板的 `#run` 认「现在跑的是谁的循环」，一次只有一个场景的循环在跑：摆整座（`obs`）会把 `#run` 拿走，夹在中间拍过整座，前面那个场景的循环就停了。三，场景的函数各在测试世界数据包里自己的文件夹下，不重摆也找得到。所以要查「停服再起以后循环接不接得上」，中间不能夹别的场景的摆放。
- 节点会停。投了单、回执过了 `timeout_sec` 十分钟不到，就不再往那台投，报总控和总监助理。新节点的第一单会自己把第 2 节那些装上，不用另外准备。

## 9. 记录

- 11-15（第 1 班 c189）：地块表、班车 `shuttle.py`、`trip.py`、`realshots.py`、看板机位 `boardshots.py`，在管理员的电脑上跑通。交付 ecf454dd，合并 78d0e548。
- 11-16（第 3 班 c319）：从有效头 9cbe672b 重开。`boardrender.py`（离线看板）、`nodeprobe.sh`、`nodemc.py`（节点上的服务端和游戏）、`nodetrip.py`（一单一趟）、`placelook.py`（按光照版本摆）；`shoot.py` 认助手截图和 `--still`；班车加了 `--look`、`--dress`、`--again`、`--step`、`--after`；`realshots.py` 记视距、`--into`、`--sheet`。看板在 42d7ef6、c992a3a、8b7735e、ec9ac97 四个总装提交上各出了离线和真机一套。
- 11-16 04:57 起一批节点同时停了，node34 在内（那一单大穹顶甲乙并排没有回来）。真机改排 node12，由总监助理发牌，一单不超过 12 分钟；离线看板走总监机（`tools/a0job.sh`）。为此：`nodetrip.py` 的默认时限改成 1500 秒，配合 `nodejob.sh` 新加的 1700 秒；班车被叫停时把拍完的图带回来；`shoot.py` 的图拍完才得名；`nodemc.py down` 没人听也做完。这几样只在合用机上用假的班车和假的相机试过，节点上的第一趟是 node12 上那几单。
- 11-16 07:20：总监定测试服视距 10、客户端 12（Realms 的服务端视距是 10）。`nodemc.py` 认 `MC_SERVER_VIEW`，`nodetrip.py --server-view`，`real.txt` 记 `view12,server10,clouds128`，别的服务端视距的图放 `renders/real-server<n>/`；`realshots.py --columns` 把几套图同一批机位排成几列；`compare.jpg` 改成后到的那套来画（3a3c6ef、2a26eea 两批真机先到，文件夹里留着 ec9ac97 的旧 `compare.jpg`）。地块表补到 53 号。
- 11-16 07:20 到 13:31 这一段的记录没来得及写（进存档拍的那几样工具：`savetrip.py`、`guidetrip.py`、`ridetrip.py`、`look.sh`、`saveround.sh`，用法在各自文件开头），要补。
- 11-17 09:04（第 3 班 c319，11-16 13:31 全队断线以后重开；新的会话，分支不换）：照 `plan/roles/RESTART.md` 从 git 上对出来的断线时的状态，不是凭记忆。断线前最后推上来的是 02fd20aa（13:31:13，B2 暖气干管近景重拍的两张）。B2 这一轮（存档 `cursor/c164-dist-f4b8` @ daefc191，看板 316941ab）的图都在分支上：`renders/real-save/c164-B2`（12 个机位各两张、`moved.txt`、`frames.txt`）、`-asked`、`-guide`、`-film`、`-film2`、`-near`、`-near2`；316941ab 的离线和真机看板也在（`renders/board/316941a/`、`renders/real/obs/`）。没做的：总装后来的代码头 0ece0331 没出过看板；B3 没导出，所以没拍；火车没在游戏里录过。第 6 节和名单里的节点号都作废，用哪台等总监回话。
