# PRD — Content Orchestrator (YouTube-First)  
**Product:** Content Orchestrator  
**Version:** v1.0 (MVP PRD)  
**Owner:** You (non-technical product owner)  
**Build style:** Visual Code Editor + RC Method + Compound Engineering + Ralph Loop + Agentic Engineering  
**Core stack:** Agent Zero (planner) + LangGraph (executor/state) + Supabase (storage/RLS) + Next.js (dashboard) + FastAPI (API/worker)  

---

## 0) One-liner (what you’re building)
**An AI content creation agent that researches what’s working, proposes high-upside topics, and generates YouTube scripts (long + shorts) in your voice—with QA, approval, and a memory that improves over time.**

---

## 1) What this is (and what it’s not)
### This **is**
- A **product app (SaaS)** with a dashboard, database, workflows, approvals, and per-user memory.
- A **content agent system** (planner + executor) that reliably turns “goal → research → topic → script → QA → approval → export/publish”.

### This is **not**
- “Just installing Agent Zero.” Agent Zero is a **tool**; this product is the **repeatable factory** around it.
- “Training a new AI model” in MVP. The “brain” comes from **memory + playbooks + workflows + feedback loops**, not from building a new foundation model.

---

## 2) Vision & positioning
### Vision
Give creators a “content brain” that:
- **finds** what audiences are asking for (signals + gaps),
- **suggests** topics and hooks with evidence,
- **writes** full scripts in the creator’s style,
- **tests** for quality/risk/repetition,
- **remembers** what the creator approves and improves over time.

### Positioning (YouTube-first)
- **Not** “another script generator.”
- A **repeatable research→script factory** with:
  - a **topic opportunity engine** (signals + gaps + scoring),
  - a **hook lab** (hook variants + selection),
  - a **quality gate** (testing + approval),
  - a **creator memory** (resources + golden library + feedback).

### Differentiators vs typical tools
Most tools do “generate text.” This does:
1) **Evidence-based topic selection** (signals + gaps + scoring)  
2) **Deterministic pipeline + resumability** (not one-shot chat)  
3) **Per-user memory that compounds** (resources + approvals + edits)  
4) **QA gates** (schema, structure, claim-risk, duplication)  
5) **Audit trail + reproducibility** (workflow snapshots, versions)

---

## 3) Goals & success metrics (MVP)
### MVP goals
- Create a **YouTube Content Pack** from a goal + profile + resources.
- Provide a **topic selection step** (human chooses topic + hook).
- Produce **Long script + 3 Shorts scripts + titles + thumbnail brief**.
- Enforce structure requirements (hook, story, examples/case studies, “new tech”, CTA).
- Save everything in Supabase with **full audit trail**.
- Enable **approve/reject/regenerate** from any step.
- Export/copy content (publish integrations optional and off by default).

### Success metrics (simple)
- Activation: user completes profile + runs 1 workflow.
- Approval rate: % scripts approved without major rewriting.
- Time-to-pack: median time from “Generate” to “Pack ready”.
- Repeat usage: workflows per user per week.
- Quality proxy: number of test flags per final pack (lower is better).
- Reliability: workflow completion rate (no stuck runs).

---

## 4) Target users & JTBD
### Primary persona
**YouTube creator / founder**  
- JTBD: “Find what to talk about and get a strong script that matches my style, fast.”

### Secondary persona
**Small team content lead**  
- JTBD: “Create consistent research-backed scripts with approvals and traceability.”

---

## 5) MVP scope
### In scope (ship)
- Auth + per-user workspace
- Profile (voice, audience, guardrails)
- **Resources Library** (upload links/files/notes; tags; search; “gold” resources)
- Trend research + gap analysis + topic scoring
- Topic selection (human picks)
- Hook lab (multiple hooks + selection)
- Script generation:
  - YouTube long (8–12 min target, configurable)
  - 3 Shorts (30–60 sec target, configurable)
  - Titles (10), description, tags, pinned comment, thumbnail brief
- Editor pass (voice, clarity, structure)
- Testing pass (structure + duplicates + claim-risk + platform constraints)
- Approval gate (approve/reject/regenerate)
- Export/copy
- Persistence: workflow plan + snapshots + outputs + versions
- Observability + cost governance basics

### Out of scope (defer)
- Multi-seat roles/permissions (beyond single-user)
- Full scheduling calendar
- Instagram posting
- Advanced performance ingestion (later v1.1/v2)
- Fine-tuning a model (later)

---

## 6) Key user flows (end-to-end)
### Flow A — Create Content Pack (standard)
1) User sets **Profile** (voice/audience/rules)  
2) User adds **Resources** (scripts, docs, links, notes)  
3) User enters goal: “3 video ideas + pick best + write script about X”  
4) System runs workflow:
   - Signal Research → Gap + Topic Candidates → Topic Pick → Hook Lab → Script → Edit → Test → Approval  
5) User reviews and approves  
6) Export/copy (optional publish later)

### Flow B — Reject & regenerate
1) User rejects with feedback (“more contrarian, fewer buzzwords, include 2 case studies”)  
2) System regenerates from the chosen step (e.g., Hook Lab or Script)  
3) Re-test, then re-approve

### Flow C — “Use my resources”
1) User marks key resources as ⭐ Gold  
2) System must use Gold resources in research and scripts where relevant  
3) Testing verifies: “resource usage present” + citations/attribution as required

---

## 7) Functional requirements (FR) — MVP

### FR1 — Authentication & workspace
- Email/password or magic link (Supabase Auth)
- Workspace scoped to user_id
- Logout, session refresh
**Accept:** User can sign in and see only their data (RLS).

---

### FR2 — Profile (creator memory: preferences)
Profile fields (MVP):
- brand_voice: tone, cadence, taboo words, preferred analogies
- audience: who they speak to, knowledge level
- content goals: education/contrarian/how-to/news
- constraints: banned topics, sensitive claims policy
- style requirements:
  - must include: hook, story arc, examples/case studies, “new tech”, CTA
  - must include: 3 hook options per script
- defaults:
  - long duration target (minutes)
  - shorts count + duration
**Accept:** Stored and applied to every workflow. Version snapshot stored per workflow.

---

### FR3 — Resources Library (NEW — required)
**Purpose:** Make the agent “remember” and ground output in the user’s actual materials.

**User actions**
- Add resource:
  - URL (article/video/doc)
  - File upload (PDF/DOCX/TXT/MD)
  - Note (rich text)
  - “Paste transcript” (text)
- Tag resources (e.g., Hooks, Case Studies, My Opinions, Competitors)
- Search resources
- Mark ⭐ Gold (high-priority retrieval)
- Delete resource (hard-delete content_text + chunks)
- View “used in workflows” references

**System behaviors**
- Ingest text:
  - Extract text from file/link
  - Chunk into sections
  - (Optional) create embeddings for retrieval
- Provide retrieval API: fetch top-K relevant chunks based on goal/topic
- Add “Resource Usage Requirements”:
  - Research step must cite which resources were used
  - Script step must incorporate at least N concrete items (quotes/paraphrases) from resources when relevant
- Testing step validates:
  - resource usage present (when resources exist)
  - proper attribution notes (internal citations) included in metadata

**Accept**
- User can add resources and see them in dashboard
- Workflow outputs list “resources_used[]”
- Deletion removes all derived chunks

---

### FR4 — Topic Opportunity Engine (signals + gaps)
**Inputs**
- Goal, profile, resources
- Optional: “sources allowed” toggles (Reddit, YouTube comments, news, competitor channels)
**Outputs**
- 10 topic candidates with:
  - topic title
  - audience pain / question
  - why now (timeliness)
  - novelty angle
  - 3 hook drafts
  - suggested structure
  - required proof (case studies/examples)
  - risk flags
  - opportunity score (0–100) with breakdown (novelty, demand, fit, saturation, proof)
  - sources list (links/notes)

**Accept**
- User receives topic list with score and reasoning
- Topics grounded in at least:
  - 3 external signals OR internal resources (configurable)
- “No hallucination” rule: if no sources, mark “speculative”.

---

### FR5 — Topic selection (human-in-the-loop)
- UI shows candidates
- User selects 1 topic
- User can tweak:
  - angle
  - audience
  - desired tone
  - length
- Selection creates a “Topic Brief” artifact

**Accept**
- Workflow pauses until selection is made
- On selection, workflow resumes at Hook Lab

---

### FR6 — Hook Lab (best hook selection)
Generate:
- 7 hook options (varied patterns: curiosity, contrarian, story, data, challenge, myth-bust, “I learned…”)
- Hook score per hook:
  - clarity
  - curiosity gap
  - specificity
  - credibility
- User picks final hook or requests regen

**Accept**
- Workflow pauses for hook selection
- Selected hook saved and used in scripts

---

### FR7 — Script generation (YouTube Content Pack)
**Outputs (MVP pack)**
1) **YouTube Long Script**
   - target 8–12 minutes (configurable)
   - structure:
     - hook (selected)
     - promise + stakes
     - story arc
     - 2–3 case studies/examples
     - “new tech / latest developments” segment (bounded: only claim what can be supported)
     - summary + CTA
   - timestamps sections
   - b-roll suggestions (optional)
2) **3 Shorts Scripts**
   - each with hook + punchline + CTA
3) **Titles (10)**
4) **Description**
5) **Tags**
6) **Pinned comment**
7) **Thumbnail brief**
   - 3 concepts (visual + text + emotion)

**Accept**
- All required sections present
- Scripts match profile voice constraints
- Pack stored with workflow_id and version

---

### FR8 — Editor node (voice + clarity)
- Remove fluff, enforce cadence, simplify language, reduce hype
- Ensure consistent POV (I/you/we)
- Ensure story arc is coherent

**Accept**
- Edited outputs retain structure and improve readability
- Changes are recorded (diff summary text in metadata)

---

### FR9 — Testing node (quality gate)
Tests:
- JSON schema validity
- Required sections exist
- Repetition/duplication across shorts
- Risk flags for claims (“needs citation”, “uncertain”, “medical/legal/financial”)
- “Resource usage” presence (if resources exist)
- Length sanity checks

**Accept**
- Produces a report per asset with PASS/FAIL + reasons
- FAIL prevents approval until fixed or user overrides (override is logged)

---

### FR10 — Approval + regeneration
- Workflow stops at pending approval
- User actions:
  - Approve pack
  - Approve individual asset
  - Reject with feedback (free text + tags)
  - Regenerate from step:
    - topics
    - hooks
    - script
    - editor
- On regenerate: keep prior versions, mark new version active

**Accept**
- No publish without approval
- Version history visible in UI

---

### FR11 — Export/copy (mandatory)
- Copy to clipboard
- Download as .md + .txt
- “Pack export”: one zip with all assets
**Accept**
- Export works even without integrations

---

### FR12 — Publishing (optional, off by default)
- MVP default: export only
- If enabled later:
  - official APIs only
  - requires OAuth + scopes
  - idempotent publish
**Accept**
- Publishing can’t run without explicit user opt-in

---

## 8) System architecture (high-level)
### Components
- **Web (Next.js):** dashboard, profile, resources, workflows, approvals
- **API (FastAPI):** create workflow, upload resources, get status, approve/reject
- **Worker:** executes workflows asynchronously
- **Planner:** Agent Zero generates workflow_plan.json
- **Executor:** LangGraph executes deterministic pipeline with checkpoints
- **DB:** Supabase Postgres + RLS
- **Storage:** Supabase storage for uploads
- **Observability:** traces + errors + logs

### Critical architecture decisions (non-negotiable)
- Execute workflows **asynchronously** (no long blocking HTTP).
- Use **workflow_id as thread_id** for LangGraph resume/pause.
- Use **strict schemas** and validate/repair once.
- Treat Agent Zero as **untrusted tool-runner**: sandboxed container, resource limits, no host access.

---

## 9) Workflow model (planner + executor)
### Planner (Agent Zero)
- Input: goal + profile + resource summary
- Output: `workflow_plan.json` (max 7 steps for YouTube pack):
  1) signal_research
  2) gap_analysis_topic_candidates
  3) topic_selection (interrupt)
  4) hook_lab (interrupt)
  5) script_generation
  6) editor
  7) testing
  8) approval (interrupt)

### Executor (LangGraph)
- Loads plan
- Runs nodes sequentially with conditional routing
- Persists checkpoint after each node
- Interrupts for:
  - topic selection
  - hook selection
  - final approval

---

## 10) Data model (Supabase) — MVP
> Use separate `workflow_snapshots` table (preferred) instead of a JSONB array.

### Tables
**users**
- id (uuid, pk)
- created_at

**profiles**
- user_id (uuid, pk/fk users)
- profile_json (jsonb)
- updated_at

**resources**
- id (uuid, pk)
- user_id (uuid, fk)
- type (link|file|note|transcript)
- title
- source_url (nullable)
- tags (text[])
- is_gold (bool)
- content_text (text)
- created_at

**resource_chunks** (optional in MVP; recommended)
- id (uuid, pk)
- resource_id (uuid, fk)
- chunk_index (int)
- chunk_text (text)
- embedding (vector) (optional)
- metadata (jsonb)

**workflows**
- id (uuid, pk)
- user_id (uuid, fk)
- status (queued|running|awaiting_topic|awaiting_hook|awaiting_approval|approved|failed)
- goal_text (text)
- profile_snapshot (jsonb)
- workflow_plan (jsonb)
- active_version (int)
- created_at

**workflow_snapshots**
- id (uuid, pk)
- workflow_id (uuid, fk)
- step_id (text)
- state_json (jsonb)
- created_at

**content_assets**
- id (uuid, pk)
- workflow_id (uuid, fk)
- version (int)
- type (youtube_long|youtube_short|title_set|description|tags|pinned_comment|thumbnail_brief|topic_candidates|hook_candidates|test_report)
- platform (youtube)
- content_json (jsonb)
- status (draft|approved|rejected)
- created_at

**workflow_resources_used**
- workflow_id (uuid, fk)
- resource_id (uuid, fk)
- usage_type (research|script|both)

**audit_events**
- id (uuid, pk)
- user_id
- workflow_id
- event_type (created|topic_selected|hook_selected|approved|rejected|regenerated|published)
- payload (jsonb)
- created_at

**usage_costs** (MVP simple)
- id (uuid, pk)
- workflow_id
- step_id
- model_name
- input_tokens
- output_tokens
- estimated_cost
- created_at

### RLS (required)
- Every table scoped by user_id.
- Policies: user can only select/insert/update rows with their user_id.
- Storage bucket policies for resources.

---

## 11) API surface (MVP)
### Public endpoints
- `POST /workflows`  
  Create workflow (goal + optional settings); status=queued.
- `GET /workflows`  
  List workflows.
- `GET /workflows/{id}`  
  Workflow detail: status + assets + test report + versions.
- `POST /workflows/{id}/topic`  
  Submit chosen topic candidate → resume execution.
- `POST /workflows/{id}/hook`  
  Submit chosen hook → resume execution.
- `POST /workflows/{id}/approve`  
  Approve assets or pack.
- `POST /workflows/{id}/reject`  
  Reject with feedback + optionally “regen_from_step”.
- `POST /workflows/{id}/regenerate`  
  regen_from_step + feedback.
- `POST /resources`  
  Add resource (url/file/note/transcript).
- `GET /resources`  
  List resources with tags + is_gold.
- `DELETE /resources/{id}`  
  Delete resource.

### Internal (worker)
- `run_workflow(workflow_id)`
- `call_agent_zero(goal, profile_snapshot, resource_summary) -> plan`
- `execute_langgraph(workflow_id, initial_state) -> outputs`

---

## 12) Non-functional requirements (NFR)
### Reliability
- Async job execution
- Idempotency keys:
  - workflow_id is idempotency for runs
  - asset_id for exports/publish
- Retry policy per node (max 2 retries; then fail with snapshot)
- Resume support via checkpoint

### Security & privacy
- Agent Zero sandboxed container
- Secrets in server env only
- RLS enforced everywhere
- Data deletion: delete resources + derived chunks; delete account
- Logging redaction (no tokens, no secrets)

### Quality
- Strict schemas + validation
- Testing node gate
- Minimum content requirements enforced

### Observability
- correlation id = workflow_id in all logs/traces
- store errors with step_id + stack + state snapshot
- optional trace tool integration (later)

### Cost governance
- model config per step (default cheaper for editor/testing)
- token ceilings per step
- per-user daily workflow cap (config)
- caching: reuse signal research for same topic/time window

---

## 13) “Brain” design (how it remembers and improves)
### Per-user memory layers
1) **Profile** (stable preferences)
2) **Resources** (ground truth + opinions + examples)
3) **Golden Library** (approved hooks/scripts/assets; mark as best-in-class)
4) **Feedback memory** (reject reasons + edits)
5) (Later) **Performance memory** (views/CTR/retention)

### Improvement mechanism (MVP)
- When user approves: save asset patterns into Golden Library tags (e.g., “Hook type: contrarian, pacing: fast”)
- When user rejects: store reasons and enforce in next generation
- Retrieval prioritizes:
  - Gold resources + Golden Library + recent approvals

---

## 14) YouTube-specific best practices (encoded as rules)
- Hooks:
  - first 5–10 seconds: specific promise + tension
  - avoid vague “today we’ll talk about…”
- Structure:
  - open loop(s), payoff later
  - concrete examples every 60–90 seconds
- Value:
  - at least 2 case studies or real-world examples per long script
  - clear “so what” takeaways
- Shorts:
  - one idea, one punchline, one CTA

(These become prompt constraints + testing rules.)

---

## 15) MVP acceptance criteria checklist (must pass)
- [ ] User can sign in and create a profile
- [ ] User can add resources (link/file/note) and tag them
- [ ] User can generate a workflow and see status changes
- [ ] System generates topic candidates with scores + sources
- [ ] Workflow pauses for topic selection; resumes correctly
- [ ] Hook lab generates options; user selects; resumes correctly
- [ ] System generates long + 3 shorts + titles + thumbnail brief
- [ ] Editor and Testing run; test report visible
- [ ] User can reject with feedback and regenerate from step
- [ ] Versioning works (old versions preserved)
- [ ] Export/copy works for all assets
- [ ] Supabase RLS verified: no cross-user access
- [ ] Workflow snapshots saved for every step
- [ ] Basic cost tracking saved per step

---

## 16) Build plan (8 weeks) — engineered, not “vibe coding”
> This is the same build timeline, now aligned to RC + agentic engineering.

### Week 1 — RC Illuminate + Define
- Finalize MVP scope and non-goals
- Define schemas (workflow_plan + node outputs + content pack)
- Define “Resources” ingestion MVP

### Week 2 — RC Architect
- Repo scaffold (monorepo)
- Supabase schema + RLS
- Async worker design + workflow lifecycle

### Week 3 — RC Sequence + Validate
- Vertical slices plan
- Validation checklists (security, UX baseline, cost caps)

### Week 4 — Forge Slice 1–3
- Auth + Profile + Resources CRUD
- Workflow creation + queue + status polling
- Storage + ingestion path (text extraction)

### Week 5 — Forge Slice 4–6
- Agent Zero planning adapter
- LangGraph pipeline with checkpointing + interrupts
- Topic candidates + topic select

### Week 6 — Forge Slice 7–9
- Hook lab + hook select
- Script generation pack
- Editor + testing + approval gate

### Week 7 — Dashboard polish + Export
- Workflow list/detail UX
- Export pack
- Regenerate from step UX

### Week 8 — Hardening + launch
- E2E tests
- Observability wiring
- Cost caps + quotas
- Deployment runbooks

---

## 17) Engineering methodology (how you build this in a visual code editor)

### Agentic engineering rules (mandatory)
- Treat the AI as a fast junior dev.
- You (human) own: architecture, gates, decisions, acceptance criteria.
- Never merge code you can’t explain at a high level.

### RC Method (phase gates)
1) Illuminate → 2) Define → 3) Architect → 4) Sequence → 5) Validate → 6) Forge → 7) Connect → 8) Compound  
At each gate:
- output artifacts to `docs/compound/`
- stop for approval

### Compound Engineering loop (every slice)
Plan → Work → Review → Compound  
“Compound” means writing reusable patterns:
- `docs/compound/patterns/rls.md`
- `docs/compound/patterns/async-worker.md`
- `docs/compound/patterns/langgraph-interrupts.md`
- `docs/compound/patterns/resource-ingestion.md`

### Ralph loop (inside Work only)
Run → read errors → patch → rerun, max 5 loops per task.

### Non-technical “merge checklist” (you enforce)
Every task must include:
- What changed (files)
- What behavior changed (plain English)
- Tests run + results
- Risk level + mitigations
- How to verify manually (3 steps)

---

## 18) Appendix — Repo structure (recommended)
```
content-orchestrator/
  apps/
    web/            # Next.js dashboard
    api/            # FastAPI + worker
  packages/
    shared/         # schemas, types
  infra/
    supabase/
      migrations/
  docs/
    compound/
      patterns/
      decisions/
      runbooks/
      schemas/
      gotchas.md
  .env.example
```

---

## 19) Appendix — Output contracts (high-level)
### Topic candidates artifact
- id, title, angle, audience_pain, why_now, novelty, hooks[], score_breakdown, sources[], risks[]

### Hook candidates artifact
- hook_text, hook_type, score_breakdown, recommended_for

### YouTube long script artifact
- title, selected_hook, sections[{timestamp, heading, script}], examples[], case_studies[], new_tech[], CTA, broll_suggestions[]

### Shorts artifact
- hook, script, punchline, CTA, on_screen_text

### Test report artifact
- asset_id, pass_fail, issues[], required_sections_missing[], risk_flags[], repetition_score

---

## 20) Appendix — “Resources” UX (minimum UI)
- `/resources` page:
  - Add (URL/file/note/transcript)
  - Tagging
  - Search
  - Toggle ⭐ Gold
  - Delete
- Workflow detail shows:
  - resources used
  - citations/attribution notes

---

**End of PRD**
