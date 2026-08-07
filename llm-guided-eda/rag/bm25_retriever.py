"""BM25 keyword retrieval (rank_bm25.BM25Okapi) with a code-aware tokenizer.

The tokenizer lowercases and keeps Tcl identifiers (``global_placement``),
options (``-density``) and namespaced names (``sta::report_checks``) as whole
tokens, and adds their sub-tokens split on ``_``, ``-``, ``::``, ``/`` and ``.``
(plus an option's name without the dash), so that both the exact command name
and the words of a natural-language question match. Plain words and sub-tokens
are Porter-stemmed (``legalizing`` / ``legalization`` -> ``legal``); whole
identifiers and options are kept verbatim. English stopwords are dropped.
"""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Sequence

import numpy as np
from rank_bm25 import BM25Okapi

TOKENIZER_VERSION = "2"
K1, B, EPSILON = 1.5, 0.75, 0.25
VOCAB_FILE, TOKENS_FILE, OFFSETS_FILE = "bm25_vocab.json", "bm25_tokens.npy", "bm25_offsets.npy"

STOPWORDS = frozenset("""
a about above after again against am an and any are as at be because been before being below between
both but by can could did do does doing down during each either else ever few for from further had has
have having he her here hers herself him himself his how i if in into is it its itself just let me
more most my myself no nor not of off on once only or other our ours ourselves out over own same she
should so some such than that the their theirs them themselves then there these they this those through
to too under until up very was we were what when where which while who whom why will with would you
your yours yourself yourselves e g ie eg etc also may might must shall within without
""".split())

_TOKEN_RE = re.compile(r"-{0,2}[a-z0-9_]+(?:(?:::|[-_.:/])+[a-z0-9_]+)*")
_COARSE_RE = re.compile(r"(?:::|[:/.])+")
_FINE_RE = re.compile(r"[-_]+")
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


# --------------------------------------------------------------------------- Porter stemmer

def _cons(w: str, i: int) -> bool:
    if w[i] in "aeiou":
        return False
    if w[i] == "y":
        return i == 0 or not _cons(w, i - 1)
    return True


def _measure(stem: str) -> int:
    """Porter's m: the number of vowel-consonant sequences in ``stem``."""
    n, i, size = 0, 0, len(stem)
    while i < size and _cons(stem, i):
        i += 1
    while i < size:
        while i < size and not _cons(stem, i):
            i += 1
        if i >= size:
            break
        while i < size and _cons(stem, i):
            i += 1
        n += 1
    return n


def _has_vowel(stem: str) -> bool:
    return any(not _cons(stem, i) for i in range(len(stem)))


def _double_cons(w: str) -> bool:
    return len(w) >= 2 and w[-1] == w[-2] and _cons(w, len(w) - 1)


def _cvc(w: str) -> bool:
    return (len(w) >= 3 and _cons(w, len(w) - 3) and not _cons(w, len(w) - 2)
            and _cons(w, len(w) - 1) and w[-1] not in "wxy")


_STEP2 = (("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"), ("izer", "ize"),
          ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"), ("ousli", "ous"),
          ("ization", "ize"), ("ation", "ate"), ("ator", "ate"), ("alism", "al"), ("iveness", "ive"),
          ("fulness", "ful"), ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"))
_STEP3 = (("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"), ("ical", "ic"),
          ("ful", ""), ("ness", ""))
_STEP4 = ("al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent", "ion", "ou",
          "ism", "ate", "iti", "ous", "ive", "ize")


@functools.lru_cache(maxsize=65536)
def stem(word: str) -> str:
    """The original Porter (1980) stemmer, for lowercase alphabetic words."""
    w = word
    if len(w) <= 2 or not w.isalpha():
        return w
    if w.endswith("sses") or w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    fixup = False
    if w.endswith("eed"):
        if _measure(w[:-3]) > 0:
            w = w[:-1]
    elif w.endswith("ed") and _has_vowel(w[:-2]):
        w, fixup = w[:-2], True
    elif w.endswith("ing") and _has_vowel(w[:-3]):
        w, fixup = w[:-3], True
    if fixup:
        if w.endswith(("at", "bl", "iz")):
            w += "e"
        elif _double_cons(w) and w[-1] not in "lsz":
            w = w[:-1]
        elif _measure(w) == 1 and _cvc(w):
            w += "e"
    if w.endswith("y") and _has_vowel(w[:-1]):
        w = w[:-1] + "i"
    for table in (_STEP2, _STEP3):
        for suffix, repl in table:
            if w.endswith(suffix):
                if _measure(w[:-len(suffix)]) > 0:
                    w = w[:-len(suffix)] + repl
                break
    for suffix in _STEP4:
        if w.endswith(suffix):
            base = w[:-len(suffix)]
            if _measure(base) > 1 and (suffix != "ion" or base[-1:] in ("s", "t")):
                w = base
            break
    if w.endswith("e"):
        base = w[:-1]
        if _measure(base) > 1 or (_measure(base) == 1 and not _cvc(base)):
            w = base
    if _measure(w) > 1 and _double_cons(w) and w.endswith("l"):
        w = w[:-1]
    return w


# --------------------------------------------------------------------------- tokenizer

def tokenize(text: str) -> list[str]:
    """Code-aware BM25 tokens (see module docstring)."""
    out: list[str] = []
    for tok in _TOKEN_RE.findall(text.lower()):
        if _NUMBER_RE.fullmatch(tok):
            out.append(tok)
            continue
        bare = tok.lstrip("-")
        if not bare:
            continue
        coarse = [c for c in _COARSE_RE.split(bare) if c]
        fine = [f for c in coarse for f in _FINE_RE.split(c) if f]
        if tok == bare and len(fine) == 1:            # plain word
            if tok not in STOPWORDS:
                out.append(stem(tok))
            continue
        out.append(tok)
        if tok != bare and len(fine) > 1:
            out.append(bare)                           # option name without its dash
        if len(coarse) > 1:
            out.extend(c for c in coarse if len(_FINE_RE.split(c)) > 1)   # e.g. report_checks
        out.extend(stem(f) for f in fine if f not in STOPWORDS)
    return out


class BM25Index:
    """BM25Okapi over pre-tokenized documents; ``search`` is read-only and thread-safe."""

    def __init__(self, corpus_tokens: list[list[str]], k1: float = K1, b: float = B,
                 epsilon: float = EPSILON):
        self.corpus_tokens = corpus_tokens
        self.k1, self.b, self.epsilon = k1, b, epsilon
        # BM25Okapi divides by the average document length: guard the all-empty corpus.
        safe = corpus_tokens if any(corpus_tokens) else [["\x00"]] * max(1, len(corpus_tokens))
        self.bm25 = BM25Okapi(safe, k1=k1, b=b, epsilon=epsilon)

    @classmethod
    def build(cls, texts: Sequence[str]) -> "BM25Index":
        return cls([tokenize(t) for t in texts])

    def __len__(self) -> int:
        return len(self.corpus_tokens)

    def scores(self, query: str) -> np.ndarray:
        q = tokenize(query)
        if not q:
            return np.zeros(len(self), dtype=np.float64)
        return np.asarray(self.bm25.get_scores(q), dtype=np.float64)

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        """Top-k (document index, score) with score > 0; ties broken by index."""
        s = self.scores(query)
        if k <= 0 or not len(s):
            return []
        order = np.lexsort((np.arange(len(s)), -s))[:k]
        return [(int(i), float(s[i])) for i in order if s[i] > 0]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        vocab: dict[str, int] = {}
        flat: list[int] = []
        offsets = [0]
        for doc in self.corpus_tokens:
            for t in doc:
                flat.append(vocab.setdefault(t, len(vocab)))
            offsets.append(len(flat))
        np.save(directory / TOKENS_FILE, np.asarray(flat, dtype=np.int32))
        np.save(directory / OFFSETS_FILE, np.asarray(offsets, dtype=np.int64))
        meta = {"tokenizer_version": TOKENIZER_VERSION, "k1": self.k1, "b": self.b,
                "epsilon": self.epsilon, "n_docs": len(self.corpus_tokens), "vocab": list(vocab)}
        (directory / VOCAB_FILE).write_text(json.dumps(meta, ensure_ascii=False))

    @classmethod
    def load(cls, directory: Path) -> "BM25Index":
        meta = json.loads((directory / VOCAB_FILE).read_text())
        if meta["tokenizer_version"] != TOKENIZER_VERSION:
            raise ValueError(f"BM25 index built with tokenizer v{meta['tokenizer_version']}, "
                             f"code is v{TOKENIZER_VERSION}: rebuild with python -m rag.build_index")
        vocab = meta["vocab"]
        flat = np.load(directory / TOKENS_FILE)
        offsets = np.load(directory / OFFSETS_FILE)
        words = [vocab[i] for i in flat.tolist()]
        corpus = [words[offsets[d]:offsets[d + 1]] for d in range(len(offsets) - 1)]
        return cls(corpus, meta["k1"], meta["b"], meta["epsilon"])
