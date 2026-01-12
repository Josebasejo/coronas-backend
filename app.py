from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor, Json

import os
from dotenv import load_dotenv

load_dotenv()  # ✅ carga .env desde la carpeta actual

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada.")



app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        create table if not exists public.modelos (
          id bigserial primary key,
          seccion text not null,
          modelo text not null,
          cliente text default '',
          fecha text default '',
          ficha_json jsonb default '{}'::jsonb
        );
    """)
    cur.execute("""
        create unique index if not exists idx_modelo_seccion
        on public.modelos (seccion, modelo);
    """)
    conn.commit()
    cur.close()
    conn.close()


def row_to_dict(row):
    d = dict(row)
    d["nombre"] = d.get("modelo", "")
    return d


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Backend Coronas activo"}), 200


@app.get("/api/modelos")
def get_modelos():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select * from public.modelos order by id desc;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows]), 200


@app.get("/api/modelos/<int:modelo_id>")
def get_modelo(modelo_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select * from public.modelos where id = %s;", (modelo_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "Modelo no encontrado"}), 404
    return jsonify(row_to_dict(row)), 200


@app.get("/api/secciones/<seccion>/modelos")
def get_modelos_by_seccion(seccion):
    seccion = str(seccion).strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "select * from public.modelos where seccion = %s order by id desc;",
        (seccion,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows]), 200


@app.post("/api/modelos")
def create_modelo():
    data = request.get_json(silent=True) or {}

    seccion = str(data.get("seccion", "")).strip()
    modelo = str(data.get("modelo") or data.get("nombre") or "").strip()
    cliente = str(data.get("cliente", "")).strip()
    fecha = str(data.get("fecha", "")).strip() or datetime.now().strftime("%Y-%m-%d")

    if not seccion or not modelo:
        return jsonify({"error": "Faltan campos obligatorios: seccion y modelo"}), 400

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            insert into public.modelos (seccion, modelo, cliente, fecha, ficha_json)
            values (%s, %s, %s, %s, %s)
            returning *;
            """,
            (seccion, modelo, cliente, fecha, Json({}))
        )
        row = cur.fetchone()
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": f"Ya existe un modelo '{modelo}' en la sección {seccion}"}), 409
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": f"Error creando modelo: {str(e)}"}), 500

    cur.close()
    conn.close()
    return jsonify(row_to_dict(row)), 201


@app.put("/api/modelos/<int:modelo_id>")
def update_modelo(modelo_id):
    data = request.get_json(silent=True) or {}

    cliente = data.get("cliente", None)
    fecha = data.get("fecha", None)
    ficha_json = data.get("ficha_json", None)

    ficha_obj = None
    if ficha_json is not None:
        if isinstance(ficha_json, (dict, list)):
            ficha_obj = ficha_json
        elif isinstance(ficha_json, str):
            try:
                ficha_obj = json.loads(ficha_json)
            except:
                ficha_obj = {"raw": ficha_json}
        else:
            ficha_obj = {"raw": str(ficha_json)}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("select id from public.modelos where id = %s;", (modelo_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Modelo no encontrado"}), 404

    try:
        if cliente is not None:
            cur.execute("update public.modelos set cliente = %s where id = %s;", (str(cliente), modelo_id))
        if fecha is not None:
            cur.execute("update public.modelos set fecha = %s where id = %s;", (str(fecha), modelo_id))
        if ficha_json is not None:
            cur.execute("update public.modelos set ficha_json = %s where id = %s;", (Json(ficha_obj), modelo_id))

        cur.execute("select * from public.modelos where id = %s;", (modelo_id,))
        row = cur.fetchone()
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": f"Error actualizando modelo: {str(e)}"}), 500

    cur.close()
    conn.close()
    return jsonify(row_to_dict(row)), 200


@app.delete("/api/modelos/<int:modelo_id>")
def delete_modelo(modelo_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("select id from public.modelos where id = %s;", (modelo_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Modelo no encontrado"}), 404

    cur.execute("delete from public.modelos where id = %s;", (modelo_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "ok", "message": "Modelo eliminado"}), 200


# fallback iOS/Safari (por si acaso)
@app.post("/api/modelos/<int:modelo_id>/delete")
def delete_modelo_post(modelo_id):
    return delete_modelo(modelo_id)


# Crear tabla/índice al arrancar
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
