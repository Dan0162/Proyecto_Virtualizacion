import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
from urllib.error import HTTPError, URLError

from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = "reportes"
TIMEOUT = 5
ZONA = ZoneInfo("America/Guatemala")


@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)


def consultar_api(url, clave):
    """Consulta un servicio interno y valida la estructura de su respuesta."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            datos = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise RuntimeError(f"Error al consultar {clave}") from error
    if not isinstance(datos, dict) or not isinstance(datos.get(clave), list):
        raise ValueError(f"Respuesta invalida del servicio {clave}")
    return datos[clave]


def consultar_catalogo():
    return consultar_api(
        os.getenv("CATALOGO_URL", "http://catalogo:5000").rstrip("/") + "/productos",
        "productos",
    )


def consultar_inventario():
    return consultar_api(
        os.getenv("INVENTARIO_URL", "http://inventario:5000").rstrip("/") + "/stock",
        "stock",
    )


def contar_pedidos(fecha):
    url = os.getenv("PEDIDOS_URL", "http://pedidos:5000").rstrip("/") + f"/conteo?fecha={fecha.isoformat()}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return int(json.load(response)["total"])
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as error:
        raise RuntimeError("Error al consultar pedidos") from error


def generar_reporte(fecha):
    """Combina respuestas de las tres APIs sin acceder a sus bases de datos."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        productos_f = executor.submit(consultar_catalogo)
        stock_f = executor.submit(consultar_inventario)
        pedidos_f = executor.submit(contar_pedidos, fecha)
        productos_lista = productos_f.result()
        stock_lista = stock_f.result()
        pedidos_del_dia = pedidos_f.result()

    productos = {producto["sku"]: producto for producto in productos_lista}
    valor_total = Decimal("0")
    alertas = []

    for existencia in stock_lista:
        sku = existencia["sku"]
        cantidad = existencia["cantidad"]
        minimo = existencia["stock_minimo"]
        producto = productos.get(sku, {})
        if producto:
            valor_total += Decimal(str(producto["precio_q"])) * cantidad
        if cantidad < minimo:
            alertas.append({
                "sku": sku,
                "nombre": producto.get("nombre"),
                "categoria": producto.get("categoria"),
                "cantidad": cantidad,
                "stock_minimo": minimo,
            })

    return {
        "fecha": fecha.isoformat(),
        "resumen": {
            "total_productos": len(productos_lista),
            "valor_total_inventario_q": float(valor_total),
            "pedidos_del_dia": pedidos_del_dia,
        },
        "alertas_stock_bajo": alertas,
    }


@app.get("/")
def get_reporte():
    fecha_texto = request.args.get("fecha")
    if fecha_texto:
        try:
            fecha = date.fromisoformat(fecha_texto)
        except ValueError:
            return jsonify(error="fecha debe tener el formato YYYY-MM-DD"), 400
    else:
        fecha = datetime.now(ZONA).date()

    try:
        return jsonify(generar_reporte(fecha)), 200
    except (RuntimeError, ValueError, KeyError, TypeError, ArithmeticError):
        app.logger.exception("No se pudo generar el reporte")
        return jsonify(error="No se pudo consultar uno de los servicios"), 502
