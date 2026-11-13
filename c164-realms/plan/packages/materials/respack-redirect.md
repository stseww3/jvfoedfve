# materials/respack-redirect

## 目标
方案 6.3 的底座：重定向工具 `redirect_block()` + 材质资源包组装入口 + `sounds.json` 脚手架。所有其它材质卡都依赖它。

## 约束
- `redirect_block(pack_dir, block, tex_map, *, variants=1, ns="c164", assets=None)`：
  - 用 `artkit.gameassets.Assets`（读 26.3 jar）读 `blockstates/<block>.json` 及其引用的全部 model（含 parent 链、所有纹理键）。
  - `tex_map`：{vanilla 贴图引用 → c164 贴图基名}。对引用到这些贴图的每个 model 生成 `c164:` 副本（保留 parent 与未命中的纹理键），命中的键改指 `c164:` 新图。
  - `variants=N`：每个 model 出 N 份副本（后缀 `__v0..vN-1`，贴图名用 `f"{基名}{v}"`，N=1 无后缀）；blockstate 每个状态键的 apply 改成 N 份副本的加权表（楼梯/台阶/墙/门/灯的所有状态都带变体）。
  - 重写 `blockstates/<block>.json`：逐状态把 `model` 换成 `c164:` 副本，原样保留 `facing/half/shape/type/axis/lit/powered/hinge/open`、`x/y/uvlock/weight` 与 multipart 的 `when`。
  - 自查断言：只写 `assets/minecraft/blockstates/<block>.json` 和 `assets/<ns>/...` 下文件；绝不写 vanilla 贴图/模型，绝不写 `waxed_oxidized_*`、`waxed_weathered_*` 的任何文件。返回写出的文件清单。
- 公共工具：`redirect_block` 加进 `build/artkit/respack.py`（公共，R1 批准优先合并）；先在 `build/scenes/obs/materials/redirect.py` 放等价实现，合并后切换。
- 色板 `common.palette`，占用表 `common.blocks`。只读 jar：`/agent/realms-study/client26/versions/26.3/26.3.jar`。

## 交付物
- `build/scenes/obs/materials/__init__.py`：`write_pack(pack_dir)`，被总场景 `obs` 调；逐卡调各自 `write_pack`。
- `build/scenes/obs/materials/redirect.py`：`redirect_block` 本地实现 + 自查。
- `build/scenes/obs/materials/sounds.py`：写 `sounds.json`（做法 E，brass 脚步改金属）脚手架（brass 卡填内容）。
- （单独提交）`build/artkit/respack.py` 增 `redirect_block`，群里点 c188 优先合并。
- 测试场景 `build/scenes/obs_mat_redirect/`：放一对"被占用块 + 应保持原状的同胞"（如 IRON_RIVETED 楼梯 ↔ waxed_oxidized_cut_copper 楼梯），`shots.json` 近看分家。

## 验收
- `redirect_block` 对一个多状态块（楼梯）跑通：所有 facing/half/shape 都指到 c164 副本、变体生效。
- 自查断言通过：没写任何 vanilla/`waxed_oxidized_*`/`waxed_weathered_*` 文件。
- 并排图：被占用块变样、同胞铜绿不变。

## 版本
1 版。

## 依赖
- 依赖：`common/palette`、`common/blocks`（已就位）；`common/skeleton`（没出来前用 R1 §0.3 常量）。
- 被依赖：ashlar、windows、iron、panels、brass-oldcopper-small 全部。

## 记录
- （领卡后填：谁领、默认做法、每次退回怎么改）
