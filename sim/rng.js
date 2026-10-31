// The game's seeded generator: a multiplicative LCG modulo 2^15.
const PCT = new Uint16Array(101);
for (let i = 0; i <= 100; i++) PCT[i] = Math.floor((32768 * i + 0.5) / 100);

export class Rng {
  constructor() {
    this.s = 1;
  }

  seed(n) {
    this.s = ((2 * n) % 32768) + 1;
  }

  next() {
    return (this.s = (167 * this.s) % 32768);
  }

  int(n) {
    return Math.floor((n * this.next() + 0.5) / 32768);
  }

  chance(pct) {
    return pct !== 0 && this.next() < PCT[pct];
  }

  range(a, b) {
    return a + this.int(b - a);
  }

  half() {
    return Math.floor((this.s - 1 + 0.5) / 2);
  }
}

export const RNG_PCT = PCT;
