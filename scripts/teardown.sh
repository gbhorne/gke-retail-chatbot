#!/usr/bin/env bash
set -uo pipefail
PROJECT_ID="gke-retail-chatbot"; REGION="us-central1"; CLUSTER="retail-chatbot-cluster"
REPO="chatbot-repo"; GSA="retail-chatbot-sa"; DATASET="retail_store"
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; N='\033[0m'
echo ""; echo -e "${R}${N}"
echo -e "${R}  TEARDOWN -- GKE Retail Chatbot${N}"
echo -e "${R}${N}"
echo ""; echo "Will delete: GKE cluster, Artifact Registry, Service Account, BigQuery dataset"
echo ""; read -p "Type DELETE to confirm: " confirm
[ "$confirm" = "DELETE" ] || { echo "Cancelled."; exit 0; }
echo ""
echo -e "${Y} 1/4 Deleting GKE cluster (3-5 min)${N}"
if gcloud container clusters describe ${CLUSTER} --region=${REGION} 2>/dev/null | grep -q "RUNNING"; then
  gcloud container clusters delete ${CLUSTER} --region=${REGION} --quiet; echo -e "  ${G}Cluster deleted${N}"
else echo -e "  ${G}Already gone${N}"; fi
echo -e "\n${Y} 2/4 Deleting Artifact Registry${N}"
if gcloud artifacts repositories describe ${REPO} --location=${REGION} 2>/dev/null | grep -q "${REPO}"; then
  gcloud artifacts repositories delete ${REPO} --location=${REGION} --quiet; echo -e "  ${G}Repo deleted${N}"
else echo -e "  ${G}Already gone${N}"; fi
echo -e "\n${Y} 3/4 Deleting service account${N}"
GSA_EMAIL="${GSA}@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe ${GSA_EMAIL} 2>/dev/null | grep -q "${GSA}"; then
  gcloud iam service-accounts delete ${GSA_EMAIL} --quiet; echo -e "  ${G}SA deleted${N}"
else echo -e "  ${G}Already gone${N}"; fi
echo -e "\n${Y} 4/4 Deleting BigQuery dataset${N}"
if bq show --dataset "${PROJECT_ID}:${DATASET}" 2>/dev/null | grep -q "${DATASET}"; then
  bq rm -r -f -d "${PROJECT_ID}:${DATASET}"; echo -e "  ${G}Dataset deleted${N}"
else echo -e "  ${G}Already gone${N}"; fi
echo ""; echo -e "${C}${N}"
echo -e "${C}  Teardown Verification${N}"; echo -e "${C}${N}"; echo ""
CLEAN=true
gcloud container clusters list --region=${REGION} --format="value(name)" 2>/dev/null | grep -q "${CLUSTER}" && { echo -e "  ${R}CLUSTER STILL EXISTS${N}"; CLEAN=false; } || echo -e "  ${G}Cluster: DELETED${N}"
gcloud artifacts repositories list --location=${REGION} --format="value(name)" 2>/dev/null | grep -q "${REPO}" && { echo -e "  ${R}REPO STILL EXISTS${N}"; CLEAN=false; } || echo -e "  ${G}Artifact Registry: DELETED${N}"
gcloud iam service-accounts list --format="value(email)" 2>/dev/null | grep -q "${GSA}" && { echo -e "  ${R}SA STILL EXISTS${N}"; CLEAN=false; } || echo -e "  ${G}Service Account: DELETED${N}"
bq ls --dataset "${PROJECT_ID}:" 2>/dev/null | grep -q "${DATASET}" && { echo -e "  ${R}DATASET STILL EXISTS${N}"; CLEAN=false; } || echo -e "  ${G}BigQuery: DELETED${N}"
echo ""
if [ "$CLEAN" = true ]; then echo -e "${G}  ALL RESOURCES DELETED -- BILLING STOPPED${N}"; else echo -e "${R}  SOME RESOURCES REMAIN${N}"; fi
echo ""
