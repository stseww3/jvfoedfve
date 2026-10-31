import re, sys
src = open(sys.argv[1], encoding='utf-8', errors='ignore').read()
funcs = re.split(r'\n(?=// ===== )', src)
apis = sys.argv[2].split(',')
for api in apis:
    hits = []
    for f in funcs:
        m = re.match(r'// ===== (\S+) @ (\S+)', f)
        if not m or m.group(1) == api: continue
        if re.search(r'\b' + api + r'\s*\(', f):
            lits = sorted(set(re.findall(r'"([^"\n]{3,80})"', f)))
            lits = [l for l in lits if not l.startswith('C:\\Users')][:8]
            hits.append(f"{m.group(1)}{(' lits='+str(lits)) if lits else ''}")
    print(f"== {api} ({len(hits)} funcs): " + " | ".join(hits)[:900])
