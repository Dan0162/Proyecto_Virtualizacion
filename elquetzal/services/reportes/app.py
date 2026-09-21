import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import psycopg
from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = "reportes"


@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)

def connect_db(prefix, default_name):
    """Abre una conexion usando variables especificas para cada base."""
    return psycopg.connect(
        host=os.getenv(f"{prefix}_DB_HOST", os.getenv("DB_HOST")),
        port=os.getenv(f"{prefix}_DB_PORT", os.getenv("DB_PORT", "5432")),
        dbname=os.getenv(f"{prefix}_DB_NAME", default_name),
        user=os.getenv(f"{prefix}_DB_USER", os.getenv("DB_USER")),
        password=os.getenv(f"{prefix}_DB_PASSWORD", os.getenv("DB_PASSWORD")),
    )


def consultar_catalogo():
    """Obtiene el total y los precios necesarios para valorar inventario."""
    with connect_db("CATALOGO", "catalogo_db") as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sku, nombre, categoria, precio_q,
                       COUNT(*) OVER () AS total_productos
                FROM productos
            """)
            filas = cur.fetchall()

    total_productos = filas[0][4] if filas else 0
    productos = {
        fila[0]: {
            "nombre": fila[1],
            "categoria": fila[2],
            "precio_q": fila[3],
        }
        for fila in filas
    }
    return total_productos, productos


def consultar_inventario():
    """Obtiene existencias y detecta alertas en una sola consulta."""
    with connect_db("INVENTARIO", "inventario_db") as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sku, cantidad, stock_minimo
                FROM stock
            """)
            existencias = cur.fetchall()
    return existencias, [fila for fila in existencias if fila[2] > fila[1]]


def contar_pedidos_del_dia(fecha):
    """Cuenta pedidos creados dentro del dia solicitado."""
    fecha_siguiente = fecha + timedelta(days=1)
    with connect_db("PEDIDOS", "pedidos_db") as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM pedidos
                WHERE creado_en >= %s
                  AND creado_en < %s
            """, (fecha, fecha_siguiente))
            return cur.fetchone()[0]


def generar_reporte(fecha):
    """Consulta las tres bases en paralelo y combina sus resultados."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futuro_catalogo = executor.submit(consultar_catalogo)
        futuro_inventario = executor.submit(consultar_inventario)
        futuro_pedidos = executor.submit(contar_pedidos_del_dia, fecha)

        total_productos, productos = futuro_catalogo.result()
        existencias, filas_alertas = futuro_inventario.result()
        pedidos_del_dia = futuro_pedidos.result()

    valor_total = Decimal("0")
    for sku, cantidad, _ in existencias:
        producto = productos.get(sku)
        if producto is not None:
            valor_total += producto["precio_q"] * cantidad

    alertas = []
    for sku, cantidad, stock_minimo in filas_alertas:
        producto = productos.get(sku, {})
        alertas.append({
            "sku": sku,
            "nombre": producto.get("nombre"),
            "categoria": producto.get("categoria"),
            "cantidad": cantidad,
            "stock_minimo": stock_minimo,
        })

    return {
        "fecha": fecha.isoformat(),
        "resumen": {
            "total_productos": total_productos,
            "valor_total_inventario_q": float(valor_total),
            "pedidos_del_dia": pedidos_del_dia,
        },
        "alertas_stock_bajo": alertas,
    }


@app.get("/")
def get_reporte():
    """Genera el resumen de catalogo, inventario y pedidos.

    Query params:
        fecha: Fecha opcional en formato `YYYY-MM-DD`. Si se omite, se usa la
        fecha del servidor.

    Returns:
        Estado 200 con el resumen, 400 si la fecha es invalida y 500 ante un
        fallo de conexion o consulta a las bases de datos.
    """
    fecha_texto = request.args.get("fecha")
    if fecha_texto:
        try:
            fecha = date.fromisoformat(fecha_texto)
        except ValueError:
            return jsonify(error="fecha debe tener el formato YYYY-MM-DD"), 400
    else:
        fecha = date.today()

    try:
        return jsonify(generar_reporte(fecha)), 200
    except Exception as error:
        return jsonify(error=str(error)), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
