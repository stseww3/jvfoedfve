#!/usr/bin/env python3
"""worthgate.py — 把 Vb「对真人邻居单独出手」的门槛按源码公式摊开成「对方密度 ÷ 自己密度」。

只做公式代入，不读对局数据；参数取自 out/trace/<mid>-params-worth.txt（dbg/params.mjs 打出来的生效参数）。

源码（src/strategy/v27-team-c116-vb.js）：
  offers  L5095       rawNeed = elimCost(g,q) + inAtk − myAtk
          L5097-5100  left = peak[q]/4；share = min(1, cnt[q]/border[q].length)；
                      baseGain = max(1, Lq − left + left×shareW×share)；c = (rawNeed + fee) / baseGain
          L5182-5185  有队友的兵压在对方身上（allyAtk > 0）：c 改按 (rawNeed − 0.85×allyAtk + fee) / baseGain 重算
          L5205-5207  编队友在打它（或 allyAtk ≥ 对方余额的 15%）：c 再 ×0.58
  elimCost L464-469   x = min(1, left/T)；elimCost = 2×B×(1 − x^1.6) + 2×T×(1 − x)
  buyLand L5350-5359  worth = maxW × winRatio(t) × refDens；c ≥ worth 且 c ≥ cheap 且没过软上限 → 不出手
  winRatio L2875-2882 winT 表上相邻两点之间线性，表外取端点

口径（都写在输出里）：对方从没掉过地（T = peak → x = 0.25）、没有任何在途攻击兵（inAtk = myAtk = 0）、
      手续费 fee 忽略、refDens 取自己密度（不触发 marketFloor）、没有贴边惩罚、没有队友联手折扣。
      share 取 0 和 1 两个端点。
输出：各拍的 winRatio、worth ÷ 自己密度、c 关于对方密度 dq 的线性式、
      自己密度为 20 / 50 / 100 时「对方密度不超过多少才会出手」及其与自己密度的比值。

用法：python3 scripts/worthgate.py <mid>
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def win_ratio(winT, t):
    if t <= winT[0][0]:
        return winT[0][1]
    for (t0, v0), (t1, v1) in zip(winT, winT[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return winT[-1][1]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    mid = sys.argv[1]
    src = os.path.join(ROOT, "out", "trace", f"{mid}-params-worth.txt")
    txt = open(src).read()

    def num(name):
        m = re.search(r"(?:^|\s)" + re.escape(name) + r"=([-0-9.e]+)", txt)
        if not m:
            raise SystemExit(f"参数 {name} 不在 {src} 里")
        return float(m.group(1))

    m = re.search(r"winT=(\[\[.*?\]\])", txt)
    winT = json.loads(m.group(1))
    maxW, shareW = num("maxW"), num("shareW")
    x = 0.25
    kB = 2 * (1 - x ** 1.6)
    kT = 2 * (1 - x)
    print(f"# {mid} 对真人邻居单独出手的门槛（worthgate.py；参数来自 {os.path.relpath(src, ROOT)}）")
    print(f"  参数：maxW={maxW:g}  shareW={shareW:g}  winT={json.dumps(winT)}")
    print(f"  对方从没掉过地（x = left/T = {x}）时 elimCost = {kB:.3f}×对方余额 + {kT:.2f}×对方地")
    for share in (0, 1):
        den = (1 - x) + x * shareW * share
        print(f"  share={share}：baseGain = {den:.4f}×对方地 → c = {kB / den:.3f}×对方密度 + {kT / den:.2f}")
    print("  各拍：winRatio | worth ÷ 自己密度（= maxW×winRatio） | 自己密度 20 / 50 / 100 时 对方密度上限（括号里是 上限 ÷ 自己密度；share=0 ~ share=1）")
    for t in (1500, 1750, 2000, 2250, 2500, 3000, 4000):
        wr = win_ratio(winT, t)
        k = maxW * wr
        cells = []
        for dme in (20, 50, 100):
            lim = []
            for share in (0, 1):
                den = (1 - x) + x * shareW * share
                a, b = kB / den, kT / den
                lim.append(max(0.0, (k * dme - b) / a))
            cells.append(f"{lim[0]:.1f}~{lim[1]:.1f}（{lim[0] / dme:.2f}~{lim[1] / dme:.2f}）")
        print(f"  t={t:<5d} winRatio {wr:.3f} | worth = {k:.3f}×自己密度 | " + " / ".join(cells))
    print("  读法：对方密度高于上限时，单独出手的报价 c ≥ worth，buyLand L5359 直接 break；"
          "只有自己过软上限（余额 > 100×地，over）或者有队友的兵已经压在对方身上（offers L5182-5185 重算、L5205-5207 再 ×0.58）才会改变")

    # 第二道闸：报价已经低于 worth，价格线放行的预算够不够发一条指令。
    full = os.path.join(ROOT, "out", "trace", f"{mid}-params.txt")
    txt2 = txt + ("\n" + open(full).read() if os.path.exists(full) else "")

    def num2(name):
        mm = re.search(r"(?:^|\s)" + re.escape(name) + r"=([-0-9.e]+)", txt2)
        return float(mm.group(1)) if mm else None

    chunk, pms = num2("chunk"), num2("pulseMinShare")
    if chunk is None or pms is None:
        print(f"  （第二道闸没有算：chunk / pulseMinShare 不在 {os.path.relpath(src, ROOT)} 或 {os.path.relpath(full, ROOT)} 里）")
        return
    fee = 12 / 1024
    print(f"  第二道闸（报价低于 worth 之后；chunk={chunk:g} pulseMinShare={pms:g}，手续费按余额的 12/1024）：buyLand L5422-5426 的预算 = (worth×地 − 手续费×m − c×地) ÷ (1+m)，m = maxW×winRatio；"
          "没过软上限时 avail 不会超过这个预算")
    print("    整吃档（offers L5291-5294：2400 拍前、对方没在打我、need > 0.35×余额 时不走脉冲；buyLand L5611-5613 要 x ≥ want 或 x ≥ chunk×余额）："
          "预算 ≥ chunk×余额 ⟺ c ≤ (m − chunk×(1+m) − 12/1024×m)×自己密度")
    print("    脉冲档（buyLand L5594-5607：x ≥ pulseMinShare×余额）：预算 ≥ pulseMinShare×余额 ⟺ c ≤ (m − pulseMinShare×(1+m) − 12/1024×m)×自己密度")
    print("    各拍：整吃档 c 上限 ÷ 自己密度 | 自己密度 20 / 50 / 100 时 对方密度上限 ÷ 自己密度（share=0 ~ share=1）‖ 脉冲档 同样两列")
    for t in (1500, 1750, 2000, 2250, 2399, 2500, 3000):
        wr = win_ratio(winT, t)
        mk = maxW * wr
        row = []
        for gate in (chunk, pms):
            kk = mk - gate * (1 + mk) - fee * mk
            cells = []
            for dme in (20, 50, 100):
                lim = []
                for share in (0, 1):
                    den = (1 - x) + x * shareW * share
                    a, b = kB / den, kT / den
                    lim.append(max(0.0, (kk * dme - b) / a) / dme)
                cells.append(f"{lim[0]:.2f}~{lim[1]:.2f}")
            row.append(f"c ≤ {kk:.3f}×自己密度 | " + " / ".join(cells))
        print(f"    t={t:<5d} 整吃档 {row[0]} ‖ 脉冲档 {row[1]}")
    print("    读法：对方没掉过地、没人在打它时，2400 拍前只要「吃掉它整个号要的兵」超过自己余额的 0.35 倍，就走整吃档——对方密度要低到整吃档那一列以下，一个号才会独自出第一手；"
          "否则报价明明低于 worth，预算却不到余额的两成，整拍不发（buy-why 里写成「拦在 worth,chunk」）")


if __name__ == "__main__":
    main()
