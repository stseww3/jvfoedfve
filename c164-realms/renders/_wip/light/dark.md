# 路上的光：暗格清单（总装 9fbb2e0c）

量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）。地面、台阶、门槛一个线：低于 5 算暗（cr2 #77677；11-16 10:39 以前的几版台阶、门槛按 7）。台阶是脚下是 `_stairs`、`_slab` 的格，门槛是 `facade.doors()`、`shell.doors()`、`S.DOME_ROOM_DOORS` 的格。坐标是格子的整数坐标，y 是脚所在的那一行。

不算进暗的总数、另列的四种：露天（正上方到天没有挡光的块；玻璃不挡，整块、台阶、半砖、活板门挡）；檐下（头上有东西，但天光从旁边照进来还有 13 级以上，按游戏的算法每走一格减一级：檐口下贴墙的那一条、敞开的门洞里头两格）；穹顶室（总监 #442）；定了不补的几处（厅入口 x 12..17、子午仪小屋、水塔底下，见「不补的」一节）。壳里的房间（`shell.room_at` 认得的）一律只看块光，不管窗子透进多少天光。

- 站得住的格：36966（走得到 8609，要跳一下 28357），其中屋顶下 1850。只能掉下去才到的地方不算（4385 个落脚点）。
- **暗：223 格，47 堆**（地面 192，台阶 28，门槛 3）。
- 不算进总数：定了不补的 48 格（8 堆，见后面），露天 32854 格，檐下 372 格，穹顶室 278 格。sky/lights 现在放了 292 个光源。
- 比上一版（总装 0dfcb27a，当时算暗 583 格 60 堆）：照现在的算法是 501 格 48 堆（台阶、门槛里已经够 5 级的 27 格不再算暗，不补的 55 格另列），拿这个数比：还暗着 193 格，新暗 30 格；亮了 280 格，现在站不了人的 28 格，改算露天、檐下的 0 格；整堆清掉的 6 堆（见后面）。

## 怎么自己量

工具不在总装里，在分支 `cursor/c164-sound-lightaudit-f3-cbc6` 的 `c164-realms/tools/darkfloor.py`；不用提交进自己的分支，发任务时现取。在自己的节点、自己的分支上（先把改动推上去）：

```
bash c164-realms/tools/nodejob.sh --wip --always --tail 80 "git fetch -q origin cursor/c164-sound-lightaudit-f3-cbc6 && git show FETCH_HEAD:c164-realms/tools/darkfloor.py > /tmp/darkfloor.py && git show FETCH_HEAD:c164-realms/tools/darkfloor_before.json > /tmp/darkfloor_before.json && python /tmp/darkfloor.py --head <自己的提交号> --before /tmp/darkfloor_before.json --out renders/_wip/light"
```

十几秒一趟。回执里有总数、各归属的格数和每段最大的一堆；整份清单（就是这个文件的样子）推到自己的 `<分支>-wip` 的 `c164-realms/renders/_wip/light/`。「比上一版」比的是 sound 发出去的最近一版，所以自己那几堆少了多少一眼看得到。只量不改：它不动场景里任何东西。

## 按归属

归属照 lights（c331）11-16 的分法（#74750、#75829、#76033、#77817）；房间里没点到的堆归房间主人，新开门的房间一律算路、归主人（cr2 #75753、#76117）；「未分」是还没人认的。

| 归谁 | 格数 | 堆数 |
| --- | --- | --- |
| lights：这一轮（astro 的 6 盏） | 40 | 4 |
| lights：22 盏之后剩的 | 34 | 5 |
| m2 | 27 | 3 |
| tower、clkrm：钟塔底厅 | 25 | 1 |
| dome、lights：屋面 | 20 | 12 |
| power | 20 | 3 |
| m5：西门里 | 19 | 6 |
| dome：小穹顶里 | 18 | 3 |
| hall | 16 | 8 |
| m1：石墩一圈 | 4 | 4 |

每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、归谁、比上一版（上一版这一堆的格数 → 现在的；还暗着的格算在它现在所在的堆里，亮了的格算在老堆剩得最多的那一堆里）、最近的 sky/lights 光源（走格数、级、它的说明）。

## room: stair hall：暗 76 格（上一版 92 格），9 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -5..1 | 7..8 | -5..5 | 38 | 2 | 37/1/0 | lights：22 盏之后剩的 23 格；lights：这一轮（astro 的 6 盏） 15 格 | 50 → 38（少 12） | 3 格外，7 级，sky/lights:way @ (0, 10, -5) |
| -6..-2 | 4..7 | -5..-3 | 12 | 0 | 1/11/0 | lights：这一轮（astro 的 6 盏） | 12 → 12（没变） | 3 格外，7 级，props/lamps:cage_a @ (-6, 9, -2) |
| -6..-2 | 4..7 | 3..5 | 12 | 0 | 1/11/0 | lights：这一轮（astro 的 6 盏） | 12 → 12（没变） | 3 格外，7 级，props/lamps:cage_a @ (-6, 9, 2) |
| -5..-3 | 0 | -1..1 | 7 | 3 | 7/0/0 | m5：西门里 | 7 → 7（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |
| -1..0 | 0 | -1 | 2 | 4 | 2/0/0 | m5：西门里 | 6 → 2（少 4） | 3 格外，7 级，interiors/starhall:way west @ (-2, 2, 0) |
| -1..0 | 0 | 1 | 2 | 4 | 2/0/0 | m5：西门里 | 2 → 2（没变） | 3 格外，7 级，interiors/starhall:way west @ (-2, 2, 0) |
| -7 | 0 | -1 | 1 | 4 | 1/0/0 | m5：西门里 | 1 → 1（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |
| -7 | 0 | 1 | 1 | 4 | 1/0/0 | m5：西门里 | 1 → 1（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |
| 1 | 11 | 3 | 1 | 4 | 0/1/0 | lights：这一轮（astro 的 6 盏） | 1 → 1（没变） | 4 格外，8 级，sky/lights:way @ (4, 12, 2) |

## in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot：暗 32 格（上一版 13 格），5 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11..15 | 18 | -32..-28 | 25 | 0 | 25/0/0 | tower、clkrm：钟塔底厅 | 新 | 3 格外，7 级，sky/lights:way @ (9, 20, -30) |
| 14..15 | 18 | -9..-8 | 3 | 0 | 3/0/0 | dome、lights：屋面 | 3 → 3（没变） | 6 格外，8 级，sky/lights:way @ (12, 20, -11) |
| 8..9 | 20 | -13 | 2 | 3 | 2/0/0 | dome、lights：屋面 | 2 → 2（没变） | 3 格外，6 级，main/roof:walk @ (8, 20, -15) |
| 12 | 18 | -8 | 1 | 4 | 1/0/0 | dome、lights：屋面 | 7 → 1（少 6） | 4 格外，8 级，sky/lights:way @ (12, 20, -11) |
| 14 | 17 | -10 | 1 | 3 | 0/1/0 | dome、lights：屋面 | 1 → 1（没变） | 5 格外，8 级，sky/lights:way @ (12, 20, -11) |

## room: star hall：暗 29 格（上一版 41 格），14 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5..8 | 7..8 | 4..5 | 6 | 3 | 6/0/0 | hall 3 格；lights：22 盏之后剩的 3 格 | 6 → 6（没变） | 2 格外，6 级，props/lamps:cage_a @ (8, 10, 5) |
| 2..3 | 7..8 | 4..5 | 4 | 3 | 4/0/0 | lights：22 盏之后剩的 | 6 → 4（少 2） | 3 格外，7 级，props/lamps:cage_a @ (4, 10, 5) |
| 14..15 | 7..8 | -5..-4 | 4 | 3 | 4/0/0 | hall | 4 → 4（没变） | 3 格外，6 级，sky/lights:window east 8 main @ (17, 10, -4) |
| 14..15 | 7..8 | 4..5 | 4 | 3 | 4/0/0 | hall | 4 → 4（没变） | 3 格外，6 级，sky/lights:window east 10 main @ (17, 10, 4) |
| 2..3 | 7 | -5 | 2 | 3 | 2/0/0 | lights：22 盏之后剩的 | 2 → 2（没变） | 3 格外，7 级，props/lamps:cage_a @ (4, 10, -5) |
| 2 | 0 | -5 | 1 | 4 | 1/0/0 | hall | 1 → 1（没变） | 2 格外，7 级，interiors/batteryroom:west way south @ (2, 1, -7) |
| 2 | 0 | -3 | 1 | 4 | 1/0/0 | m1：石墩一圈 | 6 → 1（少 5） | 4 格外，8 级，sky/lights:way @ (2, 2, 0) |
| 2 | 0 | 3 | 1 | 4 | 1/0/0 | m1：石墩一圈 | 1 → 1（没变） | 4 格外，8 级，sky/lights:way @ (2, 2, 0) |
| 2 | 0 | 5 | 1 | 4 | 1/0/0 | hall | 1 → 1（没变） | 3 格外，7 级，interiors/platevault:lift @ (2, 1, 8) |
| 3 | 0 | -2 | 1 | 4 | 1/0/0 | m1：石墩一圈 | 1 → 1（没变） | 4 格外，8 级，sky/lights:way @ (2, 2, 0) |
| 3 | 0 | 2 | 1 | 4 | 1/0/0 | m1：石墩一圈 | 1 → 1（没变） | 4 格外，8 级，sky/lights:way @ (2, 2, 0) |
| 8 | 7 | -5 | 1 | 4 | 1/0/0 | hall | 1 → 1（没变） | 2 格外，6 级，props/lamps:cage_a @ (8, 10, -5) |
| 9 | 0 | -3 | 1 | 4 | 1/0/0 | hall | 1 → 1（没变） | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, -5) |
| 9 | 0 | 3 | 1 | 4 | 1/0/0 | hall | 1 → 1（没变） | 4 格外，8 级，props/lamps:bracket_b @ (10, 2, 5) |

## room: time room：暗 27 格（上一版 27 格），3 堆，最暗 3

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6..13 | 7 | -20..-13 | 24 | 3 | 24/0/0 | m2 | 24 → 24（没变） | 5 格外，7 级，interiors/batteryroom:aisle north @ (8, 3, -17) |
| 10..11 | 7 | -7 | 2 | 4 | 2/0/0 | m2 | 2 → 2（没变） | 4 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |
| 13 | 7 | -7 | 1 | 4 | 1/0/0 | m2 | 1 → 1（没变） | 6 格外，6 级，props/lamps:cage_a @ (11, 10, -5) |

## in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome：暗 25 格（上一版 31 格），7 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11..14 | 18..20 | 27..31 | 10 | 0 | 10/0/0 | dome：小穹顶里 | 12 → 10（少 2） | 2 格外，5 级，interiors/astroroom:desk lamp @ (13, 18, 31) |
| 11..14 | 19..20 | 32..33 | 5 | 2 | 5/0/0 | dome：小穹顶里 | 3 → 5（多 2） | 3 格外，5 级，interiors/astroroom:desk lamp @ (13, 18, 31) |
| 14..15 | 18 | 8..9 | 3 | 0 | 3/0/0 | dome、lights：屋面 | 3 → 3（没变） | 6 格外，8 级，sky/lights:way @ (12, 20, 11) |
| 15 | 20 | 29..31 | 3 | 0 | 3/0/0 | dome：小穹顶里 | 3 → 3（没变） | 5 格外，5 级，interiors/astroroom:desk lamp @ (13, 18, 31) |
| 8..9 | 20 | 13 | 2 | 3 | 2/0/0 | dome、lights：屋面 | 2 → 2（没变） | 3 格外，6 级，main/roof:walk @ (8, 20, 15) |
| 12 | 18 | 8 | 1 | 4 | 1/0/0 | dome、lights：屋面 | 7 → 1（少 6） | 4 格外，8 级，sky/lights:way @ (12, 20, 11) |
| 14 | 17 | 10 | 1 | 3 | 0/1/0 | dome、lights：屋面 | 1 → 1（没变） | 5 格外，8 级，sky/lights:way @ (12, 20, 11) |

## in-L the power house, inside：暗 20 格（上一版 21 格），3 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 83..87 | -6..-5 | 26..31 | 18 | 2 | 18/0/0 | power | 18 → 18（没变） | 4 格外，12 级，site/powerhouse:fire window @ (90, -5, 27) |
| 69 | -6 | 25 | 1 | 4 | 1/0/0 | power | 2 → 1（少 1） | 3 格外，6 级，interiors/powerhouse:desk lamp @ (69, -5, 22) |
| 83 | -6 | 22 | 1 | 4 | 1/0/0 | power | 1 → 1（没变） | 4 格外，12 级，site/powerhouse:fire window @ (82, -5, 19) |

## in-C the way to the west door：暗 6 格（上一版 6 格），1 堆，最暗 2

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -9..-8 | 0 | -1..1 | 6 | 2 | 3/0/3 | m5：西门里 | 6 → 6（没变） | 3 格外，7 级，interiors/starhall:way west @ (-6, 2, 0) |

## in-I the dome room：暗 6 格（上一版 6 格），4 堆，最暗 0

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 18 | -13..-12 | 2 | 0 | 2/0/0 | dome、lights：屋面 | 2 → 2（没变） | 6 格外，5 级，interiors/domeroom:time_dial @ (3, 20, -10) |
| 0 | 18 | 12..13 | 2 | 0 | 2/0/0 | dome、lights：屋面 | 2 → 2（没变） | 7 格外，5 级，interiors/domeroom:clock_dial @ (4, 20, 10) |
| 4 | 18 | -13 | 1 | 0 | 1/0/0 | dome、lights：屋面 | 1 → 1（没变） | 5 格外，5 级，interiors/domeroom:time_dial @ (3, 20, -10) |
| 4 | 18 | 13 | 1 | 1 | 1/0/0 | dome、lights：屋面 | 1 → 1（没变） | 4 格外，5 级，interiors/domeroom:clock_dial @ (4, 20, 10) |

## in-H the ring stair：暗 2 格（上一版 10 格），1 堆，最暗 4

| x | y | z | 格数 | 最暗 | 地面/台阶/门槛 | 归谁 | 比上一版 | 最近的光源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5..6 | 17 | -3 | 2 | 4 | 0/2/0 | lights：22 盏之后剩的 | 10 → 2（少 8） | 5 格外，8 级，sky/lights:way @ (4, 15, -2) |

## 暗的门槛，逐格（3 格）

| x | y | z | 块光 | 哪道门 | 地段 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- |
| -9 | 0 | -1 | 2 | 外墙 apse 面第 0 开间（door） | in-C the way to the west door | m5：西门里 |
| -9 | 0 | 0 | 3 | 外墙 apse 面第 0 开间（door） | in-C the way to the west door | m5：西门里 |
| -9 | 0 | 1 | 2 | 外墙 apse 面第 0 开间（door） | in-C the way to the west door | m5：西门里 |

## 上一版暗、这一版整堆清掉的（6 堆，259 格）

| 地段（上一版的） | x | y | z | 格数 | 那时最暗 | 现在的块光 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| room: plate vault | 2..12 | 0..1 | 7..25 | 115 | 0 | 5..8 | vault |
| room: battery room | 2..6 | 0 | -25..-7 | 69 | 0 | 5..8 | astro |
| room: battery room | 9..13 | 0 | -25..-7 | 69 | 0 | 5..8 | astro |
| room: star hall | 2..5 | 12..13 | 3 | 4 | 1 | 5..6 | lights：22 盏之后剩的 |
| in-B the star hall, ground floor | 7 | 0 | 6 | 1 | 4 | 7 | m5：各屋门口 |
| room: star hall | 2 | 8 | -3 | 1 | 4 | 5 | lights：22 盏之后剩的 |

## 不补的（不算进暗的总数：48 格，8 堆）

总监 #58129：厅入口（东门洞和门里 x 12..17）门框要比它框住的石墩暗；A0 #22568：山上的小建筑只留门口一盏，水塔已经有了；子午仪小屋是观测室，和穹顶室一样不点灯（穹顶室整间不量，只在上面记格数）。

| 为什么 | 地段 | x | y | z | 格数 | 最暗的块光 |
| --- | --- | --- | --- | --- | --- | --- |
| 不补（A0 #22568：水塔底下） | out-E the west side: the water tower, the sunset terrace | -19..-16 | -2 | -33..-29 | 11 | 0 |
| 不补（总监 #58129：厅入口） | room: star hall | 12..15 | 0 | -4..4 | 19 | 3 |
| 不补（总监 #58129：厅入口） | in-A the entrance from the court | 16 | 0 | -1 | 1 | 4 |
| 不补（总监 #58129：厅入口） | in-A the entrance from the court | 16 | 0 | 1 | 1 | 4 |
| 不补（总监 #58129：厅入口） | in-A the entrance from the court | 17 | 0 | -3 | 1 | 4 |
| 不补（总监 #58129：厅入口） | in-A the entrance from the court | 17 | 0 | 3 | 1 | 4 |
| 不补（观测室：子午仪小屋） | in-M the meridian hut | 32 | 0 | -33..-27 | 7 | 0 |
| 不补（观测室：子午仪小屋） | in-M the meridian hut | 38 | 0 | -33..-27 | 7 | 0 |

## 檐下的（不算暗：天光从旁边照得到；块光不够，要不要补由 lights 看）

| 地段 | x | y | z | 格数 | 最暗的块光 |
| --- | --- | --- | --- | --- | --- |
| out-E the west side: the water tower, the sunset terrace | -9..-2 | 0 | 9..28 | 27 | 0 |
| out-E the west side: the water tower, the sunset terrace | -8..-2 | 0 | -29..-10 | 26 | 0 |
| out-E the west side: the water tower, the sunset terrace | -19..-15 | -2 | -29..-28 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -20..-19 | -2 | -33..-29 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -19..-15 | -2 | -34..-33 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -15..-14 | -2 | -32..-30 | 4 | 4 |
| out-E the west side: the water tower, the sunset terrace | -9 | 0 | -9 | 1 | 0 |
| out-E the west side: the water tower, the sunset terrace | -14 | -2 | -29 | 1 | 4 |
| off the routes | 124..131 | -26..-25 | -46..-43 | 15 | 0 |
| off the routes | 118..121 | -25..-24 | -44..-41 | 10 | 0 |
| off the routes | 112..115 | -22..-19 | -42..-39 | 10 | 0 |
| off the routes | 106..109 | -17..-15 | -40..-37 | 10 | 0 |
| off the routes | 102..103 | -13..-12 | -38..-36 | 4 | 0 |
| off the routes | 130 | -24 | -47 | 1 | 0 |
| off the routes | 102 | -12 | -35 | 1 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 8..16 | 17..18 | 26..34 | 23 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 3..6 | 18..20 | 14..15 | 6 | 0 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 8..10 | 18 | 27..29 | 5 | 2 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 14..15 | 17..18 | 11..12 | 3 | 4 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 9..10 | 20 | 14 | 2 | 3 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 10..11 | 19..20 | 28 | 2 | 4 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 13 | 18 | 30 | 1 | 4 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 12 | 18 | 29 | 1 | 4 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..16 | 17..18 | -34..-32 | 10 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..16 | 18..20 | -26 | 8 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 3..6 | 18..20 | -15..-14 | 6 | 0 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 14..15 | 17..18 | -12..-11 | 3 | 4 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..10 | 20 | -14 | 2 | 3 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9 | 18 | -28..-27 | 2 | 3 |
| out-F the south side: the south lookout | -2..18 | 0 | 29..36 | 31 | 0 |
| out-C the front court: axis, meridian, the foot of the front | 17..18 | 0 | -32..-19 | 15 | 0 |
| out-C the front court: axis, meridian, the foot of the front | 17..18 | 0 | 19..32 | 15 | 0 |
| in-M the meridian hut | 33..34 | 0 | -33..-27 | 13 | 0 |
| in-M the meridian hut | 36..37 | 0 | -33..-27 | 13 | 0 |
| in-C the way to the west door | -11..-9 | 0 | -8..8 | 24 | 0 |
| in-C the way to the west door | -8 | 0 | -9 | 1 | 0 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 93..97 | -9..-8 | -36..-32 | 14 | 0 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 100..101 | -11 | -37..-35 | 5 | 0 |
| out-D the north side: the mast pad, the weather station | 10..18 | 0 | -36..-33 | 12 | 0 |
| out-D the north side: the mast pad, the weather station | -2 | 0 | -34..-30 | 5 | 2 |
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
| out-E the west side: the water tower, the sunset terrace | 1169 | -31..-3 | -9..1 | -39..40 |
| out-C the front court: axis, meridian, the foot of the front | 1075 | 18..58 | 0 | -33..32 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 923 | 41..101 | -13..-3 | -49..-4 |
| out-F the south side: the south lookout | 800 | -5..60 | -12..1 | 25..61 |
| out-D the north side: the mast pad, the weather station | 719 | -14..60 | -11..2 | -54..-28 |
| out-H the lower platform, south: the way to the works, round the power house | 614 | 51..97 | -13..-5 | 4..49 |
| out-G the terrace's east lip, over the lower platform | 598 | 45..65 | -2..1 | -33..35 |
| out-A arrival: the station platform, the walk to the axis | 314 | 74..95 | -12..-3 | -44..6 |
| in-M the meridian hut | 243 | 27..48 | 0..1 | -37..-17 |
| out-B the axis and the grand stair | 228 | 59..80 | -6..0 | -9..9 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 219 | 0..16 | 17..21 | 14..34 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 217 | 0..15 | 17..21 | -34..-14 |
| in-L the power house, inside | 40 | 66..77 | -6 | 12..23 |
| in-A the entrance from the court | 8 | 28..29 | 0 | -2..2 |
| in-C the way to the west door | 6 | -11 | 0 | -8..8 |
| in-I the dome room | 6 | 0..2 | 17..18 | -16..16 |

## 起算的点

- spawn：新到 144593 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #66：新到 1292 个落脚点
- in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome #78：新到 107 个落脚点
- in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot #82：新到 1346 个落脚点
