set -u
out=renders/_wip/sky_switch
rm -rf "$out"; mkdir -p "$out"
( cd .. && git apply c164-realms/plan/packages/sky/safe-look-drivers.patch c164-realms/plan/packages/sky/safe-look-flip.patch ) > "$out/apply.txt" 2>&1 || { echo "the patches do not apply"; cat "$out/apply.txt"; exit 3; }
python tools/checkall.py --out "$out/check" > "$out/checkall.txt" 2>&1; echo "checkall exit=$?" >> "$out/checkall.txt"
pack=$(mktemp -d)
python build/makepack.py obs --out "$pack" > "$out/makepack.txt" 2>&1; echo "makepack exit=$?" >> "$out/makepack.txt"
( cd "$pack" && find assets/minecraft/shaders -type f | sort ) >> "$out/makepack.txt" 2>&1
rm -rf "$pack"
( cd .. && git apply -R c164-realms/plan/packages/sky/safe-look-flip.patch c164-realms/plan/packages/sky/safe-look-drivers.patch ) >> "$out/apply.txt" 2>&1; echo "patches taken off again: exit=$?" >> "$out/apply.txt"
git status --short | head -5 >> "$out/apply.txt"
rm -rf "$out/check"/*.json
tail -n 3 "$out/apply.txt"; tail -n 12 "$out/makepack.txt" | cut -c1-200; rg -c "" "$out/checkall.txt"; tail -n 4 "$out/checkall.txt" | cut -c1-300
