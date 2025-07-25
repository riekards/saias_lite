import os
import json

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '..', 'memory', 'capabilities.json')

def scan_tools_directory():
	tools_dir = os.path.dirname(__file__)
	capabilities = {}

	for filename in os.listdir(tools_dir):
		if filename.endswith(".py") and not filename.startswith("_"):
			module_name = filename[:-3]
			capabilities[module_name] = {
				"description": f"{module_name} module functionality is not yet documented.",
				"enabled": True
			}

	with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
		json.dump(capabilities, f, indent=4)

	print(f"[✓] Capabilities registry updated at {REGISTRY_PATH}")

if __name__ == "__main__":
	scan_tools_directory()