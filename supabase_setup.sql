-- ============================================================
--  FRP Compass - Production Grade Schema (HARDENED)
-- ============================================================

-- 0. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS
CREATE TABLE IF NOT EXISTS public.users (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email       TEXT UNIQUE NOT NULL,
    role        TEXT CHECK (role IN ('admin', 'user')) DEFAULT 'user',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. COMPANIES
CREATE TABLE IF NOT EXISTS public.companies (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    company_name  TEXT NOT NULL,
    founder_name  TEXT,
    is_active     BOOLEAN DEFAULT TRUE,
    deleted_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 3. WEEKLY SUBMISSIONS
CREATE TABLE IF NOT EXISTS public.weekly_submissions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id    UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    week_start    DATE NOT NULL,
    
    psf_score     INTEGER DEFAULT 0,
    pmf_score     INTEGER DEFAULT 0,
    gtm_score     INTEGER DEFAULT 0,
    revenue_score INTEGER DEFAULT 0,
    funding_score INTEGER DEFAULT 0,
    
    total_score   INTEGER DEFAULT 0,
    
    submitted_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, week_start)
);

-- 4. ANSWERS
CREATE TABLE IF NOT EXISTS public.answers (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id  UUID REFERENCES public.weekly_submissions(id) ON DELETE CASCADE,
    phase          TEXT NOT NULL,
    pillar         TEXT NOT NULL,
    score          INTEGER NOT NULL CHECK (score >= 0 AND score <= 100), -- Added safety bound
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 5. AUDIT LOGS
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID,
    action      TEXT NOT NULL,
    entity      TEXT NOT NULL,
    entity_id   UUID,
    old_data    JSONB,
    new_data    JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- AUTOMATION: AUTO-COMPUTE TOTAL SCORE
-- ─────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.compute_total_score()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_score := COALESCE(NEW.psf_score,0) + 
                       COALESCE(NEW.pmf_score,0) + 
                       COALESCE(NEW.gtm_score,0) + 
                       COALESCE(NEW.revenue_score,0) + 
                       COALESCE(NEW.funding_score,0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_compute_total_score ON public.weekly_submissions;
CREATE TRIGGER tr_compute_total_score
    BEFORE INSERT OR UPDATE ON public.weekly_submissions
    FOR EACH ROW EXECUTE FUNCTION public.compute_total_score();

-- ─────────────────────────────────────────────────────────────
-- AUTOMATION: AUDIT TRIGGER
-- ─────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO public.audit_logs (user_id, action, entity, entity_id, old_data)
        VALUES (auth.uid(), TG_OP, TG_TABLE_NAME, OLD.id, to_jsonb(OLD));
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO public.audit_logs (user_id, action, entity, entity_id, old_data, new_data)
        VALUES (auth.uid(), TG_OP, TG_TABLE_NAME, NEW.id, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        INSERT INTO public.audit_logs (user_id, action, entity, entity_id, new_data)
        VALUES (auth.uid(), TG_OP, TG_TABLE_NAME, NEW.id, to_jsonb(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER audit_submissions_tg AFTER INSERT OR UPDATE OR DELETE ON public.weekly_submissions FOR EACH ROW EXECUTE FUNCTION public.audit_trigger_func();
CREATE TRIGGER audit_answers_tg AFTER INSERT OR UPDATE OR DELETE ON public.answers FOR EACH ROW EXECUTE FUNCTION public.audit_trigger_func();

-- ─────────────────────────────────────────────────────────────
-- SECURITY: RLS
-- ─────────────────────────────────────────────────────────────

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- FIXED ADMIN POLICIES (Addressing Audit #13)
CREATE POLICY "Admins full access users" ON public.users FOR ALL TO authenticated 
    USING ((SELECT role FROM public.users WHERE id = auth.uid()) = 'admin');

CREATE POLICY "Admins full access companies" ON public.companies FOR ALL TO authenticated 
    USING ((SELECT role FROM public.users WHERE id = auth.uid()) = 'admin');

CREATE POLICY "Admins full access submissions" ON public.weekly_submissions FOR ALL TO authenticated 
    USING ((SELECT role FROM public.users WHERE id = auth.uid()) = 'admin');

CREATE POLICY "Admins full access answers" ON public.answers FOR ALL TO authenticated 
    USING ((SELECT role FROM public.users WHERE id = auth.uid()) = 'admin');

-- USER POLICIES
CREATE POLICY "Users view own data" ON public.users FOR SELECT TO authenticated USING (id = auth.uid());
CREATE POLICY "Users manage own company" ON public.companies FOR ALL TO authenticated USING (user_id = auth.uid());
CREATE POLICY "Users manage own submissions" ON public.weekly_submissions FOR ALL TO authenticated 
    USING (company_id IN (SELECT id FROM public.companies WHERE user_id = auth.uid()));
CREATE POLICY "Users manage own answers" ON public.answers FOR ALL TO authenticated 
    USING (submission_id IN (
        SELECT ws.id FROM public.weekly_submissions ws 
        JOIN public.companies c ON ws.company_id = c.id 
        WHERE c.user_id = auth.uid()
    ));

-- ─────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_submissions_company_week ON public.weekly_submissions (company_id, week_start DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_week ON public.weekly_submissions (week_start DESC); -- Addressing Audit #10
CREATE INDEX IF NOT EXISTS idx_answers_submission ON public.answers (submission_id);
