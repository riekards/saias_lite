import os
import sys
import json
from pathlib import Path
import shutil
import datetime
from agent.tools.dependency_graph import DependencyGraph
from agent.tools.rewards import log_reward
from agent.tools.auto_test import run_patch_tests
from agent.tools.root_registry import update_registry

ROOT_DIR = Path(__file__).resolve().parents[1]
PATCH_DIR = ROOT_DIR / "memory" / "patch_notes"
PATCH_DIR.mkdir(parents=True, exist_ok=True)


def list_pending_patches():
	patches = []
	for patch_file in sorted(PATCH_DIR.glob("PATCH_*.json")):
		with open(patch_file, "r", encoding="utf-8") as f:
			data = json.load(f)
			if not data.get("applied", False):
				patches.append((patch_file.name, data))
	return patches


def apply_patch_by_id(patch_id):
	patch_path = PATCH_DIR / f"{patch_id}.json"
	if not patch_path.exists():
		print(f"[ERROR] Patch {patch_id} not found.")
		log_reward("rejected", patch_id=patch_id, reason="not_found")
		return False

	with open(patch_path, "r", encoding="utf-8") as f:
		data = json.load(f)

	file_path = data.get("target_file")
	refactored_code = data.get("refactored_code", "")
	original_code = data.get("original_code", "")
	backup_path = f"{file_path}.bak"

	# Ensure backup exists; create one if missing
	if not os.path.exists(backup_path):
		try:
			if original_code:
				with open(backup_path, "w", encoding="utf-8") as bf:
					bf.write(original_code)
				print(f"[INFO] Created missing backup for {file_path} from patch data.")
			else:
				shutil.copyfile(file_path, backup_path)
				print(f"[INFO] Created backup from current file for {file_path}.")
		except Exception as e:
			print(f"[ERROR] Could not create backup for {file_path}: {e}")
			log_reward("rejected", patch_id=patch_id, file=str(file_path), reason=f"backup_create_failed:{e.__class__.__name__}")
			return False

	try:
		if not isinstance(refactored_code, str) or not refactored_code.strip():
			print(f"[ERROR] Patch {patch_id} has no refactored_code content.")
			log_reward("rejected", patch_id=patch_id, file=str(file_path), reason="empty_refactor")
			return False

		# Apply the refactored code
		with open(file_path, "w", encoding="utf-8") as f:
			f.write(refactored_code)

		# Optionally run tests and gate application
		tests_ok = True
		try:
			tests_ok = run_patch_tests()
		except Exception:
			tests_ok = False

		if tests_ok:
			data["applied"] = True
			data["approved"] = True
			with open(patch_path, "w", encoding="utf-8") as f:
				json.dump(data, f, indent=2)
			log_reward("approved", patch_id=patch_id, file=str(file_path), score=float(data.get("refactor_score", 0)))
			log_reward("tests_passed", patch_id=patch_id, file=str(file_path))
			# Refresh registry and capability usage after a successful apply
			try:
				update_registry()
			except Exception as e:
				print(f"[WARN] Could not update root registry: {e}")
			try:
				graph = DependencyGraph()
				graph.build()
				graph.update_capability_usage()
			except Exception as e:
				print(f"[WARN] Could not update capability usage: {e}")
		else:
			# Revert if tests fail
			shutil.copyfile(backup_path, file_path)
			log_reward("tests_failed", patch_id=patch_id, file=str(file_path))
			print(f"[ERROR] Tests failed after applying {patch_id}. Reverted changes.")
			return False
	except Exception as e:
		log_reward("rejected", patch_id=patch_id, file=str(file_path), reason=f"apply_failed:{e.__class__.__name__}")
		print(f"[ERROR] Failed to apply patch {patch_id}: {e}")
		return False

	print(f"[?] Patch {patch_id} applied.")
	return True


def print_pending_patch_summaries():
	patches = list_pending_patches()
	if not patches:
		print("? No pending patches.")
		return

	print("\n?? Pending Patch Summaries:\n")
	for fname, patch in patches:
		print(f"\a Patch ID: {patch['patch_id']}")
		print(f"  • File: {patch['target_file']}")
		print(f"  • Score: {patch['refactor_score']}/10")
		print(f"  • Summary: {patch['description']}")
		# Show impact
		target_file = patch['target_file']
		graph = DependencyGraph()
		graph.build()
		dependents = graph.get_dependents(target_file)
		if dependents:
			print(f"  • Impacts: {len(dependents)} dependent file(s)")
		else:
			print(f"  • Safe: No other files depend on this")
		print("")


if __name__ == "__main__":
	# CLI behavior:
	#   python -m agent.tools.evaluate_patch               -> list pending patches
	#   python -m agent.tools.evaluate_patch PATCH_ID ...  -> apply patches by ID
	args = [a.strip() for a in sys.argv[1:] if a.strip()]
	if not args:
		print_pending_patch_summaries()
	else:
		# Support space- or comma-separated IDs
		raw_ids = []
		for a in args:
			raw_ids.extend([x for x in a.split(",") if x])
		ids = [x.strip().upper() for x in raw_ids]
		applied = 0
		for pid in ids:
			if apply_patch_by_id(pid):
				applied += 1
		print(f"Applied {applied}/{len(ids)} patch(es).")
