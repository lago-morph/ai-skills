import sys
from pathlib import Path

# When the test suites for skill-registry and skill-sync are collected in
# the same pytest run, both ship modules named `validate` and
# `canonical_json`. Python caches the first import. Pop them here so the
# next `import` resolves through the freshly-prepended sys.path.
for _mod in ("validate", "canonical_json", "regen_agents_md", "skill_sync"):
    sys.modules.pop(_mod, None)

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
