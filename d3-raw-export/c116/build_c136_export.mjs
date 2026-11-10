import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const crypto = globalThis.crypto;

async function sha256Hex(buf) {
  const hashBuf = await crypto.subtle.digest('SHA-256', buf);
  return Buffer.from(hashBuf).toString('hex');
}

function readCleanBuf(filePath) {
  const raw = fs.readFileSync(filePath);
  let nonNull = 0;
  for (let i = 0; i < raw.length; i++) if (raw[i] !== 0) nonNull++;
  if (nonNull === raw.length) return raw;
  const out = Buffer.allocUnsafe(nonNull);
  let j = 0;
  for (let i = 0; i < raw.length; i++) if (raw[i] !== 0) out[j++] = raw[i];
  return out;
}

async function fileMeta(relPath, fullPath) {
  const st = fs.statSync(fullPath);
  const buf = fs.readFileSync(fullPath);
  const sha256 = await sha256Hex(buf);
  return {
    path: relPath,
    size: st.size,
    mtimeIso: st.mtime.toISOString(),
    mtimeMs: st.mtimeMs,
    sha256,
  };
}

async function main() {
  const c116Dir = path.resolve('.');
  const c110Dir = path.resolve('../c110');

  // 1. Package (a) + (d) + (e) + small logs into export_meta_code_results.gz.b64
  const manifest = { exportedAt: new Date().toISOString(), c116: [], c110: [] };
  const filesMap = {};

  async function addWorkspaceFiles(wsName, baseDir, list) {
    const entries = fs.readdirSync(baseDir, { withFileTypes: true });
    for (const ent of entries) {
      if (!ent.isFile()) continue;
      const name = ent.name;
      if (name.endsWith('.exe') || name.endsWith('.b64') || name === 'tsb-apex-squad.log' || name === 'tsb-team-squad.log' || name === 'day2_results.jsonl') continue;
      const full = path.join(baseDir, name);
      const st = fs.statSync(full);
      if (st.size > 5000000) continue;
      const rel = `${wsName}/${name}`;
      const meta = await fileMeta(rel, full);
      list.push(meta);
      if (name.endsWith('.png')) {
        filesMap[rel] = { encoding: 'base64', data: fs.readFileSync(full).toString('base64') };
      } else {
        filesMap[rel] = { encoding: 'utf8', data: readCleanBuf(full).toString('utf8') };
      }
    }
  }

  await addWorkspaceFiles('c116', c116Dir, manifest.c116);
  await addWorkspaceFiles('c110', c110Dir, manifest.c110);

  // Also add SHA256 + mtime of the big logs to manifest
  for (const [wsName, baseDir, logName] of [
    ['c116', c116Dir, 'tsb-apex-squad.log'],
    ['c110', c110Dir, 'tsb-team-squad.log'],
  ]) {
    const full = path.join(baseDir, logName);
    if (fs.existsSync(full)) {
      manifest[wsName].push(await fileMeta(`${wsName}/${logName}`, full));
    }
  }

  const pkg1 = zlib.gzipSync(Buffer.from(JSON.stringify({ manifest, files: filesMap }), 'utf8'), { level: 9 });
  fs.writeFileSync('export_pkg1_code_results.b64', pkg1.toString('base64'));
  console.log('pkg1_code_results b64 len:', pkg1.toString('base64').length);

  // 2. Package c110/tsb-team-squad.log.gz
  const c110LogClean = readCleanBuf(path.join(c110Dir, 'tsb-team-squad.log'));
  const c110LogGz = zlib.gzipSync(c110LogClean, { level: 9 });
  fs.writeFileSync('export_pkg2_c110_log.b64', c110LogGz.toString('base64'));
  console.log('pkg2_c110_log b64 len:', c110LogGz.toString('base64').length);

  // 3. Package c116/tsb-apex-squad.log (split into 2 parts so each b64 is ~4MB)
  const c116Raw = readCleanBuf(path.join(c116Dir, 'tsb-apex-squad.log'));
  const lines = [];
  let pos = 0;
  while (pos < c116Raw.length) {
    let nl = c116Raw.indexOf(10, pos);
    if (nl < 0) nl = c116Raw.length;
    const line = c116Raw.subarray(pos, nl).toString('utf8');
    if (!line.includes('[HL-LIVE-REPLAY-URL]')) lines.push(line);
    pos = nl + 1;
  }
  const mid = Math.floor(lines.length / 2);
  const c116LogP1 = zlib.gzipSync(Buffer.from(lines.slice(0, mid).join('\n') + '\n', 'utf8'), { level: 9 });
  const c116LogP2 = zlib.gzipSync(Buffer.from(lines.slice(mid).join('\n') + '\n', 'utf8'), { level: 9 });
  fs.writeFileSync('export_pkg3_c116_log_p1.b64', c116LogP1.toString('base64'));
  fs.writeFileSync('export_pkg4_c116_log_p2.b64', c116LogP2.toString('base64'));
  console.log('pkg3_c116_log_p1 b64 len:', c116LogP1.toString('base64').length);
  console.log('pkg4_c116_log_p2 b64 len:', c116LogP2.toString('base64').length);

  // 4. Package c116 replays (split into 2 parts)
  const c116RepDir = path.join(c116Dir, 'replays');
  const c116RepFiles = fs.existsSync(c116RepDir) ? fs.readdirSync(c116RepDir) : [];
  const half116 = Math.ceil(c116RepFiles.length / 2);
  for (let idx = 0; idx < 2; idx++) {
    const slice = c116RepFiles.slice(idx * half116, (idx + 1) * half116);
    const map = {};
    for (const f of slice) map[f] = fs.readFileSync(path.join(c116RepDir, f), 'utf8');
    const gz = zlib.gzipSync(Buffer.from(JSON.stringify(map), 'utf8'), { level: 9 });
    const outName = `export_pkg5_c116_rep_p${idx + 1}.b64`;
    fs.writeFileSync(outName, gz.toString('base64'));
    console.log(outName, 'b64 len:', gz.toString('base64').length);
  }

  // 5. Package c110 replays (deduplicated across 4 parts)
  const c110RepDir = path.join(c110Dir, 'replays');
  const c110RepFiles = fs.existsSync(c110RepDir) ? fs.readdirSync(c110RepDir) : [];
  const byKey = new Map();
  const repIndex = {};
  for (const f of c110RepFiles) {
    const s = fs.readFileSync(path.join(c110RepDir, f), 'utf8');
    const k = s.length + ':' + s.slice(0, 32) + ':' + s.slice(-32);
    if (!byKey.has(k)) byKey.set(k, s);
    repIndex[f] = k;
  }
  const uniqueEntries = Array.from(byKey.entries());
  const chunkSz = Math.ceil(uniqueEntries.length / 4);
  for (let idx = 0; idx < 4; idx++) {
    const slice = Object.fromEntries(uniqueEntries.slice(idx * chunkSz, (idx + 1) * chunkSz));
    const payload = idx === 0 ? { index: repIndex, blobs: slice } : { blobs: slice };
    const gz = zlib.gzipSync(Buffer.from(JSON.stringify(payload), 'utf8'), { level: 9 });
    const outName = `export_pkg6_c110_rep_p${idx + 1}.b64`;
    fs.writeFileSync(outName, gz.toString('base64'));
    console.log(outName, 'b64 len:', gz.toString('base64').length);
  }
}

main().catch((e) => console.error(e));
