"""Hash every file stored in the Unity Editor NSIS installer.

NSIS stores each file as its own block without its name, so files are
identified by content: every block is decompressed and SHA-256 hashed, and
blocks that are gzip'd tarballs (the Editor's bundled package .tgz files) are
opened so every member file is hashed too.

usage: nsis_hash.py <UnitySetup.exe> <out.tsv> <first_block_offset>
out.tsv columns: sha256, block index, size, tar member path ('-' for plain blocks)
"""
import hashlib
import io
import lzma
import os
import struct
import sys
import tarfile
from multiprocessing import Pool

SRC = sys.argv[1]
OUT = sys.argv[2]
START = int(sys.argv[3])
MAXC = 400 * 1024 * 1024


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


def decomp(data):
    props, dsz = data[0], struct.unpack('<I', data[1:5])[0]
    lc, rem = props % 9, props // 9
    lp, pb = rem % 5, rem // 5
    d = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{'id': lzma.FILTER_LZMA1, 'dict_size': dsz, 'lc': lc, 'lp': lp, 'pb': pb}])
    return d.decompress(data[5:])


def work(b):
    idx, off, comp, n = b
    if n > MAXC or n < 1:
        return [(None, idx, n, 'SKIPPED-SIZE')]
    with open(SRC, 'rb') as f:
        f.seek(off + 4)
        data = f.read(n)
    try:
        full = decomp(data) if comp else data
    except Exception as e:
        return [(None, idx, n, 'ERR ' + str(e))]
    out = [(hashlib.sha256(full).hexdigest(), idx, len(full), '-')]
    if full[:2] == b'\x1f\x8b':
        try:
            with tarfile.open(fileobj=io.BytesIO(full), mode='r:gz') as t:
                for m in t:
                    if m.isfile():
                        body = t.extractfile(m).read()
                        out.append((hashlib.sha256(body).hexdigest(), idx, len(body), m.name))
        except Exception as e:
            out.append((None, idx, len(full), 'TARERR ' + str(e)))
    return out


if __name__ == '__main__':
    blocks = walk()
    print('blocks', len(blocks), flush=True)
    n_err = 0
    with Pool(os.cpu_count()) as p, open(OUT, 'w') as o:
        for res in p.imap_unordered(work, blocks, chunksize=8):
            for h, idx, size, name in res:
                if h is None:
                    n_err += 1
                    print('problem', idx, size, name, flush=True)
                    continue
                o.write(f'{h}\t{idx}\t{size}\t{name}\n')
    print('done, problems:', n_err)
