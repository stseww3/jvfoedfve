# 路上的光：暗格清单（总装 89943679）

量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。地面低于 5、台阶（脚下是 `_stairs`、`_slab`）和门槛（`facade.doors()`、`shell.doors()`、`S.DOME_ROOM_DOORS` 的格）低于 7 算暗。坐标是格子的整数坐标，y 是脚所在的那一行。

不算暗、另列的三种：露天（正上方到天没有挡光的块；玻璃不挡，整块、台阶、半砖、活板门挡）；檐下（头上有东西，但天光从旁边照进来还有 13 级以上，按游戏的算法每走一格减一级：檐口下贴墙的那一条、水塔底下、敞开的门洞里头两格）；穹顶室（总监 #442）。壳里的房间（`shell.room_at` 认得的）一律只看块光，不管窗子透进多少天光。

- 站得住的格：36776（走得到 8420，要跳一下 28356），其中屋顶下 1661。只能掉下去才到的地方不算（4385 个落脚点）。
- **暗：444 格，57 堆**（地面 357，台阶 68，门槛 19）。
- 不算暗：露天 33213 格，檐下 413 格，穹顶室 292 格。sky/lights 现在放了 203 个光源。
- 比上一版（总装 d7374d32，暗 338 格 52 堆）：还暗着 324 格，新暗 120 格；上一版的暗格里亮了 10 格，现在站不了人的 4 格，改算露天、檐下或穹顶室的 0 格；整堆清掉的 0 堆（见后面）。

## 按归属

归属照 lights（c331）11-16 的分法（#74750）；带 * 的是他没点到、按房间主人填的；「未分」是还没人认的。

| 归谁 | 格数 | 堆数 |
| --- | --- | --- |
| vault* | 115 | 1 |
| lights：路灯 7 盏 | 67 | 8 |
| lights：astro 找位置 | 65 | 3 |
| dome | 50 | 16 |
| m2 | 27 | 3 |
| 未分 | 27 | 9 |
| hall：下一次交付 | 23 | 5 |
| power | 21 | 3 |
| 不补（总监 #58129） | 19 | 1 |
| hall* | 16 | 8 |
| 不补（观测室） | 14 | 2 |

每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、归谁、比上一版（上一版这一堆的格数 → 现在的；还暗着的格算在它现在所在的堆里，亮了的格算在老堆剩得最多的那一堆里）、最近的 sky/lights 光源（走格数、级、它的说明）。

## room: plate vault：暗 115 格（上一版 0 格），1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2..12 | 0..1 | 7..25 | 115 | 0 | 115/0/0 | vault* | 新 | 1 格外，5 级，interiors/platevault:safelight @ (7, 2, 24) |

## room: stair hall：暗 112 格（上一版 122 格），7 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -5..1 | 7..11 | -5..5 | 51 | 0 | 44/7/0 | lights：路灯 7 盏 30 格；lights：astro 找位置 21 格 | 51 → 51（没变） | 3 格外，7 级，props/lamps:cage_a @ (-6, 9, -2) |
| -6..1 | 1..7 | -5..-3 | 22 | 0 | 1/21/0 | lights：astro 找位置 | 22 → 22（没变） | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, -4) |
| -6..1 | 1..7 | 3..5 | 22 | 0 | 1/21/0 | lights：astro 找位置 | 22 → 22（没变） | 2 格外，8 级，interiors/starhall:stair foot @ (1, 4, 4) |
| -1..1 | 0 | -1..1 | 8 | 2 | 8/0/0 | hall：下一次交付 | 18 → 8（少 10） | 3 格外，7 级，interiors/starhall:way west @ (-2, 2, 0) |
| -5..-3 | 0 | -1..1 | 7 | 3 | 7/0/0 | hall：下一次交付 | 7 → 7（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |
| -7 | 0 | -1 | 1 | 4 | 1/0/0 | hall：下一次交付 | 1 → 1（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |
| -7 | 0 | 1 | 1 | 4 | 1/0/0 | hall：下一次交付 | 1 → 1（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |

## room: star hall：暗 62 格（上一版 62 格），14 堆，最暗 1

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12..15 | 0 | -4..4 | 19 | 3 | 19/0/0 | 不补（总监 #58129） | 19 → 19（没变） | 3 格外，7 级，props/lamps:bracket_b @ (13, 2, -5) |
| 2..3 | 0 | -3..3 | 9 | 2 | 9/0/0 | lights：路灯 7 盏 | 9 → 9（没变） | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, -4) |
| 2..3 | 7..8 | 2..5 | 6 | 1 | 6/0/0 | lights：路灯 7 盏 | 6 → 6（没变） | 3 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 5..8 | 7..8 | 4..5 | 6 | 3 | 6/0/0 | hall* 3 格；lights：路灯 7 盏 3 格 | 6 → 6（没变） | 2 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |
| 2..5 | 12..13 | 3 | 4 | 1 | 0/4/0 | lights：路灯 7 盏 | 4 → 4（没变） | 6 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 14..15 | 7..8 | -5..-4 | 4 | 3 | 4/0/0 | hall* | 4 → 4（没变） | 3 格外，6 级，sky/lights:window east 8 main @ (17, 10, -4) |
| 14..15 | 7..8 | 4..5 | 4 | 3 | 4/0/0 | hall* | 4 → 4（没变） | 3 格外，6 级，sky/lights:window east 10 main @ (17, 10, 4) |
| 2..4 | 7..8 | -3 | 3 | 4 | 0/3/0 | lights：路灯 7 盏 | 3 → 3（没变） | 3 格外，8 级，sky/lights:stair @ (5, 9, -4) |
| 2..3 | 7 | -5 | 2 | 3 | 2/0/0 | lights：路灯 7 盏 | 2 → 2（没变） | 3 格外，7 级，props/lamps:cage_a @ (4, 10, -5) |
| 2 | 0 | -5 | 1 | 4 | 1/0/0 | hall* | 1 → 1（没变） | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, -4) |
| 2 | 0 | 5 | 1 | 4 | 1/0/0 | hall* | 1 → 1（没变） | 4 格外，8 级，interiors/starhall:aisle lamp @ (5, 1, 4) |
| 8 | 7 | -5 | 1 | 4 | 1/0/0 | hall* | 1 → 1（没变） | 2 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |
| 9 | 0 | -3 | 1 | 4 | 1/0/0 | hall* | 1 → 1（没变） | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, -5) |
| 9 | 0 | 3 | 1 | 4 | 1/0/0 | hall* | 1 → 1（没变） | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, 5) |

## in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome：暗 31 格（上一版 31 格），8 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12..14 | 18 | 28..32 | 9 | 0 | 9/0/0 | dome | 9 → 9（没变） | 8 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 11..13 | 18 | 8..12 | 7 | 0 | 6/0/1 | dome | 7 → 7（没变） | 7 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 11..13 | 20 | 27 | 3 | 0 | 3/0/0 | dome | 3 → 3（没变） | 6 格外，6 级，main/roof:walk @ (8, 20, 25) |
| 11..13 | 20 | 33 | 3 | 0 | 3/0/0 | dome | 3 → 3（没变） | 11 格外，10 级，sky/lights:window south 4 main @ (14, 12, 34) |
| 14..15 | 18 | 8..9 | 3 | 0 | 3/0/0 | dome | 3 → 3（没变） | 8 格外，6 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 15 | 20 | 29..31 | 3 | 0 | 3/0/0 | dome | 3 → 3（没变） | 11 格外，10 级，sky/lights:window east 17 main @ (16, 12, 32) |
| 8..9 | 20 | 13 | 2 | 3 | 2/0/0 | dome | 2 → 2（没变） | 3 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 14 | 17 | 10 | 1 | 0 | 0/1/0 | dome | 1 → 1（没变） | 9 格外，10 级，sky/lights:window east 12 main @ (15, 12, 12) |

## room: time room：暗 27 格（上一版 27 格），3 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6..13 | 7 | -20..-13 | 24 | 3 | 24/0/0 | m2 | 24 → 24（没变） | 5 格外，7 级，interiors/batteryroom:aisle north @ (8, 3, -17) |
| 10..11 | 7 | -7 | 2 | 4 | 2/0/0 | m2 | 2 → 2（没变） | 4 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |
| 13 | 7 | -7 | 1 | 4 | 1/0/0 | m2 | 1 → 1（没变） | 6 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |

## in-L the power house, inside：暗 21 格（上一版 21 格），3 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 83..87 | -6..-5 | 26..31 | 18 | 2 | 18/0/0 | power | 18 → 18（没变） | 6 格外，10 级，sky/lights:window power power.east 2 furnace @ (89, -2, 27) |
| 69 | -6 | 24..25 | 2 | 4 | 2/0/0 | power | 2 → 2（没变） | 2 格外，6 级，interiors/powerhouse:desk lamp @ (69, -5, 22) |
| 83 | -6 | 22 | 1 | 4 | 1/0/0 | power | 1 → 1（没变） | 6 格外，10 级，sky/lights:window power power.north 4 furnace @ (82, -2, 20) |

## in-M the meridian hut：暗 14 格（上一版 14 格），2 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32 | 0 | -33..-27 | 7 | 0 | 7/0/0 | 不补（观测室） | 7 → 7（没变） | 1 格外，4 级，machines/meridian:lamp @ (32, 2, -30) |
| 38 | 0 | -33..-27 | 7 | 0 | 7/0/0 | 不补（观测室） | 7 → 7（没变） | 4 格外，7 级，props/lamps:cage_a @ (37, 2, -25) |

## in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot：暗 13 格（上一版 13 格），4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11..13 | 18 | -12..-8 | 7 | 0 | 6/0/1 | dome | 7 → 7（没变） | 7 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14..15 | 18 | -9..-8 | 3 | 0 | 3/0/0 | dome | 3 → 3（没变） | 8 格外，6 级，interiors/domeroom:pilot_lamps @ (14, 19, 0) |
| 8..9 | 20 | -13 | 2 | 3 | 2/0/0 | dome | 2 → 2（没变） | 3 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 14 | 17 | -10 | 1 | 0 | 0/1/0 | dome | 1 → 1（没变） | 9 格外，10 级，sky/lights:window east 6 main @ (15, 12, -12) |

## out-E the west side: the water tower, the sunset terrace：暗 11 格（上一版 11 格），1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -19..-16 | -2 | -33..-29 | 11 | 0 | 11/0/0 | 未分 | 11 → 11（没变） | 3 格外，7 级，props/lamps:cage_a @ (-15, 1, -32) |

## in-H the ring stair：暗 10 格（上一版 10 格），1 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5..7 | 14..17 | -3..3 | 10 | 0 | 0/10/0 | lights：路灯 7 盏 | 10 → 10（没变） | 6 格外，4 级，machines/scope:lamp @ (9, 20, 0) |

## in-A the entrance from the court：暗 9 格（上一版 9 格），3 堆，最暗 4

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 16..17 | 0 | -1..1 | 5 | 4 | 2/0/3 | 未分 | 5 → 5（没变） | 3 格外，9 级，props/ironwork:door_frame @ (17, 4, 0) |
| 17 | 0 | -4..-3 | 2 | 4 | 0/0/2 | 未分 | 2 → 2（没变） | 4 格外，8 级，props/lamps:bracket_b @ (15, 2, -5) |
| 17 | 0 | 3..4 | 2 | 4 | 0/0/2 | 未分 | 2 → 2（没变） | 4 格外，8 级，props/lamps:bracket_b @ (15, 2, 5) |

## in-C the way to the west door：暗 6 格（上一版 6 格），1 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -9..-8 | 0 | -1..1 | 6 | 2 | 3/0/3 | hall：下一次交付 | 6 → 6（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |

## in-I the dome room：暗 6 格（上一版 6 格），4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 18 | -13..-12 | 2 | 0 | 2/0/0 | dome | 2 → 2（没变） | 7 格外，5 级，interiors/domeroom:time_dial @ (4, 20, -10) |
| 0 | 18 | 12..13 | 2 | 0 | 2/0/0 | dome | 2 → 2（没变） | 7 格外，5 级，interiors/domeroom:clock_dial @ (4, 20, 10) |
| 4 | 18 | -13 | 1 | 1 | 1/0/0 | dome | 1 → 1（没变） | 4 格外，5 级，interiors/domeroom:time_dial @ (4, 20, -10) |
| 4 | 18 | 13 | 1 | 1 | 1/0/0 | dome | 1 → 1（没变） | 4 格外，5 级，interiors/domeroom:clock_dial @ (4, 20, 10) |

## in-B the star hall, ground floor：暗 3 格（上一版 2 格），3 堆，最暗 4

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7 | 0 | 6 | 1 | 4 | 0/0/1 | 未分 | 新 | 3 格外，6 级，props/lamps:desk_green @ (5, 1, 7) |
| 17 | 0 | -5 | 1 | 6 | 0/0/1 | 未分 | 1 → 1（没变） | 3 格外，8 级，props/lamps:bracket_b @ (15, 2, -5) |
| 17 | 0 | 5 | 1 | 6 | 0/0/1 | 未分 | 1 → 1（没变） | 3 格外，8 级，props/lamps:bracket_b @ (15, 2, 5) |

## in-F the time room (north wing)：暗 2 格（上一版 2 格），1 堆，最暗 5

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7..8 | 7 | -6 | 2 | 5 | 0/0/2 | 未分 | 2 → 2（没变） | 3 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |

## in-G the chart room (south wing)：暗 2 格（上一版 2 格），1 堆，最暗 6

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7..8 | 7 | 6 | 2 | 6 | 0/0/2 | 未分 | 2 → 2（没变） | 3 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |

## 暗的门槛，逐格（19 格）

| x | y | z | 块光 | 哪道门 | 地段 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- |
| -9 | 0 | -1 | 2 | 外墙 apse 面第 0 开间（door） | in-C the way to the west door | hall：下一次交付 |
| -9 | 0 | 0 | 3 | 外墙 apse 面第 0 开间（door） | in-C the way to the west door | hall：下一次交付 |
| -9 | 0 | 1 | 2 | 外墙 apse 面第 0 开间（door） | in-C the way to the west door | hall：下一次交付 |
| 7 | 0 | 6 | 4 | plate vault 的门 | in-B the star hall, ground floor | 未分 |
| 7 | 7 | -6 | 6 | time room 的门 | in-F the time room (north wing) | 未分 |
| 7 | 7 | 6 | 6 | chart room 的门 | in-G the chart room (south wing) | 未分 |
| 8 | 7 | -6 | 5 | time room 的门 | in-F the time room (north wing) | 未分 |
| 8 | 7 | 6 | 6 | chart room 的门 | in-G the chart room (south wing) | 未分 |
| 12 | 18 | -10 | 0 | dome room 的门 | in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | dome |
| 12 | 18 | 10 | 0 | dome room 的门 | in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | dome |
| 17 | 0 | -5 | 6 | 外墙 east 面第 8 开间（gate） | in-B the star hall, ground floor | 未分 |
| 17 | 0 | -4 | 5 | 外墙 east 面第 8 开间（gate） | in-A the entrance from the court | 未分 |
| 17 | 0 | -3 | 4 | 外墙 east 面第 8 开间（gate） | in-A the entrance from the court | 未分 |
| 17 | 0 | -1 | 5 | 外墙 east 面第 9 开间（door） | in-A the entrance from the court | 未分 |
| 17 | 0 | 0 | 6 | 外墙 east 面第 9 开间（door） | in-A the entrance from the court | 未分 |
| 17 | 0 | 1 | 5 | 外墙 east 面第 9 开间（door） | in-A the entrance from the court | 未分 |
| 17 | 0 | 3 | 4 | 外墙 east 面第 10 开间（gate） | in-A the entrance from the court | 未分 |
| 17 | 0 | 4 | 5 | 外墙 east 面第 10 开间（gate） | in-A the entrance from the court | 未分 |
| 17 | 0 | 5 | 6 | 外墙 east 面第 10 开间（gate） | in-B the star hall, ground floor | 未分 |

## 上一版暗、这一版整堆清掉的（0 堆，0 格）

| 地段（上一版的） | x | y | z | 格数 | 那时最暗 | 现在的块光 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- | --- |

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
| off the routes | 25675 | -69..131 | -29..-8 | -89..96 |
| out-E the west side: the water tower, the sunset terrace | 1238 | -31..-3 | -9..1 | -39..40 |
| out-C the front court: axis, meridian, the foot of the front | 1083 | 18..58 | 0..1 | -33..32 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 928 | 41..101 | -13..-3 | -49..-4 |
| out-F the south side: the south lookout | 892 | -5..60 | -12..1 | 25..61 |
| out-D the north side: the mast pad, the weather station | 796 | -14..60 | -11..2 | -54..-28 |
| out-H the lower platform, south: the way to the works, round the power house | 661 | 51..97 | -13..-4 | 4..49 |
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

- spawn：新到 144084 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #66：新到 1292 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #78：新到 95 个落脚点
- in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot #82：新到 1264 个落脚点
