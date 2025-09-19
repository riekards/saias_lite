# SAIAS Lite

Local, offline‑first AI assistant that can read and refactor its own codebase and grow new capabilities with your approval. It ships with a small PyQt GUI, uses local LLMs via Ollama, and includes a “self‑patcher” pipeline that proposes safe refactors for you to review and apply.

## What It Does

- Self‑refactor pipeline: analyzes Python files, chunks code with AST context, asks a local code LLM to refactor, scores the change, runs lightweight tests, and saves a pending patch (JSON) for human approval.
- Patch management UI: tray/window app shows pending patches, lets you approve/apply them, and provides a quick chat input.
- Capability growth: when you ask to “write/create/make/add …”, it can generate a new tool module under `agent/tools/` and register it for future use.
- Dependency awareness: builds a project dependency graph to warn about potential breakages and surface impact.
- Offline‑first LLMs: integrates with local models via Ollama (chat + code) configured in `agent/memory/config.json`.
- Safety & logging: backs up files before changes, can run tests before proposing a patch, and logs events/rewards to `agent/memory`.

## Repository Overview

- `run.py`: launches the GUI.
- `agent/gui.py`: PyQt GUI (tray + window), hotkey wake, patch viewing/approval, simple chat.
- `agent/planner.py`: creates new “capabilities” (tools) via LLM; optional Qwen‑Agent integration for tool execution.
- `agent/tools/`:
  - `llm.py`: LLM I/O (Ollama chat/code), prompt shaping, patch scoring.
  - `self_patch.py`: scans files, generates/refines patches, backs up originals, writes patch notes.
  - `code_chunker.py`: AST‑aware chunking + integrity checks to keep public interfaces stable.
  - `evaluate_patch.py`: lists pending patches and applies approved ones (uses backups, records outcomes).
  - `dependency_graph.py`: maps file‑level deps and dependents.
  - `intent_router.py`: routes chat vs. patch/capability actions.
  - `agent_tools.py`: auto‑discovers tools for Qwen‑Agent.
  - `rewards.py`, `backup.py`, `auto_test.py`, `background_setup.py`, `root_registry.py`: utilities for logging, backups, testing, startup, and file tree registry.
- `agent/memory/`: runtime data and config
  - `config.json`: model names, prompts, and behavior flags.
  - `capabilities.json`, `root_registry.json`, `rewards_log.jsonl`.
  - `patch_notes/`: pending patch JSONs (created by the self‑patcher).
  - `debug_code_dump/`: snapshots of original code when patching.
- `tests/`: minimal PyQt smoke test.

## How It Works (High‑Level)

1. The self‑patcher (`agent/tools/self_patch.py`) walks Python files, uses `CodeChunker` to create context‑aware prompts, calls the code LLM, validates and scores the result, runs lightweight tests, then writes a patch JSON and an on‑disk backup (`.bak`).
2. The GUI (`agent/gui.py`) shows pending patches and can apply them via `evaluate_patch.py`. Applying restores from backup and marks the file as patched.
3. If your request implies adding functionality (e.g., “create a … tool”), the planner may generate a new module in `agent/tools/` and register it for future use.

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Ensure Ollama is running and the models in `agent/memory/config.json` are available (e.g., `mistral` for chat and `qwen3:30b` for code), or edit the config to match your local models.
3. Run the app: `python run.py`
4. In the window:
   - Type `show` to list pending patches.
   - Click “Approve All Patches” to apply queued patches, or type `approve patch PATCH_...` to apply a specific one.
   - Ask to “create …” to generate a new capability/tool.

## Notes

- Windows background startup uses Task Scheduler; toggle in `agent/memory/config.json`.
- Capability execution via Qwen‑Agent is optional; you may need to install/enable it separately if you plan to use agent tool execution.
- Keep the repo under version control. Although files are backed up before patching, version control remains the safest rollback path.
