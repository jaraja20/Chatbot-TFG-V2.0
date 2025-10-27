# conversation_logger.py
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Boolean, Text, JSON, SmallInteger, func, Date
from sqlalchemy.orm import declarative_base, sessionmaker, Session as DBSession
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# =====================================================
# MODELOS DE BASE DE DATOS
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


class ConversationContextCapture(Base):
    """✅ NUEVA TABLA: Captura contexto completo de conversaciones problemáticas"""
    __tablename__ = 'conversation_context_enhanced'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    
    # Mensaje problemático (el que falló)
    problematic_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    intent_detected = Column(String(100))
    confidence = Column(Float, default=0.0)
    
    # ✅ CONTEXTO ANTERIOR (mensaje previo del usuario)
    previous_user_message = Column(Text, nullable=True)
    previous_bot_response = Column(Text, nullable=True)
    previous_intent = Column(String(100), nullable=True)
    
    # ✅ CONTEXTO POSTERIOR (siguiente mensaje del usuario - si existe)
    next_user_message = Column(Text, nullable=True)
    next_bot_response = Column(Text, nullable=True)
    next_intent = Column(String(100), nullable=True)
    
    # Tipo de problema
    feedback_type = Column(String(30))  # 'thumbs_down', 'fallback', 'low_confidence', 'misunderstanding'
    feedback_comment = Column(Text, nullable=True)  # Comentario del usuario si dio feedback negativo
    
    # ✅ SUGERENCIA AUTOMÁTICA
    suggested_intent = Column(String(100), nullable=True)
    suggested_training_example = Column(Text, nullable=True)
    
    # Metadatos
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    admin_notes = Column(Text, nullable=True)


class ModelEfficiencyStats(Base):
    """Estadísticas diarias de eficiencia del modelo"""
    __tablename__ = 'model_efficiency_enhanced'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    
    # Contadores de efectividad
    total_interactions = Column(Integer, default=0)
    successful_interactions = Column(Integer, default=0)  # thumbs up
    failed_interactions = Column(Integer, default=0)     # thumbs down
    neutral_interactions = Column(Integer, default=0)     # sin feedback
    fallback_interactions = Column(Integer, default=0)   # nlu_fallback
    low_confidence_interactions = Column(Integer, default=0)  # < 0.7
    
    # ✅ MÉTRICAS CALCULADAS
    success_rate = Column(Float, default=0.0)         # % exitosas (thumbs up)
    fallback_rate = Column(Float, default=0.0)        # % fallback
    confidence_rate = Column(Float, default=0.0)      # % alta confianza (>0.7)
    user_satisfaction = Column(Float, default=0.0)    # (thumbs_up - thumbs_down) / total_feedback
    overall_efficiency = Column(Float, default=0.0)   # métrica combinada


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
# CLASE PRINCIPAL DEL LOGGER MEJORADO
# =====================================================

class ImprovedConversationLogger:
    """Logger mejorado con captura de contexto completo"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Crear tablas
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("✅ Tablas de logging mejorado creadas/verificadas")
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
                
                # Actualizar estadísticas diarias
                self._update_daily_stats(session, confidence, needs_review)
                
                return message_id
                
        except Exception as e:
            self.logger.error(f"Error registrando mensaje: {e}")
            return -1
    
    def _should_review(self, intent: str, confidence: float, llm_interpretation: str) -> bool:
        """Determina si un mensaje necesita revisión"""
        if not intent or intent == 'nlu_fallback' or intent == 'No detectado':
            return True
        if confidence < 0.7:
            return True
        if not llm_interpretation:
            return True
        return False
    
    def _update_daily_stats(self, session: DBSession, confidence: float, needs_review: bool):
        """Actualiza estadísticas diarias"""
        today = datetime.utcnow().date()
        
        stats = session.query(SystemStats).filter_by(date=today).first()
        if not stats:
            stats = SystemStats(
                date=today,
                total_messages=0,
                avg_confidence=0.0,
                needs_review_count=0,
                positive_feedback=0,
                negative_feedback=0,
                satisfaction_rate=0.0
            )
            session.add(stats)
            session.flush()
        
        # Asegurar que los valores no sean None
        stats.total_messages = (stats.total_messages or 0) + 1
        stats.avg_confidence = (
            ((stats.avg_confidence or 0.0) * (stats.total_messages - 1) + confidence) 
            / stats.total_messages
        )
        if needs_review:
            stats.needs_review_count = (stats.needs_review_count or 0) + 1
    
    def update_feedback(self, session_id: str, bot_response: str, 
                       feedback_thumbs: int, feedback_comment: str = None) -> bool:
      
        try:
            with self.get_db_session() as session:
                # Buscar el mensaje más reciente que coincida
                message = session.query(ConversationMessage).filter(
                    ConversationMessage.session_id == session_id,
                    ConversationMessage.bot_response == bot_response
                ).order_by(ConversationMessage.timestamp.desc()).first()
                
                if not message:
                    self.logger.warning(f"No se encontró mensaje para actualizar feedback")
                    return False
                
                # Actualizar feedback
                message.feedback_thumbs = feedback_thumbs
                message.feedback_comment = feedback_comment
                
                # Si es negativo, marcar para revisión
                if feedback_thumbs == -1:
                    message.needs_review = True
                
                # Actualizar estadísticas diarias
                today = datetime.utcnow().date()
                stats = session.query(SystemStats).filter_by(date=today).first()
                if stats:
                    if feedback_thumbs == 1:
                        stats.positive_feedback += 1
                    elif feedback_thumbs == -1:
                        stats.negative_feedback += 1
                    
                    total_feedback = stats.positive_feedback + stats.negative_feedback
                    if total_feedback > 0:
                        stats.satisfaction_rate = (stats.positive_feedback / total_feedback) * 100
                
                # ✅ SI ES FEEDBACK NEGATIVO, CAPTURAR CONTEXTO COMPLETO
                if feedback_thumbs == -1:
                    self._capture_negative_feedback_context(
                        session, 
                        session_id, 
                        message.user_message,
                        message.bot_response,
                        message.intent_detected,
                        message.confidence,
                        feedback_comment
                    )
                
                # Actualizar eficiencia del modelo
                self.update_model_efficiency_stats()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error actualizando feedback: {e}")
            return False
    
    def _capture_negative_feedback_context(self, session: DBSession, session_id: str,
                                           problematic_message: str, bot_response: str,
                                           intent_detected: str, confidence: float,
                                           feedback_comment: str = None):
        """
        ✅ CAPTURA CONTEXTO COMPLETO cuando hay feedback negativo
        Busca mensaje anterior y deja espacio para el posterior
        """
        try:
            # Obtener todos los mensajes de la sesión ordenados por tiempo
            all_messages = session.query(ConversationMessage).filter(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.timestamp.asc()).all()
            
            # Encontrar el mensaje problemático
            problematic_index = None
            for i, msg in enumerate(all_messages):
                if msg.user_message == problematic_message and msg.bot_response == bot_response:
                    problematic_index = i
                    break
            
            if problematic_index is None:
                self.logger.warning("No se encontró el mensaje problemático en el historial")
                return
            
            # Extraer contexto anterior
            previous_user_message = None
            previous_bot_response = None
            previous_intent = None
            
            if problematic_index > 0:
                prev_msg = all_messages[problematic_index - 1]
                previous_user_message = prev_msg.user_message
                previous_bot_response = prev_msg.bot_response
                previous_intent = prev_msg.intent_detected
            
            # El contexto posterior se llenará en el siguiente mensaje del usuario
            # Por ahora lo dejamos vacío
            
            # Generar sugerencia automática
            suggested_intent, suggested_example = self._generate_suggestion(
                problematic_message, 
                intent_detected,
                confidence
            )
            
            # Crear registro de contexto
            context_capture = ConversationContextCapture(
                session_id=session_id,
                problematic_message=problematic_message,
                bot_response=bot_response,
                intent_detected=intent_detected or 'nlu_fallback',
                confidence=confidence,
                previous_user_message=previous_user_message,
                previous_bot_response=previous_bot_response,
                previous_intent=previous_intent,
                feedback_type='thumbs_down',
                feedback_comment=feedback_comment,
                suggested_intent=suggested_intent,
                suggested_training_example=suggested_example,
                timestamp=datetime.utcnow()
            )
            
            session.add(context_capture)
            self.logger.info(f"👎 Contexto de feedback negativo capturado: {problematic_message[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error capturando contexto de feedback negativo: {e}")
    
    def capture_conversation_context(self, session_id: str, problematic_message: str,
                                    bot_response: str, intent_detected: str = None,
                                    confidence: float = 0.0, feedback_type: str = 'fallback') -> int:
        """
        ✅ CAPTURA CONTEXTO de mensajes no entendidos o con baja confianza
        Se llama automáticamente cuando el bot no entiende algo
        
        Args:
            session_id: ID de sesión
            problematic_message: Mensaje que causó problema
            bot_response: Respuesta del bot
            intent_detected: Intent detectado (si hay)
            confidence: Nivel de confianza
            feedback_type: Tipo de problema ('fallback', 'low_confidence', 'misunderstanding')
        
        Returns:
            int: ID del contexto capturado
        """
        try:
            with self.get_db_session() as session:
                # Obtener todos los mensajes de la sesión
                all_messages = session.query(ConversationMessage).filter(
                    ConversationMessage.session_id == session_id
                ).order_by(ConversationMessage.timestamp.desc()).limit(10).all()
                
                all_messages.reverse()  # Orden cronológico
                
                # Buscar contexto anterior
                previous_user_message = None
                previous_bot_response = None
                previous_intent = None
                
                for i, msg in enumerate(all_messages):
                    if msg.user_message == problematic_message:
                        if i > 0:
                            prev_msg = all_messages[i - 1]
                            previous_user_message = prev_msg.user_message
                            previous_bot_response = prev_msg.bot_response
                            previous_intent = prev_msg.intent_detected
                        break
                
                # Generar sugerencia automática
                suggested_intent, suggested_example = self._generate_suggestion(
                    problematic_message,
                    intent_detected,
                    confidence
                )
                
                # Crear registro de contexto
                context_capture = ConversationContextCapture(
                    session_id=session_id,
                    problematic_message=problematic_message,
                    bot_response=bot_response,
                    intent_detected=intent_detected or 'nlu_fallback',
                    confidence=confidence,
                    previous_user_message=previous_user_message,
                    previous_bot_response=previous_bot_response,
                    previous_intent=previous_intent,
                    feedback_type=feedback_type,
                    suggested_intent=suggested_intent,
                    suggested_training_example=suggested_example,
                    timestamp=datetime.utcnow()
                )
                
                session.add(context_capture)
                session.flush()
                
                self.logger.info(f"🔍 Contexto capturado [{feedback_type}]: {problematic_message[:50]}...")
                
                return context_capture.id
                
        except Exception as e:
            self.logger.error(f"Error capturando contexto: {e}")
            return -1
    
    def update_context_with_next_message(self, session_id: str, next_user_message: str,
                                        next_bot_response: str, next_intent: str = None):
        """
        ✅ ACTUALIZA el contexto con el siguiente mensaje del usuario
        Esto completa el contexto posterior de un mensaje problemático
        """
        try:
            with self.get_db_session() as session:
                # Buscar el contexto más reciente sin mensaje siguiente
                context = session.query(ConversationContextCapture).filter(
                    ConversationContextCapture.session_id == session_id,
                    ConversationContextCapture.next_user_message == None
                ).order_by(ConversationContextCapture.timestamp.desc()).first()
                
                if context:
                    context.next_user_message = next_user_message
                    context.next_bot_response = next_bot_response
                    context.next_intent = next_intent
                    
                    self.logger.info(f"✅ Contexto actualizado con mensaje siguiente")
                    
        except Exception as e:
            self.logger.error(f"Error actualizando contexto con siguiente mensaje: {e}")
    
    def _generate_suggestion(self, user_message: str, intent_detected: str = None,
                            confidence: float = 0.0) -> tuple:
        """
        ✅ GENERA SUGERENCIAS automáticas para mejorar el modelo
        
        Returns:
            tuple: (suggested_intent, suggested_training_example)
        """
        # Si hay intent con baja confianza, sugerir reforzar ese intent
        if intent_detected and intent_detected != 'nlu_fallback' and confidence < 0.7:
            suggested_intent = intent_detected
            suggested_example = f"- intent: {intent_detected}\n  examples: |\n    - {user_message}"
            return suggested_intent, suggested_example
        
        # Si es fallback, sugerir intent común basado en palabras clave
        keywords_to_intents = {
            'turno': 'agendar_turno',
            'agendar': 'agendar_turno',
            'requisito': 'consultar_requisitos',
            'documento': 'consultar_requisitos',
            'donde': 'consultar_ubicacion',
            'ubicacion': 'consultar_ubicacion',
            'costo': 'consultar_costo',
            'precio': 'consultar_costo',
            'horario': 'consultar_horarios',
            'hora': 'elegir_horario',
        }
        
        message_lower = user_message.lower()
        for keyword, intent in keywords_to_intents.items():
            if keyword in message_lower:
                suggested_intent = intent
                suggested_example = f"- intent: {intent}\n  examples: |\n    - {user_message}"
                return suggested_intent, suggested_example
        
        # Si no hay coincidencia, sugerir revisar manualmente
        suggested_intent = 'REVISAR_MANUALMENTE'
        suggested_example = f"# Revisar este ejemplo manualmente:\n# {user_message}"
        return suggested_intent, suggested_example
    
    def update_model_efficiency_stats(self):
        """✅ ACTUALIZA estadísticas de eficiencia del modelo"""
        try:
            with self.get_db_session() as session:
                today = datetime.utcnow().date()
                
                # Obtener o crear registro de eficiencia
                efficiency = session.query(ModelEfficiencyStats).filter_by(date=today).first()
                if not efficiency:
                    efficiency = ModelEfficiencyStats(date=today)
                    session.add(efficiency)
                
                # Contar interacciones del día
                messages_today = session.query(ConversationMessage).filter(
                    func.date(ConversationMessage.timestamp) == today
                ).all()
                
                efficiency.total_interactions = len(messages_today)
                efficiency.successful_interactions = sum(1 for m in messages_today if m.feedback_thumbs == 1)
                efficiency.failed_interactions = sum(1 for m in messages_today if m.feedback_thumbs == -1)
                efficiency.neutral_interactions = sum(1 for m in messages_today if m.feedback_thumbs is None)
                efficiency.fallback_interactions = sum(1 for m in messages_today if m.intent_detected == 'nlu_fallback')
                efficiency.low_confidence_interactions = sum(1 for m in messages_today if m.confidence < 0.7)
                
                # Calcular métricas
                total = efficiency.total_interactions
                if total > 0:
                    efficiency.success_rate = (efficiency.successful_interactions / total) * 100
                    efficiency.fallback_rate = (efficiency.fallback_interactions / total) * 100
                    efficiency.confidence_rate = ((total - efficiency.low_confidence_interactions) / total) * 100
                    
                    total_feedback = efficiency.successful_interactions + efficiency.failed_interactions
                    if total_feedback > 0:
                        efficiency.user_satisfaction = ((efficiency.successful_interactions - efficiency.failed_interactions) / total_feedback) * 100
                    
                    # Métrica combinada (ponderada)
                    efficiency.overall_efficiency = (
                        efficiency.success_rate * 0.4 +
                        (100 - efficiency.fallback_rate) * 0.3 +
                        efficiency.confidence_rate * 0.2 +
                        max(0, efficiency.user_satisfaction) * 0.1
                    )
                
                self.logger.info(f"📊 Estadísticas de eficiencia actualizadas: {efficiency.overall_efficiency:.2f}%")
                
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas de eficiencia: {e}")
    
    # =====================================================
    # MÉTODOS PARA EL DASHBOARD
    # =====================================================
    
    def get_problematic_messages_with_context(self, limit: int = 50) -> List[Dict]:
        """
        ✅ OBTIENE mensajes problemáticos CON CONTEXTO COMPLETO
        Para mostrar en el dashboard con contexto anterior y posterior
        """
        try:
            with self.get_db_session() as session:
                contexts = session.query(ConversationContextCapture).filter(
                    ConversationContextCapture.resolved == False
                ).order_by(ConversationContextCapture.timestamp.desc()).limit(limit).all()
                
                results = []
                for ctx in contexts:
                    results.append({
                        'id': ctx.id,
                        'session_id': ctx.session_id,
                        'timestamp': ctx.timestamp.isoformat(),
                        
                        # Contexto ANTERIOR
                        'previous_user_message': ctx.previous_user_message,
                        'previous_bot_response': ctx.previous_bot_response,
                        'previous_intent': ctx.previous_intent,
                        
                        # Mensaje PROBLEMÁTICO
                        'problematic_message': ctx.problematic_message,
                        'bot_response': ctx.bot_response,
                        'intent_detected': ctx.intent_detected,
                        'confidence': ctx.confidence,
                        
                        # Contexto POSTERIOR
                        'next_user_message': ctx.next_user_message,
                        'next_bot_response': ctx.next_bot_response,
                        'next_intent': ctx.next_intent,
                        
                        # Feedback y sugerencias
                        'feedback_type': ctx.feedback_type,
                        'feedback_comment': ctx.feedback_comment,
                        'suggested_intent': ctx.suggested_intent,
                        'suggested_training_example': ctx.suggested_training_example
                    })
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error obteniendo mensajes problemáticos: {e}")
            return []
    
    def get_negative_feedback_messages(self, limit: int = 50) -> List[Dict]:
        """
        ✅ NUEVA: Obtiene mensajes con feedback negativo desde conversation_messages
        Y también desde conversation_context_enhanced
        
        Combina ambas fuentes para mostrar TODO el feedback negativo
        """
        try:
            with self.get_db_session() as session:
                results = []
                
                # 1. Obtener feedback directo desde conversation_messages
                direct_feedback = session.query(ConversationMessage).filter(
                    ConversationMessage.feedback_thumbs == -1
                ).order_by(ConversationMessage.timestamp.desc()).limit(limit).all()
                
                for msg in direct_feedback:
                    # Buscar contexto (mensajes previos/siguientes en la misma sesión)
                    prev_msg = session.query(ConversationMessage).filter(
                        ConversationMessage.session_id == msg.session_id,
                        ConversationMessage.timestamp < msg.timestamp
                    ).order_by(ConversationMessage.timestamp.desc()).first()
                    
                    next_msg = session.query(ConversationMessage).filter(
                        ConversationMessage.session_id == msg.session_id,
                        ConversationMessage.timestamp > msg.timestamp
                    ).order_by(ConversationMessage.timestamp.asc()).first()
                    
                    results.append({
                        'id': msg.id,
                        'session_id': msg.session_id,
                        'timestamp': msg.timestamp.isoformat(),
                        'source': 'direct_feedback',
                        
                        # Contexto ANTERIOR
                        'previous_user_message': prev_msg.user_message if prev_msg else None,
                        'previous_bot_response': prev_msg.bot_response if prev_msg else None,
                        'previous_intent': prev_msg.intent_detected if prev_msg else None,
                        
                        # Mensaje con FEEDBACK NEGATIVO
                        'problematic_message': msg.user_message,
                        'bot_response': msg.bot_response,
                        'intent_detected': msg.intent_detected or 'No detectado',
                        'confidence': msg.confidence or 0.0,
                        
                        # Contexto POSTERIOR
                        'next_user_message': next_msg.user_message if next_msg else None,
                        'next_bot_response': next_msg.bot_response if next_msg else None,
                        'next_intent': next_msg.intent_detected if next_msg else None,
                        
                        # Feedback
                        'feedback_type': 'thumbs_down',
                        'feedback_comment': msg.feedback_comment,
                        'suggested_intent': None,
                        'suggested_training_example': None
                    })
                
                # 2. Obtener también desde conversation_context_enhanced
                auto_captured = session.query(ConversationContextCapture).filter(
                    ConversationContextCapture.feedback_type == 'thumbs_down',
                    ConversationContextCapture.resolved == False
                ).order_by(ConversationContextCapture.timestamp.desc()).limit(limit).all()
                
                for ctx in auto_captured:
                    results.append({
                        'id': ctx.id,
                        'session_id': ctx.session_id,
                        'timestamp': ctx.timestamp.isoformat(),
                        'source': 'auto_captured',
                        
                        # Contexto ANTERIOR
                        'previous_user_message': ctx.previous_user_message,
                        'previous_bot_response': ctx.previous_bot_response,
                        'previous_intent': ctx.previous_intent,
                        
                        # Mensaje PROBLEMÁTICO
                        'problematic_message': ctx.problematic_message,
                        'bot_response': ctx.bot_response,
                        'intent_detected': ctx.intent_detected,
                        'confidence': ctx.confidence,
                        
                        # Contexto POSTERIOR
                        'next_user_message': ctx.next_user_message,
                        'next_bot_response': ctx.next_bot_response,
                        'next_intent': ctx.next_intent,
                        
                        # Feedback y sugerencias
                        'feedback_type': ctx.feedback_type,
                        'feedback_comment': ctx.feedback_comment,
                        'suggested_intent': ctx.suggested_intent,
                        'suggested_training_example': ctx.suggested_training_example
                    })
                
                # Ordenar por timestamp
                results.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return results[:limit]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo mensajes con feedback negativo: {e}")
            return []
    def get_model_efficiency_stats(self, days: int = 7) -> List[Dict]:
        """
        ✅ OBTIENE estadísticas de eficiencia para el dashboard
        """
        try:
            with self.get_db_session() as session:
                start_date = datetime.utcnow().date() - timedelta(days=days)
                
                stats = session.query(ModelEfficiencyStats).filter(
                    ModelEfficiencyStats.date >= start_date
                ).order_by(ModelEfficiencyStats.date.desc()).all()
                
                return [{
                    'date': s.date.isoformat(),
                    'total_interactions': s.total_interactions,
                    'successful_interactions': s.successful_interactions,
                    'failed_interactions': s.failed_interactions,
                    'success_rate': round(s.success_rate, 2),
                    'fallback_rate': round(s.fallback_rate, 2),
                    'user_satisfaction': round(s.user_satisfaction, 2),
                    'overall_efficiency': round(s.overall_efficiency, 2)
                } for s in stats]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de eficiencia: {e}")
            return []
    
    def get_overall_efficiency_summary(self) -> Dict:
        """
        ✅ OBTIENE resumen general de eficiencia para mostrar en dashboard
        Media de todas las conversaciones
        """
        try:
            with self.get_db_session() as session:
                # Obtener estadísticas de los últimos 30 días
                start_date = datetime.utcnow().date() - timedelta(days=30)
                
                stats = session.query(ModelEfficiencyStats).filter(
                    ModelEfficiencyStats.date >= start_date
                ).all()
                
                if not stats:
                    return {
                        'avg_success_rate': 0.0,
                        'avg_satisfaction': 0.0,
                        'total_feedbacks': 0,
                        'positive_feedbacks': 0,
                        'negative_feedbacks': 0,
                        'overall_efficiency': 0.0
                    }
                
                total_interactions = sum(s.total_interactions for s in stats)
                total_positive = sum(s.successful_interactions for s in stats)
                total_negative = sum(s.failed_interactions for s in stats)
                
                avg_success_rate = sum(s.success_rate for s in stats) / len(stats)
                avg_satisfaction = sum(s.user_satisfaction for s in stats if s.user_satisfaction is not None) / len(stats)
                avg_efficiency = sum(s.overall_efficiency for s in stats) / len(stats)
                
                return {
                    'avg_success_rate': round(avg_success_rate, 2),
                    'avg_satisfaction': round(avg_satisfaction, 2),
                    'total_feedbacks': total_positive + total_negative,
                    'positive_feedbacks': total_positive,
                    'negative_feedbacks': total_negative,
                    'overall_efficiency': round(avg_efficiency, 2)
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de eficiencia: {e}")
            return {}
    
    def mark_context_as_resolved(self, context_id: int, admin_notes: str = None) -> bool:
        """Marca un contexto como resuelto"""
        try:
            with self.get_db_session() as session:
                context = session.query(ConversationContextCapture).filter_by(id=context_id).first()
                if context:
                    context.resolved = True
                    context.admin_notes = admin_notes
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error marcando contexto como resuelto: {e}")
            return False
    
    def get_summary_stats(self, days: int = 7) -> Dict:
        """Obtiene estadísticas resumidas para el dashboard"""
        try:
            with self.get_db_session() as session:
                start_date = datetime.utcnow().date() - timedelta(days=days)
                
                # Obtener stats del sistema
                stats = session.query(SystemStats).filter(
                    SystemStats.date >= start_date
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
                
                return {
                    'total_conversations': sum(s.total_messages for s in stats),
                    'avg_confidence': round(sum(s.avg_confidence for s in stats) / len(stats), 3),
                    'needs_review': sum(s.needs_review_count for s in stats),
                    'positive_feedback': sum(s.positive_feedback for s in stats),
                    'negative_feedback': sum(s.negative_feedback for s in stats),
                    'satisfaction_rate': round(sum(s.satisfaction_rate for s in stats) / len(stats), 1)
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas resumidas: {e}")
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
    
    def mark_as_reviewed(self, message_id: int) -> bool:
        """Marca un mensaje como revisado"""
        try:
            with self.get_db_session() as session:
                message = session.query(ConversationMessage).filter_by(id=message_id).first()
                if message:
                    message.reviewed = True
                    message.needs_review = False
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error marcando como revisado: {e}")
            return False
    
    def _cleanup_old_data(self):
        """Limpia datos antiguos (>30 días)"""
        try:
            with self.get_db_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                # Limpiar mensajes antiguos ya revisados
                session.query(ConversationMessage).filter(
                    ConversationMessage.timestamp < cutoff_date,
                    ConversationMessage.reviewed == True
                ).delete()
                
                # Limpiar contextos resueltos antiguos
                session.query(ConversationContextCapture).filter(
                    ConversationContextCapture.timestamp < cutoff_date,
                    ConversationContextCapture.resolved == True
                ).delete()
                
                self.logger.info("🧹 Limpieza de datos antiguos completada")
                
        except Exception as e:
            self.logger.error(f"Error en limpieza de datos: {e}")


# =====================================================
# FUNCIONES DE INTEGRACIÓN CON RASA
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
        
        # ✅ AUTO-CAPTURAR CONTEXTO si es problemático
        if intent_detected == 'nlu_fallback' or confidence < 0.7:
            logger_instance.capture_conversation_context(
                session_id=session_id,
                problematic_message=user_message,
                bot_response=bot_response,
                intent_detected=intent_detected,
                confidence=confidence,
                feedback_type='low_confidence' if confidence < 0.7 else 'fallback'
            )
        
        return message_id
        
    except Exception as e:
        logger.error(f"❌ Error en log mejorado: {e}")
        return -1

DATABASE_URL = "postgresql://botuser:root@localhost:5432/chatbotdb"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def save_user_correction(session_id, user_message, bot_response, corrected_response):
    """Guarda una corrección de respuesta del usuario"""
    try:
        with engine.connect() as conn:
            conn.execute("""
                INSERT INTO feedback_training_data (session_id, user_message, bot_response, corrected_response, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (session_id, user_message, bot_response, corrected_response))
        print(f"✅ Corrección guardada: {user_message[:50]} → {corrected_response[:50]}")
    except Exception as e:
        print(f"❌ Error guardando corrección: {e}")


# Instancia global
_global_improved_logger = None

def get_improved_conversation_logger():
    """Obtiene la instancia global del logger mejorado"""
    return _global_improved_logger

def set_improved_conversation_logger(logger_instance):
    """Establece la instancia global del logger mejorado"""
    global _global_improved_logger
    _global_improved_logger = logger_instance
    
# =====================================================
# COMPATIBILIDAD CON app.py - Alias de log_interaction_improved
# =====================================================

def log_interaction_improved(session_id: str, user_message: str, bot_response: str,
                             intent_name: str = None, confidence: float = 0.0):
    """
    Función de compatibilidad para app.py.
    Registra una interacción simple en la BD usando ImprovedConversationLogger.
    """
    try:
        logger_instance = get_improved_conversation_logger()
        if not logger_instance:
            print("⚠️ Logger no inicializado aún (log_interaction_improved)")
            return
        
        logger_instance.log_message(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            intent_detected=intent_name,
            confidence=confidence
        )
    except Exception as e:
        print(f"⚠️ Error en log_interaction_improved: {e}")



