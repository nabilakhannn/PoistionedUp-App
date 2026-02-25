"""Smart Sequencing Engine for brand building.

Determines the next best field to ask about using a priority scoring
function that considers: base weight, dependency satisfaction,
completeness lift, and conversational context.

Reference: PositionedUp System Prompt v2 - Smart Sequencing Logic
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.brand_fields import (
    ALL_FIELDS,
    BrandField,
    FIELDS_BY_KEY,
    FIELDS_BY_MODULE,
    MODULE_LABELS,
    MODULES,
    TOTAL_FIELDS,
    TOTAL_REQUIRED_FIELDS,
    get_module_fields,
)

logger = logging.getLogger("app.services.brand_sequencing")


# ── Completeness Calculations ─────────────────────────────────


def get_filled_fields(profile_json: Dict[str, Any]) -> Set[str]:
    """Extract the set of filled field keys from a profile_json.

    A field is considered filled if its value is truthy (non-empty
    string, non-empty list, non-zero number, etc.).
    """
    filled = set()
    if not profile_json:
        return filled

    for full_key, field_def in FIELDS_BY_KEY.items():
        module = field_def.module
        key = field_def.key
        module_data = profile_json.get(module, {})
        if not isinstance(module_data, dict):
            continue
        value = module_data.get(key)
        if _is_value_filled(value):
            filled.add(full_key)

    return filled


def _is_value_filled(value: Any) -> bool:
    """Check if a field value is meaningfully filled."""
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        # Consider filled if any nested value is truthy
        return any(_is_value_filled(v) for v in value.values())
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, bool):
        return True
    return bool(value)


def calculate_field_completeness(
    profile_json: Dict[str, Any],
) -> Dict[str, Any]:
    """Calculate detailed completeness by module and overall.

    Returns a dict with:
    - per-module completeness (filled/total fields, percentage)
    - overall percentage
    - list of filled field keys
    - list of unfilled field keys
    """
    filled = get_filled_fields(profile_json)

    result = {
        "overall_percent": 0,
        "overall_filled": len(filled),
        "overall_total": TOTAL_FIELDS,
        "overall_required_filled": 0,
        "overall_required_total": TOTAL_REQUIRED_FIELDS,
        "modules": {},
        "filled_fields": sorted(filled),
        "unfilled_fields": [],
    }

    unfilled = []
    required_filled_count = 0

    for module in MODULES:
        module_fields = get_module_fields(module)
        module_filled = [
            f"{f.module}.{f.key}" for f in module_fields
            if f"{f.module}.{f.key}" in filled
        ]
        module_total = len(module_fields)
        module_required = [f for f in module_fields if f.is_required]
        module_required_filled = sum(
            1 for f in module_required
            if f"{f.module}.{f.key}" in filled
        )

        pct = int((len(module_filled) / module_total * 100)) if module_total else 0

        result["modules"][module] = {
            "label": MODULE_LABELS.get(module, module),
            "filled": len(module_filled),
            "total": module_total,
            "percent": pct,
            "required_filled": module_required_filled,
            "required_total": len(module_required),
            "filled_fields": module_filled,
        }

        for f in module_fields:
            full_key = f"{f.module}.{f.key}"
            if full_key not in filled:
                unfilled.append(full_key)

        required_filled_count += module_required_filled

    result["unfilled_fields"] = unfilled
    result["overall_required_filled"] = required_filled_count

    if TOTAL_FIELDS > 0:
        result["overall_percent"] = int(len(filled) / TOTAL_FIELDS * 100)

    return result


# ── Priority Scoring ──────────────────────────────────────────


def _dependencies_met(field: BrandField, filled: Set[str]) -> bool:
    """Check if all dependencies for a field are satisfied."""
    for dep in field.dependencies:
        if dep not in filled:
            return False
    return True


def _module_completeness_bonus(
    field: BrandField,
    filled: Set[str],
) -> float:
    """Bonus for fields in nearly-complete modules.

    Finishing a module feels good and builds momentum.
    """
    module_fields = get_module_fields(field.module)
    if not module_fields:
        return 0.0

    module_filled = sum(
        1 for f in module_fields
        if f"{f.module}.{f.key}" in filled
    )
    pct = module_filled / len(module_fields)

    # Big bonus if module is 80%+ complete (finish it!)
    if pct >= 0.8:
        return 5.0
    if pct >= 0.6:
        return 3.0
    if pct >= 0.4:
        return 1.5
    return 0.0


def score_field(
    field: BrandField,
    filled: Set[str],
    context_hint: Optional[str] = None,
) -> float:
    """Calculate the priority score for a field.

    Formula: base_weight + dependency_bonus + completeness_lift + context_bonus

    Returns 0.0 if the field is already filled or dependencies not met.
    """
    full_key = f"{field.module}.{field.key}"

    # Already filled
    if full_key in filled:
        return 0.0

    # Dependencies not met
    if not _dependencies_met(field, filled):
        return 0.0

    score = float(field.base_weight)

    # Dependency bonus: fields that unblock other fields
    unblocks = 0
    for other_field in ALL_FIELDS:
        if full_key in other_field.dependencies:
            other_full = f"{other_field.module}.{other_field.key}"
            if other_full not in filled:
                unblocks += 1
    score += min(unblocks * 0.5, 3.0)  # Cap dependency bonus at 3

    # Completeness lift: bonus for nearly complete modules
    score += _module_completeness_bonus(field, filled)

    # Context bonus: if the user just talked about something related
    if context_hint and field.key in context_hint.lower():
        score += 2.0

    return score


def get_next_field(
    profile_json: Dict[str, Any],
    skipped: Optional[Set[str]] = None,
    context_hint: Optional[str] = None,
) -> Optional[BrandField]:
    """Determine the single best next field to ask about.

    Args:
        profile_json: The current brand profile data
        skipped: Set of field keys to skip (user chose to skip)
        context_hint: Last user message for context scoring

    Returns:
        The highest-priority unfilled BrandField, or None if all done.
    """
    filled = get_filled_fields(profile_json)
    skip_set = skipped or set()

    candidates = []
    for field in ALL_FIELDS:
        full_key = f"{field.module}.{field.key}"
        if full_key in filled or full_key in skip_set:
            continue
        priority = score_field(field, filled, context_hint)
        if priority > 0:
            candidates.append((priority, full_key, field))

    if not candidates:
        # Check if there are skipped fields we can circle back to
        for field in ALL_FIELDS:
            full_key = f"{field.module}.{field.key}"
            if full_key in skip_set and full_key not in filled:
                priority = score_field(field, filled, context_hint)
                if priority > 0:
                    candidates.append((priority, full_key, field))

    if not candidates:
        return None

    # Sort by priority descending, then by base_weight descending for ties
    candidates.sort(key=lambda x: (x[0], x[2].base_weight), reverse=True)
    return candidates[0][2]


def get_next_n_fields(
    profile_json: Dict[str, Any],
    n: int = 3,
    skipped: Optional[Set[str]] = None,
    context_hint: Optional[str] = None,
) -> List[BrandField]:
    """Get the top N highest-priority unfilled fields.

    Useful for showing the user what is coming up next.
    """
    filled = get_filled_fields(profile_json)
    skip_set = skipped or set()

    candidates = []
    for field in ALL_FIELDS:
        full_key = f"{field.module}.{field.key}"
        if full_key in filled or full_key in skip_set:
            continue
        priority = score_field(field, filled, context_hint)
        if priority > 0:
            candidates.append((priority, full_key, field))

    candidates.sort(key=lambda x: (x[0], x[2].base_weight), reverse=True)
    return [c[2] for c in candidates[:n]]


# ── Transition Messages ───────────────────────────────────────


def get_transition_message(
    from_module: Optional[str],
    to_module: str,
) -> Optional[str]:
    """Get a natural transition message when switching modules.

    Returns None if no transition is needed (same module).
    """
    if from_module == to_module:
        return None

    transitions = {
        ("foundation", "authority"): (
            "Your foundation is locked in. Now I need to understand what "
            "makes you credible. Let us talk about your authority."
        ),
        ("foundation", "ica"): (
            "Your foundation is locked in. Now I need to understand who you "
            "are actually serving. Let us talk about your ideal client."
        ),
        ("authority", "ica"): (
            "I have a clear picture of your authority. Now let us figure out "
            "who you are actually helping."
        ),
        ("ica", "positioning"): (
            "I understand your audience deeply now. Time to turn all of this "
            "into a positioning statement that stops the right people "
            "mid-scroll."
        ),
        ("positioning", "voice"): (
            "Your positioning is sharp. Now let us define how you actually "
            "sound so every piece of content feels like YOU."
        ),
        ("voice", "offer"): (
            "We have your voice dialed in. Now let us structure your offer "
            "so it is impossible to say no to."
        ),
        ("offer", "content_pillars"): (
            "Your offer is locked. Now we need the content pillars that will "
            "attract the right people to that offer."
        ),
        ("content_pillars", "competitive"): (
            "Content pillars are set. Last piece: let us map your competitive "
            "landscape so you know exactly where you stand."
        ),
    }

    # Try exact match first
    key = (from_module, to_module) if from_module else (None, to_module)
    msg = transitions.get(key)
    if msg:
        return msg

    # Generic transition
    to_label = MODULE_LABELS.get(to_module, to_module)
    if from_module:
        from_label = MODULE_LABELS.get(from_module, from_module)
        return (
            f"Good progress on {from_label}. Let us move into "
            f"{to_label} now."
        )
    return None


# ── Resume Messages ───────────────────────────────────────────


def get_resume_message(completeness: Dict[str, Any]) -> str:
    """Generate a context-aware resume message based on completeness.

    Returns a greeting appropriate for the user's progress level.
    """
    pct = completeness.get("overall_percent", 0)
    filled = completeness.get("overall_filled", 0)

    # Find completed modules
    completed_modules = []
    for mod, data in completeness.get("modules", {}).items():
        if data.get("percent", 0) >= 80:
            completed_modules.append(data.get("label", mod))

    if pct == 0:
        return ""  # First visit, use welcome message instead

    if pct >= 100:
        return (
            "Your Brand DNA is complete. Every module is filled. Now the "
            "real work starts. Let us build your content strategy and start "
            "creating content that sounds like you and attracts the right "
            "people. What do you want to work on first?"
        )

    if pct >= 75:
        remaining = completeness.get("overall_total", 0) - filled
        return (
            f"You are {pct}% done. We are close. Just {remaining} fields "
            f"left to lock in your Brand DNA."
        )

    if pct >= 50:
        mod_str = " and ".join(completed_modules[:2]) if completed_modules else "the core modules"
        return (
            f"Good to see you. You are past the halfway mark at {pct}% "
            f"complete. {mod_str} looking solid. Let us keep building."
        )

    if pct >= 25:
        mod_str = " and ".join(completed_modules[:2]) if completed_modules else "the basics"
        return (
            f"You are back. Your brand DNA is {pct}% complete. {mod_str} "
            f"done. We are making real progress. Let us keep the momentum "
            f"going."
        )

    return (
        f"Welcome back. Your brand is {pct}% built. Let us keep the "
        f"momentum going."
    )
