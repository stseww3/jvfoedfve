const CATEGORY_LABELS = {
  all: "All",
  access: "Access",
  account: "Accounts",
  naming: "Names",
  community: "Community",
  security: "Security",
  selling: "Selling",
};

const state = {
  terms: [],
  query: "",
  category: "all",
  target: null,
};

const els = {
  grid: document.getElementById("grid"),
  filters: document.getElementById("filters"),
  search: document.getElementById("search"),
  count: document.getElementById("count"),
  empty: document.getElementById("empty"),
  error: document.getElementById("error"),
  loading: document.getElementById("loading"),
  toast: document.getElementById("toast"),
  themeToggle: document.getElementById("theme-toggle"),
  indicator: null,
};

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const prefersReduced = () => reducedMotion.matches;
const canAnimate = () => !prefersReduced() && "animate" in Element.prototype;

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Split on the raw text first and escape each piece afterwards, so a query
// such as "amp" or "quot" can never match inside an HTML entity.
function highlight(text, query) {
  const raw = String(text);
  if (!query) return escapeHtml(raw);
  const pattern = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return raw
    .split(new RegExp(`(${pattern})`, "ig"))
    .map((part, i) => (i % 2 ? `<mark>${escapeHtml(part)}</mark>` : escapeHtml(part)))
    .join("");
}

function matches(term, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  const haystack = [term.term, term.full, term.definition, ...(term.aliases || [])]
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

// The part after "#" in a term's link: "B/O" -> "b-o", "Semi-OG" -> "semi-og".
function slugify(term) {
  return term
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/* ---- filters ---- */

function renderFilters() {
  const used = new Set(state.terms.map((t) => t.category));
  const categories = ["all", ...Object.keys(CATEGORY_LABELS).filter((c) => used.has(c))];

  els.filters.innerHTML =
    '<span class="chip-indicator no-anim" aria-hidden="true"></span>' +
    categories
      .map(
        (cat) =>
          `<button type="button" class="chip" data-category="${cat}" aria-pressed="false">${CATEGORY_LABELS[cat]}</button>`
      )
      .join("");

  els.indicator = els.filters.querySelector(".chip-indicator");
  els.filters.classList.add("has-indicator");
  syncFilters(false);

  // Chip sizes change when the web font arrives or the row wraps; follow
  // them without animating, so the indicator never drifts off its chip.
  if ("ResizeObserver" in window) {
    const observer = new ResizeObserver(() => moveIndicator(false));
    observer.observe(els.filters);
    els.filters.querySelectorAll(".chip").forEach((chip) => observer.observe(chip));
  } else {
    window.addEventListener("resize", () => moveIndicator(false));
  }
}

function moveIndicator(animate) {
  const active = els.filters.querySelector(".chip.active");
  if (!active || !els.indicator) return;

  // Sub-pixel layout size, and the position taken from the box centre: both
  // are unaffected by the momentary press scale on the chip, and unlike
  // offsetWidth they are not rounded to whole pixels.
  const style = getComputedStyle(active);
  const width = parseFloat(style.width);
  const height = parseFloat(style.height);
  const box = active.getBoundingClientRect();
  const origin = els.filters.getBoundingClientRect();
  const x = box.left + box.width / 2 - width / 2 - origin.left;
  const y = box.top + box.height / 2 - height / 2 - origin.top;

  els.indicator.classList.toggle("no-anim", !animate);
  els.indicator.style.width = `${width}px`;
  els.indicator.style.height = `${height}px`;
  els.indicator.style.transform = `translate(${x}px, ${y}px)`;
}

// Chips are updated in place (not re-rendered) so keyboard focus stays on
// the chip that was just pressed and its colour can transition.
function syncFilters(animate) {
  els.filters.querySelectorAll(".chip").forEach((chip) => {
    const on = chip.dataset.category === state.category;
    chip.classList.toggle("active", on);
    chip.setAttribute("aria-pressed", String(on));
  });
  moveIndicator(animate);
}

/* ---- cards ---- */

function cardHtml(term, query) {
  const aliases = (term.aliases || [])
    .map((a) => `<li>${escapeHtml(a)}</li>`)
    .join("");

  return `
    <article class="card${term.slug === state.target ? " is-target" : ""}" id="term-${term.slug}" data-slug="${term.slug}">
      <div class="card-head">
        <h2 class="card-term"><a class="term-link" href="#${term.slug}" title="Copy link to ${escapeHtml(term.term)}">${highlight(term.term, query)}</a></h2>
        <span class="badge">${escapeHtml(CATEGORY_LABELS[term.category] || term.category)}</span>
      </div>
      <p class="card-full">${highlight(term.full, query)}</p>
      <p class="card-def">${highlight(term.definition, query)}</p>
      ${aliases ? `<ul class="aliases">${aliases}</ul>` : ""}
    </article>
  `;
}

function render() {
  const query = state.query.trim();
  const shown = state.terms.filter(
    (t) =>
      (state.category === "all" || t.category === state.category) &&
      matches(t, query)
  );

  els.grid.innerHTML = shown.map((t) => cardHtml(t, query)).join("");
  els.count.textContent = `${shown.length} of ${state.terms.length} terms`;
  els.empty.hidden = shown.length !== 0;

  // Fresh cards have no light position yet; give them one if the pointer
  // is already resting on the grid (e.g. while typing in the search box).
  if (light.on) requestLight();
}

/* ---- card motion ----
   Cards are rebuilt on every render, so motion is worked out from positions:
   where a term's card was before the render and where its new card is now. */

const GLIDE_MS = 420;
const EASE_OUT = "cubic-bezier(0.2, 0.8, 0.2, 1)";

const onScreen = (rect) => rect.bottom > 0 && rect.top < window.innerHeight;

function fadeUp(card, order) {
  card.animate(
    [
      { opacity: 0, transform: "translateY(10px)" },
      { opacity: 1, transform: "none" },
    ],
    { duration: 300, delay: Math.min(order, 14) * 22, easing: "ease", fill: "backwards" }
  );
}

// First paint: the cards on screen fade up in sequence.
function enterCards() {
  if (!canAnimate()) return;
  let order = 0;
  for (const card of els.grid.children) {
    const rect = card.getBoundingClientRect();
    if (rect.top >= window.innerHeight) break;
    if (onScreen(rect)) fadeUp(card, order++);
  }
}

// Where every card is right now, mid-flight positions included.
function snapshotCards() {
  const seen = new Map();
  for (const card of els.grid.children) {
    seen.set(card.dataset.slug, {
      node: card,
      rect: card.getBoundingClientRect(),
      opacity: Number(getComputedStyle(card).opacity),
    });
  }
  return seen;
}

// Category switch: a card that stays travels from its old place to its new
// one, a new card fades up, and a card that left fades out where it stood.
function glideCards(before) {
  const cards = Array.from(els.grid.children);
  const rects = cards.map((card) => card.getBoundingClientRect());
  const glides = [];
  let order = 0;

  cards.forEach((card, i) => {
    const last = rects[i];
    const was = before.get(card.dataset.slug);
    if (!was) {
      if (onScreen(last)) fadeUp(card, order++);
      return;
    }
    before.delete(card.dataset.slug);

    const first = was.rect;
    const dx = first.left - last.left;
    const dy = first.top - last.top;
    const distance = Math.hypot(dx, dy);
    const startsOnScreen = onScreen(first);
    const endsOnScreen = onScreen(last);
    if (!startsOnScreen && !endsOnScreen) return;
    if (distance < 1 && was.opacity > 0.99) return;

    // A trip longer than one screen is cut to one screen of travel, kept on
    // the end the reader can see, so cards never streak across the page.
    const reach = window.innerHeight + last.height;
    let from = [dx, dy];
    let to = [0, 0];
    if (distance > reach) {
      const part = reach / distance;
      if (endsOnScreen) from = [dx * part, dy * part];
      else to = [dx * (1 - part), dy * (1 - part)];
    }

    glides.push(
      card.animate(
        [
          { transform: `translate(${from[0]}px, ${from[1]}px)`, opacity: was.opacity },
          { transform: `translate(${to[0]}px, ${to[1]}px)`, opacity: 1 },
        ],
        { duration: GLIDE_MS, easing: EASE_OUT }
      )
    );
  });

  fadeOutLeft(before);

  // The pointer may be resting on the grid (keyboard filter change): once
  // the cards have landed, light the one that is now under it.
  if (glides.length) {
    Promise.allSettled(glides.map((glide) => glide.finished)).then(() => {
      if (light.on) requestLight();
    });
  }
}

// What is still in `left` are the cards the new filter removed. The ones on
// screen fade out in a fixed layer placed before the grid: they take up no
// room, stay under the arriving cards, and cannot be focused or clicked.
function fadeOutLeft(left) {
  const layer = document.createElement("div");
  layer.className = "leaving";
  layer.inert = true;
  layer.setAttribute("aria-hidden", "true");

  for (const { node, rect } of left.values()) {
    if (!onScreen(rect)) continue;
    node.removeAttribute("id");
    node.style.cssText = `left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px`;
    layer.appendChild(node);
  }
  if (!layer.childElementCount) return;

  els.grid.before(layer);
  layer
    .animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, easing: "linear" })
    .finished.catch(() => {})
    .then(() => layer.remove());
}

function setCategory(category) {
  state.category = category;
  syncFilters(true);
  if (!canAnimate()) {
    render();
    return;
  }
  const before = snapshotCards();
  render();
  glideCards(before);
}

/* ---- term links ----
   Every term has an address: this page plus "#" and the term's slug.
   Clicking a term copies that address; opening it lands on the term. */

function termUrl(slug) {
  return `${location.origin}${location.pathname}#${slug}`;
}

function hashSlug() {
  let raw = location.hash.slice(1);
  try {
    raw = decodeURIComponent(raw);
  } catch (e) {}
  raw = raw.toLowerCase();
  return state.terms.some((t) => t.slug === raw) ? raw : null;
}

function markTarget(slug) {
  state.target = slug;
  for (const card of els.grid.children) {
    card.classList.toggle("is-target", card.dataset.slug === slug);
  }
}

function goToTarget(smooth) {
  const card = document.getElementById(`term-${state.target}`);
  if (!card) return;
  card.scrollIntoView({
    block: "center",
    behavior: smooth && !prefersReduced() ? "smooth" : "auto",
  });
  // Focus follows the jump, so Tab and screen readers carry on from the
  // linked term instead of the top of the page.
  card.tabIndex = -1;
  card.focus({ preventScroll: true });
}

// Arriving from a shared link. A first-time visitor has no cached web font:
// it lands after the first jump, the filter row takes one line less, and the
// card ends up a line off centre. So the jump is repeated once the fonts are
// in, unless the reader has taken over by then.
function landOnTarget() {
  goToTarget(false);
  if (!document.fonts) return;

  let handsOff = true;
  const takeOver = () => {
    handsOff = false;
  };
  for (const type of ["wheel", "touchstart", "pointerdown", "keydown"]) {
    window.addEventListener(type, takeOver, { once: true, passive: true });
  }
  document.fonts.ready.then(() => {
    if (handsOff && state.target) goToTarget(false);
  });
}

// The address changed under an open page (edited by hand, or back/forward).
function openHashTarget() {
  const slug = hashSlug();
  if (!slug) {
    markTarget(null);
    return;
  }
  // The linked term must be on the page, whatever was filtered before.
  state.category = "all";
  state.query = "";
  els.search.value = "";
  syncFilters(false);
  state.target = slug;
  render();
  goToTarget(true);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    // No async clipboard (older or in-app browsers): the selection route.
    // It borrows focus for a moment, so focus is handed back afterwards.
    const focused = document.activeElement;
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(field);
    field.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (e2) {}
    field.remove();
    if (focused instanceof HTMLElement) focused.focus({ preventScroll: true });
    return copied;
  }
}

let toastTimer = 0;

function showToast(title, detail) {
  const head = document.createElement("strong");
  head.textContent = title;
  const body = document.createElement("span");
  body.textContent = detail;
  els.toast.replaceChildren(head, body);
  els.toast.classList.add("show");

  // Hide it, then empty it once it has faded, so no stale text is left for
  // a screen reader to find.
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    els.toast.classList.remove("show");
    toastTimer = setTimeout(() => els.toast.replaceChildren(), 300);
  }, 2400);
}

async function shareTerm(link) {
  const slug = link.closest(".card").dataset.slug;
  const url = termUrl(slug);

  // The address bar follows, so the link is at hand even if copying fails.
  history.replaceState(null, "", `#${slug}`);
  markTarget(slug);

  const copied = await copyText(url);
  if (copied) showToast("Link copied", url.replace(/^https?:\/\//, ""));
  else showToast("Could not copy", "The link is in the address bar.");
}

/* ---- pointer light ----
   One pointer position, written to every card near it as --mx / --my.
   styles.css turns those into the accent border light and the soft fill. */

const LIGHT_REACH = 320;
const light = { x: 0, y: 0, frame: 0, on: false, cards: new WeakSet() };

function paintLight() {
  light.frame = 0;
  if (!light.on) return;

  const cards = els.grid.children;
  const rects = new Array(cards.length);
  for (let i = 0; i < cards.length; i++) rects[i] = cards[i].getBoundingClientRect();

  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    const r = rects[i];
    const near =
      light.x > r.left - LIGHT_REACH &&
      light.x < r.right + LIGHT_REACH &&
      light.y > r.top - LIGHT_REACH &&
      light.y < r.bottom + LIGHT_REACH;

    if (near) {
      card.style.setProperty("--mx", `${Math.round(light.x - r.left)}px`);
      card.style.setProperty("--my", `${Math.round(light.y - r.top)}px`);
      light.cards.add(card);
    } else if (light.cards.has(card)) {
      card.style.removeProperty("--mx");
      card.style.removeProperty("--my");
      light.cards.delete(card);
    }
  }
}

function requestLight() {
  if (!light.frame) light.frame = requestAnimationFrame(paintLight);
}

function initPointerLight() {
  els.grid.addEventListener("pointermove", (e) => {
    if (e.pointerType === "touch" || prefersReduced()) return;
    light.x = e.clientX;
    light.y = e.clientY;
    if (!light.on) {
      light.on = true;
      els.grid.classList.add("lit");
    }
    requestLight();
  });

  els.grid.addEventListener("pointerleave", () => {
    light.on = false;
    els.grid.classList.remove("lit");
  });

  // The page can scroll under a pointer that is not moving.
  window.addEventListener(
    "scroll",
    () => {
      if (light.on) requestLight();
    },
    { passive: true }
  );
}

/* ---- events ---- */

function bindEvents() {
  els.search.addEventListener("input", (e) => {
    state.query = e.target.value;
    render();
  });

  els.search.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && els.search.value) {
      els.search.value = "";
      state.query = "";
      render();
    }
  });

  els.filters.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn || btn.dataset.category === state.category) return;
    setCategory(btn.dataset.category);
  });

  els.grid.addEventListener("click", (e) => {
    const link = e.target.closest(".term-link");
    // A modified click keeps its browser meaning (new tab, new window).
    if (!link || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    shareTerm(link);
  });

  window.addEventListener("hashchange", openHashTarget);

  document.addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if (e.key === "/" && tag !== "input" && tag !== "textarea") {
      e.preventDefault();
      els.search.focus();
    }
  });

  initPointerLight();
}

/* ---- theme ---- */

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const isLight = theme === "light";
  els.themeToggle.setAttribute("aria-pressed", String(isLight));
  els.themeToggle.setAttribute(
    "aria-label",
    isLight ? "Switch to dark theme" : "Switch to light theme"
  );
}

function setTheme(next) {
  try {
    localStorage.setItem("theme", next);
  } catch (e) {}
  applyTheme(next);
}

function initTheme() {
  const root = document.documentElement;
  const current = root.getAttribute("data-theme") || "dark";
  applyTheme(current);

  els.themeToggle.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";

    if (!document.startViewTransition || prefersReduced()) {
      setTheme(next);
      return;
    }

    const rect = els.themeToggle.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    );

    root.classList.add("theme-switching");
    const transition = document.startViewTransition(() => setTheme(next));
    transition.ready
      .then(() => {
        root.animate(
          {
            clipPath: [
              `circle(0px at ${x}px ${y}px)`,
              `circle(${endRadius}px at ${x}px ${y}px)`,
            ],
          },
          {
            duration: 480,
            easing: "ease-in-out",
            pseudoElement: "::view-transition-new(root)",
          }
        );
      })
      .catch(() => {});
    transition.finished
      .catch(() => {})
      .then(() => root.classList.remove("theme-switching"));
  });
}

async function init() {
  initTheme();
  try {
    const res = await fetch("terms.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.terms = (await res.json()).map((t) => ({ ...t, slug: slugify(t.term) }));
    state.terms.sort((a, b) =>
      a.term.localeCompare(b.term, undefined, { sensitivity: "base" })
    );
    state.target = hashSlug();
    els.loading.hidden = true;
    renderFilters();
    bindEvents();
    render();
    if (state.target) landOnTarget();
    enterCards();
  } catch (err) {
    console.error(err);
    els.loading.hidden = true;
    els.error.hidden = false;
    els.count.hidden = true;
  }
}

init();
