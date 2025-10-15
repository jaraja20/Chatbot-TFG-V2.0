"""
Sistema de logging y aprendizaje mejorado para el chatbot de turnos
Registra conversaciones con feedback de usuario y marcado automático de revisión
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Boolean, Text, JSON, SmallInteger, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# =====================================================
# MODELO MEJORADO CON CAMPOS DE FEEDBACK
# =====================================================

class ConversationLog(Base):
    """Registro de todas las conversaciones con feedback"""
    __tablename__ = 'conversation_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    intent_detected = Column(String(100))
    confidence = Column(Float, default=0.0)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # ✅ NUEVOS CAMPOS DE FEEDBACK
    feedback_thumbs = Column(SmallInteger, nullable=True)  # 1 = 👍, -1 = 👎, NULL = sin feedback
    feedback_comment = Column(Text, nullable=True)  # Comentario cuando presiona 👎
    needs_review = Column(Boolean, default=False)  # Marca si requiere revisión
    message_block = Column(Text, nullable=True)  # Bloque combinado [USUARIO] + [BOT]
    
    # Campos heredados
    was_helpful = Column(Boolean)
    feedback_score = Column(Integer)
    response_time_ms = Column(Integer)


class IntentAnalysis(Base):
    """Análisis de rendimiento por intent"""
    __tablename__ = 'intent_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    intent_name = Column(String(100), nullable=False)
    total_uses = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    examples_needed = Column(Boolean, default=False)


class FuzzyAnalysisLog(Base):
    """Registro específico para análisis del motor difuso"""
    __tablename__ = 'fuzzy_analysis_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    user_query = Column(Text, nullable=False)
    analysis_type = Column(String(50))
    analysis_data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    processing_time_ms = Column(Integer)


class LearningMetrics(Base):
    """Métricas generales de aprendizaje del sistema"""
    __tablename__ = 'learning_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    total_conversations = Column(Integer, default=0)
    successful_interactions = Column(Integer, default=0)
    fuzzy_activations = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0.0)
    user_satisfaction_score = Column(Float, default=0.0)


# =====================================================
# CLASE PRINCIPAL DEL LOGGER MEJORADO
# =====================================================

class ConversationLogger:
    """Maneja el logging y análisis de conversaciones con feedback"""
    
    def __init__(self, database_url: str):
        """Inicializa el logger con conexión a BD"""
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Crear tablas si no existen
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("✅ Tablas de aprendizaje verificadas/creadas con nuevos campos")
            self._add_new_columns_if_missing()
        except Exception as e:
            self.logger.error(f"❌ Error creando tablas de aprendizaje: {e}")
    
    def _add_new_columns_if_missing(self):
        """Agrega columnas nuevas si no existen (migración automática)"""
        try:
            with self.engine.connect() as conn:
                # Verificar si las columnas nuevas existen
                result = conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='conversation_logs'
                """)
                existing_columns = [row[0] for row in result]
                
                # Agregar columnas faltantes
                if 'feedback_thumbs' not in existing_columns:
                    conn.execute("ALTER TABLE conversation_logs ADD COLUMN feedback_thumbs SMALLINT")
                    conn.commit()
                    self.logger.info("✅ Columna feedback_thumbs agregada")
                
                if 'feedback_comment' not in existing_columns:
                    conn.execute("ALTER TABLE conversation_logs ADD COLUMN feedback_comment TEXT")
                    conn.commit()
                    self.logger.info("✅ Columna feedback_comment agregada")
                
                if 'needs_review' not in existing_columns:
                    conn.execute("ALTER TABLE conversation_logs ADD COLUMN needs_review BOOLEAN DEFAULT FALSE")
                    conn.commit()
                    self.logger.info("✅ Columna needs_review agregada")
                
                if 'message_block' not in existing_columns:
                    conn.execute("ALTER TABLE conversation_logs ADD COLUMN message_block TEXT")
                    conn.commit()
                    self.logger.info("✅ Columna message_block agregada")
                
        except Exception as e:
            self.logger.warning(f"⚠️ No se pudieron agregar columnas (puede ser normal): {e}")
    
    @contextmanager
    def get_db_session(self):
        """Context manager para sesiones de BD"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error en sesión de logging: {e}")
            raise
        finally:
            session.close()
    
    def log_conversation(self, session_id: str, user_message: str, bot_response: str, 
                        intent_detected: str = '', confidence: float = 0.0, 
                        response_time_ms: int = None) -> int:
        """
        Registra una conversación completa con marcado automático de revisión
        
        Returns:
            int: ID del registro creado
        """
        try:
            # Validar que user_message no sea None o vacío
            if not user_message:
                user_message = "Mensaje del usuario no disponible"
            
            # ✅ GENERAR MESSAGE_BLOCK
            message_block = self._generate_message_block(user_message, bot_response)
            
            # ✅ DETERMINAR SI NECESITA REVISIÓN
            needs_review = self._should_mark_for_review(intent_detected, confidence)
            
            log_entry = ConversationLog(
                session_id=session_id,
                user_message=user_message,
                bot_response=bot_response,
                intent_detected=intent_detected,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time_ms,
                message_block=message_block,
                needs_review=needs_review,
                feedback_thumbs=None,  # Sin feedback inicial
                feedback_comment=None
            )
            
            with self.get_db_session() as session:
                session.add(log_entry)
                session.flush()
                log_id = log_entry.id
                
            self.logger.info(f"✅ Conversación registrada (ID: {log_id}, needs_review: {needs_review})")
            
            # Actualizar métricas de intent
            self._update_intent_metrics(intent_detected, confidence)
            
            return log_id
            
        except Exception as e:
            self.logger.error(f"❌ Error logging conversación: {e}")
            return -1
    
    def _generate_message_block(self, user_message: str, bot_response: str) -> str:
        """Genera el bloque combinado de mensaje"""
        block = f"[USUARIO]\n{user_message}\n\n[BOT]\n{bot_response}"
        return block
    
    def _should_mark_for_review(self, intent_detected: str, confidence: float) -> bool:
        """
        Determina si un mensaje debe marcarse para revisión
        
        Criterios:
        - Intent no detectado o NULL
        - Confianza menor a 0.75
        """
        if not intent_detected or intent_detected == "No detectado":
            return True
        
        if confidence < 0.75:
            return True
        
        return False
    
    def update_feedback(self, log_id: int, feedback_thumbs: int, 
                       feedback_comment: str = None) -> bool:
        """
        Actualiza el feedback de un mensaje existente
        
        Args:
            log_id: ID del registro
            feedback_thumbs: 1 para 👍, -1 para 👎
            feedback_comment: Comentario opcional (requerido si thumbs=-1)
        
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            with self.get_db_session() as session:
                log_entry = session.query(ConversationLog).filter_by(id=log_id).first()
                
                if not log_entry:
                    self.logger.warning(f"⚠️ No se encontró el registro con ID {log_id}")
                    return False
                
                log_entry.feedback_thumbs = feedback_thumbs
                log_entry.feedback_comment = feedback_comment
                
                # ✅ Si es feedback negativo, marcar para revisión
                if feedback_thumbs == -1:
                    log_entry.needs_review = True
                
                session.commit()
                self.logger.info(f"✅ Feedback actualizado para ID {log_id}: {'👍' if feedback_thumbs == 1 else '👎'}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando feedback: {e}")
            return False
    
    def mark_as_reviewed(self, log_id: int) -> bool:
        """Marca un mensaje como revisado"""
        try:
            with self.get_db_session() as session:
                log_entry = session.query(ConversationLog).filter_by(id=log_id).first()
                
                if not log_entry:
                    return False
                
                log_entry.needs_review = False
                session.commit()
                self.logger.info(f"✅ Registro {log_id} marcado como revisado")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error marcando como revisado: {e}")
            return False
    
    def get_messages_needing_review(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene mensajes que necesitan revisión"""
        try:
            with self.get_db_session() as session:
                messages = session.query(ConversationLog).filter(
                    ConversationLog.needs_review == True
                ).order_by(ConversationLog.timestamp.desc()).limit(limit).all()
                
                return [{
                    'id': msg.id,
                    'session_id': msg.session_id,
                    'user_message': msg.user_message,
                    'bot_response': msg.bot_response,
                    'intent_detected': msg.intent_detected or 'No detectado',
                    'confidence': msg.confidence,
                    'timestamp': msg.timestamp.isoformat(),
                    'message_block': msg.message_block,
                    'feedback_thumbs': msg.feedback_thumbs,
                    'feedback_comment': msg.feedback_comment
                } for msg in messages]
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo mensajes para revisión: {e}")
            return []
    
    def get_feedback_messages(self, feedback_type: str = 'negative', limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene mensajes con feedback de usuario
        
        Args:
            feedback_type: 'negative' (👎) o 'positive' (👍)
            limit: Cantidad máxima de resultados
        """
        try:
            with self.get_db_session() as session:
                if feedback_type == 'negative':
                    messages = session.query(ConversationLog).filter(
                        ConversationLog.feedback_thumbs == -1
                    ).order_by(ConversationLog.timestamp.desc()).limit(limit).all()
                else:
                    messages = session.query(ConversationLog).filter(
                        ConversationLog.feedback_thumbs == 1
                    ).order_by(ConversationLog.timestamp.desc()).limit(limit).all()
                
                return [{
                    'id': msg.id,
                    'session_id': msg.session_id,
                    'user_message': msg.user_message,
                    'bot_response': msg.bot_response,
                    'intent_detected': msg.intent_detected or 'No detectado',
                    'confidence': msg.confidence,
                    'timestamp': msg.timestamp.isoformat(),
                    'message_block': msg.message_block,
                    'feedback_comment': msg.feedback_comment
                } for msg in messages]
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo mensajes con feedback: {e}")
            return []
    
    def log_fuzzy_analysis(self, session_id: str, user_query: str, 
                          analysis_type: str, analysis_data: Dict, 
                          processing_time_ms: int = None) -> bool:
        """Registra análisis específico del motor difuso"""
        try:
            if not user_query:
                user_query = "Consulta del motor difuso"
            
            fuzzy_log = FuzzyAnalysisLog(
                session_id=session_id,
                user_query=user_query,
                analysis_type=analysis_type,
                analysis_data=analysis_data,
                timestamp=datetime.utcnow(),
                processing_time_ms=processing_time_ms
            )
            
            with self.get_db_session() as session:
                session.add(fuzzy_log)
                
            self.logger.info(f"✅ Análisis difuso registrado: {analysis_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error logging análisis difuso: {e}")
            return False
    
    def _update_intent_metrics(self, intent_name: str, confidence: float):
        """Actualiza métricas de rendimiento por intent"""
        if not intent_name:
            return
        
        try:
            with self.get_db_session() as session:
                analysis = session.query(IntentAnalysis).filter_by(intent_name=intent_name).first()
                
                if analysis:
                    analysis.total_uses += 1
                    new_avg = ((analysis.avg_confidence * (analysis.total_uses - 1)) + confidence) / analysis.total_uses
                    analysis.avg_confidence = new_avg
                    analysis.last_updated = datetime.utcnow()
                    analysis.examples_needed = new_avg < 0.7
                else:
                    analysis = IntentAnalysis(
                        intent_name=intent_name,
                        total_uses=1,
                        avg_confidence=confidence,
                        examples_needed=confidence < 0.7
                    )
                    session.add(analysis)
                    
        except Exception as e:
            self.logger.error(f"❌ Error actualizando métricas de intent: {e}")
    
    def get_daily_stats(self, date: datetime = None) -> Dict[str, Any]:
        """Obtiene estadísticas del día"""
        if not date:
            date = datetime.now().date()
        
        try:
            with self.get_db_session() as session:
                start_date = datetime.combine(date, datetime.min.time())
                end_date = start_date + timedelta(days=1)
                
                conversations = session.query(ConversationLog).filter(
                    ConversationLog.timestamp >= start_date,
                    ConversationLog.timestamp < end_date
                ).all()
                
                total_conversations = len(conversations)
                unique_sessions = len(set(conv.session_id for conv in conversations))
                avg_confidence = sum(conv.confidence for conv in conversations) / max(1, total_conversations)
                
                response_times = [conv.response_time_ms for conv in conversations if conv.response_time_ms]
                avg_response_time = sum(response_times) / max(1, len(response_times)) if response_times else 0
                
                # ✅ Estadísticas de feedback
                positive_feedback = len([c for c in conversations if c.feedback_thumbs == 1])
                negative_feedback = len([c for c in conversations if c.feedback_thumbs == -1])
                needs_review_count = len([c for c in conversations if c.needs_review])
                
                return {
                    'date': date.isoformat(),
                    'total_conversations': total_conversations,
                    'unique_sessions': unique_sessions,
                    'avg_confidence': round(avg_confidence, 3),
                    'avg_response_time_ms': round(avg_response_time, 2),
                    'positive_feedback': positive_feedback,
                    'negative_feedback': negative_feedback,
                    'needs_review': needs_review_count
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estadísticas diarias: {e}")
            return {}


# =====================================================
# FUNCIONES DE UTILIDAD PARA RASA
# =====================================================

def setup_learning_system(database_url: str) -> ConversationLogger:
    """Inicializa el sistema de aprendizaje mejorado"""
    try:
        logger_instance = ConversationLogger(database_url)
        logger.info("✅ Sistema de aprendizaje mejorado inicializado correctamente")
        return logger_instance
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema de aprendizaje: {e}")
        raise


def log_rasa_interaction(logger_instance, tracker, bot_response, response_time_ms=None):
    """Log de interacción con Rasa - Versión mejorada"""
    if not logger_instance:
        return
    
    try:
        session_id = getattr(tracker, 'sender_id', 'unknown')
        
        events = getattr(tracker, 'events', [])
        user_message = "Inicio de sesión"
        intent_detected = ""
        confidence = 0.0
        
        for event in reversed(events):
            if hasattr(event, 'type') and event.type == 'user':
                if hasattr(event, 'text') and event.text:
                    user_message = event.text
                if hasattr(event, 'parse_data') and event.parse_data:
                    intent_data = event.parse_data.get('intent', {})
                    intent_detected = intent_data.get('name', '')
                    confidence = intent_data.get('confidence', 0.0)
                break
        
        if not user_message or user_message == "Inicio de sesión":
            if "sesión iniciada" in bot_response.lower():
                user_message = "/session_start"
                intent_detected = "session_start"
                confidence = 1.0
        
        if not user_message:
            user_message = "Mensaje del usuario no disponible"
        
        # ✅ Registrar con nuevos campos
        log_id = logger_instance.log_conversation(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            intent_detected=intent_detected,
            confidence=confidence,
            response_time_ms=response_time_ms
        )
        
        return log_id
        
    except Exception as e:
        logger.error(f"❌ Error logging interacción de Rasa: {e}")
        return -1


# Instancia global del logger
_global_logger = None

def get_conversation_logger():
    """Obtiene la instancia global del logger"""
    return _global_logger

def set_conversation_logger(logger_instance):
    """Establece la instancia global del logger"""
    global _global_logger
    _global_logger = logger_instance


def log_fuzzy_activation(logger_instance, tracker, analysis_data, response_time_ms=None):
    """Log específico para activación del motor difuso"""
    if not logger_instance:
        return
    
    try:
        session_id = getattr(tracker, 'sender_id', 'unknown')
        
        events = getattr(tracker, 'events', [])
        user_message = "Activación motor difuso"
        
        for event in reversed(events):
            if hasattr(event, 'type') and event.type == 'user':
                if hasattr(event, 'text') and event.text:
                    user_message = event.text
                break
        
        if not user_message:
            user_message = "Consulta del motor difuso"
        
        logger_instance.log_fuzzy_analysis(
            session_id=session_id,
            user_query=user_message,
            analysis_type="complete_recommendation",
            analysis_data=analysis_data,
            processing_time_ms=response_time_ms
        )
        
    except Exception as e:
        logger.error(f"❌ Error logging análisis difuso: {e}")


# =====================================================
# FUNCIONES ADICIONALES PARA EL DASHBOARD
# =====================================================

def get_general_stats(logger_instance, days: int = 7) -> Dict[str, Any]:
    """Obtiene estadísticas generales para el dashboard"""
    if not logger_instance:
        return {}
    
    try:
        with logger_instance.get_db_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            conversations = session.query(ConversationLog).filter(
                ConversationLog.timestamp >= start_date
            ).all()
            
            if not conversations:
                return {
                    'total_conversations': 0,
                    'unique_sessions': 0,
                    'avg_confidence': 0.0,
                    'needs_review_count': 0,
                    'positive_feedback': 0,
                    'negative_feedback': 0
                }
            
            total_conversations = len(conversations)
            unique_sessions = len(set(conv.session_id for conv in conversations))
            
            confidences = [conv.confidence for conv in conversations if conv.confidence]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            needs_review_count = len([c for c in conversations if c.needs_review])
            positive_feedback = len([c for c in conversations if c.feedback_thumbs == 1])
            negative_feedback = len([c for c in conversations if c.feedback_thumbs == -1])
            
            return {
                'total_conversations': total_conversations,
                'unique_sessions': unique_sessions,
                'avg_confidence': round(avg_confidence, 3),
                'needs_review_count': needs_review_count,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'period_days': days
            }
            
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas generales: {e}")
        return {}


def generate_yaml_suggestion(user_message: str, intent_detected: str = None) -> str:
    """Genera sugerencia YAML para agregar al nlu.yml"""
    suggested_intent = intent_detected if intent_detected and intent_detected != 'No detectado' else 'nlu_fallback'
    
    yaml_suggestion = f"""# Agregar a nlu.yml

- intent: {suggested_intent}
  examples: |
    - {user_message}"""
    
    return yaml_suggestion