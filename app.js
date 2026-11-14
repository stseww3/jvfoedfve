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
};

const els = {
  grid: document.getElementById("grid"),
  filters: document.getElementById("filters"),
  search: document.getElementById("search"),
  count: document.getElementById("count"),
  empty: document.getElementById("empty"),
  error: document.getElementById("error"),
  loading: document.getElementById("loading"),
  themeToggle: document.getElementById("theme-toggle"),
  indicator: null,
};

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const prefersReduced = () => reducedMotion.matches;

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

function cardHtml(term) {
  const aliases = (term.aliases || [])
    .map((a) => `<li>${escapeHtml(a)}</li>`)
    .join("");

  return `
    <article class="card">
      <div class="card-head">
        <h2 class="card-term">${highlight(term.term, state.query)}</h2>
        <span class="badge">${escapeHtml(CATEGORY_LABELS[term.category] || term.category)}</span>
      </div>
      <p class="card-full">${highlight(term.full, state.query)}</p>
      <p class="card-def">${highlight(term.definition, state.query)}</p>
      ${aliases ? `<ul class="aliases">${aliases}</ul>` : ""}
    </article>
  `;
}

function render(animate) {
  const query = state.query.trim();
  const filtered = state.terms.filter(
    (t) =>
      (state.category === "all" || t.category === state.category) &&
      matches(t, query)
  );

  els.grid.innerHTML = filtered.map(cardHtml).join("");

  if (animate && !prefersReduced()) {
    const cards = els.grid.querySelectorAll(".card");
    cards.forEach((card, i) => {
      card.style.animationDelay = Math.min(i, 14) * 22 + "ms";
      card.classList.add("card-in");
    });
  }

  els.count.textContent = `${filtered.length} of ${state.terms.length} terms`;
  els.empty.hidden = filtered.length !== 0;

  // Fresh cards have no light position yet; give them one if the pointer
  // is already resting on the grid (e.g. while typing in the search box).
  if (light.on) requestLight();
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
    render(false);
  });

  els.search.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && els.search.value) {
      els.search.value = "";
      state.query = "";
      render(false);
    }
  });

  els.filters.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn || btn.dataset.category === state.category) return;
    state.category = btn.dataset.category;
    syncFilters(true);
    render(true);
  });

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
    state.terms = await res.json();
    state.terms.sort((a, b) =>
      a.term.localeCompare(b.term, undefined, { sensitivity: "base" })
    );
    els.loading.hidden = true;
    renderFilters();
    bindEvents();
    render(true);
  } catch (err) {
    console.error(err);
    els.loading.hidden = true;
    els.error.hidden = false;
    els.count.hidden = true;
  }
}

init();
