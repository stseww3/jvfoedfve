import fs from 'node:fs';

const targetPath = '../c110/v27-team-live.js';
let s = fs.readFileSync(targetPath, 'utf8').replace(/\r\n/g, '\n');

// 1. Unlock AI-bot clearing before dpEnd (cap dpKeep/peopleFloor against bots at min(35*L, 0.55*B))
const oldFloorFor0 = `  floorFor0(g, q, f) {
    const P = this.p;
    if (P.winR > 0 && g.t < P.dpEnd && !this.person(g, q)) return Math.max(this.winFloor(g, q), this.peopleFloor(g));`;

const newFloorFor0 = `  floorFor0(g, q, f) {
    const P = this.p;
    if (P.winR > 0 && g.t < P.dpEnd && !this.person(g, q)) {
      const L = Math.max(1, g.terr[this.me]), B = g.bal[this.me];
      const botKeepCap = Math.min(35 * L, Math.floor(0.55 * B));
      const baseWin = (this.botPx(g, q) * L) / (P.winR * Math.max(1, g.t));
      return Math.max(baseWin, Math.min(Math.max(this.dpKeep(g), this.peopleFloor(g), this.sb || 0), botKeepCap));
    }`;

if (s.includes(oldFloorFor0)) {
  s = s.replace(oldFloorFor0, newFloorFor0);
}

// 2. Unlock dpNeutral when bordering human neighbors (cap dpKeep at 0.50*bal and grab finite neutral pockets)
const oldDpNeutral = `    const fee = iV(12 * bal, 1024);
    const max = Math.min(P.dpSpend * bal, bal - this.dpKeep(g)) - fee;
    if (!(max > 0)) return;
    const rings = this.dpRings(g, u);
    let n = 0, sum = 0;
    for (const { r } of rings) {
      if (2 * (sum + r) + r > max) break;
      sum += r;
      n++;
    }
    if (n === 0) return;
    let later = 0;
    for (const { at } of rings) if (at + P.period <= 98) later++;
    if (later >= n) return;
    const X = 2 * sum + rings[n - 1].r;
    if (X < this.minCmd(g)) return;`;

const newDpNeutral = `    const fee = iV(12 * bal, 1024);
    const keepCap = this.neutral > 0 ? Math.min(this.dpKeep(g), Math.floor(0.50 * bal)) : this.dpKeep(g);
    const max = Math.min(P.dpSpend * bal, bal - keepCap) - fee;
    if (!(max > 0)) return;
    const rings = this.dpRings(g, u);
    let n = 0, sum = 0;
    for (const { r } of rings) {
      if (2 * (sum + r) + r > max) break;
      sum += r;
      n++;
    }
    if (n === 0) return;
    const isFinitePocket = n === rings.length && rings.length <= 8 && g.t >= 450;
    let later = 0;
    for (const { at } of rings) if (at + P.period <= 98) later++;
    if (!isFinitePocket && later >= n) return;
    const X = 2 * sum + rings[n - 1].r;
    const effMin = isFinitePocket ? Math.min(this.minCmd(g), Math.max(80, 2 * fee)) : this.minCmd(g);
    if (X < effMin) return;`;

if (s.includes(oldDpNeutral)) {
  s = s.replace(oldDpNeutral, newDpNeutral);
}

// 3. Filter <18000px pockets/islands in chooseSpawn and fix g.px===0 in fallback
const oldSpawnBlock = `      const chosenSlots = [];
      for (const pos of cands) {
        const x = typeof pos === "object" ? pos.x : (pos % W);
        const y = typeof pos === "object" ? pos.y : Math.floor(pos / W);
        let tooClose = false;
        for (const prev of chosenSlots) {
          if (Math.hypot(x - prev.x, y - prev.y) < minSep) { tooClose = true; break; }
        }
        if (!tooClose) {
          chosenSlots.push({ x, y });
          if (chosenSlots.length > slot) break;
        }
      }
      // If fewer than slot+1 candidates pass minSep, relax minSep to 0.65x so slots never collide
      if (chosenSlots.length <= slot) {
        const relaxSep = minSep * 0.62;
        for (const pos of cands) {
          const x = typeof pos === "object" ? pos.x : (pos % W);
          const y = typeof pos === "object" ? pos.y : Math.floor(pos / W);
          if (chosenSlots.every((p) => Math.hypot(x - p.x, y - p.y) >= relaxSep)) {
            chosenSlots.push({ x, y });
            if (chosenSlots.length > slot) break;
          }
        }
      }
      let res = chosenSlots[slot] || cands[slot % cands.length];
      if (!chosenSlots[slot] && chosenSlots.length > 0) {
        // Fallback: Farthest-Point Sampling across the land grid so all 5 slots are guaranteed >= 160px apart!
        const mType = g.map?.type || g.px;
        for (let sIdx = chosenSlots.length; sIdx <= slot; sIdx++) {
          let bestPt = null, bestD = -1;
          for (let y = 18; y < H - 18; y += 16) {
            for (let x = 18; x < W - 18; x += 16) {
              if (mType[y * W + x] !== 1 && mType[y * W + x] < 16) continue;`;

const newSpawnBlock = `      const comp = this.compSize ? this.compSize(gClean) : null;
      const minMainLand = Math.min(18000, Math.floor(0.18 * Math.max(1, g.land)));
      const chosenSlots = [];
      for (const pos of cands) {
        const x = typeof pos === "object" ? pos.x : (pos % W);
        const y = typeof pos === "object" ? pos.y : Math.floor(pos / W);
        if (comp && comp[y * W + x] > 0 && comp[y * W + x] < minMainLand) continue;
        let tooClose = false;
        for (const prev of chosenSlots) {
          if (Math.hypot(x - prev.x, y - prev.y) < minSep) { tooClose = true; break; }
        }
        if (!tooClose) {
          chosenSlots.push({ x, y });
          if (chosenSlots.length > slot) break;
        }
      }
      if (chosenSlots.length <= slot) {
        const relaxSep = minSep * 0.62;
        for (const pos of cands) {
          const x = typeof pos === "object" ? pos.x : (pos % W);
          const y = typeof pos === "object" ? pos.y : Math.floor(pos / W);
          if (comp && comp[y * W + x] > 0 && comp[y * W + x] < minMainLand) continue;
          if (chosenSlots.every((p) => Math.hypot(x - p.x, y - p.y) >= relaxSep)) {
            chosenSlots.push({ x, y });
            if (chosenSlots.length > slot) break;
          }
        }
      }
      let res = chosenSlots[slot] || cands[slot % cands.length];
      if (!chosenSlots[slot] && chosenSlots.length > 0) {
        const pxArr = gClean.px;
        for (let sIdx = chosenSlots.length; sIdx <= slot; sIdx++) {
          let bestPt = null, bestD = -1;
          for (let y = 18; y < H - 18; y += 16) {
            for (let x = 18; x < W - 18; x += 16) {
              const idx = y * W + x;
              if (pxArr[idx] !== 0) continue;
              if (comp && comp[idx] > 0 && comp[idx] < minMainLand) continue;`;

if (s.includes(oldSpawnBlock)) {
  s = s.replace(oldSpawnBlock, newSpawnBlock);
}

// 4. Early neutral remnant cleanup & transition when neutral===0 and no bots remain at t>=750
const oldEarlyAct = `      super.act(g);
      if (this.cmds > before && g.bal[me] <= 0.75 * balBefore) {
        this.lastLandSpendTick = g.t;
      }`;

const newEarlyAct = `      super.act(g);
      if (this.cmds === before && g.t >= 600 && this.neutral > 0 && g.attackTroopsOn(me, NEUTRAL) === 0) {
        const grab = Math.min(Math.floor(0.35 * g.bal[me]), Math.max(this.minCmd(g), 4 * this.neutral + 120));
        if (grab > 0 && g.bal[me] - grab > 12 * Math.max(1, g.terr[me])) this.send(g, NEUTRAL, grab);
      }
      if (this.cmds === before && g.t >= 750 && this.neutral === 0 && !this.hasBorderFood(g)) {
        this.buyLand(g);
        if (this.cmds === before) this.tryDonateToTeammate(g);
      }
      if (this.cmds > before && g.bal[me] <= 0.75 * balBefore) {
        this.lastLandSpendTick = g.t;
      }`;

if (s.includes(oldEarlyAct)) {
  s = s.replace(oldEarlyAct, newEarlyAct);
}

// 5. Cap safeAt by oppFloorCap * L for all targets and unlock 12%B pulse expansion at dMe >= 132
const oldSafeAt = `    if (q < 0 || !this.person(g, q)) {
      s = Math.min(s, P.oppFloorCap * L);
    } else if`;

const newSafeAt = `    s = Math.min(s, P.oppFloorCap * L);
    if (q < 0 || !this.person(g, q)) {
      s = Math.min(s, P.oppFloorCap * L);
    } else if`;

if (s.includes(oldSafeAt)) {
  s = s.replace(oldSafeAt, newSafeAt);
}

const oldOverPulse = `      keep = Math.max(keep, safe);

      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }

      const usePulseBlock =
        P.pulseFrac > 0 && (!over || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));`;

const newOverPulse = `      keep = Math.max(keep, safe);
      if (dMe >= 132) {
        keep = Math.min(keep, 108 * L);
      }

      const avail = B - fee - keep;
      if (avail <= 0) continue;

      if (!person) {
        const want = 1.25 * need + 3 * this.cnt[q];
        const x = Math.min(avail, want);
        if (x <= 0 || (x < want && x < P.chunk * B)) continue;
        return this.send(g, q, x);
      }

      const usePulseBlock =
        P.pulseFrac > 0 && (!over || dMe >= 132 || (P.overPulseMode > 0 && (o.nearCollapse || o.bleeding || avail < P.chunk * B)));`;

if (s.includes(oldOverPulse)) {
  s = s.replace(oldOverPulse, newOverPulse);
}

fs.writeFileSync(targetPath, s, 'utf8');
console.log('Successfully patched ../c110/v27-team-live.js! New size:', s.length);
