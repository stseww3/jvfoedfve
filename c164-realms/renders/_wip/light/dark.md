# 路上的光：暗格清单（总装 d7374d32）

量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。地面低于 5、台阶（脚下是 `_stairs`、`_slab`）和门槛（`facade.doors()`、`shell.doors()`、`S.DOME_ROOM_DOORS` 的格）低于 7 算暗。坐标是格子的整数坐标，y 是脚所在的那一行。

不算暗、另列的三种：露天（正上方到天没有挡光的块；玻璃不挡，整块、台阶、半砖、活板门挡）；檐下（头上有东西，但天光从旁边照进来还有 13 级以上，按游戏的算法每走一格减一级：檐口下贴墙的那一条、水塔底下、敞开的门洞里头两格）；穹顶室（总监 #442）。壳里的房间（`shell.room_at` 认得的）一律只看块光，不管窗子透进多少天光。

- 站得住的格：36598（走得到 8287，要跳一下 28311），其中屋顶下 1500。只能掉下去才到的地方不算（4442 个落脚点）。
- **暗：338 格，52 堆**（地面 252，台阶 68，门槛 18）。
- 不算暗：露天 33196 格，檐下 413 格，穹顶室 296 格。sky/lights 现在放了 172 个光源。

每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、最近的 sky/lights 光源（走格数、级、它的说明）。

## room: stair hall：暗 122 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -5..1 | 7..11 | -5..5 | 51 | 0 | 44/7/0 | 3 格外，7 级，props/lamps:cage_a @ (-6, 9, -2) |
| -7..1 | 0 | -1..1 | 27 | 0 | 27/0/0 | 6 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | -5..-3 | 22 | 0 | 1/21/0 | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | 3..5 | 22 | 0 | 1/21/0 | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, 4) |

## room: star hall：暗 62 格，14 堆，最暗 1

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 12..15 | 0 | -4..4 | 19 | 3 | 19/0/0 | 3 格外，7 级，props/lamps:bracket_b @ (13, 2, -5) |
| 2..3 | 0 | -3..3 | 9 | 1 | 9/0/0 | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, -4) |
| 2..3 | 7..8 | 2..5 | 6 | 1 | 6/0/0 | 3 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 5..8 | 7..8 | 4..5 | 6 | 3 | 6/0/0 | 2 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |
| 2..5 | 12..13 | 3 | 4 | 1 | 0/4/0 | 6 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 14..15 | 7..8 | -5..-4 | 4 | 3 | 4/0/0 | 3 格外，6 级，sky/lights:window east 8 main @ (17, 10, -4) |
| 14..15 | 7..8 | 4..5 | 4 | 3 | 4/0/0 | 3 格外，6 级，sky/lights:window east 10 main @ (17, 10, 4) |
| 2..4 | 7..8 | -3 | 3 | 4 | 0/3/0 | 3 格外，8 级，sky/lights:stair @ (5, 9, -4) |
| 2..3 | 7 | -5 | 2 | 3 | 2/0/0 | 3 格外，7 级，props/lamps:cage_a @ (4, 10, -5) |
| 2 | 0 | -5 | 1 | 4 | 1/0/0 | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, -4) |
| 2 | 0 | 5 | 1 | 4 | 1/0/0 | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, 4) |
| 8 | 7 | -5 | 1 | 4 | 1/0/0 | 2 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |
| 9 | 0 | -3 | 1 | 4 | 1/0/0 | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, -5) |
| 9 | 0 | 3 | 1 | 4 | 1/0/0 | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, 5) |

## in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome：暗 31 格，8 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 12..14 | 18 | 28..32 | 9 | 0 | 9/0/0 | 8 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 11..13 | 18 | 8..12 | 7 | 0 | 6/0/1 | 7 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 11..13 | 20 | 27 | 3 | 0 | 3/0/0 | 6 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 11..13 | 20 | 33 | 3 | 0 | 3/0/0 | 11 格外，10 级，sky/lights:window south 4 main @ (14, 12, 34) |
| 14..15 | 18 | 8..9 | 3 | 0 | 3/0/0 | 8 格外，3 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 15 | 20 | 29..31 | 3 | 0 | 3/0/0 | 11 格外，10 级，sky/lights:window east 17 main @ (16, 12, 32) |
| 8..9 | 20 | 13 | 2 | 3 | 2/0/0 | 3 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 14 | 17 | 10 | 1 | 0 | 0/1/0 | 9 格外，10 级，sky/lights:window east 12 main @ (15, 12, 12) |

## room: time room：暗 27 格，3 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 6..13 | 7 | -20..-13 | 24 | 3 | 24/0/0 | 5 格外，9 级，interiors/timeroom:clock east @ (13, 8, -25) |
| 10..11 | 7 | -7 | 2 | 4 | 2/0/0 | 4 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |
| 13 | 7 | -7 | 1 | 4 | 1/0/0 | 6 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |

## in-L the power house, inside：暗 21 格，3 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 83..87 | -6 | 26..31 | 18 | 2 | 18/0/0 | 6 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 69 | -6 | 24..25 | 2 | 4 | 2/0/0 | 2 格外，6 级，interiors/powerhouse:desk lamp @ (69, -5, 22) |
| 83 | -6 | 22 | 1 | 4 | 1/0/0 | 6 格外，10 级，sky/lights:window power power.north 4 furnace @ (82, -2, 20) |

## in-M the meridian hut：暗 14 格，2 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 32 | 0 | -33..-27 | 7 | 0 | 7/0/0 | 1 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 38 | 0 | -33..-27 | 7 | 0 | 7/0/0 | 4 格外，7 级，props/lamps:cage_a @ (37, 2, -25) |

## in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot：暗 13 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 11..13 | 18 | -12..-8 | 7 | 0 | 6/0/1 | 7 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14..15 | 18 | -9..-8 | 3 | 0 | 3/0/0 | 8 格外，3 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 8..9 | 20 | -13 | 2 | 3 | 2/0/0 | 3 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14 | 17 | -10 | 1 | 0 | 0/1/0 | 9 格外，10 级，sky/lights:window east 6 main @ (15, 12, -12) |

## out-E the west side: the water tower, the sunset terrace：暗 11 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -19..-16 | -2 | -33..-29 | 11 | 0 | 11/0/0 | 3 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |

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

## in-C the way to the west door：暗 6 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -9..-8 | 0 | -1..1 | 6 | 0 | 3/0/3 | 8 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |

## in-I the dome room：暗 6 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 18 | -13..-12 | 2 | 0 | 2/0/0 | 10 格外，10 级，sky/lights:window west 5 main @ (0, 12, -16) |
| 0 | 18 | 12..13 | 2 | 0 | 2/0/0 | 6 格外，3 级，interiors/domeroom:clock_dial @ (4, 19, 10) |
| 4 | 18 | -13 | 1 | 0 | 1/0/0 | 7 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 4 | 18 | 13 | 1 | 0 | 1/0/0 | 3 格外，3 级，interiors/domeroom:clock_dial @ (4, 19, 10) |

## in-B the star hall, ground floor：暗 2 格，2 堆，最暗 6

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 17 | 0 | -5 | 1 | 6 | 0/0/1 | 3 格外，8 级，props/lamps:bracket_b @ (15, 2, -5) |
| 17 | 0 | 5 | 1 | 6 | 0/0/1 | 3 格外，8 级，props/lamps:bracket_b @ (15, 2, 5) |

## in-F the time room (north wing)：暗 2 格，1 堆，最暗 5

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 7..8 | 7 | -6 | 2 | 5 | 0/0/2 | 3 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |

## in-G the chart room (south wing)：暗 2 格，1 堆，最暗 6

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 7..8 | 7 | 6 | 2 | 6 | 0/0/2 | 3 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |

## 檐下的（不算暗：天光从旁边照得到；块光不够，要不要补由 lights 看）

| 地段 | x | y | z | 格数 | 最暗的块光 |
| --- | --- | --- | --- | --- | --- |
| out-E the west side: the water tower, the sunset terrace | -9..-2 | 0 | 9..28 | 27 | 0 |
| out-E the west side: the water tower, the sunset terrace | -8..-2 | 0 | -29..-10 | 26 | 0 |
| out-E the west side: the water tower, the sunset terrace | -19..-15 | -2 | -29..-28 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -20..-19 | -2 | -33..-29 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -19..-15 | -2 | -34..-33 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -15..-14 | -2 | -32..-29 | 6 | 1 |
| out-E the west side: the water tower, the sunset terrace | -9 | 0 | -9 | 1 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 8..16 | 17..18 | 26..34 | 29 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 9..15 | 17..20 | 11..15 | 13 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 10..13 | 18 | 28..32 | 10 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 3..6 | 18..20 | 14..15 | 6 | 0 |
| off the routes | 124..131 | -26..-25 | -46..-43 | 15 | 0 |
| off the routes | 118..121 | -25..-24 | -44..-41 | 10 | 0 |
| off the routes | 112..115 | -22..-19 | -42..-39 | 10 | 0 |
| off the routes | 106..109 | -17..-15 | -40..-37 | 10 | 0 |
| off the routes | 102..103 | -13..-12 | -38..-36 | 4 | 0 |
| off the routes | 130 | -24 | -47 | 1 | 0 |
| off the routes | 102 | -12 | -35 | 1 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..16 | 17..18 | -34..-27 | 16 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..15 | 17..20 | -15..-11 | 13 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..16 | 18..20 | -26 | 8 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 3..6 | 18..20 | -15..-14 | 6 | 0 |
| out-F the south side: the south lookout | -2..18 | 0 | 29..36 | 31 | 0 |
| out-C the front court: axis, meridian, the foot of the front | 17..18 | 0 | -32..-19 | 15 | 0 |
| out-C the front court: axis, meridian, the foot of the front | 17..18 | 0 | 19..32 | 15 | 0 |
| out-D the north side: the mast pad, the weather station | -2..18 | 0 | -36..-30 | 30 | 0 |
| in-M the meridian hut | 33..34 | 0 | -33..-27 | 13 | 0 |
| in-M the meridian hut | 36..37 | 0 | -33..-27 | 13 | 0 |
| in-C the way to the west door | -11..-9 | 0 | -8..8 | 24 | 0 |
| in-C the way to the west door | -8 | 0 | -9 | 1 | 0 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 93..97 | -9..-8 | -36..-32 | 14 | 0 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 100..101 | -11 | -37..-35 | 5 | 0 |
| in-I the dome room | 0..3 | 17..18 | -15..-14 | 6 | 0 |
| in-I the dome room | 0..3 | 17..18 | 14..15 | 6 | 0 |
| out-H the lower platform, south: the way to the works, round the power house | 63..64 | -6 | 33 | 2 | 0 |
| out-H the lower platform, south: the way to the works, round the power house | 66 | -6 | 33 | 1 | 0 |
| out-H the lower platform, south: the way to the works, round the power house | 61 | -6 | 33 | 1 | 0 |
| out-A arrival: the station platform, the walk to the axis | 90 | -4 | -30 | 1 | 4 |
| out-A arrival: the station platform, the walk to the axis | 88 | -4 | -30 | 1 | 4 |
| out-A arrival: the station platform, the walk to the axis | 83 | -4 | -37 | 1 | 0 |

## 露天的（不算暗）

| 地段 | 格数 | x | y | z |
| --- | --- | --- | --- | --- |
| off the routes | 25642 | -69..131 | -29..-8 | -89..96 |
| out-E the west side: the water tower, the sunset terrace | 1238 | -31..-3 | -9..1 | -39..40 |
| out-C the front court: axis, meridian, the foot of the front | 1083 | 18..58 | 0..1 | -33..32 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 929 | 41..101 | -13..-3 | -49..-4 |
| out-F the south side: the south lookout | 892 | -5..60 | -12..1 | 25..61 |
| out-D the north side: the mast pad, the weather station | 795 | -14..60 | -11..2 | -54..-28 |
| out-H the lower platform, south: the way to the works, round the power house | 677 | 51..97 | -13..-4 | 4..49 |
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

## 起算的点

- spawn：新到 143513 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #66：新到 1292 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #78：新到 95 个落脚点
- in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot #82：新到 1264 个落脚点
