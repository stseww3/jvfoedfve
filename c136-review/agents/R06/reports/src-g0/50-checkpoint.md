## 5. 历史断面：当年那一版策略放回去，能不能重现当年的签名

### 5.1 做法

每一局取两个断面：630 拍（开局扩张结束、开始互相接壤）和 1530 拍（卡顿波的后半段）。从断面起，我方席位交给这一局当年那一版策略，经指令通道下令；其余真人照录像。窗口是 630~1530 拍和 1530~3210 拍，录像不够长的局跑到录像结束。

四档通道各跑一遍，逐项和这一局同一窗口的录像（历史臂）比：

- 走 **C2**（这一局的实录阶梯）应当对得上——这是「模拟器能不能重现历史」的正面检验。
- 卡顿的局走 **C1**（不落后）或 **C0**（即时）应当对不上——这是反面检验：如果换掉通道签名还一样，说明签名不是通道造成的，这套通道模型就没有意义。
- 不卡的局挂上 **C3**（合成卡顿波）应当从「不卡」的签名变成「卡顿」的签名。

容差沿用会审提案 §1.2 写下的讨论起点：占比类的量与真局相差不超过 10 个百分点；计数类的量（每席位进录像条数、每席位清仓批数）与真局同一量级，这里取 0.5~2 倍。

### 5.2 任务卡点名的 60 次

{{T:ckpt-card}}

<!-- assert: n('card.n') === 60 -->
<!-- assert: n('card.C2.630.hitPc') >= 90 && n('card.C2.1530.hitPc') >= 80 -->
<!-- assert: n('card.C1.630.hitPc') >= 90 && n('card.C1.1530.hitPc') >= 80 -->
<!-- assert: n('card.C3.630.hitPc') <= 50 && n('card.C3.1530.hitPc') <= 50 -->
- C2：630~1530 拍 {{v:card.C2.630.hit}} 项签名在容差内，窗口末编队领土 {{v:card.C2.630.terrIn}} 局落在真局的 ±10% 内；1530~3210 拍 {{v:card.C2.1530.hit}} 项、{{v:card.C2.1530.terrIn}} 局。
- C1 挂在不卡的局上：{{v:card.C1.630.hit}} 项、{{v:card.C1.1530.hit}} 项在容差内。不卡的局本来就没怎么落后，C1 和 C2 在这些局上应当差不多，结果也是这样。
- C3 挂在不卡的局上：只有 {{v:card.C3.630.hit}} 项、{{v:card.C3.1530.hit}} 项还在容差内——注入一段卡顿，签名就离开了这一局的真值。这一行是反面检验，对不上才是对的。

<!-- if: n('scope.va.runs') + n('scope.vc.runs') > 0 -->
下面几小节在这 60 次之外补了两样：630 断面补齐成每一局四档通道都跑（反面检验要用：卡顿的局走 C1 / C0）；再加上新接的 Va / Vc 局。1530 断面跑了哪些臂，以各表的「运行数」一列为准。`calib/g0/` 下一共 {{v:runs.g0}} 次运行。
<!-- else -->
下面几小节在这 60 次之外补了一样：630 断面补齐成每一局四档通道都跑（反面检验要用：卡顿的局走 C1 / C0）。1530 断面跑了哪些臂，以各表的「运行数」一列为准。`calib/g0/` 下一共 {{v:runs.g0}} 次运行，都是核心 20 局（Vb、c110）的。

**新接的 Va / Vc 这 {{v:pack.ext}} 局，断面运行排在队列后面，这一版没有跑。** 所以这一节验的只有 Vb 和 c110 两版；Va、Vc 在本报告里只过了物理底座（第 2 节）、实盘签名（第 3 节）和实录阶梯（4.2 节）。
<!-- endif -->

### 5.3 逐局：C2 对这一局的真值

630~1530 拍：

{{T:ckpt-c2-630}}

1530~3210 拍：

{{T:ckpt-c2-1530}}

### 5.4 按通道和卡顿档汇总

{{T:ckpt-err}}

{{T:ckpt-hit}}

<!-- assert: n('ckpt.630.clean.C2.hitPc') >= 90 && n('ckpt.630.lag.C2.hitPc') >= 90 -->
<!-- assert: n('ckpt.1530.clean.C2.hitPc') >= 80 && n('ckpt.1530.lag.C2.hitPc') >= 80 -->
<!-- assert: n('ckpt.630.lag.C1.hitPc') <= 40 && n('ckpt.630.lag.C0.hitPc') <= 40 -->
<!-- assert: n('ckpt.630.lag.C1.batchShare.abs') >= 40 && n('ckpt.630.lag.C2.batchShare.abs') <= 10 -->
<!-- assert: n('ckpt.630.clean.C0.dupShare.abs') >= 25 && n('ckpt.630.clean.C1.dupShare.abs') <= 10 -->
<!-- assert: n('ckpt.630.clean.C3.batchShare.abs') >= 40 -->
<!-- assert: n('ckpt.630.lag.C1.terr') >= 1.3 && n('ckpt.630.clean.C3.terr') <= 0.9 -->
读法：

1. **C2 两档都对得上。** 630~1530 拍，不卡的局 {{v:ckpt.630.clean.C2.hit}} 项在容差内（{{v:ckpt.630.clean.C2.hitPc}}），卡顿的局 {{v:ckpt.630.lag.C2.hit}} 项（{{v:ckpt.630.lag.C2.hitPc}}）；1530~3210 拍是 {{v:ckpt.1530.clean.C2.hitPc}} 和 {{v:ckpt.1530.lag.C2.hitPc}}。同拍批占比在卡顿的局里真值的中位是 {{v:ckpt.630.lag.C2.batchShare.real}}，模拟是 {{v:ckpt.630.lag.C2.batchShare.sim}}，逐局相差的中位 {{v:ckpt.630.lag.C2.batchShare.abs}} 个百分点。
2. **卡顿的局换成不落后的通道，签名就没了。** 同样这些卡顿的局走 C1，只有 {{v:ckpt.630.lag.C1.hitPc}} 的项还在容差内，同拍批占比逐局差 {{v:ckpt.630.lag.C1.batchShare.abs}} 个百分点；走 C0 是 {{v:ckpt.630.lag.C0.hitPc}}。窗口末的编队领土，C1 是真局的 {{v:ckpt.630.lag.C1.terr}} 倍。所以卡顿局的那套签名（同拍批、清仓批、陆攻落空）是通道落后造成的，不是策略或对手造成的；这也是第 6 节做归因的依据。
3. **不卡的局也不能用即时通道。** 不卡的局走 C0，重复单占比逐局差 {{v:ckpt.630.clean.C0.dupShare.abs}} 个百分点（真值的中位 {{v:ckpt.630.clean.C0.dupShare.real}}，C0 只有 {{v:ckpt.630.clean.C0.dupShare.sim}}），走 C1 只差 {{v:ckpt.630.clean.C1.dupShare.abs}} 个百分点。指令从下令到执行那十来拍里，策略会对同一个目标再下一次令，即时通道里没有这一段，重复单就没了，窗口末的编队领土也比真局高（{{v:ckpt.630.clean.C0.terr}} 倍，C1 是 {{v:ckpt.630.clean.C1.terr}} 倍）。旧门禁用的就是即时口径。
<!-- assert: n('ckpt.630.lag.C3.hitPc') >= 70 && n('ckpt.630.lag.C3.hitPc') < n('ckpt.630.lag.C2.hitPc') && n('ckpt.630.lag.C3.hitPc') > n('ckpt.630.lag.C1.hitPc') + 30 -->
4. **合成卡顿波造得出卡顿局的签名。** 不卡的局挂 C3，同拍批占比逐局比真值高出 {{v:ckpt.630.clean.C3.batchShare.abs}} 个百分点，窗口末编队领土是真局的 {{v:ckpt.630.clean.C3.terr}} 倍。反过来，把卡顿的局自己的实录阶梯换成这一条合成波，{{v:ckpt.630.lag.C3.hitPc}} 的签名仍在容差内——不如用它自己的阶梯（{{v:ckpt.630.lag.C2.hitPc}}），但远好于不落后的通道（{{v:ckpt.630.lag.C1.hitPc}}）。合成波不是哪一局的实录，却抓住了卡顿局签名的大半。

### 5.5 按版本

{{T:ckpt-ver}}

{{T:ckpt-counts}}

<!-- assert: Math.min(n('ckpt.ver.vb.630.hitPc'), n('ckpt.ver.vb.1530.hitPc'), n('ckpt.ver.c110.630.hitPc'), n('ckpt.ver.c110.1530.hitPc')) >= 85 -->
<!-- if: n('scope.va.runs') + n('scope.vc.runs') > 0 -->
四版策略里，Vb 和 c110 各有十来局，签名在容差内的比例两个窗口都在八成半以上；Va、Vc 的局数少（表里有几局就是几局），只能说没有看到某一版特别对不上。计数的合计（进录像的指令、同拍批、清仓批）模拟与真局同一量级，逐项见表。
<!-- else -->
Vb 和 c110 各有十来局，签名在容差内的比例两个窗口都在八成半以上。计数的合计（进录像的指令、同拍批、清仓批）模拟与真局同一量级，逐项见表。Va、Vc 的断面运行这一版没有跑，表里没有这两版。
<!-- endif -->

### 5.6 对实盘区间

第 3 节给每一版、每一档卡顿算了实盘区间（P25~P75）。这里把模拟值和真值各自落进区间的比例并排放：

{{T:ckpt-bands}}

区间只盖住中间一半的局，所以真值自己的命中率也就在一半上下。要看的是模拟值的命中率和真值的命中率是不是同一个水平：

<!-- assert: Math.abs(n('band.C2.lag.lag.630.sim') - n('band.C2.lag.lag.630.real')) <= 15 -->
<!-- assert: n('band.C1.lag.lag.630.sim') <= n('band.C2.lag.lag.630.sim') - 20 -->
<!-- assert: n('band.C3.clean.lag.630.sim') >= n('band.C3.clean.lag.630.real') + 20 -->
- C2 挂在卡顿的局上、对卡顿档区间：630~1530 拍模拟 {{v:band.C2.lag.lag.630.sim}}、真值 {{v:band.C2.lag.lag.630.real}}，同一个水平。
- 同样的局换成 C1：模拟值的命中率掉到 {{v:band.C1.lag.lag.630.sim}}。
- C3 挂在不卡的局上、对卡顿档区间：模拟 {{v:band.C3.clean.lag.630.sim}}，而这些局的真值（不卡）只有 {{v:band.C3.clean.lag.630.real}} 落在卡顿档区间里。注入卡顿波之后，不卡的局看起来像卡顿的局。

### 5.7 对不上的局

C2 臂里，窗口末编队领土偏出真局 ±10% 的运行：

{{T:ckpt-out}}

<!-- assert: n('out.n') >= 1 -->
签名在这些运行里大多还对得上（5.3 节的表），对不上的是窗口末的领土。分三种情形。

<!-- assert: n('revived.630.n') === 0 && n('revived.630.lost') === 0 -->
<!-- assert: n('revived.1530.n') >= 3 * Math.max(1, n('revived.1530.lost')) -->
<!-- assert: n('revived.1530.inEx') > n('revived.1530.in') -->
<!-- assert: ['A027', 'A070', 'B010', 'B038'].every((m) => n(`out.${m}.1530.revived`) >= 1 && Math.abs(n(`out.${m}.1530.ratioEx`) - 1) <= 0.15) -->
**一、长窗口里，真局出了局的席位在模拟里活了下来。** 1530~3210 拍这个窗口的 {{v:revived.1530.runs}} 次 C2 运行、{{v:revived.1530.seats}} 个席位里，有 {{v:revived.1530.n}} 个席位真局里窗口末已经没有地、模拟里还有地（分布在 {{v:revived.1530.runsWith}} 次运行里）；反过来（真局还在、模拟里没了）只有 {{v:revived.1530.lost}} 个。630~1530 拍这个窗口两边各是 {{v:revived.630.n}} 个和 {{v:revived.630.lost}} 个。卡顿局在 1530~3210 拍偏高的那四次（A027、A070、B010、B038）都属于这种：把多活下来的席位的地拿掉，编队领土就回到真局的 ±15% 以内（表里「去掉后」一列）。全部 {{v:revived.1530.runs}} 次里，落在 ±10% 内的从 {{v:revived.1530.in}} 变成 {{v:revived.1530.inEx}}。

这是开环重演的结构性偏差，方向固定偏乐观。对手的指令照录像放：真局里某个席位出局之后，录像里自然不再有冲着它去的指令。模拟里这个席位只要比真局多撑过出局的那一拍，之后就再没有真人打它，可以一直长下去。窗口越长、真局里出局的席位越多，偏得越多。所以：**断面重演的窗口末领土，在 1530~3210 拍这样的长窗口、且真局里我方有席位出局的局上偏高，不能当作对真局的无偏复现**；签名（按指令数的占比）受的影响小。

<!-- assert: s('out.A041.630.topSameSide') === '是' && n('out.A041.630.top') >= 50 -->
<!-- assert: n('out.A041.630.topGap') <= n('out.A041.630.medGap') -->
<!-- assert: n('out.A023.1530.top') >= 80 && n('out.A023.1530.topLand.C2') < 0.6 * n('out.A023.1530.topLand.hist') -->
**二、偏差集中在一个席位上。** A041 的 630~1530 拍，全部偏差的 {{v:out.A041.630.top}} 在 {{v:out.A041.630.topSeat}} 号一个席位上：真局里它窗口末有 {{v:out.A041.630.topLand.hist}} 格地，模拟里 C0 / C1 / C2 三档通道下分别是 {{v:out.A041.630.topLand.C0}} / {{v:out.A041.630.topLand.C1}} / {{v:out.A041.630.topLand.C2}} 格。三档通道都偏在同一边，所以不是通道的事：同一版策略放在这个席位上，模拟里比当年多打下一块地。当年它为什么没打下来，没有查到原因；至少不是因为这个席位的页面有一长段没动静——它在窗口里最长 {{v:out.A041.630.topGap}} 拍没有已知点，全队各席位的中位是 {{v:out.A041.630.medGap}} 拍。A023 的 1530~3210 拍反过来：{{v:out.A023.1530.topSeat}} 号席位真局里从断面起长到了 {{v:out.A023.1530.topLand.hist}} 格，模拟里（C2）只有 {{v:out.A023.1530.topLand.C2}} 格，占了全部偏差的 {{v:out.A023.1530.top}}，其余九个席位几乎一样。这种单个席位的分叉不成系统（一高一低），但说明逐局的窗口末领土可以因为一个席位的一次得手或失手差出两成。

<!-- assert: n('wall.B041.recEnd') >= 1150 && n('wall.B041.recEnd') <= 1160 && n('wall.B041.afterEnd') >= 300 -->
<!-- assert: n('tailend.B041.630.lagLast.med') >= 150 && n('tailend.B041.630.toEnd.med') >= 100 && n('tailend.B041.630.quiet100') >= 0.5 * n('tailend.B041.630.seats') -->
**三、B041：录像在卡顿当中截断。** 这一局的录像到第 {{v:wall.B041.recEnd}} 拍为止，对局本身还在往下打。断的地方正是卡顿高峰：{{v:out.B041.630.blindSeats}} 个席位最后一个已知点上还落后 {{v:out.B041.630.blindLag}} 拍左右，这之后到窗口末占了窗口内 {{v:out.B041.630.blind}} 的 席位·拍。各席位最后一条进录像的指令，中位是页面在本机第 {{v:tailend.B041.630.tauLast.med}} 拍下的令、服务器第 {{v:tailend.B041.630.eLast.med}} 拍执行，离录像结束还有 {{v:tailend.B041.630.toEnd.med}} 拍；到窗口末还在场的 {{v:tailend.B041.630.seats}} 个席位里，{{v:tailend.B041.630.quiet100}} 个在最后 100 拍以上没有任何指令进录像。

<!-- assert: n('wall.B041.behind') > 2 * n('tailend.B041.630.lagLast.med') && n('wall.B041.near.behindMin') > n('tailend.B041.630.lagLast.med') && n('wall.B041.near.n') >= 5 -->
缺省的 C2 假定页面在最后一个已知点之后追平。这一局的实情正相反，日志里有旁证：录像结束之后 {{v:wall.B041.afterEnd}} 拍（服务器大约第 {{v:wall.B041.server}} 拍），{{v:wall.B041.seat}} 号的页面登记离场，那时它自己才走到本机第 {{v:wall.B041.local}} 拍，落后 {{v:wall.B041.behind}} 拍；同一时刻另外 {{v:wall.B041.near.n}} 个号的页面在本机第 {{v:wall.B041.near.local}} 拍，落后 {{v:wall.B041.near.behind}} 拍。最后一个已知点上的落后是 {{v:tailend.B041.630.lagLast.med}} 拍上下，之后没有退，还在加大。（服务器拍数由日志里整秒的时间戳换算，误差 ±18 拍；这几行由 `scripts/logdigest.py` 从结算日志里取出。）

<!-- assert: n('hold.B041.630.recDef') >= 1.7 * n('hold.B041.630.recReal') && s('out.B041.630.topSameSide') === '是' -->
<!-- assert: s('asrec.630.minMid') === 'B041' && n('asrec.630.min') <= 80 && n('asrec.630.med') >= n('asrec.630.min') + 10 -->
模拟里的页面一「追平」就照常出手，于是我方进录像的指令成了当年的两倍（每席位 {{v:hold.B041.630.recDef}} 条，真局 {{v:hold.B041.630.recReal}} 条），窗口末领土是真局的 {{v:out.B041.630.ratio}} 倍；偏差最大的那个席位在 C0 / C1 / C2 三档通道下都比真局高。其余真人的陆攻在这一局只有 {{v:asrec.630.min}} 还能照录像执行，是这个窗口各局里最低的（各局的中位是 {{v:asrec.630.med}}）——模拟里的局面离历史已经很远。

为了量「最后一个已知点之后页面追平」这条假定的影响，把它换成另外两种，重跑了清单上的运行：之后一直保持那时的落后（「保持」）；之后发出的指令一律不落地（「截断」）。「截断」不是一种可以事先设定的通道：它用了真局的结果（这个席位此后再没有指令进录像），只当诊断用，回答的是「偏差是不是全部出在最后一个已知点之后」。

{{T:ckpt-hold}}

<!-- assert: n('hold.n') >= 15 && n('cut.n') >= 15 && n('hold.outMoved') === 0 && n('hold.between') === 0 -->
<!-- assert: n('cut.B041.630.terr') >= 0.95 && n('cut.B041.630.terr') <= 1.05 && Math.abs(n('cut.B041.630.rec') - n('hold.B041.630.recReal')) <= 0.05 * n('hold.B041.630.recReal') && s('cut.B041.630.sig') === '8 / 8' && s('hold.B041.630.sigDef') === '5 / 8' -->
<!-- assert: n('hold.B041.630.hold') >= 1.15 && n('hold.B041.630.recHold') >= 1.5 * n('hold.B041.630.recReal') && Math.abs(n('hold.B041.630.bsHold') - n('hold.B041.630.bsReal')) > Math.abs(n('hold.B041.630.bsDef') - n('hold.B041.630.bsReal')) -->
- **B041 的偏差全部出在最后一个已知点之后。** 换成「截断」，窗口末领土从 ×{{v:hold.B041.630.def}} 回到 ×{{v:cut.B041.630.terr}}，进录像的指令从每席位 {{v:hold.B041.630.recDef}} 条回到 {{v:cut.B041.630.rec}} 条（真局 {{v:hold.B041.630.recReal}} 条），容差内的签名从 {{v:hold.B041.630.sigDef}} 项变成 {{v:cut.B041.630.sig}} 项。换成「保持」不行：领土 ×{{v:hold.B041.630.hold}}，进录像的指令仍是真局的近两倍（{{v:hold.B041.630.recHold}} 条），同拍批占比反而离真局更远（{{v:hold.B041.630.bsHold}} 对 {{v:hold.B041.630.bsReal}}）。也就是说，各席位最后一个已知点之前的那一段，模拟和当年对得上；对不上的是之后那一段，模拟让页面落了地的指令，当年一条也没有进录像。这和上面的旁证是一回事：页面既没有追平，也没有保持，而是越落越远。
<!-- assert: n('cut.out') === 7 && n('cut.outMoved') === 2 && n('cut.B010.1530.terr') <= 1.1 && n('hold.B010.1530.def') > 1.1 -->
- **其余的局，换假定动不了多少领土。** 清单上 {{v:cut.out}} 次窗口末领土偏出 ±10% 的运行，「保持」没有一次拉回 ±10% 以内，「截断」拉回 {{v:cut.outMoved}} 次（B041、B010）。剩下 5 次的偏差来自前面两种情形（多活下来的席位、单个席位的分叉），和这条假定无关。
<!-- assert: n('cut.hits.cut') >= n('cut.hits.def') && n('cut.hits.def') > n('cut.hits.hold') && n('cut.blindHits.cut') >= n('cut.blindHits.def') && n('cut.blindHits.def') > n('cut.blindHits.hold') -->
<!-- assert: n('cut.blind') === 8 && n('cut.worse') === 1 && n('cut.same') === 5 && n('cut.recDev.cut') < n('cut.recDev.def') -->
<!-- assert: n('hold.sig.def') > n('hold.sig.hold') && n('hold.sig.defAbs') < n('hold.sig.holdAbs') && n('hold.rec.def') > n('hold.rec.hold') -->
<!-- assert: Math.abs(n('hold.A057.1530.bsDef') - n('hold.A057.1530.bsReal')) <= 10 && Math.abs(n('hold.A057.1530.bsHold') - n('hold.A057.1530.bsReal')) >= 30 && Math.abs(n('cut.A057.1530.bs') - n('hold.A057.1530.bsReal')) <= 10 -->
- **签名：「保持」最差，「截断」和「追平」相近。** 清单上 {{v:cut.n}} 次运行合计，容差内的签名项「追平」{{v:cut.hits.def}}，「保持」{{v:cut.hits.hold}}，「截断」{{v:cut.hits.cut}}；看不见的一段占到一成以上的 {{v:cut.blind}} 次里，依次是 {{v:cut.blindHits.def}}、{{v:cut.blindHits.hold}}、{{v:cut.blindHits.cut}}。这 {{v:cut.blind}} 次里，「截断」容差内的项数比「追平」多的 2 次、一样的 {{v:cut.same}} 次、少的 {{v:cut.worse}} 次；进录像条数离真局的差（中位），「追平」{{v:cut.recDev.def}}，「截断」{{v:cut.recDev.cut}}。「追平」对「保持」：同拍批占比离真局的差，「追平」的中位是 {{v:hold.sig.defAbs}} 个百分点，「保持」是 {{v:hold.sig.holdAbs}} 个；逐次比，{{v:hold.sig.def}} 次「追平」更近，{{v:hold.sig.hold}} 次「保持」更近，{{v:hold.sig.tie}} 次相差不到 2 个百分点。最清楚的是 A057 的 1530~3210 拍（看不见的一段占 {{v:hold.A057.1530.blind}}）：同拍批占比真局 {{v:hold.A057.1530.bsReal}}，追平 {{v:hold.A057.1530.bsDef}}，截断 {{v:cut.A057.1530.bs}}，保持 {{v:hold.A057.1530.bsHold}}。

缺省假定不改，仍是「追平」，验收用的数字也不因此改动。理由有两条。其一，能事先设定的两种假定里，「追平」比「保持」更接近当年。其二，「截断」在这张清单上不比「追平」差，但它用了真局的结果；而且清单是按「偏得多、看不见的一段多」挑出来的 {{v:cut.n}} 次运行，在它上面挑规则，等于照着考题调参。「截断」留作诊断档。

<!-- assert: n('wall.B025.afterEnd') >= 300 && n('cut.B025.630.terr') < n('hold.B025.630.def') && Math.abs(n('cut.B025.630.terr') - 1) <= 0.05 -->
由此得到一条边界：**录像在卡顿当中截断的局，缺省的 C2 在各席位最后一个已知点之后会高估我方的出手。** 入库的 20 局里这样的有两局：B041（上面），和轻一些的 B025——录像到第 {{v:wall.B025.recEnd}} 拍为止，结束之后 {{v:wall.B025.afterEnd}} 拍时还有页面落后 {{v:wall.B025.behind}} 拍；它的窗口末领土「追平」是 ×{{v:hold.B025.630.def}}，「截断」是 ×{{v:cut.B025.630.terr}}。

### 5.8 判定

<!-- assert: n('card.C2.630.terrIn') >= 0.9 * n('card.C2.630.n') && n('revived.1530.in') <= 0.8 * n('revived.1530.runs') -->
<!-- assert: Math.min(n('ckpt.ver.vb.630.hitPc'), n('ckpt.ver.vb.1530.hitPc'), n('ckpt.ver.c110.630.hitPc'), n('ckpt.ver.c110.1530.hitPc')) >= 85 -->
第 2 项（通道）通过，带四条边界。

通过的依据：走这一局的实录阶梯，当年那一版策略重现了当年的指令签名。任务卡点名的 60 次里，C2 在 630~1530 拍有 {{v:card.C2.630.hit}} 项在容差内，1530~3210 拍 {{v:card.C2.1530.hit}} 项；Vb 和 c110 两版、两个窗口都在 85% 以上。反面检验也成立：卡顿的局换成不落后的通道，容差内的比例掉到 {{v:ckpt.630.lag.C1.hitPc}}；不卡的局注入合成卡顿波，掉到 {{v:card.C3.630.hitPc}}。签名是通道决定的，通道模型抓住了它。

边界：

1. **窗口末的领土，630~1530 拍可以用，1530~3210 拍不可以。** 前一个窗口 {{v:card.C2.630.terrIn}} 局落在真局的 ±10% 内；后一个窗口只有 {{v:card.C2.1530.terrIn}} 局，而且偏差偏向一边（真局出了局的席位在模拟里活下来，5.7 节）。
2. **单个席位的分叉可以让一局的窗口末领土差出两成**（A041、A023），方向不定。看领土要看多局的中位，不看单局。
3. **录像在卡顿当中截断的局（B041，轻一些的 B025），缺省的 C2 在最后一个已知点之后高估我方的出手。** B041 因此没有复现出来（窗口末领土 ×{{v:hold.B041.630.def}}）；把最后一个已知点之后的指令截掉，它就回到 ×{{v:cut.B041.630.terr}}（5.7 节）。这两局的断面重演，只到各席位最后一个已知点为止可信。
4. **即时通道（C0）不是任何一档的替身。** 连不卡的局也对不上（重复单占比差 {{v:ckpt.630.clean.C0.dupShare.abs}} 个百分点，窗口末领土是真局的 {{v:ckpt.630.clean.C0.terr}} 倍）。
