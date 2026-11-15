// Shared helpers for the verification and demo-recording tools.
// Nothing in tools/ is part of the deployed site.

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const LIVE_ORIGIN = "https://iraqies.github.io";
export const LIVE_BASE = "/dictionary/";
export const LIVE_URL = LIVE_ORIGIN + LIVE_BASE;

const CHROME = process.env.CHROME_PATH || "/usr/bin/google-chrome-stable";

// Headless Chrome reports "no hover, no fine pointer" by default, which is
// what a phone reports. These settings make it answer like a desktop with a
// mouse, so the hover-only parts of the site are the ones under test.
const MOUSE =
  "--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4";

const SITE_FILES = {
  "index.html": "text/html; charset=utf-8",
  "app.js": "text/javascript; charset=utf-8",
  "styles.css": "text/css; charset=utf-8",
  "terms.json": "application/json; charset=utf-8",
  "favicon.svg": "image/svg+xml",
  "og.png": "image/png",
};

export function launch({ mouse = true } = {}) {
  return puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ["--no-sandbox", "--hide-scrollbars", "--force-color-profile=srgb", ...(mouse ? [MOUSE] : [])],
  });
}

// Serve the working copy at the live address, inside this browser only. The
// page then runs with the real origin and path: a secure context (so the
// clipboard works) and copied links that read exactly as they will once
// deployed. The live site itself is never touched.
export async function mountLocal(page) {
  await page.setRequestInterception(true);
  page.on("request", async (request) => {
    const url = new URL(request.url());
    if (url.origin !== LIVE_ORIGIN || !url.pathname.startsWith(LIVE_BASE)) {
      request.continue();
      return;
    }
    const name = url.pathname.slice(LIVE_BASE.length) || "index.html";
    if (!(name in SITE_FILES)) {
      request.respond({ status: 404, contentType: "text/plain", body: "Not found" });
      return;
    }
    const body = await fs.readFile(path.join(ROOT, name));
    request.respond({ status: 200, contentType: SITE_FILES[name], body });
  });
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
