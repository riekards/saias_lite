import os
import sys
import json
import shutil
import subprocess
import ast
import importlib.util
import difflib
import logging
from datetime import datetime
from pathlib import Path
from agent.tools.llm import call_code_llm
from agent.tools.llm import score_code_patch
from agent.tools.llm import safe_code_llm
from agent.tools.code_chunker import chunk_and_refactor_file, ChunkContext
from agent.tools.backup import backup_file
from agent.tools.auto_test import run_patch_tests
from agent.tools.dependency_graph import DependencyGraph
from agent.tools.rewards import log_reward

ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent
PATCH_DIR = ROOT_DIR / "memory" / "patch_notes"
SKIPPED_LOG = PATCH_DIR / "skipped_patches.log"
PATCH_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename='saiasselfpatch_log.log', level=logging.DEBUG, 
					format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Your clear log message here.")

def apply_patch(file_path, patch_content):
	backup_file(file_path)  # First backup the original file
	try:
		with open(file_path, 'w') as file:
			file.write(patch_content)
		logging.info(f"Patch applied successfully to {file_path}")

		if run_patch_tests():
			logging.info("Patch successfully tested and verified.")
		else:
			raise Exception("Patch tests failed. Reverting changes.")
	except Exception as e:
		logging.error(e)
		backup_path = os.path.join(ROOT_DIR, 'backups', os.path.basename(file_path))
		shutil.copy(backup_path, file_path)
		logging.info(f"Original file restored from backup ({backup_path}).")

def get_all_python_files(base_dir="."):
	ignore_dirs = {"venv", "__pycache__", "tests"}
	ignore_files = {"__init__.py"}

	py_files = []
	for root, dirs, files in os.walk(base_dir):
		dirs[:] = [d for d in dirs if d not in ignore_dirs]
		for file in files:
			if file.endswith(".py") and file not in ignore_files:
				full_path = os.path.join(root, file)
				py_files.append(full_path)
	return py_files

def test_patch(temp_path):
	try:
		subprocess.run(["python", temp_path], check=True, timeout=10, capture_output=True)
		return True
	except Exception:
		return False

def log_skipped_patch(filename: str, reason: str):
	print(f"[DEBUG] Skipped log path: {SKIPPED_LOG}")
	with open(SKIPPED_LOG, "a", encoding="utf-8") as f:
		f.write(f"{datetime.now().isoformat()} - {filename}: {reason}\n")

def is_meaningful_change(original: str, modified: str) -> bool:
	"""
	True only for substantive changes.
	AST-equivalent code (ignoring whitespace, comments, and docstrings) is treated as NO CHANGE.
	Falls back to a lightweight text check if parsing fails.
	"""
	if not original or not modified:
		return False

	def _strip_docstrings(tree: ast.AST) -> ast.AST:
		"""
		Remove module/class/function docstrings so cosmetic doc edits don't count as changes.
		"""
		def drop_first_docstring(body):
			if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
				return body[1:]
			return body

		class _Stripper(ast.NodeTransformer):
			def visit_Module(self, node: ast.Module):
				self.generic_visit(node)
				node.body = drop_first_docstring(node.body)
				return node
			def visit_FunctionDef(self, node: ast.FunctionDef):
				self.generic_visit(node)
				node.body = drop_first_docstring(node.body)
				return node
			def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
				self.generic_visit(node)
				node.body = drop_first_docstring(node.body)
				return node
			def visit_ClassDef(self, node: ast.ClassDef):
				self.generic_visit(node)
				node.body = drop_first_docstring(node.body)
				return node
		return _Stripper().visit(tree)

	def _ast_normalize(src: str) -> str:
		tree = ast.parse(src)
		tree = _strip_docstrings(tree)
		for n in ast.walk(tree):
			for field in ("lineno","col_offset","end_lineno","end_col_offset"):
				if hasattr(n, field):
					setattr(n, field, None)
		# dump without attributes; this gives a structural fingerprint
		return ast.dump(tree, annotate_fields=False, include_attributes=False)

	try:
		return _ast_normalize(original) != _ast_normalize(modified)
	except Exception:
		# Fallback: ignore whitespace-only and comment-only diffs
		def _text_norm(code: str) -> str:
			lines = []
			for line in code.splitlines():
				s = line.strip()
				if not s or s.startswith("#"):
					continue
				lines.append(s.split("#")[0].strip())
			return "\n".join(l for l in lines if l)
		return _text_norm(original) != _text_norm(modified)

def safe_import_test(file_path):
	try:
		spec = importlib.util.spec_from_file_location("test_module", file_path)
		if spec is None or spec.loader is None:
			return False
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return True
	except Exception as e:
		print(f"[TEST ERROR] {file_path} → {e}")
		return False

def load_pending_patch_map():
	patch_map = {}
	for patch_file in PATCH_DIR.glob("PATCH_*.json"):
		try:
			with open(patch_file, "r", encoding="utf-8") as f:
				data = json.load(f)
				if not data.get("applied"):
					patch_map[data["target_file"]] = True
		except Exception:
			continue
	return patch_map

def _aggregate_chunk_score(chunk_metadata) -> float:
	"""
	Aggregate per-chunk scores into a file-level score.
	Fallback to 0 if no usable scores.
	"""
	if not chunk_metadata:
		return 0.0
	scores = []
	for ch in chunk_metadata:
		try:
			s = float(ch.get("score", 0))
			if s >= 0:
				scores.append(s)
		except Exception:
			continue
	return sum(scores) / len(scores) if scores else 0.0

def run_self_patch():
	patches_created = 0
	pending_patch_map = load_pending_patch_map()

	# Build debug dump dir once
	debug_dump_dir = ROOT_DIR / "memory" / "debug_code_dump"
	debug_dump_dir.mkdir(parents=True, exist_ok=True)

	# ✅ Single loop — no redundancy
	for file_path in get_all_python_files():
		file_path = Path(file_path)  # Ensure it's a Path object

		# 1. Read original code once
		try:
			with open(file_path, "r", encoding="utf-8") as f:
				original_code = f.read()
				graph = DependencyGraph()
				graph.build()

				rel_path = os.path.relpath(file_path, ROOT_DIR)
				dependents = graph.get_dependents(rel_path)
				if dependents:
					print(f"[⚠️] {file_path} is used by: {', '.join(dependents)}")
					warning_comment = (
						f"# WARNING: This file is imported by:\n"
						f"# {', '.join([f'  - {d}' for d in dependents])}\n"
						f"# Do NOT change public function signatures or break compatibility.\n"
						f"# If you modify any exported functions, ensure backward compatibility.\n\n"
					)
					original_code = warning_comment + original_code
		except Exception as e:
			logging.error(f"Failed to read {file_path}: {e}")
			continue

		# 2. Save debug dump (optional: only if needed)
		debug_file_path = debug_dump_dir / f"{file_path.stem}.txt"
		with open(debug_file_path, "w", encoding="utf-8") as debug_out:
			debug_out.write(original_code)

		# 3. Skip if already pending
		if pending_patch_map.get(str(file_path)):
			log_skipped_patch(str(file_path), "Already patched")
			continue

		# 4. Attempt refactoring (with one retry if empty)
		refactored_code, chunk_metadata = chunk_and_refactor_file(str(file_path))
		if not refactored_code:
			# simple nudge retry — same call, models often succeed on 2nd try
			refactored_code, chunk_metadata = chunk_and_refactor_file(str(file_path))
		if not refactored_code:
			print(f"[SKIP] LLM returned no code for {file_path}")
			log_skipped_patch(str(file_path), "LLM returned empty or invalid code")
			log_reward("skipped", reason="empty_or_invalid_code", file=str(file_path))
			continue

		# 5. Score the refactor (prefer chunk scores; fall back to LLM score)
		chunk_score = _aggregate_chunk_score(chunk_metadata)
		try:
			llm_score = score_code_patch(refactored_code, original_code)
		except Exception:
			llm_score = 0
		refactor_score = max(chunk_score, llm_score)
		if refactor_score < 4:
			print(f"[SKIP] Refactor score too low ({refactor_score:.1f}/10) for {file_path}")
			log_skipped_patch(str(file_path), f"Refactor score too low ({refactor_score:.1f}/10)")
			log_reward("skipped", reason="low_score", score=float(refactor_score), file=str(file_path))
			continue

		# 6. Check for meaningful change (AST gate)
		if not is_meaningful_change(original_code, refactored_code):
			print(f"[SKIP] No meaningful changes detected (AST-equivalent) in {file_path}")
			log_skipped_patch(str(file_path), "ast_equivalent_or_cosmetic")
			log_reward("skipped", reason="ast_equivalent_or_cosmetic", file=str(file_path))
			continue

		# 7. Test in sandbox
		temp_path = f"{file_path}.temp"
		with open(temp_path, "w", encoding="utf-8") as f:
			f.write(refactored_code)

		if "gui.py" in str(file_path) or "run.py" in str(file_path):
			test_passed = safe_import_test(temp_path)
		else:
			test_passed = test_patch(temp_path)

		# 8. Apply patch if test passed
		if test_passed:
			# Backup original
			backup_path = f"{file_path}.bak"
			with open(backup_path, "w", encoding="utf-8") as f:
				f.write(original_code)

			# Generate patch ID and info
			timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
			patch_id = f"PATCH_{timestamp}_{file_path.stem}"
			patch_info = {
				"patch_id": patch_id,
				"target_file": str(file_path),
				"description": "Refactored for readability and maintainability.",
				"refactor_score": refactor_score,
				"timestamp": timestamp,
				"applied": False,
				"approved": False,
				"original_code": original_code,
				"refactored_code": refactored_code,
				"chunks": chunk_metadata,
			}

			# Save patch
			patch_file = PATCH_DIR / f"{patch_id}.json"
			with open(patch_file, "w", encoding="utf-8") as f:
				json.dump(patch_info, f, indent=2)

			# credit SAIAS for generating a non-cosmetic patch
			# (use fields from patch_info so names can drift without breaking)
			chunks = patch_info.get("chunks", []) or []
			chunk_avg = (sum(float(c.get("score", 0)) for c in chunks) / len(chunks)) if chunks else 0.0
			log_reward(
				"emitted",
				patch_id=patch_id,
				file=str(patch_info.get("target_file") or patch_info.get("file") or ""),
				score=float(patch_info.get("refactor_score", 0)),
				chunk_avg=float(chunk_avg),
			)

		# 9. Clean up temp file
		try:
			os.remove(temp_path)
		except:
			pass

	return patches_created

if __name__ == "__main__":
	count = run_self_patch()
	print(f"✅ {count} patch(es) generated.")