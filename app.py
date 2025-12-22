from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, query_db
import datetime

app = Flask(__name__)
CORS(app)

init_db()

@app.route('/api/modelos', methods=['GET'])
def get_modelos():
    data = query_db("SELECT * FROM modelos ORDER BY fecha DESC")
    modelos = [{"id": r[0], "seccion": r[1], "modelo": r[2], "cliente": r[3], "fecha": r[4]} for r in data]
    return jsonify(modelos)

@app.route('/api/modelos', methods=['POST'])
def add_modelo():
    data = request.json
    query_db(
        "INSERT INTO modelos (seccion, modelo, cliente, fecha) VALUES (?, ?, ?, ?)",
        [data['seccion'], data['modelo'], data['cliente'], datetime.date.today()]
    )
    return jsonify({"status": "ok"})

@app.route('/api/modelos/<int:id>', methods=['DELETE'])
def delete_modelo(id):
    query_db("DELETE FROM modelos WHERE id=?", [id])
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
