#!/usr/bin/env bash
# council_build.sh — 把 scripts/council_src/*.md 按文件名顺序拼成 reports/COUNCIL-PROPOSAL.md，再核对正文里的数：
#   m7_numcheck.py（每个数在产物里出现过）和 council_attrcheck.py（点了局号的句子里的数出现在那几局自己的产物里，
#   结果写到 out/m7/council_attrcheck.txt）。
# 用法：bash scripts/council_build.sh
cd "$(dirname "$0")/.." || exit 1
out=reports/COUNCIL-PROPOSAL.md
: > "$out"
first=1
for f in scripts/council_src/*.md; do
  [ $first -eq 1 ] || printf '\n' >> "$out"
  cat "$f" >> "$out"
  first=0
done
echo "写出 $out：$(wc -l < "$out") 行，$(wc -c < "$out") 字节（$(ls scripts/council_src/*.md | wc -l) 个文件）"
python3 scripts/council_attrcheck.py "$out" > out/m7/council_attrcheck.txt; tail -1 out/m7/council_attrcheck.txt
python3 scripts/m7_numcheck.py "$out"
