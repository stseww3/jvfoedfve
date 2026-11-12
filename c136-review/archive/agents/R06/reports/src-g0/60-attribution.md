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
<!-- assert: ['0', '630', '1500', '4284'].every((t) => Math.abs(n(`attr.noise.${t}.C2.med`) - 1) < 0.035 && n(`attr.noise.${t}.C2.abs`) <= 5) -->
<!-- assert: n('attr.noise.0.C2.in10') === n('attr.noise.0.C2.n') && n('attr.noise.4284.C2.in10') === n('attr.noise.4284.C2.n') && n('attr.noise.1500.C2.in10') >= 0.8 * n('attr.noise.1500.C2.n') -->
<!-- assert: s('attr.noise.630.C2.out').includes('A027（0.8') && s('attr.noise.630.C2.out').split('、').length === 3 -->
<!-- assert: s('attr.noise.630.C2.out').includes('A041') && s('attr.noise.630.C2.out').includes('B041') && s('attr.noise.0.C2.out') === '没有' && s('attr.noise.4284.C2.out') === '没有' -->
  偏出 ±10% 的三局是 {{v:attr.noise.630.C2.out}}：A041 是单个席位的分叉，B041 是录像在卡顿当中截断（都见 5.7 节）；A027 偏低一成，原因没有查。
- 断面 0：{{v:attr.noise.0.C2.med}} 倍，偏离的中位 {{v:attr.noise.0.C2.abs}}%，{{v:attr.noise.0.C2.in10}} 局在 ±10% 以内。
- 断面 1500：{{v:attr.noise.1500.C2.med}} 倍，偏离的中位 {{v:attr.noise.1500.C2.abs}}%，{{v:attr.noise.1500.C2.in10}} 局在 ±10% 以内；偏出去的是 {{v:attr.noise.1500.C2.out}}，都偏高。
- 断面 4284：只有 c110 的 {{v:attr.noise.4284.C2.n}} 局有实录阶梯盖到这里，复现臂 {{v:attr.noise.4284.C2.med}} 倍，{{v:attr.noise.4284.C2.in10}} 局在 ±10% 以内。这个窗口里各条臂都几乎不动（6.3 节），所以这一行算不上有力的检验。
<!-- assert: ['0', '630', '1500', '4284'].every((t) => Math.abs(n(`attr.noise.${t}.C1.med`) - 1) < 0.055 && n(`attr.noise.${t}.C1.abs`) <= 6) -->
- 不卡的局本来就不落后，挂 C1 也应当重现历史。四个断面的中位依次是 {{v:attr.noise.0.C1.med}}、{{v:attr.noise.630.C1.med}}、{{v:attr.noise.1500.C1.med}}、{{v:attr.noise.4284.C1.med}} 倍，偏离的中位在 {{v:attr.noise.0.C1.abs}}%~{{v:attr.noise.630.C1.abs}}% 之间。
<!-- if: n('attr.seeds.want') > 0 && n('attr.seeds.runs') >= n('attr.seeds.want') -->
<!-- assert: ['630', '1500'].every((t) => n(`attr.noise.${t}.C2.spread`) <= 5 && n(`attr.noise.${t}.C1.spread`) <= 5) -->
- 换种子：同一局两个种子的窗口末领土（都除以历史）之差，各局的中位是 630 断面 C2 {{v:attr.noise.630.C2.spread}}%、C1 {{v:attr.noise.630.C1.spread}}%，1500 断面 C2 {{v:attr.noise.1500.C2.spread}}%、C1 {{v:attr.noise.1500.C1.spread}}%。种子带来的波动比噪声底小。
<!-- endif -->

下面把 ±10% 当作噪声底：相邻两级之差的中位不到 10% 的，不下结论。

真局里出了局的席位，在模拟里会不会「多活下来」（5.7 节讲过这种开环偏差），各断面各臂数一遍：

{{T:attr-dead}}

<!-- assert: n('attr.dead.630.lag.C2.rv') === 0 && n('attr.dead.630.lag.C1.rv') === 0 && n('attr.dead.630.lag.C0.rv') === 0 -->
<!-- assert: n('attr.dead.630.lag.hist') <= 0.05 * n('attr.dead.630.lag.seats') && n('attr.dead.630.lag.C1.lost') === 0 && n('attr.dead.630.lag.C2.lost') === 0 && n('attr.dead.630.lag.C0.lost') <= 3 -->
- 断面 630：卡顿的局 {{v:attr.dead.630.lag.seats}} 个席位里，真局只有 {{v:attr.dead.630.lag.hist}} 个在窗口末没了地；这几个席位在 C2、C1、C0 三条臂里也都没了地。这个窗口里没有「多活下来」的席位，各臂之间的差不含这种偏差。（反方向有 {{v:attr.dead.630.lag.C0.lost}} 个：真局里还在、C0 臂里没了地；C1、C2 臂里没有。）
<!-- assert: n('attr.dead.0.lag.hist') === 0 && n('attr.dead.0.clean.hist') === 0 -->
- 断面 0：窗口里真局没有席位出局，谈不上这种偏差。
<!-- assert: n('attr.dead.1500.lag.hist') >= 10 && n('attr.dead.1500.lag.C1.rv') >= 0.6 * n('attr.dead.1500.lag.C1.of') && n('attr.dead.1500.lag.C2.rv') <= 0.3 * n('attr.dead.1500.lag.C2.of') -->
<!-- assert: n('attr.dead.1500.lag.C1.share') <= 6 && n('attr.dead.1500.lag.C0.share') <= 6 && n('attr.dead.1500.clean.hist') === 0 -->
- 断面 1500：卡顿的局 {{v:attr.dead.1500.lag.seats}} 个席位里，真局有 {{v:attr.dead.1500.lag.hist}} 个在窗口末没了地。C2 臂里其中 {{v:attr.dead.1500.lag.C2.rv}} 个还有地（占 C2 编队领土的 {{v:attr.dead.1500.lag.C2.share}}），另有 {{v:attr.dead.1500.lag.C2.lost}} 个反过来。C1、C0 两条臂里这 {{v:attr.dead.1500.lag.hist}} 个席位大多还有地（{{v:attr.dead.1500.lag.C1.rv}} 个、{{v:attr.dead.1500.lag.C0.rv}} 个），它们的地占这条臂编队领土的 {{v:attr.dead.1500.lag.C1.share}}、{{v:attr.dead.1500.lag.C0.share}}。这几个百分点里，哪些是「不落后所以没死」（通道的事），哪些是「没死之后再没有真人打它」（开环重放送的），分不开。读 1500 断面的 ② 时要把它记在账上：C1 比 C2 多出来的地里，至多有这 {{v:attr.dead.1500.lag.C1.share}} 上下不该算到通道头上。
<!-- assert: ['clean', 'lag'].every((c) => ['C2', 'C1', 'C0'].every((a) => n(`attr.dead.4284.${c}.${a}.rv`) <= 2 && n(`attr.dead.4284.${c}.${a}.share`) <= 2)) -->
- 断面 4284：真局里窗口末没了地的席位，不卡的局 {{v:attr.dead.4284.clean.hist}} 个、卡顿的局 {{v:attr.dead.4284.lag.hist}} 个；各臂里多活下来的至多 2 个，占编队领土不到 2%，可以不计。

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

- 卡顿的 {{v:attr.chain.630.lag.n}} 局：走即时通道，窗口末编队领土是历史的 {{v:attr.chain.630.lag.c0}} 倍；加上正常延迟（C1）是 {{v:attr.chain.630.lag.c1}} 倍；换成这一局实录的落后阶梯（C2）是 {{v:attr.chain.630.lag.c2}} 倍，回到历史。逐局看，卡顿波这一级（② C1 → 关掉页面停摆的 C2）的中位是 {{v:attr.chain.630.lag.f21}}（P25~P75：{{v:attr.chain.630.lag.f21.range}}），{{v:attr.chain.630.lag.up}} 局是 C1 高于 C2，没有例外；逐局的 ② 从 {{v:attr.chain.630.lag.f21.max}} 到 {{v:attr.chain.630.lag.f21.min}}，没有一局小于一成，而不卡的 {{v:attr.chain.630.clean.n}} 局在 {{v:attr.chain.630.clean.f21.rest.range}} 之间，两组不重叠。正常延迟这一级（① C0 → C1）的中位是 {{v:attr.chain.630.lag.f10}}（{{v:attr.chain.630.lag.f10.range}}）。按对数拆，「即时通道 → 历史」的总差 {{v:attr.share.630.lag.tot}} 里，卡顿波占 {{v:attr.share.630.lag.s2}}%，页面停摆占 {{v:attr.share.630.lag.s3}}%，正常延迟占 {{v:attr.share.630.lag.s1}}%，余项占 {{v:attr.share.630.lag.s4}}%。
<!-- assert: s('attr.chain.630.lag.f21.le10') === '14 / 14' && n('attr.chain.630.lag.f21.max') <= -10 && s('attr.chain.630.clean.f21.le10') === '0 / 6' && n('attr.chain.630.lag.f22.le10') === 4 -->
<!-- assert: ['A058', 'B039', 'A057', 'B010'].every((m) => n(`chan.doomed.${m}`) >= 6 && s('attr.chain.630.lag.f22.le10.list').includes(m)) && ['A021', 'A027', 'A049', 'A070', 'B017', 'B022', 'B023', 'B025', 'B038', 'B041'].every((m) => n(`chan.doomed.${m}`) <= 3) -->
- 页面停摆这一级（③）只在少数局里有分量：{{v:attr.chain.630.lag.f22.le10}} 局掉了一成以上（{{v:attr.chain.630.lag.f22.le10.list}}），其余的局在 {{v:attr.chain.630.lag.f22.rest.range}} 之间。这 4 局正是页面中途停摆的席位最多的 4 局（各 6~8 个席位，其余的卡顿局不超过 3 个，见 4.2 节的表）。
- 不卡的 {{v:attr.chain.630.clean.n}} 局：总差 {{v:attr.share.630.clean.tot}}，其中正常延迟占 {{v:attr.share.630.clean.s1}}%（① 的中位 {{v:attr.chain.630.clean.f10}}，{{v:attr.chain.630.clean.f10.neg}} 局为负）；卡顿波这一级只有 {{v:attr.chain.630.clean.f21}}（{{v:attr.chain.630.clean.f21.range}}），在噪声底以内。这是应有的结果：这些局本来就没怎么落后，C2 和 C1 应当差不多。

<!-- assert: n('attr.chain.630.lag.asrec.C1') >= 80 && n('attr.chain.630.lag.asrec.C1.min') >= 65 && n('attr.chain.630.lag.c1.minAll') > 1.1 -->
- 两点说明。其一，卡顿的 {{v:attr.chain.630.lag.n}} 局里包括 B041，它的 C2 臂偏高（5.7 节），所以它自己的 ② 被低估了；这只会让上面的数偏保守。其二，C1 臂里其余真人的陆攻还能照录像执行的，各局中位 {{v:attr.chain.630.lag.asrec.C1}}，最低的一局 {{v:attr.chain.630.lag.asrec.C1.min}}：开环的前提在这个窗口大体还在。

<!-- assert: n('attr.chain.0.clean.f10') <= -15 && n('attr.chain.0.lag.f10') <= -15 && s('attr.chain.0.clean.f10.neg') === '6 / 6' && s('attr.chain.0.lag.f10.neg') === '14 / 14' -->
<!-- assert: Math.abs(n('attr.chain.0.lag.f21')) < 10 && Math.abs(n('attr.chain.0.clean.f21')) < 10 && n('attr.chain.0.lag.f21.le10') === 4 && n('attr.share.0.all.s1') >= 70 -->
<!-- assert: n('attr.early.big.n') === 4 && n('attr.early.spearman') <= -0.7 && n('attr.early.n') === 20 && n('attr.early.rest.over.n') === 1 && n('attr.early.rest.med') < n('attr.early.big.range') -->
**断面 0（0~630 拍），开局。**

- 正常延迟这一级（①）在这里最大，各局也最齐：不卡的 {{v:attr.chain.0.clean.n}} 局 {{v:attr.chain.0.clean.f10}}（{{v:attr.chain.0.clean.f10.range}}），卡顿的 {{v:attr.chain.0.lag.n}} 局 {{v:attr.chain.0.lag.f10}}（{{v:attr.chain.0.lag.f10.range}}），20 局全部为负。同一版策略，下令即执行的话，开局 630 拍末的地是历史的 {{v:attr.chain.0.clean.c0}} 倍（不卡的局）、{{v:attr.chain.0.lag.c0}} 倍（卡顿的局）。这不是可以省下来的损失：正常延迟是联机协议固有的，每个页面都有。这个数的意思是，开局抢地对十来拍的延迟很敏感；拿即时通道当口径，开局的领土会被高估两成上下。
- 卡顿波这一级（②）：卡顿的 {{v:attr.chain.0.lag.n}} 局中位 {{v:attr.chain.0.lag.f21}}（{{v:attr.chain.0.lag.f21.range}}），在噪声底以内。逐局看，{{v:attr.chain.0.lag.f21.le10}} 局掉了一成以上（{{v:attr.chain.0.lag.f21.le10.list}}），其余 {{v:attr.chain.0.lag.f21.rest.n}} 局在 {{v:attr.chain.0.lag.f21.rest.range}} 之间；不卡的局是 {{v:attr.chain.0.clean.f21.rest.range}}。
- 掉得多的这 {{v:attr.early.big.n}} 局，是开局就已经开始落后的局。0~630 拍里从下令到执行超过 30 拍的指令占比（实录配对），这 {{v:attr.early.big.n}} 局是 {{v:attr.early.big.list}}；其余 {{v:attr.early.rest.n}} 个卡顿局的中位是 {{v:attr.early.rest.med}}（{{v:attr.early.rest.range}}），不卡的局是 {{v:attr.early.clean.range}}。20 局放在一起，这个占比和 ② 的秩相关是 {{v:attr.early.spearman}}：开局落后的指令越多，② 掉得越多。有一局不合这个次序：{{v:attr.early.rest.over}}。
- 按对数拆：全部 {{v:attr.share.0.all.n}} 局的总差 {{v:attr.share.0.all.tot}}，正常延迟占 {{v:attr.share.0.all.s1}}%，卡顿波占 {{v:attr.share.0.all.s2}}%。

<!-- assert: n('attr.chain.1500.lag.c1') >= 1.1 && Math.abs(n('attr.chain.1500.lag.c2') - 1) < 0.035 && Math.abs(n('attr.chain.1500.lag.f21')) < 10 -->
<!-- assert: n('attr.chain.1500.lag.f21.le10') === 5 && n('attr.chain.1500.lag.n') === 12 && n('attr.chain.1500.lag.f21.rest.n') === 7 && s('attr.chain.1500.clean.f21.le10') === '0 / 6' && n('attr.share.1500.lag.s2') >= 60 -->
<!-- assert: s('attr.chain.1500.lag.f21.minMid') === 'B038' && s('attr.chain.1500.lag.asrec.C1.minMid') === 'B038' && n('attr.chain.1500.lag.asrec.C1') < n('attr.chain.630.lag.asrec.C1') && n('attr.chain.1500.lag.asrec.C1.min') < n('attr.chain.630.lag.asrec.C1.min') -->
<!-- assert: s('attr.chain.1500.lag.f21.rest.list').includes('B010') && s('attr.chain.1500.lag.f21.rest.list').includes('A058') && s('attr.chain.1500.lag.c1.gt110.list').includes('B010 1.2') && s('attr.chain.1500.lag.c1.gt110.list').includes('A058 1.2') -->
<!-- assert: n('attr.chain.1500.lag.f21.second') <= -25 && n('attr.chain.1500.lag.f21.second') >= -40 && s('attr.chain.1500.lag.f22.le10.list').includes('B010') && s('attr.chain.1500.lag.f22.le10.list').includes('A058') && n('attr.chain.1500.lag.f22.le10') === 2 -->
<!-- assert: ['c0', 'c1', 'c2'].every((k) => Math.abs(n(`attr.chain.1500.clean.${k}`) - 1) < 0.035) && Math.abs(n('attr.chain.1500.clean.f10')) <= 3 && Math.abs(n('attr.chain.1500.lag.f10')) <= 3 -->
**断面 1500（1500~2400 拍），卡顿波回落的窗口。**

- 卡顿的 {{v:attr.chain.1500.lag.n}} 局：即时通道 {{v:attr.chain.1500.lag.c0}} 倍，C1 {{v:attr.chain.1500.lag.c1}} 倍，C2 {{v:attr.chain.1500.lag.c2}} 倍（各局中位）。卡顿波这一级（②）的中位是 {{v:attr.chain.1500.lag.f21}}（P25~P75：{{v:attr.chain.1500.lag.f21.range}}），不到噪声底。
- 各局很不齐。{{v:attr.chain.1500.lag.f21.le10}} 局的 ② 掉了一成以上（{{v:attr.chain.1500.lag.f21.le10.list}}）；其余 {{v:attr.chain.1500.lag.f21.rest.n}} 局在 {{v:attr.chain.1500.lag.f21.rest.range}} 之间，和不卡的 {{v:attr.chain.1500.clean.n}} 局（{{v:attr.chain.1500.clean.f21.rest.range}}）分不开。按对数拆（几何平均，数大的局分量重），总差 {{v:attr.share.1500.lag.tot}} 里卡顿波占 {{v:attr.share.1500.lag.s2}}%。
- 所以这个窗口要分开说：**{{v:attr.chain.1500.lag.n}} 个卡顿局里有 5 个，拿掉卡顿波之后同一版策略在窗口末的地明显更多（一成半到三成，B038 另说）；另外 7 个看不出差别。给不出一个有代表性的数。**
- 两笔要记的账。一是 6.2 节说的「多活下来」的席位，占 C1 臂编队领土的 {{v:attr.dead.1500.lag.C1.share}} 上下。二是开环的前提在这个窗口比 630 断面弱：C1 臂里其余真人的陆攻还能照录像执行的，各局中位 {{v:attr.chain.1500.lag.asrec.C1}}，最低的一局只有 {{v:attr.chain.1500.lag.asrec.C1.min}}（630 断面是 {{v:attr.chain.630.lag.asrec.C1}} 和 {{v:attr.chain.630.lag.asrec.C1.min}}）。② 最大的 B038（{{v:attr.chain.1500.lag.f21.min}}，C1 是历史的 {{v:attr.chain.1500.lag.c1.max}} 倍）正是前提最弱的那一局，它的数不能当真。
- 页面停摆这一级（③）在 {{v:attr.chain.1500.lag.f22.le10}} 局里掉了一成以上（{{v:attr.chain.1500.lag.f22.le10.list}}），其余的局在 {{v:attr.chain.1500.lag.f22.rest.range}} 之间。这两局的 C1 比历史高出两成多，但 ② 很小（B010 在上面「其余 7 局」里，A058 也是）：差出在 ③ 和余项上，不在卡顿波这一级。
- 不卡的 {{v:attr.chain.1500.clean.n}} 局：三条臂的中位都在历史的 ±3% 以内（C0 {{v:attr.chain.1500.clean.c0}}、C1 {{v:attr.chain.1500.clean.c1}}、C2 {{v:attr.chain.1500.clean.c2}}），没有可辨的差。正常延迟这一级到这个阶段已经不起作用（① 的中位：不卡的局 {{v:attr.chain.1500.clean.f10}}，卡顿的局 {{v:attr.chain.1500.lag.f10}}）。

<!-- assert: ['clean', 'lag'].every((c) => Math.abs(n(`attr.chain.4284.${c}.c0`) - 1) < 0.055 && Math.abs(n(`attr.chain.4284.${c}.c1`) - 1) < 0.055 && Math.abs(n(`attr.chain.4284.${c}.c2`) - 1) < 0.055 && Math.abs(n(`attr.chain.4284.${c}.f10`)) <= 3 && Math.abs(n(`attr.chain.4284.${c}.f21`)) <= 3) -->
<!-- assert: s('attr.noise.4284.C1.noRatio') === 'A041' && n('attr.chain.4284.clean.n2') + n('attr.chain.4284.lag.n2') === n('attr.noise.4284.C2.n') -->
**断面 4284（4284~5184 拍），后期。**

- {{v:attr.4284.games}} 局（其中 A041 我方在窗口末已经全部出局，历史的编队领土是 0，没有比值）。各臂都贴着历史：C0 的中位 {{v:attr.chain.4284.clean.c0}}（不卡的局）、{{v:attr.chain.4284.lag.c0}}（卡顿的局），C1 {{v:attr.chain.4284.clean.c1}}、{{v:attr.chain.4284.lag.c1}}，有实录阶梯的 {{v:attr.noise.4284.C2.n}} 局 C2 是 {{v:attr.noise.4284.C2.med}}。相邻两级之差的中位都在 ±3% 以内，小于噪声底。
- 这个阶段换通道看不出差别。机制上也说得通（6.5 节）：我方每个席位在这 900 拍里只有两三条指令进录像，能出手的机会本来就少，早到晚到十来拍无所谓。

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

别的断面：

<!-- assert: n('attr.mech.0.lag.hist.batchShare') <= 2 && n('attr.mech.0.lag.C2.batchShare') <= 2 && n('attr.mech.0.lag.C0.netProd') >= 1.15 && n('attr.mech.0.clean.C0.netProd') >= 1.15 && Math.abs(n('attr.mech.0.lag.C1.netProd') - 1) <= 0.05 -->
- **断面 0。** 卡顿局和不卡的局的签名一样干净（历史的同拍批占比 {{v:attr.mech.0.lag.hist.batchShare}}）：开局指令稀，攒不成批；其中几局的页面到开局后段已经开始落后（6.3 节），但还没有在签名上留下痕迹。即时通道多出来的地是滚出来的——地早到手，利息和地租跟着多，C0 的净产兵是历史的 {{v:attr.mech.0.lag.C0.netProd}} 倍（卡顿的局）、{{v:attr.mech.0.clean.C0.netProd}} 倍（不卡的局）；C1 是 {{v:attr.mech.0.lag.C1.netProd}} 倍。
<!-- assert: n('attr.mech.1500.lag.hist.batchShare') >= 80 && Math.abs(n('attr.mech.1500.lag.C2.batchShare') - n('attr.mech.1500.lag.hist.batchShare')) <= 10 && Math.abs(n('attr.mech.1500.lag.C2.atkVoidRate') - n('attr.mech.1500.lag.hist.atkVoidRate')) <= 10 -->
<!-- assert: n('attr.mech.1500.lag.C1.batchShare') <= 5 && n('attr.mech.1500.lag.C1.atkVoidRate') <= 5 && n('attr.mech.1500.lag.C2.droppedPerSeat') >= 5 && n('attr.mech.1500.lag.C1.recPerSeat') < 0.5 * n('attr.mech.1500.lag.hist.recPerSeat') -->
- **断面 1500。** 卡顿局的签名比 630 断面更重：历史的同拍批占比 {{v:attr.mech.1500.lag.hist.batchShare}}，陆攻落空率 {{v:attr.mech.1500.lag.hist.atkVoidRate}}。C2 复现了它（{{v:attr.mech.1500.lag.C2.batchShare}}、{{v:attr.mech.1500.lag.C2.atkVoidRate}}），每个席位被「一批最多 9 条」顶掉 {{v:attr.mech.1500.lag.C2.droppedPerSeat}} 条。C1 下这些都没有（同拍批 {{v:attr.mech.1500.lag.C1.batchShare}}，落空 {{v:attr.mech.1500.lag.C1.atkVoidRate}}），进录像的指令也少得多（每席位 {{v:attr.mech.1500.lag.C1.recPerSeat}} 条，历史 {{v:attr.mech.1500.lag.hist.recPerSeat}} 条）——历史里多出来的那些大半是落后时攒下的重复单。签名差得比 630 断面多，地差得比 630 断面少。
<!-- assert: n('attr.mech.4284.lag.hist.recPerSeat') <= 6 && n('attr.mech.4284.lag.C1.recPerSeat') <= 6 && n('attr.mech.4284.lag.hist.batchShare') <= 2 && n('attr.mech.4284.lag.C1.atkVoidRate') <= 2 -->
- **断面 4284。** 各臂每个席位只有两三条指令进录像（卡顿的局：历史 {{v:attr.mech.4284.lag.hist.recPerSeat}} 条，C1 {{v:attr.mech.4284.lag.C1.recPerSeat}} 条），同拍批占比和落空率都是 0。

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
<!-- assert: [150, 300, 450, 600, 750, 900].every((o) => Math.abs(n(`attr.course.630.C2.lag.${o}`) - 1) < 0.035) -->
- 断面 630 之后，卡顿的局里 C1 相对历史一路拉开：断面后 150 拍 {{v:attr.course.630.C1.lag.150}} 倍，450 拍 {{v:attr.course.630.C1.lag.450}} 倍，900 拍 {{v:attr.course.630.C1.lag.900}} 倍。差是在卡顿波爬升的那几百拍里逐步攒出来的，不是某一拍的事。C2 这条臂在同一段里一直贴着历史（每个时点的中位都在 1 ± 0.03 以内）。
<!-- assert: n('attr.course.1500.C1.lag.300') > n('attr.course.1500.C1.lag.150') && n('attr.course.1500.C1.lag.900') < n('attr.course.1500.C1.lag.300') - 0.1 && [150, 300, 450, 600, 750, 900].every((o) => Math.abs(n(`attr.course.1500.C2.lag.${o}`) - 1) < 0.035) -->
- 断面 1500 之后，卡顿的局里 C1 相对历史先拉开、后收窄：断面后 150 拍 {{v:attr.course.1500.C1.lag.150}} 倍，300 拍 {{v:attr.course.1500.C1.lag.300}} 倍，600 拍回到 {{v:attr.course.1500.C1.lag.600}} 倍，900 拍 {{v:attr.course.1500.C1.lag.900}} 倍。拿掉卡顿波多出来的地，有一部分在窗口里又丢了回去。C2 一直贴着历史。
<!-- assert: n('attr.course.0.C0.lag.300') > n('attr.course.0.C0.lag.630') && n('attr.course.0.C0.clean.300') > n('attr.course.0.C0.clean.630') && [150, 300, 450, 630].every((o) => Math.abs(n(`attr.course.0.C1.clean.${o}`) - 1) < 0.025) -->
- 断面 0 之后，即时通道的优势在第 300 拍前后最大（卡顿的局 {{v:attr.course.0.C0.lag.300}} 倍，不卡的局 {{v:attr.course.0.C0.clean.300}} 倍），到 630 拍回落到 {{v:attr.course.0.C0.lag.630}} 倍、{{v:attr.course.0.C0.clean.630}} 倍：无主地占完以后，早到的那一步不再继续拉开差距。C1 在不卡的局里全程贴着历史。
<!-- assert: [150, 300, 450, 600, 750, 870].every((o) => Math.abs(n(`attr.course.4284.C2.all.${o}`) - 1) < 0.025) -->
<!-- assert: ['C2.all', 'C2.lag', 'C1.clean', 'C1.lag', 'C0.lag', 'C0.clean'].every((a) => [150, 300, 450, 600, 750, 870].every((o) => !has(`attr.course.4284.${a}.${o}`) || Math.abs(n(`attr.course.4284.${a}.${o}`) - 1.01) < 0.025)) -->
- 断面 4284 之后，各臂全程在历史的 0.99~1.03 倍之间。

反过来做一次：不卡的局里注入合成卡顿波（C3），看它相对 C1 掉多少，和真卡顿局的「C2 ÷ C1」比量级：

{{T:attr-c3}}

<!-- assert: n('attr.c3.630.r31') <= -15 && n('attr.c3.630.down') === n('attr.c3.630.n') -->
- 断面 630：不卡的 {{v:attr.c3.630.n}} 局挂上合成卡顿波，窗口末编队领土相对 C1 是 {{v:attr.c3.630.r31}}，{{v:attr.c3.630.down}} 局都是掉；真卡顿局「C2 ÷ C1」的中位是 {{v:attr.c3.630.r21}}。方向相同，量级相近（两成半到四成）。签名也跟着变成卡顿局的样子（同拍批占比 {{v:attr.mech.630.clean.C3.batchShare}}，陆攻落空率 {{v:attr.mech.630.clean.C3.atkVoidRate}}）。两头做出来是同一件事：给不卡的局加上卡顿波，地掉下去；把卡顿的局的卡顿波拿掉，地涨上来。
<!-- assert: Math.abs(n('attr.c3.1500.r31')) < 10 && n('attr.c3.1500.down') <= 4 && n('attr.course.1500.C3.clean.300') <= 0.9 && Math.abs(n('attr.course.1500.C3.clean.900') - 1) <= 0.05 -->
- 断面 1500：不卡的 {{v:attr.c3.1500.n}} 局挂上合成卡顿波，窗口末相对 C1 是 {{v:attr.c3.1500.r31}}，{{v:attr.c3.1500.down}} 局是掉，在噪声底以内；真卡顿局「C2 ÷ C1」的中位是 {{v:attr.c3.1500.r21}}。两头不对称。从走势看，合成波在窗口中段确实把领土压下去了（断面后 300 拍是历史的 {{v:attr.course.1500.C3.clean.300}} 倍），到窗口末又回来（{{v:attr.course.1500.C3.clean.900}} 倍）。真卡顿局到 1500 拍时已经卡了九百拍，站位和兵力都和不卡的局不同；不对称是不是因为这个，没有验证。所以 1500 断面只有单向的证据（把卡顿局的卡顿波拿掉，{{v:attr.chain.1500.lag.n}} 局里 5 局的地明显涨上来），没有 630 断面那样两头对得上的证据。

### 6.6 结论

<!-- assert: n('attr.chain.630.lag.c1') >= 1.4 && s('attr.chain.630.lag.up') === '14 / 14' && n('attr.chain.630.lag.c1.gt110') === 14 && n('attr.chain.630.lag.f21') <= -20 && n('attr.share.630.lag.s2') >= 60 && n('attr.c3.630.down') === n('attr.c3.630.n') -->
<!-- assert: n('attr.chain.1500.lag.f21.le10') === 5 && n('attr.chain.1500.lag.f21.rest.n') === 7 && Math.abs(n('attr.chain.1500.lag.f21')) < 10 && Math.abs(n('attr.c3.1500.r31')) < 10 -->
<!-- assert: n('attr.chain.630.lag.f22.le10') === 4 && n('attr.chain.1500.lag.f22.le10') === 2 && n('attr.chain.0.lag.f22.le10') === 1 && n('attr.early.big.n') === 4 -->
<!-- assert: Math.abs(n('attr.chain.0.lag.f21')) < 10 && Math.abs(n('attr.chain.4284.lag.f21')) <= 3 -->
<!-- assert: n('attr.chain.0.clean.f10') <= -15 && n('attr.chain.0.lag.f10') <= -15 && n('attr.chain.630.clean.f10') <= -10 && s('attr.chain.630.clean.f10.neg') === '6 / 6' -->
<!-- assert: n('pack.vb.n') + n('pack.c110.n') === 20 && n('pack.ext.vb') === 0 && n('pack.ext.c110') === 0 && n('attr.chain.0.lag.n') + n('attr.chain.0.clean.n') === 20 -->
<!-- assert: ['0', '630', '1500', '4284'].every((t) => ['clean', 'lag'].every((c) => Math.abs(n(`attr.chain.${t}.${c}.f22`)) <= 3 && Math.abs(n(`attr.chain.${t}.${c}.fh2`)) <= 3)) && Math.abs(n('attr.share.630.lag.l3')) <= 12 -->
1. **卡顿波是当年这些局少拿地的主要来源，集中在 630~1530 拍。** 卡顿的 {{v:attr.chain.630.lag.n}} 局里，同一版策略换成不落后的通道，窗口末编队领土是历史的 {{v:attr.chain.630.lag.c1}} 倍（中位），{{v:attr.chain.630.lag.up}} 局都比走实录阶梯时高。卡顿波这一级的中位 {{v:attr.chain.630.lag.f21}}，远大于 ±10% 的噪声底；按对数拆，占「即时通道 → 历史」总差的 {{v:attr.share.630.lag.s2}}%。反过来给不卡的局注入合成卡顿波，{{v:attr.c3.630.down}} 局都掉（中位 {{v:attr.c3.630.r31}}）。两头对得上。
2. **1500~2400 拍，只在一部分卡顿局里看得到。** {{v:attr.chain.1500.lag.n}} 个卡顿局里 5 个的 ② 掉了一成以上，另外 7 个和不卡的局分不开；② 的中位（{{v:attr.chain.1500.lag.f21}}）在噪声底以内。反向的合成波检验在这个窗口没有留下窗口末的差。只能说「一部分卡顿局里有」，说不出一个有代表性的量。
3. **开局（0~630 拍）只有开局就落后的几局受影响，后期（4284 拍起）看不到。** 开局 ② 的中位 {{v:attr.chain.0.lag.f21}}，在噪声底以内；掉了一成以上的 {{v:attr.early.big.n}} 局正是 0~630 拍里落后指令最多的几局（秩相关 {{v:attr.early.spearman}}）。后期各臂都贴着历史。
4. **正常延迟（十来拍）只在开局和 630~1530 拍有可辨的作用。** 开局 {{v:attr.chain.0.clean.f10}}（不卡的局）、{{v:attr.chain.0.lag.f10}}（卡顿的局），20 局全部为负；630 断面不卡的局 {{v:attr.chain.630.clean.f10}}（{{v:attr.chain.630.clean.f10.neg}} 局为负）。它是协议固有的，不是可以拿掉的东西。这几个数的用处是说明：拿即时通道当口径，开局和前中期的领土会被高估一到两成。
5. **页面停摆（③）只在少数局里有分量，余项（④）小。** ③ 的中位在各断面是 0 到 −2%；掉了一成以上的，630 断面 {{v:attr.chain.630.lag.f22.le10}} 局、1500 断面 {{v:attr.chain.1500.lag.f22.le10}} 局、开局 {{v:attr.chain.0.lag.f22.le10}} 局，都是有好几个页面中途停摆的局。④ 的中位在 ±3% 以内，和 6.2 节的噪声底是同一回事。

读这些数，除了 6.1 节的三条限定，还要带上两条。结果量是窗口末的编队领土，不是名次，也不是胜负。样本是核心 20 局（Vb {{v:pack.vb.n}} 局、c110 {{v:pack.c110.n}} 局），其中卡顿的 {{v:attr.chain.0.lag.n}} 局、不卡的 {{v:attr.chain.0.clean.n}} 局；再往下分，每格只有几局。
