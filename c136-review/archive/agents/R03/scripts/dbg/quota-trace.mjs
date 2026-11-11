// 调试：逐拍打印某个号的余额、影子额度 shadowQuota、待核对的 pendingQuotaCheck（act 之前）
// 用法：node dbg/quota-trace.mjs <mid> <bot> <t0> <t1>
import { shadow } from '../shadow.mjs';
const [mid, bot, t0s, t1s] = process.argv.slice(2);
const t0 = +t0s, t1 = +t1s;
shadow(mid, { until: t1 + 1, quiet: true, trace: (g, b, pol) => {
  if (b.bot !== bot || g.t < t0 || g.t > t1) return;
  const me = b.me;
  console.log(JSON.stringify({ t: g.t, B: g.bal[me], L: g.terr[me], sq: Math.round(pol.shadowQuota), nfs: !!pol.isNoFullSend, pc: pol.pendingQuotaCheck ? { ...pol.pendingQuotaCheck, want: Math.round(pol.pendingQuotaCheck.want) } : null, lastQ: pol.lastQuotaTick }));
} });
