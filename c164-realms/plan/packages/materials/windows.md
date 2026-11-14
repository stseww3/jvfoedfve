# materials/windows

## 目标
方案 6.2 亮窗/暗窗 + 6.3 发光：六种窗（亮三、暗三），块+板两形状，窗棂在贴图里画。

## 约束
- 角色 `B.WINDOW_LIT`(黄)、`B.WINDOW_CURTAIN`(橙)、`B.WINDOW_FROSTED`(白) = 亮窗；`B.WINDOW_DARK`(灰)、`B.WINDOW_BLIND`(黑)、`B.SKYLIGHT`(浅灰) = 暗窗/天窗。各含 `.block`(整块玻璃) 与 `.pane`(玻璃板)。
- 亮窗：`glow`/`opal`（白=`opal`）。**显示贴图原色**（c177 #14980：主立面朝东，东西面的面阴影是 0.6，发光 10 级时黄玻璃只剩灰度 0.39）：`emit=15`、`shade=False`（写 `shade_direction_override: "up"`）、`ao=False`；明暗变化全画在贴图里。贴图不透明（透明度 255），保留 `force_translucent`；看不见窗后的房间，窗后第一格留给 A2 的隐形光源。
- 亮窗的颜色纪律（c190 预评第 4 条）：亮窗始终是灯丝琥珀色，磨砂是暖白；亮度和 A2 的墙面亮度对齐（由 A2 给墙面在 A 版下的显示色，窗的最亮色不超过它的 3 倍明度）；立面上约 20% 的窗是暗窗（怎么分布归 main，样板上按这个比例摆一面）。
- 暗窗：`night_glass`，不发光，映天色斜向冷反光。透不透（能不能看进屋里）要和 A0、A2、interiors 定：默认外立面的暗窗不透明（看不见没做的房间），室内看得出去的窗用 `SKYLIGHT`（半透明）。
- 窗棂：贴图内 8px 一格、1px `colour("iron",1)`，四边无缝拼成网；3 格宽拱窗横显 6 列。
- 玻璃板：重定向 post/side/side_alt/noside/noside_alt 五模型；面贴图=`*_stained_glass`、边贴图=`*_stained_glass_pane_top`。
- A6 模型窗框只做铁件（拱头/外框/中横档），压在窗棂线（8px 一格）上，不另起网格；铁件和窗棂同色阶，都走 `common.palette`（c179 #14821 已确认；materials ↔ props 互为交叉看）。
- `strays()` 每张过。

## 交付物
- `build/scenes/obs/materials/windows.py`：贴图 + `_kit.paint()` / `_kit.redirect(..., emit=15, shade=False, ao=False)`；`BLOCKS = K.blocks(B.WINDOW_LIT, B.WINDOW_CURTAIN, B.WINDOW_FROSTED, B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT)`。
- 测试场景 `build/scenes/obs_mat_windows/`：亮三+暗三各一面整块玻璃墙 + 一处玻璃板窗 + 一面嵌在灰白石墙里的窗列（朝东，约 20% 暗窗）；后面留位给 A2 隐形光源；`shots.json`：A/B/C 三个时刻各一张（`time` 14000/18000/12900）、朝东的面斜看（确认没有面阴影）、近看窗棂、远看亮暗分布。

## 验收
- 亮窗在东、西、南、北四个朝向显示的都是贴图原色（离线图量像素）；暗窗映天色不发光；窗棂拼成连续网格；亮区不铺满（配合 A2）。
- `tools/check.py --scene obs_mat_windows` 全过。
- 亮窗 2 版比选并排。

## 版本
亮窗 2 版（甲 暖黄为主 + 橙帘影 + 白磨砂三件套按本稿；乙 另一种窗棂密度/发光节奏/帘影处理）。暗窗 1 版。

## 依赖
- 依赖：respack-redirect；A2（隐形光源摆放、定稿光）。
- 被依赖：main（立面大拱窗）、interiors、A6（窗框模型）。

## 记录
- 2026-11-14 c195：六窗贴图 + 块/板两形状重定向；亮窗 `emit=15`/`shade=False`/`ao=False` 不透明、暗窗不透明不发光、SKYLIGHT α=128（0.5）；亮窗两版（甲 小方灯/匀玻璃/竖褶布帘，乙 高窗棂两灯一块/头部聚光/百叶）；暗窗一版（按位混四图），窗棂两版同占 60/256。测试场景 `obs_mat_windows`（甲）、`obs_mat_windows_b`（乙）。分支 HEAD db18a103。
- 2026-11-14 c205（接手）：merge 最新总装 b3430bd4（check.py 九项、`_kit` 已同步，无冲突）。
  - **亮窗三档云端复量**（Rec.601 luma = 0.299R+0.587G+0.114B，“整扇连窗棂的平均”，与 c177 口径一致：#ffc65a→0.79、#caa356→0.65），对齐 c177 g2 #90：

    | 档 | 甲 整扇 | 甲 玻璃 | 乙 整扇 | 目标（整扇） |
    | --- | --- | --- | --- | --- |
    | WINDOW_LIT | 0.650 | 0.811 | 0.642 | ~0.65（玻璃 #ffc65a 不提到 #ffe9a6） |
    | WINDOW_FROSTED | 0.542 | 0.671 | 0.547 | 0.52–0.55 ✓ |
    | WINDOW_CURTAIN | 0.396 | 0.479 | 0.414 | 0.38–0.42 ✓ |

    暗窗显示（贴图色 × c177 东面天光系数）：DARK A 0.080 / B 0.050、BLIND A 0.073 —— 对齐 #90 的 ~0.08 / ~0.05 / ~0.073。复量脚本 `python -m scenes.obs_mat_windows.brightness`（断言三档在档内，退出码 0，可随时复跑）。
  - `tools/check.py --scene obs_mat_windows` 与 `--scene obs_mat_windows_b` 合并后全过（0 警告）。
  - 离线自查图（1280×720）进 git：`renders/obs_mat_windows/`（甲 22 张）、`renders/obs_mat_windows_b/`（乙 22 张），各带 shots.txt；甲/乙比选看两个目录里同名的机位（91c372c5 起用 `tools/selfshots.py` 重出，手工拼的 `compare_ab.png` 已去掉）。自查：朝东斜看（slant/face_*）亮窗四朝向均显贴图原色、无面阴影；暗窗映天不发光、SKYLIGHT 可看进屋；窗棂拼成连续网；远看亮暗分布对（约二成暗窗、相邻不同亮）。
  - 窗后第一格已留 A2 隐形光源位（测试场景按 sky.md §6 暂摆 level 9–10 占位，不等 A2 定稿光）。
  - 【交付】点 c188（S2，合并钥匙）→ c188 回【合并】点 c164；同步群 g2。分支 `cursor/c164-m2-windows-7bb5`。
  - 结果：交付 91c372c5，合并 e09d6a7a（c188，技检过）；评审 c219 过（`plan/aesthetics/S3-reviews-v4.md` 评审 #1：质感 4、风格 4，无红线，甲 ＞ 乙，默认甲，终选在 A0/管理员）；交叉看 c206、c220 都对得上（见下一条的记账）。
- 2026-11-14 c205（评审后打磨一轮；出图线回到管理员电脑，A0 群公告 11-14 11:42、11:46）：merge 总装 e8cb4e3c。评审 #1 的三条都是过线后的打磨项（c219），这一轮做前两条：
  - **改法 1，甲 LIT 偏平**（close_lit / near_main：整扇一个调，近看像一块匀发光片）：每格底沿压一阶（`glow` 1，1px），顶沿那道更亮的暖边（`glow` 3，1px）留着，一格自淡而深，读成玻璃后面有灯。只用一阶、不加饱和、不用 `glow` 4；不做乙那种整条高光带。候选在放大的贴图上比过（只压底沿 / 底沿加角 / 顶部加一团 / 左上右下错开 / 隔格交替），只压底沿最干净。
  - **改法 2，SKYLIGHT 窗棂偏粗**（close_skylight：每块 2px 铁框，并排成 4px，比另五种窗的网重一倍）：天窗改用同一套细网（8px 一格、1px `iron` 1，跟版本走，乙是高窗棂），半透 α=128 不变，映天反光改成格内的短斜条（α=176，四图按位混，比暗窗少）。**屋顶的粗铁框不画进贴图**：只在整扇天窗的外圈，由屋面围一圈铁件做（和立面窗框归 props 是同一条规矩）。这一条取代 `plan/parts/materials.md` 第 5 节里“大铁框格 12px”的写法；细化稿那一行已照 A0 的话改成现在的做法。
  - **改法 3，暗窗映天提一阶**：不动。待真机（c219、A0 都这么定；光和天空现在归 c220），离线图的天不作数，0.08 等电脑上的真天色图再定。
  - 复量（`python -m scenes.obs_mat_windows.brightness`，退出码 0）：

    | 档 | 甲 整扇 | 甲 玻璃 | 乙 整扇 | 目标（整扇） |
    | --- | --- | --- | --- | --- |
    | WINDOW_LIT | 0.635（原 0.650） | 0.792 | 0.642 | ~0.65，档 0.62–0.67 ✓ |
    | WINDOW_FROSTED | 0.542 | 0.671 | 0.547 | 0.52–0.55 ✓ |
    | WINDOW_CURTAIN | 0.396 | 0.479 | 0.414 | 0.38–0.42 ✓ |

    暗窗没动：DARK A 0.080 / B 0.050，BLIND A 0.073。
  - `tools/check.py`：`obs_mat_windows`、`obs_mat_windows_b` 全过 0 警告；`obs` 全过（只有主楼白模的 flatwall）。
  - 图（管理员电脑出，云端不出图）：代码 dcf301da，`bin\sync.py` → `bin\job.py m2 --heavy` 跑 `render.py`，两个场景各 22 张、各约 30 秒 → `bin\send.py` 原样 PNG 回传 → 云端 `tools/selfshots.py <场景> --take --prefix m2-dcf301d-` 落位（乙的图出图时前缀带了 `_b`，先抄到临时目录改成标准前缀再 take；下次直接按 INTERFACE 第 5 节用 `selfshots.py --out`，文件名自带场景名）。甲换了 18 张（画面里有亮窗或天窗的全部），4 张和存的逐像素一样、文件没动（close_frosted、close_curtain、close_dark、close_blind）；乙换了 5 张（画面里有天窗的：slant、walls_dark、close_skylight、panes、roof），17 张没动。面板合并后过期的 walls_dark、close_skylight（甲乙各一）这次一并更新。`shots.txt` 记 dcf301da 和每张图的 SHA-256。
  - 自查（看图）：close_lit、near_main 每格上淡下深，不再是一块平片；远看（far、front 三个时刻）亮暗分布和整体颜色没变；close_skylight、roof、walls_dark、panes 里天窗和另五种窗是同一张网，屋里那排仪表看得更清；face_* 四个朝向的亮窗仍是贴图原色。
  - 交付 306d9dc7。评审复看（c219，11-14 12:10，看 close_lit、near_main、close_skylight，和旧图逐张对过）：两条都到位，维持「过」，分数不变（质感 4、风格 4），没有新问题，不用再改。记一笔、不要求改：贴脸看（close_lit）一格像一块鼓起的小砖（上亮下暗是凸面的读法），三格以外就没有了。粗铁框由屋面铁件做，这个分工评审同意。暗窗映天照旧待真机。
  - A0（11-14 12:16）：窗这张卡到此收口。留给以后的两件都不在本卡手里：暗窗映天等电脑上的真天色图再定（找 c220、c219）；甲/乙终选等管理员（A0 并排发，默认甲）。
  - 交叉看记账（都不用改本卡）：c206（11-14 11:33）——窗棂列数和立面窗洞对得上，立面全用整块；鼓座的 1×1 小圆窗会显成四小格的方窗，要圆得靠 props 的圆窗框压在外面，或者以后加一种舷窗玻璃（要占用表加角色，归 A0），等整楼的图再定。c220（11-14 11:53）——窗后光源位和 `lights.build` 自动放的是同一格；档位 3/2/1/0 对 LIT / FROSTED / CURTAIN / DARK（约三成 BLIND），窗后等级 12 / 10·9 / 8·7 / 不放。本场景手摆的 9–10 是占位，`sky/lights` 合并后换成它来放。
