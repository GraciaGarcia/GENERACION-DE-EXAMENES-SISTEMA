from flask import Flask, jsonify, request
from flask_cors import CORS
from config import SQLALCHEMY_DATABASE_URI, FLASK_RUN_PORT
from extensions import db
from routes.auth import auth_bp
from routes.cursos import cursos_bp
from routes.preguntas import preguntas_bp
from routes.examenes import examenes_bp
from routes.realizar_examen import realizar_examen_bp
from routes.reportes import reportes_bp
import os


def create_app():
    # Crear la aplicación Flask
    app = Flask(__name__)
    
    # Configuración CORS
    CORS(app, origins='*')
    
    # Configuración de la aplicación
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'tu-clave-secreta-aqui'
    app.config['JSON_AS_ASCII'] = False  # Para soporte de caracteres especiales
    
    # Inicialización de extensiones
    db.init_app(app)

    # Ruta raíz
    @app.route('/')
    def index():
        return jsonify({
            "message": "API de Sistema de Exámenes funcionando correctamente",
            "version": "1.0",
            "endpoints": {
                "auth": {
                    "/login (POST)": "Inicia sesión",
                    "/register (POST)": "Registra un nuevo usuario",
                    "/carreras (GET)": "Obtiene todas las carreras activas"
                },
                "cursos": {
                    "/ (GET)": "Obtiene la lista de cursos",
                    "/<id_curso> (GET)": "Obtiene detalles de un curso específico",
                    "/ (POST)": "Crea un nuevo curso",
                    "/<id_curso> (PUT)": "Actualiza un curso específico"
                },
                "examenes": {
                    "/ (GET)": "Obtiene todos los exámenes",
                    "/<id_examen> (GET)": "Obtiene detalles de un examen específico",
                    "/ (POST)": "Crea un nuevo examen",
                    "/<id_examen>/preguntas (POST)": "Agrega una pregunta a un examen",
                    "/<id_examen>/estado (PUT)": "Cambia el estado de un examen"
                },
                "realizar_examen": {
                    "/<id_examen>/iniciar (POST)": "Inicia un examen para el estudiante",
                    "/estudiante/<id_examen_estudiante>/responder (POST)": "Guarda las respuestas de un examen",
                    "/estudiante/<id_examen_estudiante>/finalizar (POST)": "Finaliza un examen",
                    "/estudiante/<id_examen_estudiante>/estado (GET)": "Obtiene el estado de un examen en progreso"
                },
                "preguntas": {
                    "/ (GET)": "Obtiene todas las preguntas",
                    "/<id_pregunta> (GET)": "Obtiene detalles de una pregunta específica",
                    "/ (POST)": "Crea una nueva pregunta",
                    "/<id_pregunta> (PUT)": "Actualiza una pregunta existente",
                    "/<id_pregunta> (DELETE)": "Elimina una pregunta"
                },
                "reportes": {
                    "/examen/<id_examen>/resultados (GET)": "Obtiene los resultados de un examen específico",
                    "/estudiante/<id_estudiante>/historial (GET)": "Obtiene el historial de exámenes de un estudiante",
                    "/examen/<id_examen_estudiante>/detalle (GET)": "Obtiene el detalle completo de un examen realizado por un estudiante",
                    "/profesor/<id_profesor>/estadisticas (GET)": "Obtiene estadísticas generales de un profesor",
                    "/curso/<id_curso>/rendimiento (GET)": "Obtiene estadísticas de rendimiento por curso"
                }
            }
        })

    # Ruta de health check
    @app.route('/health')
    def health_check():
        try:
            # Verificar conexión a la base de datos
            db.session.execute('SELECT 1')
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except Exception as e:
            return jsonify({"status": "unhealthy", "error": str(e)}), 500

    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(cursos_bp, url_prefix='/api/cursos')
    app.register_blueprint(preguntas_bp, url_prefix='/api/preguntas')
    app.register_blueprint(examenes_bp, url_prefix='/api/examenes')
    app.register_blueprint(realizar_examen_bp, url_prefix='/api/realizar-examen')
    app.register_blueprint(reportes_bp, url_prefix='/api/reportes')

    # Manejadores de errores globales
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint no encontrado", "code": 404}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Error interno del servidor", "code": 500}), 500

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Solicitud incorrecta", "code": 400}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "No autorizado", "code": 401}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Acceso prohibido", "code": 403}), 403

    # Middleware para logging de requests (opcional)
    @app.before_request
    def log_request_info():
        if app.debug:
            print(f"Request: {request.method} {request.url}")

    # Crear las tablas de la base de datos si no existen
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tablas de base de datos creadas/verificadas exitosamente")
        except Exception as e:
            print(f"❌ Error al crear tablas: {e}")

    return app


if __name__ == '__main__':
    app = create_app()
    
    # Configuración para desarrollo vs producción
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando servidor en puerto {FLASK_RUN_PORT}")
    print(f"🔧 Modo debug: {debug_mode}")
    
    app.run(
        host='0.0.0.0', 
        port=FLASK_RUN_PORT,
        debug=debug_mode
    )
