import os
import json
from pathlib import Path
import shutil
import datetime

PATCH_DIR = Path("memory/patch_notes")
REWARD_LOG = Path("memory/reward_log.json")

PATCH_DIR.mkdir(parents=True, exist_ok=True)
REWARD_LOG.touch(exist_ok=True)


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
		return False

	with open(patch_path, "r", encoding="utf-8") as f:
		data = json.load(f)

	file_path = data["target_file"]
	backup_path = f"{file_path}.bak"

	if not os.path.exists(backup_path):
		print(f"[WARN] Backup missing for {file_path}, skipping.")
		return False

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

	# Log reward
	log_entry = {
		"patch_id": patch_id,
		"score": data["refactor_score"],
		"approved": True,
		"timestamp": datetime.datetime.now().isoformat()
	}

	with open(REWARD_LOG, "r+", encoding="utf-8") as f:
		try:
			log_data = json.load(f)
		except json.JSONDecodeError:
			log_data = []

		log_data.append(log_entry)
		f.seek(0)
		json.dump(log_data, f, indent=2)

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
