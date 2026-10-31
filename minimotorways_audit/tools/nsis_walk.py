import lzma, os, struct, sys
from multiprocessing import Pool

SRC = sys.argv[1]
OUT = sys.argv[2]
START = int(sys.argv[3])
MAXC = 15 * 1024 * 1024
os.makedirs(OUT, exist_ok=True)


def walk():
    blocks = []
    size = os.path.getsize(SRC)
    with open(SRC, 'rb') as f:
        off = START
        while off + 4 <= size:
            f.seek(off)
            raw = struct.unpack('<I', f.read(4))[0]
            comp, n = bool(raw & 0x80000000), raw & 0x7FFFFFFF
            if off + 4 + n > size:
                break
            blocks.append((len(blocks), off, comp, n))
            off += 4 + n
    return blocks


def decomp(data, limit=-1):
    props, dsz = data[0], struct.unpack('<I', data[1:5])[0]
    lc, rem = props % 9, props // 9
    lp, pb = rem % 5, rem // 5
    d = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{'id': lzma.FILTER_LZMA1, 'dict_size': dsz, 'lc': lc, 'lp': lp, 'pb': pb}])
    return d.decompress(data[5:], max_length=limit)


def work(b):
    idx, off, comp, n = b
    if n > MAXC or n < 64:
        return None
    with open(SRC, 'rb') as f:
        f.seek(off + 4)
        data = f.read(n)
    try:
        head = decomp(data, 64) if comp else data[:64]
        if head[:2] != b'MZ':
            return None
        full = decomp(data) if comp else data
    except Exception as e:
        return (idx, 'ERR ' + str(e))
    if b'BSJB' not in full:
        return None
    p = os.path.join(OUT, f'{idx:06d}.dll')
    with open(p, 'wb') as o:
        o.write(full)
    return (idx, len(full))


if __name__ == '__main__':
    blocks = walk()
    print('blocks', len(blocks), 'last end', blocks[-1][1] + 4 + blocks[-1][3], flush=True)
    with Pool(os.cpu_count()) as p:
        res = [r for r in p.imap_unordered(work, blocks, chunksize=16) if r]
    print('managed PEs saved', sum(1 for r in res if isinstance(r[1], int)), 'errors', sum(1 for r in res if isinstance(r[1], str)))
