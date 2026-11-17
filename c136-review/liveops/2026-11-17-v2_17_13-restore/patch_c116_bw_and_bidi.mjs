import fs from 'node:fs';
import path from 'node:path';

const c116Dir = path.resolve(process.argv[2] || '../c116');
const hbPath = path.join(c116Dir, 'headless-bot.mjs');
const sqPath = path.join(c116Dir, 'tsb-apex-squad.mjs');

const hbBak = path.join(c116Dir, 'headless-bot.mjs.bak-pre-bw-20261117');
const sqBak = path.join(c116Dir, 'tsb-apex-squad.mjs.bak-pre-bw-20261117');

if (!fs.existsSync(hbBak)) fs.copyFileSync(hbPath, hbBak);
if (!fs.existsSync(sqBak)) fs.copyFileSync(sqPath, sqBak);

let hb = fs.readFileSync(hbBak, 'utf8');
let sq = fs.readFileSync(sqBak, 'utf8');

const BW_AUTO_SOLVER_SNIPPET = `    if (typeof bw === "object" && bw && typeof bw.show === "function" && !bw.__hookedAutoSolve) {
      bw.__hookedAutoSolve = true;
      window.__bwReloadStreak = 0;
      window.__bwCooldownUntil = 0;
      window.__solveBwChallenge = function(pB) {
        function dec(data) {
          const out = new Uint8Array(16384);
          let bp = 0, px = 0, col = 0, n = data.length;
          while (px < 16384) {
            const bi = bp >> 3;
            if (bi >= n) break;
            const sh = bp & 7;
            const w = (data[bi] << 8) | (bi + 1 < n ? data[bi + 1] : 0);
            const run = (w >> (10 - sh)) & 63;
            const endp = Math.min(16384, px + run);
            if (col) out.fill(1, px, endp);
            px = endp; bp += 6; col ^= 1;
          }
          return out;
        }
        function chamfer(t) {
          const d = new Int16Array(16384);
          const INF = 9999;
          for (let y = 0; y < 128; y++) {
            const row = y << 7;
            for (let x = 0; x < 128; x++) {
              const i = row + x;
              if (!t[i]) { d[i] = 0; continue; }
              let v = INF;
              if (y > 0) {
                if (d[i - 128] + 3 < v) v = d[i - 128] + 3;
                if (x > 0 && d[i - 129] + 4 < v) v = d[i - 129] + 4;
                if (x < 127 && d[i - 127] + 4 < v) v = d[i - 127] + 4;
              }
              if (x > 0 && d[i - 1] + 3 < v) v = d[i - 1] + 3;
              d[i] = v;
            }
          }
          for (let y = 127; y >= 0; y--) {
            const row = y << 7;
            for (let x = 127; x >= 0; x--) {
              const i = row + x;
              let v = d[i];
              if (!v) continue;
              if (y < 127) {
                if (d[i + 128] + 3 < v) v = d[i + 128] + 3;
                if (x < 127 && d[i + 129] + 4 < v) v = d[i + 129] + 4;
                if (x > 0 && d[i + 127] + 4 < v) v = d[i + 127] + 4;
              }
              if (x < 127 && d[i + 1] + 3 < v) v = d[i + 1] + 3;
              d[i] = v;
            }
          }
          return d;
        }
        function cleanGlyph(t) {
          const d = chamfer(t);
          let th = 8;
          let cnt = 0;
          for (let i = 0; i < 16384; i++) if (d[i] >= th) cnt++;
          if (cnt < 140) th = 7;
          if (cnt < 70) th = 6;
          const core = new Uint8Array(16384);
          for (let i = 0; i < 16384; i++) if (d[i] >= th) core[i] = 1;
          const vis = new Uint8Array(16384);
          const comps = [];
          let maxLen = 0;
          const q = new Int32Array(16384);
          for (let i = 0; i < 16384; i++) {
            if (core[i] && !vis[i]) {
              let head = 0, tail = 0;
              q[tail++] = i; vis[i] = 1;
              while (head < tail) {
                const u = q[head++];
                const uy = u >> 7, ux = u & 127;
                for (let dy = -1; dy <= 1; dy++) {
                  const ny = uy + dy;
                  if (ny < 0 || ny > 127) continue;
                  for (let dx = -1; dx <= 1; dx++) {
                    if (!dy && !dx) continue;
                    const nx = ux + dx;
                    if (nx < 0 || nx > 127) continue;
                    const ni = (ny << 7) + nx;
                    if (core[ni] && !vis[ni]) { vis[ni] = 1; q[tail++] = ni; }
                  }
                }
              }
              const arr = q.slice(0, tail);
              comps.push(arr);
              if (arr.length > maxLen) maxLen = arr.length;
            }
          }
          const out = new Uint8Array(16384);
          const remArr = new Int16Array(16384);
          let head = 0, tail = 0;
          const minKeep = Math.max(20, Math.floor(maxLen * 0.14));
          for (const comp of comps) {
            if (comp.length >= minKeep) {
              for (let k = 0; k < comp.length; k++) {
                const u = comp[k];
                out[u] = 1;
                remArr[u] = th;
                q[tail++] = u;
              }
            }
          }
          while (head < tail) {
            const u = q[head++];
            const rem = remArr[u];
            if (rem <= 2) continue;
            const uy = u >> 7, ux = u & 127;
            for (let dy = -1; dy <= 1; dy++) {
              const ny = uy + dy;
              if (ny < 0 || ny > 127) continue;
              for (let dx = -1; dx <= 1; dx++) {
                if (!dy && !dx) continue;
                const nx = ux + dx;
                if (nx < 0 || nx > 127) continue;
                const step = (dy && dx) ? 4 : 3;
                const ni = (ny << 7) + nx;
                if (t[ni] && rem - step > remArr[ni]) {
                  if (!out[ni]) { out[ni] = 1; q[tail++] = ni; }
                  remArr[ni] = rem - step;
                }
              }
            }
          }
          return out;
        }
        function norm32(g, rotRad) {
          let sx = 0, sy = 0, n = 0;
          for (let i = 0; i < 16384; i++) {
            if (g[i]) { sx += (i & 127); sy += (i >> 7); n++; }
          }
          const out = new Float32Array(1024);
          if (n < 30) return { v: out, ok: false, n };
          const cx = sx / n, cy = sy / n;
          let sr2 = 0;
          for (let i = 0; i < 16384; i++) {
            if (g[i]) {
              const dx = (i & 127) - cx, dy = (i >> 7) - cy;
              sr2 += dx * dx + dy * dy;
            }
          }
          const r = Math.max(8, Math.sqrt(sr2 / n));
          const cosA = Math.cos(rotRad), sinA = Math.sin(rotRad);
          const scale = r / 9.5;
          for (let gy = 0; gy < 32; gy++) {
            const uy = (gy - 15.5) * scale;
            for (let gx = 0; gx < 32; gx++) {
              const ux = (gx - 15.5) * scale;
              const px = cx + ux * cosA - uy * sinA;
              const py = cy + ux * sinA + uy * cosA;
              const ix = Math.floor(px), iy = Math.floor(py);
              if (ix >= 0 && ix < 127 && iy >= 0 && iy < 127) {
                const fx = px - ix, fy = py - iy;
                const base = (iy << 7) + ix;
                const v00 = g[base], v10 = g[base + 1], v01 = g[base + 128], v11 = g[base + 129];
                out[(gy << 5) + gx] = (v00 * (1 - fx) + v10 * fx) * (1 - fy) + (v01 * (1 - fx) + v11 * fx) * fy;
              }
            }
          }
          const blur = new Float32Array(1024);
          let norm2 = 0;
          for (let y = 0; y < 32; y++) {
            for (let x = 0; x < 32; x++) {
              let s = 0;
              for (let dy = -1; dy <= 1; dy++) {
                const yy = y + dy;
                if (yy < 0 || yy > 31) continue;
                for (let dx = -1; dx <= 1; dx++) {
                  const xx = x + dx;
                  if (xx >= 0 && xx <= 31) s += out[(yy << 5) + xx] * ((dx === 0 && dy === 0) ? 4 : (dx === 0 || dy === 0) ? 2 : 1);
                }
              }
              blur[(y << 5) + x] = s;
              norm2 += s * s;
            }
          }
          const inv = norm2 > 0 ? 1 / Math.sqrt(norm2) : 0;
          for (let i = 0; i < 1024; i++) blur[i] *= inv;
          return { v: blur, ok: true, n };
        }
        const refG = cleanGlyph(dec(pB[0]));
        const refCheck = norm32(refG, 0);
        if (!refCheck.ok) return { reload: true, top: 0, bestGap: 0 };
        const refRots = [];
        for (let deg = -75; deg <= 75; deg += 5) {
          refRots.push(norm32(refG, (deg * Math.PI) / 180).v);
        }
        const scores = new Float32Array(16);
        for (let i = 0; i < 16; i++) {
          const cg = cleanGlyph(dec(pB[i + 1]));
          const cn = norm32(cg, 0);
          if (!cn.ok) { scores[i] = 0; continue; }
          const cv = cn.v;
          let best = 0;
          for (let r = 0; r < refRots.length; r++) {
            const rv = refRots[r];
            let dot = 0;
            for (let k = 0; k < 1024; k++) dot += rv[k] * cv[k];
            if (dot > best) best = dot;
          }
          scores[i] = best;
        }
        const sorted = Array.from(scores).sort((a, b) => b - a);
        let bestGap = 0, bestCutIdx = -1;
        for (let k = 0; k < 13; k++) {
          if (sorted[k] < 0.77) break;
          const gap = sorted[k] - sorted[k + 1];
          if (gap > bestGap && sorted[k + 1] < 0.80) {
            bestGap = gap;
            bestCutIdx = k;
          }
        }
        if (sorted[0] < 0.88 || bestCutIdx < 0 || bestGap < 0.09) {
          return { reload: true, top: Number(sorted[0].toFixed(3)), bestGap: Number(bestGap.toFixed(3)) };
        }
        const thresh = (sorted[bestCutIdx] + sorted[bestCutIdx + 1]) / 2;
        let mask = 0;
        for (let i = 0; i < 16; i++) {
          if (scores[i] >= thresh) mask |= (1 << i);
        }
        return { reload: false, mask, top: Number(sorted[0].toFixed(3)), thresh: Number(thresh.toFixed(3)), bestGap: Number(bestGap.toFixed(3)), count: bestCutIdx + 1 };
      };
      bw.show = function(pB, pA, oN, pow) {
        window.__lastBwChallengeAt = Date.now();
        if (Date.now() < (window.__bwCooldownUntil || 0)) return;
        const t0 = performance.now();
        let res = null;
        try {
          res = window.__solveBwChallenge(pB);
        } catch (err) {
          if (window.__hlLog) window.__hlLog("[BW-ERR] " + (err?.message || err));
          return;
        }
        const ms = (performance.now() - t0).toFixed(1);
        const sendCaptchaAns = b1?.eg?.p8 || b1?.er?.pJ;
        if (typeof sendCaptchaAns !== "function") return;
        const holder = b1?.eg?.p8 ? b1.eg : b1.er;
        if (res.reload || !res.mask) {
          window.__bwReloadStreak = (window.__bwReloadStreak || 0) + 1;
          if (window.__bwReloadStreak > 6) {
            window.__bwReloadStreak = 0;
            window.__bwCooldownUntil = Date.now() + 30000;
            if (window.__hlLog) window.__hlLog("[BW-SOLVE] oN=" + oN + " reload streak > 6 (top=" + res.top + " gap=" + res.bestGap + ") -> cooldown 30s");
            return;
          }
          const delay = 450 + Math.floor(Math.random() * 260);
          setTimeout(() => { try { sendCaptchaAns.call(holder, 0, 0, oN, pow); } catch {} }, delay);
        } else {
          window.__bwReloadStreak = 0;
          if (window.__hlLog) {
            window.__hlLog("[BW-SOLVE] oN=" + oN + " mask=0x" + res.mask.toString(16) + " count=" + res.count + " top=" + res.top + " gap=" + res.bestGap + " (" + ms + "ms)");
          }
          const delay = 480 + Math.floor(Math.random() * 320);
          setTimeout(() => { try { sendCaptchaAns.call(holder, res.mask, pA, oN, pow); } catch {} }, delay);
        }
      };
    }`;

const hbAnchor1 = `    if (typeof ax === "object" && ax && typeof ax.iK === "function" && !ax.__hookedPeaceCaller) {`;
if (!hb.includes(hbAnchor1)) throw new Error('hbAnchor1 not found');
hb = hb.replace(hbAnchor1, `${BW_AUTO_SOLVER_SNIPPET}\n${hbAnchor1}`);

const hbOldNameAssign = `            if (p && (p.aGM || p.aGT || p.aFN || p.aFU)) {
              p.username = p.aGM || p.aGT || p.aFN || p.aFU || p.username;
            }`;
const hbNewNameAssign = `            if (p && !String(p.username || "").startsWith("Player ") && (p.aGM || p.aGT || p.aFN || p.aFU)) {
              p.username = p.aGM || p.aGT || p.aFN || p.aFU || p.username;
            }`;
const hbNorm = hb.replace(/\r\n/g, '\n');
if (!hbNorm.includes(hbOldNameAssign)) throw new Error('hbOldNameAssign not found');
hb = hbNorm.replace(hbOldNameAssign, hbNewNameAssign);

// Also forward [BW-SOLVE] / [BW-ERR] from customConsole / __hlLog (already forwarded via __hlLog -> parentPort 'log')
fs.writeFileSync(hbPath, hb, 'utf8');
console.log('Patched', hbPath, 'len=', hb.length);

// Patch tsb-apex-squad.mjs
let sqNorm = sq.replace(/\r\n/g, '\n');

// 1. BiDi timeout 12000 -> 18000, wait: 'complete' -> 'interactive', relaunchDepth >= 3 + session.end
const sqOldBidiTimer = `      pending.delete(id);
      resolve(null);
    }, 12000);`;
const sqNewBidiTimer = `      pending.delete(id);
      resolve(null);
    }, 18000);`;
if (!sqNorm.includes(sqOldBidiTimer)) throw new Error('sqOldBidiTimer not found');
sqNorm = sqNorm.replace(sqOldBidiTimer, sqNewBidiTimer);

const sqOldSessionLock = `  if (!sess?.result?.sessionId) {
    console.log(\`[FIREFOX-DONOR] BiDi session locked by previous process -> recycling Firefox donor on :\${port}...\`);
    try { ws.close(); } catch {}
    killFirefoxOnPort(port);
    await new Promise((r) => setTimeout(r, 800));
    if (relaunchDepth >= 2) throw new Error(\`Firefox BiDi session.new keeps failing on port \${port}\`);
    return _initFirefoxDonor(port, relaunchDepth + 1);
  }`;
const sqNewSessionLock = `  if (!sess?.result?.sessionId) {
    console.log(\`[FIREFOX-DONOR] BiDi session locked by previous process -> recycling Firefox donor on :\${port}...\`);
    try { await callBidi('session.end', {}); } catch {}
    try { ws.close(); } catch {}
    killFirefoxOnPort(port);
    await new Promise((r) => setTimeout(r, 1200));
    if (relaunchDepth >= 3) throw new Error(\`Firefox BiDi session.new keeps failing on port \${port}\`);
    return _initFirefoxDonor(port, relaunchDepth + 1);
  }`;
if (!sqNorm.includes(sqOldSessionLock)) throw new Error('sqOldSessionLock not found');
sqNorm = sqNorm.replace(sqOldSessionLock, sqNewSessionLock);

sqNorm = sqNorm.replaceAll(
  `await callBidi('browsingContext.navigate', { context: ctx, url: 'https://territorial.io/', wait: 'complete' });`,
  `await callBidi('browsingContext.navigate', { context: ctx, url: 'https://territorial.io/', wait: 'interactive' });`
);

// 2. Replace 3s eh(5) CPU storm with passive Server 1 auto-challenge + 60s gentle fallback + myLobbyRealName
const sqOldEh5 = `        const myLobbyObj = typeof bq === "object" ? (bq?.aFv || bq?.aF0) : null;
        const myLobbyUsername = myLobbyObj ? myLobbyObj.username : null;
        if (myLobbyUsername && (myLobbyUsername.startsWith("Player ") || myLobbyUsername.includes("Redacted")) && typeof b1 === "object" && b1?.eg?.eh && b1?.z?.ef?.(0)) {
          if (!window.__lastNameVerifyAsk || Date.now() - window.__lastNameVerifyAsk > 3000) {
            window.__lastNameVerifyAsk = Date.now();
            try { b1.eg.eh(5); } catch {}
          }
        }`;
const sqNewEh5 = `        const myLobbyObj = typeof bq === "object" ? (bq?.aFv || bq?.aF0) : null;
        const myLobbyUsername = myLobbyObj ? myLobbyObj.username : null;
        const myLobbyRealName = myLobbyObj ? (myLobbyObj.aGM || myLobbyObj.username || null) : null;
        if (
          myLobbyUsername &&
          myLobbyUsername.startsWith("Player ") &&
          !(myLobbyRealName && myLobbyRealName.includes("Redacted")) &&
          typeof b1 === "object" &&
          b1?.eg?.eh &&
          b1?.z?.ef?.(0)
        ) {
          const nowMs = Date.now();
          if (!window.__playerNameSeenSince) window.__playerNameSeenSince = nowMs;
          const bwRecent = window.__lastBwChallengeAt && (nowMs - window.__lastBwChallengeAt < 45000);
          if (!bwRecent && nowMs - window.__playerNameSeenSince > 15000 && (!window.__lastNameVerifyAsk || nowMs - window.__lastNameVerifyAsk > 60000)) {
            window.__lastNameVerifyAsk = nowMs;
            try { b1.eg.eh(5); } catch {}
          }
        } else {
          window.__playerNameSeenSince = 0;
        }`;
if (!sqNorm.includes(sqOldEh5)) throw new Error('sqOldEh5 not found');
sqNorm = sqNorm.replace(sqOldEh5, sqNewEh5);

const sqOldSetLobbyUser = `        s.myLobbyUsername = myLobbyUsername;`;
const sqNewSetLobbyUser = `        s.myLobbyUsername = myLobbyUsername;\n        s.myLobbyRealName = myLobbyRealName;`;
if (!sqNorm.includes(sqOldSetLobbyUser)) throw new Error('sqOldSetLobbyUser not found');
sqNorm = sqNorm.replace(sqOldSetLobbyUser, sqNewSetLobbyUser);

// 3. Instant Redacted detection via s.myLobbyRealName even before bw.show unlock
const sqOldRedactedChk = `      if (s.myLobbyUsername.includes('Redacted')) {`;
const sqNewRedactedChk = `      if (s.myLobbyUsername.includes('Redacted') || (typeof s.myLobbyRealName === 'string' && s.myLobbyRealName.includes('Redacted'))) {`;
if (!sqNorm.includes(sqOldRedactedChk)) throw new Error('sqOldRedactedChk not found');
sqNorm = sqNorm.replace(sqOldRedactedChk, sqNewRedactedChk);

fs.writeFileSync(sqPath, sqNorm, 'utf8');
console.log('Patched', sqPath, 'len=', sqNorm.length);
