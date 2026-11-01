// Game patches behind "start --mp" (A build only) and the replay report (both
// builds). Same pattern language as the other strategyBot patches in page.js;
// the patterns are FX Client's (patches/lobbyReminders.js, patches/replayHistory.js),
// so they track the live game.
const q = JSON.stringify;

// the main menu: openMultiplayer(room) picks the lobby room (setting 158 is
// what the join request asks for) and presses "Multiplayer"
export const MENU_FROM = q('__fx.strategyBot.openSingleplayer = function() { mainMenuClick(1) };');
export const MENU_TO = q('__fx.strategyBot.openSingleplayer = function() { mainMenuClick(1) }; ' +
    '__fx.strategyBot.openMultiplayer = function(room) { k.buffer.data[158].value = room; mainMenuClick(0) }; ' +
    '__fx.strategyBot.lobbyRoom = function(room) { k.buffer.data[158].value = room };');

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
// (patches/customLobby.js)
const SOCKET_CLOSE = `this.onSocketClose = function(socketIndex, code) { /* here */ this.closeCodes.push(code); if (code === 4321) {/*...*/}};`;

// Inserted after REPLAY_PATCH (both builds). Without it the extension cannot tell a dropped
// connection from the game's bot detection or a ban, so stuck pages are not reloaded by themselves.
export const CLOSE_PATCH =
    `try{n(s(${q(SOCKET_CLOSE)},"try { __fx.strategyBot.closed(socketIndex, code) } catch (sbCloseError) {}"),["closeCodes"])}` +
    `catch(t){console.warn("strategyBot: the socket close handler was not found, stuck pages are not reloaded by themselves:\\n"+t.message)}`;

// the end of the menus' try/catch, which is the last statement of the patch function
export const PATCH_END = 'games cannot be started by the bot:\\n"+t.message)}},t=>jt(t));var jt;';
export const patchEndWith = (code) => PATCH_END.replace('t.message)}}', () => `t.message)}${code}}`);
