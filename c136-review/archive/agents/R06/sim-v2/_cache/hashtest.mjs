import { hashU } from '../lib/util.mjs';
const gauss = (u1, u2) => Math.sqrt(-2 * Math.log(Math.max(1e-9, u1))) * Math.cos(2 * Math.PI * u2);
const Phi = (z) => { const x = Math.abs(z) / Math.SQRT2, t = 1 / (1 + 0.3275911 * x); const erf = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x); return z >= 0 ? 0.5 * (1 + erf) : 0.5 * (1 - erf); };
for (const sd of [1, 2, 3, 12345]) {
  for (const N of [100, 2000]) {
    const zs = [], sl = [], u1 = [], u2 = [];
    for (let p = 0; p < N; p++) { zs.push(gauss(hashU(sd, p, 907), hashU(sd, p, 908))); sl.push(gauss(hashU(sd, p, 930, 1), hashU(sd, p, 930, 2))); u1.push(hashU(sd, p, 907)); u2.push(hashU(sd, p, 908)); }
    const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
    const vr = (a) => { const m = mean(a); return a.reduce((s, x) => s + (x - m) ** 2, 0) / a.length; };
    const corr = (a, b) => { const ma = mean(a), mb = mean(b); let s = 0; for (let i = 0; i < a.length; i++) s += (a[i] - ma) * (b[i] - mb); return s / a.length / Math.sqrt(vr(a) * vr(b)); };
    const q5 = [0, 0, 0, 0, 0], qz = [0, 0, 0, 0, 0], qu = [0, 0, 0, 0, 0];
    for (let p = 0; p < N; p++) { const b = (Math.sqrt(0.45) * zs[p] + Math.sqrt(0.49) * sl[p]) / Math.sqrt(0.94); q5[Math.min(4, Math.floor(Phi(b) * 5))]++; qz[Math.min(4, Math.floor(Phi(zs[p]) * 5))]++; qu[Math.min(4, Math.floor(u1[p] * 5))]++; }
    console.log(`seed ${sd} N ${N}: var zs ${vr(zs).toFixed(3)} var slow ${vr(sl).toFixed(3)} corr(zs,slow) ${corr(zs, sl).toFixed(3)} corr(u1,u2) ${corr(u1, u2).toFixed(3)} mean u1 ${mean(u1).toFixed(3)} | q5 base ${q5.join('/')} | q5 zs ${qz.join('/')} | q5 u1 ${qu.join('/')}`);
  }
}
