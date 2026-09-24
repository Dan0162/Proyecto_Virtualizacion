import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError

from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = "reportes"
TIMEOUT = 5


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


def consultar_pedidos():
    return consultar_api(
        os.getenv("PEDIDOS_URL", "http://pedidos:5000").rstrip("/") + "/",
        "pedidos",
    )


def generar_reporte(fecha):
    """Combina respuestas de las tres APIs sin acceder a sus bases de datos."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        productos_f = executor.submit(consultar_catalogo)
        stock_f = executor.submit(consultar_inventario)
        pedidos_f = executor.submit(consultar_pedidos)
        productos_lista = productos_f.result()
        stock_lista = stock_f.result()
        pedidos_lista = pedidos_f.result()

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

    pedidos_del_dia = 0
    for pedido in pedidos_lista:
        creado_en = datetime.fromisoformat(pedido["creado_en"].replace("Z", "+00:00"))
        if creado_en.tzinfo is None:
            creado_en = creado_en.replace(tzinfo=timezone.utc)
        if creado_en.astimezone(timezone.utc).date() == fecha:
            pedidos_del_dia += 1

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
        fecha = datetime.now(timezone.utc).date()

    try:
        return jsonify(generar_reporte(fecha)), 200
    except (RuntimeError, ValueError, KeyError, TypeError, ArithmeticError):
        app.logger.exception("No se pudo generar el reporte")
        return jsonify(error="No se pudo consultar uno de los servicios"), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
