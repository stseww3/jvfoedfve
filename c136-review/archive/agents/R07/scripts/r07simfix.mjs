// r07simfix.mjs — R07：给统筹的干净模拟器补上「船落在没人占的水 / 边界 / 山格」这一条线上规则。
//
// 来历：R01 在 /agent/repos/c136-data/src/tools/resim_lib_r01.mjs（openMatch 里的 g.landAt，L183-200）核实并修齐的差异——
//   线上引擎 acN（live_game_js.js，function aaM 内）在落点不是空地时，一律拿像素的「归属位」当目标，不检查这格是否真的有人占；
//   没人占的水 / 边界 / 山格，归属位 = (地形码 & 3) << 3，即 16 / 24 / 8 号席位。于是：
//     · 目标正好是自己 → 船上的兵原数回到余额；
//     · 目标是队友 → 按捐款入账（受配额和 150×领土封顶约束）；
//     · 目标是敌人 → 对那个席位开一条进攻；没有接壤时下一次结算原数退回余额。
//   干净模拟器的 landAt（src/sim/sim/boats.js L262-285）在这种落点直接 return，船上的兵凭空消失。
// 这里把同一段逻辑挂到 Game.prototype.landAt 上（不改数据包里的任何文件），供 R07 所有跑干净模拟器的脚本共用。
// 需要复现修正前的结果时设环境变量 R07_NO_LANDFIX=1。
export const oddLandings = [];

export function applyOddLandingFix(SIM) {
  if (process.env.R07_NO_LANDFIX === '1') return false;
  const { Game, T_LAND, P_INNER } = SIM;
  const P = Game.prototype;
  if (P.__r07LandFix) return true;
  const orig = P.landAt;
  P.landAt = function (p, troops, c, at) {
    const v = this.px[c];
    if (v !== T_LAND && v < P_INNER) {
      const target = (v & 3) << 3;
      oddLandings.push({ t: this.t, p, troops, c, v, target });
      if (target === p) { this.addBalance(p, troops); return; }
      if (!this.isEnemy(p, target)) {
        const room = this.receiverRoom(target, troops);
        if (room >= 1 && this.bookDonation(target, room)) this.addBalance(target, room);
        return;
      }
      if (this.hasAttack(p, target) || this.hasFreeSlot(p)) {
        this.front[p].push(at);
        this.addAttack(p, troops, target);
        this.schedule(p, true);
      }
      return;
    }
    return orig.call(this, p, troops, c, at);
  };
  P.__r07LandFix = true;
  return true;
}
