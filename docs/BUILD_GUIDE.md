# GKE Retail Chatbot -- Step-by-Step Build Guide

Every command below is run in **Cloud Shell**. Go in order. Each step has a verify command.

**Project ID:** gke-retail-chatbot
**Cost:** $15-30
**Time:** 2-3 hours

---

## PHASE 1: Setup (10 min)

### 1.1 Set project
```bash
gcloud config set project gke-retail-chatbot
```
Verify:
```bash
gcloud config get-value project
```

### 1.2 Enable APIs
```bash
gcloud services enable \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  --quiet
```

### 1.3 Create project files
```bash
mkdir -p gke-retail-chatbot/{k8s,src/templates,src/static,docs,scripts,data}
cd gke-retail-chatbot
```

---

## PHASE 2: BigQuery Data (5 min)

### 2.1 Generate product catalog
```bash
pip install google-cloud-bigquery --quiet
python data/generate_catalog.py
```
Verify:
```bash
bq query --use_legacy_sql=false \
  'SELECT category, COUNT(*) cnt FROM `gke-retail-chatbot.retail_store.product_catalog` GROUP BY category ORDER BY cnt DESC'
```

---

## PHASE 3: Build Container (5 min)

### 3.1 Create Artifact Registry
```bash
gcloud artifacts repositories create chatbot-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Retail chatbot images"
```

### 3.2 Build and push image
```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/gke-retail-chatbot/chatbot-repo/retail-chatbot:v1 \
  --timeout=600
```

---

## PHASE 4: Create GKE Cluster (10 min)

### 4.1 Create Autopilot cluster
```bash
gcloud container clusters create-auto retail-chatbot-cluster \
  --region=us-central1
```

### 4.2 Connect kubectl
```bash
gcloud container clusters get-credentials retail-chatbot-cluster \
  --region=us-central1
```

---

## PHASE 5: Security -- Workload Identity (5 min)

### 5.1 Create GCP service account
```bash
gcloud iam service-accounts create retail-chatbot-sa \
  --display-name="Retail Chatbot SA"
```

### 5.2 Grant BigQuery access
```bash
gcloud projects add-iam-policy-binding gke-retail-chatbot \
  --member="serviceAccount:retail-chatbot-sa@gke-retail-chatbot.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer" --quiet

gcloud projects add-iam-policy-binding gke-retail-chatbot \
  --member="serviceAccount:retail-chatbot-sa@gke-retail-chatbot.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser" --quiet
```

### 5.3 Bind K8s SA to GCP SA
```bash
gcloud iam service-accounts add-iam-policy-binding \
  retail-chatbot-sa@gke-retail-chatbot.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:gke-retail-chatbot.svc.id.goog[default/retail-chatbot-ksa]"
```

---

## PHASE 6: Deploy to GKE (10 min)

### 6.1 Set your API key
Get your key from https://aistudio.google.com/apikey then:
```bash
sed -i 's/REPLACE_WITH_YOUR_AI_STUDIO_KEY/YOUR_ACTUAL_KEY_HERE/' k8s/config.yaml
```

### 6.2 Apply manifests
```bash
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

### 6.3 Wait for pods
```bash
kubectl rollout status deployment/retail-chatbot --timeout=300s
```

### 6.4 Get external IP
```bash
kubectl get ingress retail-chatbot-ingress
```

---

## PHASE 7: Run Verification (2 min)
```bash
chmod +x scripts/verify.sh
./scripts/verify.sh
```

---

## PHASE 8: Screenshots

Capture before teardown:
1. Chat UI in browser (with a conversation)
2. `kubectl get pods -l app=retail-chatbot`
3. `kubectl get hpa retail-chatbot-hpa`
4. `kubectl get ingress retail-chatbot-ingress`
5. Verification script output (all green)

---

## PHASE 9: Teardown
```bash
chmod +x scripts/teardown.sh
./scripts/teardown.sh
```
Type DELETE when prompted. DO THIS IMMEDIATELY AFTER SCREENSHOTS.

---

## Troubleshooting

| Problem | Command | Fix |
|---------|---------|-----|
| Pod CrashLoopBackOff | `kubectl logs <pod>` | Missing env var or import error |
| Pod ImagePullBackOff | `kubectl describe pod <pod>` | Wrong image URI |
| Ingress no IP | `kubectl describe ingress retail-chatbot-ingress` | Wait 5 min |
| Chat errors | `kubectl logs -f deploy/retail-chatbot` | Check API key |
| BigQuery 403 | Check SA bindings | Re-run Phase 5 |
| Gemini 429 | Rate limited | Wait 60s, retry |

Emergency stop:
```bash
gcloud container clusters delete retail-chatbot-cluster --region=us-central1 --quiet
```
