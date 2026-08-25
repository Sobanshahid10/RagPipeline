SELECT
    query_date,
    COUNT(*) AS total_queries,
    AVG(ttft_ms) AS avg_ttft_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ttft_ms) AS p50_ttft_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ttft_ms) AS p95_ttft_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ttft_ms) AS p99_ttft_ms,
    SUM(total_tokens) AS total_tokens,
    COUNT(CASE WHEN user_feedback = 1 THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) AS thumbs_up_rate,
    COUNT(CASE WHEN route_used = 'cache' THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) AS cache_hit_rate,
    COUNT(CASE WHEN route_used = 'MULTI_HOP_GRAPH' THEN 1 END) AS graph_route_count
FROM {{ ref('stg_query_interactions') }}
GROUP BY 1
ORDER BY 1 DESC
