import json
import random
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery

PROJECT_ID = "gke-retail-chatbot"
DATASET_ID = "retail_store"
TABLE_ID = "product_catalog"

CATEGORIES = {
    "electronics": {
        "subcategories": ["smartphone", "laptop", "tablet", "headphones", "smartwatch", "speaker", "camera"],
        "brands": ["TechVault", "NovaByte", "PeakSignal", "ZenithPro", "CircuitWave", "PixelEdge"],
        "price_range": (29.99, 1999.99),
        "tags_pool": ["wireless", "bluetooth", "usb-c", "fast-charging", "noise-cancelling", "waterproof", "4k", "oled", "gaming", "portable"],
    },
    "clothing": {
        "subcategories": ["t-shirt", "jeans", "jacket", "dress", "hoodie", "shorts", "sweater"],
        "brands": ["UrbanThread", "FitForm", "CoastalWear", "SummitStyle", "LoopStitch", "RawEdge"],
        "price_range": (14.99, 299.99),
        "tags_pool": ["cotton", "slim-fit", "oversized", "organic", "stretch", "waterproof", "breathable", "recycled", "unisex", "limited-edition"],
    },
    "home": {
        "subcategories": ["cookware", "bedding", "lighting", "storage", "decor", "furniture", "appliance"],
        "brands": ["NestCraft", "HearthStone", "CleanLine", "WoodHaven", "BrightHome", "IronRoot"],
        "price_range": (9.99, 899.99),
        "tags_pool": ["stainless-steel", "non-stick", "led", "smart-home", "eco-friendly", "handmade", "compact", "dishwasher-safe", "energy-star", "modular"],
    },
    "sports": {
        "subcategories": ["running-shoes", "yoga-mat", "dumbbells", "resistance-bands", "cycling-gear", "gym-bag", "fitness-tracker"],
        "brands": ["TrailForge", "FlexPeak", "IronGrip", "VeloCore", "ZenFit", "StridePro"],
        "price_range": (12.99, 499.99),
        "tags_pool": ["lightweight", "anti-slip", "adjustable", "foldable", "moisture-wicking", "ergonomic", "high-impact", "reflective", "padded", "carbon-fiber"],
    },
    "beauty": {
        "subcategories": ["skincare", "haircare", "fragrance", "makeup", "tools", "sunscreen"],
        "brands": ["GlowLab", "VelvetRoot", "ClearCanvas", "PetalSoft", "LuxBlend", "BareElement"],
        "price_range": (7.99, 189.99),
        "tags_pool": ["vegan", "cruelty-free", "spf-50", "hypoallergenic", "fragrance-free", "organic", "travel-size", "long-lasting", "dermatologist-tested", "paraben-free"],
    },
    "grocery": {
        "subcategories": ["snacks", "beverages", "pantry-staples", "fresh-produce", "frozen", "organic"],
        "brands": ["HarvestBin", "CleanPlate", "FieldGood", "PurePantry", "SnapFresh", "GreenBasket"],
        "price_range": (1.99, 49.99),
        "tags_pool": ["gluten-free", "non-gmo", "sugar-free", "high-protein", "keto", "plant-based", "fair-trade", "locally-sourced", "bulk", "zero-waste"],
    },
}

COLORS = ["black", "white", "navy", "gray", "red", "blue", "green", "brown", "silver", "gold", "pink", "orange", "teal", "charcoal", "cream"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "One Size"]
CONDITIONS = ["new", "refurbished", "open-box"]
ADJECTIVES = ["Premium", "Essential", "Classic", "Ultra", "Pro", "Elite", "Everyday", "Signature", "Core", "Max", "Lite", "Flex", "Prime", "Edge", "Nova"]
NOUNS = {
    "electronics": ["Station", "Hub", "Device", "System", "Gear", "Unit"],
    "clothing": ["Collection", "Wear", "Line", "Fit", "Series", "Edition"],
    "home": ["Set", "Collection", "Kit", "Suite", "Series", "Pack"],
    "sports": ["Gear", "Kit", "Pro", "System", "Series", "Trainer"],
    "beauty": ["Formula", "Blend", "Ritual", "Complex", "System", "Kit"],
    "grocery": ["Pack", "Box", "Bundle", "Selection", "Mix", "Sampler"],
}

def generate_products(count=500):
    products = []
    for i in range(count):
        category = random.choice(list(CATEGORIES.keys()))
        cat = CATEGORIES[category]
        subcategory = random.choice(cat["subcategories"])
        brand = random.choice(cat["brands"])
        adj = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS[category])
        sub_pretty = subcategory.replace("-", " ").title()
        name = f"{brand} {adj} {sub_pretty} {noun}"
        lo, hi = cat["price_range"]
        price = round(random.uniform(lo, hi), 2)
        price_tier = "budget" if price < 25 else "mid" if price < 75 else "premium" if price < 200 else "luxury"
        on_sale = random.random() < 0.20
        sale_pct = random.choice([10, 15, 20, 25, 30, 40]) if on_sale else 0
        sale_price = round(price * (1 - sale_pct / 100), 2) if on_sale else None
        tags = random.sample(cat["tags_pool"], k=random.randint(2, 5))
        color = random.choice(COLORS)
        stock_qty = random.choices([0, random.randint(1, 5), random.randint(6, 50), random.randint(51, 500)], weights=[0.08, 0.12, 0.50, 0.30])[0]
        rating = min(round(random.uniform(2.5, 5.0), 1), 5.0)
        review_count = int(rating * random.randint(10, 120))
        created_at = (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat()
        tag_str = ", ".join(tags[:3])
        templates = [
            f"The {name} delivers exceptional quality for {category} enthusiasts. Features {tag_str} design built for everyday reliability.",
            f"Upgrade your {sub_pretty.lower()} game with the {name}. Engineered with {tag_str} technology for superior performance.",
            f"Meet the {name} -- a top-rated {sub_pretty.lower()} combining {tag_str} features at an unbeatable value.",
        ]
        products.append({
            "product_id": f"PROD-{i+1:04d}", "product_name": name, "category": category,
            "subcategory": subcategory, "brand": brand, "color": color,
            "size_available": random.sample(SIZES, k=random.randint(2, 5)) if category == "clothing" else ["One Size"],
            "price": price, "price_tier": price_tier, "sale_active": on_sale,
            "sale_percentage": sale_pct, "sale_price": sale_price, "rating": rating,
            "review_count": review_count, "in_stock": stock_qty > 0, "stock_quantity": stock_qty,
            "condition": random.choices(CONDITIONS, weights=[0.85, 0.10, 0.05])[0],
            "season": random.choice(["spring", "summer", "fall", "winter", "all-season"]),
            "tags": tags, "description": random.choice(templates),
            "image_url": f"https://storage.googleapis.com/{PROJECT_ID}/images/{category}/{subcategory}.png",
            "created_at": created_at,
        })
    return products

def create_dataset_and_table(client):
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset '{DATASET_ID}' ready")
    schema = [
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("subcategory", "STRING"),
        bigquery.SchemaField("brand", "STRING"),
        bigquery.SchemaField("color", "STRING"),
        bigquery.SchemaField("size_available", "STRING", mode="REPEATED"),
        bigquery.SchemaField("price", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("price_tier", "STRING"),
        bigquery.SchemaField("sale_active", "BOOL"),
        bigquery.SchemaField("sale_percentage", "INT64"),
        bigquery.SchemaField("sale_price", "FLOAT64"),
        bigquery.SchemaField("rating", "FLOAT64"),
        bigquery.SchemaField("review_count", "INT64"),
        bigquery.SchemaField("in_stock", "BOOL", mode="REQUIRED"),
        bigquery.SchemaField("stock_quantity", "INT64"),
        bigquery.SchemaField("condition", "STRING"),
        bigquery.SchemaField("season", "STRING"),
        bigquery.SchemaField("tags", "STRING", mode="REPEATED"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("image_url", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
    ]
    table_ref = dataset_ref.table(TABLE_ID)
    table = bigquery.Table(table_ref, schema=schema)
    client.create_table(table, exists_ok=True)
    print(f"Table '{TABLE_ID}' ready")
    return table_ref

def load_data(client, table_ref, products):
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    job = client.load_table_from_json(products, table_ref, job_config=job_config)
    job.result()
    print(f"Loaded {job.output_rows} products")

def verify_data(client):
    queries = [
        ("Total products", f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`"),
        ("By category", f"SELECT category, COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` GROUP BY category ORDER BY cnt DESC"),
        ("On sale", f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` WHERE sale_active = TRUE"),
        ("Out of stock", f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` WHERE in_stock = FALSE"),
    ]
    print("\n-- Data Verification --")
    for label, query in queries:
        rows = list(client.query(query).result())
        if len(rows) == 1 and hasattr(rows[0], "cnt"):
            print(f"  {label}: {rows[0].cnt}")
        else:
            print(f"  {label}:")
            for row in rows:
                print(f"    {dict(row)}")
    print("------------------------\n")

if __name__ == "__main__":
    print("Generating 500 retail products...")
    products = generate_products(500)
    print("Connecting to BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = create_dataset_and_table(client)
    load_data(client, table_ref, products)
    verify_data(client)
    print("Done -- product catalog ready.")
