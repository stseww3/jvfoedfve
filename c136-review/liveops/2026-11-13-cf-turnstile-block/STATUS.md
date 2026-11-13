# c116 live-ops handoff: Turnstile mint outage (2026-11-13 evening)

State as of about 22:10 (d3 clock). Written so a replacement sub-agent can pick up without re-diagnosing.

## Current state on d3

- Engine `node_apex.exe` (`tsb-apex-squad.mjs`): **stopped on purpose**. Firefox donors: stopped.
- Proxy `tun_apex_socks5.py`: left running (PID 36992 when last checked, about 22:05).
- Last match result in `c116\tsb-team-results.jsonl`: 20:02:44. No matches since.
- Waiting on an admin decision (see "Open decision"). Do not restart the 40-bot pool before that.

Working dir: `C:\Users\workstation\Desktop\远程\workspaces\c116`

## Symptom

In every test run this evening the Firefox donors produced no Turnstile tokens (the
`Fresh Turnstile token ready` line never appears in `tsb-apex-squad.log`). Bots that do get into the
lobby are repeatedly kicked with error 4573. The pool therefore never reaches the 12 ready bots the
engine needs to enter a match. When exactly minting stopped between 20:02 and 20:50 was not pinned down.

## What was tested

| Suspect | Test | Result |
|---|---|---|
| Engine merely slow | Checked process list | Engine was dead; restarted |
| BiDi "session locked" loop | Killed stray Firefox, deleted `parent.lock`, clean restart | Loop gone, mint still failing |
| Proxy down | `curl` through the donor egress SOCKS ports (`portToSocks`: 10821/10824/10827/10830) | Live exit IPs, territorial.io HTTP 200 |
| Code regression from tonight's edits | Restored `.bak-34teamonly` (the 19:05 build that was winning) | Still 0 tokens |
| Stale exit IP | Donor recycle rotates the SOCKS session; roughly 20 fresh IPs tried | Still 0 tokens |
| Donor contention / solve window too short | `patch_coldstart.mjs` | Still 0 tokens |
| Reduced refresh rate plus about 8 min idle | `patch_gentle_cf.mjs`, engine and Firefox stopped in between | Still 0 tokens |

The last row shows a short pause does not restore minting. It does not clear the old refresh rate as
the original trigger.

## Working conclusion (inference, not directly observed)

Cloudflare is refusing to issue tokens to this automation. This is inferred by elimination: every local
cause tested came back clean. No Cloudflare response stating a block was captured, and the Turnstile
widget's own error code inside the donor page has not been read. Reading that code is the cheapest next
piece of direct evidence. The meaning of error 4573 was not confirmed either.

Probable contributing factor: before the gentle patch the engine retried mint every 15 s for each
token-less headless bot (line 1721), ran two concurrent solves per donor, and launched waves 3.5 s
apart. The bridge chat history says one token is good for about 60 minutes per account, so that rate
was far above what is needed.

## Changes made to `tsb-apex-squad.mjs` on d3 (both applied and present in the file now)

`patch_coldstart.mjs`
- `donor._mintFailCount >= 2` to `>= 5`
- solve loop `i < 14` to `i < 22`

`patch_gentle_cf.mjs`
- retry interval `(c.isHeadless ? 15000 : 75000)` to `(c.isHeadless ? 90000 : 180000)`
- per-donor concurrent solves `cur < 2` to `cur < 1`
- wave cadence `lastSyncLaunch > 3500` to `> 8000`
- `reloadingForFreshTokens` reset `3200` to `7000`

Both scripts use the relative path `tsb-apex-squad.mjs`, so run them with the c116 dir as cwd. Each
asserts its anchors are unique and aborts without writing otherwise. Copies on d3 are in
`workspaces\c136\`.

Backups in c116: `.bak-34teamonly` (19:05, last winning build), `.bak-40pool` (16:43),
`.bak-coldstart`, `.bak-before-revert` (20:39 build plus coldstart patch), `.bak-gentlecf`.

Neither patch has been shown to restore minting. They lower the load placed on Cloudflare; whether that
is sufficient once tokens are issued again is untested.

## Open decision (put to the admin about 22:10, in reply to #14338 and #14365)

1. Cool down for hours, then retry with the gentle config. Zero cost. How long recovery takes is a
   guess; there is no evidence yet on how long the refusal lasts.
2. Replace donor minting with a paid solver API (CapSolver / 2captcha). Needs an API key and balance
   from the admin. Not implemented.
3. Use the archive the admin says they sent ("4 个磨片", described as the Turnstile answer). It was
   **not found** on d3 or in the bridge chat history. Ask the admin to resend it or give its path.

## Suggested next steps for whoever continues

- Before any full restart, probe with **one** donor and one solve to see whether tokens are being
  issued again. Do not bring up 40 bots to find out.
- Capture the Turnstile error code from the donor page during a failed solve.
- Standing admin instruction (#14338): do not refresh CF constantly; a token lasts 1 to 2 hours and can
  be renewed. Keep the gentle config.
