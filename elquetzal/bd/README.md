# Datos (Área 4)

Un solo motor Postgres (`postgres:16-alpine`), con **una base de datos y un
rol independientes por microservicio**. Los scripts en `init/` se montan en
`/docker-entrypoint-initdb.d` del contenedor `db` y corren una sola vez, la
primera vez que arrancan con el volumen `db_data` vacío.

| Orden | Script | Qué hace |
|---|---|---|
| `00-databases.sh` | Crea los 5 roles y las 5 bases de datos (uno por servicio) |
| `01-catalogo.sql` | Esquema + seed de `catalogo_db` |
| `02-inventario.sql` | Esquema + seed de `inventario_db` |
| `03-clientes.sql` | Esquema + seed de `clientes_db` |
| `04-pedidos.sql` | Esquema + seed de `pedidos_db`, incluye la tabla `integrantes` (evidencia de carnés) |
| `05-reportes.sql` | Solo comentario — rol/BD ya creados, sin esquema propio |

Cada base solo es accesible por su propio rol (`catalogo_user`,
`inventario_user`, `clientes_user`, `pedidos_user`, `reportes_user`); las
tablas quedan creadas directamente por ese rol (`SET ROLE ... RESET ROLE`
dentro de cada script), no por el superusuario.

## Configurar credenciales

Nunca hay contraseñas quemadas en el código. Hay que copiar las plantillas
`.env.example` a `.env` y llenarlas (los `.env` reales están en
`.gitignore`, no se commitean):

1. `elquetzal/.env.example` → `elquetzal/.env` — contraseña de cada base de
   datos (las lee el contenedor `db` para crear los roles) + credenciales
   de Docker Hub.
2. `elquetzal/services/<servicio>/.env.example` → `.env` en esa misma
   carpeta — cómo se conecta cada microservicio a **su** base. El password
   de cada uno debe coincidir con el que se puso en el `.env` de la raíz
   para ese mismo servicio.

## Modelo de datos por servicio

**catalogo_db** — datos maestros de producto (sin stock):
- `productos(id, sku UNIQUE, nombre, categoria, precio_q, creado_en)`

**inventario_db** — cantidades en existencia:
- `stock(id, sku UNIQUE, cantidad, stock_minimo, actualizado_en)`
- Seed incluye 2 SKUs por debajo de `stock_minimo` a propósito, para
  demostrar la alerta de stock bajo del dashboard.

**clientes_db**:
- `clientes(id, nombre, nit UNIQUE, telefono, email, direccion, creado_en)`

**pedidos_db**:
- `integrantes(carne PK, nombre)` — los 5 carnés del equipo (evidencia
  personalizada requerida por el enunciado).
- `pedidos(id, cliente_id, carne_integrante FK → integrantes, estado, creado_en)`
- `detalle_pedido(id, pedido_id FK → pedidos, sku, cantidad, precio_unitario_q)`

**reportes_db** — sin tablas propias; el enunciado indica que Backend de
dominio (Área 5) resuelve la lógica de reportes por su cuenta, agregando
datos de los demás servicios vía sus APIs.

### Sobre las referencias entre servicios

`pedidos.cliente_id` y `detalle_pedido.sku` son referencias **lógicas** a
`clientes_db.clientes.id` y `catalogo_db.productos.sku`: no existen FKs
reales porque cada microservicio tiene su propia base de datos aislada. La
validación cruzada (¿existe el cliente?, ¿existe el SKU?, ¿alcanza el
stock?) la hace el backend (Área 5) llamando a los otros microservicios.

## Probar solo la base de datos (sin levantar todo el stack)

```bash
docker compose up -d db
docker exec -it elquetzal-db psql -U pedidos_user -d pedidos_db -c "select * from integrantes;"
```

## Volver a sembrar los datos

Los scripts de `init/` solo corren si el volumen está vacío. Para forzar
que vuelvan a correr en desarrollo (esto borra todos los datos):

```bash
docker compose down -v
docker compose up -d db
```
