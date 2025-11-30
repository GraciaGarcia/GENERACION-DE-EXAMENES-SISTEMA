# models.py
from extensions import db
from sqlalchemy import text
from datetime import datetime

class Carrera(db.Model):
    __tablename__ = 'carreras'
    
    id_carrera = db.Column(db.Integer, primary_key=True)
    nombre_carrera = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(500))
    estado = db.Column(db.String(1), default='A')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuarios = db.relationship('Usuario', backref='carrera', lazy=True)
    cursos = db.relationship('Curso', backref='carrera', lazy=True)
    
    def to_dict(self):
        return {
            'id_carrera': self.id_carrera,
            'nombre_carrera': self.nombre_carrera,
            'descripcion': self.descripcion,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

class TipoPregunta(db.Model):
    __tablename__ = 'tipos_pregunta'
    
    id_tipo = db.Column(db.Integer, primary_key=True)
    tipo_nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    
    # Relaciones
    preguntas = db.relationship('Pregunta', backref='tipo_pregunta', lazy=True)
    
    def to_dict(self):
        return {
            'id_tipo': self.id_tipo,
            'tipo_nombre': self.tipo_nombre,
            'descripcion': self.descripcion
        }

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    tipo_usuario = db.Column(db.String(20), nullable=False)  # PROFESOR o ESTUDIANTE
    id_carrera = db.Column(db.Integer, db.ForeignKey('carreras.id_carrera'), nullable=False)
    estado = db.Column(db.String(1), default='A')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_ultimo_acceso = db.Column(db.DateTime)
    
    # Relaciones
    preguntas_creadas = db.relationship('Pregunta', backref='profesor', lazy=True)
    examenes_creados = db.relationship('Examen', backref='profesor', lazy=True)
    examenes_estudiante = db.relationship('ExamenEstudiante', backref='estudiante', lazy=True)
    
    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'nombres': self.nombres,
            'apellidos': self.apellidos,
            'email': self.email,
            'tipo_usuario': self.tipo_usuario,
            'id_carrera': self.id_carrera,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_ultimo_acceso': self.fecha_ultimo_acceso.isoformat() if self.fecha_ultimo_acceso else None
        }

class Curso(db.Model):
    __tablename__ = 'cursos'
    
    id_curso = db.Column(db.Integer, primary_key=True)
    codigo_curso = db.Column(db.String(10), unique=True, nullable=False)
    nombre_curso = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(500))
    id_carrera = db.Column(db.Integer, db.ForeignKey('carreras.id_carrera'), nullable=False)
    creditos = db.Column(db.Integer, default=3)
    estado = db.Column(db.String(1), default='A')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    preguntas = db.relationship('Pregunta', backref='curso', lazy=True)
    examenes = db.relationship('Examen', backref='curso', lazy=True)
    
    def to_dict(self):
        return {
            'id_curso': self.id_curso,
            'codigo_curso': self.codigo_curso,
            'nombre_curso': self.nombre_curso,
            'descripcion': self.descripcion,
            'id_carrera': self.id_carrera,
            'creditos': self.creditos,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

class Pregunta(db.Model):
    __tablename__ = 'preguntas'
    
    id_pregunta = db.Column(db.Integer, primary_key=True)
    enunciado = db.Column(db.Text, nullable=False)
    explicacion = db.Column(db.Text)
    id_tipo_pregunta = db.Column(db.Integer, db.ForeignKey('tipos_pregunta.id_tipo'), nullable=False)
    id_curso = db.Column(db.Integer, db.ForeignKey('cursos.id_curso'), nullable=False)
    id_profesor = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    dificultad = db.Column(db.String(10), default='MEDIO')
    puntos = db.Column(db.Numeric(3,1), default=1.0)
    estado = db.Column(db.String(1), default='A')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime)
    
    # Relaciones
    alternativas = db.relationship('Alternativa', backref='pregunta', lazy=True, cascade='all, delete-orphan')
    preguntas_examen = db.relationship('PreguntaExamen', backref='pregunta', lazy=True)
    respuestas_estudiante = db.relationship('RespuestaEstudiante', backref='pregunta', lazy=True)
    
    def to_dict(self):
        return {
            'id_pregunta': self.id_pregunta,
            'enunciado': self.enunciado,
            'explicacion': self.explicacion,
            'id_tipo_pregunta': self.id_tipo_pregunta,
            'id_curso': self.id_curso,
            'id_profesor': self.id_profesor,
            'dificultad': self.dificultad,
            'puntos': float(self.puntos) if self.puntos else 0,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_modificacion': self.fecha_modificacion.isoformat() if self.fecha_modificacion else None,
            'alternativas': [alt.to_dict() for alt in self.alternativas] if self.alternativas else []
        }

class Alternativa(db.Model):
    __tablename__ = 'alternativas'
    
    id_alternativa = db.Column(db.Integer, primary_key=True)
    id_pregunta = db.Column(db.Integer, db.ForeignKey('preguntas.id_pregunta'), nullable=False)
    texto_alternativa = db.Column(db.Text, nullable=False)
    es_correcta = db.Column(db.String(1), default='N')
    orden_alternativa = db.Column(db.Integer, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    respuestas_estudiante = db.relationship('RespuestaEstudiante', backref='alternativa', lazy=True)
    
    def to_dict(self):
        return {
            'id_alternativa': self.id_alternativa,
            'id_pregunta': self.id_pregunta,
            'texto_alternativa': self.texto_alternativa,
            'es_correcta': self.es_correcta,
            'orden_alternativa': self.orden_alternativa,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

class Examen(db.Model):
    __tablename__ = 'examenes'
    
    id_examen = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    id_curso = db.Column(db.Integer, db.ForeignKey('cursos.id_curso'), nullable=False)
    id_profesor = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_inicio = db.Column(db.DateTime)
    fecha_fin = db.Column(db.DateTime)
    duracion_minutos = db.Column(db.Integer, default=60)
    intentos_permitidos = db.Column(db.Integer, default=1)
    nota_minima = db.Column(db.Numeric(4,2), default=10.50)
    estado = db.Column(db.String(20), default='BORRADOR')
    mostrar_resultados = db.Column(db.String(1), default='S')
    aleatorizar_preguntas = db.Column(db.String(1), default='N')
    
    # Relaciones
    preguntas_examen = db.relationship('PreguntaExamen', backref='examen', lazy=True, cascade='all, delete-orphan')
    examenes_estudiante = db.relationship('ExamenEstudiante', backref='examen', lazy=True)
    
    def to_dict(self):
        return {
            'id_examen': self.id_examen,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'id_curso': self.id_curso,
            'id_profesor': self.id_profesor,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'duracion_minutos': self.duracion_minutos,
            'intentos_permitidos': self.intentos_permitidos,
            'nota_minima': float(self.nota_minima) if self.nota_minima else 0,
            'estado': self.estado,
            'mostrar_resultados': self.mostrar_resultados,
            'aleatorizar_preguntas': self.aleatorizar_preguntas
        }

class PreguntaExamen(db.Model):
    __tablename__ = 'preguntas_examen'
    
    id_pregunta_examen = db.Column(db.Integer, primary_key=True)
    id_examen = db.Column(db.Integer, db.ForeignKey('examenes.id_examen'), nullable=False)
    id_pregunta = db.Column(db.Integer, db.ForeignKey('preguntas.id_pregunta'), nullable=False)
    orden_pregunta = db.Column(db.Integer, nullable=False)
    puntos_asignados = db.Column(db.Numeric(4,2), default=1.00)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id_pregunta_examen': self.id_pregunta_examen,
            'id_examen': self.id_examen,
            'id_pregunta': self.id_pregunta,
            'orden_pregunta': self.orden_pregunta,
            'puntos_asignados': float(self.puntos_asignados) if self.puntos_asignados else 0,
            'fecha_asignacion': self.fecha_asignacion.isoformat() if self.fecha_asignacion else None
        }

class ExamenEstudiante(db.Model):
    __tablename__ = 'examenes_estudiante'
    
    id_examen_estudiante = db.Column(db.Integer, primary_key=True)
    id_examen = db.Column(db.Integer, db.ForeignKey('examenes.id_examen'), nullable=False)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    intento_numero = db.Column(db.Integer, default=1)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    tiempo_transcurrido = db.Column(db.Integer)  # en segundos
    nota_obtenida = db.Column(db.Numeric(4,2))
    estado = db.Column(db.String(20), default='EN_PROGRESO')
    observaciones = db.Column(db.Text)
    
    # Relaciones
    respuestas_estudiante = db.relationship('RespuestaEstudiante', backref='examen_estudiante', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id_examen_estudiante': self.id_examen_estudiante,
            'id_examen': self.id_examen,
            'id_estudiante': self.id_estudiante,
            'intento_numero': self.intento_numero,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'tiempo_transcurrido': self.tiempo_transcurrido,
            'nota_obtenida': float(self.nota_obtenida) if self.nota_obtenida else 0,
            'estado': self.estado,
            'observaciones': self.observaciones
        }

class RespuestaEstudiante(db.Model):
    __tablename__ = 'respuestas_estudiante'
    
    id_respuesta = db.Column(db.Integer, primary_key=True)
    id_examen_estudiante = db.Column(db.Integer, db.ForeignKey('examenes_estudiante.id_examen_estudiante'), nullable=False)
    id_pregunta = db.Column(db.Integer, db.ForeignKey('preguntas.id_pregunta'), nullable=False)
    id_alternativa = db.Column(db.Integer, db.ForeignKey('alternativas.id_alternativa'))
    respuesta_texto = db.Column(db.String(10))  # Para V/F
    es_correcta = db.Column(db.String(1))
    puntos_obtenidos = db.Column(db.Numeric(4,2), default=0)
    mostrar_feedback = db.Column(db.String(1), default='S')
    fecha_respuesta = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id_respuesta': self.id_respuesta,
            'id_examen_estudiante': self.id_examen_estudiante,
            'id_pregunta': self.id_pregunta,
            'id_alternativa': self.id_alternativa,
            'respuesta_texto': self.respuesta_texto,
            'es_correcta': self.es_correcta,
            'puntos_obtenidos': float(self.puntos_obtenidos) if self.puntos_obtenidos else 0,
            'mostrar_feedback': self.mostrar_feedback,
            'fecha_respuesta': self.fecha_respuesta.isoformat() if self.fecha_respuesta else None
        }