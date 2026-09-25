"""Pharmacy handoff stays a source-controlled discovery action."""

from __future__ import annotations

import os
import sys
import unittest
from urllib.parse import parse_qs, urlparse


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from commerce_service import materialize_product, pharmacy_search_url
from recommendation_service import catalog_for_area, product_discovery_catalog, search_product_discovery


class PharmacyLinkTests(unittest.TestCase):
    def test_verified_provider_urls_encode_full_medicine_names(self):
        names = [
            "Adapalene 0.1% Gel",
            "Ketoconazole 2% Shampoo",
            "Clindamycin + Nicotinamide Gel",
            "Care / Skin (day-night) + 2%",
        ]
        for provider, host in (("tata_1mg", "www.1mg.com"), ("pharmeasy", "pharmeasy.in")):
            for name in names:
                with self.subTest(provider=provider, name=name):
                    url = pharmacy_search_url(provider, name)
                    parsed = urlparse(url)
                    self.assertEqual(parsed.scheme, "https")
                    self.assertEqual(parsed.netloc, host)
                    self.assertEqual(parsed.path, "/search/all")
                    self.assertEqual(parse_qs(parsed.query), {"name": [name]})
        encoded = pharmacy_search_url("tata_1mg", names[-1])
        for token in ("%2F", "%28", "%29", "%2B", "%25", "day-night"):
            self.assertIn(token, encoded)

    def test_provider_and_query_must_be_explicit(self):
        with self.assertRaises(ValueError):
            pharmacy_search_url("untrusted", "Adapalene Gel")
        with self.assertRaises(ValueError):
            pharmacy_search_url("tata_1mg", "  ")

    def test_relevant_existing_categories_get_pharmacy_actions(self):
        catalog = {item["id"]: item for item in product_discovery_catalog()}
        for product_id in ("barrier-moisturiser", "sun-protection", "ketoconazole-shampoo", "topical-antifungal", "nail-antifungal"):
            with self.subTest(product=product_id):
                links = catalog[product_id]["pharmacy_links"]
                self.assertEqual([item["name"] for item in links], ["Tata 1mg", "PharmEasy"])
                self.assertTrue(all(item["url"].startswith("https://") for item in links))
                self.assertFalse(catalog[product_id].get("is_medicine", False))

    def test_irrelevant_and_user_entered_categories_do_not_gain_pharmacy_actions(self):
        catalog = {item["id"]: item for item in product_discovery_catalog()}
        for product_id in ("protective-gloves", "nail-clippers", "breathable-socks"):
            self.assertNotIn("pharmacy_links", catalog[product_id])
        exact_search = search_product_discovery("Adapalene 0.1% Gel")[0]
        self.assertEqual(exact_search["id"], "exact-user-search")
        self.assertNotIn("pharmacy_links", exact_search)
        self.assertFalse(exact_search["commerce"]["primary"]["is_affiliate"])

    def test_existing_marketplaces_and_assessment_products_stay_available(self):
        for area in ("Skin", "Hair", "Nails"):
            for product in catalog_for_area(area):
                destinations = [product["commerce"]["primary"], *product["commerce"]["alternatives"]]
                kinds = {item["destination_type"] for item in destinations}
                self.assertIn("AMAZON_SEARCH", kinds)
                self.assertIn("FLIPKART_SEARCH", kinds)
                self.assertFalse(product.get("is_medicine", False))

    def test_explicit_medicine_metadata_can_be_materialized_without_inference(self):
        medicine = materialize_product({
            "id": "clinician-provided-item", "name": "Clindamycin + Nicotinamide Gel",
            "is_medicine": True, "pharmacy_query": "Clindamycin + Nicotinamide Gel",
        })
        self.assertTrue(medicine["is_medicine"])
        self.assertNotIn("prescription_required", medicine)
        self.assertEqual(len(medicine["pharmacy_links"]), 2)
        self.assertEqual(parse_qs(urlparse(medicine["pharmacy_links"][0]["url"]).query)["name"], [medicine["name"]])
        self.assertNotIn("pharmacy_links", materialize_product({"id": "unknown", "name": "No recommendation"}))

    def test_products_api_keeps_discovery_separate_from_assessment_medicines(self):
        from app import app

        response = app.test_client().get("/api/products?area=All&mode=discovery&risk_score=0")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()["items"]
        self.assertTrue(any(item.get("pharmacy_links") for item in items))
        self.assertTrue(all(not item.get("is_medicine", False) for item in items))


if __name__ == "__main__":
    unittest.main()
