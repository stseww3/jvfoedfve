import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldRecord = `      console.log(\`[RESULT \${name}] result=\${data.result} event=\${data.event} place=\${data.place} peak=\${data.peak} team=\${JSON.stringify(data.team || null)}\`);`;
const newRecord = `      const hCount = Array.isArray(data.humans) ? data.humans.length : (typeof data.humans === 'number' ? data.humans : '?');
      console.log(\`[RESULT \${name}] result=\${data.result} event=\${data.event} place=\${data.place} humans=\${hCount} alivePlayers=\${data.alivePlayers ?? '?'} peak=\${data.peak} team=\${JSON.stringify(data.team || null)}\`);`;

if (tsb.includes(oldRecord)) {
  tsb = tsb.replace(oldRecord, newRecord);
  fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
  console.log('Updated tsb-apex-squad.mjs to log explicit humans count and alivePlayers count!');
} else {
  console.log('Already updated or pattern not found in tsb-apex-squad.mjs');
}
