# GKE Retail Chatbot: Complete Project Documentation

## Executive Summary

This project delivers a production-grade ecommerce retail chatbot deployed on Google Kubernetes Engine (GKE Autopilot). The chatbot helps customers find products, compare options, discover deals, and check stock across 500 products in 6 categories. It uses Gemini 2.5 Flash for natural language conversation and BigQuery as the product catalog database. No agent frameworks were used. The entire system was built with clean Python (FastAPI), containerized with Docker, and orchestrated with Kubernetes.

**Key Metrics:**
- 24/24 verification checks passed
- 500 products across 6 categories (electronics, clothing, home, sports, beauty, grocery)
- 2-pod deployment with autoscaling to 8 pods
- Sub-2-second response times on product queries
- Complete teardown verified with zero residual resources
- Total cost: under $3 from $300 free trial credits

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

Created GCP project `gke-retail-chatbot`. Linked to a billing account with $300 free trial credits. Set a $25 budget alert with email notifications. Enabled four GCP APIs: Kubernetes Engine, Artifact Registry, Cloud Build, and BigQuery.

### Phase 2: Data Layer

Wrote a Python script that generates 500 retail products with realistic attributes: 6 categories with 7 subcategories each, 6 fictional brands per category (36 total), realistic price distributions per category, 20% of products randomly on sale (10-40% off), 8% out of stock, ratings between 2.5 and 5.0 with correlated review counts.

22-field BigQuery schema covering product identity, pricing, inventory, ratings, and metadata. Data loaded via `load_table_from_json` with WRITE_TRUNCATE for idempotent reruns.

### Phase 3: Application Code

**Chatbot engine:** Two-step architecture separating data retrieval from language generation. Intent classification using keyword matching across seven types (search, compare, deals, stock, recommend, browse, general). Parameterized SQL generation with dynamic filters for category, price, color, and brand. No text-to-SQL.

**Web server:** FastAPI with five endpoints: chat UI, chat API, health probe, readiness probe, and auto-generated OpenAPI docs. In-memory session storage with 20-turn history.

**Chat UI:** Single-file HTML/CSS/JS with Plus Jakarta Sans typography, suggestion chips, typing indicator, and responsive design.

### Phase 4: Containerization

Multi-stage Dockerfile. Stage 1 installs dependencies. Stage 2 copies only installed packages, creates non-root user. Built with Cloud Build and pushed to Artifact Registry in us-central1.

### Phase 5: GKE Deployment

Created GKE Autopilot cluster. Set up Workload Identity (GCP SA with BigQuery roles bound to K8s SA). Applied 6 Kubernetes manifests: ServiceAccount, ConfigMap + Secret, Deployment (2 replicas with health probes and topology spread), Service (ClusterIP), Ingress (external LB), HPA (2-8 pods).

---

## Issues Encountered and Solutions

### Issue 1: Cloud Shell Authentication Timeout

**Problem:** After the GKE cluster creation (which took 8 minutes), Cloud Shell's authentication token expired. Running `kubectl apply` returned: `You do not currently have an active account selected.`

**Root cause:** Cloud Shell sessions have an authentication timeout. Long-running operations like cluster creation can exceed this window.

**Solution:** Re-authenticated with `gcloud auth login`, then reconnected kubectl with `gcloud container clusters get-credentials`.

**Lesson:** Always re-authenticate after long operations. In production CI/CD, use service account keys or Workload Identity for non-interactive authentication.

### Issue 2: Jinja2 Template Syntax Conflict

**Problem:** The chat UI returned "Internal Server Error" (HTTP 500). Pod logs showed: `jinja2.exceptions.TemplateSyntaxError: Missing end of comment tag`

**Root cause:** The CSS in `chat.html` contained `{#chat}` as an ID selector. Jinja2 interprets `{#` as a comment opening tag, causing a syntax error during template compilation.

**Solution (v3):** Replaced Jinja2 template rendering with direct file reading. Changed `templates.TemplateResponse()` to `HTMLResponse(content=open(html_path).read())`. This bypasses Jinja2 entirely since the HTML has no dynamic server-side content.

**Lesson:** If your HTML does not need server-side template variables, serve it as a static file. Jinja2 template syntax conflicts with CSS and JavaScript.

### Issue 3: Gemini 2.0 Flash Deprecated

**Problem:** Chat queries returned "I'm having trouble right now." Pod logs showed: `404 This model models/gemini-2.0-flash is no longer available to new users.`

**Root cause:** The `gemini-2.0-flash` model was deprecated for new API keys between the time the project was designed and when it was built.

**Solution (v4):** Queried the Gemini API for available models, confirmed `gemini-2.5-flash` was available. Updated `src/chatbot.py`, rebuilt the container, and redeployed.

**Lesson:** Always check model availability before deploying. In production, use model version pinning and have a fallback model configured.

### Issue 4: API Rate Limiting

**Problem:** Initial tests returned Gemini quota violations for the free tier.

**Root cause:** Multiple rapid test requests during debugging exceeded the free tier rate limit for the first API key.

**Solution:** Generated a new API key from AI Studio, updated the Kubernetes secret, then restarted the deployment.

**Lesson:** Free tier rate limits are per-key and per-project. In production, use paid tier with higher limits. Implement retry with exponential backoff.

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

**Combined approach (production ideal):** Use ADK for the agent logic, wrap it in FastAPI, containerize, and deploy to GKE. This gives you ADK's orchestration with GKE's infrastructure.

---

## Kubernetes Concepts Demonstrated

**Pods:** The smallest deployable unit. Each pod runs one container (the chatbot). Pods are ephemeral and can be replaced at any time.

**Deployment:** Declares the desired state: "I want 2 copies of my chatbot running." The controller continuously reconciles actual state with desired state.

**Service (ClusterIP):** Provides a stable internal IP that routes to healthy pods. Acts as a stable endpoint since pods have ephemeral IPs.

**Ingress:** Creates an external load balancer with a public IP. Routes internet traffic to the Service.

**HPA:** Watches resource utilization. When average CPU exceeds 70%, it adds pods (up to 8). Scale-down has 5-minute stabilization.

**Workload Identity:** Binds a K8s SA to a GCP SA. Pods automatically receive GCP credentials. No JSON key files.

**Topology Spread:** Forces pods onto different nodes. If one node fails, pods on the other continue serving.

**Health Probes:** Liveness (is the process alive?), Readiness (can it handle traffic?), Startup (has it finished initializing?).

---

## Cost Analysis

| Resource | Duration | Cost |
|----------|----------|------|
| GKE Autopilot (2 pods) | ~2 hours | ~$2.50 |
| GCE Load Balancer | ~2 hours | ~$0.05 |
| Cloud Build (4 builds) | 4 minutes total | ~$0.02 |
| Artifact Registry storage | ~200MB | ~$0.02 |
| BigQuery (queries) | ~50 queries | $0 (free tier) |
| AI Studio (Gemini 2.5 Flash) | ~100 requests | $0 (free tier) |
| **Total** | | **~$2.59** |

---

## Verification Results

All 24 automated checks passed:

- 4 GCP API checks (container, artifactregistry, cloudbuild, bigquery)
- 3 BigQuery checks (500 products, 6 categories, 99 on sale)
- 2 Artifact Registry checks (repo exists, image pushed)
- 1 GKE cluster check (RUNNING status)
- 7 Kubernetes resource checks (SA, ConfigMap, Secret, 2 pods, Service, Ingress, HPA)
- 5 external access checks (external IP, /health 200, /ready 200, / 200, /chat valid response)
- 2 Workload Identity checks (GCP SA exists, binding configured)

---

## Teardown Verification

All 4 resource groups confirmed deleted:
- GKE cluster: DELETED
- Artifact Registry: DELETED
- Service Account: DELETED
- BigQuery dataset: DELETED

Billing confirmed stopped. Zero residual resources.
