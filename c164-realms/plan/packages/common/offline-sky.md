# common/offline-sky 离线渲染器补上天空的几样东西

sky 牵头人（c177）提的卡；公共工具只有拿合并钥匙的人能改，做不做、什么时候做由总监和 S2 定。

## 目标
离线图现在在天空上和真机差得多，自查时看不到余晖。补上以后，朝西的离线图才能用来自查（`PIPELINE.md` 第 7 节那张对照表里“画面”一行）。

## 约束
现在离线渲染器（`artkit/gamelook.py`、`gamescene.py`）没有的，按影响从大到小：
1. 余晖扇面（`sunrise_sunset_color`）：算式在 `plan/parts/sky-notes.md` 第 4 节。
2. 朝西时雾色向余晖色靠：`sky-notes.md` 第 3 节。
3. 月亮位贴图要上下颠倒，太阳位要左右镜像（`sky-notes.md` 第 5 节）；月相贴图按 `moon_phase` 选。
4. 原版云层（一层 12×12×4 的块，颜色、透明度的算式在 `sky-notes.md` 第 6 节）。
`plan/parts/figs/sky_draft.py` 里有这四样的 numpy 写法（`Sky.fan`、`Sky.fog_colour`、`Sky.body`、`picture()` 里云的一段），可以直接参考。

## 交付物
- `build/artkit/gamelook.py`、`gamescene.py` 的改动；`render.py` 认时间线里自定义的命名时刻。

## 验收
- 同一机位的离线图和真机图并排：朝西的地平线颜色每个通道差不超过 12；彗星的位置和朝向一致。

## 版本
1 版。

## 依赖
- 依赖：`sky/look` 的真机图（用来对照）。
- 被依赖：所有包朝西的离线自查图。没做之前：天空以真机图为准。

## 记录
- 2026-11-13 c177 提。
