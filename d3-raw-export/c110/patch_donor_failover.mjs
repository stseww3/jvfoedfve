import fs from 'node:fs';
import path from 'node:path';

const sqPath = path.resolve('tsb-team-squad.mjs');
let sq = fs.readFileSync(sqPath, 'utf8');

// 1. Add automatic proxy session rotation when a Firefox donor port hits 4 consecutive mint timeouts,
//    AND if a mint fails on targetPort, automatically retry once on a backup donor port (9226/9227/9225)!
const oldFailBlock = `    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 4) {
      donor._mintFailCount = 0;
      console.warn('[FIREFOX-DONOR] 2 consecutive mint timeouts on :' + donor.port + ' -> recycling Firefox donor...');
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      import('node:child_process').then(({ execSync }) => {
        try { execSync(\`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'firefox.exe' -and $_.CommandLine -match 'firefox_donor_\${donor.port}' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"\`, { stdio: 'ignore' }); } catch {}
      }).catch(() => {});
    }
    throw new Error('Firefox BiDi mint timeout');`;

const newFailBlock = `    donor._mintFailCount = (donor._mintFailCount || 0) + 1;
    if (donor._mintFailCount >= 2) {
      donor._mintFailCount = 0;
      const pToSocks = { 9225: 10801, 9226: 10806, 9227: 10811 };
      if (pToSocks[donor.port]) {
        rotateSocksSession(pToSocks[donor.port]).catch(() => {});
      }
      console.warn('[FIREFOX-DONOR] 2 consecutive mint timeouts on :' + donor.port + ' -> rotating proxy & recycling Firefox donor...');
      try { donor.ws.close(); } catch {}
      firefoxDonors.delete(donor.port);
      import('node:child_process').then(({ execSync }) => {
        try { execSync(\`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'firefox.exe' -and $_.CommandLine -match 'firefox_donor_\${donor.port}' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"\`, { stdio: 'ignore' }); } catch {}
      }).catch(() => {});
    }
    throw new Error('Firefox BiDi mint timeout');`;

sq = sq.replace(oldFailBlock, newFailBlock);

// 2. In mintViaDonorChrome, if targetPort fails, automatically failover to one of the other working donor ports (9226 / 9227 / 9225)
const oldChain = `  const prevChain = donorMintChains.get(targetPort) || Promise.resolve();
  const next = prevChain.then(runMint, runMint);
  donorMintChains.set(targetPort, next.catch(() => {}));
  return next;`;

const newChain = `  const enqueueOnPort = (p) => {
    const fn = () => {
      targetPort = p;
      return runMint();
    };
    const prev = donorMintChains.get(p) || Promise.resolve();
    const nxt = prev.then(fn, fn);
    donorMintChains.set(p, nxt.catch(() => {}));
    return nxt;
  };
  return enqueueOnPort(targetPort).catch(() => {
    const alts = [9226, 9227, 9225].filter((p) => p !== targetPort);
    const altPort = alts[Math.floor(Math.random() * alts.length)];
    return enqueueOnPort(altPort);
  });`;

sq = sq.replace('  const targetPort = (donorPort === 9228 || !donorPort) ? 9225 : donorPort;', '  let targetPort = (donorPort === 9228 || !donorPort) ? 9225 : donorPort;');
sq = sq.replace(oldChain, newChain);

fs.writeFileSync(sqPath, sq, 'utf8');
console.log('Added donor port failover + SOCKS5 rotation to tsb-team-squad.mjs');
