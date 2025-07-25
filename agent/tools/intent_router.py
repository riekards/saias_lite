def detect_intent(user_input: str) -> str:
	"""
	Returns 'code' if the input likely needs code generation,
	otherwise returns 'chat'.
	"""
	code_keywords = [
		"generate", "refactor", "write code", "create script",
		"build api", "make function", "python code", "javascript code"
	]

	lower_input = user_input.lower()
	for phrase in code_keywords:
		if phrase in lower_input:
			print(f"[DEBUG] Intent detected as 'code' based on phrase: '{phrase}'")
			return "code"
	print("[DEBUG] Intent detected as 'chat'")
	return "chat"
