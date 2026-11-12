// util.mjs — 命令行参数、确定性随机、分位数、小工具。

export function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const eq = a.indexOf('=');
    if (eq > 0) { o[a.slice(2, eq)] = a.slice(eq + 1); continue; }
    const k = a.slice(2);
    const v = argv[i + 1];
    if (v === undefined || v.startsWith('--')) o[k] = true;
    else { o[k] = v; i++; }
  }
  return o;
}

export const num = (v, d) => (v === undefined || v === true || v === '' || Number.isNaN(+v) ? d : +v);
export const list = (v) => (v === undefined || v === true || v === '' ? [] : String(v).split(',').map((s) => s.trim()).filter(Boolean));

// 32 位整数散列（确定性：同一组键两臂、两次运行得到同一个数）
export function hash32(...ks) {
  let h = 0x9e3779b9 | 0;
  for (const k0 of ks) {
    let k = k0 | 0;
    k = Math.imul(k ^ (k >>> 16), 0x85ebca6b);
    k = Math.imul(k ^ (k >>> 13), 0xc2b2ae35);
    k ^= k >>> 16;
    h = Math.imul(h ^ k, 0x01000193) + 0x165667b1 | 0;
    h ^= h >>> 15;
  }
  h = Math.imul(h ^ (h >>> 16), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return (h ^ (h >>> 16)) >>> 0;
}
// [0,1) 的确定性小数
export const hashU = (...ks) => hash32(...ks) / 4294967296;
// [a, b] 的确定性整数
export const hashInt = (a, b, ...ks) => a + (hash32(...ks) % (b - a + 1));

export function strHash(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return h >>> 0;
}

// mulberry32：有状态的小随机数发生器（对手原型用）
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function quantile(arr, q) {
  if (!arr.length) return NaN;
  const a = arr.slice().sort((x, y) => x - y);
  const i = (a.length - 1) * q;
  const lo = Math.floor(i), hi = Math.ceil(i);
  return a[lo] + (a[hi] - a[lo]) * (i - lo);
}
export const median = (arr) => quantile(arr, 0.5);
export const mean = (arr) => (arr.length ? arr.reduce((s, x) => s + x, 0) / arr.length : NaN);
export const sum = (arr) => arr.reduce((s, x) => s + x, 0);

// 与 tools/make_packs.py 的 fnv() 同一个算法：每个数按 4 个字节（低位在前）过 FNV-1a
export function fnvU32(vals) {
  let h = 0x811c9dc5;
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i] >>> 0;
    h ^= v & 0xff; h = Math.imul(h, 0x01000193);
    h ^= (v >>> 8) & 0xff; h = Math.imul(h, 0x01000193);
    h ^= (v >>> 16) & 0xff; h = Math.imul(h, 0x01000193);
    h ^= v >>> 24; h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

export const pct = (a, b, d = 1) => (b > 0 ? (100 * a / b).toFixed(d) + '%' : '-');
export const fmtN = (x) => (x === null || x === undefined || Number.isNaN(x) ? '-' : Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(2) + 'M' : Math.abs(x) >= 1e4 ? (x / 1e3).toFixed(1) + 'k' : String(Math.round(x * 100) / 100));
export const ceil7 = (x) => 7 * Math.ceil(x / 7);
