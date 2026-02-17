# Pattern: Brand Data Pipeline Integration

**Extracted from:** Slice 7 (Brand Foundation)
**Date:** 2026-02-14

## Problem

Content generation prompts produce generic output when they don't know who the user's audience is, what they sell, or how they're positioned. Brand data (ICA, offer, positioning) needs to flow into every pipeline node without breaking backward compatibility.

## Pattern: Graceful Brand Context Injection

### 1. Format helpers extract structured brand data

Create helper functions in the node files that extract brand data from the profile and format it as human-readable strings:

```python
def _format_ica(profile: Dict[str, Any]) -> str:
    ica = profile.get("ica", {})
    if not ica:
        return "No ICA defined yet."
    parts = []
    # Extract demographics, pains, desires, buying_motivations...
    return "\n".join(parts) if parts else "No ICA defined yet."
```

### 2. Prompts have dedicated sections with format placeholders

```python
USER = """\
## Creator Profile
{profile}

## Ideal Client Avatar
{ica_context}

## Offer & Positioning
{offer_context}

## Instructions
...
"""
```

### 3. Nodes call helpers and pass to `.format()`

```python
resp = prompts.USER.format(
    profile=json.dumps(profile),
    ica_context=_format_ica(profile),
    offer_context=_format_offer(profile),
    # ... other fields
)
```

### 4. Fallback strings prevent breakage

When brand data doesn't exist (new user, empty profile), helpers return "No ICA defined yet." / "No offer defined yet." The pipeline works identically to before brand data existed.

## Key Decisions

- **Brand data lives in `profiles.profile_json` JSONB** -- no new tables needed for brand data itself
- **`brand_chats` table** stores conversational discovery sessions separately
- **Writing rules go in SYSTEM prompts** (not USER) so they persist as instructions
- **AI_TELLS_CHECKLIST** added to editor node specifically (it's a review step)
- **Helper functions are reusable** -- `_format_ica()` and `_format_offer()` imported by gap_analysis from signal_research

## Testing Pattern

Test that brand data appears in prompts by:
1. Creating state with a rich `profile_snapshot` containing ICA/offer/brand
2. Running the node with a mock LLM
3. Inspecting `mock_llm.calls[0][1]["content"]` for expected strings
4. Also test empty profile uses fallback strings

## Gotchas

- Python `.format()` with JSON in prompts: use `{{` and `}}` for literal braces in JSON examples within prompt templates
- Don't add brand data to PipelineState -- it's already in `profile_snapshot`
- Platform-specific formatting helpers may be needed for non-YouTube content types (future)
