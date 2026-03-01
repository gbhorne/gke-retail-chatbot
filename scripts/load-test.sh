#!/usr/bin/env bash
set -euo pipefail
EIP=$(kubectl get ingress retail-chatbot-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
[ -z "$EIP" ] && { echo "No external IP yet"; exit 1; }
NUM="${1:-100}"; CONC="${2:-10}"
echo "Load test: http://${EIP}/chat  (${NUM} reqs, ${CONC} concurrent)"
echo "Watch: kubectl get hpa --watch"; echo ""
MSGS=('{"message":"electronics under $100"}' '{"message":"best deals"}' '{"message":"compare headphones"}' '{"message":"sports gear on sale"}' '{"message":"show me laptops"}')
for i in $(seq 1 "$NUM"); do
  curl -s -o /dev/null -w "req=${i} status=%{http_code} time=%{time_total}s\n" \
    -X POST "http://${EIP}/chat" -H "Content-Type: application/json" \
    -d "${MSGS[$((RANDOM % ${#MSGS[@]}))]}" &
  (( i % CONC == 0 )) && wait
done; wait
echo -e "\nDone. Check: kubectl get hpa retail-chatbot-hpa"
