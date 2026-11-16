# sky/safe-look 天换载体：资源包着色器

## 目标
Realms 不收带实验性设置的地图，数据包里有一个注册表文件（群系、时间线）就算。成品的数据包不带注册表文件：原版群系、钟和天气锁住，天的样子改由资源包里的核心着色器画。`sky/mood.py` 的 `LOOKS` 仍是唯一写数的地方，着色器由它生成（总监 11-16 #64150、#65771、#68450、#68701）。

## 约束
- 着色器只有这一套，别人不加（总监 #65771）。别的 sky 包要往天上画东西，走 `sky/_shaders.py` 的 `shader_layer(look)` 接口（远山：comet）。
- 数只写在 `sky/mood.py`：`LOOKS`（天顶、地平线、余晖、天光、环境光、星、海色）、`LAMP`、雾的两条律（`fog_depth()`、`levelled()`）、`LOCK_TICK`。着色器和离线出图用同一条。
- 雾在海面上、山顶在雾上面（总监 #68701）：V12 上楼的雾不超过两成半，V1 正立面不超过一成；海面和地平线以下看不出盘边；人能走到的地方望出去，160 格的渲染边上不许看见方块突然没有。
- Realms 的服务端视距是 10（160 格）。短律 60 到 150 格（按图上的水平距离），只管贴着海面的东西（离海面 8 格内全收，8 到 12 格渐无）。
- 游戏的文件从客户端 jar 里读出来改几处，补丁对不上就报错（换了游戏版本会在生成时发现，不会画错）。整个重写的只有 `sky.vsh`、`sky.fsh`、`stars.vsh`、`stars.fsh` 和 `include/fog.glsl`。
- 钟锁在 `mood.LOCK_TICK`（20370）：原版月亮这时在正西 48 度高，彗星占月亮位；星场由着色器从原版这一刻的转角转到 `STAR_ANGLE`。

## 交付物
- `build/scenes/obs/sky/_shaders.py`：`files(look)`、`pack(pack_dir)`（往资源包写 10 个文件）、`Twin(look)`（同一套算式的 numpy 版，离线出图和检查用）。下划线开头：各场景的包里不自动带，成品包由导出脚本加（`_shaders.pack(pack_dir)`）；开发用的场景还带注册表的天，整体切换另做（见记录）。
- `build/scenes/obs/sky/mood.py`：加 `AIR`、`MIST`、`MIST_HEIGHT`、`LEVEL_FULL`、`LEVEL_NONE`、`fog_depth()`、`levelled()`、`LOCK_TICK`、`GAME_STAR_ANGLE`；`FOG_START, FOG_END` 改成 60、150。
- 样板场景 `build/scenes/obs_sky_safe/`：整座 obs，不带群系和时间线，群系填 `minecraft:the_void`，资源包加着色器；镜头是看板的 V1、V2、V4、V12 和两张看海的。
- 检查 `plan/parts/figs/sky_shaders.py`（补丁、算式、用游戏自己的 shaderc 编译每一条管线的两段着色器、阶段之间的接口）和 `sky_shaderc.py`（从 Mojang 取游戏自己的 shaderc，照游戏的参数调）。
- 发现记在 `plan/parts/sky-notes.md` 第 11 节。

## 验收
- 真机（s1）：样板场景的 V1、V2、V4、V12 和看板上现在的并排；着色器全部编译通过，资源包没被退回。
- V12 上楼清楚，海没有盘边；V1 正立面的雾不到一成。
- `sky_shaders.py` 结尾 `result: PASS`。
- 成品包（outb 导出）的数据包里没有注册表文件，天是着色器画的。

## 版本
1 版。

## 依赖
- 依赖：`sky/look`（数）、`sky/comet`（彗星占月亮位、太阳位涂掉）、`sky/cloudsea`（方块云海，远海接它）。
- 被依赖：成品包（`common/export`）；`sky/ridges`（远山改由着色器画）；离线出图的雾（`render.py`，cloud 备补丁）。

## 记录
- c322 领（牵头）。comet（c330）管远山进着色器和彗星、星的核对，cloud（c329）管远海的数和离线图对上，a1（c324）管水色草色不靠群系。
- 11-16 第一趟真机（s1，07817cbe，Vulkan）：着色器生效，包没被退回，天、星、彗星、余晖都在，日志里没有编译报错；并排图 `cursor/c164-s1-render-f3-fd9c` 的 `renders/real/_sheets/sky-safe-07817cb.jpg`。V12 上楼清楚了；海盘有一圈硬边（那一版还没有短律）。s1 的机器上 OpenGL 后端起不来，OpenGL 下没验过。
- 雾的数和 cloud 对定：甲 `AIR` 1600、`MIST` 587、`MIST_HEIGHT` 12（从平台看海，800 格一个光学厚度，海留本色到地平线前几度）；乙（8、0.035）往西百格外化成一片粉，不用。短律按水平距离（按直线距离 V12 整片海被抹平）。
- 11-16 第二趟真机（a295e90，带短律，Vulkan，客户端视距 12、服务端 10）：`cursor/c164-s1-render-f3-fd9c` @ 14240931 的 `renders/real/obs_sky_safe/`，六张。V12 上海近处留着云的起伏，往远收平，没有盘边；朝东（下平台栏杆）、朝西（日落台）看海都没有边：人能走到的地方望出去看不见方块突然没有。cloud 在 V12 上量：方块海和背后画的远海差在 4/255 以内，海色不用改。日落台往西，台沿挡住 130 格以内的海，看到的全是收平后的远海，一片平色：远海的明暗由 cloud 加（`sky/cloudsea.py` 的 `far_glsl()`，接在 `c164_sea()`）。
- 11-16 关口 PASS（104b94b6，基 73ba97f1），cr2 合进总装 16ad2817。总装里 comet 的 `ridges.py` 带 `shader_layer()`，远山随这一单改由着色器画。
- 11-16 第三趟真机（264e7f9 = 交付的那套 + 远山层，Vulkan）：@ 421cca00，六张；和注册表版并排 `renders/real/_sheets/sky-safe-264e7f9.jpg`（@ 859bf30f）。comet 核：山脊线和表一致，彗核正西 41.4 度、是天上最亮的点，6.8 度内无星，山脚化进余晖没有线。
- 11-16 OpenGL。游戏先试 OpenGL 后端，起不来才退到 Vulkan，玩家多半走 OpenGL；那条路上着色器多过一道（SPIR-V 用 SPIRV-Cross 反编成 `#version 330` 的 GLSL，再交给驱动）。两道验证：一、离线（`sky_shaders.py`，节点上）：动到的 37 个着色器、630 个变体，用游戏自带的 SPIRV-Cross 照游戏的选项反编，得到的文本按 OpenGL 的规则再严格编一遍，全过，不要任何扩展，和原版的一样；`Fog` 这个 uniform 块只在我们的 `fog.glsl` 里声明，两个阶段对得上。二、真机（s1 让 SDL 走 EGL 建窗，Mesa 4.5 core，llvmpipe）：@ 6a3beaca 的 `renders/real-gl-egl/obs_sky_safe/`，V1、V12 和 Vulkan 的一样，日志 0 条报错。没验到的：英伟达、AMD、英特尔、苹果的驱动。成品旁边留一个不带着色器的包（outb 的 `-plain`）作退路。
- 成品：outb 的导出在 `--look off` 时资源包写完后调 `_shaders.pack()`（10 个文件），数据包注册表文件 0 个，钟 20370。
- 整体切换的做法（和 s2 对）：不改场景。90 个场景的 `mood.py` 都转出这里的 `BIOMES`，63 个写 `BIOME = "obs_blue"`。`artkit.mood` 加 `Carried`（带 `game_biome`、`clock`、`pack`），`sky/mood.py` 的 `BIOMES` 换成它，内容不变（离线渲染照旧从它算天色，shots.json 的 14000 照旧表示蓝调）；驱动见到它：不写注册表文件、群系填 `minecraft:the_void`、钟停在 20370、场景的包写完后加着色器，`shoot.py --clock` 一律拍这一刻。两个补丁（`safe-look-drivers.patch` 给 s2，`safe-look-flip.patch` 是 `sky/mood.py` 那一处）先在节点上合起来跑 checkall；驱动进了总装，翻转作为本卡的跟进交付，补丁文件和样板场景随后撤。
- 没做完、接着做的：开发用的 obs 和各测试场景整体切到着色器（要动 `obs/__init__.py` 的 `BIOME`、`render.py` 的离线雾、看板和真机的拍照时刻锁 20370，驱动是 s2 的，和 cloud 备好补丁再交）；`check.py` 第 260 行不认原版群系名（已请 s2 改成和 `place.py` 一样，样板场景的 `mood.py` 里先垫了一下）；远海加明暗（cloud）；deep、glow 两版各是一套着色器包，没生成。
