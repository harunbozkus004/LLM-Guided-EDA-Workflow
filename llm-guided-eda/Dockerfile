# Linux reproduction environment for llm-guided-eda.
#
# Installs the same pinned toolchain as scripts/setup_env.sh (OpenROAD
# 2.0-10927-g0922eecb9 from litex-hub, Python 3.11) inside the image, then
# fetches the version-matched OpenROAD/OpenSTA/ORFS sources.
#
# NOTE: the reference experiments were run on macOS (arm64 + Rosetta) because
# Docker was not available on that host; this image has not been executed there.
# On Linux there is no Seatbelt, so the executor's static policy additionally
# rejects absolute paths; run the container without access to anything but the
# repository (see docker-compose.yml).
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git bzip2 perl libgl1 libxkbcommon0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work/llm-guided-eda
COPY requirements.txt ./
COPY scripts/ ./scripts/
RUN bash scripts/setup_env.sh && bash scripts/fetch_sources.sh

COPY . .
ENV PATH="/work/llm-guided-eda/.tools/envs/py/bin:${PATH}"
RUN python -m benchmark.states build && python -m rag.build_index

CMD ["python", "-m", "pytest", "-q"]
