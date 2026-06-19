import logging

logger = logging.getLogger("retrieval.hybrid_merge")

def reciprocal_rank_fusion_many(
    ranked_lists: list[list[dict]],
    k: int = 60
) -> list[dict]:
    """Merge ranked job result lists using Reciprocal Rank Fusion (RRF)."""

    logger.debug("Performing Reciprocal Rank Fusion over %d lists", len(ranked_lists))
    scores = {}
    docs = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
            docs[doc_id] = doc

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    merged = []
    for doc_id in sorted_ids:
        doc = docs[doc_id].copy()
        doc["rrf_score"] = scores[doc_id]
        merged.append(doc)
    
    logger.debug("RRF merged results count: %d", len(merged))
    return merged


def reciprocal_rank_fusion(
    fts_results: list[dict],
    vector_results: list[dict],
    k: int = 60
) -> list[dict]:
    """Merge FTS and vector ranked lists using RRF."""

    return reciprocal_rank_fusion_many(
        [fts_results, vector_results],
        k=k,
    )
