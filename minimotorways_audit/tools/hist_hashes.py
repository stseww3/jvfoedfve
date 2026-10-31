import hashlib, subprocess, sys
repo, out = sys.argv[1], sys.argv[2]
revs = subprocess.run(['git','-C',repo,'rev-list','--all'],capture_output=True,text=True).stdout.split()
seen = {}
for r in revs:
    files = subprocess.run(['git','-C',repo,'ls-tree','-r','--format=%(objectname) %(path)',r],capture_output=True,text=True).stdout.splitlines()
    for line in files:
        oid, path = line.split(' ',1)
        if not path.endswith('.cs') or oid in seen: continue
        body = subprocess.run(['git','-C',repo,'cat-file','blob',oid],capture_output=True).stdout
        lf = body.replace(b'\r\n', b'\n'); crlf = lf.replace(b'\n', b'\r\n')
        variants = {'raw': body, 'lf': lf, 'crlf': crlf}
        for k in list(variants):
            v = variants[k]
            if not v.startswith(b'\xef\xbb\xbf'): variants[k + '+bom'] = b'\xef\xbb\xbf' + v
        seen[oid] = (path, r, {k: hashlib.sha256(v).hexdigest() for k, v in variants.items()})
with open(out,'w') as o:
    for oid,(path,r,hs) in seen.items():
        for k,h in hs.items(): o.write(f'{h}\t{k}\t{r[:10]}\t{path}\n')
print(repo, len(revs), 'commits', len(seen), 'distinct .cs blobs')
