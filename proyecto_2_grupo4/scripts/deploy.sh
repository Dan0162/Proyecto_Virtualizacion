#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
kubectl apply -f 00-namespace.yaml
if [ -f secrets.yaml ]; then
  kubectl apply -f secrets.yaml
else
  ./scripts/create-secret.sh
fi
kubectl apply -f 01-configmap-app.yaml -f 02-configmap-gateway.yaml -f 03-configmap-db-init.yaml
kubectl apply -f 04-db.yaml
kubectl apply -f 05-backends.yaml -f 06-frontend.yaml -f 07-gateway.yaml
kubectl -n proyecto-2-grupo-4 get all
