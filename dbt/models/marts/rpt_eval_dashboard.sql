SELECT
    s.eval_date,
    COUNT(s.id) AS total_evaluations,
    AVG(s.faithfulness) AS avg_faithfulness,
    AVG(s.answer_relevancy) AS avg_answer_relevancy,
    AVG(s.context_precision) AS avg_context_precision,
    AVG(s.context_recall) AS avg_context_recall,
    COUNT(CASE WHEN s.hallucination_detected = TRUE THEN 1 END)::FLOAT / NULLIF(COUNT(s.id), 0) AS hallucination_rate,
    AVG(q.ttft_ms) AS avg_ttft_ms
FROM {{ ref('stg_eval_scores') }} s
LEFT JOIN {{ ref('stg_query_interactions') }} q ON s.interaction_id = q.id
GROUP BY 1
ORDER BY 1 DESC
