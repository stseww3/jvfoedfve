# 所有人先读这一份

你是 c164 项目流水线上的一个 agent。项目：一张 Minecraft Java 26.3 的展示地图，云海之上的电气时代天文台，目标是顶级美术。

必读，按顺序：

1. `plan/ART-PLAN.md`：美术方案（风格、色板、光、场地、材质、模型、室内）。管理员批过，不许自己改。
2. `plan/PIPELINE.md`：流水线第 3 版。活在任务池里，工序固定，人通用。第 3 节是现在的排班。
3. `plan/roles/` 里你的岗位那一份：工人读 `LINE.md`；常驻出图读 `S1-render.md`；常驻合并读 `S2-integrator.md`；常驻评审读 `S3-critic.md`。
4. `plan/reviews/R1-first-designs.md`：总监第一轮审稿结论（骨架数字、色板和占用表的决定、实体预算）。
5. `plan/roles/INTERFACE.md`：各包怎么接进总场景和总资源包（拿合并钥匙的人写；没出来之前按现有测试场景 `build/scenes/kitcheck`、`skyobs` 的写法做）。
6. `plan/aesthetics/RUBRIC.md`：评分标准。做东西之前先看一遍，知道会被怎么打分。

## 1. 人和群

- 总监是 A0（聊天 c164）。**管理员只和总监说话**，你不要给管理员发消息。
- 全员一个群 g2。发消息必须用 mentions 点名要处理这条消息的人；只做记录的消息 mentions 填 `[]`。不发客套话，不回“收到”。
- 消息开头用 `PIPELINE.md` 第 4.3 节的固定词。【公告】只有总监发。

## 2. 云端机器上的路径

- 总装仓库：`/agent/repos/jvfoedfve-c164`，分支 `cursor/c164-realms-map-b59c`，项目在里面的 `c164-realms/`。**只读**：不许在这个目录里改文件、切分支、提交。
- 你自己的工作目录，第一次这样建（`<代号>` 见 `PIPELINE.md` 第 3 节）：

```
git -C /agent/repos/jvfoedfve-c164 fetch -q origin cursor/c164-realms-map-b59c
git -C /agent/repos/jvfoedfve-c164 worktree add -b <你的分支> /agent/repos/c164-<代号> origin/cursor/c164-realms-map-b59c
```

  分支名按你自己的命名规则起，中间带 `c164-<代号>`。之后只在 `/agent/repos/c164-<代号>` 里干活。
- 跟上总装：每领一张新卡之前，`git fetch origin cursor/c164-realms-map-b59c`，再 `git merge origin/cursor/c164-realms-map-b59c`。
- Python：`/agent/realms-study/.venv/bin/python`（共用，只读，不许往里装东西）。脚本在 `c164-realms/build/` 下运行。
- 游戏文件：`/agent/realms-study/client26/versions/26.3/26.3.jar`（只读）。
- 回传的图：`/agent/realms-study/inbox/`（只读，用读文件的工具直接看图）。
- **realms-study 不在仓库里，VM 重启后整个会没掉，由总监重建**（workers 等总监恢复，别自己装）。步骤：

```
# 1) venv（check.py / 离线渲染要 numpy+Pillow+nbtlib）
sudo mkdir -p /agent/realms-study/inbox && sudo chown -R "$USER" /agent/realms-study
sudo apt-get install -y python3.12-venv            # 若报 ensurepip 不可用
python3 -m venv /agent/realms-study/.venv
/agent/realms-study/.venv/bin/pip install "nbtlib==2.0.4" "numpy>=2.0" Pillow
# 2) 只读 jar：从 Mojang 版本清单取 26.3 的 client jar（sha1 校验）下到
#    /agent/realms-study/client26/versions/26.3/26.3.jar。云端只要这一个 jar，不用整份 client
#    （库和 assets 是管理员电脑跑游戏才要，那边用 tools/fetch_client.py）
# 3) 回传通道（tmux 常驻）：
python3 c164-realms/tools/inbox.py /agent/realms-study/inbox --port 8765    # 只听 127.0.0.1
#    再起隧道把 127.0.0.1:8765 暴露成公网 URL（如 cloudflared quick tunnel），把
#    <公网URL>/<inbox/.token 里的 token> 写进管理员电脑 dl/inbox.url（机密：别进群、别进仓库）
# 4) 冒烟：check.py --scene obs 应全 PASS
/agent/realms-study/.venv/bin/python c164-realms/tools/check.py --scene obs
```
- 临时文件放 `/tmp/c164_<代号>/`。
- 不许打印 git 的远程地址（里面有凭据）。

**云端机器只有 4 核，十几个 agent 共用，还有别的项目在上面。** 在它上面只做轻的事：改代码、`git`、语法检查、几秒钟的小脚本，命令前面加 `nice`。不许在它上面出图、生成大场景、跑循环、开服务。这些一律去管理员电脑。

## 3. 管理员电脑上怎么跑

管理员电脑是他自己在用的桌面机，他同时在上面跑自己的活。我们只在一个文件夹里活动：`workspaces\c164`（共用工作区）。你的本机命令默认落在你自己聊天的工作区里，所以**每条命令都这样开头**，先进到共用工作区：

```
Set-Location (Join-Path (Split-Path (Get-Location) -Parent) 'c164')
```

然后只用下面四条（`<代号>` 是你的代号，`<场景>` 是测试场景名）：

```
# 1. 把你分支的最新提交同步过来（先在云端 push）。第一次约 40 秒，之后几秒
.\venv\Scripts\python.exe bin\sync.py <你的分支> --to agents/<代号>

# 2. 轻任务（几秒的预览、打包）
.\venv\Scripts\python.exe bin\job.py <代号> -- preview.py <场景> --out '@out/pv/x'

# 3. 离线出图（重任务，排队执行；--only 可以只出几张）
.\venv\Scripts\python.exe bin\job.py <代号> --heavy --timeout 900 -- render.py <场景> --shots scenes/<场景>/shots.json --out '@out/rt/<提交前七位>'

# 4. 把图传回云端（到 /agent/realms-study/inbox/，文件名前面带你的代号）
.\venv\Scripts\python.exe bin\send.py "agents\<代号>\out\rt\<提交前七位>-*.png" --jpeg 90 --prefix <代号>-
```

说明：

- `job.py` 在你的 `agents\<代号>\repo\c164-realms\build` 里运行脚本，`@out` 会换成 `agents\<代号>\out`。它负责排队、限线程、降优先级、记日志（`agents\<代号>\logs\`）。退出码 75 表示重任务名额一直被占着，过一会儿再试。
- 离线渲染第一次运行要编译约半分钟，之后每张 1 到 5 秒（室外）；室内的图慢得多，分辨率和张数省着用。离线渲染不画粒子、方块实体和原版的云。
- 你的本机命令默认超时很短，出图时把超时设到 900 秒以上。
- 工作区里的脚本版本由拿出图钥匙的人维护。命令报“part must be …”之类的错，说明脚本还没更新，在群里点名他。

规矩，没有例外：

1. 只通过 `bin\job.py` 运行仓库里的脚本。不许绕开它直接跑 Python，不许自己改线程数和名额。
2. 只写自己的 `agents\<代号>\` 文件夹。不许动 `bin`、`venv`、`git`、`client26`、`server26`、`jre`、`dl`、`repo`、`locks`、`cache` 和别人的文件夹。
3. 不许装任何东西。不许碰 `workspaces\c164` 以外的任何文件夹、进程、窗口。旁边别的工作区是别的项目的，不许看不许动。管理员自己的进程（比如几个很吃 CPU 的 `sparrow`）绝对不许动。
4. **测试服和游戏只有拿出图钥匙的人能开能动。** 真机图在合并以后由他出；急用就在群里点名他。
5. 不许并发重试，不许写循环去抢名额。
6. 进不去共用工作区、命令报权限错误、或者弹出要管理员批准的提示：立刻停下，在群里点名总监，不要自己想别的办法。

## 4. 代码和提交

- 只改自己领的卡对应的文件（`PIPELINE.md` 第 4.2 节：代码按卡片的类别放，一个包一个模块）。公共的东西只有拿合并钥匙的人改；`plan/ART-PLAN.md`、`plan/PIPELINE.md`、`plan/roles/` 只有总监改。要改就在群里提。
- 每做完一步就提交并推到你自己的分支。提交说明以 `c164-<代号>: ` 开头，写清做了什么。不许强推，不许建合并请求，不许动别人的分支。合并由拿合并钥匙的人做。
- 代码和注释用英文，文档和群消息用中文。不用表情符号。不估“几天、几周”。
- 色板：`from scenes.obs.common.palette import mat, colour, RAMPS, strays`。方块：`from scenes.obs.common import blocks as B`，用角色名（比如 `B.ASHLAR_FINE.block`），不直接写被重画方块的原名。骨架：`from scenes.obs.common import skeleton`（正在写；没出来之前用审稿结论里的数，写成你文件顶上的常量，出来以后换掉）。不自己定义颜色；色板里缺颜色就在群里向总监提。

## 5. 红线

1. 全部原创。不用任何第三方贴图、模型、音效、字体；不照搬别的地图的设计、代码、结构。别的地图的文件和截图不进仓库。
2. 机密（令牌、密码、带令牌的地址）不进仓库、不进消息、不打印。
3. 没有暴力和宗教内容，没有真实的品牌、机构、人名。地图里的文字只用数字、符号和少量英文。
4. 只用色板里的颜色；16 像素一格，方块和模型一致；占用表之外的方块不重画，被占用的方块不按原意使用。
5. 成品只靠原版、数据包、资源包。版本锁定 26.3（数据包格式 121，资源包格式 97）。
6. 不碰别的聊天、别的项目的任何东西：文件、进程、tmux 会话、仓库、分支，云端和管理员电脑都一样。

## 6. 不许空等

- 问题发出去以后，10 分钟工作量内没人回：按你自己写明的默认做法继续，在卡片里记一笔。涉及管理员电脑上“能不能做”的事除外，那种必须等总监答复。
- 手上的卡卡在别人那里（等合并、等真机图、等评审、等依赖）：领下一张卡，或者把这个包再打磨一轮。
- 被退回是正常的：按退回意见逐条改，改完重新交付，交付消息里逐条写明怎么改的。
- 池子里没有能领的卡：在群里点名总监说一声，然后等群消息。
