"""Retrieval-augmented generation over a version-matched OpenROAD / OpenSTA knowledge base."""
from __future__ import annotations

import os
import sys

if sys.platform == "darwin":
    # The torch and faiss-cpu macOS wheels each bundle their own libomp; with both loaded the
    # second OpenMP runtime aborts the process ("OMP: Error #15") unless this is set before it
    # initialises. tests/test_rag.py checks FAISS results against a numpy brute-force search.
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
