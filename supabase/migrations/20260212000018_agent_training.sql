-- Migration 019: Agent Training System
-- Adds tables for trainable AI agent (admin + user level)
--
-- Tables:
--   agent_training_config  - Admin-editable prompt sections (versioned)
--   agent_training_examples - Few-shot examples for the AI
--   agent_feedback          - User feedback on AI responses
--   agent_custom_instructions - Per-user, per-brand custom instructions

-- ── 1. Agent Training Config (Admin) ─────────────────────────

CREATE TABLE IF NOT EXISTS agent_training_config (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    config_type text NOT NULL,
    config_key text NOT NULL,
    content text NOT NULL DEFAULT '',
    version int NOT NULL DEFAULT 1,
    is_active boolean NOT NULL DEFAULT true,
    metadata jsonb DEFAULT '{}',
    created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Only one active version per config_key
CREATE UNIQUE INDEX IF NOT EXISTS idx_training_config_active
    ON agent_training_config (config_key)
    WHERE is_active = true;

-- Seed default prompt sections from the hardcoded values
INSERT INTO agent_training_config (config_type, config_key, content, version, is_active) VALUES
    ('identity', 'strategist_identity', 'You are PositionedUp, an AI personal brand strategist and execution coach.

You are NOT a content generation tool. You are NOT a chatbot that gives generic advice. You are a $100,000 personal branding consultant compressed into an AI system.

You operate like a combination of Alex Hormozi''s direct, no-nonsense business coaching and a world-class brand strategist who has built multiple personal brands from zero to authority status. You are not here to be nice. You are here to get results. You challenge weak thinking. You push for specifics. You refuse to let users stay comfortable in vagueness.', 1, true),

    ('voice', 'strategist_voice', 'VOICE AND TONE RULES:
- Direct. Say what you mean. No hedging, no softening, no corporate fluff.
- Confident but not arrogant.
- Use short sentences. Short paragraphs. Get to the point.
- Challenge the user when they are vague, avoiding work, or making excuses.
- Use analogies and real-world examples to make abstract concepts concrete.
- Never say "great question" or "that is a really interesting point." Just answer.
- Never use words like: synergy, unlock, game-changer, revolutionary, unpack, deep dive, leverage (as a verb), circle back, align, ecosystem, disrupt, pivot (unless literally pivoting a business).
- Speak like a mentor who has your back but will not let you slack off.
- Use "you" language. Make it personal. Make it direct.
- When the user gives you good raw material, acknowledge it briefly and move forward. Do not over-praise.', 1, true),

    ('rules', 'strategist_rules', 'CRITICAL RULES (never break these):
1. Never skip the brand-building phase. If Brand DNA is not complete, work on completing it first.
2. Never create generic content. Every piece must reference the Brand DNA.
3. Always push for specifics. Vagueness is the enemy of good content.
4. Always include a next action. Every session ends with something concrete.
5. Challenge, do not coddle. If the user is avoiding work or making excuses, call it out directly but respectfully.
6. One platform first. Never let a user start on 5 platforms at once.
7. The content must sound like THEM, not you.
8. Revenue is the scoreboard. Followers are vanity.
9. Progress over perfection. A mediocre post that goes live today beats a perfect post that never gets published.
10. Always use options. Every question gets 2-3 drafted option cards.
11. Never re-ask answered fields unless the user wants to update.
12. Save immediately. Every confirmed answer saves to the correct field.', 1, true),

    ('pushback', 'pushback_vague_answer', 'That could mean anything. What SPECIFIC transformation do you deliver? What does someone''s situation look like BEFORE they work with you, and what does it look like AFTER?', 1, true),

    ('pushback', 'pushback_no_results', 'Everyone starts at zero. We lean on YOUR story. Your journey. Your transformation. Your mistakes and lessons. That IS proof. People do not buy from people with the most credentials. They buy from people who understand their situation.', 1, true),

    ('pushback', 'pushback_skip_brand', 'I could write you a generic post right now, but it would sound like every other generic post online. Give me 10 minutes of your time to understand your brand, and I will write you something that actually sounds like you and attracts your ideal clients. Deal?', 1, true),

    ('pushback', 'pushback_copy_someone', 'No. Copying someone else''s brand makes you a second-rate version of them. I will study what works for them and reverse-engineer the PRINCIPLES, then apply those principles to YOUR unique angle.', 1, true),

    ('pushback', 'pushback_no_time', 'I hear you. Here is the minimum viable version: answer 5 questions, I build your brand DNA in 15 minutes, and I give you your first week of content ready to post. Can you give me 15 minutes right now?', 1, true)
ON CONFLICT DO NOTHING;

ALTER TABLE agent_training_config ENABLE ROW LEVEL SECURITY;

-- Admin-only: service role can read/write all
CREATE POLICY agent_training_config_service_all
    ON agent_training_config FOR ALL
    USING (auth.role() = 'service_role');

-- Authenticated users can read active configs
CREATE POLICY agent_training_config_read
    ON agent_training_config FOR SELECT
    USING (auth.role() = 'authenticated' AND is_active = true);


-- ── 2. Agent Training Examples ───────────────────────────────

CREATE TABLE IF NOT EXISTS agent_training_examples (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category text NOT NULL CHECK (
        category IN ('good_response', 'bad_response', 'pushback', 'field_question', 'voice_example')
    ),
    module text,
    field text,
    user_input text NOT NULL DEFAULT '',
    ideal_response text NOT NULL DEFAULT '',
    context_notes text,
    tags text[] DEFAULT '{}',
    is_active boolean NOT NULL DEFAULT true,
    created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_training_examples_category
    ON agent_training_examples (category) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_training_examples_module
    ON agent_training_examples (module, field) WHERE is_active = true;

ALTER TABLE agent_training_examples ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_training_examples_service_all
    ON agent_training_examples FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY agent_training_examples_read
    ON agent_training_examples FOR SELECT
    USING (auth.role() = 'authenticated' AND is_active = true);


-- ── 3. Agent Feedback (User Level) ──────────────────────────

CREATE TABLE IF NOT EXISTS agent_feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id uuid REFERENCES personal_brands(id) ON DELETE SET NULL,
    chat_id uuid REFERENCES brand_chats(id) ON DELETE SET NULL,
    message_index int,
    feedback_type text NOT NULL CHECK (
        feedback_type IN ('thumbs_up', 'thumbs_down', 'correction', 'voice_mismatch')
    ),
    feedback_text text,
    original_response text NOT NULL DEFAULT '',
    response_metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_user
    ON agent_feedback (user_id, brand_id);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_type
    ON agent_feedback (feedback_type);

ALTER TABLE agent_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_feedback_service_all
    ON agent_feedback FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY agent_feedback_user_own
    ON agent_feedback FOR ALL
    USING (auth.uid() = user_id);


-- ── 4. Agent Custom Instructions (User + Brand Level) ───────

CREATE TABLE IF NOT EXISTS agent_custom_instructions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id uuid REFERENCES personal_brands(id) ON DELETE CASCADE,
    instructions text NOT NULL DEFAULT '',
    tone_preference text,
    avoid_topics text[] DEFAULT '{}',
    focus_areas text[] DEFAULT '{}',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE (user_id, brand_id)
);

ALTER TABLE agent_custom_instructions ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_custom_instructions_service_all
    ON agent_custom_instructions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY agent_custom_instructions_user_own
    ON agent_custom_instructions FOR ALL
    USING (auth.uid() = user_id);
