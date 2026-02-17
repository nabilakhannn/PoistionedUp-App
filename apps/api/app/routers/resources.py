"""Resource endpoints: CRUD, file upload, audio upload, channel import."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.resource import (
    ChannelImportRequest,
    ChannelImportResponse,
    ChannelVideoSummary,
    ChunkOut,
    ResourceCreateNote,
    ResourceCreated,
    ResourceDetail,
    ResourceSummary,
    ResourceUpdate,
)
from app.services.ingestion import (
    chunk_text,
    detect_platform,
    extract_channel_videos,
    extract_text,
    extract_text_from_url,
    extract_youtube_transcript,
    format_metadata_header,
    transcribe_audio_bytes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["resources"])

# Max file size: 50 MB (matches Supabase Storage bucket limit)
MAX_FILE_SIZE = 50 * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/csv",
}

AUDIO_CONTENT_TYPES = {
    "audio/mpeg",       # MP3
    "audio/mp3",        # MP3 (alt)
    "audio/wav",        # WAV
    "audio/x-wav",      # WAV (alt)
    "audio/mp4",        # M4A
    "audio/x-m4a",      # M4A (alt)
    "audio/ogg",        # OGG
    "audio/flac",       # FLAC
    "audio/webm",       # WebM audio
}


def _create_chunks(admin, resource_id: str, text: str, extra_metadata: Optional[dict] = None) -> int:
    """Chunk text and insert into resource_chunks table. Returns chunk count."""
    chunks = chunk_text(text)
    if not chunks:
        return 0

    rows = []
    for i, chunk in enumerate(chunks):
        meta = {"char_count": len(chunk)}
        if extra_metadata:
            meta.update(extra_metadata)
        rows.append({
            "resource_id": resource_id,
            "chunk_index": i,
            "chunk_text": chunk,
            "metadata": meta,
        })

    admin.table("resource_chunks").insert(rows).execute()

    # Generate and store embeddings for semantic search (non-blocking)
    try:
        from app.services.embeddings import embed_and_store_chunks
        embed_and_store_chunks(resource_id, chunks)
    except Exception:
        import logging
        logging.getLogger("app.routers.resources").warning(
            "Embedding generation failed for resource %s — chunks stored without embeddings",
            resource_id,
        )

    return len(rows)


# ── POST /resources (note, link, transcript) ──────────────


@router.post("", response_model=ResourceCreated, status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: ResourceCreateNote,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a text-based resource (note, link, or transcript).

    For links with a source_url: auto-fetches the page content or video transcript.
    Supports YouTube, TikTok, and Facebook video URLs (auto-extracts transcript + metadata).
    For YouTube channel URLs: returns guidance to use the /resources/channel endpoint.
    """
    admin = get_admin_client()

    content_text = body.content_text
    resource_type = body.type
    extraction_metadata = {}

    # Auto-fetch content for links
    if body.type == "link" and body.source_url and not content_text.strip():
        # Check if this is a channel URL (redirect to channel endpoint)
        platform = detect_platform(body.source_url)
        if platform == "youtube_channel":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This is a YouTube channel URL. Use POST /resources/channel to import all videos from a channel.",
            )

        result = extract_text_from_url(body.source_url)
        if result["text"]:
            content_text = result["text"]
            extraction_metadata = {
                "source_type": result["source_type"],
                "auto_extracted": True,
            }
            if result.get("metadata"):
                extraction_metadata.update(result["metadata"])
            # Video links become transcripts
            if result["source_type"] in (
                "youtube_transcript", "tiktok_transcript", "facebook_transcript"
            ):
                resource_type = "transcript"

    # Insert resource row
    insert_data = {
        "user_id": user.id,
        "type": resource_type,
        "title": body.title,
        "content_text": content_text,
        "source_url": body.source_url,
        "tags": body.tags,
        "is_gold": body.is_gold,
    }
    if body.collection_id:
        insert_data["collection_id"] = body.collection_id

    resp = (
        admin.table("resources")
        .insert(insert_data)
        .execute()
    )
    resource = resp.data[0]

    # Generate chunks from content_text
    chunk_count = _create_chunks(
        admin, resource["id"], content_text, extra_metadata=extraction_metadata,
    )

    return ResourceCreated(
        id=resource["id"],
        type=resource["type"],
        title=resource["title"],
        chunk_count=chunk_count,
    )


# ── POST /resources/upload (file + audio) ────────────────


@router.post("/upload", response_model=ResourceCreated, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    file: UploadFile = File(...),
    title: str = Query(..., min_length=1, max_length=500),
    tags: str = Query(default="", description="Comma-separated tags"),
    is_gold: bool = Query(default=False),
    collection_id: Optional[str] = Query(default=None, description="Collection to assign resource to"),
    user: CurrentUser = Depends(get_current_user),
):
    """Upload a file or audio, extract text, create resource + chunks.

    Supports:
    - Documents: PDF, DOCX, TXT, MD, CSV
    - Audio: MP3, WAV, M4A, OGG, FLAC, WebM (transcribed via Whisper)
    """
    content_type = file.content_type or ""
    filename = file.filename or "unnamed"
    is_audio = content_type in AUDIO_CONTENT_TYPES or filename.lower().endswith(
        (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm")
    )

    if not is_audio and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed: {content_type}. Allowed: PDF, DOCX, TXT, MD, CSV, MP3, WAV, M4A, OGG, FLAC",
        )

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit",
        )

    admin = get_admin_client()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # Extract text based on file type
    extraction_metadata = {}
    if is_audio:
        # Audio file → Whisper transcription
        result = transcribe_audio_bytes(file_bytes, filename)
        if result["error"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Audio transcription failed: {result['error']}",
            )
        content_text = result["text"]
        resource_type = "transcript"
        extraction_metadata = {
            "source_type": "audio_upload",
            "auto_extracted": True,
            "method": "whisper",
        }
    else:
        # Document file → text extraction
        try:
            content_text = extract_text(file_bytes, content_type, filename)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to extract text from file: {str(e)}",
            )
        resource_type = "file"

    # Insert resource row
    upload_data = {
        "user_id": user.id,
        "type": resource_type,
        "title": title,
        "content_text": content_text,
        "tags": tag_list,
        "is_gold": is_gold,
    }
    if collection_id:
        upload_data["collection_id"] = collection_id

    resp = (
        admin.table("resources")
        .insert(upload_data)
        .execute()
    )
    resource = resp.data[0]
    resource_id = resource["id"]

    # Upload file to Supabase Storage
    storage_path = f"{user.id}/{resource_id}/{filename}"
    try:
        admin.storage.from_("resource-uploads").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type},
        )
        admin.table("resources").update(
            {"storage_path": storage_path}
        ).eq("id", resource_id).execute()
    except Exception:
        pass  # Storage upload is best-effort

    # Generate chunks
    chunk_count = _create_chunks(admin, resource_id, content_text, extra_metadata=extraction_metadata)

    return ResourceCreated(
        id=resource_id,
        type=resource_type,
        title=title,
        chunk_count=chunk_count,
    )


# ── POST /resources/channel (YouTube channel bulk import) ─


def _extract_transcripts_background(
    user_id: str,
    resource_video_pairs: list,
    channel_name: str,
    tags: list,
):
    """Background task: extract transcripts for imported channel videos.

    For each (resource_id, video_id) pair:
    1. Extract transcript (captions first, Whisper fallback)
    2. Update resource content_text with transcript appended to metadata header
    3. Delete old chunks and create new ones from full content
    """
    admin = get_admin_client()

    for resource_id, video_id, meta_header in resource_video_pairs:
        try:
            transcript = extract_youtube_transcript(video_id)
            if not transcript["text"]:
                logger.info(f"No transcript for video {video_id}: {transcript.get('error', '')}")
                continue

            # Build full content with metadata header + transcript
            full_content = meta_header + "\n" + transcript["text"]

            # Update resource content_text
            admin.table("resources").update({
                "content_text": full_content,
            }).eq("id", resource_id).execute()

            # Delete old chunks (metadata-only) and create new ones (full transcript)
            admin.table("resource_chunks").delete().eq("resource_id", resource_id).execute()

            extraction_metadata = {
                "source_type": "youtube_transcript",
                "auto_extracted": True,
                "video_id": video_id,
                "channel": channel_name,
                "language": transcript["language"],
                "method": transcript.get("method", ""),
            }
            _create_chunks(admin, resource_id, full_content, extra_metadata=extraction_metadata)

            logger.info(f"Transcript extracted for video {video_id} (resource {resource_id})")

        except Exception as e:
            logger.warning(f"Background transcript extraction failed for {video_id}: {e}")


@router.post("/channel", response_model=ChannelImportResponse, status_code=status.HTTP_201_CREATED)
async def import_channel(
    body: ChannelImportRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """Import all videos from a YouTube channel.

    Returns immediately after creating resources with video metadata.
    Transcript extraction runs in the background — check individual resources
    to see when their transcripts are ready (content_text will contain [TRANSCRIPT]).
    """
    admin = get_admin_client()

    # Step 1: List all videos from channel (fast, no downloads)
    channel_data = extract_channel_videos(body.channel_url, max_videos=body.max_videos)

    if channel_data["error"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Channel import failed: {channel_data['error']}",
        )

    if not channel_data["videos"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No videos found in this channel",
        )

    # Step 2: Check which videos are already imported (by source_url)
    video_urls = [v["url"] for v in channel_data["videos"]]
    existing_resp = (
        admin.table("resources")
        .select("source_url")
        .eq("user_id", user.id)
        .in_("source_url", video_urls)
        .execute()
    )
    existing_urls = {r["source_url"] for r in existing_resp.data}

    # Step 3: Create resource rows immediately (metadata only, no transcript yet)
    results = []
    imported = 0
    skipped = 0
    failed = 0
    background_pairs = []  # (resource_id, video_id, meta_header) for transcript extraction

    for video in channel_data["videos"]:
        video_summary = ChannelVideoSummary(
            video_id=video["video_id"],
            title=video["title"],
            views_str=video.get("views_str", ""),
            duration_str=video.get("duration_str", ""),
        )

        # Skip already imported
        if video["url"] in existing_urls:
            video_summary.status = "skipped"
            skipped += 1
            results.append(video_summary)
            continue

        try:
            # Build metadata header (instant, no downloads)
            meta_header = format_metadata_header({
                "title": video["title"],
                "channel": channel_data["channel_name"],
                "platform": "youtube",
                "views_str": video.get("views_str", ""),
                "duration_str": video.get("duration_str", ""),
                "upload_date": video.get("upload_date", ""),
            })

            extraction_metadata = {
                "source_type": "youtube_transcript",
                "auto_extracted": True,
                "video_id": video["video_id"],
                "channel": channel_data["channel_name"],
                "views": video.get("views"),
                "duration": video.get("duration"),
                "thumbnail": video.get("thumbnail", ""),
                "upload_date": video.get("upload_date", ""),
            }

            # Insert resource with metadata-only content (transcript comes later)
            video_insert = {
                "user_id": user.id,
                "type": "transcript",
                "title": video["title"],
                "content_text": meta_header,
                "source_url": video["url"],
                "tags": body.tags,
                "is_gold": body.is_gold,
            }
            if body.collection_id:
                video_insert["collection_id"] = body.collection_id

            resp = (
                admin.table("resources")
                .insert(video_insert)
                .execute()
            )
            resource_id = resp.data[0]["id"]

            # Create initial chunks from metadata header
            _create_chunks(admin, resource_id, meta_header, extra_metadata=extraction_metadata)

            # Queue for background transcript extraction
            if body.extract_transcripts and video["video_id"]:
                background_pairs.append((resource_id, video["video_id"], meta_header))
                video_summary.status = "processing"
            else:
                video_summary.status = "success"

            video_summary.resource_id = resource_id
            imported += 1

        except Exception as e:
            logger.warning(f"Failed to create resource for video {video['video_id']}: {e}")
            video_summary.status = "failed"
            failed += 1

        results.append(video_summary)

    # Step 4: Kick off transcript extraction in the background
    if background_pairs:
        background_tasks.add_task(
            _extract_transcripts_background,
            user_id=user.id,
            resource_video_pairs=background_pairs,
            channel_name=channel_data["channel_name"],
            tags=body.tags,
        )

    processing_count = len(background_pairs)
    msg = f"Imported {imported} videos from {channel_data['channel_name']}"
    if processing_count > 0:
        msg += f". Transcripts extracting in background for {processing_count} videos."

    return ChannelImportResponse(
        channel_name=channel_data["channel_name"],
        total_videos=channel_data["count"],
        imported=imported,
        skipped=skipped,
        failed=failed,
        videos=results,
        message=msg,
    )


# ── GET /resources ─────────────────────────────────────────


@router.get("", response_model=List[ResourceSummary])
async def list_resources(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    is_gold: Optional[bool] = Query(None, description="Filter gold resources only"),
    resource_type: Optional[str] = Query(None, alias="type", description="Filter by type"),
    user: CurrentUser = Depends(get_current_user),
):
    """List resources for the authenticated user. Supports filtering by tag, gold, type."""
    admin = get_admin_client()

    query = (
        admin.table("resources")
        .select("id, type, title, source_url, tags, is_gold, storage_path, created_at, updated_at")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
    )

    if tag:
        query = query.contains("tags", [tag])

    if is_gold is not None:
        query = query.eq("is_gold", is_gold)

    if resource_type:
        query = query.eq("type", resource_type)

    resp = query.execute()

    # Get chunk counts for all resources in one query
    resource_ids = [r["id"] for r in resp.data]
    chunk_counts = {}
    if resource_ids:
        chunks_resp = (
            admin.table("resource_chunks")
            .select("resource_id", count="exact")
            .in_("resource_id", resource_ids)
            .execute()
        )
        for row in chunks_resp.data:
            rid = row["resource_id"]
            chunk_counts[rid] = chunk_counts.get(rid, 0) + 1

    return [
        ResourceSummary(
            chunk_count=chunk_counts.get(r["id"], 0),
            **r,
        )
        for r in resp.data
    ]


# ── GET /resources/{id} ───────────────────────────────────


@router.get("/{resource_id}", response_model=ResourceDetail)
async def get_resource(
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a resource by ID with its chunks. Returns 404 if not found or not owned."""
    admin = get_admin_client()

    resp = (
        admin.table("resources")
        .select("*")
        .eq("id", resource_id)
        .eq("user_id", user.id)
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    resource = resp.data[0]

    # Fetch chunks
    chunks_resp = (
        admin.table("resource_chunks")
        .select("id, chunk_index, chunk_text, metadata")
        .eq("resource_id", resource_id)
        .order("chunk_index")
        .execute()
    )

    return ResourceDetail(
        chunks=[ChunkOut(**c) for c in chunks_resp.data],
        **resource,
    )


# ── PATCH /resources/{id} ─────────────────────────────────


@router.patch("/{resource_id}", response_model=ResourceSummary)
async def update_resource(
    resource_id: str,
    body: ResourceUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update resource title, tags, or gold status."""
    admin = get_admin_client()

    # Verify ownership
    existing = (
        admin.table("resources")
        .select("id")
        .eq("id", resource_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    # Build update payload (only include non-None fields)
    update_data = {}
    if body.title is not None:
        update_data["title"] = body.title
    if body.tags is not None:
        update_data["tags"] = body.tags
    if body.is_gold is not None:
        update_data["is_gold"] = body.is_gold

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    resp = (
        admin.table("resources")
        .update(update_data)
        .eq("id", resource_id)
        .eq("user_id", user.id)
        .execute()
    )

    resource = resp.data[0]
    return ResourceSummary(chunk_count=0, **resource)


# ── DELETE /resources/{id} ─────────────────────────────────


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a resource, its chunks, and its storage file (if any)."""
    admin = get_admin_client()

    # Verify ownership and get storage_path
    existing = (
        admin.table("resources")
        .select("id, storage_path")
        .eq("id", resource_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    storage_path = existing.data[0].get("storage_path")

    # Delete chunks
    admin.table("resource_chunks").delete().eq("resource_id", resource_id).execute()

    # Delete storage file if exists
    if storage_path:
        try:
            admin.storage.from_("resource-uploads").remove([storage_path])
        except Exception:
            pass  # Storage cleanup is best-effort

    # Delete resource row
    admin.table("resources").delete().eq("id", resource_id).eq("user_id", user.id).execute()
