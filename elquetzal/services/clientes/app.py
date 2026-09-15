# Esto es solo la base mínima digamos, podes cambiar lo que crear que necesites cambiar.
# Igual en el otro archivo de requerimientos.
import os
from flask import Flask, jsonify

app = Flask(__name__)
SERVICE_NAME = "clientes"

# Verificar si el servicio está "vivo".
@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)

# Leemos el nombre y host de la base de datos (lo tiene que poner Daniel luego en el .env)
@app.get("/")
def index():
    return jsonify(message=f"Microservicio {SERVICE_NAME} de El Quetzal", db_host=os.getenv("DB_HOST"), db_name=os.getenv)

# Solo sirve para debug fuera del contenedor, el servicio lo arranca gunicorn
if __name__ == "__main__":
    # Escuchamos el 0.0.0.0 y no 127.0.0.1 para que pueda ser alcanzado.
    app.run(host="0.0.0.0", port=5000)
