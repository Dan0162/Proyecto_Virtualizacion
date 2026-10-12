#!/bin/bash
# Construye las imagenes propias. Con PUSH=1 las sube a Docker Hub (docker login previo);
# con IMPORT=1 las importa al containerd de k3s (para correr sin acceso a Docker Hub).
set -euo pipefail
USER_HUB="${DOCKERHUB_USER:-lu0512}"; TAG="${TAG:-k8s}"
ROOT="$(cd "$(dirname "$0")/../../elquetzal" && pwd)"
for s in catalogo inventario clientes pedidos reportes; do
  docker build -t "$USER_HUB/elquetzal-$s:$TAG" "$ROOT/services/$s"
done
docker build -t "$USER_HUB/elquetzal-frontend:$TAG" "$ROOT/frontend"
for img in catalogo inventario clientes pedidos reportes frontend; do
  [ "${PUSH:-0}" = 1 ] && docker push "$USER_HUB/elquetzal-$img:$TAG"
  [ "${IMPORT:-0}" = 1 ] && docker save "$USER_HUB/elquetzal-$img:$TAG" | sudo k3s ctr images import -
done
true
