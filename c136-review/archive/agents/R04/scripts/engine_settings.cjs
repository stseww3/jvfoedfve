// 读每局的引擎开局设置（只读；用未改动的线上客户端把录像头读进来，不往后跑）。
// 用法：node scripts/engine_settings.cjs <局号> [<局号> …]
// 输出：aE.lC（进攻比例上限模式：只有等于 10 时引擎才把单次出兵压到余额的 25%）、真人数 aE.ku、
//       队伍字段 aE.a0L、捐款开关 aE.iT。
const { startReplay } = require('./engine_replay.cjs');
for (const m of process.argv.slice(2)) {
  try {
    const { h } = startReplay(m);
    console.log([m, 'lC=' + h.run('aE.lC'), 'ku=' + h.run('aE.ku'), 'a0L=' + h.run('aE.a0L'), 'iT=' + h.run('aE.iT')].join('\t'));
  } catch (e) {
    console.log(m + '\t出错 ' + String(e).slice(0, 120));
  }
}
