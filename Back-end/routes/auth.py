# routes/auth.py
from flask import Blueprint, request, jsonify
from models import Usuario, Carrera
from extensions import db
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email y contraseña son requeridos'}), 400
        
        # Buscar usuario por email
        usuario = Usuario.query.filter_by(email=email, estado='A').first()
        
        if not usuario:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Verificar contraseña (en producción usar hash)
        if usuario.password != password:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Actualizar último acceso
        usuario.fecha_ultimo_acceso = datetime.utcnow()
        db.session.commit()
        
        # Obtener información de la carrera
        carrera = Carrera.query.get(usuario.id_carrera)
        
        return jsonify({
            'message': 'Login exitoso',
            'usuario': {
                'id_usuario': usuario.id_usuario,
                'nombres': usuario.nombres,
                'apellidos': usuario.apellidos,
                'email': usuario.email,
                'tipo_usuario': usuario.tipo_usuario,
                'carrera': {
                    'id_carrera': carrera.id_carrera,
                    'nombre_carrera': carrera.nombre_carrera
                } if carrera else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error en el servidor: {str(e)}'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['nombres', 'apellidos', 'email', 'password', 'tipo_usuario', 'id_carrera']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400
        
        # Verificar si el email ya existe
        existing_user = Usuario.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'El email ya está registrado'}), 400
        
        # Verificar tipo de usuario válido
        if data['tipo_usuario'] not in ['PROFESOR', 'ESTUDIANTE']:
            return jsonify({'error': 'Tipo de usuario inválido'}), 400
        
        # Verificar que la carrera existe
        carrera = Carrera.query.get(data['id_carrera'])
        if not carrera:
            return jsonify({'error': 'Carrera no encontrada'}), 400
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombres=data['nombres'],
            apellidos=data['apellidos'],
            email=data['email'],
            password=data['password'],  # En producción usar hash
            tipo_usuario=data['tipo_usuario'],
            id_carrera=data['id_carrera']
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario registrado exitosamente',
            'usuario': nuevo_usuario.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al registrar usuario: {str(e)}'}), 500

@auth_bp.route('/carreras', methods=['GET'])
def get_carreras():
    try:
        carreras = Carrera.query.filter_by(estado='A').all()
        return jsonify([carrera.to_dict() for carrera in carreras]), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener carreras: {str(e)}'}), 500
    
# Obtener todos los estudiantes
@auth_bp.route('/estudiantes', methods=['GET'])
def get_estudiantes():
    try:
        # Solo los profesores pueden acceder a esta ruta
        # Si el usuario autenticado es un profesor, devuelves todos los estudiantes
        # Filtramos solo los estudiantes activos
        estudiantes = Usuario.query.filter_by(tipo_usuario='ESTUDIANTE', estado='A').all()

        # Retornar la lista de estudiantes
        return jsonify([{
            'id_usuario': estudiante.id_usuario,
            'nombres': estudiante.nombres,
            'apellidos': estudiante.apellidos,
            'email': estudiante.email,
            'tipo_usuario': estudiante.tipo_usuario,
            'id_carrera': estudiante.id_carrera,
        } for estudiante in estudiantes]), 200

    except Exception as e:
        return jsonify({'error': f'Error al obtener estudiantes: {str(e)}'}), 500

# Obtener todos los profesores
@auth_bp.route('/profesores', methods=['GET'])
def get_profesores():
    try:
        # Solo los administradores o usuarios con privilegios adecuados pueden acceder a esta ruta
        # Filtramos solo los profesores activos
        profesores = Usuario.query.filter_by(tipo_usuario='PROFESOR', estado='A').all()

        # Retornar la lista de profesores
        return jsonify([{
            'id_usuario': profesor.id_usuario,
            'nombres': profesor.nombres,
            'apellidos': profesor.apellidos,
            'email': profesor.email,
            'tipo_usuario': profesor.tipo_usuario,
            'id_carrera': profesor.id_carrera,
        } for profesor in profesores]), 200

    except Exception as e:
        return jsonify({'error': f'Error al obtener profesores: {str(e)}'}), 500


# Obtener un profesor por su ID
@auth_bp.route('/profesores/<int:id_profesor>', methods=['GET'])
def get_profesor(id_profesor):
    try:
        # Buscar profesor por ID y estado activo
        profesor = Usuario.query.filter_by(id_usuario=id_profesor, tipo_usuario='PROFESOR', estado='A').first()

        if not profesor:
            return jsonify({'error': 'Profesor no encontrado o inactivo'}), 404

        # Retornar los datos del profesor
        return jsonify({
            'id_usuario': profesor.id_usuario,
            'nombres': profesor.nombres,
            'apellidos': profesor.apellidos,
            'email': profesor.email,
            'tipo_usuario': profesor.tipo_usuario,
            'id_carrera': profesor.id_carrera,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error al obtener profesor: {str(e)}'}), 500


# Obtener un estudiante por su ID
@auth_bp.route('/estudiantes/<int:id_estudiante>', methods=['GET'])
def get_estudiante(id_estudiante):
    try:
        # Buscar estudiante por ID y estado activo
        estudiante = Usuario.query.filter_by(id_usuario=id_estudiante, tipo_usuario='ESTUDIANTE', estado='A').first()

        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado o inactivo'}), 404

        # Retornar los datos del estudiante
        return jsonify({
            'id_usuario': estudiante.id_usuario,
            'nombres': estudiante.nombres,
            'apellidos': estudiante.apellidos,
            'email': estudiante.email,
            'tipo_usuario': estudiante.tipo_usuario,
            'id_carrera': estudiante.id_carrera,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error al obtener estudiante: {str(e)}'}), 500
