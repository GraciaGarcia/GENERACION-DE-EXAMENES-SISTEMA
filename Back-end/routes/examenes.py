# routes/examenes.py
from flask import Blueprint, request, jsonify
from models import (Examen, PreguntaExamen, Pregunta, Curso, Usuario, 
                   ExamenEstudiante, RespuestaEstudiante, Alternativa)
from extensions import db
from datetime import datetime
import random

examenes_bp = Blueprint('examenes', __name__, url_prefix='/api/examenes')

# Ruta para obtener lista de exámenes con filtros opcionales
@examenes_bp.route('/', methods=['GET'])
def get_examenes():
    try:
        id_curso = request.args.get('id_curso', type=int)
        id_profesor = request.args.get('id_profesor', type=int)
        estado = request.args.get('estado')
        
        query = Examen.query
        
        if id_curso:
            query = query.filter_by(id_curso=id_curso)
        if id_profesor:
            query = query.filter_by(id_profesor=id_profesor)
        if estado:
            query = query.filter_by(estado=estado)
        
        examenes = query.all()
        
        resultado = []
        for examen in examenes:
            examen_dict = examen.to_dict()
            
            # Agregar información del curso
            curso = Curso.query.get(examen.id_curso)
            examen_dict['curso'] = curso.to_dict() if curso else None
            
            # Agregar número de preguntas
            total_preguntas = PreguntaExamen.query.filter_by(id_examen=examen.id_examen).count()
            examen_dict['total_preguntas'] = total_preguntas
            
            resultado.append(examen_dict)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener exámenes: {str(e)}'}), 500


# Ruta para obtener un examen específico por ID
@examenes_bp.route('/<int:id_examen>', methods=['GET'])
def get_examen(id_examen):
    try:
        examen = Examen.query.get(id_examen)
        if not examen:
            return jsonify({'error': 'Examen no encontrado'}), 404
        
        examen_dict = examen.to_dict()
        
        # Agregar información del curso
        curso = Curso.query.get(examen.id_curso)
        examen_dict['curso'] = curso.to_dict() if curso else None
        
        # Agregar preguntas del examen
        preguntas_examen = db.session.query(PreguntaExamen, Pregunta)\
            .join(Pregunta, PreguntaExamen.id_pregunta == Pregunta.id_pregunta)\
            .filter(PreguntaExamen.id_examen == id_examen)\
            .order_by(PreguntaExamen.orden_pregunta)\
            .all()
        
        preguntas = []
        for pe, p in preguntas_examen:
            pregunta_dict = p.to_dict()
            pregunta_dict['puntos_asignados'] = float(pe.puntos_asignados)
            pregunta_dict['orden_pregunta'] = pe.orden_pregunta
            preguntas.append(pregunta_dict)
        
        examen_dict['preguntas'] = preguntas
        
        return jsonify(examen_dict), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener examen: {str(e)}'}), 500
    
@examenes_bp.route('/', methods=['POST'])
def crear_examen():
    try:
        data = request.get_json()
        
        required_fields = ['titulo', 'id_curso', 'id_profesor'] 
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400
        
        # Validar referencias
        curso = Curso.query.get(data['id_curso'])
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 400
        
        profesor = Usuario.query.get(data['id_profesor'])
        if not profesor or profesor.tipo_usuario != 'PROFESOR':
            return jsonify({'error': 'Profesor no válido'}), 400
        
        nuevo_examen = Examen(
            titulo=data['titulo'],
            descripcion=data.get('descripcion'),
            id_curso=data['id_curso'],
            id_profesor=data['id_profesor'],
            fecha_inicio=datetime.fromisoformat(data['fecha_inicio']) if data.get('fecha_inicio') else None,
            fecha_fin=datetime.fromisoformat(data['fecha_fin']) if data.get('fecha_fin') else None,
            duracion_minutos=data.get('duracion_minutos', 60),
            intentos_permitidos=data.get('intentos_permitidos', 1),
            nota_minima=data.get('nota_minima', 10.50),
            mostrar_resultados=data.get('mostrar_resultados', 'S'),
            aleatorizar_preguntas=data.get('aleatorizar_preguntas', 'N')
        )
        
        db.session.add(nuevo_examen)
        db.session.commit()
        
        return jsonify({
            'message': 'Examen creado exitosamente',
            'examen': nuevo_examen.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear examen: {str(e)}'}), 500

@examenes_bp.route('/<int:id_examen>/preguntas', methods=['POST'])
def agregar_pregunta_examen(id_examen):
    try:
        examen = Examen.query.get(id_examen)
        if not examen:
            return jsonify({'error': 'Examen no encontrado'}), 404
        
        data = request.get_json()
        id_pregunta = data.get('id_pregunta')
        puntos_asignados = data.get('puntos_asignados', 1.0)
        
        if not id_pregunta:
            return jsonify({'error': 'ID de pregunta es requerido'}), 400
        
        # Verificar que la pregunta existe
        pregunta = Pregunta.query.get(id_pregunta)
        if not pregunta:
            return jsonify({'error': 'Pregunta no encontrada'}), 404
        
        # Verificar que la pregunta no esté ya en el examen
        existing = PreguntaExamen.query.filter_by(
            id_examen=id_examen, 
            id_pregunta=id_pregunta
        ).first()
        if existing:
            return jsonify({'error': 'La pregunta ya está en el examen'}), 400
        
        # Obtener el siguiente orden
        max_orden = db.session.query(db.func.max(PreguntaExamen.orden_pregunta))\
            .filter_by(id_examen=id_examen).scalar() or 0
        
        pregunta_examen = PreguntaExamen(
            id_examen=id_examen,
            id_pregunta=id_pregunta,
            orden_pregunta=max_orden + 1,
            puntos_asignados=puntos_asignados
        )
        
        db.session.add(pregunta_examen)
        db.session.commit()
        
        return jsonify({
            'message': 'Pregunta agregada al examen exitosamente',
            'pregunta_examen': pregunta_examen.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al agregar pregunta: {str(e)}'}), 500

@examenes_bp.route('/<int:id_examen>/preguntas/<int:id_pregunta>', methods=['DELETE'])
def remover_pregunta_examen(id_examen, id_pregunta):
    try:
        pregunta_examen = PreguntaExamen.query.filter_by(
            id_examen=id_examen, 
            id_pregunta=id_pregunta
        ).first()
        
        if not pregunta_examen:
            return jsonify({'error': 'Pregunta no encontrada en el examen'}), 404
        
        db.session.delete(pregunta_examen)
        db.session.commit()
        
        return jsonify({'message': 'Pregunta removida del examen'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al remover pregunta: {str(e)}'}), 500

@examenes_bp.route('/<int:id_examen>/estado', methods=['PUT'])
def cambiar_estado_examen(id_examen):
    try:
        examen = Examen.query.get(id_examen)
        if not examen:
            return jsonify({'error': 'Examen no encontrado'}), 404
        
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['BORRADOR', 'ACTIVO', 'FINALIZADO', 'CANCELADO']:
            return jsonify({'error': 'Estado inválido'}), 400
        
        examen.estado = nuevo_estado
        db.session.commit()
        
        return jsonify({
            'message': 'Estado del examen actualizado',
            'examen': examen.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al cambiar estado: {str(e)}'}), 500

@examenes_bp.route('/disponibles/<int:id_estudiante>', methods=['GET'])
def get_examenes_disponibles(id_estudiante):
    try:
        # Obtener carrera del estudiante
        estudiante = Usuario.query.get(id_estudiante)
        if not estudiante or estudiante.tipo_usuario != 'ESTUDIANTE':
            return jsonify({'error': 'Estudiante no válido'}), 400
        
        # Obtener exámenes activos de la carrera del estudiante
        examenes = db.session.query(Examen)\
            .join(Curso, Examen.id_curso == Curso.id_curso)\
            .filter(Curso.id_carrera == estudiante.id_carrera)\
            .filter(Examen.estado == 'ACTIVO')\
            .filter(Examen.fecha_inicio <= datetime.utcnow())\
            .filter(Examen.fecha_fin >= datetime.utcnow())\
            .all()
        
        resultado = []
        for examen in examenes:
            examen_dict = examen.to_dict()
            
            # Agregar información del curso
            curso = Curso.query.get(examen.id_curso)
            examen_dict['curso'] = curso.to_dict() if curso else None
            
            # Verificar intentos realizados
            intentos = ExamenEstudiante.query.filter_by(
                id_examen=examen.id_examen,
                id_estudiante=id_estudiante
            ).count()
            
            examen_dict['intentos_realizados'] = intentos
            examen_dict['puede_realizar'] = intentos < examen.intentos_permitidos
            
            resultado.append(examen_dict)
        
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener exámenes disponibles: {str(e)}'}), 500