#!/bin/bash
# Crea secret.yaml (local, ignorado por git) con contrasenas aleatorias a partir de la
# plantilla. Si ya existe no lo toca: Postgres crea los roles solo en el primer arranque,
# asi que cambiar las contrasenas despues deja el Secret distinto a la base.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f secret.yaml ]; then echo "secret.yaml ya existe, se conserva"; exit 0; fi
while IFS= read -r line; do
  case "$line" in
    *": CAMBIAR") echo "${line%CAMBIAR}$(openssl rand -hex 12)" ;;
    *) echo "$line" ;;
  esac
done < plantilla-credenciales.yaml | grep -v '^# ' > secret.yaml
echo "secret.yaml generado (no se sube al repositorio)"
