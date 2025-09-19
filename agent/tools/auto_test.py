# [SAIAS PATCHED VERSION]
import subprocess

def run_patch_tests():
    try:
        result = subprocess.run(['python', '-m', 'unittest', 'discover', '-s', 'tests'], capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("Tests passed successfully.")
            return True
        else:
            print("Tests failed:\n", result.stdout, result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("Tests timed out.")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False