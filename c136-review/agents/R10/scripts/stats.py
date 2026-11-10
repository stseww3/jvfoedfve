#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stats.py — c136 复盘项目的统计口径工具（R10，裁判用）。只依赖 Python 标准库。

提供（每个函数的定义、出处、适用条件都写在各自的 docstring 里）：

  比例的区间
    wilson(k, n, conf)                    Wilson 计分区间（本项目的默认区间）
    clopper_pearson(k, n, conf)           Clopper–Pearson 精确区间（保守，用作小样本对照）
  两个比例之差
    newcombe_diff(k1, n1, k2, n2, conf)   Newcombe(1998) 方法 10：p2 − p1 的混合计分区间
    fisher_exact(k1, n1, k2, n2)          Fisher 精确检验的双侧 p 值
    prob_b_beats_a(kA, nA, kB, nB, prior) Beta 后验下 P(pB > pA)（PLAN 阶段 5 的判定量）
  样本量与功效
    n_per_arm(p1, p2, alpha, power)       每臂需要的局数（正态近似，可选连续性校正）
    power_normal(p1, p2, n, alpha)        给定每臂局数时的功效（正态近似）
    power_exact(p1, p2, n1, n2, alpha)    精确功效（枚举全部结果，按 Fisher 双侧检验判定）
    mde(p1, n, alpha, power, exact)       给定每臂局数时能分辨的最小提升（最小可检出效应）
  带基础期望的胜率（每局的基础期望可以不同）
    poisson_binomial_pmf(ps)              各局独立、胜率各不相同时，总胜局数的精确分布
    excess_test(wins, exps)               实际胜局数相对基础期望的超额及精确双侧/单侧 p 值
    logit_shift(wins, exps, conf)         单参数「实力」估计：logit(p_i) = logit(e_i) + delta，
                                          给出 delta 的极大似然估计和似然比区间

用法：
  python3 stats.py selftest
  python3 stats.py wilson 10 74
  python3 stats.py cp 1 9
  python3 stats.py diff 1 9 10 74            # 第二组减第一组
  python3 stats.py fisher 1 9 10 74
  python3 stats.py bayes 1 9 10 74           # P(第二组的真实胜率 > 第一组)
  python3 stats.py n 0.135 0.40              # 每臂局数
  python3 stats.py power 0.135 0.40 45       # 每臂 45 局时的功效（近似 + 精确）
  python3 stats.py mde 0.135 100             # 每臂 100 局时的最小可检出提升
  python3 stats.py plan-table                # 重算 PLAN.md §1.3 和 §7 的两张表

分析单位提醒：这里所有函数都假定「观测之间相互独立」。本项目的独立单位是「局」
（见 reports/METRICS.md），不是单号结算记录；同一局里 8~20 个号的结果高度相关，
把单号记录数当作 n 会让区间虚假变窄。
"""

from __future__ import annotations

import json
import math
import sys
from statistics import NormalDist

_ND = NormalDist()


# ----------------------------------------------------------------------------
# 基础
# ----------------------------------------------------------------------------

def z_of(conf: float) -> float:
    """双侧置信水平 conf 对应的标准正态分位数，例如 0.95 -> 1.959964。"""
    if not 0.0 < conf < 1.0:
        raise ValueError("conf 必须在 (0,1) 内")
    return _ND.inv_cdf(1.0 - (1.0 - conf) / 2.0)


def _check_kn(k: int, n: int) -> None:
    if n < 0 or k < 0 or k > n:
        raise ValueError(f"需要 0 <= k <= n，得到 k={k}, n={n}")


def _log_binom_pmf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log1p(-p))


def binom_pmf(k: int, n: int, p: float) -> float:
    """二项分布概率 P(X = k)，X ~ Bin(n, p)。"""
    return math.exp(_log_binom_pmf(k, n, p))


def binom_cdf(k: int, n: int, p: float) -> float:
    """二项分布累积概率 P(X <= k)。"""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return min(1.0, math.fsum(binom_pmf(i, n, p) for i in range(0, k + 1)))


def binom_sf(k: int, n: int, p: float) -> float:
    """二项分布上尾概率 P(X >= k)。"""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return min(1.0, math.fsum(binom_pmf(i, n, p) for i in range(k, n + 1)))


# ----------------------------------------------------------------------------
# 单个比例的区间
# ----------------------------------------------------------------------------

def wilson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """
    Wilson 计分区间（不带连续性校正）。

    出处：Wilson (1927)；Brown, Cai & DasGupta (2001) 推荐它用于小样本。
    公式：centre = (p + z²/2n) / (1 + z²/n)
          half   = z * sqrt(p(1−p)/n + z²/4n²) / (1 + z²/n)
    性质：k=0 时下界恰为 0，k=n 时上界恰为 1；实际覆盖率在名义水平附近波动
    （平均接近名义值，个别 p 值处略低），不像 Wald 区间那样在小样本下严重偏窄。
    n=0 时返回 (0, 1)：没有数据，什么也不能说。
    """
    _check_kn(k, n)
    if n == 0:
        return (0.0, 1.0)
    z = z_of(conf)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, centre - half)
    hi = 1.0 if k == n else min(1.0, centre + half)
    return (lo, hi)


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """
    Clopper–Pearson「精确」区间：下界 pL 满足 P(X >= k | pL) = alpha/2，
    上界 pU 满足 P(X <= k | pU) = alpha/2。用二分法解，不依赖 Beta 分位数函数。

    性质：覆盖率保证不低于名义水平，因此偏宽（保守）。用途：样本只有个位数时
    和 Wilson 并列给出，让读者看到「最保守的说法」是什么。
    """
    _check_kn(k, n)
    if n == 0:
        return (0.0, 1.0)
    alpha = 1.0 - conf

    def solve(f, target):
        # f 在 [0,1] 上单调递增，求 f(p) = target
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2.0
            if f(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    if k == 0:
        lower = 0.0
    else:
        lower = solve(lambda p: binom_sf(k, n, p), alpha / 2.0)
    if k == n:
        upper = 1.0
    else:
        upper = solve(lambda p: 1.0 - binom_cdf(k, n, p), 1.0 - alpha / 2.0)
    return (lower, upper)


# ----------------------------------------------------------------------------
# 两个比例之差
# ----------------------------------------------------------------------------

def newcombe_diff(k1: int, n1: int, k2: int, n2: int,
                  conf: float = 0.95) -> tuple[float, float, float]:
    """
    两个独立比例之差 d = p2 − p1 的区间：Newcombe (1998) 方法 10（混合计分法）。

    做法：先分别求两组的 Wilson 区间 (l1,u1)、(l2,u2)，然后
        lower = d − sqrt((p2 − l2)² + (u1 − p1)²)
        upper = d + sqrt((u2 − p2)² + (p1 − l1)²)
    返回 (d, lower, upper)。方向约定：第二组减第一组（「新 − 旧」「处理 − 对照」）。

    性质：小样本和比例接近 0/1 时比 Wald 差值区间可靠；区间不会越出 [−1, 1]。
    前提：两组相互独立，组内各局相互独立。
    """
    _check_kn(k1, n1)
    _check_kn(k2, n2)
    if n1 == 0 or n2 == 0:
        return (float("nan"), -1.0, 1.0)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, conf)
    l2, u2 = wilson(k2, n2, conf)
    d = p2 - p1
    lower = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    upper = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return (d, max(-1.0, lower), min(1.0, upper))


def _log_hypergeom(a: int, r1: int, r2: int, c1: int) -> float:
    # 2x2 表 [[a, r1-a], [c1-a, r2-c1+a]] 在边际固定时的对数概率
    def lc(n, k):
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    return lc(r1, a) + lc(r2, c1 - a) - lc(r1 + r2, c1)


def fisher_exact(k1: int, n1: int, k2: int, n2: int) -> float:
    """
    Fisher 精确检验的双侧 p 值（零假设：两组真实胜率相同）。
    双侧定义：把边际固定时所有「概率不大于观测表概率」的表的概率相加（R 的 fisher.test 同款）。
    性质：保守（实际第一类错误率低于名义水平），小样本时功效偏低，但不会虚报显著。
    """
    _check_kn(k1, n1)
    _check_kn(k2, n2)
    c1 = k1 + k2
    lo = max(0, c1 - n2)
    hi = min(n1, c1)
    logp_obs = _log_hypergeom(k1, n1, n2, c1)
    total = 0.0
    for a in range(lo, hi + 1):
        lp = _log_hypergeom(a, n1, n2, c1)
        if lp <= logp_obs + 1e-9:
            total += math.exp(lp)
    return min(1.0, total)


def _log_beta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def prob_b_beats_a(kA: int, nA: int, kB: int, nB: int,
                   prior: tuple[float, float] = (1.0, 1.0),
                   grid: int = 4000) -> float:
    """
    贝叶斯后验概率 P(pB > pA)。两组各自用 Beta(prior) 先验（默认均匀先验 Beta(1,1)），
    后验分别是 Beta(prior_a + k, prior_b + n − k)。

    计算：P = ∫ f_B(x) · F_A(x) dx，在 [0,1] 上用复合 Simpson 数值积分，
    F_A 由同一网格上对 f_A 的累积 Simpson 积分得到。grid=4000 时绝对误差 < 1e-6
    （自测里和整数参数的闭式解比对）。

    注意：这是 PLAN 阶段 5 登记的判定量。「连续监测、一过 95% 就停」会抬高假阳性率，
    停止规则必须事先登记（见 reports/OVERFIT-THREATS.md）。
    """
    _check_kn(kA, nA)
    _check_kn(kB, nB)
    a1, b1 = prior[0] + kA, prior[1] + nA - kA
    a2, b2 = prior[0] + kB, prior[1] + nB - kB
    if grid % 2:
        grid += 1
    h = 1.0 / grid
    lb1, lb2 = _log_beta(a1, b1), _log_beta(a2, b2)

    def pdf(x, a, b, lb):
        if x <= 0.0 or x >= 1.0:
            # 端点：a<1 或 b<1 时密度发散；本项目的先验 >= 0.5 且数值积分用开区间近似
            if (x <= 0.0 and a > 1.0) or (x >= 1.0 and b > 1.0):
                return 0.0
            if (x <= 0.0 and a == 1.0):
                return math.exp(-lb)
            if (x >= 1.0 and b == 1.0):
                return math.exp(-lb)
            x = min(max(x, 1e-12), 1.0 - 1e-12)
        return math.exp((a - 1.0) * math.log(x) + (b - 1.0) * math.log1p(-x) - lb)

    fa = [pdf(i * h, a1, b1, lb1) for i in range(grid + 1)]
    fb = [pdf(i * h, a2, b2, lb2) for i in range(grid + 1)]
    # 累积分布 F_A 在偶数节点上用 Simpson，奇数节点用相邻梯形补
    FA = [0.0] * (grid + 1)
    for i in range(2, grid + 1, 2):
        FA[i] = FA[i - 2] + h / 3.0 * (fa[i - 2] + 4.0 * fa[i - 1] + fa[i])
    for i in range(1, grid, 2):
        FA[i] = FA[i - 1] + h / 12.0 * (5.0 * fa[i - 1] + 8.0 * fa[i] - fa[i + 1])
    total_a = FA[grid] if FA[grid] > 0 else 1.0
    g = [fb[i] * (FA[i] / total_a) for i in range(grid + 1)]
    s = g[0] + g[grid]
    s += 4.0 * math.fsum(g[i] for i in range(1, grid, 2))
    s += 2.0 * math.fsum(g[i] for i in range(2, grid, 2))
    total_b = (fb[0] + fb[grid] + 4.0 * math.fsum(fb[i] for i in range(1, grid, 2))
               + 2.0 * math.fsum(fb[i] for i in range(2, grid, 2))) * h / 3.0
    return min(1.0, max(0.0, (s * h / 3.0) / (total_b if total_b > 0 else 1.0)))


def _prob_b_beats_a_closed(kA: int, nA: int, kB: int, nB: int) -> float:
    """均匀先验、整数参数时的闭式解（Evan Miller 2014 的求和式），只用于自测比对。"""
    a1, b1 = 1 + kA, 1 + nA - kA
    a2, b2 = 1 + kB, 1 + nB - kB
    total = 0.0
    for i in range(a2):
        total += math.exp(_log_beta(a1 + i, b1 + b2) - math.log(b2 + i)
                          - _log_beta(1 + i, b2) - _log_beta(a1, b1))
    return total


# ----------------------------------------------------------------------------
# 样本量与功效
# ----------------------------------------------------------------------------

def n_per_arm(p1: float, p2: float, alpha: float = 0.05, power: float = 0.80,
              continuity: bool = False) -> int:
    """
    两组等量、双侧检验时每臂需要的独立局数（向上取整）。

    公式（正态近似；零假设下用合并方差，备择假设下用各自方差）：
        n = [ z_{1−alpha/2}·sqrt(2·pbar·(1−pbar)) + z_{power}·sqrt(p1(1−p1) + p2(1−p2)) ]² / (p1 − p2)²
        其中 pbar = (p1 + p2) / 2
    continuity=True 时加 Fleiss 连续性校正：n' = n/4 · (1 + sqrt(1 + 4/(n·|p1−p2|)))²，
    它对应「用 Fisher 精确检验或带校正的卡方检验」时的需要量，比未校正的大。

    PLAN.md §7 的表（约 45 / 100 / 160 / 1350）对应未校正公式，见 plan-table 子命令。
    """
    if not (0.0 < p1 < 1.0 and 0.0 < p2 < 1.0) or p1 == p2:
        raise ValueError("需要 0 < p1, p2 < 1 且 p1 != p2")
    za = _ND.inv_cdf(1.0 - alpha / 2.0)
    zb = _ND.inv_cdf(power)
    pbar = (p1 + p2) / 2.0
    d = abs(p1 - p2)
    n = (za * math.sqrt(2.0 * pbar * (1.0 - pbar))
         + zb * math.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))) ** 2 / (d * d)
    if continuity:
        n = n / 4.0 * (1.0 + math.sqrt(1.0 + 4.0 / (n * d))) ** 2
    return int(math.ceil(n - 1e-9))


def power_normal(p1: float, p2: float, n: int, alpha: float = 0.05) -> float:
    """每臂 n 局、双侧检验时的功效（正态近似，与 n_per_arm 未校正公式互逆）。"""
    za = _ND.inv_cdf(1.0 - alpha / 2.0)
    pbar = (p1 + p2) / 2.0
    d = abs(p1 - p2)
    se0 = math.sqrt(2.0 * pbar * (1.0 - pbar) / n)
    se1 = math.sqrt((p1 * (1.0 - p1) + p2 * (1.0 - p2)) / n)
    if se1 == 0.0:
        return 1.0 if d > 0 else alpha
    return _ND.cdf((d - za * se0) / se1) + _ND.cdf((-d - za * se0) / se1)


def power_exact(p1: float, p2: float, n1: int, n2: int, alpha: float = 0.05,
                rule: str = "fisher", tail_eps: float = 1e-10) -> float:
    """
    精确功效：真实胜率为 p1（第一组 n1 局）和 p2（第二组 n2 局）时，
    按判定规则「宣布两组不同」的概率。枚举所有 (k1, k2)，概率极小的尾部（< tail_eps）略去。

    rule = "fisher"   ：Fisher 双侧 p < alpha
    rule = "newcombe" ：Newcombe 差值区间（置信水平 1−alpha）不含 0
    p1 == p2 时返回的就是该规则实际的第一类错误率。
    """
    def support(n, p):
        out = []
        for k in range(n + 1):
            pr = binom_pmf(k, n, p)
            if pr >= tail_eps:
                out.append((k, pr))
        return out

    s1, s2 = support(n1, p1), support(n2, p2)
    cache: dict[tuple[int, int], bool] = {}
    total = 0.0
    for k1, pr1 in s1:
        for k2, pr2 in s2:
            key = (k1, k2)
            rej = cache.get(key)
            if rej is None:
                if rule == "fisher":
                    rej = fisher_exact(k1, n1, k2, n2) < alpha
                elif rule == "newcombe":
                    _, lo, hi = newcombe_diff(k1, n1, k2, n2, 1.0 - alpha)
                    rej = lo > 0.0 or hi < 0.0
                else:
                    raise ValueError("rule 只能是 fisher 或 newcombe")
                cache[key] = rej
            if rej:
                total += pr1 * pr2
    return total


def mde(p1: float, n: int, alpha: float = 0.05, power: float = 0.80,
        exact: bool = False, rule: str = "fisher") -> float:
    """
    最小可检出效应：基线胜率 p1、每臂 n 局时，功效刚好达到 power 的 p2（> p1）。
    返回 p2；达不到（p2 逼近 1 仍不够）返回 nan。exact=True 用 power_exact（慢，n<=300 可用）。
    """
    def pw(p2):
        return power_exact(p1, p2, n, n, alpha, rule) if exact else power_normal(p1, p2, n, alpha)

    lo, hi = p1 + 1e-6, 1.0 - 1e-6
    if pw(hi) < power:
        return float("nan")
    for _ in range(40 if exact else 60):
        mid = (lo + hi) / 2.0
        if pw(mid) < power:
            lo = mid
        else:
            hi = mid
    return hi


# ----------------------------------------------------------------------------
# 带基础期望的胜率
# ----------------------------------------------------------------------------

def poisson_binomial_pmf(ps: list[float]) -> list[float]:
    """
    各局相互独立、第 i 局胜率为 ps[i] 时，总胜局数 W 的精确分布（动态规划卷积）。
    返回长度 len(ps)+1 的列表，第 w 项是 P(W = w)。
    """
    pmf = [1.0]
    for p in ps:
        if not 0.0 <= p <= 1.0:
            raise ValueError("概率必须在 [0,1] 内")
        nxt = [0.0] * (len(pmf) + 1)
        for w, pr in enumerate(pmf):
            nxt[w] += pr * (1.0 - p)
            nxt[w + 1] += pr * p
        pmf = nxt
    return pmf


def excess_test(wins: list[int], exps: list[float]) -> dict:
    """
    超额胜率检验。wins[i] ∈ {0,1} 是第 i 局是否获胜，exps[i] 是该局的基础期望
    （例如 1/开局队伍数）。零假设：每局胜率恰好等于它的基础期望。

    返回：
      n, wins, expected            局数、实际胜局数、期望胜局数
      excess_per_game              (实际 − 期望) / 局数，即「超额胜率」
      p_upper, p_lower             精确单侧 p 值：P(W >= 实际)、P(W <= 实际)
      p_two_sided                  min(1, 2·min(单侧))
    用途：回答「这支队比『随便分一个队伍』强还是弱」，把队伍数不同的局放在一起比。
    """
    if len(wins) != len(exps):
        raise ValueError("wins 和 exps 长度必须相同")
    n = len(wins)
    w = int(sum(wins))
    pmf = poisson_binomial_pmf(list(exps))
    p_upper = min(1.0, math.fsum(pmf[w:]))
    p_lower = min(1.0, math.fsum(pmf[: w + 1]))
    e = math.fsum(exps)
    return {
        "n": n, "wins": w, "expected": e,
        "excess_per_game": (w - e) / n if n else float("nan"),
        "p_upper": p_upper, "p_lower": p_lower,
        "p_two_sided": min(1.0, 2.0 * min(p_upper, p_lower)),
    }


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def _expit(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def logit_shift(wins: list[int], exps: list[float], conf: float = 0.95) -> dict:
    """
    单参数实力模型：logit(p_i) = logit(e_i) + delta。
    delta = 0 表示「和基础期望一样」；delta > 0 表示每局胜算的赔率被放大 exp(delta) 倍。
    用极大似然估计 delta，用似然比（profile likelihood）给区间：
        { delta : 2·(L(delta_hat) − L(delta)) <= 卡方(1) 的 conf 分位数 }
    全胜或全负时估计值为 ±inf，区间只有一侧有限。

    返回 delta_hat, lo, hi, odds_ratio(=exp(delta_hat)), 以及把 delta 套回各局后的
    平均胜率 mean_p_hat / mean_p_lo / mean_p_hi（便于和基础期望的均值对照）。
    前提：e_i 严格在 (0,1) 内；局与局独立。
    """
    if len(wins) != len(exps) or not wins:
        raise ValueError("wins 和 exps 长度必须相同且非空")
    for e in exps:
        if not 0.0 < e < 1.0:
            raise ValueError("基础期望必须严格在 (0,1) 内")
    offs = [_logit(e) for e in exps]
    w = int(sum(wins))
    n = len(wins)

    def ll(d):
        s = 0.0
        for y, o in zip(wins, offs):
            x = o + d
            # log(expit(x)) = -log1p(exp(-x))，分正负号避免溢出
            if y:
                s += -math.log1p(math.exp(-x)) if x > -30 else x
            else:
                s += -math.log1p(math.exp(x)) if x < 30 else -x
        return s

    def score(d):
        return math.fsum(y - _expit(o + d) for y, o in zip(wins, offs))

    BIG = 40.0
    if w == 0:
        d_hat = -math.inf
        ll_hat = 0.0
    elif w == n:
        d_hat = math.inf
        ll_hat = 0.0
    else:
        lo, hi = -BIG, BIG
        for _ in range(200):
            mid = (lo + hi) / 2.0
            if score(mid) > 0:
                lo = mid
            else:
                hi = mid
        d_hat = (lo + hi) / 2.0
        ll_hat = ll(d_hat)

    crit = z_of(conf) ** 2 / 2.0  # 卡方(1) 分位数的一半

    def bound(side):
        # 在 d_hat 的 side 一侧找 ll(d) = ll_hat − crit 的解
        if side < 0:
            if w == 0:
                return -math.inf
            a, b = -BIG, (d_hat if math.isfinite(d_hat) else BIG)
            # ll 在 (−inf, d_hat) 上单调增
            for _ in range(200):
                mid = (a + b) / 2.0
                if ll(mid) < ll_hat - crit:
                    a = mid
                else:
                    b = mid
            return (a + b) / 2.0
        else:
            if w == n:
                return math.inf
            a, b = (d_hat if math.isfinite(d_hat) else -BIG), BIG
            for _ in range(200):
                mid = (a + b) / 2.0
                if ll(mid) < ll_hat - crit:
                    b = mid
                else:
                    a = mid
            return (a + b) / 2.0

    d_lo, d_hi = bound(-1), bound(+1)

    def mean_p(d):
        if d == -math.inf:
            return 0.0
        if d == math.inf:
            return 1.0
        return math.fsum(_expit(o + d) for o in offs) / n

    return {
        "n": n, "wins": w, "mean_base": math.fsum(exps) / n,
        "delta_hat": d_hat, "delta_lo": d_lo, "delta_hi": d_hi,
        "odds_ratio": math.exp(d_hat) if math.isfinite(d_hat) else (0.0 if d_hat < 0 else math.inf),
        "odds_ratio_lo": math.exp(d_lo) if math.isfinite(d_lo) else 0.0,
        "odds_ratio_hi": math.exp(d_hi) if math.isfinite(d_hi) else math.inf,
        "mean_p_hat": mean_p(d_hat), "mean_p_lo": mean_p(d_lo), "mean_p_hi": mean_p(d_hi),
    }


# ----------------------------------------------------------------------------
# 自测
# ----------------------------------------------------------------------------

def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def selftest(verbose: bool = True) -> int:
    checks: list[tuple[str, bool, str]] = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # --- z 分位数
    ck("z(0.95)=1.959964", _close(z_of(0.95), 1.959963985, 1e-8), f"{z_of(0.95):.9f}")
    ck("z(0.90)=1.644854", _close(z_of(0.90), 1.644853627, 1e-8), f"{z_of(0.90):.9f}")

    # --- Wilson：手算值（见 reports/METRICS.md 附录的推导）和 PLAN §1.3 的三个区间
    lo, hi = wilson(1, 9)
    ck("wilson(1,9)≈(0.0199,0.4350)", _close(lo, 0.01990, 5e-5) and _close(hi, 0.43499, 5e-5), f"{lo:.5f},{hi:.5f}")
    lo, hi = wilson(10, 74)
    ck("wilson(10,74)≈(0.0751,0.2312)", _close(lo, 0.0751, 5e-4) and _close(hi, 0.2312, 5e-4), f"{lo:.5f},{hi:.5f}")
    lo, hi = wilson(35, 53)
    ck("wilson(35,53)≈(0.526,0.773)", _close(lo, 0.526, 1e-3) and _close(hi, 0.773, 1e-3), f"{lo:.5f},{hi:.5f}")
    # Wilson 区间的定义性质：端点处计分统计量恰等于 z
    for (k, n) in [(1, 9), (10, 74), (35, 53), (3, 20), (17, 20)]:
        z = z_of(0.95)
        lo, hi = wilson(k, n)
        p = k / n
        ok = True
        for e in (lo, hi):
            if 0.0 < e < 1.0:
                ok = ok and _close(abs(p - e) / math.sqrt(e * (1 - e) / n), z, 1e-9)
        ck(f"wilson({k},{n}) 端点满足计分方程", ok)
    ck("wilson(0,10) 下界=0", wilson(0, 10)[0] == 0.0 and _close(wilson(0, 10)[1], 0.27753, 5e-5), f"{wilson(0,10)}")
    ck("wilson(10,10) 上界=1", wilson(10, 10)[1] == 1.0 and _close(wilson(10, 10)[0], 1 - 0.27753, 5e-5), f"{wilson(10,10)}")
    ck("wilson(0,0)=(0,1)", wilson(0, 0) == (0.0, 1.0))
    # 对称性：wilson(k,n) 与 wilson(n-k,n) 镜像
    a = wilson(3, 17)
    b = wilson(14, 17)
    ck("wilson 镜像对称", _close(a[0], 1 - b[1], 1e-12) and _close(a[1], 1 - b[0], 1e-12))

    # --- Clopper–Pearson：闭式特例和定义方程
    lo, hi = clopper_pearson(0, 10)
    ck("cp(0,10) 上界 = 1−0.025^(1/10)", lo == 0.0 and _close(hi, 1 - 0.025 ** 0.1, 1e-9), f"{hi:.9f}")
    lo, hi = clopper_pearson(10, 10)
    ck("cp(10,10) 下界 = 0.025^(1/10)", hi == 1.0 and _close(lo, 0.025 ** 0.1, 1e-9), f"{lo:.9f}")
    lo, hi = clopper_pearson(1, 9)
    ck("cp(1,9)≈(0.0028,0.4825)", _close(lo, 0.00281, 5e-5) and _close(hi, 0.48250, 5e-5), f"{lo:.5f},{hi:.5f}")
    ck("cp(1,9) 端点满足定义方程",
       _close(binom_sf(1, 9, lo), 0.025, 1e-9) and _close(binom_cdf(1, 9, hi), 0.025, 1e-9))
    for (k, n) in [(1, 9), (10, 74), (35, 53)]:
        w, c = wilson(k, n), clopper_pearson(k, n)
        ck(f"cp({k},{n}) 比 wilson 宽", (c[1] - c[0]) > (w[1] - w[0]))

    # --- Newcombe 方法 10：论文里的例子 56/70 对 48/80 -> 差 0.2，区间 (0.0524, 0.3339)
    d, lo, hi = newcombe_diff(48, 80, 56, 70)
    ck("newcombe 56/70−48/80 = 0.2 (0.0524,0.3339)",
       _close(d, 0.2, 1e-12) and _close(lo, 0.0524, 5e-4) and _close(hi, 0.3339, 5e-4), f"{d:.4f},{lo:.4f},{hi:.4f}")
    d2, lo2, hi2 = newcombe_diff(56, 70, 48, 80)
    ck("newcombe 交换两组后区间取负", _close(d2, -d, 1e-12) and _close(lo2, -hi, 1e-12) and _close(hi2, -lo, 1e-12))
    d, lo, hi = newcombe_diff(0, 10, 0, 10)
    ck("newcombe 0/10 对 0/10 含 0 且对称", _close(d, 0.0, 1e-12) and _close(lo, -hi, 1e-12) and hi > 0.2)
    d, lo, hi = newcombe_diff(5, 10, 5, 10)
    ck("newcombe 相同数据含 0", lo < 0 < hi)

    # --- Fisher 精确检验
    ck("fisher [[3,1],[1,3]] = 0.485714", _close(fisher_exact(3, 4, 1, 4), 34 / 70, 1e-9), f"{fisher_exact(3,4,1,4):.6f}")
    # 茶会经典表 [[4,0],[0,4]]：双侧 p = 2/70
    ck("fisher [[4,0],[0,4]] = 2/70", _close(fisher_exact(4, 4, 0, 4), 2 / 70, 1e-12))
    ck("fisher 相同比例 = 1", _close(fisher_exact(5, 10, 5, 10), 1.0, 1e-12))
    ck("fisher 对称", _close(fisher_exact(1, 9, 10, 74), fisher_exact(10, 74, 1, 9), 1e-12))
    # 超几何概率之和 = 1
    tot = math.fsum(math.exp(_log_hypergeom(a, 9, 74, 11)) for a in range(0, 10))
    ck("超几何概率归一", _close(tot, 1.0, 1e-10), f"{tot:.12f}")

    # --- 贝叶斯 P(B > A)
    ck("bayes 相同数据 = 0.5", _close(prob_b_beats_a(3, 10, 3, 10), 0.5, 1e-6), f"{prob_b_beats_a(3,10,3,10):.7f}")
    for (kA, nA, kB, nB) in [(1, 9, 10, 74), (10, 74, 35, 53), (0, 5, 5, 5), (2, 30, 9, 30), (14, 100, 30, 100)]:
        num = prob_b_beats_a(kA, nA, kB, nB)
        closed = _prob_b_beats_a_closed(kA, nA, kB, nB)
        ck(f"bayes 数值积分 = 闭式解 ({kA}/{nA} vs {kB}/{nB})", _close(num, closed, 2e-6), f"{num:.7f} vs {closed:.7f}")
    ck("bayes 互补", _close(prob_b_beats_a(2, 30, 9, 30) + prob_b_beats_a(9, 30, 2, 30), 1.0, 2e-6))
    # 无数据 + 均匀先验：两边都是 U(0,1)，P = 0.5
    ck("bayes 无数据 = 0.5", _close(prob_b_beats_a(0, 0, 0, 0), 0.5, 1e-6))

    # --- 样本量：PLAN §7 的四行（未校正公式）
    ck("n(0.135→0.40)=43", n_per_arm(0.135, 0.40) == 43, str(n_per_arm(0.135, 0.40)))
    ck("n(0.135→0.30)=97", n_per_arm(0.135, 0.30) == 97, str(n_per_arm(0.135, 0.30)))
    ck("n(0.66→0.80)=157", n_per_arm(0.66, 0.80) == 157, str(n_per_arm(0.66, 0.80)))
    ck("n(0.66→0.71)=1354", n_per_arm(0.66, 0.71) == 1354, str(n_per_arm(0.66, 0.71)))
    ck("n 对称", n_per_arm(0.3, 0.5) == n_per_arm(0.5, 0.3))
    ck("连续性校正使 n 变大", n_per_arm(0.135, 0.40, continuity=True) > n_per_arm(0.135, 0.40))
    # 教科书例：p1=0.5, p2=0.6, alpha=0.05, power=0.8 -> 388（未校正）
    ck("n(0.5→0.6)=388", n_per_arm(0.5, 0.6) == 388, str(n_per_arm(0.5, 0.6)))
    # 功效与样本量互逆
    for (p1, p2) in [(0.135, 0.40), (0.135, 0.30), (0.66, 0.80), (0.5, 0.6)]:
        n = n_per_arm(p1, p2)
        ck(f"power_normal 在 n={n} 处 ≥0.80 且 n−1 处 <0.80 ({p1}→{p2})",
           power_normal(p1, p2, n) >= 0.80 and power_normal(p1, p2, n - 1) < 0.80,
           f"{power_normal(p1,p2,n):.4f},{power_normal(p1,p2,n-1):.4f}")
    # 精确功效：零假设下的实际第一类错误率不超过 alpha（Fisher 保守）
    t1 = power_exact(0.135, 0.135, 40, 40)
    ck("power_exact 零假设下 ≤ alpha（Fisher 保守）", 0.0 < t1 <= 0.05, f"{t1:.4f}")
    pe = power_exact(0.135, 0.40, 45, 45)
    ck("power_exact(0.135,0.40,45) 在 0.6~0.9 之间", 0.6 < pe < 0.9, f"{pe:.4f}")
    ck("power_exact 随 n 增大", power_exact(0.135, 0.40, 60, 60) > pe)
    m = mde(0.135, 100)
    ck("mde 与 n_per_arm 一致", n_per_arm(0.135, m) in (100, 101), f"mde={m:.4f} n={n_per_arm(0.135, m)}")

    # --- Poisson 二项分布与超额检验
    pmf = poisson_binomial_pmf([0.5] * 6)
    ck("poisson-binomial 等概率时 = 二项分布", all(_close(pmf[k], binom_pmf(k, 6, 0.5), 1e-12) for k in range(7)))
    pmf = poisson_binomial_pmf([0.1, 0.5, 0.9])
    ck("poisson-binomial 归一", _close(sum(pmf), 1.0, 1e-12))
    ck("poisson-binomial P(0)=0.9*0.5*0.1", _close(pmf[0], 0.045, 1e-12) and _close(pmf[3], 0.045, 1e-12))
    r = excess_test([1, 0, 0, 0], [0.25] * 4)
    ck("excess_test 期望=实际时超额=0", _close(r["excess_per_game"], 0.0, 1e-12) and _close(r["expected"], 1.0, 1e-12))
    r = excess_test([0] * 9, [0.5] * 9)
    ck("excess_test 全负 p_lower = 0.5^9", _close(r["p_lower"], 0.5 ** 9, 1e-12) and _close(r["p_upper"], 1.0, 1e-12))

    # --- logit 平移模型
    # 基础期望全相同时，delta_hat 的闭式解：logit(w/n) − logit(e)
    wins = [1] * 3 + [0] * 7
    r = logit_shift(wins, [0.2] * 10)
    ck("logit_shift 同质时 = logit(3/10)−logit(0.2)",
       _close(r["delta_hat"], _logit(0.3) - _logit(0.2), 1e-9) and _close(r["mean_p_hat"], 0.3, 1e-9),
       f"{r['delta_hat']:.6f}")
    ck("logit_shift 区间包住估计值", r["delta_lo"] < r["delta_hat"] < r["delta_hi"])
    # 同质时似然比区间端点满足 2*(ll_hat − ll) = 3.8415
    def ll_binom(p):
        return 3 * math.log(p) + 7 * math.log(1 - p)
    for d in (r["delta_lo"], r["delta_hi"]):
        p = _expit(_logit(0.2) + d)
        ck("logit_shift 区间端点满足似然比方程", _close(2 * (ll_binom(0.3) - ll_binom(p)), z_of(0.95) ** 2, 1e-6))
    r0 = logit_shift([0] * 5, [0.3] * 5)
    ck("logit_shift 全负：估计 −inf，上界有限", r0["delta_hat"] == -math.inf and math.isfinite(r0["delta_hi"]) and r0["mean_p_hat"] == 0.0)
    # 全负时上界的闭式：(1−p)^5 = exp(−1.9207) -> p = 1 − exp(−1.9207/5)
    p_hi = 1 - math.exp(-(z_of(0.95) ** 2 / 2) / 5)
    ck("logit_shift 全负上界闭式", _close(r0["mean_p_hi"], p_hi, 1e-6), f"{r0['mean_p_hi']:.6f} vs {p_hi:.6f}")
    # 异质：胜局的得分方程 sum(y − p) = 0
    wins = [1, 0, 0, 1, 0, 0, 0, 1]
    exps = [0.5, 0.5, 0.25, 0.25, 0.2, 0.2, 0.1, 0.1]
    r = logit_shift(wins, exps)
    resid = sum(y - _expit(_logit(e) + r["delta_hat"]) for y, e in zip(wins, exps))
    ck("logit_shift 异质时得分方程为 0", _close(resid, 0.0, 1e-8), f"{resid:.2e}")

    bad = [c for c in checks if not c[1]]
    if verbose:
        for name, ok, detail in checks:
            print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
        print(f"\nselftest: {len(checks) - len(bad)}/{len(checks)} 通过")
    return 1 if bad else 0


# ----------------------------------------------------------------------------
# 命令行
# ----------------------------------------------------------------------------

def _pct(x: float) -> str:
    return f"{100.0 * x:.1f}%"


def plan_table() -> dict:
    """重算 PLAN.md §1.3（三个区间）和 §7（样本量表），并给出带校正和精确功效的对照。"""
    out: dict = {"intervals": [], "sample_size": []}
    for label, k, n in [("自动局 1/9", 1, 9), ("c116 白天 10/74", 10, 74), ("c110 35/53", 35, 53)]:
        w = wilson(k, n)
        c = clopper_pearson(k, n)
        out["intervals"].append({
            "label": label, "k": k, "n": n, "p": k / n,
            "wilson95": [w[0], w[1]], "clopper_pearson95": [c[0], c[1]],
        })
    for p1, p2, plan in [(0.135, 0.40, 45), (0.135, 0.30, 100), (0.66, 0.80, 160), (0.66, 0.71, 1350)]:
        n0 = n_per_arm(p1, p2)
        n1 = n_per_arm(p1, p2, continuity=True)
        row = {"p1": p1, "p2": p2, "plan_says": plan, "n_uncorrected": n0, "n_continuity": n1,
               "power_normal_at_plan": power_normal(p1, p2, plan)}
        if plan <= 200:
            row["power_exact_fisher_at_plan"] = power_exact(p1, p2, plan, plan)
            row["power_exact_fisher_at_n_continuity"] = power_exact(p1, p2, n1, n1)
        out["sample_size"].append(row)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[1], argv[2:]
    if cmd == "selftest":
        return selftest()
    if cmd == "wilson":
        k, n = int(args[0]), int(args[1])
        conf = float(args[2]) if len(args) > 2 else 0.95
        lo, hi = wilson(k, n, conf)
        print(f"{k}/{n} = {_pct(k / n) if n else 'NA'}  Wilson {int(conf*100)}%: {_pct(lo)} ~ {_pct(hi)}")
        return 0
    if cmd == "cp":
        k, n = int(args[0]), int(args[1])
        conf = float(args[2]) if len(args) > 2 else 0.95
        lo, hi = clopper_pearson(k, n, conf)
        print(f"{k}/{n} = {_pct(k / n) if n else 'NA'}  Clopper-Pearson {int(conf*100)}%: {_pct(lo)} ~ {_pct(hi)}")
        return 0
    if cmd == "diff":
        k1, n1, k2, n2 = (int(x) for x in args[:4])
        conf = float(args[4]) if len(args) > 4 else 0.95
        d, lo, hi = newcombe_diff(k1, n1, k2, n2, conf)
        print(f"第二组 {k2}/{n2} − 第一组 {k1}/{n1} = {100*d:+.1f} 个百分点  "
              f"Newcombe {int(conf*100)}%: {100*lo:+.1f} ~ {100*hi:+.1f}")
        return 0
    if cmd == "fisher":
        k1, n1, k2, n2 = (int(x) for x in args[:4])
        print(f"Fisher 双侧 p = {fisher_exact(k1, n1, k2, n2):.4f}")
        return 0
    if cmd == "bayes":
        k1, n1, k2, n2 = (int(x) for x in args[:4])
        print(f"P(第二组真实胜率 > 第一组) = {prob_b_beats_a(k1, n1, k2, n2):.4f}（均匀先验）")
        return 0
    if cmd == "n":
        p1, p2 = float(args[0]), float(args[1])
        alpha = float(args[2]) if len(args) > 2 else 0.05
        power = float(args[3]) if len(args) > 3 else 0.80
        print(f"{_pct(p1)} → {_pct(p2)}  alpha={alpha} power={power}: "
              f"每臂 {n_per_arm(p1, p2, alpha, power)} 局（未校正），"
              f"{n_per_arm(p1, p2, alpha, power, True)} 局（连续性校正）")
        return 0
    if cmd == "power":
        p1, p2, n = float(args[0]), float(args[1]), int(args[2])
        alpha = float(args[3]) if len(args) > 3 else 0.05
        print(f"{_pct(p1)} → {_pct(p2)} 每臂 {n} 局: 功效 {power_normal(p1, p2, n, alpha):.3f}（正态近似），"
              f"{power_exact(p1, p2, n, n, alpha):.3f}（Fisher 精确），"
              f"{power_exact(p1, p2, n, n, alpha, 'newcombe'):.3f}（Newcombe 区间不含 0）")
        return 0
    if cmd == "mde":
        p1, n = float(args[0]), int(args[1])
        m = mde(p1, n)
        print(f"基线 {_pct(p1)}、每臂 {n} 局、功效 0.80：最小可检出 {_pct(m)}（提升 {100*(m-p1):+.1f} 个百分点，正态近似）")
        return 0
    if cmd == "plan-table":
        print(json.dumps(plan_table(), ensure_ascii=False, indent=2))
        return 0
    print(f"不认识的子命令：{cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
