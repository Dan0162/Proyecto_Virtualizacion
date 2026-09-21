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

Asegúrate de contar con un archivo `.env` en el directorio `elquetzal/` con las contraseñas de las bases de datos. Luego, ejecuta:

```bash
docker compose up -d --build
```

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