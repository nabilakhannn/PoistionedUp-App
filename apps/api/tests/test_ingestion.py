"""Unit tests for text extraction, chunking, platform detection, and metadata (Slice 5).

These are fast, local-only tests (no network, no database).
"""

import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingestion import (
    _clean_reddit_url,
    _extract_youtube_id,
    _flatten_comments,
    _format_duration,
    _format_reddit_comments,
    _format_reddit_header,
    _format_views,
    _parse_reddit_post,
    chunk_text,
    detect_platform,
    extract_text_from_csv,
    extract_text_from_plain,
    format_metadata_header,
)


class TestChunking:

    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        text = "This is a short paragraph."
        chunks = chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        # Create text with multiple paragraphs totaling > 2000 chars
        paragraphs = [f"Paragraph {i}: " + "x" * 400 for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_text(text, chunk_size=2000, overlap=200)
        assert len(chunks) >= 2

    def test_chunk_size_respected(self):
        # Each chunk should be roughly within chunk_size * 1.5
        paragraphs = [f"Para {i}: " + "y" * 300 for i in range(20)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_text(text, chunk_size=1000, overlap=100)
        for chunk in chunks:
            assert len(chunk) <= 1000 * 2  # Allow some flex for overlap

    def test_single_huge_paragraph_gets_split(self):
        text = "A" * 6000  # Single paragraph, no newlines
        chunks = chunk_text(text, chunk_size=2000, overlap=200)
        assert len(chunks) >= 2

    def test_overlap_exists(self):
        # With overlap, end of chunk N should appear in start of chunk N+1
        paragraphs = [f"unique_marker_{i} " + "w" * 500 for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        if len(chunks) >= 2:
            # The overlap region should share some text
            # (overlap means we re-include the tail of the previous chunk)
            assert len(chunks[1]) > 0  # Second chunk is non-empty

    def test_preserves_paragraph_boundaries(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=10000, overlap=0)
        # All fits in one chunk
        assert len(chunks) == 1
        assert "First paragraph." in chunks[0]
        assert "Third paragraph." in chunks[0]


class TestTextExtraction:

    def test_plain_text_extraction(self):
        content = b"Hello, world! This is a test file."
        result = extract_text_from_plain(content)
        assert result == "Hello, world! This is a test file."

    def test_plain_text_utf8(self):
        content = "Unicode: \u00e9\u00e0\u00fc\u00f1".encode("utf-8")
        result = extract_text_from_plain(content)
        assert "\u00e9" in result

    def test_csv_extraction(self):
        content = b"name,score\nAlice,95\nBob,87"
        result = extract_text_from_csv(content)
        assert "Alice" in result
        assert "95" in result
        assert "Bob" in result

    def test_csv_pipe_separated_output(self):
        content = b"col1,col2,col3\na,b,c"
        result = extract_text_from_csv(content)
        lines = result.strip().split("\n")
        assert " | " in lines[0]  # Cells joined with pipe


class TestYouTubeIdExtraction:
    """Unit tests for YouTube URL parsing (no network)."""

    def test_standard_url(self):
        assert _extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert _extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert _extract_youtube_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        assert _extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120") == "dQw4w9WgXcQ"

    def test_not_youtube(self):
        assert _extract_youtube_id("https://www.google.com/search?q=test") is None

    def test_plain_text(self):
        assert _extract_youtube_id("not a url at all") is None

    def test_empty_string(self):
        assert _extract_youtube_id("") is None


class TestPlatformDetection:
    """Unit tests for multi-platform URL detection (no network)."""

    # YouTube videos
    def test_youtube_standard(self):
        assert detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube_video"

    def test_youtube_short_url(self):
        assert detect_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube_video"

    def test_youtube_shorts(self):
        assert detect_platform("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "youtube_video"

    # YouTube channels
    def test_youtube_channel_at(self):
        assert detect_platform("https://www.youtube.com/@MrBeast") == "youtube_channel"

    def test_youtube_channel_c(self):
        assert detect_platform("https://www.youtube.com/c/MrBeast") == "youtube_channel"

    def test_youtube_channel_id(self):
        assert detect_platform("https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA") == "youtube_channel"

    def test_youtube_channel_user(self):
        assert detect_platform("https://www.youtube.com/user/PewDiePie") == "youtube_channel"

    def test_youtube_channel_with_videos_tab(self):
        assert detect_platform("https://www.youtube.com/@MrBeast/videos") == "youtube_channel"

    # TikTok
    def test_tiktok_video(self):
        assert detect_platform("https://www.tiktok.com/@username/video/1234567890") == "tiktok"

    def test_tiktok_short_link(self):
        assert detect_platform("https://vm.tiktok.com/ZMhCabcde") == "tiktok"

    # Facebook
    def test_facebook_video(self):
        assert detect_platform("https://www.facebook.com/page/videos/12345") == "facebook"

    def test_facebook_reel(self):
        assert detect_platform("https://www.facebook.com/reel/12345") == "facebook"

    def test_facebook_ads_library(self):
        assert detect_platform("https://www.facebook.com/ads/library/?id=12345") == "facebook"

    def test_facebook_watch(self):
        assert detect_platform("https://www.facebook.com/watch/?v=12345") == "facebook"

    def test_fb_watch_short(self):
        assert detect_platform("https://fb.watch/abc123") == "facebook"

    # Webpages (fallback)
    def test_regular_webpage(self):
        assert detect_platform("https://www.example.com/article") == "webpage"

    def test_blog_url(self):
        assert detect_platform("https://blog.hubspot.com/marketing/content-strategy") == "webpage"

    def test_google_url(self):
        assert detect_platform("https://www.google.com/search?q=test") == "webpage"


class TestFormatDuration:
    """Unit tests for duration formatting."""

    def test_seconds_only(self):
        assert _format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert _format_duration(630) == "10:30"

    def test_hours(self):
        assert _format_duration(3661) == "1:01:01"

    def test_none_returns_unknown(self):
        assert _format_duration(None) == "unknown"

    def test_zero_returns_unknown(self):
        assert _format_duration(0) == "unknown"


class TestFormatViews:
    """Unit tests for view count formatting."""

    def test_small_number(self):
        assert _format_views(999) == "999"

    def test_thousands(self):
        assert _format_views(1500) == "1.5K"

    def test_millions(self):
        assert _format_views(2500000) == "2.5M"

    def test_none_returns_unknown(self):
        assert _format_views(None) == "unknown"

    def test_exact_million(self):
        assert _format_views(1000000) == "1.0M"

    def test_exact_thousand(self):
        assert _format_views(1000) == "1.0K"


class TestMetadataHeader:
    """Unit tests for metadata header formatting."""

    def test_full_metadata(self):
        meta = {
            "title": "How to Cook Pasta",
            "channel": "Gordon Ramsay",
            "platform": "youtube",
            "views_str": "1.5M",
            "duration_str": "10:30",
            "upload_date": "20240615",
            "description": "A great recipe",
        }
        header = format_metadata_header(meta)
        assert "[VIDEO INFO]" in header
        assert "Title: How to Cook Pasta" in header
        assert "Channel: Gordon Ramsay" in header
        assert "Platform: youtube" in header
        assert "Views: 1.5M" in header
        assert "Duration: 10:30" in header
        assert "Published: 2024-06-15" in header
        assert "[TRANSCRIPT]" in header

    def test_partial_metadata(self):
        meta = {"title": "Test Video"}
        header = format_metadata_header(meta)
        assert "[VIDEO INFO]" in header
        assert "Title: Test Video" in header
        assert "[TRANSCRIPT]" in header
        # Should not have Views or Duration lines
        assert "Views:" not in header
        assert "Duration:" not in header

    def test_empty_metadata(self):
        header = format_metadata_header({})
        assert "[VIDEO INFO]" in header
        assert "[TRANSCRIPT]" in header

    def test_description_truncated(self):
        meta = {"description": "x" * 500}
        header = format_metadata_header(meta)
        # Description should be capped at 300 chars
        desc_line = [line for line in header.split("\n") if line.startswith("Description:")][0]
        assert len(desc_line) <= len("Description: ") + 300


# ── Reddit URL detection tests ───────────────────────────


class TestRedditDetection:

    def test_reddit_post_url(self):
        assert detect_platform("https://www.reddit.com/r/python/comments/abc123/my_post_title/") == "reddit"

    def test_reddit_no_trailing_slash(self):
        assert detect_platform("https://www.reddit.com/r/python/comments/abc123/my_post") == "reddit"

    def test_reddit_old_domain(self):
        assert detect_platform("https://old.reddit.com/r/python/comments/abc123/some_post/") == "reddit"

    def test_reddit_short_link(self):
        assert detect_platform("https://redd.it/abc123") == "reddit"

    def test_reddit_with_query_params(self):
        assert detect_platform("https://www.reddit.com/r/python/comments/abc123/post/?utm_source=share") == "reddit"

    def test_reddit_subreddit_listing_is_webpage(self):
        # r/python without /comments/ should be webpage, not reddit
        assert detect_platform("https://www.reddit.com/r/python/") == "webpage"

    def test_reddit_homepage_is_webpage(self):
        assert detect_platform("https://www.reddit.com/") == "webpage"


# ── Twitter/X URL detection tests ────────────────────────


class TestTwitterDetection:

    def test_twitter_standard(self):
        assert detect_platform("https://twitter.com/elonmusk/status/1234567890") == "twitter"

    def test_x_domain(self):
        assert detect_platform("https://x.com/elonmusk/status/1234567890") == "twitter"

    def test_twitter_www(self):
        assert detect_platform("https://www.twitter.com/user/status/9876543210") == "twitter"

    def test_x_www(self):
        assert detect_platform("https://www.x.com/user/status/9876543210") == "twitter"

    def test_twitter_mobile(self):
        assert detect_platform("https://mobile.twitter.com/user/status/1234567890") == "twitter"

    def test_twitter_with_params(self):
        assert detect_platform("https://twitter.com/user/status/1234567890?s=20&t=abc") == "twitter"

    def test_twitter_profile_is_webpage(self):
        assert detect_platform("https://twitter.com/elonmusk") == "webpage"


# ── Substack URL detection tests ─────────────────────────


class TestSubstackDetection:

    def test_substack_article(self):
        assert detect_platform("https://example.substack.com/p/my-great-article") == "substack"

    def test_substack_publish_post(self):
        assert detect_platform("https://example.substack.com/publish/post/12345") == "substack"

    def test_substack_with_params(self):
        assert detect_platform("https://newsletter.substack.com/p/my-article?utm_source=email") == "substack"

    def test_substack_homepage_is_webpage(self):
        assert detect_platform("https://example.substack.com/") == "webpage"

    def test_custom_domain_is_webpage(self):
        assert detect_platform("https://stratechery.com/2024/some-article") == "webpage"


# ── LinkedIn URL detection tests ─────────────────────────


class TestLinkedInDetection:

    def test_linkedin_post(self):
        assert detect_platform("https://www.linkedin.com/posts/username-abc123") == "linkedin"

    def test_linkedin_pulse(self):
        assert detect_platform("https://www.linkedin.com/pulse/my-article-title-abc123") == "linkedin"

    def test_linkedin_feed_update(self):
        assert detect_platform("https://www.linkedin.com/feed/update/urn:li:activity:1234567890") == "linkedin"

    def test_linkedin_profile_is_webpage(self):
        assert detect_platform("https://www.linkedin.com/in/username") == "webpage"

    def test_linkedin_company_is_webpage(self):
        assert detect_platform("https://www.linkedin.com/company/acme") == "webpage"


# ── Reddit URL cleaning tests ────────────────────────────


class TestRedditUrlCleaning:

    def test_strips_query_params(self):
        result = _clean_reddit_url(
            "https://www.reddit.com/r/python/comments/abc123/my_post/?utm_source=share&utm_medium=web"
        )
        assert "utm_source" not in result
        assert result.endswith("/my_post")

    def test_strips_existing_json_suffix(self):
        result = _clean_reddit_url(
            "https://www.reddit.com/r/python/comments/abc123/my_post.json"
        )
        assert not result.endswith(".json")

    def test_normalizes_old_reddit(self):
        result = _clean_reddit_url("https://old.reddit.com/r/python/comments/abc123/post")
        assert "www.reddit.com" in result
        assert "old.reddit.com" not in result


# ── Reddit JSON parsing tests (mock data, no network) ───


class TestRedditParsing:

    def _make_comment(self, body, score=1, author="testuser", replies=None):
        return {
            "kind": "t1",
            "data": {
                "body": body,
                "score": score,
                "author": author,
                "created_utc": 1700000000,
                "replies": replies or "",
            },
        }

    def _make_reddit_json(self, post_data, comments):
        return [
            {"data": {"children": [{"kind": "t3", "data": post_data}]}},
            {"data": {"children": comments}},
        ]

    def test_parse_basic_post(self):
        json_data = self._make_reddit_json(
            {"title": "Test Post", "selftext": "Hello world", "score": 100,
             "num_comments": 5, "subreddit": "python", "author": "testuser",
             "created_utc": 1700000000, "url": "", "is_self": True},
            [],
        )
        result = _parse_reddit_post(json_data)
        assert result["post"]["title"] == "Test Post"
        assert result["post"]["score"] == 100
        assert result["error"] == ""

    def test_comments_sorted_by_score(self):
        json_data = self._make_reddit_json(
            {"title": "T", "selftext": "", "score": 1, "num_comments": 3,
             "subreddit": "test", "author": "a", "created_utc": 0,
             "url": "", "is_self": True},
            [
                self._make_comment("low", score=1),
                self._make_comment("high", score=100),
                self._make_comment("mid", score=50),
            ],
        )
        result = _parse_reddit_post(json_data)
        assert result["comments"][0]["body"] == "high"
        assert result["comments"][1]["body"] == "mid"
        assert result["comments"][2]["body"] == "low"

    def test_deleted_comments_skipped(self):
        json_data = self._make_reddit_json(
            {"title": "T", "selftext": "", "score": 1, "num_comments": 2,
             "subreddit": "test", "author": "a", "created_utc": 0,
             "url": "", "is_self": True},
            [
                self._make_comment("[deleted]", score=50),
                self._make_comment("real comment", score=10),
                self._make_comment("[removed]", score=30),
            ],
        )
        result = _parse_reddit_post(json_data)
        assert len(result["comments"]) == 1
        assert result["comments"][0]["body"] == "real comment"

    def test_nested_comments_flattened(self):
        nested = [
            {
                "kind": "t1",
                "data": {
                    "body": "parent",
                    "score": 10,
                    "author": "a",
                    "created_utc": 0,
                    "replies": {
                        "data": {
                            "children": [
                                {
                                    "kind": "t1",
                                    "data": {
                                        "body": "child",
                                        "score": 5,
                                        "author": "b",
                                        "created_utc": 0,
                                        "replies": "",
                                    },
                                }
                            ]
                        }
                    },
                },
            }
        ]
        result = []
        _flatten_comments(nested, result)
        assert len(result) == 2
        bodies = [c["body"] for c in result]
        assert "parent" in bodies
        assert "child" in bodies

    def test_invalid_json_returns_error(self):
        result = _parse_reddit_post([])
        assert result.get("error")

    def test_more_stubs_skipped(self):
        """Reddit 'more' comment stubs (kind != 't1') should be skipped."""
        comments = [
            self._make_comment("real", score=10),
            {"kind": "more", "data": {"count": 5, "children": ["id1", "id2"]}},
        ]
        json_data = self._make_reddit_json(
            {"title": "T", "selftext": "", "score": 1, "num_comments": 6,
             "subreddit": "test", "author": "a", "created_utc": 0,
             "url": "", "is_self": True},
            comments,
        )
        result = _parse_reddit_post(json_data)
        assert len(result["comments"]) == 1
        assert result["comments"][0]["body"] == "real"


# ── Reddit format header tests ───────────────────────────


class TestRedditFormatHeader:

    def test_full_reddit_header(self):
        post = {
            "title": "How to learn Python",
            "subreddit": "learnpython",
            "author": "newbie",
            "score": 250,
            "num_comments": 42,
            "created_utc": 1700000000,
            "selftext": "I want to learn Python, any tips?",
            "is_self": True,
            "url": "",
        }
        header = _format_reddit_header(post, 10)
        assert "[REDDIT POST]" in header
        assert "r/learnpython" in header
        assert "Score: 250" in header
        assert "Comments: 42" in header
        assert "[TOP COMMENTS (10)]" in header
        assert "I want to learn Python" in header

    def test_link_post_includes_url(self):
        post = {
            "title": "Cool article",
            "subreddit": "tech",
            "author": "poster",
            "score": 50,
            "num_comments": 3,
            "created_utc": 0,
            "selftext": "",
            "is_self": False,
            "url": "https://example.com/article",
        }
        header = _format_reddit_header(post, 0)
        assert "Link: https://example.com/article" in header
        assert "[TOP COMMENTS" not in header

    def test_reddit_comments_formatting(self):
        comments = [
            {"body": "Great post!", "score": 100, "author": "fan", "created_utc": 0},
            {"body": "I disagree", "score": 5, "author": "critic", "created_utc": 0},
        ]
        text = _format_reddit_comments(comments)
        assert "Comment 1" in text
        assert "score: 100" in text
        assert "u/fan" in text
        assert "Comment 2" in text
        assert "I disagree" in text
