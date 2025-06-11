from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", "3306"))
)

@app.route('/datos', methods=['POST'])
def recibir_datos():
    try:
        data = request.get_json()
        cursor = db.cursor()
        sql = """
            INSERT INTO mediciones (
                sensor_id, fecha, hora,
                temperatura, humedad, presion, gas,
                altitud, latitud, longitud
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            data['sensor_id'], data['fecha'], data['hora'],
            float(data['temperatura']), float(data['humedad']),
            float(data['presion']), float(data['gas']),
            float(data['altitud']), float(data['latitud']), float(data['longitud'])
        )
        cursor.execute(sql, valores)
        db.commit()
        cursor.close()
        return jsonify({"mensaje": "Insertado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return 'API ESP32 lista y funcionando', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)