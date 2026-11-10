import fs from 'node:fs';
import path from 'node:path';

function patchHeadlessBot(filePath) {
  let src = fs.readFileSync(filePath, 'utf8');

  const sIdx = src.indexOf('export function createHeadlessBot(');
  const endMarker = '// ============================================================================\n// WORKER THREAD IMPLEMENTATION';
  const endMarkerCRLF = '// ============================================================================\r\n// WORKER THREAD IMPLEMENTATION';

  let eIdx = src.indexOf(endMarker);
  if (eIdx < 0) eIdx = src.indexOf(endMarkerCRLF);
  if (sIdx < 0 || eIdx < 0) {
    throw new Error(`Markers not found in ${filePath} (sIdx=${sIdx}, eIdx=${eIdx})`);
  }

  const replacement = `export function createHeadlessBot(bot, { onResult, onGameInit, onGamePacket, onSpawnRequest, onRotateProxy, getStrategySource, mintTurnstileToken }) {
  const { port, socksPort, donorChromePort, slot } = bot;
  const name = bot.name;
  let seq = 0;
  const pending = new Map();

  const client = {
    port,
    socksPort,
    donorChromePort,
    name: bot.name,
    slot,
    isHeadless: true,
    freshToken: false,
    wasInGame: false,
    lastReloadAt: 0,
    enteredLobbyAt: 0,
    enteredGameAt: 0,
    minting: false,
    mintStartedAt: 0,
    evalTimeouts: 0,
    worker: null,
    send() {},
    respawnWorker(reason = 'watchdog') {
      console.warn(\`[\${this.name}] [WATCHDOG] Respawning Worker (\${reason})...\`);
      for (const [, fn] of pending) {
        try { fn(null); } catch {}
      }
      pending.clear();
      this.evalTimeouts = 0;
      this.freshToken = false;
      this.wasInGame = false;
      this.minting = false;
      const oldW = this.worker;
      this.worker = null;
      if (oldW) {
        try { oldW.removeAllListeners(); } catch {}
        try { oldW.terminate(); } catch {}
      }
      spawnWorker();
    },
    evalJs(expression, awaitPromise = false) {
      return new Promise((resolve) => {
        if (!this.worker) return resolve(null);
        const id = ++seq;
        const timer = setTimeout(() => {
          if (pending.has(id)) {
            pending.delete(id);
            this.evalTimeouts = (this.evalTimeouts || 0) + 1;
            if (this.evalTimeouts >= 3) {
              this.respawnWorker(\`\${this.evalTimeouts} consecutive evalJs timeouts\`);
            }
            resolve(null);
          }
        }, 4500);
        pending.set(id, (val) => {
          clearTimeout(timer);
          this.evalTimeouts = 0;
          resolve(val);
        });
        try {
          this.worker.postMessage({ type: 'eval', id, expression, awaitPromise });
        } catch {
          clearTimeout(timer);
          pending.delete(id);
          resolve(null);
        }
      });
    },
    mintToken() {
      const now = Date.now();
      if (this.minting && now - (this.mintStartedAt || 0) < 22000) return;
      this.minting = true;
      this.mintStartedAt = now;
      console.log(\`[\${this.name}] (Worker) Requesting Turnstile token from Chrome :\${donorChromePort}...\`);
      Promise.race([
        mintTurnstileToken(donorChromePort),
        new Promise((_, rej) => setTimeout(() => rej(new Error('mintTurnstileToken hard timeout 20s')), 20000))
      ])
        .then((tok) => {
          this.minting = false;
          // Wait for worker 'token_imported' before setting freshToken = true!
          this.worker?.postMessage({
            type: 'token',
            token: tok,
            strategySource: getStrategySource()
          });
        })
        .catch((err) => {
          this.minting = false;
          console.error(\`[\${this.name}] (Worker) Turnstile mint error on :\${donorChromePort}:\`, err.message);
        });
    }
  };

  function spawnWorker() {
    const w = new Worker(new URL(import.meta.url), {
      execArgv: [],
      workerData: { bot, strategySource: getStrategySource() }
    });
    client.worker = w;

    w.on('message', (msg) => {
      client.lastMsgAt = Date.now();
      client.evalTimeouts = 0;
      if (msg.type === 'eval_res') {
        const fn = pending.get(msg.id);
        if (fn) {
          pending.delete(msg.id);
          fn(msg.value);
        }
      } else if (msg.type === 'need_token') {
        client.freshToken = false;
        client.enteredLobbyAt = 0;
      } else if (msg.type === 'token_imported') {
        client.freshToken = true;
        console.log(\`[\${client.name}] (Worker) Fresh Turnstile token ready & v27team (slot=\${slot}) imported!\`);
      } else if (msg.type === 'log') {
        console.log(\`[\${client.name}]\`, msg.text);
        if (msg.text.includes('socket close index 3') || msg.text.includes('socket close index 2')) {
          client.evalJs(\`(() => {
            const d = window.dictionary, g = d && window[d.game];
            const activeSockOpen = typeof b1 === "object" && b1?.z?.ef && (b1.z.ef(2) || b1.z.ef(3));
            if (!activeSockOpen && g && g[d.sbLeave] && g[d.gameState] !== 0) {
              g[d.sbLeave](true);
            }
          })()\`);
        }
        if (msg.text.includes('error 4563') || msg.text.includes('error 4530')) {
          // Stagger re-entry after 4563/4530 lobby disconnect to prevent reconnect stampede
          client.enteredLobbyAt = Date.now() - 12000 + (slot * 300);
        }
        if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4576') || msg.text.includes('error 4229')) {
          client.freshToken = false;
          client.enteredLobbyAt = 0;
          if ((msg.text.includes('error 4577') || msg.text.includes('error 4576')) && typeof onRotateProxy === 'function') {
            onRotateProxy(client);
          } else if (msg.text.includes('error 4577') || msg.text.includes('error 4576')) {
            if (socksPort) {
              const s = net.connect(socksPort, '127.0.0.1');
              let stg = 0, b = Buffer.alloc(0);
              s.on('error', () => {});
              s.on('connect', () => s.write(Buffer.from([0x05, 0x01, 0x00])));
              s.on('data', (c) => {
                b = Buffer.concat([b, c]);
                if (stg === 0 && b.length >= 2) {
                  stg = 1;
                  const hb = Buffer.from('rotate.proxy.local', 'utf8');
                  const req = Buffer.alloc(4 + 1 + hb.length + 2);
                  req[0] = 0x05; req[1] = 0x01; req[2] = 0x00; req[3] = 0x03;
                  req[4] = hb.length; hb.copy(req, 5); req.writeUInt16BE(80, 5 + hb.length);
                  s.write(req);
                } else if (stg === 1 && b.length >= 10) {
                  try { s.destroy(); } catch {}
                }
              });
            }
          }
          if (msg.text.includes('error 4577') && typeof onRotateProxy !== 'function') {
            client.evalJs(\`(() => {
              localStorage.setItem("d105", "");
              localStorage.setItem("d106", "");
              localStorage.setItem("v105", "0");
              localStorage.setItem("v106", "0");
              const setSetting = bm?.qq?.qr || bm?.qo?.qp;
              if (typeof bm === "object" && typeof setSetting === "function") {
                setSetting.call(bm.qq || bm.qo, 105, "");
                setSetting.call(bm.qq || bm.qo, 106, "");
              }
            })()\`);
          }
          if (msg.text.includes('error 4229')) {
            client.evalJs(\`(() => { const d = window.dictionary, g = d && window[d.game]; if (g && g[d.sbLeave] && g[d.gameState] !== 0) g[d.sbLeave](true); })()\`);
          }
        }
      } else if (msg.type === 'result') {
        client.wasInGame = false;
        client.enteredGameAt = 0;
        if (onResult) onResult(client, msg.payload);
      } else if (msg.type === 'game_init') {
        client.wasInGame = true;
        client.enteredGameAt = Date.now();
        client.enteredLobbyAt = 0;
        if (onGameInit) onGameInit(client, msg.initData);
      } else if (msg.type === 'game_pkt') {
        if (onGamePacket) onGamePacket(client, msg.pkt);
      } else if (msg.type === 'spawn_req') {
        if (onSpawnRequest) onSpawnRequest(client, msg);
      }
    });

    w.on('error', (err) => {
      console.error(\`[\${client.name}] Worker error:\`, err.message);
    });

    w.on('exit', (code) => {
      if (client.worker === w) {
        console.warn(\`[\${client.name}] Worker exited unexpectedly (code=\${code}), respawning in 1s...\`);
        setTimeout(() => {
          if (client.worker === w) client.respawnWorker(\`exit code \${code}\`);
        }, 1000);
      }
    });
  }

  spawnWorker();
  return client;
}

`;

  src = src.slice(0, sIdx) + replacement + src.slice(eIdx);
  fs.writeFileSync(filePath, src, 'utf8');
  console.log('Patched headless-bot:', filePath);
}

function patchSquadFile(filePath, isC116) {
  let src = fs.readFileSync(filePath, 'utf8');

  // 1. Safe log write stream ('a' flag + error handler)
  src = src.replace(
    "const __logStream = fs.createWriteStream('tsb-apex-squad.log', { flags: 'w' });",
    "const __logStream = fs.createWriteStream('tsb-apex-squad.log', { flags: 'a' }); __logStream.on('error', () => {});"
  );
  src = src.replace(
    "const __logStream = fs.createWriteStream('tsb-team-squad.log', { flags: 'w' });",
    "const __logStream = fs.createWriteStream('tsb-team-squad.log', { flags: 'a' }); __logStream.on('error', () => {});"
  );

  // 2. Replace global taskkill /F /IM firefox.exe in c116 with port-scoped kill
  src = src.replace(
    "try { execSync('taskkill /F /IM firefox.exe', { stdio: 'ignore' }); } catch {}",
    `try { execSync(\`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'firefox.exe' -and $_.CommandLine -match 'firefox_donor_\${port}' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"\`, { stdio: 'ignore' }); } catch {}`
  );

  // 3. Auto-recycle Firefox Donor on 2 consecutive mint timeouts
  if (!src.includes('donor._mintFailCount')) {
    src = src.replace(
      "if (typeof tok0 === 'string' && tok0.length > 100) {\n        return tok0;\n      }",
      "if (typeof tok0 === 'string' && tok0.length > 100) {\n        donor._mintFailCount = 0;\n        return tok0;\n      }"
    );
    src = src.replace(
      "if (typeof tok0 === 'string' && tok0.length > 100) {\r\n        return tok0;\r\n      }",
      "if (typeof tok0 === 'string' && tok0.length > 100) {\r\n        donor._mintFailCount = 0;\r\n        return tok0;\r\n      }"
    );

    const recycleSnippet = isC116
      ? `donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 2) {
      donor._mintFailCount = 0;
      console.warn('[FIREFOX-DONOR] 2 consecutive mint timeouts on :' + donor.port + ' -> recycling Firefox donor...');
      try { donor.ws.close(); } catch {}
      if (firefoxDonor === donor) firefoxDonor = null;
      import('node:child_process').then(({ execSync }) => {
        try { execSync(\`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'firefox.exe' -and $_.CommandLine -match 'firefox_donor_\${donor.port}' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"\`, { stdio: 'ignore' }); } catch {}
      }).catch(() => {});
    }
    throw new Error('Firefox BiDi mint timeout');`
      : `donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 2) {
      donor._mintFailCount = 0;
      console.warn('[FIREFOX-DONOR] 2 consecutive mint timeouts on :' + donor.port + ' -> recycling Firefox donor...');
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      import('node:child_process').then(({ execSync }) => {
        try { execSync(\`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'firefox.exe' -and $_.CommandLine -match 'firefox_donor_\${donor.port}' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"\`, { stdio: 'ignore' }); } catch {}
      }).catch(() => {});
    }
    throw new Error('Firefox BiDi mint timeout');`;

    src = src.replace("throw new Error('Firefox BiDi mint timeout');", recycleSnippet);
  }

  // 4. Add non-reentrant mutex guard __syncTickBusy to the main 2500ms setInterval loop
  if (!src.includes('__syncTickBusy')) {
    src = src.replace(
      /setInterval\(async \(\) => \{\r?\n  if \(clients\.length < HEADLESS_BOTS\.length\) return;/,
      `let __syncTickBusy = false;\nsetInterval(async () => {\n  if (__syncTickBusy || clients.length < HEADLESS_BOTS.length) return;\n  __syncTickBusy = true;\n  try {\n    const rssMB = Math.round(process.memoryUsage().rss / 1048576);\n    if (rssMB > 3200 && !clients.some((c) => c.wasInGame)) {\n      console.warn(\`[MEM-WATCHDOG] RSS=\${rssMB}MB (>3200MB) while idle -> recycling all Worker threads!\`);\n      for (const c of clients) { if (c.respawnWorker) c.respawnWorker('RSS memory guard'); }\n    }`
    );

    const lastIntervalClose = src.lastIndexOf('}, 2500);');
    if (lastIntervalClose >= 0) {
      src = src.slice(0, lastIntervalClose) + '  } finally {\n    __syncTickBusy = false;\n  }\n}, 2500);' + src.slice(lastIntervalClose + 9);
    }
  }

  // 5. Fix lobbyFailCount >= 4 tight loop by also updating c.enteredLobbyAt = now
  src = src.replace(
    /if \(c\.lobbyFailCount >= 4\) \{\r?\n\s*c\.freshToken = false;\r?\n\s*c\.lobbyFailCount = 0;\r?\n\s*continue;\r?\n\s*\}/,
    `if (c.lobbyFailCount >= 4) {\n        c.freshToken = false;\n        c.lobbyFailCount = 0;\n        c.enteredLobbyAt = now;\n        continue;\n      }`
  );

  fs.writeFileSync(filePath, src, 'utf8');
  console.log('Patched squad file:', filePath);
}

patchHeadlessBot(path.resolve('headless-bot.mjs'));
patchHeadlessBot(path.resolve('../c110/headless-bot.mjs'));
patchSquadFile(path.resolve('tsb-apex-squad.mjs'), true);
patchSquadFile(path.resolve('../c110/tsb-team-squad.mjs'), false);
console.log('ALL PATCHES APPLIED SUCCESSFULLY');
