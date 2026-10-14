"""Pruebas de integracion contra el stack levantado (Compose o k3s).

    BASE_URL=http://localhost/api python -m unittest discover -s elquetzal/tests
"""
import json
import os
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

BASE = os.getenv("BASE_URL", "http://localhost/api").rstrip("/")
CARNE = os.getenv("CARNE", "1040023")


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def pedido(sku, cantidad, carne=CARNE, precio=1):
    return call("POST", "/pedidos/", {
        "carne_integrante": carne,
        "detalles": [{"sku": sku, "cantidad": cantidad, "precio_unitario_q": precio}],
    })


class PedidosTest(unittest.TestCase):
    SKU = "TEST-AUDIT"

    @classmethod
    def setUpClass(cls):
        call("DELETE", f"/inventario/stock/{cls.SKU}")
        call("DELETE", f"/catalogo/productos/{cls.SKU}")
        call("POST", "/catalogo/productos",
             {"sku": cls.SKU, "nombre": "Prueba", "categoria": "Test", "precio_q": 25})
        call("POST", "/inventario/stock", {"sku": cls.SKU, "cantidad": 10, "stock_minimo": 1})

    @classmethod
    def tearDownClass(cls):
        call("DELETE", f"/inventario/stock/{cls.SKU}")
        call("DELETE", f"/catalogo/productos/{cls.SKU}")

    def stock(self):
        return call("GET", f"/inventario/stock/{self.SKU}")[1]["stock"]["cantidad"]

    def reset(self, cantidad):
        call("PUT", f"/inventario/stock/{self.SKU}", {"cantidad": cantidad})

    def test_precio_viene_del_catalogo(self):
        self.reset(10)
        status, body = pedido(self.SKU, 1, precio=0.01)
        self.assertEqual(status, 201)
        self.assertEqual(body["pedido"]["detalles"][0]["precio_unitario_q"], 25.0)

    def test_dos_pedidos_a_la_vez_no_venden_de_mas(self):
        self.reset(5)
        with ThreadPoolExecutor(2) as pool:
            r = list(pool.map(lambda _: pedido(self.SKU, 4)[0], range(2)))
        self.assertEqual(sorted(r), [201, 409])
        self.assertEqual(self.stock(), 1)

    def test_carne_invalido_no_toca_el_stock(self):
        self.reset(10)
        status, _ = pedido(self.SKU, 2, carne="0000000")
        self.assertEqual(status, 400)
        self.assertEqual(self.stock(), 10)

    def test_solo_pedidos_confirmados(self):
        status, _ = call("POST", "/pedidos/", {
            "carne_integrante": CARNE, "estado": "cancelado",
            "detalles": [{"sku": self.SKU, "cantidad": 1}]})
        self.assertEqual(status, 422)


if __name__ == "__main__":
    unittest.main()
