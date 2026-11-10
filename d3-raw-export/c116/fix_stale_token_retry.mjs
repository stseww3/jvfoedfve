import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldEnter = `  const readyToEnter = clients.filter(
    (c, i) =>
      (headlessOnly ? c.isHeadless : (!c.isHeadless || wantTenForCurrentLobby)) &&
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 15000
  );
  if (readyToEnter.length > 0 && (headlessOnly || !clients.some((c, i) => !c.isHeadless && !c.freshToken && !(states[i]?.lobby?.inLobby)))) {
    lastSyncLaunch = now;
    console.log(
      \`[SQUAD-SYNC] Entering Team Room 0 for \${readyToEnter.map((c) => c.name).join(', ')} (mode=\${headlessOnly ? '5-HEADLESS-GUARD' : wantTenForCurrentLobby ? '10-BOT >=35p' : '5-BOT <35p'}, waitBoss=\${waitMode}, room0Players=\${maxRoom0Players})...\`
    );
    for (let i = 0; i < readyToEnter.length; i++) {
      const c = readyToEnter[i];
      c.enteredLobbyAt = now;`;

const newEnter = `  const readyToEnter = clients.filter(
    (c, i) =>
      (headlessOnly ? c.isHeadless : (!c.isHeadless || wantTenForCurrentLobby)) &&
      !states[i]?.inGame &&
      !(states[i]?.lobby?.inLobby && states[i]?.lobby?.room === 0) &&
      c.freshToken &&
      now - c.enteredLobbyAt > 15000
  );
  if (readyToEnter.length > 0 && (headlessOnly || !clients.some((c, i) => !c.isHeadless && !c.freshToken && !(states[i]?.lobby?.inLobby)))) {
    lastSyncLaunch = now;
    console.log(
      \`[SQUAD-SYNC] Entering Team Room 0 for \${readyToEnter.map((c) => c.name).join(', ')} (mode=\${headlessOnly ? '5-HEADLESS-GUARD' : wantTenForCurrentLobby ? '10-BOT >=35p' : '5-BOT <35p'}, waitBoss=\${waitMode}, room0Players=\${maxRoom0Players})...\`
    );
    for (let i = 0; i < readyToEnter.length; i++) {
      const c = readyToEnter[i];
      c.lobbyFailCount = (c.lobbyFailCount || 0) + 1;
      if (c.lobbyFailCount >= 2) {
        c.freshToken = false;
        c.lobbyFailCount = 0;
        continue;
      }
      c.enteredLobbyAt = now;`;

if (!tsb.includes(oldEnter)) {
  console.error('Could not find oldEnter in tsb-apex-squad.mjs');
  process.exit(1);
}
tsb = tsb.replace(oldEnter, newEnter);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Successfully added lobbyFailCount token refresh guard to tsb-apex-squad.mjs!');
