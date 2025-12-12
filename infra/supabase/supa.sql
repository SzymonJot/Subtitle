-- 1. Cache for translations (shared across everything)
CREATE TABLE IF NOT EXISTS cached_translations (
    cache_id TEXT PRIMARY KEY,
    form_org_lang TEXT NOT NULL,
    sentence_org_lang TEXT NOT NULL,
    word_target_lang TEXT,
    target_lang_sentence TEXT, -- matched Code use vs DB naming
    org_lang TEXT,
    target_lang TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Decks (The user request / configuration)
-- A deck is a specific build configuration (knobs) applied to an analyzed episode.
CREATE TABLE IF NOT EXISTS decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyzed_hash TEXT NOT NULL, -- references the Analysis Job
    idempotency_key TEXT,        -- Unique hash of (analyzed_hash + build_params)
    build_version TEXT,
    
    -- Store the full request so we can reproduce/debug
    request_params JSONB NOT NULL,
    
    -- Metadata about the result
    card_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Cards
-- Individual cards generated for a deck.
CREATE TABLE IF NOT EXISTS cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Auto-generated
    deck_id UUID REFERENCES decks(id), -- Ownership
    
    -- Core Content
    lemma TEXT NOT NULL,
    pos TEXT,
    prompt TEXT NOT NULL,
    answer TEXT NOT NULL,
    sentence TEXT,
    
    -- Meta / Indexing
    analyzed_hash TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
