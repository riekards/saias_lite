import os
import json
from pathlib import Path
import shutil
import datetime
from agent.tools.dependency_graph import DependencyGraph
from agent.tools.rewards import log_reward

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

	file_path = data["target_file"]
	backup_path = f"{file_path}.bak"

	if not os.path.exists(backup_path):
		print(f"[WARN] Backup missing for {file_path}, skipping.")
		log_reward("rejected", patch_id=patch_id, file=str(file_path), reason="backup_missing")
		return False

	try:
		# Restore backup first (undo prior changes)
		shutil.copyfile(backup_path, file_path)

		# Simulate patch: add comment line to show it was patched
		with open(file_path, "r+", encoding="utf-8") as f:
			lines = f.readlines()
			lines.insert(0, "# [SAIAS PATCHED VERSION]\n")
			f.seek(0)
			f.writelines(lines)

		# Update patch file
		data["applied"] = True
		data["approved"] = True
		with open(patch_path, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2)

		# Rewards: successful approval
		log_reward("approved", patch_id=patch_id, file=str(file_path), score=float(data.get("refactor_score", 0)))
	except Exception as e:
		# Rewards: failed to apply
		log_reward("rejected", patch_id=patch_id, file=str(file_path), reason=f"apply_failed:{e.__class__.__name__}")
		print(f"[ERROR] Failed to apply patch {patch_id}: {e}")
		return False

	print(f"[✅] Patch {patch_id} applied.")
	return True


def print_pending_patch_summaries():
	patches = list_pending_patches()
	if not patches:
		print("✅ No pending patches.")
		return

	print("\n🧠 Pending Patch Summaries:\n")
	for fname, patch in patches:
		print(f"• Patch ID: {patch['patch_id']}")
		print(f"  ↪ File: {patch['target_file']}")
		print(f"  ↪ Score: {patch['refactor_score']}/10")
		print(f"  ↪ Summary: {patch['description']}")
		# Show impact
		target_file = patch['target_file']
		graph = DependencyGraph()
		graph.build()
		dependents = graph.get_dependents(target_file)
		if dependents:
			print(f"  ⚠️  Impacts: {len(dependents)} dependent file(s)")
		else:
			print(f"  ✅ Safe: No other files depend on this")
		print("")

if __name__ == "__main__":
	print_pending_patch_summaries()

	# Sample input loop (replace later with GUI/voice handler)
	while True:
		user_input = input(">> ").strip().lower()
		if user_input.startswith("approve patch"):
			ids = user_input.replace("approve patch", "").strip()
			id_list = [x.strip().upper() for x in ids.split(",")]
			for patch_id in id_list:
				apply_patch_by_id(patch_id)
		elif user_input in {"exit", "quit"}:
			break
		elif user_input == "show":
			print_pending_patch_summaries()
		else:
			print("Unknown command. Use:\n- approve patch PATCH_xxx\n- show\n- exit")
