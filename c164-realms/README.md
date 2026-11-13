# c164：Realms Mapmaker 披风地图项目

Telegram 聊天 c164 的工作目录。目标：做出能通过 Java Realms 内容创作者计划审核的原创地图。目前在做的是美术测试：不管玩法，只看 agent 用代码能把画面做到什么程度。

## 目录

- `study/published-maps-study.md`：四张已上线 Realms 的地图的拆解结论（规模、共同做法、审核改动、26.x 格式）。
- `study/art-comparison.md`：样品和这四张图的美术对比，以及这个对比的限制。
- `study/raw/`：分析脚本的原始输出。
- `tools/survey.py`、`tools/census.py`：只读的存档分析脚本。
- `tools/fetch_client.py`、`tools/run_client.sh`：下载官方 26.3 客户端，在 Xvfb + Mesa 软件渲染下离线启动，只连本机测试服。
- `tools/rcon.py`、`tools/shoot.py`：通过 RCON 移动镜头玩家并截图。镜头表里的 `pos` 是眼睛的位置。
- `tools/mcbot.py`、`verify/`：用假玩家检查数据包逻辑的脚本和 26.3 服务端验证记录。
- `build/artkit/`：体素画布、方块表、噪声、树和建筑零件、结构模板导出。
- `build/artkit/pixelart.py`、`build/artkit/models.py`：自定义模型工具。模型由盒子、八边/十六边管、圆环拼成，贴图按材质规则生成（每个模型一张图集），用 item_display 实体摆进场景。
- `build/scenes/skyobs/`：样品场景“浮空岛天文台”（地形、塔、小屋、场地、植被、镜头表）。`props.py` 是这个场景的全部自定义模型。
- `build/place.py`：生成场景，导出成数据包里的结构模板（含模型实体），通过 RCON 摆进测试服的世界。
- `build/makepack.py`：把场景的模型和贴图写成资源包（26.3，pack format 97）。
- `build/gallery.py`：把所有模型排成一排单独摆出来并生成镜头表，方便先单看模型再放进场景。
- `renders/`：样品的出图（软件渲染，1280×720）。`skyobs-v5` 是纯原版方块，`skyobs-v6` 加了自定义模型，`props-gallery.jpg` 是模型一览。

## 出图循环

需要一个本机 26.3 服务端（开 RCON，离线模式，虚空世界）和 `run_client.sh` 启动的镜头客户端。客户端要启用生成的资源包（放进 `resourcepacks/` 的文件夹包，`options.txt` 里写进 `resourcePacks`）。

```
cd build
python makepack.py skyobs --out <客户端目录>/resourcepacks/c164art
python place.py skyobs --world <服务端目录>/<世界> --pw-file <服务端目录>/.rcon_pw --at 0 200 0
python ../tools/shoot.py scenes/skyobs/shots.json --pw-file <服务端目录>/.rcon_pw \
    --out <输出目录> --origin 0 200 0 --settle 10 --first-settle 16
```

改了模型或贴图以后，客户端不用重启：给它的窗口发 F3+T（`xdotool keydown F3 key t keyup F3`）重载资源，大约 25 秒。

约 15 万方块加 48 个模型实体的场景：生成 4 秒，摆放 3 到 7 秒，每个镜头约 10 秒。

## 自定义模型的几条实测结论（26.3）

- 物品定义在 `assets/<ns>/items/<名字>.json`，模型在 `models/item/`，贴图在 `textures/item/`；实体用 `minecraft:item_model` 组件指向它。
- 模型元素坐标只能在 -16 到 32 之间（最大 48 个单位，即 3 格）。更大的东西靠 item_display 的 scale 放大；模型的 `px` 取和 scale 相同的值，贴图像素密度就和原版一致。
- 元素旋转只用 ±22.5°、±45° 单轴；任意角度靠实体的 `transformation`（`models.display` 的 `turns`、`models.between`）。
- item_display 没有碰撞，也不发光。灯下面另放了看不见的 `light` 方块；做成正式地图时要给大件补屏障方块。
- 模型取实体所在格的亮度。锚点落在实心方块里会变黑，所以贴墙的模型要让锚点留在空气格里，或者用 `brightness` 指定。

## 进度（交接用）

- v6 已完成并推送：望远镜（镜筒和叉式支架）、浑天仪、路灯、路牌、招牌、风向标、风向袋、彩旗、货箱和行李箱、飞艇的缆绳、发动机和舵轮、池边的香蒲。穹顶内部已经打通成一个房间。
- v6 的图还没有发给用户。上一次发给用户的是 v5 的五张图和对比结论。
- 还没做的：室内陈设（穹顶观测室是最合适的第一间，其余室内全空）、天空和光照仍是原版、规模小。对比结论里“自定义模型和贴图”这一项现在有了样品，但只有我一个评审，没有盲测。
- 本机状态（不在仓库里，换了机器就要重建）：`/agent/realms-study/` 下有服务端 `server26/`（世界 `art`）、客户端 `client26/`、截图 `shots/`、Python 虚拟环境 `.venv/`。

## 约定

第三方地图的文件和截图不放进仓库。RCON 密码、`server.properties` 不放进仓库。
