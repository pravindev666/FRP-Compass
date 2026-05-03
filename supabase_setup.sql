-- ============================================================
--  FRP Tracker – Supabase Database Setup
--  Run this in Supabase → SQL Editor
-- ============================================================

-- 1. FRP Entries table (weekly pillar scores per user)
CREATE TABLE IF NOT EXISTS frp_entries (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID         NOT NULL,          -- from supabase auth
    company_name  TEXT         NOT NULL,
    founder_name  TEXT         NOT NULL,
    phase         TEXT         NOT NULL,          -- PSF, PMF, GTM, Revenue, Funding
    pillar        TEXT         NOT NULL,          -- pillar name within phase
    score_value   INTEGER      NOT NULL DEFAULT 0,
    entry_date    DATE         NOT NULL,          -- the Friday date of that week
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, phase, pillar, entry_date)
);

-- 2. Row Level Security — users only see their own data
ALTER TABLE frp_entries ENABLE ROW LEVEL SECURITY;

-- Users can read/write their own rows
CREATE POLICY "User owns their rows"
    ON frp_entries
    FOR ALL
    USING  (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Admin can read ALL rows. 
-- IMPORTANT: Add all admin emails inside the brackets below.
CREATE POLICY "Admin reads all"
    ON frp_entries
    FOR SELECT
    USING (
        auth.email() IN (
            'pravindev666@gmail.com',
            'admin@frp.in'
        )
    );

-- 3. Index for fast queries
CREATE INDEX IF NOT EXISTS idx_frp_user_date ON frp_entries (user_id, entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_frp_phase     ON frp_entries (phase);

-- ============================================================
--  DONE. Now set these env vars in Streamlit Cloud:
--   SUPABASE_URL      = https://xxxx.supabase.co
--   SUPABASE_ANON_KEY = eyJ...
--   ADMIN_EMAIL       = admin@frp.in
-- ============================================================
