# GKE Retail Chatbot: Complete Project Documentation

## Executive Summary

This project delivers a production-grade ecommerce retail chatbot deployed on Google Kubernetes Engine (GKE Autopilot). The chatbot helps customers find products, compare options, discover deals, and check stock across 500 products in 6 categories. It uses Gemini 2.5 Flash for natural language conversation and BigQuery as the product catalog database. No agent frameworks were used. The entire system was built with clean Python (FastAPI), containerized with Docker, and orchestrated with Kubernetes.

**Key Metrics:**
- 24/24 verification checks passed
- 500 products across 6 categories (electronics, clothing, home, sports, beauty, grocery)
- 2-pod deployment with autoscaling to 8 pods
- Sub-2-second response times on product queries
- Complete teardown verified with zero residual resources

---

## Architecture Overview

### System Components

**User Layer:**
A web browser accesses the chat UI served at the GKE load balancer's public IP over HTTP.

**Load Balancing Layer:**
A GCE HTTP(S) Load Balancer (provisioned automatically by the Kubernetes Ingress resource) distributes incoming traffic across healthy pods. Health checks ensure traffic only reaches pods that are ready to serve.

**Compute Layer (GKE Autopilot):**
Two FastAPI application pods run inside a GKE Autopilot cluster. Each pod contains the full application stack: FastAPI web server, Gemini API client, and BigQuery client. Pods are spread across different nodes via topology constraints for high availability.

**Data Layer:**
BigQuery stores the product catalog (500 products with 22 fields each). The chatbot queries BigQuery using parameterized SQL based on classified user intent.

**AI Layer:**
Gemini 2.5 Flash (via AI Studio API) generates conversational responses. The chatbot sends structured product data from BigQuery along with the user's message, and Gemini formats a natural, helpful reply.

**Security Layer:**
Workload Identity binds Kubernetes service accounts to GCP service accounts. Pods authenticate to BigQuery without JSON key files. The Gemini API key is stored in a Kubernetes Secret.

### Request Flow

1. User types "Show me electronics under $100" in the chat UI
2. Browser sends POST to /chat on the load balancer IP
3. Load balancer routes to a healthy pod
4. FastAPI receives the request, passes to chatbot engine
5. Chatbot engine classifies intent as "search" with category "electronics" and price ceiling $100
6. Engine builds parameterized BigQuery SQL with those filters
7. BigQuery returns matching products (up to 10)
8. Engine sends product data + user message + system prompt to Gemini 2.5 Flash
9. Gemini returns a conversational response with formatted product details
10. FastAPI returns the response as JSON
11. Chat UI displays the response with typing animation

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI 0.115 + Uvicorn | Async HTTP server with auto OpenAPI docs |
| AI Model | Gemini 2.5 Flash | Conversational response generation |
| Database | BigQuery | Product catalog storage and querying |
| Container | Docker (multi-stage) | Application packaging |
| Orchestration | GKE Autopilot | Managed Kubernetes cluster |
| Image Registry | Artifact Registry | Private Docker image storage |
| CI/CD | Cloud Build | Automated image builds |
| Load Balancer | GCE HTTP(S) LB | External traffic routing via Ingress |
| Autoscaling | HPA (Horizontal Pod Autoscaler) | CPU/memory-based pod scaling |
| Security | Workload Identity | Keyless authentication to GCP services |
| Language | Python 3.11 | Application code |

---

## Build Process: Step by Step

### Phase 1: Project Setup

**1.1 Project and billing configuration**
Created GCP project `gke-retail-chatbot` under the `cloudmaster2026-org` organization. Linked to a billing account with $300 free trial credits (89 days remaining). Set a $25 budget alert with email notifications at 50%, 75%, and 100% thresholds via Cloud Monitoring notification channels.

**1.2 API enablement**
Enabled four GCP APIs: Kubernetes Engine, Artifact Registry, Cloud Build, and BigQuery. These are the foundational services the project depends on.

**1.3 File creation**
Created 16 project files directly in Cloud Shell using heredoc (`cat > file << 'EOF'`) commands. No local IDE or GitHub clone was used during initial build. Files were created one at a time to understand each component before moving forward.

### Phase 2: Data Layer

**2.1 Synthetic data generation**
Wrote a Python script (`data/generate_catalog.py`) that generates 500 retail products with realistic attributes:
- 6 categories with 7 subcategories each
- 6 fictional brands per category (36 total)
- Realistic price distributions per category (grocery $1.99-$49.99, electronics $29.99-$1,999.99)
- 20% of products randomly on sale (10-40% off)
- 8% out of stock, 12% low stock
- Ratings between 2.5 and 5.0 with correlated review counts
- Tags, colors, sizes, conditions, seasons

**2.2 BigQuery schema design**
22-field schema covering product identity, pricing, inventory, ratings, and metadata. Used REPEATED mode for `size_available` and `tags` fields to support array queries. Data loaded via `load_table_from_json` with WRITE_TRUNCATE for idempotent reruns.

**2.3 Verification**
Confirmed 500 products loaded, 6 categories populated, ~99 products on sale, ~38 out of stock.

### Phase 3: Application Code

**3.1 Chatbot engine (`src/chatbot.py`)**
Two-step architecture separating data retrieval from language generation:

Step 1: Intent classification using keyword matching. Seven intent types: search, compare, deals, stock, recommend, browse, general. Keyword-based classification is fast, deterministic, and debuggable compared to LLM-based intent detection.

Step 2: Parameterized SQL generation. Each intent maps to a pre-built query template with dynamic filters extracted from the user's message: category, price ceiling/floor, color, and brand. Filters use string matching against known values, preventing SQL injection.

The engine then sends the BigQuery results plus the user's message to Gemini 2.5 Flash with a system prompt that defines the assistant's personality, formatting rules, and constraints (never invent products, highlight sales, mention ratings).

**3.2 Web server (`src/app.py`)**
FastAPI application with five endpoints:
- `GET /` serves the chat HTML (read as static file, not Jinja template)
- `POST /chat` receives messages and returns responses
- `GET /health` for Kubernetes liveness probes
- `GET /ready` for Kubernetes readiness probes
- `GET /docs` auto-generated OpenAPI documentation

In-memory session storage keyed by session_id. Conversation history (last 20 turns) sent to Gemini for multi-turn context. CORS middleware enabled for cross-origin testing.

**3.3 Chat UI (`src/templates/chat.html`)**
Single-file HTML/CSS/JS chat interface with:
- Plus Jakarta Sans typography
- Suggestion chips for common queries
- Typing indicator with animated dots
- Auto-scrolling message container
- Responsive design for mobile
- GKE and Live status badges

### Phase 4: Containerization

**4.1 Multi-stage Dockerfile**
Stage 1 (builder): Installs Python dependencies into a prefix directory.
Stage 2 (runtime): Copies only installed packages from the builder. Creates a non-root user (`appuser`). No pip cache, no build tools in the final image. This reduces image size and attack surface.

**4.2 Artifact Registry**
Created `chatbot-repo` in us-central1 (same region as the GKE cluster for free, fast image pulls).

**4.3 Cloud Build**
Built and pushed the container image using `gcloud builds submit`. Cloud Build reads the Dockerfile, builds the image on Google's infrastructure, and pushes to Artifact Registry. No local Docker daemon needed.

### Phase 5: GKE Deployment

**5.1 Cluster creation**
Created a GKE Autopilot cluster (`retail-chatbot-cluster`) in us-central1. Autopilot mode means Google manages nodes, security patches, and infrastructure. Billing is per-pod (CPU + memory requested), not per-VM.

**5.2 Workload Identity setup**
Created GCP service account `retail-chatbot-sa` with two IAM roles:
- `roles/bigquery.dataViewer` (read table data)
- `roles/bigquery.jobUser` (execute queries)

Bound the Kubernetes service account (`retail-chatbot-ksa`) to the GCP service account via Workload Identity. This allows pods to authenticate to BigQuery without storing JSON key files.

**5.3 Kubernetes manifests (6 files)**

**ServiceAccount** (`k8s/service-account.yaml`): Annotated with the GCP service account email for Workload Identity binding.

**ConfigMap + Secret** (`k8s/config.yaml`): Project ID in ConfigMap (non-sensitive), API key in Secret (sensitive). Both injected as environment variables into pods.

**Deployment** (`k8s/deployment.yaml`): 2 replicas running the chatbot container with:
- Resource requests: 250m CPU, 512Mi memory
- Resource limits: 1000m CPU, 1Gi memory
- Liveness probe: GET /health every 15s
- Readiness probe: GET /ready every 10s
- Startup probe: GET /health every 5s (up to 60s for cold starts)
- Topology spread: pods on different nodes (maxSkew: 1)

**Service** (`k8s/service.yaml`): ClusterIP service routing port 80 to container port 8080. Internal-only; external access is through the Ingress.

**Ingress** (`k8s/ingress.yaml`): GCE HTTP(S) load balancer providing a public IP address. Routes all traffic to the Service.

**HPA** (`k8s/hpa.yaml`): Horizontal Pod Autoscaler with:
- Min 2, max 8 replicas
- Scale up at 70% CPU utilization (max 2 pods per scale event)
- Scale down at 80% memory utilization
- 5-minute stabilization window for scale-down (prevents flapping)

---

## Issues Encountered and Solutions

### Issue 1: Cloud Shell Authentication Timeout

**Problem:** After the GKE cluster creation (which took ~8 minutes), Cloud Shell's authentication token expired. Running `kubectl apply` returned: `You do not currently have an active account selected.`

**Root cause:** Cloud Shell sessions have an authentication timeout. Long-running operations like cluster creation can exceed this window.

**Solution:** Re-authenticated with `gcloud auth login`, then reconnected kubectl with `gcloud container clusters get-credentials retail-chatbot-cluster --region=us-central1`. All subsequent kubectl commands worked.

**Lesson:** Always re-authenticate after long operations. In production CI/CD, use service account keys or Workload Identity for non-interactive authentication.

### Issue 2: Jinja2 Template Syntax Conflict

**Problem:** The chat UI returned "Internal Server Error" (HTTP 500). Pod logs showed: `jinja2.exceptions.TemplateSyntaxError: Missing end of comment tag`

**Root cause:** The CSS in `chat.html` contained `{#chat}` as an ID selector. Jinja2 interprets `{#` as a comment opening tag, causing a syntax error during template compilation.

**Solution (v3):** Replaced Jinja2 template rendering with direct file reading. Changed `templates.TemplateResponse("chat.html", {"request": request})` to `HTMLResponse(content=open(html_path).read())`. This bypasses Jinja2 entirely since the HTML has no dynamic server-side content. The chat is fully client-side JavaScript.

**Lesson:** If your HTML does not need server-side template variables, serve it as a static file. Jinja2 template syntax (`{{ }}`, `{% %}`, `{# #}`) conflicts with CSS and JavaScript template literals.

### Issue 3: Gemini 2.0 Flash Deprecated

**Problem:** Chat queries returned "I'm having trouble right now." Pod logs showed: `404 This model models/gemini-2.0-flash is no longer available to new users.`

**Root cause:** The `gemini-2.0-flash` model was deprecated for new API keys between the time the project was designed and when it was built.

**Solution (v4):** Queried the Gemini API for available models, confirmed `gemini-2.5-flash` was available. Updated `src/chatbot.py` with `sed -i 's/gemini-2.0-flash/gemini-2.5-flash/'`, rebuilt the container, and redeployed.

**Lesson:** Always check model availability before deploying. In production, use model version pinning (e.g., `gemini-2.5-flash-001`) and have a fallback model configured.

### Issue 4: API Rate Limiting

**Problem:** Initial tests returned Gemini quota violations: `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`

**Root cause:** Multiple rapid test requests during debugging exceeded the free tier rate limit for the first API key.

**Solution:** Generated a new API key from AI Studio, updated the Kubernetes secret using `kubectl delete secret` followed by `kubectl create secret generic`, then restarted the deployment.

**Lesson:** Free tier rate limits are per-key and per-project. In production, use paid tier with higher limits. Implement client-side retry with exponential backoff for transient rate limit errors.

---

## ADK Chatbot vs. GKE Chatbot: Comparison

This project was built as a companion to a prior ADK (Agent Development Kit) Shopping Chatbot. Here is how they compare:

### Architecture

| Aspect | ADK Chatbot | GKE Chatbot |
|--------|------------|-------------|
| Framework | Google ADK with multi-agent routing | No framework. Direct Gemini API calls |
| Agent structure | Root agent + sub-agents (search, compare, recommend, order) | Single chatbot engine with intent classification |
| Tool system | ADK tool decorators (@tool) with 11 registered tools | Python functions called directly based on intent |
| Model | Gemini 2.5 Flash via ADK Runner | Gemini 2.5 Flash via google-generativeai SDK |
| Data | BigQuery product catalog | BigQuery product catalog (same schema concept, different data) |
| Serving | ADK dev server (`adk web .`) | FastAPI + Uvicorn |
| Deployment | Local Cloud Shell only | GKE Autopilot with load balancer |

### What ADK Provides That This Project Does Not

ADK handles agent orchestration, automatic tool selection, and multi-agent delegation. The ADK chatbot has a root agent that routes to specialized sub-agents (search agent, comparison agent, order agent). Each sub-agent has registered tools that ADK automatically selects based on the user's intent.

The GKE chatbot replaces all of this with a simpler two-step approach: classify intent with keywords, then run the appropriate BigQuery query. This trades ADK's sophisticated agent routing for predictable, debuggable behavior.

### What This Project Provides That ADK Does Not

| Capability | ADK Chatbot | GKE Chatbot |
|-----------|------------|-------------|
| Container packaging | None | Multi-stage Docker build |
| Kubernetes orchestration | None | Deployment, Service, Ingress, HPA |
| Autoscaling | None | 2 to 8 pods based on CPU/memory |
| High availability | Single process | 2+ pods on different nodes |
| Load balancing | None | GCE HTTP(S) Load Balancer |
| Health monitoring | None | Liveness, readiness, startup probes |
| Zero-trust security | ADK default auth | Workload Identity (no key files) |
| CI/CD pipeline | None | Cloud Build with Artifact Registry |
| External access | localhost only | Public IP via Ingress |
| Rolling updates | Restart required | Zero-downtime `kubectl set image` |

### When to Use Each

**Use ADK when:** You need complex multi-agent orchestration, automatic tool selection, or are prototyping conversational AI quickly. ADK excels at agent-to-agent delegation and provides guardrails for tool use.

**Use direct API + GKE when:** You need production deployment, autoscaling, high availability, and full control over the request pipeline. Better for production workloads where you want deterministic query behavior and infrastructure-level resilience.

**Combined approach (production ideal):** Use ADK for the agent logic, wrap it in FastAPI, containerize, and deploy to GKE. This gives you ADK's orchestration with GKE's infrastructure. The original project roadmap proposed this approach, but building them separately provides clearer learning of each component.

---

## Kubernetes Concepts Demonstrated

### Pods
The smallest deployable unit. Each pod runs one container (the chatbot). Pods are ephemeral and can be created, destroyed, and replaced at any time.

### Deployment
Declares the desired state: "I want 2 copies of my chatbot running." The Deployment controller continuously reconciles actual state with desired state. If a pod crashes, a new one is created automatically.

### Service (ClusterIP)
Provides a stable internal IP that routes to healthy pods. Since pods come and go (ephemeral IPs), the Service acts as a stable endpoint for internal routing.

### Ingress
Creates an external load balancer with a public IP. Routes internet traffic to the Service, which distributes it across pods. The GCE ingress class provisions a Google Cloud HTTP(S) Load Balancer.

### HPA (Horizontal Pod Autoscaler)
Watches resource utilization metrics. When average CPU exceeds 70%, it adds pods (up to 8). When load decreases, it removes pods (down to 2) with a 5-minute stabilization window to prevent flapping.

### Workload Identity
Binds a Kubernetes ServiceAccount to a GCP ServiceAccount. Pods running with that K8s SA automatically receive GCP credentials. No JSON key files stored anywhere.

### Topology Spread Constraints
Forces pods onto different nodes. If node A fails, pods on node B continue serving. Without this, both replicas could land on the same node, creating a single point of failure.

### Health Probes
- **Liveness:** "Is the process alive?" Failing this restarts the container.
- **Readiness:** "Can it handle traffic?" Failing this removes the pod from the Service's endpoints.
- **Startup:** "Has it finished initializing?" Prevents liveness probes from killing slow-starting containers.

---

## Files Reference

```
gke-retail-chatbot/
├── Dockerfile                    # Multi-stage production build
├── .dockerignore                 # Excludes non-runtime files
├── .gitignore                    # Python cache exclusions
├── cloudbuild.yaml               # CI/CD pipeline definition
├── requirements.txt              # Python dependencies
├── README.md                     # Project overview
├── data/
│   └── generate_catalog.py       # 500-product synthetic data generator
├── src/
│   ├── app.py                    # FastAPI server (5 endpoints)
│   ├── chatbot.py                # Gemini + BigQuery engine
│   └── templates/
│       └── chat.html             # Chat UI (single-file HTML/CSS/JS)
├── k8s/
│   ├── service-account.yaml      # Workload Identity K8s SA
│   ├── config.yaml               # ConfigMap + Secret
│   ├── deployment.yaml           # Pod spec, probes, resources, topology
│   ├── service.yaml              # ClusterIP internal routing
│   ├── ingress.yaml              # External load balancer
│   └── hpa.yaml                  # Autoscaling rules
├── scripts/
│   └── load-test.sh              # Concurrent request generator
└── docs/
    ├── ARCHITECTURE.md            # Architecture Decision Records
    ├── BUILD_GUIDE.md             # Step-by-step deployment commands
    └── QA_GUIDE.md                # Interview preparation Q&A
```

---

## Verification Results

All 24 automated checks passed:

- 4 GCP API checks (container, artifactregistry, cloudbuild, bigquery)
- 3 BigQuery checks (500 products, 6 categories, 99 on sale)
- 2 Artifact Registry checks (repo exists, image pushed)
- 1 GKE cluster check (RUNNING status)
- 7 Kubernetes resource checks (SA, ConfigMap, Secret, 2 pods, Service, Ingress, HPA)
- 5 external access checks (external IP assigned, /health 200, /ready 200, / 200, /chat returns valid response)
- 2 Workload Identity checks (GCP SA exists, binding configured)
