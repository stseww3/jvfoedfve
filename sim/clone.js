// Fast deep copy of a running game for lookahead search. Static data and
// per-call scratch buffers are shared; everything that changes between ticks
// is copied. Route arrays are immutable once created, so only the route list
// itself is copied.
import { Game } from './game.js';
import { Rng } from './rng.js';

const SHARED = new Set([
  'map', 'wid', 'mountainMap', 'dir4', 'dir8', 'dirRing', 'humanColors',
  'colR', 'colG', 'colB', 'colLow', 'borR', 'borG', 'borB', 'froR', 'froG', 'froB',
  'botDiff', 'botPctStep', 'cellNb',
  'cand', 'frontCopy', 'mark', 'scratchList', 'tgt', 'bfsCost', 'spawnTiles',
]);
const LIST_OF_LISTS = new Set(['front', 'border', 'coast', 'cliff', 'cells']);
const LIST_OF_REFS = new Set(['routes', 'bRoute']);

Game.prototype.clone = function clone() {
  const g = Object.create(Game.prototype);
  for (const k of Object.keys(this)) {
    const v = this[k];
    if (v === null || typeof v !== 'object' || SHARED.has(k)) g[k] = v;
    else if (ArrayBuffer.isView(v)) g[k] = v.slice();
    else if (LIST_OF_LISTS.has(k)) g[k] = v.map((a) => (a ? a.slice() : a));
    else if (LIST_OF_REFS.has(k)) g[k] = v.slice();
    else if (v instanceof Map) g[k] = new Map(v);
    else if (v instanceof Rng) {
      g[k] = new Rng();
      g[k].s = v.s;
    } else throw new Error(`clone: unhandled field ${k}`);
  }
  return g;
};
