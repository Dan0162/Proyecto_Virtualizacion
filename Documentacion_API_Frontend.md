# Documentación de API Backend - El Quetzal

Este documento contiene la especificación de los endpoints del backend organizados por dominio. Utilice esta referencia para realizar las integraciones con el cliente Frontend (React, Vue, Angular, etc.).

Todas las peticiones que envíen datos deben usar el header:
`Content-Type: application/json`

La base de la URL (`BASE_URL`) dependerá del entorno (ej. `http://localhost`).

---

## 1. Catálogo de Productos

Gestiona los productos disponibles en la tienda. La llave primaria es el `sku`.

### Obtener todos los productos
- **Método:** `GET`
- **URL:** `/api/catalogo/productos`

### Obtener un producto específico
- **Método:** `GET`
- **URL:** `/api/catalogo/productos/{sku}`

### Crear un nuevo producto
- **Método:** `POST`
- **URL:** `/api/catalogo/productos`
- **Body (JSON):**
```json
{
  "sku": "TEST-100",
  "nombre": "Monitor Gamer 24 pulgadas",
  "categoria": "Electronica",
  "precio_q": 1500.50
}
```

### Actualizar un producto existente
- **Método:** `PUT`
- **URL:** `/api/catalogo/productos/{sku}`
- **Body (JSON):** *(Puedes enviar solo los campos que deseas actualizar)*
```json
{
  "precio_q": 1200.00
}
```

### Eliminar un producto
- **Método:** `DELETE`
- **URL:** `/api/catalogo/productos/{sku}`

---

## 2. Inventario

Gestiona el stock físico de los productos.

### Obtener todo el inventario
- **Método:** `GET`
- **URL:** `/api/inventario/stock`

### Obtener stock de un producto específico
- **Método:** `GET`
- **URL:** `/api/inventario/stock/{sku}`

### Registrar stock inicial de un producto
- **Método:** `POST`
- **URL:** `/api/inventario/stock`
- **Body (JSON):**
```json
{
  "sku": "TEST-101",
  "cantidad": 50,
  "stock_minimo": 10
}
```

### Actualizar stock de un producto
- **Método:** `PUT`
- **URL:** `/api/inventario/stock/{sku}`
- **Body (JSON):**
```json
{
  "cantidad": 45
}
```

### Eliminar registro de stock
- **Método:** `DELETE`
- **URL:** `/api/inventario/stock/{sku}`

---

## 3. Clientes

Administración de información de los clientes.

### Obtener todos los clientes
- **Método:** `GET`
- **URL:** `/api/clientes/`

### Obtener un cliente específico
- **Método:** `GET`
- **URL:** `/api/clientes/{id}`

### Crear un cliente
- **Método:** `POST`
- **URL:** `/api/clientes/`
- **Body (JSON):**
```json
{
  "nombre": "Juan Pérez",
  "nit": "123456-7",
  "telefono": "5555-4444",
  "email": "juanperez@example.com",
  "direccion": "Ciudad de Guatemala, Zona 10"
}
```

### Actualizar un cliente
- **Método:** `PUT`
- **URL:** `/api/clientes/{id}`
- **Body (JSON):**
```json
{
  "telefono": "1111-2222",
  "direccion": "Nueva Dirección, Zona 1"
}
```

### Eliminar un cliente
- **Método:** `DELETE`
- **URL:** `/api/clientes/{id}`

---

## 4. Pedidos

Procesamiento y registro de órdenes de compra.

### Obtener todos los pedidos
- **Método:** `GET`
- **URL:** `/api/pedidos/`

### Obtener un pedido específico
- **Método:** `GET`
- **URL:** `/api/pedidos/{id}`

### Crear un nuevo pedido
- **Método:** `POST`
- **URL:** `/api/pedidos/`
- **Body (JSON):**
```json
{
  "cliente_id": 1,
  "carne_integrante": "1199923",
  "estado": "pendiente",
  "detalles": [
    {
      "sku": "QT-0001",
      "cantidad": 2,
      "precio_unitario_q": 45.00
    },
    {
      "sku": "QT-0004",
      "cantidad": 1,
      "precio_unitario_q": 55.75
    }
  ]
}
```

---

## 5. Reportes

Consultas para la generación de datos y análisis.

### Obtener reporte general
- **Método:** `GET`
- **URL:** `/api/reportes`

### Obtener reporte por fecha específica
- **Método:** `GET`
- **URL:** `/api/reportes?fecha={YYYY-MM-DD}`
- **Ejemplo:** `/api/reportes?fecha=2023-10-25`
