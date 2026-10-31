#!/usr/bin/env python3
"""Scan every non-PE file of the extracted game for embedded payloads.

Raw bytes are searched for executable/archive/script signatures. Unity
serialized files and UnityFS asset bundles are additionally opened with
UnityPy so the *decompressed* object data is scanned too, and every
TextAsset (the usual hiding place for raw blobs) is listed.

usage: datascan.py <extract_root> <out_report.txt> <out_summary.json>
"""
import json
import os
import re
import struct
import sys
from collections import Counter

import UnityPy

PE_EXT = {".dll", ".exe"}

SIMPLE_SIGS = {
    "ELF": re.compile(rb"\x7fELF[\x01\x02][\x01\x02]\x01"),
    "ZIP": re.compile(rb"PK\x03\x04"),
    "RAR": re.compile(rb"Rar!\x1a\x07"),
    "7Z": re.compile(rb"7z\xbc\xaf\x27\x1c"),
    "DOTNET_METADATA": re.compile(rb"BSJB\x01\x00\x01\x00"),
    "MACHO": re.compile(rb"\xcf\xfa\xed\xfe|\xce\xfa\xed\xfe"),
    "SCRIPT": re.compile(rb"(?i)powershell|cmd\.exe|wscript|cscript|mshta|rundll32|regsvr32|#!/bin/"),
}


def find_pe(data):
    hits = []
    for m in re.finditer(rb"MZ", data):
        off = m.start()
        if off + 0x40 > len(data):
            continue
        lfanew = struct.unpack_from("<I", data, off + 0x3C)[0]
        p = off + lfanew
        if 0 < lfanew < 0x1000 and p + 4 <= len(data) and data[p:p + 4] == b"PE\x00\x00":
            hits.append(off)
    return hits


def scan_bytes(data):
    found = {}
    pe = find_pe(data)
    if pe:
        found["PE"] = pe[:10]
    for name, rx in SIMPLE_SIGS.items():
        offs = [m.start() for m in rx.finditer(data)][:10]
        if offs:
            found[name] = offs
    return found


def unity_scan(path):
    """Return (object type counts, decompressed-data hits, text assets)."""
    env = UnityPy.load(path)
    types = Counter()
    hits = {}
    texts = []
    for obj in env.objects:
        tname = obj.type.name
        types[tname] += 1
        try:
            raw = obj.get_raw_data()
        except Exception:
            raw = b""
        h = scan_bytes(raw)
        if h:
            hits[f"{tname}#{obj.path_id}"] = h
        if tname == "TextAsset":
            try:
                d = obj.read()
                body = d.m_Script
                if isinstance(body, str):
                    body = body.encode("utf-8", "surrogateescape")
                texts.append((d.m_Name, len(body)))
                th = scan_bytes(body)
                if th:
                    hits[f"TextAsset:{d.m_Name}"] = th
            except Exception as e:
                texts.append((f"<unreadable path_id={obj.path_id}: {e}>", -1))
    return types, hits, texts


def classify(path, head):
    name = os.path.basename(path)
    if head.startswith(b"UnityFS"):
        return "UnityFS asset bundle"
    if name.endswith(".manifest"):
        return "AssetBundle manifest (text)"
    if head[:3] == b"\xff\xd8\xff":
        return "JPEG image"
    if head[4:8] == b"ftyp":
        return "MP4 video"
    if name.endswith(".resS") or name.endswith(".resource"):
        return "Unity streamed resource data"
    if re.match(r"^(level\d+|sharedassets\d+\.assets|resources\.assets|globalgamemanagers(\.assets)?|unity default resources|unity_builtin_extra)$", name):
        return "Unity serialized file"
    if name.endswith(".pdb") and head.startswith(b"BSJB"):
        return "Portable PDB (debug symbols)"
    return "other"


def jpeg_trailer(data):
    end = data.rfind(b"\xff\xd9")
    return -1 if end < 0 else len(data) - (end + 2)


def main():
    root, out_txt, out_json = sys.argv[1:4]
    summary = {}
    lines = []
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            if os.path.splitext(fn)[1].lower() in PE_EXT:
                continue
            data = open(p, "rb").read()
            kind = classify(p, data[:16])
            entry = {"kind": kind, "size": len(data)}
            raw_hits = scan_bytes(data)
            if kind == "Portable PDB (debug symbols)":
                raw_hits.pop("DOTNET_METADATA", None)
            entry["raw_hits"] = raw_hits
            if kind == "JPEG image":
                entry["bytes_after_jpeg_end"] = jpeg_trailer(data)
            if kind in ("UnityFS asset bundle", "Unity serialized file"):
                try:
                    types, hits, texts = unity_scan(p)
                    entry["object_types"] = dict(types)
                    entry["decompressed_hits"] = hits
                    entry["text_assets"] = texts
                except Exception as e:
                    entry["unity_error"] = str(e)
            summary[rel] = entry
            flag = bool(raw_hits) or bool(entry.get("decompressed_hits")) or entry.get("bytes_after_jpeg_end", 0) > 0
            lines.append(f"{'HIT ' if flag else 'ok  '} {rel}  [{kind}, {len(data)} bytes]")
            if raw_hits:
                lines.append(f"       raw: {raw_hits}")
            if entry.get("decompressed_hits"):
                lines.append(f"       decompressed: {entry['decompressed_hits']}")
            if "object_types" in entry:
                top = ", ".join(f"{k}={v}" for k, v in sorted(entry["object_types"].items(), key=lambda kv: -kv[1]))
                lines.append(f"       objects: {top}")
            for n, sz in entry.get("text_assets", []):
                lines.append(f"       TextAsset {n!r} {sz} bytes")
            if "unity_error" in entry:
                lines.append(f"       unity load error: {entry['unity_error']}")
            if entry.get("bytes_after_jpeg_end", 0) > 0:
                lines.append(f"       {entry['bytes_after_jpeg_end']} bytes after JPEG end marker")
    n_hit = sum(1 for l in lines if l.startswith("HIT"))
    n_ok = sum(1 for l in lines if l.startswith("ok"))
    lines.insert(0, f"# data scan: {n_ok + n_hit} non-PE files, {n_hit} with hits\n")
    open(out_txt, "w").write("\n".join(lines) + "\n")
    json.dump(summary, open(out_json, "w"), indent=1)
    print(lines[0])


if __name__ == "__main__":
    main()
