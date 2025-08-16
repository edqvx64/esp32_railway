from flask import Flask, request, jsonify
from flask_cors import CORS
import os, time
import mysql.connector
from mysql.connector import pooling, Error

app = Flask(__name__)
CORS(app)

def db_params(use_ssl_disabled=True):
    host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
    user = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD")
    database = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")
    port = int(os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or 3306)

    params = dict(
        host=host, user=user, password=password, database=database, port=port,
        autocommit=False, connection_timeout=10
    )
    if use_ssl_disabled:
        params["ssl_disabled"] = True
    # Si prefieres validar TLS con CA (cuando la tengas):
    # params.update({"client_flags":[mysql.connector.ClientFlag.SSL], "ssl_ca":"ca.pem"})
    return params

# Pool de conexiones (reusa sockets y evita reconexiones por request)
POOL = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    **db_params(use_ssl_disabled=True)  # pon False si vas a usar ssl_ca
)

def get_conn(retries=2, wait=1.0):
    last = None
    for _ in range(retries+1):
        try:
            return POOL.get_connection()
        except Error as e:
            last = e
            time.sleep(wait)
    raise last

@app.route('/health', methods=['GET'])
def health():
    try:
        cn = get_conn()
        cur = cn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close(); cn.close()
        return "ok", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/datos', methods=['POST'])
def recibir_datos():
    cn = None; cur = None
    try:
        data = request.get_json(force=True)
        cn = get_conn()
        cur = cn.cursor()

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

        cur.execute(sql, valores)
        cn.commit()
        return jsonify({"mensaje": "Insertado correctamente"}), 200

    except Error as e:
        # reintento suave si el handshake murió o hubo corte momentáneo
        try:
            if cur: cur.close()
            if cn: cn.close()
        except: pass
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
            if cur: cur.close()
            if cn: cn.close()
        except: pass

@app.route('/')
def home():
    return 'API ESP32 lista y funcionando.', 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
