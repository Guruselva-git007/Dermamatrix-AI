"""External product-discovery resolution for the DermaMatrix care catalogue.

This module deliberately resolves *discovery* links only.  It does not infer
medical suitability, invent a retailer's stock, price, rating or affiliate
relationship, or decide the product order.  Suitability remains in the
recommendation service; commerce is evaluated only after that decision.
"""

from __future__ import annotations

import os
from urllib.parse import urlencode, urlparse


GOOGLE_SHOPPING_URL = "https://www.google.com/search"
AMAZON_IN_SEARCH_URL = "https://www.amazon.in/s"
FLIPKART_SEARCH_URL = "https://www.flipkart.com/search"
PHARMACY_PROVIDERS = {
    "tata_1mg": {"name": "Tata 1mg", "search_url": "https://www.1mg.com/search/all", "query_key": "name"},
    "pharmeasy": {"name": "PharmEasy", "search_url": "https://pharmeasy.in/search/all", "query_key": "name"},
}
# Only these existing care categories get pharmacy discovery links. An exact
# user search and unrelated catalogue items never acquire pharmacy actions.
PHARMACY_CATALOG_QUERIES = {
    "barrier-moisturiser": "fragrance free barrier moisturiser",
    "sun-protection": "broad spectrum sunscreen",
    "psoriasis-emollient": "rich fragrance free emollient ointment",
    "salicylic-acid": "salicylic acid skin care product",
    "benzoyl-peroxide": "benzoyl peroxide skin care product",
    "azelaic-acid": "azelaic acid skin care product",
    "ketoconazole-shampoo": "ketoconazole shampoo",
    "selenium-sulfide-shampoo": "selenium sulfide shampoo",
    "zinc-pyrithione-shampoo": "zinc pyrithione shampoo",
    "minoxidil-category": "minoxidil hair loss product",
    "topical-antifungal": "topical antifungal skin product",
    "nail-antifungal": "nail antifungal product",
}


def valid_external_url(value: object) -> str | None:
    """Allow only complete HTTP(S) destinations supplied by configuration."""
    candidate = str(value or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return candidate
    return None


def product_search_query(product: dict) -> str:
    """Use source-controlled product data, never UI labels, for a search query."""
    terms = product.get("search_terms") or product.get("name") or ""
    return " ".join(str(terms).split())


def marketplace_search_url(marketplace: str, query: str) -> str:
    """Build an exact, encoded discovery search for a supported marketplace."""
    if marketplace == "amazon_india":
        return f"{AMAZON_IN_SEARCH_URL}?{urlencode({'k': query})}"
    if marketplace == "flipkart":
        return f"{FLIPKART_SEARCH_URL}?{urlencode({'q': query})}"
    return f"{GOOGLE_SHOPPING_URL}?{urlencode({'tbm': 'shop', 'q': query})}"


def pharmacy_search_url(provider: str, query: str) -> str:
    """Build an encoded search only for a configured external pharmacy."""
    if provider not in PHARMACY_PROVIDERS:
        raise ValueError("Unsupported pharmacy provider")
    normalized = " ".join(str(query or "").split())
    if not normalized:
        raise ValueError("A pharmacy search needs a product name")
    config = PHARMACY_PROVIDERS[provider]
    return f"{config['search_url']}?{urlencode({config['query_key']: normalized})}"


def resolve_product_destination(product: dict) -> dict:
    """Return a safe primary external destination and optional exact searches.

    A configured affiliate URL wins, followed by a configured direct product
    URL.  In their absence, Google Shopping is the neutral default. Amazon and
    Flipkart links are exact search links, not claims that either marketplace
    carries the product and never affiliate links unless an explicit partner
    URL was configured.
    """
    query = product_search_query(product)
    affiliate_url = valid_external_url(product.get("affiliate_url"))
    direct_url = valid_external_url(product.get("product_url"))
    search_destinations = [
        {
            "merchant": "Google Shopping",
            "destination_type": "GOOGLE_SHOPPING_SEARCH",
            "url": marketplace_search_url("google_shopping", query),
            "is_affiliate": False,
        },
        {
            "merchant": "Amazon India",
            "destination_type": "AMAZON_SEARCH",
            "url": marketplace_search_url("amazon_india", query),
            "is_affiliate": False,
        },
        {
            "merchant": "Flipkart",
            "destination_type": "FLIPKART_SEARCH",
            "url": marketplace_search_url("flipkart", query),
            "is_affiliate": False,
        },
    ]
    if affiliate_url:
        primary = {
            "merchant": product.get("merchant") or "Configured partner",
            "destination_type": "AFFILIATE_URL",
            "url": affiliate_url,
            "is_affiliate": True,
        }
    elif direct_url:
        primary = {
            "merchant": product.get("merchant") or "Product page",
            "destination_type": "DIRECT_PRODUCT_URL",
            "url": direct_url,
            "is_affiliate": False,
        }
    else:
        primary = search_destinations[0]

    alternatives = [item for item in search_destinations if item["url"] != primary["url"]]
    return {
        "query": query,
        "primary": primary,
        "alternatives": alternatives,
        "disclosure_required": bool(primary["is_affiliate"]),
    }


def materialize_product(product: dict) -> dict:
    """Expose a UI-safe product record with resolved commerce metadata."""
    affiliate_url = valid_external_url(os.getenv(product.get("affiliate_env", ""), ""))
    direct_url = valid_external_url(os.getenv(product.get("product_url_env", ""), ""))
    record = {
        key: value for key, value in product.items()
        if key not in {"affiliate_env", "product_url_env"}
    }
    record["affiliate_url"] = affiliate_url
    record["product_url"] = direct_url
    # Catalogue entries are often care categories rather than a verified retail
    # SKU.  A real image is exposed only when a source-controlled, HTTPS image
    # URL is explicitly configured; otherwise the client uses an honest category
    # illustration rather than impersonating a brand or product package.
    image = product.get("image") if isinstance(product.get("image"), dict) else {}
    image_url = valid_external_url(image.get("src") or product.get("image_url"))
    record["image"] = {
        "src": image_url,
        "alt": str(image.get("alt") or product.get("image_alt") or product.get("name") or "Care product"),
    } if image_url else None
    record["commerce"] = resolve_product_destination(record)
    pharmacy_query = product.get("pharmacy_query") or PHARMACY_CATALOG_QUERIES.get(product.get("id"))
    if pharmacy_query:
        record["pharmacy_links"] = [
            {"provider": provider, "name": config["name"], "url": pharmacy_search_url(provider, pharmacy_query)}
            for provider, config in PHARMACY_PROVIDERS.items()
        ]
    # Kept for older clients that only understand a single external link.
    record["url"] = record["commerce"]["primary"]["url"]
    return record
