#!/usr/bin/env python3
"""Download the official Minecraft client files for one version from Mojang's servers.

    fetch_client.py <version> <target_dir> [--skip-music]

Layout written under <target_dir>:
    versions/<v>/<v>.json, versions/<v>/<v>.jar, libraries/..., assets/indexes/<id>.json, assets/objects/xx/<hash>
and <target_dir>/classpath-<v>.txt with the classpath for Linux x86_64.
Every file is checked against the SHA-1 from the metadata. Nothing here belongs in a git repository.
"""
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES = "https://resources.download.minecraft.net"


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, path, sha1=None, retries=4):
    if os.path.exists(path) and (sha1 is None or sha1_of(path) == sha1):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last = None
    for attempt in range(retries):
        if attempt:
            time.sleep(4 * 2 ** (attempt - 1))
        try:
            tmp = path + ".part"
            with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
            if sha1 and sha1_of(tmp) != sha1:
                raise IOError(f"sha1 mismatch for {url}")
            os.replace(tmp, path)
            return True
        except Exception as exc:  # retried, then reported
            last = exc
    raise IOError(f"failed to download {url}: {last}")


def allowed(rules, os_name="linux"):
    if not rules:
        return True
    ok = False
    for rule in rules:
        cond = rule.get("os", {})
        if "name" in cond and cond["name"] != os_name:
            continue
        if "arch" in cond and cond["arch"] != "x86_64":
            continue
        if rule.get("features"):
            continue
        ok = rule["action"] == "allow"
    return ok


def main():
    version, target = sys.argv[1], sys.argv[2]
    skip_music = "--skip-music" in sys.argv

    with urllib.request.urlopen(MANIFEST, timeout=60) as resp:
        manifest = json.load(resp)
    entry = next(v for v in manifest["versions"] if v["id"] == version)
    vdir = os.path.join(target, "versions", version)
    vjson = os.path.join(vdir, f"{version}.json")
    fetch(entry["url"], vjson, entry["sha1"])
    with open(vjson) as fh:
        meta = json.load(fh)

    jobs = []
    client = meta["downloads"]["client"]
    client_jar = os.path.join(vdir, f"{version}.jar")
    jobs.append((client["url"], client_jar, client["sha1"]))

    classpath = []
    for lib in meta["libraries"]:
        if not allowed(lib.get("rules")):
            continue
        art = lib.get("downloads", {}).get("artifact")
        if not art:
            continue
        name = lib["name"]
        if "natives-" in name and "natives-linux" not in name:
            continue
        if name.endswith(("natives-linux-arm64", "natives-linux-arm32", "natives-linux-ppc64le", "natives-linux-riscv64")):
            continue
        path = os.path.join(target, "libraries", art["path"])
        jobs.append((art["url"], path, art["sha1"]))
        classpath.append(path)
    classpath.append(client_jar)

    index = meta["assetIndex"]
    index_path = os.path.join(target, "assets", "indexes", f"{index['id']}.json")
    fetch(index["url"], index_path, index["sha1"])
    with open(index_path) as fh:
        objects = json.load(fh)["objects"]
    skipped = 0
    for name, obj in objects.items():
        if skip_music and ("/sounds/music/" in name or "/sounds/records/" in name):
            skipped += 1
            continue
        h = obj["hash"]
        jobs.append((f"{RESOURCES}/{h[:2]}/{h}", os.path.join(target, "assets", "objects", h[:2], h), h))

    # Bulk download through one curl process: it reuses connections and caches DNS, which a
    # thread pool of urllib calls does not (the resolver here drops bursts of lookups).
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        present = list(pool.map(lambda j: os.path.exists(j[1]) and sha1_of(j[1]) == j[2], jobs))
    missing = [j for j, ok in zip(jobs, present) if not ok]
    done = len(missing)
    if missing:
        cfg = os.path.join(target, "curl-jobs.txt")
        with open(cfg, "w") as fh:
            for url, path, _ in missing:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                fh.write(f'url = "{url}"\noutput = "{path}"\n')
        subprocess.run(["curl", "-sS", "--fail", "--parallel", "--parallel-max", "8", "--retry", "5",
                        "--retry-all-errors", "--retry-delay", "2", "-K", cfg], check=False)
        os.remove(cfg)
        bad = [url for url, path, sha1 in missing if not os.path.exists(path) or sha1_of(path) != sha1]
        if bad:
            raise SystemExit(f"{len(bad)} files failed verification, e.g. {bad[0]}; run again to resume")

    with open(os.path.join(target, f"classpath-{version}.txt"), "w") as fh:
        fh.write(":".join(classpath))
    print(json.dumps({
        "version": version, "mainClass": meta["mainClass"], "assetIndex": index["id"],
        "files": len(jobs), "downloaded": done, "assets_skipped": skipped, "classpath_entries": len(classpath),
    }))


if __name__ == "__main__":
    main()
