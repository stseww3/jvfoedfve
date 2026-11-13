# c164：Realms Mapmaker 披风地图项目

Telegram 聊天 c164 的工作目录。目标：做出能通过 Java Realms 内容创作者计划审核的原创地图。目前在做的是美术测试：不管玩法，只看 agent 用代码能把画面做到什么程度。

## 目录

- `study/published-maps-study.md`：四张已上线 Realms 的地图的拆解结论（规模、共同做法、审核改动、26.x 格式）。
- `study/art-comparison.md`：样品和这四张图的美术对比，以及这个对比的限制。
- `study/raw/`：分析脚本的原始输出。
- `tools/survey.py`、`tools/census.py`：只读的存档分析脚本。
- `tools/fetch_client.py`、`tools/run_client.sh`：下载官方 26.3 客户端，在 Xvfb + Mesa 软件渲染下离线启动，只连本机测试服。
- `tools/rcon.py`、`tools/shoot.py`：通过 RCON 移动镜头玩家并截图。
- `tools/mcbot.py`、`verify/`：用假玩家检查数据包逻辑的脚本和 26.3 服务端验证记录。
- `build/artkit/`：体素画布、方块表、噪声、树和建筑零件、结构模板导出。
- `build/scenes/skyobs/`：样品场景“浮空岛天文台”（地形、塔、小屋、场地、植被、镜头表）。
- `build/place.py`：生成场景，导出成数据包里的结构模板，通过 RCON 摆进测试服的世界。
- `renders/`：样品的出图（软件渲染，1280×720）。

## 出图循环

需要一个本机 26.3 服务端（开 RCON，离线模式，虚空世界）和 `run_client.sh` 启动的镜头客户端。

```
cd build
python place.py skyobs --world <服务端目录>/<世界> --pw-file <服务端目录>/.rcon_pw --at 0 200 0
python ../tools/shoot.py scenes/skyobs/shots.json --pw-file <服务端目录>/.rcon_pw \
    --out <输出目录> --origin 0 200 0 --settle 10 --first-settle 16
```

约 15 万方块的场景：生成 3 秒，摆放 3 秒，每个镜头约 10 秒。

## 约定

第三方地图的文件和截图不放进仓库。RCON 密码、`server.properties` 不放进仓库。
