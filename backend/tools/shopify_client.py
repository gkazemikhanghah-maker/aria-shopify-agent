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
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Mock data — Fashion + Beauty + Tech + Home
# ---------------------------------------------------------------------------

MOCK_PRODUCTS: list[dict] = [
    # === FASHION ===
    {
        "id": 1001,
        "title": "Classic Cotton T-Shirt",
        "body_html": "<p>Soft 100% organic cotton tee. Perfect for everyday wear. Relaxed fit, pre-shrunk fabric.</p>",
        "vendor": "Aria Basics",
        "product_type": "T-Shirts",
        "tags": ["cotton", "basics", "unisex", "sustainable", "fashion"],
        "handle": "classic-cotton-tshirt",
        "status": "active",
        "variants": [
            {"id": 2001, "title": "S / White", "price": "29.00", "sku": "CCT-S-W", "inventory_quantity": 42},
            {"id": 2002, "title": "M / White", "price": "29.00", "sku": "CCT-M-W", "inventory_quantity": 38},
            {"id": 2003, "title": "L / White", "price": "29.00", "sku": "CCT-L-W", "inventory_quantity": 25},
            {"id": 2004, "title": "S / Black", "price": "29.00", "sku": "CCT-S-B", "inventory_quantity": 50},
            {"id": 2005, "title": "M / Black", "price": "29.00", "sku": "CCT-M-B", "inventory_quantity": 44},
        ],
        "images": [{"id": 3001, "src": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400", "alt": "White cotton tee"}],
    },
    {
        "id": 1002,
        "title": "Slim Fit Chinos",
        "body_html": "<p>Modern slim-fit chinos with 2% stretch fabric. Dress up or down. Wrinkle-resistant.</p>",
        "vendor": "Aria Basics",
        "product_type": "Pants",
        "tags": ["chinos", "slim-fit", "stretch", "smart-casual", "fashion"],
        "handle": "slim-fit-chinos",
        "status": "active",
        "variants": [
            {"id": 2010, "title": "30 / Navy", "price": "59.00", "sku": "SFC-30-N", "inventory_quantity": 20},
            {"id": 2011, "title": "32 / Navy", "price": "59.00", "sku": "SFC-32-N", "inventory_quantity": 35},
            {"id": 2012, "title": "34 / Navy", "price": "59.00", "sku": "SFC-34-N", "inventory_quantity": 28},
            {"id": 2013, "title": "32 / Khaki", "price": "59.00", "sku": "SFC-32-K", "inventory_quantity": 15},
        ],
        "images": [{"id": 3002, "src": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400", "alt": "Navy slim chinos"}],
    },
    {
        "id": 1003,
        "title": "Merino Wool Sweater",
        "body_html": "<p>Luxurious merino wool crew-neck sweater. Breathable, warm, and itch-free. Perfect for layering.</p>",
        "vendor": "Aria Premium",
        "product_type": "Sweaters",
        "tags": ["merino", "wool", "premium", "winter", "fashion"],
        "handle": "merino-wool-sweater",
        "status": "active",
        "variants": [
            {"id": 2020, "title": "M / Charcoal", "price": "89.00", "sku": "MWS-M-C", "inventory_quantity": 18},
            {"id": 2021, "title": "L / Charcoal", "price": "89.00", "sku": "MWS-L-C", "inventory_quantity": 12},
            {"id": 2022, "title": "M / Burgundy", "price": "89.00", "sku": "MWS-M-B", "inventory_quantity": 10},
        ],
        "images": [{"id": 3003, "src": "https://images.unsplash.com/photo-1434389677669-e08b4cda3a43?w=400", "alt": "Charcoal merino sweater"}],
    },
    {
        "id": 1004,
        "title": "Canvas Sneakers",
        "body_html": "<p>Minimalist canvas sneakers with vulcanised rubber sole. Light, durable, and versatile.</p>",
        "vendor": "Aria Footwear",
        "product_type": "Shoes",
        "tags": ["sneakers", "canvas", "minimal", "unisex", "fashion"],
        "handle": "canvas-sneakers",
        "status": "active",
        "variants": [
            {"id": 2030, "title": "40 / White", "price": "49.00", "sku": "CS-40-W", "inventory_quantity": 30},
            {"id": 2031, "title": "42 / White", "price": "49.00", "sku": "CS-42-W", "inventory_quantity": 25},
            {"id": 2032, "title": "44 / White", "price": "49.00", "sku": "CS-44-W", "inventory_quantity": 20},
        ],
        "images": [{"id": 3004, "src": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=400", "alt": "White canvas sneakers"}],
    },
    {
        "id": 1005,
        "title": "Leather Crossbody Bag",
        "body_html": "<p>Handcrafted full-grain leather crossbody bag. Fits phone, wallet, keys and more. Adjustable strap.</p>",
        "vendor": "Aria Accessories",
        "product_type": "Bags",
        "tags": ["leather", "crossbody", "handcrafted", "accessories", "fashion"],
        "handle": "leather-crossbody-bag",
        "status": "active",
        "variants": [
            {"id": 2040, "title": "Tan", "price": "79.00", "sku": "LCB-TAN", "inventory_quantity": 14},
            {"id": 2041, "title": "Black", "price": "79.00", "sku": "LCB-BLK", "inventory_quantity": 22},
        ],
        "images": [{"id": 3005, "src": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400", "alt": "Tan leather crossbody"}],
    },
    {
        "id": 1006,
        "title": "Recycled Nylon Puffer Jacket",
        "body_html": "<p>Lightweight puffer jacket made from 100% recycled nylon. Water-resistant, packable, warm.</p>",
        "vendor": "Aria Outerwear",
        "product_type": "Jackets",
        "tags": ["puffer", "recycled", "sustainable", "water-resistant", "winter", "fashion"],
        "handle": "recycled-nylon-puffer",
        "status": "active",
        "variants": [
            {"id": 2050, "title": "S / Olive", "price": "129.00", "sku": "RNP-S-O", "inventory_quantity": 10},
            {"id": 2051, "title": "M / Olive", "price": "129.00", "sku": "RNP-M-O", "inventory_quantity": 16},
            {"id": 2052, "title": "L / Olive", "price": "129.00", "sku": "RNP-L-O", "inventory_quantity": 12},
        ],
        "images": [{"id": 3006, "src": "https://images.unsplash.com/photo-1544923246-77307dd270b1?w=400", "alt": "Olive recycled puffer"}],
    },

    # === BEAUTY & SKINCARE ===
    {
        "id": 2001,
        "title": "Hydrating Ceramide Moisturizer",
        "body_html": "<p>Lightweight daily moisturizer with ceramides and hyaluronic acid. Fragrance-free, non-comedogenic. Perfect for sensitive and combination skin.</p>",
        "vendor": "Aria Beauty",
        "product_type": "Moisturizer",
        "tags": ["skincare", "moisturizer", "ceramides", "hyaluronic-acid", "sensitive-skin", "beauty"],
        "handle": "hydrating-ceramide-moisturizer",
        "status": "active",
        "variants": [
            {"id": 3050, "title": "50ml", "price": "34.00", "sku": "HCM-50", "inventory_quantity": 60},
            {"id": 3051, "title": "100ml", "price": "54.00", "sku": "HCM-100", "inventory_quantity": 35},
        ],
        "images": [{"id": 4001, "src": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=400", "alt": "Ceramide moisturizer"}],
    },
    {
        "id": 2002,
        "title": "Vitamin C Brightening Serum",
        "body_html": "<p>20% Vitamin C serum with ferulic acid and vitamin E. Targets dark spots, uneven tone, and fine lines. Use with SPF.</p>",
        "vendor": "Aria Beauty",
        "product_type": "Serum",
        "tags": ["skincare", "serum", "vitamin-c", "brightening", "anti-aging", "beauty"],
        "handle": "vitamin-c-brightening-serum",
        "status": "active",
        "variants": [
            {"id": 3060, "title": "30ml", "price": "42.00", "sku": "VCS-30", "inventory_quantity": 45},
        ],
        "images": [{"id": 4002, "src": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400", "alt": "Vitamin C serum"}],
    },
    {
        "id": 2003,
        "title": "Gentle Foaming Cleanser",
        "body_html": "<p>pH-balanced gentle foaming cleanser. Removes makeup and impurities without stripping. With green tea extract and aloe vera.</p>",
        "vendor": "Aria Beauty",
        "product_type": "Cleanser",
        "tags": ["skincare", "cleanser", "gentle", "foaming", "green-tea", "beauty"],
        "handle": "gentle-foaming-cleanser",
        "status": "active",
        "variants": [
            {"id": 3070, "title": "150ml", "price": "24.00", "sku": "GFC-150", "inventory_quantity": 80},
        ],
        "images": [{"id": 4003, "src": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400", "alt": "Foaming cleanser"}],
    },
    {
        "id": 2004,
        "title": "SPF 50 Daily Sunscreen",
        "body_html": "<p>Broad spectrum SPF 50 sunscreen. Lightweight, no white cast, works under makeup. With niacinamide for extra skin benefits.</p>",
        "vendor": "Aria Beauty",
        "product_type": "Sunscreen",
        "tags": ["skincare", "sunscreen", "spf50", "niacinamide", "daily", "beauty"],
        "handle": "spf-50-daily-sunscreen",
        "status": "active",
        "variants": [
            {"id": 3080, "title": "50ml", "price": "28.00", "sku": "SPF-50", "inventory_quantity": 55},
        ],
        "images": [{"id": 4004, "src": "https://images.unsplash.com/photo-1532947974358-a218d18d8d24?w=400", "alt": "SPF 50 sunscreen"}],
    },

    # === TECH ===
    {
        "id": 3001,
        "title": "Wireless Noise-Cancelling Headphones",
        "body_html": "<p>Premium over-ear headphones with active noise cancellation. 30-hour battery, USB-C fast charge, Bluetooth 5.3. Foldable design.</p>",
        "vendor": "Aria Tech",
        "product_type": "Headphones",
        "tags": ["tech", "headphones", "noise-cancelling", "wireless", "bluetooth"],
        "handle": "wireless-nc-headphones",
        "status": "active",
        "variants": [
            {"id": 4050, "title": "Matte Black", "price": "149.00", "sku": "WNC-BLK", "inventory_quantity": 22},
            {"id": 4051, "title": "Sand", "price": "149.00", "sku": "WNC-SND", "inventory_quantity": 18},
        ],
        "images": [{"id": 5001, "src": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400", "alt": "Wireless headphones"}],
    },
    {
        "id": 3002,
        "title": "Portable Bluetooth Speaker",
        "body_html": "<p>Compact waterproof speaker with 360-degree sound. 12-hour battery, IP67 rated, pairs with up to 2 devices.</p>",
        "vendor": "Aria Tech",
        "product_type": "Speaker",
        "tags": ["tech", "speaker", "bluetooth", "waterproof", "portable"],
        "handle": "portable-bluetooth-speaker",
        "status": "active",
        "variants": [
            {"id": 4060, "title": "Midnight Blue", "price": "69.00", "sku": "PBS-BLU", "inventory_quantity": 30},
            {"id": 4061, "title": "Coral", "price": "69.00", "sku": "PBS-CRL", "inventory_quantity": 25},
        ],
        "images": [{"id": 5002, "src": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400", "alt": "Bluetooth speaker"}],
    },

    # === HOME ===
    {
        "id": 4001,
        "title": "Linen Throw Blanket",
        "body_html": "<p>Stonewashed linen throw blanket. Naturally breathable, gets softer with every wash. 140x200cm.</p>",
        "vendor": "Aria Home",
        "product_type": "Blanket",
        "tags": ["home", "linen", "throw", "cozy", "natural"],
        "handle": "linen-throw-blanket",
        "status": "active",
        "variants": [
            {"id": 5050, "title": "Oatmeal", "price": "68.00", "sku": "LTB-OAT", "inventory_quantity": 20},
            {"id": 5051, "title": "Sage", "price": "68.00", "sku": "LTB-SAG", "inventory_quantity": 15},
        ],
        "images": [{"id": 6001, "src": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400", "alt": "Linen throw blanket"}],
    },
    {
        "id": 4002,
        "title": "Ceramic Scented Candle",
        "body_html": "<p>Hand-poured soy wax candle in a reusable ceramic vessel. 45-hour burn time. Notes of cedar, vanilla, and amber.</p>",
        "vendor": "Aria Home",
        "product_type": "Candle",
        "tags": ["home", "candle", "scented", "ceramic", "cozy", "gift"],
        "handle": "ceramic-scented-candle",
        "status": "active",
        "variants": [
            {"id": 5060, "title": "Cedar & Vanilla", "price": "38.00", "sku": "CSC-CV", "inventory_quantity": 40},
            {"id": 5061, "title": "Lavender & Sage", "price": "38.00", "sku": "CSC-LS", "inventory_quantity": 35},
        ],
        "images": [{"id": 6002, "src": "https://images.unsplash.com/photo-1602028915047-37269d1a73f7?w=400", "alt": "Ceramic scented candle"}],
    },
]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ShopifyClient:
    API_VERSION = "2024-01"

    def __init__(self, store_url: str = "", access_token: str = "", use_mock: bool = False):
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

    def _headers(self) -> dict[str, str]:
        return {"X-Shopify-Access-Token": self.access_token, "Content-Type": "application/json"}

    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}/{endpoint}"
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _parse_product(raw: dict) -> Product:
        variants = [
            ProductVariant(
                id=v["id"], title=v.get("title", ""), price=v.get("price", "0.00"),
                sku=v.get("sku", ""), available=v.get("available", True),
                inventory_quantity=v.get("inventory_quantity", 0),
            ) for v in raw.get("variants", [])
        ]
        images = [
            ProductImage(id=img["id"], src=img.get("src", ""), alt=img.get("alt", ""))
            for img in raw.get("images", [])
        ]
        return Product(
            id=raw["id"], title=raw.get("title", ""), body_html=raw.get("body_html", ""),
            vendor=raw.get("vendor", ""), product_type=raw.get("product_type", ""),
            tags=[t.strip() for t in raw.get("tags", "").split(",") if t.strip()]
                 if isinstance(raw.get("tags"), str) else raw.get("tags", []),
            handle=raw.get("handle", ""), status=raw.get("status", "active"),
            variants=variants, images=images,
        )

    async def get_products(self, limit: int = 50) -> list[Product]:
        if self.use_mock:
            return [self._parse_product(p) for p in MOCK_PRODUCTS]
        data = await self._get("products.json", params={"limit": limit, "status": "active"})
        return [self._parse_product(p) for p in data.get("products", [])]

    async def get_product(self, product_id: int) -> Optional[Product]:
        if self.use_mock:
            for p in MOCK_PRODUCTS:
                if p["id"] == product_id:
                    return self._parse_product(p)
            return None
        try:
            data = await self._get(f"products/{product_id}.json")
            return self._parse_product(data["product"])
        except httpx.HTTPStatusError:
            return None

    async def search_products(self, query: str) -> list[Product]:
        if self.use_mock:
            q = query.lower()
            return [
                self._parse_product(p) for p in MOCK_PRODUCTS
                if q in p["title"].lower() or q in p.get("product_type", "").lower()
                or any(q in tag for tag in (p.get("tags", []) if isinstance(p.get("tags"), list) else []))
            ]
        data = await self._get("products.json", params={"title": query, "limit": 20})
        return [self._parse_product(p) for p in data.get("products", [])]

    async def get_collections(self) -> list[dict]:
        if self.use_mock:
            return [
                {"id": 5001, "title": "Fashion", "handle": "fashion"},
                {"id": 5002, "title": "Beauty & Skincare", "handle": "beauty"},
                {"id": 5003, "title": "Tech", "handle": "tech"},
                {"id": 5004, "title": "Home", "handle": "home"},
            ]
        data = await self._get("custom_collections.json")
        return data.get("custom_collections", [])

    async def health_check(self) -> dict:
        if self.use_mock:
            return {"status": "ok", "mode": "mock", "store": self.store_url, "products_available": len(MOCK_PRODUCTS)}
        try:
            data = await self._get("shop.json")
            shop = data.get("shop", {})
            return {"status": "ok", "mode": "live", "store": shop.get("name", self.store_url)}
        except Exception as e:
            return {"status": "error", "mode": "live", "error": str(e)}


def create_shopify_client() -> ShopifyClient:
    store_url = os.getenv("SHOPIFY_STORE_URL", "")
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    use_mock = os.getenv("SHOPIFY_USE_MOCK", "false").lower() in ("true", "1", "yes")
    if use_mock or (not store_url and not access_token):
        return ShopifyClient(use_mock=True)
    return ShopifyClient(store_url=store_url, access_token=access_token)