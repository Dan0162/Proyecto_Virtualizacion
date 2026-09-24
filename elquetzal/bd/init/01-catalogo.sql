-- Área 4 (Datos) — esquema y seed de catalogo_db (microservicio "catalogo").
-- Datos maestros de producto: SKU, nombre, categoría, precio en Q.
-- El stock (cantidades) vive en inventario_db, no aquí.
\connect catalogo_db

SET ROLE catalogo_user;

CREATE TABLE productos (
    id        SERIAL PRIMARY KEY,
    sku       VARCHAR(30)  NOT NULL UNIQUE,
    nombre    VARCHAR(120) NOT NULL,
    categoria VARCHAR(60)  NOT NULL,
    precio_q  NUMERIC(10,2) NOT NULL CHECK (precio_q >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO productos (sku, nombre, categoria, precio_q) VALUES
    ('QT-0001', 'Café tostado 1lb',        'Abarrotes', 45.00),
    ('QT-0002', 'Azúcar blanca 5lb',       'Abarrotes', 32.50),
    ('QT-0003', 'Aceite vegetal 1L',       'Abarrotes', 28.00),
    ('QT-0004', 'Detergente en polvo 2kg', 'Limpieza',  55.75),
    ('QT-0005', 'Papel higiénico x12',     'Limpieza',  39.90),
    ('QT-0006', 'Jabón de tocador x3',     'Higiene',   18.25),
    ('QT-0007', 'Arroz 5lb',               'Abarrotes', 30.00),
    ('QT-0008', 'Frijol negro 5lb',        'Abarrotes', 34.50);

RESET ROLE;

