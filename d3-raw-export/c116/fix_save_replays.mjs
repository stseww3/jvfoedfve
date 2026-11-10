import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldFunc = `function recordResult(name, port, rawPayload) {
  try {
    const data = typeof rawPayload === 'string' ? JSON.parse(rawPayload) : rawPayload;
    if (data && data.type === 'result') {
      const line = JSON.stringify({ bot: name, port, ...data });
      const resFile = fs.existsSync(__dirname) ? path.join(__dirname, 'tsb-team-results.jsonl') : '/tmp/tsb-team-results.jsonl';
      fs.appendFileSync(resFile, line + '\\n');
      const hCount = Array.isArray(data.humans) ? data.humans.length : (typeof data.humans === 'number' ? data.humans : '?');
      console.log(\`[RESULT \${name}] result=\${data.result} event=\${data.event} place=\${data.place} humans=\${hCount} alivePlayers=\${data.alivePlayers ?? '?'} peak=\${data.peak} team=\${JSON.stringify(data.team || null)}\`);
    }
  } catch {}
}`;

const newFunc = `function recordResult(name, port, rawPayload) {
  try {
    const data = typeof rawPayload === 'string' ? JSON.parse(rawPayload) : rawPayload;
    if (data && data.type === 'result') {
      const line = JSON.stringify({ bot: name, port, ...data });
      const resFile = fs.existsSync(__dirname) ? path.join(__dirname, 'tsb-team-results.jsonl') : '/tmp/tsb-team-results.jsonl';
      fs.appendFileSync(resFile, line + '\\n');
      const hCount = Array.isArray(data.humans) ? data.humans.length : (typeof data.humans === 'number' ? data.humans : '?');
      const aiCount = typeof hCount === 'number' && typeof data.players === 'number' ? (data.players - hCount) : '?';
      console.log(\`[RESULT \${name}] result=\${data.result} event=\${data.event} place=\${data.place} humans=\${hCount} aiBots=\${aiCount} alivePlayers=\${data.alivePlayers ?? '?'} peak=\${data.peak} team=\${JSON.stringify(data.team || null)}\`);
    } else if (data && data.type === 'replay' && typeof data.replay === 'string' && data.replay.length > 100) {
      const repDir = path.join(__dirname, 'replays');
      if (!fs.existsSync(repDir)) fs.mkdirSync(repDir, { recursive: true });
      const safeName = String(name).replace(/[^\\w.-]+/g, '_');
      const repFile = path.join(repDir, \`replay-\${data.game || Date.now()}-\${safeName}.txt\`);
      fs.writeFileSync(repFile, data.replay, 'utf8');
      fs.writeFileSync(path.join(repDir, 'latest-replay.txt'), data.replay, 'utf8');
      console.log(\`[REPLAY SAVED \${name}] game=\${data.game} len=\${data.replay.length} -> \${repFile}\`);
    }
  } catch {}
}`;

if (!tsb.includes(oldFunc)) {
  console.error('Could not find oldFunc in tsb-apex-squad.mjs');
  process.exit(1);
}
tsb = tsb.replace(oldFunc, newFunc);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Successfully added replay saving to tsb-apex-squad.mjs!');
