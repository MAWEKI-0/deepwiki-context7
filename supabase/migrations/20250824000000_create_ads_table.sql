CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.ads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ad_id BIGINT NOT NULL,
    raw_data_snapshot JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    enriched_at TIMESTAMPTZ,
    error_log TEXT,
    strategic_analysis JSONB,
    visual_analysis JSONB,
    audience_persona TEXT,
    vector_summary VECTOR(768),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ads_ad_id ON public.ads (ad_id);
CREATE INDEX IF NOT EXISTS idx_ads_status ON public.ads (status);
CREATE INDEX IF NOT EXISTS idx_ads_vector_summary_hnsw ON public.ads USING hnsw (vector_summary vector_l2_ops);

-- Enable Row Level Security (RLS)
ALTER TABLE public.ads ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- This policy restricts all access (SELECT, INSERT, UPDATE, DELETE) to the 'ads' table
-- to only the service_role. This is a critical security measure to ensure that
-- only our authenticated backend can interact with the ad intelligence data.
-- Anonymous and regular authenticated users are denied access.
CREATE POLICY "Allow full access for service role only" ON public.ads
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- Optional: If users can create their own ads, add a policy for inserts
-- CREATE POLICY "Allow authenticated users to insert their own ads" ON public.ads
-- FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Optional: If users can update their own ads, add a policy for updates
-- CREATE POLICY "Allow authenticated users to update their own ads" ON public.ads
-- FOR UPDATE USING (auth.uid() IS NOT NULL) WITH CHECK (auth.uid() IS NOT NULL);
