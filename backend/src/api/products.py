"""
Products API Endpoints

Provides product search and catalog access via mock Merchant API.

AP2 Compliance:
- Merchant provides product data (price, stock, delivery)
- Merchant never accesses payment information
- Clean separation of roles per AP2 specification
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import logging

from ..mocks.merchant_api import search_products, get_product_by_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search")
async def search_products_endpoint(
    query: Optional[str] = Query(None, description="Search keywords"),
    max_price: Optional[float] = Query(None, description="Maximum price in dollars", ge=0),
    category: Optional[str] = Query(None, description="Product category filter")
) -> Dict[str, Any]:
    """
    Search product catalog.

    Query Parameters:
        query: Search terms (matches name/description)
        max_price: Maximum price in dollars
        category: Filter by category (Electronics, Kitchen, Fashion, Home)

    Returns:
        {
            "count": int,
            "products": List[Product]
        }

    Examples:
        GET /api/products/search?query=coffee&max_price=100
        GET /api/products/search?category=Electronics
        GET /api/products/search?query=airpods

    AP2 Compliance:
        Merchant API provides product catalog without payment knowledge.
    """
    logger.info(f"Product search: query='{query}', max_price=${max_price}, category={category}")

    products = search_products(query=query, max_price=max_price, category=category)

    return {
        "count": len(products),
        "products": products
    }


@router.get("/{product_id}")
async def get_product_endpoint(product_id: str) -> Dict[str, Any]:
    """
    Get specific product by ID.

    Path Parameters:
        product_id: Product identifier

    Returns:
        Product details or 404 if not found

    Example:
        GET /api/products/prod_coffee_001
    """
    logger.debug(f"Get product: {product_id}")

    product = get_product_by_id(product_id)

    if not product:
        return {
            "error": "product_not_found",
            "message": f"No product found with ID: {product_id}"
        }

    return product


@router.get("/categories/list")
async def list_categories() -> Dict[str, Any]:
    """
    Get list of available product categories.

    Returns:
        {
            "categories": List[str]
        }
    """
    # Hardcoded from mock catalog
    categories = ["Electronics", "Kitchen", "Fashion", "Home"]

    return {
        "categories": categories
    }
