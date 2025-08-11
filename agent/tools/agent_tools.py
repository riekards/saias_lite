# agent/tools/agent_tools.py
from qwen_agent.tools import Tool
import subprocess
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

class RunSelfPatch(Tool):
    description = "Trigger SAIAS self-patching system to refactor or extend code"
    parameters = {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why this patch is needed"
            }
        },
        "required": ["reason"]
    }

    def call(self, params: dict, **kwargs) -> str:
        print(f"[🔧] Running self-patch: {params['reason']}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "agent.tools.self_patch"],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True
            )
            return f"Self-patch completed.\nOutput: {result.stdout}\nErrors: {result.stderr}"
        except Exception as e:
            return f"Failed to run self-patch: {str(e)}"

class EvaluatePendingPatches(Tool):
    description = "Check for pending patches and summarize them"
    parameters = {}

    def call(self, params: dict, **kwargs) -> str:
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