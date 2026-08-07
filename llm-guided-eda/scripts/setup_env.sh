#!/bin/bash
# Self-contained environment setup for llm-guided-eda.
#
# Everything is installed under ./.tools inside the repository. HOME and all
# cache directories are redirected there too, so no tool writes dotfiles or
# caches into the real home directory. Deleting ./.tools removes everything.
#
# Pinned components:
#   micromamba  2.10.0-0
#   OpenROAD    2.0-10927-g0922eecb9 (litex-hub conda build of commit 0922eecb9, 2023-11-06)
#   Python      3.11 (conda-forge) + requirements.txt
#
# On Apple Silicon the OpenROAD build is x86_64 (osx-64) and runs under Rosetta 2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
MICROMAMBA_VERSION="2.10.0-0"
OPENROAD_VERSION="2.0_10927_g0922eecb9"

export HOME="$TOOLS/home"
export MAMBA_ROOT_PREFIX="$TOOLS/mamba"
export XDG_CACHE_HOME="$TOOLS/cache"
export PIP_CACHE_DIR="$TOOLS/cache/pip"
export CONDA_PKGS_DIRS="$TOOLS/mamba/pkgs"
mkdir -p "$TOOLS/bin" "$HOME" "$MAMBA_ROOT_PREFIX" "$XDG_CACHE_HOME"

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  MM_PLAT=osx-arm64; EDA_PLAT=osx-64 ;;
  Darwin-x86_64) MM_PLAT=osx-64;    EDA_PLAT=osx-64 ;;
  Linux-x86_64)  MM_PLAT=linux-64;  EDA_PLAT=linux-64 ;;
  *) echo "Unsupported platform $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

log() { printf '\n[setup %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

# ---------------------------------------------------------------- micromamba
MM="$TOOLS/bin/micromamba"
if [ ! -x "$MM" ]; then
  log "Downloading micromamba $MICROMAMBA_VERSION ($MM_PLAT)"
  url="https://github.com/mamba-org/micromamba-releases/releases/download/$MICROMAMBA_VERSION/micromamba-$MM_PLAT"
  curl -fsSL -o "$MM.tmp" "$url"
  expected="$(curl -fsSL "$url.sha256" | awk '{print $1}')"
  actual="$(shasum -a 256 "$MM.tmp" | awk '{print $1}')"
  if [ "$expected" != "$actual" ]; then echo "micromamba checksum mismatch" >&2; exit 1; fi
  chmod +x "$MM.tmp" && mv "$MM.tmp" "$MM"
fi
"$MM" --version

# ------------------------------------------------------------------ OpenROAD
# The litex-hub package declares Anaconda-defaults dependency names (libboost).
# To stay on conda-forge only, the unmodified package is served from a local
# channel whose repodata maps libboost -> boost-cpp (conda-forge's name for
# the same Boost 1.73 libraries); every other dependency resolves on conda-forge.
EDA="$TOOLS/envs/openroad"
OPENROAD_BUILD="20231104_052339_py37"
case "$EDA_PLAT" in
  osx-64)   OPENROAD_SHA256="bc9b0490d0ef6db83b1b72a93becd594bc866a8c0ac5de8acba9c0fe22f81b42" ;;
  linux-64) OPENROAD_SHA256="a0bfdda11caaa3b7ebaa351275399e246f25384a273a1c200294cb92ae88321b" ;;
esac
if [ ! -x "$EDA/bin/openroad" ]; then
  if [ ! -d "$EDA/conda-meta" ]; then
    log "Creating OpenROAD runtime environment ($EDA_PLAT)"
    if [ "$EDA_PLAT" = "osx-64" ]; then
      RUNTIME_DEPS=("python=3.7" "boost-cpp=1.73.0" "qt=5.9.7" "spdlog=1.9.2" "fmt=8.1.1" "tk=8.6.12" "llvm-openmp" "zlib=1.2.13" "libcxx")
    else
      RUNTIME_DEPS=("python=3.7" "boost-cpp=1.73.0" "qt=5.9.7" "spdlog=1.9.2" "fmt=8.1.1" "tk=8.6.12" "libgomp" "zlib=1.2.13")
    fi
    "$MM" create -y -p "$EDA" --platform "$EDA_PLAT" -c conda-forge --override-channels "${RUNTIME_DEPS[@]}"
  fi

  log "Preparing local channel for OpenROAD $OPENROAD_VERSION"
  CH="$TOOLS/local-channel"
  PKG="openroad-${OPENROAD_VERSION}-${OPENROAD_BUILD}.tar.bz2"
  mkdir -p "$CH/$EDA_PLAT" "$CH/noarch"
  if [ ! -f "$CH/$EDA_PLAT/$PKG" ]; then
    curl -fsSL -o "$CH/$EDA_PLAT/$PKG.tmp" "https://conda.anaconda.org/litex-hub/$EDA_PLAT/$PKG"
    mv "$CH/$EDA_PLAT/$PKG.tmp" "$CH/$EDA_PLAT/$PKG"
  fi
  actual="$(shasum -a 256 "$CH/$EDA_PLAT/$PKG" | awk '{print $1}')"
  if [ "$actual" != "$OPENROAD_SHA256" ]; then echo "OpenROAD package checksum mismatch" >&2; exit 1; fi
  /usr/bin/python3 - "$CH" "$EDA_PLAT" "$PKG" <<'PY'
import hashlib, json, os, sys, tarfile
ch, plat, pkg = sys.argv[1:4]
path = os.path.join(ch, plat, pkg)
with tarfile.open(path, "r:bz2") as tf:
    rec = json.load(tf.extractfile("info/index.json"))
rec["depends"] = [d.replace("libboost ", "boost-cpp ") for d in rec["depends"]]
data = open(path, "rb").read()
rec.update(md5=hashlib.md5(data).hexdigest(), sha256=hashlib.sha256(data).hexdigest(), size=len(data))
json.dump({"info": {"subdir": plat}, "packages": {pkg: rec}, "packages.conda": {}},
          open(os.path.join(ch, plat, "repodata.json"), "w"), indent=1)
json.dump({"info": {"subdir": "noarch"}, "packages": {}, "packages.conda": {}},
          open(os.path.join(ch, "noarch", "repodata.json"), "w"))
print("patched depends:", rec["depends"])
PY
  log "Installing OpenROAD $OPENROAD_VERSION"
  # micromamba cannot parse file:// channel URLs containing spaces, so the
  # channel is reached through a temporary space-free symlink.
  TMP_CH="$(mktemp -d)"
  ln -s "$CH" "$TMP_CH/channel"
  "$MM" install -y -p "$EDA" --platform "$EDA_PLAT" -c "file://$TMP_CH/channel" -c conda-forge --override-channels \
    "openroad=$OPENROAD_VERSION" "fmt=8.1.1"
  rm -rf "$TMP_CH"
fi
log "OpenROAD version check"
"$EDA/bin/openroad" -version

# -------------------------------------------------------------------- Python
PY="$TOOLS/envs/py"
if [ ! -x "$PY/bin/python" ]; then
  log "Creating Python 3.11 environment ($MM_PLAT)"
  "$MM" create -y -p "$PY" -c conda-forge --override-channels "python=3.11" pip
fi
log "Installing Python requirements"
"$PY/bin/python" -m pip install --upgrade pip
"$PY/bin/python" -m pip install -r "$ROOT/requirements.txt"
"$PY/bin/python" -m pip freeze > "$ROOT/requirements.lock.txt"

log "Done. Python: $PY/bin/python  OpenROAD: $EDA/bin/openroad"
