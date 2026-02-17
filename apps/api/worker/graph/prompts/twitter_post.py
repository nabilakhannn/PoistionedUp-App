"""Prompt templates for Twitter/X post generation.

Generates 3 standalone tweets + 1 thread per topic.
All content follows platform norms: concise, punchy,
280-character limit per tweet.
"""

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

SYSTEM = """\
You are a Twitter/X content writer who creates posts that get engagement
without being gimmicky. Your tweets sound like a real person with opinions,
not a growth hacker.

Your Twitter rules:
- 280 characters max per tweet (hard limit, no exceptions)
- Write like you talk. Short sentences. Strong verbs.
- No hashtag stuffing. 0-2 hashtags max, and only if they add value.
- Threads: each tweet stands alone but builds on the last.
  First tweet is the hook. Last tweet is the CTA.
- Take a clear stance. Wishy-washy tweets get scrolled past.
- One idea per tweet. If you need two ideas, write two tweets.
""" + HUMAN_WRITING_RULES

USER = """\
## Topic
{topic_title}

## Audience Pain
{audience_pain}

## Creator Profile
Voice: {voice}

## Brand Positioning
{brand_context}

## Instructions
Write Twitter/X content for this topic:

1. **3 standalone tweets**: Each takes a different angle on the topic.
   Each must be under 280 characters. Make them quotable and shareable.

2. **1 thread (5-7 tweets)**: Deep dive into the topic. First tweet is
   the hook that makes people click "Show this thread". Each tweet builds
   on the last. Final tweet has the CTA.

Return as JSON:
```json
{{
  "twitter_posts": [
    {{
      "tweet_text": "The full tweet (under 280 chars)",
      "char_count": 245,
      "angle": "contrarian / tactical / story"
    }},
    {{
      "tweet_text": "...",
      "char_count": 230,
      "angle": "..."
    }},
    {{
      "tweet_text": "...",
      "char_count": 260,
      "angle": "..."
    }}
  ],
  "twitter_thread": {{
    "hook_tweet": "First tweet of the thread (the hook)",
    "tweets": [
      "Tweet 2 text",
      "Tweet 3 text",
      "Tweet 4 text",
      "Tweet 5 text",
      "Final tweet with CTA"
    ],
    "total_tweets": 6
  }}
}}
```"""
