# materials/respack-redirect

## 目标
方案 6.3 的底座：重定向工具 `redirect_block()`、材质类别的共用工具（画图、重定向、声音、总检查）、占位材质、对比样板。所有其它材质卡都站在它上面。

## 约束
- **只换方块状态文件**：一个被占用的方块，只重写 `assets/minecraft/blockstates/<方块>.json`，让它指向 `assets/c164/models/block/<方块>/` 下的模型副本，副本用 `assets/c164/textures/block/` 下自己的图。原版的模型和贴图一个都不替换，所以和它共用文件的方块（`waxed_oxidized_*` 铜绿、未上蜡的 exposed 铜、整个砂岩家族之间）不会被连带改掉。
- **模型拍平**：副本不带 `parent`，把原版的继承链折进一个独立模型里，按“面”指定图（`up`/`down`/`north`…，或 `side`、`end`、`*`）。这样原版同一张图可以按面换成不同的图（细琢石的踏面和立面要分开，c190 预评第 1 条）。面的名字是模型自己的方向，方块状态里的旋转之后才是世界方向（釉陶：模型的 `south` 面就是 `facing` 那一面）。
- **原样保留**：每个状态键、multipart 的 `when`、`x`/`y`/`uvlock`、权重；26.x 的贴图对象（`force_translucent`）、元素的 `rotation`、`light_emission`、`shade_direction_override`、`display`。
- **变体**：图写成 `<名>0..k-1` 就是 k 个变体，每个状态的每个模型都出 k 份（楼梯 40 个状态 × 4 变体都带上）。
- **严格**：有一个面没说用哪张图、图不存在、图不是 16 的整数倍见方、有色板外的颜色、方块不在占用表的重画名单里、写到了自己那一块之外，都直接报错，不出包。
- 色板 `common.palette`，占用表 `common.blocks`。游戏 jar 只读：`MC_JAR`，否则 `<MC_ROOT>/client26/versions/26.3/26.3.jar`（管理员电脑上 `bin\job.py` 会设好）。

## 交付物
公共工具（单独提交 `38db8e2`、`05cf443`，请 S2 先合）：
- `build/artkit/respack.py`
  - `redirect_block(pack_dir, assets, block, textures, *, variants=None, weights=None, ns="c164", emit=0, shade=True, ao=None, edit=None, keep=(), protect=("waxed_*",))`
    - `assets`：只读 jar 的 `Assets`。`textures`：`{原版贴图引用: 图名 | {面: 图名} | None(保留原版)}`。
    - `emit`：整数或 `函数(模型引用)`，写进每个元素的 `light_emission`。`shade=False`：不按朝向打阴影（写 `shade_direction_override: "up"`；26.x 没有 `"shade": false`）。`ao=False`：不要角落变暗。
    - `edit(引用, 拍平的模型)`：映射之前改模型的钩子（去掉釉陶面上的 `rotation` 之类）。
    - 返回 `{"block","variants","models","files","pictures"}`；自查：只写了这个方块的状态文件和它自己的模型文件夹，路径里没有 `protect` 里的名字，状态和旋转一个不少。
  - `flat_model(assets, ref)`、`state_models(state)`、`block_pictures(assets, block)`：读原版模型用的小工具。

材质类别（`build/scenes/obs/materials/`）：
- `_kit.py`：别的材质包都用它，不直接碰 `redirect_block`。
  - `paint(pack_dir, 名, 图或图的列表, meta=None)`：存图，查尺寸和色板。
  - `redirect(pack_dir, 方块, textures, **kw)`：查占用表后调 `redirect_block`，`protect` 自动带上铜绿和所有“照原样用”的方块。
  - `blocks(*角色)`、`vanilla_picture(引用)`、`sounds(pack_dir, 事件)`（合并写 `assets/minecraft/sounds.json`，不带音频文件）。
  - `audit(pack_dir, replaced)`：对整个包的总检查。
- `respack_redirect.py`（本卡的模块，`ORDER = 99`，排在真画的包后面）：`pack()` 先给还没人画的方块铺占位材质，再跑 `audit`。
- `_standin.py`：占位材质。占用表重画名单里**每一个**方块从第一天起就都已重定向：原版图按明暗套进该材质的色阶（形状是游戏的，颜色是色板的）；亮窗是不透明的发光窗格；16 种仪表盘先是同一只表盘。图名一律 `ph_` 开头。一个包真画了某族，就在模块里写 `BLOCKS = K.blocks(B.XXX, ...)`，那一族自动退出占位。**成品里不许剩 `ph_`**（`_standin.left()` 列出还剩哪些）。云海的五个方块（`B.CLOUD`）也有占位：平色、不打面阴影、不要角落变暗；它们将来由 sky/cloudsea 画（总监 #15512 的明文例外），所以 `BLOCKS` 在 `materials` 和 `sky` 两个类别的模块里都认。
- `_board.py`：样板的零件（地台、成对摆放、各种形状的摆法），各材质卡的测试场景都用它拼。
- 测试场景 `build/scenes/obs_mat_redirect/`：每个被占用的铜方块旁边摆上和它共用文件的原版方块（铸铁 ↔ 上蜡铜绿，旧铜 ↔ 未上蜡 exposed 铜），各种形状都有；后面是全部重画角色的目录（四种石、六种窗、十六种仪表盘、黄铜族、小件、云海五色）。`python -m scenes.obs_mat_redirect` 按布局重写 `shots.json`。

## 验收
- `redirect_block` 对楼梯（40 个状态 × 4 变体）、台阶（双层态）、墙和玻璃板（multipart）、门（8 个模型 32 个状态）、灯（亮灭两套发光）、釉陶（`edit`）都跑通；被保护的方块、漏说的面、不存在的图都会报错。
- `tools/check.py --scene obs_mat_redirect`：全过。`blocks` 一项有 12 个警告是有意的——样板上那些“应保持原状”的同胞（`waxed_oxidized_copper_grate` 等）本来就不在占用表里，只在这块样板上出现。
- 并排图：被占用块变样、同胞铜绿不变（`plates_a`、`plates_b`、`shapes_a`、`shapes_b`、`plates_treads`）。
- 亮窗朝西的面和朝南的面一样亮（`windows_side`）。

## 版本
1 版。

## 依赖
- 依赖：`common/palette`、`common/blocks`、`common/assembly`（已就位）。
- 被依赖：ashlar、windows、iron、panels、brass-oldcopper-small 全部；别的类别从今天起就能用全部重画角色出图（先是占位色）。

## 已知的边界（写给用这些方块的人）
- 重定向只改“摆在世界里的方块”。物品栏图标、`item_display` 里的这个方块仍是原版样子；要在展示实体里用重画的方块，用 `block_display`。
- 发光只是画面上亮（`light_emission`），不照亮周围；真的照明归 sky/lights。
- 告示牌在 26.3 里是普通方块模型，重定向和别的方块一样；牌上的字是游戏另画的，不受影响。

## 记录
- c176 领（群 g2）。默认做法：拍平模型、按面映射；先把整张占用表都重定向成占位色，再一族一族真画。
- 相对最初的卡：工具签名改了（多了 `assets`、按面的 `textures`、`emit`/`shade`/`ao`/`edit`）；没有 `materials/redirect.py`，公共工具直接进 `artkit/respack.py`；`materials/__init__.py` 是 S2 的固定样板，不由本卡写；`sounds.py` 并进 `_kit.sounds()`。
- c177（#14980）：亮窗要贴图原色 → `emit=15` + `shade=False` + `ao=False`，占位亮窗已这样做。
- c190（预评）：细琢石踏面分图 → 工具按面映射；其余四条写进各自的卡。
- 云的五色（c188 #15389、c177 #15451、总监 #15512）：归 sky/cloudsea 画，这里只给占位。
- 自查图（离线图，A 版光）：`a1-<提交>-plates_a/plates_b/shapes_a/shapes_b/stone/windows_a/windows_b/windows_side/panels/panels_side/brass_a/brass_b/clouds_a/clouds_b/plates_treads/stone_treads.jpg`。
