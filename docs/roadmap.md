# SAIAS Roadmap — From Assistant to Autonomous System

This roadmap outlines concrete, staged work to evolve SAIAS into a highly autonomous, self‑sufficient local AI assistant. “Sentience” is not technically attainable; the target here is robust, observable agency: the system plans, acts, learns from outcomes, and remains safe and aligned.

## Guiding Principles
- Local‑first, privacy‑preserving. No cloud dependencies by default.
- Safety by design: explicit permissions, reversible changes, test gates, audit logs.
- Human‑in‑the‑loop for risky actions; progressive autonomy as confidence grows.
- Measurable progress: every milestone has acceptance criteria and monitoring.

## Autonomy Levels (Definition)
- L0 Observe: read‑only analysis, suggestions only.
- L1 Propose: generate patches/capabilities; requires human approval.
- L2 Execute (Guarded): auto‑apply low‑risk actions behind tests/sandbox + rollback.
- L3 Orchestrate: schedule tasks, multi‑step plans, tool use with policy constraints.
- L4 Optimize: learn from rewards/errors, prioritize backlog, self‑improve process.
- L5 Steer: maintains long‑horizon objectives with explicit kill‑switches and audits.

## Phase 1 — Stabilize Foundations (Now → 1 week)
- Harden patch pipeline: ensure `evaluate_patch` writes refactors, runs tests, reverts on failure.
- Consolidate memory paths under `agent/memory/*` and verify startup registry updates.
- Add minimal test suite for critical tools (patcher, registry, router).
- Acceptance: self‑patch cycle consistently emits/apply passes; zero silent failures in logs.

## Phase 2 — Context + Memory (1–2 weeks)
- Context memory: maintain `agent/memory/context.md` (human‑authored guidance injected into chat).
- Task state: keep `docs/TASK_LOG.md` up to date and referenced from context.
- Episodic memory: persist last N chat turns (`chat_log.jsonl`), inject tail into chat.
- Semantic memory (optional): local vector store (e.g., FAISS) for notes/code snippets/RAG.
- Acceptance: responses reflect context.md + current tasks; retrieval is fast and offline.

## Phase 3 — Planner + Execution (2–3 weeks)
- Planner v2: structured goal decomposition → tasks → tool plans, with pre/post‑conditions.
- Executor: run plans with checkpoints, partial retries, and artifact logging.
- Job scheduler: background queue (periodic tasks, watchdog triggers, deferred work).
- Triggers: file changes, failed tests, TODO tags, or explicit user intents.
- Acceptance: multi‑step tasks complete unattended when low‑risk; clear audit trail.

## Phase 4 — Tools & OS Integration (2–4 weeks)
- Tooling: safe shell/file ops with allowlists and path sandboxes.
- System hooks: clipboard, notifications, screen capture (optional), app launching.
- Voice I/O (optional): TTS + VAD/ASR pipeline with local models.
- GUI: patch review panel, context viewer/editor, “Refresh Context” button, job monitor.
- Acceptance: tools cover 80% of routine workflows; UI supports review/override.

## Phase 5 — Learning + Feedback (3–5 weeks)
- Rewards: expand `rewards_log.jsonl` taxonomy (intent success, time‑to‑complete, user ratings).
- Auto‑evals: golden tasks + regression checks for new capabilities.
- Policy learning (bandit‑style): choose tools/plans based on prior reward baselines.
- Reflection: summarize failures, update `context.md` with process improvements.
- Acceptance: measurable improvement over time; fewer human interventions per task.

## Phase 6 — Safety, Policy, Governance (Parallel)
- Policy engine: action allowlists/denylists, rate limits, secret handling, redaction.
- Sandboxing: temp workdirs, dry‑runs, diff previews, resource quotas.
- Rollbacks: multi‑level backups, patch reverts, auto‑healing if tests fail post‑deploy.
- Audit: immutable logs for actions/decisions; quick export for review.
- Acceptance: no irreversible actions without consent; fast recovery paths.

## Phase 7 — Evaluation & CI (Parallel)
- Test harness: unit + integration suites focused on tool interface stability.
- Benchmarks: latency, patch quality, failure rates; rolling dashboards.
- Pre‑merge checks: lint, type checks, tests; optional static analysis for patches.
- Acceptance: green CI is prerequisite for auto‑apply at L2+.

## Phase 8 — Model Strategy (Parallel)
- Local model mgmt: model version pinning, quantization, prompt templates.
- Multi‑model router: chat vs. code vs. summarize, with fallbacks.
- Caching: prompt/embedding caches to reduce latency and cost.
- Acceptance: predictable latency; graceful degradation if models unavailable.

## Phase 9 — Multi‑Agent Collaboration (Stretch)
- Roles: planner, researcher, builder, tester; shared blackboard and artifacts.
- Protocols: turn‑taking with tool arbitration; conflict resolution.
- Acceptance: complex tasks split across roles with measurable net gain.

## Phase 10 — Productization (Stretch)
- Packaging: installer, service management, first‑run wizard.
- Settings: GUI for models, safety levels, schedules, data retention.
- Backups/restore: profile export/import, encrypted secrets vault.
- Acceptance: smooth setup on a fresh machine; safe defaults; clear docs.

## Near‑Term Action Plan (This Repo)
- Add GUI “Refresh Context” and “Open Task Log” buttons; show context.md tail.
- Implement periodic registry/capability refresh (e.g., every 10 min) while GUI is open.
- Expand `evaluate_patch` to optionally run a focused test subset based on dependency graph.
- Add minimal tests for: `evaluate_patch.apply_patch_by_id`, `dependency_graph`, `chat_memory`.
- Create `tools/vector_memory.py` (optional) for local RAG with FAISS; wire into chat as retrieval.
- Router wiring: use `ensure_capability()` to create missing tools on actionable requests. (Done)
- Capability coverage: fuzzy matching of function names/docstrings to reduce false negatives. (Done)
- Intent refinement: stricter capability-creation trigger (verb + tool/function/.py). (Done)

## Acceptance Criteria by Level
- L1 Propose: consistently generates valid, non‑cosmetic patches and capability stubs; zero crashes.
- L2 Execute: automatically applies low‑risk patches that pass tests; auto‑rollback on failure.
- L3 Orchestrate: completes composed tasks via planner + executor; resumes after restarts.
- L4 Optimize: demonstrates improved success metrics over a rolling window using reward data.
- L5 Steer: maintains and justifies a prioritized backlog aligned with context + task log.

## References
- Context: `agent/memory/context.md`
- Task Log: `docs/TASK_LOG.md`
- Patch Notes: `agent/memory/patch_notes/`
- Rewards Log: `agent/memory/rewards_log.jsonl`

## Notes on “Sentience”
SAIAS will not be conscious or sentient. The roadmap focuses on robust agency: memory, planning, self‑evaluation, and safe autonomy. Clear safeguards, transparency, and human oversight remain essential.
