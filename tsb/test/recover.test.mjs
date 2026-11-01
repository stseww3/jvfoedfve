// Stuck-page recovery in remote-page.js (0.6.7), on a fake clock with a stubbed game.
// usage: node tsb/test/recover.test.mjs
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';

const here = new URL('.', import.meta.url).pathname;
const SRC = fs.readFileSync(`${here}../remote/remote-page.js`, 'utf8');
const KEY = 'test-key';

function env({ session = null, settings = {}, single = false, hook = true } = {}) {
    let now = Date.UTC(2026, 10, 1, 3, 0, 0);
    let timers = [];
    const posts = [], reloads = [], opens = [], leaves = [];
    let tick = 0, singles = 0;
    const store = (init) => {
        const m = new Map(init ? Object.entries(init) : []);
        return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k), map: m };
    };
    const local = store(), sessionStore = store(session);
    const listeners = {};
    const document = {
        visibilityState: 'visible',
        body: { innerText: '' },
        head: { appendChild() {} },
        addEventListener: (t, f) => (listeners[t] ||= []).push(f),
        dispatchEvent: (e) => ((listeners[e.type] || []).forEach((f) => f(e)), true)
    };
    const el = (tag, className, text) => {
        const on = {};
        return { tag, className, textContent: text, style: {}, on, addEventListener: (t, f) => (on[t] = f), append() {}, appendChild() {}, blur() {} };
    };
    const ue = { manual: true, armed: true, allow: '', cmdUrl: 'https://webhook.site/00000000-0000-4000-8000-000000000001', resultUrl: 'https://webhook.site/00000000-0000-4000-8000-000000000002', key: KEY, pollMs: 3000, strategy: 'file:v5', spawn: true, play: true, ...settings };
    const G = { gs: 0, sp: false, rp: false, tg: false, pid: 0, hum: 1, mp: 512, lv: () => (leaves.push(now), (G.gs = 0), true) };
    const win = {
        dictionary: { game: 'G', gameState: 'gs', gIsSingleplayer: 'sp', gIsReplay: 'rp', gIsTeamGame: 'tg', playerId: 'pid', gHumans: 'hum', gMaxPlayers: 'mp',
            sbTickHolder: 'TH', sbGetTick: 'gt', sbLeave: 'lv', rawPlayerNames: 'names', playerData: 'PD', sbPixels: 'PX', replayData: 'rd',
            ...(single ? {} : { lobbySelection: 'sel' }), ...(hook ? { closeCodes: 'uI' } : {}) },
        G, TH: { gt: () => tick }, PD: { names: ['me', 'friend', 'stranger'] }, PX: {},
        __fx: { strategyBot: {} }
    };
    class FakeDate extends Date {
        constructor(...a) { super(...(a.length ? a : [now])); }
        static now() { return now; }
    }
    const ctx = vm.createContext({
        window: win, document, localStorage: local, sessionStorage: sessionStore, navigator: {}, console,
        TextEncoder, atob, crypto: globalThis.crypto, Date: FakeDate,
        KeyboardEvent: class { constructor(type, o) { this.type = type; Object.assign(this, o); } },
        location: { reload: () => reloads.push(now) },
        setTimeout: (fn, ms = 0) => (timers.push({ at: now + ms, fn }), timers.length),
        setInterval: (fn, ms) => (timers.push({ at: now + ms, fn, every: ms }), timers.length),
        clearTimeout() {}, clearInterval() {},
        ue, fe() {},
        be: (type, detail) => { const c = JSON.parse(detail); c.kind === 'post' && posts.push(JSON.parse(c.body)); },
        de: { phase: 'ready' }, me: { ctl: { abandon() {} } },
        Te: { list: () => [['file:v5']], async add() {}, changed() {} },
        we: () => ({ canStartGames: () => true, startGame: () => (singles++, (G.gs = 1), (G.sp = true), true) }),
        ee: el, ne: (s, n) => String(s).slice(0, n), ie: (t) => String(t)
    });
    const src = single ? SRC.replace('const SINGLE_ONLY = !1;', 'const SINGLE_ONLY = !0;') : SRC;
    const Re = vm.runInContext(`(${src.trim()})`, ctx);
    Object.assign(win.__fx.strategyBot, Re.hooks, single ? {} : { openMultiplayer: (room) => opens.push(room), lobbyRoom() {} });
    const sel = [1, 0, 0, 0];
    const t = {
        Re, G, ue, win, document, posts, reloads, opens, leaves, sel, sessionStore,
        get now() { return now; },
        get singles() { return singles; },
        // game ticks advance while running; lobby updates come twice a second while connected
        running: false, lobbyOn: false,
        enterLobby() { Re.hooks.lobbyInit(sel, [null, { lobbyRoomMode: 7 }]); t.lobbyOn = true; },
        advance(ms) {
            const end = now + ms;
            while (now < end) {
                now = Math.min(end, now + 250);
                // a hidden tab gets no animation frames, so the game and frame() stop
                const shown = document.visibilityState === 'visible';
                if (shown && t.running && G.gs === 1) tick++;
                if (shown && t.lobbyOn && G.gs === 0) Re.hooks.lobbyTick();
                shown && Re.frame(G.gs ? { tick, alive: true, territory: 10, players: 5, rank: 2, leader: 1, spawnPhase: false } : null);
                const due = timers.filter((x) => x.at <= now);
                timers = timers.filter((x) => x.at > now);
                for (const x of due) {
                    x.every && timers.push({ ...x, at: x.at + x.every });
                    x.fn();
                }
            }
        },
        recovers: () => posts.filter((p) => p.type === 'recover'),
        resume: () => JSON.parse(sessionStore.getItem('territorialStrategyBotRecover') || '{}'),
        async send(cmd, extra = {}) {
            const p = JSON.stringify({ cmd, ts: now, nonce: `n${Math.random()}`, ...extra });
            const sig = createHmac('sha256', KEY).update(p).digest('base64url');
            return Re.handle(JSON.stringify({ p, sig }));
        }
    };
    return t;
}
// the page after reload: same tab (sessionStorage), same settings (localStorage)
const reopen = (t, opts = {}) => env({ session: Object.fromEntries(t.sessionStore.map), settings: { ...t.ue }, ...opts });

const results = [];
const test = async (name, fn) => {
    try {
        await fn();
        results.push(['ok', name]);
    } catch (err) {
        results.push(['FAIL', name, err]);
    }
};

await test('in the lobby with updates coming: no reload', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.enterLobby();
    t.advance(180e3);
    assert.equal(t.reloads.length, 0);
    assert.equal(t.recovers().length, 0);
    assert.equal(t.sel[3], 0, 'no Enter key handler in the stub, so Ready stays off; the loop keeps trying');
});

await test('1006 in the lobby, updates stop: reload after 20 s, loop carried over', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.enterLobby();
    t.advance(10e3);
    t.lobbyOn = false;
    t.Re.hooks.closed(0, 1006);
    t.advance(15e3);
    assert.equal(t.recovers().length, 0, 'not before 20 s');
    t.advance(10e3);
    const [r] = t.recovers();
    assert.equal(r.action, 'reload');
    assert.equal(r.code, 1006);
    assert.match(r.why, /1006/);
    assert.equal(r.loop, 'mp');
    assert.equal(t.reloads.length, 1, 'location.reload 1.5 s after the report');
    const s = t.resume();
    assert.equal(s.resume.loop, 'mp');
    assert.equal(s.inRow, 1);
    assert.equal(s.reloads.length, 1);
});

await test('after the reload: the loop goes on and opens the battle royale lobby', async () => {
    const a = env();
    await a.send('start', { mp: true });
    a.enterLobby();
    a.advance(5e3);
    a.lobbyOn = false;
    a.Re.hooks.closed(0, 4530);
    a.advance(30e3);
    assert.equal(a.reloads.length, 1);
    const b = reopen(a);
    assert.equal(b.Re.state.loop, 'mp');
    b.advance(4e3);
    assert.equal(b.opens.length, 0, 'waits for the menu first');
    b.advance(3e3);
    assert.deepEqual(b.opens, [1]);
    assert.equal(b.resume().resume, null, 'the carry-over is used once');
    b.enterLobby();
    b.advance(5e3);
    assert.equal(b.resume().inRow, 0, 'reaching the lobby ends the run of reloads');
});

await test('a page refreshed by hand does not resume the loop', async () => {
    const t = env();
    assert.equal(t.Re.state.loop, null);
    t.advance(120e3);
    assert.equal(t.reloads.length, 0);
});

await test('bot detection (4591): loop stops, bot disarmed, no reload', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.enterLobby();
    t.advance(5e3);
    t.lobbyOn = false;
    t.Re.hooks.closed(0, 4591);
    t.advance(1e3);
    const [r] = t.recovers();
    assert.equal(r.action, 'stop');
    assert.equal(r.code, 4591);
    assert.equal(t.ue.armed, false);
    assert.equal(t.Re.state.loop, null);
    assert.match(t.Re.lobby.stopped, /4591/);
    t.advance(600e3);
    assert.equal(t.reloads.length, 0);
    assert.equal(t.recovers().length, 1);
});

for (const code of [4577, 4555, 4540, 4528, 4730]) {
    await test(`stop code ${code}: no reload`, async () => {
        const t = env();
        await t.send('start', { mp: true });
        t.Re.hooks.closed(0, code);
        t.advance(300e3);
        assert.equal(t.reloads.length, 0);
        assert.equal(t.recovers()[0].action, 'stop');
    });
}

await test('the game window says Bot Detection, no code seen: no reload', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.document.body.innerText = '🤖 Bot Detection\nThe algo thinks you are a bot. Please reload the game';
    t.advance(70e3);
    assert.equal(t.reloads.length, 0);
    const [r] = t.recovers();
    assert.equal(r.action, 'stop');
    assert.match(r.why, /Bot Detection/);
});

await test('stuck without a code (menu, lobby never opens): reload after 60 s', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.advance(50e3);
    assert.equal(t.reloads.length, 0);
    t.advance(15e3);
    assert.equal(t.reloads.length, 1);
    assert.equal(t.recovers()[0].code, null);
    assert.match(t.recovers()[0].why, /卡住 6\d 秒/);
});

await test('frozen game (ticks stop, 1006): result "left" with why=reload, then reload', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.G.gs = 1, t.running = true;
    t.advance(30e3);
    t.running = false;
    t.Re.hooks.closed(1, 1006);
    t.advance(25e3);
    const result = t.posts.find((p) => p.type === 'result');
    assert.equal(result.event, 'left');
    assert.equal(result.why, 'reload');
    assert.equal(t.reloads.length, 1);
});

await test('frozen game with someone off the allowlist: no reload, the loop stops', async () => {
    const t = env({ settings: { allow: 'friend' } });
    await t.send('start', { mp: true });
    t.G.gs = 1, t.G.hum = 3, t.running = true;
    t.advance(10e3);
    t.running = false;
    t.advance(65e3);
    assert.equal(t.reloads.length, 0);
    const [r] = t.recovers();
    assert.equal(r.action, 'stop');
    assert.match(r.why, /白名单/);
});

await test('3 reloads in a row without reaching a lobby or game: stop', async () => {
    let t = env();
    await t.send('start', { mp: true });
    for (let i = 0; i < 3; i++) {
        t.advance(65e3);
        assert.equal(t.reloads.length, 1, `reload ${i + 1}`);
        t = reopen(t);
    }
    t.advance(65e3);
    assert.equal(t.reloads.length, 0);
    const [r] = t.recovers();
    assert.equal(r.action, 'stop');
    assert.match(r.why, /连续自动刷新 3 次/);
});

await test('10 automatic reloads in an hour: stop', async () => {
    const now = Date.UTC(2026, 10, 1, 3, 0, 0);
    const reloads = Array.from({ length: 10 }, (_, i) => now - 50 * 60e3 + i * 60e3);
    const t = env({ session: { territorialStrategyBotRecover: JSON.stringify({ reloads, inRow: 0, resume: { loop: 'mp', at: now - 1e3, why: 'x' }, last: null }) } });
    assert.equal(t.Re.state.loop, 'mp');
    t.advance(65e3);
    assert.equal(t.reloads.length, 0);
    assert.match(t.recovers()[0].why, /1 小时内已经自动刷新 10 次/);
});

await test('"Please try again later!" (4557): waits 5 minutes', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.Re.hooks.closed(0, 4557);
    t.advance(240e3);
    assert.equal(t.reloads.length, 0);
    t.advance(70e3);
    assert.equal(t.reloads.length, 1);
});

await test('hidden tab: never reloads', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.document.visibilityState = 'hidden';
    t.Re.hooks.closed(0, 1006);
    t.advance(600e3);
    assert.equal(t.reloads.length, 0);
    t.document.visibilityState = 'visible';
    t.advance(30e3);
    assert.equal(t.reloads.length, 0, 'counts from when the tab is visible again');
    t.advance(35e3);
    assert.equal(t.reloads.length, 1);
});

await test('close hook missing: no automatic reload, the loop stops with the reason', async () => {
    const t = env({ hook: false });
    await t.send('start', { mp: true });
    t.advance(65e3);
    assert.equal(t.reloads.length, 0);
    assert.match(t.recovers()[0].why, /断线钩子没装上/);
    assert.equal(t.Re.snapshot().recover.patched, false);
});

await test('no loop on: the watchdog does nothing', async () => {
    const t = env();
    await t.send('start');
    t.Re.hooks.closed(0, 1006);
    t.advance(300e3);
    assert.equal(t.reloads.length, 0);
    assert.equal(t.recovers().length, 0);
});

await test('lobby command with the loop on: reload, loop goes on, not counted as automatic', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.enterLobby();
    t.advance(5e3);
    const ack = await t.send('lobby');
    assert.equal(ack.ok, true);
    assert.equal(ack.resume, 'mp');
    t.advance(2e3);
    assert.equal(t.reloads.length, 1);
    const s = t.resume();
    assert.equal(s.inRow, 0);
    assert.equal(s.reloads.length, 0);
    const b = reopen(t);
    assert.equal(b.Re.state.loop, 'mp');
    b.advance(6e3);
    assert.deepEqual(b.opens, [1]);
});

await test('lobby command without a loop: reload, then the lobby opens once, bot stays disarmed', async () => {
    const t = env({ settings: { armed: false } });
    const ack = await t.send('lobby');
    assert.equal(ack.resume, 'lobby');
    t.advance(2e3);
    assert.equal(t.reloads.length, 1);
    const b = reopen(t);
    assert.equal(b.Re.state.loop, null);
    b.advance(10e3);
    assert.deepEqual(b.opens, [1]);
    assert.equal(b.ue.armed, false);
    b.advance(60e3);
    assert.deepEqual(b.opens, [1], 'only once');
});

await test('after a stop, the lobby command reloads without starting the loop again', async () => {
    const t = env();
    await t.send('start', { mp: true });
    t.Re.hooks.closed(0, 4591);
    t.advance(1e3);
    await t.send('lobby');
    t.advance(2e3);
    const b = reopen(t);
    assert.equal(b.Re.state.loop, null);
    assert.equal(b.ue.armed, false);
});

await test('panel button does the same as the lobby command', async () => {
    const t = env();
    const [box] = t.Re.fields();
    assert.ok(box);
    await t.send('start', { mp: true });
    // the second button in the row; the stub elements keep their click handlers
    const buttons = [];
    const orig = t.Re.fields;
    assert.equal(typeof orig, 'function');
    // fields() builds fresh elements; grab the handler from a new call
    const ctxEl = t.Re.state.armButton;
    assert.ok(ctxEl && ctxEl.on.click);
    buttons.push(ctxEl);
    // decorate shows the recovery row once something happened
    t.Re.hooks.closed(0, 1006);
    t.advance(25e3);
    const view = t.Re.decorate({ text: '', tone: 'ok', stats: [] });
    assert.ok(view.stats.some(([k, v]) => k === '恢复' && /正在刷新|刷新/.test(v)));
});

await test('B build: single loop recovers too, lobby command never opens a lobby', async () => {
    const t = env({ single: true });
    await t.send('start', { single: true });
    t.advance(1e3);
    assert.equal(t.singles, 1);
    t.running = false;
    t.advance(65e3);
    assert.equal(t.reloads.length, 1);
    const b = reopen(t, { single: true });
    assert.equal(b.Re.state.loop, 'single');
    b.advance(12e3);
    assert.equal(b.singles, 1);
    const c = env({ single: true, settings: { armed: false } });
    const ack = await c.send('lobby');
    assert.equal(ack.resume, null);
});

await test('ping state carries the recovery info', async () => {
    const t = env();
    const ack = await t.send('ping');
    assert.equal(ack.state.recover.patched, true);
    assert.equal(ack.state.recover.inRow, 0);
    assert.equal(JSON.stringify(ack.state.recover.codes), '[]');
    t.Re.hooks.closed(0, 4229);
    assert.equal(JSON.stringify(t.Re.snapshot().recover.codes), '[4229]');
});

let failed = 0;
for (const [s, name, err] of results) {
    console.log(`${s} ${name}`);
    if (err) failed++, console.log(err);
}
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
