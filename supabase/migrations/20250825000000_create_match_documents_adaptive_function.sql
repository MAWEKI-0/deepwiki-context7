CREATE OR REPLACE FUNCTION match_documents_adaptive (
  query_embedding VECTOR(768),
  match_count INT,
  filter_criteria JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE (
  id UUID,
  ad_id BIGINT,
  raw_data_snapshot JSONB,
  status TEXT,
  enriched_at TIMESTAMPTZ,
  error_log TEXT,
  strategic_analysis JSONB,
  visual_analysis JSONB,
  audience_persona TEXT,
  vector_summary VECTOR(768),
  created_at TIMESTAMPTZ,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
DECLARE
  sql_query TEXT;
  where_clauses TEXT[] := ARRAY['status = ''ENRICHED'''];
  json_key TEXT;
  json_value JSONB;
BEGIN
  -- Build WHERE clauses from filter_criteria JSONB
  FOR json_key, json_value IN SELECT * FROM jsonb_each(filter_criteria)
  LOOP
    -- Handle nested keys for strategic_analysis
    IF json_key LIKE 'strategic_analysis.%' THEN
      let nested_key = split_part(json_key, '.', 2);
      where_clauses := array_append(where_clauses, format('strategic_analysis->>%L = %L', nested_key, json_value #>> '{}'));
    ELSE
      where_clauses := array_append(where_clauses, format('%I = %L', json_key, json_value #>> '{}'));
    END IF;
  END LOOP;

  -- Construct the final SQL query
  sql_query := 'SELECT *, 1 - (vector_summary <=> $1) AS similarity FROM public.ads';

  IF array_length(where_clauses, 1) > 0 THEN
    sql_query := sql_query || ' WHERE ' || array_to_string(where_clauses, ' AND ');
  END IF;

  sql_query := sql_query || ' ORDER BY similarity DESC LIMIT $2';

  -- Execute the query
  RETURN QUERY EXECUTE sql_query USING query_embedding, match_count;
END;
$$;
