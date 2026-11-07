// Builds 0.7.0 (manual / remote mode) from the 0.5.3 extension folder.
// usage: node apply-remote.mjs [--single-only] <0.5.3 folder> <output folder> [cmdUrl resultUrl key]
//   --single-only: remote mode plays singleplayer games only (no allowlist, no lobby)
import fs from 'node:fs';
import path from 'node:path';
import { MENU_FROM, MENU_TO, LOBBY_PATCH, REPLAY_PATCH, CLOSE_PATCH, EXTRAS_PATCH, PATCH_END, patchEndWith } from './lobby-patch.mjs';

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
once('Te={list:()=>[...pe.list(),["backend","后端 general",!1]],changed(){ge.strategy=null},',
    'Te={list:()=>[...pe.list(),["backend","后端 general",!1]],has:t=>pe.has(t),changed(){ge.strategy=null},');
once('window.__fx=window.__fx||{},window.__fx.strategyBot=Me,',
    `const Re=${remote};\nwindow.__fx=window.__fx||{},window.__fx.strategyBot=Object.assign(Me,Re.hooks),`);
once('beforeTick:()=>we().beforeTick(),beforeFrame:()=>we().beforeFrame(),',
    'beforeTick:()=>we().beforeTick(),afterTick:()=>we().afterTick?.(),beforeFrame:()=>we().beforeFrame(),');
once('if(null!==this.spawnAt&&(!t.online||e-this.spawnAt<1e3))return;',
    'if(null!==this.spawnAt&&(!t.online||e-this.spawnAt<250))return;');
page = page.replaceAll(
    'queueAfterTick(){this.afterQueued||(this.afterQueued=!0,queueMicrotask(()=>{this.afterQueued=!1,this.afterTick()}))}',
    'queueAfterTick(){this.afterQueued||(this.afterQueued=!0,queueMicrotask(()=>{this.afterQueued&&(this.afterQueued=!1,this.afterTick())}))}'
);
once('beforeTick(){if(this.eligible()&&this.options().play)try{const t=this.sync();t.online?this.queueAfterTick():!this.error&&t.canAct(t.me)&&this.strategy.act(t)}catch(t){this.fail(t)}}',
    'beforeTick(){if(this.eligible()&&this.options().play)try{if(window[dictionary.game]&&!window[dictionary.game][dictionary.gIsSingleplayer])return;const t=this.sync();!this.error&&t.canAct(t.me)&&this.strategy.act(t)}catch(t){this.fail(t)}}');
once('i&&this.view.online&&"sbSpawn"!==t&&(this.inflight=Ct(),this.view.sendsHeld=!0)',
    'i&&this.view.online&&"sbSpawn"!==t&&(this.inflight=Ct(),this.inflightTick=this.view.t,this.view.sendsHeld=!0)');
once('afterTick(){if(this.eligible()&&this.options().play)try{const t=this.sync();if(null!==this.inflight&&Ct()-this.inflight<2e3)return;',
    'afterTick(){if(this.afterQueued=!1,this.eligible()&&this.options().play)try{const t=this.sync();if(null!==this.inflight&&Ct()-this.inflight<450&&t.t-(this.inflightTick??0)<8)return;');
once('version:"0.5.2",setPort(t){', `version:"${VERSION}",remote:Re,setPort(t){`);
// the backend port only with the backend strategy; without it the service worker opens no WebSocket
once('ke=()=>be("tsb-control",JSON.stringify({kind:"connect",port:ue.port}))',
    'ke=()=>be("tsb-control",JSON.stringify({kind:"connect",port:"backend"===ue.strategy?ue.port:null}))');
once('U={sbAttack:"sbSendAttack",sbBoat:"sbSendBoat",sbRetreat:"sbSendRetreat",sbSpawn:"sbSendSpawn"}',
    'U={sbAttack:"sbSendAttack",sbDonate:"sbSendDonate",sbBoat:"sbSendBoat",sbChase:"sbSendChase",sbMountain:"sbSendMountain",sbRetreat:"sbSendRetreat",sbSpawn:"sbSendSpawn"}');
once('else if (id === 2) { sbCommands.sbHandlers.d(player, b, c) }\\n            else if (id === 3) { sbCommands.sbHandlers.sbBoat(player, b, c) }\\n            else if (id === 4) { sbCommands.sbHandlers.sbChase(player, b, c) }\\n            else if (id === 5) { sbCommands.sbHandlers.sbRetreat(player, b) } /*...*/\\n        };",{addToDictionary:["sbCommands","sbHandlers","sbSpawn","sbAttack","sbBoat","sbChase","sbRetreat"]}',
    'else if (id === 2) { sbCommands.sbHandlers.sbDonate(player, b, c) }\\n            else if (id === 3) { sbCommands.sbHandlers.sbBoat(player, b, c) }\\n            else if (id === 4) { sbCommands.sbHandlers.sbChase(player, b, c) }\\n            else if (id === 5) { sbCommands.sbHandlers.sbRetreat(player, b) } /*...*/\\n        };",{addToDictionary:["sbCommands","sbHandlers","sbSpawn","sbAttack","sbDonate","sbBoat","sbChase","sbRetreat"]}');
once('this.borderLists=new Array(512),this.coastLists=new Array(512)',
    'this.borderLists=new Array(512),this.coastLists=new Array(512),this.frontLists=new Array(512),this.cliffLists=new Array(512)');
once('this.bal=e[dictionary.playerBalances],this.x0=e[dictionary.sbX0]',
    'this.bal=e[dictionary.playerBalances],this.debt=dictionary.sbDebt?e[dictionary.sbDebt]:null,this.aSo=dictionary.sbQuotaHolder&&dictionary.sbQuota&&I("sbQuotaHolder")?I("sbQuotaHolder")[dictionary.sbQuota]:null,this.x0=e[dictionary.sbX0]');
once('this.boats=I("sbBoatsHolder")[dictionary.sbBoats],this.boatCount=this.boats[dictionary.sbBoatCount]',
    'this.boats=I("sbBoatsHolder")[dictionary.sbBoats],this.boatCount=this.boats[dictionary.sbBoatCount],this.bSlot=dictionary.sbBoatSlot?this.boats[dictionary.sbBoatSlot]:null,this.bPos=dictionary.sbBoatPos?this.boats[dictionary.sbBoatPos]:null,this.bProg=dictionary.sbBoatProg?this.boats[dictionary.sbBoatProg]:null,this.bTroops=dictionary.sbBoatTroops?this.boats[dictionary.sbBoatTroops]:null,this.bId=dictionary.sbBoatId?this.boats[dictionary.sbBoatId]:null,this.bType=dictionary.sbBoatType?this.boats[dictionary.sbBoatType]:null,this.bHit=dictionary.sbBoatHit?this.boats[dictionary.sbBoatHit]:null,this.bRoute=dictionary.sbBoatRoute?this.boats[dictionary.sbBoatRoute]:null,this.bLeg=dictionary.sbBoatLeg?this.boats[dictionary.sbBoatLeg]:null,this.boatOf=dictionary.sbBoatOf?this.boats[dictionary.sbBoatOf]:null');
once('const e=I("game").data;this.passableWater=e.passableWater?1:0,this.passableMountains=e.passableMountains?1:0;',
    'const e=I("game").data;this.passableWater=e.passableWater?1:0,this.passableMountains=e.passableMountains?1:0,this.gameMode=e.gameMode|0,this.battleRoyaleMode=e.battleRoyaleMode|0,this.noFullSend=0===(e.gameMode|0)&&1===(e.battleRoyaleMode|0)?1:0;');
once('get border(){return this.convertLists(),this.borderLists}get coast(){return this.convertLists(),this.coastLists}convertLists(){if(this.listsStamp===this.t&&this.decoded)return;const t=I("playerData"),e=t[dictionary.sbBorder],s=t[dictionary.sbCoast],i=t=>{const e=new Array(t.length);for(let s=t.length-1;s>=0;s--)e[s]=t[s]>>2;return e};for(let t=0;t<512;t++){const n=0!==this.alive[t]||t===this.me;this.borderLists[t]=n&&e&&e[t]?i(e[t]):[],this.coastLists[t]=n&&s&&s[t]?i(s[t]):[]}this.decoded||this.decode(),this.listsStamp=this.t}',
    'get border(){return this.convertLists(),this.borderLists}get coast(){return this.convertLists(),this.coastLists}get front(){return this.convertLists(),this.frontLists}get cliff(){return this.convertLists(),this.cliffLists}convertLists(){if(this.listsStamp===this.t&&this.decoded)return;const t=I("playerData"),e=t[dictionary.sbBorder],s=t[dictionary.sbCoast],a=t[dictionary.sbFront],r=t[dictionary.sbCliff],i=t=>{const e=new Array(t.length);for(let s=t.length-1;s>=0;s--)e[s]=t[s]>>2;return e};for(let t=0;t<512;t++){const n=0!==this.alive[t]||t===this.me;this.borderLists[t]=n&&e&&e[t]?i(e[t]):[],this.coastLists[t]=n&&s&&s[t]?i(s[t]):[],this.frontLists[t]=n&&a&&a[t]?i(a[t]):[],this.cliffLists[t]=n&&r&&r[t]?i(r[t]):[]}this.decoded||this.decode(),this.listsStamp=this.t}');
once('t.front=[],t.cliff=[]',
    't.front=this.front.map(t=>t?t.slice():t),t.cliff=this.cliff.map(t=>t?t.slice():t)');
once('retreat(t,e=this.me){return t=Math.min(t,512),!(!this.canAct(e)||!this.hasAttack(e,t))&&this.command("sbRetreat",e,[t],this.attackProbe(e,t))}',
    'retreat(t,e=this.me){return t=Math.min(t,512),!(!this.canAct(e)||!this.hasAttack(e,t))&&this.command("sbRetreat",e,[t],this.attackProbe(e,t))}donate(t,e,s=this.me){return!(!this.canAct(s)||s===e)&&(t=Math.max(0,Math.min(1023,0|t)),e=Math.min(e,512),this.command("sbDonate",s,[t,e],()=>`${this.bal[s]} ${this.bal[e]}`))}chase(t,e,s=this.me){return!!this.canAct(s)&&(t=Math.max(0,Math.min(1023,0|t)),849===t&&(t=850),this.command("sbChase",s,[t,0|e],()=>`${this.bal[s]} ${this.boatN} ${this.boatCount[s]}`))}recall(t,e=this.me){if(!this.canAct(e))return!1;const s=0|t;return this.online?this.send("sbChase",e,[849,s]):this.command("sbChase",e,[849,s],()=>{const t=this.bId?this.playerBoat(e,s):-1;return t<0?"":`${this.bType[t]} ${this.bLeg[t]}`})}mountainAttack(t,e,s,i=this.me){return!(!this.canAct(i)||i===s)&&(t=Math.max(0,Math.min(1023,0|t)),s=Math.min(s,512),this.command("sbMountain",i,[t,0|e,s],this.attackProbe(i,s)))}');
once('for(const e of["sbAttack","sbBoat","sbRetreat"]){const s=t[dictionary[e]];if(s.tsbHook)continue;',
    'for(const e of["sbAttack","sbDonate","sbBoat","sbChase","sbMountain","sbRetreat"]){const s=dictionary[e]&&t[dictionary[e]];if(!s||s.tsbHook)continue;');
if (!singleOnly) {
    once('(t=>{if(!dictionary.sbRoomId)return!0;const e=t[dictionary.sbRoomId];return null==e||""===e})(t)', '!0');
    once(MENU_FROM, MENU_TO);
}
once(PATCH_END, patchEndWith((singleOnly ? '' : LOBBY_PATCH) + REPLAY_PATCH + CLOSE_PATCH + EXTRAS_PATCH));
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
manifest.version_name = singleOnly ? `${VERSION} 远程只管单人局` : `${VERSION} 远程版`;
manifest.description = manifest.description.replace(/。$/, '') + (singleOnly
    ? '；远程模式（只管单人局）：签名指令开始/结束，死了自动退出，卡住自动刷新，结果发 webhook。'
    : '；远程模式：签名指令控制，start --mp 进大逃杀，卡住自动刷新，结果发 webhook。');
if (manifest.description.length > 132) throw new Error(`manifest description is ${manifest.description.length} characters, Chrome allows 132`);

fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(src, out, { recursive: true });
for (const f of fs.readdirSync(out)) if (f.endsWith('.bak')) fs.rmSync(path.join(out, f));
fs.writeFileSync(path.join(out, 'page.js'), page);
for (const f of ['relay.js', 'background.js']) fs.copyFileSync(path.join(here, f), path.join(out, f));
fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`wrote ${out} (page.js ${page.length} bytes${singleOnly ? ', singleplayer only' : ''})`);
