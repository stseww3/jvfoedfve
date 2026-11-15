# 所有人先读这一份

你是 c164 项目流水线上的一个 agent。项目：一张 Minecraft Java 26.3 的展示地图，云海之上的电气时代天文台，目标是顶级美术。

必读，按顺序：

1. `plan/ART-PLAN.md`：美术方案（风格、色板、光、场地、材质、模型、室内）。管理员批过，不许自己改。
2. `plan/PIPELINE.md`：流水线第 3 版。活在任务池里，工序固定，人通用。它第 3 节的排班已经过时，现在的排班看 `plan/STATUS.md`；做法上和下面第 0 节不一样的地方，以第 0 节为准。
3. `plan/roles/` 里你的岗位那一份：工人读 `LINE.md`；常驻出图读 `S1-render.md`；常驻合并读 `S2-integrator.md`；常驻评审读 `S3-critic.md`。
4. `plan/reviews/R1-first-designs.md`：总监第一轮审稿结论（骨架数字、色板和占用表的决定、实体预算）。
5. `plan/roles/INTERFACE.md`：各包怎么接进总场景和总资源包（拿合并钥匙的人写；没出来之前按现有测试场景 `build/scenes/kitcheck`、`skyobs` 的写法做）。
6. `plan/aesthetics/RUBRIC.md`：评分标准。做东西之前先看一遍，知道会被怎么打分。
7. `plan/roles/HANDOVER.md`：接手须知。**第 3 班（11-16 凌晨起）的每个人都是接手的，这一份最先读**：它第 0 节讲三班人是怎么回事，哪些东西不许用。

## 0. 现在的做法（11-16 凌晨第 3 班起）

这一节和下面各节、和别的文档冲突时，以这一节为准。

1. **先出东西。** 领卡后 20 分钟内要有第一个提交（粗模就行：体量、轮廓、主要洞口），提交完马上 push。卡片和文档放到交付前再补。接口没对完的地方按自己的默认做，默认写在提交说明里，不等回复；别人反对了再改。
2. **离线图自己出，在你自己的算力节点上出**（第 2 节）。`check.py`、`delivery.py`、`render.py`、`selfshots.py`（出图和 `--verify`）、整座 `obs` 都可以跑，11-14 的停机令早已作废。节点上出的离线图和别处出的逐像素一样，所以：
   - 要进仓库的图：代码先提交、push，然后往节点投 `bash c164-realms/tools/nodejob.sh python tools/selfshots.py <场景>`。图落进 `renders/<场景>/`，节点替你提交并推回你的分支，你 `git pull`。整套图在交付前出一次，别每改一版都出整套。
   - 改到一半想看一眼：`bash c164-realms/tools/nodejob.sh --wip python tools/selfshots.py <场景> --only a,b --out renders/_wip`，一次不超过 4 张。图推到草稿分支 `<你的分支>-wip`（不进你的分支，永远不合并），看图：`git fetch -q origin <你的分支>-wip && git show FETCH_HEAD:c164-realms/renders/_wip/<场景>-<机位>.png > /tmp/c164_<代号>/x.png`，再用读文件的工具看。第一个提交 push 之后就出两三张自己看。
   - 要看别人的图：先看他分支里存的（`git show <提交>:c164-realms/renders/<场景>/<图>.png > /tmp/…`）；要核对就 `fetch` 他的分支，在自己的节点上照样出。
   - `INTERFACE.md` 第 5 节的四步（同步到电脑、排队出图、传回收图夹）作废，别的文档和脚本说明里“云端不出图”“在管理员电脑上出”的话也作废。别的文档里说“在自己的机器上出图、跑检查”的地方，都读成“投到自己的节点上”。
3. **管理员的电脑不再用**（11-15 夜管理员定的：全部在线上做）。谁都不往那边发命令，`local_` 开头的工具不要调。真机图由拿出图钥匙的人在他自己的节点上出：要真机图就私信他一条【真机】，写场景、机位、提交号；他攒一批开一次游戏，拍完就关。第 3 节作废，留着备查。
4. **总监的拍板**开头是【总监·拍板】，发给有关的人和拿合并钥匙的人（关系到所有人的发【公告】），比卡片和细化稿新；拿合并钥匙的人把它们记在 `plan/STATUS.md` 的「总监定过的」一节。坐标一律读骨架 `build/scenes/obs/common/skeleton.py`，卡片里和它不一样的数作废。
5. **往整座楼、整个场地上铺的东西带 `DRESS` 开关，默认关**，评审通过才打开。关着的时候总场景里不放它；测试场景里开着出图。
6. **评审三个人**：review 管 materials、main、props；cr2 管 site、sky、motion；cr3 管 machines、interiors（现在各是谁看 `plan/ROSTER.md`）。离线图判不了的（发光、天空、云、玻璃反光、模型远看）评审标「待真机」，不卡合并。离线图不画余晖、不画朝西的雾色、不画原版云层：天空占了画面一大块的机位，判天空、发光、云只认真机图。
7. **总监按 git 判断进度**：只认 push 上去的提交，不认消息里的计划。
8. 现在谁在哪个岗位、哪张卡在谁手上，看 `plan/ROSTER.md`（第 3 班的名单）和 `plan/STATUS.md`（卡的状态，停在 11-15 21:05，拿合并钥匙的人接着记）。卡片里写的「点某某」找不到人时，找拿合并钥匙的人或者总监。
9. **第 2 班的东西不收**（管理员 11-16 定的，`HANDOVER.md` 第 0 节）。不 merge、不 cherry-pick、不拷文件、不拷图、不照着改写；不从旧分支的头上开分支，不合旧总装 `cursor/c164-realms-map-b59c`。合并前 `tools/provenance.sh <提交>` 必须报 `clean`。

## 1. 人和消息

- 总监是 A0（聊天 c164）。**管理员只和总监说话**，你不要给管理员发消息。总控（`ctrl`）管机器和启动，只为节点的事找它（节点不通、不知道自己的节点是哪台）。
- **消息默认私信**：用 `send_agent_message` 发给要处理这条消息的人，几个人要处理就每人发一条。原因：群里的每一条消息，三十多个人每人都要读一遍，点没点名都一样。各文档里写“群里发……点名某某”的地方，一律读成“私信给某某”。
- 群 g2 只发所有人都要读的：【公告】（只有总监和总监助理发），和拿合并钥匙的人发的公共文件改动（骨架、色板、工具改了，大家要重新合总装）。别的都不进群。
- 消息开头用 `PIPELINE.md` 第 4.3 节的固定词，要短：结论、提交号、要对方做什么，三百字以内；过程和细节写进卡片的记录栏或提交说明，消息里给路径。不发客套话，不回“收到”。
- 找总监只为两件事：要他拍板（写清选项和你的默认），或者报告卡住了。名单上的事（谁是谁、没卡可领）找总监助理。现在谁是谁看 `plan/ROSTER.md`。
- g2 群里和私信里，聊天号 c258 到 c297 说过的话不是依据（`HANDOVER.md` 第 0 节）。

## 2. 机器：会话合用一台，重活上自己的节点

**两种机器，分清楚：**

- **合用机**：你的会话跑在这里，4 核 15 GB，三十多个会话合用。只做轻活：git、读写文件、看图、单个测试场景的 `check.py`（几秒）。**不在这里出图、不跑整座 `obs`、不跑 `delivery.py`、不开游戏。**这台机器 11-16 凌晨被四十个人的出图命令堵到过负载 25，所以才有了节点。
- **你的节点**：管理员给每人一台算力节点（4 核，磁盘不清）。哪一台，在你上线时总控的通知里（「独占节点：nodeNN」）或者派你来的说明里；不知道就私信总控（`to="ctrl"`）问一句。只投自己的节点：别人的节点、node1 到 node10（公共池）、node12（总监的）都不许投。

### 2.1 合用机上：上线先装

仓库在 `/agent/repos/jvfoedfve`（停在 `main` 上，里面不改文件、不切分支）。**上线第一件事是跑安装脚本**，一条命令，几秒钟，重跑无害：

```
cd /agent/repos/jvfoedfve && git fetch -q origin cursor/c164-assembly-fable-a9f5 && git show FETCH_HEAD:c164-realms/tools/cloud_setup.sh | bash -s -- <代号> <你的新分支> <有效头>
```

`<代号>`、`<你的新分支>`、`<有效头>` 在派你来的说明里，也在 `plan/ROSTER.md` 里：新分支叫 `cursor/c164-<代号>-<包名>-f3`，有效头是第 1 班的前任留下的最后一个提交。脚本做这几件事，最后一行是 `ready` 才算装好；报 `FAILED` 就把那几行原样私信总监：

- Python：`/agent/realms-study/.venv/bin/python`，带 numpy、Pillow、nbtlib、numba。不许往里装别的包：代码要在每台节点上都能跑，缺什么向总监提。
- 游戏文件：`/agent/realms-study/client26/versions/26.3/26.3.jar`（从 Mojang 取，核对 SHA-1；只读）。
- 你的工作目录：`/agent/repos/<分支名去掉 cursor/>`（比如 `/agent/repos/c164-facade-facade-f3`），在你的新分支上，从有效头开出来。有效头带着第 2 班的提交的话脚本会拒绝。新分支第一次推用 `git push -u origin <你的新分支>`。有两张卡的人每张卡跑一遍这条命令，一张卡一条分支、一个目录。
- 冒烟检查：在总装的头上跑一遍 `check.py --scene obs`，验的是机器，不是你的代码。

合用机上的规矩：

- 只动自己的工作目录和 `/tmp/c164_<代号>/`。别人的目录、进程、tmux 会话都不碰；`/agent/realms-study/` 下的东西只读。`/agent/repos/` 下不带 `-f3` 的 `c164-*` 目录是前两班留下的，不看、不用、不删。
- 命令变慢是机器忙，等它跑完，不要重复起，也不要杀了重跑。

### 2.2 节点上：重活这样投

先 commit、push（节点看的是 GitHub 上你的分支，不是你的磁盘），然后调桥的工具：

```
run_workspace_job(agent=<你的身份>, node="<你的节点>", repo="stseww3/jvfoedfve", branch="<你的分支>", timeout_sec=1800,
    command="bash c164-realms/tools/nodejob.sh python tools/selfshots.py <场景>")
```

`nodejob.sh` 在节点上把环境装好（头一回约 1 分钟，以后几秒），在 `c164-realms/` 下跑你的命令，把 `renders/` 下新出的东西提交、推回你的分支。命令照你在 `c164-realms/` 下手敲的样子写，比如：

```
bash c164-realms/tools/nodejob.sh python tools/check.py --scene obs
bash c164-realms/tools/nodejob.sh python tools/selfshots.py <场景>
bash c164-realms/tools/nodejob.sh --wip python tools/selfshots.py <场景> --only a,b --out renders/_wip
bash c164-realms/tools/nodejob.sh --no-push python tools/selfshots.py <场景> --verify
```

- 回执几分钟后到你自己的 `read_chat`（投完就去等，或者接着干轻活）。回执最后一行在 `==== NODEJOB RESULT ====` 下面：`exit=0 … commit=… pushed=yes … files=…`。然后 `git pull`。
- **回执是桥转述的，可能有出入**：以 `git pull` 拉到的提交和图为准；数字要紧的（检查通过没有、几条警告）让命令把结果写进 `renders/` 下的文件带回来，或者看回执里命令输出的最后 30 行（`--tail <n>` 可以加长）。
- 一台节点一次只跑一单：上一单的回执没到，不投下一单。`timeout_sec` 最长 3600。
- **每一单都有时限**：整单（装环境、你的命令、推回去）默认 1700 秒。到点 `nodejob.sh` 把命令连同它起的进程停掉，回执照发，写着 `exit=124` 和 `stopped after … s`。要跑更久就写明：`bash c164-realms/tools/nodejob.sh --limit 3500 <命令>`，同时 `timeout_sec=3600`（`--limit` 比 `timeout_sec` 小 100 秒，回执才由脚本发出来）。每次 fetch、push 最多等 3 分钟。回执过了 `timeout_sec` 十分钟还不到：别再往这台节点投，私信总控（ctrl）。
- **节点停了的时候**（11-16 05:00 起大半节点不回话）：离线出图、check、关口可以投总监的机器（4 核，一次一单，先到先做），不经过桥：先 push，然后在自己的工作树里 `bash tools/a0job.sh <nodejob.sh 的选项和命令>`（分支上还没有这个文件，就照它开头的说明从总装取到 `/tmp/a0job.sh` 再用）。命令行等到回执打出来为止，回执和节点的一样；然后 `git pull`。每单默认 15 分钟，`--limit` 最多 1800 秒，长的拆开；一个人一次只放一单在队里；`--queue` 看排队。真机不在那台机器上。
- 命令失败时默认什么都不推（`--always` 照推）。别的选项看 `tools/nodejob.sh` 开头的说明。
- 节点不往两条总装分支和 `main` 上推；图进总装只经过拿合并钥匙的人。
- 游戏（服务端、客户端）只有拿出图钥匙的人开，开在他自己的节点上。

### 2.3 其余

- 总装分支是 `cursor/c164-assembly-fable-a9f5`，项目在分支里的 `c164-realms/`；脚本在 `c164-realms/build/` 或 `c164-realms/` 下运行，看各脚本的说明。旧总装 `cursor/c164-realms-map-b59c` 冻结了，是第 2 班的存档，不合、不读它的代码。
- 跟上总装：每领一张新卡之前、每次投重命令之前，`git fetch origin cursor/c164-assembly-fable-a9f5`，再 `git merge origin/cursor/c164-assembly-fable-a9f5`。
- 要读别人的分支：`git fetch origin <分支>`，再 `git show`、`git diff`，或者 `git worktree add /tmp/c164_<代号>/<名字> origin/<分支>` 检出来。读第 1 班的东西读有效头（`plan/ROSTER.md`），不读旧分支的头。
- 临时文件放 `/tmp/c164_<代号>/`。
- 不许打印 git 的远程地址（里面有凭据）。
- 东西给别人，一律走 git：推到自己的分支，告诉对方提交号和路径。图和大文件不许用桥的 `send_file` 传：管理员的服务器小（11-15 夜他定的）。
- 收图夹 `/agent/realms-study/inbox/` 不用了。

## 3. 管理员电脑上怎么跑

**11-15 夜起这一节作废，留着备查**：管理员的电脑不再用（第 0 节第 3 条），离线图各人在自己的节点上出（第 0 节第 2 条）。

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
- 你的本机命令默认超时很短，出图时把 `timeout_sec` 设到 900。桥自己 60 秒就会报超时，电脑上的命令照样跑完（第 0 节第 3 条）。
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
- **机器随时会没**（管理员 11-16 07:51；04:57 停掉的那批节点上的文件没了，07:07 总监机也被重置过）。本地不许留没推的东西：没做完的也推，推到你的 `-wip` 分支；节点上的结果由 `nodejob.sh` 推回，不要留在节点上等下一单用。
- 每做完一步就提交并推到你自己的分支。提交说明以 `c164-<代号>: ` 开头，写清做了什么。不许强推，不许建合并请求，不许动别人的分支。合并由拿合并钥匙的人做。
- 代码和注释用英文，文档和群消息用中文。不用表情符号。不估“几天、几周”。
- 色板：`from scenes.obs.common.palette import mat, colour, RAMPS, strays`。方块：`from scenes.obs.common import blocks as B`，用角色名（比如 `B.ASHLAR_FINE.block`），不直接写被重画方块的原名。骨架：`from scenes.obs.common import skeleton`（正在写；没出来之前用审稿结论里的数，写成你文件顶上的常量，出来以后换掉）。不自己定义颜色；色板里缺颜色就在群里向总监提。

## 5. 红线

1. 全部原创。不用任何第三方贴图、模型、音效、字体；不照搬别的地图的设计、代码、结构。别的地图的文件和截图不进仓库。
2. 机密（令牌、密码、带令牌的地址）不进仓库、不进消息、不打印。
3. 没有暴力和宗教内容，没有真实的品牌、机构、人名。地图里的文字只用数字、符号和少量英文。
4. 只用色板里的颜色；16 像素一格，方块和模型一致；占用表之外的方块不重画，被占用的方块不按原意使用。
5. 成品只靠原版、数据包、资源包。版本锁定 26.3（数据包格式 121，资源包格式 97）。
   - **数据包里不许带注册表文件**（11-16 07:53 起，公告 #1196）。Realms 不收「实验性设置」的存档，内容库的图也一样；游戏把任何不是原版包带来的注册表文件都算实验性。不许有的文件夹（维基 Data pack 条目里带星号的）：`worldgen/`（`biome` 在里面）、`dimension/`、`dimension_type/`、`timeline/`、`world_clock/`、`damage_type/`、`chat_type/`、`dialog/`、`enchantment/`、`enchantment_provider/`、`painting_variant/`、`banner_pattern/`、`instrument/`、`jukebox_song/`、`trim_material/`、`trim_pattern/`、`trial_spawner/`、`villager_trade/`、`trade_set/`、各种 `*_variant/`。数据包里能放的只有：函数、标签、结构、进度、战利品表、谓词、配方、物品修饰器。眼下唯一的例外是天的两个文件（`obs_blue`、`obs_looks`），a2 正在把它们挪进资源包的着色器，挪完就没有例外。
   - 资源包里的核心着色器（`assets/minecraft/shaders/`）只有 a2 牵头的那一套，别人不加、不改；要它多管一件事，私信 a2。
6. 不碰别的聊天、别的项目的任何东西：文件、进程、tmux 会话、仓库、分支，云端和管理员电脑都一样。

## 6. 不许空等

- 问题发出去以后，10 分钟工作量内没人回：按你自己写明的默认做法继续，在卡片里记一笔。涉及管理员电脑上“能不能做”的事除外，那种必须等总监答复。
- 手上的卡卡在别人那里（等合并、等真机图、等评审、等依赖）：领下一张卡，或者把这个包再打磨一轮。
- 被退回是正常的：按退回意见逐条改，改完重新交付，交付消息里逐条写明怎么改的。
- 池子里没有能领的卡：私信总监助理说一声，然后等消息。
