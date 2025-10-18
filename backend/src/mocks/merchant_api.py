"""
Mock Merchant API

Simulates product catalog for AP2 demonstration.
15 products across 4 categories (Electronics, Kitchen, Fashion, Home).

AP2 Compliance: Merchant role per AP2 specification - provides product data,
never accesses payment information.

Demo Mode: Simulates dynamic price drops 45 seconds after monitoring activation.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Price drop tracking for demo mode
_price_drops: Dict[str, Dict[str, Any]] = {}
# Format: {"product_query_lower": {"target_price_cents": int, "activated_at": datetime}}


@dataclass
class Product:
    """Product data structure."""
    product_id: str
    name: str
    description: str
    category: str
    price_cents: int
    stock_status: str  # "in_stock" or "out_of_stock"
    delivery_estimate_days: int
    image_url: str


# Product catalog - 15 products across 4 categories
PRODUCT_CATALOG: List[Product] = [
    # Electronics (4 products)
    Product(
        product_id="prod_airpods_001",
        name="Apple AirPods Pro",
        description="Active noise cancellation, wireless charging case",
        category="Electronics",
        price_cents=24900,  # $249.00
        stock_status="in_stock",
        delivery_estimate_days=1,
        image_url="https://demo.ghostcart.com/images/airpods-pro.jpg"
    ),
    Product(
        product_id="prod_headphones_001",
        name="Sony WH-1000XM5 Headphones",
        description="Industry-leading noise canceling headphones",
        category="Electronics",
        price_cents=39900,  # $399.00
        stock_status="in_stock",
        delivery_estimate_days=2,
        image_url="https://demo.ghostcart.com/images/sony-headphones.jpg"
    ),
    Product(
        product_id="prod_tablet_001",
        name="Samsung Galaxy Tab S9",
        description="11-inch Android tablet with S Pen",
        category="Electronics",
        price_cents=79900,  # $799.00
        stock_status="out_of_stock",
        delivery_estimate_days=7,
        image_url="https://demo.ghostcart.com/images/samsung-tablet.jpg"
    ),
    Product(
        product_id="prod_watch_001",
        name="Fitbit Charge 6",
        description="Fitness tracker with heart rate monitor",
        category="Electronics",
        price_cents=15999,  # $159.99
        stock_status="in_stock",
        delivery_estimate_days=1,
        image_url="https://demo.ghostcart.com/images/fitbit.jpg"
    ),

    # Kitchen (4 products)
    Product(
        product_id="prod_coffee_001",
        name="Philips HD7462 Coffee Maker",
        description="12-cup programmable coffee maker with timer",
        category="Kitchen",
        price_cents=6900,  # $69.00
        stock_status="in_stock",
        delivery_estimate_days=2,
        image_url="https://demo.ghostcart.com/images/coffee-maker.jpg"
    ),
    Product(
        product_id="prod_blender_001",
        name="Ninja Professional Blender",
        description="1000-watt blender with 72oz pitcher",
        category="Kitchen",
        price_cents=8999,  # $89.99
        stock_status="in_stock",
        delivery_estimate_days=1,
        image_url="https://demo.ghostcart.com/images/blender.jpg"
    ),
    Product(
        product_id="prod_mixer_001",
        name="KitchenAid Stand Mixer",
        description="5-quart tilt-head stand mixer",
        category="Kitchen",
        price_cents=37999,  # $379.99
        stock_status="in_stock",
        delivery_estimate_days=3,
        image_url="https://demo.ghostcart.com/images/mixer.jpg"
    ),
    Product(
        product_id="prod_airfryer_001",
        name="Cosori Air Fryer",
        description="5.8-quart air fryer with 11 presets",
        category="Kitchen",
        price_cents=11999,  # $119.99
        stock_status="out_of_stock",
        delivery_estimate_days=5,
        image_url="https://demo.ghostcart.com/images/airfryer.jpg"
    ),

    # Fashion (4 products)
    Product(
        product_id="prod_sneakers_001",
        name="Nike Air Max 270",
        description="Men's running shoes, size 10",
        category="Fashion",
        price_cents=14999,  # $149.99
        stock_status="in_stock",
        delivery_estimate_days=2,
        image_url="https://demo.ghostcart.com/images/nike-shoes.jpg"
    ),
    Product(
        product_id="prod_jacket_001",
        name="The North Face Fleece Jacket",
        description="Men's full-zip fleece jacket, size L",
        category="Fashion",
        price_cents=9999,  # $99.99
        stock_status="in_stock",
        delivery_estimate_days=1,
        image_url="https://demo.ghostcart.com/images/jacket.jpg"
    ),
    Product(
        product_id="prod_backpack_001",
        name="Herschel Supply Co. Backpack",
        description="Classic backpack with laptop sleeve",
        category="Fashion",
        price_cents=7999,  # $79.99
        stock_status="in_stock",
        delivery_estimate_days=1,
        image_url="https://demo.ghostcart.com/images/backpack.jpg"
    ),
    Product(
        product_id="prod_sunglasses_001",
        name="Ray-Ban Aviator Sunglasses",
        description="Classic metal aviator sunglasses",
        category="Fashion",
        price_cents=15300,  # $153.00
        stock_status="out_of_stock",
        delivery_estimate_days=10,
        image_url="https://demo.ghostcart.com/images/rayban.jpg"
    ),

    # Home (3 products)
    Product(
        product_id="prod_vacuum_001",
        name="Dyson V11 Cordless Vacuum",
        description="Powerful cordless vacuum with LCD screen",
        category="Home",
        price_cents=59999,  # $599.99
        stock_status="in_stock",
        delivery_estimate_days=2,
        image_url="https://demo.ghostcart.com/images/dyson.jpg"
    ),
    Product(
        product_id="prod_sheets_001",
        name="Egyptian Cotton Sheet Set",
        description="Queen size, 800 thread count, white",
        category="Home",
        price_cents=12999,  # $129.99
        stock_status="in_stock",
        delivery_estimate_days=3,
        image_url="https://demo.ghostcart.com/images/sheets.jpg"
    ),
    Product(
        product_id="prod_lamp_001",
        name="Modern LED Desk Lamp",
        description="Adjustable brightness and color temperature",
        category="Home",
        price_cents=4599,  # $45.99
        stock_status="in_stock",
        delivery_estimate_days=1,
        image_url="https://demo.ghostcart.com/images/lamp.jpg"
    ),
]


# ============================================================================
# Demo Mode: Price Drop Simulation
# ============================================================================

def register_price_drop(product_query: str, target_price_cents: int) -> None:
    """
    Register a price drop for demo mode.

    Called when monitoring is activated. After 45 seconds, products matching
    the query will return the target price.

    Args:
        product_query: Product search query from monitoring (e.g., "coffee maker")
        target_price_cents: Target price to drop to (e.g., 5000 for $50)
    """
    query_lower = product_query.lower()
    _price_drops[query_lower] = {
        "target_price_cents": target_price_cents,
        "activated_at": datetime.utcnow()
    }
    logger.info(
        f"📉 DEMO: Price drop registered for '{product_query}' "
        f"to ${target_price_cents/100:.2f} (drops in 45 seconds)"
    )


def _apply_demo_price_drop(product: Product, query: Optional[str]) -> int:
    """
    Apply demo price drop if conditions are met.

    Checks if 45 seconds have passed since price drop registration.
    Returns modified price if drop should be applied.

    Args:
        product: Product to potentially modify price for
        query: Search query being used

    Returns:
        Modified price in cents (or original if no drop applies)
    """
    if not query or not _price_drops:
        return product.price_cents

    query_lower = query.lower()

    # Check if this product matches any registered price drop
    for drop_query, drop_info in _price_drops.items():
        # Match if query contains the drop query OR product name/desc contains drop query
        if (drop_query in query_lower or
            drop_query in product.name.lower() or
            drop_query in product.description.lower()):

            # Check if 45 seconds have passed since activation
            elapsed = (datetime.utcnow() - drop_info["activated_at"]).total_seconds()

            if elapsed >= 10:
                target_price = drop_info["target_price_cents"]
                if product.price_cents > target_price:
                    logger.info(
                        f"💰 DEMO: Price drop applied! {product.name}: "
                        f"${product.price_cents/100:.2f} → ${target_price/100:.2f}"
                    )
                    return target_price

    return product.price_cents


# ============================================================================
# Product Search API
# ============================================================================

def search_products(
    query: Optional[str] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search product catalog by query, price, and category.

    Args:
        query: Search terms (case-insensitive match on name/description)
        max_price: Maximum price in dollars
        category: Filter by category

    Returns:
        List of matching products as dictionaries

    AP2 Compliance: Merchant provides product data only, no payment info.
    Demo Mode: Applies dynamic price drops after 45 seconds.
    """
    results = PRODUCT_CATALOG

    # Filter by search query
    if query:
        query_lower = query.lower()
        results = [
            p for p in results
            if query_lower in p.name.lower() or query_lower in p.description.lower()
        ]

    # Apply demo price drops BEFORE filtering by max_price
    # This allows products to match after price drop
    results_with_price_drops = []
    for p in results:
        modified_price = _apply_demo_price_drop(p, query)
        results_with_price_drops.append((p, modified_price))

    # Filter by max price (using modified prices)
    if max_price is not None:
        max_price_cents = int(max_price * 100)
        results_with_price_drops = [
            (p, price) for p, price in results_with_price_drops
            if price <= max_price_cents
        ]

    # Filter by category
    if category:
        results_with_price_drops = [
            (p, price) for p, price in results_with_price_drops
            if p.category.lower() == category.lower()
        ]

    # Convert to dictionaries with modified prices
    return [
        {
            "product_id": p.product_id,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "price_cents": modified_price,  # Use modified price
            "stock_status": p.stock_status,
            "delivery_estimate_days": p.delivery_estimate_days,
            "image_url": p.image_url
        }
        for p, modified_price in results_with_price_drops
    ]


def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Get specific product by ID."""
    for product in PRODUCT_CATALOG:
        if product.product_id == product_id:
            return {
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price_cents": product.price_cents,
                "stock_status": product.stock_status,
                "delivery_estimate_days": product.delivery_estimate_days,
                "image_url": product.image_url
            }
    return None
