# routes/realizar_examen.py
from flask import Blueprint, request, jsonify
from models import (Examen, ExamenEstudiante, PreguntaExamen, Pregunta, 
                   RespuestaEstudiante, Alternativa, Usuario)
from extensions import db
from datetime import datetime, timedelta
import random

realizar_examen_bp = Blueprint('realizar_examen', __name__, url_prefix='/api/realizar-examen')

@realizar_examen_bp.route('/<int:id_examen>/iniciar', methods=['POST'])
def iniciar_examen(id_examen):
    try:
        data = request.get_json()
        id_estudiante = data.get('id_estudiante')
        
        if not id_estudiante:
            return jsonify({'error': 'ID de estudiante es requerido'}), 400
        
        # Verificar examen
        examen = Examen.query.get(id_examen)
        if not examen:
            return jsonify({'error': 'Examen no encontrado'}), 404
        
        if examen.estado != 'ACTIVO':
            return jsonify({'error': 'El examen no está activo'}), 400
        
        # Verificar fechas
        now = datetime.utcnow()
        if examen.fecha_inicio and now < examen.fecha_inicio:
            return jsonify({'error': 'El examen aún no ha comenzado'}), 400
        
        if examen.fecha_fin and now > examen.fecha_fin:
            return jsonify({'error': 'El examen ya ha finalizado'}), 400
        
        # Verificar intentos
        intentos_realizados = ExamenEstudiante.query.filter_by(
            id_examen=id_examen,
            id_estudiante=id_estudiante
        ).count()
        
        if intentos_realizados >= examen.intentos_permitidos:
            return jsonify({'error': 'Ya has agotado todos los intentos'}), 400
        
        # Verificar que no tenga un examen en progreso
        examen_en_progreso = ExamenEstudiante.query.filter_by(
            id_examen=id_examen,
            id_estudiante=id_estudiante,
            estado='EN_PROGRESO'
        ).first()
        
        if examen_en_progreso:
            return jsonify({'error': 'Ya tienes un examen en progreso'}), 400
        
        # Crear nuevo intento
        nuevo_intento = ExamenEstudiante(
            id_examen=id_examen,
            id_estudiante=id_estudiante,
            intento_numero=intentos_realizados + 1,
            fecha_inicio=now
        )
        
        db.session.add(nuevo_intento)
        db.session.flush()
        
        # Obtener preguntas del examen
        preguntas_query = db.session.query(PreguntaExamen, Pregunta)\
            .join(Pregunta, PreguntaExamen.id_pregunta == Pregunta.id_pregunta)\
            .filter(PreguntaExamen.id_examen == id_examen)\
            .order_by(PreguntaExamen.orden_pregunta)
        
        preguntas = preguntas_query.all()
        
        # Aleatorizar si está configurado
        if examen.aleatorizar_preguntas == 'S':
            preguntas = random.sample(preguntas, len(preguntas))
        
        # Crear respuestas vacías para cada pregunta
        for pe, p in preguntas:
            respuesta = RespuestaEstudiante(
                id_examen_estudiante=nuevo_intento.id_examen_estudiante,
                id_pregunta=p.id_pregunta
            )
            db.session.add(respuesta)
        
        db.session.commit()
        
        # Preparar respuesta con preguntas
        preguntas_response = []
        for pe, p in preguntas:
            pregunta_dict = p.to_dict()
            pregunta_dict['puntos_asignados'] = float(pe.puntos_asignados)
            
            # Para preguntas de opción múltiple, aleatorizar alternativas
            if p.tipo_pregunta.tipo_nombre in ['MULTIPLE', 'SIMPLE']:
                alternativas = list(pregunta_dict['alternativas'])
                random.shuffle(alternativas)
                pregunta_dict['alternativas'] = alternativas
            
            preguntas_response.append(pregunta_dict)
        
        return jsonify({
            'message': 'Examen iniciado exitosamente',
            'examen_estudiante': nuevo_intento.to_dict(),
            'examen': examen.to_dict(),
            'preguntas': preguntas_response,
            'tiempo_limite': examen.duracion_minutos * 60  # en segundos
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al iniciar examen: {str(e)}'}), 500

@realizar_examen_bp.route('/estudiante/<int:id_examen_estudiante>/responder', methods=['POST'])
def guardar_respuesta(id_examen_estudiante):
    try:
        data = request.get_json()
        id_pregunta = data.get('id_pregunta')
        id_alternativa = data.get('id_alternativa')
        respuesta_texto = data.get('respuesta_texto')
        
        if not id_pregunta:
            return jsonify({'error': 'ID de pregunta es requerido'}), 400
        
        # Verificar que el examen estudiante existe y está en progreso
        examen_estudiante = ExamenEstudiante.query.get(id_examen_estudiante)
        if not examen_estudiante:
            return jsonify({'error': 'Examen de estudiante no encontrado'}), 404
        
        if examen_estudiante.estado != 'EN_PROGRESO':
            return jsonify({'error': 'El examen no está en progreso'}), 400
        
        # Verificar tiempo límite
        tiempo_transcurrido = (datetime.utcnow() - examen_estudiante.fecha_inicio).total_seconds()
        tiempo_limite = examen_estudiante.examen.duracion_minutos * 60
        
        if tiempo_transcurrido > tiempo_limite:
            # Auto-finalizar examen por tiempo
            examen_estudiante.estado = 'FINALIZADO'
            examen_estudiante.fecha_fin = datetime.utcnow()
            examen_estudiante.tiempo_transcurrido = int(tiempo_transcurrido)
            db.session.commit()
            return jsonify({'error': 'Tiempo agotado', 'auto_finalizado': True}), 400
        
        # Buscar la respuesta existente
        respuesta = RespuestaEstudiante.query.filter_by(
            id_examen_estudiante=id_examen_estudiante,
            id_pregunta=id_pregunta
        ).first()
        
        if not respuesta:
            return jsonify({'error': 'Respuesta no encontrada'}), 404
        
        # Actualizar respuesta
        respuesta.id_alternativa = id_alternativa
        respuesta.respuesta_texto = respuesta_texto
        respuesta.fecha_respuesta = datetime.utcnow()
        
        # Evaluar si es correcta
        pregunta = Pregunta.query.get(id_pregunta)
        if pregunta.tipo_pregunta.tipo_nombre in ['MULTIPLE', 'SIMPLE']:
            if id_alternativa:
                alternativa = Alternativa.query.get(id_alternativa)
                if alternativa and alternativa.es_correcta == 'S':
                    respuesta.es_correcta = 'S'
                    # Obtener puntos de la pregunta en el examen
                    pregunta_examen = PreguntaExamen.query.filter_by(
                        id_examen=examen_estudiante.id_examen,
                        id_pregunta=id_pregunta
                    ).first()
                    respuesta.puntos_obtenidos = pregunta_examen.puntos_asignados if pregunta_examen else 0
                else:
                    respuesta.es_correcta = 'N'
                    respuesta.puntos_obtenidos = 0
        elif pregunta.tipo_pregunta.tipo_nombre == 'VERDADERO_FALSO':
            # Obtener la alternativa correcta
            alternativa_correcta = Alternativa.query.filter_by(
                id_pregunta=id_pregunta,
                es_correcta='S'
            ).first()
            
            if alternativa_correcta and respuesta_texto == alternativa_correcta.texto_alternativa:
                respuesta.es_correcta = 'S'
                pregunta_examen = PreguntaExamen.query.filter_by(
                    id_examen=examen_estudiante.id_examen,
                    id_pregunta=id_pregunta
                ).first()
                respuesta.puntos_obtenidos = pregunta_examen.puntos_asignados if pregunta_examen else 0
            else:
                respuesta.es_correcta = 'N'
                respuesta.puntos_obtenidos = 0
        
        db.session.commit()
        
        return jsonify({
            'message': 'Respuesta guardada exitosamente',
            'respuesta': respuesta.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al guardar respuesta: {str(e)}'}), 500

@realizar_examen_bp.route('/estudiante/<int:id_examen_estudiante>/finalizar', methods=['POST'])
def finalizar_examen(id_examen_estudiante):
    try:
        examen_estudiante = ExamenEstudiante.query.get(id_examen_estudiante)
        if not examen_estudiante:
            return jsonify({'error': 'Examen de estudiante no encontrado'}), 404
        
        if examen_estudiante.estado != 'EN_PROGRESO':
            return jsonify({'error': 'El examen no está en progreso'}), 400
        
        # Calcular tiempo transcurrido
        tiempo_transcurrido = (datetime.utcnow() - examen_estudiante.fecha_inicio).total_seconds()
        
        # Calcular nota final
        respuestas = RespuestaEstudiante.query.filter_by(
            id_examen_estudiante=id_examen_estudiante
        ).all()
        
        puntos_obtenidos = sum(float(r.puntos_obtenidos or 0) for r in respuestas)
        puntos_totales = sum(
            float(pe.puntos_asignados) for pe in 
            PreguntaExamen.query.filter_by(id_examen=examen_estudiante.id_examen).all()
        )
        
        # Calcular nota sobre 20
        if puntos_totales > 0:
            nota_obtenida = (puntos_obtenidos / puntos_totales) * 20
        else:
            nota_obtenida = 0
        
        # Actualizar examen estudiante
        examen_estudiante.fecha_fin = datetime.utcnow()
        examen_estudiante.tiempo_transcurrido = int(tiempo_transcurrido)
        examen_estudiante.nota_obtenida = round(nota_obtenida, 2)
        examen_estudiante.estado = 'FINALIZADO'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Examen finalizado exitosamente',
            'examen_estudiante': examen_estudiante.to_dict(),
            'puntos_obtenidos': puntos_obtenidos,
            'puntos_totales': puntos_totales,
            'nota_final': round(nota_obtenida, 2)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al finalizar examen: {str(e)}'}), 500

@realizar_examen_bp.route('/estudiante/<int:id_examen_estudiante>/estado', methods=['GET'])
def get_estado_examen(id_examen_estudiante):
    try:
        examen_estudiante = ExamenEstudiante.query.get(id_examen_estudiante)
        if not examen_estudiante:
            return jsonify({'error': 'Examen de estudiante no encontrado'}), 404
        
        # Calcular tiempo restante
        tiempo_transcurrido = (datetime.utcnow() - examen_estudiante.fecha_inicio).total_seconds()
        tiempo_limite = examen_estudiante.examen.duracion_minutos * 60
        tiempo_restante = max(0, tiempo_limite - tiempo_transcurrido)
        
        # Obtener respuestas actuales
        respuestas = RespuestaEstudiante.query.filter_by(
            id_examen_estudiante=id_examen_estudiante
        ).all()
        
        respuestas_dict = {}
        for respuesta in respuestas:
            respuestas_dict[respuesta.id_pregunta] = {
                'id_alternativa': respuesta.id_alternativa,
                'respuesta_texto': respuesta.respuesta_texto,
                'fecha_respuesta': respuesta.fecha_respuesta.isoformat() if respuesta.fecha_respuesta else None
            }
        
        return jsonify({
            'examen_estudiante': examen_estudiante.to_dict(),
            'tiempo_restante': int(tiempo_restante),
            'respuestas': respuestas_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener estado: {str(e)}'}), 500