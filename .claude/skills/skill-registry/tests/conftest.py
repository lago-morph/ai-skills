import sys
from pathlib import Path

# Make `scripts/` importable as a flat package for the tests.
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
