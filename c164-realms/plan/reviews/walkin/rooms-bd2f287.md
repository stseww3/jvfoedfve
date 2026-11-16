# 室内外走查：人走得到的地方，哪些件眼睛会进到模型里（总装 bd2f2874，props 和 interiors 摆的件）

ashlar 用 `tools/walkin.py obs --category props,interiors --items --brief` 在 node96 上算的，只读画布，不改任何包。原始输出在同目录 `rooms-bd2f287.txt`（两类合排，按房间）、`props-bd2f287.txt`、`interiors-bd2f287.txt`（逐件，带屏障的份额）。

量法：站位是 walkreach 的半格点阵（从出生点走、跳 1.2 以内；「要开门」是方块门后面的）。人眼在脚上 1.62，站在一个点上时人实际可以在它四周四分之一格以内。模型的体素（八分之一格）问一句「围没围住」：本身是模型，或六个方向里有五个方向上有本件的模型（柜子肚里算，桌子底下、灯头下面、拱下面不算）；再往里缩一个体素叫芯（门扇、墙上的纸、细杆没有芯）。**眼睛进去** = 眼睛那一片（半格见方、高 0.2）有两成以上是芯。**身体** = 人的盒子（0.6×0.6×1.8）里被围住的份额，细件按整个体素算会偏大。「谁摆的」是把它放上画布的那个包（房间摆的柜子算房间的，不算画柜子的 props）。「件号」是它在本类逐件表里的号。

合计：487 件里眼睛进得去的 **23 件**，另有 71 件人能穿过去但眼睛在外面（桌、凳、灯柱、矮箱）。

| 房间 | 眼睛进得去 | 只穿身子 |
|---|---|---|
| 授时室 | 11 | 12 |
| 圆顶室 | 3 | 8 |
| 星厅回廊（脚 7） | 3 | 2 |
| 星图室 | 2 | 11 |
| 前庭和各层平台（室外） | 1 | 9 |
| 底片库和暗房 | 1 | 8 |
| 发电房 | 1 | 4 |
| 星厅（底层） | 1 | 4 |
| 索道站 | 0 | 4 |
| 下平台 | 0 | 8 |
| 坡道和坡下（室外） | 0 | 1 |

## 授时室

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 289 | `prop_furn_card_cabinet x2` | x 4..5, y 7..8, z -8..-7 | interiors/timeroom | 走 6 处，1.5 m²：x 4.5..5.5, 脚 7, z -7..-6.5 | 95% | 整格屏障放不下（最满的一格 88%） |
| interiors 293 | `prop_lamp_pendant_b` | x 6, y 9..10, z -24..-23 | interiors/timeroom | 跳 2 处，0.5 m²：x 6.5, 脚 8, z -23.5..-23 | 21% | 整格屏障放不下（最满的一格 0%） |
| interiors 304 | `prop_lamp_pendant_b` | x 9, y 9..10, z -24..-23 | interiors/timeroom | 跳 2 处，0.5 m²：x 9.5, 脚 8, z -23.5..-23 | 21% | 整格屏障放不下（最满的一格 0%） |
| interiors 317 | `int_timeroom_phone_feed, prop_elec_wall_phone` | x 13, y 7..9, z -14 | interiors/timeroom | 走 1 处，0.25 m²：x 13.5, 脚 7, z -13.5 | 26% | 整格屏障放不下（最满的一格 16%） |
| interiors 269 | `prop_inst_regulator_clock` | x 2, y 8..9, z -25 | interiors/timeroom | 走 1 处，0.25 m²：x 2.5, 脚 7, z -24.5 | 21% | 整格屏障放不下（最满的一格 0%） |
| interiors 316 | `prop_inst_regulator_clock` | x 13, y 8..9, z -25 | interiors/timeroom | 走 1 处，0.25 m²：x 13.5, 脚 7, z -24.5 | 21% | 整格屏障放不下（最满的一格 0%） |
| interiors 273 | `int_timeroom_clock_e5` | x 2, y 8..10, z -12 | interiors/timeroom | 跳 1 处，0.25 m²：x 2.5, 脚 8, z -11.5 | 20% | 整格屏障放不下（最满的一格 0%） |
| interiors 274 | `int_timeroom_clock_e2` | x 2, y 8..10, z -11 | interiors/timeroom | 跳 1 处，0.25 m²：x 2.5, 脚 8, z -10.5 | 20% | 整格屏障放不下（最满的一格 0%） |
| interiors 275 | `int_timeroom_clock_home` | x 2, y 8..10, z -10 | interiors/timeroom | 跳 1 处，0.25 m²：x 2.5, 脚 8, z -9.5 | 20% | 整格屏障放不下（最满的一格 0%） |
| interiors 276 | `int_timeroom_clock_w3` | x 2, y 8..10, z -9 | interiors/timeroom | 跳 1 处，0.25 m²：x 2.5, 脚 8, z -8.5 | 20% | 整格屏障放不下（最满的一格 0%） |
| interiors 277 | `int_timeroom_clock_w5` | x 2, y 8..10, z -8 | interiors/timeroom | 跳 1 处，0.25 m²：x 2.5, 脚 8, z -7.5 | 20% | 整格屏障放不下（最满的一格 0%） |

只穿身子、眼睛在外面的：`mach_rec_drum`（timeroom，x 8..9, y 8, z -24，跳 1 处，身体 34%）；`mach_rec_tape, mach_rec_telegraph`（timeroom，x 6, y 7..8, z -24..-23，跳 4 处，身体 33%）；`mach_rec_drum_frame`（timeroom，x 8..9, y 8, z -24，跳 4 处，身体 27%）；`int_timeroom_jacket, prop_furn_swivel_chair`（timeroom，x 11..12, y 7, z -12，走 2 处，身体 27%）；`prop_furn_writing_desk`（timeroom，x 2..3, y 7, z -17..-15，走 8 处，身体 24%）；`prop_furn_writing_desk`（timeroom，x 12..13, y 7, z -13..-11，走 8 处，身体 24%）；`prop_furn_coat_stand`（timeroom，x 10, y 7..8, z -7，走 1 处，身体 23%）；`prop_furn_stool`（timeroom，x 7, y 7, z -23，走 1 处，身体 19%）；`prop_furn_swivel_chair`（timeroom，x 3..4, y 7, z -16，走 2 处，身体 17%）；`int_timeroom_chronometer x2`（timeroom，x 2, y 7..8, z -16..-15，走 1 处，身体 12%）；`mach_rec_tube`（timeroom，x 13, y 8..10, z -10，走 1 处，身体 12%）；`prop_elec_telegraph_key`（timeroom，x 7, y 8, z -24，跳 1 处，身体 8%）。

## 圆顶室

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 74 | `prop_furn_card_cabinet` | x 4, y 18..19, z -10 | interiors/domeroom | 走 4 处，1 m²：x 4..5, 脚 18, z -9.5..-9 | 93% | 整格屏障放不下（最满的一格 84%） |
| interiors 72 | `prop_furn_instrument_cabinet` | x 3, y 18..19, z -10 | interiors/domeroom | 走 2 处，0.5 m²：x 3.5..4, 脚 18, z -9.5 | 93% | 整格屏障放不下（最满的一格 78%） |
| interiors 77 | `prop_furn_instrument_cabinet` | x 5, y 18..19, z -10 | interiors/domeroom | 走 2 处，0.5 m²：x 5..5.5, 脚 18, z -9.5 | 93% | 整格屏障放不下（最满的一格 78%） |

只穿身子、眼睛在外面的：`prop_furn_plate_box x3`（domeroom，x 7..8, y 18..19, z 8..9，走 3 处，身体 71%）；`prop_furn_coat_stand`（domeroom，x 10, y 18..19, z -7，走 1 处，身体 30%）；`prop_furn_drafting_table`（domeroom，x 6..8, y 18..19, z -9，走 8 处，身体 27%）；`int_domeroom_chair`（domeroom，x -3, y 18..20, z 4..6，走 5 处，身体 23%）；`prop_furn_writing_desk`（domeroom，x 1..3, y 18, z 6，走 11 处，身体 21%）；`prop_furn_swivel_chair`（domeroom，x 2, y 18, z 7，走 1 处，身体 21%）；`prop_furn_stool`（domeroom，x 13, y 18, z 1，走 1 处，身体 19%）；`prop_paper_logbook`（domeroom，x 2..3, y 18, z 6，走 1 处，身体 7%）。

## 星厅回廊（脚 7）

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 213 | `prop_furn_card_cabinet x2` | x 2..3, y 7..8, z 5 | interiors/starhall | 走 5 处，1.25 m²：x 2..4, 脚 7, z 5.5 | 95% | 整格屏障放不下（最满的一格 88%） |
| interiors 220 | `prop_furn_instrument_cabinet` | x 4, y 7..8, z 5 | interiors/starhall | 走 3 处，0.75 m²：x 4..5, 脚 7, z 5.5 | 93% | 整格屏障放不下（最满的一格 88%） |
| interiors 260 | `prop_furn_instrument_cabinet` | x 13, y 7..8, z -5 | interiors/starhall | 走 3 处，0.75 m²：x 13..14, 脚 7, z -4.5 | 93% | 整格屏障放不下（最满的一格 88%） |

只穿身子、眼睛在外面的：`prop_furn_display_case`（starhall，x 5, y 7..8, z 5，走 4 处，身体 71%）；`prop_paper_logbook`（starhall，x 5, y 7, z 5，走 1 处，身体 14%）。

## 星图室

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 5 | `prop_furn_card_cabinet x3` | x 2..3, y 7..8, z 8..10 | interiors/chartroom | 走 10 处，2.5 m²：x 2.5..3, 脚 7, z 8.5..10.5 | 94% | 整格屏障放不下（最满的一格 88%） |
| interiors 12 | `prop_inst_celestial_globe` | x 2..4, y 7..8, z 19..21 | interiors/chartroom | 走 2 处，0.5 m²：x 3.5..4, 脚 7, z 20.5 | 80% | 整格屏障放不下（最满的一格 88%） |

只穿身子、眼睛在外面的：`int_chart_viewer`（chartroom，x 6..9, y 7..9, z 16..17，跳 7 处，身体 57%）；`prop_furn_trunk`（chartroom，x 12..13, y 7, z 22..24，走 3 处，身体 43%）；`prop_inst_tripod_scope_comet`（chartroom，x 11..13, y 6..9, z 15..17，走 2 处，身体 27%）；`prop_inst_calc_machine`（chartroom，x 13, y 7..8, z 12..13，走 2 处，身体 27%）；`prop_furn_coat_stand`（chartroom，x 12..13, y 7..8, z 7..8，走 1 处，身体 24%）；`prop_furn_writing_desk`（chartroom，x 12..13, y 7, z 11..13，走 8 处，身体 24%）；`prop_furn_drafting_table`（chartroom，x 2..3, y 7..8, z 15..17，走 6 处，身体 23%）；`int_chart_bridge`（chartroom，x 6..9, y 7..8, z 13，跳 4 处，身体 21%）；`prop_furn_swivel_chair`（chartroom，x 11..12, y 7, z 11..12，走 1 处，身体 18%）；`prop_furn_bench`（chartroom，x 12..13, y 6..8, z 19..21，走 3 处，身体 16%）；`prop_paper_blackboard`（chartroom，x 2, y 8..9, z 11..13，走 2 处，身体 13%）。

## 前庭和各层平台（室外）

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| props 10 | `prop_inst_tripod_scope_comet` | x -26..-24, y -1..2, z -1..1 | props/instruments | 走 1 处，0.25 m²：x -24.5, 脚 0, z 0.5 | 40% | 整格屏障放不下（最满的一格 20%） |

只穿身子、眼睛在外面的：`prop_lamp_street`（lamps，x 26, y 0..5, z -6，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 26, y 0..5, z 6，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 44, y 0..5, z -6，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 44, y 0..5, z 6，走 1 处，身体 61%）；`prop_pipe_valve_angle_l`（pipes，x 18..19, y -1..0, z 33，走 2 处，身体 42%）；`prop_furn_bench`（furniture，x -24..-23, y -1..1, z -4..-3，走 3 处，身体 9%）；`prop_furn_bench`（furniture，x -24..-23, y -1..1, z 3..4，走 3 处，身体 9%）；`prop_furn_bench`（furniture，x -22, y -1..1, z -8..-7，走 3 处，身体 9%）；`prop_furn_bench`（furniture，x -22, y -1..1, z 7..8，走 3 处，身体 9%）。

## 底片库和暗房

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 132 | `int_vault_dark_safelight` | x 7, y 2..3, z 25 | interiors/platevault | 跳 1 处，0.25 m²：x 7.5, 脚 1, z 25.5 | 32% | 整格屏障放不下（最满的一格 0%） |

只穿身子、眼睛在外面的：`int_vault_dark_rack x2`（platevault，x 3..5, y 0..1, z 25，跳 5 处，身体 38%）；`prop_furn_crate`（platevault，x 11..12, y 0, z 7..8，走 2 处，身体 32%）；`int_vault_checker`（platevault，x 9..11, y 0, z 7..8，走 4 处，身体 23%）；`prop_furn_writing_desk`（platevault，x 3..5, y 0, z 7，走 8 处，身体 21%）；`prop_furn_crate_small`（platevault，x 11..12, y 0..1, z 7，走 1 处，身体 21%）；`int_vault_dark_shelf`（platevault，x 10..11, y 1..2, z 25，跳 3 处，身体 17%）；`prop_furn_stool`（platevault，x 4, y 0, z 8，走 1 处，身体 15%）；`prop_lamp_desk_green`（platevault，x 4..5, y 0..1, z 7，走 1 处，身体 14%）。

## 发电房

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 202 | `prop_pipe_valve_l` | x 85, y -3..-2, z 35..36 | interiors/powerhouse | 跳 1 处，0.25 m²：x 85.5, 脚 -4, z 36 | 12% | 整格屏障放不下（最满的一格 0%） |

只穿身子、眼睛在外面的：`int_power_coal`（powerhouse，x 76..78, y -7..-5, z 21..23，走 6 处，身体 44%）；`prop_furn_swivel_chair`（powerhouse，x 70, y -6, z 22..23，走 1 处，身体 22%）；`prop_furn_writing_desk`（powerhouse，x 69, y -6, z 22..23，走 4 处，身体 20%）；`prop_pipe_flange_l`（powerhouse，x 85, y -4, z 35..36，跳 1 处，身体 13%）。

## 星厅（底层）

| 件号 | 件名 | 占的格 | 谁摆的 | 眼睛进去的站位 | 身体 | 屏障 |
|---|---|---|---|---|---|---|
| interiors 219 | `prop_inst_celestial_globe` | x 3..5, y 0..1, z 3..5 | interiors/starhall | 走 2 处，0.5 m²：x 4.5, 脚 0, z 4.5..5 | 79% | 整格屏障放不下（最满的一格 77%） |

只穿身子、眼睛在外面的：`prop_furn_display_table_plates`（starhall，x 9..10, y 0..1, z -5..-4，走 6 处，身体 33%）；`prop_furn_display_table_lenses`（starhall，x 12..13, y 0..1, z -5..-4，走 6 处，身体 32%）；`prop_furn_bench`（starhall，x 9..10, y -1..1, z 4..5，走 3 处，身体 15%）；`prop_furn_bench`（starhall，x 12..13, y -1..1, z 4..5，走 3 处，身体 15%）。

## 索道站

只穿身子、眼睛在外面的：`prop_furn_trunk`（furniture，x 84..85, y -4, z -36，走 3 处，身体 43%）；`prop_furn_crate_small`（furniture，x 84..85, y -4..-3, z -36，走 1 处，身体 26%）；`prop_furn_bench`（furniture，x 79, y -5..-3, z -39..-38，走 3 处，身体 9%）；`prop_furn_bench`（furniture，x 80..82, y -5..-3, z -36，走 3 处，身体 9%）。

## 下平台

只穿身子、眼睛在外面的：`prop_lamp_street`（lamps，x 72..73, y -3..2, z -10..-9，跳 1 处，身体 61%）；`prop_lamp_street`（lamps，x 72..73, y -3..2, z 9..10，跳 1 处，身体 61%）；`prop_lamp_street`（lamps，x 79, y -6..-1, z -10，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 79, y -6..-1, z 10，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 80, y -6..-1, z -18，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 86, y -6..-1, z -18，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 87, y -6..-1, z -10，走 1 处，身体 61%）；`prop_lamp_street`（lamps，x 87, y -6..-1, z 10，走 1 处，身体 61%）。

## 坡道和坡下（室外）

只穿身子、眼睛在外面的：`prop_furn_bench`（furniture，x 49, y -6..-4, z 50..51，走 3 处，身体 14%）。

## 不在这两类模型里的屏障

场景里不落在 props、interiors 摆的模型里的屏障： 137 格：1 格在 x -1, y 18, z -9; 6 格在 x 16, y 0..1, z -5..-3; 6 格在 x 16, y 0..1, z 3..5; 2 格在 x 33, y 0..1, z -30; 2 格在 x 37, y 0..1, z -30; 14 格在 x 70, y -5..-4, z 26..32; 8 格在 x 71..72, y -6..-5, z 37..38; 2 格在 x 77, y -6..-5, z 37; 30 格在 x 79..83, y -5..-4, z 23..25; 30 格在 x 79..83, y -5..-4, z 27..29; 24 格在 x 80..85, y -6..-5, z 34..35; 12 格在 x 90..91, y -4..-3, z -34..-32

（其中 machines 的 125 格见 `machines-be109b7.md`；(16, 0..1, ±3..5) 那 12 格在正门两侧的铁栅门里，是 main 摆的门扇。）
