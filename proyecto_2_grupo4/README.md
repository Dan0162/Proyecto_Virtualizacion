# Proyecto 2: Migración a Kubernetes (grupo-4)

La aplicación El Quetzal del Proyecto 1 se re-despliega en Kubernetes (k3s) dentro de la
VM `srv-elquetzal-grupo-4`. No se cambió el código ni el motor de base de datos
(PostgreSQL 16). Todos los recursos viven en el namespace `proyecto-2-grupo-4` y llevan el
sufijo `-grupo-4` y la etiqueta `equipo: grupo-4`.

> Nota sobre el nombre: el enunciado pide `proyecto_2_<idEquipo>`, pero Kubernetes solo
> acepta minúsculas, números y `-` en nombres de namespace (RFC 1123). Por eso el namespace
> es `proyecto-2-grupo-4`; la carpeta y la rama conservan el guion bajo (`proyecto_2_grupo4`).

## Traducción Compose a Kubernetes

| Proyecto 1 (Compose) | Proyecto 2 (Kubernetes) | Archivo |
|---|---|---|
| Contenedores | Deployments (Pod gestionado por ReplicaSet) | `04-db.yaml` `05-backends.yaml` `06-frontend.yaml` `07-gateway.yaml` |
| Volumen `db_data` | PersistentVolumeClaim `db-data-grupo-4` (local-path) | `04-db.yaml` |
| `.env` (no sensible) | ConfigMap `app-config-grupo-4` | `01-configmap-app.yaml` |
| `.env` (contraseñas) | Secret `db-credentials-grupo-4` | creado con `scripts/create-secret.sh` (no está en el repo) |
| Scripts `bd/init` | ConfigMap `db-init-grupo-4` montado en `/docker-entrypoint-initdb.d` | `03-configmap-db-init.yaml` |
| `nginx.conf` del gateway | ConfigMap `gateway-conf-grupo-4` | `02-configmap-gateway.yaml` |
| Red `internal` y puertos | Services ClusterIP / NodePort / LoadBalancer | en cada archivo |
| `proxy_pass` a nombres | `proxy_pass` al DNS del Service (`catalogo-grupo-4:5000`) | `02-configmap-gateway.yaml` |

## Arquitectura

```
navegador -> Service LoadBalancer :8080 / NodePort :30080
          -> Deployment gateway (nginx + ConfigMap)
               /            -> Service frontend-grupo-4 (2 réplicas)
               /api/<svc>/  -> Service <svc>-grupo-4 (catalogo inventario clientes pedidos reportes)
                                  -> Service db-grupo-4 -> Deployment Postgres + PVC
```

- Imágenes propias: `lu0512/elquetzal-{catalogo,inventario,clientes,pedidos,reportes,frontend}:k8s`.
  El gateway usa la imagen oficial `nginx:1.27-alpine` con su configuración en un ConfigMap.
- Los backends reciben `DB_HOST DB_PORT DB_NAME DB_USER` desde el ConfigMap y `DB_PASSWORD`
  desde el Secret. Las URLs entre servicios (`INVENTARIO_URL` etc.) también vienen del ConfigMap.
- El carné de cada integrante se siembra en `pedidos_db.integrantes` (`04-pedidos.sql`) y se
  muestra en la vista Pedidos.

## Despliegue

Prerrequisitos en la VM: k3s con `kubectl` funcionando y las imágenes disponibles.

```bash
# 1. construir imágenes (PUSH=1 las sube a Docker Hub, IMPORT=1 las carga en k3s)
cd proyecto_2_grupo4/scripts && IMPORT=1 ./build-images.sh
# 2. desplegar todo (crea namespace, Secret con contraseñas aleatorias y los manifiestos)
./deploy.sh
# 3. verificar
kubectl get all -n proyecto-2-grupo-4
kubectl get endpoints -n proyecto-2-grupo-4
```

El Secret nunca se guarda en el repositorio: `create-secret.sh` lo crea directamente en el
cluster con contraseñas generadas al azar (o tomadas de variables de entorno).

## Evidencia por criterio de la lista de cotejo

Cada captura debe mostrar el reloj del sistema y el carné.

| # | Criterio | Comando de evidencia |
|---|---|---|
| 1 | Namespace con todos los recursos | `kubectl get all -n proyecto-2-grupo-4` |
| 2 | Deployments con imágenes propias en Running | `kubectl get pods -n proyecto-2-grupo-4 -o wide` y `kubectl get deploy -n proyecto-2-grupo-4 -o wide` |
| 3 | PVC montado en la base | `kubectl get pvc -n proyecto-2-grupo-4` y `kubectl describe pod -l app=db -n proyecto-2-grupo-4` (sección Volumes) |
| 4 | Persistencia | crear un registro en la UI, `kubectl delete pod -l app=db -n proyecto-2-grupo-4`, esperar el nuevo Pod y comprobar que el registro sigue |
| 5 | ConfigMap consumido | `kubectl get cm app-config-grupo-4 -n proyecto-2-grupo-4 -o yaml` y `kubectl describe deploy catalogo-grupo-4 -n proyecto-2-grupo-4` |
| 6 | Secret fuera del repo | `kubectl get secret db-credentials-grupo-4 -n proyecto-2-grupo-4` (valores en base64) y `git grep -i password -- proyecto_2_grupo4` |
| 7 | Backend usa ConfigMap y Secret | `kubectl exec deploy/catalogo-grupo-4 -n proyecto-2-grupo-4 -- env \| grep DB_` |
| 8 | Escalado declarativo | editar `replicas` en `05-backends.yaml` o `06-frontend.yaml` y `kubectl apply -f ...` (no `kubectl scale`) |
| 9 | Autoreparación | `kubectl delete pod <pod-frontend> -n proyecto-2-grupo-4` y `kubectl get pods -w` |
| 10 | ClusterIP con endpoints | `kubectl get svc -n proyecto-2-grupo-4` y `kubectl get endpoints catalogo-grupo-4 -n proyecto-2-grupo-4` |
| 11 | NodePort y LoadBalancer | `kubectl get svc -n proyecto-2-grupo-4` y abrir `http://<IP-VM>:30080` y `http://<IP-VM>:8080/` (respaldo: `kubectl port-forward svc/gateway-lb-grupo-4 8080:80 -n proyecto-2-grupo-4`) |
| 12 | Rutas del gateway | `kubectl get cm gateway-conf-grupo-4 -n proyecto-2-grupo-4 -o yaml` |
| 13 | CRUD en el navegador | crear editar y eliminar un producto en Inventario y crear un pedido en Pedidos |

## Problemas encontrados

- `00-databases.sh` debe tener finales de línea LF; el repositorio lo fuerza con `.gitattributes`.
  El ConfigMap se genera desde los archivos LF.
- La base usa estrategia `Recreate` porque el PVC es `ReadWriteOnce`, y `PGDATA` apunta a un
  subdirectorio del volumen.
- Si un Service no responde y `get endpoints` sale vacío, revisar que el `selector` coincida con
  los labels del Pod.
- La VM original (1 CPU y 2 GB) no soportaba k3s con 9 Pods: el API server daba timeout. Se subió a 4 CPU y 4 GB.
- El LoadBalancer usa el puerto 8080 porque Traefik (incluido en k3s) ya ocupa el 80 de la VM.
- Los Services NodePort y LoadBalancer del gateway se aplican con `kubectl apply -f 07-gateway.yaml`; verificar con `kubectl get svc` que existan.
- Las imágenes locales se cargan en k3s con `docker save | sudo k3s ctr images import -` cuando
  no se usa Docker Hub.
