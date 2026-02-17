# Compound Engineering Methodology -- Content Orchestrator

This file defines the exact build process. Follow it every time, without being asked.

---

## The RC Method (Phase Gates)

Every phase produces artifacts. Every phase ends with a **gate** where the product owner approves before moving on. Never skip a gate.

```
1. ILLUMINATE  → Understand the problem (read PRD, ask questions)
2. DEFINE      → Lock scope and schemas
3. ARCHITECT   → Design components, database, infrastructure
4. SEQUENCE    → Break into vertical build slices
5. VALIDATE    → Security, UX, and cost checklists
6. FORGE       → Build each slice (this is where code gets written)
7. CONNECT     → Integration testing, end-to-end verification
8. COMPOUND    → Extract learnings, update patterns, improve process
```

### Gate Approval Format (MANDATORY)

Before every gate, explain to the product owner in **plain English**:
1. **What we just did** (1-2 sentences, no jargon)
2. **What we're asking you to approve** (bullet list of decisions/files)
3. **What happens next if you approve** (what gets built)
4. **What could go wrong** (risks, in simple terms)
5. **How you can verify** (3 steps a non-technical person can do)

---

## The Compound Loop (Every Slice)

Every build slice follows this loop:

```
PLAN    → Write what we'll build and why (before touching code)
WORK    → Write the code (Ralph loop: run → fix → rerun, max 5 tries)
REVIEW  → Show what changed in plain English + tests + verification steps
COMPOUND → Save reusable patterns to docs/compound/patterns/
```

### Review Format (MANDATORY -- shown after every slice)

| Section | What to include |
|---------|----------------|
| What files changed | List of files created/modified |
| What changed in behavior | Plain English, no jargon |
| Tests run + results | Pass/fail summary |
| How to verify manually | 3 steps the owner can do |
| Risks + mitigations | What could break, how we prevent it |

### Compound Step (MANDATORY -- after every slice)

After completing a slice, save any reusable pattern to `docs/compound/patterns/`. Examples:
- `rls.md` -- How we do row-level security
- `async-worker.md` -- How we do background jobs
- `fastapi-auth.md` -- How we do authentication
- `langgraph-interrupts.md` -- How we pause/resume pipelines
- `resource-ingestion.md` -- How we process uploaded files

---

## The Ralph Loop (Inside WORK Only)

When writing code, follow this loop (max 5 iterations):

```
1. RUN    → Execute the code / run tests
2. READ   → Read the error messages carefully
3. PATCH  → Fix the specific issue
4. RERUN  → Run again
5. If still failing after 5 loops → STOP and ask the product owner
```

---

## Product Owner Preferences

- **Non-technical.** Always explain in plain English. No jargon.
- **Wants to understand while building.** Every decision, every gate, every slice review must be written for someone who doesn't code.
- **Gate checklist.** Before approving anything, the owner needs:
  - What changed (files)
  - What changed (behavior, plain English)
  - Tests run + results
  - How to verify in 3 steps
  - Risks + mitigations
- **Export-only MVP.** No YouTube API publishing (see ADR-01).
- **Compound everything.** Save patterns so the agent can replicate the process on future projects without being reminded.
