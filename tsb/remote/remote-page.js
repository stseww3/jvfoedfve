(() => {
  // Manual (remote) mode. Commands come from the command webhook (polled by
  // relay.js) as {"p": "<command JSON>", "sig": "<base64url HMAC-SHA256 of p>"};
  // the HMAC key is the key text from the panel, as UTF-8.
  const VERSION = "0.7.0";
  const SINGLE_ONLY = !1;
  const SEEN_KEY = "territorialStrategyBotRemoteSeen";
  // Stuck pages. The lobby command and the panel button reload the page; with a loop on, a page
  // without progress (no game ticks, no lobby updates) reloads by itself and the loop goes on.
  // The loop carries over in sessionStorage: this tab only, the next page load only.
  const RECOVER_KEY = "territorialStrategyBotRecover";
  const STUCK_MS = 6e4;
  // after the game reports a closed connection; "Player already in lobby" and "Please try again later!" wait longer
  const CLOSED_MS = 2e4;
  const WAIT_MS = { 4527: 3e4, 4557: 3e5, 4558: 3e5, 4559: 3e5, 4560: 3e5, 4589: 3e5 };
  // these stop the loop and disarm instead of reloading: the game's bot detection, bans, blocks,
  // kicks, a second login, account problems, not enough gold
  const STOP_CODES = [4591, 4577, 4555, 4540, 4730, 4528, 4495, 4480, 4580];
  // the same, from the text of the game's window, in case the close code was missed
  const STOP_TEXT = /Bot Detection|you are a bot|IP is banned|Account is blocked|been kicked|Kicked from lobby|Another login detected/i;
  const RELOADS_IN_A_ROW = 3;
  const RELOADS_PER_HOUR = 10;
  // After the extension is updated, reloaded or disabled, this page keeps running the old scripts
  // and the relay can no longer reach the service worker, so no command gets through. In manual mode
  // the page reloads itself once the bot is not in a running game, at most this long after.
  const UPDATE_WAIT_MS = 18e5;
  // the texts the game's error window shows
  const CODE_TEXT = {
    1006: "No Internet / No Server Response / Server Restart", 3249: "No Internet / No Server Response / Server Restart",
    4211: "New Game Update", 4229: "Bad Internet / Unresponsive Client", 4480: "account error", 4495: "Account doesn't exist.",
    4527: "Player already in lobby", 4528: "Lobby Kick: Another login detected.", 4530: "Lobby Timeout", 4540: "You have been kicked.",
    4555: "This Account is blocked.", 4577: "Your IP is banned.", 4580: "More Gold needed", 4591: "The algo determined you are a bot.",
    4705: "Lobby not found", 4730: "Kicked from lobby"
  };
  const codeText = (c) => CODE_TEXT[c] || (4557 <= c && c <= 4560 || 4589 === c ? "Please try again later!" : "Unknown error");
  const WINDOW_MS = 6e5;
  const AHEAD_MS = 12e4;
  // after I die or the game ends, wait this long, then leave
  const EXIT_MS = 3e3;
  // with "stay" on, after I die the bot stays in the game until it is over, at most this long
  const STAY_MAX_MS = 18e5;
  // lobby rooms: 0 team, 1 battle royale, 2 1v1, 3 zombie; room modes 0..6 are team, 7 and 10 are battle royale
  const TEAM_ROOM = 0;
  const TEAM_MODES = [0, 1, 2, 3, 4, 5, 6];
  const BR_ROOM = 1;
  const BR_MODES = [7, 10];
  // longer replay texts are reported without the text
  const REPLAY_MAX = 2e6;
  const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
  const encoder = new TextEncoder();
  const dict = () => window.dictionary || null;
  const read = (name) => {
    const d = dict();
    return d && d[name] ? window[d[name]] : undefined;
  };
  const state = {
    poll: null,
    post: null,
    last: null,
    game: null,
    gate: null,
    queue: [],
    busy: false,
    configured: null,
    box: null,
    armButton: null,
    stayBox: null,
    info: null,
    // "single": a new singleplayer game after each game; "mp": back to the battle royale lobby and Ready
    loop: null,
    startAt: 0,
    // after a reload by the extension: wait for the menu until then, and open the lobby once (lobby command without a loop)
    resumeAt: 0,
    openOnce: !1,
    // the relay's line to the service worker; dead once the extension is updated, reloaded or disabled
    worker: null,
    // { at }: a reload for an extension update is due
    update: null
  };
  // sel is the game's lobbySelection, [room, ?, view, ready]; rooms its LobbyRoom objects
  const lobby = {
    sel: null,
    rooms: null,
    initAt: 0,
    tickAt: 0,
    openAt: 0,
    opens: 0,
    reopens: 0,
    leftAt: 0,
    pressAt: 0,
    presses: 0,
    closing: null,
    error: null,
    stopped: null
  };
  // reloads: automatic reloads in the last hour; inRow: automatic reloads since the last lobby or running game
  const rec = (() => {
    let v = null;
    try {
      v = JSON.parse(sessionStorage.getItem(RECOVER_KEY));
    } catch {}
    v = v && "object" == typeof v ? v : {};
    return { reloads: Array.isArray(v.reloads) ? v.reloads : [], inRow: v.inRow | 0, resume: v.resume || null, last: v.last || null };
  })();
  const saveRecover = () => {
    try {
      sessionStorage.setItem(RECOVER_KEY, JSON.stringify(rec));
    } catch {}
  };
  // the watchdog: mark changes with the game state, the game tick and lobby updates
  const rw = { mark: "", progressAt: Date.now(), code: null, codes: [], pending: !1 };

  const loadSeen = () => {
    try {
      const v = JSON.parse(localStorage.getItem(SEEN_KEY));
      return v && "object" == typeof v ? v : {};
    } catch {
      return {};
    }
  };
  let seen = loadSeen();
  const saveSeen = () => {
    const now = Date.now();
    seen = Object.fromEntries(Object.entries(seen).filter(([, t]) => now - t < 864e5).sort((a, b) => b[1] - a[1]).slice(0, 500));
    try {
      localStorage.setItem(SEEN_KEY, JSON.stringify(seen));
    } catch {}
  };
  // true when no tab has used any of the keys yet
  const claim = (keys) => {
    const take = () => {
      seen = loadSeen();
      if (keys.some((k) => seen[k])) return false;
      const now = Date.now();
      for (const k of keys) seen[k] = now;
      saveSeen();
      return true;
    };
    return navigator.locks ? navigator.locks.request("tsb-remote-seen", take) : Promise.resolve(take());
  };

  // Nothing sent to the webhooks carries real player names: I am "me", the other
  // humans are "bot1", "bot2", ... in player order. Replays are renamed the same way.
  const tagger = (mine) => (i) => {
    if (!Number.isInteger(i) || i < 0) return "";
    if (i === mine) return "me";
    return `bot${Number.isInteger(mine) && mine >= 0 && i > mine ? i : i + 1}`;
  };
  const norm = (s) => String(s ?? "").normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
  const allowList = () => String(ue.allow || "").split(/\r?\n/).map(norm).filter(Boolean);

  // In multiplayer games allow all games unless single-only build.
  function gate() {
    const d = dict(), g = read("game");
    if (!d || !g) return { ok: false, single: false, blocked: [], blockedIds: [] };
    const pixels = read("sbPixels"), now = Date.now(), c = state.gate;
    if (c && c.pixels === pixels && c.state === g[d.gameState] && now - c.at < 1e3) return c.result;
    let result;
    if (g[d.gIsSingleplayer]) result = { ok: true, single: true, blocked: [], blockedIds: [] };
    else if (SINGLE_ONLY) result = { ok: false, single: false, blocked: [], blockedIds: [] };
    else result = { ok: (g[d.gHumans] | 0) > 0, single: false, blocked: [], blockedIds: [] };
    state.gate = { pixels, allow: ue.allow, state: g[d.gameState], at: now, result };
    return result;
  }
  const allowed = () => !ue.manual || (!!ue.armed && gate().ok);
  const options = () => {
    const ok = allowed();
    return { spawn: !!ue.spawn && ok, play: !!ue.play && ok };
  };

  // webhook.site, or the relay with its API (tsb/relay): commands and results are posted to
  // <origin>/<uuid> and listed at <origin>/token/<uuid>/requests. A bare uuid is a webhook.site
  // address; any address with a uuid in it (the webhook.site page's #!/view/ link too) is read so.
  function hook(raw) {
    raw = String(raw || "").trim();
    const m = UUID.exec(raw);
    if (m && raw === m[0]) return { origin: "https://webhook.site", id: m[0].toLowerCase() };
    let u;
    try {
      u = new URL(raw);
    } catch {
      return null;
    }
    if (!/^https?:$/.test(u.protocol)) return null;
    return { origin: /^(www\.)?webhook\.site$/i.test(u.hostname) ? "https://webhook.site" : u.origin, id: m && m[0].toLowerCase(), raw };
  }
  function pollUrl() {
    const h = hook(ue.cmdUrl);
    return h ? h.id ? `${h.origin}/token/${h.id}/requests?sorting=newest&per_page=20` : h.raw : null;
  }
  function postUrl() {
    const h = hook(ue.resultUrl);
    return h ? h.id ? `${h.origin}/${h.id}` : h.raw : null;
  }
  function configure(force = false) {
    const url = ue.manual ? pollUrl() : null,
      ms = Math.max(1e3, Number(ue.pollMs) || 3e3),
      key = url ? `${url} ${ms}` : "";
    if (!force && key === state.configured) return;
    state.configured = key, url || (state.poll = null);
    be("tsb-remote", JSON.stringify({ kind: "poll", url, ms }));
  }
  function post(body, tag) {
    const url = postUrl();
    url && be("tsb-remote", JSON.stringify({ kind: "post", url, tag, body: JSON.stringify({ ...body, ext: VERSION, at: new Date().toISOString() }) }));
  }

  function bytes64(s) {
    s = s.trim().replace(/-/g, "+").replace(/_/g, "/").replace(/=+$/, "");
    const bin = atob(s + "===".slice((s.length + 3) % 4));
    return Uint8Array.from(bin, (ch) => ch.charCodeAt(0));
  }
  async function verify(key, payload, sig) {
    let b;
    try {
      b = bytes64(sig);
    } catch {
      return false;
    }
    const k = await crypto.subtle.importKey("raw", encoder.encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
    return crypto.subtle.verify("HMAC", k, b, encoder.encode(payload));
  }

  const modeOf = (d, g) => g[d.gIsReplay] ? "replay" : g[d.gIsSingleplayer] ? "single" : g[d.gIsTeamGame] ? "team" : "multi";
  function snapshot() {
    const d = dict(), g = read("game"),
      s = { manual: !!ue.manual, armed: !!ue.armed, stay: !!ue.stay, strategy: ue.strategy, phase: de.phase, loop: state.loop, replays: !!(d && d.replayData), inGame: false };
    SINGLE_ONLY || (s.lobby = lobbyInfo(d));
    s.recover = recoverInfo(d);
    if (!d || !g) return s;
    const gs = g[d.gameState];
    if (s.inGame = 1 === gs || 2 === gs) {
      const gt = gate(), info = state.info;
      Object.assign(s, { mode: modeOf(d, g), over: 2 === gs, alive: !!(info && info.alive), allowed: gt.ok, blocked: gt.blockedIds.map(tagger(g[d.playerId])) });
    }
    return s;
  }
  function lobbyInfo(d) {
    const o = { patched: lobbyPatched(), inLobby: inLobby() };
    if (o.inLobby) {
      const sel = lobby.sel, r = lobby.rooms && lobby.rooms[sel[0]];
      o.room = sel[0], o.ready = !!sel[3];
      r && d.lobbyRoomMode && (o.mode = r[d.lobbyRoomMode]);
      r && d.lobbyRoomTimeLeft && (o.startsIn = r[d.lobbyRoomTimeLeft]);
    }
    lobby.error && (o.error = lobby.error);
    lobby.stopped && (o.stopped = lobby.stopped);
    return o;
  }
  function recoverInfo(d) {
    const now = Date.now();
    return {
      patched: !!(d && d.closeCodes),
      idle: Math.round((now - rw.progressAt) / 1e3),
      codes: rw.codes.slice(-3),
      inRow: rec.inRow,
      lastHour: rec.reloads.filter((t) => now - t < 36e5).length,
      last: rec.last
    };
  }
  function disarm() {
    ue.armed = !1, fe(), state.loop = null;
    try {
      me.ctl.abandon();
    } catch {}
    inLobby() && lobby.sel[3] && press("Escape");
  }
  function leave() {
    const d = dict(), g = read("game");
    if (!d || !g || !d.sbLeave || 0 === g[d.gameState]) return !1;
    return g[d.sbLeave](!0), !0;
  }
  function startSingle() {
    const bot = we();
    return !!(dict() && bot.canStartGames() && bot.startGame());
  }

  // The multiplayer lobby (A build). The game calls hooks.lobbyInit on every
  // join and hooks.lobbyTick on every lobby update (about twice a second).
  const sb = () => window.__fx && window.__fx.strategyBot || null;
  function lobbyPatched() {
    const d = dict(), b = sb();
    return !SINGLE_ONLY && !!(d && d.lobbySelection && b && "function" == typeof b.openMultiplayer);
  }
  function inLobby() {
    const d = dict(), g = read("game");
    return !!(d && g && 0 === g[d.gameState] && lobby.sel && Date.now() - lobby.tickAt < 3e3);
  }
  // the game reads keys on document keyup; in the lobby Enter toggles Ready, Escape un-readies or presses Close
  function press(code) {
    document.dispatchEvent(new KeyboardEvent("keyup", { code, key: code, bubbles: !0, cancelable: !0 }));
  }
  // the battle royale or team room as far as the last lobby update tells
  function pickRoom(d, defRoom, wantModes) {
    const rooms = lobby.rooms;
    if (!d.lobbyRoomMode || !rooms || !rooms.length) return defRoom;
    const modes = Array.from(rooms, (r) => r ? r[d.lobbyRoomMode] : null);
    if (wantModes.includes(modes[defRoom])) return defRoom;
    const i = modes.findIndex((m) => wantModes.includes(m));
    return i < 0 ? defRoom : i;
  }
  function brRoom(d) {
    return pickRoom(d, BR_ROOM, BR_MODES);
  }
  function teamRoom(d) {
    return pickRoom(d, TEAM_ROOM, TEAM_MODES);
  }
  const isMpLoop = (l = state.loop) => "mp" === l || "team" === l;
  const wantRoom = (d) => "team" === state.loop ? teamRoom(d) : brRoom(d);
  function lobbyRoom(room) {
    const b = sb();
    try {
      b && "function" == typeof b.lobbyRoom && b.lobbyRoom(room);
    } catch {}
  }
  function openLobby(room) {
    lobby.openAt = Date.now(), lobby.opens++;
    try {
      return sb().openMultiplayer(room), !0;
    } catch (err) {
      return lobby.error = `点「多人」出错：${String(err && err.message || err)}`, !1;
    }
  }
  function closeLobby(room = -1) {
    if (!inLobby()) return !1;
    lobby.closing = { room, presses: 0, pressAt: 0 };
    closeStep(Date.now());
    return !0;
  }
  // Escape until the lobby updates stop; a second Escape right away when the first one only un-readied
  function closeStep(now) {
    const c = lobby.closing;
    if (!inLobby()) {
      lobby.closing = null;
      ue.armed && isMpLoop() && c.room >= 0 && openLobby(c.room);
      return;
    }
    if (c.pressAt && (now - c.pressAt < 1500 || lobby.tickAt < c.pressAt + 1e3)) return;
    if (c.presses >= 4) return void(lobby.closing = null, lobby.error = "关不掉大厅（按了 4 次 Esc）");
    const ready = !!lobby.sel[3];
    c.presses++, c.pressAt = now, press("Escape");
    ready && !lobby.sel[3] && (c.presses++, press("Escape"));
  }
  function stopLoop(reason) {
    state.loop = null, lobby.stopped = reason;
  }
  function startMulti(mode = "mp") {
    const d = dict(), g = read("game"), now = Date.now();
    Object.assign(lobby, { opens: 0, reopens: 0, presses: 0, pressAt: 0, leftAt: 0, openAt: 0, closing: null, error: null, stopped: null });
    state.loop = mode;
    if (!d || !g) return "waiting for the game";
    const gs = g[d.gameState], room = wantRoom(d);
    if (1 === gs || 2 === gs) {
      const single = !!g[d.gIsSingleplayer];
      lobbyRoom(room);
      return leave() ? (lobby.leftAt = single ? 0 : now, "leaving the game") : "in a game";
    }
    if (inLobby()) return "in the lobby";
    return openLobby(room) ? "opening the lobby" : lobby.error;
  }
  function readyStep(d, now) {
    const sel = lobby.sel, want = wantRoom(d);
    if (sel[0] !== want) {
      if (lobby.reopens >= 3) return void stopLoop(`大厅总进错房间（在 ${sel[0]} 号，要 ${want} 号）`);
      return lobby.reopens++, lobbyRoom(want), void closeLobby(want);
    }
    const follow = followLeaderStatus(d, want);
    if (follow && !follow.ready) {
      if (sel[3] && (!lobby.pressAt || now - lobby.pressAt >= 1200)) {
        lobby.pressAt = now, press("Escape");
      }
      return;
    }
    if (sel[3]) return void(lobby.presses = 0, lobby.error = null);
    if (now - lobby.initAt < 1e3 || now - lobby.pressAt < (lobby.presses >= 5 ? 1e4 : 1500)) return;
    lobby.pressAt = now, press("Enter");
    lobby.sel[3] ? (lobby.presses = 0, lobby.error = null) : ++lobby.presses >= 5 && (lobby.error = `点 Ready 没反应（试了 ${lobby.presses} 次）`);
  }
  function parseClanTag(name) {
    const s = String(name || "");
    const i = s.indexOf("["), j = s.indexOf("]");
    return i >= 0 && j - i > 1 && j - i <= 8 ? s.slice(i + 1, j).toUpperCase().trim() : null;
  }
  function followLeaderStatus(d, room) {
    const leaderKey = String(window.__tsbFollowLeader ?? "").trim().toLowerCase();
    const waitLeader = !!window.__tsbWaitForLeader;
    if (!leaderKey && !waitLeader) return null;
    const mgr = lobby.mgr || (d && d.lobbyManager && window[d.lobbyManager]);
    if (!mgr) return waitLeader ? { found: false, ready: false } : null;
    let vh = null, vi = null;
    for (const v of Object.values(mgr)) {
      if (v && "object" == typeof v) {
        if (d.lobbyPlayers && Array.isArray(v[d.lobbyPlayers])) {
          vh = v[d.lobbyPlayers], vi = v[d.lobbyReadyCounts];
          break;
        }
        const vals = Object.values(v);
        const arr4 = vals.find((x) => Array.isArray(x) && 4 === x.length && Array.isArray(x[0]));
        const cnt4 = vals.find((x) => Array.isArray(x) && 4 === x.length && "number" == typeof x[0]);
        if (arr4 && cnt4) {
          vh = arr4, vi = cnt4;
          break;
        }
      }
    }
    const rooms = (mgr && d.lobbyRooms && mgr[d.lobbyRooms]) || mgr?.z?.tO || mgr?.tO;
    const roomObj = rooms && rooms[room];
    const list = (vh && Array.isArray(vh[room]) && vh[room].length > 0 ? vh[room] : null) || (roomObj && Array.isArray(roomObj.tP) ? roomObj.tP : null);
    if (!list) return waitLeader ? { found: false, ready: false } : null;
    const readyCount = vi && "number" == typeof vi[room] ? (vi[room] | 0) : (roomObj && "number" == typeof roomObj.tQ ? (roomObj.tQ | 0) : list.length);
    const myClan = parseClanTag(window.__tsbPlayerName || "");
    const targetKey = leaderKey || "npl";
    for (let idx = 0; idx < list.length; idx++) {
      const p = list[idx];
      const raw = String((p && (p.aFN || p.username || p.name)) || "");
      const low = raw.toLowerCase();
      if (
        low.includes("mishi") || low.includes("matzz") || low.includes("kiholma") ||
        low.includes("leo_99") || low.includes("racoon") || low.includes("zexos") ||
        low.includes("talon") || low.includes("vortex") || low.includes("kronos") || low.includes("nexus") ||
        low.includes("777") || low.includes("sayo") || low.includes("kaito") ||
        low.includes("riku") || low.includes("_alex") || low.includes("tomo") ||
        low.includes("zero_2") || low.includes("sora")
      ) {
        continue;
      }
      const clan = parseClanTag(raw);
      const stripped = raw.replace(/\[[^\]]*\]/g, "").trim().toLowerCase();
      if ((stripped === targetKey || stripped.includes(targetKey) || low === "[npl]npl") && (!myClan || !clan || clan === myClan)) {
        return { found: true, ready: idx < readyCount || !!(p && p.ready), name: raw };
      }
    }
    return waitLeader ? { found: false, ready: false } : null;
  }
  // after I die or the game ends: leave, then the loop starts the next game
  function exitStep(d, g, now) {
    const r = state.game;
    if (!r || !r.exitAt || now < r.exitAt) return;
    r.exitAt = 0;
    if (!ue.armed) return;
    state.loop && !(r.gate && r.gate.ok) && stopLoop(`上一局有不在白名单里的真人，停止自动${isMpLoop() ? "排队" : "开局"}`);
    if ("single" === state.loop) return void(state.startAt = now, startSingle());
    const single = !!g[d.gIsSingleplayer], mp = isMpLoop();
    mp && lobbyRoom(wantRoom(d));
    leave() && mp && (lobby.leftAt = single ? 0 : now, lobby.opens = 0);
  }
  function step() {
    const d = dict(), g = read("game");
    if (!ue.manual || !d || !g) return;
    const gs = g[d.gameState], now = Date.now();
    if (1 === gs || 2 === gs) return lobby.closing = null, void exitStep(d, g, now);
    if (lobby.closing) return void closeStep(now);
    if (now < state.resumeAt) return;
    if (state.openOnce) return state.openOnce = !1, void(inLobby() || !lobbyPatched() || openLobby(wantRoom(d)));
    if (!ue.armed || !state.loop) return;
    if ("single" === state.loop) return void(inLobby() ? closeLobby() : now - state.startAt >= 5e3 && (state.startAt = now, startSingle()));
    if (inLobby()) return void readyStep(d, now);
    // leaving a multiplayer game rejoins the lobby by itself
    if (window.__tsbSquadSyncHold || now - lobby.leftAt < 1e4 || now - lobby.openAt < 15e3) return;
    // the server asked to wait ("Please try again later!", "Player already in lobby"); the watchdog reloads afterwards
    const c = rw.code;
    if (c && WAIT_MS[c.code] && now - c.at < WAIT_MS[c.code]) return;
    // with the close hook in, the watchdog reloads a page that does not get into the lobby
    if (lobby.opens >= 5) return void(d.closeCodes || stopLoop(`进不了大厅（试了 ${lobby.opens} 次）`));
    openLobby(wantRoom(d));
  }
  const hooks = {
    lobbyInit(sel, rooms) {
      const now = Date.now();
      Object.assign(lobby, { sel, rooms, initAt: now, tickAt: now, opens: 0, presses: 0, pressAt: 0 });
    },
    lobbyTick(mgr) {
      mgr && (lobby.mgr = mgr);
      lobby.tickAt = Date.now();
    },
    // the game calls this for every connection it sees closing, with the close code
    closed(sock, code) {
      const c = rw.code = { code: Number(code) | 0, sock: Number(sock) | 0, at: Date.now() };
      rw.codes.push(c.code), rw.codes.length > 8 && rw.codes.shift();
      STOP_CODES.includes(c.code) && setTimeout(() => ue.manual && ue.armed && giveUp(`服务器断开连接 [${c.code}] ${codeText(c.code)}`, c.code), 0);
    },
    // the game calls this when it leaves a game, with the replay text its Replay window shows
    replay(text) {
      try {
        sendReplay(text);
      } catch (err) {
        console.warn("strategyBot remote: replay report failed", err);
      }
    }
  };
  // Replay texts (replay version 25) are 6-bit characters, read as bits MSB first:
  // version 12, hash 12, size 31 (bytes), the game settings, the actions, the tick
  // runs. The settings hold the humans' usernames in player order (10-bit count,
  // each a 5-bit length and 16-bit characters; selectedPlayer is me) and their
  // account ids (10-bit count, 30 bits each), which only the player list shows.
  const REPLAY_VERSION = 25;
  const REPLAY_CHARS = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz";
  const REPLAY_CODES = new Int8Array(128).fill(-1);
  for (let i = 0; i < 64; i++) REPLAY_CODES[REPLAY_CHARS.charCodeAt(i)] = i;
  // bits after an action's 4-bit kind and 9-bit player, by kind
  const ACTION_BITS = [22, 20, 19, 37, 26, 10, 10, 1, 0, 0, 42, 0, 0, 0, 0, 0];
  const bitAt = (b, i) => (b[i >> 3] >> (7 - (7 & i))) & 1;
  function putBits(b, at, n, v) {
    for (let i = n - 1; i >= 0; i--, at++) (v >>> i) & 1 ? b[at >> 3] |= 128 >> (7 & at) : b[at >> 3] &= ~(128 >> (7 & at));
  }
  function replayBits(text) {
    const b = new Uint8Array(Math.ceil(6 * text.length / 8));
    for (let i = 0; i < text.length; i++) {
      const c = text.charCodeAt(i), v = c < 128 ? REPLAY_CODES[c] : -1;
      if (v < 0) throw new Error(`character ${i} is not a replay character`);
      putBits(b, 6 * i, 6, v);
    }
    return b;
  }
  function replayText(b, chars) {
    const s = [];
    for (let i = 0, at = 0; i < chars; i++) {
      let v = 0;
      for (let k = 0; k < 6; k++, at++) v = (v << 1) | bitAt(b, at);
      s.push(REPLAY_CHARS[v]);
    }
    return s.join("");
  }
  function replayHash(b, version) {
    let h = version;
    for (let i = 3; i < b.length; i++) h = (h + b[i]) & 4095;
    return h;
  }
  // the same reads and checks as the game's replay loader
  function readReplay(b) {
    const bits = 8 * b.length;
    let at = 0;
    const read = (n) => {
      let v = 0;
      for (let i = 0; i < n; i++, at++) v = 2 * v + (at < bits ? bitAt(b, at) : 0);
      return v;
    };
    const skip = (n) => void (at += n);
    const list = (count, size) => skip(read(count) * size);
    const text = (len) => {
      let s = "";
      for (let n = read(len); n > 0; n--) s += String.fromCharCode(read(16));
      return s;
    };
    if (b.length < 10) throw new Error("too short");
    const version = read(12), hash = read(12), size = read(31);
    if (version !== REPLAY_VERSION) throw new Error(`replay version ${version}, this build reads ${REPLAY_VERSION}`);
    if (size !== b.length) throw new Error(`stated size ${size}, actual ${b.length}`);
    if (hash !== replayHash(b, version)) throw new Error("hash mismatch");
    const mapType = read(2);
    skip(8 + 8 + 14), text(5); // map indexes, map seed, map name
    if (2 === mapType) {
      const n = read(30);
      if (6 * n > bits - at) throw new Error("map image runs past the end");
      skip(6 * n);
    }
    skip(1 + 1 + 10); // passable water, passable mountains, player count
    const humans = read(10), mine = read(9);
    skip(1 + 2 + 2 + 4 + 1 + 1 + 1), list(2, 14); // game mode, player mode, battle royale mode, teams, zombies, contest, is replay; elo
    skip(1 + 1), list(10, 18); // colors
    skip(1), list(4, 10); // selectable color, team player counts
    skip(1 + 2 + 4), list(4, 4), list(10, 4); // bot difficulty
    skip(2 + 14), list(11, 12); // spawning
    skip(1 + 2); // selectable spawn, player names type
    const names = { at, list: [] };
    for (let n = read(10); n > 0; n--) names.list.push(text(5));
    names.end = at;
    skip(1); // selectable name
    for (const v of [8, 8, 8, 11]) skip(2 + v), list(10, v); // incomes, starting resources
    const ids = { at };
    list(10, 30);
    ids.end = at;
    const width = read(5), actions = read(30), runs = read(30);
    if (actions + runs > bits) throw new Error("corrupted action counts");
    for (let i = 0; i < actions && at <= bits; i++) skip(9 + ACTION_BITS[read(4)]);
    skip(runs * (1 + width));
    if (at < bits - 13 || at > bits) throw new Error(`data ends at bit ${at} of ${bits}`);
    return { version, humans, mine, names, ids, end: at };
  }
  // renames the humans the way the reports tag them and drops their account ids;
  // every other bit is copied, then the result is read back and compared
  function anonymizeReplay(raw) {
    const cut = raw.indexOf("="), src = replayBits(raw.slice(cut + 1).trim()), r = readReplay(src), tag = tagger(r.mine);
    const names = r.names.list.length ? Array.from({ length: r.humans }, (_, i) => tag(i)).concat(r.names.list.slice(r.humans)) : [];
    // the game repeats the last name for every player past the list, so the list never ends in repeats
    while (names.length > 1 && names[names.length - 2] === names[names.length - 1]) names.pop();
    const namesBits = names.reduce((n, s) => n + 5 + 16 * s.length, 10),
      total = r.names.at + namesBits + (r.ids.at - r.names.end) + 10 + (r.end - r.ids.end),
      chars = Math.ceil(total / 6),
      out = new Uint8Array(Math.ceil(6 * chars / 8));
    let at = 0;
    const copy = (from, to) => {
      for (let i = from; i < to; i++, at++) bitAt(src, i) && (out[at >> 3] |= 128 >> (7 & at));
    };
    const put = (n, v) => void (putBits(out, at, n, v), at += n);
    copy(0, r.names.at);
    put(10, names.length);
    for (const s of names) {
      put(5, s.length);
      for (let i = 0; i < s.length; i++) put(16, s.charCodeAt(i));
    }
    copy(r.names.end, r.ids.at);
    put(10, 0);
    copy(r.ids.end, r.end);
    putBits(out, 24, 31, out.length);
    putBits(out, 12, 12, replayHash(out, r.version));
    const text = replayText(out, chars), back = replayBits(text), c = readReplay(back);
    const same = (from, to, at2) => {
      for (let i = from; i < to; i++, at2++) if (bitAt(src, i) !== bitAt(back, at2)) return !1;
      return !0;
    };
    if (c.humans !== r.humans || c.mine !== r.mine || c.names.list.length !== names.length || c.names.list.some((s, i) => s !== names[i]) || c.ids.end - c.ids.at !== 10 ||
      c.end - c.ids.end !== r.end - r.ids.end || !same(55, r.names.at, 55) || !same(r.names.end, r.ids.at, c.names.end) || !same(r.ids.end, r.end, c.ids.end)) throw new Error("the rewritten replay does not read back the same");
    return { text: raw.slice(0, cut + 1) + text, humans: r.humans };
  }
  // one replay per reported game, with the game id of its result; renamed after the game is left,
  // and withheld when renaming fails
  function sendReplay(text) {
    const d = dict(), g = read("game"), r = state.game;
    if (!ue.manual || !d || !g || g[d.gIsReplay] || !r || r.replaySent || "string" != typeof text || !text) return;
    r.replaySent = !0;
    const head = { type: "replay", game: r.id, mode: r.meta ? r.meta.mode : modeOf(d, g) };
    setTimeout(() => {
      let out;
      try {
        out = anonymizeReplay(text);
      } catch (err) {
        return void post({ ...head, length: text.length, error: `names not replaced, replay withheld: ${String(err && err.message || err)}` }, "replay");
      }
      post({ ...head, length: out.text.length, renamed: out.humans, ...(out.text.length > REPLAY_MAX ? { skipped: "too long" } : { replay: out.text }) }, "replay");
    }, 0);
  }

  async function run(c) {
    switch (c.cmd) {
      case "ping":
        return { ok: !0, state: snapshot() };
      case "start": {
        const mp = !!c.mp, team = !!c.team, single = !!c.single;
        if ((mp ? 1 : 0) + (team ? 1 : 0) + (single ? 1 : 0) > 1) return { ok: !1, error: "--mp, --team and --single do not go together", state: snapshot() };
        if ((mp || team) && !lobbyPatched()) return { ok: !1, error: SINGLE_ONLY ? "this build only plays singleplayer games, it has no --mp/--team" : "the multiplayer lobby is not patched (see the browser console), --mp/--team is off", state: snapshot() };
        if ("string" == typeof c.clan && c.clan.trim()) window.__tsbPlayerName = c.clan.trim();
        if (Number.isInteger(c.color)) window.__tsbPlayerColor = c.color;
        if ("string" == typeof c.follow) window.__tsbFollowLeader = c.follow.trim();
        if ("boolean" == typeof c.waitLeader) window.__tsbWaitForLeader = c.waitLeader;
        if ("string" == typeof c.strategy && c.strategy.trim()) {
          const name = String(c.name || "remote").replace(/[^\w.-]+/g, "_").slice(0, 40) || "remote";
          await Te.add({ name: `${name}.js`, text: async () => c.strategy });
        } else if ("string" == typeof c.use && c.use) {
          if (!Te.list().some(([id]) => id === c.use)) return { ok: !1, error: `no strategy "${c.use}"`, state: snapshot() };
          ue.strategy = c.use, fe(), Te.changed(c.use);
        }
        "boolean" == typeof c.stay && (ue.stay = c.stay);
        syncBackend();
        ue.armed = !0, fe(), rec.inRow = 0, saveRecover(), rw.progressAt = Date.now();
        if (mp || team) {
          const action = startMulti(team ? "team" : "mp");
          return { ok: !0, started: !1, action, state: snapshot() };
        }
        if (!single) return { ok: !0, started: !1, state: snapshot() };
        state.loop = "single", state.startAt = Date.now();
        const started = inLobby() ? (closeLobby(), !1) : startSingle();
        return { ok: !0, started, state: snapshot() };
      }
      case "stop":
        return disarm(), { ok: !0, state: snapshot() };
      case "end": {
        disarm();
        const left = leave() || closeLobby();
        return { ok: !0, left, state: snapshot() };
      }
      // reload the page; a loop goes on afterwards, without one the A build opens the battle royale lobby
      case "lobby": {
        if (rw.pending) return { ok: !1, error: "already reloading", state: snapshot() };
        const loop = ue.armed ? state.loop : null;
        reloadPage("远程 lobby 指令", null, !0);
        return { ok: !0, reloading: !0, resume: loop || (SINGLE_ONLY ? null : "lobby"), state: snapshot() };
      }
    }
    return { ok: !1, error: `unknown cmd "${c.cmd}"` };
  }
  async function handle(content) {
    let env;
    try {
      env = JSON.parse(content);
    } catch {
      return { ok: !1, error: "body is not JSON" };
    }
    if (!env || "string" != typeof env.p || "string" != typeof env.sig) return { ok: !1, error: 'unsigned: the body must be {"p": "<command JSON>", "sig": "<HMAC>"}' };
    if (!ue.key) return { ok: !1, error: "no key in the panel" };
    if (!(await verify(String(ue.key), env.p, env.sig))) return { ok: !1, error: "bad signature" };
    let c;
    try {
      c = JSON.parse(env.p);
    } catch {
      return { ok: !1, error: "p is not JSON" };
    }
    if (!c || "object" != typeof c) return { ok: !1, error: "p is not an object" };
    const base = { cmd: c.cmd ?? null, seq: c.seq ?? null }, now = Date.now(), ts = Number(c.ts);
    if (!Number.isFinite(ts) || now - ts > WINDOW_MS || ts - now > AHEAD_MS) return { ...base, ok: !1, error: `ts is outside the 10-minute window (browser clock ${new Date(now).toISOString()})` };
    if ("string" != typeof c.nonce || !c.nonce || c.nonce.length > 100) return { ...base, ok: !1, error: "missing nonce" };
    if (!(await claim([`n:${c.nonce}`]))) return { ...base, ok: !1, error: "nonce already used" };
    return { ...base, ...(await run(c)) };
  }
  async function pump() {
    if (state.busy || "waiting" === de.phase) return;
    if (!ue.manual) return void(state.queue.length = 0);
    state.busy = !0;
    try {
      for (; state.queue.length;) {
        const m = state.queue.shift();
        if (!m || "string" != typeof m.id) continue;
        const at = Date.parse(String(m.at || "").replace(" ", "T") + "Z");
        if (at && Date.now() - at > WINDOW_MS + AHEAD_MS) continue;
        if (!(await claim([`id:${m.id}`]))) continue;
        let res;
        try {
          res = await handle(String(m.content ?? ""));
        } catch (err) {
          res = { ok: !1, error: String(err && err.message || err) };
        }
        state.last = { cmd: res.cmd ?? null, ok: !!res.ok, error: res.error || null, at: Date.now() };
        post({ type: "ack", id: m.id, ...res }, "ack");
      }
    } finally {
      state.busy = !1;
    }
  }

  function teams(d, g) {
    if (!g[d.gIsTeamGame] || !d.sbTeams || !d.sbTeamHolder) return null;
    const holder = window[d.sbTeamHolder], t = holder && holder[d.sbTeams], pd = read("playerData"), terr = pd && pd[d.playerTerritories];
    if (!t || !terr) return null;
    const totals = {};
    for (let i = 0, n = Math.min(t.length, terr.length); i < n; i++) terr[i] > 0 && (totals[t[i]] = (totals[t[i]] || 0) + terr[i]);
    let best = null;
    for (const k of Object.keys(totals)) (null === best || totals[k] > totals[best]) && (best = k);
    return { mine: t[g[d.playerId]], best: null === best ? null : Number(best), totals };
  }
  function meta(d, g) {
    const mine = g[d.playerId], humans = g[d.gHumans] | 0, tag = tagger(mine);
    return { mode: modeOf(d, g), id: mine, name: tag(mine), humans: Array.from({ length: humans }, (_, i) => tag(i)), players: g[d.gMaxPlayers] | 0 };
  }
  // one report per game: when I die, else when the game ends, else when it is left
  // (why: "reload" when the extension reloads the page in the middle of it)
  function report(r, event, why) {
    r.done = !0;
    const d = dict(), g = read("game"), info = r.info, last = r.lastAlive || info, m = r.meta,
      team = "left" === event ? null : teams(d, g), gt = r.gate || { ok: !1, blocked: [], blockedIds: [] };
    let result = "left";
    "died" === event ? result = "lost" : "end" === event && (result = team ? team.best === team.mine ? "won" : info.alive ? "over" : "lost" : info.alive ? info.leader === m.id ? "won" : "over" : "lost");
    post({
      type: "result",
      event,
      result,
      game: r.id,
      mode: m.mode,
      me: { id: m.id, name: m.name },
      humans: m.humans,
      players: m.players,
      tick: info.tick | 0,
      time: ie(info.tick | 0),
      seconds: Math.round((Date.now() - r.t0) / 1e3),
      alive: !!info.alive,
      place: "died" === event ? (info.players | 0) + 1 : info.rank | 0,
      alivePlayers: info.players | 0,
      territory: info.territory | 0,
      lastTerritory: last.territory | 0,
      lastRank: last.rank | 0,
      peak: r.peak,
      land: info.land | 0,
      balance: last.balance | 0,
      sent: info.sent | 0,
      accepted: info.accepted | 0,
      strategy: ue.strategy,
      armed: !!ue.armed,
      loop: state.loop,
      // what happens 3 s after a death or the end: leave, then queue again / a new singleplayer game / stop the loop
      next: "left" === event || !ue.armed ? null : !state.loop ? "leave" : gt.ok ? isMpLoop() ? "queue" : "single" : "stop",
      // after a death: true when the bot stays until the game is over and does "next" then
      stay: !!ue.stay,
      allowed: gt.ok,
      blocked: gt.blockedIds.map(tagger(m.id)),
      ...(team ? { team } : {}),
      ...(why ? { why } : {})
    }, "result");
  }
  function track(info) {
    const d = dict(), g = read("game");
    if (!ue.manual || !d || !g) return void(state.game = null);
    const gs = g[d.gameState], pixels = read("sbPixels"), now = Date.now();
    let r = state.game;
    r && (0 === gs || pixels !== r.pixels) && (r.done || !r.info || report(r, "left"), r = state.game = null);
    if (1 !== gs && 2 !== gs || g[d.gIsReplay]) return;
    // dead with "stay" on: leave once the game is over, the option is turned off, or after STAY_MAX_MS
    if (r && r.stayAt) return void((2 === gs || !ue.stay || now - r.stayAt >= STAY_MAX_MS) && (r.stayAt = 0, ue.armed && (r.exitAt = now + EXIT_MS)));
    if (!info) return;
    if (!r) {
      if (2 === gs) return;
      r = state.game = { pixels, id: `${now.toString(36)}-${Math.floor(1e9 * Math.random()).toString(36)}`, t0: now, done: !1, info: null, lastAlive: null, wasAlive: !1, peak: 0, exitAt: 0, stayAt: 0 };
    }
    if (r.done) return;
    r.info = info, r.meta = meta(d, g), r.gate = gate(), r.peak = Math.max(r.peak, info.territory | 0), info.alive && !info.spawnPhase && (r.wasAlive = !0, r.lastAlive = info);
    r.wasAlive && !info.alive && 1 === gs ? report(r, "died") : 2 === gs && report(r, "end");
    r.done && ue.armed && (ue.stay && 1 === gs ? r.stayAt = now : r.exitAt = now + EXIT_MS);
  }
  function frame(info) {
    state.info = info || null;
    try {
      track(info);
    } catch (err) {
      console.warn("strategyBot remote: result report failed", err);
    }
    try {
      step();
    } catch (err) {
      console.warn("strategyBot remote: lobby / next game step failed", err);
    }
  }

  const tickNow = (d) => {
    try {
      const h = read("sbTickHolder");
      return h && d.sbGetTick ? h[d.sbGetTick]() : null;
    } catch {
      return null;
    }
  };
  // Runs every second on its own timer, since a stuck game may stop calling frame().
  // A hidden tab freezes the game, so it only counts time while the tab is visible.
  function watch() {
    const now = Date.now(), d = dict(), g = read("game"), gs = d && g ? g[d.gameState] : -1, lob = inLobby();
    let mark = `m${gs}`;
    if (1 === gs || 2 === gs) {
      const tick = tickNow(d);
      // no tick to watch: never call a game stuck
      mark = null == tick ? `g${now}` : `g${gs}:${tick}`;
    } else if (lob) mark = `l${lobby.tickAt}`;
    // dropping out of a lobby or a game to the menu is no progress
    if (mark !== rw.mark && "m" !== (rw.mark = mark)[0]) {
      rw.progressAt = now;
      (lob || 1 === gs) && rec.inRow && (rec.inRow = 0, saveRecover());
    }
    if (rw.pending) return;
    // in a hidden tab too: nothing else brings in the new scripts
    if (false && ue.manual && (state.update || state.worker && state.worker.dead)) {
      const u = state.update || (state.update = { at: now, held: !1 });
      if (playing(d, g) && now - u.at < UPDATE_WAIT_MS) return;
      rec.reloads = rec.reloads.filter((t) => now - t < 36e5);
      (u.held = rec.reloads.length >= RELOADS_PER_HOUR) || reloadPage("插件已更新或停用，刷新页面换上新版本", null, !0, !0);
      return;
    }
    if (!ue.manual || !ue.armed || !state.loop || "visible" !== document.visibilityState) return void(rw.progressAt = now);
    const c = rw.code, after = c && c.at > rw.progressAt - 2e3 ? Math.max(c.at, rw.progressAt) : 0;
    if (now - (after || rw.progressAt) < (after ? WAIT_MS[c.code] || CLOSED_MS : STUCK_MS)) return;
    recover(after ? c.code : null, now - rw.progressAt);
  }
  function recover(code, idle) {
    const now = Date.now(), d = dict(), r = state.game,
      why = null === code ? `卡住 ${Math.round(idle / 1e3)} 秒没有动静` : `连接断开 [${code}] ${codeText(code)}`;
    if (!d) return giveUp(`${why}；游戏页面没加载出来（可能停在 Cloudflare 验证），不自动刷新`, code);
    if (!d.closeCodes) return giveUp(`${why}；断线钩子没装上，分不清是断线还是被游戏拦了，不自动刷新`, code);
    if (r && r.gate && !r.gate.ok) return giveUp(`${why}；这局有不在白名单里的真人，不自动刷新`, code);
    const shown = STOP_TEXT.exec(document.body && document.body.innerText || "");
    if (shown) return giveUp(`${why}；游戏提示「${shown[0]}」，不自动刷新`, code);
    if (rec.inRow >= RELOADS_IN_A_ROW) return giveUp(`${why}；连续自动刷新 ${rec.inRow} 次都没回到大厅或对局（可能要人工处理，比如 Cloudflare 验证）`, code);
    rec.reloads = rec.reloads.filter((t) => now - t < 36e5);
    if (rec.reloads.length >= RELOADS_PER_HOUR) return giveUp(`${why}；1 小时内已经自动刷新 ${rec.reloads.length} 次`, code);
    reloadPage(why, code, !1);
  }
  function giveUp(why, code = null) {
    const loop = state.loop;
    disarm(), lobby.stopped = why, rec.last = { action: "stop", why, code, at: Date.now() }, saveRecover();
    post({ type: "recover", action: "stop", why, code, text: null === code ? null : codeText(code), loop, codes: rw.codes.slice(), state: snapshot() }, "recover");
  }
  // a game the bot is still in: its result is not reported yet, or it stays to the end after dying
  function playing(d, g) {
    const r = state.game;
    return !!(d && g && 1 === g[d.gameState] && !g[d.gIsReplay] && !(r && r.done && !r.stayAt));
  }
  // also called by the service worker of the new version right after it is installed
  function updateReload() {
    state.update || (state.update = { at: Date.now(), held: !1 });
  }
  // update: a reload for an extension update, which keeps the loop but opens no lobby; it counts
  // toward the reloads per hour, not toward those in a row (reaching a lobby is up to the loop)
  function reloadPage(why, code, manual, update = !1) {
    const now = Date.now(), r = state.game, loop = ue.armed ? state.loop : null;
    r && !r.done && r.info && report(r, "left", "reload");
    rw.pending = !0;
    update ? rec.reloads.push(now) : manual ? rec.inRow = 0 : (rec.inRow++, rec.reloads.push(now));
    rec.resume = { loop, open: manual && !update && !loop, at: now, why };
    rec.last = { action: "reload", why, code, at: now };
    saveRecover();
    post({ type: "recover", action: "reload", why, code, text: null === code ? null : codeText(code), loop, manual, inRow: rec.inRow, lastHour: rec.reloads.length, codes: rw.codes.slice(), state: snapshot() }, "recover");
    // time for the report to reach the service worker
    setTimeout(() => location.reload(), 1500);
  }

  const clock = (t) => new Date(t).toTimeString().slice(0, 8);
  function sync() {
    state.box && (state.box.style.display = ue.manual ? "" : "none");
    state.armButton && (state.armButton.textContent = ue.armed ? "停手（本地）" : "接管（本地）");
    state.stayBox && (state.stayBox.checked = !!ue.stay);
  }
  function fields() {
    const css = ee("style");
    css.textContent = "\n#tsb-panel .tsb-remote { margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(255, 255, 255, 0.12); }\n#tsb-panel .tsb-remote label { display: block; padding: 2px 0 0; color: #9aa3ad; cursor: default; }\n#tsb-panel .tsb-remote input, #tsb-panel .tsb-remote textarea { display: block; box-sizing: border-box; width: 100%; margin: 1px 0 0;\n  padding: 2px 4px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 4px; background: rgba(0, 0, 0, 0.35); color: #e8e8e8;\n  font: inherit; cursor: text; user-select: text; -webkit-user-select: text; }\n#tsb-panel .tsb-remote textarea { height: 54px; resize: vertical; }\n#tsb-panel .tsb-remote .tsb-files { margin-top: 4px; }\n#tsb-panel .tsb-remote label.tsb-check { display: flex; align-items: center; gap: 7px; padding: 1px 0; color: inherit; cursor: pointer; }\n#tsb-panel .tsb-remote label.tsb-check input { display: inline-block; width: auto; margin: 0; padding: 0; cursor: pointer; }\n", document.head.appendChild(css);
    const box = state.box = ee("div", "tsb-remote"),
      field = (key, title, type) => {
        const label = ee("label", "", title), input = ee("area" === type ? "textarea" : "input");
        return "area" !== type && (input.type = type), input.value = String(ue[key] ?? ""), input.spellcheck = !1, input.autocomplete = "off", input.addEventListener("change", () => {
          ue[key] = input.value.trim(), fe(), configure();
        }), label.appendChild(input), label;
      },
      stay = ee("label", "tsb-check"),
      stayBox = state.stayBox = ee("input"),
      row = ee("div", "tsb-files"),
      arm = state.armButton = ee("button", "tsb-button"),
      back = ee("button", "tsb-button", SINGLE_ONLY ? "刷新游戏页" : "回大厅（刷新）");
    back.type = "button", back.title = "刷新游戏页；开着循环就接着循环", back.addEventListener("click", () => {
      back.blur(), rw.pending || reloadPage("面板按钮", null, !0);
    });
    stayBox.type = "checkbox", stayBox.addEventListener("change", () => {
      ue.stay = stayBox.checked, fe(), stayBox.blur();
    }), stay.append(stayBox, ee("span", "", "死了不退，留到整局结束"));
    return arm.type = "button", arm.addEventListener("click", () => {
      ue.armed ? disarm() : (ue.armed = !0, fe()), sync(), arm.blur();
    }), row.append(arm, back), box.append(stay), box.append(field("cmdUrl", "指令 webhook", "text"), field("resultUrl", "结果 webhook", "text"), field("key", "密钥", "password"), row), sync(), [box];
  }
  function loopText(s) {
    if ("single" === state.loop) return "单人：一局完了自动开下一局";
    if (!isMpLoop()) return lobby.stopped ? `已停：${ne(lobby.stopped, 40)}` : "";
    const tag = "team" === state.loop ? "组队" : "大逃杀";
    const l = s.lobby || {}, e = lobby.error ? `（${ne(lobby.error, 30)}）` : "";
    if (s.inGame) return `${tag}：对局中，完了回大厅再排`;
    if (lobby.closing) return `${tag}：换房间中…` + e;
    if (!l.inLobby) return `${tag}：正在进大厅…` + e;
    return (l.ready ? `${tag}：已 Ready${l.startsIn > 0 ? `，约 ${l.startsIn} 秒后开` : "，等开局"}` : `${tag}：在大厅，正在点 Ready`) + e;
  }
  // the service worker connects to the local backend only while the backend strategy is in use
  let backendPort;
  function syncBackend() {
    const want = "backend" === ue.strategy ? ue.port : null;
    want !== backendPort && (backendPort = want, be("tsb-control", JSON.stringify({ kind: "connect", port: want })));
  }
  function decorate(view) {
    sync(), configure(), syncBackend(), pump();
    const dead = !!(state.worker && state.worker.dead);
    if (!view) return view;
    if (!ue.manual) return dead ? { ...view, stats: [...view.stats, ["插件", "已更新或停用，请刷新页面"]] } : view;
    const s = snapshot(), names = s.inGame ? gate().blocked : [], rows = [];
    let text = view.text, tone = view.tone;
    "bad" !== tone && (ue.armed ? s.inGame && "replay" !== s.mode && !s.allowed && (text = SINGLE_ONLY ? "已接管，但远程版只在单人局里动，这局机器人不动。" : `已接管，但这局有不在白名单里的真人（${names.slice(0, 3).map((n) => ne(n, 12)).join("、")}${names.length > 3 ? ` 等 ${names.length} 人` : ""}），机器人不动。`, tone = "off") : (text = "手动模式：等远程 start 指令，机器人不动。", tone = "off"));
    "bad" !== tone && ue.armed && !s.inGame && isMpLoop() && (text = `已接管：${loopText(s)}`, tone = "wait");
    rows.push(["远程", ue.armed ? "已接管" : "待命"]);
    const lp = loopText(s);
    lp && rows.push(["循环", lp]);
    state.game && state.game.stayAt && rows.push(["这局", "死了，留到整局结束再退"]);
    const p = state.poll, u = state.update;
    rows.push(["指令", dead || u ? `插件已更新或停用，${rw.pending ? "正在刷新页面…" : u && u.held ? `1 小时内已自动刷新 ${RELOADS_PER_HOUR} 次，请手动刷新页面` : "等这局打完自动刷新"}`
      : pollUrl() ? p ? p.ok ? `正常 ${clock(p.at)}` : `失败：${ne(p.error || "?", 60)}` : "连接中…" : "没填指令地址"]);
    const l = state.last;
    l && rows.push(["上条指令", `${l.cmd || "?"} ${l.ok ? "✓" : `✗ ${ne(l.error || "", 40)}`} ${clock(l.at)}`]);
    const q = state.post;
    postUrl() ? q && !q.ok && rows.push(["上报", `失败：${ne(q.error || `HTTP ${q.status}`, 60)}${q.retry ? `，第 ${q.retry} 次重试` : ""}`])
      : rows.push(["上报", "没填结果地址，指令的回执发不出去"]);
    const r = rec.last;
    rw.pending ? rows.push(["恢复", "正在刷新页面…"]) : r && Date.now() - r.at < 36e5 && rows.push(["恢复", `${clock(r.at)} ${"stop" === r.action ? "停了" : "刷新"}：${ne(r.why, 40)}`]);
    return { ...view, text, tone, stats: [...view.stats, ...rows] };
  }

  document.addEventListener("tsb-remote-msg", (e) => {
    let list;
    try {
      list = JSON.parse(e.detail);
    } catch {
      return;
    }
    ue.manual && Array.isArray(list) && (state.queue.push(...list), pump());
  });
  document.addEventListener("tsb-remote-status", (e) => {
    let s;
    try {
      s = JSON.parse(e.detail);
    } catch {
      return;
    }
    const v = { ok: !!s.ok, error: s.error || null, at: Date.now() };
    "worker" === s.kind ? state.worker = { ...v, dead: !!s.dead }
      : "post" === s.kind ? state.post = { ...v, tag: s.tag || null, status: s.status || 0, retry: s.retry | 0 } : state.poll = v;
  });
  document.addEventListener("tsb-status", (e) => {
    let s;
    try {
      s = JSON.parse(e.detail);
    } catch {
      return;
    }
    "relay" === s.kind && configure(!0);
  });
  // after a reload by the extension the loop goes on ("armed" is a setting, so it is still on)
  {
    const now = Date.now(), r = rec.resume;
    rec.reloads = rec.reloads.filter((t) => now - t < 36e5), rec.resume = null, saveRecover();
    if (r && now - r.at < 3e5 && ue.manual) {
      state.resumeAt = now + 5e3;
      if (ue.armed && isMpLoop(r.loop) && !SINGLE_ONLY) state.loop = r.loop;
      else if (ue.armed && "single" === r.loop) state.loop = "single", state.startAt = now;
      else state.openOnce = !!r.open && !SINGLE_ONLY;
    }
  }
  setInterval(() => {
    try {
      watch();
    } catch (err) {
      console.warn("strategyBot remote: stuck page check failed", err);
    }
  }, 1e3);
  configure(!0);
  return { version: VERSION, state, lobby, rec, rw, hooks, options, allowed, gate, frame, watch, decorate, fields, configure, snapshot, handle, verify, updateReload };
})()
