# 路上的光：暗格清单（总装 99d62c96）

量法：`tools/walkreach.py` 算人走得到的地方（从出生点起；再加两条走查路线上出生点走不到的点），`sky/_lightkit.levels` 算块光，取脚格和头格里亮的那个（同 `obs_sky_lights/ways.py`）；灯具包当成挡光、其实人站得进去的格（游戏的梯子之类，这一版 866 格）照游戏的算法取旁边最亮的格减一。地面、台阶、门槛一个线：低于 5 算暗（cr2 #77677；11-16 10:39 以前的几版台阶、门槛按 7）。台阶是脚下是 `_stairs`、`_slab` 的格，门槛是 `facade.doors()`、`shell.doors()`、`S.DOME_ROOM_DOORS` 的格。坐标是格子的整数坐标，y 是脚所在的那一行。

不算进暗的总数、另列的四种：露天（正上方到天没有挡光的块；玻璃不挡，整块、台阶、半砖、活板门挡）；檐下（头上有东西，但天光从旁边照进来还有 13 级以上，按游戏的算法每走一格减一级：檐口下贴墙的那一条、敞开的门洞里头两格）；穹顶室（总监 #442）；定了不补的几处（厅入口 x 12..17、子午仪小屋、水塔底下，见「不补的」一节）。壳里的房间（`shell.room_at` 认得的）一律只看块光，不管窗子透进多少天光。

- 站得住的格：36849（走得到 8476，要跳一下 28373），其中屋顶下 1854。只能掉下去才到的地方不算（2805 个落脚点）。
- **暗：0 格，0 堆**（地面 0，台阶 0，门槛 0）。
- 不算进总数：定了不补的 27 格（5 堆，见后面），栏杆、屏障、玻璃板顶上的 0 格（栏杆、屏障、玻璃板的顶不算路，cr2 11:26 定；逐格见后面），露天 32688 格，檐下 324 格，穹顶室 278 格。sky/lights 现在放了 350 个光源。
- 比上一版（总装 8d51207d，当时算暗 2 格 2 堆）：还暗着 0 格，新暗 0 格；亮了 2 格，现在站不了人的 0 格，改成另列的（露天、檐下、栏杆顶）0 格；整堆清掉的 2 堆（见后面）。

## 怎么自己量

工具不在总装里，在分支 `cursor/c164-sound-lightaudit-f3-cbc6` 的 `c164-realms/tools/darkfloor.py`；不用提交进自己的分支，发任务时现取。在自己的节点、自己的分支上（先把改动推上去）：

```
bash c164-realms/tools/nodejob.sh --wip --always --tail 80 "git fetch -q origin cursor/c164-sound-lightaudit-f3-cbc6 && git show FETCH_HEAD:c164-realms/tools/darkfloor.py > /tmp/darkfloor.py && git show FETCH_HEAD:c164-realms/tools/darkfloor_before.json > /tmp/darkfloor_before.json && python /tmp/darkfloor.py --head auto --before /tmp/darkfloor_before.json --out renders/_wip/light"
```

十几秒一趟。回执里有总数、各归属的格数和每段最大的一堆；整份清单（就是这个文件的样子）推到自己的 `<分支>-wip` 的 `c164-realms/renders/_wip/light/`。「比上一版」比的是 sound 发出去的最近一版，所以自己那几堆少了多少一眼看得到。只量不改：它不动场景里任何东西。

## 按归属

归属照 lights（c331）11-16 的分法（#74750、#75829、#76033、#77817）；房间里没点到的堆归房间主人，新开门的房间一律算路、归主人（cr2 #75753、#76117）；「未分」是还没人认的。

| 归谁 | 格数 | 堆数 |
| --- | --- | --- |

每堆一行：范围（x，y，z）、格数、最暗的块光、地面/台阶/门槛各几格、归谁、比上一版（上一版这一堆的格数 → 现在的；还暗着的格算在它现在所在的堆里，亮了的格算在老堆剩得最多的那一堆里）、最近的 sky/lights 光源（走格数、级、它的说明）。

## 暗的门槛，逐格（0 格）

| x | y | z | 块光 | 哪道门 | 地段 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- |

## 上一版暗、这一版整堆清掉的（2 堆，2 格）

| 地段（上一版的） | x | y | z | 格数 | 那时最暗 | 现在的块光 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome | 14 | 17 | 10 | 1 | 4 | 5 | dome、lights：屋面 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 14 | 17 | -10 | 1 | 4 | 5 | dome、lights：屋面 |

## 不补的（不算进暗的总数：27 格，5 堆）

总监 #58129：厅入口（东门洞和门里 x 12..17）门框要比它框住的石墩暗；A0 #22568：山上的小建筑只留门口一盏，水塔已经有了；子午仪小屋是观测室，和穹顶室一样不点灯（穹顶室整间不量，只在上面记格数）。

| 为什么 | 地段 | x | y | z | 格数 | 最暗的块光 |
| --- | --- | --- | --- | --- | --- | --- |
| 不补（A0 #22568：水塔底下） | out-E the west side: the water tower, the sunset terrace | -19..-16 | -2 | -33..-29 | 11 | 0 |
| 不补（总监 #58129：厅入口） | in-B the star hall, ground floor | 17 | 0 | -3 | 1 | 4 |
| 不补（总监 #58129：厅入口） | in-B the star hall, ground floor | 17 | 0 | 3 | 1 | 4 |
| 不补（观测室：子午仪小屋） | in-M the meridian hut | 32 | 0 | -33..-27 | 7 | 0 |
| 不补（观测室：子午仪小屋） | in-M the meridian hut | 38 | 0 | -33..-27 | 7 | 0 |

## 栏杆、屏障、玻璃板的顶（不算路，cr2 11:26 定；0 格，不进总数）

跳一下站得上去，可不是人走的路：脚下是栏杆（`_bars`）、屏障块（`barrier`）、玻璃板（`_pane`）的暗格，逐格。

| x | y | z | 块光 | 脚下的块 | 地段 | 本来归谁 |
| --- | --- | --- | --- | --- | --- | --- |

## 暗格里要跳一下才站得上的（0 格，算在上面的总数里）

走不上去、跳一格才站得上的地方，脚下是整块的：一级没有台阶块的坎，也可能是箱子、机座、台面的顶。照算（cr2 11:26）；脚下是什么块列在这里。

| 地段 | x | y | z | 跳的格数 / 全堆 | 脚下的块 | 归谁 |
| --- | --- | --- | --- | --- | --- | --- |

## 檐下的（不算暗：天光从旁边照得到；块光不够，要不要补由 lights 看）

| 地段 | x | y | z | 格数 | 最暗的块光 |
| --- | --- | --- | --- | --- | --- |
| out-E the west side: the water tower, the sunset terrace | -8..-2 | 0 | -29..-10 | 26 | 0 |
| out-E the west side: the water tower, the sunset terrace | -9..-2 | 0 | 9..15 | 14 | 0 |
| out-E the west side: the water tower, the sunset terrace | -20..-19 | -2 | -33..-29 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -19..-15 | -2 | -34..-33 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -19..-15 | -2 | -29..-28 | 7 | 0 |
| out-E the west side: the water tower, the sunset terrace | -15..-14 | -2 | -32..-30 | 4 | 4 |
| out-E the west side: the water tower, the sunset terrace | -2 | 0 | 26..28 | 3 | 0 |
| out-E the west side: the water tower, the sunset terrace | -14 | -2 | -29 | 1 | 4 |
| out-E the west side: the water tower, the sunset terrace | -9 | 0 | -9 | 1 | 0 |
| off the routes | 124..131 | -26..-25 | -46..-43 | 15 | 0 |
| off the routes | 118..121 | -25..-24 | -44..-41 | 10 | 0 |
| off the routes | 112..115 | -22..-19 | -42..-39 | 10 | 0 |
| off the routes | 106..109 | -17..-15 | -40..-37 | 10 | 0 |
| off the routes | 102..103 | -13..-12 | -38..-36 | 4 | 0 |
| off the routes | 130 | -24 | -47 | 1 | 0 |
| off the routes | 102 | -12 | -35 | 1 | 0 |
| out-F the south side: the south lookout | -2..18 | 0 | 29..36 | 31 | 0 |
| in-M the meridian hut | 33..34 | 0 | -33..-27 | 13 | 0 |
| in-M the meridian hut | 36..37 | 0 | -33..-27 | 13 | 0 |
| out-C the front court: axis, meridian, the foot of the front | 17..18 | 0 | -32..-20 | 14 | 0 |
| out-C the front court: axis, meridian, the foot of the front | 17..18 | 0 | 23..32 | 11 | 0 |
| in-C the way to the west door | -11..-9 | 0 | -8..8 | 23 | 0 |
| in-C the way to the west door | -8 | 0 | -9 | 1 | 0 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 93..97 | -9..-8 | -36..-32 | 14 | 0 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 100..101 | -11 | -37..-35 | 5 | 0 |
| out-D the north side: the mast pad, the weather station | 10..18 | 0 | -36..-33 | 12 | 0 |
| out-D the north side: the mast pad, the weather station | -2 | 0 | -34..-30 | 5 | 2 |
| in-N the plate vault and its darkroom (south wing, ground floor) | -2 | 0 | 16..25 | 10 | 0 |
| in-N the plate vault and its darkroom (south wing, ground floor) | 17 | 0 | 19..22 | 4 | 1 |
| in-R the astrograph room (the small dome) | 13..15 | 17..18 | 26..28 | 5 | 1 |
| in-R the astrograph room (the small dome) | 9..10 | 18 | 27..28 | 3 | 2 |
| in-R the astrograph room (the small dome) | 9..10 | 17..18 | 32..33 | 3 | 1 |
| in-R the astrograph room (the small dome) | 10..11 | 18 | 29 | 2 | 3 |
| in-R the astrograph room (the small dome) | 10 | 18 | 31 | 1 | 4 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..11 | 19..20 | -26 | 3 | 2 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 5..6 | 19..20 | -15..-14 | 3 | 4 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9..10 | 20 | -14 | 2 | 4 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9 | 18 | -28..-27 | 2 | 3 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 9 | 18 | -32 | 1 | 4 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome's door | 8 | 18 | 28..32 | 5 | 1 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome's door | 5..6 | 19..20 | 14..15 | 3 | 4 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome's door | 9..10 | 20 | 14 | 2 | 4 |
| in-Q the clock tower: the lobby, the ladder, the clock room | 12..14 | 18..19 | -26 | 3 | 0 |
| in-Q the clock tower: the lobby, the ladder, the clock room | 9 | 17 | -33 | 1 | 2 |
| out-A arrival: the station platform, the walk to the axis | 90 | -4 | -30 | 1 | 4 |
| out-A arrival: the station platform, the walk to the axis | 88 | -4 | -30 | 1 | 4 |
| out-A arrival: the station platform, the walk to the axis | 83 | -4 | -37 | 1 | 0 |
| out-H the lower platform, south: the way to the works, round the power house | 63..64 | -6 | 33 | 2 | 0 |
| out-H the lower platform, south: the way to the works, round the power house | 61 | -6 | 33 | 1 | 0 |
| in-L the power house, inside | 66 | -6 | 33 | 1 | 0 |
| in-P the battery room (north wing, ground floor) | 17 | 0 | -19 | 1 | 4 |

## 露天的（不算暗）

| 地段 | 格数 | x | y | z |
| --- | --- | --- | --- | --- |
| off the routes | 25675 | -69..131 | -29..-8 | -89..96 |
| out-E the west side: the water tower, the sunset terrace | 1164 | -31..-3 | -9..1 | -39..40 |
| out-C the front court: axis, meridian, the foot of the front | 1058 | 18..58 | 0 | -33..32 |
| out-I the lower platform, north: its edges, the wall's foot, back to the station | 923 | 41..101 | -13..-3 | -49..-4 |
| out-F the south side: the south lookout | 720 | -5..60 | -12..1 | 25..61 |
| out-D the north side: the mast pad, the weather station | 719 | -14..60 | -11..2 | -54..-28 |
| out-H the lower platform, south: the way to the works, round the power house | 611 | 51..97 | -13..-5 | 4..49 |
| out-G the terrace's east lip, over the lower platform | 598 | 45..65 | -2..1 | -33..35 |
| out-A arrival: the station platform, the walk to the axis | 312 | 74..95 | -12..-3 | -44..6 |
| in-M the meridian hut | 244 | 27..48 | 0..1 | -37..-17 |
| out-B the axis and the grand stair | 228 | 59..80 | -6..0 | -9..9 |
| in-K the north roofs: corner terrace, ridge walk, the end terrace, the clock tower's foot | 172 | 1..14 | 17..21 | -33..-15 |
| in-J the south roofs: corner terrace, ridge walk, the end terrace, the small dome's door | 167 | 1..14 | 17..21 | 15..33 |
| in-L the power house, inside | 43 | 66..77 | -6 | 12..40 |
| in-R the astrograph room (the small dome) | 16 | 8..14 | 17..18 | 23..33 |
| in-N the plate vault and its darkroom (south wing, ground floor) | 15 | -3..20 | 0 | 17..23 |
| in-Q the clock tower: the lobby, the ladder, the clock room | 11 | 11..14 | 17..18 | -25..-23 |
| in-C the way to the west door | 6 | -11 | 0 | -8..8 |
| in-A the entrance from the court | 4 | 28..29 | 0 | -1..1 |
| in-I the dome room | 2 | 2 | 17 | -16..16 |

## 起算的点

- spawn：新到 146585 个落脚点
- in-Q the clock tower: the lobby, the ladder, the clock room #102：新到 62 个落脚点
