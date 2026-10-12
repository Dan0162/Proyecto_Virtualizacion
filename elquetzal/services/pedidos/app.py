import json
import os
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from datetime import date
from decimal import Decimal

import psycopg
from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = "pedidos"


@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)


def connect_db():
    """Abre una conexion a la base de datos de pedidos."""
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def validar_pedido(datos):
    """Valida los campos insertables de un pedido.

    Args:
        datos: Diccionario con los campos recibidos en la solicitud.

    Returns:
        Una tupla `(campos, error)` con los valores normalizados.
    """
    campos_permitidos = {"cliente_id", "carne_integrante", "estado", "detalles"}
    campos_desconocidos = set(datos) - campos_permitidos
    if campos_desconocidos:
        return None, f"Campos no permitidos: {', '.join(sorted(campos_desconocidos))}"

    if "carne_integrante" not in datos:
        return None, "Falta el campo requerido: carne_integrante"
    carne = datos["carne_integrante"]
    if not isinstance(carne, str) or not carne.strip():
        return None, "carne_integrante debe ser un texto no vacio"
    if len(carne.strip()) > 15:
        return None, "carne_integrante excede el limite de 15 caracteres"

    cliente_id = datos.get("cliente_id")
    if cliente_id is not None and (
        isinstance(cliente_id, bool)
        or not isinstance(cliente_id, int)
        or cliente_id < 1
    ):
        return None, "cliente_id debe ser un entero positivo o null"

    estado = datos.get("estado", "confirmado")
    if estado != "confirmado":
        return None, "solo se pueden crear pedidos con estado confirmado"

    if "detalles" not in datos:
        return None, "Falta el campo requerido: detalles"
    detalles = datos["detalles"]
    if not isinstance(detalles, list):
        return None, "detalles debe ser una lista"

    detalles_validados = []
    for posicion, detalle in enumerate(detalles, start=1):
        detalle_validado, error = validar_detalle(detalle)
        if error:
            return None, f"Detalle {posicion}: {error}"
        detalles_validados.append(detalle_validado)

    return {
        "cliente_id": cliente_id,
        "carne_integrante": carne.strip(),
        "estado": estado,
        "detalles": detalles_validados,
    }, None


def validar_detalle(detalle):
    """Valida una linea de detalle, excluyendo sus IDs generados."""
    if not isinstance(detalle, dict):
        return None, "debe ser un objeto"

    campos_permitidos = {"sku", "cantidad", "precio_unitario_q"}
    campos_desconocidos = set(detalle) - campos_permitidos - {"id", "pedido_id"}
    if campos_desconocidos:
        return None, f"campos no permitidos: {', '.join(sorted(campos_desconocidos))}"

    campos_faltantes = {"sku", "cantidad"} - detalle.keys()
    if campos_faltantes:
        return None, f"faltan campos: {', '.join(sorted(campos_faltantes))}"

    sku = detalle["sku"]
    if not isinstance(sku, str) or not sku.strip():
        return None, "sku debe ser un texto no vacio"
    if len(sku.strip()) > 30:
        return None, "sku excede el limite de 30 caracteres"

    cantidad = detalle["cantidad"]
    if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
        return None, "cantidad debe ser un entero positivo"

    # El precio real lo toma pedidos del catalogo; el del cliente se ignora.
    precio_decimal = Decimal("0")

    return {
        "sku": sku.strip(),
        "cantidad": cantidad,
        "precio_unitario_q": precio_decimal,
    }, None


def serializar_detalle(detalle):
    """Convierte una fila de detalle en JSON publico."""
    return {
        "id": detalle[0],
        "pedido_id": detalle[1],
        "sku": detalle[2],
        "cantidad": detalle[3],
        "precio_unitario_q": float(detalle[4]),
    }


def serializar_pedidos(filas):
    """Agrupa las filas del JOIN por pedido y conserva todos sus campos."""
    pedidos = {}
    for fila in filas:
        pedido_id = fila[0]
        if pedido_id not in pedidos:
            pedidos[pedido_id] = {
                "id": pedido_id,
                "cliente_id": fila[1],
                "carne_integrante": fila[2],
                "estado": fila[3],
                "creado_en": fila[4].isoformat(),
                "detalles": [],
            }
        if fila[5] is not None:
            pedidos[pedido_id]["detalles"].append(serializar_detalle(fila[5:]))
    return list(pedidos.values())


CONSULTA_PEDIDOS = """
    SELECT p.id, p.cliente_id, p.carne_integrante, p.estado, p.creado_en,
           d.id, d.pedido_id, d.sku, d.cantidad, d.precio_unitario_q
    FROM pedidos AS p
    LEFT JOIN detalle_pedido AS d ON d.pedido_id = p.id
"""


@app.get("/")
def get_pedidos():
    """Obtiene todos los pedidos con sus detalles.

    Returns:
        Estado 200 con todos los campos de `pedidos` y `detalle_pedido`,
        o estado 500 ante un fallo del servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(CONSULTA_PEDIDOS + " ORDER BY p.id, d.id")
                filas = cur.fetchall()
        return jsonify(pedidos=serializar_pedidos(filas)), 200
    except Exception as error:
        app.logger.exception("Error interno")
        return jsonify(error="Error interno del servidor"), 500


@app.get("/conteo")
def contar_pedidos():
    """Cuenta los pedidos del dia dado (YYYY-MM-DD) en hora de Guatemala."""
    try:
        fecha = date.fromisoformat(request.args.get("fecha", ""))
    except ValueError:
        return jsonify(error="fecha debe tener el formato YYYY-MM-DD"), 400
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM pedidos "
                    "WHERE (creado_en AT TIME ZONE 'America/Guatemala')::date = %s",
                    (fecha,),
                )
                return jsonify(fecha=fecha.isoformat(), total=cur.fetchone()[0]), 200
    except Exception:
        app.logger.exception("Error interno")
        return jsonify(error="Error interno del servidor"), 500


@app.get("/<int:id>")
def get_pedido_por_id(id):
    """Obtiene un pedido por ID, incluyendo todos sus detalles.

    Args:
        id: Identificador del pedido.

    Returns:
        Estado 200 con el pedido, 404 si no existe o 500 ante un fallo del
        servidor.
    """
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute(CONSULTA_PEDIDOS + " WHERE p.id = %s ORDER BY d.id", (id,))
                filas = cur.fetchall()
        if not filas:
            return jsonify(error="Pedido no encontrado"), 404
        return jsonify(pedido=serializar_pedidos(filas)[0]), 200
    except Exception as error:
        app.logger.exception("Error interno")
        return jsonify(error="Error interno del servidor"), 500


@app.post("/")
def crear_pedido():
    """Crea un pedido y sus detalles asociados.

    Request JSON:
        Requiere `carne_integrante` y `detalles`. Acepta opcionalmente
        `cliente_id` y `estado`. Los campos `id` y `creado_en` se ignoran.
        Cada detalle requiere `sku`, `cantidad` y `precio_unitario_q`.

    Returns:
        Estado 201 con el pedido creado, 400 para JSON invalido o conflictos
        de integridad, 422 para datos invalidos y 500 ante un fallo del
        servidor.
    """
    if not request.is_json:
        return jsonify(error="El cuerpo debe enviarse como JSON"), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error="El cuerpo JSON debe ser un objeto"), 400

    datos.pop("id", None)
    datos.pop("creado_en", None)
    campos, error = validar_pedido(datos)
    if error:
        return jsonify(error=error), 422

    inventario_url = os.getenv("INVENTARIO_URL", "http://inventario:5000")
    
    if not campos["detalles"]:
        return jsonify(error="El pedido debe incluir al menos un producto"), 422

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM integrantes WHERE carne = %s", (campos["carne_integrante"],))
                if cur.fetchone() is None:
                    return jsonify(error="carne_integrante no existe en integrantes"), 400
    except Exception:
        app.logger.exception("No se pudo validar el carné")
        return jsonify(error="No se pudo validar el carné"), 500

    # El precio sale del catalogo; el precio que manda el cliente se ignora.
    catalogo_url = os.getenv("CATALOGO_URL", "http://catalogo:5000").rstrip("/")
    for detalle in campos["detalles"]:
        try:
            with urllib.request.urlopen(
                f"{catalogo_url}/productos/{urllib.parse.quote(detalle['sku'], safe='')}", timeout=10
            ) as response:
                detalle["precio_unitario_q"] = Decimal(str(json.load(response)["producto"]["precio_q"]))
        except HTTPError as error:
            if error.code == 404:
                return jsonify(error=f"SKU no existe en el catalogo: {detalle['sku']}"), 422
            app.logger.exception("Catalogo no pudo responder")
            return jsonify(error="No se pudo consultar el catalogo"), 502
        except (URLError, TimeoutError, ValueError, KeyError):
            app.logger.exception("No se pudo contactar catalogo")
            return jsonify(error="No se pudo consultar el catalogo"), 503

    # Inventario valida y descuenta todos los SKU bajo bloqueos en una transaccion.
    cantidades = [
        {"sku": d["sku"], "cantidad": d["cantidad"]}
        for d in campos["detalles"]
    ]
    req = urllib.request.Request(
        f"{inventario_url}/stock/descontar",
        data=json.dumps({"detalles": cantidades}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
    except HTTPError as error:
        if error.code in (404, 409, 422):
            try:
                mensaje = json.loads(error.read()).get("error", "Stock no disponible")
            except (ValueError, UnicodeDecodeError):
                mensaje = "Stock no disponible"
            return jsonify(error=mensaje), error.code
        app.logger.exception("Inventario no pudo procesar el descuento")
        return jsonify(error="No se pudo confirmar el inventario"), 502
    except (URLError, TimeoutError):
        app.logger.exception("No se pudo contactar inventario")
        return jsonify(error="No se pudo contactar inventario; verifique el stock antes de reintentar"), 503

    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pedidos (cliente_id, carne_integrante, estado)
                    VALUES (%s, %s, %s)
                    RETURNING id, cliente_id, carne_integrante, estado, creado_en
                """, (campos["cliente_id"], campos["carne_integrante"], campos["estado"]))
                pedido = cur.fetchone()

                detalles = []
                for detalle in campos["detalles"]:
                    cur.execute("""
                        INSERT INTO detalle_pedido
                            (pedido_id, sku, cantidad, precio_unitario_q)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, pedido_id, sku, cantidad, precio_unitario_q
                    """, (pedido[0], detalle["sku"], detalle["cantidad"],
                          detalle["precio_unitario_q"]))
                    detalles.append(cur.fetchone())

        respuesta = {
            "id": pedido[0],
            "cliente_id": pedido[1],
            "carne_integrante": pedido[2],
            "estado": pedido[3],
            "creado_en": pedido[4].isoformat(),
            "detalles": [serializar_detalle(detalle) for detalle in detalles],
        }
        return jsonify(pedido=respuesta), 201
    except Exception as error:
        app.logger.exception("Pedido no guardado tras descontar inventario: %s", error)
        try:
            reintegro = urllib.request.Request(
                f"{inventario_url}/stock/reintegrar",
                data=json.dumps({"detalles": cantidades}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(reintegro, timeout=10) as response:
                response.read()
        except Exception:
            app.logger.exception("Compensacion fallida: conciliar inventario manualmente")
            return jsonify(error="Pedido no guardado y reintegro fallido; requiere conciliacion"), 500
        if isinstance(error, psycopg.errors.ForeignKeyViolation):
            return jsonify(error="carne_integrante no existe en integrantes"), 400
        if isinstance(error, psycopg.errors.IntegrityError):
            return jsonify(error="Pedido invalido: viola una restriccion de datos"), 400
        return jsonify(error="Pedido no guardado; inventario reintegrado"), 500
