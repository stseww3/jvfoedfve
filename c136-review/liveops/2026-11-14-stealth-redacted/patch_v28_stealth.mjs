// Patch tsb-apex-squad.mjs + headless-bot.mjs for:
//   1. Option A Stealth Lobby + Rotating Clan Tag:
//      - Bots use ordinary random names (<= 14 chars) in Room 0 while idle/waiting.
//      - Only the K bots selected by DYNAMIC-POOL put on "[TAG] <baseName>" during the final
//        startsIn <= 17s commit window (reconnecting Server 1 inside the 60-min Turnstile pass).
//      - Tags rotate after every finished match or >= 2 Redacted events in 60s (never [APEX]).
//      - Bots strip the tag back to plain <baseName> as soon as they return to Room 0.
//   2. Account persistence (tsb-accounts.json):
//      - Healthy d105/d106 accounts survive engine restarts; only Redacted/4555 slots rotate.
//      - Redacted slots also rotate to a fresh ordinary baseName + fresh proxy session.
//   3. Turnstile + BiDi fixes:
//      - 4229 in-game disconnect no longer discards a valid 60-min Turnstile pass.
//      - Donor failures (including 300010) immediately rotate that donor's proxy session & reload
//        the donor tab when appropriate; parallel default = 3 across independent residential exits.
//      - _initFirefoxDonor waits for TCP port release on kill and retries session.new up to 3x.
//
// Usage (cwd = c116):
//   node_apex.exe ..\c136\patch_v28_stealth.mjs --dry
//   node_apex.exe ..\c136\patch_v28_stealth.mjs --apply
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const mode = process.argv[2];
const squadTarget = path.resolve(process.argv[3] || 'tsb-apex-squad.mjs');
const headlessTarget = path.resolve(path.dirname(squadTarget), 'headless-bot.mjs');

const report = { mode, ok: false, squadSteps: [], headlessSteps: [] };
const finish = (msg) => {
  if (msg) report.error = msg;
  console.log(JSON.stringify(report));
  process.exit(report.ok ? 0 : 1);
};
if (mode !== '--dry' && mode !== '--apply') finish('usage: --dry | --apply [tsb-apex-squad.mjs]');

function loadSource(file) {
  const raw = fs.readFileSync(file, 'utf8');
  const crlf = (raw.match(/\r\n/g) || []).length;
  const loneLf = (raw.match(/(?<!\r)\n/g) || []).length;
  if (crlf > 0 && loneLf > 0) finish(`mixed line endings in ${path.basename(file)}`);
  return { raw, crlf, s: raw.replace(/\r\n/g, '\n') };
}

const sq = loadSource(squadTarget);
const hb = loadSource(headlessTarget);

if (sq.s.includes('V28-STEALTH-PATCH')) finish('tsb-apex-squad.mjs already patched (V28-STEALTH-PATCH)');
if (hb.s.includes('V28-STEALTH-HB')) finish('headless-bot.mjs already patched (V28-STEALTH-HB)');

function rep(obj, steps, name, anchor, replacement) {
  const n = obj.s.split(anchor).length - 1;
  steps.push(`${name}:${n}`);
  if (n !== 1) finish(`anchor "${name}" found ${n} times, expected 1`);
  obj.s = obj.s.replace(anchor, () => replacement);
}

// --- 1. Patch headless-bot.mjs ---
rep(
  hb,
  report.headlessSteps,
  'hb-4229-keep-token',
  "if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4576') || msg.text.includes('error 4229')) {",
  "// V28-STEALTH-HB: keep 60-min pass on 4229 (in-game lag), only clear on lobby/ban/bot codes\n        if (msg.text.includes('error 4591') || msg.text.includes('error 4215') || msg.text.includes('error 4577') || msg.text.includes('error 4576') || msg.text.includes('error 4555')) {"
);

rep(
  hb,
  report.headlessSteps,
  'hb-mint-send-name',
  `          this.worker?.postMessage({
            type: 'token',
            token: tok,
            strategySource: getStrategySource()
          });`,
  `          this.worker?.postMessage({
            type: 'token',
            token: tok,
            playerName: this.name,
            strategySource: getStrategySource()
          });`
);

rep(
  hb,
  report.headlessSteps,
  'hb-token-playername',
  '            window.__tsbPlayerName = ${JSON.stringify(name)};\n            window.__tsbPlayerColor = 4095;',
  '            window.__tsbPlayerName = ${JSON.stringify(msg.playerName || name)};\n            window.__tsbPlayerColor = 4095;'
);

// --- 2. Patch tsb-apex-squad.mjs ---
rep(
  sq,
  report.squadSteps,
  'sq-stealth-pool-and-accounts',
  'function isC110GatheringInLobby() {',
  `// V28-STEALTH-PATCH: ordinary name pool (<= 14 chars so "[TAG] " + baseName <= 20 chars),
// rotating clan tag, and persistent account storage (tsb-accounts.json).
const STEALTH_NAME_POOL = [
  "KFC", "Sever (rus)", "KUKU", "World empire", "SPQR", "Polska Gurom", "Bismarck",
  "giga_chad", "San Marino", "NoobSlayer", "Vatican City", "TokyoGhoul", "Ottoman",
  "bruh", "404 Not Found", "Roman Empire", "Byzantium", "Prussia", "Holy Roman",
  "Carthage", "Sparta", "Macedon", "Mongol Horde", "Timurid", "Qing Dynasty",
  "Ming", "Shogunate", "Tokugawa", "Takeda", "USSR", "Red Army", "Yugoslavia",
  "Tito", "Habsburg", "Kaiser", "Weimar", "Cossack", "Novgorod", "Muscovy",
  "Tsardom", "Siberia", "Kamchatka", "Alaska", "Texas", "California", "Florida Man",
  "Ohio", "New York", "Chicago", "Dixie", "Cascadia", "Quebec", "Maple Leaf",
  "Aztec", "Maya", "Inca", "Bolivar", "Brazil", "Argentina", "Patagonia", "Chile",
  "Peru", "Cuba", "Panama", "Scotland", "Highlander", "Ireland", "Celtic", "Wales",
  "Normandy", "Brittany", "Burgundy", "Frankia", "Bourbon", "Gaul", "Corsica",
  "Iberia", "Castile", "Aragon", "Catalonia", "Andalusia", "Portugal", "Venice",
  "Genoa", "Sardinia", "Savoy", "Lombardy", "Tuscany", "Florence", "Medici",
  "Caesar", "Augustus", "Trajan", "Aurelian", "Justinian", "Constantine",
  "Hannibal", "Scipio", "Alexander", "Leonidas", "Cleopatra", "Pharaoh",
  "Mamluk", "Saladin", "Abbasid", "Seljuk", "Safavid", "Cyrus", "Darius",
  "Parthia", "Babylon", "Assyria", "Sumer", "Phoenicia", "Palmyra", "Armenia",
  "Georgia", "Khazar", "Bulgar", "Serbia", "Croatia", "Bosnia", "Wallachia",
  "Moldavia", "Hungary", "Magyar", "Bohemia", "Moravia", "Silesia", "Saxony",
  "Bavaria", "Swabia", "Hanover", "Switzerland", "Netherlands", "Orange",
  "Flanders", "Belgium", "Denmark", "Norway", "Sweden", "Finland", "Suomi",
  "Iceland", "Greenland", "Vinland", "Viking", "Ragnar", "Estonia", "Latvia",
  "Lithuania", "Crimea", "Kuban", "Kazan", "Kazakh", "Uzbek", "Manchu", "Tang",
  "Song", "Han", "Qin", "Cao Cao", "Liu Bei", "Sun Quan", "Lu Bu", "Silla",
  "Goryeo", "Joseon", "Yamato", "Sengoku", "Dai Viet", "Khmer", "Angkor", "Siam",
  "Majapahit", "Brunei", "Maurya", "Ashoka", "Chola", "Mughal", "Akbar",
  "Maratha", "Bengal", "Nepal", "Tibet", "Ethiopia", "Mali", "Songhai", "Ghana",
  "Zulu", "Morocco", "Tunis", "Algiers", "Tripoli", "DarkKnight", "GhostRider",
  "SniperWolf", "IceKing", "FireLord", "StormBringer", "TryHard", "CasualPlayer",
  "PizzaTime", "Baguette", "Sushi", "Ramen", "Watermelon", "Banana", "Potato",
  "Cheese", "Heisenberg", "Batman", "Joker", "Spiderman", "Venom", "IronMan",
  "Thanos", "DarthVader", "ObiWan", "MasterChief", "Kratos", "Geralt", "Steve",
  "Creeper", "Enderman", "Cristiano", "Messi", "Mbappe", "Haaland", "Neymar",
  "Zidane", "Ronaldinho", "Modric", "Verstappen", "Hamilton", "Leclerc", "Alonso",
  "Senna", "LeBron", "Curry", "Jordan", "Kobe", "Jokic", "Doncic", "Stockfish",
  "Kasparov", "Fischer", "Naruto", "Sasuke", "Itachi", "Kakashi", "Goku",
  "Vegeta", "Luffy", "Zoro", "Sanji", "Shanks", "Ichigo", "Aizen", "Gojo",
  "Sukuna", "Levi", "Mikasa", "Saitama", "Tanjiro", "Guts", "Lelouch", "Spike",
  "Frieren", "Anya", "Rimuru", "Scorpion", "Raiden", "Ryu", "Ken", "Sephiroth",
  "Cloud", "Link", "Zelda", "Mario", "Luigi", "Bowser", "Kirby", "Pikachu",
  "Charizard", "Mewtwo", "Gengar", "Lucario", "Snorlax", "Doge", "Cheems",
  "Pepe", "Satoshi", "Bitcoin", "Samurai", "Ronin", "Shinobi", "Spartan",
  "Centurion", "Gladiator", "Praetorian", "Varangian", "Janissary"
].filter((n) => n.length >= 2 && n.length <= 14);

const CLAN_TAG_POOL = [
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
}

const accountsFile = path.join(__dirname, 'tsb-accounts.json');
let savedAccounts = {};
try {
  savedAccounts = JSON.parse(fs.readFileSync(accountsFile, 'utf8')) || {};
} catch { savedAccounts = {}; }
function flushSavedAccounts() {
  try { fs.writeFileSync(accountsFile, JSON.stringify(savedAccounts, null, 2), 'utf8'); } catch {}
}

let stealthNameDeck = [];
function pickFreshBaseName(usedSet) {
  for (let tries = 0; tries < STEALTH_NAME_POOL.length * 2; tries++) {
    if (stealthNameDeck.length === 0) {
      stealthNameDeck = STEALTH_NAME_POOL.slice();
      for (let i = stealthNameDeck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        const tmp = stealthNameDeck[i];
        stealthNameDeck[i] = stealthNameDeck[j];
        stealthNameDeck[j] = tmp;
      }
    }
    const cand = stealthNameDeck.pop();
    if (!usedSet || !usedSet.has(cand.toLowerCase())) {
      if (usedSet) usedSet.add(cand.toLowerCase());
      return cand;
    }
  }
  return STEALTH_NAME_POOL[Math.floor(Math.random() * STEALTH_NAME_POOL.length)];
}

const usedBaseNames = new Set();
for (const bot of HEADLESS_BOTS) {
  const rec = savedAccounts[String(bot.slot)] || null;
  if (rec && typeof rec.id === 'string' && rec.id.length >= 4 && typeof rec.pw === 'string' && rec.pw.length >= 4) {
    bot.id = rec.id;
    bot.pw = rec.pw;
  } else {
    bot.id = '';
    bot.pw = '';
  }
  const candidateBase = (rec && typeof rec.baseName === 'string' && rec.baseName.length >= 2 && rec.baseName.length <= 14 && !rec.baseName.includes('['))
    ? rec.baseName
    : pickFreshBaseName(usedBaseNames);
  usedBaseNames.add(candidateBase.toLowerCase());
  bot.baseName = candidateBase;
  bot.name = candidateBase;
}
if (CHROME_BOTS[0] && HEADLESS_BOTS[0]) {
  CHROME_BOTS[0].name = HEADLESS_BOTS[0].baseName;
}
console.log(\`[STEALTH] Initialized \${HEADLESS_BOTS.length} bots with ordinary lobby names (restored \${Object.values(savedAccounts).filter((r) => r && r.id && r.pw).length} saved accounts); initial match tag=[\${activeClanTag}]\`);

function isC110GatheringInLobby() {`
);

rep(
  sq,
  report.squadSteps,
  'sq-kill-wait',
  `function killFirefoxOnPort(port) {
  try {
    execSync(\`powershell -NoProfile -Command "$pids = @(Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess); $pids += @(Get-CimInstance Win32_Process -Filter \\"Name='firefox.exe'\\" | Where-Object { $_.CommandLine -match 'firefox_donor_\${port}' -or $_.CommandLine -match '--remote-debugging-port \${port}' } | Select-Object -ExpandProperty ProcessId); foreach ($p in ($pids | Select-Object -Unique)) { if ($p -gt 0) { taskkill /F /T /PID $p 2>$null | Out-Null; Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }"\`, { stdio: 'ignore' });
  } catch {}
}`,
  `function killFirefoxOnPort(port) {
  try {
    execSync(\`powershell -NoProfile -Command "$pids = @(Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess); $pids += @(Get-CimInstance Win32_Process -Filter \\"Name='firefox.exe'\\" | Where-Object { $_.CommandLine -match 'firefox_donor_\${port}' -or $_.CommandLine -match '--remote-debugging-port \${port}' } | Select-Object -ExpandProperty ProcessId); foreach ($p in ($pids | Select-Object -Unique)) { if ($p -gt 0) { taskkill /F /T /PID $p 2>$null | Out-Null; Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }; for ($i=0; $i -lt 12; $i++) { if (-not (Get-NetTCPConnection -LocalPort \${port} -State Listen -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Milliseconds 250 }"\`, { stdio: 'ignore' });
  } catch {}
}`
);

rep(
  sq,
  report.squadSteps,
  'sq-bidi-session-retry',
  `  const callBidi = (method, params = {}) => new Promise((resolve) => {
    if (ws.readyState !== 1) return resolve(null);
    const id = ++seq;
    const timer = setTimeout(() => {
      pending.delete(id);
      resolve(null);
    }, 8000);
    pending.set(id, (msg) => {
      clearTimeout(timer);
      resolve(msg);
    });
    ws.send(JSON.stringify({ id, method, params }));
  });

  const sess = await callBidi('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) {
    console.log('[FIREFOX-DONOR] BiDi session locked by previous process -> recycling Firefox donor on :9228...');`,
  `  const callBidi = (method, params = {}) => new Promise((resolve) => {
    if (ws.readyState !== 1) return resolve(null);
    const id = ++seq;
    const timer = setTimeout(() => {
      pending.delete(id);
      resolve(null);
    }, 12000);
    pending.set(id, (msg) => {
      clearTimeout(timer);
      resolve(msg);
    });
    ws.send(JSON.stringify({ id, method, params }));
  });

  let sess = null;
  for (let sTry = 0; sTry < 3; sTry++) {
    sess = await callBidi('session.new', { capabilities: {} });
    if (sess?.result?.sessionId) break;
    if (sess?.error && String(sess.error).includes('session not created') && String(sess.message || '').includes('already')) break;
    await new Promise((r) => setTimeout(r, 900));
  }
  if (!sess?.result?.sessionId) {
    console.log(\`[FIREFOX-DONOR] BiDi session locked by previous process -> recycling Firefox donor on :\${port}...\`);`
);

rep(
  sq,
  report.squadSteps,
  'sq-mintknobs-parallel3',
  "mintKnobCache = { at: now, parallel: readInt('tsb-mint-parallel.txt', 1, 4, direct ? 3 : 1), cap: readInt('tsb-mint-hourly-cap.txt', 1, 100, 90) };",
  "mintKnobCache = { at: now, parallel: readInt('tsb-mint-parallel.txt', 1, 4, 3), cap: readInt('tsb-mint-hourly-cap.txt', 1, 100, 90) };"
);

rep(
  sq,
  report.squadSteps,
  'sq-fast-proxy-rotate-on-fail',
  `    console.log(\`[FIREFOX-DONOR] mint gave no token on :\${donor.port} after \${Math.round((Date.now() - stepStartedAt) / 1000)}s (clicks=\${mintClicks}\${mintErrNote ? ', cf_error=' + mintErrNote : ', no answer from the widget'})\`);
    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 5) {
      donor._mintFailCount = 0;
      const spMap = { 9228: 10821, 9229: 10824, 9230: 10827, 9231: 10830 };
      if (spMap[donor.port]) { try { await rotateSocksSession(spMap[donor.port]); } catch {} }
      console.warn('[FIREFOX-DONOR] 2 consecutive mint timeouts on :' + donor.port + ' -> rotated proxy & recycling Firefox donor + fallback to healthy donor!');
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      killFirefoxOnPort(donor.port);
    }`,
  `    console.log(\`[FIREFOX-DONOR] mint gave no token on :\${donor.port} after \${Math.round((Date.now() - stepStartedAt) / 1000)}s (clicks=\${mintClicks}\${mintErrNote ? ', cf_error=' + mintErrNote : ', no answer from the widget'})\`);
    const spMap = { 9228: 10821, 9229: 10824, 9230: 10827, 9231: 10830 };
    const isDirectDonor = fs.existsSync(path.join(__dirname, 'tsb-donor-direct.flag'));
    if (!isDirectDonor && spMap[donor.port]) {
      try {
        await rotateSocksSession(spMap[donor.port]);
        console.log(\`[FIREFOX-DONOR] Rotated proxy on :\${donor.port} (:\${spMap[donor.port]}) after mint failure\`);
      } catch {}
    }
    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (mintErrNote === '300010' || mintErrNote === '300030' || mintErrNote === 'interactive-timeout') {
      try {
        await callBidi('browsingContext.reload', { context: ctx, wait: 'interactive' });
      } catch {}
    }
    if (donor._mintFailCount >= 3) {
      donor._mintFailCount = 0;
      console.warn(\`[FIREFOX-DONOR] 3 consecutive mint failures on :\${donor.port} -> recycling Firefox donor!\`);
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      killFirefoxOnPort(donor.port);
    }`
);

rep(
  sq,
  report.squadSteps,
  'sq-spawn-name-strip',
  `    if (activeClients.length < 4 && Array.isArray(humans) && humans.length > 0) {
      const inMatchNames = new Set(humans.map((h) => String(h?.name || '').trim().toLowerCase()));
      const matched = clients.filter((c) => c.isHeadless && inMatchNames.has(c.name.toLowerCase()));
      if (matched.length >= activeClients.length) activeClients = matched;
    }`,
  `    if (activeClients.length < 4 && Array.isArray(humans) && humans.length > 0) {
      const inMatchNames = new Set(humans.map((h) => String(h?.name || '').trim().toLowerCase()));
      const matched = clients.filter((c) => c.isHeadless && (inMatchNames.has(c.name.toLowerCase()) || (c.baseName && inMatchNames.has(c.baseName.toLowerCase()))));
      if (matched.length >= activeClients.length) activeClients = matched;
    }`
);

rep(
  sq,
  report.squadSteps,
  'sq-spawn-summary-strip',
  "summary.push(`${c.name.replace('[NPL] ', '')}(${pos.role === 'FLANK_GUARD' ? 'GUARD' : 'BANK'})->(${pos.x},${pos.y})`);",
  "summary.push(`${c.name.replace(/^\\[[^\\]]+\\]\\s*/, '')}(${pos.role === 'FLANK_GUARD' ? 'GUARD' : 'BANK'})->(${pos.x},${pos.y})`);"
);

rep(
  sq,
  report.squadSteps,
  'sq-create-headless-baseName',
  `  hc.donorChromePort = bot.donorChromePort;
  clients.push(hc);`,
  `  hc.donorChromePort = bot.donorChromePort;
  hc.baseName = bot.baseName || bot.name;
  hc.name = hc.baseName;
  clients.push(hc);`
);

rep(
  sq,
  report.squadSteps,
  'sq-eval-room0-stealth',
  `              if (lowDisp.includes("[apex]")) room0NopeCount++;
              if (!lowDisp.includes("[apex]") && (lowDisp.includes("[nope]") ||`,
  `              if (window.__tsbActiveTag && lowDisp.includes("[" + window.__tsbActiveTag + "]")) room0NopeCount++;
              if ((!window.__tsbActiveTag || !lowDisp.includes("[" + window.__tsbActiveTag + "]")) && (lowDisp.includes("[nope]") ||`
);

rep(
  sq,
  report.squadSteps,
  'sq-eval-boss-skip-own',
  `              const low = raw.toLowerCase();
              if (low.startsWith("[apex]")) continue;`,
  `              const low = raw.toLowerCase();
              if (window.__tsbActiveTag && low.startsWith("[" + window.__tsbActiveTag + "]")) continue;`
);

rep(
  sq,
  report.squadSteps,
  'sq-eval-return-pw',
  `        const myAccId = typeof bm === "object" && bm?.buffer?.data?.[105] ? bm.buffer.data[105].value : null;`,
  `        window.__tsbActiveTag = \${JSON.stringify(activeClanTag.toLowerCase())};
        const myAccId = typeof bm === "object" && bm?.buffer?.data?.[105] ? bm.buffer.data[105].value : null;
        const myAccPw = typeof bm === "object" && bm?.buffer?.data?.[106] ? bm.buffer.data[106].value : null;`
);

rep(
  sq,
  report.squadSteps,
  'sq-eval-assign-pw',
  `        s.myLobbyUsername = myLobbyUsername;
        s.myAccId = myAccId;`,
  `        s.myLobbyUsername = myLobbyUsername;
        s.myAccId = myAccId;
        s.myAccPw = myAccPw;`
);

rep(
  sq,
  report.squadSteps,
  'sq-redacted-and-persist',
  `    // Self-check each bot's own display username in Room 0 (#6694):
    // Detect account-level or IP-level "Redacted XX" and auto-rotate account & re-enter!
    const c = clients[idx];
    if ((c.isHeadless || !headlessOnly) && s.lobby?.inLobby && s.lobby?.room === 0 && s.myLobbyUsername) {
      if (s.myLobbyUsername.includes('Redacted')) {
        if (!c.redactedDetectedAt) c.redactedDetectedAt = now;
        if (now - c.redactedDetectedAt >= 1500) {
          console.log(\`[SELF-CHECK REDACTED] \${c.name} banned as "\${s.myLobbyUsername}" (acc=\${s.myAccId}) -> immediately creating brand-new account & rotating proxy IP!\`);
          c.redactedDetectedAt = 0;
          c.lastVerifiedLobbyName = null;
          c.freshToken = false;
          c.enteredLobbyAt = 0;
          rotateSocksSession(c.socksPort).then(() => {
            c.evalJs(\`(() => {
              localStorage.setItem("d105", "");
              localStorage.setItem("d106", "");
              localStorage.setItem("v105", "0");
              localStorage.setItem("v106", "0");
              const setSetting = bm?.qq?.qr || bm?.qo?.qp;
              if (typeof bm === "object" && typeof setSetting === "function") {
                setSetting.call(bm.qq || bm.qo, 105, "");
                setSetting.call(bm.qq || bm.qo, 106, "");
              }
              if (typeof b1 === "object" && b1?.z?.close) {
                b1.z.close(1, 3252);
                b1.z.close(0, 3253);
                const reconn = b1.z.aJc || b1.z.aIR;
                if (typeof reconn === "function") reconn.call(b1.z, 0, 18, 0);
              }
            })()\`);
          });
        }
      } else if (s.myLobbyUsername.startsWith('[APEX]')) {
        c.redactedDetectedAt = 0;
        if (c.lastVerifiedLobbyName !== s.myLobbyUsername) {
          c.lastVerifiedLobbyName = s.myLobbyUsername;
          console.log(\`[SELF-CHECK OK] \${c.name} verified in Room 0 as "\${s.myLobbyUsername}" (acc=\${s.myAccId}, room0NopeCount=\${s.room0NopeCount})\`);
        }
      }
    } else if (!s.lobby?.inLobby) {
      c.redactedDetectedAt = 0;
      c.lastVerifiedLobbyName = null;
    }`,
  `    // Persist healthy account credentials across restarts
    const c = clients[idx];
    if (
      c.isHeadless &&
      s.myAccId &&
      typeof s.myAccId === 'string' &&
      s.myAccId.length >= 4 &&
      s.myAccPw &&
      typeof s.myAccPw === 'string' &&
      s.myAccPw.length >= 4 &&
      !(s.myLobbyUsername && s.myLobbyUsername.includes('Redacted'))
    ) {
      const k = String(c.slot);
      const prevRec = savedAccounts[k];
      if (!prevRec || prevRec.id !== s.myAccId || prevRec.pw !== s.myAccPw || prevRec.baseName !== c.baseName) {
        savedAccounts[k] = { id: s.myAccId, pw: s.myAccPw, baseName: c.baseName };
        flushSavedAccounts();
      }
    }
    // Self-check each bot's own display username in Room 0 (#6694):
    // Detect account-level or IP-level "Redacted XX" and rotate account + name + proxy IP!
    if ((c.isHeadless || !headlessOnly) && s.lobby?.inLobby && s.lobby?.room === 0 && s.myLobbyUsername) {
      if (s.myLobbyUsername.includes('Redacted')) {
        if (!c.redactedDetectedAt) c.redactedDetectedAt = now;
        if (now - c.redactedDetectedAt >= 1500) {
          const prevName = c.name;
          usedBaseNames.delete((c.baseName || '').toLowerCase());
          c.baseName = pickFreshBaseName(usedBaseNames);
          c.name = c.baseName;
          c.retaggingUntil = 0;
          c.retagTargetRoomId = 0;
          delete savedAccounts[String(c.slot)];
          flushSavedAccounts();
          recentRedactedAtList = recentRedactedAtList.filter((t) => now - t < 60000);
          recentRedactedAtList.push(now);
          if (recentRedactedAtList.length >= 2) {
            recentRedactedAtList = [];
            rotateClanTag('redacted-burst');
          }
          console.log(\`[SELF-CHECK REDACTED] \${prevName} banned as "\${s.myLobbyUsername}" (acc=\${s.myAccId}) -> rotating proxy IP, fresh account & new stealth name "\${c.baseName}"!\`);
          c.redactedDetectedAt = 0;
          c.lastVerifiedLobbyName = null;
          c.freshToken = false;
          c.enteredLobbyAt = 0;
          const nextName = c.baseName;
          rotateSocksSession(c.socksPort).then(() => {
            c.evalJs(\`(() => {
              window.__tsbPlayerName = \${JSON.stringify(nextName)};
              localStorage.setItem("d105", "");
              localStorage.setItem("d106", "");
              localStorage.setItem("v105", "0");
              localStorage.setItem("v106", "0");
              localStorage.setItem("d122", \${JSON.stringify(nextName)});
              localStorage.setItem("v122", "0");
              const setSetting = bm?.qq?.qr || bm?.qo?.qp;
              if (typeof bm === "object" && typeof setSetting === "function") {
                setSetting.call(bm.qq || bm.qo, 105, "");
                setSetting.call(bm.qq || bm.qo, 106, "");
                setSetting.call(bm.qq || bm.qo, 122, \${JSON.stringify(nextName)});
              }
              if (typeof b1 === "object" && b1?.z?.close) {
                b1.z.close(1, 3252);
                b1.z.close(0, 3253);
                const reconn = b1.z.aJc || b1.z.aIR;
                if (typeof reconn === "function") reconn.call(b1.z, 0, 18, 0);
              }
            })()\`);
          });
        }
      } else if (!s.myLobbyUsername.startsWith('Player ')) {
        c.redactedDetectedAt = 0;
        if (c.lastVerifiedLobbyName !== s.myLobbyUsername) {
          c.lastVerifiedLobbyName = s.myLobbyUsername;
          console.log(\`[SELF-CHECK OK] \${c.name} verified in Room 0 as "\${s.myLobbyUsername}" (acc=\${s.myAccId}, tag=[\${activeClanTag}], taggedInRoom=\${s.room0NopeCount})\`);
        }
      }
    } else if (!s.lobby?.inLobby) {
      c.redactedDetectedAt = 0;
      c.lastVerifiedLobbyName = null;
    }`
);

rep(
  sq,
  report.squadSteps,
  'sq-rotate-tag-after-match',
  `  if (anyMeaningfulAlive) {
    reloadingForFreshTokens = false;
    wantTenForCurrentLobby = false;
    globalThis.__squadIdleSince = 0;`,
  `  if (anyMeaningfulAlive) {
    globalThis.__wasSquadInGame = true;
    reloadingForFreshTokens = false;
    wantTenForCurrentLobby = false;
    globalThis.__squadIdleSince = 0;`
);

rep(
  sq,
  report.squadSteps,
  'sq-opening-check-strip',
  ".map((b) => `${b.name.replace('[NPL] ', '')}:tick=${b.tick},terr=${b.terr},sent=${b.sent}${b.terr < 100 ? '(WARN:LOW_TERR!)' : '(OK)'}`)",
  ".map((b) => `${b.name.replace(/^\\[[^\\]]+\\]\\s*/, '')}:tick=${b.tick},terr=${b.terr},sent=${b.sent}${b.terr < 100 ? '(WARN:LOW_TERR!)' : '(OK)'}`)"
);

rep(
  sq,
  report.squadSteps,
  'sq-post-match-untag',
  `  // If all squad bots are dead or match is over, leave lingering finished games to main menu!`,
  `  if (globalThis.__wasSquadInGame) {
    globalThis.__wasSquadInGame = false;
    globalThis.__holdUntagUntil = 0;
    globalThis.__chosenBigRoomId = 0;
    globalThis.__lastChosenCard = null;
    rotateClanTag('match-finished');
    for (const c of clients) {
      if (c.isHeadless) {
        c.name = c.baseName;
        c.retaggingUntil = 0;
        c.retagTargetRoomId = 0;
      }
    }
  }

  // If all squad bots are dead or match is over, leave lingering finished games to main menu!`
);

rep(
  sq,
  report.squadSteps,
  'sq-room-pick-cache',
  `  let chosenCard = anyBigCardNow || null;
  if (!chosenCard && bigTeamCards.length > 0) {
    const scoreCard = (r) => {
      let sc = 0;
      if (r.nS >= 60 || r.nS === 0) sc += 500;
      if (r.vz === 1 || r.vz === 2) sc += 340;      // Sweet spot: 3 Teams or 4 Teams big room!
      else if (r.vz === 3) sc += 230;               // 5 Teams
      else if (r.vz === 0) sc += 170;               // 2 Teams big room (50+ players, 25v25+)
      else if (r.vz >= 4 && r.vz <= 6) sc += 90;    // 6..8 Teams chaotic fallback
      sc += Math.min(140, r.h2 * 3);
      if (r.wK >= 5 && r.wK <= 45) sc += 100;
      else sc -= Math.min(90, Math.floor(r.wK / 2));
      return sc;
    };
    chosenCard = bigTeamCards.slice().sort((a, b) => scoreCard(b) - scoreCard(a))[0];
    globalThis.__chosenBigRoomId = chosenCard ? chosenCard.id : 0;
    if (chosenCard) {
      console.log(\`[ROOM-PICK] Selected BIG Team Room id=\${chosenCard.id} (\${chosenCard.vz + 2} Teams, players=\${chosenCard.h2}/\${chosenCard.nS}, startsIn=\${chosenCard.wK}s, map=\${chosenCard.fF})\`);
    }
  } else if (!chosenCard) {
    globalThis.__chosenBigRoomId = 0;
  }`,
  `  let chosenCard = anyBigCardNow || null;
  if (chosenCard) {
    globalThis.__lastChosenCard = chosenCard;
    globalThis.__lastChosenCardAt = now;
  } else if (sampleCards.length === 0 && globalThis.__lastChosenCard && now - (globalThis.__lastChosenCardAt || 0) < 9000) {
    chosenCard = globalThis.__lastChosenCard;
  } else if (bigTeamCards.length > 0) {
    const scoreCard = (r) => {
      let sc = 0;
      if (r.nS >= 60 || r.nS === 0) sc += 500;
      if (r.vz === 1 || r.vz === 2) sc += 340;
      else if (r.vz === 3) sc += 230;
      else if (r.vz === 0) sc += 170;
      else if (r.vz >= 4 && r.vz <= 6) sc += 90;
      sc += Math.min(140, r.h2 * 3);
      if (r.wK >= 5 && r.wK <= 45) sc += 100;
      else sc -= Math.min(90, Math.floor(r.wK / 2));
      return sc;
    };
    chosenCard = bigTeamCards.slice().sort((a, b) => scoreCard(b) - scoreCard(a))[0];
    globalThis.__chosenBigRoomId = chosenCard ? chosenCard.id : 0;
    if (chosenCard) {
      globalThis.__lastChosenCard = chosenCard;
      globalThis.__lastChosenCardAt = now;
      console.log(\`[ROOM-PICK] Selected BIG Team Room id=\${chosenCard.id} (\${chosenCard.vz + 2} Teams, players=\${chosenCard.h2}/\${chosenCard.nS}, startsIn=\${chosenCard.wK}s, map=\${chosenCard.fF})\`);
    }
  } else if (sampleCards.length > 0) {
    globalThis.__chosenBigRoomId = 0;
    globalThis.__lastChosenCard = null;
  }`
);

rep(
  sq,
  report.squadSteps,
  'sq-dynamic-pool-stealth-retag',
  `  const verifiedApexIndices = [];
  states.forEach((s, idx) => {
    const c = clients[idx];
    if (!c.isHeadless && headlessOnly) return;
    if (
      s?.lobby?.inLobby &&
      s.lobby.room === 0 &&
      typeof s.myLobbyUsername === 'string' &&
      s.myLobbyUsername.startsWith('[APEX]') &&
      !s.myLobbyUsername.includes('Redacted')
    ) {
      verifiedApexIndices.push(idx);
    }
  });

  const ourAlreadySelectedOnTarget = states.filter(
    (s) => targetRoomId > 0 && s?.lobby?.inLobby && s.lobby.selectedId === targetRoomId
  ).length;
  const rawCardH2 = chosenCard ? (chosenCard.h2 | 0) : 0;
  const outsidersE = Math.max(0, rawCardH2 - ourAlreadySelectedOnTarget);
  const roomTeamsT = chosenCard ? Math.max(2, (chosenCard.vz | 0) + 2) : 3;
  const roomCapNs = chosenCard && chosenCard.nS > 0 ? chosenCard.nS : 512;

  // Hold selection until final 15s window (so E has finished gathering!) unless already committed
  const alreadyCommitted = ourAlreadySelectedOnTarget > 0;
  const inCommitWindow = alreadyCommitted || (minStartsIn >= 4 && minStartsIn <= 15);

  let desiredK = 0;
  if (targetRoomId > 0 && inCommitWindow && verifiedApexIndices.length >= 10) {
    // Exact full-team formula: K = floor(E / (T - 1)) when E >= 10*(T-1); minimum 10 bots
    const idealFullTeamK = outsidersE > 0 ? Math.floor(outsidersE / Math.max(1, roomTeamsT - 1)) : 12;
    const roomSpaceLeft = Math.max(0, roomCapNs - outsidersE);
    desiredK = Math.max(10, Math.min(40, verifiedApexIndices.length, roomSpaceLeft, Math.max(10, idealFullTeamK)));
    // Once within final 6s, never shrink desiredK below what we already selected so we don't churn packets at t=3s
    if (minStartsIn <= 6 && ourAlreadySelectedOnTarget >= 10) {
      desiredK = Math.max(desiredK, Math.min(verifiedApexIndices.length, ourAlreadySelectedOnTarget));
    }
  }

  // Pick the exact subset of \`desiredK\` bots: keep bots already selected on targetRoomId first, then fill from verifiedApexIndices!
  const chosenBotIdxSet = new Set();
  if (!avoidC110Collision && timerSpreadOk && desiredK >= 10) {
    for (const idx of verifiedApexIndices) {
      if (chosenBotIdxSet.size < desiredK && states[idx]?.lobby?.selectedId === targetRoomId) {
        chosenBotIdxSet.add(idx);
      }
    }
    for (const idx of verifiedApexIndices) {
      if (chosenBotIdxSet.size < desiredK) {
        chosenBotIdxSet.add(idx);
      }
    }
    const logSig = \`\${targetRoomId}:\${desiredK}:\${outsidersE}\`;
    if (globalThis.__lastDynLogSig !== logSig && (now - (globalThis.__lastDynLogAt || 0) > 3000 || !alreadyCommitted)) {
      globalThis.__lastDynLogSig = logSig;
      globalThis.__lastDynLogAt = now;
      console.log(
        \`[DYNAMIC-POOL] Room id=\${targetRoomId} (\${roomTeamsT} Teams, startsIn=\${minStartsIn}s): outsiders E=\${outsidersE} -> deploying K=\${chosenBotIdxSet.size}/\${verifiedApexIndices.length} [APEX] bots (est team fill=\${outsidersE > 0 ? Math.round((100 * chosenBotIdxSet.size) / Math.ceil((outsidersE + chosenBotIdxSet.size) / roomTeamsT)) : 100}%)!\`
      );
    }
  }

  const bossReadyNow = inRoom0.some((s) => !!s.bossReadyInRoom0);

  const srcHash = getV27TeamSource().length;
  await Promise.all(
    clients.map((c, idx) => {
      if (!c.isHeadless && headlessOnly) return Promise.resolve(null);
      const isStandby = !headlessOnly && c.isHeadless && !wantTenForCurrentLobby;
      const allowReady = !isStandby && (waitMode ? bossReadyNow : chosenBotIdxSet.has(idx));
      const needHotImport = c.lastStrategyLen !== srcHash;
      if (needHotImport) c.lastStrategyLen = srcHash;
      return c.evalJs(\`(async () => {
        window.__tsbPlayerName = \${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = \${c.slot};
        window.__tsbFollowLeader = "kazerd183";
        window.__tsbWaitForLeader = true;
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          if (\${needHotImport ? 'true' : 'false'}) {
            const sid = await ext.strategies.add({ name: "v27team.js", text: async () => \${JSON.stringify(getV27TeamSource())} });
            const targetSid = sid || "file:v27team";
            ext.settings.strategy = targetSid;
            if (ext.strategies.changed) ext.strategies.changed(targetSid);
          }
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          const isInLobbyNow = (typeof bq === "object" && bq?.f6 === 1 && typeof b1 === "object" && b1?.z?.ef?.(1));
          const wantId = \${targetRoomId | 0};
          const isReadyOnTarget = isInLobbyNow && (bq?.sH ? (wantId > 0 && bq.sH.wF === wantId) : !!(bq?.z?.tM?.[3]));
          const isReadyWrongRoom = isInLobbyNow && bq?.sH && bq.sH.wF > 0 && bq.sH.wF !== wantId;
          if (isReadyWrongRoom && !\${waitMode ? 'true' : 'false'}) {
            window.__readyJitterScheduled = false;
            bq.sH.select(0);
          }
          if (isInLobbyNow && !isReadyOnTarget && \${allowReady ? 'true' : 'false'}) {
            if (!window.__readyJitterScheduled) {
              window.__readyJitterScheduled = true;
              const delayMs = 40 + ((\${c.slot} * 35) % 950) + Math.floor(Math.random() * 120);
              setTimeout(() => {
                window.__readyJitterScheduled = false;
                if (typeof bq === "object" && bq?.f6 === 1) {
                  if (bq?.sH?.sH && typeof bq.sH.select === "function" && wantId > 0) {
                    const cardStillThere = bq.sH.sH.find(r => r && r.id === wantId && (r.vz === 1 || r.vz === 2) && (r.nS === 0 || r.nS > 32));
                    if (cardStillThere && bq.sH.wF !== wantId) {
                      bq.sH.select(wantId);
                    }
                  }
                }
              }, delayMs);
            }
          } else if (isInLobbyNow && (bq?.sH ? bq.sH.wF > 0 : !!(bq?.z?.tM?.[3])) && !\${allowReady ? 'true' : 'false'} && !\${waitMode ? 'true' : 'false'}) {
            window.__readyJitterScheduled = false;
            if (bq?.sH && typeof bq.sH.select === "function" && bq.sH.wF) {
              bq.sH.select(0);
            } else {
              document.dispatchEvent(new KeyboardEvent("keyup", { code: "Escape", key: "Escape", bubbles: true, cancelable: true }));
            }
          }
        }
      })()\`, true);
    })
  );`,
  `  const verifiedApexIndices = [];
  states.forEach((s, idx) => {
    const c = clients[idx];
    if (!c.isHeadless && headlessOnly) return;
    const isVerifiedInRoom0 =
      s?.lobby?.inLobby &&
      s.lobby.room === 0 &&
      typeof s.myLobbyUsername === 'string' &&
      !s.myLobbyUsername.includes('Redacted') &&
      !s.myLobbyUsername.startsWith('Player ');
    const isRetaggingForTarget = targetRoomId > 0 && now < (c.retaggingUntil || 0) && c.retagTargetRoomId === targetRoomId;
    if (isVerifiedInRoom0 || isRetaggingForTarget) {
      verifiedApexIndices.push(idx);
    }
  });

  const ourAlreadySelectedOnTarget = states.filter(
    (s, idx) =>
      targetRoomId > 0 &&
      ((s?.lobby?.inLobby && s.lobby.selectedId === targetRoomId) ||
        (now < (clients[idx].retaggingUntil || 0) && clients[idx].retagTargetRoomId === targetRoomId))
  ).length;
  const rawCardH2 = chosenCard ? (chosenCard.h2 | 0) : 0;
  const outsidersE = Math.max(0, rawCardH2 - ourAlreadySelectedOnTarget);
  const roomTeamsT = chosenCard ? Math.max(2, (chosenCard.vz | 0) + 2) : 3;
  const roomCapNs = chosenCard && chosenCard.nS > 0 ? chosenCard.nS : 512;

  // Hold selection until final 20s window (allowing ~1s for stealth tag-on reconnect inside 60-min pass)
  const alreadyCommitted = ourAlreadySelectedOnTarget > 0;
  const inCommitWindow = alreadyCommitted || (minStartsIn >= 5 && minStartsIn <= 20);

  let desiredK = 0;
  if (targetRoomId > 0 && inCommitWindow && verifiedApexIndices.length >= 10) {
    const idealFullTeamK = outsidersE > 0 ? Math.floor(outsidersE / Math.max(1, roomTeamsT - 1)) : 12;
    const roomSpaceLeft = Math.max(0, roomCapNs - outsidersE);
    desiredK = Math.max(10, Math.min(40, verifiedApexIndices.length, roomSpaceLeft, Math.max(10, idealFullTeamK)));
    if (minStartsIn <= 6 && ourAlreadySelectedOnTarget >= 10) {
      desiredK = Math.max(desiredK, Math.min(verifiedApexIndices.length, ourAlreadySelectedOnTarget));
    }
  }

  const chosenBotIdxSet = new Set();
  if (!avoidC110Collision && timerSpreadOk && desiredK >= 10) {
    for (const idx of verifiedApexIndices) {
      const c = clients[idx];
      const committed = states[idx]?.lobby?.selectedId === targetRoomId || (now < (c.retaggingUntil || 0) && c.retagTargetRoomId === targetRoomId);
      if (chosenBotIdxSet.size < desiredK && committed) {
        chosenBotIdxSet.add(idx);
      }
    }
    for (const idx of verifiedApexIndices) {
      if (chosenBotIdxSet.size < desiredK) {
        chosenBotIdxSet.add(idx);
      }
    }
    const logSig = \`\${targetRoomId}:\${desiredK}:\${outsidersE}:\${activeClanTag}\`;
    if (globalThis.__lastDynLogSig !== logSig && (now - (globalThis.__lastDynLogAt || 0) > 3000 || !alreadyCommitted)) {
      globalThis.__lastDynLogSig = logSig;
      globalThis.__lastDynLogAt = now;
      console.log(
        \`[DYNAMIC-POOL] Room id=\${targetRoomId} (\${roomTeamsT} Teams, startsIn=\${minStartsIn}s, tag=[\${activeClanTag}]): outsiders E=\${outsidersE} -> deploying K=\${chosenBotIdxSet.size}/\${verifiedApexIndices.length} bots (est team fill=\${outsidersE > 0 ? Math.round((100 * chosenBotIdxSet.size) / Math.ceil((outsidersE + chosenBotIdxSet.size) / roomTeamsT)) : 100}%)!\`
      );
    }
  }

  const bossReadyNow = inRoom0.some((s) => !!s.bossReadyInRoom0);

  const srcHash = getV27TeamSource().length;
  await Promise.all(
    clients.map((c, idx) => {
      if (!c.isHeadless && headlessOnly) return Promise.resolve(null);
      const isStandby = !headlessOnly && c.isHeadless && !wantTenForCurrentLobby;
      const allowReady = !isStandby && (waitMode ? bossReadyNow : chosenBotIdxSet.has(idx));
      const wantTag = allowReady && targetRoomId > 0 && !waitMode;
      const desiredName = wantTag ? \`[\${activeClanTag}] \${c.baseName}\`.slice(0, 20) : (c.baseName || c.name);
      if (c.name !== desiredName) c.name = desiredName;
      const curLobbyUser = String(states[idx]?.myLobbyUsername || '');
      const hasAnyTag = curLobbyUser.startsWith('[');
      const hasRightTag = curLobbyUser.startsWith(\`[\${activeClanTag}]\`);
      let triggerRetag = false;
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
      }
      const needHotImport = c.lastStrategyLen !== srcHash;
      if (needHotImport) c.lastStrategyLen = srcHash;
      return c.evalJs(\`(async () => {
        window.__tsbPlayerName = \${JSON.stringify(c.name)};
        window.__tsbPlayerColor = 4095;
        window.__tsbSquadSlot = \${c.slot};
        window.__tsbFollowLeader = "kazerd183";
        window.__tsbWaitForLeader = true;
        if (\${triggerRetag ? 'true' : 'false'}) {
          localStorage.setItem("d122", \${JSON.stringify(c.name)});
          localStorage.setItem("v122", "0");
          if (typeof bm === "object" && bm?.buffer?.data?.[122]) bm.buffer.data[122].value = \${JSON.stringify(c.name)};
          if (typeof b1 === "object" && b1?.z?.close) {
            try { b1.z.close(1, 3252); } catch {}
          }
          setTimeout(() => {
            try {
              const ext = window.__fx?.strategyBotExtension;
              if (ext) {
                ext.settings.armed = true;
                ext.remote.state.loop = "team";
              }
              window.__tsbSquadSyncHold = false;
              if (typeof b1 === "object" && b1?.z) b1.z.f7 = 1;
              window.__fx?.strategyBot?.openMultiplayer?.(0);
              setTimeout(() => { window.__tsbSquadSyncHold = true; }, 4500);
            } catch {}
          }, 80);
          return;
        }
        const ext = window.__fx?.strategyBotExtension;
        if (ext) {
          if (\${needHotImport ? 'true' : 'false'}) {
            const sid = await ext.strategies.add({ name: "v27team.js", text: async () => \${JSON.stringify(getV27TeamSource())} });
            const targetSid = sid || "file:v27team";
            ext.settings.strategy = targetSid;
            if (ext.strategies.changed) ext.strategies.changed(targetSid);
          }
          ext.settings.armed = true;
          ext.remote.state.loop = "team";
          const isInLobbyNow = (typeof bq === "object" && bq?.f6 === 1 && typeof b1 === "object" && b1?.z?.ef?.(1));
          const wantId = \${targetRoomId | 0};
          const isReadyOnTarget = isInLobbyNow && (bq?.sH ? (wantId > 0 && bq.sH.wF === wantId) : !!(bq?.z?.tM?.[3]));
          const isReadyWrongRoom = isInLobbyNow && bq?.sH && bq.sH.wF > 0 && bq.sH.wF !== wantId;
          if (isReadyWrongRoom && !\${waitMode ? 'true' : 'false'}) {
            window.__readyJitterScheduled = false;
            bq.sH.select(0);
          }
          if (isInLobbyNow && !isReadyOnTarget && \${allowReady ? 'true' : 'false'} && (\${wantTag ? 'true' : 'false'} ? \${hasRightTag ? 'true' : 'false'} : true)) {
            if (!window.__readyJitterScheduled) {
              window.__readyJitterScheduled = true;
              const delayMs = 40 + ((\${c.slot} * 35) % 950) + Math.floor(Math.random() * 120);
              setTimeout(() => {
                window.__readyJitterScheduled = false;
                if (typeof bq === "object" && bq?.f6 === 1) {
                  if (bq?.sH?.sH && typeof bq.sH.select === "function" && wantId > 0) {
                    const cardStillThere = bq.sH.sH.find(r => r && r.id === wantId && (r.vz === 1 || r.vz === 2) && (r.nS === 0 || r.nS > 32));
                    if (cardStillThere && bq.sH.wF !== wantId) {
                      bq.sH.select(wantId);
                    }
                  }
                }
              }, delayMs);
            }
          } else if (isInLobbyNow && (bq?.sH ? bq.sH.wF > 0 : !!(bq?.z?.tM?.[3])) && !\${allowReady ? 'true' : 'false'} && !\${waitMode ? 'true' : 'false'}) {
            window.__readyJitterScheduled = false;
            if (bq?.sH && typeof bq.sH.select === "function" && bq.sH.wF) {
              bq.sH.select(0);
            } else {
              document.dispatchEvent(new KeyboardEvent("keyup", { code: "Escape", key: "Escape", bubbles: true, cancelable: true }));
            }
          }
        }
      })()\`, true);
    })
  );`
);

rep(
  sq,
  report.squadSteps,
  'sq-skip-retagging-in-readyToEnter',
  `  const allSquadTokensReady = !anyStillInGame && (
    readyOrInLobbyCount === activePool.length ||
    (readyOrInLobbyCount >= Math.min(activePool.length, 28) && now - globalThis.__squadIdleSince > 18000) ||
    (readyOrInLobbyCount >= 12 && now - globalThis.__squadIdleSince > 32000)
  );
  const readyToEnter = clients.filter(
    (c, i) =>
      (headlessOnly ? c.isHeadless : (!c.isHeadless || wantTenForCurrentLobby)) &&
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 15000
  );`,
  `  // Option A: bots enter Room 0 with ordinary names immediately once minted so sendTokenToLobby
  // locks in the 60-min pass before the 300s Turnstile token expires; DYNAMIC-POOL holds selection.
  const allSquadTokensReady = !anyStillInGame;
  const readyToEnter = clients.filter(
    (c, i) =>
      (headlessOnly ? c.isHeadless : (!c.isHeadless || wantTenForCurrentLobby)) &&
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      now > (c.retaggingUntil || 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 15000
  );`
);

// Add markers
sq.s = '// V28-STEALTH-PATCH\n' + sq.s;
hb.s = '// V28-STEALTH-HB\n' + hb.s;

const sqOut = sq.crlf > 0 ? sq.s.replace(/\n/g, '\r\n') : sq.s;
const hbOut = hb.crlf > 0 ? hb.s.replace(/\n/g, '\r\n') : hb.s;

const check = (file) => {
  const r = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  return r.status === 0 ? 'OK' : 'FAIL: ' + String(r.stderr || r.stdout || r.error || '').slice(0, 400);
};

if (mode === '--dry') {
  const sqPrev = squadTarget.replace(/\.mjs$/, '.preview-v28stealth.mjs');
  const hbPrev = headlessTarget.replace(/\.mjs$/, '.preview-v28stealth.mjs');
  fs.writeFileSync(sqPrev, sqOut, 'utf8');
  fs.writeFileSync(hbPrev, hbOut, 'utf8');
  report.squadSyntax = check(sqPrev);
  report.headlessSyntax = check(hbPrev);
  report.ok = report.squadSyntax === 'OK' && report.headlessSyntax === 'OK';
  finish();
}

const sqBak = squadTarget + '.bak-v28stealth';
const hbBak = headlessTarget + '.bak-v28stealth';
if (!fs.existsSync(sqBak)) fs.copyFileSync(squadTarget, sqBak);
if (!fs.existsSync(hbBak)) fs.copyFileSync(headlessTarget, hbBak);

const sqTmp = squadTarget.replace(/\.mjs$/, '.tmp-v28stealth.mjs');
const hbTmp = headlessTarget.replace(/\.mjs$/, '.tmp-v28stealth.mjs');
fs.writeFileSync(sqTmp, sqOut, 'utf8');
fs.writeFileSync(hbTmp, hbOut, 'utf8');
report.squadSyntax = check(sqTmp);
report.headlessSyntax = check(hbTmp);
if (report.squadSyntax !== 'OK' || report.headlessSyntax !== 'OK') {
  try { fs.unlinkSync(sqTmp); } catch {}
  try { fs.unlinkSync(hbTmp); } catch {}
  finish('syntax check failed; originals untouched');
}
fs.renameSync(sqTmp, squadTarget);
fs.renameSync(hbTmp, headlessTarget);
report.ok = true;
finish();
