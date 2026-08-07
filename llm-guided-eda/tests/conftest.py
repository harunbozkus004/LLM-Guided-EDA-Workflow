import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common.paths  # noqa: E402,F401  (redirects library caches into .tools/cache)
