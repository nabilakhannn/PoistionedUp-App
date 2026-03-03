# Future Plan: Character Animation — Agent Office View

**Status:** Parked — not yet built
**Reference:** Pixel Agents VS Code extension (screenshot saved below)
**Target page:** `/mission-control/orchestrator` (My Team tab)

---

## The Idea

Replace the current flat agent list on the My Team page with a live top-down pixel-art office where each agent is an animated character at a desk. When working → typing animation + glow. When idle → static. Speech bubbles show what they're doing in real time.

Inspired by: [Pixel Agents extension](https://marketplace.visualstudio.com/items?itemName=PabloDeuca.pixel-agents)

---

## What the Office Looks Like

```
┌─────────────────────────────────────────────────────┐
│  🪴          📚📚📚          🖥️                    │
│                                                     │
│  [🧠 Jumbo]     [🔍 Trend]     [✍️ Writer]          │
│  ╔══════════╗   ╔══════════╗   ╔══════════╗         │
│  ║   IDLE   ║   ║ WORKING  ║   ║   IDLE   ║         │
│  ╚══════════╝   ╚══════════╝   ╚══════════╝         │
│                💬 "researching hooks..."             │
│                                                     │
│  [✅ QA]    [🕵️ Comp]    [📤 Dist]    [📊 Ana]     │
│  ╔══════╗   ╔══════╗    ╔══════╗    ╔══════╗        │
│  ║ IDLE ║   ║ IDLE ║    ║ IDLE ║    ║ IDLE ║        │
│  ╚══════╝   ╚══════╝    ╚══════╝    ╚══════╝        │
└─────────────────────────────────────────────────────┘
```

---

## 4 Components Needed

### 1. Office Background
- Top-down office grid — desks, plants, bookshelves
- Option A: CSS grid + emoji furniture (zero dependencies, ships fast)
- Option B: Static pixel art tilemap image (more polished)

### 2. Agent Sprites (biggest decision)

| Option | Quality | Cost | Time |
|--------|---------|------|------|
| Free sprites from itch.io / OpenGameArt | Good | $0 | 2h finding + adapting |
| AI-generated pixel art (Midjourney/DALL-E) | Medium | ~$5 | 1h |
| Commission a pixel artist | Best | $50–150 | 1–2 weeks |
| CSS-only characters (no real sprites) | Minimal | $0 | 2h |

**8 agents to represent:**
- 🧠 Jumbo (Orchestrator)
- 🔍 Trend Analyzer
- ✍️ Copywriter
- ✅ QA Reviewer
- 🕵️ Competitor Analyst
- 📤 Distributor
- 🎨 Visual Designer
- 📊 Analytics

### 3. Animations (CSS @keyframes — no game engine needed)
- `idle` — subtle breathing or blinking loop
- `working` — up-down typing motion + green desk glow
- `speech-bubble` — shows `agent.status_reason` text for 5s when it changes, then fades out
- `completed` — quick flash/celebrate animation when deliverable is created

### 4. Status Wiring
**Already built.** `/orchestrator/status` API returns agent status every 30s.
Just map:
- `status === "working"` → play working animation
- `status === "idle"` → play idle animation
- `status_reason` changed → show speech bubble

---

## Two Build Paths

### Path A — CSS Office (1 slice, ~1 day)
- No external sprites
- Emoji agents with stylised desks
- Pure CSS animations
- Builds fast, on-brand dark theme
- Looks clean, not as fun as real pixel art

### Path B — Real Pixel Art (2 slices)
- **Slice 1:** Source sprites (AI-generate or free itch.io pack), wire into app as PNG spritesheets with CSS animation
- **Slice 2:** Add office tilemap background, speech bubbles, completed flash
- Looks exactly like the Pixel Agents screenshot

---

## Files to Create (when ready to build)

| File | Purpose |
|------|---------|
| `apps/web/src/app/mission-control/orchestrator/components/agent-office.tsx` | Main office component |
| `apps/web/src/app/mission-control/orchestrator/components/agent-desk.tsx` | Single desk + character unit |
| `apps/web/src/app/mission-control/orchestrator/components/speech-bubble.tsx` | Timed speech bubble |
| `public/sprites/` | PNG spritesheets (if Path B) |
| `apps/web/src/app/mission-control/orchestrator/office.css` | Keyframe animations |

The office component replaces (or sits above) the existing agent cards on the orchestrator page.

---

## Why This Was Parked

- Functional monitoring already exists (agent status cards, activity feed)
- Sprite sourcing takes non-code time (design/asset decision)
- Nice-to-have vs need-to-have at current stage
- Revisit when the core content workflow is fully proven

---

## Reference Screenshot

Saved: `docs/future-plans/character-animation/pixel-agents-reference.png`
(Copy of the Pixel Agents VS Code extension screenshot)
