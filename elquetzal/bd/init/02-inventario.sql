-- Área 4 (Datos) — esquema y seed de inventario_db (microservicio "inventario").
-- Cantidades en existencia por SKU. El SKU referencia lógicamente a
-- catalogo_db.productos.sku (no hay FK real: son bases de datos distintas).
\connect inventario_db

SET ROLE inventario_user;

CREATE TABLE stock (
    id             SERIAL PRIMARY KEY,
    sku            VARCHAR(30) NOT NULL UNIQUE,
    cantidad       INTEGER NOT NULL CHECK (cantidad >= 0),
    stock_minimo   INTEGER NOT NULL DEFAULT 10 CHECK (stock_minimo >= 0),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- QT-0002 y QT-0005 quedan a propósito por debajo de su stock_minimo,
-- para poder demostrar la alerta de stock bajo del dashboard.
INSERT INTO stock (sku, cantidad, stock_minimo) VALUES
    ('QT-0001', 120, 20),
    ('QT-0002',   8, 15),
    ('QT-0003',  60, 15),
    ('QT-0004',  45, 10),
    ('QT-0005',   5, 20),
    ('QT-0006', 200, 30),
    ('QT-0007',  90, 20),
    ('QT-0008',  75, 20);

RESET ROLE;

