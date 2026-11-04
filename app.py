import os
from flask import Flask, render_template, request, jsonify
import psycopg

app = Flask(__name__)

# Función para conectar a la base de datos (lee la nube o usa local si no existe)
def get_db_connection():
    # Render busca la variable de entorno llamada "DATABASE_URL"
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg.connect(database_url)
    else:
        # Tus datos locales por si quieres probar en tu PC
        return psycopg.connect(
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
        conn = get_db_connection()
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

        return jsonify({"success": True, "mensaje": "¡Asistencia registrada correctamente!"})

    except Exception as e:
        print("Error al conectar con la base de datos:", e)
        return jsonify({"error": "Hubo un error al guardar los datos"}), 500

@app.route('/admin/ver-lista')
def ver_lista():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # ¡Importante! Asegúrate de incluir la palabra SELECT aquí:
        cur.execute("""
            SELECT f.id, f.nombre_familia, f.total_asistentes, 
            STRING_AGG(i.nombre_completo, ', ') as integrantes
            FROM public.familias f
            LEFT JOIN public.integrantes i ON f.id = i.familia_id
            GROUP BY f.id, f.nombre_familia, f.total_asistentes;
        """)
        resultados = cur.fetchall()
        cur.close()
        conn.close()

        html = "<h2>Familias Registradas</h2><table border='1' cellpadding='8'><tr><th>Familia</th><th>Total Asistentes</th><th>Integrantes</th></tr>"
        for row in resultados:
            html += f"<tr><td>{row[1]}</td><td>{row[2]}</td><td>{row[3] or 'Ninguno'}</td></tr>"
        html += "</table><br><a href='/'>Volver al inicio</a>"
        return html
    except Exception as e:
        return f"Error al consultar la base de datos: {e}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)

    # Crear las tablas automáticamente al arrancar si no existen
with app.app_context():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.familias (
                id SERIAL PRIMARY KEY,
                nombre_familia VARCHAR(255) NOT NULL,
                total_asistentes INT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS public.integrantes (
                id SERIAL PRIMARY KEY,
                familia_id INT REFERENCES public.familias(id) ON DELETE CASCADE,
                nombre_completo VARCHAR(255) NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Tablas creadas o verificadas exitosamente en la base de datos.")
    except Exception as e:
        print("Error al crear tablas automáticamente:", e)