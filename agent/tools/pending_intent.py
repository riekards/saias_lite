import json
from pathlib import Path
from typing import Optional, Dict, Any

MEMORY_DIR = Path(__file__).resolve().parents[1] / "memory"
PENDING_PATH = MEMORY_DIR / "pending_proposal.json"


def save_proposal(spec: Dict[str, Any]) -> None:
	PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
	with PENDING_PATH.open("w", encoding="utf-8") as f:
		json.dump(spec, f, indent=2)


def load_proposal() -> Optional[Dict[str, Any]]:
	try:
		with PENDING_PATH.open("r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return None


def clear_proposal() -> None:
	try:
		PENDING_PATH.unlink(missing_ok=True)  # type: ignore[arg-type]
	except Exception:
		pass

