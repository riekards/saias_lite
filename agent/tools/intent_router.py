# agent/tools/intent_router.py
import json
from pathlib import Path
import subprocess
import sys
import re
from agent.tools.agent_tools import can_perform, ensure_capability
from agent.tools.llm import call_chat_llm
from agent.planner import propose_capability, create_new_capability
from agent.tools.pending_intent import save_proposal, load_proposal, clear_proposal
from agent.tools.llm import load_config

ROOT_DIR = Path(__file__).resolve().parents[2]


def is_capability_creation(text: str) -> bool:
    """Detect explicit requests to create new tools/functions/modules (low false-positives)."""
    t = (text or "").strip().lower()
    if not t:
        return False
    verbs = {"create", "make", "add", "write", "generate", "build", "implement"}
    nouns = {"tool", "function", "module", "script", "capability"}
    first = re.split(r"\s+", t, maxsplit=1)[0]
    has_py = ".py" in t
    has_verb = first in verbs or any(v + " " in t for v in verbs)
    has_noun = any(n in t for n in nouns)
    return has_verb and (has_noun or has_py)


def is_patch_command(text: str) -> str:
    """Return 'show'|'approve'|'' based on common patch management phrasings."""
    t = (text or "").strip().lower()
    if not t:
        return ""
    if t in {"show", "show patches", "list patches", "pending patches"}:
        return "show"
    if t.startswith("approve patch") or t.startswith("apply patch"):
        return "approve"
    return ""


def route(user_input: str) -> str:
    """
    Main entry point: decide if input is chat, code refactor, or new capability
    """
    user_input = user_input.strip()

    # Patch management shortcuts
    cmd = is_patch_command(user_input)
    if cmd == "show":
        return run_evaluate_patch()
    if cmd == "approve":
        return run_apply_patch(user_input)

    # Capability creation (explicit)
    if is_capability_creation(user_input):
        return ensure_capability(user_input)

    # Ability queries: propose a capability plan when missing
    t = user_input.strip().lower()
    if any(t.startswith(p) for p in ("can you ", "could you ", "would you ", "please ", "i want you to ")):
        if not can_perform(user_input):
            cfg = load_config()
            auto = cfg.get("chat", {}).get("auto_create_capability", False)
            spec = propose_capability(user_input)
            spec["request"] = user_input
            save_proposal(spec)
            tool = spec.get("tool_name")
            funcs = spec.get("functions") or []
            fn_preview = ", ".join(f.get("name") for f in funcs if isinstance(f, dict) and f.get("name"))
            if auto:
                # proceed immediately
                out = create_new_capability(spec.get("request", user_input), tool_name=tool, description=spec.get("description", user_input))
                clear_proposal()
                return out
            else:
                suggestion = (
                    f"I can’t do that yet. I can create '{tool}' with functions: {fn_preview or 'TBD'}. "
                    f"Reply 'yes' to proceed or 'no' to cancel."
                )
                return suggestion

    # Confirm/cancel last proposal
    if t in {"yes", "do it", "sure", "ok", "okay", "proceed", "go ahead"}:
        spec = load_proposal()
        if spec:
            out = create_new_capability(spec.get("request", ""), tool_name=spec.get("tool_name"), description=spec.get("description"))
            clear_proposal()
            return out
        # Fall through to chat if nothing pending
    if t in {"no", "cancel", "stop"}:
        clear_proposal()
        return "Okay, cancelled."

    # Default: treat as chat
    try:
        return call_chat_llm(user_input)
    except Exception as e:
        return f"[ERROR] Chat failed: {e}"

def run_evaluate_patch() -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "agent.tools.evaluate_patch"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        return result.stdout or "No output"
    except Exception as e:
        return f"Error: {str(e)}"

def run_apply_patch(user_input: str) -> str:
    patch_id = user_input.replace("approve patch", "").strip().upper()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "agent.tools.evaluate_patch", patch_id],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True
        )
        return result.stdout or "Applied."
    except Exception as e:
        return f"Error: {str(e)}"
