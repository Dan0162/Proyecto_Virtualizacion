#!/usr/bin/env bash
# Construye y publica todas las imágenes propias de El Quetzal en Docker Hub.
#
# Requisitos:
#   - Haber corrido "docker login" (o tener sesión ya iniciada en Docker Desktop).
#   - Tener un archivo .env en la raíz del proyecto con DOCKERHUB_USER y TAG.
#
# Uso:
#   ./scripts/build-and-push.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DOCKERHUB_USER:?Falta DOCKERHUB_USER (definilo en .env)}"
TAG="${TAG:-latest}"

SERVICES=(catalogo inventario clientes pedidos reportes)

echo "==> Publicando como docker.io/${DOCKERHUB_USER}/elquetzal-*:${TAG}"

for svc in "${SERVICES[@]}"; do
  echo "--- Build: ${svc} ---"
  docker build -t "${DOCKERHUB_USER}/elquetzal-${svc}:${TAG}" "./services/${svc}"
  echo "--- Push: ${svc} ---"
  docker push "${DOCKERHUB_USER}/elquetzal-${svc}:${TAG}"
done

echo "--- Build: frontend ---"
docker build -t "${DOCKERHUB_USER}/elquetzal-frontend:${TAG}" ./frontend
echo "--- Push: frontend ---"
docker push "${DOCKERHUB_USER}/elquetzal-frontend:${TAG}"

echo "--- Build: gateway ---"
docker build -t "${DOCKERHUB_USER}/elquetzal-gateway:${TAG}" ./gateway
echo "--- Push: gateway ---"
docker push "${DOCKERHUB_USER}/elquetzal-gateway:${TAG}"

echo "==> Listo. Imágenes disponibles en:"
echo "    https://hub.docker.com/u/${DOCKERHUB_USER}"
