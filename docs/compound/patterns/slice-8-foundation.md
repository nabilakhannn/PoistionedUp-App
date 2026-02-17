# Slice 8: Foundation Module + Learning Path UI

## Pattern: Adding a new brand module

### Steps taken:
1. **brand_chat.py** — Added `FOUNDATION_QUESTIONS` (10 questions) + `FOUNDATION_EXTRACTION_SYSTEM` prompt + updated `MODULE_QUESTIONS` and `MODULE_SYSTEMS` dicts + extended `calculate_completeness()` with foundation fields
2. **schemas/brand.py** — Added `FoundationData` model, updated `BrandProfile` to include `foundation`, added `foundation_percent` to `BrandCompleteness`, updated `BrandChatRequest` regex pattern
3. **brand.py router** — Added `PATCH /brand/foundation` endpoint, updated `GET /brand` response, extended module validation in `get_chat_history` and `complete_chat` from 3 modules to 4
4. **api.ts** — Added `foundation` to `BrandProfile` + `BrandCompleteness` interfaces, added `updateFoundation()` method
5. **chat/[module]/page.tsx** — Added "foundation" to `MODULE_LABELS` and `editPaths`
6. **brand/foundation/page.tsx** — New form page with 7 sections (beliefs, IT factor, achievements, personal backstory, macro story, micro stories, content pillars) using ListField for arrays and TextArea for text
7. **brand/page.tsx** — Redesigned as 10-stage learning path with vertical connector, stage circles (numbered/checkmark), progress bars, and "Coming soon" badges
8. **test_brand.py** — Added 11 new tests for Foundation (schema defaults, values, opening message, system prompt, questions count, completeness, progress)

### Key decisions:
- Foundation data stored in `profiles.profile_json.foundation` (JSONB extension, no migration needed)
- Beliefs are stored as string arrays (not objects) for simplicity
- IT Factor lives in Foundation now (not Brand), but Brand still keeps its own copy for backward compatibility
- Learning path shows all 10 stages but only 4 are active (foundation, ica, offer, brand)
- "Coming soon" stages are greyed out with no clickable links

### Reusable pattern:
To add another module (e.g. positioning, profile_audit):
1. Add questions + extraction system prompt in brand_chat.py
2. Add Pydantic model in schemas/brand.py
3. Add PATCH endpoint in brand.py, update module validation
4. Add to api.ts interfaces + methods
5. Add to chat MODULE_LABELS + editPaths
6. Create form page
7. Update dashboard stages array
8. Add tests
