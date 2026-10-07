#!/usr/bin/env python3
"""Create/update the extra content types (idempotent). Usage: python3 scripts/seed/schemas.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import seed  # noqa: E402  (reuses the Contentstack API helper + credential loading)


# ------------------------------------------------------------ field builders
def _base(uid, name, data_type, **kw):
    f = {"data_type": data_type, "display_name": name, "uid": uid, "mandatory": False, "multiple": False, "unique": False}
    f.update(kw)
    return f


def title(name="Title"):
    return _base("title", name, "text", mandatory=True, unique=True, field_metadata={"_default": True, "version": 3})


def url():
    return _base("url", "URL", "text", field_metadata={"_default": True, "version": 3})


def text(uid, name, multiline=False, multiple=False, required=False, help=""):
    return _base(uid, name, "text", mandatory=required, multiple=multiple,
                 field_metadata={"description": help, "default_value": "", "multiline": multiline, "version": 3})


def select(uid, name, choices, required=False, default=""):
    return _base(uid, name, "text", mandatory=required, display_type="dropdown",
                 enum={"advanced": False, "choices": [{"value": c} for c in choices]},
                 field_metadata={"description": "", "default_value": default, "version": 3})


def number(uid, name, multiple=False, required=False, help=""):
    return _base(uid, name, "number", mandatory=required, multiple=multiple,
                 field_metadata={"description": help, "default_value": ""})


def boolean(uid, name, default=False):
    return _base(uid, name, "boolean", field_metadata={"description": "", "default_value": default})


def date(uid, name, help=""):
    return _base(uid, name, "isodate", startDate=None, endDate=None,
                 field_metadata={"description": help, "default_value": {}})


def link(uid, name):
    return _base(uid, name, "link", field_metadata={"description": "", "default_value": {"title": "", "url": ""}})


def image(uid, name, required=False):
    return _base(uid, name, "file", mandatory=required, extensions=[],
                 field_metadata={"description": "", "rich_text_type": "standard", "image": True})


def rte(uid, name, required=False):
    return _base(uid, name, "json", mandatory=required, reference_to=["sys_assets"], format="", error_messages={"format": ""},
                 field_metadata={"allow_json_rte": True, "embed_entry": False, "description": "", "default_value": "",
                                 "multiline": False, "rich_text_type": "advanced", "options": []})


def group(uid, name, fields, multiple=False):
    return _base(uid, name, "group", multiple=multiple, schema=fields, field_metadata={"description": "", "instruction": ""})


def reference(uid, name, to, multiple=True):
    return _base(uid, name, "reference", reference_to=to, multiple=multiple,
                 field_metadata={"ref_multiple": multiple, "ref_multiple_content_types": len(to) > 1})


# ------------------------------------------------------------ content types
INDUSTRIES = ["Automotive Workshops", "Transport & Logistics", "Marine & Leisure", "Wholesale Distribution", "Public Sector", "Other"]

CONTENT_TYPES = [
    {
        "title": "FAQ",
        "uid": "faq",
        "description": "A question with a rich-text answer, grouped by topic. The title is the question.",
        "schema": [
            title("Question"),
            rte("answer", "Answer", required=True),
            select("topic", "Topic", ["Ordering", "Pricing & Credit", "Delivery & Returns", "Account & Users", "Products & Fitment"], required=True),
            number("sort_order", "Sort order", help="Lower numbers appear first within a topic."),
            boolean("is_featured", "Featured on the FAQ page"),
        ],
        "options": {"is_page": False, "singleton": False, "title": "title", "sub_title": []},
    },
    {
        "title": "Buying Guide",
        "uid": "buying_guide",
        "description": "A step-by-step guide that recommends real BigCommerce products by ID and SKU.",
        "schema": [
            title(),
            url(),
            text("summary", "Summary", multiline=True, required=True),
            image("hero_image", "Hero image"),
            select("audience", "Audience", ["Workshops", "Fleet managers", "Leisure & marine", "Everyone"], default="Everyone"),
            number("read_minutes", "Read time (minutes)"),
            group("steps", "Steps", [
                text("step_title", "Step title", required=True),
                text("step_body", "Step body", multiline=True, required=True),
                text("pro_tip", "Pro tip", multiline=True),
            ], multiple=True),
            text("checklist", "Checklist items", multiple=True, help="Short 'before you order' checks."),
            number("recommended_bc_products", "Recommended BigCommerce product IDs", multiple=True),
            text("recommended_skus", "Recommended SKUs", multiple=True),
            reference("related_faqs", "Related FAQs", ["faq"]),
            reference("author", "Author", ["author"], multiple=False),
        ],
        "options": {"is_page": True, "singleton": False, "title": "title", "sub_title": [], "url_pattern": "/:title", "url_prefix": "/guides/"},
    },
    {
        "title": "Product Spotlight",
        "uid": "product_spotlight",
        "description": "Editorial content layered on top of a BigCommerce product. Price, stock and variants stay in BigCommerce.",
        "schema": [
            title(),
            number("bc_product_id", "BigCommerce product ID", required=True, help="Entity ID in the BigCommerce catalog."),
            text("bc_sku", "BigCommerce SKU"),
            text("tagline", "Tagline", required=True),
            rte("editorial_summary", "Editorial summary"),
            text("key_features", "Key features", multiple=True),
            group("use_cases", "Best used for", [
                text("use_case", "Use case", required=True),
                text("description", "Description", multiline=True),
            ], multiple=True),
            text("pairs_well_with_skus", "Pairs well with (SKUs)", multiple=True),
            select("badge", "Badge", ["None", "Best seller", "Trade favourite", "New in", "Heavy duty"], default="None"),
            image("editorial_image", "Editorial image"),
            boolean("is_featured", "Feature on the home page"),
        ],
        "options": {"is_page": False, "singleton": False, "title": "title", "sub_title": []},
    },
    {
        "title": "Announcement Bar",
        "uid": "announcement_bar",
        "description": "A scheduled site-wide banner. The storefront shows the first active one for the visitor's audience.",
        "schema": [
            title("Internal name"),
            text("message", "Message", required=True),
            link("cta", "Call to action"),
            select("style", "Style", ["info", "promo", "warning"], required=True, default="info"),
            select("audience", "Audience", ["everyone", "logged_in", "guests"], required=True, default="everyone"),
            date("starts_at", "Starts at"),
            date("ends_at", "Ends at"),
            boolean("is_active", "Active", default=True),
        ],
        "options": {"is_page": False, "singleton": False, "title": "title", "sub_title": []},
    },
    {
        "title": "Site Navigation",
        "uid": "site_navigation",
        "description": "Header links, footer columns and contact details. A single entry drives the whole site chrome.",
        "schema": [
            title("Name"),
            group("header_links", "Header links", [
                text("label", "Label", required=True),
                text("href", "Link", required=True),
                boolean("highlight", "Highlight as a button"),
            ], multiple=True),
            group("footer_columns", "Footer columns", [
                text("heading", "Heading", required=True),
                group("links", "Links", [
                    text("label", "Label", required=True),
                    text("href", "Link", required=True),
                ], multiple=True),
            ], multiple=True),
            group("contact", "Contact details", [
                text("sales_email", "Sales email"),
                text("support_phone", "Support phone"),
                text("opening_hours", "Opening hours"),
            ]),
            text("legal_text", "Legal / copyright line"),
        ],
        "options": {"is_page": False, "singleton": True, "title": "title", "sub_title": []},
    },
]


def main():
    existing = {c["uid"] for c in seed.api("GET", "/content_types", params={"limit": 100})["content_types"]}
    for ct in CONTENT_TYPES:
        body = {"content_type": {k: ct[k] for k in ("title", "uid", "description", "schema", "options")}}
        if ct["uid"] in existing:
            seed.api("PUT", f"/content_types/{ct['uid']}", body=body)
            print(f"  updated {ct['uid']}")
        else:
            seed.api("POST", "/content_types", body=body)
            print(f"  created {ct['uid']}")


if __name__ == "__main__":
    main()
