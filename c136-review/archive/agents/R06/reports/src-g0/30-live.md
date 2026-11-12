## 3. 实盘签名与区间（`--mode live`）

### 3.1 做法

断面重演要回答「模拟出来的指令签名像不像当年」，先得知道当年是什么样。`--mode live` 把数据包里每一局有录像的对局原样重放一遍，用和复现臂同一套账本，算出我方席位在 630~1530、1530~3210 两个窗口里真实的指令签名和席位结果。这一步不挂策略、不经通道，只是把录像读成数字。

每一局同时拿策略日志的快照核对重放（同第 2 节）。快照有对不上的局不进区间。

### 3.2 覆盖面

{{T:live-cover}}

<!-- assert: n('live.n') >= 90 -->
<!-- assert: n('live.inBands') >= 70 -->
一共扫了 {{v:live.n}} 局，{{v:live.inBands}} 局进了区间。日志快照有对不上的 {{v:live.badSnap.n}} 局是：{{v:live.badSnap.list}}。早先抽查时，这些局在真引擎重放里同样对不上（记在 `outbox/0018`），问题出在录像或日志本身；这一次没有重新核实，一律不用。

### 3.3 区间

{{T:live-bands}}

读这张表要注意的几点（下面引的都是 630~1530 拍这个窗口各局的中位）：

<!-- assert: n('live.band.vb.clean.630.batchShare') < 15 && n('live.band.c110.clean.630.batchShare') < 15 -->
<!-- assert: Math.min(n('live.band.va.lag.630.batchShare'), n('live.band.vb.lag.630.batchShare'), n('live.band.vc.lag.630.batchShare'), n('live.band.c110.lag.630.batchShare')) >= 50 -->
<!-- assert: n('live.band.vb.clean.630.dumpPerSeat') === 0 && n('live.band.c110.clean.630.dumpPerSeat') === 0 -->
<!-- assert: Math.min(n('live.band.va.lag.630.dumpPerSeat'), n('live.band.vb.lag.630.dumpPerSeat'), n('live.band.vc.lag.630.dumpPerSeat'), n('live.band.c110.lag.630.dumpPerSeat')) >= 0.5 -->
<!-- assert: Math.max(n('live.band.vb.clean.630.atkVoidRate'), n('live.band.c110.clean.630.atkVoidRate')) <= 5 -->
<!-- assert: Math.min(n('live.band.va.lag.630.atkVoidRate'), n('live.band.vb.lag.630.atkVoidRate'), n('live.band.vc.lag.630.atkVoidRate'), n('live.band.c110.lag.630.atkVoidRate')) >= 20 -->
- 「不卡」和「卡顿」两档的签名差得很远，四个版本都是这样。同拍批占比：不卡的局 Vb {{v:live.band.vb.clean.630.batchShare}}、c110 {{v:live.band.c110.clean.630.batchShare}}；卡顿的局 Va {{v:live.band.va.lag.630.batchShare}}、Vb {{v:live.band.vb.lag.630.batchShare}}、Vc {{v:live.band.vc.lag.630.batchShare}}、c110 {{v:live.band.c110.lag.630.batchShare}}。清仓批：不卡的局是 {{v:live.band.vb.clean.630.dumpPerSeat}}，卡顿的局每个席位 {{v:live.band.c110.lag.630.dumpPerSeat}}（c110）到 {{v:live.band.va.lag.630.dumpPerSeat}}（Va）批。陆攻落空率：不卡的局 Vb {{v:live.band.vb.clean.630.atkVoidRate}}、c110 {{v:live.band.c110.clean.630.atkVoidRate}}，卡顿的局 {{v:live.band.vc.lag.630.atkVoidRate}}（Vc）到 {{v:live.band.va.lag.630.atkVoidRate}}（Va）。所以模拟器复现得对不对，必须分档看，不能合在一起报。
<!-- assert: n('live.band.vb.clean.630.gap0') >= 15 && n('live.band.c110.clean.630.gap0') < 10 -->
- 不卡的局里，Vb 的同回合连发占比也有 {{v:live.band.vb.clean.630.gap0}}，c110 只有 {{v:live.band.c110.clean.630.gap0}}。这是策略版本自己的差别，不是通道造成的（已知的一处代码差别：c110 的策略文件在桥接层带一段在途保护，c116 系三版没有）。第 5 节的复现要把这一条也对上。
<!-- assert: n('live.cover.va.clean') === 0 && n('live.cover.vc.inBands') <= 4 -->
- Va 进区间的 {{v:live.cover.va.inBands}} 局里没有不卡的局，Vc 进区间的一共只有 {{v:live.cover.vc.inBands}} 局。这两个版本的区间只能当参考。

区间取的是 P25~P75，只盖住中间一半的局。第 5.6 节用它时，会把真值自己落在区间里的比例一起报出来当参照。
