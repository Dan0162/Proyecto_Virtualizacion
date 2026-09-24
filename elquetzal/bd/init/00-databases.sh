#!/bin/bash
# Área 4 (Datos): crea un rol y una base de datos independiente por microservicio.
# Se ejecuta una sola vez, la primera vez que arranca el contenedor con el volumen
# db_data vacío (comportamiento estándar de la imagen postgres). Para volver a
# correrlo en desarrollo: docker compose down -v (borra el volumen) y docker
# compose up de nuevo.
#
# Las contraseñas llegan por variables de entorno del contenedor "db" (ver
# environment en docker-compose.yml), que a su vez las toma del archivo .env
# en la raíz del proyecto (ver .env.example). Cero contraseñas quemadas aquí.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE catalogo_user   WITH LOGIN PASSWORD '$CATALOGO_DB_PASSWORD';
    CREATE ROLE inventario_user WITH LOGIN PASSWORD '$INVENTARIO_DB_PASSWORD';
    CREATE ROLE clientes_user   WITH LOGIN PASSWORD '$CLIENTES_DB_PASSWORD';
    CREATE ROLE pedidos_user    WITH LOGIN PASSWORD '$PEDIDOS_DB_PASSWORD';
    CREATE ROLE reportes_user   WITH LOGIN PASSWORD '$REPORTES_DB_PASSWORD';

    CREATE DATABASE catalogo_db   OWNER catalogo_user;
    CREATE DATABASE inventario_db OWNER inventario_user;
    CREATE DATABASE clientes_db   OWNER clientes_user;
    CREATE DATABASE pedidos_db    OWNER pedidos_user;
    CREATE DATABASE reportes_db   OWNER reportes_user;

    -- Postgres otorga CONNECT sobre toda base de datos nueva a PUBLIC por
    -- defecto: cualquier rol podría conectarse a la base de otro servicio
    -- (aunque no leer sus tablas). Se revoca para que cada base sea alcanzable
    -- únicamente por su propio usuario, como pide el enunciado.
    REVOKE CONNECT ON DATABASE catalogo_db   FROM PUBLIC;
    REVOKE CONNECT ON DATABASE inventario_db FROM PUBLIC;
    REVOKE CONNECT ON DATABASE clientes_db   FROM PUBLIC;
    REVOKE CONNECT ON DATABASE pedidos_db    FROM PUBLIC;
    REVOKE CONNECT ON DATABASE reportes_db   FROM PUBLIC;

    GRANT CONNECT ON DATABASE catalogo_db   TO catalogo_user;
    GRANT CONNECT ON DATABASE inventario_db TO inventario_user;
    GRANT CONNECT ON DATABASE clientes_db   TO clientes_user;
    GRANT CONNECT ON DATABASE pedidos_db    TO pedidos_user;
    GRANT CONNECT ON DATABASE reportes_db   TO reportes_user;

    -- Reportes consulta APIs internas y solo posee acceso a reportes_db.
EOSQL
