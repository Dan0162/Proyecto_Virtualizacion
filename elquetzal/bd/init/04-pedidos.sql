-- Área 4 (Datos) — esquema y seed de pedidos_db (microservicio "pedidos").
--
-- "integrantes" es la tabla de evidencia personalizada: los carnés del
-- equipo, referenciados por cada pedido (FK). El backend (Área 5) debe
-- insertar el carné real del integrante que crea el pedido al confirmarlo.
--
-- cliente_id y detalle_pedido.sku son referencias lógicas a clientes_db y
-- catalogo_db respectivamente (no hay FK real entre bases de datos distintas).
\connect pedidos_db

SET ROLE pedidos_user;

CREATE TABLE integrantes (
    carne  VARCHAR(15) PRIMARY KEY,
    nombre VARCHAR(120)
);

INSERT INTO integrantes (carne, nombre) VALUES
    ('1040023', 'Daniel Diaz'),
    ('1053223', 'Jose Enríquez'),
    ('1199923', 'Hector Flores'),
    ('1280423', 'Joaquín Choc'),
    ('333123',  'Sofia Sigüenza');

CREATE TABLE pedidos (
    id               SERIAL PRIMARY KEY,
    cliente_id       INTEGER,
    carne_integrante VARCHAR(15) NOT NULL REFERENCES integrantes(carne),
    estado           VARCHAR(20) NOT NULL DEFAULT 'confirmado'
                         CHECK (estado IN ('pendiente', 'confirmado', 'cancelado')),
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE detalle_pedido (
    id                SERIAL PRIMARY KEY,
    pedido_id         INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    sku               VARCHAR(30) NOT NULL,
    cantidad          INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario_q NUMERIC(10,2) NOT NULL CHECK (precio_unitario_q >= 0)
);

-- Un pedido de ejemplo por cada carné del equipo, como evidencia sembrada.
INSERT INTO pedidos (cliente_id, carne_integrante, estado) VALUES
    (1, '1040023', 'confirmado'),
    (2, '1053223', 'confirmado'),
    (3, '1199923', 'confirmado'),
    (4, '1280423', 'confirmado'),
    (5, '333123',  'confirmado');

INSERT INTO detalle_pedido (pedido_id, sku, cantidad, precio_unitario_q) VALUES
    (1, 'QT-0001', 2, 45.00),
    (1, 'QT-0003', 1, 28.00),
    (2, 'QT-0002', 3, 32.50),
    (3, 'QT-0004', 1, 55.75),
    (3, 'QT-0005', 2, 39.90),
    (4, 'QT-0006', 5, 18.25),
    (5, 'QT-0007', 4, 30.00);

RESET ROLE;

-- Lectura para el dashboard de "reportes" (Área 5): solo cuenta pedidos del
-- día, no necesita integrantes ni detalle_pedido. Sin INSERT/UPDATE/DELETE.
GRANT SELECT ON pedidos TO reportes_user;
