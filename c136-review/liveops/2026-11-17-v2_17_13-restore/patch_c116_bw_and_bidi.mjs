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
        function cleanGlyph(t, thStart) {
          const d = chamfer(t);
          let th = thStart;
          let cnt = 0;
          for (let i = 0; i < 16384; i++) if (d[i] >= th) cnt++;
          if (cnt < 140) th = Math.min(th, 7);
          if (cnt < 70) th = Math.min(th, 6);
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
          const minKeep = Math.max(12, Math.floor(maxLen * 0.10));
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
        function prep(raw, thStart) {
          const g = cleanGlyph(raw, thStart);
          let sx = 0, sy = 0, n = 0;
          for (let i = 0; i < 16384; i++) {
            if (g[i]) { sx += (i & 127); sy += (i >> 7); n++; }
          }
          if (n < 30) return null;
          const cx = sx / n, cy = sy / n;
          let sr2 = 0;
          for (let i = 0; i < 16384; i++) {
            if (g[i]) {
              const dx = (i & 127) - cx, dy = (i >> 7) - cy;
              sr2 += dx * dx + dy * dy;
            }
          }
          return { g, cx, cy, n, rRms: Math.max(8, Math.sqrt(sr2 / n)) };
        }
        function render32(info, rotRad, dxShift, dyShift) {
          const g = info.g, cx = info.cx, cy = info.cy, rRms = info.rRms;
          const out = new Float32Array(1024);
          const cosA = Math.cos(rotRad), sinA = Math.sin(rotRad);
          const scale = rRms / 9.2;
          for (let gy = 0; gy < 32; gy++) {
            const uy = (gy - 15.5 - dyShift) * scale;
            for (let gx = 0; gx < 32; gx++) {
              const ux = (gx - 15.5 - dxShift) * scale;
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
          let sum = 0;
          for (let y = 0; y < 32; y++) {
            for (let x = 0; x < 32; x++) {
              let s = out[(y << 5) + x] * 10;
              if (y > 0) s += out[((y - 1) << 5) + x] * 1.5;
              if (y < 31) s += out[((y + 1) << 5) + x] * 1.5;
              if (x > 0) s += out[(y << 5) + x - 1] * 1.5;
              if (x < 31) s += out[(y << 5) + x + 1] * 1.5;
              blur[(y << 5) + x] = s;
              sum += s;
            }
          }
          const mean = sum / 1024;
          let norm2 = 0;
          for (let i = 0; i < 1024; i++) {
            blur[i] -= mean;
            norm2 += blur[i] * blur[i];
          }
          const inv = norm2 > 0 ? 1 / Math.sqrt(norm2) : 0;
          for (let i = 0; i < 1024; i++) blur[i] *= inv;
          return blur;
        }
        const rawTiles = [];
        for (let i = 0; i < 17; i++) rawTiles.push(dec(pB[i]));
        const shifts = [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1]];
        function runWithTh(thStart) {
          const refInfo = prep(rawTiles[0], thStart);
          if (!refInfo) return { reload: true, top: 0, bestGap: 0, maskFallback: 0, countFallback: 0 };
          const refRots = [];
          for (let deg = 0; deg < 360; deg += 5) {
            const rad = (deg * Math.PI) / 180;
            for (let s = 0; s < shifts.length; s++) {
              refRots.push(render32(refInfo, rad, shifts[s][0], shifts[s][1]));
            }
          }
          const scores = new Float32Array(16);
          for (let i = 0; i < 16; i++) {
            const ci = prep(rawTiles[i + 1], thStart);
            if (!ci) { scores[i] = 0; continue; }
            const cv = render32(ci, 0, 0, 0);
            let best = -1;
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
            if (sorted[k] < 0.75) break;
            const gap = sorted[k] - sorted[k + 1];
            if (gap > bestGap && sorted[k + 1] < 0.80) {
              bestGap = gap;
              bestCutIdx = k;
            }
          }
          let maskFallback = 0;
          let countFallback = 0;
          if (bestCutIdx >= 0) {
            const thF = (sorted[bestCutIdx] + sorted[bestCutIdx + 1]) / 2;
            for (let i = 0; i < 16; i++) {
              if (scores[i] >= thF) { maskFallback |= (1 << i); countFallback++; }
            }
          } else {
            let maxG = 0, cutF = 0;
            for (let k = 0; k < 9; k++) {
              const g = sorted[k] - sorted[k + 1];
              if (g > maxG) { maxG = g; cutF = k; }
            }
            const thF = (sorted[cutF] + sorted[cutF + 1]) / 2;
            for (let i = 0; i < 16; i++) {
              if (scores[i] >= thF) { maskFallback |= (1 << i); countFallback++; }
            }
          }
          if (sorted[0] < 0.86 || bestCutIdx < 0 || bestGap < 0.095) {
            return { reload: true, top: Number(sorted[0].toFixed(3)), bestGap: Number(bestGap.toFixed(3)), maskFallback, countFallback };
          }
          const thresh = (sorted[bestCutIdx] + sorted[bestCutIdx + 1]) / 2;
          let mask = 0;
          for (let i = 0; i < 16; i++) {
            if (scores[i] >= thresh) mask |= (1 << i);
          }
          return { reload: false, mask, top: Number(sorted[0].toFixed(3)), thresh: Number(thresh.toFixed(3)), bestGap: Number(bestGap.toFixed(3)), count: bestCutIdx + 1 };
        }
        let res = runWithTh(8);
        if (res.reload) {
          const r7 = runWithTh(7);
          if (!r7.reload || r7.bestGap > res.bestGap) res = r7;
        }
        return res;
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
        if ((res.reload || !res.mask) && (window.__bwReloadStreak || 0) < 3) {
          window.__bwReloadStreak = (window.__bwReloadStreak || 0) + 1;
          const delay = 800 + Math.floor(Math.random() * 350);
          setTimeout(() => { try { sendCaptchaAns.call(holder, 0, 0, oN, pow); } catch {} }, delay);
        } else {
          const finalMask = res.mask || res.maskFallback || 0;
          const finalCnt = res.count || res.countFallback || 0;
          window.__bwReloadStreak = 0;
          if (!finalMask) {
            window.__bwCooldownUntil = Date.now() + 25000;
            if (window.__hlLog) window.__hlLog("[BW-SOLVE] oN=" + oN + " empty mask -> cooldown 25s");
            return;
          }
          if (window.__hlLog) {
            window.__hlLog("[BW-SOLVE] oN=" + oN + " mask=0x" + finalMask.toString(16) + " count=" + finalCnt + " top=" + res.top + " gap=" + res.bestGap + (res.reload ? " (fallback)" : "") + " (" + ms + "ms)");
          }
          const delay = 1100 + Math.floor(Math.random() * 600);
          setTimeout(() => { try { if (!b1?.z?.ef || b1.z.ef(oN)) sendCaptchaAns.call(holder, finalMask, pA, oN, pow); } catch {} }, delay);
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

// Match mint guard timeout to serialized donor budget (130s) and widen 4563 reconnect stagger
const hbOldMintGuard = `      if (this.minting && now - (this.mintStartedAt || 0) < 95000) return;
      this.minting = true;
      this.mintStartedAt = now;
      console.log(\`[\${this.name}] (Worker) Requesting Turnstile token from Chrome :\${donorChromePort}...\`);
      Promise.race([
        mintTurnstileToken(donorChromePort),
        new Promise((_, rej) => setTimeout(() => rej(new Error('mintTurnstileToken hard timeout 90s')), 90000))
      ])`;
const hbNewMintGuard = `      if (this.minting && now - (this.mintStartedAt || 0) < 135000) return;
      this.minting = true;
      this.mintStartedAt = now;
      console.log(\`[\${this.name}] (Worker) Requesting Turnstile token from Chrome :\${donorChromePort}...\`);
      Promise.race([
        mintTurnstileToken(donorChromePort),
        new Promise((_, rej) => setTimeout(() => rej(new Error('mintTurnstileToken hard timeout 130s')), 130000))
      ])`;
if (!hb.includes(hbOldMintGuard)) throw new Error('hbOldMintGuard not found');
hb = hb.replace(hbOldMintGuard, hbNewMintGuard);

const hbOld4563 = `        if (msg.text.includes('error 4563') || msg.text.includes('error 4530')) {
          // Stagger re-entry after 4563/4530 lobby disconnect to prevent reconnect stampede
          client.enteredLobbyAt = Date.now() - 12000 + (slot * 300);
        }`;
const hbNew4563 = `        if (msg.text.includes('error 4563') || msg.text.includes('error 4530')) {
          // Stagger re-entry after 4563/4530 lobby disconnect to prevent reconnect stampede
          client.enteredLobbyAt = Date.now() - 9500 + (slot * 380);
        }`;
if (!hb.includes(hbOld4563)) throw new Error('hbOld4563 not found');
hb = hb.replace(hbOld4563, hbNew4563);

fs.writeFileSync(hbPath, hb, 'utf8');
console.log('Patched', hbPath, 'len=', hb.length);

// Patch tsb-apex-squad.mjs
let sqNorm = sq.replace(/\r\n/g, '\n');

// 1. Async killFirefoxOnPort (no event-loop freeze), clean profile sessionstore prefs, about:blank launch,
// serialized per-donor queue with internal deadline (eliminates overlapping relaunch/BiDi lock races)
const sqOldKillBlock = `import { execSync } from 'node:child_process';
function killFirefoxOnPort(port) {
  try {
    execSync(\`powershell -NoProfile -Command "$pids = @(Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess); $pids += @(Get-CimInstance Win32_Process -Filter \\"Name='firefox.exe'\\" | Where-Object { $_.CommandLine -match 'firefox_donor_\${port}' -or $_.CommandLine -match '--remote-debugging-port \${port}' } | Select-Object -ExpandProperty ProcessId); foreach ($p in ($pids | Select-Object -Unique)) { if ($p -gt 0) { taskkill /F /T /PID $p 2>$null | Out-Null; Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }; for ($i=0; $i -lt 12; $i++) { if (-not (Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Milliseconds 250 }"\`, { stdio: 'ignore' });
  } catch {}
}`;
const sqNewKillBlock = `import { execSync, execFile } from 'node:child_process';
function killFirefoxOnPort(port) {
  return new Promise((resolve) => {
    const cmd = \`$pids = @(Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess); $pids += @(Get-CimInstance Win32_Process -Filter "Name='firefox.exe'" | Where-Object { $_.CommandLine -match 'firefox_donor_\${port}' -or $_.CommandLine -match '--remote-debugging-port \${port}' } | Select-Object -ExpandProperty ProcessId); foreach ($p in ($pids | Select-Object -Unique)) { if ($p -gt 0) { taskkill /F /T /PID $p 2>$null | Out-Null; Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }; for ($i=0; $i -lt 12; $i++) { if (-not (Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Milliseconds 200 }\`;
    try {
      execFile('powershell', ['-NoProfile', '-Command', cmd], { timeout: 7000, windowsHide: true }, () => resolve());
    } catch {
      resolve();
    }
  });
}`;
if (!sqNorm.includes(sqOldKillBlock)) throw new Error('sqOldKillBlock not found');
sqNorm = sqNorm.replace(sqOldKillBlock, sqNewKillBlock);

const sqOldProfTail = `user_pref("focusmanager.testmode", true);
\${proxyPrefs}\`;
  fs.writeFileSync(path.join(profDir, 'user.js'), prefs, 'utf8');`;
const sqNewProfTail = `user_pref("focusmanager.testmode", true);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.sessionstore.max_tabs_undo", 0);
user_pref("browser.startup.page", 0);
user_pref("browser.startup.homepage", "about:blank");
\${proxyPrefs}\`;
  fs.writeFileSync(path.join(profDir, 'user.js'), prefs, 'utf8');
  try { fs.rmSync(path.join(profDir, 'sessionstore-backups'), { recursive: true, force: true }); } catch {}
  for (const sf of ['sessionstore.jsonlz4', 'recovery.jsonlz4', 'recovery.baklz4']) {
    try { fs.unlinkSync(path.join(profDir, sf)); } catch {}
  }`;
if (!sqNorm.includes(sqOldProfTail)) throw new Error('sqOldProfTail not found');
sqNorm = sqNorm.replace(sqOldProfTail, sqNewProfTail);

const sqOldInitLaunch = `  let ws = await tryConnectBidi();
    if (!ws && fs.existsSync(ffExe)) {
      killFirefoxOnPort(port);
      await new Promise((r) => setTimeout(r, 600));
      try { fs.unlinkSync(path.join(profDir, 'parent.lock')); } catch {}
      try { fs.unlinkSync(path.join(profDir, '.startup-incomplete')); } catch {}
      if (typeof ensureFirefoxProfile === 'function') ensureFirefoxProfile(profDir, (typeof portToSocks === 'object' && portToSocks[port]) || 0);
      console.log(\`[FIREFOX-DONOR] Launching Mozilla Firefox on port \${port}...\`);
      const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], {
        detached: true,
        stdio: 'ignore'
      });
      child.unref();
      for (let retry = 0; retry < 18; retry++) {
        await new Promise((r) => setTimeout(r, 1000));
        ws = await tryConnectBidi();
        if (ws) break;
      }
    }`;
const sqNewInitLaunch = `  let ws = await tryConnectBidi();
    if (!ws && fs.existsSync(ffExe)) {
      await killFirefoxOnPort(port);
      await new Promise((r) => setTimeout(r, 600));
      try { fs.unlinkSync(path.join(profDir, 'parent.lock')); } catch {}
      try { fs.unlinkSync(path.join(profDir, '.startup-incomplete')); } catch {}
      if (typeof ensureFirefoxProfile === 'function') ensureFirefoxProfile(profDir, (typeof portToSocks === 'object' && portToSocks[port]) || 0);
      console.log(\`[FIREFOX-DONOR] Launching Mozilla Firefox on port \${port}...\`);
      const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'about:blank'], {
        detached: true,
        stdio: 'ignore'
      });
      child.unref();
      await new Promise((r) => setTimeout(r, 1500));
      for (let retry = 0; retry < 20; retry++) {
        await new Promise((r) => setTimeout(r, 900));
        ws = await tryConnectBidi();
        if (ws) break;
      }
    }`;
if (!sqNorm.includes(sqOldInitLaunch)) throw new Error('sqOldInitLaunch not found');
sqNorm = sqNorm.replace(sqOldInitLaunch, sqNewInitLaunch);

const sqOldBidiTimer = `      pending.delete(id);
      resolve(null);
    }, 12000);`;
const sqNewBidiTimer = `      pending.delete(id);
      resolve(null);
    }, 18000);`;
if (!sqNorm.includes(sqOldBidiTimer)) throw new Error('sqOldBidiTimer not found');
sqNorm = sqNorm.replace(sqOldBidiTimer, sqNewBidiTimer);

const sqOldSessionLock = `  let sess = null;
  for (let sTry = 0; sTry < 3; sTry++) {
    sess = await callBidi('session.new', { capabilities: {} });
    if (sess?.result?.sessionId) break;
    if (sess?.error && String(sess.error).includes('session not created') && String(sess.message || '').includes('already')) break;
    await new Promise((r) => setTimeout(r, 900));
  }
  if (!sess?.result?.sessionId) {
    console.log(\`[FIREFOX-DONOR] BiDi session locked by previous process -> recycling Firefox donor on :\${port}...\`);
    try { ws.close(); } catch {}
    killFirefoxOnPort(port);
    await new Promise((r) => setTimeout(r, 800));
    if (relaunchDepth >= 2) throw new Error(\`Firefox BiDi session.new keeps failing on port \${port}\`);
    return _initFirefoxDonor(port, relaunchDepth + 1);
  }`;
const sqNewSessionLock = `  await new Promise((r) => setTimeout(r, 350));
  let sess = null;
  for (let sTry = 0; sTry < 3; sTry++) {
    sess = await callBidi('session.new', { capabilities: {} });
    if (sess?.result?.sessionId) break;
    if (sess?.error && String(sess.error).includes('session not created') && String(sess.message || '').includes('already')) break;
    await new Promise((r) => setTimeout(r, 1200));
  }
  if (!sess?.result?.sessionId) {
    console.log(\`[FIREFOX-DONOR] BiDi session.new failed on :\${port} (reply=\${JSON.stringify(sess).slice(0, 180)}) -> recycling Firefox donor...\`);
    try { await callBidi('session.end', {}); } catch {}
    try { ws.close(); } catch {}
    await killFirefoxOnPort(port);
    await new Promise((r) => setTimeout(r, 2500));
    if (relaunchDepth >= 2) throw new Error(\`Firefox BiDi session.new keeps failing on port \${port}\`);
    return _initFirefoxDonor(port, relaunchDepth + 1);
  }`;
if (!sqNorm.includes(sqOldSessionLock)) throw new Error('sqOldSessionLock not found');
sqNorm = sqNorm.replace(sqOldSessionLock, sqNewSessionLock);

const sqOldMintChain = `async function mintViaDonorChrome(requestedDonorPort = 9228) {
  if (mintsLastHour() >= mintKnobs().cap) throw new Error('hourly Cloudflare budget used up');
  const donorPort = pickMintDonor();
  if (!donorPort) throw new Error('no donor free (all busy or paused)');
  const mintStartDelay = mintInflightTotal() * 2500;
  mintStamps.push(Date.now());
  if (donorPort === 9228) mihomoMintStamps.push(Date.now());
  try { fs.writeFileSync(mintStampFile, JSON.stringify(mintStamps)); } catch {}
  donorLastUsedAt.set(donorPort, Date.now());
  donorMintInflight.set(donorPort, (donorMintInflight.get(donorPort) || 0) + 1);
  const doOne = async () => {
    const stepStartedAt = Date.now();
    if (mintStartDelay) await new Promise((r) => setTimeout(r, mintStartDelay));
    const donor = await ensureFirefoxDonor(donorPort);
  const runMint = async () => {
    const { callBidi, ctx } = donor;
    let tsReady = false;
    for (let w = 0; w < 15; w++) {
      const tsChk = await callBidi('script.evaluate', {
        expression: 'typeof window.turnstile?.render',
        target: { context: ctx },
        awaitPromise: false
      });
      if (tsChk?.result?.result?.value === 'function') { tsReady = true; break; }
      await new Promise((r) => setTimeout(r, 600));
    }
    if (!tsReady) {
      await callBidi('browsingContext.navigate', { context: ctx, url: 'https://territorial.io/', wait: 'complete' });
      for (let w = 0; w < 12; w++) {
        await new Promise((r) => setTimeout(r, 600));
        const tsChk = await callBidi('script.evaluate', {
          expression: 'typeof window.turnstile?.render',
          target: { context: ctx },
          awaitPromise: false
        });
        if (tsChk?.result?.result?.value === 'function') { tsReady = true; break; }
      }
    }
    if (!tsReady) {
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      killFirefoxOnPort(donor.port);
      throw new Error('Turnstile API not loaded on :' + donor.port);
    }`;
const sqNewMintChain = `async function mintViaDonorChrome(requestedDonorPort = 9228) {
  if (mintsLastHour() >= mintKnobs().cap) throw new Error('hourly Cloudflare budget used up');
  const donorPort = pickMintDonor();
  if (!donorPort) throw new Error('no donor free (all busy or paused)');
  const mintStartDelay = mintInflightTotal() * 2000;
  donorLastUsedAt.set(donorPort, Date.now());
  donorMintInflight.set(donorPort, (donorMintInflight.get(donorPort) || 0) + 1);
  const doOne = async () => {
    const stepStartedAt = Date.now();
    const hardDeadline = stepStartedAt + 115000;
    if (mintStartDelay) await new Promise((r) => setTimeout(r, mintStartDelay));
    const donor = await ensureFirefoxDonor(donorPort);
  const runMint = async () => {
    const { callBidi, ctx } = donor;
    const spMap = { 9229: 10824, 9230: 10827, 9231: 10830 };
    const isDirectDonor = fs.existsSync(path.join(__dirname, 'tsb-donor-direct.flag'));
    let tsReady = false;
    for (let w = 0; w < 12 && Date.now() < hardDeadline - 25000; w++) {
      const tsChk = await callBidi('script.evaluate', {
        expression: 'typeof window.turnstile?.render',
        target: { context: ctx },
        awaitPromise: false
      });
      if (tsChk?.result?.result?.value === 'function') { tsReady = true; break; }
      await new Promise((r) => setTimeout(r, 700));
    }
    if (!tsReady && Date.now() < hardDeadline - 20000) {
      if (!isDirectDonor && spMap[donor.port]) {
        try { await rotateSocksSession(spMap[donor.port]); } catch {}
      }
      await callBidi('browsingContext.navigate', { context: ctx, url: 'https://territorial.io/', wait: 'complete' });
      for (let w = 0; w < 18 && Date.now() < hardDeadline - 12000; w++) {
        await new Promise((r) => setTimeout(r, 750));
        const tsChk = await callBidi('script.evaluate', {
          expression: 'typeof window.turnstile?.render',
          target: { context: ctx },
          awaitPromise: false
        });
        if (tsChk?.result?.result?.value === 'function') { tsReady = true; break; }
      }
    }
    if (!tsReady) {
      donor._navFailCount = (donor._navFailCount || 0) + 1;
      if (donor._navFailCount >= 2) {
        donor._navFailCount = 0;
        try { donor.ws.close(); } catch {}
        firefoxDonors.delete(donor.port);
        await killFirefoxOnPort(donor.port);
      }
      throw new Error('Turnstile API not loaded on :' + donor.port);
    }
    donor._navFailCount = 0;
    mintStamps.push(Date.now());
    if (donorPort === 9228) mihomoMintStamps.push(Date.now());
    try { fs.writeFileSync(mintStampFile, JSON.stringify(mintStamps)); } catch {}`;
if (!sqNorm.includes(sqOldMintChain)) throw new Error('sqOldMintChain not found');
sqNorm = sqNorm.replace(sqOldMintChain, sqNewMintChain);

const sqOldDoOneRace = `    console.log(\`[FIREFOX-DONOR] mint gave no token on :\${donor.port} after \${Math.round((Date.now() - stepStartedAt) / 1000)}s (clicks=\${mintClicks}\${mintErrNote ? ', cf_error=' + mintErrNote : ', no answer from the widget'})\`);
    const spMap = { 9229: 10824, 9230: 10827, 9231: 10830 };
    const isDirectDonor = fs.existsSync(path.join(__dirname, 'tsb-donor-direct.flag'));
    if (!isDirectDonor && spMap[donor.port]) {
      try {
        await rotateSocksSession(spMap[donor.port]);
        console.log(\`[FIREFOX-DONOR] Rotated proxy on :\${donor.port} (:\${spMap[donor.port]})\`);
      } catch {}
    }
    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 4) {
      donor._mintFailCount = 0;
      console.warn(\`[FIREFOX-DONOR] 4 consecutive mint failures on :\${donor.port} -> recycling Firefox donor!\`);
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      killFirefoxOnPort(donor.port);
    }
    throw new Error(mintErrNote ? 'Turnstile error ' + mintErrNote : 'Firefox BiDi mint timeout');
  };

  return await runMint();
  };
  const doOneTimed = () => Promise.race([
    doOne(),
    new Promise((_, rej) => setTimeout(() => rej(new Error('donor chain step 92s timeout')), 92000))
  ]);
  const prev = donorMintChains.get(donorPort) || Promise.resolve();
  const next = prev.then(doOneTimed, doOneTimed);`;
const sqNewDoOneRace = `    console.log(\`[FIREFOX-DONOR] mint gave no token on :\${donor.port} after \${Math.round((Date.now() - stepStartedAt) / 1000)}s (clicks=\${mintClicks}\${mintErrNote ? ', cf_error=' + mintErrNote : ', no answer from the widget'})\`);
    if (!isDirectDonor && spMap[donor.port]) {
      try {
        await rotateSocksSession(spMap[donor.port]);
        console.log(\`[FIREFOX-DONOR] Rotated proxy on :\${donor.port} (:\${spMap[donor.port]})\`);
      } catch {}
    }
    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 4) {
      donor._mintFailCount = 0;
      console.warn(\`[FIREFOX-DONOR] 4 consecutive mint failures on :\${donor.port} -> recycling Firefox donor!\`);
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      await killFirefoxOnPort(donor.port);
    }
    throw new Error(mintErrNote ? 'Turnstile error ' + mintErrNote : 'Firefox BiDi mint timeout');
  };

  return await runMint();
  };
  const prev = donorMintChains.get(donorPort) || Promise.resolve();
  const next = prev.then(doOne, doOne);`;
if (!sqNorm.includes(sqOldDoOneRace)) throw new Error('sqOldDoOneRace not found');
sqNorm = sqNorm.replace(sqOldDoOneRace, sqNewDoOneRace);

const sqOldMintDeadline = `    const mintDeadline = Math.min(Date.now() + 75000, stepStartedAt + 86000);`;
const sqNewMintDeadline = `    const mintDeadline = Math.min(Date.now() + 68000, hardDeadline - 4000);`;
if (!sqNorm.includes(sqOldMintDeadline)) throw new Error('sqOldMintDeadline not found');
sqNorm = sqNorm.replace(sqOldMintDeadline, sqNewMintDeadline);

// 2. Remove eh(5) Propaganda spam completely and track myLobbyRealName
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
        const myLobbyRealName = myLobbyObj ? (myLobbyObj.aGM || myLobbyObj.username || null) : null;`;
if (!sqNorm.includes(sqOldEh5)) throw new Error('sqOldEh5 not found');
sqNorm = sqNorm.replace(sqOldEh5, sqNewEh5);

const sqOldSetLobbyUser = `        s.myLobbyUsername = myLobbyUsername;`;
const sqNewSetLobbyUser = `        s.myLobbyUsername = myLobbyUsername;\n        s.myLobbyRealName = myLobbyRealName;`;
if (!sqNorm.includes(sqOldSetLobbyUser)) throw new Error('sqOldSetLobbyUser not found');
sqNorm = sqNorm.replace(sqOldSetLobbyUser, sqNewSetLobbyUser);

// 3. Instant Redacted detection via s.myLobbyRealName
const sqOldRedactedChk = `      if (s.myLobbyUsername.includes('Redacted')) {`;
const sqNewRedactedChk = `      if (s.myLobbyUsername.includes('Redacted') || (typeof s.myLobbyRealName === 'string' && s.myLobbyRealName.includes('Redacted'))) {`;
if (!sqNorm.includes(sqOldRedactedChk)) throw new Error('sqOldRedactedChk not found');
sqNorm = sqNorm.replace(sqOldRedactedChk, sqNewRedactedChk);

// 4. Use recognized clan tag [APEX] and NEVER fall back to unrecognized 'V7K' on rotateClanTag!
const sqOldClanPool = `const CLAN_TAG_POOL = [
  "V7K", "R4P", "N2X", "Q8M", "Z3L", "K9T", "M5J", "T2W", "H6C", "B4F",
  "X9D", "P3V", "J7R", "C2N", "L8G", "W4S", "F6Y", "D5H", "G3K", "S8P",
  "A4Z", "E9M", "U2C", "Y5B", "V3N", "R8X", "K4D", "M9W", "T7L", "H2Q"
];
let activeClanTag = CLAN_TAG_POOL[Math.floor(Math.random() * CLAN_TAG_POOL.length)];
let recentRedactedAtList = [];
function rotateClanTag(reason = 'match-end') {
  const choices = CLAN_TAG_POOL.filter((t) => t !== activeClanTag);
  activeClanTag = choices[Math.floor(Math.random() * choices.length)] || 'V7K';
  console.log(\`[STEALTH] Active match clan tag rotated (\${reason}) -> [\${activeClanTag}]\`);
  return activeClanTag;
}`;
const sqNewClanPool = `const CLAN_TAG_POOL = ["APEX"];
let activeClanTag = "APEX";
let recentRedactedAtList = [];
function rotateClanTag(reason = 'match-end') {
  const choices = CLAN_TAG_POOL.filter((t) => t !== activeClanTag);
  activeClanTag = choices.length > 0 ? choices[Math.floor(Math.random() * choices.length)] : (CLAN_TAG_POOL[0] || 'APEX');
  console.log(\`[STEALTH] Active match clan tag rotated (\${reason}) -> [\${activeClanTag}]\`);
  return activeClanTag;
}`;
if (!sqNorm.includes(sqOldClanPool)) throw new Error('sqOldClanPool not found');
sqNorm = sqNorm.replace(sqOldClanPool, sqNewClanPool);

// 5. Initialize & reset bots with [APEX] tag, align verifiedApexIndices with hasRightTag,
// and stop retag storm when Server 1 stripped tag on a "Player XX" slot
const sqOldBotInitName = `  bot.baseName = candidateBase;
  bot.name = candidateBase;`;
const sqNewBotInitName = `  bot.baseName = candidateBase;
  bot.name = ('[' + activeClanTag + '] ' + candidateBase).slice(0, 20);`;
if (!sqNorm.includes(sqOldBotInitName)) throw new Error('sqOldBotInitName not found');
sqNorm = sqNorm.replace(sqOldBotInitName, sqNewBotInitName);

const sqOldPostMatchReset = `    for (const c of clients) {
      if (c.isHeadless) {
        c.name = c.baseName;
        c.retaggingUntil = 0;
        c.retagTargetRoomId = 0;
      }
    }`;
const sqNewPostMatchReset = `    for (const c of clients) {
      if (c.isHeadless) {
        c.name = ('[' + activeClanTag + '] ' + c.baseName).slice(0, 20);
        c.retaggingUntil = 0;
        c.retagTargetRoomId = 0;
      }
    }`;
if (!sqNorm.includes(sqOldPostMatchReset)) throw new Error('sqOldPostMatchReset not found');
sqNorm = sqNorm.replace(sqOldPostMatchReset, sqNewPostMatchReset);

const sqOldVerified = `      !s.myLobbyUsername.includes('Redacted') &&
      !s.myLobbyUsername.startsWith('Player ');`;
const sqNewVerified = `      !s.myLobbyUsername.includes('Redacted') &&
      !s.myLobbyUsername.startsWith('Player ') &&
      s.myLobbyUsername.startsWith(\`[\${activeClanTag}]\`);`;
if (!sqNorm.includes(sqOldVerified)) throw new Error('sqOldVerified not found');
sqNorm = sqNorm.replace(sqOldVerified, sqNewVerified);

const sqOldWantTag = `      const wantTag = allowReady && targetRoomId > 0 && !waitMode;`;
const sqNewWantTag = `      const curLobbyStr0 = String(states[idx]?.myLobbyUsername || '');
      const hasCustomNameUnlocked = curLobbyStr0.length > 0 && !curLobbyStr0.includes('Player ') && !curLobbyStr0.includes('Redacted');
      const wantTag = !isStandby && !waitMode && (hasCustomNameUnlocked ? (allowReady && targetRoomId > 0) : true);`;
if (!sqNorm.includes(sqOldWantTag)) throw new Error('sqOldWantTag not found');
sqNorm = sqNorm.replace(sqOldWantTag, sqNewWantTag);

const sqOldRetag = `      let triggerRetag = false;
      if (states[idx]?.lobby?.inLobby && states[idx]?.lobby?.room === 0 && now > (c.retaggingUntil || 0)) {
        if (wantTag) globalThis.__holdUntagUntil = now + 8000;
        if (wantTag && !hasRightTag) {
          triggerRetag = true;
          c.retaggingUntil = now + 4500;
          c.retagTargetRoomId = targetRoomId;
        } else if (!wantTag && hasAnyTag && now > (globalThis.__holdUntagUntil || 0)) {
          triggerRetag = true;
          c.retaggingUntil = now + 4500;
          c.retagTargetRoomId = 0;
        }
      }`;
const sqNewRetag = `      let triggerRetag = false;
      if (hasRightTag) c.retagFailStreak = 0;
      if (states[idx]?.lobby?.inLobby && states[idx]?.lobby?.room === 0 && curLobbyUser && now > (c.retaggingUntil || 0)) {
        if (wantTag) globalThis.__holdUntagUntil = now + 8000;
        if (wantTag && !hasRightTag) {
          if (curLobbyUser.startsWith('Player ')) {
            c.retaggingUntil = now + 300000;
            c.retagFailStreak = 0;
          } else {
            c.retagFailStreak = (c.retagFailStreak || 0) + 1;
            if (c.retagFailStreak <= 1) {
              triggerRetag = true;
              c.retaggingUntil = now + 7000;
              c.retagTargetRoomId = targetRoomId;
            } else {
              c.retaggingUntil = now + 180000;
              c.retagFailStreak = 0;
            }
          }
        } else if (!wantTag && hasAnyTag && now > (globalThis.__holdUntagUntil || 0)) {
          triggerRetag = true;
          c.retaggingUntil = now + 5000;
          c.retagTargetRoomId = 0;
        }
      }`;
if (!sqNorm.includes(sqOldRetag)) throw new Error('sqOldRetag not found');
sqNorm = sqNorm.replace(sqOldRetag, sqNewRetag);

// 6. Do not burn Turnstile tokens on 4563 lobby bounces (only invalidate after 24 consecutive failures),
// widen entry jitter to prevent 4563 bursts, and sync d122 + bm.qq.qr before openMultiplayer(0)
const sqOldFailCnt = `      c.lobbyFailCount = (c.lobbyFailCount || 0) + 1;
      if (c.lobbyFailCount >= 4) {
        c.freshToken = false;
        c.lobbyFailCount = 0;
        c.enteredLobbyAt = now;
        continue;
      }
      c.enteredLobbyAt = now;
      const enterJitterMs = i * 65 + Math.floor(Math.random() * 80);
      setTimeout(() => {
        c.evalJs(\`(() => {`;
const sqNewFailCnt = `      c.lobbyFailCount = (c.lobbyFailCount || 0) + 1;
      if (c.lobbyFailCount >= 24) {
        c.freshToken = false;
        c.lobbyFailCount = 0;
        c.enteredLobbyAt = now;
        continue;
      }
      c.enteredLobbyAt = now;
      const enterJitterMs = i * 180 + Math.floor(Math.random() * 180);
      setTimeout(() => {
        c.evalJs(\`(() => {
          try {
            localStorage.setItem("d122", \${JSON.stringify(c.name)});
            localStorage.setItem("v122", "0");
            if (typeof bm === "object" && bm?.buffer?.data?.[122]) bm.buffer.data[122].value = \${JSON.stringify(c.name)};
            if (typeof bm === "object" && typeof bm?.qq?.qr === "function") bm.qq.qr(122, \${JSON.stringify(c.name)});
          } catch {}`;
if (!sqNorm.includes(sqOldFailCnt)) throw new Error('sqOldFailCnt not found');
sqNorm = sqNorm.replace(sqOldFailCnt, sqNewFailCnt);

fs.writeFileSync(sqPath, sqNorm, 'utf8');
console.log('Patched', sqPath, 'len=', sqNorm.length);
