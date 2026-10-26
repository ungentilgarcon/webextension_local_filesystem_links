#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <version> <output-directory>" >&2
    exit 2
fi

version="$1"
output_dir="$2"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid native-host version: $version" >&2
    exit 2
fi
if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "The Debian package must be built on an x86_64 Linux system." >&2
    exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
binary_dir="$repo_root/native-host/bin/linux/local-link-messaging-host"
manifest_source="$repo_root/native-host/src/webextension_local_filesystem_links.json"
package_name="local-filesystem-links-native-host"
host_path="/usr/lib/local-filesystem-links/local-link-messaging-host/local-link-messaging-host"

if [[ ! -x "$binary_dir/local-link-messaging-host" ]]; then
    echo "Linux native host executable not found; build it first." >&2
    exit 1
fi
if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "dpkg-deb is required to build the Debian package." >&2
    exit 1
fi

mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
package_root="$(mktemp -d)"
verification_dir="$(mktemp -d)"
trap 'rm -rf "$package_root" "$verification_dir"' EXIT

install_dir="$package_root/usr/lib/local-filesystem-links/local-link-messaging-host"
manifest_dir="$package_root/usr/lib/mozilla/native-messaging-hosts"
mkdir -p "$package_root/DEBIAN" "$install_dir" "$manifest_dir"
cp -a "$binary_dir/." "$install_dir/"
chmod 755 "$install_dir/local-link-messaging-host"

python3 - "$manifest_source" "$manifest_dir/webextension_local_filesystem_links.json" "$host_path" <<'PY'
import json
import sys
from pathlib import Path

source, destination, host_path = sys.argv[1:]
manifest = json.loads(Path(source).read_text(encoding="utf-8"))
manifest["path"] = host_path
Path(destination).write_text(
    json.dumps(manifest, indent=4) + "\n",
    encoding="utf-8",
)
PY
chmod 644 "$manifest_dir/webextension_local_filesystem_links.json"

cat > "$package_root/DEBIAN/control" <<EOF
Package: $package_name
Version: $version
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.35)
Maintainer: ungentilgarcon
Homepage: https://github.com/ungentilgarcon/webextension_local_filesystem_links
Description: Firefox native host for Local Filesystem Links
 Companion application that opens local and network file links from Firefox.
EOF

versioned_package="$output_dir/${package_name}_${version}_amd64.deb"
dpkg-deb --build --root-owner-group "$package_root" "$versioned_package"
cp "$versioned_package" "$output_dir/${package_name}.deb"

package_architecture="$(dpkg-deb --field "$versioned_package" Architecture)"
package_version="$(dpkg-deb --field "$versioned_package" Version)"
if [[ "$package_architecture" != "amd64" || "$package_version" != "$version" ]]; then
    echo "Generated Debian package has unexpected metadata." >&2
    exit 1
fi

dpkg-deb --extract "$versioned_package" "$verification_dir"
python3 - "$verification_dir" "$host_path" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
host_path = sys.argv[2]
manifest_path = root / "usr/lib/mozilla/native-messaging-hosts/webextension_local_filesystem_links.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("path") != host_path:
    raise SystemExit("Debian package manifest has an incorrect host path.")
required_ids = {
    "jid1-JAzC7z53jemo5Q@jetpack",
    "{b0875df6-5b25-4907-a2c1-10ca04249fb8}",
}
if not required_ids.issubset(manifest.get("allowed_extensions", [])):
    raise SystemExit("Debian package manifest is missing an authorized Firefox add-on ID.")
if not (root / host_path.lstrip("/")).is_file():
    raise SystemExit("Debian package is missing its native host executable.")
if not (root / host_path.lstrip("/")).stat().st_mode & 0o111:
    raise SystemExit("Debian package native host executable is not executable.")
PY

echo "Created and validated $versioned_package"
