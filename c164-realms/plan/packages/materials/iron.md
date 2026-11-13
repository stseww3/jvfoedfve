# materials/iron

## 目标
方案 6.2 铸铁十二种：用 `redirect_block` 把非蜡 `oxidized_*` 全族改成铸铁；灯件自发光。

## 约束
- 角色：`IRON_PLATE`、`IRON_RIVETED`(+stairs/slab)、`IRON_CAST`、`IRON_GRATE`、`IRON_DOOR`、`IRON_HATCH`、`IRON_BARS`、`IRON_PIPE`、`IRON_ROD`、`IRON_BULB`、`IRON_LANTERN`。
- `mat("iron")`/`iron_dark`/`iron_flat`，色阶 I0–I6；16px；`strays()` 每张过。像素规则见 materials.md §4（铆接板铆钉 8 点贴边连成行；格栅 alpha 透空；门舷窗 brass+glow；灯件 glow+light_emission）。
- 变体覆盖楼梯/台阶/门/灯的各状态。门舷窗发光 M2 定（整扇低亮 vs 窗后 light）。
- 铆接板大面积平铺容易起条纹、发平（c190 预评第 3 条）：铆钉行不许在 8×8 墙上连成贯穿的斜线或等距横条；板面要有够用的明暗（至少用到色阶里相隔 3 级的两色），变体之间铆钉位置一致、只变板面锈迹。8×8 墙和 20 格远看各一张来确认。
- 灯件：`IRON_LANTERN` 本身是 15 级真光源，`IRON_BULB` 点亮只有 4 级（A2 的隐形光源补照明）。画面上的亮靠 `emit`：灯芯那几个像素用 `glow`，`K.redirect(..., emit=lambda ref: 15 if "_lit" in ref else 0)`；铁笼不发光的话把灯芯和铁笼分成两张图不现实（同一个元素），所以整件发光时铁笼的颜色要按“被灯照亮”来画。
- 和 `waxed_oxidized_*`（铜绿）分家：只改非蜡 blockstate（做法 B1 自查）。

## 交付物
- `build/scenes/obs/materials/iron.py`：贴图 + `_kit.paint()` / `_kit.redirect()`；`BLOCKS = K.blocks(B.IRON_PLATE, ...)` 写上真画了的角色（可以一种一种替，没画的继续是占位）。
- 测试场景 `build/scenes/obs_mat_iron/`（零件用 `materials/_board.py`：`twins_plates`、`twins_shapes` 已经是“铸铁 ↔ 铜绿”成对的摆法）：十二种各样例（含楼梯/台阶/门/格栅/灯），旁边并排对应 `waxed_oxidized_*` 铜绿块证明分家；铆接板和平板各一面 8×8 墙；`shots.json`：近看铆钉/缝、灯件发光、分家并排、8×8 墙、20 格远看。

## 验收
- 分家正确（铸铁↔铜绿并排）；每状态显示对；灯件发光；颜色全在色阶；20 格认得出；8×8 墙不起条纹。
- `tools/check.py --scene obs_mat_iron` 全过（`blocks` 里铜绿同胞的警告是有意的）。

## 版本
1 版。

## 依赖
- 依赖：respack-redirect；灯件发光配合 A2。
- 被依赖：main（梁/门/栏杆/平台）、site、machines、props、interiors。

## 记录
- （领卡后填）
