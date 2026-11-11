// engine_probe.cjs — 在总部的真引擎重放器（src/tools/engine_replay.cjs）里走到指定拍，逐拍打印一段表达式的值。
// 用法：node engine_probe.cjs <局号> <起始拍> <结束拍> '<在引擎作用域里求值的 JS 表达式>'
//   例：node engine_probe.cjs A057 2484 2491 'JSON.stringify({bal: ah.hb[93], boats: bQ.z.ky[93]})'
// 只读；规则全部来自线上客户端原文。
const { startReplay } = require('/agent/repos/c136-data/src/tools/engine_replay.cjs');
const [mid, t0s, t1s, expr] = process.argv.slice(2);
const t0 = +t0s, t1 = +t1s;
const { h, api } = startReplay(mid, {});
let t = 0;
let guard = 0;
while (guard++ < 400000) {
  const r = api.advance(1);
  t = r[0];
  if (!r[1] && t >= t0) {
    let v;
    try { v = h.run(expr); } catch (e) { v = 'ERR ' + e.message; }
    console.log(`t=${t} ${v}`);
  }
  if ((!r[1] && t >= t1) || r[2] === 2) break;
}
