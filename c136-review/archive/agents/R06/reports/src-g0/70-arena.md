## 7. 闭环对手模型的标定和已知边界

### 7.1 做法

前面几节里，其余真人都是照录像出手的。闭环模式把他们全部换成对手模型（`sim-v2/lib/opponents.mjs`）：

- 每个真人按 20 局真局统计出来的画像出手：各阶段每 100 拍几条指令，打无主地 / 内置 AI / 真人 / 发船各占多少，每条用掉余额的千分之几，人与人之间差多少。画像存在 `sim-v2/calib/human-profile.json`，由 `tools/human_profile.mjs` 从录像统计。
- 在这之上有六类原型打法（攒兵补刀、整仓喂大号、固定档连压、梭哈、跨海登陆、同战队抱团集火）和被打之后的还手，参数取自会审提案 §1.3 的实测画像。
- 真局里整局没下过指令的席位，模型里也挂机；真局里活着离场的席位，模型里在同一拍离场。
- 对手的指令即时生效，不走我方那条通道。

标定用任务卡说的核心 20 局：取真局的房间（地图、出生点、队伍、内置 AI），从第 0 拍起闭环跑到 4300 拍。我方挂这一局当年那一版策略，走这一局的实录阶梯（C2），各席位页面的寿命照当年。然后在几个时刻把模型里的世界和同一局录像里的世界并排比。

要说明的是：这是一项**统计上**的检验。对手模型不认识具体的人，闭环里每一局的走向和录像不会相同；要看的是各局的中位和分布对不对。

### 7.2 各时刻的世界

{{T:arena-cps}}

<!-- assert: n('arena.n') === 20 && n('arena.trunc') === 0 -->
<!-- assert: Math.abs(n('arena-cps.357.oLand') - 1) <= 0.05 && Math.abs(n('arena-cps.357.sLand') - 1) <= 0.05 -->
<!-- assert: Math.abs(n('arena-cps.630.oLand') - 1) <= 0.10 && Math.abs(n('arena-cps.630.sLand') - 1) <= 0.05 -->
<!-- assert: Math.abs(n('arena-cps.1071.oLand') - 1) <= 0.12 && Math.abs(n('arena-cps.1071.sLand') - 1) <= 0.08 -->
<!-- assert: n('arena-cps.1530.sLand') >= 1.08 && n('arena-cps.3210.sLand') >= 1.3 && n('arena-cps.4284.sLand') >= 1.5 -->
<!-- assert: n('arena-cps.3210.oLand') <= 0.85 && n('arena-cps.4284.oLand') <= 0.8 -->
<!-- assert: ['357', '630'].every((t) => Math.abs(n(`arena-cps.${t}.oDens`) - 1) <= 0.08 && Math.abs(n(`arena-cps.${t}.sDens`) - 1) <= 0.08 && n(`arena-cps.${t}.oAlive`) === 0 && n(`arena-cps.${t}.ai`) === 0 && Math.abs(n(`arena-cps.${t}.rel`) - 1) <= 0.08) -->
<!-- assert: n('arena-cps.1071.rel') >= 1.08 && n('arena-cps.1071.rel') <= 1.15 && Math.abs(n('arena-cps.1071.oDens') - 1) <= 0.05 && Math.abs(n('arena-cps.1071.sDens') - 1) <= 0.05 && n('arena-cps.1071.ai') <= 3 -->
<!-- assert: n('arena-cps.357.oDens') <= Math.min(n('arena-cps.357.sDens'), n('arena-cps.630.oDens')) && n('arena-cps.630.sDens') >= Math.max(n('arena-cps.357.sDens'), n('arena-cps.630.oDens')) -->
- **到 630 拍对得上。** 其余真人的人均地，模型 ÷ 录像的中位：357 拍 {{v:arena-cps.357.oLand}}，630 拍 {{v:arena-cps.630.oLand}}；我方人均地：{{v:arena-cps.357.sLand}}、{{v:arena-cps.630.sLand}}。两边的兵密度在 {{v:arena-cps.357.oDens}}~{{v:arena-cps.630.sDens}} 之间，其余真人在场占比、内置 AI 占的陆地和录像没有差。
- **1071 拍，绝对量还对得上，相对量开始偏。** 其余真人的人均地 {{v:arena-cps.1071.oLand}}，我方人均地 {{v:arena-cps.1071.sLand}}，两边兵密度都是 {{v:arena-cps.1071.oDens}}。但这两个小偏差方向相反，叠起来，我方人均地 ÷ 其余真人人均地的中位已经是录像的 {{v:arena-cps.1071.rel}} 倍（630 拍是 {{v:arena-cps.630.rel}}）。内置 AI 占的陆地与录像的差是 {{v:arena-cps.1071.ai}} 个百分点（模型里多）：模型里的对手吃内置 AI 比真人慢一点。
<!-- assert: n('arena-cps.1530.rel') >= 1.15 && n('arena-cps.2142.rel') > n('arena-cps.1530.rel') && n('arena-cps.3210.rel') > n('arena-cps.2142.rel') && n('arena-cps.4284.rel') > n('arena-cps.3210.rel') -->
- **1530 拍以后一路偏离。** 我方人均地 模型 ÷ 录像：1530 拍 {{v:arena-cps.1530.sLand}}，2142 拍 {{v:arena-cps.2142.sLand}}，3210 拍 {{v:arena-cps.3210.sLand}}，4284 拍 {{v:arena-cps.4284.sLand}}；其余真人人均地同时走低：{{v:arena-cps.1530.oLand}}、{{v:arena-cps.2142.oLand}}、{{v:arena-cps.3210.oLand}}、{{v:arena-cps.4284.oLand}}。相对量从 {{v:arena-cps.1530.rel}} 倍涨到 {{v:arena-cps.4284.rel}} 倍。也就是说，闭环里的对手在中后期比真人弱，我方在闭环里的中后期成绩比当年的实际成绩好得多。

### 7.3 对手的出手强度

{{T:arena-intensity}}

<!-- assert: Math.abs(n('arena.int.0.cmd') - 1) <= 0.2 && Math.abs(n('arena.int.490.cmd') - 1) <= 0.1 && Math.abs(n('arena.int.630.cmd') - 1) <= 0.1 -->
<!-- assert: n('arena.int.3210.hum') <= 0.7 && n('arena.int.3210.bal') <= 0.75 -->
<!-- assert: ['105', '231', '357', '490', '630', '850'].every((k) => Math.abs(n(`arena.int.${k}.cmd`) - 1) <= 0.065) && ['0', '1071', '1300', '1530', '2142', '3210'].every((k) => Math.abs(n(`arena.int.${k}.cmd`) - 1) <= 0.16) -->
- 出手的密度和对象构成，模型逐阶段贴着录像（这是按画像生成的，贴得上是应该的）。每人每 100 拍生效指令 模型 ÷ 录像：105 拍到 1071 拍的六个阶段都在 1 ± 0.06 以内（490~630 拍 {{v:arena.int.490.cmd}}，630~850 拍 {{v:arena.int.630.cmd}}）；偏得最多的是开头 0~105 拍（{{v:arena.int.0.cmd}}）、1071~1300 拍（{{v:arena.int.1071.cmd}}）和最后 3210~4284 拍（{{v:arena.int.3210.cmd}}）。
<!-- assert: n('arena.int.630.bal') >= 0.9 && n('arena.int.1071.bal') < n('arena.int.630.bal') && n('arena.int.1300.bal') < n('arena.int.1071.bal') && n('arena.int.1530.bal') <= 0.7 && n('arena.int.2142.bal') < n('arena.int.1530.bal') && n('arena.int.3210.bal') < n('arena.int.2142.bal') -->
<!-- assert: n('arena.int.3210.hum') <= 0.5 && n('arena.int.1530.spend') >= 1.5 && ['0', '105', '231', '357', '490', '630', '850', '1071', '1300', '3210'].every((k) => Math.abs(n(`arena.int.${k}.spend`) - 1) <= 0.12) && n('arena.int.2142.spend') <= 1.35 -->
- 对不上的是**兵**。模型里其余真人的人均余额从 630 拍起一点点低于录像（630~850 拍 {{v:arena.int.630.bal}}，1071~1300 拍 {{v:arena.int.1071.bal}}，1300~1530 拍 {{v:arena.int.1300.bal}}），1530 拍以后掉得快（{{v:arena.int.1530.bal}}、{{v:arena.int.2142.bal}}、{{v:arena.int.3210.bal}}）。余额低了，差不多的条数出的兵就少：3210~4284 拍打真人出的兵，模型是录像的 {{v:arena.int.3210.hum}} 倍（{{v:arena.int.3210.humSent}}）。
- 还有一处对不上：1530~2142 拍，模型里其余真人每 100 拍花掉的余额占比是录像的 {{v:arena.int.1530.spend}} 倍，2142~3210 拍 {{v:arena.int.2142.spend}} 倍；别的阶段这个比都在 1 ± 0.12 以内。余额变低和花得更快，哪个是因、哪个是果，这里没有分开。

人与人之间的差别，到各时刻为止每人下过几条有兵的陆攻（这一项只统计到 1071 拍）：

{{T:arena-people}}

<!-- assert: ['105', '231', '357', '630', '1071'].every((t) => Math.abs(n(`arena.people.${t}.mean`) - 1) <= 0.12 && n(`arena.people.${t}.qmax`) <= 2) -->
每个时刻，模型的均值和实测相差不超过 12%，五个分位各自相差不超过 2 条。

其余真人的地在人与人之间怎么分布（以同一局录像的中位数为 1）：

{{T:arena-dist}}

<!-- assert: ['10', '25', '50', '75', '90'].every((k) => Math.abs(n(`arena.dist.1071.m${k}`) - n(`arena.dist.1071.r${k}`)) <= 0.25) -->
<!-- assert: n('arena.dist.3210.m10') <= 0.1 && n('arena.dist.3210.r10') >= 0.25 && n('arena.dist.3210.m25') <= n('arena.dist.3210.r25') - 0.2 && n('arena.dist.3210.m50') <= 0.8 -->
<!-- assert: Math.abs(n('arena.dist.3210.m90') - n('arena.dist.3210.r90')) <= 0.25 -->
到 1071 拍，模型的 P10 到 P90 各分位和录像相差都不超过 0.25。之后是下半截塌了：3210 拍，模型的 P10 / P25 / 中位是 {{v:arena.dist.3210.m10}} / {{v:arena.dist.3210.m25}} / {{v:arena.dist.3210.m50}}，录像是 {{v:arena.dist.3210.r10}} / {{v:arena.dist.3210.r25}} / {{v:arena.dist.3210.r50}}；P90 两边差不多（{{v:arena.dist.3210.m90}} 对 {{v:arena.dist.3210.r90}}）。也就是说，模型里靠前的人和真局差不多大，中下游的人比真局丢地丢得快。

### 7.4 我方这一侧

{{T:arena-squad}}

<!-- assert: Math.abs(n('arena.sq.0.aiSentR') - 1) <= 0.25 -->
<!-- assert: n('arena.sq.1071.aiSentR') >= 1.3 -->
<!-- assert: n('arena.sq.1530.humSentR') >= 1.1 && n('arena.sq.2142.humSentR') >= 1.2 && n('arena.sq.3210.humSentR') >= 1.3 && Math.abs(n('arena.sq.630.aiSentR') - 1) <= 0.1 -->
我方在闭环里和在录像里出手的对比（同一版策略、同一条通道）：1071 拍之前打无主地、打内置 AI 的条数和出兵都接近（打内置 AI 的出兵，0~630 拍是录像的 {{v:arena.sq.0.aiSentR}} 倍，630~1071 拍 {{v:arena.sq.630.aiSentR}} 倍）；1071 拍起，闭环里我方打内置 AI 的出兵明显多于录像（1071~1530 拍是录像的 {{v:arena.sq.1071.aiSentR}} 倍），1530 拍起打真人的出兵也多（{{v:arena.sq.1530.humSentR}}、{{v:arena.sq.2142.humSentR}}、{{v:arena.sq.3210.humSentR}} 倍）。和 7.2 节合起来看，一种读法是：模型里的对手吃内置 AI 慢一点，留给我方的内置 AI 多，我方的地从 1071 拍前后开始超出历史，之后越滚越大。这个读法没有单独验证过（7.5 节）。

### 7.5 误差是前期滚出来的，还是后期没拟合上

<!-- if: n('runs.arenaRp') >= 20 -->
为了把这两件事分开，另跑了一遍：前 1530 拍其余真人照录像执行，1530 拍起才换成对手模型。

{{T:arena-rp}}

{{v:arena.rp.text}}
<!-- else -->
要把这两件事分开，需要另跑一遍：前 1530 拍其余真人照录像执行，1530 拍起才换成对手模型。这一组运行（20 次）排在队列后面，这一版没有跑完，不报。所以 1530 拍以后的偏差现在只能记为「没有分清来源」。
<!-- endif -->

### 7.6 已知边界

1. **闭环对得上的范围是开局到 630 拍；到 1071 拍只有绝对量对得上。** 630 拍为止，对手的地、兵密度、在场人数和我方的地都和录像对得上（中位在 1 ± 0.07 以内）。1071 拍，这几项的中位仍在 1 ± 0.05 以内，但我方相对其余真人的人均地已经偏高（{{v:arena-cps.1071.rel}} 倍）。
2. **1530 拍以后闭环里我方的绝对成绩不可信。** 我方人均地到 4284 拍被高估到录像的 {{v:arena-cps.4284.sLand}} 倍。这一段模型里的名次、领土不能拿去对实盘。
3. **对手模型重现的是平均倾向，不是临场判断。** 出手密度、对象构成、千分比和六类原型都来自 20 局的合计。真人在具体一局里看谁正卡着、谁刚被打空、几家一起压一个大号，这些模型里没有。
4. **画像和标定用的是同一批 20 局。** 这是拟合优度，不是样本外的检验。新接的 Va / Vc 局没有进画像，也没有拿来跑闭环。

### 7.7 判定

<!-- assert: Math.abs(n('arena-cps.630.oLand') - 1) <= 0.08 && Math.abs(n('arena-cps.630.sLand') - 1) <= 0.05 && n('arena-cps.1071.rel') >= 1.08 && n('arena-cps.4284.sLand') >= 1.5 && n('arena.n') === 20 -->
对手模型这一项：**部分通过，带边界。**

- 开局到 630 拍：通过。对手的地、兵密度、在场人数，出手的密度和对象构成，人与人之间的分布，都和 {{v:arena.n}} 局录像对得上。
- 630~1071 拍：绝对量对得上，相对量开始偏高（1071 拍，我方人均地 ÷ 其余真人人均地是录像的 {{v:arena-cps.1071.rel}} 倍）。可以用来看方向，一成以内的差不要读。
<!-- if: n('runs.arenaRp') >= 20 -->
- 1530 拍以后：不通过。闭环里对手越来越弱，我方人均地到 4284 拍是录像的 {{v:arena-cps.4284.sLand}} 倍。这一段的闭环结果不能用。偏差的来源见 7.5 节。
<!-- else -->
- 1530 拍以后：不通过。闭环里对手越来越弱，我方人均地到 4284 拍是录像的 {{v:arena-cps.4284.sLand}} 倍。这一段的闭环结果不能用。偏差是前期滚出来的，还是后期的打法没拟合上，这一版没有分清（7.5 节）。
<!-- endif -->
- 以上是拟合优度（画像和标定是同一批 {{v:arena.n}} 局），不是样本外检验。
