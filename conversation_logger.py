"""
Sistema de logging y aprendizaje para el chatbot de turnos
Registra conversaciones, análisis difusos y métricas de rendimiento
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Boolean, Text, JSON, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# =====================================================
# MODELOS DE BASE DE DATOS PARA APRENDIZAJE
# =====================================================

class ConversationLog(Base):
    """Registro de todas las conversaciones"""
    __tablename__ = 'conversation_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)  # No permitir NULL
    bot_response = Column(Text, nullable=False)
    intent_detected = Column(String(100))
    confidence = Column(Float, default=0.0)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
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
    analysis_type = Column(String(50))  # 'recommendation', 'availability', etc.
    analysis_data = Column(JSON)  # Datos del análisis difuso
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
# CLASE PRINCIPAL DEL LOGGER
# =====================================================

class ConversationLogger:
    """Maneja el logging y análisis de conversaciones"""
    
    def __init__(self, database_url: str):
        """Inicializa el logger con conexión a BD"""
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Crear tablas si no existen
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("Tablas de aprendizaje verificadas/creadas")
        except Exception as e:
            self.logger.error(f"Error creando tablas de aprendizaje: {e}")
    
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
                        response_time_ms: int = None) -> bool:
        """Registra una conversación completa"""
        try:
            # Validar que user_message no sea None o vacío
            if not user_message:
                user_message = "Mensaje del usuario no disponible"
            
            # Procesar patrones de palabras para análisis
            sentiment_keywords = self._extract_sentiment_keywords(user_message)
            
            log_entry = ConversationLog(
                session_id=session_id,
                user_message=user_message,
                bot_response=bot_response,
                intent_detected=intent_detected,
                confidence=confidence,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time_ms
            )
            
            with self.get_db_session() as session:
                session.add(log_entry)
                
            self.logger.info(f"Conversación registrada para sesión {session_id}")
            
            # Actualizar métricas de intent
            self._update_intent_metrics(intent_detected, confidence)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging conversación: {e}")
            return False
    
    def log_fuzzy_analysis(self, session_id: str, user_query: str, 
                          analysis_type: str, analysis_data: Dict, 
                          processing_time_ms: int = None) -> bool:
        """Registra análisis específico del motor difuso"""
        try:
            # Validar user_query
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
                
            self.logger.info(f"Análisis difuso registrado: {analysis_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging análisis difuso: {e}")
            return False
    
    def _extract_sentiment_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave de sentimiento del texto"""
        if not text or not isinstance(text, str):
            return []
        
        try:
            text_lower = text.lower()
            
            positive_words = ['bueno', 'excelente', 'perfecto', 'gracias', 'bien', 'genial', 'fantástico']
            negative_words = ['mal', 'error', 'problema', 'no funciona', 'difícil', 'confuso', 'lento']
            
            found_keywords = []
            for word in positive_words + negative_words:
                if word in text_lower:
                    found_keywords.append(word)
            
            return found_keywords
            
        except Exception as e:
            self.logger.error(f"Error procesando patrones de palabras: {e}")
            return []
    
    def _update_intent_metrics(self, intent_name: str, confidence: float):
        """Actualiza métricas de rendimiento por intent"""
        if not intent_name:
            return
        
        try:
            with self.get_db_session() as session:
                # Buscar intent existente
                analysis = session.query(IntentAnalysis).filter_by(intent_name=intent_name).first()
                
                if analysis:
                    # Actualizar existente
                    analysis.total_uses += 1
                    new_avg = ((analysis.avg_confidence * (analysis.total_uses - 1)) + confidence) / analysis.total_uses
                    analysis.avg_confidence = new_avg
                    analysis.last_updated = datetime.utcnow()
                    
                    # Marcar si necesita más ejemplos (confianza baja)
                    analysis.examples_needed = new_avg < 0.7
                else:
                    # Crear nuevo
                    analysis = IntentAnalysis(
                        intent_name=intent_name,
                        total_uses=1,
                        avg_confidence=confidence,
                        examples_needed=confidence < 0.7
                    )
                    session.add(analysis)
                    
        except Exception as e:
            self.logger.error(f"Error actualizando métricas de intent: {e}")
    
    def get_daily_stats(self, date: datetime = None) -> Dict[str, Any]:
        """Obtiene estadísticas del día"""
        if not date:
            date = datetime.now().date()
        
        try:
            with self.get_db_session() as session:
                start_date = datetime.combine(date, datetime.min.time())
                end_date = start_date + timedelta(days=1)
                
                # Conversaciones del día
                conversations = session.query(ConversationLog).filter(
                    ConversationLog.timestamp >= start_date,
                    ConversationLog.timestamp < end_date
                ).all()
                
                # Análisis difusos del día
                fuzzy_analyses = session.query(FuzzyAnalysisLog).filter(
                    FuzzyAnalysisLog.timestamp >= start_date,
                    FuzzyAnalysisLog.timestamp < end_date
                ).all()
                
                # Calcular estadísticas
                total_conversations = len(conversations)
                unique_sessions = len(set(conv.session_id for conv in conversations))
                avg_confidence = sum(conv.confidence for conv in conversations) / max(1, total_conversations)
                
                response_times = [conv.response_time_ms for conv in conversations if conv.response_time_ms]
                avg_response_time = sum(response_times) / max(1, len(response_times)) if response_times else 0
                
                return {
                    'date': date.isoformat(),
                    'total_conversations': total_conversations,
                    'unique_sessions': unique_sessions,
                    'fuzzy_activations': len(fuzzy_analyses),
                    'avg_confidence': round(avg_confidence, 3),
                    'avg_response_time_ms': round(avg_response_time, 2)
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas diarias: {e}")
            return {}
    
    def get_intent_performance(self) -> List[Dict[str, Any]]:
        """Obtiene rendimiento de todos los intents"""
        try:
            with self.get_db_session() as session:
                analyses = session.query(IntentAnalysis).all()
                
                return [{
                    'intent_name': analysis.intent_name,
                    'total_uses': analysis.total_uses,
                    'avg_confidence': round(analysis.avg_confidence, 3),
                    'success_rate': round(analysis.success_rate, 3),
                    'examples_needed': analysis.examples_needed,
                    'last_updated': analysis.last_updated.isoformat() if analysis.last_updated else None
                } for analysis in analyses]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo rendimiento de intents: {e}")
            return []
    
    def get_recent_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene conversaciones recientes"""
        try:
            with self.get_db_session() as session:
                conversations = session.query(ConversationLog)\
                    .order_by(ConversationLog.timestamp.desc())\
                    .limit(limit).all()
                
                return [{
                    'id': conv.id,
                    'session_id': conv.session_id,
                    'user_message': conv.user_message,
                    'bot_response': conv.bot_response[:200] + '...' if len(conv.bot_response) > 200 else conv.bot_response,
                    'intent_detected': conv.intent_detected,
                    'confidence': round(conv.confidence, 3),
                    'timestamp': conv.timestamp.isoformat(),
                    'response_time_ms': conv.response_time_ms
                } for conv in conversations]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo conversaciones recientes: {e}")
            return []
    
    def get_fuzzy_analysis_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del motor difuso"""
        try:
            with self.get_db_session() as session:
                # Análisis de los últimos 7 días
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                analyses = session.query(FuzzyAnalysisLog).filter(
                    FuzzyAnalysisLog.timestamp >= week_ago
                ).all()
                
                if not analyses:
                    return {'total_analyses': 0, 'avg_processing_time': 0, 'analysis_types': {}}
                
                # Estadísticas generales
                total_analyses = len(analyses)
                processing_times = [a.processing_time_ms for a in analyses if a.processing_time_ms]
                avg_processing_time = sum(processing_times) / max(1, len(processing_times))
                
                # Tipos de análisis
                analysis_types = {}
                for analysis in analyses:
                    analysis_type = analysis.analysis_type or 'unknown'
                    analysis_types[analysis_type] = analysis_types.get(analysis_type, 0) + 1
                
                return {
                    'total_analyses': total_analyses,
                    'avg_processing_time_ms': round(avg_processing_time, 2),
                    'analysis_types': analysis_types,
                    'period_days': 7
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas difusas: {e}")
            return {}
    
    # =====================================================
    # MÉTODOS ADICIONALES PARA EL DASHBOARD
    # =====================================================
    
    def get_conversation_stats(self, days: int = 7) -> Dict[str, Any]:
        """Obtiene estadísticas de conversaciones de los últimos N días"""
        try:
            with self.get_db_session() as session:
                # Calcular fecha límite
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # Consultar conversaciones
                conversations = session.query(ConversationLog).filter(
                    ConversationLog.timestamp >= start_date
                ).all()
                
                if not conversations:
                    return {
                        'total_conversations': 0,
                        'unique_sessions': 0,
                        'avg_confidence': 0.0,
                        'intents_distribution': {},
                        'daily_counts': [],
                        'avg_response_time': 0.0
                    }
                
                # Estadísticas generales
                total_conversations = len(conversations)
                unique_sessions = len(set(conv.session_id for conv in conversations))
                
                # Promedio de confianza
                confidences = [conv.confidence for conv in conversations if conv.confidence]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                # Tiempo de respuesta promedio
                response_times = [conv.response_time_ms for conv in conversations if conv.response_time_ms]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
                
                # Distribución de intents
                intents_distribution = {}
                for conv in conversations:
                    intent = conv.intent_detected or 'unknown'
                    intents_distribution[intent] = intents_distribution.get(intent, 0) + 1
                
                # Conteos diarios
                daily_counts = []
                for i in range(days):
                    day = start_date + timedelta(days=i)
                    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                    day_end = day_start + timedelta(days=1)
                    
                    day_conversations = [
                        conv for conv in conversations 
                        if day_start <= conv.timestamp < day_end
                    ]
                    
                    daily_counts.append({
                        'date': day.strftime('%Y-%m-%d'),
                        'count': len(day_conversations)
                    })
                
                return {
                    'total_conversations': total_conversations,
                    'unique_sessions': unique_sessions,
                    'avg_confidence': round(avg_confidence, 3),
                    'intents_distribution': intents_distribution,
                    'daily_counts': daily_counts,
                    'avg_response_time': round(avg_response_time, 2),
                    'period_days': days
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de conversación: {e}")
            return {}
    
    def get_all_conversations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene todas las conversaciones con límite - Versión corregida"""
        try:
            with self.get_db_session() as session:
                conversations = session.query(ConversationLog)\
                    .order_by(ConversationLog.timestamp.desc())\
                    .limit(limit).all()
                
                return [{
                    'id': conv.id,
                    'session_id': conv.session_id,
                    'user_message': conv.user_message,
                    'bot_response': conv.bot_response,
                    'intent_detected': conv.intent_detected,
                    'confidence': conv.confidence,
                    'timestamp': conv.timestamp.isoformat(),
                    'response_time_ms': conv.response_time_ms,
                    'feedback_score': getattr(conv, 'feedback_score', None),  # Manejar campo faltante
                    'was_helpful': getattr(conv, 'was_helpful', None)
                } for conv in conversations]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo todas las conversaciones: {e}")
            return []

    def get_failed_interactions(self, limit: int = 50, interaction_type: str = None) -> List[Dict[str, Any]]:
        """Obtiene interacciones que fallaron - Versión completamente compatible con dashboard"""
        try:
            with self.get_db_session() as session:
                results = []
                
                if interaction_type == 'unknown_phrases':
                    # Frases sin intent o con confianza muy baja
                    failed_conversations = session.query(ConversationLog).filter(
                        (ConversationLog.intent_detected.is_(None)) |
                        (ConversationLog.intent_detected == '') |
                        (ConversationLog.confidence < 0.3)
                    ).order_by(ConversationLog.timestamp.desc()).limit(limit).all()
                    
                elif interaction_type == 'negative_feedback':
                    # Conversaciones con feedback negativo - manejo cuidadoso de NULL
                    failed_conversations = session.query(ConversationLog).filter(
                        (ConversationLog.was_helpful == False) |
                        ((ConversationLog.feedback_score.isnot(None)) & (ConversationLog.feedback_score < 3))
                    ).order_by(ConversationLog.timestamp.desc()).limit(limit).all()
                    
                else:
                    # Comportamiento por defecto: baja confianza
                    failed_conversations = session.query(ConversationLog).filter(
                        ConversationLog.confidence < 0.6
                    ).order_by(ConversationLog.timestamp.desc()).limit(limit).all()
                
                # Convertir TODOS los resultados al formato correcto
                for conv in failed_conversations:
                    # Asegurar que todos los campos estén presentes y tengan valores válidos
                    result = {
                        'id': conv.id,
                        'session_id': conv.session_id or 'unknown',
                        'phrase': conv.user_message or "Mensaje vacío",
                        'user_message': conv.user_message or "Mensaje vacío", 
                        'bot_response': (conv.bot_response[:100] + '...') if conv.bot_response and len(conv.bot_response) > 100 else (conv.bot_response or "Sin respuesta"),
                        'intent_detected': conv.intent_detected or 'no_intent',
                        'confidence': round(float(conv.confidence or 0.0), 3),
                        'timestamp': conv.timestamp.isoformat() if conv.timestamp else datetime.utcnow().isoformat(),
                        'failure_reason': self._get_failure_reason(conv, interaction_type),
                        # CRÍTICO: Asegurar que estos campos SIEMPRE existan
                        'feedback_score': getattr(conv, 'feedback_score', None),
                        'was_helpful': getattr(conv, 'was_helpful', None)
                    }
                    results.append(result)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error obteniendo interacciones fallidas: {e}")
            return []

    def get_word_patterns(self, limit: int = 100, category: str = None, pattern_type: str = 'words') -> List[tuple]:
        """Devuelve patrones como lista de tuplas para el dashboard - Versión ultra robusta"""
        try:
            with self.get_db_session() as session:
                query = session.query(ConversationLog).order_by(ConversationLog.timestamp.desc())
                
                # Filtrar por categoría si se especifica
                if category and category not in ['all', 'word', 'phrase', None]:
                    query = query.filter(ConversationLog.intent_detected == category)
                
                conversations = query.limit(limit).all()
                
                if not conversations:
                    return []
                
                # Determinar qué tipo de análisis hacer
                if category == 'phrase' or pattern_type == 'phrases':
                    return self._get_phrase_patterns_as_tuples(conversations)
                else:
                    return self._get_word_patterns_as_tuples(conversations)
                
        except Exception as e:
            self.logger.error(f"Error obteniendo patrones como tuplas: {e}")
            return []
    
    def _get_word_patterns_as_tuples(self, conversations) -> List[tuple]:
        """Devuelve patrones de palabras como tuplas - Garantizando tipos correctos"""
        word_count = {}
        word_intents = {}
        
        stop_words = {'para', 'con', 'por', 'que', 'una', 'del', 'las', 'los', 'como', 'esto', 'esta', 'este', 'son', 'más'}
        
        for conv in conversations:
            if conv.user_message and len(conv.user_message.strip()) > 0:
                words = conv.user_message.lower().split()
                for word in words:
                    clean_word = word.strip('.,!?;:"()[]{}').lower()
                    if len(clean_word) > 2 and clean_word.isalpha() and clean_word not in stop_words:
                        word_count[clean_word] = word_count.get(clean_word, 0) + 1
                        
                        if clean_word not in word_intents:
                            word_intents[clean_word] = {}
                        
                        intent = conv.intent_detected or 'unknown'
                        word_intents[clean_word][intent] = word_intents[clean_word].get(intent, 0) + 1
        
        # Convertir a tuplas con tipos garantizados
        results = []
        try:
            # Ordenar de forma segura
            sorted_words = []
            for word, count in word_count.items():
                if isinstance(word, str) and isinstance(count, int):
                    sorted_words.append((word, count))
            
            # Ordenar por frecuencia
            sorted_words.sort(key=lambda x: x[1], reverse=True)
            
            for word, count in sorted_words[:50]:
                # Encontrar el intent más común para esta palabra
                main_intent = 'unknown'
                if word in word_intents and word_intents[word]:
                    try:
                        intent_counts = [(intent, cnt) for intent, cnt in word_intents[word].items() if isinstance(cnt, int)]
                        if intent_counts:
                            main_intent = max(intent_counts, key=lambda x: x[1])[0]
                    except (ValueError, TypeError):
                        main_intent = 'unknown'
                
                # Garantizar que todos los elementos de la tupla sean del tipo correcto
                results.append((
                    str(word),           # palabra como string
                    int(count),          # frecuencia como int
                    str(main_intent),    # intent como string  
                    str('word')          # categoría como string
                ))
        
        except Exception as e:
            self.logger.error(f"Error procesando patrones de palabras: {e}")
            return []
        
        return results
    
    def _get_phrase_patterns_as_tuples(self, conversations) -> List[tuple]:
        """Devuelve patrones de frases como tuplas - Garantizando tipos correctos"""
        phrase_count = {}
        phrase_intents = {}
        
        for conv in conversations:
            if conv.user_message and len(conv.user_message.strip()) > 5:
                phrase = conv.user_message.lower().strip()
                # Limpiar la frase
                phrase = phrase[:100]  # Limitar longitud
                
                phrase_count[phrase] = phrase_count.get(phrase, 0) + 1
                
                if phrase not in phrase_intents:
                    phrase_intents[phrase] = {}
                
                intent = conv.intent_detected or 'unknown'
                phrase_intents[phrase][intent] = phrase_intents[phrase].get(intent, 0) + 1
        
        # Convertir a tuplas con tipos garantizados
        results = []
        try:
            # Ordenar de forma segura
            sorted_phrases = []
            for phrase, count in phrase_count.items():
                if isinstance(phrase, str) and isinstance(count, int) and count > 1:  # Solo frases que aparecen más de una vez
                    sorted_phrases.append((phrase, count))
            
            # Ordenar por frecuencia
            sorted_phrases.sort(key=lambda x: x[1], reverse=True)
            
            for phrase, count in sorted_phrases[:30]:
                # Encontrar el intent más común
                main_intent = 'unknown'
                if phrase in phrase_intents and phrase_intents[phrase]:
                    try:
                        intent_counts = [(intent, cnt) for intent, cnt in phrase_intents[phrase].items() if isinstance(cnt, int)]
                        if intent_counts:
                            main_intent = max(intent_counts, key=lambda x: x[1])[0]
                    except (ValueError, TypeError):
                        main_intent = 'unknown'
                
                # Garantizar tipos correctos en la tupla
                results.append((
                    str(phrase),         # frase como string
                    int(count),          # frecuencia como int
                    str(main_intent),    # intent como string
                    str('phrase')        # categoría como string
                ))
        
        except Exception as e:
            self.logger.error(f"Error procesando patrones de frases: {e}")
            return []
        
        return results
    
    def _get_failure_reason(self, conv, interaction_type):
        """Determina la razón del fallo basado en el tipo y datos de la conversación"""
        if interaction_type == 'unknown_phrases':
            if not conv.intent_detected:
                return 'Sin intent detectado'
            elif conv.confidence < 0.3:
                return 'Confianza muy baja'
            else:
                return 'Frase no entendida'
        elif interaction_type == 'negative_feedback':
            return 'Feedback negativo del usuario'
        else:
            return 'Baja confianza' if conv.confidence < 0.6 else 'Interacción fallida'

    def get_word_patterns(self, limit: int = 100, category: str = None, pattern_type: str = 'words') -> Dict[str, Any]:
        """Analiza patrones - Versión ultra robusta"""
        try:
            with self.get_db_session() as session:
                # Obtener mensajes recientes
                query = session.query(ConversationLog).order_by(ConversationLog.timestamp.desc())
                
                # Filtrar por categoría si se especifica y no es 'all'
                if category and category != 'all' and category.strip():
                    query = query.filter(ConversationLog.intent_detected == category)
                
                conversations = query.limit(limit).all()
                
                if not conversations:
                    return self._empty_patterns_response(pattern_type)
                
                # Procesar según el tipo
                if pattern_type == 'phrases':
                    return self._analyze_phrases(conversations)
                else:
                    return self._analyze_words(conversations, category)
                
        except Exception as e:
            self.logger.error(f"Error analizando patrones: {e}")
            return self._empty_patterns_response(pattern_type)
    
    def _empty_patterns_response(self, pattern_type):
        """Respuesta vacía consistente"""
        base_response = {
            'common_words': {},
            'intent_keywords': {},
            'total_messages_analyzed': 0,
            'pattern_type': pattern_type
        }
        
        if pattern_type == 'phrases':
            base_response.update({
                'common_phrases': {},
                'phrase_frequency': []
            })
        else:
            base_response.update({
                'word_frequency': []
            })
        
        return base_response
    
    def _analyze_phrases(self, conversations):
        """Analiza patrones de frases"""
        phrase_count = {}
        
        for conv in conversations:
            if conv.user_message and len(conv.user_message.strip()) > 5:
                phrase = conv.user_message.lower().strip()
                # Limpiar la frase
                phrase = phrase.strip('.,!?;:"()[]{}')
                if phrase and len(phrase) > 5:
                    phrase_count[phrase] = phrase_count.get(phrase, 0) + 1
        
        # Convertir a lista ordenada de forma segura
        try:
            sorted_phrases = sorted(phrase_count.items(), key=lambda x: int(x[1]), reverse=True)
            common_phrases = dict(sorted_phrases[:20])
            phrase_frequency = [
                {'phrase': phrase, 'count': int(count)} 
                for phrase, count in sorted_phrases[:20]
            ]
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error ordenando frases: {e}")
            common_phrases = {}
            phrase_frequency = []
        
        return {
            'common_phrases': common_phrases,
            'phrase_frequency': phrase_frequency,
            'total_messages_analyzed': len(conversations),
            'pattern_type': 'phrases'
        }
    
    def _analyze_words(self, conversations, category):
        """Analiza patrones de palabras"""
        word_count = {}
        intent_keywords = {}
        
        stop_words = {
            'para', 'con', 'por', 'que', 'una', 'del', 'las', 'los', 'como',
            'esto', 'esta', 'este', 'son', 'más', 'muy', 'todo', 'cada',
            'pero', 'sin', 'sobre', 'también', 'hasta', 'donde', 'cuando'
        }
        
        for conv in conversations:
            if conv.user_message and len(conv.user_message.strip()) > 0:
                words = conv.user_message.lower().split()
                
                for word in words:
                    # Limpiar palabra
                    clean_word = word.strip('.,!?;:"()[]{}')
                    
                    # Filtrar palabras válidas
                    if (len(clean_word) > 2 and 
                        clean_word not in stop_words and 
                        clean_word.isalpha()):
                        
                        word_count[clean_word] = word_count.get(clean_word, 0) + 1
                        
                        # Asociar con intent
                        if conv.intent_detected:
                            if conv.intent_detected not in intent_keywords:
                                intent_keywords[conv.intent_detected] = {}
                            intent_keywords[conv.intent_detected][clean_word] = intent_keywords[conv.intent_detected].get(clean_word, 0) + 1
        
        # Convertir a listas ordenadas de forma segura
        try:
            sorted_words = sorted(word_count.items(), key=lambda x: int(x[1]), reverse=True)
            common_words = dict(sorted_words[:20])
            word_frequency = [
                {'word': word, 'count': int(count)} 
                for word, count in sorted_words[:20]
            ]
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error ordenando palabras: {e}")
            common_words = {}
            word_frequency = []
        
        # Procesar keywords por intent
        for intent in intent_keywords:
            try:
                sorted_intent_words = sorted(intent_keywords[intent].items(), key=lambda x: int(x[1]), reverse=True)
                intent_keywords[intent] = dict(sorted_intent_words[:10])
            except (ValueError, TypeError):
                intent_keywords[intent] = {}
        
        return {
            'common_words': common_words,
            'word_frequency': word_frequency,
            'intent_keywords': intent_keywords,
            'total_messages_analyzed': len(conversations),
            'pattern_type': 'words',
            'category_filter': category
        }
    
    def get_intent_stats(self) -> List[Dict[str, Any]]:
        """Obtiene estadísticas de rendimiento por intent"""
        try:
            with self.get_db_session() as session:
                # Obtener datos de conversation_logs agrupados por intent
                intent_stats = session.query(
                    ConversationLog.intent_detected,
                    func.count(ConversationLog.id).label('total_uses'),
                    func.avg(ConversationLog.confidence).label('avg_confidence')
                ).filter(
                    ConversationLog.intent_detected.isnot(None),
                    ConversationLog.intent_detected != ''
                ).group_by(ConversationLog.intent_detected).all()
                
                results = []
                for intent, uses, confidence in intent_stats:
                    results.append({
                        'intent': intent,
                        'uses': uses,
                        'avg_confidence': round(confidence or 0.0, 3)
                    })
                
                return sorted(results, key=lambda x: x['uses'], reverse=True)
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de intents: {e}")
            return []
    
    def get_fuzzy_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del motor difuso"""
        try:
            with self.get_db_session() as session:
                # Análisis de los últimos 7 días
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                analyses = session.query(FuzzyAnalysisLog).filter(
                    FuzzyAnalysisLog.timestamp >= week_ago
                ).all()
                
                if not analyses:
                    return {
                        'total_analyses': 0,
                        'avg_processing_time': 0.0,
                        'analysis_types': {}
                    }
                
                # Estadísticas generales
                total_analyses = len(analyses)
                processing_times = [a.processing_time_ms for a in analyses if a.processing_time_ms]
                avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
                
                # Tipos de análisis
                analysis_types = {}
                for analysis in analyses:
                    analysis_type = analysis.analysis_type or 'unknown'
                    analysis_types[analysis_type] = analysis_types.get(analysis_type, 0) + 1
                
                return {
                    'total_analyses': total_analyses,
                    'avg_processing_time': round(avg_processing_time, 2),
                    'analysis_types': analysis_types
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas difusas: {e}")
            return {}

    def get_failed_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene interacciones que fallaron o tuvieron baja confianza"""
        try:
            with self.get_db_session() as session:
                # Conversaciones con confianza baja (< 0.6)
                failed_conversations = session.query(ConversationLog)\
                    .filter(ConversationLog.confidence < 0.6)\
                    .order_by(ConversationLog.timestamp.desc())\
                    .limit(limit).all()
                
                return [{
                    'id': conv.id,
                    'session_id': conv.session_id,
                    'user_message': conv.user_message,
                    'bot_response': conv.bot_response[:100] + '...' if len(conv.bot_response) > 100 else conv.bot_response,
                    'intent_detected': conv.intent_detected or 'no_intent',
                    'confidence': round(conv.confidence, 3),
                    'timestamp': conv.timestamp.isoformat(),
                    'failure_reason': 'Baja confianza' if conv.confidence < 0.6 else 'Sin intent detectado'
                } for conv in failed_conversations]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo interacciones fallidas: {e}")
            return []

    def get_word_patterns(self, limit: int = 100) -> Dict[str, Any]:
        """Analiza patrones de palabras en las conversaciones"""
        try:
            with self.get_db_session() as session:
                # Obtener mensajes recientes
                conversations = session.query(ConversationLog)\
                    .order_by(ConversationLog.timestamp.desc())\
                    .limit(limit).all()
                
                if not conversations:
                    return {'common_words': {}, 'intent_keywords': {}}
                
                # Análisis de palabras comunes
                word_count = {}
                intent_keywords = {}
                
                for conv in conversations:
                    if conv.user_message:
                        words = conv.user_message.lower().split()
                        # Filtrar palabras comunes y cortas
                        filtered_words = [
                            word.strip('.,!?;:"()[]{}')
                            for word in words
                            if len(word) > 3 and word not in ['para', 'con', 'por', 'que', 'una', 'del', 'las', 'los', 'como']
                        ]
                        
                        for word in filtered_words:
                            word_count[word] = word_count.get(word, 0) + 1
                            
                            # Asociar palabras con intents
                            if conv.intent_detected:
                                if conv.intent_detected not in intent_keywords:
                                    intent_keywords[conv.intent_detected] = {}
                                intent_keywords[conv.intent_detected][word] = intent_keywords[conv.intent_detected].get(word, 0) + 1
                
                # Top 20 palabras más comunes
                common_words = dict(sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:20])
                
                # Top palabras por intent
                for intent in intent_keywords:
                    intent_keywords[intent] = dict(sorted(intent_keywords[intent].items(), key=lambda x: x[1], reverse=True)[:10])
                
                return {
                    'common_words': common_words,
                    'intent_keywords': intent_keywords,
                    'total_messages_analyzed': len(conversations)
                }
                
        except Exception as e:
            self.logger.error(f"Error analizando patrones de palabras: {e}")
            return {'common_words': {}, 'intent_keywords': {}}

    def generate_training_suggestions(self) -> List[Dict[str, Any]]:
        """Genera sugerencias para mejorar el entrenamiento"""
        try:
            suggestions = []
            
            # Analizar intents con baja confianza
            intent_stats = self.get_intent_stats()
            for intent_data in intent_stats:
                if intent_data['avg_confidence'] < 0.7:
                    suggestions.append({
                        'type': 'low_confidence_intent',
                        'priority': 'alta' if intent_data['avg_confidence'] < 0.5 else 'media',
                        'title': f"Intent '{intent_data['intent']}' tiene baja confianza",
                        'description': f"Confianza promedio: {intent_data['avg_confidence']:.3f}",
                        'recommendation': f"Agregar más ejemplos de entrenamiento para el intent '{intent_data['intent']}'",
                        'examples_needed': max(5, 10 - intent_data['uses'])
                    })
            
            # Analizar interacciones fallidas
            failed_interactions = self.get_failed_interactions(20)
            if len(failed_interactions) > 5:
                suggestions.append({
                    'type': 'high_failure_rate',
                    'priority': 'alta',
                    'title': f"{len(failed_interactions)} interacciones recientes fallaron",
                    'description': "Alto número de mensajes con baja confianza o sin intent detectado",
                    'recommendation': "Revisar y agregar nuevos ejemplos para los casos fallidos",
                    'failed_count': len(failed_interactions)
                })
            
            # Analizar patrones de palabras
            word_patterns = self.get_word_patterns()
            common_words = word_patterns.get('common_words', {})
            if common_words:
                # Buscar palabras frecuentes que podrían necesitar nuevos intents
                frequent_words = [word for word, count in common_words.items() if count > 3]
                if len(frequent_words) > 0:
                    suggestions.append({
                        'type': 'new_vocabulary',
                        'priority': 'baja',
                        'title': "Nuevas palabras frecuentes detectadas",
                        'description': f"Palabras como '{', '.join(frequent_words[:5])}' aparecen con frecuencia",
                        'recommendation': "Considerar crear nuevos intents o expandir los existentes",
                        'new_words': frequent_words[:10]
                    })
            
            # Si no hay sugerencias, crear una positiva
            if not suggestions:
                suggestions.append({
                    'type': 'good_performance',
                    'priority': 'info',
                    'title': "Sistema funcionando correctamente",
                    'description': "No se detectaron problemas significativos",
                    'recommendation': "Continuar monitoreando el rendimiento",
                    'status': 'optimal'
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generando sugerencias: {e}")
            return [{
                'type': 'error',
                'priority': 'alta',
                'title': "Error generando sugerencias",
                'description': str(e),
                'recommendation': "Verificar la configuración del sistema de aprendizaje"
            }]

    def get_unknown_phrases(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene frases que el bot no pudo entender - Formato correcto para dashboard"""
        try:
            with self.get_db_session() as session:
                # Buscar conversaciones sin intent o con confianza muy baja
                unknown_conversations = session.query(ConversationLog).filter(
                    (ConversationLog.intent_detected.is_(None)) |
                    (ConversationLog.intent_detected == '') |
                    (ConversationLog.confidence < 0.3)
                ).order_by(ConversationLog.timestamp.desc()).limit(limit * 2).all()  # Obtener más para filtrar duplicados
                
                # Agrupar frases similares y contar frecuencia
                phrase_freq = {}
                phrase_details = {}
                
                for conv in unknown_conversations:
                    if conv.user_message and len(conv.user_message.strip()) > 3:
                        phrase = conv.user_message.lower().strip()
                        
                        if phrase not in phrase_freq:
                            phrase_freq[phrase] = 0
                            phrase_details[phrase] = {
                                'first_seen': conv.timestamp,
                                'last_seen': conv.timestamp,
                                'sessions': set()
                            }
                        
                        phrase_freq[phrase] += 1
                        phrase_details[phrase]['last_seen'] = max(phrase_details[phrase]['last_seen'], conv.timestamp)
                        phrase_details[phrase]['sessions'].add(conv.session_id)
                
                # Convertir a formato esperado por el dashboard
                results = []
                for phrase, frequency in sorted(phrase_freq.items(), key=lambda x: x[1], reverse=True)[:limit]:
                    details = phrase_details[phrase]
                    
                    results.append({
                        'id': hash(phrase) % 100000,  # ID único para la frase
                        'phrase': phrase,
                        'frequency': frequency,
                        'first_seen': details['first_seen'].isoformat(),
                        'last_seen': details['last_seen'].isoformat(),
                        'suggested_intent': self._suggest_intent_for_phrase(phrase),
                        'sessions_count': len(details['sessions'])
                    })
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error obteniendo frases desconocidas: {e}")
            return []
    
    def _suggest_intent_for_phrase(self, phrase: str) -> str:
        """Sugiere un intent basado en palabras clave en la frase"""
        phrase_lower = phrase.lower()
        
        # Mapeo de palabras clave a intents
        intent_keywords = {
            'agendar_turno': ['turno', 'agendar', 'reservar', 'cita', 'appointment'],
            'consultar_horarios': ['horario', 'hora', 'cuando', 'disponible', 'tiempo'],
            'consultar_requisitos': ['requisitos', 'necesito', 'documentos', 'papeles'],
            'consultar_disponibilidad': ['disponibilidad', 'libre', 'ocupado'],
            'cancelar_turno': ['cancelar', 'anular', 'cambiar'],
            'saludo': ['hola', 'buenos', 'buenas', 'saludos'],
            'despedida': ['chau', 'adiós', 'gracias', 'hasta']
        }
        
        # Buscar coincidencias
        for intent, keywords in intent_keywords.items():
            if any(keyword in phrase_lower for keyword in keywords):
                return intent
        
        return 'frase_ambigua'  # Intent por defecto
    
    def mark_phrase_as_resolved(self, phrase_id: int):
        """Marca una frase como resuelta - Placeholder"""
        self.logger.info(f"Frase {phrase_id} marcada como resuelta")
        return True

    def get_word_patterns(self, limit: int = 100, category: str = None, pattern_type: str = 'words') -> List[tuple]:
        """Devuelve patrones como lista de tuplas para el dashboard"""
        try:
            with self.get_db_session() as session:
                query = session.query(ConversationLog).order_by(ConversationLog.timestamp.desc())
                
                if category and category not in ['all', 'word', 'phrase']:
                    query = query.filter(ConversationLog.intent_detected == category)
                
                conversations = query.limit(limit).all()
                
                if not conversations:
                    return []
                
                if category == 'phrase' or pattern_type == 'phrases':
                    return self._get_phrase_patterns_as_tuples(conversations)
                else:
                    return self._get_word_patterns_as_tuples(conversations)
                
        except Exception as e:
            self.logger.error(f"Error obteniendo patrones como tuplas: {e}")
            return []
    
    def _get_word_patterns_as_tuples(self, conversations) -> List[tuple]:
        """Devuelve patrones de palabras como tuplas (palabra, frecuencia, intent_principal, 'word')"""
        word_count = {}
        word_intents = {}
        
        stop_words = {'para', 'con', 'por', 'que', 'una', 'del', 'las', 'los', 'como', 'esto', 'esta', 'este'}
        
        for conv in conversations:
            if conv.user_message:
                words = conv.user_message.lower().split()
                for word in words:
                    clean_word = word.strip('.,!?;:"()[]{}')
                    if len(clean_word) > 2 and clean_word not in stop_words:
                        word_count[clean_word] = word_count.get(clean_word, 0) + 1
                        
                        if clean_word not in word_intents:
                            word_intents[clean_word] = {}
                        
                        intent = conv.intent_detected or 'unknown'
                        word_intents[clean_word][intent] = word_intents[clean_word].get(intent, 0) + 1
        
        # Convertir a tuplas ordenadas
        results = []
        for word, count in sorted(word_count.items(), key=lambda x: x[1], reverse=True):
            # Encontrar el intent más común para esta palabra
            if word in word_intents and word_intents[word]:
                main_intent = max(word_intents[word].items(), key=lambda x: x[1])[0]
            else:
                main_intent = 'unknown'
            
            results.append((word, count, main_intent, 'word'))
        
        return results[:50]  # Limitar resultados
    
    def _get_phrase_patterns_as_tuples(self, conversations) -> List[tuple]:
        """Devuelve patrones de frases como tuplas (frase, frecuencia, intent_principal, 'phrase')"""
        phrase_count = {}
        phrase_intents = {}
        
        for conv in conversations:
            if conv.user_message and len(conv.user_message.strip()) > 5:
                phrase = conv.user_message.lower().strip()
                phrase_count[phrase] = phrase_count.get(phrase, 0) + 1
                
                if phrase not in phrase_intents:
                    phrase_intents[phrase] = {}
                
                intent = conv.intent_detected or 'unknown'
                phrase_intents[phrase][intent] = phrase_intents[phrase].get(intent, 0) + 1
        
        # Convertir a tuplas ordenadas
        results = []
        for phrase, count in sorted(phrase_count.items(), key=lambda x: x[1], reverse=True):
            if phrase in phrase_intents and phrase_intents[phrase]:
                main_intent = max(phrase_intents[phrase].items(), key=lambda x: x[1])[0]
            else:
                main_intent = 'unknown'
            
            results.append((phrase, count, main_intent, 'phrase'))
        
        return results[:30]  # Limitar resultados

    def get_word_patterns(self, limit: int = 100, category: str = None) -> Dict[str, Any]:
        """Analiza patrones de palabras en las conversaciones - Versión corregida"""
        try:
            with self.get_db_session() as session:
                # Obtener mensajes recientes
                query = session.query(ConversationLog).order_by(ConversationLog.timestamp.desc())
                
                # Filtrar por categoría/intent si se especifica
                if category:
                    query = query.filter(ConversationLog.intent_detected == category)
                
                conversations = query.limit(limit).all()
                
                if not conversations:
                    return {'common_words': {}, 'intent_keywords': {}}
                
                # Análisis de palabras comunes
                word_count = {}
                intent_keywords = {}
                
                for conv in conversations:
                    if conv.user_message:
                        words = conv.user_message.lower().split()
                        # Filtrar palabras comunes y cortas
                        filtered_words = [
                            word.strip('.,!?;:"()[]{}')
                            for word in words
                            if len(word) > 3 and word not in ['para', 'con', 'por', 'que', 'una', 'del', 'las', 'los', 'como']
                        ]
                        
                        for word in filtered_words:
                            word_count[word] = word_count.get(word, 0) + 1
                            
                            # Asociar palabras con intents
                            if conv.intent_detected:
                                if conv.intent_detected not in intent_keywords:
                                    intent_keywords[conv.intent_detected] = {}
                                intent_keywords[conv.intent_detected][word] = intent_keywords[conv.intent_detected].get(word, 0) + 1
                
                # Top 20 palabras más comunes
                common_words = dict(sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:20])
                
                # Top palabras por intent
                for intent in intent_keywords:
                    intent_keywords[intent] = dict(sorted(intent_keywords[intent].items(), key=lambda x: x[1], reverse=True)[:10])
                
                return {
                    'common_words': common_words,
                    'intent_keywords': intent_keywords,
                    'total_messages_analyzed': len(conversations),
                    'category_filter': category
                }
                
        except Exception as e:
            self.logger.error(f"Error analizando patrones de palabras: {e}")
            return {'common_words': {}, 'intent_keywords': {}}

# =====================================================
# FUNCIONES DE UTILIDAD PARA RASA
# =====================================================

def setup_learning_system(database_url: str) -> ConversationLogger:
    """Inicializa el sistema de aprendizaje"""
    try:
        logger_instance = ConversationLogger(database_url)
        logger.info("Sistema de aprendizaje inicializado correctamente")
        return logger_instance
    except Exception as e:
        logger.error(f"Error inicializando sistema de aprendizaje: {e}")
        raise

def log_rasa_interaction(logger_instance, tracker, bot_response, response_time_ms=None):
    """Log de interacción con Rasa - Versión corregida"""
    if not logger_instance:
        return
    
    try:
        # Obtener datos del tracker
        session_id = getattr(tracker, 'sender_id', 'unknown')
        
        # Obtener el último mensaje del usuario
        events = getattr(tracker, 'events', [])
        user_message = "Inicio de sesión"  # Valor por defecto válido
        intent_detected = ""
        confidence = 0.0
        
        # Buscar el último mensaje del usuario
        for event in reversed(events):
            if hasattr(event, 'type') and event.type == 'user':
                if hasattr(event, 'text') and event.text:
                    user_message = event.text
                if hasattr(event, 'parse_data') and event.parse_data:
                    intent_data = event.parse_data.get('intent', {})
                    intent_detected = intent_data.get('name', '')
                    confidence = intent_data.get('confidence', 0.0)
                break
        
        # Casos especiales para sesiones de inicio
        if not user_message or user_message == "Inicio de sesión":
            if "sesión iniciada" in bot_response.lower():
                user_message = "/session_start"
                intent_detected = "session_start"
                confidence = 1.0
        
        # Validar que user_message no sea None o vacío
        if not user_message:
            user_message = "Mensaje del usuario no disponible"
        
        # Registrar la conversación
        logger_instance.log_conversation(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            intent_detected=intent_detected,
            confidence=confidence,
            response_time_ms=response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Error logging interacción de Rasa: {e}")

def log_fuzzy_activation(logger_instance, tracker, analysis_data, response_time_ms=None):
    """Log específico para activación del motor difuso"""
    if not logger_instance:
        return
    
    try:
        session_id = getattr(tracker, 'sender_id', 'unknown')
        
        # Obtener el último mensaje del usuario
        events = getattr(tracker, 'events', [])
        user_message = "Activación motor difuso"  # Valor por defecto
        
        for event in reversed(events):
            if hasattr(event, 'type') and event.type == 'user':
                if hasattr(event, 'text') and event.text:
                    user_message = event.text
                break
        
        # Validar user_message
        if not user_message:
            user_message = "Consulta del motor difuso"
        
        # Registrar análisis difuso
        logger_instance.log_fuzzy_analysis(
            session_id=session_id,
            user_query=user_message,
            analysis_type="complete_recommendation",
            analysis_data=analysis_data,
            processing_time_ms=response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Error logging análisis difuso: {e}")

# Función para obtener el logger global
_global_logger = None

def get_conversation_logger():
    """Obtiene la instancia global del logger"""
    return _global_logger

def set_conversation_logger(logger_instance):
    """Establece la instancia global del logger"""
    global _global_logger
    _global_logger = logger_instance