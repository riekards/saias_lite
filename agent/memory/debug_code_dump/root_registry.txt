import os
import json

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REGISTRY_PATH = os.path.join(ROOT_PATH, 'memory', 'root_registry.json')

def build_file_tree(base_dir):
	file_tree = {}

	for root, dirs, files in os.walk(base_dir):
		rel_root = os.path.relpath(root, base_dir).replace("\\", "/")
		if rel_root == ".":
			rel_root = ""
		current = file_tree
		for part in rel_root.split("/"):
			if part:
				current = current.setdefault(part, {})
		for f in files:
			current[f] = "file"

	return file_tree

def update_registry():
	tree = build_file_tree(ROOT_PATH)
	with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
		json.dump(tree, f, indent=2)

	print(f"[✓] Root registry saved at {REGISTRY_PATH}")

if __name__ == "__main__":
	update_registry()