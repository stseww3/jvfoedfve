#!/usr/bin/env python3
"""Check every Unity-package source file recorded in the game's PDBs against
Unity's official package sources.

Each portable PDB stores a SHA-256 of every source file the DLL was compiled
from. A match means the compiler was fed Unity's unmodified file.

usage: pkgsrc_check.py <pdb_docs.tsv> <registry_extract_dir> <editor_hashes.tsv> <out.txt>
  registry_extract_dir/<package>@<version>/package/...   (tarballs from download.packages.unity.com)
  editor_hashes.tsv: sha256, block, size, tar member  (from nsis_hash.py over the Editor installer)
"""
import hashlib
import os
import re
import sys
from collections import defaultdict

docs_tsv, reg_dir, editor_tsv, out_txt = sys.argv[1:5]

editor = defaultdict(list)
for line in open(editor_tsv):
    h, idx, size, name = line.rstrip("\n").split("\t")
    editor[h].append((int(idx), name))

file_hash_cache = {}


def sha256_file(p):
    if p not in file_hash_cache:
        file_hash_cache[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return file_hash_cache[p]


results = defaultdict(lambda: defaultdict(list))
for line in open(docs_tsv):
    pdb, _alg, h, _emb, path = line.rstrip("\n").split("\t")
    m = re.search(r"PackageCache/(com\.unity\.[^/@]+)@([^/]+)/(.*)$", path)
    if not m:
        if pdb.startswith(("Unity.", "UnityEngine.UI.")):
            kind = "GENERATED" if "Unity.SourceGenerators/" in path else "OTHER"
            results[pdb][kind].append(path)
        continue
    pkgver, rel = f"{m.group(1)}@{m.group(2)}", m.group(3)
    local = os.path.join(reg_dir, pkgver, "package", rel)
    if os.path.isdir(os.path.join(reg_dir, pkgver)):
        if not os.path.exists(local):
            results[pdb]["NOT_IN_OFFICIAL_PACKAGE"].append(f"{pkgver}/{rel}")
        elif sha256_file(local) == h:
            results[pdb]["MATCH (registry tarball)"].append(f"{pkgver}/{rel}")
        else:
            results[pdb]["MISMATCH"].append(f"{pkgver}/{rel}  pdb={h} official={sha256_file(local)}")
        continue
    hits = editor.get(h, [])
    if any(name == "package/" + rel or name.endswith("/" + rel) for _, name in hits):
        results[pdb]["MATCH (Editor installer, same path)"].append(f"{pkgver}/{rel}")
    elif hits:
        results[pdb]["MATCH (Editor installer, hash only)"].append(f"{pkgver}/{rel}  -> block {hits[0][0]} {hits[0][1]}")
    else:
        results[pdb]["NOT_FOUND"].append(f"{pkgver}/{rel}  pdb={h}")

order = ["MATCH (registry tarball)", "MATCH (Editor installer, same path)", "MATCH (Editor installer, hash only)",
         "GENERATED", "MISMATCH", "NOT_IN_OFFICIAL_PACKAGE", "NOT_FOUND", "OTHER"]
with open(out_txt, "w") as o:
    o.write("# Unity package sources: PDB SHA-256 of every source file vs Unity's official package files\n\n")
    for pdb in sorted(results):
        r = results[pdb]
        total = sum(len(v) for v in r.values())
        o.write(f"{pdb}: {total} documents | " + " | ".join(f"{k}={len(r[k])}" for k in order if r.get(k)) + "\n")
    o.write("\n")
    for pdb in sorted(results):
        for k in order:
            if k.startswith("MATCH"):
                continue
            for item in results[pdb].get(k, []):
                o.write(f"{pdb}\t{k}\t{item}\n")
print(open(out_txt).read()[:4000])
