import fs from 'node:fs';

let sq = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

// 1. Fix isC110GatheringInLobby so an individual bot dying ([RESULT ]) while other c110 bots are still in game ([HL-TICK]) is NOT treated as c110 being in lobby!
const oldFunc = sq.slice(sq.indexOf('function isC110GatheringInLobby() {'), sq.indexOf('const isWaitNplMode'));

const newFunc = `function isC110GatheringInLobby() {
  try {
    const c110Log = path.resolve(__dirname, '../c110/tsb-team-squad.log');
    if (!fs.existsSync(c110Log)) return false;
    const st = fs.statSync(c110Log);
    if (Date.now() - st.mtimeMs > 120000) return false;
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
        return false; // c110 is actively inside a running match!
      }
      if (line.includes('Entering Team Room 0') || line.includes('[SELF-CHECK OK]')) {
        return true; // c110 is in Lobby gathering!
      }
    }
  } catch {}
  return false;
}

`;

sq = sq.replace(oldFunc, newFunc);

// 2. Fix isReadyNow and targetRoom so [APEX] bots always ready up on sH[0] when it's a Team game (vz < 7)!
sq = sq.replace(
  'const targetRoom = bq.sH.sH.find(r => r && r.vz <= 2) || bq.sH.sH.find(r => r && r.vz < 7) || bq.sH.sH[0];',
  'const targetRoom = (bq.sH.sH[0] && bq.sH.sH[0].vz < 7) ? bq.sH.sH[0] : (bq.sH.sH.find(r => r && r.vz < 7) || bq.sH.sH[0]);'
);

fs.writeFileSync('tsb-apex-squad.mjs', sq, 'utf8');
console.log('Fixed isC110GatheringInLobby and sH[0] Team room selection in tsb-apex-squad.mjs!');
