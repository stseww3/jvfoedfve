import fs from 'node:fs';
import path from 'node:path';

for (const hb of ['headless-bot.mjs', '../c110/headless-bot.mjs']) {
  const p = path.resolve(hb);
  let src = fs.readFileSync(p, 'utf8');
  src = src.replace('if (this.minting && now - (this.mintStartedAt || 0) < 22000) return;', 'if (this.minting && now - (this.mintStartedAt || 0) < 95000) return;');
  src = src.replace("new Promise((_, rej) => setTimeout(() => rej(new Error('mintTurnstileToken hard timeout 20s')), 20000))", "new Promise((_, rej) => setTimeout(() => rej(new Error('mintTurnstileToken hard timeout 90s')), 90000))");
  fs.writeFileSync(p, src, 'utf8');
  console.log('Updated mint queue timeout to 90s in:', p);
}

const c110Path = path.resolve('../c110/tsb-team-squad.mjs');
let c110Src = fs.readFileSync(c110Path, 'utf8');
if (!c110Src.includes('__logStream')) {
  c110Src = `import fs from 'node:fs';
import path from 'node:path';
const __logStream = fs.createWriteStream(path.join(path.dirname(new URL(import.meta.url).pathname.replace(/^\\/([A-Za-z]:)/, '$1')), 'tsb-team-squad.log'), { flags: 'a' });
__logStream.on('error', () => {});
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
` + c110Src.replace(/^import fs from 'node:fs';\r?\nimport path from 'node:path';\r?\n/, '');
  fs.writeFileSync(c110Path, c110Src, 'utf8');
  console.log('Added safe __logStream to c110/tsb-team-squad.mjs');
}
