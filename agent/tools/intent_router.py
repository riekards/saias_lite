# agent/tools/intent_router.py
import json
from pathlib import Path
import subprocess
import sys
from agent.tools.capabilities_registry import can_handle_request
from agent.planner import create_new_capability

ROOT_DIR = Path(__file__).resolve().parents[2]

def route(user_input: str) -> str:
    """
    Main entry point: decide if input is chat, code refactor, or new capability
    """
    user_input = user_input.strip()

    # Command shortcuts
    if user_input.lower() == "show":
        return run_evaluate_patch()
    if user_input.lower().startswith("approve patch"):
        return run_apply_patch(user_input)

    # Check if it's a capability request
    if "write" in user_input or "create" in user_input or "make" in user_input or "add" in user_input:
        if not can_handle_request(user_input):
            return create_new_capability(user_input)

    # Default: treat as chat
    return f"[CHAT] {user_input}"

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