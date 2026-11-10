import fs from 'node:fs';
import path from 'node:path';

// 1. Patch headless-bot.mjs:
//    - In customConsole.log: when "delayed pass" is logged (meaning we are in state 10 waiting for ay.aK5() to run 2 frames),
//      remember that sandbox.aE.a38 is still 0 during state 10! And worse, in af0.ee(), ay.aK5() runs, which after 2 frames
//      calls bq.aFy.aH4(), setting aE.a38 = 1. Once aE.a38 === 1, bi.ee() switches from af0.ee() to af2.ee()!
//      And if b1.z.aJc(a4P, 5, 2) on game server index 2/3 fails or takes > 2s, ay.nE() retries every 4.5s,
//      OR if it fails once, let's make ay.nE() retry after 1500ms instead of 4500ms!
//    - In w.on('message') for 'socket close index 2/3': DO NOT call sbLeave(true) during the first 15s of the game or while aE.hx (spawnPhase) is true,
//      and instead if !activeSockOpen && aE.a38 === 1 && bi.kr() === 0, immediately trigger b1.z.aJc(b1.z.a4P, 5, 2) to reconnect to the game server!
{
  const hbPath = path.resolve('headless-bot.mjs');
  let hb = fs.readFileSync(hbPath, 'utf8');

  // Fix 1a: faster game-server handshake retry in live_game_js.js replacement (1800ms instead of 4500ms)
  if (!hb.includes("replaceAll('aJw=bi.eZ+4500', 'aJw=bi.eZ+1800')")) {
    hb = hb.replace(
      ".replace('bV.zf.dk();', '');",
      ".replace('bV.zf.dk();', '')\n    .replaceAll('aJw=bi.eZ+4500', 'aJw=bi.eZ+1800')\n    .replaceAll('aJw+=4500', 'aJw+=1800');"
    );
  }

  // Fix 1b: When socket close index 2 or 3 happens:
  //   - If we are at tick 0 (waiting for game server handshake), immediately reconnect to b1.z.a4P instead of calling sbLeave!
  //   - If we are mid-game (tick > 0), wait 3500ms and re-verify !activeSockOpen before calling sbLeave(true), so transient proxy blips or unused socket closes never mass-quit our squad!
  const oldSockClose = `        if (msg.text.includes('socket close index 3') || msg.text.includes('socket close index 2')) {
          client.evalJs(\`(() => {
            const d = window.dictionary, g = d && window[d.game];
            const activeSockOpen = typeof b1 === "object" && b1?.z?.ef && (b1.z.ef(2) || b1.z.ef(3));
            if (!activeSockOpen && g && g[d.sbLeave] && g[d.gameState] !== 0) {
              g[d.sbLeave](true);
            }
          })()\`);
        }`;

  const newSockClose = `        if (msg.text.includes('socket close index 3') || msg.text.includes('socket close index 2')) {
          client.evalJs(\`(() => {
            const d = window.dictionary, g = d && window[d.game];
            const activeSockOpen = typeof b1 === "object" && b1?.z?.ef && (b1.z.ef(2) || b1.z.ef(3));
            if (!activeSockOpen && g && g[d.gameState] === 1) {
              const curTick = typeof bi === "object" && bi?.kr ? bi.kr() : 0;
              if (curTick === 0 && typeof b1 === "object" && b1?.z?.aJc && b1.z.a4P >= 2) {
                b1.z.aJc(b1.z.a4P, 5, 2);
                return "RECONNECTING_GAME_SERVER";
              }
            }
          })()\`);
          setTimeout(() => {
            client.evalJs(\`(() => {
              const d = window.dictionary, g = d && window[d.game];
              const activeSockOpen = typeof b1 === "object" && b1?.z?.ef && (b1.z.ef(2) || b1.z.ef(3));
              const curTick = typeof bi === "object" && bi?.kr ? bi.kr() : 0;
              if (!activeSockOpen && curTick > 30 && g && g[d.sbLeave] && g[d.gameState] !== 0) {
                g[d.sbLeave](true);
              }
            })()\`);
          }, 4000);
        }`;

  if (hb.includes(oldSockClose)) {
    hb = hb.replace(oldSockClose, newSockClose);
    console.log('Patched socket close index 2/3 handler in headless-bot.mjs');
  } else {
    console.warn('Could not find oldSockClose in headless-bot.mjs');
  }

  fs.writeFileSync(hbPath, hb, 'utf8');
}

// 2. Patch v27-team-live.js & make_v27_team.py:
//    Enable Unified Backend Spawn Coordinator (if (true)) even when Boss is not in match!
for (const f of ['v27-team-live.js', 'make_v27_team.py']) {
  const p = path.resolve(f);
  if (!fs.existsSync(p)) continue;
  let s = fs.readFileSync(p, 'utf8');
  s = s.replace(
    'const bossId = this.findBossId(g);\n    if (bossId >= 0) {',
    'const bossId = this.findBossId(g);\n    if (true) {'
  ).replace(
    'const bossId = this.findBossId(g);\r\n    if (bossId >= 0) {',
    'const bossId = this.findBossId(g);\r\n    if (true) {'
  );
  fs.writeFileSync(p, s, 'utf8');
  console.log('Enabled backend SpawnCoordinator for all matches in', f);
}

// 3. Patch spawn-coordinator.mjs:
//    Sync the 2D compact disc phalanx improvements (`distToClusterCore`, `allyMinSep`, `clusterMax` scaling for K<=20)
{
  const scPath = path.resolve('spawn-coordinator.mjs');
  let sc = fs.readFileSync(scPath, 'utf8');

  // Scale clusterMax appropriately for 20 bots (sqrt(K/5) factor so 20 bots fit in a 2D sector disc without overflowing)
  sc = sc.replace(
    `    const scales = {
      rCell: Math.round(rCell),
      bossExcl: clamp(Math.round(Math.max(1.12 * rCell, 0.078 * diag)), 68, 120),
      flankMax: clamp(Math.round(Math.max(2.30 * rCell, 0.170 * diag)), 135, 235),
      allyMinSep: clamp(Math.round(Math.max(1.05 * rCell, 0.075 * diag)), 62, 112),
      enemyMinClearance: clamp(Math.round(0.70 * rCell), 36, 78),
      clusterMax: clamp(Math.round(Math.max(3.0 * rCell, 0.25 * diag)), 195, 350),
    };`,
    `    const kScale = Math.sqrt(Math.max(1, K) / 6);
    const scales = {
      rCell: Math.round(rCell),
      bossExcl: clamp(Math.round(Math.max(1.12 * rCell, 0.078 * diag)), 68, 120),
      flankMax: clamp(Math.round(Math.max(2.30 * rCell, 0.170 * diag)), 135, 235),
      allyMinSep: clamp(Math.round(Math.max(1.15 * rCell, 0.068 * diag)), 64, 110),
      enemyMinClearance: clamp(Math.round(0.70 * rCell), 36, 78),
      clusterMax: clamp(Math.round(Math.max(2.8 * rCell * kScale, 0.22 * diag * Math.min(1.45, kScale))), 220, 460),
    };`
  );

  // Add distToClusterCore if not present
  if (!sc.includes('distToClusterCore')) {
    sc = sc.replace(
      `    const distToOurCluster = (x, y) => {
      let minD = 999999;
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        minD = Math.min(minD, Math.hypot(x - anchorBoss.x, y - anchorBoss.y));
      }
      for (const prev of chosenTargets) {
        minD = Math.min(minD, Math.hypot(x - prev.x, y - prev.y));
      }
      return minD;
    };`,
      `    const distToOurCluster = (x, y) => {
      let minD = 999999;
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        minD = Math.min(minD, Math.hypot(x - anchorBoss.x, y - anchorBoss.y));
      }
      for (const prev of chosenTargets) {
        minD = Math.min(minD, Math.hypot(x - prev.x, y - prev.y));
      }
      return minD;
    };

    const distToClusterCore = (x, y) => {
      if (chosenTargets.length >= 2) {
        let sx = 0, sy = 0;
        for (const t of chosenTargets) { sx += t.x; sy += t.y; }
        sx /= chosenTargets.length;
        sy /= chosenTargets.length;
        return Math.hypot(x - sx, y - sy);
      }
      if (anchorBoss && anchorBoss.x >= 0 && anchorBoss.y >= 0) {
        return Math.hypot(x - anchorBoss.x, y - anchorBoss.y);
      }
      if (chosenTargets.length > 0) {
        return Math.hypot(x - chosenTargets[0].x, y - chosenTargets[0].y);
      }
      return 0;
    };`
    );

    sc = sc.replace(
      `            } else if (enforceCluster) {
              // Keep outer wing connected to the same continent & geodesic distance from Boss
              if (distToOurCluster(x, y) > maxClusterDist) continue;
              if (anchorBoss && (this.dBoss[c] < 0 || this.dBoss[c] > maxClusterDist * 1.35) && relax >= 0.60) continue;
            }`,
      `            } else if (enforceCluster) {
              // Keep 20-bot phalanx in a compact 2D sector disc (adjacent link <= 2.2*allyMinSep AND core radius <= maxClusterDist)
              if (distToOurCluster(x, y) > scales.allyMinSep * (2.25 - 0.45 * relax)) continue;
              if (distToClusterCore(x, y) > maxClusterDist) continue;
              if (anchorBoss && (this.dBoss[c] < 0 || this.dBoss[c] > maxClusterDist * 1.35) && relax >= 0.60) continue;
            }`
    );
  }

  fs.writeFileSync(scPath, sc, 'utf8');
  console.log('Patched 20-bot 2D phalanx formation in spawn-coordinator.mjs');
}

// 4. Patch tsb-team-squad.mjs:
//    - Tighten allReadyInRoom0 gate so we wait for >= 18/20 bots in Room 0 (or >= 16 when startsIn <= 12s),
//      and if startsIn <= 6s with < 16 bots in Room 0, UN-READY any ready bots so we never enter with a 5~13 bot partial squad!
//    - Add tick===0 delayed-pass auto-heal in the poll loop (if a bot is inGame with tick===0 for > 4.5s, trigger b1.z.aJc(b1.z.a4P, 5, 2))
{
  const sqPath = path.resolve('tsb-team-squad.mjs');
  let sq = fs.readFileSync(sqPath, 'utf8');

  sq = sq.replace(
    /\? \(headlessInRoom0 >= HEADLESS_BOTS\.length - 5 \|\| \(headlessInRoom0 >= 10 && minStartsIn <= 18\)\)/,
    '? (headlessInRoom0 >= HEADLESS_BOTS.length - 2 || (headlessInRoom0 >= 16 && minStartsIn <= 14))'
  );

  // Also add auto-heal when s.inGame && s.tick === 0 && !s.spawnPhase
  if (!sq.includes('__zeroTickPolls')) {
    sq = sq.replace(
      `        if (s.inGame) {
          if (s.tick > 0 && !s.spawnPhase && window.__lastObsTick === s.tick) {`,
      `        if (s.inGame) {
          if (s.tick === 0 && !s.spawnPhase) {
            window.__zeroTickPolls = (window.__zeroTickPolls || 0) + 1;
            if (window.__zeroTickPolls >= 2 && typeof b1 === "object" && b1?.z?.aJc && b1.z.a4P >= 2) {
              b1.z.aJc(b1.z.a4P, 5, 2);
            }
          } else {
            window.__zeroTickPolls = 0;
          }
          if (s.tick > 0 && !s.spawnPhase && window.__lastObsTick === s.tick) {`
    );
  }

  // Also if !allowReady && isReadyNow in Lobby (e.g. countdown < 8s and we only have < 16 bots), un-click ready so partial bots don't get sucked in!
  if (!sq.includes('// Unready if squad is incomplete')) {
    sq = sq.replace(
      `          if (isInLobbyNow && !isReadyNow && \${allowReady ? 'true' : 'false'}) {`,
      `          // Unready if squad is incomplete (<16 bots) and countdown is getting close
          if (isInLobbyNow && isReadyNow && !\${allowReady ? 'true' : 'false'}) {
            if (bq?.sH && typeof bq.sH.select === "function" && bq.sH.wF !== 0) {
              bq.sH.select(0);
            }
          }
          if (isInLobbyNow && !isReadyNow && \${allowReady ? 'true' : 'false'}) {`
    );
  }

  fs.writeFileSync(sqPath, sq, 'utf8');
  console.log('Patched Ready gate (>=18/20) and zero-tick game server auto-heal in tsb-team-squad.mjs');
}
