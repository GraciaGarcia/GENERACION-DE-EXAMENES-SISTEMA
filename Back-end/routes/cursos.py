# routes/cursos.py
from flask import Blueprint, request, jsonify
from models import Curso, Carrera, Usuario
from extensions import db

cursos_bp = Blueprint('cursos', __name__, url_prefix='/api/cursos')

@cursos_bp.route('/', methods=['GET'])
def get_cursos():
    try:
        # Obtener parámetros de consulta
        id_carrera = request.args.get('id_carrera', type=int)
        estado = request.args.get('estado', 'A')
        
        query = Curso.query.filter_by(estado=estado)
        
        if id_carrera:
            query = query.filter_by(id_carrera=id_carrera)
        
        cursos = query.all()
        
        # Incluir información de carrera
        resultado = []
        for curso in cursos:
            curso_dict = curso.to_dict()
            carrera = Carrera.query.get(curso.id_carrera)
            curso_dict['carrera'] = carrera.to_dict() if carrera else None
            resultado.append(curso_dict)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener cursos: {str(e)}'}), 500

@cursos_bp.route('/<int:id_curso>', methods=['GET'])
def get_curso(id_curso):
    try:
        curso = Curso.query.get(id_curso)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404
        
        curso_dict = curso.to_dict()
        carrera = Carrera.query.get(curso.id_carrera)
        curso_dict['carrera'] = carrera.to_dict() if carrera else None
        
        return jsonify(curso_dict), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener curso: {str(e)}'}), 500

@cursos_bp.route('/', methods=['POST'])
def crear_curso():
    try:
        data = request.get_json()
        
        required_fields = ['codigo_curso', 'nombre_curso', 'id_carrera']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400
        
        # Verificar que el código no existe
        existing_curso = Curso.query.filter_by(codigo_curso=data['codigo_curso']).first()
        if existing_curso:
            return jsonify({'error': 'El código de curso ya existe'}), 400
        
        # Verificar que la carrera existe
        carrera = Carrera.query.get(data['id_carrera'])
        if not carrera:
            return jsonify({'error': 'Carrera no encontrada'}), 400
        
        nuevo_curso = Curso(
            codigo_curso=data['codigo_curso'],
            nombre_curso=data['nombre_curso'],
            descripcion=data.get('descripcion'),
            id_carrera=data['id_carrera'],
            creditos=data.get('creditos', 3)
        )
        
        db.session.add(nuevo_curso)
        db.session.commit()
        
        return jsonify({
            'message': 'Curso creado exitosamente',
            'curso': nuevo_curso.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear curso: {str(e)}'}), 500

@cursos_bp.route('/<int:id_curso>', methods=['PUT'])
def actualizar_curso(id_curso):
    try:
        curso = Curso.query.get(id_curso)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404
        
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'nombre_curso' in data:
            curso.nombre_curso = data['nombre_curso']
        if 'descripcion' in data:
            curso.descripcion = data['descripcion']
        if 'creditos' in data:
            curso.creditos = data['creditos']
        if 'estado' in data:
            curso.estado = data['estado']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Curso actualizado exitosamente',
            'curso': curso.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar curso: {str(e)}'}), 500