import os
import json
import re
import logging
import time
from google.cloud import bigquery
import google.generativeai as genai

logger = logging.getLogger("chatbot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gke-retail-chatbot")
DATASET = "retail_store"
TABLE = "product_catalog"
FQN = f"`{PROJECT_ID}.{DATASET}.{TABLE}`"

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")
bq = bigquery.Client(project=PROJECT_ID)

SYSTEM_PROMPT = """You are a friendly, knowledgeable ecommerce retail shopping assistant.

Your job:
- Help customers find products matching their needs
- Compare options with clear pros/cons
- Highlight deals and discounts
- Check stock availability
- Give honest, helpful recommendations

Rules:
- Be conversational and warm, not robotic
- Format products clearly: name, price, rating, key details
- Always highlight sale prices and discounts when present
- If out of stock, suggest alternatives
- Use ONLY the product data provided -- never invent products
- If no results match, say so and suggest broadening the search
- Keep responses concise -- 3-5 products max unless asked for more
- When comparing, structure as clear pros/cons
- Mention ratings and review counts to build trust
- If a customer seems unsure, ask a clarifying question"""


def classify_intent(message):
    msg = message.lower()
    if any(w in msg for w in ["compare", "versus", "vs", "difference between", "which is better"]):
        return "compare"
    if any(w in msg for w in ["sale", "deal", "discount", "cheap", "budget", "under $", "affordable", "clearance", "save"]):
        return "deals"
    if any(w in msg for w in ["stock", "available", "availability", "left", "how many", "in stock"]):
        return "stock"
    if any(w in msg for w in ["recommend", "suggest", "best", "top", "popular", "highest rated", "trending", "favorite"]):
        return "recommend"
    if any(w in msg for w in ["find", "show", "search", "looking for", "need", "want", "get me", "i need"]):
        return "search"
    if any(w in msg for w in ["category", "categories", "what do you sell", "what do you have", "browse", "catalog"]):
        return "browse"
    return "general"


def build_query(intent, message):
    msg = message.lower()
    if intent == "browse":
        return f"""SELECT category, COUNT(*) as product_count, ROUND(MIN(price),2) as min_price, ROUND(MAX(price),2) as max_price, ROUND(AVG(rating),1) as avg_rating, COUNTIF(sale_active = TRUE) as on_sale_count FROM {FQN} WHERE in_stock = TRUE GROUP BY category ORDER BY product_count DESC"""
    if intent == "deals":
        return f"""SELECT product_id, product_name, category, brand, price, sale_price, sale_percentage, rating, review_count, stock_quantity, tags, description FROM {FQN} WHERE sale_active = TRUE AND in_stock = TRUE {_cat(msg)} {_price_ceil(msg)} ORDER BY sale_percentage DESC, rating DESC LIMIT 10"""
    if intent == "stock":
        pf = _prod_id(msg)
        if pf:
            return f"""SELECT product_id, product_name, in_stock, stock_quantity, size_available, price, sale_active, sale_price FROM {FQN} WHERE {pf}"""
        return f"""SELECT product_id, product_name, category, stock_quantity, price FROM {FQN} WHERE stock_quantity <= 5 AND in_stock = TRUE {_cat(msg)} ORDER BY stock_quantity ASC LIMIT 10"""
    if intent == "recommend":
        return f"""SELECT product_id, product_name, category, subcategory, brand, color, price, price_tier, sale_active, sale_price, sale_percentage, rating, review_count, tags, description FROM {FQN} WHERE in_stock = TRUE AND rating >= 4.0 {_cat(msg)} {_price_ceil(msg)} ORDER BY rating DESC, review_count DESC LIMIT 8"""
    if intent in ("search", "compare"):
        return f"""SELECT product_id, product_name, category, subcategory, brand, color, price, price_tier, sale_active, sale_price, sale_percentage, rating, review_count, stock_quantity, tags, description FROM {FQN} WHERE in_stock = TRUE {_cat(msg)} {_price_ceil(msg)} {_color(msg)} {_brand(msg)} ORDER BY rating DESC, review_count DESC LIMIT 10"""
    return None


def _cat(msg):
    mapping = {
        "electronics": ["electronics", "tech", "gadget", "phone", "laptop", "tablet", "headphone", "speaker", "camera", "smartwatch"],
        "clothing": ["clothing", "clothes", "shirt", "jeans", "jacket", "dress", "hoodie", "shorts", "sweater", "apparel"],
        "home": ["home", "kitchen", "cookware", "bedding", "lighting", "furniture", "decor", "appliance"],
        "sports": ["sports", "fitness", "gym", "running", "yoga", "cycling", "workout", "exercise"],
        "beauty": ["beauty", "skincare", "haircare", "makeup", "fragrance", "sunscreen", "cosmetic"],
        "grocery": ["grocery", "food", "snack", "beverage", "drink", "pantry", "organic"],
    }
    for cat, kws in mapping.items():
        if any(kw in msg for kw in kws):
            return f"AND category = '{cat}'"
    return ""

def _price_ceil(msg):
    tokens = msg.split()
    for i, t in enumerate(tokens):
        c = t.replace("$", "").replace(",", "")
        try:
            n = float(c)
            if i > 0 and tokens[i-1] in ("over", "above", "more", "min", ">"):
                return f"AND price >= {n}"
            return f"AND price <= {n}"
        except ValueError:
            continue
    return ""

def _color(msg):
    for c in ["black","white","navy","gray","red","blue","green","brown","silver","gold","pink","orange","teal"]:
        if c in msg:
            return f"AND color = '{c}'"
    return ""

def _brand(msg):
    brands_map = {
        "techvault": "TechVault", "novabyte": "NovaByte", "peaksignal": "PeakSignal",
        "zenithpro": "ZenithPro", "circuitwave": "CircuitWave", "pixeledge": "PixelEdge",
        "urbanthread": "UrbanThread", "fitform": "FitForm", "coastalwear": "CoastalWear",
        "summitstyle": "SummitStyle", "loopstitch": "LoopStitch", "rawedge": "RawEdge",
        "nestcraft": "NestCraft", "hearthstone": "HearthStone", "cleanline": "CleanLine",
        "woodhaven": "WoodHaven", "brighthome": "BrightHome", "ironroot": "IronRoot",
        "trailforge": "TrailForge", "flexpeak": "FlexPeak", "irongrip": "IronGrip",
        "velocore": "VeloCore", "zenfit": "ZenFit", "stridepro": "StridePro",
        "glowlab": "GlowLab", "velvetroot": "VelvetRoot", "clearcanvas": "ClearCanvas",
        "petalsoft": "PetalSoft", "luxblend": "LuxBlend", "bareelement": "BareElement",
        "harvestbin": "HarvestBin", "cleanplate": "CleanPlate", "fieldgood": "FieldGood",
        "purepantry": "PurePantry", "snapfresh": "SnapFresh", "greenbasket": "GreenBasket",
    }
    for key, val in brands_map.items():
        if key in msg:
            return f"AND brand = '{val}'"
    return ""

def _prod_id(msg):
    m = re.search(r'PROD-\d{4}', msg.upper())
    return f"product_id = '{m.group()}'" if m else ""

def run_query(sql):
    try:
        start = time.time()
        rows = [dict(r) for r in bq.query(sql).result()]
        elapsed = round((time.time() - start) * 1000, 1)
        logger.info(f"BigQuery: {len(rows)} rows in {elapsed}ms")
        return rows
    except Exception as e:
        logger.error(f"BigQuery error: {e}")
        return []

async def get_response(message, history=None):
    intent = classify_intent(message)
    logger.info(f"Intent: {intent} | Message: {message[:80]}")
    sql = build_query(intent, message)
    products = run_query(sql) if sql else []
    parts = [SYSTEM_PROMPT, ""]
    if products:
        parts.append(f"Product data ({len(products)} results):")
        parts.append(json.dumps(products, indent=2, default=str))
    elif intent != "general":
        parts.append("No products matched. Help the customer refine their search.")
    parts.append(f"\nCustomer: {message}")
    parts.append("\nRespond helpfully. Format products clearly if showing results.")
    prompt = "\n".join(parts)
    gemini_history = []
    if history:
        for turn in history[-6:]:
            gemini_history.append({"role": turn["role"], "parts": [turn["content"]]})
    try:
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "I'm having trouble right now. Please try again in a moment."
