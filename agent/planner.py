# agent/planner.py
import os
import json
from pathlib import Path
from agent.tools.llm import safe_code_llm
from agent.tools.capabilities_registry import register_capability

ROOT_DIR = Path(__file__).resolve().parents[1]

def create_new_capability(user_request: str) -> str:
    """
    Generate a new tool to fulfill a missing capability
    """
    # Infer tool name and purpose
    prompt = f"""
User wants: "{user_request}"
Suggest a Python module name (e.g., weather_tool.py) and a short description of what it should do.
Respond in JSON format:
{{"tool_name": "...", "description": "..."}}
"""
    try:
        response = safe_code_llm(prompt)
        import json as j
        data = j.loads(response)
        tool_name = data["tool_name"]
        description = data["description"]
    except Exception:
        tool_name = "new_tool"
        description = user_request

    file_name = f"{tool_name}.py" if not tool_name.endswith(".py") else tool_name
    file_path = ROOT_DIR / "tools" / file_name

    # Generate code
    code_prompt = f"""
Write a Python module for SAIAS that:
- Does: {description}
- File: {file_name}
- Must be safe, local, no cloud dependencies
- Use only standard library or common packages
- Include error handling
- Add docstrings
- Return structured data

Write only the code.
"""
    code = safe_code_llm(code_prompt)

    # Save file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    # Register capability
    func_name = tool_name.replace(".py", "")
    register_capability(func_name, description, f"tools/{file_name}")

    # Generate patch
    _create_patch(file_path, code, user_request)

    return f"""
I can't do that yet — but I can learn.

I've written a new tool: `{file_name}`
Purpose: {description}

I've generated a patch for your approval.
Run `show` to see pending changes.
"""

def _create_patch(file_path, code, reason):
    from datetime import datetime
    PATCH_DIR = ROOT_DIR / "memory" / "patch_notes"
    PATCH_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    patch_id = f"PATCH_{timestamp}_{Path(file_path).stem}"

    patch_info = {
        "patch_id": patch_id,
        "target_file": str(file_path),
        "description": f"New capability: {reason}",
        "refactor_score": 8,
        "timestamp": timestamp,
        "applied": False,
        "approved": False,
        "original_code": "",
        "refactored_code": code,
        "chunks": []
    }

    with open(PATCH_DIR / f"{patch_id}.json", "w", encoding="utf-8") as f:
        json.dump(patch_info, f, indent=2)