# ?? SAIAS Task Log

## ? Completed
- 2025-06-26: Project audit complete
- 2025-06-26: Architecture plan accepted
- 2025-06-26: Patch system reviewed and verified
- 2025-06-26: Mistral = chat, Deepseek = code generation
- 2025-06-27: Refactor llm.py into chat/code split to route via Ollama API using Mistral + Deepseek
- 2025-06-27: Added "intent_router.py" to classify user prompts as "chat" or "code".
- 2025-06-27: Upgraded "gui.py" to use subtext-based routing for model selection.
- 2025-06-27: Refactored "self_patch.py" to use "call_code_llm()".
- 2025-06-27: Verified that system prompts are correctly injected and respected by the local LLM (Mistral) via llm.py.
- 2025-06-27: Functional Model Handoff Between Mistral and Deepseek
- 2025-06-28: Injected dynamic root structure and capabilities into LLM system prompt
- 2025-06-28: Implemented code sanitization, syntax validation, and patch scoring with logging to rewards_log.json
- 2025-06-28: Added automatic prompt rewriting for code generation to enforce clean, code-only output
- 2025-06-28: Improved patch scoring and logging system.

- 2025-09-16: Added persistent context memory (`agent/memory/context.md`) and wired into chat context.
- 2025-09-16: Implemented persistent chat history (`agent/memory/chat_log.jsonl`), injected last messages into chat prompts.
- 2025-09-16: Auto-updated root registry and capability usage at app startup and after patch application.
- 2025-09-16: Fixed capabilities path to `agent/memory/capabilities.json` and corrected `register_capability(...)` call in planner.
- 2025-09-16: Rewrote patch apply flow to write `refactored_code`, run tests, and support CLI args for applying patches.
- 2025-09-16: Guarded GUI test to avoid blocking test discovery; import-safe without PyQt5.
- 2025-09-16: Repaired `launch_gui` scope/indent and removed unused `pystray` import.
- 2025-09-16: Applied patches for `auto_test.py`, `background_setup.py`, `llm.py`, and `rewards.py` via the new evaluator.
- 2025-09-16: Router upgraded to ensure capabilities: detects actionable requests, checks existing tools, and auto-creates new capabilities when missing.
- 2025-09-16: Capability detection improved with fuzzy matching on discovered functions and docstrings.
 - 2025-09-16: Intent router refined: only creates capabilities on explicit requests (verb + tool/function/module/.py), adds friendlier patch commands, and defaults to LLM chat for general questions.
 - 2025-09-16: Added proposal flow for ability queries ("can you …"): proposes a module + functions, saves pending intent, supports one-word confirmation (yes/proceed) or auto-create via config.

## ?? Planned
- Self-triggered scanning and proposal generation
- Contextual decision-making (basic autonomy)
- Patch ranking and filtering
- Memory evolution (summaries; GUI editor for context)
- Extend GUI with patch review panel and context refresh button
- Safeguards & rollback intelligence (multi-level backups, dry-run validation)
- Periodic registry/capability auto-refresh while GUI is running
