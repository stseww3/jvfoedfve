import fs from 'node:fs';

// 1. Kill previous tsb-apex-squad.mjs if pid file exists or by checking port 8298
let sq = fs.readFileSync('../c110/tsb-team-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const headerHook = `import fs from 'node:fs';
import path from 'node:path';
const __logStream = fs.createWriteStream('tsb-apex-squad.log', { flags: 'w' });
const __origLog = console.log.bind(console);
const __origErr = console.error.bind(console);
console.log = (...args) => {
  const s = args.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join(' ');
  __logStream.write(s + '\\n');
  __origLog(...args);
};
console.error = (...args) => {
  const s = args.map((x) => (typeof x === 'string' ? x : String(x))).join(' ');
  __logStream.write('[ERR] ' + s + '\\n');
  __origErr(...args);
};
try { fs.writeFileSync('tsb-apex.pid', String(process.pid)); } catch {}
`;

sq = sq.replace("import fs from 'node:fs';\nimport path from 'node:path';", headerHook);

const oldBots = `const CHROME_BOTS = [
  { port: 9223, name: '[Nope] lucas94', slot: 0, id: 'w7V8j', pw: 'M9IzNEQ6E0GLYyH' },
  { port: 9224, name: '[Nope] dave_w', slot: 1, id: 'Wgg7N', pw: 'uYomek27OY-ndDJ' },
  { port: 9225, name: '[Nope] mark07', slot: 2, id: 'YQqLM', pw: 'ZerbXEIzTfnv_gk' },
  { port: 9226, name: '[Nope] kevin_k', slot: 3, id: 'CjQcL', pw: 'bCevZwzI-d7xXea' },
  { port: 9227, name: '[Nope] ethan21', slot: 4, id: 'cbtQj', pw: 'Y0cUCnzmkwaeP2g' },
];

const HEADLESS_BOTS = [
  { port: 9305, socksPort: 10811, donorChromePort: 9225, name: '[Nope] lucas94', slot: 0, id: '', pw: '' },
  { port: 9306, socksPort: 10812, donorChromePort: 9225, name: '[Nope] dave_w', slot: 1, id: '', pw: '' },
  { port: 9307, socksPort: 10813, donorChromePort: 9225, name: '[Nope] mark07', slot: 2, id: '', pw: '' },
  { port: 9308, socksPort: 10814, donorChromePort: 9225, name: '[Nope] kevin_k', slot: 3, id: '', pw: '' },
  { port: 9309, socksPort: 10815, donorChromePort: 9225, name: '[Nope] ethan21', slot: 4, id: '', pw: '' },
];`;

const newBots = `const CHROME_BOTS = [
  { port: 9228, name: '[APEX] ryan_m', slot: 0, id: 'CjQcL', pw: 'bCevZwzI-d7xXea' },
];

const HEADLESS_BOTS = [
  { port: 9310, socksPort: 10801, donorChromePort: 9228, name: '[APEX] ryan_m', slot: 0, id: '', pw: '' },
  { port: 9311, socksPort: 10802, donorChromePort: 9228, name: '[APEX] noah88', slot: 1, id: '', pw: '' },
  { port: 9312, socksPort: 10803, donorChromePort: 9228, name: '[APEX] leo_tx', slot: 2, id: '', pw: '' },
  { port: 9313, socksPort: 10804, donorChromePort: 9228, name: '[APEX] alex_k', slot: 3, id: '', pw: '' },
  { port: 9314, socksPort: 10805, donorChromePort: 9228, name: '[APEX] zero_7', slot: 4, id: '', pw: '' },
];

function isC110GatheringInLobby() {
  try {
    const c110Log = path.resolve(__dirname, '../c110/tsb-team-squad.log');
    if (!fs.existsSync(c110Log)) return false;
    const st = fs.statSync(c110Log);
    if (Date.now() - st.mtimeMs > 180000) return false;
    const sz = st.size;
    const fd = fs.openSync(c110Log, 'r');
    const readLen = Math.min(sz, 8192);
    const buf = Buffer.alloc(readLen);
    fs.readSync(fd, buf, 0, readLen, sz - readLen);
    fs.closeSync(fd);
    const tail = buf.toString('utf8');
    const lines = tail.split(/\\r?\\n/).reverse();
    for (const line of lines) {
      if (line.includes('[HL-TICK]') || line.includes('[HL-OPENING]') || line.includes('[HL-SPAWN]') || line.includes('[HL-GAME-INIT]')) {
        return false;
      }
      if (line.includes('Entering Team Room 0') || line.includes('[SELF-CHECK OK]') || line.includes('[RESULT ')) {
        return true;
      }
    }
  } catch {}
  return false;
}`;

sq = sq.replace(oldBots, newBots);
sq = sq.replace('new TeamSpawnCoordinator({ port: 8198 })', 'new TeamSpawnCoordinator({ port: 8299 })');

const oldAttachLoop = `for (const bot of CHROME_BOTS) {
  await attachChromeBot(bot);
}`;

const newAttachLoop = `for (const bot of CHROME_BOTS) {
  for (let retry = 0; retry < 15; retry++) {
    const ok = await attachChromeBot(bot);
    if (ok) break;
    await new Promise((r) => setTimeout(r, 1500));
  }
}`;

sq = sq.replace(oldAttachLoop, newAttachLoop);

const oldScan = `            for (let idx = 0; idx < list.length; idx++) {
              const p = list[idx];
              const disp = String((p && p.username) || "").trim();
              if (disp.toLowerCase().includes("[nope]")) room0NopeCount++;`;

const newScan = `            let c110NopeInLobby = 0;
            for (let idx = 0; idx < list.length; idx++) {
              const p = list[idx];
              const disp = String((p && p.username) || "").trim();
              const lowDisp = disp.toLowerCase();
              if (lowDisp.includes("[apex]")) room0NopeCount++;
              if (
                lowDisp.includes("[nope]") ||
                lowDisp.includes("lucas94") ||
                lowDisp.includes("dave_w") ||
                lowDisp.includes("mark07") ||
                lowDisp.includes("kevin_k") ||
                lowDisp.includes("ethan21")
              ) {
                c110NopeInLobby++;
              }`;

sq = sq.replace(oldScan, newScan);
sq = sq.replace(
  's.room0NopeCount = typeof room0NopeCount === "number" ? room0NopeCount : 0;',
  's.room0NopeCount = typeof room0NopeCount === "number" ? room0NopeCount : 0;\n        s.c110NopeInLobby = typeof c110NopeInLobby === "number" ? c110NopeInLobby : 0;'
);
sq = sq.replace("} else if (s.myLobbyUsername.startsWith('[Nope]')) {", "} else if (s.myLobbyUsername.startsWith('[APEX]')) {");

const oldGate = `  const allReadyInRoom0 =
    timerSpreadOk &&
    (headlessOnly`;

const newGate = `  const maxC110NopeInLobby = inRoom0.reduce((m, s) => Math.max(m, s.c110NopeInLobby || 0), 0);
  const c110Gathering = isC110GatheringInLobby();
  const avoidC110Collision = maxC110NopeInLobby > 0 || c110Gathering;
  if (avoidC110Collision && inRoom0.length > 0 && Date.now() - (globalThis.__lastAntiColLog || 0) > 10000) {
    globalThis.__lastAntiColLog = Date.now();
    console.log(\`[ANTI-COLLISION] Detected c110 v27 squad in lobby (nopeInLobby=\${maxC110NopeInLobby}, logInLobby=\${c110Gathering}) -> holding [APEX] Ready so we never enter the same match!\`);
  }

  const allReadyInRoom0 =
    !avoidC110Collision &&
    timerSpreadOk &&
    (headlessOnly`;

sq = sq.replace(oldGate, newGate);

fs.writeFileSync('tsb-apex-squad.mjs', sq, 'utf8');
console.log('Updated tsb-apex-squad.mjs with port 9228 & 8299:', sq.length);
