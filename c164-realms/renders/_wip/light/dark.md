# 路上的光：暗格清单（总装 8f3a0621）

量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。地面低于 5、台阶（脚下是 `_stairs`、`_slab`）和门槛（`facade.doors()`、`shell.doors()`、`S.DOME_ROOM_DOORS` 的格）低于 7 算暗。坐标是格子的整数坐标，y 是脚所在的那一行。

不算暗、另列的三种：露天（正上方到天没有挡光的块；玻璃不挡，整块、台阶、半砖、活板门挡）；檐下（头上有东西，但天光从旁边照进来还有 13 级以上，按游戏的算法每走一格减一级：檐口下贴墙的那一条、水塔底下、敞开的门洞里头两格）；穹顶室（总监 #442）。壳里的房间（`shell.room_at` 认得的）一律只看块光，不管窗子透进多少天光。

- 站得住的格：36598（走得到 8287，要跳一下 28311），其中屋顶下 2746。只能掉下去才到的地方不算（4442 个落脚点）。
- **暗：1521 格，242 堆**（地面 1052，台阶 451，门槛 18）。
- 不算暗：露天 32013 格，檐下 413 格，穹顶室 296 格。sky/lights 现在放了 172 个光源。

每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、最近的 sky/lights 光源（走格数、级、它的说明）。

## off the routes：暗 608 格，20 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 60..86 | -20..-18 | -53..-49 | 86 | 0 | 86/0/0 | 26 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 30..44 | -21..-20 | -64..-49 | 66 | 0 | 66/0/0 | 48 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 13..27 | -21..-20 | -67..-56 | 45 | 0 | 45/0/0 | 52 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 3..17 | -20..-19 | 48..54 | 44 | 0 | 44/0/0 | 43 格外，10 级，sky/lights:window south 4 main @ (14, 9, 34) |
| 89..100 | -21..-19 | 43..52 | 41 | 0 | 41/0/0 | 34 格外，12 级，interiors/powerhouse:engine lamp x 84 @ (84, -5, 36) |
| -29..-19 | -15..-12 | -21..-13 | 39 | 0 | 39/0/0 | 28 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -9..5 | -16..-15 | 45..49 | 39 | 0 | 39/0/0 | 34 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| 97..102 | -20..-19 | 16..28 | 39 | 0 | 39/0/0 | 25 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| -20..-11 | -16 | 40..47 | 31 | 0 | 31/0/0 | 50 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| 13..21 | -13..-12 | -56..-49 | 31 | 0 | 31/0/0 | 37 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 27..35 | -14 | 45..49 | 26 | 0 | 26/0/0 | 47 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| -15..-12 | -9..-8 | 32..40 | 23 | 0 | 23/0/0 | 31 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| -20..-16 | -16 | 30..37 | 17 | 0 | 17/0/0 | 41 格外，10 级，sky/lights:window west 16 main @ (0, 9, 29) |
| 28..32 | -23..-20 | 52..56 | 16 | 0 | 16/0/0 | 65 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| -34..-28 | -21..-19 | -42..-40 | 13 | 0 | 13/0/0 | 41 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -17..-13 | -15..-14 | -45..-42 | 13 | 0 | 13/0/0 | 24 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| 16..22 | -14 | 45..47 | 13 | 0 | 13/0/0 | 36 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 34..38 | -12 | -45..-43 | 13 | 0 | 13/0/0 | 28 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 56..60 | -20 | 50..52 | 12 | 0 | 12/0/0 | 40 格外，12 级，interiors/powerhouse:engine lamp x 72 @ (73, -5, 37) |
| 4 | -8 | 42 | 1 | 0 | 1/0/0 | 25 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |

## room: stair hall：暗 122 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -5..1 | 7..11 | -5..5 | 51 | 0 | 44/7/0 | 3 格外，7 级，props/lamps:cage_a @ (-6, 9, -2) |
| -7..1 | 0 | -1..1 | 27 | 0 | 27/0/0 | 6 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | -5..-3 | 22 | 0 | 1/21/0 | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | 3..5 | 22 | 0 | 1/21/0 | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, 4) |

## in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome：暗 114 格，17 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 1..8 | 17 | 27..33 | 14 | 0 | 0/14/0 | 7 格外，10 级，sky/lights:window south 1 main @ (3, 12, 34) |
| 11 | 18 | 15..25 | 11 | 0 | 0/11/0 | 4 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 4 | 18 | 16..25 | 10 | 0 | 0/10/0 | 5 格外，6 级，main/roof:walk @ (8, 20, 20) |
| 6 | 19 | 16..25 | 10 | 2 | 0/10/0 | 2 格外，6 级，main/roof:walk @ (8, 20, 20) |
| 9 | 19 | 16..25 | 10 | 3 | 0/10/0 | 1 格外，6 级，main/roof:walk @ (8, 20, 20) |
| 13 | 17 | 16..25 | 10 | 0 | 0/10/0 | 7 格外，6 级，main/roof:walk @ (8, 20, 20) |
| 3..7 | 18 | 27..29 | 9 | 0 | 0/9/0 | 4 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 12..14 | 18 | 28..32 | 9 | 0 | 9/0/0 | 8 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 2 | 17 | 17..24 | 8 | 0 | 0/8/0 | 8 格外，10 级，sky/lights:window west 14 main @ (0, 12, 20) |
| 11..13 | 18 | 8..12 | 7 | 0 | 6/0/1 | 7 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 11..13 | 20 | 27 | 3 | 0 | 3/0/0 | 6 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 11..13 | 20 | 33 | 3 | 0 | 3/0/0 | 11 格外，10 级，sky/lights:window south 4 main @ (14, 12, 34) |
| 14..15 | 18 | 8..9 | 3 | 0 | 3/0/0 | 8 格外，3 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 15 | 20 | 29..31 | 3 | 0 | 3/0/0 | 11 格外，10 级，sky/lights:window east 17 main @ (16, 12, 32) |
| 8..9 | 20 | 13 | 2 | 3 | 2/0/0 | 3 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 14 | 17 | 10 | 1 | 0 | 0/1/0 | 9 格外，10 级，sky/lights:window east 12 main @ (15, 12, 12) |
| 14 | 17 | 13 | 1 | 0 | 0/1/0 | 8 格外，10 级，sky/lights:window east 12 main @ (15, 12, 12) |

## in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot：暗 96 格，13 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 1..8 | 17 | -33..-27 | 14 | 0 | 0/14/0 | 7 格外，10 级，sky/lights:window north 2 main @ (6, 12, -34) |
| 11 | 18 | -25..-15 | 11 | 0 | 0/11/0 | 4 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 4 | 18 | -25..-16 | 10 | 0 | 0/10/0 | 5 格外，6 级，main/roof:walk @ (8, 20, -20) |
| 6 | 19 | -25..-16 | 10 | 2 | 0/10/0 | 2 格外，6 级，main/roof:walk @ (8, 20, -20) |
| 9 | 19 | -25..-16 | 10 | 3 | 0/10/0 | 1 格外，6 级，main/roof:walk @ (8, 20, -20) |
| 13 | 17 | -25..-16 | 10 | 0 | 0/10/0 | 7 格外，6 级，main/roof:walk @ (8, 20, -20) |
| 3..7 | 18 | -29..-27 | 9 | 0 | 0/9/0 | 4 格外，6 级，main/roof:walk @ (8, 20, -25) |
| 2 | 17 | -24..-17 | 8 | 0 | 0/8/0 | 8 格外，10 级，sky/lights:window west 3 main @ (0, 12, -24) |
| 11..13 | 18 | -12..-8 | 7 | 0 | 6/0/1 | 7 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14..15 | 18 | -9..-8 | 3 | 0 | 3/0/0 | 8 格外，3 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 8..9 | 20 | -13 | 2 | 3 | 2/0/0 | 3 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14 | 17 | -13 | 1 | 0 | 0/1/0 | 8 格外，10 级，sky/lights:window east 6 main @ (15, 12, -12) |
| 14 | 17 | -10 | 1 | 0 | 0/1/0 | 9 格外，10 级，sky/lights:window east 6 main @ (15, 12, -12) |

## out-F the south side: the south lookout：暗 85 格，25 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 25..38 | -7..-6 | 40..43 | 37 | 0 | 37/0/0 | 31 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 4..9 | -7 | 40..42 | 12 | 0 | 12/0/0 | 23 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| 44..46 | -5 | 53..55 | 8 | 0 | 8/0/0 | 43 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 50..51 | -7..-6 | 40..41 | 4 | 0 | 4/0/0 | 25 格外，12 级，interiors/powerhouse:engine lamp x 72 @ (73, -5, 37) |
| 57..60 | 0..1 | 34 | 4 | 0 | 0/4/0 | 16 格外，10 级，props/lamps:post @ (60, 2, 18) |
| -2 | 1 | 38 | 1 | 0 | 0/1/0 | 16 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| 2 | 1 | 38 | 1 | 0 | 0/1/0 | 12 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| 6 | 1 | 38 | 1 | 0 | 0/1/0 | 14 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| 10 | 1 | 38 | 1 | 0 | 0/1/0 | 15 格外，10 级，sky/lights:window south 4 main @ (14, 9, 34) |
| 14 | 1 | 38 | 1 | 0 | 0/1/0 | 11 格外，10 级，sky/lights:window south 4 main @ (14, 9, 34) |
| 19 | 1 | 38 | 1 | 0 | 0/1/0 | 16 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 23 | 1 | 38 | 1 | 0 | 0/1/0 | 20 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 27 | 1 | 38 | 1 | 0 | 0/1/0 | 24 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 31 | 1 | 38 | 1 | 0 | 0/1/0 | 28 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 35 | 1 | 38 | 1 | 0 | 0/1/0 | 32 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 39 | 1 | 38 | 1 | 0 | 0/1/0 | 36 格外，10 级，sky/lights:window east 17 main @ (16, 9, 32) |
| 40 | -4 | 53 | 1 | 0 | 0/1/0 | 48 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 43 | -4 | 56 | 1 | 0 | 0/1/0 | 48 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 43 | 1 | 38 | 1 | 0 | 0/1/0 | 35 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 47 | -4 | 56 | 1 | 0 | 0/1/0 | 44 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 47 | 1 | 38 | 1 | 0 | 0/1/0 | 31 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 50 | -4 | 53 | 1 | 0 | 0/1/0 | 38 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 51 | 1 | 38 | 1 | 0 | 0/1/0 | 27 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 56 | 1 | 38 | 1 | 0 | 0/1/0 | 22 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 60 | 1 | 38 | 1 | 0 | 0/1/0 | 18 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |

## out-B the axis and the grand stair：暗 77 格，7 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 65 | -3 | -8..8 | 17 | 0 | 0/17/0 | 8 格外，10 级，props/lamps:post @ (61, 1, -9) |
| 67 | -4..-3 | -7..9 | 17 | 0 | 0/17/0 | 9 格外，10 级，props/lamps:post @ (61, 1, 9) |
| 63 | -2 | -6..6 | 13 | 0 | 0/13/0 | 7 格外，10 级，props/lamps:post @ (61, 1, -9) |
| 69 | -5 | -7..4 | 12 | 0 | 0/12/0 | 7 格外，12 级，sky/lights:pool @ (73, -6, -8) |
| 61 | -1 | -4..4 | 9 | 0 | 0/9/0 | 6 格外，10 级，props/lamps:post @ (61, 1, -9) |
| 71 | -6 | -4..3 | 8 | 2 | 0/8/0 | 7 格外，12 级，sky/lights:pool @ (73, -6, -8) |
| 67 | -3 | -9 | 1 | 4 | 0/1/0 | 9 格外，10 级，props/lamps:post @ (61, 1, -9) |

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

## out-C the front court: axis, meridian, the foot of the front：暗 60 格，6 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 33..37 | 0 | 3..29 | 33 | 0 | 33/0/0 | 4 格外，8 级，props/lamps:uplight @ (33, 0, 2) |
| 33..37 | 0 | -16..-3 | 20 | 0 | 20/0/0 | 4 格外，8 级，props/lamps:uplight @ (33, 0, -2) |
| 42 | 0 | -1..1 | 3 | 3 | 3/0/0 | 7 格外，8 级，props/lamps:uplight @ (37, 0, -2) |
| 35 | 0 | -25..-24 | 2 | 3 | 2/0/0 | 3 格外，7 级，props/lamps:cage_a @ (37, 2, -25) |
| 41 | 0 | -2 | 1 | 4 | 1/0/0 | 5 格外，8 级，props/lamps:uplight @ (37, 0, -2) |
| 41 | 0 | 2 | 1 | 4 | 1/0/0 | 5 格外，8 级，props/lamps:uplight @ (37, 0, 2) |

## out-I the lower platform, north: its edges, the wall's foot, back to the station：暗 54 格，16 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 52..64 | -12..-11 | -48..-44 | 39 | 0 | 39/0/0 | 23 格外，10 级，props/lamps:post @ (60, 2, -34) |
| 61 | -6 | -34 | 1 | 2 | 0/1/0 | 8 格外，10 级，props/lamps:post @ (60, 2, -34) |
| 61 | -6 | -26 | 1 | 2 | 0/1/0 | 8 格外，10 级，props/lamps:post @ (60, 2, -26) |
| 61 | -6 | -18 | 1 | 2 | 0/1/0 | 8 格外，10 级，props/lamps:post @ (60, 2, -18) |
| 61 | -5 | -42 | 1 | 0 | 0/1/0 | 15 格外，10 级，props/lamps:post @ (60, 2, -34) |
| 65 | -5 | -42 | 1 | 0 | 0/1/0 | 19 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 67 | -4 | -8 | 1 | 4 | 0/1/0 | 9 格外，12 级，sky/lights:pool @ (73, -6, -8) |
| 69 | -4 | -9 | 1 | 5 | 0/1/0 | 8 格外，13 级，props/lamps:street @ (73, 1, -9) |
| 70 | -5 | -42 | 1 | 0 | 0/1/0 | 14 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 74 | -5 | -42 | 1 | 0 | 0/1/0 | 10 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 77 | -3 | -40 | 1 | 3 | 0/1/0 | 5 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 78 | -5 | -42 | 1 | 1 | 0/1/0 | 6 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 91 | -5 | -22 | 1 | 2 | 0/1/0 | 11 格外，13 级，props/lamps:street @ (86, -2, -18) |
| 91 | -5 | -18 | 1 | 6 | 0/1/0 | 7 格外，13 级，props/lamps:street @ (86, -2, -18) |
| 91 | -5 | -14 | 1 | 3 | 0/1/0 | 10 格外，13 级，props/lamps:street @ (87, -2, -10) |
| 91 | -5 | -6 | 1 | 3 | 0/1/0 | 10 格外，13 级，props/lamps:street @ (87, -2, -10) |

## out-E the west side: the water tower, the sunset terrace：暗 38 格，28 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -19..-16 | -2 | -33..-29 | 11 | 0 | 11/0/0 | 3 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -28 | 1 | -3 | 1 | 0 | 0/1/0 | 29 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |
| -28 | 1 | 3 | 1 | 0 | 0/1/0 | 29 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |
| -26 | 1 | -8 | 1 | 0 | 0/1/0 | 32 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |
| -26 | 1 | 8 | 1 | 0 | 0/1/0 | 32 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |
| -23 | 1 | -13 | 1 | 0 | 0/1/0 | 28 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -23 | 1 | 13 | 1 | 0 | 0/1/0 | 30 格外，9 级，props/lamps:pendant_b @ (4, 4, 14) |
| -21 | -1 | -35 | 1 | 0 | 0/1/0 | 10 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -21 | -1 | -31 | 1 | 0 | 0/1/0 | 8 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -21 | -1 | -27 | 1 | 0 | 0/1/0 | 12 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -20 | 1 | -16 | 1 | 0 | 0/1/0 | 22 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -20 | 1 | 16 | 1 | 0 | 0/1/0 | 28 格外，12 级，interiors/chartroom:drafting table @ (3, 7, 16) |
| -17 | -1 | -35 | 1 | 1 | 0/1/0 | 6 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -17 | -1 | -27 | 1 | 0 | 0/1/0 | 8 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -14 | 1 | -18 | 1 | 0 | 0/1/0 | 16 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -14 | 1 | 18 | 1 | 0 | 0/1/0 | 23 格外，10 级，sky/lights:window west 14 main @ (0, 9, 20) |
| -13 | -1 | -35 | 1 | 1 | 0/1/0 | 6 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -13 | -1 | -27 | 1 | 0 | 0/1/0 | 8 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -10 | 1 | -34 | 1 | 0 | 0/1/0 | 8 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -10 | 1 | -30 | 1 | 0 | 0/1/0 | 8 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -10 | 1 | -26 | 1 | 0 | 0/1/0 | 12 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -10 | 1 | -20 | 1 | 0 | 0/1/0 | 18 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -10 | 1 | 20 | 1 | 0 | 0/1/0 | 17 格外，10 级，sky/lights:window west 14 main @ (0, 9, 20) |
| -10 | 1 | 26 | 1 | 0 | 0/1/0 | 19 格外，5 级，interiors/platevault:safelight @ (7, 2, 24) |
| -10 | 1 | 30 | 1 | 0 | 0/1/0 | 18 格外，10 级，sky/lights:window west 16 main @ (0, 9, 29) |
| -10 | 1 | 34 | 1 | 0 | 0/1/0 | 20 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| -10 | 1 | 38 | 1 | 0 | 0/1/0 | 24 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |
| -6 | 1 | 38 | 1 | 0 | 0/1/0 | 20 格外，10 级，sky/lights:window south 1 main @ (3, 9, 34) |

## out-H the lower platform, south: the way to the works, round the power house：暗 30 格，17 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 52..57 | -7..-6 | 40..42 | 12 | 0 | 12/0/0 | 19 格外，12 级，interiors/powerhouse:engine lamp x 72 @ (73, -5, 37) |
| 69 | -5 | 5..7 | 3 | 4 | 0/3/0 | 7 格外，12 级，sky/lights:pool @ (73, -6, 8) |
| 61 | -6 | 18 | 1 | 2 | 0/1/0 | 8 格外，10 级，props/lamps:post @ (60, 2, 18) |
| 61 | -6 | 26 | 1 | 0 | 0/1/0 | 12 格外，6 级，interiors/powerhouse:desk lamp @ (69, -5, 22) |
| 61 | -6 | 34 | 1 | 0 | 0/1/0 | 14 格外，10 级，machines/board:lamp @ (71, -4, 31) |
| 61 | -5 | 43 | 1 | 0 | 0/1/0 | 18 格外，6 级，machines/engine: the pilot lamp on the dynamo @ (72, -3, 37) |
| 69 | -4 | 9 | 1 | 5 | 0/1/0 | 8 格外，12 级，sky/lights:pool @ (73, -6, 8) |
| 71 | -6 | 4 | 1 | 6 | 0/1/0 | 7 格外，12 级，sky/lights:pool @ (73, -6, 8) |
| 91 | -5 | 6 | 1 | 3 | 0/1/0 | 10 格外，13 级，props/lamps:street @ (87, -2, 10) |
| 91 | -5 | 14 | 1 | 3 | 0/1/0 | 10 格外，13 级，props/lamps:street @ (87, -2, 10) |
| 91 | -5 | 18 | 1 | 0 | 0/1/0 | 13 格外，10 级，sky/lights:window power power.north 4 furnace @ (82, -2, 20) |
| 91 | -5 | 22 | 1 | 1 | 0/1/0 | 9 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 91 | -5 | 26 | 1 | 5 | 0/1/0 | 5 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 91 | -5 | 30 | 1 | 3 | 0/1/0 | 7 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 91 | -5 | 34 | 1 | 0 | 0/1/0 | 10 格外，12 级，interiors/powerhouse:engine lamp x 84 @ (84, -5, 36) |
| 91 | -5 | 38 | 1 | 0 | 0/1/0 | 10 格外，12 级，interiors/powerhouse:engine lamp x 84 @ (84, -5, 36) |
| 91 | -5 | 43 | 1 | 0 | 0/1/0 | 15 格外，12 级，interiors/powerhouse:engine lamp x 84 @ (84, -5, 36) |

## in-M the meridian hut：暗 29 格，4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 35 | 0 | -33..-26 | 8 | 0 | 8/0/0 | 4 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 32 | 0 | -33..-27 | 7 | 0 | 7/0/0 | 1 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 35 | 0 | -23..-17 | 7 | 0 | 7/0/0 | 5 格外，7 级，props/lamps:cage_a @ (37, 2, -25) |
| 38 | 0 | -33..-27 | 7 | 0 | 7/0/0 | 4 格外，7 级，props/lamps:cage_a @ (37, 2, -25) |

## room: time room：暗 27 格，3 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 6..13 | 7 | -20..-13 | 24 | 3 | 24/0/0 | 5 格外，9 级，interiors/timeroom:clock east @ (13, 8, -25) |
| 10..11 | 7 | -7 | 2 | 4 | 2/0/0 | 4 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |
| 13 | 7 | -7 | 1 | 4 | 1/0/0 | 6 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |

## out-D the north side: the mast pad, the weather station：暗 26 格，26 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -10 | 1 | -38 | 1 | 0 | 0/1/0 | 12 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -4 | 1 | -38 | 1 | 0 | 0/1/0 | 18 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -2 | -3 | -49 | 1 | 0 | 0/1/0 | 33 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| -2 | -3 | -43 | 1 | 0 | 0/1/0 | 27 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |
| 1 | 1 | -38 | 1 | 0 | 0/1/0 | 16 格外，10 级，sky/lights:window north 2 main @ (6, 9, -34) |
| 3 | -3 | -49 | 1 | 0 | 0/1/0 | 29 格外，10 级，sky/lights:window north 2 main @ (6, 9, -34) |
| 5 | 1 | -38 | 1 | 0 | 0/1/0 | 12 格外，10 级，sky/lights:window north 2 main @ (6, 9, -34) |
| 8 | -3 | -49 | 1 | 0 | 0/1/0 | 28 格外，10 级，sky/lights:window north 2 main @ (6, 9, -34) |
| 8 | -3 | -43 | 1 | 0 | 0/1/0 | 22 格外，10 级，sky/lights:window north 2 main @ (6, 9, -34) |
| 9 | 1 | -38 | 1 | 0 | 0/1/0 | 14 格外，10 级，sky/lights:window north 2 main @ (6, 9, -34) |
| 13 | 1 | -38 | 1 | 0 | 0/1/0 | 14 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 17 | 1 | -46 | 1 | 0 | 0/1/0 | 20 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 17 | 1 | -42 | 1 | 0 | 0/1/0 | 16 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 17 | 1 | -38 | 1 | 0 | 0/1/0 | 12 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 21 | 1 | -46 | 1 | 0 | 0/1/0 | 24 格外，5 级，sky/lights:window east 2 base @ (16, 3, -28) |
| 25 | 1 | -46 | 1 | 0 | 0/1/0 | 23 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 29 | 1 | -46 | 1 | 0 | 0/1/0 | 19 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 29 | 1 | -42 | 1 | 0 | 0/1/0 | 15 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 29 | 1 | -38 | 1 | 0 | 0/1/0 | 11 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 33 | 1 | -38 | 1 | 0 | 0/1/0 | 9 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 38 | 1 | -38 | 1 | 0 | 0/1/0 | 14 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 42 | 1 | -38 | 1 | 0 | 0/1/0 | 18 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 47 | 1 | -38 | 1 | 0 | 0/1/0 | 17 格外，10 级，props/lamps:post @ (60, 2, -34) |
| 51 | 1 | -38 | 1 | 0 | 0/1/0 | 13 格外，10 级，props/lamps:post @ (60, 2, -34) |
| 56 | 1 | -38 | 1 | 2 | 0/1/0 | 8 格外，10 级，props/lamps:post @ (60, 2, -34) |
| 60 | 1 | -38 | 1 | 6 | 0/1/0 | 4 格外，10 级，props/lamps:post @ (60, 2, -34) |

## in-L the power house, inside：暗 21 格，3 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 83..87 | -6 | 26..31 | 18 | 2 | 18/0/0 | 6 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 69 | -6 | 24..25 | 2 | 4 | 2/0/0 | 2 格外，6 级，interiors/powerhouse:desk lamp @ (69, -5, 22) |
| 83 | -6 | 22 | 1 | 4 | 1/0/0 | 6 格外，10 级，sky/lights:window power power.north 4 furnace @ (82, -2, 20) |

## out-G the terrace's east lip, over the lower platform：暗 21 格，14 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 57..59 | 0 | 32..33 | 4 | 0 | 0/4/0 | 16 格外，10 级，props/lamps:post @ (60, 2, 18) |
| 61 | -1 | -6..-5 | 2 | 5 | 0/2/0 | 4 格外，10 级，props/lamps:post @ (61, 1, -9) |
| 61 | -1 | 5..6 | 2 | 5 | 0/2/0 | 4 格外，10 级，props/lamps:post @ (61, 1, 9) |
| 63 | -2 | -8..-7 | 2 | 4 | 0/2/0 | 5 格外，10 级，props/lamps:post @ (61, 1, -9) |
| 63 | -2 | 7..8 | 2 | 4 | 0/2/0 | 5 格外，10 级，props/lamps:post @ (61, 1, 9) |
| 60 | 1 | -30 | 1 | 6 | 0/1/0 | 4 格外，10 级，props/lamps:post @ (60, 2, -26) |
| 60 | 1 | -22 | 1 | 6 | 0/1/0 | 4 格外，10 级，props/lamps:post @ (60, 2, -18) |
| 60 | 1 | -14 | 1 | 6 | 0/1/0 | 4 格外，10 级，props/lamps:post @ (60, 2, -18) |
| 60 | 1 | 14 | 1 | 6 | 0/1/0 | 4 格外，10 级，props/lamps:post @ (60, 2, 18) |
| 60 | 1 | 22 | 1 | 6 | 0/1/0 | 4 格外，10 级，props/lamps:post @ (60, 2, 18) |
| 60 | 1 | 26 | 1 | 2 | 0/1/0 | 8 格外，10 级，props/lamps:post @ (60, 2, 18) |
| 60 | 1 | 30 | 1 | 0 | 0/1/0 | 12 格外，10 级，props/lamps:post @ (60, 2, 18) |
| 65 | -2 | -9 | 1 | 4 | 0/1/0 | 6 格外，10 级，props/lamps:post @ (61, 1, -9) |
| 65 | -2 | 9 | 1 | 4 | 0/1/0 | 6 格外，10 级，props/lamps:post @ (61, 1, 9) |

## in-A the entrance from the court：暗 14 格，6 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 16..17 | 0 | -1..1 | 5 | 4 | 2/0/3 | 3 格外，9 级，props/ironwork:door_frame @ (17, 4, 0) |
| 28 | 0 | -1..1 | 3 | 3 | 3/0/0 | 7 格外，8 级，props/lamps:uplight @ (33, 0, -2) |
| 17 | 0 | -4..-3 | 2 | 4 | 0/0/2 | 4 格外，8 级，props/lamps:bracket_b @ (15, 2, -5) |
| 17 | 0 | 3..4 | 2 | 4 | 0/0/2 | 4 格外，8 级，props/lamps:bracket_b @ (15, 2, 5) |
| 29 | 0 | -2 | 1 | 4 | 1/0/0 | 5 格外，8 级，props/lamps:uplight @ (33, 0, -2) |
| 29 | 0 | 2 | 1 | 4 | 1/0/0 | 5 格外，8 级，props/lamps:uplight @ (33, 0, 2) |

## in-H the ring stair：暗 10 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 5..7 | 14..17 | -3..3 | 10 | 0 | 0/10/0 | 6 格外，4 级，machines/scope:lamp @ (9, 20, 0) |

## in-I the dome room：暗 8 格，6 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 18 | -13..-12 | 2 | 0 | 2/0/0 | 10 格外，10 级，sky/lights:window west 5 main @ (0, 12, -16) |
| 0 | 18 | 12..13 | 2 | 0 | 2/0/0 | 6 格外，3 级，interiors/domeroom:clock_dial @ (4, 19, 10) |
| 2 | 17 | -16 | 1 | 0 | 0/1/0 | 8 格外，10 级，sky/lights:window west 5 main @ (0, 12, -16) |
| 2 | 17 | 16 | 1 | 0 | 0/1/0 | 9 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 4 | 18 | -13 | 1 | 0 | 1/0/0 | 7 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 4 | 18 | 13 | 1 | 0 | 1/0/0 | 3 格外，3 级，interiors/domeroom:clock_dial @ (4, 19, 10) |

## out-A arrival: the station platform, the walk to the axis：暗 7 格，7 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| 82 | -5 | -42 | 1 | 0 | 0/1/0 | 8 格外，7 级，sky/lights:window station station.west -39 main @ (79, -3, -38) |
| 87 | -5 | -42 | 1 | 4 | 0/1/0 | 8 格外，12 级，props/lamps:bracket_a @ (89, -1, -39) |
| 87 | -3 | -26 | 1 | 4 | 0/1/0 | 9 格外，13 级，props/lamps:street @ (86, -2, -18) |
| 91 | -5 | -42 | 1 | 4 | 0/1/0 | 6 格外，10 级，sky/lights:window station station.east -39 main @ (92, -2, -39) |
| 91 | -5 | -2 | 1 | 0 | 0/1/0 | 14 格外，13 级，props/lamps:street @ (87, -2, -10) |
| 91 | -5 | 2 | 1 | 0 | 0/1/0 | 14 格外，13 级，props/lamps:street @ (87, -2, 10) |
| 91 | -3 | -26 | 1 | 2 | 0/1/0 | 7 格外，9 级，machines/cable:car_windows @ (91, -2, -33) |

## in-C the way to the west door：暗 6 格，1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- |
| -9..-8 | 0 | -1..1 | 6 | 0 | 3/0/3 | 8 格外，10 级，sky/lights:window apse 0 main @ (-9, 9, 0) |

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
| off the routes | 25034 | -69..131 | -29..-8 | -89..96 |
| out-E the west side: the water tower, the sunset terrace | 1211 | -31..-3 | -9..1 | -39..40 |
| out-C the front court: axis, meridian, the foot of the front | 1023 | 18..58 | 0..1 | -33..32 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 875 | 41..101 | -13..-3 | -49..-4 |
| out-F the south side: the south lookout | 807 | -5..60 | -12..1 | 25..61 |
| out-D the north side: the mast pad, the weather station | 769 | -14..58 | -11..2 | -54..-28 |
| out-H the lower platform, south: the way to the works, round the power house | 647 | 51..97 | -13..-4 | 4..49 |
| out-G the terrace's east lip, over the lower platform | 588 | 45..64 | -2..1 | -33..35 |
| out-A arrival: the station platform, the walk to the axis | 308 | 74..95 | -12..-3 | -44..6 |
| in-M the meridian hut | 228 | 27..48 | 0..1 | -37..-17 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 158 | 0..16 | 17..21 | 13..34 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 154 | 0..15 | 17..21 | -34..-13 |
| out-B the axis and the grand stair | 134 | 59..80 | -6..0 | -9..9 |
| in-L the power house, inside | 64 | 66..85 | -6 | 12..23 |
| in-C the way to the west door | 6 | -11 | 0 | -8..8 |
| in-I the dome room | 4 | 0..1 | 17..18 | -16..16 |
| in-A the entrance from the court | 3 | 29 | 0 | -1..1 |

## 起算的点

- spawn：新到 143513 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #66：新到 1292 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #78：新到 95 个落脚点
- in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot #82：新到 1264 个落脚点
