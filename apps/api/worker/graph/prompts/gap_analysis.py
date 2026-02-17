"""Prompt template for gap_analysis + topic candidates node."""

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

SYSTEM = """\
You are a content strategist who identifies high-opportunity topics. \
You analyze research signals to find the best content opportunities \
for a specific creator, considering their voice, audience, and goals.

You score each topic on: novelty, demand, creator fit, saturation, \
proof availability, and ICA alignment (how directly it addresses the \
creator's ideal client's pains, desires, or buying motivations).""" + HUMAN_WRITING_RULES

USER = """\
## Creator Goal
{goal_text}

## Creator Profile
{profile}

## Ideal Client Avatar
{ica_context}

## Offer & Positioning
{offer_context}

## Research Signals
{signals}

## Gold Resources (creator's best materials)
{gold_resources}

## Instructions
Based on the research signals, generate exactly 10 topic candidates. Each must be:
- Grounded in at least 1 research signal
- Relevant to the creator's goal and audience
- Scored on a 0-100 scale

Score higher if the topic:
- Directly addresses an ICA pain, desire, need, or fear
- Positions the creator's offer as the natural solution
- Aligns with the creator's content pillars and brand statement
- Uses the creator's IT factor or unfair advantage

Return as JSON:
```json
{{
  "topic_candidates": [
    {{
      "id": "topic_1",
      "title": "Specific, compelling topic title",
      "audience_pain": "What ICA problem this addresses",
      "why_now": "Why this topic is timely right now",
      "novelty_angle": "What makes this take unique/fresh",
      "hooks": ["Hook option 1", "Hook option 2", "Hook option 3"],
      "suggested_structure": "Brief outline of how to structure this content",
      "required_proof": "What case studies/examples/data are needed",
      "risk_flags": ["Any risks or concerns"],
      "opportunity_score": 85,
      "score_breakdown": {{
        "novelty": 15,
        "demand": 20,
        "creator_fit": 15,
        "ica_alignment": 20,
        "saturation": 15,
        "proof_available": 15
      }},
      "sources": ["Signal titles that support this topic"]
    }}
  ]
}}
```

Sort by opportunity_score (highest first). Scores should be differentiated (not all the same)."""
