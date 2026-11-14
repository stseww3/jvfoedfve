# DESIGN.md

Direction and the one-line reason behind every major decision (anti-slop R-31). This is the filter's "soul" file: identity first, then the anti-slop rules sit on top of it.

## Identity

- **Product:** a reference dictionary for abbreviations used in the OG Minecraft account-trading community (OG, NFA, FA, MSA, MM, and so on).
- **Audience:** traders, collectors and middlemen who live on dark forums (OGUsers and similar). They value speed, density and credibility over marketing gloss.
- **Voice:** plain, lowercase, no hype. It explains jargon; it never sells.

## Design Read (dials)

Reading this as: a single-page reference tool for a forum/trading audience, in a terminal-adjacent minimalist language.

- **ENERGY 1 (calm):** it is a lookup tool, not a landing page. Quiet by default.
- **RHYTHM 1 (uniform):** every entry is an equal data item, so a uniform card grid is correct here (this is deliberate uniformity, not a template accident). The only non-uniform surface is the hero.
- **MOTION 1 (hover + micro-transitions only):** hover lift on cards, colour transitions on controls, a brief loading pulse. Nothing parallax, nothing auto-playing. All of it stops under `prefers-reduced-motion`.

## Decisions (one line each)

- **Why dark default:** the trading scene lives on dark forums; dark is real identity here, not "dark looks tech" (R-21). A working light theme is still shipped and persisted, so users choose (R-21/R-34).
- **Why the type split (mono + sans):** Inconsolata (mono) carries the identity and sits on the "codes", the wordmark, the terms, the category labels, the filter chips and the search field; a system sans carries the prose, the expansions and the definitions, because long definitions in monospace are harder to read and readability is the whole job (R-06).
- **Why one accent (green `#34d399` dark / `#047857` light):** a single accent marks "current / active / match": the wordmark dot, the active filter, the search-match highlight and the focus ring. One colour, used only at those moments, keeps a strong identity without slop (R-13/R-29, Liveliness).
- **Why this palette:** two neutrals (near-black / near-white surfaces) plus one accent. No gradients, no glow, no second accent (R-01/R-29).
- **Why cards, uniform:** each term is an equal record; a uniform grid is the honest shape for equal data, not a "feature card" template (R-14/R-05).
- **Why no icons beyond three:** only search, theme and GitHub get an icon, each genuinely functional; no decorative sparkles or arrows (R-04/R-08).
- **Why these radii:** varied on purpose (cards `0.8rem`, chips/buttons `0.5rem`, badges `0.4rem`) so nothing is a uniform pill (R-11).
- **Why the contrast targets:** every text pair clears WCAG AA and every control border clears the 3:1 non-text bar, verified with the skill's `contrast-check.py`, not eyeballed (R-25).
- **Why landmarks + one h1:** it is a whole document, so it has `header` / `main` / `footer`, one `h1`, and no skipped heading levels; the tagline is a paragraph, not an `h3` (R-39).
- **Why the three states:** the term list is a data view, so it has an explicit loading, empty and error state, each perceivable and announced (R-27).
- **Why the copy avoids em dashes and buzzwords:** honest, plain wording; no `—`, no "seamless / powerful / next-gen" (R-02/R-16).
- **Why the favicon and OG card:** real identity assets built from the actual wordmark and real terms, so shared links and the browser tab look finished; no fabricated numbers on the card (R-17/R-23).
