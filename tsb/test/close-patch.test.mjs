// usage: FX_CLIENT=<FX Client checkout with uglify-js installed> node tsb/test/close-patch.test.mjs
// The socket close hook, applied the way page.js applies it (matchCode e, insertCode s,
// dictionary helper n, safe dictionary i), with FX Client's ModUtils.
import assert from 'node:assert/strict';
import { CLOSE_PATCH } from '../remote/lobby-patch.mjs';

const fx = process.env.FX_CLIENT || '/tmp/fxclient-src';
const { default: ModUtils, minifyCode } = await import(`${fx}/modUtils.js`);

// the close handler as FX Client's customLobby pattern expects it in the live game
const source = `
var log = [];
function SocketErrors() {
    this.uI = [], this.uJ = function(uK, cb) {
        this.uI.push(cb);
        if (cb === 4321) { log.push("reset") }
        if (cb === 4211) { log.push("update") } else { log.push("error " + cb) }
    }, this.ub = function(cb) { this.uI.push(cb) }
}
var a88 = new SocketErrors();`;

const apply = (script) => {
    const m = new ModUtils(minifyCode(script));
    const warn = console.warn;
    let warned = null;
    console.warn = (s) => { warned = s };
    try {
        new Function('e', 's', 'n', 'i', CLOSE_PATCH)(m.matchCode, m.insertCode, (r, keys) => keys.forEach((k) => m.addToDictionary(k, r[k])), m.safeDictionary);
    } finally {
        console.warn = warn;
    }
    return { m, warned };
};

{
    const { m, warned } = apply(source);
    assert.equal(warned, null);
    assert.equal(m.dictionary.closeCodes, 'uI');
    const calls = [];
    const run = new Function('__fx', `${m.script}; return { a88, log };`);
    const { a88, log } = run({ strategyBot: { closed: (sock, code) => calls.push([sock, code]) } });
    a88.uJ(0, 1006);
    a88.uJ(1, 4530);
    assert.deepEqual(calls, [[0, 1006], [1, 4530]]);
    assert.deepEqual(a88.uI, [1006, 4530]);
    assert.deepEqual(log, ['error 1006', 'error 4530']);
    // a hook that throws does not break the game's handler
    const run2 = new Function('__fx', `${m.script}; return { a88, log };`);
    const g2 = run2({ strategyBot: { closed: () => { throw new Error('boom') } } });
    g2.a88.uJ(0, 4211);
    assert.deepEqual(g2.log, ['update']);
    console.log('patched:', /this\.uJ=function\(uK,cb\)\{try\{__fx\.strategyBot\.closed\(uK,cb\)\}catch\(sbCloseError\)\{\}/.test(m.script.replace(/\s+/g, '')) ? 'yes' : m.script);
}

// FX Client's own pattern for the same function matches the same code
{
    const m = new ModUtils(minifyCode(source));
    m.insertCode('this.b = function(id, t) { /* here */ this.a.push(t); if (t === 4321) {/*...*/}};', 'void 0;');
}

// a game without that function: one warning, nothing else changes
{
    const other = 'function x() { this.a = [], this.b = function(c, d) { this.a.push(d) } }';
    const { m, warned } = apply(other);
    assert.match(warned, /socket close handler was not found/);
    assert.equal(m.dictionary.closeCodes, undefined);
    assert.equal(m.script, minifyCode(other));
}
console.log('close patch: ok');
