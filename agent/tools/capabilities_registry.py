# agent/tools/capabilities_registry.py
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
CAPABILITIES_PATH = ROOT_DIR / "memory" / "capabilities.json"

def load_capabilities():
    if not CAPABILITIES_PATH.exists():
        caps = {
            "core": {
                "say": {"description": "Say something out loud", "file": "tools/speech.py"},
                "listen": {"description": "Listen to user", "file": "tools/speech.py"}
            }
        }
        save_capabilities(caps)
        return caps
    try:
        with open(CAPABILITIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_capabilities(data):
    with open(CAPABILITIES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def can_handle_request(query: str) -> bool:
    """
    Check if SAIAS can already handle this request
    """
    caps = load_capabilities()
    query_lower = query.lower()
    for module, funcs in caps.items():
        for name, data in funcs.items():
            if name.lower() in query_lower:
                return True
            if data["description"].lower() in query_lower:
                return True
    return False

def register_capability(name: str, description: str, file_path: str):
    caps = load_capabilities()
    module = file_path.replace("/", ".").replace(".py", "")
    if module not in caps:
        caps[module] = {}
    caps[module][name] = {
        "description": description,
        "file": file_path,
        "dependencies": [],
        "used_by": []
    }
    save_capabilities(caps)