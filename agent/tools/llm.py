import json
import requests
import os
import re
import ast
import difflib
import time
import logging
import ollama
from datetime import datetime
from pathlib import Path
from agent.tools.chat_memory import load_recent

# Path to config
MEMORY_DIR = Path(__file__).resolve().parents[1] / "memory"
CONFIG_PATH = str(MEMORY_DIR / "config.json")
root_registry_data = str(MEMORY_DIR / "root_registry.json")
capabilities_data = str(MEMORY_DIR / "capabilities.json")


def load_config():
	with open(CONFIG_PATH, "r", encoding="utf-8") as f:
		return json.load(f)

# Load model names from config
def get_model_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["llm"]["chat_model"], data["llm"]["code_model"]

# Core LLM call via Ollama API
def call_ollama_model(model_name, prompt, system_prompt=None):
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = ollama.chat(
            model=model_name,
            messages=messages,
            stream=False
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"[ERROR] Failed to call model '{model_name}': {e}"



def get_saias_context():
	"""Return a compact context for chat: context.md (truncated), capability summary, and top-level dirs."""
	capabilities_file = Path(capabilities_data)
	root_registry_file = Path(root_registry_data)
	context_md_file = MEMORY_DIR / "context.md"

	# Context notes (truncate to avoid verbosity)
	ctx_str = ""
	if context_md_file.exists():
		try:
			text = context_md_file.read_text(encoding="utf-8").strip()
			ctx_str = (text[:1000] + ("…" if len(text) > 1000 else ""))
		except Exception:
			ctx_str = ""

	# Capabilities summary (module keys only)
	cap_summary = ""
	try:
		if capabilities_file.exists():
			with capabilities_file.open(encoding="utf-8") as f:
				caps = json.load(f)
				mods = list(caps.keys())
				preview = ", ".join(mods[:5])
				cap_summary = f"modules={len(mods)}; examples: {preview}"
	except Exception:
		cap_summary = ""

	# Root registry summary (top-level keys only)
	reg_summary = ""
	try:
		if root_registry_file.exists():
			with root_registry_file.open(encoding="utf-8") as f:
				tree = json.load(f)
				if isinstance(tree, dict):
					top = list(tree.keys())
					reg_summary = f"top-level: {', '.join(top[:10])}"
	except Exception:
		reg_summary = ""

	return (
		f"Context Notes:\n{ctx_str}\n\n"
		f"Capabilities: {cap_summary}\n"
		f"Project: {reg_summary}"
	)

def get_prompt(prompt_key: str) -> str:
    config = load_config()
    return config.get("prompts", {}).get(prompt_key, "")

def rewrite_code_prompt(user_prompt: str) -> str:
	system_instruction = get_prompt("rewrite_code")
	if not system_instruction:
		raise ValueError("rewrite_code prompt not found in config.json")

	clean_user_prompt = user_prompt.lower().strip()
	clean_system_prompt = system_instruction.lower().strip()

	if clean_user_prompt.startswith(clean_system_prompt[:40]):
		return user_prompt.strip()

	final_prompt = f"{system_instruction.strip()}\n{user_prompt.strip()}"
	print(f"[DEBUG] Final rewrite prompt:\n{final_prompt[:2500]}")
	return final_prompt

def strip_prompt_echo(prompt: str, response: str) -> str:
	"""
	Strips the echoed prompt from the beginning of the LLM's response.
	This helps when models (like Codellama) include the prompt in the output.
	"""
	# Find the first line that starts with actual code
	for i, line in enumerate(response.splitlines()):
		if line.strip().startswith("import") or line.strip().startswith("from"):
			return "\n".join(response.splitlines()[i:])

	# Fallback: return entire response if no 'import' or 'from' found
	return response

def sanitize_code_response(response: str) -> str:
	code_blocks = re.findall(r"```(?:python)?\s*(.*?)```", response, flags=re.DOTALL | re.IGNORECASE)
	if code_blocks:
		clean_code = code_blocks[0].strip()
	else:
		lines = response.strip().splitlines()
		code_lines = [line for line in lines if line.strip() and not line.strip().lower().startswith("in this") and not line.strip().startswith("# ") and not line.strip().startswith("```")]
		clean_code = "\n".join(code_lines)
	return clean_code.strip()

def safe_code_llm(prompt):
	try:
		_, code_model = get_model_config()
		rephrased_prompt = rewrite_code_prompt(prompt)

		raw_output = call_ollama_model(code_model, rephrased_prompt)
		print(f"[DEBUG] Raw LLM output (before cleaning):\n{raw_output}\n{'='*50}")

		clean_code = strip_prompt_echo(prompt, raw_output)
		print(f"[DEBUG] Cleaned LLM output (before syntax check):\n{clean_code}\n{'='*50}")

		if not raw_output or not isinstance(raw_output, str) or raw_output.strip().startswith("[ERROR]"):
			raise ValueError("Empty or invalid response from code LLM")

		if not is_valid_python_code(clean_code):
			print("[WARN] LLM returned invalid Python code")
			return None

		return clean_code

	except Exception as e:
		print(f"[FALLBACK] Failed to call raw LLM: {e}")
		return None

def is_valid_python_code(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        print(f"[SYNTAX ERROR] {e}")
        return False

def is_meaningful_change(original: str, modified: str) -> bool:
    if not original or not modified:
        return False
    if original.strip() == modified.strip():
        return False

    def normalize(code: str) -> str:
        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                no_comment = stripped.split("#")[0].strip()
                if no_comment:
                    lines.append(no_comment)
        return "\n".join(lines)

    orig_norm = normalize(original)
    mod_norm = normalize(modified)

    return orig_norm != mod_norm

def score_code_patch(refactored_code: str, original_code: str = "") -> int:
    if not refactored_code.strip():
        return 0
    try:
        ast.parse(refactored_code)
    except SyntaxError:
        return 0
    if original_code and not is_meaningful_change(original_code, refactored_code):
        return 1
    score = 4
    lines = refactored_code.strip().splitlines()
    if len(lines) >= 3:
        score += 2
    if all(line.strip() == "" or line.startswith("    ") or line.startswith("\t") for line in lines):
        score += 2
    if any("def " in line or "class " in line for line in lines):
        score += 1
    if original_code:
        diff = list(difflib.unified_diff(
            original_code.strip().splitlines(),
            refactored_code.strip().splitlines(),
            lineterm=""
        ))
        change_count = len([l for l in diff if l.startswith(("+", "-")) and not l.startswith(("---", "+++"))])
        if change_count > 1:
            score += 1
    return min(10, max(0, score))

def log_patch_score(prompt: str, score: int, raw_code: str):
	log_path = Path(__file__).resolve().parents[1] / "memory" / "rewards_log.json"
	log_entry = {
		"timestamp": datetime.now().isoformat(),
		"score": score,
		"prompt": prompt.strip()[:100],
		"code_preview": raw_code.strip()[:300]
	}

	if log_path.exists():
		try:
			with open(log_path, "r", encoding="utf-8") as f:
				data = json.load(f)
		except (json.JSONDecodeError, ValueError):
			print("[WARN] rewards_log.json was empty or corrupted. Resetting log.")
			data = []
	else:
		data = []

	data.append(log_entry)

	with open(log_path, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2)


# Mistral - natural language / reasoning
def call_chat_llm(prompt: str) -> str:
	try:
		config = load_config()
		chat_model = config["llm"]["chat_model"]
	except Exception as e:
		print(f"[ERROR] Failed to load config: {e}")
		return "[ERROR] Could not load chat model configuration."
	identity_prompt = config.get("chat", {}).get("system_prompt", "")
	context_prompt = get_saias_context()
	style_rules = (
		"Guidance: Be concise (1-3 short sentences for casual chat). "
		"Do not restate your identity, offline/local status, or implementation details unless asked. "
		"Answer directly and naturally; avoid boilerplate and repetition."
	)
	system_prompt = f"{identity_prompt}\n\n{context_prompt}\n\n{style_rules}"
	print(f"[DEBUG] Loaded system prompt (truncated): {system_prompt[:100]}...")

	# Incorporate recent chat history (limit to avoid token bloat)
	recent = load_recent(6)
	messages = [{"role": "system", "content": system_prompt}]
	for m in recent:
		role = m.get("role")
		content = m.get("content")
		if role in ("user", "assistant") and isinstance(content, str):
			# clip overly long turns to reduce verbosity feedback loops
			clip = content.strip()
			if len(clip) > 500:
				clip = clip[:500] + "…"
			messages.append({"role": role, "content": clip})
	# Current user prompt last
	messages.append({"role": "user", "content": prompt})

	payload = {
		"model": chat_model,
		"messages": messages,
		"stream": False,
		"options": {"num_predict": 200, "temperature": 0.5, "repeat_penalty": 1.1}
	}

	print("[DEBUG] Injected capabilities:\n", capabilities_data)
	print("[DEBUG] Injected root registry:\n", root_registry_data)
	print(f"[DEBUG] Calling chat model '{chat_model}' with payload:")
	print(json.dumps(payload, indent=2)[:500])
	try:
		response = requests.post("http://localhost:11434/api/chat", json=payload)
		response.raise_for_status()
		result = response.json()
		return result.get("message", {}).get("content", "[ERROR] No content in response.")
	except Exception as e:
		return f"[ERROR] Failed to call model '{chat_model}': {e}"


# Deepseek - code generation / refactoring
def call_code_llm(prompt):
	_, code_model = get_model_config()
	rephrased_prompt = rewrite_code_prompt(prompt)
	print(f"[DEBUG] Calling code model '{code_model}' with prompt (truncated): {rephrased_prompt[:100]}...")
	print(f"[DEBUG] Rewritten code prompt:\n{rephrased_prompt[:300]}")
	system_prompt = get_prompt("rewrite_code")
	raw_output = call_ollama_model(code_model, rephrased_prompt, system_prompt)
	sanitized = sanitize_code_response(raw_output)
	clean_code = strip_prompt_echo(rephrased_prompt, sanitized)
	print(f"[DEBUG] Raw LLM Output (truncated):\n{raw_output[:300]}")
	score = score_code_patch(clean_code)
	print(f"[DEBUG] Patch Score: {score}/10")
	log_patch_score(prompt, score, clean_code)
	if not is_valid_python_code(clean_code):
		print("[WARN] LLM returned invalid Python code")
	return clean_code
