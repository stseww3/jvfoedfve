#!/usr/bin/env python3
# replay_stream.py — 把对局包里的 replay.txt（实况分享串）解码成逐拍的指令流。纯 Python，不要地图、不跑引擎、不跑 node。
# 解码步骤逐字照 /agent/repos/c136-data/src/tools/replay_cmds.mjs（它取自 src/sim/tools/c102-replay-lib.mjs）移植，只读。
#   id=0 出生(x,y)  id=1 陆攻(比例/1024, 目标)  id=2 捐款(比例, 收款人)  id=3 船(比例, 水格<<3|方向)  id=8/9 离场
#   拍号：选点阶段占 jJ+1 步（真人 ≤2:30，≤50:40，否则 50），之后一步一拍；选点阶段的指令拍号为负。
# 用法：python3 scripts/replay_stream.py <局号>            （打印头信息和各类指令条数）
#       python3 scripts/replay_stream.py <局号> --tsv      （打印 tick id player a b）
#       python3 scripts/replay_stream.py <局号> --check    （和 tmp/truth/<局号>/cmd.tsv 逐条对账；只有跑过真引擎事实表的局能对）
import sys, os, collections
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('C136_DATA', '/agent/repos/c136-data')


class Bits:
    def __init__(self, raw):
        ga = raw.strip()
        eq = ga.find('=')
        if eq >= 0:
            ga = ga[eq + 1:]
        abv = [0] * 78
        abv[50] = 37
        for i in range(10):
            abv[i + 3] = i + 1
        for i in range(26):
            abv[i + 20] = i + 11
            abv[i + 52] = i + 38
        vals = []
        for ch in ga:
            o = ord(ch)
            if not (48 <= o <= 57 or 65 <= o <= 90 or 97 <= o <= 122 or ch in '_-'):
                o = 45
            vals.append(abv[o - 45])
        # 每个字符 6 位，拼成一个大整数再按位取
        n = 0
        for v in vals:
            n = (n << 6) | v
        self.total = 6 * len(vals)
        pad = (-self.total) % 8
        self.n = n << pad
        self.size = self.total + pad
        self.pos = 0

    def take(self, k):
        if k == 0:
            return 0
        shift = self.size - self.pos - k
        self.pos += k
        if shift < 0:
            raise ValueError('replay 串读过头了')
        return (self.n >> shift) & ((1 << k) - 1)

    def text(self, k):
        ln = self.take(k)
        return ''.join(chr(self.take(16)) for _ in range(ln))

    def arr(self, k, bits, minlen):
        fe = self.take(k)
        if not fe:
            return None
        d = [self.take(bits) for _ in range(fe)]
        if d[-1]:
            d += [d[-1]] * max(0, minlen - fe)
        else:
            d += [0] * max(0, minlen - fe)
        return d

    def texts(self, k, k2, minlen):
        fe = self.take(k)
        if not fe:
            return None
        d = [self.text(k2) for _ in range(fe)]
        d += [d[-1]] * max(0, minlen - fe)
        return d[:max(fe, minlen)], fe


def decode(raw):
    b = Bits(raw)
    vu = collections.OrderedDict()
    vu['version'], vu['vs'], vu['statedSize'] = b.take(12), b.take(12), b.take(31)
    vu['mapType'] = b.take(2)
    vu['mapProceduralIndex'] = b.take(8)
    vu['mapRealisticIndex'] = b.take(8)
    vu['mapSeed'] = b.take(14)
    vu['mapName'] = b.text(5)
    if vu['mapType'] == 2:
        b.pos += 6 * b.take(30)
    vu['passableWater'] = b.take(1)
    vu['passableMountains'] = b.take(1)
    vu['playerCount'] = b.take(10)
    vu['humanCount'] = b.take(10)
    vu['selectedPlayer'] = b.take(9)
    vu['gameMode'] = b.take(1)
    vu['playerMode'] = b.take(2)
    vu['battleRoyaleMode'] = b.take(2)
    vu['numberTeams'] = b.take(4)
    vu['isZombieMode'] = b.take(1)
    vu['isContest'] = b.take(1)
    vu['isReplay'] = b.take(1)
    b.arr(2, 14, 2)
    vu['colorsType'] = b.take(1)
    vu['colorsPersonalized'] = b.take(1)
    b.arr(10, 18, 512)
    vu['selectableColor'] = b.take(1)
    vu['teamPlayerCount'] = b.arr(4, 10, 9)
    vu['neutralBots'] = b.take(1)
    vu['botDifficultyType'] = b.take(2)
    vu['botDifficultyValue'] = b.take(4)
    b.arr(4, 4, 9)
    b.arr(10, 4, 512)
    vu['spawningType'] = b.take(2)
    vu['spawningSeed'] = b.take(14)
    b.arr(11, 12, 1024)
    vu['selectableSpawn'] = b.take(1)
    vu['playerNamesType'] = b.take(2)
    nm = b.texts(10, 5, 512)
    vu['names'] = nm[0][:nm[1]] if nm else []
    vu['selectableName'] = b.take(1)
    for _ in range(3):
        b.take(2)
        b.take(8)
        b.arr(10, 8, 512)
    b.take(2)
    b.take(11)
    b.arr(10, 11, 512)
    b.arr(10, 30, 0)
    ek, n_cmd, n_blk = b.take(5), b.take(30), b.take(30)
    cmds = []
    for _ in range(n_cmd):
        cid, player = b.take(4), b.take(9)
        dx = dz = 0
        if cid == 0:
            dx = b.take(22)
        elif cid == 1:
            dx, dz = b.take(10), b.take(10)
        elif cid == 2:
            dx, dz = b.take(10), b.take(9)
        elif cid == 3:
            dx, dz = b.take(10), b.take(27)
        elif cid == 4:
            dx, dz = b.take(10), b.take(16)
        elif cid in (5, 6):
            dx = b.take(10)
        elif cid == 7:
            dx = b.take(1)
        elif cid == 10:
            dx, dz = b.take(20), b.take(22)
        cmds.append((cid, player, dx, dz))
    blocks = [(b.take(1), b.take(ek)) for _ in range(n_blk)]
    H = vu['humanCount']
    jj = 30 if H <= 2 else 40 if H <= 50 else 50
    spawn_steps = jj + 1 if vu['selectableSpawn'] else 0
    out = []
    step = iw = 0
    for is_cmd, n in blocks:
        if is_cmd:
            for a in range(iw, iw + n):
                c = cmds[a]
                out.append((step - spawn_steps, c[0], c[1], c[2], c[3]))
            iw += n
            step += 1
        else:
            step += max(1, n)
    vu['spawnSteps'] = spawn_steps
    vu['totalTicks'] = step - spawn_steps
    vu['bitsUsed'], vu['totalBits'] = b.pos, b.total
    return vu, out


def load(mid):
    for sub in ('bundles', 'validation_bundles'):
        p = os.path.join(DATA, sub, mid, 'replay.txt')
        if os.path.exists(p):
            return decode(open(p, encoding='utf8').read())
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__ or '用法见脚本开头')
        return
    mid = args[0]
    r = load(mid)
    if not r:
        print('%s 没有 replay.txt' % mid)
        return
    vu, cmds = r
    if '--tsv' in sys.argv:
        print('tick\tid\tplayer\ta\tb')
        for c in cmds:
            print('\t'.join(str(x) for x in c))
        return
    if '--check' in sys.argv:
        fp = os.path.join(ROOT, 'tmp', 'truth', mid, 'cmd.tsv')
        if not os.path.exists(fp):
            print('%s 没有 tmp/truth/%s/cmd.tsv，对不了账' % (mid, mid))
            return
        truth = collections.Counter()
        hdr = None
        for ln in open(fp, encoding='utf8'):
            c = ln.rstrip('\n').split('\t')
            if hdr is None:
                hdr = c
                continue
            d = dict(zip(hdr, c))
            if int(d['t']) > 0 or int(d['id']) != 0:
                truth[(int(d['t']), int(d['id']), int(d['p']), int(d['a']), int(d['b'] or 0))] += 1
        mine = collections.Counter((c[0], c[1], c[2], c[3], c[4]) for c in cmds if c[0] > 0 or c[1] != 0)
        both = sum((truth & mine).values())
        print('%s 对账（拍 >0 的全部指令；出生指令不比）：真引擎事实表 %d 条，本脚本 %d 条，逐条相同（拍、类型、号、两个参数）%d 条' % (
            mid, sum(truth.values()), sum(mine.values()), both))
        return
    cnt = collections.Counter(c[1] for c in cmds)
    print('%s：真人位 %d，玩家位 %d，队数字段 %d，选点 %d 步，共 %d 拍；指令 %d 条（出生 %d、陆攻 %d、捐款 %d、船 %d、其他 %d）；读了 %d / %d 位' % (
        mid, vu['humanCount'], vu['playerCount'], vu['numberTeams'], vu['spawnSteps'], vu['totalTicks'], len(cmds),
        cnt[0], cnt[1], cnt[2], cnt[3], len(cmds) - cnt[0] - cnt[1] - cnt[2] - cnt[3], vu['bitsUsed'], vu['totalBits']))
    fix = lambda n: n.encode('utf-16', 'surrogatepass').decode('utf-16', 'replace')
    print('  名字：' + '、'.join('%d=%s' % (i, fix(n)) for i, n in enumerate(vu['names'][:vu['humanCount']])))


if __name__ == '__main__':
    main()
