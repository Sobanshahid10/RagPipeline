SELECT
    id,
    interaction_id,
    context_recall,
    context_precision,
    faithfulness,
    answer_relevancy,
    hallucination_detected,
    evaluated_at::DATE AS eval_date,
    evaluated_at
FROM {{ source('rag_raw', 'eval_scores') }}
WHERE evaluated_at >= CURRENT_DATE - INTERVAL '90 days'
