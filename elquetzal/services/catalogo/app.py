import os
import math
from flask import Flask, jsonify, request
import psycopg

app = Flask(__name__)
SERVICE_NAME = "catalogo"

# Verificar si el servicio está "vivo".
@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)

# Leemos el nombre y host de la base de datos (lo tiene que poner Daniel luego en el .env)
@app.get("/")
def index():
    return jsonify(message=f"Microservicio {SERVICE_NAME} de El Quetzal", db_host=os.getenv("DB_HOST"), db_name=os.getenv("DB_NAME"))

def connect_db():
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    return psycopg.connect(
        host=db_host,
        dbname=db_name,
        user=db_user,
        password=db_password
    )


def validar_campos_producto(datos, campos_requeridos):
    """Valida y normaliza los campos recibidos de un producto.

    Args:
        datos: Diccionario con los campos enviados por el cliente.
        campos_requeridos: Campos que deben estar presentes en `datos`.

    Returns:
        Una tupla `(campos, error)`, donde `campos` contiene los valores
        normalizados y `error` es `None` cuando la validacion es exitosa.
    """
    campos_permitidos = {"sku", "nombre", "categoria", "precio_q"}
    campos_desconocidos = set(datos) - campos_permitidos
    if campos_desconocidos:
        return None, f"Campos no permitidos: {', '.join(sorted(campos_desconocidos))}"

    campos_faltantes = set(campos_requeridos) - datos.keys()
    if campos_faltantes:
        return None, f"Faltan campos requeridos: {', '.join(sorted(campos_faltantes))}"

    campos = {}
    for campo in ("sku", "nombre", "categoria"):
        if campo not in datos:
            continue
        valor = datos[campo]
        if not isinstance(valor, str):
            return None, f"{campo} debe ser un texto"
        if not valor.strip():
            return None, f"{campo} no puede estar vacio"
        limite = {"sku": 30, "nombre": 120, "categoria": 60}[campo]
        if len(valor.strip()) > limite:
            return None, f"{campo} excede el limite de {limite} caracteres"
        campos[campo] = valor.strip()

    if "precio_q" in datos:
        precio_q = datos["precio_q"]
        if isinstance(precio_q, bool) or not isinstance(precio_q, (int, float)):
            return None, "precio_q debe ser un numero"
        try:
            precio_valido = math.isfinite(precio_q)
        except OverflowError:
            precio_valido = False
        if not precio_valido or precio_q < 0:
            return None, "precio_q debe ser un numero finito no negativo"
        campos["precio_q"] = precio_q

    return campos, None


#Endpoint GET para obtener todos los productos del catalogo
@app.get("/productos")
def get_productos():
    '''
    Devuelve un JSON con la lista de productos en el catologo, ordenados por sku.
    cada producto es un diccionario con las llaves: sku, nombre, categoria, precio_q
    
    '''
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                SELECT sku,nombre,categoria,precio_q 
                FROM productos
                ORDER BY sku
                """)
                productos = cur.fetchall()

        return jsonify(productos=[
            {"sku": p[0], 
            "nombre": p[1], 
            "categoria": p[2], 
            "precio_q": float(p[3])
            } 
            for p in productos
        ])
                
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.post("/productos")
def crear_producto():
    """Crea un producto nuevo en el catalogo.

    El cuerpo de la solicitud debe ser JSON con los campos `sku`, `nombre`,
    `categoria` y `precio_q`. Devuelve el producto creado con estado 201.
    Devuelve 400 si el cuerpo no es JSON valido o el SKU ya existe, 422 si
    faltan campos o sus tipos/valores no son validos, y 500 ante un fallo del
    servidor.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400

    campos, error = validar_campos_producto(
        datos, {"sku", "nombre", "categoria", "precio_q"}
    )
    if error:
        return jsonify(error=error), 422

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO productos (sku, nombre, categoria, precio_q)
                    VALUES (%s, %s, %s, %s)
                    RETURNING sku, nombre, categoria, precio_q
                """, (campos["sku"], campos["nombre"], campos["categoria"], campos["precio_q"]))
                producto = cur.fetchone()

        return jsonify(producto={
            "sku": producto[0],
            "nombre": producto[1],
            "categoria": producto[2],
            "precio_q": float(producto[3])
        }), 201

    except psycopg.errors.UniqueViolation:
        return jsonify(error="Ya existe un producto con ese SKU"), 400
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.put("/productos/<sku>")
def actualizar_producto(sku):
    """Actualiza nombre, categoria y/o precio de un producto por su SKU.

    Objetivo:
        Modificar parcialmente los datos editables de un producto existente.

    Args:
        sku: SKU del producto que se desea actualizar.

    Request JSON:
        Debe incluir al menos uno de `nombre`, `categoria` o `precio_q`.
        El SKU se toma de la URL y no puede modificarse.

    Returns:
        Estado 200 con el producto actualizado, 404 si el SKU no existe,
        400 si el cuerpo no es JSON valido, 422 si los datos son invalidos,
        o 500 si ocurre un error de base de datos.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400
    if "sku" in datos:
        return jsonify(error="sku se define en la URL y no se puede modificar"), 422

    campos, error = validar_campos_producto(datos, set())
    if error:
        return jsonify(error=error), 422

    campos_editables = {campo: campos[campo] for campo in ("nombre", "categoria", "precio_q") if campo in campos}
    if not campos_editables:
        return jsonify(error="Debe proporcionar nombre, categoria o precio_q"), 422

    columnas = ", ".join(f"{campo} = %s" for campo in campos_editables)
    valores = list(campos_editables.values()) + [sku]

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE productos
                    SET {columnas}
                    WHERE sku = %s
                    RETURNING sku, nombre, categoria, precio_q
                """, valores)
                producto = cur.fetchone()

        if producto is None:
            return jsonify(error="Producto no encontrado"), 404

        return jsonify(producto={
            "sku": producto[0],
            "nombre": producto[1],
            "categoria": producto[2],
            "precio_q": float(producto[3])
        }), 200

    except Exception as error:
        return jsonify(error=str(error)), 500

@app.get("/productos/<sku>")
def get_producto_por_sku(sku):
    """Obtiene un producto del catalogo mediante su SKU.

    Args:
        sku: SKU del producto que se desea consultar.

    Returns:
        Una respuesta JSON con los datos del producto y estado 200 si existe.
        Si no existe un producto con ese SKU, devuelve un JSON de error y
        estado 404. Si ocurre un error de base de datos, devuelve estado 500.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sku, nombre, categoria, precio_q
                    FROM productos
                    WHERE sku = %s
                """, (sku,))
                producto = cur.fetchone()

        if producto is None:
            return jsonify(error="Producto no encontrado"), 404

        return jsonify(producto={
            "sku": producto[0],
            "nombre": producto[1],
            "categoria": producto[2],
            "precio_q": float(producto[3])
        }), 200

    except Exception as error:
        return jsonify(error=str(error)), 500


@app.delete("/productos/<sku>")
def eliminar_producto(sku):
    """Elimina un producto del catalogo mediante su SKU.

    Args:
        sku: SKU del producto que se desea eliminar.

    Returns:
        Estado 201 con confirmacion y el SKU eliminado si el producto existe,
        estado 404 si no existe, o estado 500 si ocurre un fallo del servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM productos
                    WHERE sku = %s
                    RETURNING sku
                """, (sku,))
                producto_eliminado = cur.fetchone()

        if producto_eliminado is None:
            return jsonify(error="Producto no encontrado"), 404

        return jsonify(
            mensaje="Producto eliminado correctamente",
            sku=producto_eliminado[0]
        ), 201

    except Exception as error:
        return jsonify(error=str(error)), 500


# Solo sirve para debug fuera del contenedor, el servicio lo arranca gunicorn
if __name__ == "__main__":
    # Escuchamos el 0.0.0.0 y no 127.0.0.1 para que pueda ser alcanzado.
    app.run(host="0.0.0.0", port=5000)

