#!/bin/bash
# Crea el Secret db-credentials-grupo-4 directamente en el cluster.
# Las contrasenas NO se guardan en el repositorio: se leen de variables de
# entorno o se generan al azar. Uso:
#   CATALOGO_DB_PASSWORD=... ./create-secret.sh   (o sin variables para generarlas)
set -euo pipefail
NS=proyecto-2-grupo-4
gen() { openssl rand -hex 12; }
kubectl -n "$NS" delete secret db-credentials-grupo-4 --ignore-not-found
kubectl -n "$NS" create secret generic db-credentials-grupo-4 \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(gen)}" \
  --from-literal=CATALOGO_DB_PASSWORD="${CATALOGO_DB_PASSWORD:-$(gen)}" \
  --from-literal=INVENTARIO_DB_PASSWORD="${INVENTARIO_DB_PASSWORD:-$(gen)}" \
  --from-literal=CLIENTES_DB_PASSWORD="${CLIENTES_DB_PASSWORD:-$(gen)}" \
  --from-literal=PEDIDOS_DB_PASSWORD="${PEDIDOS_DB_PASSWORD:-$(gen)}" \
  --from-literal=REPORTES_DB_PASSWORD="${REPORTES_DB_PASSWORD:-$(gen)}"
kubectl -n "$NS" label secret db-credentials-grupo-4 equipo=grupo-4 --overwrite
