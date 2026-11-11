#!/usr/bin/env node
// engine-evidence.mjs — 把规格书引用的每一处引擎代码按「类.成员 + 正则」定位出来，输出原文行和字符偏移。
// 只读：不执行引擎代码。规格书里的「出处」一栏都指向这里的条目编号。
//
// 用法：node engine-evidence.mjs > ../out/engine-evidence.txt
// 每条：编号 | 说明 | 定位（类.成员 @成员在原文件里的字符偏移）| 命中的排版后源码行
// 某条正则没有命中或命中次数不符，会在末尾列出 MISSING / COUNT，退出码 1。
import { loadEngine, resolve, pretty } from './engine-extract.mjs';

// [编号, 说明, 定位, 正则, 期望命中次数(可省略=至少1)]
const ITEMS = [
  // ---- 版本与时间
  ['V1', '版本号 2.17.1', 'dM', /var dz = 2;|var e0 = 17;|var e1 = 1;/, 3],
  ['T1', '每拍名义时长 56 ms', 'dX', /this\.aEY = 56;/, 1],
  ['T2', '联机循环：每个服务器回合包推进 7 拍', 'af2.af6', /this\.af1 !== this\.aK3 \* 7/, 1],
  ['T3', '联机循环：积压时一次补跑一个回合剩下的 af4-1 拍', 'af2', /this\.af4 = 7;/, 1],
  ['T4', '一拍内各子系统的执行顺序（n8）', 'n8', /^\s+(b2|aH|ao|af|b5|aG|ap|bQ\.z|am|aW|b0|bY|ag|aX|bS|aV|aQ|b9|aO|b6|aS|ax|bg|bk|b1\.z|b1\.nC|u|bX\.eS|bC|bi)\.(ee|n9|nA|nB)\(\);/],
  ['T5', '单机循环：按 bi.aEY 的整数倍推进，不补拍', 'afN.ee', /eZ \+= bi\.aEY \* Math\.floor\(1 \+ \(bi\.eZ - eZ\) \/ bi\.aEY\)/, 1],
  // ---- 常量
  ['C1', '全局常量：最多 512 人、兵力硬顶 15e8、软上限顶 1e9、欠款顶 5e4、每格基础成本 2、硬上限倍数 150', 'c5',
    /this\.fW = 512;|this\.a6e = 15e8;|this\.a7X = 1e9;|this\.a6n = 5e4;|this\.gt = 2;|this\.a6d = 150;/, 6],
  ['C2', '整数除法 g0(a,b)=floor((a+0.5)/b)', 'c1.g0', /return Math\.floor\(\(fs \+ \.5\) \/ ft\);/, 1],
  ['C3', '整数开方 aQk（牛顿迭代）', 'aQk', /ej = bO\.g0\(ej \+ bO\.g0\(g1, ej\), 2\);|var ej = bO\.g0\(g1 \+ 1, 2\);/, 2],
  // ---- 经济
  ['E1', '利息每 10 拍结算（t%10==9）', 'cd.ee', /bi\.kr\(\) % 10 !== 9/, 1],
  ['E2', '领土收入每 100 拍结算（t%100==99）', 'cd.aMj', /bi\.kr\(\) % 100 !== 99/, 1],
  ['E3', '利息表：100 + isqrt(25600*i/508)，i=0..511', 'cd.dr', /aMg\[aC\] = kA \+ aMh\(bO\.g0\(aC \* 25600, fZ - 4\), 9\);|var kA = 100;/, 2],
  ['E4', '利息率：查表下标 = floor(511*领土/全图陆地)', 'cd.aMi', /var eH = aMg\[bO\.g0\(\(aE\.fW - 1\) \* ah\.hN\[player\], aE\.ke\)\];/, 1],
  ['E5', '利息率：t<1920 的开局下限 floor(100*(13440-6t)/1920)', 'cd.aMi', /if \(bi\.kr\(\) < 1920\)|eH = Math\.max\(bO\.g0\(100 \* \(13440 - 6 \* bi\.kr\(\)\), 1920\), eH\);/, 2],
  ['E6', '利息率：超过软上限后的扣减 floor(2*r*(B-cap)/cap)，最后夹在 0..700', 'cd.aMi', /eH -= bO\.g0\(2 \* eH \* \(ah\.hb\[player\] - kZ\), kZ\);|return Math\.min\(Math\.max\(eH, 0\), 700\);/, 2],
  ['E7', '软上限 = min(100*领土, 1e9)', 'cd.ka', /return Math\.min\(100 \* ah\.hN\[player\], aE\.a7X\);/, 1],
  ['E8', '离开的真人（状态 2）利息率为 0', 'cd.aMi', /if \(bD\.gv\.kH\(player\) && player < aE\.ku\)/, 1],
  ['E9', '利息入账：max(floor(r*B/1e4),1)，经 gy 入账', 'cd.aMo', /var aMs = bO\.g0\(af\.aEX\(h7\) \* hb\[h7\], 1e4\);|bD\.gv\.gy\(h7, Math\.max\(aMs, 1\)\);/, 2],
  ['E10', '领土收入：默认 tIncomeType=0 → floor(32*领土/32)=领土', 'cd.aMq', /aMu\(32\);/, 1],
  ['E11', '领土收入入账', 'cd.aMu', /bD\.gv\.gy\(h7, bO\.g0\(o7 \* hN\[h7\], 32\)\);/, 1],
  ['E12', '利息倍率类型（默认 iIncomeType=0 → 不缩放）', 'cd.dk', /aE\.data\.iIncomeType === 0/, 1],
  ['E13', '默认场景数据：aIncomeType=0、tIncomeType=0、tIncomeValue=32、iIncomeType=0、iIncomeValue=64', 'a7b',
    /this\.aIncomeType = 0;|this\.tIncomeType = 0;|this\.tIncomeValue = 32;|this\.iIncomeType = 0;|this\.iIncomeValue = 64;/, 5],
  ['E14', '入账 gy：先夹到上限，再入账，再用余额抵欠款', 'a5M.gy', /g1 = this\.a6a\(player, g1\);|ah\.hb\[player\] \+= g1;|var min = Math\.min\(ah\.a6b\[player\], ah\.hb\[player\]\);/, 3],
  ['E15', '入账上限 a6a：min(150*领土-B, 15e8-B)，不小于 0', 'a5M.a6a',
    /g1 = Math\.min\(g1, ah\.hN\[player\] \* aE\.a6d - a6c\);|g1 = Math\.min\(g1, aE\.a6e - a6c\);|return Math\.max\(g1, 0\);/, 3],
  ['E16', '扣款 gw：余额不够时余额清零，差额按 5*(差额>>2) 记欠款，欠款顶 5e4', 'a5M.gw',
    /var gK = 5 \* \(gI >> 2\);|ah\.hb\[player\] = 0;|if \(gM <= aE\.a6n\)|ah\.a6b\[player\] = aE\.a6n;/, 4],
  ['E17', '初始兵力：真人 512', 'cE.adg', /hb\[aC\] = 512;/, 1],
  // ---- 发兵
  ['A1', '陆攻指令处理：报价费率参数 12，最小兵力 0', 'qj.i6', /if \(!bD\.gv\.n2\(player, jC, 12, 0\)\)/, 1],
  ['A2', '报价 n2：兵 = floor(B*(pct+1)/1024)，费 = floor(k*B/1024)，兵 ≤ B-费', 'a5M.n2',
    /var iI = bO\.g0\(a6c \* \(jC \+ 1\), 1024\);|var a6h = bO\.g0\(a6f \* a6c, 1024\);|iI = Math\.min\(iI, a6c - a6h\);/, 3],
  ['A3', '付款 n4：B -= 兵 + 费', 'a5M.n4', /ah\.hb\[player\] -= iI \+ bR\.g6\[1\];/, 1],
  ['A4', '陆攻前置：对局进行中、存活未离开、目标不是自己、目标可打（非队友；死人改成无主地）、有空槽或已在打', 'qj.i6',
    /bD\.gv\.hk\(1\)|bD\.gv\.hl\(player\)|bD\.gv\.rj\(player, k3\)|bD\.gv\.rk\(player, k3\)|if \(!ju && !ae\.kY\(player\)\)/, 5],
  ['A5', '目标解析 rk：≥512 或已死 → 512（无主地）；否则要求 bv.fS（不同队）', 'a5M.rk',
    /k3 = Math\.min\(k3, aE\.fW\);|if \(k3 < aE\.fW && ah\.nU\[k3\] === 0\)|return k3 === aE\.fW \|\| bv\.fS\(player, k3\);/, 3],
  ['A6', '可打判定 fS：自己队号为 0 或与对方队号不同', 'dh.fS', /return bj\.fX\[player\] === 0 \|\| bj\.fX\[player\] !== bj\.fX\[k3\];/, 1],
  ['A7', '战线生成 jt：没有任何战线格 → 失败；新目标且没有新增战线格 → 失败（都发生在付款之前）', 'jg.jt',
    /if \(bR\.fV\[1\] === 0 && ah\.h1\[player\]\.length === 0\)|if \(!ju && bR\.fV\[1\] === ah\.h1\[player\]\.length\)/, 2],
  ['A8', '战线格来源 jw：自己的「边界态」格且四邻有目标的格', 'jg.jw', /if \(ad\.k5\(ah\.hF\[player\]\[aC\]\)\)|ad\.fR\(ah\.hF\[player\]\[aC\] \+ fb\[iQ\]\) === k3/, 2],
  ['A9', '提交 jz：登记进攻槽并进入推进调度（首次等待标记 64）', 'jg.jz', /ae\.ei\(player, bR\.g6\[0\], bR\.fV\[0\]\);|aG\.k1\(player, false\);/, 2],
  ['A10', '进攻槽数：真人 <16 人的局 12 个，否则 8 个；内置 AI 4 个', 'cc.dk', /aMX = aE\.ku < 16 \? 12 : 8;|aMY = 4;/, 2],
  ['A11', '同目标再发兵：并入已有槽，兵力顶 15e8；新目标占新槽并标记「新发」', 'cc.ei',
    /iI\[lp \+ aC\] \+= aMf;|iI\[lp \+ aC\] = iI\[lp \+ aC\] > aE\.a6e \? aE\.a6e : iI\[lp \+ aC\];|aMZ\[lp \+ size\[player\]\] = 1;/, 3],
  ['A12', '撤回 r2：目标夹到 512，要求正在打它，然后 ru', 'qj.r2', /k3 = Math\.min\(k3, aE\.fW\);|if \(!ae\.kF\(player, k3\)\)|ae\.ru\(player, k3\);/, 3],
  ['A13', '撤回 ru：槽里的兵清零并经 gy 回到余额（超上限部分丢失）', 'cc.ru', /this\.ha\(aB1, aMb, 0\);|var aMd = bD\.gv\.gy\(aB1, aMc\);/, 2],
  ['A14', '内置 AI 的陆攻提交 k2：同样收 12/1024 的费，发兵 ≥ 余额一半时费从兵里扣', 'jg.k2',
    /var k4 = bO\.g0\(12 \* ah\.hb\[player\], 1024\);|iI -= iI >= bO\.g0\(ah\.hb\[player\], 2\) \? k4 : 0;|ah\.hb\[player\] -= iI \+ k4;/, 3],
  ['A15', '指令编码：id 4 位 + 玩家 9 位；陆攻 pct 10 位 + 目标 10 位', 'ql.ee', /id = bK\.rU\(4\);|gI = bK\.rU\(9\);|this\.rV\(id, gI, bK\.rU\(10\), bK\.rU\(10\)\);/, 3],
  // ---- 推进调度
  ['S1', '调度 k1：已在表里不重复登记；新登记等待值 64（来自船/山为 2）', 'cA.k1', /nL\[player\] = nR \? 2 : 64;/, 1],
  ['S2', '调度节拍 nM：64→6；领土 <1e3:3、<1e4:2、<6e4:1、否则 0', 'cA.nM',
    /nL\[player\] = 6;|if \(ea < 1e3\)|nL\[player\] = 3;|nL\[player\] = 2;|nL\[player\] = 1;|nL\[player\] = 0;/, 6],
  ['S3', '调度主循环：等待值 64 只换算不推进；等待值减到 0 的那拍推进一步', 'cA.ee', /if \(nL\[nK\[aC\]\] === 64\)|else if \(nL\[nK\[aC\]\]-- === 0\)/, 2],
  ['S4', '全场第一名领土 ≥16 万 / ≥30 万时，大玩家每拍额外推进', 'cA.ee', /if \(ah\.hN\[mV\[0\]\] >= 16e4\)|if \(ah\.hN\[mV\[0\]\] >= 3e5\)/, 2],
  ['S5', '额外推进 nN：只对等待值为 0 且领土 ≥ 阈值的玩家', 'cA.nN', /if \(nL\[nK\[aC\]\] === 0 && ah\.hN\[nK\[aC\]\] >= nP\)/, 1],
  // ---- 推进一步
  ['X1', '战线上限 2048 格', 'gc', /gW = 2048;/, 1],
  ['X2', '推进 gd：先拷贝战线、战线格退回边界态，再按槽号从大到小逐个进攻推进', 'gd', /for \(var aC = ae\.gg\(gQ\) - 1; aC >= 0; aC--\)/, 1],
  ['X3', '拷贝战线 ge：只取战线表前 min(长度,2048) 项', 'ge', /var fZ = Math\.min\(h1\[player\]\.length, gW\);/, 1],
  ['X4', '候选格（打无主地）：战线格四邻中的无主陆地，去重', 'h5', /if \(ga\[h8\] === 0 && ad\.fQ\(h7\)\)/, 1],
  ['X5', '候选格（打玩家）：战线格四邻中属于目标的格，去重', 'h6', /if \(ga\[h8\] === 0 && ad\.h9\(h7\) && ad\.fR\(h7\) === gU\)/, 1],
  ['X6', '没有候选格 → 结束进攻（gp）', 'gh', /if \(gV === 0\)/, 1],
  ['X7', '人均兵 gr：per=floor(兵/候选数)，per>2 才继续；不够且是新发则从余额补到 3*候选数', 'gr',
    /gT = bO\.g0\(gR, gV\);|if \(gT > aE\.gt\)|if \(!gS\)|var gu = gV \* \(1 \+ aE\.gt\);|gR \+= bD\.gv\.gw\(gQ, gu - gR\);/, 6],
  ['X8', '结束进攻 gp：剩余兵经 gy 回余额，最后一个槽结束时退出调度', 'gp', /var ea = bD\.gv\.gy\(gQ, gR\);|aG\.gx\(gQ\);|ae\.h0\(gQ, gP\);/, 3],
  ['X9', '打无主地 hQ：成本 = 2*候选数，必成', 'hQ', /var hd = gV \* aE\.gt;|gR -= hd;|return true;/, 3],
  ['X10', '打玩家 hR：成本 = 2*候选数 + 2*防御 + 对攻兵；可用 = per*候选数；可用 > 成本才占地', 'hR',
    /var hS = gV \* aE\.gt;|var hX = hS \+ 2 \* hT \+ hV;|var hY = gT \* gV;|if \(hY > hX\)/, 4],
  ['X11', '防御量 hU = floor(候选数*目标余额 / (1+floor(10*目标领土/16)))', 'hU', /return bO\.g0\(gV \* ah\.hb\[gU\], 1 \+ bO\.g0\(10 \* ah\.hN\[gU\], 16\)\);/, 1],
  ['X12', '对攻兵 hW = 目标正在打我的那个槽里的兵', 'hW', /return ae\.hc\(gU, gQ\);/, 1],
  ['X13', '新发且无对攻时兵不够：从余额补足「成本-可用+1」后照样占地', 'hR', /if \(gS && hV === 0\)|hY \+= bD\.gv\.gw\(gQ, hX - hY \+ 1\);/, 2],
  ['X14', '兵不够且不满足补足条件：可用兵全部打掉，不占地，进攻结束', 'hR', /hZ\(hY - hS, hV\);\n?|return false;/, 2],
  ['X15', '伤害 hZ：先 1:1 抵消对攻槽里的兵，剩余的一半（向下取整）从目标余额扣，不低于 0', 'hZ',
    /if \(hY <= hV\)|ae\.ha\(gU, gQ, hV - hY\);|hY = bO\.g0\(hY, 2\);|hY = Math\.min\(ah\.hb\[gU\], hY\);|ah\.hb\[gU\] -= hY;/, 5],
  ['X16', '占地 hB：槽内剩余兵写回（不小于 0）、清「新发」标记、领土 += 候选数', 'hB', /ae\.hL\(gQ, gP, gR\);|ae\.hM\(gQ, gP\);|ah\.hN\[gQ\] \+= gV;/, 3],
  ['X17', '新占的格进入战线表和边界表', 'hP', /ah\.h1\[gQ\]\.push\(gX\[aC\]\);|ah\.hF\[gQ\]\.push\(gX\[aC\]\);/, 2],
  ['X18', '失地方 hD：领土 -= 候选数（兵力不随失地另行扣减）', 'dh.hD', /ah\.hN\[gU\] -= gV;/, 1],
  ['X19', '推进后刷新战线 gj：只保留四邻有无主地或他人格的战线格', 'dh.gj', /if \(ad\.fQ\(h7\) \|\| ad\.h9\(h7\) && ad\.fR\(h7\) !== gQ\)/, 1],
  // ---- 淘汰
  ['D1', '存活检查 aOV：领土 ≤ floor(峰值/4) → 崩溃；领土 ≥ 峰值 → 峰值=领土；否则峰值每拍下降 max(1,floor((峰值-领土)/1000))', 'cZ.aOV',
    /if \(ea <= bO\.g0\(lp, 4\)\)|al\.dt\(h7\);|a0i\[h7\] = ea;|a0i\[h7\] = lp - Math\.max\(1, bO\.g0\(lp - ea, 1e3\)\);/, 4],
  ['D2', '崩溃 dt：海上有船 → 只清空领土与兵力但不出局；否则出局', 'cY.dt', /if \(bQ\.z\.ky\[h7\]\)|aL3\(h7\);|this\.aL4\(h7\);/, 4],
  ['D3', '出局 aL4 的顺序：改道进攻者、清领土、清余额、标记死亡、退出调度、清进攻槽、清船', 'cY.aL4',
    /aLC\(player\);|aL8\(player\);|aL9\(player\);|aLD\(player\);|aG\.gx\(player\);|ae\.clear\(player\);|bQ\.aLE\.aLF\(player\);/, 7],
  ['D4', '清领土 aL8：包围盒内属于该玩家的格全部变成无主陆地', 'cY.aL8', /ad\.a19\(h7\);/, 1],
  ['D5', '清余额 aL9：余额与欠款归零', 'cY.aL9', /ah\.hb\[player\] = 0;|ah\.a6b\[player\] = 0;/, 2],
  ['D6', '进攻者改道 aLK：打死者的槽改成打无主地（兵力并入）', 'cc.aLK', /this\.h0\(player, aC\);|this\.ei\(player, aMf, aE\.fW\);/, 2],
  // ---- 交界处（R04 的范围，仅定位）
  ['B1', '捐款 rD：费 = floor(64*捐出方余额/1024)，额 ≤ 余额-费，再夹到受捐方入账上限，≥1 才成立', 'a5M.rD',
    /var a6h = bO\.g0\(64 \* a6c, 1024\);|qv = Math\.min\(qv, a6c - a6h\);|qv = this\.a6a\(qu, qv\);|return qv >= 1;/, 4],
  ['B2', '捐款指令 qv：仅组队局、受捐方存活且是队友、过受捐额度 ao.ei', 'qj.qv', /if \(!aE\.iT\)|bD\.gv\.rn\(player, qu\)|if \(!ao\.ei\(qu, bR\.g6\[0\]\)\)/, 3],
  ['B3', '受捐额度 ca：每个受捐者累计点数不得超过全场额度 aOY（初值 15，每 100 拍 +4/6/8/10）', 'ca',
    /aOY = 15;|aOY \+= 4;|aOY \+= 6;|aOY \+= 8;|aOY \+= 10;|if \(aOX\[a9h\] \+ g1 > aOY\)/, 6],
  ['B4', '受捐点数 aOc：随时间分段', 'ca.aOc',
    /if \(ej >= 3213\)|return 4 \+ bO\.g0\(100 \* aOa, af\.ka\(a9h\)\);|var uv = 1 \+ bO\.g0\(aE\.ke, 300\);|if \(ej < 357\)|if \(ej < 714\)|if \(ej < 1071\)|if \(ej < 2142\)/, 7],
  ['B5', '受捐额度豁免：单机、t≥4284、受捐方是内置 AI/已离开', 'ca.aOb', /return aE\.lE \|\| bi\.kr\(\) >= 4284 \|\| bD\.gv\.kH\(a9h\);/, 1],
  ['B6', '发船/追船报价费率参数 32', 'qj.iB', /if \(!bD\.gv\.n2\(player, jC, 32, 0\)\)/, 1],
  ['B7', '翻山进攻 m6：费 = max(floor(B/10), 1000)', 'a5M.m6', /var a6h = Math\.max\(bO\.g0\(a6c, 10\), 1e3\);/, 1],
];

const eng = loadEngine();
console.log(`# engine-evidence  sha256=${eng.sha}  chars=${eng.src.length}`);
console.log('# 偏移是 JS 字符串下标（UTF-16 码元），以上述 sha256 的 live_game_js.js 为准。');
const bad = [];
for (const [id, note, loc, re, want] of ITEMS) {
  const r = resolve(eng, loc);
  if (!r) {
    bad.push(`${id} MISSING locator ${loc}`);
    continue;
  }
  const lines = pretty(r.node).split('\n');
  const g = new RegExp(re.source, 'g');
  const hits = [];
  lines.forEach((l, i) => {
    const m = l.match(g);
    if (m) hits.push({ i: i + 1, l: l.trim(), n: m.length });
  });
  const n = hits.reduce((s, h) => s + h.n, 0);
  console.log(`\n[${id}] ${note}`);
  console.log(`    定位：${r.label} @${r.node.start}+${r.node.end - r.node.start}`);
  for (const h of hits) console.log(`    L${h.i}: ${h.l}`);
  if (n === 0) bad.push(`${id} MISSING pattern in ${loc}`);
  else if (want !== undefined && n !== want) bad.push(`${id} COUNT ${n} != ${want} in ${loc}`);
}
console.log(`\n# 条目 ${ITEMS.length}，问题 ${bad.length}`);
for (const b of bad) console.log('# ' + b);
process.exit(bad.length ? 1 : 0);
