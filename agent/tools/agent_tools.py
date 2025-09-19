# agent/tools/agent_tools.py
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import difflib

# --- Qwen-Agent Tool class compatibility (optional) ---
_QWEN_TOOL = None
try:
    from qwen_agent.tools import Tool as _QWEN_TOOL  # Older versions
except Exception:
    try:
        from qwen_agent.agent.tool import BaseTool as _QWEN_TOOL  # Newer versions
    except Exception:
        _QWEN_TOOL = None

if _QWEN_TOOL is None:
    # Minimal fallback so the rest of the system works without qwen-agent
    class Tool:  # type: ignore
        description: str = ""
        parameters: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

        def call(self, params: dict, **kwargs):  # pragma: no cover - override in subclasses
            raise NotImplementedError("Tool.call must be implemented")
else:  # Use qwen-agent's Tool base class
    Tool = _QWEN_TOOL  # type: ignore

TOOLS_DIR = Path(__file__).parent
PACKAGE_NAME = __name__.rsplit(".", 1)[0]  # "agent.tools"


def build_param_schema(fn) -> Dict[str, Any]:
    """Generate JSON Schema for Tool parameters from function signature."""
    sig = inspect.signature(fn)
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        param_type = "string"  # default
        if param.annotation in (int, "int"):
            param_type = "integer"
        elif param.annotation in (float, "float"):
            param_type = "number"
        elif param.annotation in (bool, "bool"):
            param_type = "boolean"
        properties[name] = {
            "type": param_type,
            "description": f"Parameter {name}"
        }
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def discover_tools() -> List[Tool]:
    """Auto-discover functions or classes in agent/tools and wrap as Qwen-Agent Tools."""
    tools: List[Tool] = []

    for _, mod_name, is_pkg in pkgutil.iter_modules([str(TOOLS_DIR)]):
        if mod_name.startswith("_") or mod_name in ("agent_tools", "__init__"):
            continue
        module = importlib.import_module(f"{PACKAGE_NAME}.{mod_name}")

        for name, obj in inspect.getmembers(module):
            # Wrap top-level functions as tools
            if inspect.isfunction(obj) and obj.__module__ == module.__name__:
                schema = build_param_schema(obj)

                class FuncTool(Tool):
                    description = obj.__doc__ or f"Run {obj.__name__} function"
                    parameters = schema

                    def call(self, params: dict, **kwargs):
                        return obj(**params)

                FuncTool.__name__ = f"{obj.__name__.title()}Tool"
                tools.append(FuncTool())

            # Already defined Tool subclasses
            elif inspect.isclass(obj) and issubclass(obj, Tool) and obj is not Tool:
                tools.append(obj())

    return tools


def list_discovered_functions() -> List[Tuple[str, str]]:
    """
    Return a lightweight list of discovered top-level functions as (qualified_name, doc).
    qualified_name example: "tools.module:function".
    """
    out: List[Tuple[str, str]] = []
    for _, mod_name, is_pkg in pkgutil.iter_modules([str(TOOLS_DIR)]):
        if is_pkg or mod_name.startswith("_") or mod_name in ("agent_tools", "__init__"):
            continue
        module = importlib.import_module(f"{PACKAGE_NAME}.{mod_name}")
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and obj.__module__ == module.__name__:
                q = f"tools.{mod_name}:{name}"
                out.append((q, (obj.__doc__ or "").strip()))
    return out


def can_perform(query: str) -> bool:
    """
    Determine if the current tool/capability set likely supports the query.
    Uses the capabilities registry first; falls back to discovered functions and docstrings.
    """
    from .capabilities_registry import can_handle_request

    q = (query or "").lower().strip()
    if not q:
        return False
    try:
        if can_handle_request(q):
            return True
    except Exception:
        pass

    # Fallback: scan discovered functions + docstrings with fuzzy matching
    try:
        tokens = [t for t in q.split() if len(t) > 2]
        for qualified, doc in list_discovered_functions():
            fname = qualified.split(":", 1)[-1].lower()
            # direct substring hits
            if fname and fname in q:
                return True
            if doc and any(tok in (doc or "").lower() for tok in tokens):
                return True
            # fuzzy similarity against function name and doc
            ratios = []
            if fname:
                ratios.append(difflib.SequenceMatcher(None, q, fname).ratio())
            if doc:
                ratios.append(difflib.SequenceMatcher(None, q, doc.lower()).ratio())
            if ratios and max(ratios) >= 0.6:
                return True
    except Exception:
        pass
    return False


def ensure_capability(query: str) -> str:
    """
    Ensure there is a capability for the user's query.
    - If supported: returns a short confirmation string.
    - If not: triggers capability creation via planner and returns the planner's message.
    """
    if can_perform(query):
        return "Capability available."

    # Lazy import to avoid hard dependency on qwen-agent when not used
    try:
        from agent.planner import create_new_capability  # type: ignore
    except Exception as e:
        return f"[ERROR] Cannot create capability (planner unavailable): {e}"

    try:
        return create_new_capability(query)
    except Exception as e:
        return f"[ERROR] Failed to create capability: {e}"


# Expose tools list for Qwen-Agent
tools = discover_tools()
