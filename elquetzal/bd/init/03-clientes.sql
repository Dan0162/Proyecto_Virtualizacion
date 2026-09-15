-- Área 4 (Datos) — esquema y seed de clientes_db (microservicio "clientes").
\connect clientes_db

SET ROLE clientes_user;

CREATE TABLE clientes (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(120) NOT NULL,
    nit       VARCHAR(20) UNIQUE,
    telefono  VARCHAR(20),
    email     VARCHAR(120),
    direccion VARCHAR(200),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO clientes (nombre, nit, telefono, email, direccion) VALUES
    ('Tienda La Esquina',        '1234567-8', '5555-1111', 'contacto@laesquina.gt', 'Zona 1, Ciudad de Guatemala'),
    ('Supermercado San Rafael',  '2345678-9', '5555-2222', 'ventas@sanrafael.gt',   'Zona 5, Ciudad de Guatemala'),
    ('Distribuidora Norte',      '3456789-0', '5555-3333', 'info@distnorte.gt',     'Cobán, Alta Verapaz'),
    ('Minimarket El Ahorro',     '4567890-1', '5555-4444', 'compras@elahorro.gt',   'Quetzaltenango'),
    ('Abarrotería Don Chepe',    '5678901-2', '5555-5555', 'donchepe@gmail.com',    'Escuintla');

RESET ROLE;
