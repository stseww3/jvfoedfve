import fs from 'node:fs';

let tsb = fs.readFileSync('tsb-apex-squad.mjs', 'utf8').replace(/\r\n/g, '\n');

const oldSess = `  // End any stale BiDi session first, then create a fresh session
  await callBidi('session.end', {});
  const sess = await callBidi('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) {
    // If a previous process held a session on this Firefox instance, reconnect cleanly
    console.log('[FIREFOX-DONOR] BiDi session busy or re-initializing...');
  }`;

const newSess = `  const sess = await callBidi('session.new', { capabilities: {} });
  if (!sess?.result?.sessionId) {
    console.log('[FIREFOX-DONOR] BiDi session locked by previous process -> recycling Firefox donor on :9228...');
    try { ws.close(); } catch {}
    const { execSync } = await import('node:child_process');
    try { execSync('taskkill /F /IM firefox.exe', { stdio: 'ignore' }); } catch {}
    await new Promise((r) => setTimeout(r, 800));
    return _initFirefoxDonor(port);
  }`;

if (!tsb.includes(oldSess)) {
  console.error('Could not find oldSess in tsb-apex-squad.mjs!');
  process.exit(1);
}
tsb = tsb.replace(oldSess, newSess);
fs.writeFileSync('tsb-apex-squad.mjs', tsb, 'utf8');
console.log('Added automatic Firefox BiDi session recycle on restart in tsb-apex-squad.mjs!');
