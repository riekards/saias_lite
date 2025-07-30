import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
import importlib.util
import difflib
import logging
from pathlib import Path
from agent.tools.llm import call_code_llm
from agent.tools.llm import score_code_patch
from agent.tools.llm import safe_code_llm
from agent.tools.code_chunker import chunk_and_refactor_file, ChunkContext
from agent.tools.backup import backup_file
from agent.tools.auto_test import run_patch_tests

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
	diff = list(difflib.unified_diff(
		original.strip().splitlines(),
		modified.strip().splitlines()
	))
	return len(diff) > 0

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

def run_self_patch():
	patches_created = 0
	pending_patch_map = load_pending_patch_map()

	for file_path in get_all_python_files():
				# DEBUG: Save the raw code to a text file for inspection
		debug_dump_dir = ROOT_DIR / "memory" / "debug_code_dump"
		debug_dump_dir.mkdir(parents=True, exist_ok=True)

		debug_file_path = debug_dump_dir / f"{Path(file_path).stem}.txt"
		with open(file_path, "r", encoding="utf-8") as f:
			original_code = f.read()

		with open(debug_file_path, "w", encoding="utf-8") as debug_out:
			debug_out.write(original_code)


	for file_path in get_all_python_files():
		if pending_patch_map.get(file_path):
			log_skipped_patch(file_path, "Already patched")
			continue

		with open(file_path, "r", encoding="utf-8") as f:
			original_code = f.read()

		refactored_code, chunk_metadata = chunk_and_refactor_file(file_path)
		if not refactored_code:
			print(f"[SKIP] LLM returned no code for {file_path}")
			log_skipped_patch(str(file_path), "LLM returned empty or invalid code")
			continue

		refactor_score = score_code_patch(refactored_code, original_code)
		if refactor_score < 3:
			print(f"[SKIP] Refactor score too low ({refactor_score}/10) for {file_path}")
			log_skipped_patch(str(file_path), f"Refactor score too low ({refactor_score}/10)")
			continue

		print(f"[DEBUG] Refactoring: {file_path}")
		
		if not refactored_code or not is_meaningful_change(original_code, refactored_code):
			print(f"[SKIP] No meaningful changes detected in {file_path}")
			log_skipped_patch(str(file_path), "No meaningful change")
			continue


		temp_path = f"{file_path}.temp"
		with open(temp_path, "w", encoding="utf-8") as f:
			f.write(refactored_code)

		if "gui.py" in file_path or "run.py" in file_path:
			test_passed = safe_import_test(temp_path)
		else:
			test_passed = test_patch(temp_path)

		if test_passed:
			with open(f"{file_path}.bak", "w", encoding="utf-8") as f:
				f.write(original_code)

			refactor_score = score_code_patch(refactored_code, original_code)
			summary = {
					"description": "Refactored for readability and maintainability.",
					"refactor_score": refactor_score
				}

			timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
			patch_id = f"PATCH_{timestamp}_{Path(file_path).stem}"
			patch_info = {
				"patch_id": patch_id,
				"target_file": file_path,
				"description": summary["description"],
				"refactor_score": summary["refactor_score"],
				"timestamp": timestamp,
				"applied": False,
				"approved": False,
				"original_code": original_code,
				"refactored_code": refactored_code,
				"chunks": chunk_metadata,
			}
			with open(PATCH_DIR / f"{patch_id}.json", "w", encoding="utf-8") as f:
				json.dump(patch_info, f, indent=2)

			patches_created += 1

		os.remove(temp_path)

	return patches_created

if __name__ == "__main__":
	count = run_self_patch()
	print(f"✅ {count} patch(es) generated.")