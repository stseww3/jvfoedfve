import fs from 'node:fs';
import path from 'node:path';

for (const p of ['tsb-team-squad.mjs', '../c116/tsb-apex-squad.mjs']) {
  const full = path.resolve(p);
  let s = fs.readFileSync(full, 'utf8');
  s = s.replace(
    /let ws = await tryConnectBidi\(\);\r?\n\s*if \(!ws && fs\.existsSync\(ffExe\)\) \{[\s\S]*?if \(!ws\) throw new Error\(`Firefox BiDi not reachable on port \$\{port\}`\);/,
    `let ws = await tryConnectBidi();
    if (!ws && fs.existsSync(ffExe)) {
      try {
        const { execSync } = await import('node:child_process');
        execSync(\`powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'firefox.exe' -and $_.CommandLine -match 'firefox_donor_\${port}' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"\`, { stdio: 'ignore' });
      } catch {}
      await new Promise((r) => setTimeout(r, 600));
      try { fs.unlinkSync(path.join(profDir, 'parent.lock')); } catch {}
      try { fs.unlinkSync(path.join(profDir, '.startup-incomplete')); } catch {}
      if (typeof ensureFirefoxProfile === 'function') ensureFirefoxProfile(profDir, (typeof portToSocks === 'object' && portToSocks[port]) || 0);
      console.log(\`[FIREFOX-DONOR] Launching Mozilla Firefox on port \${port}...\`);
      const child = spawn(ffExe, ['-no-remote', '-profile', profDir, '--remote-debugging-port', String(port), 'https://territorial.io/'], {
        detached: true,
        stdio: 'ignore'
      });
      child.unref();
      for (let retry = 0; retry < 18; retry++) {
        await new Promise((r) => setTimeout(r, 1000));
        ws = await tryConnectBidi();
        if (ws) break;
      }
    }
    if (!ws) throw new Error(\`Firefox BiDi not reachable on port \${port}\`);`
  );
  fs.writeFileSync(full, s, 'utf8');
  console.log('Patched ensureFirefoxDonor in', full);
}
