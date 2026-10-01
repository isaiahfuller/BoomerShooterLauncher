#!/usr/bin/env bash
# Run from any directory after: python src/setup.py build_exe --build-exe build/frozen
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
    echo 'This packaging script requires x86_64 Linux.' >&2
    exit 1
fi
FROZEN=${1:-build/frozen}
if [[ ! -x "$FROZEN/boomershooterlauncher" ]]; then
    echo "Missing frozen executable in $FROZEN; run the cx_Freeze build first." >&2
    exit 1
fi
TOOLS="$ROOT/build/appimage-tools"
APPDIR="$ROOT/build/BSL.AppDir"
mkdir -p "$TOOLS" "$ROOT/dist"

# Versioned upstream releases, verified before execution. Update URLs and hashes together.
fetch() {
    local url=$1 target=$2 checksum=$3
    if [[ ! -f "$target" ]]; then
        curl --fail --location --retry 3 "$url" --output "$target.tmp"
        mv "$target.tmp" "$target"
    fi
    echo "$checksum  $target" | sha256sum --check --status
}
fetch 'https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage' \
    "$TOOLS/appimagetool.AppImage" \
    ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
fetch 'https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64' \
    "$TOOLS/runtime-x86_64" \
    2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d
chmod +x "$TOOLS/appimagetool.AppImage"

# Preserve cx_Freeze's library layout and Qt plugin paths; do not mix in a second Qt.
rm -rf -- "$APPDIR"
mkdir -p "$APPDIR"
cp -a "$FROZEN/." "$APPDIR/"
cp packaging/linux/{AppRun,bsl.desktop,bsl.svg} "$APPDIR/"
cp LICENSE "$APPDIR/LICENSE"
chmod +x "$APPDIR/AppRun"
ln -s bsl.svg "$APPDIR/.DirIcon"
# Extract the packaging tool itself so builds do not depend on FUSE access.
(cd "$TOOLS" && ./appimagetool.AppImage --appimage-extract > /dev/null)
ARCH=x86_64 "$TOOLS/squashfs-root/AppRun" \
    --runtime-file "$TOOLS/runtime-x86_64" --no-appstream \
    --mksquashfs-opt -processors --mksquashfs-opt 2 \
    "$APPDIR" "$ROOT/dist/BSL-linux-x86_64.AppImage"
