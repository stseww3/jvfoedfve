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
- **MOTION 2 (hover states + state transitions):** raised from 1 at the owner's request (2026-11-14) for a livelier feel. Every motion is a reaction to something the reader just did: nothing plays on its own, nothing loops except the loading dots, nothing is scroll-driven or parallax. All of it stops under `prefers-reduced-motion`. The full list, each with its purpose, is under "Motion" below.

## Decisions (one line each)

- **Why dark default:** the trading scene lives on dark forums; dark is real identity here, not "dark looks tech" (R-21). A working light theme is still shipped and persisted, so users choose (R-21/R-34).
- **Why the type split (mono + sans):** Inconsolata (mono) carries the identity and sits on the "codes", the wordmark, the terms, the category labels, the filter chips and the search field; a system sans carries the prose, the expansions and the definitions, because long definitions in monospace are harder to read and readability is the whole job (R-06).
- **Why one accent (green `#34d399` dark / `#047857` light):** a single accent marks "current / active / match": the wordmark dot, the active filter, the search-match highlight, the focus ring and the pointer light (the card under the pointer is the current one). One colour, used only at those moments, keeps a strong identity without slop (R-13/R-29, Liveliness).
- **Why this palette:** two neutrals (near-black / near-white surfaces) plus one accent. No decorative gradients, no second accent (R-01/R-29). The one exception is the pointer light on the cards, with its reason and its limits written under "Motion".
- **Why cards, uniform:** each term is an equal record; a uniform grid is the honest shape for equal data, not a "feature card" template (R-14/R-05).
- **Why no icons beyond three:** only search, theme and GitHub get an icon, each genuinely functional; no decorative sparkles or arrows (R-04/R-08).
- **Why these radii:** varied on purpose (cards `0.8rem`, chips/buttons `0.5rem`, badges `0.4rem`) so nothing is a uniform pill (R-11).
- **Why the contrast targets:** every text pair clears WCAG AA and every control border clears the 3:1 non-text bar, verified with the skill's `contrast-check.py`, not eyeballed (R-25).
- **Why landmarks + one h1:** it is a whole document, so it has `header` / `main` / `footer`, one `h1`, and no skipped heading levels; the tagline is a paragraph, not an `h3` (R-39).
- **Why the three states:** the term list is a data view, so it has an explicit loading, empty and error state, each perceivable and announced (R-27).
- **Why the copy avoids em dashes and buzzwords:** honest, plain wording; no `—`, no "seamless / powerful / next-gen" (R-02/R-16).
- **Why the favicon and OG card:** real identity assets built from the actual wordmark and real terms, so shared links and the browser tab look finished; no fabricated numbers on the card (R-17/R-23).
- **Why the "/" hint in the search field:** the shortcut already existed but nobody could discover it. The hint only shows where a keyboard is likely (hidden on touch) and steps aside on focus or once a query is typed.

## Motion (what moves, and why)

Each entry is a reaction to a user action and has a stated purpose (R-19). None of them runs on its own.

- **Pointer light on cards:** a soft accent light follows the pointer. It tints the card under it and brushes the borders of the cards next to it. Purpose: in a grid of 50 equal records it marks which one is "current" and makes the grid answer the hand, using the accent for the meaning it already has. This is the only gradient and the only glow on the site (R-01; R-13: one kind of element, nothing on buttons, badges, icons or the page background). Off for touch input and under reduced motion. Contrast was re-measured at the brightest point of the light with `contrast-check.py`: lowest text pair 5.79:1 dark / 6.17:1 light; the tag outlines on the lit card step up one shade (`--border-strong`) to hold 3.55:1 / 3.78:1, because the regular outline would drop to 2.70:1 / 2.96:1 there.
- **Card lift on hover:** a 3px rise, plus a soft shadow in the light theme only. Purpose: an elevation marker for the current card, not a default on every component (R-12). No shadow in the dark theme, where it cannot be seen against a black page.
- **Sliding filter indicator:** the accent outline travels from the old category to the new one. Purpose: shows the filter state moving instead of teleporting, and ties the click to the result. The chips are updated in place, so keyboard focus stays on the chip that was pressed.
- **Card stagger on category switch:** cards fade up in sequence (first 15 only, 22ms apart). Purpose: signals that the list was replaced and leads the eye from the top. Not used while typing in search, where it would read as lag.
- **Circular theme reveal and icon turn:** the new theme wipes out from the toggle while the sun and moon swap with a quarter turn. Purpose: ties the change to the control that caused it. Uses the View Transitions API; browsers without it switch instantly.
- **Press feedback:** chips and icon buttons dip slightly while pressed. Purpose: confirms the press before the result renders (the active state R-39 asks for).
- **Left out on purpose:** card tilt and 3D parallax (they blur the definition text exactly while it is being read), scroll-triggered reveals, and any looping or floating decoration.
