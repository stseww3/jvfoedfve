// Builds 0.7.0 (manual / remote mode) from the 0.5.3 extension folder.
// usage: node apply-remote.mjs [--single-only] <0.5.3 folder> <output folder> [cmdUrl resultUrl key]
//   --single-only: remote mode plays singleplayer games only (no allowlist, no lobby)
import fs from 'node:fs';
import path from 'node:path';
import { MENU_FROM, MENU_TO, LOBBY_PATCH, REPLAY_PATCH, CLOSE_PATCH, PATCH_END, patchEndWith } from './lobby-patch.mjs';

const VERSION = '0.7.0';
// the server running tsb/relay/relay.py (in place of webhook.site); match patterns cover every port
const RELAY_HOST = 'http://173.249.205.165/*';
const argv = process.argv.slice(2);
const singleOnly = argv.includes('--single-only');
const [src, out, cmdUrl = '', resultUrl = '', key = ''] = argv.filter((a) => a !== '--single-only');
if (!src || !out) {
    console.error('usage: node apply-remote.mjs [--single-only] <0.5.3 folder> <output folder> [cmdUrl resultUrl key]');
    process.exit(2);
}
const here = path.dirname(new URL(import.meta.url).pathname);
let page = fs.readFileSync(path.join(src, 'page.js'), 'utf8');
if (!page.includes('addToDictionary("sbRoomId","nu")')) throw new Error('page.js is not 0.5.3 (no sbRoomId "nu")');
if (page.includes('remote:Re')) throw new Error('page.js already has the remote mode');

const once = (from, to) => {
    const n = page.split(from).length - 1;
    if (n !== 1) throw new Error(`expected one match, found ${n}: ${from.slice(0, 80)}`);
    page = page.replace(from, () => to);
};
let remote = fs.readFileSync(path.join(here, 'remote-page.js'), 'utf8').trim();
if (!remote.includes(`const VERSION = "${VERSION}";`)) throw new Error(`remote-page.js is not ${VERSION}`);
if (singleOnly) {
    if (!remote.includes('const SINGLE_ONLY = !1;')) throw new Error('no SINGLE_ONLY switch in remote-page.js');
    remote = remote.replace('const SINGLE_ONLY = !1;', 'const SINGLE_ONLY = !0;');
}
const q = JSON.stringify;

once('Qt={spawn:!0,play:!0,autoStart:!1,folded:!1,left:null,top:null}',
    'Qt={spawn:!0,play:!0,autoStart:!1,manual:!1,armed:!1,stay:!1,allow:"",cmdUrl:"",resultUrl:"",key:"",pollMs:3e3,folded:!1,left:null,top:null}');
once('(ce,{port:8765,strategy:"v3"})',
    `(ce,{port:8765,strategy:"v3",cmdUrl:${q(cmdUrl)},resultUrl:${q(resultUrl)},key:${q(key)}})`);
once('["autoStart","自动开局（打开页面时和每局结束后）"]]',
    '["autoStart","自动开局（打开页面时和每局结束后）"],["manual","手动（远程）：只听远程 start / end"]]');
once('"command"===t.type&&(this.eligible()?this.sync(!1):this.ctl.abandon())',
    '"command"===t.type&&(this.eligible()&&Re.allowed()?this.sync(!1):this.ctl.abandon())');
once('window.__fx=window.__fx||{},window.__fx.strategyBot=Me,',
    `const Re=${remote};\nwindow.__fx=window.__fx||{},window.__fx.strategyBot=Object.assign(Me,Re.hooks),`);
once('version:"0.5.2",setPort(t){', `version:"${VERSION}",remote:Re,setPort(t){`);
// the backend port only with the backend strategy; without it the service worker opens no WebSocket
once('ke=()=>be("tsb-control",JSON.stringify({kind:"connect",port:ue.port}))',
    'ke=()=>be("tsb-control",JSON.stringify({kind:"connect",port:"backend"===ue.strategy?ue.port:null}))');
if (!singleOnly) once(MENU_FROM, MENU_TO);
once(PATCH_END, patchEndWith((singleOnly ? '' : LOBBY_PATCH) + REPLAY_PATCH + CLOSE_PATCH));
once('for(const t of ye)t.options=()=>({spawn:ue.spawn,play:ue.play});',
    'for(const t of ye)t.options=()=>Re.options();');
once('this.onPort&&n.appendChild(this.portField()),',
    'this.onPort&&n.appendChild(this.portField()),n.append(...Re.fields()),');
once('t=we().info(),e=xe.update(ue.autoStart,t)',
    't=we().info(),Re.frame(t),e=xe.update(ue.autoStart&&!ue.manual,t)');
once('Ae.render(function({status:t,settings:e,info:s,pending:i,backend:n,strategy:a}){',
    'Ae.render(Re.decorate(function({status:t,settings:e,info:s,pending:i,backend:n,strategy:a}){');
once('strategy:pe.name(ue.strategy)}))}function Be(){',
    'strategy:pe.name(ue.strategy)})))}function Be(){');

new Function(page);

const manifest = JSON.parse(fs.readFileSync(path.join(src, 'manifest.json'), 'utf8'));
manifest.version = VERSION;
// territorial.io (already granted through the content scripts) and scripting: after an install or
// update the service worker finds the open game tabs and reloads the remote-mode ones
manifest.host_permissions = [...new Set([...(manifest.host_permissions || []), 'https://webhook.site/*', RELAY_HOST, 'https://territorial.io/*'])];
manifest.permissions = [...new Set([...(manifest.permissions || []), 'scripting'])];
manifest.version_name = singleOnly ? `${VERSION} 远程只管单人局` : `${VERSION} 远程+白名单`;
manifest.description = manifest.description.replace(/。$/, '') + (singleOnly
    ? '；远程模式（只管单人局）：签名指令开始/结束，死了自动退出，卡住自动刷新，结果发 webhook。'
    : '；远程模式：签名指令控制，start --mp 进大逃杀，卡住自动刷新，多人局只跟白名单打，结果发 webhook。');
if (manifest.description.length > 132) throw new Error(`manifest description is ${manifest.description.length} characters, Chrome allows 132`);

fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(src, out, { recursive: true });
for (const f of fs.readdirSync(out)) if (f.endsWith('.bak')) fs.rmSync(path.join(out, f));
fs.writeFileSync(path.join(out, 'page.js'), page);
for (const f of ['relay.js', 'background.js']) fs.copyFileSync(path.join(here, f), path.join(out, f));
fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`wrote ${out} (page.js ${page.length} bytes${singleOnly ? ', singleplayer only' : ''})`);
