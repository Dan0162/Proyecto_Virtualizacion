# Esto es solo la base mínima digamos, podes cambiar lo que crear que necesites cambiar.
# Igual en el otro archivo de requerimientos.
import os
from flask import Flask, jsonify, request

import psycopg

app = Flask(__name__)
SERVICE_NAME = "clientes"

@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)

def connect_db():
    """Abre una conexion a la base de datos de clientes."""
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

def validar_campos_cliente(datos, campos_requeridos):
    """Valida y normaliza los campos publicos de un cliente.

    Args:
        datos: Diccionario con los campos enviados por el cliente.
        campos_requeridos: Campos que deben estar presentes en `datos`.

    Returns:
        Una tupla `(campos, error)`. `campos` contiene valores normalizados y
        `error` es `None` cuando la validacion es exitosa.
    """
    limites = {
        "nombre": 120,
        "nit": 20,
        "telefono": 20,
        "email": 120,
        "direccion": 200,
    }
    campos_permitidos = set(limites)
    campos_desconocidos = set(datos) - campos_permitidos
    if campos_desconocidos:
        return None, f"Campos no permitidos: {', '.join(sorted(campos_desconocidos))}"

    campos_faltantes = set(campos_requeridos) - datos.keys()
    if campos_faltantes:
        return None, f"Faltan campos requeridos: {', '.join(sorted(campos_faltantes))}"

    campos = {}
    for campo, limite in limites.items():
        if campo not in datos:
            continue
        valor = datos[campo]
        if valor is None and campo != "nombre":
            campos[campo] = None
            continue
        if not isinstance(valor, str):
            return None, f"{campo} debe ser un texto"
        valor = valor.strip()
        if not valor:
            return None, f"{campo} no puede estar vacio"
        if len(valor) > limite:
            return None, f"{campo} excede el limite de {limite} caracteres"
        campos[campo] = valor

    return campos, None

def serializar_cliente(cliente):
    """Convierte una fila de clientes en la respuesta publica del servicio."""
    return {
        "nombre": cliente[0],
        "nit": cliente[1],
        "telefono": cliente[2],
        "email": cliente[3],
        "direccion": cliente[4],
    }

SELECT_CLIENTE = """
    SELECT nombre, nit, telefono, email, direccion
    FROM clientes
"""

@app.get("/")
def get_clientes():
    """Obtiene todos los clientes ordenados por nombre.

    Returns:
        Estado 200 con la lista de clientes o estado 500 ante un fallo del
        servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_CLIENTE + " ORDER BY nombre")
                clientes = cur.fetchall()

        return jsonify(clientes=[serializar_cliente(cliente) for cliente in clientes]), 200
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.post("/")
def crear_cliente():
    """Crea un cliente nuevo.

    Request JSON:
        Requiere `nombre`; `nit`, `telefono`, `email` y `direccion` son
        opcionales. `id` y `creado_en` no forman parte de la API.

    Returns:
        Estado 201 con el cliente creado, 400 si el NIT ya existe, 422 si los
        datos son invalidos, o 500 ante un fallo del servidor.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400

    campos, error = validar_campos_cliente(datos, {"nombre"})
    if error:
        return jsonify(error=error), 422

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO clientes (nombre, nit, telefono, email, direccion)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING nombre, nit, telefono, email, direccion
                """, tuple(campos.get(campo) for campo in (
                    "nombre", "nit", "telefono", "email", "direccion"
                )))
                cliente = cur.fetchone()

        return jsonify(cliente=serializar_cliente(cliente)), 201
    except psycopg.errors.UniqueViolation:
        return jsonify(error="Ya existe un cliente con ese NIT"), 400
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.get("/<int:id>")
def get_cliente_por_id(id):
    """Obtiene un cliente por su identificador interno.

    Args:
        id: Identificador del cliente usado solo para localizar el recurso.

    Returns:
        Estado 200 con el cliente, 404 si no existe o 500 ante un fallo del
        servidor. El campo `id` no se incluye en la respuesta.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(SELECT_CLIENTE + " WHERE id = %s", (id,))
                cliente = cur.fetchone()

        if cliente is None:
            return jsonify(error="Cliente no encontrado"), 404
        return jsonify(cliente=serializar_cliente(cliente)), 200
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.put("/<int:id>")
def actualizar_cliente(id):
    """Actualiza parcialmente un cliente por su ID.

    Args:
        id: Identificador del cliente que se desea actualizar.

    Request JSON:
        Debe incluir al menos uno de `nombre`, `nit`, `telefono`, `email` o
        `direccion`. El ID no puede modificarse.

    Returns:
        Estado 200 con el cliente actualizado, 404 si no existe, 400 si el
        cuerpo no es JSON valido, 422 si los datos son invalidos, o 500 ante
        un fallo del servidor.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400

    campos, error = validar_campos_cliente(datos, set())
    if error:
        return jsonify(error=error), 422
    if not campos:
        return jsonify(error="Debe proporcionar al menos un campo editable"), 422

    columnas = ", ".join(f"{campo} = %s" for campo in campos)
    valores = list(campos.values()) + [id]

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE clientes
                    SET {columnas}
                    WHERE id = %s
                    RETURNING nombre, nit, telefono, email, direccion
                """, valores)
                cliente = cur.fetchone()

        if cliente is None:
            return jsonify(error="Cliente no encontrado"), 404
        return jsonify(cliente=serializar_cliente(cliente)), 200
    except psycopg.errors.UniqueViolation:
        return jsonify(error="Ya existe un cliente con ese NIT"), 400
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.delete("/<int:id>")
def eliminar_cliente(id):
    """Elimina un cliente por su ID.

    Args:
        id: Identificador del cliente que se desea eliminar.

    Returns:
        Estado 201 con confirmacion, 404 si no existe o 500 ante un fallo del
        servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM clientes WHERE id = %s RETURNING id", (id,))
                cliente = cur.fetchone()

        if cliente is None:
            return jsonify(error="Cliente no encontrado"), 404
        return jsonify(mensaje="Cliente eliminado correctamente"), 201
    except Exception as error:
        return jsonify(error=str(error)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
