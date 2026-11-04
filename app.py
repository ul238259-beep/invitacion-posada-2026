import os
from flask import Flask, render_template, request, jsonify
import psycopg

app = Flask(__name__)

# Función para conectar a la base de datos (lee la nube o usa local si no existe)
def get_db_connection():
    # Render nos dará una variable llamada DATABASE_URL
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return get_db_connection(database_url)
    else:
        # Tus datos locales por si quieres probar en tu PC
        return get_db_connection(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )

@app.route('/')
def index():
    return render_template('index.html')

# Endpoint para recibir el registro de asistencia del formulario
@app.route('/api/confirmar', methods=['POST'])
def confirmar_asistencia():
    datos = request.json
    nombre_familia = datos.get('nombre_familia')
    integrantes = datos.get('integrantes', []) # Lista con los nombres de cada asistente
    total_asistentes = len(integrantes)

    if not nombre_familia or total_asistentes == 0:
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    try:
        # Conexión a PostgreSQL
        conn = get_db_connection(**DB_CONFIG)
        cur = conn.cursor()

        # 1. Insertar en la tabla familias y obtener el ID generado
        cur.execute(
            "INSERT INTO public.familias (nombre_familia, total_asistentes) VALUES (%s, %s) RETURNING id;",
            (nombre_familia, total_asistentes)
        )
        familia_id = cur.fetchone()[0]

        # 2. Insertar cada integrante en su respectiva tabla
        for integrante in integrantes:
            cur.execute(
                "INSERT INTO public.integrantes (familia_id, nombre_completo) VALUES (%s, %s);",
                (familia_id, integrante)
            )

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True, "mensaje": "¡Asistencia registrada correctamente en la base de datos!"})

    except Exception as e:
        print("Error al conectar con la base de datos:", e)
        return jsonify({"error": "Hubo un error al guardar en la base de datos"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)