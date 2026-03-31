"""
Vector Store — Embeds product catalog into Qdrant for semantic search.

Uses sentence-transformers for embedding and Qdrant for storage/search.
Supports mock mode for development without Qdrant running.
"""

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

from tools.shopify_client import Product, ShopifyClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

COLLECTION_NAME = "aria_products"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, 384-dim, good quality
EMBEDDING_DIM = 384


# ---------------------------------------------------------------------------
# Vector Store
# ---------------------------------------------------------------------------

class VectorStore:
    """
    Manages product embeddings in Qdrant.

    Usage:
        store = VectorStore()                         # connects to localhost
        store = VectorStore(url="http://qdrant:6333") # custom URL
        store = VectorStore(use_mock=True)             # in-memory, no server

        await store.load_products(shopify_client)      # embed & store catalog
        results = await store.search("warm winter jacket", top_k=3)
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        use_mock: bool = False,
    ):
        self.use_mock = use_mock

        # Qdrant client
        if use_mock:
            logger.info("VectorStore running in MOCK mode (in-memory)")
            self.client = QdrantClient(location=":memory:")
        else:
            logger.info(f"VectorStore connecting to Qdrant at {url}")
            self.client = QdrantClient(url=url)

        # Embedding model (lazy load on first use)
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model (takes a few seconds first time)."""
        if self._model is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        return self._model

    # -- Collection management ----------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]

        if COLLECTION_NAME in collections:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists")
            return

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created collection '{COLLECTION_NAME}'")

    def delete_collection(self) -> None:
        """Delete the collection (useful for reloading)."""
        self.client.delete_collection(collection_name=COLLECTION_NAME)
        logger.info(f"Deleted collection '{COLLECTION_NAME}'")

    # -- Embedding ----------------------------------------------------------

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors."""
        vectors = self.model.encode(texts, show_progress_bar=False)
        return vectors.tolist()

    # -- Load products ------------------------------------------------------

    async def load_products(self, shopify_client: ShopifyClient) -> int:
        """
        Fetch all products from Shopify and load into Qdrant.
        Returns number of products loaded.
        """
        # 1. Fetch products
        products = await shopify_client.get_products(limit=250)
        if not products:
            logger.warning("No products found to load")
            return 0

        logger.info(f"Embedding {len(products)} products...")

        # 2. Create RAG texts and embed
        rag_texts = [p.to_rag_text() for p in products]
        vectors = self._embed(rag_texts)

        # 3. Ensure collection exists
        self._ensure_collection()

        # 4. Build points with metadata
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
            points.append(
                PointStruct(id=i, vector=vectors[i], payload=payload)
            )

        # 5. Upsert into Qdrant
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

        logger.info(f"Loaded {len(points)} products into Qdrant")
        return len(points)

    # -- Search -------------------------------------------------------------

    async def search(
        self,
        query: str,
        top_k: int = 5,
        product_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic search across the product catalog.

        Args:
            query: Natural language search (e.g. "warm jacket for winter")
            top_k: Number of results to return
            product_type: Optional filter by product type

        Returns:
            List of dicts with product info + relevance score
        """
        # Embed query
        query_vector = self._embed([query])[0]

        # Optional filter
        search_filter = None
        if product_type:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="product_type",
                        match=MatchValue(value=product_type),
                    )
                ]
            )

        # Search
        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k,
        ).points

        # Format results
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

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get collection statistics."""
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