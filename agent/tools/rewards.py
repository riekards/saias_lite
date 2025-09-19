import json
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path(__file__).resolve().parents[1] / "memory"
LOG_PATH = MEMORY_DIR / "rewards_log.jsonl"  # append-only NDJSON

def log_reward(action: str, **fields) -> None:
	"""
	action ∈ {"emitted","approved","rejected","skipped","tests_passed","tests_failed","error"}
	Writes one JSON line per event. Keep it small; analyze later.
	"""
	entry = {
		"when": datetime.utcnow().isoformat(),
		"action": action,
		**fields
	}
	LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
	with LOG_PATH.open("a", encoding="utf-8") as f:
		f.write(json.dumps(entry, ensure_ascii=False) + "\n")
