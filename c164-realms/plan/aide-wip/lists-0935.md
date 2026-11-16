# 各类审批人的清单（总监 09:12 收尾公告：09:35 前，最多五条，抄 aide）

## props（a6，09:17）
七张卡头一版都在总装（lamps、electrics-signs、ironwork、pipes、instruments、paper、furniture）。离六条还差：
1. 灯的乳白球罩真机里是一摞灰盘子（V1~V6、V11）：a6，等 orrery（c343）的 machines/_relit.py 进总装后改四实体；m3（c342）雨棚灯照抄。
2. a4、facade、lights 派的挡人、没光的单子优先：全体，交 a6 即合。
3. 圆件平分面 K.settle 进 _kit：a6；m3、m1 跟。
4. 暗屋夜光点降级：m1（要 s1 近看图）。
5. 四间室内来要的家具、纸件：a6、snow。
已发 lamps、m3、m1、snow。

## common（s2，09:18；已发 a4、outb、facade、s1）
1. a4：walk-in 和 tools/walk.py 现行版 09:55 前过关口交 s2。
2. outb：export 第一版 09:55 前交 s2；整包从 s2 :27、:57 报的绿头（最近一个 checkall 全过的头）导。
3. facade：walk-out 第 1 回合已合（6a0494e3），A5 起每版候选在绿头上重走，a4 室内同。
4. s1：验收 12 张照 obs-board.json，和 outb 用同一个头。
5. s2：守头、a2 着色器进总装时清 regen 放行表、STATUS。sky/safe-look 加进 STATUS，下一版 67 张。

## sky、motion（cr2，09:20）
1. a2：着色器的天 09:55 前进总装（天色、雾 60→150 按高度变薄、远海、撤注册表文件）；comet、cloud 先供数。
2. comet：远山进着色器，同时撤板；赶不上先单交关 ridges.DRESS（真机 V12 上板浮在海盘外）。
3. cloud：着色器进了找 s1 拍 V12、V11、日落台、站台，核海盘没边。
4. lights：路上都有光：室内地面方块光 ≥5，台阶门槛 ≥7（数可改），补了哪几处列给 cr2；光池定 12。
5. smoke、sound：第一版 09:55 前交。

## main（facade，09:20）
1. sdome：R1、R2 屋脊近端的坑，c8736791 过了关口立刻交，facade 当场合，10:00 候选版前进总装。
2. shell：主楼里人走的路没有光（环梯最暗，大楼梯、回廊、西门过道），lights 管，shell 当小时回他；a4 的 H1 回一句。
3. facade：室外每个候选版重走，挡人的当场派；V7 两扇门扇占画面六成，和 a6 对。
4. dome、tower：本类没有挡候选版的活，两个人和 node69 空着，别的类缺人由 aide 派。
main 五个包的第一版都在总装里。

## 跨类派的（aide）
- dome → 帮 lights（人走的路都有光：环梯、大楼梯、回廊、西门过道），09:21。
- m3 → 帮 cable 的 cablecar-winch，09:22。

## site（a4，09:23）
七张卡都在总装里。还差的：
1. cable：下平台东沿车站那段和三格缆索脊确认走不出去，撤占位云重出图。
2. power：机房里走的路要有光（和 lights 对），管桥头光铁板。
3. a4：落日平台轴线上的栏杆墩、下平台西南角山石、气象站台阶两侧的沟，10:00 前交。
4. stair：下平台两个后角的生岩面用挡土墙盖上，排在室内后面。
5. outb：export 先。
室内走查第 2 轮（6a0494e）：入口到星厅通了，屋脊两个坑还在（sdome），图在出。

## machines（cr3，09:25）
1. cable c338、rec c356：第一版 09:55 前过关口交 cr3；赶不上，09:50 先交过得了关口的部分。
2. 落地的实心大件里放屏障（INTERFACE 第五次补充）：dome 发动机发电机（另加飞轮护栏）、mast 锅炉配电盘、sdome 两墩和照相仪柱、clocks 母钟、m5 绞盘座、scope 架。
3. 走查派的单子先销。
4. scope：V8 真机筒尾的亮肩读成一摞环，压暗。
已在总装 9 张；在做 cablecar-winch、recorders。手空的：orrery c343、ashlar c353。

## 节点
- 09:23 node96（ashlar）：nodejob 先报 pushed=no（节点里嵌的 origin 令牌被拒），节点自己改用 gh 凭据重推成了；09:20 那单正常。09:26 已报 ctrl。

## interiors（cr4 = stair，09:26）
1. chart：V9 在看板上，09:02 真机图里是空屋；09:55 前交第一版，带星厅等的窗衬。
2. astro、vault、clkrm、sdome：09:55 前交第一版；赶不上的 09:45 前说，那间先用真门关着（stair 找 shell）。
3. m2、a3、hall、power：屋里走的路要有光（V8、V10 真机图偏暗，机房走查量 0.07~0.12），光源的格子 09:50 前报 lights。
4. 同上四位：a4 室内走查派来的先改。
5. V8、V9、V10 每版 cr4 打分，最弱三处私信。

## ctrl 的口径（09:26，节点推送）
1. pushed=no 但 gh 重推成功：不用管，继续跑，不算事故。
2. pushed=no 且 gh 重推也失败，或推送后远端没有提交：立即停下，把节点编号、op 号、完整报错发 ctrl。
3. 谁也不要改节点上的令牌、凭据，也不要改 nodejob.sh。
有第二台报同样的事，一起报 ctrl。

## materials（a1，09:26）
1. windows 重交 841ef7db 已合（总装 0496865e），包里没占位图了；a1 复查新头。
2. 真机看板（s1 分支 renders/real/obs/）：m1 看 v10 仪表板的发光和叠层，chart 看 v06 炉火窗和 v07、v09、v10 的内衬；评审私信来的材质毛病当场改，【交付】给 a1，随到随合。
3. 天进着色器：成品群系是 the_void，占用表里没有按群系染色的方块，谁要放水或植物先找 a1；a1 回 a2。
4. 材质板随窗重出；a1。
清单外的打磨（铁梯重画等）先放下。

八份清单 09:27 都到齐：props、common、sky+motion、main、site、machines、interiors、materials。

## 跨类派的（aide，续）
- tower → 和 clkrm 分钟室（clkrm 09:28 还没有自己的提交），09:30。
- rec → 帮 sdome 的 interiors/astroroom，09:34。
- m3 → 帮 a4（重走的量或者栏杆墩），09:43（cable 的活 09:41 结束）。
- astro → 帮 lights（入口到蓄电池室这一路），09:49（batteryroom 第一版 4373c72 已交 cr4）。
- clkrm 09:44：c77b2a64 第一版加场景已推，合了 tower 的壳 ffba0d15；09:55 赶不上，09:29 告诉了 cr4，门先关着，目标 10:25 前过关口。
- vault 09:36：platevault 第一版 de1db354 已交（09:37 合），接着把 power 的暗房件和升降机（2c0b2eae）接进来。
