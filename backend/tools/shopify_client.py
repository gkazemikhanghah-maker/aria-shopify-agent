"""
Shopify Admin API Client for Aria.

Connects to any Shopify store via Admin API.
Always has mock fallback for development/demo without credentials.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ProductVariant:
    id: int
    title: str
    price: str
    sku: str = ""
    available: bool = True
    inventory_quantity: int = 0

@dataclass
class ProductImage:
    id: int
    src: str
    alt: str = ""

@dataclass
class Product:
    id: int
    title: str
    body_html: str
    vendor: str
    product_type: str
    tags: list[str]
    variants: list[ProductVariant]
    images: list[ProductImage]
    handle: str = ""
    status: str = "active"

    @property
    def price_range(self) -> str:
        prices = [float(v.price) for v in self.variants if v.price]
        if not prices:
            return "N/A"
        lo, hi = min(prices), max(prices)
        return f"${lo:.2f}" if lo == hi else f"${lo:.2f} - ${hi:.2f}"

    @property
    def primary_image(self) -> Optional[str]:
        return self.images[0].src if self.images else None

    def to_rag_text(self) -> str:
        """Flatten product into a single text block for embedding."""
        parts = [
            f"Product: {self.title}",
            f"Type: {self.product_type}" if self.product_type else "",
            f"Vendor: {self.vendor}" if self.vendor else "",
            f"Price: {self.price_range}",
            f"Tags: {', '.join(self.tags)}" if self.tags else "",
            f"Description: {_strip_html(self.body_html)}" if self.body_html else "",
        ]
        return "\n".join(p for p in parts if p)


def _strip_html(html: str) -> str:
    """Rough HTML tag removal -- good enough for embeddings."""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Mock data (always available for dev / demo)
# ---------------------------------------------------------------------------

MOCK_PRODUCTS: list[dict] = [
    {
        "id": 1001,
        "title": "Classic Cotton T-Shirt",
        "body_html": "<p>Soft 100% organic cotton tee. Perfect for everyday wear.</p>",
        "vendor": "Aria Basics",
        "product_type": "T-Shirts",
        "tags": ["cotton", "basics", "unisex", "sustainable"],
        "handle": "classic-cotton-tshirt",
        "status": "active",
        "variants": [
            {"id": 2001, "title": "S / White", "price": "29.00", "sku": "CCT-S-W", "inventory_quantity": 42},
            {"id": 2002, "title": "M / White", "price": "29.00", "sku": "CCT-M-W", "inventory_quantity": 38},
            {"id": 2003, "title": "L / White", "price": "29.00", "sku": "CCT-L-W", "inventory_quantity": 25},
            {"id": 2004, "title": "S / Black", "price": "29.00", "sku": "CCT-S-B", "inventory_quantity": 50},
            {"id": 2005, "title": "M / Black", "price": "29.00", "sku": "CCT-M-B", "inventory_quantity": 44},
            {"id": 2006, "title": "L / Black", "price": "29.00", "sku": "CCT-L-B", "inventory_quantity": 30},
        ],
        "images": [
            {"id": 3001, "src": "https://cdn.shopify.com/placeholder/tshirt_white.jpg", "alt": "White cotton tee"},
        ],
    },
    {
        "id": 1002,
        "title": "Slim Fit Chinos",
        "body_html": "<p>Modern slim-fit chinos with stretch fabric. Dress up or down.</p>",
        "vendor": "Aria Basics",
        "product_type": "Pants",
        "tags": ["chinos", "slim-fit", "stretch", "smart-casual"],
        "handle": "slim-fit-chinos",
        "status": "active",
        "variants": [
            {"id": 2010, "title": "30 / Navy", "price": "59.00", "sku": "SFC-30-N", "inventory_quantity": 20},
            {"id": 2011, "title": "32 / Navy", "price": "59.00", "sku": "SFC-32-N", "inventory_quantity": 35},
            {"id": 2012, "title": "34 / Navy", "price": "59.00", "sku": "SFC-34-N", "inventory_quantity": 28},
            {"id": 2013, "title": "32 / Khaki", "price": "59.00", "sku": "SFC-32-K", "inventory_quantity": 15},
            {"id": 2014, "title": "34 / Khaki", "price": "59.00", "sku": "SFC-34-K", "inventory_quantity": 22},
        ],
        "images": [
            {"id": 3002, "src": "https://cdn.shopify.com/placeholder/chinos_navy.jpg", "alt": "Navy slim chinos"},
        ],
    },
    {
        "id": 1003,
        "title": "Merino Wool Sweater",
        "body_html": "<p>Luxurious merino wool crew-neck sweater. Breathable and warm.</p>",
        "vendor": "Aria Premium",
        "product_type": "Sweaters",
        "tags": ["merino", "wool", "premium", "winter"],
        "handle": "merino-wool-sweater",
        "status": "active",
        "variants": [
            {"id": 2020, "title": "M / Charcoal", "price": "89.00", "sku": "MWS-M-C", "inventory_quantity": 18},
            {"id": 2021, "title": "L / Charcoal", "price": "89.00", "sku": "MWS-L-C", "inventory_quantity": 12},
            {"id": 2022, "title": "M / Burgundy", "price": "89.00", "sku": "MWS-M-B", "inventory_quantity": 10},
            {"id": 2023, "title": "L / Burgundy", "price": "89.00", "sku": "MWS-L-B", "inventory_quantity": 8},
        ],
        "images": [
            {"id": 3003, "src": "https://cdn.shopify.com/placeholder/sweater_charcoal.jpg", "alt": "Charcoal merino sweater"},
        ],
    },
    {
        "id": 1004,
        "title": "Canvas Sneakers",
        "body_html": "<p>Minimalist canvas sneakers with vulcanised rubber sole. Light and durable.</p>",
        "vendor": "Aria Footwear",
        "product_type": "Shoes",
        "tags": ["sneakers", "canvas", "minimal", "unisex"],
        "handle": "canvas-sneakers",
        "status": "active",
        "variants": [
            {"id": 2030, "title": "40 / White", "price": "49.00", "sku": "CS-40-W", "inventory_quantity": 30},
            {"id": 2031, "title": "42 / White", "price": "49.00", "sku": "CS-42-W", "inventory_quantity": 25},
            {"id": 2032, "title": "44 / White", "price": "49.00", "sku": "CS-44-W", "inventory_quantity": 20},
            {"id": 2033, "title": "42 / Black", "price": "49.00", "sku": "CS-42-B", "inventory_quantity": 35},
        ],
        "images": [
            {"id": 3004, "src": "https://cdn.shopify.com/placeholder/sneakers_white.jpg", "alt": "White canvas sneakers"},
        ],
    },
    {
        "id": 1005,
        "title": "Leather Crossbody Bag",
        "body_html": "<p>Handcrafted full-grain leather crossbody bag. Fits phone, wallet, keys and more.</p>",
        "vendor": "Aria Accessories",
        "product_type": "Bags",
        "tags": ["leather", "crossbody", "handcrafted", "accessories"],
        "handle": "leather-crossbody-bag",
        "status": "active",
        "variants": [
            {"id": 2040, "title": "Tan", "price": "79.00", "sku": "LCB-TAN", "inventory_quantity": 14},
            {"id": 2041, "title": "Black", "price": "79.00", "sku": "LCB-BLK", "inventory_quantity": 22},
        ],
        "images": [
            {"id": 3005, "src": "https://cdn.shopify.com/placeholder/bag_tan.jpg", "alt": "Tan leather crossbody"},
        ],
    },
    {
        "id": 1006,
        "title": "Recycled Nylon Puffer Jacket",
        "body_html": "<p>Lightweight puffer jacket made from 100% recycled nylon. Water-resistant, packable.</p>",
        "vendor": "Aria Outerwear",
        "product_type": "Jackets",
        "tags": ["puffer", "recycled", "sustainable", "water-resistant", "winter"],
        "handle": "recycled-nylon-puffer",
        "status": "active",
        "variants": [
            {"id": 2050, "title": "S / Olive", "price": "129.00", "sku": "RNP-S-O", "inventory_quantity": 10},
            {"id": 2051, "title": "M / Olive", "price": "129.00", "sku": "RNP-M-O", "inventory_quantity": 16},
            {"id": 2052, "title": "L / Olive", "price": "129.00", "sku": "RNP-L-O", "inventory_quantity": 12},
            {"id": 2053, "title": "M / Black", "price": "129.00", "sku": "RNP-M-B", "inventory_quantity": 20},
            {"id": 2054, "title": "L / Black", "price": "129.00", "sku": "RNP-L-B", "inventory_quantity": 18},
        ],
        "images": [
            {"id": 3006, "src": "https://cdn.shopify.com/placeholder/puffer_olive.jpg", "alt": "Olive recycled puffer"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ShopifyClient:
    """
    Async Shopify Admin API client.

    Usage:
        # Real store
        client = ShopifyClient(
            store_url="aria-demo.myshopify.com",
            access_token="shpat_xxxxx",
        )

        # Mock mode (no credentials needed)
        client = ShopifyClient(use_mock=True)

        products = await client.get_products()
    """

    API_VERSION = "2024-01"

    def __init__(
        self,
        store_url: str = "",
        access_token: str = "",
        use_mock: bool = False,
    ):
        self.use_mock = use_mock or (not store_url and not access_token)

        if self.use_mock:
            logger.info("ShopifyClient running in MOCK mode")
            self.store_url = "mock-store.myshopify.com"
            self.access_token = ""
        else:
            self.store_url = store_url.rstrip("/")
            self.access_token = access_token
            if not self.store_url or not self.access_token:
                raise ValueError("store_url and access_token required for live mode")

        self._base_url = f"https://{self.store_url}/admin/api/{self.API_VERSION}"

    # -- internal helpers ---------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Generic GET against the Admin API."""
        url = f"{self._base_url}/{endpoint}"
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    # -- parsing helpers ----------------------------------------------------

    @staticmethod
    def _parse_product(raw: dict) -> Product:
        variants = [
            ProductVariant(
                id=v["id"],
                title=v.get("title", ""),
                price=v.get("price", "0.00"),
                sku=v.get("sku", ""),
                available=v.get("available", True),
                inventory_quantity=v.get("inventory_quantity", 0),
            )
            for v in raw.get("variants", [])
        ]
        images = [
            ProductImage(
                id=img["id"],
                src=img.get("src", ""),
                alt=img.get("alt", ""),
            )
            for img in raw.get("images", [])
        ]
        return Product(
            id=raw["id"],
            title=raw.get("title", ""),
            body_html=raw.get("body_html", ""),
            vendor=raw.get("vendor", ""),
            product_type=raw.get("product_type", ""),
            tags=[t.strip() for t in raw.get("tags", "").split(",") if t.strip()]
                 if isinstance(raw.get("tags"), str)
                 else raw.get("tags", []),
            handle=raw.get("handle", ""),
            status=raw.get("status", "active"),
            variants=variants,
            images=images,
        )

    # -- public API ---------------------------------------------------------

    async def get_products(self, limit: int = 50) -> list[Product]:
        """Fetch products from Shopify (or mock data)."""
        if self.use_mock:
            logger.info(f"Returning {len(MOCK_PRODUCTS)} mock products")
            return [self._parse_product(p) for p in MOCK_PRODUCTS]

        data = await self._get("products.json", params={"limit": limit, "status": "active"})
        raw_products = data.get("products", [])
        logger.info(f"Fetched {len(raw_products)} products from Shopify")
        return [self._parse_product(p) for p in raw_products]

    async def get_product(self, product_id: int) -> Optional[Product]:
        """Fetch a single product by ID."""
        if self.use_mock:
            for p in MOCK_PRODUCTS:
                if p["id"] == product_id:
                    return self._parse_product(p)
            return None

        try:
            data = await self._get(f"products/{product_id}.json")
            return self._parse_product(data["product"])
        except httpx.HTTPStatusError as e:
            logger.warning(f"Product {product_id} not found: {e}")
            return None

    async def search_products(self, query: str) -> list[Product]:
        """Search products by title (Shopify GraphQL would be better, but REST works)."""
        if self.use_mock:
            q = query.lower()
            return [
                self._parse_product(p)
                for p in MOCK_PRODUCTS
                if q in p["title"].lower()
                or q in p.get("product_type", "").lower()
                or any(q in tag for tag in (p.get("tags", []) if isinstance(p.get("tags"), list) else []))
            ]

        data = await self._get("products.json", params={"title": query, "limit": 20})
        return [self._parse_product(p) for p in data.get("products", [])]

    async def get_collections(self) -> list[dict]:
        """Fetch custom collections."""
        if self.use_mock:
            return [
                {"id": 5001, "title": "Basics", "handle": "basics"},
                {"id": 5002, "title": "Premium", "handle": "premium"},
                {"id": 5003, "title": "Accessories", "handle": "accessories"},
            ]

        data = await self._get("custom_collections.json")
        return data.get("custom_collections", [])

    async def health_check(self) -> dict:
        """Verify connection to the Shopify store."""
        if self.use_mock:
            return {
                "status": "ok",
                "mode": "mock",
                "store": self.store_url,
                "products_available": len(MOCK_PRODUCTS),
            }

        try:
            data = await self._get("shop.json")
            shop = data.get("shop", {})
            return {
                "status": "ok",
                "mode": "live",
                "store": shop.get("name", self.store_url),
                "domain": shop.get("domain", ""),
                "plan": shop.get("plan_display_name", ""),
            }
        except Exception as e:
            return {"status": "error", "mode": "live", "error": str(e)}


# ---------------------------------------------------------------------------
# Factory -- reads from env vars
# ---------------------------------------------------------------------------

def create_shopify_client() -> ShopifyClient:
    """Create a ShopifyClient from environment variables (or mock)."""
    store_url = os.getenv("SHOPIFY_STORE_URL", "")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    use_mock = os.getenv("SHOPIFY_USE_MOCK", "false").lower() in ("true", "1", "yes")

    if use_mock or (not store_url and not access_token):
        return ShopifyClient(use_mock=True)

    return ShopifyClient(store_url=store_url, access_token=access_token)