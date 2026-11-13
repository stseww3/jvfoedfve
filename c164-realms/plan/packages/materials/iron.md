# materials/iron

## 目标
方案 6.2 铸铁十二种：用 `redirect_block` 把非蜡 `oxidized_*` 全族改成铸铁；灯件自发光。

## 约束
- 角色：`IRON_PLATE`、`IRON_RIVETED`(+stairs/slab)、`IRON_CAST`、`IRON_GRATE`、`IRON_DOOR`、`IRON_HATCH`、`IRON_BARS`、`IRON_PIPE`、`IRON_ROD`、`IRON_BULB`、`IRON_LANTERN`。
- `mat("iron")`/`iron_dark`/`iron_flat`，色阶 I0–I6；16px；`strays()` 每张过。像素规则见 materials.md §4（铆接板铆钉 8 点贴边连成行；格栅 alpha 透空；门舷窗 brass+glow；灯件 glow+light_emission）。
- 变体覆盖楼梯/台阶/门/灯的各状态。门舷窗发光 M2 定（整扇低亮 vs 窗后 light）。
- 和 `waxed_oxidized_*`（铜绿）分家：只改非蜡 blockstate（做法 B1 自查）。

## 交付物
- `build/scenes/obs/materials/iron.py`：贴图 + `redirect_block`。
- 测试场景 `build/scenes/obs_mat_iron/`：十二种各样例（含楼梯/台阶/门/格栅/灯），旁边并排对应 `waxed_oxidized_*` 铜绿块证明分家；`shots.json`：近看铆钉/缝、灯件发光、分家并排、20 格远看。

## 验收
- 分家正确（铸铁↔铜绿并排）；每状态显示对；灯件发光；颜色全在色阶；20 格认得出。

## 版本
1 版。

## 依赖
- 依赖：respack-redirect；灯件发光配合 A2。
- 被依赖：main（梁/门/栏杆/平台）、site、machines、props、interiors。

## 记录
- （领卡后填）
