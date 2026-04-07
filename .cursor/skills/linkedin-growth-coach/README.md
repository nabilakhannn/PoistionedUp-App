# LinkedIn growth coach (agent skill)

A **Cursor / Claude Code** skill that steers the model like a direct, systems-first LinkedIn operator: content packaging, ICP tiers, DMs, engagement blocks, lead magnets, profile alignment, and countable homework. It also embeds **human-sounding** writing rules (AI-tell aware) and, for LinkedIn posts, a **five-comment author thread** you can paste under your own post.

## Contents

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill: stance, session flow, questions, playbooks, human-writing contract, LinkedIn post + five comments bundle |
| `references/frameworks.md` | Time split, trackers, habits, hooks, platform notes, nurture |
| `references/coach-voice.md` | How the cohort-style coach talks, thinks, and stacks questions |
| `references/human-writing-ai-tells.md` | Full AI-tell library, detector teaching rules, generation process, prompt template |
| `references/human-writing-ai-tells.json` | Machine-readable hard bans + pointers (full prose in `.md`) |
| `references/custom-ai-instructions.md` | LinkedIn formatting defaults, voice, gimmick intro ban, hashtag rule |
| `references/brand-blueprint.md` | Fill-in template for offer, ICP, proof, forbidden phrases |
| `references/source/README.md` | Index of bundled transcripts |
| `references/source/transcripts/*.vtt` | Normalized copies of shared meeting transcripts (VTT) |

## Use in Cursor

1. Repo path: `.cursor/skills/linkedin-growth-coach/`
2. Ask the agent to follow this skill when you want LinkedIn coaching, post teardowns, human-sounding posts, or weekly execution plans.

Cursor discovers skills under `.cursor/skills/` per project.

## Mirror for Claude (optional)

Copy the whole folder so references and transcripts stay intact:

```bash
rsync -a --delete "/path/to/repo/.cursor/skills/linkedin-growth-coach/" ~/.claude/skills/linkedin-growth-coach/
```

Or without rsync:

```bash
mkdir -p ~/.claude/skills/linkedin-growth-coach/references/source/transcripts
cp SKILL.md ~/.claude/skills/linkedin-growth-coach/
cp -R references/* ~/.claude/skills/linkedin-growth-coach/references/
```

## Triggers (from skill description)

Pipeline over vanity metrics, hooks and carousels, outreach scripts, broad or narrow or niche planning, 30-day trackers, wrong-audience viral fixes, employer vs personal brand balance, stigma niches, viral follow-ups, AI-assisted drafting workflows, low engagement diagnostics, **human LinkedIn copy with five self-comments**.

## License / attribution

Methodology is distilled from third-party coaching material for **generic** coaching behavior. It is not an impersonation of any individual. Bundled `.vtt` files are copies of recordings you placed in the repo for your own access.

## Links (this repo on GitHub)

After push, open the skill from the default branch (`main` if that is your default):

- **README (this file):** [`.cursor/skills/linkedin-growth-coach/README.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/README.md)
- **Main skill:** [`.cursor/skills/linkedin-growth-coach/SKILL.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/SKILL.md)
- **Frameworks:** [`.cursor/skills/linkedin-growth-coach/references/frameworks.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/frameworks.md)
- **Coach voice:** [`.cursor/skills/linkedin-growth-coach/references/coach-voice.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/coach-voice.md)
- **Human writing (full):** [`.cursor/skills/linkedin-growth-coach/references/human-writing-ai-tells.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/human-writing-ai-tells.md)
- **Human writing (JSON):** [`.cursor/skills/linkedin-growth-coach/references/human-writing-ai-tells.json`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/human-writing-ai-tells.json)
- **Custom AI instructions:** [`.cursor/skills/linkedin-growth-coach/references/custom-ai-instructions.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/custom-ai-instructions.md)
- **Brand blueprint template:** [`.cursor/skills/linkedin-growth-coach/references/brand-blueprint.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/brand-blueprint.md)
- **Source index:** [`.cursor/skills/linkedin-growth-coach/references/source/README.md`](https://github.com/nabilakhannn/PoistionedUp-App/blob/main/.cursor/skills/linkedin-growth-coach/references/source/README.md)
- **Folder tree:** [`.cursor/skills/linkedin-growth-coach`](https://github.com/nabilakhannn/PoistionedUp-App/tree/main/.cursor/skills/linkedin-growth-coach)

If your default branch is not `main`, replace `main` in the URLs.
