import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldCol = `  const maxC110NopeInLobby = inRoom0.reduce((m, s) => Math.max(m, s.c110NopeInLobby || 0), 0);
  const c110Gathering = isC110GatheringInLobby();
  const avoidC110Collision = maxC110NopeInLobby > 0 || c110Gathering;`;

const newCol = `  const maxC110NopeInLobby = inRoom0.reduce((m, s) => Math.max(m, s.c110NopeInLobby || 0), 0);
  const c110Gathering = false; // Never block on c110 log when c110 is in waitBoss=true LOBBY-WAIT mode!
  const avoidC110Collision = maxC110NopeInLobby > 0;`;

if (!tsb.includes(oldCol)) {
  console.error('Could not find oldCol in tsb-apex-squad.mjs!');
  process.exit(1);
}
tsb = tsb.replace(oldCol, newCol);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Successfully disabled false-positive c110Gathering log lock in tsb-apex-squad.mjs!');
