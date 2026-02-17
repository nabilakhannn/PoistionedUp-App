"""Brand endpoints: ICA, Offer, Brand Statement, Chat, Suggest."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.brand import (
    BrandChatCompleteResponse,
    BrandChatHistory,
    BrandChatListResponse,
    BrandChatRequest,
    BrandChatResponse,
    BrandChatSummary,
    BrandChatTitleRequest,
    BrandCompleteness,
    BrandProfile,
    BrandSuggestRequest,
    BrandSuggestResponse,
)
import logging

logger = logging.getLogger(__name__)
from app.services.brand_chat import (
    build_chat_messages,
    calculate_completeness,
    deep_merge,
    estimate_progress,
    get_opening_message,
    get_relevant_context,
    parse_chat_response,
    SUGGEST_SYSTEM,
    _fetch_research_context,
)

router = APIRouter(prefix="/brand", tags=["brand"])


# ── Helpers ──────────────────────────────────────────────────


VALID_MODULES = ("foundation", "ica", "offer", "brand")


def _validate_module(module: str):
    """Raise 400 if module is invalid."""
    if module not in VALID_MODULES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module must be one of: {', '.join(VALID_MODULES)}",
        )


def _get_profile_json(admin, user_id: str) -> Dict[str, Any]:
    """Fetch profile_json for a user. Returns empty dict if no profile."""
    resp = (
        admin.table("profiles")
        .select("profile_json")
        .eq("user_id", user_id)
        .execute()
    )
    if resp.data:
        return resp.data[0].get("profile_json", {}) or {}
    return {}


def _update_profile_section(admin, user_id: str, section: str, data: Dict[str, Any]):
    """Update a specific section within profile_json."""
    current = _get_profile_json(admin, user_id)
    current[section] = data

    # Upsert profile (creates if not exists)
    admin.table("profiles").upsert({
        "user_id": user_id,
        "profile_json": current,
    }).execute()


def _get_llm_client():
    """Get the LLM client (lazy import to avoid circular deps)."""
    from worker.graph.llm import get_llm_client
    return get_llm_client()


# ── Brand CRUD ───────────────────────────────────────────────


@router.get("", response_model=BrandProfile)
async def get_brand(
    user: CurrentUser = Depends(get_current_user),
):
    """Get complete brand profile (Foundation + ICA + Offer + Brand Statement)."""
    admin = get_admin_client()
    profile = _get_profile_json(admin, user.id)
    return BrandProfile(
        foundation=profile.get("foundation", {}),
        ica=profile.get("ica", {}),
        offer=profile.get("offer", {}),
        brand=profile.get("brand", {}),
    )


@router.patch("/foundation")
async def update_foundation(
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Foundation fields (beliefs, IT factor, achievements, stories)."""
    admin = get_admin_client()
    current = _get_profile_json(admin, user.id)
    current_foundation = current.get("foundation", {})
    merged = deep_merge(current_foundation, body)
    _update_profile_section(admin, user.id, "foundation", merged)
    return {"message": "Foundation updated", "foundation": merged}


@router.patch("/ica")
async def update_ica(
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update ICA fields (manual form edit)."""
    admin = get_admin_client()
    current = _get_profile_json(admin, user.id)
    current_ica = current.get("ica", {})
    merged = deep_merge(current_ica, body)
    _update_profile_section(admin, user.id, "ica", merged)
    return {"message": "ICA updated", "ica": merged}


@router.patch("/offer")
async def update_offer(
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Offer fields (manual form edit)."""
    admin = get_admin_client()
    current = _get_profile_json(admin, user.id)
    current_offer = current.get("offer", {})
    merged = deep_merge(current_offer, body)
    _update_profile_section(admin, user.id, "offer", merged)
    return {"message": "Offer updated", "offer": merged}


@router.patch("/statement")
async def update_statement(
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Update Brand Statement + IT Factor."""
    admin = get_admin_client()
    current = _get_profile_json(admin, user.id)
    current_brand = current.get("brand", {})
    merged = deep_merge(current_brand, body)
    _update_profile_section(admin, user.id, "brand", merged)
    return {"message": "Brand statement updated", "brand": merged}


@router.get("/completeness", response_model=BrandCompleteness)
async def get_completeness(
    user: CurrentUser = Depends(get_current_user),
):
    """Get completion percentage for each brand module."""
    admin = get_admin_client()
    profile = _get_profile_json(admin, user.id)
    result = calculate_completeness(profile)
    return BrandCompleteness(**result)


# ── Brand Chat ───────────────────────────────────────────────


def _ocr_image_with_vision(image_bytes: bytes, filename: str) -> str:
    """Use GPT-4 Vision to extract text from an image or scanned document.

    Falls back to empty string if OpenAI key is missing or call fails.
    """
    import base64

    try:
        from openai import OpenAI
        from app.config import settings

        api_key = settings.openai_api_key
        if not api_key:
            logger.warning("OCR skipped: no OPENAI_API_KEY configured")
            return ""

        b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Guess MIME type from extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
        mime = f"image/{mime_map.get(ext, 'png')}"

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL text from this image. If it is a document, "
                                "resume, screenshot, or scan, reproduce the full text exactly. "
                                "If it is a photo or graphic with minimal text, describe what "
                                "you see and extract any visible text. Return ONLY the extracted "
                                "text, no commentary."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=4000,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning("Vision OCR failed for %s: %s", filename, e)
        return ""


def _ocr_pdf_fallback(file_bytes: bytes) -> str:
    """When text extraction returned empty, try PyMuPDF text then Vision OCR.

    Strategy (cheapest first):
      1. Try PyMuPDF's built-in text extraction (free, fast)
      2. If still empty, convert pages to images and send to GPT-4 Vision OCR
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # ── Tier 1: PyMuPDF text extraction (free) ──
        fitz_pages = []
        for page in doc:
            page_text = page.get_text()
            if page_text and page_text.strip():
                fitz_pages.append(page_text.strip())

        fitz_text = "\n\n".join(fitz_pages)
        if fitz_text.strip():
            logger.info(
                "PyMuPDF text extraction recovered %d chars from PDF",
                len(fitz_text),
            )
            doc.close()
            return fitz_text

        # ── Tier 2: Vision OCR (costs per page, last resort) ──
        logger.info("PyMuPDF text also empty, trying Vision OCR on %d pages", len(doc))
        pages_text = []
        for page_num in range(min(len(doc), 10)):  # Max 10 pages for cost control
            page = doc[page_num]
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            text = _ocr_image_with_vision(img_bytes, f"page_{page_num + 1}.png")
            if text:
                pages_text.append(text)
        doc.close()
        return "\n\n".join(pages_text)
    except ImportError:
        logger.info("PyMuPDF not installed, cannot do PDF OCR fallback")
        return ""
    except Exception as e:
        logger.warning("PDF OCR fallback failed: %s", e)
        return ""


@router.post("/chat/upload-context")
async def upload_chat_context(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Upload a file and extract its text for use as chat context.

    Supports:
      - Documents: PDF, DOCX, TXT, MD, CSV
      - Images: PNG, JPG, JPEG, GIF, WEBP (uses GPT-4 Vision OCR)
      - Scanned PDFs: falls back to OCR when text extraction returns empty

    Returns the extracted text so the frontend can attach it to the next chat message.
    """
    DOC_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB (images can be larger)

    # Validate extension
    filename = file.filename or "upload.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read bytes
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    text = ""
    source_type = "file"

    if ext in IMAGE_EXTENSIONS:
        # ── Image: use GPT-4 Vision OCR ──
        source_type = "image_ocr"
        text = _ocr_image_with_vision(file_bytes, filename)
        if not text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from this image. Make sure it contains readable text.",
            )
    else:
        # ── Document: use standard extraction ──
        from app.services.ingestion import extract_text

        try:
            text = extract_text(file_bytes, file.content_type or "", filename)
        except Exception as e:
            logger.error("File text extraction failed for %s: %s", filename, e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract text from this file: {str(e)[:200]}",
            )

        # ── PDF fallback: if extraction returned empty or very short text ──
        # (scanned docs return empty, garbled encodings return a few chars)
        if ext == ".pdf" and len(text.strip()) < 20:
            logger.info(
                "PDF text extraction got only %d chars for %s, trying fallback",
                len(text.strip()), filename,
            )
            fallback_text = _ocr_pdf_fallback(file_bytes)
            if len(fallback_text.strip()) > len(text.strip()):
                text = fallback_text
                source_type = "pdf_ocr"
            if not text.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Could not extract text from this PDF. It may be scanned, image-based, or have an unusual format. Try uploading as an image or pasting the text manually.",
                )

    # Truncate to 20k chars to avoid blowing up the context window
    max_chars = 20000
    truncated = len(text) > max_chars
    text = text[:max_chars]

    return {
        "filename": filename,
        "chars_extracted": len(text),
        "truncated": truncated,
        "text": text,
        "source_type": source_type,
    }


@router.post("/chat/extract-link")
async def extract_link_context(
    body: Dict[str, Any],
    user: CurrentUser = Depends(get_current_user),
):
    """Extract text from a URL (website, YouTube video, Reddit post, etc.) for chat context.

    Supports:
      - YouTube videos: captions first, then Whisper transcription fallback
      - TikTok/Facebook videos: Whisper transcription
      - Reddit posts: post body + top comments
      - Twitter/X: tweet text + metrics
      - Substack articles: full article text
      - LinkedIn posts/articles
      - Any other website: extracts readable article text

    Returns the extracted text so the frontend can attach it to the next chat message.
    """
    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required.",
        )

    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    from app.services.ingestion import detect_platform, extract_text_from_url

    try:
        platform = detect_platform(url)
        result = extract_text_from_url(url)
    except Exception as e:
        logger.error("URL extraction failed for %s: %s", url, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract content from this link: {str(e)[:200]}",
        )

    text = result.get("text", "")
    error = result.get("error", "")

    if not text.strip():
        detail = "Could not extract text from this link."
        if error:
            detail = f"{detail} Reason: {error}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    # Truncate
    max_chars = 20000
    truncated = len(text) > max_chars
    text = text[:max_chars]

    return {
        "url": url,
        "platform": platform,
        "source_type": result.get("source_type", platform),
        "chars_extracted": len(text),
        "truncated": truncated,
        "text": text,
        "metadata": result.get("metadata", {}),
    }


@router.post("/chat", response_model=BrandChatResponse)
async def chat(
    body: BrandChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to the brand discovery AI. Creates a new chat if needed."""
    admin = get_admin_client()

    # Find or create active chat for this module
    chat_resp = (
        admin.table("brand_chats")
        .select("*")
        .eq("user_id", user.id)
        .eq("module", body.module)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if chat_resp.data:
        chat_row = chat_resp.data[0]
    else:
        # Create new chat with opening message
        opening = get_opening_message(body.module)
        new_chat = (
            admin.table("brand_chats")
            .insert({
                "user_id": user.id,
                "module": body.module,
                "messages": [{"role": "assistant", "content": opening}],
                "extracted": {},
                "status": "active",
            })
            .execute()
        )
        chat_row = new_chat.data[0]

    # ── Build document context block with markers (Fix Ladder step 2) ──
    import hashlib

    doc_context_block = None
    if body.file_context:
        file_label = body.file_name or "attached content"
        doc_text = body.file_context[:15000]

        # Validation gate (Fix Ladder step 1): reject if extraction is empty/broken
        if len(doc_text.strip()) < 50:
            logger.error(
                "Document text too short to be useful (len=%d). "
                "Extraction/attachment pipeline may be broken.",
                len(doc_text.strip()),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Document text was not included properly (length={len(doc_text.strip())}). "
                    "The file extraction may have failed. Please try uploading the file again."
                ),
            )

        sha1 = hashlib.sha1(doc_text.encode("utf-8", errors="replace")).hexdigest()[:12]
        doc_context_block = (
            f"DOCUMENT_CONTEXT v1\n"
            f"source={file_label}\n"
            f"sha1={sha1}\n"
            f"chars={len(doc_text)}\n"
            f"--- BEGIN DOCUMENT TEXT ---\n"
            f"{doc_text}\n"
            f"--- END DOCUMENT TEXT ---"
        )
        logger.info(
            "Document context prepared: source=%s, sha1=%s, chars=%d",
            file_label, sha1, len(doc_text),
        )

    # Append user message to chat history (stored version shows attachment label only)
    messages = list(chat_row.get("messages", []))
    stored_msg = body.message
    if body.file_name:
        # Use link icon for URLs, paperclip for files
        is_url = body.file_name.startswith(("http://", "https://"))
        icon = "🔗" if is_url else "📎"
        stored_msg = f"{body.message}\n\n{icon} {body.file_name}"
    messages.append({"role": "user", "content": stored_msg})

    # Retrieve relevant context from user's uploaded resources
    resource_context = get_relevant_context(body.message, user.id)

    # Retrieve performance context (what's worked for this user)
    perf_context = ""
    try:
        from app.services.brand_chat import _fetch_performance_context
        perf_context = _fetch_performance_context(user.id)
    except Exception:
        pass

    # Retrieve agent memory context (learned preferences and patterns)
    mem_context = ""
    try:
        from app.services.brand_chat import _fetch_memory_context
        mem_context = _fetch_memory_context(user.id)
    except Exception:
        pass

    # Retrieve real-time research context (live web, YouTube, Reddit)
    research_context = ""
    try:
        profile = _get_profile_json(admin, user.id)
        research_context = _fetch_research_context(body.message, profile)
    except Exception as e:
        logger.debug("Research context fetch failed: %s", e)

    # Build LLM prompt and get response
    # Document text is injected as a DEDICATED message (not appended to user msg)
    llm = _get_llm_client()
    llm_messages = build_chat_messages(
        body.module, messages, resource_context,
        perf_context, mem_context, research_context,
        document_context=doc_context_block or "",
    )

    # ── Debug: log outbound message structure (Fix Ladder step 2) ──
    if doc_context_block:
        msg_roles = [m["role"] for m in llm_messages]
        has_doc_marker = any("DOCUMENT_CONTEXT v1" in m.get("content", "") for m in llm_messages)
        logger.info(
            "LLM message structure: roles=%s, has_doc_marker=%s, total_chars=%d",
            msg_roles,
            has_doc_marker,
            sum(len(m.get("content", "")) for m in llm_messages),
        )

    try:
        response = llm.chat(
            messages=llm_messages,
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API quota exceeded. Please check your billing at https://platform.openai.com/billing",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {error_msg[:200]}",
        )

    reply, new_extracted = parse_chat_response(response["content"])

    # Merge newly extracted fields into running total
    current_extracted = chat_row.get("extracted", {}) or {}
    merged_extracted = deep_merge(current_extracted, new_extracted)

    # Append assistant reply
    messages.append({"role": "assistant", "content": reply})

    # Update chat row
    admin.table("brand_chats").update({
        "messages": messages,
        "extracted": merged_extracted,
    }).eq("id", chat_row["id"]).execute()

    progress = estimate_progress(body.module, merged_extracted)

    return BrandChatResponse(
        reply=reply,
        extracted_so_far=merged_extracted,
        progress=progress,
        chat_id=chat_row["id"],
    )


@router.get("/chats/{module}", response_model=BrandChatListResponse)
async def list_chats(
    module: str,
    user: CurrentUser = Depends(get_current_user),
):
    """List all chats for a module (active + completed, not archived)."""
    _validate_module(module)
    admin = get_admin_client()

    resp = (
        admin.table("brand_chats")
        .select("id, module, title, status, messages, created_at, updated_at")
        .eq("user_id", user.id)
        .eq("module", module)
        .neq("status", "archived")
        .order("created_at", desc=True)
        .execute()
    )

    chats = []
    for row in resp.data or []:
        msgs = row.get("messages", []) or []
        chats.append(BrandChatSummary(
            chat_id=row["id"],
            module=row["module"],
            title=row.get("title"),
            status=row["status"],
            message_count=len(msgs),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        ))

    return BrandChatListResponse(module=module, chats=chats)


@router.get("/chat/{module}", response_model=BrandChatHistory)
async def get_chat_history(
    module: str,
    chat_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Get chat history for a module. Pass ?chat_id= to load a specific chat."""
    _validate_module(module)
    admin = get_admin_client()

    if chat_id:
        # Load a specific chat
        resp = (
            admin.table("brand_chats")
            .select("*")
            .eq("id", chat_id)
            .eq("user_id", user.id)
            .eq("module", module)
            .execute()
        )
    else:
        # Load the most recent active chat
        resp = (
            admin.table("brand_chats")
            .select("*")
            .eq("user_id", user.id)
            .eq("module", module)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

    if not resp.data:
        return BrandChatHistory(module=module)

    row = resp.data[0]
    return BrandChatHistory(
        chat_id=row["id"],
        module=row["module"],
        messages=row.get("messages", []),
        extracted=row.get("extracted", {}),
        status=row["status"],
    )


@router.post("/chat/{module}/new", response_model=BrandChatHistory)
async def start_new_chat(
    module: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Start a fresh chat for a module. Old active chats stay but are no longer the 'current' one."""
    _validate_module(module)
    admin = get_admin_client()

    opening = get_opening_message(module)
    new_chat = (
        admin.table("brand_chats")
        .insert({
            "user_id": user.id,
            "module": module,
            "messages": [{"role": "assistant", "content": opening}],
            "extracted": {},
            "status": "active",
            "title": None,
        })
        .execute()
    )

    row = new_chat.data[0]
    return BrandChatHistory(
        chat_id=row["id"],
        module=row["module"],
        messages=row.get("messages", []),
        extracted=row.get("extracted", {}),
        status=row["status"],
    )


@router.delete("/chat/{chat_id}")
async def delete_chat(
    chat_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete (archive) a chat. Doesn't remove data — just hides it."""
    admin = get_admin_client()

    # Verify ownership
    resp = (
        admin.table("brand_chats")
        .select("id")
        .eq("id", chat_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Chat not found")

    admin.table("brand_chats").update({
        "status": "archived",
    }).eq("id", chat_id).execute()

    return {"message": "Chat deleted"}


@router.patch("/chat/{chat_id}/title")
async def rename_chat(
    chat_id: str,
    body: BrandChatTitleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Rename a chat."""
    admin = get_admin_client()

    resp = (
        admin.table("brand_chats")
        .select("id")
        .eq("id", chat_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Chat not found")

    admin.table("brand_chats").update({
        "title": body.title,
    }).eq("id", chat_id).execute()

    return {"message": "Chat renamed", "title": body.title}


@router.post("/chat/{module}/complete", response_model=BrandChatCompleteResponse)
async def complete_chat(
    module: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Mark a chat as complete and merge extracted data into the profile."""
    _validate_module(module)

    admin = get_admin_client()

    # Find active chat
    resp = (
        admin.table("brand_chats")
        .select("*")
        .eq("user_id", user.id)
        .eq("module", module)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active chat found for module '{module}'",
        )

    chat_row = resp.data[0]
    extracted = chat_row.get("extracted", {})

    # Merge into profile
    current_profile = _get_profile_json(admin, user.id)
    current_section = current_profile.get(module, {})
    merged = deep_merge(current_section, extracted)

    current_profile[module] = merged
    admin.table("profiles").upsert({
        "user_id": user.id,
        "profile_json": current_profile,
    }).execute()

    # Mark chat as completed
    admin.table("brand_chats").update({
        "status": "completed",
    }).eq("id", chat_row["id"]).execute()

    field_count = _count_fields(extracted)

    return BrandChatCompleteResponse(
        message=f"Chat completed. {field_count} fields merged into your {module} profile.",
        merged_fields=field_count,
    )


# ── AI Suggest ───────────────────────────────────────────────


@router.post("/suggest", response_model=BrandSuggestResponse)
async def suggest_field(
    body: BrandSuggestRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Given a field path and current context, suggest a value."""
    admin = get_admin_client()

    # Get current profile for context
    profile = _get_profile_json(admin, user.id)
    context = body.context or profile

    # Retrieve relevant resources for richer suggestions
    resource_context = get_relevant_context(body.field, user.id)

    # Build prompt
    llm = _get_llm_client()
    context_str = _format_context(context)

    system = SUGGEST_SYSTEM
    if resource_context:
        system += (
            "\n\nRelevant knowledge from the user's uploaded resources:\n"
            + resource_context
        )

    try:
        response = llm.chat(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Field to suggest: {body.field}\n\n"
                        f"Current profile context:\n{context_str}\n\n"
                        f"Suggest a specific, relevant value for this field. "
                        f"Return only the suggestion text."
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=500,
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API quota exceeded. Please check your billing at https://platform.openai.com/billing",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {error_msg[:200]}",
        )

    return BrandSuggestResponse(
        field=body.field,
        suggestion=response["content"].strip(),
    )


# ── Internal helpers ─────────────────────────────────────────


def _count_fields(data: Dict[str, Any], depth: int = 0) -> int:
    """Count non-empty leaf values in a nested dict."""
    if depth > 4:
        return 0
    count = 0
    for val in data.values():
        if isinstance(val, dict):
            count += _count_fields(val, depth + 1)
        elif isinstance(val, list) and len(val) > 0:
            count += 1
        elif val is not None and val != "":
            count += 1
    return count


def _format_context(profile: Dict[str, Any]) -> str:
    """Format profile data as readable text for the LLM."""
    parts = []

    foundation = profile.get("foundation", {})
    if foundation:
        if foundation.get("beliefs"):
            parts.append(f"Core beliefs: {', '.join(foundation['beliefs'][:5])}")
        it_f = foundation.get("it_factor", {})
        if it_f.get("unfair_advantage"):
            parts.append(f"Unfair advantage: {it_f['unfair_advantage']}")
        if foundation.get("content_pillars"):
            parts.append(f"Content pillars: {', '.join(foundation['content_pillars'])}")

    ica = profile.get("ica", {})
    if ica:
        demo = ica.get("demographics", {})
        if demo:
            parts.append(f"Target audience: {demo.get('occupation', 'unknown')}, "
                         f"age {demo.get('age', 'unknown')}, "
                         f"based in {demo.get('location', 'unknown')}")
        if ica.get("big_need"):
            parts.append(f"Their biggest need: {ica['big_need']}")
        if ica.get("big_want"):
            parts.append(f"Their desired outcome: {ica['big_want']}")

    offer = profile.get("offer", {})
    if offer:
        if offer.get("what"):
            parts.append(f"Offer: {offer['what']}")
        if offer.get("target_audience"):
            parts.append(f"Target audience: {offer['target_audience']}")
        if offer.get("differentiator"):
            parts.append(f"Differentiator: {offer['differentiator']}")

    brand = profile.get("brand", {})
    if brand:
        if brand.get("statement"):
            parts.append(f"Brand statement: {brand['statement']}")
        if brand.get("content_pillars"):
            parts.append(f"Content pillars: {', '.join(brand['content_pillars'])}")

    return "\n".join(parts) if parts else "No profile data yet."
