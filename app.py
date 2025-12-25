from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)

# ✅ CORS robusto para Safari/iOS (incluye DELETE + OPTIONS + headers)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


# ---------- DB HELPERS ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seccion TEXT NOT NULL,
            modelo TEXT NOT NULL,
            cliente TEXT DEFAULT '',
            fecha TEXT DEFAULT '',
            ficha_json TEXT DEFAULT ''
        )
    """)
    # índice para evitar duplicados de modelo en la misma sección
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_modelo_seccion
        ON modelos(seccion, modelo)
    """)
    conn.commit()
    conn.close()


init_db()


def row_to_dict(row):
    d = dict(row)
    # compatibilidad: si el frontend/otros lados usan "nombre"
    d["nombre"] = d.get("modelo", "")
    return d


# ---------- HEALTH ----------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Backend Coronas activo"}), 200


# ---------- MODELOS CRUD ----------
@app.get("/api/modelos")
def get_modelos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM modelos ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows]), 200


@app.get("/api/modelos/<int:modelo_id>")
def get_modelo(modelo_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM modelos WHERE id = ?", (modelo_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Modelo no encontrado"}), 404
    return jsonify(row_to_dict(row)), 200


@app.post("/api/modelos")
def create_modelo():
    data = request.get_json(silent=True) or {}

    # Aceptamos "modelo" o "nombre" por compatibilidad
    seccion = str(data.get("seccion", "")).strip()
    modelo = str(data.get("modelo") or data.get("nombre") or "").strip()
    cliente = str(data.get("cliente", "")).strip()
    fecha = str(data.get("fecha", "")).strip()

    if not seccion or not modelo:
        return jsonify({"error": "Faltan campos obligatorios: seccion y modelo"}), 400

    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO modelos (seccion, modelo, cliente, fecha, ficha_json) VALUES (?, ?, ?, ?, ?)",
            (seccion, modelo, cliente, fecha, "")
        )
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        # duplicado por índice (seccion, modelo)
        return jsonify({"error": f"Ya existe un modelo '{modelo}' en la sección {seccion}"}), 409
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Error creando modelo: {str(e)}"}), 500

    row = conn.execute("SELECT * FROM modelos WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.put("/api/modelos/<int:modelo_id>")
def update_modelo(modelo_id):
    data = request.get_json(silent=True) or {}

    # Permitimos actualizar cliente / fecha / ficha_json
    cliente = data.get("cliente", None)
    fecha = data.get("fecha", None)
    ficha_json = data.get("ficha_json", None)

    conn = get_conn()
    cur = conn.cursor()

    row = conn.execute("SELECT * FROM modelos WHERE id = ?", (modelo_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Modelo no encontrado"}), 404

    try:
        if cliente is not None:
            cur.execute("UPDATE modelos SET cliente = ? WHERE id = ?", (str(cliente), modelo_id))
        if fecha is not None:
            cur.execute("UPDATE modelos SET fecha = ? WHERE id = ?", (str(fecha), modelo_id))
        if ficha_json is not None:
            # Validar que sea JSON si viene como objeto
            if isinstance(ficha_json, (dict, list)):
                ficha_json = json.dumps(ficha_json, ensure_ascii=False)
            cur.execute("UPDATE modelos SET ficha_json = ? WHERE id = ?", (str(ficha_json), modelo_id))

        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Error actualizando modelo: {str(e)}"}), 500

    row2 = conn.execute("SELECT * FROM modelos WHERE id = ?", (modelo_id,)).fetchone()
    conn.close()
    return jsonify(row_to_dict(row2)), 200


@app.delete("/api/modelos/<int:modelo_id>")
def delete_modelo(modelo_id):
    conn = get_conn()
    cur = conn.cursor()
    row = conn.execute("SELECT * FROM modelos WHERE id = ?", (modelo_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Modelo no encontrado"}), 404

    cur.execute("DELETE FROM modelos WHERE id = ?", (modelo_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Modelo eliminado"}), 200


# ✅ NUEVO: fallback iOS/Safari (si DELETE falla, borramos con POST)
@app.post("/api/modelos/<int:modelo_id>/delete")
def delete_modelo_post(modelo_id):
    return delete_modelo(modelo_id)


# ---------- FILTRADO POR SECCIÓN ----------
@app.get("/api/secciones/<seccion>/modelos")
def get_modelos_by_seccion(seccion):
    seccion = str(seccion).strip()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM modelos WHERE seccion = ? ORDER BY id DESC",
        (seccion,)
    ).fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows]), 200


# ---------- MAIN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
