import fs from 'node:fs';
import path from 'node:path';

const sqPath = path.resolve('tsb-team-squad.mjs');
let sq = fs.readFileSync(sqPath, 'utf8');

// 1. Wait until window.turnstile is actually loaded (false:object) after reload
const oldReload = `    if (!wdVal.startsWith('false:object')) {
      console.log(\`[FIREFOX-DONOR] Reloading territorial.io tab on :\${port} so preloadScript (webdriver=false) takes effect (was \${wdVal})...\`);
      await callBidi('browsingContext.reload', { context: ctx, wait: 'complete' });
      await new Promise((r) => setTimeout(r, 2500));
    }`;

const newReload = `    if (!wdVal.startsWith('false:object')) {
      console.log(\`[FIREFOX-DONOR] Reloading territorial.io tab on :\${port} so preloadScript (webdriver=false) takes effect (was \${wdVal})...\`);
      await callBidi('browsingContext.reload', { context: ctx, wait: 'complete' });
      for (let w = 0; w < 15; w++) {
        await new Promise((r) => setTimeout(r, 700));
        const chk = await callBidi('script.evaluate', {
          expression: 'String(navigator.webdriver) + ":" + String(typeof window.turnstile?.render)',
          target: { context: ctx },
          awaitPromise: false
        });
        if ((chk?.result?.result?.value || '').startsWith('false:function')) break;
      }
    }`;

sq = sq.replace(oldReload, newReload);

// 2. Fix mintViaDonorChrome so runMint dynamically fetches the live donor for targetPort and waits for turnstile.render
const oldMint = `async function mintViaDonorChrome(donorPort = 9225) {
  const targetPort = (donorPort === 9228 || !donorPort) ? 9225 : donorPort;
  let donor;
  try {
    donor = await ensureFirefoxDonor(targetPort);
  } catch {
    donor = await ensureFirefoxDonor(9225);
  }
  const runMint = async () => {
    const { callBidi, ctx } = donor;`;

const newMint = `const donorMintChains = new Map();
async function mintViaDonorChrome(donorPort = 9225) {
  const targetPort = (donorPort === 9228 || !donorPort) ? 9225 : donorPort;
  const runMint = async () => {
    let donor;
    try {
      donor = await ensureFirefoxDonor(targetPort);
    } catch {
      donor = await ensureFirefoxDonor(9225);
    }
    const { callBidi, ctx } = donor;
    for (let w = 0; w < 10; w++) {
      const tsChk = await callBidi('script.evaluate', {
        expression: 'typeof window.turnstile?.render',
        target: { context: ctx },
        awaitPromise: false
      });
      if (tsChk?.result?.result?.value === 'function') break;
      await new Promise((r) => setTimeout(r, 600));
    }`;

sq = sq.replace(oldMint, newMint);

// 3. Increase recycle threshold from >= 2 to >= 4 and use donorMintChains per targetPort
sq = sq.replace(
  'if (donor._mintFailCount >= 2) {',
  'if (donor._mintFailCount >= 4) {'
).replace(
  `  const next = (donor._mintChain || Promise.resolve()).then(runMint, runMint);
  donor._mintChain = next.catch(() => {});
  return next;`,
  `  const prevChain = donorMintChains.get(targetPort) || Promise.resolve();
  const next = prevChain.then(runMint, runMint);
  donorMintChains.set(targetPort, next.catch(() => {}));
  return next;`
);

fs.writeFileSync(sqPath, sq, 'utf8');
console.log('Patched mintViaDonorChrome and reload wait in tsb-team-squad.mjs');
