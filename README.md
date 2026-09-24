# Smart E-Commerce Concierge

An AI-powered conversational shopping assistant built with the **Google Agent Development Kit (ADK)** and deployed on **Google Cloud Agent Engine**.

![Smart E-Commerce Concierge Demo](demo.gif)

---

## 🌟 Capabilities & Features

The agent implements the following features based on the codebase in `app/` and integration parameters in `agents-cli-manifest.yaml`:

### 🛍️ Smart Shopping & Cart Management (Cloud Firestore)
* **Product Catalog Queries**: Searches in-stock merchandise and retrieves pricing, ratings, and features.
* **Persistent Cart State**: Reads and updates shopping cart items in **Google Cloud Firestore** (`get_cart`, `add_to_cart`, `clear_cart`).
* **Tax & Discount Calculation**: Computes itemized sub-totals, discounts, estimated tax, and shipping totals (`calculate_cart_totals`).

### 📍 Physical Store Pickup (Google Maps Places API)
* **Real-time Location Search**: Uses the Google Maps Places API (`find_store_pickup_locations`) to locate nearby retail stores offering same-day pickup for selected products.

### 🖼️ AI Product Image Generation (Vertex AI Imagen 3)
* **On-Demand Visual Renders**: Generates realistic product concept images using `imagen-3.0-generate-002` via Vertex AI (`generate_product_image`).
* **Cloud Storage Hosting**: Uploads generated images directly to **Google Cloud Storage** and returns public HTTPS media URLs.

### 🎬 AI Product Video Showcase (Gemini Omni Model)
* **Omni Model Video Generation**: Creates short product demonstration videos using `gemini-omni-flash-preview` in the `global` Vertex AI region (`generate_product_video`).
* **Artifact & GCS Publishing**: Saves videos as framework artifacts for UI display and publishes them to Google Cloud Storage.

### 🧠 Personalized Shopping Memory (Google Memory Bank)
* **User Context Recall**: Integrates `MemoryBankExtension` to preserve user preferences (e.g., favorite brands, budget limits, sizing) across conversation sessions.

### 🎨 Structured UI Cards (A2UI v0.8)
* **Rich Visual Responses**: Formats recommendations, store pickup details, cart summaries, and generated media into structured **Agent-to-UI (A2UI)** component cards.

---

## 🏗️ Architecture & Cloud Infrastructure

```
┌─────────────────────────┐       ┌──────────────────────────┐       ┌────────────────────────┐
│  FastAPI Proxy Frontend │ <───> │ Vertex AI Agent Engine   │ <───> │  Google Cloud Services │
│   (HTML/CSS/JS Chat)    │       │   (ADK Root Agent)       │       │ - Cloud Firestore      │
└─────────────────────────┘       └──────────────────────────┘       │ - Cloud Storage        │
                                                                     │ - Vertex AI Imagen 3   │
                                                                     │ - Gemini Omni Model    │
                                                                     │ - Google Maps Places   │
                                                                     └────────────────────────┘
```

---

## 🛠️ Local Development Setup

### Prerequisites
* **Python 3.11+**
* **Google Cloud SDK (`gcloud`)** authenticated to your GCP project.
* A **Google Maps API Key** with Places API enabled.

### 1. Environment Configuration

Define the required environment variables in your terminal:

```bash
export PROJECT_ID="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="us-east1"
export GOOGLE_MAPS_API_KEY="your-google-maps-api-key"
```

### 2. Install Dependencies

Install the project dependencies using `uv` or `pip`:

```bash
uv sync
# OR
pip install -r requirements.txt
```

### 3. Run the Agent & Frontend Locally

Start the local FastAPI development server:

```bash
# Set local development parameters
export AGENT_DIRECTORY="app"

# Start the frontend proxy server
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Once running, navigate to port `8080` in your web browser to test the conversational interface locally.

---

## 🚀 Deployment to Google Cloud

### Deploy Agent to Agent Engine
Deploy the agent runtime to Google Cloud Agent Engine using `agents-cli`:

```bash
agents-cli deploy --project $PROJECT_ID --update-env-vars GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
```

### Deploy Frontend to Cloud Run
Deploy the FastAPI chat frontend to Cloud Run:

```bash
gcloud run deploy smart-ecommerce-frontend \
  --source ./frontend \
  --region us-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars AGENT_DIRECTORY=app
```
