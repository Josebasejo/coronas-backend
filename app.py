from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

# 🔹 Inicialización de la aplicación Flask
app = Flask(__name__)
CORS(app)  # Permite acceso desde tu frontend en Render

# 🔹 Render utiliza el puerto 8080
PORT = int(os.environ.get("PORT", 8080))

# ---------------------------
# 🔸 Función para conectar a la base de datos
# ---------------------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------
# 🔸 Ruta raíz (para comprobar si el backend está activo)
# ---------------------------
@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Backend Coronas activo"})


# ---------------------------
# 🔸 Obtener todos los modelos
# ---------------------------
@app.route("/api/modelos", methods=["GET"])
def get_modelos():
    conn = get_db_connection()
    modelos = conn.execute("SELECT * FROM modelos").fetchall()
    conn.close()

    resultado = [
        {
            "id": row["id"],
            "modelo": row["modelo"],
            "seccion": row["seccion"],
            "cliente": row["cliente"],
            "fecha": row["fecha"],
            "ficha_json": row["ficha_json"]
        }
        for row in modelos
    ]
    return jsonify(resultado)


# ---------------------------
# 🔸 Crear nuevo modelo
# ---------------------------
@app.route("/api/modelos", methods=["POST"])
def crear_modelo():
    data = request.get_json()
    modelo = data.get("modelo")
    seccion = data.get("seccion")
    cliente = data.get("cliente", "")
    fecha = data.get("fecha", "")
    ficha_json = data.get("ficha_json", "")

    if not modelo or not seccion:
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO modelos (modelo, seccion, cliente, fecha, ficha_json) VALUES (?, ?, ?, ?, ?)",
        (modelo, seccion, cliente, fecha, ficha_json)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": "Modelo creado correctamente"})


# ---------------------------
# 🔸 Eliminar un modelo
# ---------------------------
@app.route("/api/modelos/<int:id>", methods=["DELETE"])
def eliminar_modelo(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM modelos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": f"Modelo {id} eliminado"})


# ---------------------------
# 🔸 Crear tabla en caso de que no exista
# ---------------------------
def inicializar_bd():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo TEXT NOT NULL,
            seccion TEXT NOT NULL,
            cliente TEXT,
            fecha TEXT,
            ficha_json TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------------------------
# 🔸 Punto de entrada principal
# ---------------------------
if __name__ == "__main__":
    inicializar_bd()
    app.run(host="0.0.0.0", port=PORT)


# ---------------------------
# 🔸 ROL ADMIN/INVITADO
# ---------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import jwt
import datetime

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "clave_supersecreta")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "CIEcoronas2025")

    if username == admin_user and password == admin_pass:
        token = jwt.encode(
            {"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)},
            app.config['SECRET_KEY'],
            algorithm="HS256"
        )
        return jsonify({"token": token, "role": "admin"}), 200

    return jsonify({"message": "Credenciales inválidas"}), 401
