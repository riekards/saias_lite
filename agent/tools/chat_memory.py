import json
from pathlib import Path
from typing import List, Dict

MEMORY_DIR = Path(__file__).resolve().parents[1] / "memory"
CHAT_LOG = MEMORY_DIR / "chat_log.jsonl"


def append_chat(role: str, content: str, max_messages: int = 100) -> None:
	"""Append a chat message and prune to the last max_messages entries."""
	CHAT_LOG.parent.mkdir(parents=True, exist_ok=True)
	entry = {"role": role, "content": content}
	with CHAT_LOG.open("a", encoding="utf-8") as f:
		f.write(json.dumps(entry, ensure_ascii=False) + "\n")
	# Prune if longer than max_messages
	try:
		lines = CHAT_LOG.read_text(encoding="utf-8").splitlines()
		if len(lines) > max_messages:
			trimmed = lines[-max_messages:]
			CHAT_LOG.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
	except Exception:
		pass


def load_recent(n: int = 100) -> List[Dict[str, str]]:
	"""Load up to the last n chat entries as a list of {role, content}."""
	try:
		lines = CHAT_LOG.read_text(encoding="utf-8").splitlines()
		tail = lines[-n:]
		out: List[Dict[str, str]] = []
		for line in tail:
			try:
				obj = json.loads(line)
				if isinstance(obj, dict) and "role" in obj and "content" in obj:
					out.append({"role": obj["role"], "content": obj["content"]})
			except Exception:
				continue
		return out
	except FileNotFoundError:
		return []
	except Exception:
		return []

