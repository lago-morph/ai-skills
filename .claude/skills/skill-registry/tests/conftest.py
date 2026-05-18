import sys
from pathlib import Path

# Pop shared-name modules so this skill's versions are imported fresh
# when the suites for both skills run in the same pytest invocation.
for _mod in ("validate", "canonical_json", "hash_skill", "hash_single_file",
             "render_ledger", "sweep", "reconcile", "semantic_diff",
             "process_incoming", "install_workflows"):
    sys.modules.pop(_mod, None)

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
