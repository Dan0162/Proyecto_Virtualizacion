
import os
from collections import Counter
from flask import Flask, jsonify, request

import psycopg

app = Flask(__name__)
SERVICE_NAME = "inventario"

@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)

@app.get("/")
def index():
    return jsonify(
        message=f"Microservicio {SERVICE_NAME} de El Quetzal",
        db_host=os.getenv("DB_HOST"),
        db_name=os.getenv("DB_NAME"),
    )

def connect_db():
    """Abre una conexion a la base de datos del inventario."""
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


@app.post("/stock/descontar")
def descontar_stock():
    """Valida y descuenta todos los SKU en una sola transaccion de inventario."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not isinstance(datos.get("detalles"), list) or not datos["detalles"]:
        return jsonify(error="detalles debe ser una lista no vacia"), 422

    cantidades = Counter()
    for detalle in datos["detalles"]:
        if not isinstance(detalle, dict) or set(detalle) != {"sku", "cantidad"}:
            return jsonify(error="Cada detalle requiere sku y cantidad"), 422
        sku, cantidad = detalle["sku"], detalle["cantidad"]
        if not isinstance(sku, str) or not sku.strip() or len(sku.strip()) > 30:
            return jsonify(error="sku invalido"), 422
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
            return jsonify(error="cantidad debe ser un entero positivo"), 422
        cantidades[sku.strip()] += cantidad

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                # Orden estable para evitar deadlocks entre pedidos concurrentes.
                for sku in sorted(cantidades):
                    cur.execute(
                        "SELECT cantidad FROM stock WHERE sku = %s FOR UPDATE", (sku,)
                    )
                    fila = cur.fetchone()
                    if fila is None:
                        conn.rollback()
                        return jsonify(error=f"Stock no encontrado para el SKU: {sku}"), 404
                    if fila[0] < cantidades[sku]:
                        conn.rollback()
                        return jsonify(error=f"Stock insuficiente para el SKU: {sku}"), 409

                for sku in sorted(cantidades):
                    cur.execute(
                        """UPDATE stock SET cantidad = cantidad - %s,
                           actualizado_en = now() WHERE sku = %s""",
                        (cantidades[sku], sku),
                    )
        return jsonify(descontado=dict(cantidades)), 200
    except Exception:
        app.logger.exception("Fallo al descontar stock")
        return jsonify(error="No se pudo descontar el stock"), 500


@app.post("/stock/reintegrar")
def reintegrar_stock():
    """Compensa un descuento si no se pudo registrar el pedido."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not isinstance(datos.get("detalles"), list) or not datos["detalles"]:
        return jsonify(error="detalles debe ser una lista no vacia"), 422
    cantidades = Counter()
    for detalle in datos["detalles"]:
        if not isinstance(detalle, dict) or set(detalle) != {"sku", "cantidad"}:
            return jsonify(error="Cada detalle requiere sku y cantidad"), 422
        sku, cantidad = detalle["sku"], detalle["cantidad"]
        if not isinstance(sku, str) or not sku.strip() or len(sku.strip()) > 30:
            return jsonify(error="sku invalido"), 422
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
            return jsonify(error="cantidad debe ser un entero positivo"), 422
        cantidades[sku.strip()] += cantidad
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for sku in sorted(cantidades):
                    cur.execute(
                        """UPDATE stock SET cantidad = cantidad + %s,
                           actualizado_en = now() WHERE sku = %s RETURNING sku""",
                        (cantidades[sku], sku),
                    )
                    if cur.fetchone() is None:
                        raise ValueError(f"Stock no encontrado: {sku}")
        return jsonify(reintegrado=dict(cantidades)), 200
    except Exception:
        app.logger.exception("Fallo al reintegrar stock")
        return jsonify(error="No se pudo reintegrar el stock"), 500

def validar_campos_stock(datos, campos_requeridos):
    """Valida y normaliza los campos permitidos de un registro de stock.

    Args:
        datos: Diccionario con los campos enviados por el cliente.
        campos_requeridos: Campos que deben estar presentes en `datos`.

    Returns:
        Una tupla `(campos, error)`. `campos` contiene valores normalizados y
        `error` es `None` cuando la validacion es exitosa.
    """
    campos_permitidos = {"sku", "cantidad", "stock_minimo"}
    campos_desconocidos = set(datos) - campos_permitidos
    if campos_desconocidos:
        return None, f"Campos no permitidos: {', '.join(sorted(campos_desconocidos))}"

    campos_faltantes = set(campos_requeridos) - datos.keys()
    if campos_faltantes:
        return None, f"Faltan campos requeridos: {', '.join(sorted(campos_faltantes))}"

    campos = {}
    if "sku" in datos:
        sku = datos["sku"]
        if not isinstance(sku, str):
            return None, "sku debe ser un texto"
        if not sku.strip():
            return None, "sku no puede estar vacio"
        if len(sku.strip()) > 30:
            return None, "sku excede el limite de 30 caracteres"
        campos["sku"] = sku.strip()

    for campo in ("cantidad", "stock_minimo"):
        if campo not in datos:
            continue
        valor = datos[campo]
        if isinstance(valor, bool) or not isinstance(valor, int):
            return None, f"{campo} debe ser un entero"
        if valor < 0:
            return None, f"{campo} debe ser un entero no negativo"
        campos[campo] = valor

    return campos, None

def serializar_stock(stock):
    """Convierte una fila de stock en la respuesta publica del servicio."""
    return {
        "sku": stock[0],
        "cantidad": stock[1],
        "stock_minimo": stock[2],
    }

@app.get("/stock")
def get_stock():
    """Obtiene todos los registros de stock ordenados por SKU.

    Returns:
        Estado 200 con la lista de registros o estado 500 ante un fallo del
        servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sku, cantidad, stock_minimo
                    FROM stock
                    ORDER BY sku
                """)
                registros = cur.fetchall()

        return jsonify(stock=[serializar_stock(registro) for registro in registros]), 200
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.post("/stock")
def crear_stock():
    """Crea un registro de stock.

    Request JSON:
        Requiere `sku`, `cantidad` y `stock_minimo`; `id` y `actualizado_en`
        no forman parte de la API.

    Returns:
        Estado 201 con el registro creado, 400 si el SKU ya existe, 422 si
        faltan campos o son invalidos, o 500 ante un fallo del servidor.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400

    campos, error = validar_campos_stock(
        datos, {"sku", "cantidad", "stock_minimo"}
    )
    if error:
        return jsonify(error=error), 422

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO stock (sku, cantidad, stock_minimo)
                    VALUES (%s, %s, %s)
                    RETURNING sku, cantidad, stock_minimo
                """, (campos["sku"], campos["cantidad"], campos["stock_minimo"]))
                registro = cur.fetchone()

        return jsonify(stock=serializar_stock(registro)), 201
    except psycopg.errors.UniqueViolation:
        return jsonify(error="Ya existe stock para ese SKU"), 400
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.get("/stock/<sku>")
def get_stock_por_sku(sku):
    """Obtiene el stock de un SKU.

    Args:
        sku: SKU del producto cuyo stock se desea consultar.

    Returns:
        Estado 200 con el registro, 404 si no existe o 500 ante un fallo del
        servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT sku, cantidad, stock_minimo
                    FROM stock
                    WHERE sku = %s
                """, (sku,))
                registro = cur.fetchone()

        if registro is None:
            return jsonify(error="Stock no encontrado"), 404
        return jsonify(stock=serializar_stock(registro)), 200
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.put("/stock/<sku>")
def actualizar_stock(sku):
    """Actualiza cantidad y/o stock minimo de un SKU.

    Args:
        sku: SKU del registro que se desea actualizar.

    Request JSON:
        Debe incluir al menos `cantidad` o `stock_minimo`. El SKU se toma de
        la URL y no puede modificarse.

    Returns:
        Estado 200 con el registro actualizado, 404 si no existe, 400 si el
        cuerpo no es JSON valido, 422 si los datos son invalidos, o 500 ante
        un fallo del servidor.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400
    if "sku" in datos:
        return jsonify(error="sku se define en la URL y no se puede modificar"), 422

    campos, error = validar_campos_stock(datos, set())
    if error:
        return jsonify(error=error), 422

    campos_editables = {
        campo: campos[campo]
        for campo in ("cantidad", "stock_minimo")
        if campo in campos
    }
    if not campos_editables:
        return jsonify(error="Debe proporcionar cantidad o stock_minimo"), 422

    columnas = ", ".join(f"{campo} = %s" for campo in campos_editables)
    valores = list(campos_editables.values()) + [sku]

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE stock
                    SET {columnas}
                    WHERE sku = %s
                    RETURNING sku, cantidad, stock_minimo
                """, valores)
                registro = cur.fetchone()

        if registro is None:
            return jsonify(error="Stock no encontrado"), 404
        return jsonify(stock=serializar_stock(registro)), 200
    except Exception as error:
        return jsonify(error=str(error)), 500

@app.delete("/stock/<sku>")
def eliminar_stock(sku):
    """Elimina el registro de stock de un SKU.

    Args:
        sku: SKU del registro que se desea eliminar.

    Returns:
        Estado 201 con confirmacion, 404 si no existe o 500 ante un fallo del
        servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM stock
                    WHERE sku = %s
                    RETURNING sku
                """, (sku,))
                registro = cur.fetchone()

        if registro is None:
            return jsonify(error="Stock no encontrado"), 404
        return jsonify(mensaje="Stock eliminado correctamente", sku=registro[0]), 201
    except Exception as error:
        return jsonify(error=str(error)), 500

# Solo sirve para debug fuera del contenedor, el servicio lo arranca gunicorn
if __name__ == "__main__":
    # Escuchamos el 0.0.0.0 y no 127.0.0.1 para que pueda ser alcanzado.
    app.run(host="0.0.0.0", port=5000)
