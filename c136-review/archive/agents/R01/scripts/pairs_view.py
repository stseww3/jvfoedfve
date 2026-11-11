import csv,json,sys
from collections import defaultdict
mid=sys.argv[1]
meta=json.load(open(f'out/{mid}/resim_meta.json'))
names=meta['names']; teams=meta['teams']; H=meta['humans']; squad={int(v):k for k,v in meta['squad'].items()}
def tm(p): return teams[str(p)] if isinstance(teams,dict) else teams[p]
def nm(p):
    p=int(p)
    if p in squad: return f"{squad[p]}(T{tm(p)})"
    if p<H: return f"{names[p]}/T{tm(p)}"
    return f"AI#{p}"
rows=list(csv.DictReader(open(f'out/{mid}/resim_pairs.csv')))
mode=sys.argv[2]
for v in sys.argv[3:]:
    v=int(v)
    agg=defaultdict(int); last={}; first={}
    for r in rows:
        key='victim' if mode=='victim' else 'attacker'
        oth='attacker' if mode=='victim' else 'victim'
        if int(r[key])==v:
            o=int(r[oth]); agg[o]+=int(r['px']); last[o]=r['t1']; first.setdefault(o,r['t0'])
    print(mode, nm(v), [(nm(k),c,first[k],last[k]) for k,c in sorted(agg.items(), key=lambda x:-x[1])[:8]])
