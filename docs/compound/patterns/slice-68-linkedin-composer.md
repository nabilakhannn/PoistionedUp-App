# Slice 68: LinkedIn Composer with Live Preview

**Date:** 2026-02-25
**Status:** Complete
**Methodology:** Compound Engineering + Ralph Loop

## Requirements

Build a dedicated LinkedIn/X post composer inspired by Raycaster (reference screenshots).
Key features: rich text editor, live mobile/desktop preview, AI generation, save/queue/schedule actions.

## Changes

| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/app/composer/page.tsx` | Created | Full composer page: editor + live preview + actions |
| `apps/web/src/lib/api/composer.ts` | Created | API client: saveDraft, updateDraft, schedule, addToQueue, generateContent, loadDrafts |
| `apps/web/src/lib/api/index.ts` | Updated | Re-export composer module |
| `apps/web/src/app/nav-bar.tsx` | Updated | Added Composer nav link + icon |

## Features

### Editor Panel (Left)
- **Platform toggle:** LinkedIn / X (Twitter) with platform-specific config
- **Formatting toolbar:** Bold, Italic, Bullet list, Numbered list, Emoji
- **Rich textarea:** Auto-resizing, placeholder text with tips
- **Character count:** Real-time char/word/read-time stats with limit warning
- **Copy to clipboard** and **Clear** actions

### Preview Panel (Right)
- **LinkedIn post preview** with author avatar, name, headline, timestamp
- **Mobile / Desktop** toggle (375px vs 555px width)
- **"See more" truncation** — matches LinkedIn's real behavior
- **Engagement bar** — Like, Comment, Repost, Send buttons
- **Writing tips** panel — platform-specific best practices

### Actions
- **Save Draft** — saves to schedule board (status: draft)
- **Add to Queue** — adds to publishing queue
- **Schedule For...** — modal with date/time picker
- **AI Generate** — modal with prompt input, calls content-chat API with brand voice

### API Client Pattern
- Composes existing schedule + content-chat endpoints (no new backend endpoints)
- LinkedIn Unicode bold conversion (for **bold** text)
- Character counting and reading time estimation

## Architecture Decisions

1. **No new backend endpoints** — the composer wraps existing schedule and content-chat APIs. This keeps the backend lean and avoids duplication.
2. **No TipTap dependency** — LinkedIn doesn't support rich formatting, so a plain textarea with formatting helpers is more appropriate. Avoids 200KB bundle for a library we'd only use for bold/italic.
3. **Platform-aware config** — character limits, colors, tips all driven by PLATFORM_CONFIG constant.

## Verification

- 826/826 Python tests passing (no backend changes)
- 0 TypeScript errors
- Composer page renders with live preview

## Next Steps

- [ ] Image upload to Supabase storage + attach to posts
- [ ] LinkedIn API OAuth + direct publishing
- [ ] Draft auto-save (debounced)
- [ ] Load existing drafts from schedule board
- [ ] AI image generation (via Visual Designer agent)
