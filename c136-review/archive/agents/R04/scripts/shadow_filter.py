#!/usr/bin/env python3
# shadow_filter.py — 拆队 / 掉线局用：把 tmp/shadow/<局号>/ 里的影子结果裁成「只留指定的号」，
#   原来的全量结果先挪到 tmp/shadow/<局号>.all/（已经有就不再动它）。
# 用法：python3 scripts/shadow_filter.py <局号> --keep id,id,… [--cut id:拍,id:拍,…]
#   --keep  留下来的号（引擎编号；B 组影子表里号这一列就是引擎编号）
#   --cut   这些号只留到指定的拍为止（含）——客户端停摆的号，停摆以后影子还在替它「想」，那些行不能算进账里
# 之后各张表（latency_ledger.py、exec_gap.py、core_gate_tally.py …）读到的就只是这些号。
import sys, os, json, shutil
sys.dont_write_bytecode = True
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def main():
    a = sys.argv[1:]
    mid = a[0]
    keep = set(a[a.index('--keep') + 1].split(','))
    cut = {}
    if '--cut' in a:
        for kv in a[a.index('--cut') + 1].split(','):
            k, v = kv.split(':')
            cut[k] = int(v)
    cur = os.path.join(ROOT, 'tmp', 'shadow', mid)
    full = cur + '.all'
    if not os.path.isdir(full):
        shutil.copytree(cur, full)
    os.makedirs(cur, exist_ok=True)
    stat = {}
    for name, col in (('intents.tsv', 2), ('rows.tsv', 1)):
        with open(os.path.join(full, name), encoding='utf8') as f:
            lines = f.read().split('\n')
        out = [lines[0]]
        n0 = n1 = 0
        for l in lines[1:]:
            if not l:
                continue
            n0 += 1
            c = l.split('\t')
            b = c[col]
            if b not in keep:
                continue
            if b in cut and int(c[0]) > cut[b]:
                continue
            out.append(l)
            n1 += 1
        with open(os.path.join(cur, name), 'w', encoding='utf8') as f:
            f.write('\n'.join(out) + '\n')
        stat[name] = (n0, n1)
    chk = json.load(open(os.path.join(full, 'check.json'), encoding='utf8'))
    chk['bots'] = [b for b in chk['bots'] if b['bot'] in keep]
    chk['filtered'] = {'keep': sorted(keep, key=int), 'cut': cut}
    json.dump(chk, open(os.path.join(cur, 'check.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    shutil.copyfile(os.path.join(full, 'logs.txt'), os.path.join(cur, 'logs.txt'))
    print('%s：留 %d 个号%s；意图 %d → %d 条，行动拍 %d → %d 行；全量在 tmp/shadow/%s.all/' % (
        mid, len(keep), '（其中 %d 个号截到停摆拍）' % len(cut) if cut else '',
        stat['intents.tsv'][0], stat['intents.tsv'][1], stat['rows.tsv'][0], stat['rows.tsv'][1], mid))


if __name__ == '__main__':
    main()
