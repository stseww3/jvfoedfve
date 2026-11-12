#!/usr/bin/env node
/**
 * Standalone Sketchfab Public 3D Model Downloader (Node 20+, zero npm dependencies)
 *
 * Usage:
 *   node sketchfab_dl.mjs <sketchfab-url-or-uid> [output-dir]
 *
 * Exports self-contained .glb (with embedded descrambled RGBA textures, pixel-art
 * NEAREST sampler & AlphaMask preservation, skeleton & animations) + loose textures.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  extractUid,
  fetchViewerInfo,
  extractStaticKey,
  getDiterB,
  modelBinzUrls,
  fetchBytes,
  fetchTextures,
  fetchAnimations,
  parseViewerMaterials,
  viewerOrientation,
  sanitizeName,
} from "./lib/sf-api.js";
import { decryptBinzBytes, outNameFor } from "./lib/decrypt.js";
import { convertOsgjsToGlbFromFiles } from "./lib/osgjs2gltf.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function patchPixelArtAndAlphaMask(glbBytes, viewerInfo) {
  const mats = (viewerInfo && viewerInfo.options && viewerInfo.options.materials) || {};
  let hasNearest = false;
  let alphaMaskCutoff = null;
  for (const [id, m] of Object.entries(mats)) {
    if (id === "updatedAt" || !m || !m.channels) continue;
    const alb = m.channels.AlbedoPBR || m.channels.DiffuseColor || {};
    if (alb.texture && alb.texture.magFilter === "NEAREST") hasNearest = true;
    const am = m.channels.AlphaMask;
    if (am && am.enable && am.texture) {
      alphaMaskCutoff = typeof am.factor === "number" ? am.factor : 0.05;
    }
  }
  if (!hasNearest && alphaMaskCutoff === null) return glbBytes;

  const dv = new DataView(glbBytes.buffer, glbBytes.byteOffset, glbBytes.byteLength);
  const jsonLen = dv.getUint32(12, true);
  const gltf = JSON.parse(new TextDecoder().decode(glbBytes.subarray(20, 20 + jsonLen)));
  const binOffset = 20 + jsonLen + 8;
  const binChunk = glbBytes.subarray(binOffset);

  if (hasNearest && Array.isArray(gltf.samplers)) {
    for (const s of gltf.samplers) {
      s.magFilter = 9728;
      s.minFilter = 9728;
    }
  }
  if (alphaMaskCutoff !== null && Array.isArray(gltf.materials)) {
    for (const m of gltf.materials) {
      if (!m.alphaMode || m.alphaMode === "OPAQUE") {
        m.alphaMode = "MASK";
        m.alphaCutoff = alphaMaskCutoff;
      }
    }
  }

  let jsonBytes = new TextEncoder().encode(JSON.stringify(gltf));
  const pad = (4 - (jsonBytes.length % 4)) % 4;
  if (pad) {
    const padded = new Uint8Array(jsonBytes.length + pad);
    padded.set(jsonBytes);
    padded.fill(0x20, jsonBytes.length);
    jsonBytes = padded;
  }
  const total = 12 + 8 + jsonBytes.length + 8 + binChunk.length;
  const out = new Uint8Array(total);
  const odv = new DataView(out.buffer);
  odv.setUint32(0, 0x46546c67, true);
  odv.setUint32(4, 2, true);
  odv.setUint32(8, total, true);
  odv.setUint32(12, jsonBytes.length, true);
  odv.setUint32(16, 0x4e4f534a, true);
  out.set(jsonBytes, 20);
  odv.setUint32(20 + jsonBytes.length, binChunk.length, true);
  odv.setUint32(24 + jsonBytes.length, 0x004e4942, true);
  out.set(binChunk, 28 + jsonBytes.length);
  return out;
}

async function main() {
  const input = process.argv[2];
  if (!input || input === "-h" || input === "--help") {
    console.log("Usage: node sketchfab_dl.mjs <sketchfab-url-or-uid> [output-dir]");
    process.exit(input ? 0 : 1);
  }
  const uid = extractUid(input);
  if (!uid) throw new Error(`Could not extract 32-char Sketchfab UID from: ${input}`);

  const log = (msg) => console.log(msg);
  log(`[1/5] Fetching public viewer metadata for ${uid}…`);
  const { info, embedHtml } = await fetchViewerInfo(uid);
  const modelName = sanitizeName(info.name || uid);
  const author = (info.user && (info.user.displayName || info.user.username)) || "unknown";
  log(`      Model: "${info.name}" by ${author}`);

  const outRoot = path.resolve(process.argv[3] || path.join(process.cwd(), `${modelName}-${uid.slice(0, 8)}`));
  fs.mkdirSync(path.join(outRoot, "textures"), { recursive: true });

  log(`[2/5] Extracting viewer static key & loading WASM decryptor…`);
  const staticKey = await extractStaticKey(embedHtml);
  const wasmBytes = new Uint8Array(fs.readFileSync(path.join(__dirname, "lib", "wasm", "decrypt.wasm")));
  const diterB = getDiterB(info);

  log(`[3/5] Downloading & decrypting .binz geometry…`);
  const decrypted = {};
  for (const url of modelBinzUrls(info)) {
    const binzName = url.split("/").pop().split("?")[0];
    try {
      const enc = await fetchBytes(url);
      const plain = await decryptBinzBytes(wasmBytes, enc, diterB, staticKey);
      const outName = outNameFor(binzName);
      decrypted[outName] = plain;
      log(`      ✓ ${binzName} -> ${outName} (${plain.length} B)`);
    } catch (e) {
      if (binzName.includes("wireframe")) continue;
      throw e;
    }
  }
  Object.assign(decrypted, await fetchAnimations(info, (m) => log(`      ${m}`)));

  log(`[4/5] Downloading & descrambling textures…`);
  const textures = await fetchTextures(uid, (m) => log(`      ${m}`), { maxEdge: 0, concurrency: 3 });
  for (const t of textures) {
    decrypted[t.name] = t.data;
    fs.writeFileSync(path.join(outRoot, t.name), t.data);
  }

  log(`[5/5] Converting OSGJS scene to GLB…`);
  const vm = parseViewerMaterials(info);
  const orient = viewerOrientation(info);
  const res = await convertOsgjsToGlbFromFiles(decrypted, vm, textures, orient);
  const finalGlb = patchPixelArtAndAlphaMask(res.glb, info);

  const glbPath = path.join(outRoot, `${modelName}.glb`);
  fs.writeFileSync(glbPath, finalGlb);
  fs.writeFileSync(
    path.join(outRoot, "info.json"),
    JSON.stringify(
      {
        uid,
        name: info.name,
        author,
        source_url: input,
        glb: path.basename(glbPath),
        geometries: res.geometryCount,
        textures: textures.map((t) => ({ name: t.name, width: t.width, height: t.height, descrambled: !!t.fromDescramble })),
      },
      null,
      2
    )
  );
  log(`\nDone! Saved ${glbPath} (${finalGlb.length} bytes)`);
}

main().catch((err) => {
  console.error("ERROR:", err.message || err);
  process.exit(1);
});
