# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import logging
import os
from pathlib import Path
import urllib.parse
import urllib.request
import uuid

logger = logging.getLogger(__name__)

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from app.a2ui_utils import a2ui_callback

# IMPORTANT: Hardcode the GCP Project ID and Bucket Name strings.
# Do NOT read from google.auth.default() or GOOGLE_CLOUD_PROJECT environment variable.
PROJECT_ID = "qwiklabs-gcp-02-1493a032172c"
BUCKET_NAME = "smart-ecommerce-media-qwiklabs-gcp-02-1493a032172c"
MEMORY_BANK_ID = "7515797493569814528"

_db = None
_storage_client = None


def get_firestore_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


# Memory Bank Service configuration for future deployment
memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location="us-east1",
    agent_engine_id=MEMORY_BANK_ID,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, send the session to Memory Bank for durable fact extraction."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        logger.warning(f"Memory callback skipped non-fatally: {e}")
    return None


def search_products(query: str = "", category: str = "") -> list[dict]:
    """Search for products in the store catalog by keyword or category.

    Args:
        query: Optional search keyword to match against product name or description.
        category: Optional product category filter (e.g., Electronics, Kitchen, Furniture).

    Returns:
        A list of matching product dictionaries from the Firestore database.
    """
    db = get_firestore_db()
    docs = db.collection("products").stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        name_match = query.lower() in data.get("name", "").lower() or query.lower() in data.get("description", "").lower() if query else True
        category_match = category.lower() in data.get("category", "").lower() if category else True
        if name_match and category_match:
            results.append(data)
    return results


def get_product_details(product_id: str) -> dict:
    """Fetch details for a specific product by its product ID.

    Args:
        product_id: Unique product identifier (e.g. prod-101).

    Returns:
        Product dictionary or error message if not found.
    """
    db = get_firestore_db()
    doc = db.collection("products").document(product_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Product '{product_id}' not found."}


def add_product(
    product_id: str,
    name: str,
    category: str,
    price: float,
    stock: int,
    description: str,
) -> dict:
    """Add a new product to the Firestore e-commerce catalog.

    Args:
        product_id: Unique product ID (e.g., prod-106).
        name: Name of the product.
        category: Category (e.g. Electronics, Home, Apparel).
        price: Price in USD.
        stock: Available inventory stock quantity.
        description: Detailed product description.

    Returns:
        Status confirmation dictionary with product data.
    """
    db = get_firestore_db()
    item = {
        "id": product_id,
        "name": name,
        "category": category,
        "price": float(price),
        "stock": int(stock),
        "rating": 5.0,
        "description": description,
        "in_stock": int(stock) > 0,
    }
    db.collection("products").document(product_id).set(item)
    return {"status": "success", "message": f"Added product '{name}' ({product_id}).", "product": item}


def update_product_stock(product_id: str, stock_change: int) -> dict:
    """Update stock quantity for an existing product in Firestore.

    Args:
        product_id: Unique product ID.
        stock_change: Quantity to add (positive) or remove (negative).

    Returns:
        Updated stock status dictionary.
    """
    db = get_firestore_db()
    doc_ref = db.collection("products").document(product_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Product '{product_id}' not found."}

    data = doc.to_dict()
    new_stock = max(0, data.get("stock", 0) + stock_change)
    in_stock = new_stock > 0
    doc_ref.update({"stock": new_stock, "in_stock": in_stock})
    return {
        "status": "success",
        "product_id": product_id,
        "old_stock": data.get("stock", 0),
        "new_stock": new_stock,
        "in_stock": in_stock,
    }


def manage_shopping_cart(
    action: str,
    product_id: str = "",
    quantity: int = 1,
    cart_id: str = "default_cart",
) -> dict:
    """Manage the user's shopping cart in Firestore (add, remove, view, or clear).

    Args:
        action: Action to perform - 'add', 'remove', 'view', or 'clear'.
        product_id: Product ID (e.g. prod-101) for 'add' or 'remove' actions.
        quantity: Item quantity to add or remove (default 1).
        cart_id: Unique cart ID (defaults to 'default_cart').

    Returns:
        Dictionary with cart items, subtotal, and total item count.
    """
    db = get_firestore_db()
    cart_ref = db.collection("carts").document(cart_id)
    cart_doc = cart_ref.get()

    cart_data = cart_doc.to_dict() if cart_doc.exists else {"items": {}}
    items = cart_data.get("items", {})

    action_clean = action.lower().strip()

    if action_clean == "clear":
        cart_ref.set({"items": {}, "subtotal": 0.0, "total_items": 0})
        return {"status": "success", "message": "Cart cleared.", "items": [], "subtotal": 0.0, "total_items": 0}

    if action_clean == "add":
        if not product_id:
            return {"error": "product_id is required for 'add' action."}
        product = get_product_details(product_id)
        if "error" in product:
            return product

        current_qty = items.get(product_id, {}).get("quantity", 0)
        new_qty = current_qty + quantity
        items[product_id] = {
            "product_id": product_id,
            "name": product.get("name", product_id),
            "price": product.get("price", 0.0),
            "quantity": new_qty,
            "item_total": round(product.get("price", 0.0) * new_qty, 2),
        }

    elif action_clean == "remove":
        if not product_id or product_id not in items:
            return {"error": f"Product '{product_id}' is not in the cart."}
        current_qty = items[product_id]["quantity"]
        new_qty = current_qty - quantity
        if new_qty <= 0:
            del items[product_id]
        else:
            items[product_id]["quantity"] = new_qty
            items[product_id]["item_total"] = round(items[product_id]["price"] * new_qty, 2)

    subtotal = round(sum(item["item_total"] for item in items.values()), 2)
    total_items = sum(item["quantity"] for item in items.values())

    updated_cart = {
        "items": items,
        "subtotal": subtotal,
        "total_items": total_items,
    }
    cart_ref.set(updated_cart)

    return {
        "status": "success",
        "action": action_clean,
        "items": list(items.values()),
        "subtotal": subtotal,
        "total_items": total_items,
    }


def fetch_external_deals(limit: int = 5) -> list[dict]:
    """Fetch live external store deals and trending products from a public e-commerce API (FakeStoreAPI).

    Args:
        limit: Maximum number of deals to return (default 5, max 20).

    Returns:
        List of product deal dictionaries with title, price, category, description, and rating.
    """
    api_key = os.environ.get("FAKESTORE_API_KEY", "")
    url = f"https://fakestoreapi.com/products?limit={min(max(1, limit), 20)}"
    headers = {"User-Agent": "Smart-Ecommerce-Agent/1.0"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                raw_items = json.loads(response.read().decode("utf-8"))
                deals = []
                for item in raw_items:
                    deals.append({
                        "id": f"ext-{item.get('id')}",
                        "title": item.get("title"),
                        "price": item.get("price"),
                        "category": item.get("category"),
                        "description": item.get("description", "")[:120] + "...",
                        "rating": item.get("rating", {}).get("rate", 4.5),
                        "image_url": item.get("image"),
                    })
                return deals
    except Exception as e:
        return [{"error": f"Failed to fetch external deals: {str(e)}"}]
    return []


def geocode_address(address: str) -> dict:
    """Convert a street address or location name into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: Full street address or location (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not configured."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                loc = result.get("geometry", {}).get("location", {})
                return {
                    "status": "success",
                    "address": result.get("formatted_address"),
                    "location": {
                        "latitude": loc.get("lat"),
                        "longitude": loc.get("lng"),
                    },
                }
            return {"error": f"Geocoding failed with status: {data.get('status')}"}
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "store",
    radius: float = 1000.0,
) -> list[dict]:
    """Find nearby places (stores, restaurants, pickup locations) around a location using Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Place type filter (e.g., 'store', 'electronics_store', 'shopping_mall', 'restaurant').
        radius: Search radius in meters (default 1000.0 meters).

    Returns:
        List of place dictionaries with name, address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not configured."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    body = {
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius),
            }
        },
    }

    try:
        data_bytes = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            places = []
            for place in res_data.get("places", []):
                places.append({
                    "name": place.get("displayName", {}).get("text", "Unknown"),
                    "address": place.get("formattedAddress", "N/A"),
                    "location": place.get("location", {}),
                })
            return places
    except Exception as e:
        return [{"error": f"Places API request failed: {str(e)}"}]


async def generate_product_image(
    prompt: str,
    item_name: str = "product",
    tool_context: ToolContext = None,
) -> dict:
    """Generate an image for an item using gemini-3.1-flash-lite-image model in global location, save as an artifact, and upload to public Cloud Storage.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'Wireless noise-canceling headphones on a sleek desk').
        item_name: Short name of the item or product.
        tool_context: ToolContext injected by the framework.

    Returns:
        Dictionary containing status, filename, and public Cloud Storage https URL.
    """
    client = genai.Client(vertexai=True, location="global", project=PROJECT_ID)

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "No image data returned from gemini-3.1-flash-lite-image."}

        clean_name = item_name.lower().replace(" ", "_")
        filename = f"{clean_name}_{uuid.uuid4().hex[:6]}.jpeg"

        # 1. Save artifact with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            res = tool_context.save_artifact(filename=filename, artifact=artifact_part)
            if hasattr(res, "__await__"):
                await res

        # 2. Upload image bytes directly to the public Cloud Storage bucket without writing to a local file
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "message": f"Generated image for '{item_name}'.",
            "filename": filename,
            "public_url": public_url,
        }

    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}


async def generate_product_video(
    prompt: str,
    item_name: str = "product",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a short video for an item using Google's Omni model (gemini-omni-flash-preview) in global location, save as an artifact, and upload to public Cloud Storage.

    Args:
        prompt: Detailed description of the video to generate for the item (e.g. 'Short product showcase video of ergonomic desk chair').
        item_name: Short name of the item or product.
        tool_context: ToolContext injected by the framework.

    Returns:
        Dictionary containing status, filename, and public Cloud Storage https URL.
    """
    client = genai.Client(vertexai=True, location="global", project=PROJECT_ID)

    try:
        res = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(res, "output_video") and res.output_video and getattr(res.output_video, "data", None):
            vdata = res.output_video.data
            if isinstance(vdata, bytes):
                video_bytes = vdata
            elif isinstance(vdata, str):
                video_bytes = base64.b64decode(vdata)
            if getattr(res.output_video, "mime_type", None):
                mime_type = res.output_video.mime_type

        if not video_bytes and hasattr(res, "steps") and res.steps:
            for s in res.steps:
                contents = getattr(s, "contents", []) or []
                for c in contents:
                    if getattr(c, "type", None) == "video" or hasattr(c, "data"):
                        vdata = getattr(c, "data", None)
                        if isinstance(vdata, bytes):
                            video_bytes = vdata
                            if getattr(c, "mime_type", None):
                                mime_type = c.mime_type
                            break
                        elif isinstance(vdata, str):
                            video_bytes = base64.b64decode(vdata)
                            if getattr(c, "mime_type", None):
                                mime_type = c.mime_type
                            break

        if not video_bytes:
            return {"error": "No video data returned from gemini-omni-flash-preview."}

        clean_name = item_name.lower().replace(" ", "_")
        filename = f"{clean_name}_{uuid.uuid4().hex[:6]}.mp4"

        # 1. Save artifact with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            res_art = tool_context.save_artifact(filename=filename, artifact=artifact_part)
            if hasattr(res_art, "__await__"):
                await res_art

        # 2. Upload video bytes directly to the public Cloud Storage bucket without writing to a local file
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "message": f"Generated video for '{item_name}'.",
            "filename": filename,
            "public_url": public_url,
        }

    except Exception as e:
        return {"error": f"Video generation failed: {str(e)}"}


# Load AgentEngineSandboxCodeExecutor using deployment_metadata.json
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
sandbox_resource_name = None

if metadata_path.exists():
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
            sandbox_resource_name = metadata.get("sandbox_resource_name")
    except Exception:
        pass

if not agent_engine_resource_name:
    agent_engine_resource_name = "projects/40148140586/locations/us-east1/reasoningEngines/7515797493569814528"

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name,
    sandbox_resource_name=sandbox_resource_name,
)

# Build A2UI system prompt using A2uiSchemaManager version 0.8 with BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Smart E-Commerce Concierge agent. You help shoppers explore products, "
        "search the catalog, check stock levels, view details, manage inventory, handle shopping cart operations, "
        "fetch market deals, geocode addresses, locate store pickup locations, generate product lifestyle imagery, "
        "generate short product showcase videos, "
        "and safely execute Python code in a sandbox environment. "
        "Always record, track, and remember all products that the user searches for, views, adds to cart, purchases, "
        "or expresses interest in as durable long-term user memories across sessions."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_products,
        get_product_details,
        add_product,
        update_product_stock,
        manage_shopping_cart,
        fetch_external_deals,
        geocode_address,
        find_nearby_places,
        generate_product_image,
        generate_product_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
