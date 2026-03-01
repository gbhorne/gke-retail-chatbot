#!/usr/bin/env bash
set -uo pipefail
PROJECT_ID="gke-retail-chatbot"; REGION="us-central1"; CLUSTER="retail-chatbot-cluster"
DATASET="retail_store"; TABLE="product_catalog"; REPO="chatbot-repo"; IMAGE="retail-chatbot"
PASS=0; FAIL=0; TOTAL=0
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'
check() { TOTAL=$((TOTAL+1)); if [ "$2" -eq 0 ]; then PASS=$((PASS+1)); echo -e "  ${G} PASS${N}  $1"; else FAIL=$((FAIL+1)); echo -e "  ${R} FAIL${N}  $1"; fi; }
echo ""; echo -e "${C}${N}"
echo -e "${C}  GKE Retail Chatbot  Verification Report${N}"
echo -e "${C}  $(date '+%Y-%m-%d %H:%M:%S %Z')${N}"
echo -e "${C}${N}"
echo -e "\n${Y} GCP APIs${N}"
for api in container artifactregistry cloudbuild bigquery; do gcloud services list --enabled --filter="NAME:${api}.googleapis.com" --format="value(NAME)" 2>/dev/null | grep -q "$api"; check "${api} API enabled" $?; done
echo -e "\n${Y} BigQuery Product Catalog${N}"
PC=$(bq query --use_legacy_sql=false --format=csv --quiet "SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.${TABLE}\`" 2>/dev/null | tail -1)
[ "${PC:-0}" -ge 400 ] 2>/dev/null; check "Product catalog: ${PC:-0} products" $?
CC=$(bq query --use_legacy_sql=false --format=csv --quiet "SELECT COUNT(DISTINCT category) FROM \`${PROJECT_ID}.${DATASET}.${TABLE}\`" 2>/dev/null | tail -1)
[ "${CC:-0}" -ge 5 ] 2>/dev/null; check "Categories: ${CC:-0}" $?
SC=$(bq query --use_legacy_sql=false --format=csv --quiet "SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.${TABLE}\` WHERE sale_active = TRUE" 2>/dev/null | tail -1)
[ "${SC:-0}" -ge 50 ] 2>/dev/null; check "Products on sale: ${SC:-0}" $?
echo -e "\n${Y} Container Image${N}"
gcloud artifacts repositories describe ${REPO} --location=${REGION} 2>/dev/null | grep -q "${REPO}"; check "Artifact Registry repo exists" $?
gcloud artifacts docker images list "us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}" 2>/dev/null | grep -q "${IMAGE}"; check "Container image pushed" $?
echo -e "\n${Y} GKE Cluster${N}"
CS=$(gcloud container clusters describe ${CLUSTER} --region=${REGION} --format="value(status)" 2>/dev/null)
[ "$CS" = "RUNNING" ]; check "Cluster status: ${CS:-NOT FOUND}" $?
echo -e "\n${Y} Kubernetes Resources${N}"
kubectl get sa retail-chatbot-ksa 2>/dev/null | grep -q "retail-chatbot-ksa"; check "ServiceAccount" $?
kubectl get configmap retail-chatbot-config 2>/dev/null | grep -q "retail-chatbot-config"; check "ConfigMap" $?
kubectl get secret retail-chatbot-secrets 2>/dev/null | grep -q "retail-chatbot-secrets"; check "Secret" $?
RP=$(kubectl get pods -l app=retail-chatbot --no-headers 2>/dev/null | grep "Running" | grep "1/1" | wc -l)
[ "$RP" -ge 2 ]; check "Running pods: ${RP} (need 2)" $?
kubectl get svc retail-chatbot-svc 2>/dev/null | grep -q "retail-chatbot-svc"; check "Service" $?
kubectl get ingress retail-chatbot-ingress 2>/dev/null | grep -q "retail-chatbot-ingress"; check "Ingress" $?
kubectl get hpa retail-chatbot-hpa 2>/dev/null | grep -q "retail-chatbot-hpa"; check "HPA" $?
echo -e "\n${Y} External Access${N}"
EIP=$(kubectl get ingress retail-chatbot-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
[ -n "$EIP" ]; check "External IP: ${EIP:-PENDING}" $?
if [ -n "$EIP" ]; then
  HS=$(curl -s -o /dev/null -w "%{http_code}" "http://${EIP}/health" --max-time 10 2>/dev/null)
  [ "$HS" = "200" ]; check "GET /health -> ${HS:-timeout}" $?
  RS=$(curl -s -o /dev/null -w "%{http_code}" "http://${EIP}/ready" --max-time 10 2>/dev/null)
  [ "$RS" = "200" ]; check "GET /ready -> ${RS:-timeout}" $?
  US=$(curl -s -o /dev/null -w "%{http_code}" "http://${EIP}/" --max-time 10 2>/dev/null)
  [ "$US" = "200" ]; check "GET / (chat UI) -> ${US:-timeout}" $?
  CR=$(curl -s -X POST "http://${EIP}/chat" -H "Content-Type: application/json" -d '{"message":"Show me electronics under $50"}' --max-time 30 2>/dev/null)
  echo "$CR" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'reply' in d and len(d['reply'])>20" 2>/dev/null
  check "POST /chat returns valid response" $?
else echo -e "  ${Y} Skipping HTTP tests -- no external IP yet${N}"; fi
echo -e "\n${Y} Workload Identity${N}"
gcloud iam service-accounts describe retail-chatbot-sa@gke-retail-chatbot.iam.gserviceaccount.com 2>/dev/null | grep -q "retail-chatbot-sa"; check "GCP Service Account" $?
gcloud iam service-accounts get-iam-policy retail-chatbot-sa@gke-retail-chatbot.iam.gserviceaccount.com 2>/dev/null | grep -q "workloadIdentityUser"; check "Workload Identity binding" $?
echo ""; echo -e "${C}${N}"
if [ "$FAIL" -eq 0 ]; then echo -e "${G}  ALL ${TOTAL} CHECKS PASSED${N}"; else echo -e "${R}  ${FAIL}/${TOTAL} FAILED${N}  |  ${G}${PASS}/${TOTAL} PASSED${N}"; fi
echo -e "${C}${N}"
[ -n "${EIP:-}" ] && echo -e "\n  Chat UI:  ${C}http://${EIP}${N}\n  API docs: ${C}http://${EIP}/docs${N}"
echo -e "\n  Run ${R}./scripts/teardown.sh${N} when done!\n"
exit $FAIL
