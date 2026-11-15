// Records the demo video of the round-2 interactions, one frame at a time.
//
// A real-time screen capture stutters on a busy machine, so the page runs on
// a virtual clock instead: its timers, animation-frame callbacks, CSS
// transitions and Web Animations are all stepped 1/60 s per frame, and a
// screenshot is taken after every step. The result is what a 60 fps display
// shows, however slow the recording machine is.
//
// The arrow, the click ring and the caption bar under the page are added by
// this script for the recording. They are not part of the site.
//
//   node record.mjs [output.mp4] [--keep-frames]

import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { launch, mountLocal, LIVE_ORIGIN, LIVE_URL, ROOT } from "./lib.mjs";

const FPS = 60;
const FRAME_MS = 1000 / FPS;
const WIDTH = 1280;
const HEIGHT = 720;
const BAR = 64;
const FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf";

const args = process.argv.slice(2);
const keepFrames = args.includes("--keep-frames");
const output = path.resolve(args.find((a) => !a.startsWith("--")) ?? path.join(ROOT, "delivery", "round2-demo.mp4"));
const frameDir = path.join(os.tmpdir(), "dictionary-demo-frames");

/* ---- injected into the page before any of its scripts run ---- */

function installClock() {
  const clock = { now: 0, nextId: 1, timers: new Map(), frames: new Map(), started: new WeakMap() };

  window.setTimeout = (fn, delay, ...rest) => {
    const id = clock.nextId++;
    clock.timers.set(id, { at: clock.now + (Number(delay) || 0), fn, rest });
    return id;
  };
  window.clearTimeout = (id) => clock.timers.delete(id);
  window.requestAnimationFrame = (fn) => {
    const id = clock.nextId++;
    clock.frames.set(id, fn);
    return id;
  };
  window.cancelAnimationFrame = (id) => clock.frames.delete(id);

  window.__tick = (dt) => {
    clock.now += dt;

    for (;;) {
      let next = null;
      for (const [id, timer] of clock.timers) {
        if (timer.at <= clock.now && (!next || timer.at < next.timer.at)) next = { id, timer };
      }
      if (!next) break;
      clock.timers.delete(next.id);
      next.timer.fn(...next.timer.rest);
    }

    const callbacks = [...clock.frames.values()];
    clock.frames.clear();
    for (const fn of callbacks) fn(clock.now);

    // The document timeline is frozen by the recorder, so an animation only
    // moves when its time is set here. One first seen on this frame starts now.
    for (const animation of document.getAnimations()) {
      let start = clock.started.get(animation);
      if (start === undefined) {
        start = clock.now;
        clock.started.set(animation, start);
      }
      const time = clock.now - start;
      const end = animation.effect ? animation.effect.getComputedTiming().endTime : 0;
      if (time >= end) animation.finish();
      else animation.currentTime = time;
    }
  };
}

function installPointer() {
  const build = () => {
    const pointer = document.createElement("div");
    pointer.id = "demo-pointer";
    pointer.setAttribute("aria-hidden", "true");
    pointer.innerHTML =
      '<i></i><svg width="24" height="24" viewBox="0 0 24 24"><path d="M3 2v17.5l4.6-4.2 3 6.9 2.9-1.3-3-6.7h6.2z" fill="#fff" stroke="#0a0a0a" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    const style = document.createElement("style");
    style.textContent = `
      #demo-pointer { position: fixed; left: 0; top: 0; z-index: 2147483647; pointer-events: none; transform: translate(-100px, -100px); }
      #demo-pointer svg { position: absolute; left: -3px; top: -2px; filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.45)); }
      #demo-pointer i { position: absolute; left: -18px; top: -18px; width: 36px; height: 36px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.5); opacity: 0; }
      #demo-pointer.click i { animation: demo-click 380ms ease-out; }
      @keyframes demo-click { from { opacity: 0.9; transform: scale(0.25); } to { opacity: 0; transform: scale(1); } }
    `;
    document.head.appendChild(style);
    document.documentElement.appendChild(pointer);
    window.addEventListener(
      "mousemove",
      (e) => {
        pointer.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
      },
      true
    );
    window.addEventListener(
      "mousedown",
      () => {
        pointer.classList.remove("click");
        void pointer.offsetWidth;
        pointer.classList.add("click");
      },
      true
    );
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
}

/* ---- recorder ---- */

const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

class Recorder {
  constructor(context) {
    this.context = context;
    this.page = null;
    this.client = null;
    this.frame = 0;
    this.mouse = { x: 90, y: 430 };
    this.captions = [];
  }

  // A fresh tab on the virtual clock, with the pointer where it was left.
  async newTab(url) {
    if (this.page) await this.page.close();
    const page = await this.context.newPage();
    page.on("pageerror", (e) => console.error(`pageerror: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") console.error(`console error: ${m.text()}`);
    });
    await mountLocal(page);
    await page.setViewport({ width: WIDTH, height: HEIGHT });
    await page.emulateMediaFeatures([
      { name: "prefers-color-scheme", value: "dark" },
      { name: "prefers-reduced-motion", value: "no-preference" },
    ]);
    await page.evaluateOnNewDocument(installClock);
    await page.evaluateOnNewDocument(installPointer);
    const client = await page.createCDPSession();
    await client.send("Animation.enable");
    await client.send("Animation.setPlaybackRate", { playbackRate: 0 });
    await page.bringToFront();
    this.page = page;
    this.client = client;

    await page.goto(url, { waitUntil: "networkidle0" });
    await page.waitForSelector("#grid .card");
    await page.evaluate(() => document.fonts.ready);
    await client.send("Animation.setPlaybackRate", { playbackRate: 0 });
    await page.mouse.move(this.mouse.x, this.mouse.y);
  }

  async shoot() {
    await this.page.evaluate((dt) => window.__tick(dt), FRAME_MS);
    const { data } = await this.client.send("Page.captureScreenshot", { format: "png", optimizeForSpeed: true });
    await fs.writeFile(path.join(frameDir, `${String(this.frame).padStart(6, "0")}.png`), Buffer.from(data, "base64"));
    this.frame += 1;
  }

  async wait(ms) {
    for (let i = Math.round(ms / FRAME_MS); i > 0; i--) await this.shoot();
  }

  caption(text) {
    const last = this.captions.at(-1);
    if (last) last.to = this.frame - 1;
    this.captions.push({ text, from: this.frame, to: Infinity });
    console.log(`frame ${this.frame}: ${text}`);
  }

  note(label) {
    console.log(`frame ${this.frame}: [${label}]`);
  }

  async moveTo(x, y, ms) {
    const from = { ...this.mouse };
    const steps = Math.max(1, Math.round(ms / FRAME_MS));
    // A slight arc reads as a hand, a straight line as a robot.
    const bow = Math.min(40, Math.hypot(x - from.x, y - from.y) * 0.08);
    for (let i = 1; i <= steps; i++) {
      const p = easeInOut(i / steps);
      const lift = Math.sin(Math.PI * p) * bow;
      this.mouse = { x: from.x + (x - from.x) * p, y: from.y + (y - from.y) * p - lift };
      await this.page.mouse.move(this.mouse.x, this.mouse.y);
      await this.shoot();
    }
  }

  async point(selector) {
    return this.page.evaluate((sel) => {
      const b = document.querySelector(sel).getBoundingClientRect();
      return { x: b.left + b.width / 2, y: b.top + b.height / 2, left: b.left, top: b.top, width: b.width, height: b.height };
    }, selector);
  }

  async moveToElement(selector, ms, at = [0.5, 0.5]) {
    const b = await this.point(selector);
    await this.moveTo(b.left + b.width * at[0], b.top + b.height * at[1], ms);
  }

  async click() {
    await this.page.mouse.down();
    await this.wait(80);
    await this.page.mouse.up();
  }

  async scrollTo(top, ms) {
    const from = await this.page.evaluate(() => scrollY);
    const steps = Math.max(1, Math.round(ms / FRAME_MS));
    for (let i = 1; i <= steps; i++) {
      await this.page.evaluate((y) => window.scrollTo(0, y), from + (top - from) * easeInOut(i / steps));
      await this.page.mouse.move(this.mouse.x, this.mouse.y);
      await this.shoot();
    }
  }
}

/* ---- the demo ---- */

await fs.rm(frameDir, { recursive: true, force: true });
await fs.mkdir(frameDir, { recursive: true });

const browser = await launch({ mouse: true });
const context = await browser.createBrowserContext();
await context.overridePermissions(LIVE_ORIGIN, ["clipboard-read", "clipboard-write"]);

const rec = new Recorder(context);
const chip = (category) => `.chip[data-category="${category}"]`;
const started = Date.now();

// 1. category glide
await rec.newTab(LIVE_URL);
rec.caption("1   Switch category: the cards glide to their new places");
await rec.wait(1000);
await rec.moveToElement(chip("naming"), 750);
await rec.click();
await rec.wait(1500);
await rec.moveToElement(chip("all"), 550);
await rec.click();
await rec.wait(1500);
await rec.moveToElement(chip("security"), 600);
await rec.click();
await rec.wait(1400);
await rec.moveToElement(chip("naming"), 550);
await rec.click();
await rec.wait(1300);

// 2. copy a term's link
rec.caption("2   Click a term to copy a link to it");
const og = await rec.point("#term-og");
await rec.scrollTo(Math.max(0, og.top + og.height / 2 - HEIGHT / 2), 650);
await rec.moveToElement("#term-og", 650, [0.6, 0.62]);
await rec.wait(250);
await rec.moveToElement("#term-og .term-link", 500, [0.35, 0.55]);
await rec.wait(450);
await rec.click();
rec.note("copied");
await rec.wait(2300);
const copied = await rec.page.evaluate(() => navigator.clipboard.readText());
if (copied !== `${LIVE_URL}#og`) throw new Error(`Clipboard holds "${copied}", expected the OG link`);

// 3. open that link in a new tab
rec.caption("3   Open that link in a new tab: the page lands on the term");
rec.mouse = { x: 1190, y: 330 };
await rec.newTab(copied);
await rec.wait(2600);

// 4. light theme
rec.caption("Same in light mode");
await rec.moveToElement("#theme-toggle", 700);
await rec.click();
await rec.wait(1200);
await rec.scrollTo(0, 800);
await rec.moveToElement(chip("community"), 650);
await rec.click();
await rec.wait(1300);
await rec.moveToElement("#term-dnw", 600, [0.7, 0.6]);
await rec.moveToElement("#term-dnw .term-link", 500, [0.35, 0.55]);
await rec.wait(300);
await rec.click();
await rec.wait(1900);

rec.captions.at(-1).to = rec.frame - 1;
await browser.close();
console.log(`${rec.frame} frames in ${((Date.now() - started) / 1000).toFixed(0)}s`);

/* ---- encode: page on top, caption bar underneath ---- */

const filters = [
  `pad=${WIDTH}:${HEIGHT + BAR}:0:0:color=0x0a0a0a`,
  `drawbox=x=0:y=${HEIGHT}:w=${WIDTH}:h=1:color=0x2a2a2a:t=fill`,
];
for (const [i, caption] of rec.captions.entries()) {
  const file = path.join(frameDir, `caption-${i}.txt`);
  await fs.writeFile(file, caption.text);
  filters.push(
    `drawtext=fontfile=${FONT}:textfile=${file}:x=28:y=${HEIGHT + 21}:fontsize=22:fontcolor=0xf2f2f2:enable='between(n,${caption.from},${caption.to})'`
  );
}

await fs.mkdir(path.dirname(output), { recursive: true });
execFileSync(
  "ffmpeg",
  [
    "-y", "-loglevel", "error",
    "-framerate", String(FPS),
    "-i", path.join(frameDir, "%06d.png"),
    "-vf", filters.join(","),
    "-c:v", "libx264", "-preset", "slow", "-crf", "21",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    output,
  ],
  { stdio: "inherit" }
);
if (!keepFrames) await fs.rm(frameDir, { recursive: true, force: true });
console.log(`Wrote ${output}`);
