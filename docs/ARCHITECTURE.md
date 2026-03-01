# Architecture Decisions

## ADR-001: Direct Gemini API, No ADK
Use `google-generativeai` SDK directly. Single-concern chatbot does not need multi-agent orchestration. Simpler deps, smaller image, easier to debug.

## ADR-002: GKE Autopilot
Per-pod billing, Google-managed nodes, built-in security. More cost-efficient for a POC than Standard mode.

## ADR-003: FastAPI
Async-native (Gemini calls are I/O-bound), auto OpenAPI docs, better concurrency than Flask.

## ADR-004: Intent + SQL + Gemini (two-step)
Classify intent with keywords, run parameterized BigQuery SQL, send results to Gemini. Separates deterministic data retrieval from LLM generation. No text-to-SQL risk.

## ADR-005: Multi-stage Docker Build
Smaller image, no build artifacts, non-root user. GKE security best practice.

## ADR-006: Workload Identity
No JSON key files. Pods get GCP credentials automatically via K8s SA to GCP SA binding.

## ADR-007: Conservative HPA
70% CPU target, 5-min scale-down stabilization. Prevents flapping during bursty chat traffic.
