#!/bin/bash
# Fetch version-matched OpenROAD / OpenSTA / ORFS sources into ./third_party.
#
# Only documentation, Tcl command definitions, official Tcl examples and the
# Nangate45 test platform + GCD reference design are checked out (sparse,
# blob-filtered partial clones), all pinned to commits that match the OpenROAD
# binary installed by setup_env.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TP="$ROOT/third_party"
export HOME="$ROOT/.tools/home"
mkdir -p "$TP" "$HOME"

OPENROAD_COMMIT="0922eecb9b6a9de5fc7209e11f0781c75d2a0ff2"   # 2023-11-06, matches openroad 2.0_10927_g0922eecb9
ORFS_COMMIT="2271f5d9648b825a7702d30df54a7bc7b7bbbcf1"       # 2023-11-07, contemporaneous flow scripts

# sparse_clone <url> <commit> <dest> <pattern>...
sparse_clone() {
  local url="$1" commit="$2" dest="$3"; shift 3
  if [ -d "$dest/.git" ] && [ "$(git -C "$dest" rev-parse HEAD 2>/dev/null)" = "$commit" ]; then
    echo "[fetch] $dest already at $commit"; return
  fi
  rm -rf "$dest"; mkdir -p "$dest"
  git -C "$dest" init -q
  git -C "$dest" remote add origin "$url"
  git -C "$dest" config core.sparseCheckout true
  git -C "$dest" sparse-checkout set --no-cone "$@"
  git -C "$dest" fetch -q --depth 1 --filter=blob:none origin "$commit"
  git -C "$dest" checkout -q FETCH_HEAD
  echo "[fetch] $dest @ $(git -C "$dest" rev-parse --short HEAD)"
}

sparse_clone https://github.com/The-OpenROAD-Project/OpenROAD.git "$OPENROAD_COMMIT" "$TP/OpenROAD" \
  '/README.md' '/docs/**' '/src/*/README.md' '/src/*/src/*.tcl' '/src/*/test/*.tcl' \
  '/test/*.tcl' '/test/gcd_nangate45*' '/test/aes_nangate45*' '/test/Nangate45/**'

# OpenSTA is a submodule of OpenROAD; use the exact commit recorded in the superproject.
STA_COMMIT="$(git -C "$TP/OpenROAD" ls-tree HEAD src/sta | awk '{print $3}')"
sparse_clone https://github.com/The-OpenROAD-Project/OpenSTA.git "$STA_COMMIT" "$TP/OpenSTA" \
  '/README.md' '/doc/**' '/tcl/*.tcl' '/*/*.tcl'

sparse_clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git "$ORFS_COMMIT" "$TP/OpenROAD-flow-scripts" \
  '/README.md' '/docs/user/*.md' '/docs/tutorials/*.md' '/flow/scripts/*.tcl' '/flow/platforms/nangate45/*.tcl' \
  '/flow/platforms/nangate45/config.mk'

cat > "$TP/VERSIONS.txt" <<EOF
OpenROAD               $OPENROAD_COMMIT
OpenSTA                $STA_COMMIT
OpenROAD-flow-scripts  $ORFS_COMMIT
EOF
cat "$TP/VERSIONS.txt"
