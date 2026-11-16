# 路上的光：暗格清单（总装 cda721ae）

量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。地面低于 5、台阶（脚下是 `_stairs`、`_slab`）和门槛（`facade.doors()`、`shell.doors()`、`S.DOME_ROOM_DOORS` 的格）低于 7 算暗。露天的（头上没有块）和穹顶室不算，另列。坐标是格子的整数坐标，y 是脚所在的那一行。

- 站得住的格：36644（走得到 8260，要跳一下 28384），其中屋顶下 1996。只能掉下去才到的地方不算（5022 个落脚点）。
- **暗：856 格，94 堆**（地面 749，台阶 89，门槛 18）。
- 露天不算暗：33200 格。穹顶室不算：296 格。sky/lights 现在放了 171 个光源。

每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、最近的 sky/lights 光源（走格数、级、它的说明）。

## room: stair hall：暗 117 格，5 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -5..1 | 7..8 | -5..5 | 45 | 0 | 44/1/0 | 3 格外，7 级，props/lamps:cage_a @ (-6, 9, -2) |
| -7..1 | 0 | -1..1 | 27 | 0 | 27/0/0 | 6 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | -5..-3 | 22 | 0 | 1/21/0 | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | 3..5 | 22 | 0 | 1/21/0 | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, 4) |
| 1 | 11 | 3 | 1 | 1 | 0/1/0 | 7 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |

## out-E the west side: the water tower, the sunset terrace：暗 92 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -20..-14 | -2 | -34..-28 | 38 | 0 | 38/0/0 | 3 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -9..-2 | 0 | 9..28 | 27 | 0 | 27/0/0 | 9 格外，9 级，props/lamps:pendant_b @ (4, 4, 14) |
| -8..-2 | 0 | -29..-10 | 26 | 0 | 26/0/0 | 10 格外，10 级，sky/lights:window west 3 main @ (0, 9, -24) |
| -9 | 0 | -9 | 1 | 0 | 1/0/0 | 17 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |

## in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome：暗 89 格，8 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 8..16 | 17..18 | 26..34 | 29 | 0 | 22/7/0 | 4 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 8..15 | 17..20 | 8..15 | 23 | 0 | 18/4/1 | 1 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 10..14 | 18 | 28..32 | 19 | 0 | 19/0/0 | 7 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 3..6 | 18..20 | 14..15 | 6 | 0 | 3/3/0 | 2 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 11..13 | 20 | 27 | 3 | 0 | 3/0/0 | 6 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 11..13 | 20 | 33 | 3 | 0 | 3/0/0 | 11 格外，10 级，sky/lights:window south 4 main @ (14, 12, 34) |
| 14..15 | 18 | 8..9 | 3 | 0 | 3/0/0 | 8 格外，3 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 15 | 20 | 29..31 | 3 | 0 | 3/0/0 | 11 格外，10 级，sky/lights:window east 17 main @ (16, 12, 32) |

## room: time room：暗 89 格，5 堆，最暗 1

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 4..13 | 7 | -20..-7 | 83 | 1 | 83/0/0 | 4 格外，8 级，sky/lights:stair @ (5, 9, -4) |
| 2..3 | 7 | -20..-19 | 3 | 4 | 3/0/0 | 5 格外，9 级，interiors/timeroom:clock west @ (2, 8, -25) |
| 2 | 7 | -13 | 1 | 4 | 1/0/0 | 5 格外，8 级，interiors/timeroom:rating bench @ (3, 7, -16) |
| 4 | 7 | -19 | 1 | 4 | 1/0/0 | 5 格外，8 级，interiors/timeroom:rating bench @ (3, 7, -16) |
| 5 | 7 | -18 | 1 | 4 | 1/0/0 | 5 格外，8 级，interiors/timeroom:rating bench @ (3, 7, -16) |

## room: star hall：暗 65 格，14 堆，最暗 1

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 12..15 | 0 | -4..4 | 19 | 3 | 19/0/0 | 3 格外，7 级，props/lamps:bracket_b @ (13, 2, -5) |
| 2..3 | 0 | -3..3 | 9 | 1 | 9/0/0 | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, -4) |
| 5..8 | 7..8 | 4..5 | 8 | 3 | 8/0/0 | 2 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |
| 2..3 | 7..8 | 2..5 | 6 | 1 | 6/0/0 | 3 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 2..5 | 12..13 | 3 | 4 | 1 | 0/4/0 | 6 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 14..15 | 7..8 | -5..-4 | 4 | 3 | 4/0/0 | 3 格外，6 级，sky/lights:window east 8 main @ (17, 10, -4) |
| 14..15 | 7..8 | 4..5 | 4 | 3 | 4/0/0 | 3 格外，6 级，sky/lights:window east 10 main @ (17, 10, 4) |
| 2..4 | 7..8 | -3 | 3 | 4 | 0/3/0 | 3 格外，8 级，sky/lights:stair @ (5, 9, -4) |
| 2..3 | 7 | -5 | 2 | 3 | 2/0/0 | 3 格外，7 级，props/lamps:cage_a @ (4, 10, -5) |
| 7..8 | 7 | -5 | 2 | 4 | 2/0/0 | 2 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |
| 2 | 0 | -5 | 1 | 4 | 1/0/0 | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, -4) |
| 2 | 0 | 5 | 1 | 4 | 1/0/0 | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, 4) |
| 9 | 0 | -3 | 1 | 4 | 1/0/0 | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, -5) |
| 9 | 0 | 3 | 1 | 4 | 1/0/0 | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, 5) |

## in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot：暗 56 格，5 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 8..15 | 17..20 | -15..-8 | 23 | 0 | 18/4/1 | 1 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 9..16 | 17..18 | -34..-27 | 16 | 0 | 15/1/0 | 3 格外，7 级，sky/lights:window tower tower 3 shaft @ (10, 22, -30) |
| 9..16 | 18..20 | -26 | 8 | 0 | 8/0/0 | 3 格外，6 级，main/roof:walk @ (8, 20, -25) |
| 3..6 | 18..20 | -15..-14 | 6 | 0 | 3/3/0 | 2 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14..15 | 18 | -9..-8 | 3 | 0 | 3/0/0 | 8 格外，3 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |

## off the routes：暗 51 格，7 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 124..131 | -26..-25 | -46..-43 | 15 | 0 | 15/0/0 | 58 格外，10 级，sky/lights:window station station.east -39 main @ (92, -2, -39) |
| 106..109 | -17..-15 | -40..-37 | 10 | 0 | 10/0/0 | 26 格外，10 级，sky/lights:window station station.east -39 main @ (92, -2, -39) |
| 112..115 | -22..-19 | -42..-39 | 10 | 0 | 10/0/0 | 36 格外，10 级，sky/lights:window station station.east -39 main @ (92, -2, -39) |
| 118..121 | -25..-24 | -44..-41 | 10 | 0 | 10/0/0 | 50 格外，10 级，sky/lights:window station station.east -39 main @ (92, -2, -39) |
| 102..103 | -13..-12 | -38..-36 | 4 | 0 | 4/0/0 | 19 格外，10 级，sky/lights:window station station.east -37 main @ (92, -2, -37) |
| 102 | -12 | -35 | 1 | 0 | 1/0/0 | 21 格外，10 级，sky/lights:window station station.east -37 main @ (92, -2, -37) |
| 130 | -24 | -47 | 1 | 0 | 1/0/0 | 67 格外，10 级，sky/lights:window station station.east -39 main @ (92, -2, -39) |

## in-M the meridian hut：暗 42 格，2 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 32..34 | 0 | -33..-27 | 21 | 0 | 21/0/0 | 1 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 36..38 | 0 | -33..-27 | 21 | 0 | 21/0/0 | 3 格外，7 级，props/lamps:cage_a @ (37, 2, -25) |

## room: chart room：暗 40 格，14 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 4..10 | 7 | 20..25 | 21 | 3 | 21/0/0 | 5 格外，9 级，interiors/chartroom:bracket lamp on a pier of the bookcase @ (11, 10, 24) |
| 12..13 | 7 | 7..9 | 4 | 3 | 4/0/0 | 4 格外，8 级，interiors/chartroom:sky_map_b @ (11, 10, 8) |
| 2 | 7 | 8..9 | 2 | 4 | 2/0/0 | 4 格外，8 级，interiors/chartroom:blackboard @ (3, 8, 12) |
| 5..6 | 7 | 7 | 2 | 4 | 2/0/0 | 4 格外，8 级，interiors/chartroom:sky_map @ (4, 10, 8) |
| 9..10 | 7 | 7 | 2 | 4 | 2/0/0 | 4 格外，8 级，interiors/chartroom:sky_map_b @ (11, 10, 8) |
| 2 | 7 | 23 | 1 | 4 | 1/0/0 | 5 格外，9 级，interiors/chartroom:bracket lamp on a pier of the bookcase @ (4, 10, 24) |
| 2 | 7 | 25 | 1 | 4 | 1/0/0 | 5 格外，9 级，interiors/chartroom:bracket lamp on a pier of the bookcase @ (4, 10, 24) |
| 3 | 7 | 7 | 1 | 4 | 1/0/0 | 4 格外，8 级，interiors/chartroom:sky_map @ (4, 10, 8) |
| 3 | 7 | 22 | 1 | 4 | 1/0/0 | 5 格外，9 级，interiors/chartroom:bracket lamp on a pier of the bookcase @ (4, 10, 24) |
| 4 | 7 | 19 | 1 | 4 | 1/0/0 | 5 格外，8 级，interiors/chartroom:drafting table @ (3, 7, 16) |
| 13 | 7 | 15 | 1 | 4 | 1/0/0 | 5 格外，8 级，interiors/chartroom:the green desk lamp @ (12, 7, 12) |
| 13 | 7 | 17 | 1 | 4 | 1/0/0 | 5 格外，8 级，interiors/chartroom:bench @ (12, 7, 20) |
| 13 | 7 | 23 | 1 | 4 | 1/0/0 | 5 格外，9 级，interiors/chartroom:bracket lamp on a pier of the bookcase @ (11, 10, 24) |
| 13 | 7 | 25 | 1 | 4 | 1/0/0 | 5 格外，9 级，interiors/chartroom:bracket lamp on a pier of the bookcase @ (11, 10, 24) |

## in-C the way to the west door：暗 31 格，2 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -11..-8 | 0 | -8..8 | 30 | 0 | 27/0/3 | 8 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |
| -8 | 0 | -9 | 1 | 0 | 1/0/0 | 17 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |

## out-F the south side: the south lookout：暗 31 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -2..18 | 0 | 29..36 | 31 | 0 | 31/0/0 | 10 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |

## out-C the front court: axis, meridian, the foot of the front：暗 30 格，2 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 17..18 | 0 | -32..-19 | 15 | 0 | 15/0/0 | 4 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 17..18 | 0 | 19..32 | 15 | 0 | 15/0/0 | 6 格外，10 级，sky/lights:wash @ (17, 2, 14) |

## out-D the north side: the mast pad, the weather station：暗 30 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -2..18 | 0 | -36..-30 | 30 | 0 | 30/0/0 | 9 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |

## in-L the power house, inside：暗 24 格，4 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 83..87 | -6 | 25..31 | 19 | 2 | 19/0/0 | 6 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 69 | -6 | 24..25 | 2 | 4 | 2/0/0 | 2 格外，6 级，interiors/powerhouse:desk lamp @ (69, -5, 22) |
| 83 | -6 | 22..23 | 2 | 4 | 2/0/0 | 6 格外，10 级，sky/lights:window power power.north 4 furnace @ (82, -2, 20) |
| 83 | -6 | 29 | 1 | 4 | 1/0/0 | 6 格外，10 级，machines/boiler:fire @ (78, -5, 28) |

## out-I the lower platform, north: its edges, the wall's foot, back to the station：暗 19 格，2 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 93..97 | -9..-8 | -36..-32 | 14 | 0 | 14/0/0 | 7 格外，9 级，machines/cable:car_windows @ (91, -2, -33) |
| 100..101 | -11 | -37..-35 | 5 | 0 | 5/0/0 | 16 格外，10 级，sky/lights:window station station.east -37 main @ (92, -2, -37) |

## in-I the dome room：暗 18 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 0..3 | 17..18 | -15..-12 | 8 | 0 | 5/3/0 | 6 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 0..3 | 17..18 | 12..15 | 8 | 0 | 5/3/0 | 6 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 4 | 18 | -13 | 1 | 0 | 1/0/0 | 7 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 4 | 18 | 13 | 1 | 0 | 1/0/0 | 3 格外，3 级，interiors/domeroom:clock_dial @ (4, 19, 10) |

## in-H the ring stair：暗 10 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 5..7 | 14..17 | -3..3 | 10 | 0 | 0/10/0 | 6 格外，4 级，machines/scope:lamp @ (9, 20, 0) |

## in-A the entrance from the court：暗 9 格，3 堆，最暗 4

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 16..17 | 0 | -1..1 | 5 | 4 | 2/0/3 | 3 格外，9 级，props/ironwork:door_frame @ (17, 4, 0) |
| 17 | 0 | -4..-3 | 2 | 4 | 0/0/2 | 4 格外，8 级，props/lamps:bracket_b @ (15, 2, -5) |
| 17 | 0 | 3..4 | 2 | 4 | 0/0/2 | 4 格外，8 级，props/lamps:bracket_b @ (15, 2, 5) |

## out-H the lower platform, south: the way to the works, round the power house：暗 4 格，3 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 63..64 | -6 | 33 | 2 | 0 | 2/0/0 | 10 格外，10 级，machines/board:lamp @ (71, -4, 31) |
| 61 | -6 | 33 | 1 | 0 | 1/0/0 | 13 格外，10 级，machines/board:lamp @ (71, -4, 31) |
| 66 | -6 | 33 | 1 | 0 | 1/0/0 | 8 格外，10 级，machines/board:lamp @ (71, -4, 31) |

## out-A arrival: the station platform, the walk to the axis：暗 3 格，3 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 83 | -4 | -37 | 1 | 0 | 1/0/0 | 5 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 88 | -4 | -30 | 1 | 4 | 1/0/0 | 7 格外，9 级，machines/cable:car_windows @ (91, -2, -33) |
| 90 | -4 | -30 | 1 | 4 | 1/0/0 | 5 格外，9 级，machines/cable:car_windows @ (91, -2, -33) |

## in-B the star hall, ground floor：暗 2 格，2 堆，最暗 6

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 17 | 0 | -5 | 1 | 6 | 0/0/1 | 3 格外，8 级，props/lamps:bracket_b @ (15, 2, -5) |
| 17 | 0 | 5 | 1 | 6 | 0/0/1 | 3 格外，8 级，props/lamps:bracket_b @ (15, 2, 5) |

## in-F the time room (north wing)：暗 2 格，1 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 7..8 | 7 | -6 | 2 | 3 | 0/0/2 | 3 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |

## in-G the chart room (south wing)：暗 2 格，1 堆，最暗 4

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 7..8 | 7 | 6 | 2 | 4 | 0/0/2 | 3 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |

## 露天的（不算暗，天光照得到）

| 地段 | 格数 | x | y | z |
| --- | --- | --- | --- | --- |
| off the routes | 25642 | -69..131 | -29..-8 | -89..96 |
| out-E the west side: the water tower, the sunset terrace | 1241 | -31..-3 | -9..1 | -39..40 |
| out-C the front court: axis, meridian, the foot of the front | 1083 | 18..58 | 0..1 | -33..32 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 929 | 41..101 | -13..-3 | -49..-4 |
| out-F the south side: the south lookout | 892 | -5..60 | -12..1 | 25..61 |
| out-D the north side: the mast pad, the weather station | 795 | -14..60 | -11..2 | -54..-28 |
| out-H the lower platform, south: the way to the works, round the power house | 673 | 51..97 | -13..-4 | 4..49 |
| out-G the terrace's east lip, over the lower platform | 609 | 45..65 | -2..1 | -33..35 |
| out-A arrival: the station platform, the walk to the axis | 315 | 74..95 | -12..-3 | -44..6 |
| in-M the meridian hut | 243 | 27..48 | 0..1 | -37..-17 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 241 | 0..16 | 17..21 | 13..34 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 237 | 0..15 | 17..21 | -34..-13 |
| out-B the axis and the grand stair | 211 | 59..80 | -6..0 | -9..9 |
| in-L the power house, inside | 64 | 66..85 | -6 | 12..23 |
| in-A the entrance from the court | 8 | 28..29 | 0 | -2..2 |
| in-C the way to the west door | 6 | -11 | 0 | -8..8 |
| in-I the dome room | 6 | 0..2 | 17..18 | -16..16 |
| room: stair hall | 5 | 1 | 9..11 | -2..2 |

## 起算的点

- spawn：新到 143758 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #66：新到 1292 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #78：新到 95 个落脚点
- in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot #82：新到 1264 个落脚点
