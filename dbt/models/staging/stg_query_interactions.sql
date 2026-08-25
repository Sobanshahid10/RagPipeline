SELECT
    id,
    tenant_id,
    user_id,
    raw_query,
    route_used,
    ttft_ms,
    total_latency_ms,
    prompt_tokens,
    completion_tokens,
    (prompt_tokens + completion_tokens) AS total_tokens,
    user_feedback,
    created_at::DATE AS query_date,
    created_at
FROM {{ source('rag_raw', 'query_interactions') }}
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
