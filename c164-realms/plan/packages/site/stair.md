# site/stair 大台阶＋挡土墙＋下平台

- 类别：site　优先级：P2
- 目标：ART-PLAN §4、§5.3——前庭东缘正中的大台阶下到下平台；深板岩砖挡土墙带扶壁；下平台铺地。把上平台（y=0）和下平台（y=−9）接起来。
- 约束：
  - 大台阶 x=60（前庭东缘）、z −8..7（宽 16）、下 9 格到 y=−9（`GRAND_STAIR`）；两侧铸铁路灯灯位留给 A6。
  - 下平台 x 61..91、z −42..43、地面 y=−9（`LOWER_PLATFORM`，30×85）；铺地凝灰岩（`TUFF_BRICK`/`TUFF`）。
  - 挡土墙：下平台外缘与上/下平台落差处，`SLATE_BRICK` 墙带扶壁（§5.3）；栏杆灰白石。
  - 和 site/court 的东缘栏杆接：台阶口处栏杆断开、改台阶侧墙。展示实体 0。
- 交付物：`build/scenes/obs/site/stair.py`、`lowerplatform.py`（`ORDER` 20~30）；测试场景 `obs_site_stair`。
- 验收：V1（台阶居中、路灯位）、V12；层高够走人、台阶坡度顺；挡土墙无 >5×5 平墙。
- 版本：1 版。
- 依赖：court 东缘坐标；骨架 `GRAND_STAIR`/`LOWER_PLATFORM`。被依赖：缆车站/发电房（站在下平台上）、A6 台阶路灯。
- 记录：待领。
