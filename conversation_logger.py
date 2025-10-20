"""
Sistema de logging mejorado y simplificado
Enfocado en datos esenciales y funcionalidad real

MEJORAS:
- Solo guarda datos útiles
- Sistema de feedback funcional
- Conversaciones completas por semana
- Integración con LLM para mejor interpretación
- Dashboard simplificado

"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Boolean, Text, JSON, SmallInteger, func, Date
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# =====================================================
# MODELOS DE BASE DE DATOS SIMPLIFICADOS
# =====================================================

class ConversationMessage(Base):
    """Registro individual de cada mensaje (para feedback y revisión)"""
    __tablename__ = 'conversation_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    
    # Datos de interpretación
    intent_detected = Column(String(100))
    confidence = Column(Float, default=0.0)
    llm_interpretation = Column(String(100))  # Interpretación del LLM
    
    # Control de calidad
    needs_review = Column(Boolean, default=False)
    feedback_thumbs = Column(SmallInteger, nullable=True)  # 1 = 👍, -1 = 👎
    feedback_comment = Column(Text, nullable=True)
    
    # Metadatos
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed = Column(Boolean, default=False)


class WeeklyConversation(Base):
    """Conversaciones completas por semana (para análisis de uso)"""
    __tablename__ = 'weekly_conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    conversation_data = Column(JSON, nullable=False)  # Conversación completa
    
    # Metadatos de la conversación
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    message_count = Column(Integer, default=0)
    week_start = Column(Date, nullable=False)  # Lunes de la semana
    
    # Estadísticas básicas
    avg_confidence = Column(Float, default=0.0)
    feedback_positive = Column(Integer, default=0)
    feedback_negative = Column(Integer, default=0)


class SystemStats(Base):
    """Estadísticas diarias del sistema (resumen)"""
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    
    # Contadores esenciales
    total_messages = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    needs_review_count = Column(Integer, default=0)
    positive_feedback = Column(Integer, default=0)
    negative_feedback = Column(Integer, default=0)
    
    # Calculados
    satisfaction_rate = Column(Float, default=0.0)  # % feedback positivo


# =====================================================
# CLASE PRINCIPAL MEJORADA
# =====================================================

class ImprovedConversationLogger:
    """Logger simplificado enfocado en funcionalidad real"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Crear tablas
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("✅ Tablas de logging creadas/verificadas")
            self._cleanup_old_data()
        except Exception as e:
            self.logger.error(f"❌ Error creando tablas: {e}")
    
    @contextmanager
    def get_db_session(self):
        """Context manager para sesiones de BD"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error en sesión: {e}")
            raise
        finally:
            session.close()
    
    def log_message(self, session_id: str, user_message: str, bot_response: str,
                   intent_detected: str = None, confidence: float = 0.0,
                   llm_interpretation: str = None) -> int:
        """
        Registra un mensaje individual
        
        Returns:
            int: ID del mensaje registrado
        """
        try:
            # Determinar si necesita revisión
            needs_review = self._should_review(intent_detected, confidence, llm_interpretation)
            
            message = ConversationMessage(
                session_id=session_id,
                user_message=user_message or "Mensaje no disponible",
                bot_response=bot_response,
                intent_detected=intent_detected,
                confidence=confidence,
                llm_interpretation=llm_interpretation,
                needs_review=needs_review,
                timestamp=datetime.utcnow()
            )
            
            with self.get_db_session() as session:
                session.add(message)
                session.flush()
                message_id = message.id
            
            self.logger.info(f"✅ Mensaje registrado (ID: {message_id}, review: {needs_review})")
            
            # Actualizar estadísticas diarias
            self._update_daily_stats()
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"❌ Error logging mensaje: {e}")
            return -1
    
    def update_feedback(self, session_id: str, bot_response: str, 
                       feedback_thumbs: int, feedback_comment: str = None) -> bool:
        """
        Actualiza feedback de un mensaje específico
        
        Args:
            session_id: ID de sesión
            bot_response: Respuesta exacta del bot
            feedback_thumbs: 1 para 👍, -1 para 👎
            feedback_comment: Comentario del usuario
        """
        try:
            with self.get_db_session() as session:
                # Buscar mensaje más reciente que coincida
                message = session.query(ConversationMessage).filter(
                    ConversationMessage.session_id == session_id,
                    ConversationMessage.bot_response == bot_response
                ).order_by(ConversationMessage.timestamp.desc()).first()
                
                if not message:
                    self.logger.warning(f"No se encontró mensaje para feedback")
                    return False
                
                message.feedback_thumbs = feedback_thumbs
                message.feedback_comment = feedback_comment
                
                # Si es negativo, marcar para revisión
                if feedback_thumbs == -1:
                    message.needs_review = True
                
                session.commit()
                self.logger.info(f"✅ Feedback actualizado: {'👍' if feedback_thumbs == 1 else '👎'}")
                
                # Actualizar estadísticas
                self._update_daily_stats()
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error actualizando feedback: {e}")
            return False
    
    def save_weekly_conversation(self, session_id: str, conversation_data: List[Dict]) -> bool:
        """
        Guarda conversación completa de la semana
        
        Args:
            session_id: ID de la sesión
            conversation_data: Lista de mensajes de la conversación
        """
        try:
            if not conversation_data:
                return False
            
            # Calcular semana actual (lunes)
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            # Extraer metadatos
            start_time = datetime.fromisoformat(conversation_data[0].get('timestamp', datetime.now().isoformat()))
            end_time = datetime.fromisoformat(conversation_data[-1].get('timestamp', datetime.now().isoformat()))
            message_count = len(conversation_data)
            
            # Calcular estadísticas
            feedback_positive = len([m for m in conversation_data if m.get('feedback_thumbs') == 1])
            feedback_negative = len([m for m in conversation_data if m.get('feedback_thumbs') == -1])
            
            confidences = [m.get('confidence', 0) for m in conversation_data if m.get('confidence', 0) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            conversation = WeeklyConversation(
                session_id=session_id,
                conversation_data=conversation_data,
                start_time=start_time,
                end_time=end_time,
                message_count=message_count,
                week_start=week_start,
                avg_confidence=avg_confidence,
                feedback_positive=feedback_positive,
                feedback_negative=feedback_negative
            )
            
            with self.get_db_session() as session_db:
                # Verificar si ya existe conversación para esta sesión esta semana
                existing = session_db.query(WeeklyConversation).filter(
                    WeeklyConversation.session_id == session_id,
                    WeeklyConversation.week_start == week_start
                ).first()
                
                if existing:
                    # Actualizar existente
                    existing.conversation_data = conversation_data
                    existing.end_time = end_time
                    existing.message_count = message_count
                    existing.avg_confidence = avg_confidence
                    existing.feedback_positive = feedback_positive
                    existing.feedback_negative = feedback_negative
                else:
                    # Crear nueva
                    session_db.add(conversation)
                
                session_db.commit()
            
            self.logger.info(f"✅ Conversación semanal guardada: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando conversación semanal: {e}")
            return False
    
    def _should_review(self, intent: str, confidence: float, llm_interpretation: str) -> bool:
        """Determina si un mensaje necesita revisión"""
        # Sin intent detectado
        if not intent or intent == "nlu_fallback":
            return True
        
        # Confianza baja
        if confidence < 0.7:
            return True
        
        # LLM no pudo interpretar
        if not llm_interpretation or llm_interpretation == "unknown":
            return True
        
        return False
    
    def _update_daily_stats(self):
        """Actualiza estadísticas diarias"""
        try:
            today = datetime.now().date()
            
            with self.get_db_session() as session:
                # Obtener datos del día
                today_messages = session.query(ConversationMessage).filter(
                    func.date(ConversationMessage.timestamp) == today
                ).all()
                
                if not today_messages:
                    return
                
                # Calcular estadísticas
                total_messages = len(today_messages)
                confidences = [m.confidence for m in today_messages if m.confidence > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                needs_review_count = len([m for m in today_messages if m.needs_review])
                positive_feedback = len([m for m in today_messages if m.feedback_thumbs == 1])
                negative_feedback = len([m for m in today_messages if m.feedback_thumbs == -1])
                
                total_feedback = positive_feedback + negative_feedback
                satisfaction_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0.0
                
                # Actualizar o crear registro diario
                daily_stats = session.query(SystemStats).filter(
                    SystemStats.date == today
                ).first()
                
                if daily_stats:
                    daily_stats.total_messages = total_messages
                    daily_stats.avg_confidence = avg_confidence
                    daily_stats.needs_review_count = needs_review_count
                    daily_stats.positive_feedback = positive_feedback
                    daily_stats.negative_feedback = negative_feedback
                    daily_stats.satisfaction_rate = satisfaction_rate
                else:
                    daily_stats = SystemStats(
                        date=today,
                        total_messages=total_messages,
                        avg_confidence=avg_confidence,
                        needs_review_count=needs_review_count,
                        positive_feedback=positive_feedback,
                        negative_feedback=negative_feedback,
                        satisfaction_rate=satisfaction_rate
                    )
                    session.add(daily_stats)
                
                session.commit()
                
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas diarias: {e}")
    
    def _cleanup_old_data(self):
        """Limpia datos antiguos (conversaciones > 1 semana)"""
        try:
            cutoff_date = datetime.now().date() - timedelta(days=7)
            
            with self.get_db_session() as session:
                # Eliminar conversaciones semanales antiguas
                old_conversations = session.query(WeeklyConversation).filter(
                    WeeklyConversation.week_start < cutoff_date
                ).delete()
                
                # Mantener mensajes individuales por 30 días para feedback
                old_cutoff = datetime.now() - timedelta(days=30)
                old_messages = session.query(ConversationMessage).filter(
                    ConversationMessage.timestamp < old_cutoff,
                    ConversationMessage.feedback_thumbs.is_(None),  # Solo si no tienen feedback
                    ConversationMessage.needs_review == False
                ).delete()
                
                session.commit()
                
                if old_conversations > 0:
                    self.logger.info(f"🗑️ Eliminadas {old_conversations} conversaciones antiguas")
                if old_messages > 0:
                    self.logger.info(f"🗑️ Eliminados {old_messages} mensajes antiguos")
                    
        except Exception as e:
            self.logger.error(f"Error en limpieza: {e}")
    
    # =====================================================
    # MÉTODOS PARA EL DASHBOARD
    # =====================================================
    
    def get_summary_stats(self, days: int = 7) -> Dict[str, Any]:
        """Obtiene estadísticas de resumen para el dashboard"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            with self.get_db_session() as session:
                stats = session.query(SystemStats).filter(
                    SystemStats.date >= start_date,
                    SystemStats.date <= end_date
                ).all()
                
                if not stats:
                    return {
                        'total_conversations': 0,
                        'avg_confidence': 0.0,
                        'needs_review': 0,
                        'positive_feedback': 0,
                        'negative_feedback': 0,
                        'satisfaction_rate': 0.0
                    }
                
                # Sumar estadísticas
                total_conversations = sum(s.total_messages for s in stats)
                avg_confidence = sum(s.avg_confidence for s in stats) / len(stats)
                needs_review = sum(s.needs_review_count for s in stats)
                positive_feedback = sum(s.positive_feedback for s in stats)
                negative_feedback = sum(s.negative_feedback for s in stats)
                
                total_feedback = positive_feedback + negative_feedback
                satisfaction_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0.0
                
                return {
                    'total_conversations': total_conversations,
                    'avg_confidence': round(avg_confidence, 3),
                    'needs_review': needs_review,
                    'positive_feedback': positive_feedback,
                    'negative_feedback': negative_feedback,
                    'satisfaction_rate': round(satisfaction_rate, 1)
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def get_messages_for_review(self, limit: int = 50) -> List[Dict]:
        """Obtiene mensajes que necesitan revisión"""
        try:
            with self.get_db_session() as session:
                messages = session.query(ConversationMessage).filter(
                    ConversationMessage.needs_review == True,
                    ConversationMessage.reviewed == False
                ).order_by(ConversationMessage.timestamp.desc()).limit(limit).all()
                
                return [{
                    'id': m.id,
                    'session_id': m.session_id,
                    'user_message': m.user_message,
                    'bot_response': m.bot_response,
                    'intent_detected': m.intent_detected or 'No detectado',
                    'confidence': m.confidence,
                    'llm_interpretation': m.llm_interpretation,
                    'timestamp': m.timestamp.isoformat()
                } for m in messages]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo mensajes para revisión: {e}")
            return []
    
    def get_feedback_messages(self, feedback_type: str, limit: int = 50) -> List[Dict]:
        """Obtiene mensajes con feedback específico"""
        try:
            thumbs_value = 1 if feedback_type == 'positive' else -1
            
            with self.get_db_session() as session:
                messages = session.query(ConversationMessage).filter(
                    ConversationMessage.feedback_thumbs == thumbs_value
                ).order_by(ConversationMessage.timestamp.desc()).limit(limit).all()
                
                return [{
                    'id': m.id,
                    'session_id': m.session_id,
                    'user_message': m.user_message,
                    'bot_response': m.bot_response,
                    'intent_detected': m.intent_detected,
                    'confidence': m.confidence,
                    'feedback_comment': m.feedback_comment,
                    'timestamp': m.timestamp.isoformat()
                } for m in messages]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo feedback: {e}")
            return []
    
    def get_weekly_conversations(self) -> List[Dict]:
        """Obtiene conversaciones de la semana actual"""
        try:
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            with self.get_db_session() as session:
                conversations = session.query(WeeklyConversation).filter(
                    WeeklyConversation.week_start == week_start
                ).order_by(WeeklyConversation.start_time.desc()).all()
                
                return [{
                    'id': c.id,
                    'session_id': c.session_id,
                    'start_time': c.start_time.isoformat(),
                    'end_time': c.end_time.isoformat(),
                    'message_count': c.message_count,
                    'avg_confidence': c.avg_confidence,
                    'feedback_positive': c.feedback_positive,
                    'feedback_negative': c.feedback_negative,
                    'conversation_data': c.conversation_data
                } for c in conversations]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo conversaciones semanales: {e}")
            return []
    
    def mark_as_reviewed(self, message_id: int) -> bool:
        """Marca un mensaje como revisado"""
        try:
            with self.get_db_session() as session:
                message = session.query(ConversationMessage).filter_by(id=message_id).first()
                if message:
                    message.reviewed = True
                    message.needs_review = False
                    session.commit()
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error marcando como revisado: {e}")
            return False


# =====================================================
# FUNCIONES PARA INTEGRACIÓN CON RASA Y LLM
# =====================================================

def setup_improved_logging_system(database_url: str) -> ImprovedConversationLogger:
    """Inicializa el sistema mejorado"""
    try:
        logger_instance = ImprovedConversationLogger(database_url)
        logger.info("✅ Sistema de logging mejorado inicializado")
        return logger_instance
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema: {e}")
        raise

def log_rasa_interaction_improved(logger_instance, tracker, bot_response, 
                                 llm_classification=None, response_time_ms=None):
    """Log mejorado para interacciones de Rasa con clasificación LLM"""
    if not logger_instance:
        return
    
    try:
        session_id = getattr(tracker, 'sender_id', 'unknown')
        
        # Extraer mensaje del usuario
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
        
        # Usar clasificación LLM si está disponible
        llm_interpretation = None
        if llm_classification:
            llm_interpretation = llm_classification.get('intent')
            if llm_classification.get('confidence', 0) > confidence:
                confidence = llm_classification.get('confidence', 0)
        
        # Registrar mensaje
        message_id = logger_instance.log_message(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            intent_detected=intent_detected,
            confidence=confidence,
            llm_interpretation=llm_interpretation
        )
        
        return message_id
        
    except Exception as e:
        logger.error(f"❌ Error en log mejorado: {e}")
        return -1

# Instancia global
_global_improved_logger = None

def get_improved_conversation_logger():
    """Obtiene la instancia global del logger mejorado"""
    return _global_improved_logger

def set_improved_conversation_logger(logger_instance):
    """Establece la instancia global del logger mejorado"""
    global _global_improved_logger
    _global_improved_logger = logger_instance