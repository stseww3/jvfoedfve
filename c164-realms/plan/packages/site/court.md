# site/court 前庭铺地＋黄铜子午线

- 类别：site　优先级：**P1**（看板 V2 和入口样板段前庭要用）
- 目标：ART-PLAN §4 前庭——铺地、南北向黄铜子午线、中央台徽嵌花（浑天仪位）、前庭栏杆。缩成邮票一眼读到“浅色前庭上一个十字＋焦点圆，推向点亮的入口”。
- 约束：
  - 前庭 x 16..60、z −30..30；子午线 x=35（`MERIDIAN_X`）；台徽中心 (35,0)。铺地方块 y=−1，子午线碑面/台徽碑面 y=0。
  - 只用占用表角色：场 `TUFF_SMOOTH`；网格缝/边框/子午线镶边 `SLATE_SMOOTH`/`SLATE_BRICK`；仪典带 `ASHLAR_FINE`；子午线 `BRASS_INLAY`（`yellow_carpet`）；台徽 `ASHLAR_EMBLEM`＋黄铜嵌线；栏杆 `ASHLAR_ROUGH`＋`ASHLAR_PANEL`。开间网格对齐主楼 4 格（`BAY`）。
  - 中心一格留给浑天仪（A5），不放方块。东缘栏杆在 x=60，台阶口 z −8..7 留空（归 site/stair）。地面不加发光面（亮区留给窗/灯）。前庭进深按 skeleton 44，A0 看 V2 真机图可回退，不锁死。
  - 展示实体 0（全方块）。
- 交付物：`build/scenes/obs/site/plaza.py`（`ORDER=60`，在 ground 之后铺）；测试场景 `build/scenes/obs_site_court/`（__init__ 建 Canvas 调 site.build＋主楼 massing 作背景＋sky.build 补光；mood 复用；shots.json）。
- 验收：V2 前庭正轴（对称、十字＋焦点、引向入口）；一张近景看子午线嵌线与台徽像素；一张东侧斜看前庭对主楼。技术：`check.py` regen/strays/conflicts/blocks 过；无色板外色；铺地平铺无条纹（用 `canvas.Mix` 变体）。
- 版本：1 版。
- 依赖：骨架 `FRONT_COURT`/`MERIDIAN_X`/`GRAND_STAIR`（本稿提议值，已可用）。被依赖：A5 浑天仪位、A6 前庭路灯/栏杆铁件、c191 星厅子午线共 x=35。
- 记录：a4 领（制作中）。子午线用 `yellow_carpet` 角色，A1 重画黄铜前显示为黄；台阶口与栏杆接 site/stair。
