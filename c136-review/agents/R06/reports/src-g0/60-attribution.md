## 6. 通道延迟的历史反事实归因

### 6.1 问法

问题是：当年这些局里，指令通道的延迟让编队少拿了多少地。办法是同一局、同一版策略、同一批对手（照录像），只换通道，看窗口末的编队领土差多少。

四个断面，每个断面之后看一段窗口：

| 断面 t0 | 窗口 | 这一段在局里是什么 |
|---|---|---|
| 0 | 0~630 拍 | 开局扩张，抢无主地 |
| 630 | 630~1530 拍 | 接壤、吃内置 AI；卡顿波在这一段爬到顶 |
| 1500 | 1500~2400 拍 | 开始打真人；卡顿波回落 |
| 4284 | 4284~5184 拍 | 后期。A 组的实录阶梯到不了这里，只有 c110 的局有 C2 |

630 以后的窗口都取 900 拍上下，不取到底。原因在 1.2 节说过：其余真人是照录像出手的，我方的地一旦和历史不同，这些录像指令就越来越对不上；窗口越长，「只换了通道」这个前提越站不住。表里「其余真人陆攻照录像执行」一列给出每条臂里还能原样执行的比例。

每个断面跑五条臂，排成一条链，相邻两级只差一样东西：

| 级 | 臂 | 比上一级多了什么 |
|---|---|---|
| — | C0 即时 | 起点：下令即执行 |
| ① | C1 正常延迟 | 指令要等十来拍、7 拍一个回合、每席位 3 个回合最多 9 条 |
| ② | C2，关掉页面停摆 | 这一局实录的落后阶梯（卡顿波） |
| ③ | C2 | 页面中途停摆（席位还活着，页面不再出手） |
| ④ | 历史 | 余项：模拟器没复现好的部分，加上开环重放本身的偏差 |

<!-- if: n('attr.seeds.want') > 0 && n('attr.seeds.runs') >= n('attr.seeds.want') -->
C1 和 C2 里有随机抽样的 d。卡顿波所在的两个断面（630、1500），核心 20 局的 C1、C2 各换一个种子再跑一遍（{{v:attr.seeds.runs}} 次），先在局内取平均；两个种子之间的差另列在噪声底那张表里。结果量是窗口末的编队领土（各席位合计，出局的记 0）。
<!-- else -->
C1 和 C2 里有随机抽样的 d。原计划在卡顿波所在的两个断面（630、1500）给核心 20 局的 C1、C2 各换一个种子再跑一遍（{{v:attr.seeds.want}} 次），这一组排在队列后面，这一版跑完了 {{v:attr.seeds.runs}} 次：跑了两个种子的局先在局内取平均，其余的局只有一个种子；噪声底那张表里「换种子」一列只统计跑了两个种子的局。结果量是窗口末的编队领土（各席位合计，出局的记 0）。
<!-- endif -->

断面 630 的窗口和第 5 节相同（630~1530 拍），这个断面的 C0 / C1 / C2 / C3 就是第 5 节那张整表里的运行，没有重复跑。

三条限定，读后面的数字时都要带上：

1. **这是历史归因，不是预测。** 跑的是当年那一版策略。数字说的是「当年这一局如果通道不落后，同一版策略在这个窗口末会多多少地」，不说明任何别的策略会怎样。
2. **其余真人不会对我方的变化作出反应。** 他们照录像出手。我方地多了，现实里对手会有不同的应对，这里没有。所以「通道不落后能多拿多少」是开环口径下的数，偏乐观。
3. **只看到窗口末。** 多出来的地在窗口之后能不能守住、能不能变成名次，这里不回答。

### 6.2 覆盖和噪声底

{{T:attr-cover}}

复现臂（当年的策略 + 当年的通道）本该重现历史。它和历史的差，就是这套办法自身的误差——各级之间的差要比它大才算数：

{{T:attr-noise}}

<!-- assert: Math.abs(n('attr.noise.630.C2.med') - 1) <= 0.03 && n('attr.noise.630.C2.abs') <= 6 -->
<!-- assert: n('attr.noise.630.C2.in10') >= 0.85 * n('attr.noise.630.C2.n') -->
- 断面 630：C2 复现臂的窗口末编队领土是历史的 {{v:attr.noise.630.C2.med}} 倍（中位），各局偏离 1 的中位是 {{v:attr.noise.630.C2.abs}}%，{{v:attr.noise.630.C2.in10}} 局落在 ±10% 以内（P10~P90：{{v:attr.noise.630.C2.range}}）。
{{v:attr.noise.rest}}

下面把 ±10% 当作噪声底：相邻两级之差的中位不到 10% 的，不下结论。

真局里出了局的席位，在模拟里会不会「多活下来」（5.7 节讲过这种开环偏差），各断面各臂数一遍：

{{T:attr-dead}}

<!-- assert: n('attr.dead.630.lag.C2.rv') === 0 && n('attr.dead.630.lag.C1.rv') === 0 && n('attr.dead.630.lag.C0.rv') === 0 -->
<!-- assert: n('attr.dead.630.lag.hist') <= 0.05 * n('attr.dead.630.lag.seats') -->
- 断面 630：卡顿的局 {{v:attr.dead.630.lag.seats}} 个席位里，真局只有 {{v:attr.dead.630.lag.hist}} 个在窗口末没了地；这几个席位在 C2、C1、C0 三条臂里也都没了地。这个窗口里没有「多活下来」的席位，各臂之间的差不含这种偏差。
{{v:attr.dead.rest}}

### 6.3 归因链

{{T:attr-chain}}

把「即时通道 → 历史」的总差按对数拆开，四段相加正好等于总差：

{{T:attr-share}}

<!-- assert: n('attr.chain.630.lag.n') >= 12 && n('attr.chain.630.lag.n2') === n('attr.chain.630.lag.n') -->
<!-- assert: n('attr.chain.630.lag.c0') >= 1.5 && n('attr.chain.630.lag.c1') >= 1.4 && Math.abs(n('attr.chain.630.lag.c2') - 1) <= 0.05 -->
<!-- assert: n('attr.chain.630.lag.f21') <= -25 && n('attr.chain.630.lag.up') === n('attr.chain.630.lag.n2') -->
<!-- assert: n('attr.share.630.lag.s2') >= 60 && n('attr.share.630.lag.s1') <= 30 && Math.abs(n('attr.share.630.lag.s4')) <= 15 -->
<!-- assert: n('attr.chain.630.clean.f10') <= -8 && Math.abs(n('attr.chain.630.clean.f21')) < 10 && n('attr.share.630.clean.s1') >= 60 -->
**断面 630（630~1530 拍），卡顿波所在的窗口。**

- 卡顿的 {{v:attr.chain.630.lag.n}} 局：走即时通道，窗口末编队领土是历史的 {{v:attr.chain.630.lag.c0}} 倍；加上正常延迟（C1）是 {{v:attr.chain.630.lag.c1}} 倍；换成这一局实录的落后阶梯（C2）是 {{v:attr.chain.630.lag.c2}} 倍，回到历史。逐局看，卡顿波这一级（② C1 → C2）的中位是 {{v:attr.chain.630.lag.f21}}（P25~P75：{{v:attr.chain.630.lag.f21.range}}），{{v:attr.chain.630.lag.up}} 局是 C1 高于 C2，没有例外；正常延迟这一级（① C0 → C1）的中位是 {{v:attr.chain.630.lag.f10}}（{{v:attr.chain.630.lag.f10.range}}）。按对数拆，「即时通道 → 历史」的总差 {{v:attr.share.630.lag.tot}} 里，卡顿波占 {{v:attr.share.630.lag.s2}}%，正常延迟占 {{v:attr.share.630.lag.s1}}%，余项占 {{v:attr.share.630.lag.s4}}%。
- 不卡的 {{v:attr.chain.630.clean.n}} 局：总差 {{v:attr.share.630.clean.tot}}，其中正常延迟占 {{v:attr.share.630.clean.s1}}%（① 的中位 {{v:attr.chain.630.clean.f10}}，{{v:attr.chain.630.clean.f10.neg}} 局为负）；卡顿波这一级只有 {{v:attr.chain.630.clean.f21}}（{{v:attr.chain.630.clean.f21.range}}），在噪声底以内。这是应有的结果：这些局本来就没怎么落后，C2 和 C1 应当差不多。

{{v:attr.chain.rest}}

### 6.4 逐局

断面 0（0~630 拍）：

{{T:attr-games-0}}

断面 630（630~1530 拍）：

{{T:attr-games-630}}

断面 1500（1500~2400 拍）：

{{T:attr-games-1500}}

断面 4284（4284~5184 拍）：

{{T:attr-games-4284}}

### 6.5 机制和走势

各臂的指令签名，说明差是怎么来的：

{{T:attr-mech}}

<!-- assert: n('attr.mech.630.lag.C2.landedShare') <= 60 && n('attr.mech.630.lag.C1.landedShare') >= 95 -->
<!-- assert: n('attr.mech.630.lag.C2.batchShare') >= 50 && n('attr.mech.630.lag.C1.batchShare') <= 5 -->
<!-- assert: n('attr.mech.630.lag.C2.atkVoidRate') >= 20 && n('attr.mech.630.lag.C1.atkVoidRate') <= 5 -->
<!-- assert: n('attr.mech.630.lag.C2.dumpPerSeat') >= 0.3 && n('attr.mech.630.lag.C1.dumpPerSeat') <= 0.05 -->
<!-- assert: Math.abs(n('attr.mech.630.lag.C1.netProd') - 1) <= 0.15 && Math.abs(n('attr.mech.630.lag.C2.netProd') - 1) <= 0.15 -->
卡顿波是怎么让编队少拿地的，看 630 断面卡顿的局里 C2 和 C1 两行的差：

- **发出去的指令一半没进录像。** C2 下，策略发出的指令只有 {{v:attr.mech.630.lag.C2.landedShare}} 进了录像（C1 是 {{v:attr.mech.630.lag.C1.landedShare}}），每个席位有 {{v:attr.mech.630.lag.C2.droppedPerSeat}} 条被「一批最多 9 条」顶掉。页面落后的时候，策略照本机的节奏一条条下令，这些指令攒在一起，等页面追上来时一口气到。
- **到的时候挤在同一拍。** 同拍批占比 {{v:attr.mech.630.lag.C2.batchShare}}（C1 是 {{v:attr.mech.630.lag.C1.batchShare}}）；每席位 {{v:attr.mech.630.lag.C2.dumpPerSeat}} 次清仓批——同一拍里几条指令连着执行，把余额抽干。
- **到的时候目标已经变了。** 陆攻落空率 {{v:attr.mech.630.lag.C2.atkVoidRate}}（C1 是 {{v:attr.mech.630.lag.C1.atkVoidRate}}）：下令时看到的邻居，执行时已经不接壤或者已经没了。
- **兵没有少产。** 净产兵相对历史，C2 是 {{v:attr.mech.630.lag.C2.netProd}}，C1 是 {{v:attr.mech.630.lag.C1.netProd}}。地的差不是产兵的差，是同样多的兵打没打到该打的地方。

历史这一行和 C2 这一行的签名贴得住（第 5 节），所以这几条说的也就是当年真实发生的事。

{{v:attr.mech.rest}}

编队领土相对历史随时间的走势：

断面 630 之后：

{{T:attr-course-630}}

断面 1500 之后：

{{T:attr-course-1500}}

断面 0 之后：

{{T:attr-course-0}}

断面 4284 之后：

{{T:attr-course-4284}}

<!-- assert: n('attr.course.630.C1.lag.150') < n('attr.course.630.C1.lag.450') && n('attr.course.630.C1.lag.450') < n('attr.course.630.C1.lag.900') -->
<!-- assert: [150, 300, 450, 600, 750, 900].every((o) => Math.abs(n(`attr.course.630.C2.lag.${o}`) - 1) <= 0.03) -->
- 断面 630 之后，卡顿的局里 C1 相对历史一路拉开：断面后 150 拍 {{v:attr.course.630.C1.lag.150}} 倍，450 拍 {{v:attr.course.630.C1.lag.450}} 倍，900 拍 {{v:attr.course.630.C1.lag.900}} 倍。差是在卡顿波爬升的那几百拍里逐步攒出来的，不是某一拍的事。C2 这条臂在同一段里一直贴着历史（每个时点的中位都在 1 ± 0.03 以内）。
{{v:attr.course.rest}}

反过来做一次：不卡的局里注入合成卡顿波（C3），看它相对 C1 掉多少，和真卡顿局的「C2 ÷ C1」比量级：

{{T:attr-c3}}

<!-- assert: n('attr.c3.630.r31') <= -15 && n('attr.c3.630.down') === n('attr.c3.630.n') -->
- 断面 630：不卡的 {{v:attr.c3.630.n}} 局挂上合成卡顿波，窗口末编队领土比 C1 低 {{v:attr.c3.630.r31}}，{{v:attr.c3.630.down}} 局都是掉；真卡顿局「C2 ÷ C1」的中位是 {{v:attr.c3.630.r21}}。方向相同，量级相近（两成半到四成）。签名也跟着变成卡顿局的样子（同拍批占比 {{v:attr.mech.630.clean.C3.batchShare}}，陆攻落空率 {{v:attr.mech.630.clean.C3.atkVoidRate}}）。两头做出来是同一件事：给不卡的局加上卡顿波，地掉下去；把卡顿的局的卡顿波拿掉，地涨上来。
{{v:attr.c3.rest}}

### 6.6 结论

{{v:attr.conclusion}}
