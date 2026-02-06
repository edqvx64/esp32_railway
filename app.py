from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import mysql.connector
from mysql.connector import pooling, Error

app = Flask(__name__)
CORS(app)

# =========================
# Configuración MySQL
# =========================
def db_params(use_ssl_disabled=True):
    host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
    user = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD")
    database = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")
    port = int(os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or 3306)

    params = dict(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        autocommit=False,
        connection_timeout=10
    )

    # Railway (conexión interna) → sin SSL
    if use_ssl_disabled:
        params["ssl_disabled"] = True

    return params


# =========================
# Pool de conexiones
# =========================
POOL = pooling.MySQLConnectionPool(
    pool_name="railway_pool",
    pool_size=5,
    **db_params(use_ssl_disabled=True)
)


def get_conn(retries=2, wait=1.0):
    last_error = None
    for _ in range(retries + 1):
        try:
            return POOL.get_connection()
        except Error as e:
            last_error = e
            time.sleep(wait)
    raise last_error


# =========================
# Health check
# =========================
@app.route('/health', methods=['GET'])
def health():
    try:
        cn = get_conn()
        cur = cn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        cn.close()
        return "ok", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# Endpoint ESP32
# =========================
@app.route('/datos', methods=['POST'])
def recibir_datos():
    cn = None
    cur = None

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON inválido"}), 400

        sql = """
            INSERT INTO mediciones (
                sensor_id, fecha, hora,
                temperatura, humedad, presion, gas,
                altitud, latitud, longitud
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        valores = (
            data["sensor_id"],
            data["fecha"],
            data["hora"],
            float(data["temperatura"]),
            float(data["humedad"]),
            float(data["presion"]),
            float(data["gas"]),
            float(data["altitud"]),
            float(data["latitud"]),
            float(data["longitud"]),
        )

        cn = get_conn()
        cur = cn.cursor()
        cur.execute(sql, valores)
        cn.commit()

        return jsonify({"mensaje": "Insertado correctamente"}), 200

    except Error:
        # Reintento simple si el pool perdió la conexión
        try:
            if cur:
                cur.close()
            if cn:
                cn.close()
        except:
            pass

        try:
            cn = get_conn()
            cur = cn.cursor()
            cur.execute(sql, valores)
            cn.commit()
            return jsonify({"mensaje": "Insertado correctamente (retry)"}), 200
        except Exception as e2:
            return jsonify({"error": str(e2)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            if cur:
                cur.close()
            if cn:
                cn.close()
        except:
            pass


# =========================
# Home
# =========================
@app.route('/')
def home():
    return "API ESP32 lista y funcionando.", 200


# =========================
# Main
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
