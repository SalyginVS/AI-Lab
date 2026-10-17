#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
exec python3 -I "$package_dir/runtime.py" "$@"
