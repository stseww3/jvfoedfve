import fs from 'node:fs';

let hb = fs.readFileSync('headless-bot.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldRemote = `  document.addEventListener('tsb-remote', (e) => {
    try {
      const c = JSON.parse(e.detail);
      if (c.kind === 'post' && sandbox.__tsbReportResult) {
        sandbox.__tsbReportResult(c.body);
      }
    } catch (err) {
      parentPort.postMessage({ type: 'log', text: \`[HL-ERR] tsb-remote parse: \${err?.message || err}\` });
    }
  });`;

const newRemote = `  document.addEventListener('tsb-remote', (e) => {
    try {
      const c = JSON.parse(e.detail);
      if (c.kind === 'post' && sandbox.__tsbReportResult) {
        sandbox.__tsbReportResult(c.body);
      }
      if (c.kind === 'post' && c.body) {
        const d = typeof c.body === 'string' ? JSON.parse(c.body) : c.body;
        if (d && d.type === 'replay' && typeof d.replay === 'string' && d.replay.length > 100) {
          const repDir = path.join(__dirname, 'replays');
          if (!fs.existsSync(repDir)) fs.mkdirSync(repDir, { recursive: true });
          const rawText = (typeof sandbox.aE === 'object' && typeof sandbox.aE.a7f === 'string' && sandbox.aE.a7f.length > 100) ? sandbox.aE.a7f : d.replay;
          const safeName = String(name).replace(/[^\\w.-]+/g, '_');
          const repFile = path.join(repDir, \`replay-\${d.game || Date.now()}-\${safeName}.txt\`);
          fs.writeFileSync(repFile, rawText, 'utf8');
          fs.writeFileSync(path.join(repDir, 'latest-replay.txt'), rawText, 'utf8');
        }
      }
    } catch (err) {
      parentPort.postMessage({ type: 'log', text: \`[HL-ERR] tsb-remote parse: \${err?.message || err}\` });
    }
  });`;

if (!hb.includes(oldRemote)) {
  console.error('Could not find oldRemote in headless-bot.mjs!');
  process.exit(1);
}
hb = hb.replace(oldRemote, newRemote);
fs.writeFileSync('headless-bot.mjs', hb, 'utf8');
console.log('Successfully added raw un-anonymized replay saving to headless-bot.mjs!');
