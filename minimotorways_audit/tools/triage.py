import os, hashlib, math, glob, json, datetime, subprocess, re
import pefile
root = "Mini Motorways"
files = sorted([p for p in glob.glob(root + "/**/*", recursive=True) if os.path.isfile(p) and open(p,'rb').read(2)==b'MZ'])
def entropy(b):
    if not b: return 0
    c=[0]*256
    for x in b: c[x]+=1
    n=len(b); return -sum(v/n*math.log2(v/n) for v in c if v)
def sigcheck(p):
    r=subprocess.run(['osslsigncode','verify','-in',p],capture_output=True,text=True,timeout=60)
    out=r.stdout+r.stderr
    if 'No signature found' in out: return 'UNSIGNED'
    subj=re.findall(r'Subject: (.*)',out)
    signer=subj[0] if subj else '?'
    cn=re.search(r'CN=([^/,]+)',signer)
    ok = 'Signature verification: ok' in out
    digest_ok = not re.search(r'MISMATCH',out)
    return f"{'VALID' if ok else 'INVALID'}{'' if digest_ok else ' (DIGEST MISMATCH = file modified after signing)'} signer={cn.group(1) if cn else signer[:60]}"
rows=[]
for p in files:
    d=open(p,'rb').read()
    pe=pefile.PE(data=d, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    is_net = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14].VirtualAddress != 0
    vi={}
    if hasattr(pe,'FileInfo'):
        for fi in pe.FileInfo:
            for e in fi:
                if hasattr(e,'StringTable'):
                    for st in e.StringTable:
                        for k,v in st.entries.items(): vi[k.decode(errors='ignore')]=v.decode(errors='ignore')
    ts=datetime.datetime.fromtimestamp(pe.FILE_HEADER.TimeDateStamp, datetime.UTC).strftime('%Y-%m-%d')
    secs=[(s.Name.rstrip(b'\0').decode(errors='ignore'), round(entropy(s.get_data()),2)) for s in pe.sections]
    rows.append(dict(path=p, size=len(d), md5=hashlib.md5(d).hexdigest(), sha256=hashlib.sha256(d).hexdigest(), net=is_net, sig=sigcheck(p), ts=ts,
        company=vi.get('CompanyName',''), product=vi.get('ProductName',''), desc=vi.get('FileDescription',''), ver=vi.get('FileVersion',''), orig=vi.get('OriginalFilename',''), secs=secs))
json.dump(rows, open('/home/ubuntu/mal/triage.json','w'), indent=1)
print("=== NATIVE PE FILES")
for r in rows:
    if r['net']: continue
    print(f"\n### {r['path']}  ({r['size']} B)  built {r['ts']}\n  md5 {r['md5']}\n  sig: {r['sig']}\n  ver: {r['company']} | {r['product']} | {r['desc']} | {r['ver']} | orig={r['orig']}\n  sections(entropy): {r['secs']}")
print("\n\n=== MANAGED (.NET) ASSEMBLIES")
for r in rows:
    if not r['net']: continue
    print(f"  {os.path.basename(r['path']):52s} {r['ts']}  {r['sig'][:58]:58s} | {r['company'][:28]}")
