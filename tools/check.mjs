// Click-through checks for the dictionary site (anti-slop R-35: run it,
// click it, read the console). Every line printed is one observed behaviour.
//
//   node check.mjs          the working copy, served at the live address
//                           inside the test browser only
//   node check.mjs --live   the deployed site itself

import fs from "node:fs/promises";
import path from "node:path";
import { launch, mountLocal, sleep, LIVE_ORIGIN, LIVE_URL, ROOT } from "./lib.mjs";

const live = process.argv.includes("--live");
const results = [];

function check(name, ok, detail = "") {
  results.push({ name, ok: Boolean(ok) });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${ok || !detail ? "" : `  [${detail}]`}`);
}

async function openPage(
  context,
  { suffix = "", viewport, reduced = false, scheme = "dark", phone = false, holdFonts = null, waitUntil = "networkidle0" } = {}
) {
  const page = await context.newPage();
  page.problems = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") page.problems.push(`${m.type()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => page.problems.push(`pageerror: ${e.message}`));
  page.on("requestfailed", (r) => page.problems.push(`failed: ${r.url()}`));
  page.on("response", (r) => {
    if (r.status() >= 400) page.problems.push(`${r.status()}: ${r.url()}`);
  });
  if (!live) await mountLocal(page, { holdFonts });
  if (phone) {
    await page.emulate({
      viewport: viewport ?? { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
      userAgent:
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    });
  } else {
    await page.setViewport(viewport ?? { width: 1280, height: 800 });
  }
  await page.emulateMediaFeatures([
    { name: "prefers-color-scheme", value: scheme },
    { name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" },
  ]);
  await page.goto(LIVE_URL + suffix, { waitUntil });
  await page.waitForSelector("#grid .card");
  return page;
}

// Nothing is moving any more: no running animation or transition anywhere,
// and no layer of leaving cards left behind.
const settle = (page) =>
  page.waitForFunction(() => document.getAnimations().length === 0 && !document.querySelector(".leaving"), {
    timeout: 15000,
  });

const quiet = (page, label) => check(`${label}: console is clean`, page.problems.length === 0, page.problems.join(" | "));

const slugsOf = (page) => page.evaluate(() => [...document.querySelectorAll("#grid .card")].map((c) => c.dataset.slug));

const clipboard = (page) => page.evaluate(() => navigator.clipboard.readText());

const toastText = async (page) => {
  await page.waitForSelector("#toast.show", { timeout: 5000 });
  return page.evaluate(() => [...document.getElementById("toast").children].map((n) => n.textContent));
};

/* ---- source rules (working copy only) ---- */

async function sourceRules() {
  const files = ["index.html", "app.js", "styles.css", "terms.json"];
  const text = Object.fromEntries(
    await Promise.all(files.map(async (f) => [f, await fs.readFile(path.join(ROOT, f), "utf8")]))
  );
  const dashes = files.filter((f) => text[f].includes("\u2014"));
  check("source: no em dash in any shipped file (R-02)", dashes.length === 0, dashes.join(", "));
  check("source: no outline:none / outline:0 (R-32)", !/outline\s*:\s*(none|0)\b/.test(text["styles.css"]));
  const versions = [...text["index.html"].matchAll(/\?v=(\d+)/g)].map((m) => m[1]);
  check("source: styles.css and app.js carry the same cache version", versions.length === 2 && versions[0] === versions[1], versions.join(","));
}

/* ---- load ---- */

async function loadChecks(context) {
  const page = await openPage(context);
  const info = await page.evaluate(() => {
    const cards = [...document.querySelectorAll("#grid .card")];
    return {
      cards: cards.length,
      count: document.getElementById("count").textContent,
      loadingHidden: document.getElementById("loading").hidden,
      linked: cards.every((c) => {
        const link = c.querySelector("h2.card-term > a.term-link");
        return link && c.id === `term-${c.dataset.slug}` && link.getAttribute("href") === `#${c.dataset.slug}` && link.title.startsWith("Copy link to ");
      }),
      unique: new Set(cards.map((c) => c.id)).size === cards.length,
      sorted: cards.map((c) => c.querySelector(".term-link").textContent).join("|"),
      h1: document.querySelectorAll("h1").length,
      toastRole: document.getElementById("toast")?.getAttribute("role"),
      toastEmpty: document.getElementById("toast")?.childElementCount === 0,
      hashHidden: getComputedStyle(cards[0].querySelector(".term-link"), "::after").opacity,
    };
  });
  check("load: 50 cards and the count reads '50 of 50 terms'", info.cards === 50 && info.count === "50 of 50 terms", `${info.cards} / ${info.count}`);
  check("load: loading state is hidden once terms are in", info.loadingHidden);
  check("load: every term is a link to its own #slug with a 'Copy link to' title", info.linked);
  check("load: card ids are unique", info.unique);
  const names = info.sorted.split("|");
  const expected = [...names].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  check("load: cards are in alphabetical order", names.join("|") === expected.join("|"));
  check("load: still exactly one h1; toast is an empty role=status region", info.h1 === 1 && info.toastRole === "status" && info.toastEmpty);
  check("load (mouse): the '#' hint is hidden until a card is hovered", info.hashHidden === "0", `opacity ${info.hashHidden}`);
  quiet(page, "load");
  await page.close();
}

/* ---- category glide ---- */

async function glideChecks(context) {
  const page = await openPage(context);
  await settle(page);

  const toNames = await page.evaluate(() => {
    const box = (el) => {
      const b = el.getBoundingClientRect();
      return { left: b.left, top: b.top, bottom: b.bottom };
    };
    const before = new Map([...document.querySelectorAll("#grid .card")].map((c) => [c.dataset.slug, box(c)]));
    document.querySelector('.chip[data-category="naming"]').click();
    const cards = [...document.querySelectorAll("#grid .card")];
    return {
      vh: innerHeight,
      count: document.getElementById("count").textContent,
      leaving: document.querySelectorAll(".leaving .card").length,
      leavingInert: document.querySelector(".leaving")?.inert === true,
      cards: cards.map((c) => {
        const was = before.get(c.dataset.slug);
        const now = box(c);
        return {
          slug: c.dataset.slug,
          wasOnScreen: was.bottom > 0 && was.top < innerHeight,
          moving: c.getAnimations().length > 0,
          startError: Math.hypot(now.left - was.left, now.top - was.top),
          startTop: now.top,
        };
      }),
    };
  });
  check("glide All -> Names: count updates at once ('9 of 50 terms')", toNames.count === "9 of 50 terms", toNames.count);
  check("glide All -> Names: removed cards on screen fade out in an inert layer", toNames.leaving > 0 && toNames.leavingInert, `${toNames.leaving} leaving`);

  await settle(page);
  const rested = await page.evaluate(() => ({
    slugs: [...document.querySelectorAll("#grid .card")].map((c) => c.dataset.slug).join(","),
    flat: [...document.querySelectorAll("#grid .card")].every((c) => getComputedStyle(c).transform === "none" && getComputedStyle(c).opacity === "1"),
    leaving: document.querySelectorAll(".leaving").length,
    ghostIds: document.querySelectorAll('[id^="term-"]').length,
    onScreen: [...document.querySelectorAll("#grid .card")].filter((c) => c.getBoundingClientRect().top < innerHeight).map((c) => c.dataset.slug),
  }));
  const seen = toNames.cards.filter((c) => c.wasOnScreen);
  const arriving = toNames.cards.filter((c) => !c.wasOnScreen && rested.onScreen.includes(c.slug));
  const unseen = toNames.cards.filter((c) => !c.wasOnScreen && !rested.onScreen.includes(c.slug));
  check(
    "glide All -> Names: cards that were on screen start exactly where they stood, and move",
    seen.length > 0 && seen.every((c) => c.startError < 1 && c.moving),
    seen.map((c) => `${c.slug}:${c.startError.toFixed(1)}`).join(" ")
  );
  check(
    "glide All -> Names: cards from far down the page come in from just below the fold, not from thousands of px away",
    arriving.length > 0 && arriving.every((c) => c.moving && c.startTop >= toNames.vh - 1 && c.startTop < toNames.vh * 2 + 400),
    arriving.map((c) => `${c.slug}:${Math.round(c.startTop)}`).join(" ")
  );
  check("glide All -> Names: cards nobody can see (off screen before and after) are not animated", unseen.every((c) => !c.moving), unseen.map((c) => c.slug).join(" "));
  check("glide All -> Names: lands on the 9 name cards in order", rested.slugs === "3c,3l,4c,4l,drop,handle,og,semi-og,snipe", rested.slugs);
  check("glide All -> Names: after landing nothing is transformed, faded or left behind", rested.flat && rested.leaving === 0 && rested.ghostIds === 9);

  const toAll = await page.evaluate(() => {
    const box = (el) => {
      const b = el.getBoundingClientRect();
      return { left: b.left, top: b.top, bottom: b.bottom };
    };
    const before = new Map([...document.querySelectorAll("#grid .card")].map((c) => [c.dataset.slug, box(c)]));
    document.querySelector('.chip[data-category="all"]').click();
    const cards = [...document.querySelectorAll("#grid .card")];
    const stay = cards.filter((c) => before.has(c.dataset.slug) && before.get(c.dataset.slug).top < innerHeight);
    const fresh = cards.filter((c) => !before.has(c.dataset.slug) && c.getBoundingClientRect().top < innerHeight);
    return {
      total: cards.length,
      stay: stay.length,
      stayError: Math.max(...stay.map((c) => Math.hypot(box(c).left - before.get(c.dataset.slug).left, box(c).top - before.get(c.dataset.slug).top))),
      freshOpacity: Math.max(...fresh.map((c) => Number(getComputedStyle(c).opacity))),
      fresh: fresh.length,
    };
  });
  check("glide Names -> All: the name cards on screen leave from where they stood", toAll.total === 50 && toAll.stay >= 6 && toAll.stayError < 1, `${toAll.stay} cards, error ${toAll.stayError.toFixed(2)}`);
  check("glide Names -> All: cards new to the screen start transparent and fade up", toAll.fresh > 0 && toAll.freshOpacity < 0.05, `${toAll.fresh} fresh, opacity ${toAll.freshOpacity}`);
  await settle(page);

  await page.evaluate(async () => {
    for (const category of ["security", "naming", "all", "selling", "account"]) {
      document.querySelector(`.chip[data-category="${category}"]`).click();
      await new Promise((resolve) => setTimeout(resolve, 45));
    }
  });
  await settle(page);
  const rapid = await page.evaluate(() => {
    const active = document.querySelector(".chip.active");
    const a = active.getBoundingClientRect();
    const i = document.querySelector(".chip-indicator").getBoundingClientRect();
    return {
      slugs: [...document.querySelectorAll("#grid .card")].map((c) => c.dataset.slug).join(","),
      count: document.getElementById("count").textContent,
      active: active.dataset.category,
      pressed: document.querySelectorAll('.chip[aria-pressed="true"]').length,
      flat: [...document.querySelectorAll("#grid .card")].every((c) => getComputedStyle(c).transform === "none" && getComputedStyle(c).opacity === "1"),
      indicatorOff: Math.max(Math.abs(a.left - i.left), Math.abs(a.top - i.top), Math.abs(a.width - i.width)),
    };
  });
  check(
    "glide: five category changes 45ms apart end in a clean final state",
    rapid.slugs === "alt,cape,clean,cracked,msa,msi,nca,unbanned" && rapid.count === "8 of 50 terms" && rapid.flat,
    `${rapid.slugs} / ${rapid.count}`
  );
  check("glide: the sliding outline rests on the active chip", rapid.active === "account" && rapid.pressed === 1 && rapid.indicatorOff < 1.5, `off by ${rapid.indicatorOff.toFixed(2)}px`);

  await page.focus('.chip[data-category="security"]');
  await page.keyboard.press("Enter");
  await settle(page);
  const keyboard = await page.evaluate(() => ({
    focus: document.activeElement?.dataset?.category,
    count: document.getElementById("count").textContent,
  }));
  check("glide: a keyboard category change works and keeps focus on the chip", keyboard.focus === "security" && keyboard.count === "11 of 50 terms", JSON.stringify(keyboard));
  quiet(page, "glide");
  await page.close();
}

/* ---- share links ---- */

async function shareChecks(context) {
  const page = await openPage(context);
  await page.bringToFront();
  await settle(page);

  await page.hover("#term-3l");
  await sleep(250);
  const hint = await page.evaluate(() => getComputedStyle(document.querySelector("#term-3l .term-link"), "::after").opacity);
  check("share: hovering a card reveals the '#' next to its term", hint === "1", `opacity ${hint}`);

  const scrollBefore = await page.evaluate(() => scrollY);
  await page.click("#term-3l .term-link");
  const toast = await toastText(page);
  const copied = await clipboard(page);
  await sleep(400);
  const after = await page.evaluate(() => ({
    hash: location.hash,
    targets: [...document.querySelectorAll(".card.is-target")].map((c) => c.id).join(","),
    scrollY,
    border: getComputedStyle(document.querySelector("#term-3l .card-face")).borderTopColor,
  }));
  check("share: clicking a term copies its link to the clipboard", copied === `${LIVE_URL}#3l`, copied);
  check("share: the toast says 'Link copied' and shows the link", toast[0] === "Link copied" && toast[1] === "iraqies.github.io/dictionary/#3l", toast.join(" / "));
  check("share: the address bar follows (#3l) and only that card is marked", after.hash === "#3l" && after.targets === "term-3l", JSON.stringify(after));
  check("share: the marked card carries the accent border", after.border === "rgb(52, 211, 153)", after.border);
  check("share: copying does not scroll the page", after.scrollY === scrollBefore, `${scrollBefore} -> ${after.scrollY}`);

  await page.waitForFunction(() => !document.querySelector("#toast.show") && document.getElementById("toast").childElementCount === 0, { timeout: 8000 });
  check("share: the toast hides by itself and is emptied", true);

  await page.focus("#term-4c .term-link");
  await page.keyboard.press("Enter");
  await toastText(page);
  const viaKeyboard = await page.evaluate(async () => ({
    clip: await navigator.clipboard.readText(),
    targets: [...document.querySelectorAll(".card.is-target")].map((c) => c.id).join(","),
    focusOnLink: document.activeElement === document.querySelector("#term-4c .term-link"),
  }));
  check(
    "share: Enter on a focused term copies its link, moves the mark, keeps focus",
    viaKeyboard.clip === `${LIVE_URL}#4c` && viaKeyboard.targets === "term-4c" && viaKeyboard.focusOnLink,
    JSON.stringify(viaKeyboard)
  );

  const pagesBefore = (await context.pages()).length;
  await page.keyboard.down("Control");
  await page.click("#term-alt .term-link");
  await page.keyboard.up("Control");
  await sleep(600);
  const modified = await page.evaluate(async () => ({ hash: location.hash, clip: await navigator.clipboard.readText() }));
  const opened = (await context.pages()).filter((p) => p !== page);
  check(
    "share: Ctrl+click is left to the browser (new tab), nothing is copied",
    modified.hash === "#4c" && modified.clip === `${LIVE_URL}#4c` && opened.length === pagesBefore,
    `${JSON.stringify(modified)} tabs ${opened.length}`
  );
  for (const extra of opened) await extra.close();
  await page.bringToFront();

  await page.evaluate(() => {
    navigator.clipboard.writeText = () => Promise.reject(new Error("blocked"));
  });
  await page.click("#term-b-o .term-link");
  const fallbackToast = await toastText(page);
  const fallback = await page.evaluate(async () => ({
    clip: await navigator.clipboard.readText(),
    focusOnLink: document.activeElement === document.querySelector("#term-b-o .term-link"),
    strays: document.querySelectorAll("body > textarea").length,
  }));
  check(
    "share: without the async clipboard the fallback still copies and hands focus back",
    fallbackToast[0] === "Link copied" && fallback.clip === `${LIVE_URL}#b-o` && fallback.focusOnLink && fallback.strays === 0,
    `${fallbackToast.join(" / ")} ${JSON.stringify(fallback)}`
  );

  await page.evaluate(() => {
    document.execCommand = () => false;
  });
  await page.click("#term-alt .term-link");
  await page.waitForFunction(() => document.querySelector("#toast.show strong")?.textContent === "Could not copy", { timeout: 5000 });
  const failed = await page.evaluate(() => ({
    text: [...document.getElementById("toast").children].map((n) => n.textContent).join(" / "),
    hash: location.hash,
  }));
  check(
    "share: when copying is impossible the toast says so and the link is in the address bar",
    failed.text === "Could not copy / The link is in the address bar." && failed.hash === "#alt",
    JSON.stringify(failed)
  );
  quiet(page, "share");
  await page.close();
}

/* ---- opening a link ---- */

async function linkChecks(context) {
  const visible = (page, slug) =>
    page.evaluate((id) => {
      const card = document.getElementById(id);
      const b = card.getBoundingClientRect();
      return {
        marked: card.classList.contains("is-target"),
        marks: document.querySelectorAll(".card.is-target").length,
        inside: b.top >= 0 && b.bottom <= innerHeight,
        offCentre: Math.abs((b.top + b.bottom) / 2 - innerHeight / 2),
        focused: document.activeElement === card,
        ring: getComputedStyle(card).outlineStyle !== "none",
        radius: getComputedStyle(card).borderTopLeftRadius,
        category: document.querySelector(".chip.active").dataset.category,
        cards: document.querySelectorAll("#grid .card").length,
      };
    }, `term-${slug}`);

  let page = await openPage(context, { suffix: "#semi-og" });
  let r = await visible(page, "semi-og");
  check("link #semi-og: opens scrolled to that card, centred on screen", r.marked && r.marks === 1 && r.inside && r.offCentre < 40, JSON.stringify(r));
  check("link #semi-og: the card takes focus and shows a ring that follows its corners", r.focused && r.ring && r.radius !== "3px", JSON.stringify(r));
  check("link #semi-og: all 50 terms are still on the page", r.cards === 50 && r.category === "all");
  quiet(page, "link #semi-og");
  await page.close();

  page = await openPage(context, { suffix: "#vouch" });
  r = await visible(page, "vouch");
  check("link #vouch (last card): fully on screen even though it cannot be centred", r.marked && r.inside, JSON.stringify(r));
  await page.close();

  page = await openPage(context, { suffix: "#2fa" });
  r = await visible(page, "2fa");
  check("link #2fa (first card): fully on screen", r.marked && r.inside, JSON.stringify(r));
  await page.close();

  page = await openPage(context, { suffix: "#NFA" });
  r = await visible(page, "nfa");
  check("link #NFA: capital letters in the link still resolve", r.marked && r.inside, JSON.stringify(r));
  await page.close();

  page = await openPage(context, { suffix: "#semi%2Dog" });
  r = await visible(page, "semi-og");
  check("link #semi%2Dog: a percent-encoded link still resolves", r.marked && r.inside, JSON.stringify(r));
  await page.close();

  for (const bad of ["#nope", "#%E0%A4%A", "#"]) {
    page = await openPage(context, { suffix: bad });
    const state = await page.evaluate(() => ({
      marks: document.querySelectorAll(".card.is-target").length,
      scrollY,
      cards: document.querySelectorAll("#grid .card").length,
    }));
    check(`link ${bad}: an unknown link opens the normal page, no error`, state.marks === 0 && state.scrollY === 0 && state.cards === 50 && page.problems.length === 0, `${JSON.stringify(state)} ${page.problems.join(" | ")}`);
    await page.close();
  }

  page = await openPage(context);
  await settle(page);
  await page.click('.chip[data-category="naming"]');
  await page.type("#search", "og");
  await settle(page);
  const narrowed = await slugsOf(page);
  await page.evaluate(() => {
    location.hash = "#mm";
  });
  await page.waitForFunction(
    () => {
      const card = document.querySelector("#term-mm.is-target");
      if (!card) return false;
      const b = card.getBoundingClientRect();
      return Math.abs((b.top + b.bottom) / 2 - innerHeight / 2) < 40;
    },
    { timeout: 15000 }
  );
  r = await visible(page, "mm");
  const cleared = await page.evaluate(() => document.getElementById("search").value === "");
  check(
    "link change on an open page: filter and search are reset so the linked term is reachable",
    narrowed.length < 9 && !narrowed.includes("mm") && r.cards === 50 && r.category === "all" && cleared && r.marked && r.focused,
    `${narrowed.join(",")} ${JSON.stringify(r)}`
  );
  await page.evaluate(() => {
    location.hash = "";
  });
  await page.waitForFunction(() => document.querySelectorAll(".card.is-target").length === 0, { timeout: 5000 });
  check("link removed from the address: the mark is cleared", true);
  quiet(page, "link change");
  await page.close();
}

/* ---- a web font that arrives after the page has rendered ---- */

// A first-time visitor has no cached font. When it lands, the filter row
// above the grid takes one line less and everything below moves up by it.
// These checks hold the font back, let the page render, then let it through.
// Working copy only: the hold needs the staged requests.
async function lateFontChecks(browser) {
  const open = async (slug) => {
    let release;
    const holdFonts = new Promise((resolve) => (release = resolve));
    const context = await browser.createBrowserContext();
    const page = await openPage(context, { suffix: `#${slug}`, holdFonts, waitUntil: "domcontentloaded" });
    const read = () =>
      page.evaluate((id) => {
        const b = document.getElementById(id).getBoundingClientRect();
        return {
          off: Math.round(Math.abs((b.top + b.bottom) / 2 - innerHeight / 2)),
          y: Math.round(scrollY),
          height: document.documentElement.scrollHeight,
        };
      }, `term-${slug}`);
    const fontIn = async () => {
      release();
      await page.evaluate(() => document.fonts.ready.then(() => new Promise((r) => requestAnimationFrame(r))));
      return read();
    };
    return { context, page, read, fontIn };
  };
  const says = (before, after) => `off centre ${before.off}px, then ${after.off}px; page ${before.height}px tall, then ${after.height}px`;

  // Near the top the filter row itself is on screen, so the browser has no
  // anchor below the reflow and would leave the card a line off centre.
  let t = await open("2fa");
  let before = await t.read();
  let after = await t.fontIn();
  check(
    "late font, link to a card near the top: centred before the font and still centred after it",
    before.off < 40 && after.off < 40 && after.height < before.height,
    says(before, after)
  );
  await t.context.close();

  // Font lands while the first-paint fade is still running on the cards.
  t = await open("semi-og");
  before = await t.read();
  after = await t.fontIn();
  check(
    "late font, link to a card far down, font lands during the first-paint fade: still centred",
    before.off < 40 && after.off < 40 && after.height < before.height,
    says(before, after)
  );
  await t.context.close();

  // Font lands after everything has come to rest: the browser keeps the card
  // in place by itself, and the second jump must not add a second correction.
  t = await open("semi-og");
  await settle(t.page);
  before = await t.read();
  after = await t.fontIn();
  check(
    "late font, link to a card far down, font lands on a page at rest: centred, no double correction",
    before.off < 40 && after.off < 40 && after.height < before.height,
    says(before, after)
  );
  await t.context.close();

  t = await open("semi-og");
  await t.page.mouse.move(640, 400);
  await t.page.mouse.wheel({ deltaY: -700 });
  await sleep(500);
  before = await t.read();
  after = await t.fontIn();
  await sleep(200);
  const rested = await t.read();
  check(
    "late font, reader has already scrolled away: the page does not pull them back to the card",
    before.off > 300 && Math.abs(rested.y - before.y) < 80 && rested.off > 300,
    `scrolled to ${before.y}, font in at ${after.y}, rests at ${rested.y}`
  );
  await t.context.close();
}

/* ---- reduced motion ---- */

async function reducedChecks(context) {
  const page = await openPage(context, { reduced: true, suffix: "#og" });
  const arrived = await page.evaluate(() => {
    const b = document.getElementById("term-og").getBoundingClientRect();
    return b.top >= 0 && b.bottom <= innerHeight;
  });
  check("reduced motion: a shared link still lands on its term", arrived);
  const still = await page.evaluate(() => {
    document.querySelector('.chip[data-category="naming"]').click();
    return {
      moving: document.getAnimations().filter((a) => a.effect && a.effect.target && a.effect.target.closest("#grid")).length,
      leaving: document.querySelectorAll(".leaving").length,
      cards: document.querySelectorAll("#grid .card").length,
    };
  });
  check("reduced motion: a category change swaps the cards with no glide and no fade", still.moving === 0 && still.leaving === 0 && still.cards === 9, JSON.stringify(still));
  await page.mouse.move(640, 420);
  await page.mouse.move(660, 440);
  await sleep(150);
  const lit = await page.evaluate(() => document.getElementById("grid").classList.contains("lit"));
  check("reduced motion: the pointer light stays off", !lit);
  quiet(page, "reduced motion");
  await page.close();
}

/* ---- card tilt ---- */

async function tiltChecks(context) {
  let page = await openPage(context);
  await settle(page);

  const box = await page.evaluate(() => {
    const b = document.getElementById("term-3c").getBoundingClientRect();
    return { left: b.left, top: b.top, width: b.width, height: b.height };
  });
  const at = (fx, fy) => [box.left + box.width * fx, box.top + box.height * fy];
  const read = (p = page) =>
    p.evaluate(() => {
      const card = document.getElementById("term-3c");
      const face = card.querySelector(".card-face");
      const m = new DOMMatrix(getComputedStyle(face).transform);
      const w = face.offsetWidth / 2;
      const h = face.offsetHeight / 2;
      // After the transform, w above 1 means the corner has moved away from
      // the viewer, below 1 that it has come closer.
      const depth = (x, y) => m.transformPoint(new DOMPoint(x, y, 0, 1)).w;
      const b = card.getBoundingClientRect();
      return {
        lean: card.classList.contains("lean"),
        hovered: card.matches(":hover"),
        degrees: parseFloat(card.style.getPropertyValue("--tilt")) || 0,
        flat: m.is2D,
        topLeft: depth(-w, -h),
        bottomRight: depth(w, h),
        left: depth(-w, 0),
        right: depth(w, 0),
        box: { left: b.left, top: b.top, width: b.width, height: b.height },
        leaning: document.querySelectorAll("#grid .card.lean").length,
      };
    });
  const expected = (fx, fy) => {
    const reach = Math.max(box.width, box.height) / 2;
    return Math.min(1, Math.hypot((fx - 0.5) * box.width, (fy - 0.5) * box.height) / reach) * 10;
  };

  await page.mouse.move(...at(0.5, 0.5));
  await page.mouse.move(...at(0.25, 0.25), { steps: 4 });
  await sleep(450);
  let r = await read();
  check(
    "tilt: the card under the pointer leans, steeper the further the pointer is from its centre",
    r.lean && !r.flat && Math.abs(r.degrees - expected(0.25, 0.25)) < 0.3,
    `${r.degrees} degrees, expected ${expected(0.25, 0.25).toFixed(2)}`
  );
  check(
    "tilt: the card is pressed down on the pointer's side and rises on the far side",
    r.topLeft > 1.01 && r.bottomRight < 0.99,
    `corner under the pointer ${r.topLeft.toFixed(3)}, far corner ${r.bottomRight.toFixed(3)}`
  );
  check(
    "tilt: only the face moves; the card's own box stays exactly where it was",
    Math.abs(r.box.left - box.left) < 0.5 && Math.abs(r.box.top - box.top) < 0.5 && Math.abs(r.box.width - box.width) < 0.5 && Math.abs(r.box.height - box.height) < 0.5,
    JSON.stringify(r.box)
  );

  // The left edge is where the face moves furthest away from the pointer.
  const edge = at(0, 0.5);
  await page.mouse.move(edge[0] + 2, edge[1], { steps: 4 });
  await sleep(450);
  const held = [];
  for (let i = 0; i < 6; i++) {
    await page.mouse.move(edge[0] + 2, edge[1] + (i % 2));
    await sleep(60);
    r = await read();
    held.push(r.hovered && r.lean && r.left > 1.03);
  }
  check(
    "tilt: at the very edge the card leans its most (10 degrees at the outside) and the hover holds, no flicker",
    held.every(Boolean) && r.degrees <= 10.001 && r.degrees > 9.5,
    `${held.join(",")} at ${r.degrees} degrees`
  );

  const next = await page.evaluate(() => {
    const b = document.getElementById("term-3l").getBoundingClientRect();
    return { x: b.left + b.width * 0.7, y: b.top + b.height * 0.4 };
  });
  await page.mouse.move(next.x, next.y, { steps: 6 });
  await sleep(450);
  r = await read();
  const moved = await page.evaluate(() => ({
    lean: document.getElementById("term-3l").classList.contains("lean"),
    old: document.getElementById("term-3c").getAttribute("style") || "",
  }));
  check(
    "tilt: moving on to the next card hands the lean over and leaves nothing behind on the old one",
    !r.lean && r.leaning === 1 && moved.lean && !moved.old.includes("--tilt"),
    JSON.stringify({ ...moved, leaning: r.leaning })
  );

  await page.mouse.move(640, 60, { steps: 4 });
  await settle(page);
  r = await read();
  check("tilt: leaving the grid lays every card flat again", r.leaning === 0 && r.flat, JSON.stringify({ leaning: r.leaning, flat: r.flat }));
  quiet(page, "tilt");
  await page.close();

  page = await openPage(context, { reduced: true });
  await page.mouse.move(...at(0.5, 0.5));
  await page.mouse.move(...at(0.25, 0.25), { steps: 4 });
  await sleep(200);
  r = await read(page);
  check("tilt: off under reduced motion", r.leaning === 0 && r.flat, JSON.stringify({ leaning: r.leaning, flat: r.flat }));
  await page.close();
}

/* ---- earlier behaviour that must still hold ---- */

async function regressionChecks(context) {
  const page = await openPage(context);
  await settle(page);

  await page.keyboard.press("/");
  const slash = await page.evaluate(() => document.activeElement.id);
  check("search: '/' jumps to the search field", slash === "search");

  await page.keyboard.type("og");
  const found = await page.evaluate(() => ({
    count: document.getElementById("count").textContent,
    marks: document.querySelectorAll("#grid mark").length,
    moving: document.getAnimations().filter((a) => a.effect && a.effect.target && a.effect.target.closest("#grid")).length,
  }));
  check("search: typing filters at once, highlights matches, and does not animate", /^\d+ of 50 terms$/.test(found.count) && found.count !== "50 of 50 terms" && found.marks > 0 && found.moving === 0, JSON.stringify(found));

  await page.keyboard.type("zzzz");
  const none = await page.evaluate(() => ({ cards: document.querySelectorAll("#grid .card").length, empty: !document.getElementById("empty").hidden }));
  check("search: no match shows the empty state", none.cards === 0 && none.empty);

  await page.keyboard.press("Escape");
  const cleared = await page.evaluate(() => ({ value: document.getElementById("search").value, cards: document.querySelectorAll("#grid .card").length }));
  check("search: Escape clears the query and restores all 50", cleared.value === "" && cleared.cards === 50);

  const box = await page.evaluate(() => {
    const b = document.getElementById("term-3c").getBoundingClientRect();
    return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
  });
  await page.mouse.move(box.x - 30, box.y - 10);
  await page.mouse.move(box.x, box.y, { steps: 5 });
  await page.waitForFunction(() => document.getElementById("term-3c").style.getPropertyValue("--mx") !== "", { timeout: 5000 });
  await sleep(450);
  const lit = await page.evaluate(() => {
    const card = document.getElementById("term-3c");
    return {
      lit: document.getElementById("grid").classList.contains("lit"),
      mx: card.style.getPropertyValue("--mx"),
      lift: new DOMMatrix(getComputedStyle(card.querySelector(".card-face")).transform).m42,
    };
  });
  check("pointer light: still follows the mouse over the cards", lit.lit && lit.mx.endsWith("px"), JSON.stringify(lit));
  check("hover: the card under the pointer still lifts 3px", Math.abs(lit.lift + 3) < 0.2, JSON.stringify(lit));

  await page.click("#theme-toggle");
  await page.waitForFunction(() => document.documentElement.dataset.theme === "light" && !document.documentElement.classList.contains("theme-switching"), { timeout: 10000 });
  await page.click("#term-3c .term-link");
  await toastText(page);
  await sleep(400);
  const light = await page.evaluate(() => ({
    border: getComputedStyle(document.querySelector("#term-3c .card-face")).borderTopColor,
    toastBg: getComputedStyle(document.getElementById("toast")).backgroundColor,
    stored: localStorage.getItem("theme"),
  }));
  check("theme: the toggle switches to light and is remembered", light.stored === "light");
  check("theme (light): the marked card uses the light accent and the toast the light surface", light.border === "rgb(4, 120, 87)" && light.toastBg === "rgb(240, 240, 240)", JSON.stringify(light));
  await page.reload({ waitUntil: "networkidle0" });
  const kept = await page.evaluate(() => document.documentElement.dataset.theme);
  check("theme: light survives a reload", kept === "light");
  quiet(page, "regression");
  await page.close();
}

/* ---- phone ---- */

async function phoneChecks(browser) {
  const context = await browser.createBrowserContext();
  await context.overridePermissions(LIVE_ORIGIN, ["clipboard-read", "clipboard-write"]);

  for (const width of [390, 320]) {
    const page = await openPage(context, {
      phone: true,
      viewport: { width, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
    });
    await page.bringToFront();
    const fit = await page.evaluate(() => {
      const cards = [...document.querySelectorAll("#grid .card")];
      const links = cards.map((c) => c.querySelector(".term-link").getBoundingClientRect());
      return {
        overflow: document.documentElement.scrollWidth - innerWidth,
        headsFit: cards.every((c) => {
          const head = c.querySelector(".card-head");
          const face = c.querySelector(".card-face");
          const inner = face.getBoundingClientRect().right - parseFloat(getComputedStyle(face).paddingRight);
          return head.scrollWidth <= head.clientWidth && c.querySelector(".badge").getBoundingClientRect().right <= inner + 0.5;
        }),
        oneLine: cards.every((c) => c.querySelector(".card-head").getBoundingClientRect().height < 50),
        minTapW: Math.min(...links.map((b) => b.width)),
        minTapH: Math.min(...links.map((b) => b.height)),
        hash: getComputedStyle(cards[0].querySelector(".term-link"), "::after").opacity,
      };
    });
    check(`phone ${width}px: no sideways scroll`, fit.overflow <= 0, `overflow ${fit.overflow}px`);
    check(`phone ${width}px: every term and its category tag fit on one line inside the card`, fit.headsFit && fit.oneLine);
    check(`phone ${width}px: every term link is at least 44 x 44 px to tap`, fit.minTapW >= 44 && fit.minTapH >= 44, `${fit.minTapW.toFixed(1)} x ${fit.minTapH.toFixed(1)}`);
    check(`phone ${width}px: the '#' is always visible (no hover on touch)`, fit.hash === "1", `opacity ${fit.hash}`);

    await page.tap("#term-demigrated .term-link");
    const toast = await toastText(page);
    await sleep(350);
    const placed = await page.evaluate(async () => {
      const b = document.getElementById("toast").getBoundingClientRect();
      return {
        inside: b.left >= 0 && b.right <= innerWidth && b.bottom <= innerHeight && b.top >= 0,
        clip: await navigator.clipboard.readText(),
        lit: document.getElementById("grid").classList.contains("lit"),
        leaning: document.querySelectorAll("#grid .card.lean").length,
        overflow: document.documentElement.scrollWidth - innerWidth,
      };
    });
    check(
      `phone ${width}px: tapping a term copies the link; the toast fits on screen`,
      toast[0] === "Link copied" && placed.clip === `${LIVE_URL}#demigrated` && placed.inside && placed.overflow <= 0,
      `${toast.join(" / ")} ${JSON.stringify(placed)}`
    );
    check(`phone ${width}px: no pointer light and no tilt on touch`, !placed.lit && placed.leaning === 0);
    quiet(page, `phone ${width}px`);
    await page.close();
  }
  await context.close();
}

/* ---- run ---- */

console.log(`Checking ${live ? "the live site" : "the working copy (served at the live address in the test browser)"}: ${LIVE_URL}\n`);

if (!live) await sourceRules();

const desktop = await launch({ mouse: true });
const context = await desktop.createBrowserContext();
await context.overridePermissions(LIVE_ORIGIN, ["clipboard-read", "clipboard-write"]);
for (const group of [loadChecks, glideChecks, shareChecks, linkChecks, reducedChecks, tiltChecks]) {
  await group(context);
}
// A fresh context: the theme checks write to localStorage.
const themed = await desktop.createBrowserContext();
await themed.overridePermissions(LIVE_ORIGIN, ["clipboard-read", "clipboard-write"]);
await regressionChecks(themed);
if (!live) await lateFontChecks(desktop);
await desktop.close();

const phone = await launch({ mouse: false });
await phoneChecks(phone);
await phone.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length} of ${results.length} checks passed.`);
if (failed.length) {
  console.log("Failed:");
  for (const f of failed) console.log(`  - ${f.name}`);
  process.exitCode = 1;
}
