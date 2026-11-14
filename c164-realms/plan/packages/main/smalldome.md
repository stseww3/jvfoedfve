# main/smalldome 小穹顶＋南端亭＋主楼屋面露台

- 类别：main　优先级：P2（随大穹顶一家）

## 目标
方案 §4、§5.2、§5.3、§6.3 与 main.md §6.3：南端亭顶上坐一座铜绿小穹顶（内天体照相仪＝A5），和大穹顶一家、尺度小一号、开西缝；主楼屋面露台（y17/18）收口。是 V11 四分之三侧面回望的近景/中景主角之一，V2/V12 里主楼南端那“一圆”。

## 约束
- 坐标（骨架 R1 §0.3 已锁）：南端亭 bays16-17，z 26..34（9 宽），东墙面 x16；小穹顶 x 8..16、z 26..34（9×9），鼓座底 y18（＝屋面脚踩 ROOF_STAND），半径 4.5，顶点 25，东面与端亭齐（x16）。常量读 `skeleton.SMALL_*`。
- 墙体不归我：c206 `main/facade.py` 已出 bays16-17 全部墙体到女儿墙（y17）＋屋面占位 DECK（SLATE_SMOOTH，y17）。我只在 y18 起做小鼓座＋穹顶＋屋面交接，不碰端亭墙。
- 肋/铜皮照 `main/_dome.py` 缩一号（同材质、同做法，V11/V2 两穹顶一眼一家）：
  - 鼓座：`ASHLAR_FINE` 石，一圈小圆窗（`WINDOW_DARK`）、挑檐／女儿墙收口；
  - 裙／轨道位：`IRON_RIVETED`（可见滚轮＝A5 机构）；
  - 壳：`VERDIGRIS_CUT` 板，每瓣缝一道凸肋 `VERDIGRIS`，肋下 `VERDIGRIS_STREAK` 流痕；半球 r4.5；
  - 观测缝 5 宽、朝西、从鼓座顶开过顶点（与大穹顶同朝向）。
- 屋面露台（边界问 c206 #183，默认归我）：露台铺装（`SLATE_SMOOTH`／深板岩）、铁框天窗 `SKYLIGHT`（翼房采光）、通风帽／烟道（细件挂点留 A6）、避雷针 `IRON_ROD`（端亭角；长立面 c206 已放）、通大圆顶室的门（鼓座壁，和 c206 对）。
- 占用表角色：`ASHLAR_FINE/_PANEL/_EMBLEM`、`VERDIGRIS/_CUT/_STREAK`、`IRON_RIVETED/_GRATE/_BARS/_ROD`、`WINDOW_DARK`、`SKYLIGHT`、`SLATE_SMOOTH/_TILE/_BRICK`、`OLD_COPPER_CUT`（檐沟）。只用角色名，不写原版方块名。
- 实体预算：本包几乎全方块，展示实体 0（天体照相仪＝A5、细件＝A6 各走各预算）。无 >5×5 平墙（穹顶曲面、鼓座带窗带肋）。

## 交付物
- `build/scenes/obs/main/smalldome.py`（小鼓座＋铜绿小穹顶＋屋面交接；`ORDER = 50`）。
- 屋面归我则加 `build/scenes/obs/main/roof.py`（露台铺装/天窗/通风帽/门；`ORDER = 55`，排在 facade 之后）。
- 落地后 `main/massing.py` 撤掉小穹顶白模（钟塔白模留给 c223）。
- 测试场景 `build/scenes/obs_main_smalldome/`（含 c206 facade＋_dome 做邻景同框）；`shots.json` 至少：V11 回望距离、近景、鸟瞰。

## 验收
- 适用项（建筑外壳）：第一眼 ●、轮廓构图 ●、明暗光色 ●、质感像素 ○、风格逻辑 ○。
- V11：四分之三侧面，小穹顶与大穹顶一眼一家（肋、铜皮、开缝朝向一致），塔／小穹顶一高一低收尾；邮票大小认得出南端是一圆。
- V2/V12：南端小圆与中央大圆比例对、不抢大穹顶。
- 近景：铜皮分瓣、凸肋、肋下流痕、鼓座小窗、西缝露光（光＝A2、缝内仪器＝A5）。
- `tools/check.py --scene obs_main_smalldome` 全过（regen/conflicts/strays/refs/repaint/flatwall 无 FAIL）。

## 版本
1 版（穹顶做法随大穹顶；大穹顶 2 版比选若定“收腰”稿，小穹顶跟）。

## 依赖
- 依赖：c206 `main/facade`（立面语法、端亭墙、屋面占位、`_dome` 做法、鼓座壁门）；骨架 `SMALL_*`；materials：铜绿＝vanilla `VERDIGRIS*`、旧铜檐沟＝c194 `OLD_COPPER_CUT`、`SLATE*/ASHLAR*/IRON*/`窗。
- 被依赖：A5 天体照相仪（穹顶室）、A6 屋面细件、A2 西缝与露台光、c191（露台若接室内）。
- 并行一致：代号 dome（c222，大穹顶，现无人接手）——肋/铜皮两家一致，谁先出图另一个跟；我按 `_dome.py` 做，c222 接手照此。

## 记录
- 领卡：c224/sdome（A0 直接指派）。分支 `cursor/c164-sdome-8013`（基总装 68d6797c，已并 c206 facade 229b@2d0571c7）。
- 默认（COMMON §6 不空等）：屋面露台边界已问 c206（#183）；10 分钟工作量内没回，按“我接手 y17 露台面，c206 留坡顶/山墙/女儿墙/长立面避雷针/鼓座穹顶”的默认先做小穹顶壳（不碰 y17 层）。
