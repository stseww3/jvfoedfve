#!/usr/bin/env python3
"""Download the official Minecraft client files for one version from Mojang's servers.

    fetch_client.py <version> <target_dir> [--skip-music] [--server <server_dir>]

Layout written under <target_dir>:
    versions/<v>/<v>.json, versions/<v>/<v>.jar, libraries/..., assets/indexes/<id>.json, assets/objects/xx/<hash>
and <target_dir>/classpath-<v>.txt with the classpath for the machine it runs on (Linux or Windows,
x86_64), one path per line, relative to <target_dir>.
`--server` also fetches the server jar of the same version into <server_dir>/server.jar.
Every file is checked against the SHA-1 from the metadata. Nothing here belongs in a git repository.
"""
import concurrent.futures
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES = "https://resources.download.minecraft.net"
OS_NAME = {"Linux": "linux", "Windows": "windows", "Darwin": "osx"}[platform.system()]

# Only a proxy named in the environment is used. A Windows machine may carry a system proxy in its
# settings that nothing listens on, and Python would pick that up by itself.
urllib.request.install_opener(urllib.request.build_opener(
    urllib.request.ProxyHandler(urllib.request.getproxies_environment())))


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


def allowed(rules, os_name=OS_NAME):
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


def wanted_natives(name, os_name=OS_NAME):
    """Libraries named group:artifact:version:natives-<system>[-<cpu>] carry machine code; keep the
    one for this system on x86_64 and none of the others."""
    parts = name.split(":")
    if len(parts) < 4 or not parts[3].startswith("natives-"):
        return True
    return parts[3] == f"natives-{os_name}"


def main():
    args = sys.argv[1:]
    skip_music = "--skip-music" in args
    server_dir = None
    if "--server" in args:
        server_dir = args[args.index("--server") + 1]
        del args[args.index("--server"):args.index("--server") + 2]
    version, target = args[0], os.path.abspath(args[1])

    with urllib.request.urlopen(MANIFEST, timeout=60) as resp:
        manifest = json.load(resp)
    entry = next(v for v in manifest["versions"] if v["id"] == version)
    vdir = os.path.join("versions", version)
    vjson = os.path.join(target, vdir, f"{version}.json")
    fetch(entry["url"], vjson, entry["sha1"])
    with open(vjson) as fh:
        meta = json.load(fh)

    # (url, path relative to the target folder, sha1)
    jobs = []
    client = meta["downloads"]["client"]
    client_jar = os.path.join(vdir, f"{version}.jar")
    jobs.append((client["url"], client_jar, client["sha1"]))

    classpath = []
    for lib in meta["libraries"]:
        if not allowed(lib.get("rules")):
            continue
        art = lib.get("downloads", {}).get("artifact")
        if not art or not wanted_natives(lib["name"]):
            continue
        path = os.path.join("libraries", *art["path"].split("/"))
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
        jobs.append((f"{RESOURCES}/{h[:2]}/{h}", os.path.join("assets", "objects", h[:2], h), h))

    def present(job):
        path = os.path.join(target, job[1])
        return os.path.exists(path) and sha1_of(path) == job[2]

    # Bulk download through one curl process: it reuses connections and caches DNS, which a
    # thread pool of urllib calls does not (the resolver here drops bursts of lookups).
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        have = list(pool.map(present, jobs))
    missing = [j for j, ok in zip(jobs, have) if not ok]
    done = len(missing)
    if missing:
        # curl runs inside the target folder and gets relative paths with forward slashes: its
        # list file treats backslashes as escapes and knows nothing of the folder's encoding
        cfg = os.path.join(target, "curl-jobs.txt")
        with open(cfg, "w", encoding="ascii") as fh:
            for url, path, _ in missing:
                os.makedirs(os.path.dirname(os.path.join(target, path)), exist_ok=True)
                fh.write('url = "{}"\noutput = "{}"\n'.format(url, path.replace(os.sep, "/")))
        cmd = ["curl", "-sS", "--fail", "--parallel", "--parallel-max", "8", "--retry", "5",
               "--retry-all-errors", "--retry-delay", "2", "-K", "curl-jobs.txt"]
        if OS_NAME == "windows":
            # the system's certificate check asks a revocation server that may be out of reach;
            # the certificates themselves are still verified
            cmd[1:1] = ["--ssl-revoke-best-effort"]
        subprocess.run(cmd, check=False, cwd=target)
        os.remove(cfg)
        bad = [url for url, path, sha1 in missing if not present((url, path, sha1))]
        if bad:
            raise SystemExit(f"{len(bad)} files failed verification, e.g. {bad[0]}; run again to resume")

    with open(os.path.join(target, f"classpath-{version}.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(classpath) + "\n")

    report = {
        "version": version, "system": OS_NAME, "mainClass": meta["mainClass"], "assetIndex": index["id"],
        "files": len(jobs), "downloaded": done, "assets_skipped": skipped, "classpath_entries": len(classpath),
    }
    if server_dir:
        server = meta["downloads"]["server"]
        report["server_downloaded"] = fetch(server["url"], os.path.join(os.path.abspath(server_dir), "server.jar"),
                                            server["sha1"])
    print(json.dumps(report))


if __name__ == "__main__":
    main()
