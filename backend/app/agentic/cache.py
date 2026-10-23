"""Answer cache intentionally disabled until scoped provenance is implemented."""


class SemanticCache:
    def __init__(self, redis_client=None, threshold=0.96):
        self.redis_client = redis_client
        self.threshold = threshold

    async def get(self, query_embedding):
        return None

    async def set(self, query, embedding, answer, ttl=3600):
        raise RuntimeError(
            "Answer caching is disabled pending tenant, permission, model and corpus scope support"
        )
