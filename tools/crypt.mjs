// Sealed bundles of files (AES-256-GCM, key in STRAT_KEY as 32 bytes of
// base64), so a public repository can carry code and results only CI can
// read.
// node tools/crypt.mjs seal OUT PATH...   bundle files / directories into OUT
// node tools/crypt.mjs open IN [DIR]      write the bundled files under DIR
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';

const key = Buffer.from(process.env.STRAT_KEY ?? '', 'base64');
if (key.length !== 32) throw new Error('STRAT_KEY must hold 32 bytes of base64');
const [cmd, file, ...rest] = process.argv.slice(2);

function collect(p, out) {
  if (fs.statSync(p).isDirectory()) for (const f of fs.readdirSync(p).sort()) collect(path.join(p, f), out);
  else out[p.split(path.sep).join('/')] = fs.readFileSync(p).toString('base64');
  return out;
}

if (cmd === 'seal') {
  const files = {};
  for (const p of rest) collect(p, files);
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key, iv);
  const body = Buffer.concat([c.update(zlib.gzipSync(JSON.stringify(files))), c.final()]);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, Buffer.concat([iv, c.getAuthTag(), body]));
} else if (cmd === 'open') {
  const buf = fs.readFileSync(file);
  const d = crypto.createDecipheriv('aes-256-gcm', key, buf.subarray(0, 12));
  d.setAuthTag(buf.subarray(12, 28));
  const files = JSON.parse(zlib.gunzipSync(Buffer.concat([d.update(buf.subarray(28)), d.final()])));
  const dir = rest[0] ?? '.';
  for (const [p, b64] of Object.entries(files)) {
    const out = path.join(dir, p);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, Buffer.from(b64, 'base64'));
  }
} else throw new Error('usage: crypt.mjs seal OUT PATH... | open IN [DIR]');
