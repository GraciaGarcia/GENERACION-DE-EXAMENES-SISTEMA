# routes/reportes.py
from flask import Blueprint, request, jsonify
from models import (Examen, ExamenEstudiante, RespuestaEstudiante, Usuario, 
                   Curso, Pregunta, PreguntaExamen, Alternativa)
from extensions import db
from sqlalchemy import func, desc
from datetime import datetime, timedelta

reportes_bp = Blueprint('reportes', __name__, url_prefix='/api/reportes')

@reportes_bp.route('/examen/<int:id_examen>/resultados', methods=['GET'])
def get_resultados_examen(id_examen):
    """Obtener todos los resultados de un examen específico"""
    try:
        examen = Examen.query.get(id_examen)
        if not examen:
            return jsonify({'error': 'Examen no encontrado'}), 404
        
        # Obtener todos los intentos del examen
        resultados = db.session.query(ExamenEstudiante, Usuario)\
            .join(Usuario, ExamenEstudiante.id_estudiante == Usuario.id_usuario)\
            .filter(ExamenEstudiante.id_examen == id_examen)\
            .filter(ExamenEstudiante.estado == 'FINALIZADO')\
            .order_by(desc(ExamenEstudiante.nota_obtenida))\
            .all()
        
        # Calcular estadísticas
        notas = [float(r[0].nota_obtenida) for r in resultados if r[0].nota_obtenida]
        estadisticas = {}
        
        if notas:
            estadisticas = {
                'total_estudiantes': len(notas),
                'promedio': round(sum(notas) / len(notas), 2),
                'nota_maxima': max(notas),
                'nota_minima': min(notas),
                'aprobados': len([n for n in notas if n >= float(examen.nota_minima)]),
                'desaprobados': len([n for n in notas if n < float(examen.nota_minima)])
            }
        
        # Formatear resultados
        resultados_formateados = []
        for exam_est, usuario in resultados:
            resultado = {
                'examen_estudiante': exam_est.to_dict(),
                'estudiante': {
                    'id_usuario': usuario.id_usuario,
                    'nombres': usuario.nombres,
                    'apellidos': usuario.apellidos,
                    'email': usuario.email
                }
            }
            resultados_formateados.append(resultado)
        
        return jsonify({
            'examen': examen.to_dict(),
            'estadisticas': estadisticas,
            'resultados': resultados_formateados
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener resultados: {str(e)}'}), 500

@reportes_bp.route('/estudiante/<int:id_estudiante>/historial', methods=['GET'])
def get_historial_estudiante(id_estudiante):
    """Obtener historial de exámenes de un estudiante"""
    try:
        estudiante = Usuario.query.get(id_estudiante)
        if not estudiante or estudiante.tipo_usuario != 'ESTUDIANTE':
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Obtener todos los exámenes realizados
        historial = db.session.query(ExamenEstudiante, Examen, Curso)\
            .join(Examen, ExamenEstudiante.id_examen == Examen.id_examen)\
            .join(Curso, Examen.id_curso == Curso.id_curso)\
            .filter(ExamenEstudiante.id_estudiante == id_estudiante)\
            .order_by(desc(ExamenEstudiante.fecha_inicio))\
            .all()
        
        # Formatear historial
        historial_formateado = []
        for exam_est, examen, curso in historial:
            registro = {
                'examen_estudiante': exam_est.to_dict(),
                'examen': {
                    'id_examen': examen.id_examen,
                    'titulo': examen.titulo,
                    'nota_minima': float(examen.nota_minima)
                },
                'curso': {
                    'id_curso': curso.id_curso,
                    'codigo_curso': curso.codigo_curso,
                    'nombre_curso': curso.nombre_curso
                }
            }
            historial_formateado.append(registro)
        
        # Calcular estadísticas del estudiante
        examenes_finalizados = [h for h in historial if h[0].estado == 'FINALIZADO']
        estadisticas = {}
        
        if examenes_finalizados:
            notas = [float(h[0].nota_obtenida) for h in examenes_finalizados if h[0].nota_obtenida]
            if notas:
                estadisticas = {
                    'total_examenes': len(notas),
                    'promedio_general': round(sum(notas) / len(notas), 2),
                    'mejor_nota': max(notas),
                    'peor_nota': min(notas)
                }
        
        return jsonify({
            'estudiante': {
                'id_usuario': estudiante.id_usuario,
                'nombres': estudiante.nombres,
                'apellidos': estudiante.apellidos
            },
            'estadisticas': estadisticas,
            'historial': historial_formateado
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener historial: {str(e)}'}), 500

@reportes_bp.route('/examen/<int:id_examen_estudiante>/detalle', methods=['GET'])
def get_detalle_examen_estudiante(id_examen_estudiante):
    """Obtener detalle completo de un examen realizado por un estudiante"""
    try:
        examen_estudiante = ExamenEstudiante.query.get(id_examen_estudiante)
        if not examen_estudiante:
            return jsonify({'error': 'Examen de estudiante no encontrado'}), 404
        
        # Verificar permisos (solo el estudiante o profesores pueden ver)
        usuario_id = request.args.get('usuario_id', type=int)
        if usuario_id:
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                return jsonify({'error': 'Usuario no encontrado'}), 404
            
            # Solo el mismo estudiante o un profesor pueden ver los detalles
            if (usuario.id_usuario != examen_estudiante.id_estudiante and 
                usuario.tipo_usuario != 'PROFESOR'):
                return jsonify({'error': 'No tienes permisos para ver este examen'}), 403
        
        # Obtener respuestas detalladas
        respuestas = db.session.query(RespuestaEstudiante, Pregunta, PreguntaExamen)\
            .join(Pregunta, RespuestaEstudiante.id_pregunta == Pregunta.id_pregunta)\
            .join(PreguntaExamen, 
                  (PreguntaExamen.id_pregunta == Pregunta.id_pregunta) & 
                  (PreguntaExamen.id_examen == examen_estudiante.id_examen))\
            .filter(RespuestaEstudiante.id_examen_estudiante == id_examen_estudiante)\
            .order_by(PreguntaExamen.orden_pregunta)\
            .all()
        
        # Formatear respuestas detalladas
        respuestas_detalle = []
        for respuesta, pregunta, pregunta_examen in respuestas:
            # Obtener alternativas de la pregunta
            alternativas = Alternativa.query.filter_by(
                id_pregunta=pregunta.id_pregunta
            ).order_by(Alternativa.orden_alternativa).all()
            
            # Obtener alternativa seleccionada
            alternativa_seleccionada = None
            if respuesta.id_alternativa:
                alternativa_seleccionada = Alternativa.query.get(respuesta.id_alternativa)
            
            # Obtener alternativa correcta
            alternativa_correcta = None
            for alt in alternativas:
                if alt.es_correcta == 'S':
                    alternativa_correcta = alt
                    break
            
            detalle = {
                'pregunta': {
                    'id_pregunta': pregunta.id_pregunta,
                    'enunciado': pregunta.enunciado,
                    'explicacion': pregunta.explicacion,
                    'tipo_pregunta': pregunta.tipo_pregunta.tipo_nombre,
                    'alternativas': [alt.to_dict() for alt in alternativas]
                },
                'respuesta': {
                    'respuesta_texto': respuesta.respuesta_texto,
                    'alternativa_seleccionada': alternativa_seleccionada.to_dict() if alternativa_seleccionada else None,
                    'alternativa_correcta': alternativa_correcta.to_dict() if alternativa_correcta else None,
                    'es_correcta': respuesta.es_correcta,
                    'puntos_obtenidos': float(respuesta.puntos_obtenidos or 0),
                    'puntos_asignados': float(pregunta_examen.puntos_asignados),
                    'fecha_respuesta': respuesta.fecha_respuesta.isoformat() if respuesta.fecha_respuesta else None
                }
            }
            respuestas_detalle.append(detalle)
        
        return jsonify({
            'examen_estudiante': examen_estudiante.to_dict(),
            'examen': examen_estudiante.examen.to_dict(),
            'respuestas_detalle': respuestas_detalle
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener detalle: {str(e)}'}), 500

@reportes_bp.route('/profesor/<int:id_profesor>/estadisticas', methods=['GET'])
def get_estadisticas_profesor(id_profesor):
    """Obtener estadísticas generales de un profesor"""
    try:
        profesor = Usuario.query.get(id_profesor)
        if not profesor or profesor.tipo_usuario != 'PROFESOR':
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        # Contar exámenes creados
        total_examenes = Examen.query.filter_by(id_profesor=id_profesor).count()
        
        # Contar preguntas creadas
        total_preguntas = Pregunta.query.filter_by(id_profesor=id_profesor).count()
        
        # Obtener exámenes activos
        examenes_activos = Examen.query.filter_by(
            id_profesor=id_profesor, 
            estado='ACTIVO'
        ).count()
        
        # Obtener estudiantes que han tomado exámenes
        estudiantes_examenes = db.session.query(func.count(func.distinct(ExamenEstudiante.id_estudiante)))\
            .join(Examen, ExamenEstudiante.id_examen == Examen.id_examen)\
            .filter(Examen.id_profesor == id_profesor)\
            .scalar()
        
        # Obtener cursos donde tiene preguntas
        cursos_con_preguntas = db.session.query(func.count(func.distinct(Pregunta.id_curso)))\
            .filter(Pregunta.id_profesor == id_profesor)\
            .scalar()
        
        return jsonify({
            'profesor': {
                'id_usuario': profesor.id_usuario,
                'nombres': profesor.nombres,
                'apellidos': profesor.apellidos
            },
            'estadisticas': {
                'total_examenes': total_examenes,
                'examenes_activos': examenes_activos,
                'total_preguntas': total_preguntas,
                'estudiantes_evaluados': estudiantes_examenes,
                'cursos_con_preguntas': cursos_con_preguntas
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener estadísticas: {str(e)}'}), 500

@reportes_bp.route('/curso/<int:id_curso>/rendimiento', methods=['GET'])
def get_rendimiento_curso(id_curso):
    """Obtener estadísticas de rendimiento por curso"""
    try:
        curso = Curso.query.get(id_curso)
        if not curso:
            return jsonify({'error': 'Curso no encontrado'}), 404
        
        # Obtener todos los exámenes del curso
        examenes = Examen.query.filter_by(id_curso=id_curso).all()
        
        # Estadísticas por examen
        estadisticas_examenes = []
        for examen in examenes:
            resultados = ExamenEstudiante.query.filter_by(
                id_examen=examen.id_examen,
                estado='FINALIZADO'
            ).all()
            
            if resultados:
                notas = [float(r.nota_obtenida) for r in resultados if r.nota_obtenida]
                if notas:
                    estadistica = {
                        'examen': {
                            'id_examen': examen.id_examen,
                            'titulo': examen.titulo,
                            'fecha_creacion': examen.fecha_creacion.isoformat()
                        },
                        'total_estudiantes': len(notas),
                        'promedio': round(sum(notas) / len(notas), 2),
                        'nota_maxima': max(notas),
                        'nota_minima': min(notas),
                        'aprobados': len([n for n in notas if n >= float(examen.nota_minima)])
                    }
                    estadisticas_examenes.append(estadistica)
        
        # Total de preguntas en el curso
        total_preguntas = Pregunta.query.filter_by(id_curso=id_curso).count()
        
        return jsonify({
            'curso': curso.to_dict(),
            'total_examenes': len(examenes),
            'total_preguntas': total_preguntas,
            'estadisticas_examenes': estadisticas_examenes
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener rendimiento: {str(e)}'}), 500