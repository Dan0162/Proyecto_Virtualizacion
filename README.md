# Proyecto: El Quetzal - Arquitectura de Microservicios

Este proyecto implementa el backend de un sistema de gestión empresarial ("El Quetzal") basado en una arquitectura de microservicios contenerizados utilizando Docker y Docker Compose.

## Arquitectura y Lógica Implementada

El backend está compuesto por las siguientes piezas fundamentales:

1. **API Gateway (Nginx):** Actúa como único punto de entrada para el cliente en el puerto `80`. Se encarga de enrutar las peticiones (`/api/catalogo/`, `/api/inventario/`, etc.) hacia el microservicio interno correspondiente, manteniendo los puertos de los microservicios aislados del exterior.
2. **Microservicios (Python + Flask):** Existen 5 microservicios independientes. Cada uno expone una API RESTFul para gestionar su propio dominio.
   - **Catálogo:** Gestión de los productos disponibles.
   - **Inventario:** Gestión de existencias y niveles mínimos de stock.
   - **Clientes:** Gestión de los datos de los compradores.
   - **Pedidos:** Registro de órdenes de compra cruzando datos de clientes y productos.
   - **Reportes:** Un servicio de sólo lectura que consulta paralelamente los catálogos, inventarios y pedidos para consolidar un reporte gerencial.
3. **Base de Datos (PostgreSQL):** Un único contenedor de Postgres, pero configurado de forma segura mediante un script de inicialización (`00-databases.sh`) que crea **bases de datos y roles independientes** para cada microservicio. Los servicios sólo tienen permisos para acceder a su propia base de datos (con contraseñas inyectadas por variables de entorno), asegurando un aislamiento total de los datos.

## Cómo levantar el proyecto

Nunca hay contraseñas quemadas en el código: no hay plantillas `.env.example` en el repo (se quitaron una vez el equipo configuró sus `.env` reales), así que cada quien crea estos archivos directamente, a mano. Los `.env` reales están en `.gitignore`, nunca se commitean.

1. `elquetzal/.env` (junto a `docker-compose.yml`) — lo lee Compose para sustituir `${...}` y se lo pasa al contenedor `db`:
   ```
   DOCKERHUB_USER=<usuario de Docker Hub del grupo>
   TAG=latest
   PG_SUPERUSER=postgres
   PG_SUPERUSER_PASSWORD=<password del superusuario de Postgres>
   CATALOGO_DB_PASSWORD=<password de catalogo_user>
   INVENTARIO_DB_PASSWORD=<password de inventario_user>
   CLIENTES_DB_PASSWORD=<password de clientes_user>
   PEDIDOS_DB_PASSWORD=<password de pedidos_user>
   REPORTES_DB_PASSWORD=<password de reportes_user>
   ```
2. `elquetzal/services/<servicio>/.env` — cómo se conecta cada microservicio a **su** base (mismo esquema para `catalogo`, `inventario`, `clientes`, `pedidos`, `reportes`):
   ```
   DB_HOST=db
   DB_PORT=5432
   DB_NAME=<servicio>_db
   DB_USER=<servicio>_user
   DB_PASSWORD=<debe ser igual a <SERVICIO>_DB_PASSWORD del .env de la raíz>
   ```
   `reportes/.env` no necesita nada extra: `reportes_user` ya tiene acceso de solo lectura a `catalogo_db`, `inventario_db` y `pedidos_db` (ver [Base de Datos](#base-de-datos-área-4)), así que reutiliza estas mismas 5 líneas para las 4 bases.

Con los `.env` listos:

```bash
docker compose up -d --build
```

### Probar solo la base de datos (sin levantar todo el stack)

```bash
docker compose up -d db
docker exec -it elquetzal-db psql -U pedidos_user -d pedidos_db -c "select * from integrantes;"
```

### Volver a sembrar los datos

Los scripts de `elquetzal/bd/init/` solo corren si el volumen está vacío. Para forzar que vuelvan a correr en desarrollo (esto borra todos los datos):

```bash
docker compose down -v
docker compose up -d db
```

---

## Base de Datos (Área 4)

Un solo motor Postgres (`postgres:16-alpine`), con **una base de datos y un rol independientes por microservicio**. Los scripts en `elquetzal/bd/init/` se montan en `/docker-entrypoint-initdb.d` del contenedor `db` y corren una sola vez, la primera vez que arrancan con el volumen `db_data` vacío.

| Orden | Script | Qué hace |
|---|---|---|
| `00-databases.sh` | Crea los 5 roles y las 5 bases de datos (uno por servicio) |
| `01-catalogo.sql` | Esquema + seed de `catalogo_db` |
| `02-inventario.sql` | Esquema + seed de `inventario_db` |
| `03-clientes.sql` | Esquema + seed de `clientes_db` |
| `04-pedidos.sql` | Esquema + seed de `pedidos_db`, incluye la tabla `integrantes` (evidencia de carnés) |
| `05-reportes.sql` | Solo comentario — rol/BD ya creados, sin esquema propio |

Cada base solo es accesible por su propio rol (`catalogo_user`, `inventario_user`, `clientes_user`, `pedidos_user`, `reportes_user`); las tablas quedan creadas directamente por ese rol (`SET ROLE ... RESET ROLE` dentro de cada script), no por el superusuario.

### Modelo de datos por servicio

**catalogo_db** — datos maestros de producto (sin stock):
- `productos(id, sku UNIQUE, nombre, categoria, precio_q, creado_en)`

**inventario_db** — cantidades en existencia:
- `stock(id, sku UNIQUE, cantidad, stock_minimo, actualizado_en)`
- Seed incluye 2 SKUs por debajo de `stock_minimo` a propósito, para demostrar la alerta de stock bajo del dashboard.

**clientes_db**:
- `clientes(id, nombre, nit UNIQUE, telefono, email, direccion, creado_en)`

**pedidos_db**:
- `integrantes(carne PK, nombre)` — los 5 carnés del equipo (evidencia personalizada requerida por el enunciado).
- `pedidos(id, cliente_id, carne_integrante FK → integrantes, estado, creado_en)`
- `detalle_pedido(id, pedido_id FK → pedidos, sku, cantidad, precio_unitario_q)`

**reportes_db** — sin tablas propias y sin acceso a las demás bases: `reportes` arma el dashboard llamando a las APIs de `catalogo`, `inventario` y `pedidos` (no lee sus bases de datos directamente), así que `reportes_user` solo tiene permisos sobre `reportes_db`. Si esa lógica necesita persistir algo propio (p. ej. una tabla de caché de métricas), se puede crear ahí siguiendo el patrón comentado en `05-reportes.sql`.

### Sobre las referencias entre servicios

`pedidos.cliente_id` y `detalle_pedido.sku` son referencias **lógicas** a `clientes_db.clientes.id` y `catalogo_db.productos.sku`: no existen FKs reales porque cada microservicio tiene su propia base de datos aislada. Toda validación cruzada (¿alcanza el stock?, métricas del dashboard) la hacen los backends (Área 5) llamando a las APIs de los otros microservicios, nunca conectándose directo a una base ajena.

---

## Documentación de Endpoints

Todos los endpoints están prefijados por el API Gateway. La base de la URL asume que estás corriendo el proyecto localmente: `http://localhost/api/`

### 1. Catálogo (`/api/catalogo`)

* **GET `/productos`**
  * **Descripción:** Obtiene todos los productos.
  * **Respuesta Esperada (200 OK):**
    ```json
    {
      "productos": [
        { "sku": "QT-0001", "nombre": "Café", "categoria": "Abarrotes", "precio_q": 45.0 }
      ]
    }
    ```

* **GET `/productos/<sku>`**
  * **Descripción:** Obtiene un producto por su código SKU.

* **POST `/productos`**
  * **Descripción:** Crea un nuevo producto.
  * **Body (JSON):**
    ```json
    {
      "sku": "TEST-100",
      "nombre": "Monitor",
      "categoria": "Electrónica",
      "precio_q": 1500.00
    }
    ```

* **PUT `/productos/<sku>`**
  * **Descripción:** Modifica `nombre`, `categoria` o `precio_q`. El `sku` va en la URL.
  * **Body (JSON):**
    ```json
    { "precio_q": 1200.00 }
    ```

* **DELETE `/productos/<sku>`**
  * **Descripción:** Elimina un producto.

### 2. Inventario (`/api/inventario`)

* **GET `/stock`**
  * **Descripción:** Devuelve los niveles de stock de todos los productos.

* **GET `/stock/<sku>`**
  * **Descripción:** Devuelve el stock de un producto específico.

* **POST `/stock`**
  * **Descripción:** Registra inventario inicial.
  * **Body (JSON):**
    ```json
    {
      "sku": "TEST-100",
      "cantidad": 50,
      "stock_minimo": 10
    }
    ```

* **PUT `/stock/<sku>`**
  * **Descripción:** Actualiza cantidades de un producto.
  * **Body (JSON):**
    ```json
    { "cantidad": 45 }
    ```

* **DELETE `/stock/<sku>`**
  * **Descripción:** Elimina el registro de inventario de un producto.

### 3. Clientes (`/api/clientes/clientes`)

* **GET `/clientes`**
  * **Descripción:** Devuelve el listado de clientes registrados.

* **GET `/clientes/<id>`**
  * **Descripción:** Obtiene detalles de un cliente por ID interno.

* **POST `/clientes`**
  * **Descripción:** Registra un nuevo cliente. (`nombre` es obligatorio).
  * **Body (JSON):**
    ```json
    {
      "nombre": "Juan Pérez",
      "nit": "123456-7",
      "telefono": "5555-4444",
      "email": "juanperez@example.com",
      "direccion": "Zona 10"
    }
    ```

* **PUT `/clientes/<id>`**
  * **Descripción:** Actualiza cualquier campo del cliente (excepto su ID).

* **DELETE `/clientes/<id>`**
  * **Descripción:** Elimina un cliente.

### 4. Pedidos (`/api/pedidos`)

* **GET `/`**
  * **Descripción:** Devuelve el historial completo de pedidos con sus detalles de compra.

* **GET `/<id>`**
  * **Descripción:** Devuelve un pedido específico.

* **POST `/`**
  * **Descripción:** Genera una nueva orden de compra, insertando también el detalle de los productos.
  * **Body (JSON):**
    ```json
    {
      "cliente_id": 1,
      "carne_integrante": "202300001",
      "estado": "pendiente",
      "detalles": [
        {
          "sku": "QT-0001",
          "cantidad": 2,
          "precio_unitario_q": 45.00
        }
      ]
    }
    ```

### 5. Reportes (`/api/reportes`)

* **GET `/`**
  * **Descripción:** Devuelve un reporte consolidado. Consulta de forma paralela las bases de datos de Catálogo, Inventario y Pedidos para entregar una radiografía financiera y de stock del negocio en un momento dado.
  * **Query Params (Opcional):** `?fecha=YYYY-MM-DD` (Para ver los pedidos de un día específico. Por defecto usa el día actual).
  * **Respuesta Esperada:**
    ```json
    {
      "fecha": "2023-10-25",
      "resumen": {
        "total_productos": 15,
        "valor_total_inventario_q": 45000.50,
        "pedidos_del_dia": 3
      },
      "alertas_stock_bajo": [
        {
          "sku": "QT-0005",
          "nombre": "Papel higiénico",
          "categoria": "Limpieza",
          "cantidad": 5,
          "stock_minimo": 10
        }
      ]
    }
    ```
# Publicación de imágenes en Docker Hub 

## 1. Crear cuenta / namespace del grupo

Uno de los integrantes crea (o ya tiene) una cuenta en https://hub.docker.com.
Ese usuario (o una organización creada ahí) es el `DOCKERHUB_USER` que va en
el `.env` de la raíz.

## 2. Login desde la VM (o el host, si el build se hace ahí)

```bash
docker login -u <usuario_dockerhub>
```

Pide el password o, mejor, un **Access Token** (Docker Hub → Account
Settings → Security → New Access Token) para no guardar la contraseña real
en ningún lado.

## 3. Completar el .env

En `elquetzal/.env` (ver [Cómo levantar el proyecto](#cómo-levantar-el-proyecto)), editar `DOCKERHUB_USER` y `TAG`.

## 4. Build + push de todas las imágenes

Opción A — script automático (recomendado):

```bash
./scripts/build-and-push.sh
```

Opción B — manual, servicio por servicio:

```bash
docker build -t <usuario>/elquetzal-catalogo:latest ./services/catalogo
docker push <usuario>/elquetzal-catalogo:latest
# repetir para inventario, clientes, pedidos, reportes
docker build -t <usuario>/elquetzal-gateway:latest -f gateway/Dockerfile .
docker push <usuario>/elquetzal-gateway:latest
```

## 5. Verificar

Abrir `https://hub.docker.com/u/<usuario_dockerhub>` y confirmar que
aparecen los 6 repositorios (`elquetzal-catalogo`, `elquetzal-inventario`,
`elquetzal-clientes`, `elquetzal-pedidos`, `elquetzal-reportes`,
`elquetzal-gateway`). Esa URL es la evidencia a incluir en la entrega.

## 6. Levantar el stack usando las imágenes publicadas (no build local)

Para la demo en vivo, una vez publicadas las imágenes, `docker compose up`
puede usar directamente las imágenes de Docker Hub en lugar de reconstruir,
quitando el bloque `build:` de cada servicio o corriendo:

```bash
docker compose pull
docker compose up -d
```

## Convención de nombres y tags

| Imagen                          | Repositorio en Docker Hub              |
|----------------------------------|-----------------------------------------|
| gateway                          | `<usuario>/elquetzal-gateway`           |
| catalogo                         | `<usuario>/elquetzal-catalogo`          |
| inventario                       | `<usuario>/elquetzal-inventario`        |
| clientes                         | `<usuario>/elquetzal-clientes`          |
| pedidos                          | `<usuario>/elquetzal-pedidos`           |
| reportes                         | `<usuario>/elquetzal-reportes`          |

`TAG` por defecto es `latest`; para versionar releases de la demo se puede
usar `TAG=s12` u otro identificador al correr el script.
