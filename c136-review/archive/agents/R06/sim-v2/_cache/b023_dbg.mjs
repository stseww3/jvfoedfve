import { loadMatch, buildWorld, ReplayStepper } from '../lib/match.mjs';

const M = loadMatch('B023');
const g = buildWorld(M);
const st = new ReplayStepper(M, g);
st.runSpawnPhase();
const P = Number(process.argv[2] || 15);
const from = Number(process.argv[3] || 8700), to = Number(process.argv[4] || 8800);
const origDecide = g.botDecide.bind(g);
g.botDecide = function (p) {
  if (p === P || this.t >= from && p < this.humans) {
    const b0 = this.bal[p];
    const r = origDecide(p);
    console.log(`  t=${this.t} botDecide #${p} period ${this.botPeriod[p]}/${this.botPeriodGoal[p]} pct ${this.botPct[p]}/${this.botPctGoal[p]} timer→${this.botTimer[p]} 兵 ${b0}→${this.bal[p]} 领土 ${this.terr[p]}`);
    return r;
  }
  return origDecide(p);
};
const origDonate = g.transfer ? g.transfer.bind(g) : null;
let lastFast = 0;
while (!g.over && g.t <= to) {
  if (!st.step()) break;
  if (g.t >= from) {
    const a5c = g.teamCacheGet();
    if (g.t % 30 === 7 || g.endgameFast !== lastFast || g.teamW0 === 0) {
      console.log(`t=${g.t} endgameFast=${g.endgameFast} w0=${g.teamW0} cache=${Array.from(a5c).join(',')} 90%线=${Math.floor(90 * g.land / 100)} 80%线=${Math.floor(8 * g.land / 10)} 实时队地=${JSON.stringify(g.teamLands ? Array.from(g.teamLands()) : null)} timer15=${g.botTimer[15]} period15=${g.botPeriod[15]} bal12=${g.bal[12]} bal15=${g.bal[15]}`);
      lastFast = g.endgameFast;
    }
  }
  g.tick();
}
