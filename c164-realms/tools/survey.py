#!/usr/bin/env python3
"""Survey a Minecraft Java world folder: level.dat, datapacks, resource pack, region files.

Usage: survey.py <world_dir> [--rp <resource_pack_dir_or_zip>]
Read-only. Prints a plain-text report.
"""
import collections
import io
import json
import os
import re
import sys
import zipfile

import nbtlib


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def find_world_root(path):
    for root, _dirs, files in os.walk(path):
        if "level.dat" in files:
            return root
    return None


def nbt_get(tag, *keys, default=None):
    cur = tag
    for k in keys:
        try:
            cur = cur[k]
        except (KeyError, TypeError, IndexError):
            return default
    return cur


def survey_level(world):
    f = nbtlib.load(os.path.join(world, "level.dat"))
    data = f.get("Data", f)
    print("== level.dat")
    print("  top-level keys:", sorted(data.keys()))
    ver = data.get("Version")
    if ver is not None:
        print("  Version:", {k: (v.unpack() if hasattr(v, "unpack") else v) for k, v in ver.items()})
    for k in ("DataVersion", "LevelName", "GameType", "Difficulty", "DifficultyLocked", "hardcore",
              "allowCommands", "SpawnX", "SpawnY", "SpawnZ", "DayTime", "Time", "raining", "initialized"):
        if k in data:
            print(f"  {k}: {data[k]}")
    for k in ("spawn", "difficulty_settings"):
        if k in data:
            print(f"  {k}: {data[k].unpack() if hasattr(data[k], 'unpack') else data[k]}")
    dp = data.get("DataPacks")
    if dp is not None:
        print("  DataPacks.Enabled:", [str(x) for x in dp.get("Enabled", [])])
        print("  DataPacks.Disabled:", [str(x) for x in dp.get("Disabled", [])])
    gr = data.get("GameRules") or data.get("game_rules")
    if gr is not None:
        print("  GameRules (in level.dat):")
        for k in sorted(gr.keys()):
            print(f"    {k} = {gr[k]}")
    ef = data.get("enabled_features")
    if ef is not None:
        print("  enabled_features:", [str(x) for x in ef])


def survey_data_dir(world):
    d = os.path.join(world, "data")
    if not os.path.isdir(d):
        return
    print("== data/ files")
    for root, _dirs, files in os.walk(d):
        for fn in sorted(files):
            p = os.path.join(root, fn)
            print(f"  {os.path.relpath(p, world)}  {human(os.path.getsize(p))}")
    for cand in ("data/minecraft/game_rules.dat",):
        p = os.path.join(world, cand)
        if os.path.exists(p):
            try:
                t = nbtlib.load(p)
                print(f"== {cand}")
                print("  ", json.dumps(t.unpack(json=True), ensure_ascii=False)[:4000])
            except Exception as e:  # noqa: BLE001
                print("  (could not parse)", e)
    for cand in ("data/scoreboard.dat", "data/minecraft/scoreboard.dat"):
        p = os.path.join(world, cand)
        if os.path.exists(p):
            try:
                t = nbtlib.load(p)
                data = t.get("data", t)
                objs = data.get("Objectives", [])
                teams = data.get("Teams", [])
                scores = data.get("PlayerScores", [])
                print(f"== {cand}: objectives={len(objs)} teams={len(teams)} scores={len(scores)}")
                crit = collections.Counter(str(o.get("CriteriaName", "?")) for o in objs)
                print("  criteria:", dict(crit.most_common(12)))
                print("  sample objectives:", [str(o.get("Name")) for o in objs[:40]])
            except Exception as e:  # noqa: BLE001
                print("  (could not parse)", e)


RES_TYPES = [
    "function", "functions", "advancement", "advancements", "predicate", "predicates", "loot_table", "loot_tables",
    "item_modifier", "item_modifiers", "recipe", "recipes", "tags", "structure", "structures", "dimension",
    "dimension_type", "worldgen", "damage_type", "enchantment", "dialog", "chat_type", "trim_material",
    "trim_pattern", "banner_pattern", "painting_variant", "jukebox_song", "instrument", "test_instance",
    "test_environment", "timeline", "world_clock",
]


def survey_datapack(dp_path):
    print(f"== datapack: {dp_path}")
    names = []
    read = None
    if os.path.isdir(dp_path):
        for root, _d, files in os.walk(dp_path):
            for fn in files:
                names.append(os.path.relpath(os.path.join(root, fn), dp_path).replace(os.sep, "/"))

        def read(n):
            with open(os.path.join(dp_path, n), "rb") as fh:
                return fh.read()
    else:
        z = zipfile.ZipFile(dp_path)
        names = [n for n in z.namelist() if not n.endswith("/")]
        read = z.read
    if "pack.mcmeta" in names:
        try:
            print("  pack.mcmeta:", json.dumps(json.loads(read("pack.mcmeta").decode("utf-8-sig")), ensure_ascii=False)[:600])
        except Exception as e:  # noqa: BLE001
            print("  pack.mcmeta unreadable:", e)
    by_ns = collections.defaultdict(lambda: collections.Counter())
    fn_lines = collections.Counter()
    fn_cmds = collections.Counter()
    cmd_heads = collections.Counter()
    total_lines = 0
    biggest = []
    for n in names:
        m = re.match(r"(?:.*?/)?data/([^/]+)/([^/]+)/(.*)", n)
        if not m:
            continue
        ns, typ, rest = m.groups()
        by_ns[ns][typ] += 1
        if typ in ("function", "functions") and n.endswith(".mcfunction"):
            try:
                txt = read(n).decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                continue
            lines = [l.strip() for l in txt.splitlines()]
            code = [l for l in lines if l and not l.startswith("#")]
            fn_lines[ns] += len(lines)
            fn_cmds[ns] += len(code)
            total_lines += len(code)
            biggest.append((len(code), n))
            for l in code:
                head = l.split(" ", 1)[0].lstrip("$")
                cmd_heads[head] += 1
    for ns in sorted(by_ns):
        print(f"  ns {ns}: {dict(by_ns[ns])}  function-commands={fn_cmds[ns]}")
    print("  total function commands:", total_lines)
    print("  top command heads:", cmd_heads.most_common(40))
    biggest.sort(reverse=True)
    print("  biggest functions:", biggest[:8])
    for tagname in ("tick", "load"):
        for n in names:
            if n.endswith(f"data/minecraft/tags/function/{tagname}.json") or n.endswith(f"data/minecraft/tags/functions/{tagname}.json"):
                try:
                    print(f"  #{tagname}:", json.loads(read(n).decode("utf-8-sig")))
                except Exception as e:  # noqa: BLE001
                    print(f"  #{tagname} unreadable", e)


def survey_resource_pack(rp_path):
    print(f"== resource pack: {rp_path}")
    if os.path.isdir(rp_path):
        names = []
        sizes = {}
        for root, _d, files in os.walk(rp_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, rp_path).replace(os.sep, "/")
                names.append(rel)
                sizes[rel] = os.path.getsize(p)

        def read(n):
            with open(os.path.join(rp_path, n), "rb") as fh:
                return fh.read()
    else:
        try:
            z = zipfile.ZipFile(rp_path)
        except Exception as e:  # noqa: BLE001
            print("  not a readable zip:", e)
            return
        infos = [i for i in z.infolist() if not i.filename.endswith("/")]
        names = [i.filename for i in infos]
        sizes = {i.filename: i.file_size for i in infos}
        read = z.read
    print(f"  files: {len(names)}  uncompressed: {human(sum(sizes.values()))}")
    if "pack.mcmeta" in names:
        try:
            print("  pack.mcmeta:", json.dumps(json.loads(read("pack.mcmeta").decode("utf-8-sig")), ensure_ascii=False)[:600])
        except Exception as e:  # noqa: BLE001
            print("  pack.mcmeta unreadable:", e)
    cat = collections.Counter()
    catsize = collections.Counter()
    for n in names:
        m = re.match(r"assets/([^/]+)/([^/]+)(?:/|$)", n)
        key = f"{m.group(1)}/{m.group(2)}" if m else n.split("/")[0]
        cat[key] += 1
        catsize[key] += sizes[n]
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v} files, {human(catsize[k])}")
    ext = collections.Counter(os.path.splitext(n)[1].lower() for n in names)
    print("  by extension:", dict(ext.most_common(12)))
    shaders = [n for n in names if "/shaders/" in n]
    if shaders:
        print("  shaders:", shaders[:40])
    fonts = [n for n in names if "/font/" in n and n.endswith(".json")]
    print("  font json:", fonts[:30])


def region_dirs(world):
    out = []
    for root, dirs, _files in os.walk(world):
        for d in dirs:
            if d in ("region", "entities", "poi"):
                out.append(os.path.join(root, d))
    return sorted(out)


def survey_regions(world):
    print("== region-like dirs")
    for d in region_dirs(world):
        files = [f for f in os.listdir(d) if f.endswith(".mca")]
        size = sum(os.path.getsize(os.path.join(d, f)) for f in files)
        coords = []
        chunks = 0
        for f in files:
            m = re.match(r"r\.(-?\d+)\.(-?\d+)\.mca", f)
            if not m:
                continue
            rx, rz = int(m.group(1)), int(m.group(2))
            p = os.path.join(d, f)
            if os.path.getsize(p) < 8192:
                continue
            with open(p, "rb") as fh:
                header = fh.read(4096)
            present = sum(1 for i in range(1024) if header[i * 4:i * 4 + 4] != b"\x00\x00\x00\x00")
            if present:
                coords.append((rx, rz))
                chunks += present
        if coords:
            xs = [c[0] for c in coords]
            zs = [c[1] for c in coords]
            bbox = f"regions x[{min(xs)}..{max(xs)}] z[{min(zs)}..{max(zs)}]"
        else:
            bbox = "no chunks"
        print(f"  {os.path.relpath(d, world)}: {len(files)} files, {human(size)}, chunks={chunks}, {bbox}")


def main():
    args = sys.argv[1:]
    rp = None
    if "--rp" in args:
        i = args.index("--rp")
        rp = args[i + 1]
        del args[i:i + 2]
    world = find_world_root(args[0])
    if not world:
        print("no level.dat under", args[0])
        return 1
    print("#### WORLD:", world)
    survey_level(world)
    survey_data_dir(world)
    dpdir = os.path.join(world, "datapacks")
    if os.path.isdir(dpdir):
        for name in sorted(os.listdir(dpdir)):
            survey_datapack(os.path.join(dpdir, name))
    for cand in ("resources.zip", "resourcepacks/resources.zip"):
        p = os.path.join(world, cand)
        if os.path.exists(p):
            survey_resource_pack(p)
    if rp:
        survey_resource_pack(rp)
    survey_regions(world)
    return 0


if __name__ == "__main__":
    sys.exit(main())
