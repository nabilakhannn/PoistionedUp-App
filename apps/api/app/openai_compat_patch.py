"""Defensive patch for openai SDK + pydantic v2 compatibility.

Older pydantic v2 releases (< 2.12) reject ``by_alias=None`` in
``model_dump()``, but the openai SDK passes ``None`` from its compat
layer.  Upgrading to pydantic >= 2.12.5 fixes this natively.

This module exists as a **safety net**: it detects the bug at import
time and only patches if the problem still exists.  If pydantic is
new enough, the patch is a no-op.

Import this module early in your entry-point (``app/main.py`` or
``worker/main.py``) before any OpenAI calls.
"""

import logging
import sys

logger = logging.getLogger(__name__)


def _needs_patch() -> bool:
    """Return True if the current pydantic version rejects by_alias=None."""
    import pydantic

    class _Probe(pydantic.BaseModel):
        x: int = 1

    try:
        _Probe().model_dump(by_alias=None)
        return False  # pydantic handles None fine
    except TypeError:
        return True  # needs patching


try:
    if _needs_patch():
        import openai._compat as _compat

        _original_model_dump = _compat.model_dump

        def _patched_model_dump(model, **kwargs):  # type: ignore[no-untyped-def]
            if kwargs.get("by_alias") is None:
                kwargs["by_alias"] = False
            return _original_model_dump(model, **kwargs)

        # Patch the source module (covers lazy / function-body imports)
        _compat.model_dump = _patched_model_dump

        # Patch already-imported top-level references
        for mod_name in [
            "openai._base_client",
            "openai._utils._json",
            "openai.lib.streaming.chat._completions",
            "openai.lib.streaming._assistants",
        ]:
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "model_dump"):
                mod.model_dump = _patched_model_dump  # type: ignore[attr-defined]

        logger.info(
            "Applied openai/pydantic compat patch (pydantic %s needs by_alias fix)",
            __import__("pydantic").__version__,
        )
    else:
        logger.debug("openai/pydantic compat patch not needed (pydantic handles by_alias=None)")

except Exception:
    logger.warning(
        "Failed to check/apply openai compat patch. "
        "If you see 'by_alias NoneType' errors, upgrade pydantic to >= 2.12.5.",
        exc_info=True,
    )
