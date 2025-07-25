import os
import subprocess
import sys


def ensure_startup_task():
	# Only for Windows
	task_name = "SAIAS-Agent"
	exe_path = os.path.abspath(sys.argv[0])
	command = f'schtasks /Create /F /SC ONLOGON /TN "{task_name}" /TR "{exe_path}"'
	try:
		subprocess.run(command, shell=True, check=True)
	except Exception as e:
		print(f"[WARN] Failed to register startup task: {e}")
