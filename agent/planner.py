# agent/planner.py
import os
import json
from pathlib import Path

from agent.tools.agent_tools import tools  # dynamically discovered tools
from agent.tools.llm import safe_code_llm
from agent.tools.capabilities_registry import register_capability

ROOT_DIR = Path(__file__).resolve().parents[1]

def propose_capability(user_request: str) -> dict:
    """
    Generate a proposed capability spec without writing files.
    Returns a dict: {tool_name, description, functions: [{name, description}]}
    """
    prompt = f"""
User wants: "{user_request}"
Suggest a Python module name (e.g., screen_tools.py) and a short description.
Also list 2-3 key functions with one-sentence descriptions.
Respond ONLY in JSON with keys: tool_name, description, functions (list of {{name, description}})
"""
    suggestion = {
        "tool_name": "new_tool.py",
        "description": user_request.strip()[:120],
        "functions": []
    }
    try:
        raw = safe_code_llm(prompt)
        data = json.loads(raw)
        if isinstance(data, dict) and "tool_name" in data and "description" in data:
            suggestion.update({
                "tool_name": data.get("tool_name") or suggestion["tool_name"],
                "description": data.get("description") or suggestion["description"],
                "functions": data.get("functions") or []
            })
    except Exception:
        pass
    # ensure .py suffix
    if suggestion["tool_name"] and not suggestion["tool_name"].endswith(".py"):
        suggestion["tool_name"] += ".py"
    return suggestion

def create_new_capability(user_request: str, tool_name: str | None = None, description: str | None = None) -> str:
    """
    Generate a new tool to fulfill a missing capability.
    """
    if not tool_name or not description:
        prompt = f"""
User wants: "{user_request}"
Suggest a Python module name (e.g., weather_tool.py) and a short description of what it should do.
Respond in JSON format:
{{"tool_name": "...", "description": "..."}}
"""
        try:
            response = safe_code_llm(prompt)
            data = json.loads(response)
            tool_name = tool_name or data.get("tool_name") or "new_tool"
            description = description or data.get("description") or user_request
        except Exception:
            tool_name = tool_name or "new_tool"
            description = description or user_request

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

    # Register capability for reference (store file path relative to 'agent')
    register_capability(tool_name, description, f"tools/{file_name}")

    return f"Created tool {tool_name} at {file_path}"

def run_agent_with_qwen(task: str):
    """
    Initialize Qwen-Agent with dynamically loaded tools and run a task.
    """
    # Lazy import to avoid hard dependency when not needed
    from qwen_agent.agent import QwenAgent
    agent = QwenAgent(
        model="qwen2.5-coder:14b",  # or whichever local/remote Qwen model
        tools=tools
    )

    return agent.run(task)
