import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

export const MAP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../data/maps');
// gzipped copies of the exported maps kept in the repository
const PACKED_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../maps');

// Terrain codes of unowned pixels, as stored by the game.
export const T_LAND = 1;
export const T_WATER = 2;
export const T_EDGE = 3;
export const T_MOUNTAIN = 5;

export const MOUNTAIN_MAPS = new Set([3, 7, 9, 21, 25]);

export function loadMap(index, seed) {
  let file = path.join(MAP_DIR, `${index}_${seed}.bin`);
  let buf;
  if (fs.existsSync(file)) buf = fs.readFileSync(file);
  else {
    file = path.join(PACKED_DIR, `${index}_${seed}.bin.gz`);
    buf = zlib.gunzipSync(fs.readFileSync(file));
  }
  if (buf.toString('latin1', 0, 4) !== 'TMAP') throw new Error(`bad map file ${file}`);
  const w = buf.readUInt16LE(4);
  const h = buf.readUInt16LE(6);
  const n = w * h;
  const type = new Uint8Array(buf.buffer, buf.byteOffset + 8, n).slice();
  const id = new Uint16Array(n);
  for (let p = 0; p < n; p++) id[p] = buf.readUInt16LE(8 + n + 2 * p);
  let land = 0;
  for (let p = 0; p < n; p++) if (type[p] === T_LAND) land++;
  return { index, seed, w, h, type, id, land, mountains: MOUNTAIN_MAPS.has(index) };
}
