"""
Vector Store — Product catalog search.

In deployment (mock mode): uses keyword matching instead of embeddings.
Locally with Qdrant: uses sentence-transformers for semantic search.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

COLLECTION_NAME = "aria_products"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Try to import qdrant and sentence-transformers, but don't fail if missing
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, PointStruct, VectorParams,
        Filter, FieldCondition, MatchValue,
    )
    from sentence_transformers import SentenceTransformer
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    logger.info("Qdrant/sentence-transformers not available, using keyword search")

from tools.shopify_client import Product, ShopifyClient


class VectorStore:
    def __init__(
        self,
        url: str = "http://localhost:6333",
        use_mock: bool = False,
    ):
        self.use_mock = use_mock or not HAS_QDRANT

        if self.use_mock:
            logger.info("VectorStore running in MOCK mode (keyword search)")
            self.client = None
            self._products: list[dict] = []
            self._model = None
        else:
            logger.info(f"VectorStore connecting to Qdrant at {url}")
            self.client = QdrantClient(url=url)
            self._model = None

    @property
    def model(self):
        if self._model is None and HAS_QDRANT:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        return self._model

    def _ensure_collection(self) -> None:
        if self.use_mock:
            return
        collections = [c.name for c in self.client.get_collections().collections]
        if COLLECTION_NAME in collections:
            return
        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Created collection '{COLLECTION_NAME}'")

    def delete_collection(self) -> None:
        if not self.use_mock:
            self.client.delete_collection(collection_name=COLLECTION_NAME)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, show_progress_bar=False)
        return vectors.tolist()

    async def load_products(self, shopify_client: ShopifyClient) -> int:
        products = await shopify_client.get_products(limit=250)
        if not products:
            return 0

        if self.use_mock:
            # Store products for keyword search
            self._products = []
            for p in products:
                self._products.append({
                    "product_id": p.id,
                    "title": p.title,
                    "product_type": p.product_type,
                    "vendor": p.vendor,
                    "price_range": p.price_range,
                    "tags": p.tags,
                    "image_url": p.primary_image or "",
                    "handle": p.handle,
                    "rag_text": p.to_rag_text(),
                })
            logger.info(f"Loaded {len(self._products)} products (keyword mode)")
            return len(self._products)

        # Full vector mode
        rag_texts = [p.to_rag_text() for p in products]
        vectors = self._embed(rag_texts)
        self._ensure_collection()

        points = []
        for i, product in enumerate(products):
            payload = {
                "product_id": product.id,
                "title": product.title,
                "product_type": product.product_type,
                "vendor": product.vendor,
                "price_range": product.price_range,
                "tags": product.tags,
                "image_url": product.primary_image or "",
                "handle": product.handle,
                "rag_text": rag_texts[i],
            }
            points.append(PointStruct(id=i, vector=vectors[i], payload=payload))

        self.client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"Loaded {len(points)} products into Qdrant")
        return len(points)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        product_type: Optional[str] = None,
    ) -> list[dict]:
        if self.use_mock:
            return self._keyword_search(query, top_k, product_type)

        query_vector = self._embed([query])[0]
        search_filter = None
        if product_type:
            search_filter = Filter(
                must=[FieldCondition(key="product_type", match=MatchValue(value=product_type))]
            )

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k,
        ).points

        formatted = []
        for hit in results:
            formatted.append({
                "score": hit.score,
                "product_id": hit.payload.get("product_id"),
                "title": hit.payload.get("title"),
                "product_type": hit.payload.get("product_type"),
                "vendor": hit.payload.get("vendor"),
                "price_range": hit.payload.get("price_range"),
                "tags": hit.payload.get("tags", []),
                "image_url": hit.payload.get("image_url", ""),
                "handle": hit.payload.get("handle", ""),
            })
        return formatted

    def _keyword_search(
        self, query: str, top_k: int, product_type: Optional[str] = None
    ) -> list[dict]:
        """Simple keyword matching for deployment without Qdrant."""
        q = query.lower()
        scored = []

        for p in self._products:
            if product_type and p.get("product_type") != product_type:
                continue

            score = 0.0
            text = p.get("rag_text", "").lower()
            title = p.get("title", "").lower()
            tags = [t.lower() for t in p.get("tags", [])]

            # Score based on keyword matches
            words = q.split()
            for word in words:
                if word in title:
                    score += 0.4
                if word in text:
                    score += 0.2
                if any(word in tag for tag in tags):
                    score += 0.3

            if score > 0:
                result = {**p, "score": min(score, 1.0)}
                scored.append(result)

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)

        # If no matches, return top products with low score
        if not scored:
            scored = [{**p, "score": 0.1} for p in self._products[:top_k]]

        return scored[:top_k]

    def get_stats(self) -> dict:
        if self.use_mock:
            return {
                "status": "ok",
                "collection": "mock",
                "points_count": len(self._products),
                "embedding_model": "keyword",
                "embedding_dim": 0,
            }
        try:
            info = self.client.get_collection(collection_name=COLLECTION_NAME)
            return {
                "status": "ok",
                "collection": COLLECTION_NAME,
                "points_count": info.points_count,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dim": EMBEDDING_DIM,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}