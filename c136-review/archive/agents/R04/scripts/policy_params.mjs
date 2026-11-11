// 打印部署版策略 Policy 的实际生效参数（各层默认值合并之后的结果）。
// 用法：node scripts/policy_params.mjs [vb|va|vc|c110] [参数名…]（不给参数名 = 常用的一组）
import { loadPolicy } from './shadow.mjs';
const a = process.argv.slice(2);
const ver = a[0] && /^(vb|va|vc|c110)$/.test(a[0]) ? a.shift() : 'vb';
const mod = await loadPolicy(ver);
const Policy = mod.Policy || mod.default;
const pol = new Policy({}, 0);
const keys = a.length ? a : ['feeK', 'boatFrac', 'boatRange', 'boatEvery', 'maxBoats', 'boatFee', 'idleCap', 'winR', 'botMax', 'coreFrom', 'oppFloorCap', 'pulseFrac', 'minSend', 'period', 'dpEnd', 'aiFrom', 'sharedBotMult', 'quotaGuardMode', 'defendDiscount', 'counterClearMode', 'absorbMode'];
console.log('# 策略版本 ' + ver + ' 的生效参数');
for (const k of keys) console.log(k + ' = ' + JSON.stringify(pol.p[k]));
