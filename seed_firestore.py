import sys
from google.cloud import firestore

# IMPORTANT: Hardcode the Project ID string explicitly.
# Do NOT use os.getenv("GOOGLE_CLOUD_PROJECT") or google.auth.default()
# because Agent Platform sets GOOGLE_CLOUD_PROJECT to the numeric project number.
PROJECT_ID = "qwiklabs-gcp-02-1493a032172c"

PRODUCTS = [
    {
        "id": "prod-101",
        "name": "Wireless Noise-Canceling Headphones",
        "category": "Electronics",
        "price": 199.99,
        "stock": 25,
        "rating": 4.7,
        "description": "Premium over-ear wireless headphones with active noise cancellation and 30-hour battery life.",
        "in_stock": True,
    },
    {
        "id": "prod-102",
        "name": "Ergonomic Office Chair",
        "category": "Furniture",
        "price": 249.50,
        "stock": 12,
        "rating": 4.5,
        "description": "Mesh high-back desk chair with adjustable lumbar support and 3D armrests.",
        "in_stock": True,
    },
    {
        "id": "prod-103",
        "name": "Smart Fitness Watch",
        "category": "Electronics",
        "price": 149.00,
        "stock": 0,
        "rating": 4.3,
        "description": "Water-resistant smartwatch with heart rate monitoring, GPS, and sleep tracking.",
        "in_stock": False,
    },
    {
        "id": "prod-104",
        "name": "Organic Cold Brew Coffee Maker",
        "category": "Kitchen",
        "price": 34.99,
        "stock": 40,
        "rating": 4.8,
        "description": "1-liter glass pitcher cold brew maker with extra-fine stainless steel mesh filter.",
        "in_stock": True,
    },
    {
        "id": "prod-105",
        "name": "Mechanical Gaming Keyboard",
        "category": "Electronics",
        "price": 89.99,
        "stock": 18,
        "rating": 4.6,
        "description": "RGB backlit mechanical keyboard with tactile brown switches and durable aluminum frame.",
        "in_stock": True,
    },
]


def seed_database():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("products")

    for item in PRODUCTS:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"  [+] Seeded product {item['id']}: {item['name']}")

    print("\n✅ Firestore database successfully seeded with initial product catalog!")


if __name__ == "__main__":
    seed_database()
