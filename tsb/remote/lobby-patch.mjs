// Game patches behind "start --mp" (A build only) and the replay report (both
// builds). Same pattern language as the other strategyBot patches in page.js;
// the patterns are FX Client's (patches/lobbyReminders.js, patches/replayHistory.js),
// so they track the live game.
const q = JSON.stringify;

// the main menu: openMultiplayer(room) picks the lobby room (setting 158 is
// what the join request asks for) and presses "Multiplayer"
export const MENU_FROM = q('__fx.strategyBot.openSingleplayer = function() { mainMenuClick(1) };');
export const MENU_TO = q('__fx.strategyBot.openSingleplayer = function() { mainMenuClick(1) }; ' +
    '__fx.strategyBot.openMultiplayer = function(room) { if (window.__tsbPlayerName) k.buffer.data[122].value = window.__tsbPlayerName; if (Number.isInteger(window.__tsbPlayerColor)) k.buffer.data[121].value = window.__tsbPlayerColor; k.buffer.data[158].value = room; mainMenuClick(0) }; ' +
    '__fx.strategyBot.lobbyRoom = function(room) { if (window.__tsbPlayerName) k.buffer.data[122].value = window.__tsbPlayerName; if (Number.isInteger(window.__tsbPlayerColor)) k.buffer.data[121].value = window.__tsbPlayerColor; k.buffer.data[158].value = room };');

const LOBBY_ROOM = `function LobbyRoom() {
        this.lobbyRoomState = 0;
        this.lobbyRoomMap = 0;
        this.lobbyRoomMapSeed = 0;
        this.lobbyRoomMode = 0;
        this.lobbyRoomNextMap = 0;
        this.lobbyRoomNextMapSeed = 0;
        this.lobbyRoomNextMode = 0;
        this.lobbyRoomIsContest = 0;
        this.lobbyRoomTimeLeft = 0;
        this.lobbyRoomSpawningSeed = 0;
        this.lobbyRoomPlayerIndex = 0;
        this.lobbyRoomTeamOffset = 0;
        this.lobbyRoomChatLog = [];
        this.lobbyRoomChatId = 1048575;
        /*...*/
    }`;

// called about twice a second while connected to the lobby
const LOBBY_UPDATE = `this.onFullLobbyUpdate = function () {
        updateLobbyUI(true);
        lobbyManager.joinTracker.di();
    };
    this.onLobbyUpdate = function () {
        lobbyManager.joinTracker.onLobbyUpdate();
        updateRoomTimers();
        updateLobbyUI(false);
        /* here */
    }`;

// runs on every join, before the rooms are filled in: lobbySelection is
// [room, ?, view, ready]
const LOBBY_INIT = `this.di = function () {
        for (var index = 0; index < this.lobbyRooms.length; index++) { this.lobbyRooms[index] = new LobbyRoom }
        this.lobbySelection[0] = settingsHolder.userSettings.data[158].value
        /* here */
    }`;

// Inserted at the end of the patch function (matchCode e, insertCode s,
// dictionary helper n). lobbySelection lands in the dictionary only when both
// lobby hooks are in.
export const LOBBY_PATCH =
    `try{e(${q(LOBBY_ROOM)},{addToDictionary:["lobbyRoomMode","lobbyRoomTimeLeft"]})}` +
    `catch(t){console.warn("strategyBot: LobbyRoom was not found, start --mp does not check the room's mode:\\n"+t.message)}` +
    `try{s(${q(LOBBY_UPDATE)},"__fx.strategyBot.lobbyTick();"),` +
    `n(s(${q(LOBBY_INIT)},";__fx.strategyBot.lobbyInit(this.lobbySelection, this.lobbyRooms);"),["lobbySelection","lobbyRooms"])}` +
    `catch(t){console.warn("strategyBot: the multiplayer lobby was not found, start --mp is off:\\n"+t.message)}`;

// leaving a game (sbLeave: the in-game menu's Leave, the end screen, a dropped
// connection): replayData is the replay text the Replay window shows afterwards
const LEAVE_GAME = `this.sbLeave = function (a) {
        if (!replayProtocol.replayParser.replayIn.length) {
            this.replayData = replayProtocol.replayRecorder.replayEncode();
        } else {
            this.replayData = replayProtocol.replayParser.replayIn;
        }
        /* here */ /*...*/
    }`;

// Inserted after LOBBY_PATCH (A build) or alone (B build); i is the safe dictionary.
export const REPLAY_PATCH =
    `try{n(s(${q(LEAVE_GAME)},"try { __fx.strategyBot.replay(this.replayData) } catch (sbReplayError) {}",{dictionary:{sbLeave:i.sbLeave}}),["replayData"])}` +
    `catch(t){console.warn("strategyBot: leaving a game was not found, replays are not reported:\\n"+t.message)}`;

// the socket close handler: every connection the game sees closing (a server code such as
// 4530 Lobby Timeout, or 1006) is pushed to closeCodes here; FX Client hooks the same spot
// (patches/customLobby.js). 2.16.66 logs the close first; earlier versions start with the push.
const SOCKET_CLOSE = `this.onSocketClose = function(socketIndex, code) { console.log("socket close index " + socketIndex + " error " + code); /* here */ this.closeCodes.push(code); if (code === 4321) {/*...*/}};`;
const SOCKET_CLOSE_OLD = `this.onSocketClose = function(socketIndex, code) { /* here */ this.closeCodes.push(code); if (code === 4321) {/*...*/}};`;
const CLOSED = 'try { __fx.strategyBot.closed(socketIndex, code) } catch (sbCloseError) {}';

// Inserted after REPLAY_PATCH (both builds). Without it the extension cannot tell a dropped
// connection from the game's bot detection or a ban, so stuck pages are not reloaded by themselves.
export const CLOSE_PATCH =
    `try{let r;try{r=s(${q(SOCKET_CLOSE)},${q(CLOSED)})}catch(t){r=s(${q(SOCKET_CLOSE_OLD)},${q(CLOSED)})}n(r,["closeCodes"])}` +
    `catch(t){console.warn("strategyBot: the socket close handler was not found, stuck pages are not reloaded by themselves:\\n"+t.message)}`;

const QUOTA_A = 'this.a = function(player, b) { return 10 !== game.gGameType || c.d.f(player) ? b : Math.min(this.sbQuota[player], b) };';
const QUOTA_B = 'this.a = function(player, b) { return game.gGameType !== 10 || c.d.f(player) ? b : Math.min(this.sbQuota[player], b) };';
const QUOTA_HOLDER_A = 'this.a = function(player) { var b = c.d[0]; playerData.playerBalances[player] -= b + c.d[1]; sbQuotaHolder.f(player, b) };';
const QUOTA_HOLDER_B = 'this.a = function(player) { var b = c.d[0]; playerData.playerBalances[player] -= b + c.d[1], sbQuotaHolder.f(player, b) };';
const QUOTA_HOLDER_C = 'this.a = function(player, b, c, d) { var e = playerData.playerBalances[player], b = f.g(e * (b + 1), 1024), c = f.g(c * e, 1024), b = Math.min(b, e - c); return b = sbQuotaHolder.h(player, b), j.k[0] = b, j.k[1] = c, d <= b };';
const DEBT_A = 'this.a = function(player, b) { var d; b = this.c(player, b); playerData.playerBalances[player] += b; if (playerData.sbDebt[player]) { d = Math.min(playerData.sbDebt[player], playerData.playerBalances[player]); playerData.sbDebt[player] -= d; playerData.playerBalances[player] -= d } return b };';
const DEBT_B = 'this.a = function(player, b) { var d; return b = this.c(player, b), playerData.playerBalances[player] += b, playerData.sbDebt[player] && (d = Math.min(playerData.sbDebt[player], playerData.playerBalances[player]), playerData.sbDebt[player] -= d, playerData.playerBalances[player] -= d), b };';
const DONATE_A = 'this.a = function(b, c) { if (game.gIsSingleplayer) { sbCommands.sbHandlers.sbDonate(game.playerId, b, c) } else { sbNet.sbSender.sbSendDonate(b, c) } };';
const DONATE_B = 'this.a = function(b, c) { game.gIsSingleplayer ? sbCommands.sbHandlers.sbDonate(game.playerId, b, c) : sbNet.sbSender.sbSendDonate(b, c) };';
const RECALL_A = 'this.a = function(b) { if (game.gIsSingleplayer) { sbCommands.sbHandlers.sbRecall(game.playerId, b) } else { sbNet.sbSender.sbSendChase(849, b) } };';
const RECALL_B = 'this.a = function(b) { game.gIsSingleplayer ? sbCommands.sbHandlers.sbRecall(game.playerId, b) : sbNet.sbSender.sbSendChase(849, b) };';
const MOUNTAIN_A = 'this.a = function(b, c, d) { if (game.gIsSingleplayer) { sbCommands.sbHandlers.sbMountain(game.playerId, b, c, d) } else { sbNet.sbSender.sbSendMountain(b, c, d) } };';
const MOUNTAIN_B = 'this.a = function(b, c, d) { game.gIsSingleplayer ? sbCommands.sbHandlers.sbMountain(game.playerId, b, c, d) : sbNet.sbSender.sbSendMountain(b, c, d) };';
const BOAT_ARRAYS_A = 'function a() { this.b = 512; this.c = 8; this.sbBoatN = 0; this.d = 0; this.sbBoatSlot = new Uint16Array(this.b); this.sbBoatPos = new Uint32Array(this.b); this.sbBoatProg = new Uint16Array(this.b); this.sbBoatTroops = new Uint32Array(this.b); this.f = new Uint16Array(this.b); this.sbBoatId = new Uint16Array(this.b); this.sbBoatType = new Uint8Array(this.b); this.sbBoatHit = new Uint8Array(this.b); this.sbBoatRoute = new Array(this.b); this.sbBoatLeg = new Uint16Array(this.b); this.sbBoatCount = new Uint8Array(game.gMaxPlayers); this.sbBoatOf = new Uint16Array(this.c * game.gMaxPlayers); /*...*/ }';
const BOAT_ARRAYS_B = 'function a() { this.b = 512, this.c = 8, this.sbBoatN = 0, this.d = 0, this.sbBoatSlot = new Uint16Array(this.b), this.sbBoatPos = new Uint32Array(this.b), this.sbBoatProg = new Uint16Array(this.b), this.sbBoatTroops = new Uint32Array(this.b), this.f = new Uint16Array(this.b), this.sbBoatId = new Uint16Array(this.b), this.sbBoatType = new Uint8Array(this.b), this.sbBoatHit = new Uint8Array(this.b), this.sbBoatRoute = new Array(this.b), this.sbBoatLeg = new Uint16Array(this.b), this.sbBoatCount = new Uint8Array(game.gMaxPlayers), this.sbBoatOf = new Uint16Array(this.c * game.gMaxPlayers) /*...*/ }';

export const EXTRAS_PATCH =
    `try{try{e(${q(QUOTA_A)},{dictionary:{game:i.game,gGameType:i.gGameType},addToDictionary:["sbQuota"]})}catch(t){e(${q(QUOTA_B)},{dictionary:{game:i.game,gGameType:i.gGameType},addToDictionary:["sbQuota"]})}try{e(${q(QUOTA_HOLDER_A)},{dictionary:{playerData:i.playerData,playerBalances:i.playerBalances},addToDictionary:["sbQuotaHolder"]})}catch(t){try{e(${q(QUOTA_HOLDER_B)},{dictionary:{playerData:i.playerData,playerBalances:i.playerBalances},addToDictionary:["sbQuotaHolder"]})}catch(t2){e(${q(QUOTA_HOLDER_C)},{dictionary:{playerData:i.playerData,playerBalances:i.playerBalances},addToDictionary:["sbQuotaHolder"]})}}}catch(t){console.warn("strategyBot: quota holder was not found:\\n"+t.message)}` +
    `try{try{e(${q(DEBT_A)},{dictionary:{playerData:i.playerData,playerBalances:i.playerBalances},addToDictionary:["sbDebt"]})}catch(t){e(${q(DEBT_B)},{dictionary:{playerData:i.playerData,playerBalances:i.playerBalances},addToDictionary:["sbDebt"]})}}catch(t){console.warn("strategyBot: player debt was not found:\\n"+t.message)}` +
    `try{const l={game:i.game,gIsSingleplayer:i.gIsSingleplayer,playerId:i.playerId,sbCommands:i.sbCommands,sbHandlers:i.sbHandlers,sbNet:i.sbNet,sbSender:i.sbSender,sbDonate:i.sbDonate};try{e(${q(DONATE_A)},{dictionary:l,addToDictionary:["sbSendDonate"]})}catch(t){try{e(${q(DONATE_B)},{dictionary:l,addToDictionary:["sbSendDonate"]})}catch(t2){}}try{e(${q(RECALL_A)},{dictionary:l,addToDictionary:["sbRecall","sbSendChase"]})}catch(t){e(${q(RECALL_B)},{dictionary:l,addToDictionary:["sbRecall","sbSendChase"]})}try{e(${q(MOUNTAIN_A)},{dictionary:l,addToDictionary:["sbMountain","sbSendMountain"]})}catch(t){e(${q(MOUNTAIN_B)},{dictionary:l,addToDictionary:["sbMountain","sbSendMountain"]})}}catch(t){console.warn("strategyBot: chase/mountain commands were not found:\\n"+t.message)}` +
    `try{const bd={game:i.game,gMaxPlayers:i.gMaxPlayers,sbBoatN:i.sbBoatN,sbBoatCount:i.sbBoatCount},ba=["sbBoatSlot","sbBoatPos","sbBoatProg","sbBoatTroops","sbBoatId","sbBoatType","sbBoatHit","sbBoatRoute","sbBoatLeg","sbBoatOf"];try{e(${q(BOAT_ARRAYS_A)},{dictionary:bd,addToDictionary:ba})}catch(t){e(${q(BOAT_ARRAYS_B)},{dictionary:bd,addToDictionary:ba})}}catch(t){console.warn("strategyBot: boat arrays were not found:\\n"+t.message)}`;

// the end of the menus' try/catch, which is the last statement of the patch function
export const PATCH_END = 'games cannot be started by the bot:\\n"+t.message)}},t=>jt(t));var jt;';
export const patchEndWith = (code) => PATCH_END.replace('t.message)}}', () => `t.message)}${code}}`);
