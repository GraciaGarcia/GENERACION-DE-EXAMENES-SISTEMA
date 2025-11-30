# routes/preguntas.py
from flask import Blueprint, request, jsonify
from models import Pregunta, Alternativa, TipoPregunta, Curso, Usuario
from extensions import db
from datetime import datetime

preguntas_bp = Blueprint('preguntas', __name__, url_prefix='/api/preguntas')

@preguntas_bp.route('/', methods=['GET'])
def get_preguntas():
    try:
        # Parámetros de filtro
        id_curso = request.args.get('id_curso', type=int)
        id_profesor = request.args.get('id_profesor', type=int)
        dificultad = request.args.get('dificultad')
        id_tipo = request.args.get('id_tipo', type=int)
        estado = request.args.get('estado', 'A')
        
        query = Pregunta.query.filter_by(estado=estado)
        
        if id_curso:
            query = query.filter_by(id_curso=id_curso)
        if id_profesor:
            query = query.filter_by(id_profesor=id_profesor)
        if dificultad:
            query = query.filter_by(dificultad=dificultad)
        if id_tipo:
            query = query.filter_by(id_tipo_pregunta=id_tipo)
        
        preguntas = query.all()
        
        # Incluir información adicional
        resultado = []
        for pregunta in preguntas:
            pregunta_dict = pregunta.to_dict()
            
            # Agregar información del curso
            curso = Curso.query.get(pregunta.id_curso)
            pregunta_dict['curso'] = curso.to_dict() if curso else None
            
            # Agregar información del tipo
            tipo = TipoPregunta.query.get(pregunta.id_tipo_pregunta)
            pregunta_dict['tipo_pregunta'] = tipo.to_dict() if tipo else None
            
            # Agregar información del profesor
            profesor = Usuario.query.get(pregunta.id_profesor)
            if profesor:
                pregunta_dict['profesor'] = {
                    'nombres': profesor.nombres,
                    'apellidos': profesor.apellidos
                }
            
            resultado.append(pregunta_dict)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener preguntas: {str(e)}'}), 500

@preguntas_bp.route('/<int:id_pregunta>', methods=['GET'])
def get_pregunta(id_pregunta):
    try:
        pregunta = Pregunta.query.get(id_pregunta)
        if not pregunta:
            return jsonify({'error': 'Pregunta no encontrada'}), 404
        
        pregunta_dict = pregunta.to_dict()
        
        # Agregar información adicional
        curso = Curso.query.get(pregunta.id_curso)
        pregunta_dict['curso'] = curso.to_dict() if curso else None
        
        tipo = TipoPregunta.query.get(pregunta.id_tipo_pregunta)
        pregunta_dict['tipo_pregunta'] = tipo.to_dict() if tipo else None
        
        return jsonify(pregunta_dict), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener pregunta: {str(e)}'}), 500

@preguntas_bp.route('/', methods=['POST'])
def crear_pregunta():
    try:
        data = request.get_json()
        
        required_fields = ['enunciado', 'id_tipo_pregunta', 'id_curso', 'id_profesor', 'alternativas']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400
        
        # Validar que existan las referencias
        tipo = TipoPregunta.query.get(data['id_tipo_pregunta'])
        if not tipo:
            return jsonify({'error': 'Tipo de pregunta no encontrado'}), 400
        
        curso = Curso.query.get(data['id_curso'])
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 400
        
        profesor = Usuario.query.get(data['id_profesor'])
        if not profesor or profesor.tipo_usuario != 'PROFESOR':
            return jsonify({'error': 'Profesor no válido'}), 400
        
        # Validar alternativas
        alternativas_data = data['alternativas']
        if not alternativas_data or len(alternativas_data) < 2:
            return jsonify({'error': 'Se requieren al menos 2 alternativas'}), 400
        
        # Verificar que haya al menos una alternativa correcta
        tiene_correcta = any(alt.get('es_correcta') == 'S' for alt in alternativas_data)
        if not tiene_correcta:
            return jsonify({'error': 'Debe haber al menos una alternativa correcta'}), 400
        
        # Crear la pregunta
        nueva_pregunta = Pregunta(
            enunciado=data['enunciado'],
            explicacion=data.get('explicacion'),
            id_tipo_pregunta=data['id_tipo_pregunta'],
            id_curso=data['id_curso'],
            id_profesor=data['id_profesor'],
            dificultad=data.get('dificultad', 'MEDIO'),
            puntos=data.get('puntos', 1.0)
        )
        
        db.session.add(nueva_pregunta)
        db.session.flush()  # Para obtener el ID
        
        # Crear las alternativas
        for i, alt_data in enumerate(alternativas_data, 1):
            alternativa = Alternativa(
                id_pregunta=nueva_pregunta.id_pregunta,
                texto_alternativa=alt_data['texto_alternativa'],
                es_correcta=alt_data.get('es_correcta', 'N'),
                orden_alternativa=i
            )
            db.session.add(alternativa)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Pregunta creada exitosamente',
            'pregunta': nueva_pregunta.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear pregunta: {str(e)}'}), 500

@preguntas_bp.route('/<int:id_pregunta>', methods=['PUT'])
def actualizar_pregunta(id_pregunta):
    try:
        pregunta = Pregunta.query.get(id_pregunta)
        if not pregunta:
            return jsonify({'error': 'Pregunta no encontrada'}), 404
        
        data = request.get_json()
        
        # Actualizar campos de la pregunta
        if 'enunciado' in data:
            pregunta.enunciado = data['enunciado']
        if 'explicacion' in data:
            pregunta.explicacion = data['explicacion']
        if 'dificultad' in data:
            pregunta.dificultad = data['dificultad']
        if 'puntos' in data:
            pregunta.puntos = data['puntos']
        
        pregunta.fecha_modificacion = datetime.utcnow()
        
        # Si se envían alternativas, actualizarlas
        if 'alternativas' in data:
            # Eliminar alternativas existentes
            Alternativa.query.filter_by(id_pregunta=id_pregunta).delete()
            
            # Crear nuevas alternativas
            for i, alt_data in enumerate(data['alternativas'], 1):
                alternativa = Alternativa(
                    id_pregunta=id_pregunta,
                    texto_alternativa=alt_data['texto_alternativa'],
                    es_correcta=alt_data.get('es_correcta', 'N'),
                    orden_alternativa=i
                )
                db.session.add(alternativa)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Pregunta actualizada exitosamente',
            'pregunta': pregunta.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar pregunta: {str(e)}'}), 500

@preguntas_bp.route('/<int:id_pregunta>', methods=['DELETE'])
def eliminar_pregunta(id_pregunta):
    try:
        pregunta = Pregunta.query.get(id_pregunta)
        if not pregunta:
            return jsonify({'error': 'Pregunta no encontrada'}), 404
        
        # Soft delete
        pregunta.estado = 'I'
        db.session.commit()
        
        return jsonify({'message': 'Pregunta eliminada exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar pregunta: {str(e)}'}), 500

@preguntas_bp.route('/tipos', methods=['GET'])
def get_tipos_pregunta():
    try:
        tipos = TipoPregunta.query.all()
        return jsonify([tipo.to_dict() for tipo in tipos]), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener tipos de pregunta: {str(e)}'}), 500