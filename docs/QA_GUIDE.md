# Project Q&A

### How does the Dockerfile work?

The build uses a multi-stage approach. The first stage installs Python dependencies into a prefix directory. The second stage copies only the installed packages from the first stage, creates a non-root user called `appuser`, and sets up the health check. The final image contains no pip cache, no build tools, and runs as an unprivileged user. This reduces the image size and limits the attack surface.

### Why was GKE chosen over Cloud Run?

Cloud Run would have been simpler for a single container deployment. GKE was chosen to demonstrate Kubernetes-level infrastructure: Horizontal Pod Autoscaling, liveness/readiness/startup probes, topology spread constraints across nodes, Workload Identity for keyless authentication, and Ingress-based load balancing. These are the components required for production workloads that need fine-grained control over scaling, availability, and traffic management.

### What happens if a pod crashes?

The Deployment controller detects that the actual replica count has dropped below the desired count (2) and schedules a replacement pod. While the new pod is starting, the readiness probe prevents traffic from being routed to it until it is fully initialized. Meanwhile, the Kubernetes Service continues routing requests to the surviving healthy pod, so users experience no downtime.

### How does autoscaling work in this project?

The Horizontal Pod Autoscaler monitors average CPU utilization across all pods. When it exceeds 70%, the HPA scales up by adding pods (maximum 2 per scale event, up to 8 total). When load drops, the HPA scales down, but with a 5-minute stabilization window to prevent flapping. This means the system waits 5 minutes after load decreases before removing pods, avoiding rapid scale-up/scale-down cycles during bursty traffic.

### Why was text-to-SQL not used for database queries?

Letting the LLM generate SQL directly introduces three risks: SQL injection from malformed output, unpredictable query costs if the LLM writes expensive full-table scans, and harder debugging when queries produce unexpected results. Instead, the chatbot classifies user intent with keyword matching, then builds parameterized SQL from pre-defined templates. Data retrieval is fully deterministic. Gemini only handles the conversational formatting of results that BigQuery already returned.

### How do pods authenticate to BigQuery without key files?

Through Workload Identity. A Kubernetes ServiceAccount (`retail-chatbot-ksa`) is bound to a GCP ServiceAccount (`retail-chatbot-sa`) that has BigQuery DataViewer and JobUser roles. When a pod runs with that Kubernetes ServiceAccount, GKE automatically provides GCP credentials to the pod. No JSON key files are stored anywhere in the container, the cluster, or the repository.

### Why was no agent framework used (ADK, LangChain, etc.)?

A separate project was built with Google ADK to learn multi-agent orchestration. For this project, the goal was demonstrating infrastructure: Docker multi-stage builds, GKE Autopilot, HPA autoscaling, Workload Identity, Ingress load balancing, and Cloud Build CI/CD. Using a framework would have added abstraction layers that obscure those infrastructure components. The chatbot engine is approximately 150 lines of transparent Python where every step is visible and auditable. In a production system, ADK or similar agent logic could be wrapped inside this same GKE infrastructure to combine both capabilities.

### What caused the Jinja2 template error and how was it fixed?

The CSS in `chat.html` contained `{#chat}` as an ID selector. Jinja2 interprets `{#` as the opening of a comment tag, which caused a `TemplateSyntaxError` at runtime. Since the HTML had no dynamic server-side content (the chat is entirely client-side JavaScript), the fix was to stop using Jinja2 entirely. The template rendering call was replaced with a simple file read: `HTMLResponse(content=open(html_path).read())`. This bypasses Jinja2 parsing completely.

### Why did the Gemini model return a 404 error?

The code was originally written for `gemini-2.0-flash`, which was deprecated for new API keys between the time the project was designed and when it was deployed. The fix involved querying the Gemini API for available models, confirming `gemini-2.5-flash` was available, updating the model string in `chatbot.py`, rebuilding the container image, and redeploying to GKE.

### What would need to change to make this fully production-ready?

Five things: Secret Manager instead of Kubernetes Secrets for API key management with automatic rotation. Redis or Firestore for session persistence, since the current in-memory sessions are lost when pods restart. Cloud Armor WAF for DDoS protection and rate limiting at the load balancer level. A custom domain with managed TLS certificates for HTTPS. And Cloud Monitoring dashboards for tracking latency, error rates, and pod health over time.
