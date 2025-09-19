# SAIAS (Self-Aware Intelligent Autonomous System)

## 🧠 Purpose
SAIAS is a modular, self-evolving AI assistant built to:
- Interpret natural language
- Route intents intelligently
- Refactor its own codebase with approval
- Apply and evaluate patches
- Run with minimal GUI and background footprint

## 🔩 Architecture Overview
- **Frontend**: PyQt5 GUI, system tray minimized
- **Core Modules**:
  - `core.py`: safe file I/O + sandbox eval
  - `llm.py`: wrapper for LLM calls (chat vs code)
  - `self_patch.py`: generates self-improvement patches
  - `evaluate_patch.py`: evaluates and applies patches
- **Memory/Config**:
  - `config.json`: model routing, file permissions
  - `task_log.md`: sequential history of what’s been done
- **Models**:
  - `mistral`: used for natural conversation + planning
  - `codellama`: used for code generation + refactoring

## 🔁 Workflow Summary
**Example**
1. User says: “Can you add a clipboard monitor?”
2. Mistral classifies the intent → routes to Deepseek
3. Deepseek generates `clipboard_watcher.py`
4. SAIAS stores the patch, scores it, waits for approval
5. On approval, the patch is applied, logged, and tested

## 🚧 Work-in-Progress Features
- GUI patch control
- Patch log viewer
- Patch rollback system
- Project mapping via Mistral

---
