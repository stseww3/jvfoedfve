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
};

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function highlight(text, query) {
  const safe = escapeHtml(text);
  if (!query) return safe;
  const pattern = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return safe.replace(new RegExp(`(${pattern})`, "ig"), "<mark>$1</mark>");
}

function matches(term, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  const haystack = [term.term, term.full, term.definition, ...(term.aliases || [])]
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

function renderFilters() {
  const used = new Set(state.terms.map((t) => t.category));
  const categories = ["all", ...Object.keys(CATEGORY_LABELS).filter((c) => used.has(c))];

  els.filters.innerHTML = categories
    .map((cat) => {
      const active = cat === state.category ? " active" : "";
      const pressed = cat === state.category ? "true" : "false";
      return `<button type="button" class="chip${active}" data-category="${cat}" aria-pressed="${pressed}">${CATEGORY_LABELS[cat]}</button>`;
    })
    .join("");
}

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

function render() {
  const query = state.query.trim();
  const filtered = state.terms.filter(
    (t) =>
      (state.category === "all" || t.category === state.category) &&
      matches(t, query)
  );

  els.grid.innerHTML = filtered.map(cardHtml).join("");
  els.count.textContent = `${filtered.length} of ${state.terms.length} terms`;
  els.empty.hidden = filtered.length !== 0;
}

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
    if (!btn) return;
    state.category = btn.dataset.category;
    renderFilters();
    render();
  });

  document.addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if (e.key === "/" && tag !== "input" && tag !== "textarea") {
      e.preventDefault();
      els.search.focus();
    }
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const isLight = theme === "light";
  els.themeToggle.setAttribute("aria-pressed", String(isLight));
  els.themeToggle.setAttribute(
    "aria-label",
    isLight ? "Switch to dark theme" : "Switch to light theme"
  );
}

function initTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(current);
  els.themeToggle.addEventListener("click", () => {
    const next =
      document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    try {
      localStorage.setItem("theme", next);
    } catch (e) {}
    applyTheme(next);
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
    render();
  } catch (err) {
    console.error(err);
    els.loading.hidden = true;
    els.error.hidden = false;
    els.count.hidden = true;
  }
}

init();
