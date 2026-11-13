#!/usr/bin/env python3
"""Block / block-entity / entity census of a Minecraft Java world (1.18+ chunk format).

Usage: census.py <world_dir> [--dim overworld] [--json out.json]
Read-only. Counts block states per id, bounding box of non-air blocks, block entities, entities.
"""
import collections
import gzip
import io
import json
import os
import re
import struct
import sys
import zlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import nbtlib

AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def read_chunks(path):
    """Yield (cx_in_region, cz_in_region, raw_nbt_bytes) for each chunk in a region file."""
    size = os.path.getsize(path)
    if size < 8192:
        return
    with open(path, "rb") as fh:
        header = fh.read(4096)
        for i in range(1024):
            entry = header[i * 4:i * 4 + 4]
            if entry == b"\x00\x00\x00\x00":
                continue
            off = int.from_bytes(entry[:3], "big") * 4096
            if off == 0 or off >= size:
                continue
            fh.seek(off)
            head = fh.read(5)
            if len(head) < 5:
                continue
            length, ctype = struct.unpack(">IB", head)
            if length <= 1:
                continue
            if ctype & 0x80:
                continue  # external .mcc chunk, ignored
            data = fh.read(length - 1)
            try:
                if ctype == 1:
                    raw = gzip.decompress(data)
                elif ctype == 2:
                    raw = zlib.decompress(data)
                elif ctype == 3:
                    raw = data
                else:
                    continue  # lz4 or unknown
            except Exception:  # noqa: BLE001
                continue
            yield i % 32, i // 32, raw


def parse_nbt(raw):
    return nbtlib.File.parse(io.BytesIO(raw), byteorder="big")


def palette_name(p):
    """Block id of a palette entry.

    Up to 26.1.x entries are {Name, Properties}. In 26.3 (DataVersion 5023) entries are either a bare
    string id (stored wrapped as {"": id} because NBT lists are homogeneous) or {id, properties}.
    """
    if isinstance(p, str):
        return str(p)
    for key in ("Name", "id", ""):
        if key in p:
            return str(p[key])
    return "?"


def section_counts(section):
    bs = section.get("block_states")
    if bs is None:
        return None, None
    palette = bs.get("palette")
    if palette is None:
        return None, None
    names = [palette_name(p) for p in palette]
    data = bs.get("data")
    if data is None or len(names) == 1:
        return names, np.array([4096], dtype=np.int64) if len(names) == 1 else None
    bits = max(4, (len(names) - 1).bit_length())
    per_long = 64 // bits
    longs = np.asarray(data, dtype=np.int64).astype(np.uint64)
    mask = np.uint64((1 << bits) - 1)
    idx = np.empty((len(longs), per_long), dtype=np.uint16)
    for j in range(per_long):
        idx[:, j] = ((longs >> np.uint64(j * bits)) & mask).astype(np.uint16)
    flat = idx.reshape(-1)[:4096]
    counts = np.bincount(flat, minlength=len(names))[:len(names)]
    return names, counts


def process_region(args):
    path, kind = args
    m = re.match(r"r\.(-?\d+)\.(-?\d+)\.mca", os.path.basename(path))
    rx, rz = int(m.group(1)), int(m.group(2))
    blocks = collections.Counter()
    bents = collections.Counter()
    ents = collections.Counter()
    cmd_blocks = 0
    cmd_chars = 0
    nonair_chunks = 0
    bbox = [10**9, 10**9, 10**9, -10**9, -10**9, -10**9]
    chunk_cols = []
    for lx, lz, raw in read_chunks(path):
        try:
            nbt = parse_nbt(raw)
        except Exception:  # noqa: BLE001
            continue
        cx, cz = rx * 32 + lx, rz * 32 + lz
        if kind == "entities":
            for e in nbt.get("Entities", []):
                stack = [e]
                while stack:
                    cur = stack.pop()
                    ents[str(cur.get("id", "?"))] += 1
                    for p in cur.get("Passengers", []):
                        stack.append(p)
            continue
        has_nonair = False
        for sec in nbt.get("sections", []):
            names, counts = section_counts(sec)
            if names is None or counts is None:
                continue
            y = int(sec.get("Y", 0))
            sec_nonair = 0
            for n, c in zip(names, counts):
                c = int(c)
                if c:
                    blocks[n] += c
                    if n not in AIR:
                        sec_nonair += c
            if sec_nonair:
                has_nonair = True
                bbox[0] = min(bbox[0], cx * 16)
                bbox[2] = min(bbox[2], cz * 16)
                bbox[3] = max(bbox[3], cx * 16 + 15)
                bbox[5] = max(bbox[5], cz * 16 + 15)
                bbox[1] = min(bbox[1], y * 16)
                bbox[4] = max(bbox[4], y * 16 + 15)
        if has_nonair:
            nonair_chunks += 1
            chunk_cols.append((cx, cz))
        for be in nbt.get("block_entities", []):
            bid = str(be.get("id", "?"))
            bents[bid] += 1
            if bid == "minecraft:command_block":
                cmd_blocks += 1
                cmd_chars += len(str(be.get("Command", "")))
    return blocks, bents, ents, cmd_blocks, cmd_chars, nonair_chunks, bbox, chunk_cols


def main():
    args = sys.argv[1:]
    out_json = None
    dim = None
    if "--json" in args:
        i = args.index("--json")
        out_json = args[i + 1]
        del args[i:i + 2]
    if "--dim" in args:
        i = args.index("--dim")
        dim = args[i + 1]
        del args[i:i + 2]
    root = args[0]
    world = None
    for r, _d, files in os.walk(root):
        if "level.dat" in files:
            world = r
            break
    jobs = []
    for r, dirs, _files in os.walk(world):
        base = os.path.basename(r)
        if base in ("region", "entities"):
            if dim and dim not in r and not (dim == "overworld" and os.path.dirname(r) == world):
                continue
            for f in sorted(os.listdir(r)):
                if f.endswith(".mca"):
                    jobs.append((os.path.join(r, f), base))
    blocks = collections.Counter()
    bents = collections.Counter()
    ents = collections.Counter()
    cmd_blocks = cmd_chars = nonair_chunks = 0
    bbox = [10**9, 10**9, 10**9, -10**9, -10**9, -10**9]
    cols = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for res in ex.map(process_region, jobs):
            b, be, e, cb, cc, nc, bb, cl = res
            blocks.update(b)
            bents.update(be)
            ents.update(e)
            cmd_blocks += cb
            cmd_chars += cc
            nonair_chunks += nc
            cols.extend(cl)
            for i in range(3):
                bbox[i] = min(bbox[i], bb[i])
            for i in range(3, 6):
                bbox[i] = max(bbox[i], bb[i])
    nonair = {k: v for k, v in blocks.items() if k not in AIR}
    total_nonair = sum(nonair.values())
    print("#### CENSUS:", world)
    print("region+entity files:", len(jobs))
    print("chunks with non-air blocks:", nonair_chunks)
    print("non-air blocks:", total_nonair, " distinct block ids:", len(nonair))
    print("bbox of chunks with non-air blocks (x,y,z min -> max):", bbox[:3], "->", bbox[3:])
    # main cluster: ignore far outlier chunks for a tighter bbox
    if cols:
        xs = np.array([c[0] for c in cols])
        zs = np.array([c[1] for c in cols])
        mx, mz = np.median(xs), np.median(zs)
        near = (np.abs(xs - mx) < 200) & (np.abs(zs - mz) < 200)
        print("main cluster (within 200 chunks of median): chunks=%d, x[%d..%d] z[%d..%d] blocks" % (
            near.sum(), xs[near].min() * 16, xs[near].max() * 16 + 15, zs[near].min() * 16, zs[near].max() * 16 + 15))
        print("outlier chunks:", int((~near).sum()))
    print("top blocks:")
    for k, v in sorted(nonair.items(), key=lambda kv: -kv[1])[:60]:
        print(f"  {k.replace('minecraft:', ''):40s} {v:>10d}  {100.0 * v / max(1, total_nonair):5.1f}%")
    print("block entities:", dict(bents.most_common(25)))
    print("command blocks:", cmd_blocks, "total command chars:", cmd_chars)
    print("entities:", dict(ents.most_common(30)))
    if out_json:
        with open(out_json, "w") as fh:
            json.dump({"world": world, "blocks": dict(blocks), "block_entities": dict(bents), "entities": dict(ents),
                       "bbox": bbox, "nonair_chunks": nonair_chunks, "command_blocks": cmd_blocks,
                       "command_chars": cmd_chars}, fh)


if __name__ == "__main__":
    main()
