import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from refiner.runner import run_from_stdin


if __name__ == "__main__":
    raise SystemExit(run_from_stdin())
