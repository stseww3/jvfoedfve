#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_SDK="${ANDROID_HOME:-/home/ubuntu/android-sdk}"
BUILD_TOOLS="$ANDROID_SDK/build-tools/36.0.0"
PLATFORM_JAR="$ANDROID_SDK/platforms/android-36/android.jar"

WORK_DIR="/tmp/mm-apk-build"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/classes" "$WORK_DIR/dex" "$WORK_DIR/apk_root/lib/arm64-v8a" "$WORK_DIR/apk_root/lib/armeabi-v7a"
mkdir -p "$WORK_DIR/apk_root/assets/Resources/featuretoggleconfigs" "$WORK_DIR/apk_root/assets/Sounds/48000"

# 1. Compile Java Activity against android.jar
javac --release 11 -cp "$PLATFORM_JAR" \
  -d "$WORK_DIR/classes" \
  "$SCRIPT_DIR/src/com/dinopoloclub/minimotorways/MobilePortActivity.java"

# 2. Convert class files to classes.dex using d8
"$BUILD_TOOLS/d8" --min-api 21 \
  --lib "$PLATFORM_JAR" \
  --output "$WORK_DIR/dex" \
  $(find "$WORK_DIR/classes" -name "*.class")

# 3. Link AndroidManifest.xml with aapt2
"$BUILD_TOOLS/aapt2" link \
  -I "$PLATFORM_JAR" \
  --manifest "$SCRIPT_DIR/AndroidManifest.xml" \
  -o "$WORK_DIR/unaligned.apk"

# 4. Copy classes.dex, compiled NDK native libraries (arm64-v8a & armeabi-v7a), AndroidConfig.json, and FLAC chime slice
cp "$WORK_DIR/dex/classes.dex" "$WORK_DIR/apk_root/classes.dex"
cp "$PORT_DIR/native/libs/arm64-v8a/"*.so "$WORK_DIR/apk_root/lib/arm64-v8a/"
cp "$PORT_DIR/native/libs/armeabi-v7a/"*.so "$WORK_DIR/apk_root/lib/armeabi-v7a/"
cp "$PORT_DIR/resources/AndroidConfig.json" "$WORK_DIR/apk_root/assets/Resources/featuretoggleconfigs/AndroidConfig.json"

# Extract a 48kHz FLAC chime ("Boop_3_A#4" at offset 7149422, 9895 samples) from core.bytes if present
if [ -f "/tmp/mm-c63/assets/StreamingAssets/Sounds/48000/core.bytes" ]; then
  python3 -c '
import struct
with open("/tmp/mm-c63/assets/StreamingAssets/Sounds/48000/core.bytes", "rb") as f:
    f.seek(7149422)
    hdr = f.read(4)
    sz = struct.unpack("<I", hdr)[0]
    flac = f.read(sz)
with open("'"$WORK_DIR"'/apk_root/assets/Sounds/48000/chime.bytes", "wb") as out:
    out.write(hdr + flac)
'
fi

(cd "$WORK_DIR/apk_root" && zip -q -r "$WORK_DIR/unaligned.apk" classes.dex lib assets)

# 5. Align on 16 KB / 4-byte boundaries with zipalign
OUT_APK="${1:-$PORT_DIR/dist/MiniMotorways-MobilePort.apk}"
mkdir -p "$(dirname "$OUT_APK")"
"$BUILD_TOOLS/zipalign" -P 16 -f 4 "$WORK_DIR/unaligned.apk" "$OUT_APK"

# 6. Sign APK with debug keystore using apksigner (v1 + v2 + v3 signatures)
KEYSTORE="$WORK_DIR/debug.keystore"
keytool -genkeypair -v \
  -keystore "$KEYSTORE" \
  -storepass android \
  -keypass android \
  -alias androiddebugkey \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1

"$BUILD_TOOLS/apksigner" sign \
  --ks "$KEYSTORE" \
  --ks-pass pass:android \
  --key-pass pass:android \
  "$OUT_APK"

"$BUILD_TOOLS/apksigner" verify --verbose "$OUT_APK"
ls -lh "$OUT_APK"
