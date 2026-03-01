# QA Guide -- Interview Prep

**Q: Walk me through the Dockerfile.**
> Multi-stage. Builder installs deps into a prefix. Runtime copies only installed packages. Non-root user. No pip cache or build tools in final image.

**Q: Why GKE over Cloud Run?**
> Cloud Run is simpler. I chose GKE to demonstrate Kubernetes: HPA, health probes, topology spreading, Workload Identity, Ingress. These are senior cloud eng requirements.

**Q: What happens when a pod crashes?**
> Deployment controller detects replica count mismatch, schedules a new pod. Readiness probe blocks traffic until initialized. Service routes to surviving pod.

**Q: How does autoscaling work?**
> HPA watches CPU across pods. Over 70%, scale up (max 2 per event). Scale-down has 5-min stabilization to prevent flapping. Min 2, max 8 pods.

**Q: Why not text-to-SQL?**
> Security and reliability. I classify intent with keywords, run parameterized SQL, then send results to Gemini for formatting. Data retrieval is deterministic; LLM only handles conversation.

**Q: How do pods auth to BigQuery?**
> Workload Identity. K8s SA bound to GCP SA with BigQuery DataViewer + JobUser. No key files.

**Q: Why no agent framework (ADK, etc.)?**
> I built a separate project with ADK to learn multi-agent orchestration. For this project, the goal was demonstrating infrastructure: Docker, GKE, HPA, Workload Identity, Ingress, CI/CD. A framework would obscure those skills. The chatbot engine is 150 lines of transparent Python. In production, I would wrap ADK agent logic inside this same GKE infrastructure to get both.

**Q: What would you change for production?**
> Secret Manager for API keys, Redis for sessions, Cloud Armor WAF, custom domain + TLS, monitoring dashboards.
