import hashlib
import logging
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import settings

logger = logging.getLogger(__name__)

VECTOR_SIZE = 384        # sentence-transformers/multi-qa-MiniLM-L6-cos-v1
COLLECTION = settings.qdrant_collection


def _point_id(pr_number: int, repo: str) -> int:
    key = f"{repo}:{pr_number}"
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)


class QdrantService:
    """Manages only vector embeddings for similarity search."""

    def __init__(self):
        kwargs = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        self.client = QdrantClient(**kwargs)

    async def ensure_collection(self):
        try:
            self.client.get_collection(COLLECTION)
        except Exception:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=qm.VectorParams(size=VECTOR_SIZE, distance=qm.Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection '{COLLECTION}'")

    async def store_embedding(self, pr_number: int, repo: str, embedding: List[float]) -> None:
        if not embedding or len(embedding) != VECTOR_SIZE:
            return
        self.client.upsert(
            collection_name=COLLECTION,
            points=[qm.PointStruct(
                id=_point_id(pr_number, repo),
                vector=embedding,
                payload={"pr_number": pr_number, "repo": repo},
            )],
        )

    async def search_similar_prs(
        self,
        embedding: List[float],
        repo: str,
        exclude_id: int,
        threshold: float = 0.88,
        limit: int = 5,
    ) -> List[int]:
        if not embedding or len(embedding) != VECTOR_SIZE:
            return []
        try:
            hits = self.client.search(
                collection_name=COLLECTION,
                query_vector=embedding,
                query_filter=qm.Filter(must=[
                    qm.FieldCondition(key="repo", match=qm.MatchValue(value=repo))
                ]),
                limit=limit + 1,
                score_threshold=threshold,
            )
            return [
                h.payload["pr_number"]
                for h in hits
                if h.payload.get("pr_number") != exclude_id
            ][:limit]
        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
            return []
