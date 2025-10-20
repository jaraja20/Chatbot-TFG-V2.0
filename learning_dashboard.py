"""
Dashboard de aprendizaje simplificado
Solo funcionalidades esenciales que realmente funcionan

PESTAÑAS:
1. Resumen - Solo métricas útiles
2. Mensajes para Revisar - Funcionamiento correcto
3. Feedback - Positivo y negativo funcional
4. Conversaciones Semanales - Nueva funcionalidad

"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import psycopg2
from typing import Dict, List

# Importar el logger mejorado
try:
    from improved_conversation_logger import (
        ImprovedConversationLogger, 
        get_improved_conversation_logger,
        setup_improved_logging_system
    )
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False

# Configuración de BD
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        st.error(f"Error conectando a BD: {e}")
        return None

def initialize_improved_logger():
    """Inicializa el logger mejorado"""
    if not LOGGER_AVAILABLE:
        st.error("Sistema de logging mejorado no disponible")
        return None
    
    try:
        database_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
        logger_instance = setup_improved_logging_system(database_url)
        return logger_instance
    except Exception as e:
        st.error(f"Error inicializando logger: {e}")
        return None

# =====================================================
# PESTAÑA 1: RESUMEN SIMPLIFICADO
# =====================================================

def show_summary_tab_simplified():
    """Resumen con solo métricas esenciales"""
    st.header("📈 Resumen del Sistema")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # Obtener estadísticas
    stats = logger_instance.get_summary_stats(days=7)
    
    if not stats or stats.get('total_conversations', 0) == 0:
        st.warning("⚠️ No hay datos disponibles de los últimos 7 días")
        st.info("Interactúa con el chatbot para generar estadísticas")
        return
    
    # Métricas principales en columnas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "💬 Total Conversaciones",
            stats['total_conversations'],
            help="Mensajes procesados últimos 7 días"
        )
        
        st.metric(
            "🎯 Confianza Promedio",
            f"{stats['avg_confidence']:.3f}",
            help="Nivel promedio de confianza"
        )
    
    with col2:
        st.metric(
            "⚠️ Requieren Revisión",
            stats['needs_review'],
            help="Mensajes que necesitan atención"
        )
        
        st.metric(
            "👍 Feedback Positivo",
            stats['positive_feedback'],
            help="Usuarios satisfechos"
        )
    
    with col3:
        st.metric(
            "👎 Feedback Negativo",
            stats['negative_feedback'],
            help="Usuarios insatisfechos"
        )
        
        st.metric(
            "😊 Satisfacción",
            f"{stats['satisfaction_rate']:.1f}%",
            help="% de feedback positivo"
        )
    
    # Alerta si hay problemas
    if stats['needs_review'] > 10:
        st.warning(f"⚠️ Hay {stats['needs_review']} mensajes que requieren tu atención")
    
    if stats['satisfaction_rate'] < 70 and stats['positive_feedback'] + stats['negative_feedback'] > 5:
        st.error("🔴 Satisfacción baja. Revisa el feedback negativo.")
    
    # Botón de actualización
    if st.button("🔄 Actualizar Datos"):
        st.rerun()

# =====================================================
# PESTAÑA 2: MENSAJES PARA REVISAR
# =====================================================

def show_review_tab_functional():
    """Mensajes que realmente necesitan revisión"""
    st.header("🗂️ Mensajes para Revisar")
    st.write("Mensajes que el sistema marcó automáticamente para revisión manual")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # Obtener mensajes para revisar
    messages = logger_instance.get_messages_for_review(limit=30)
    
    if not messages:
        st.success("🎉 ¡Excelente! No hay mensajes pendientes de revisión")
        st.info("Los mensajes se marcan automáticamente cuando:")
        st.markdown("""
        - No se detecta un intent específico
        - La confianza es menor al 70%
        - El LLM no puede interpretar el mensaje
        - El usuario da feedback negativo
        """)
        return
    
    st.write(f"📋 **{len(messages)} mensajes** requieren tu atención:")
    
    # Mostrar mensajes
    for i, msg in enumerate(messages):
        with st.expander(f"📝 {msg['user_message'][:60]}... • Confianza: {msg['confidence']:.2f}"):
            
            # Mostrar conversación
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("👤 Usuario")
                st.write(msg['user_message'])
                
                st.subheader("📊 Análisis")
                st.write(f"**Intent detectado:** {msg['intent_detected']}")
                st.write(f"**Confianza:** {msg['confidence']:.3f}")
                if msg['llm_interpretation']:
                    st.write(f"**LLM interpretó:** {msg['llm_interpretation']}")
                st.write(f"**Timestamp:** {msg['timestamp'][:16]}")
            
            with col2:
                st.subheader("🤖 Bot")
                st.write(msg['bot_response'])
            
            # Sugerencia YAML
            st.subheader("🔧 Sugerencia para nlu.yml")
            suggested_intent = msg['intent_detected'] if msg['intent_detected'] != 'No detectado' else 'nlu_fallback'
            
            yaml_suggestion = f"""- intent: {suggested_intent}
  examples: |
    - {msg['user_message']}"""
            
            st.code(yaml_suggestion, language="yaml")
            
            # Acciones
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Marcar como revisado", key=f"reviewed_{msg['id']}"):
                    if logger_instance.mark_as_reviewed(msg['id']):
                        st.success("Marcado como revisado!")
                        st.rerun()
                    else:
                        st.error("Error al marcar")
            
            with col2:
                # Descargar como texto
                message_content = f"""Usuario: {msg['user_message']}
Bot: {msg['bot_response']}
Intent: {msg['intent_detected']}
Confianza: {msg['confidence']}
Timestamp: {msg['timestamp']}"""
                
                st.download_button(
                    "📄 Descargar",
                    data=message_content,
                    file_name=f"mensaje_{msg['id']}.txt",
                    mime="text/plain",
                    key=f"download_{msg['id']}"
                )
            
            with col3:
                # Selector de nuevo intent
                new_intent = st.selectbox(
                    "Reasignar intent:",
                    ["", "agendar_turno", "consultar_horarios", "consultar_requisitos", 
                     "cancelar_turno", "frase_ambigua", "consultar_disponibilidad"],
                    key=f"intent_{msg['id']}"
                )
                if new_intent:
                    st.info(f"Sugerido: {new_intent}")

# =====================================================
# PESTAÑA 3: FEEDBACK FUNCIONAL
# =====================================================

def show_feedback_tab_functional():
    """Feedback que realmente funciona"""
    st.header("💬 Feedback de Usuarios")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # Tabs para positivo y negativo
    tab1, tab2 = st.tabs(["👎 Feedback Negativo", "👍 Feedback Positivo"])
    
    with tab1:
        st.subheader("👎 Mensajes con Feedback Negativo")
        
        negative_messages = logger_instance.get_feedback_messages('negative', limit=30)
        
        if not negative_messages:
            st.success("🎉 ¡No hay feedback negativo reciente!")
            st.info("Los usuarios están satisfechos con las respuestas")
            return
        
        st.write(f"📋 **{len(negative_messages)} mensajes** con feedback negativo:")
        
        for msg in negative_messages:
            with st.expander(f"👎 {msg['user_message'][:50]}... • {msg['timestamp'][:16]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**👤 Usuario preguntó:**")
                    st.write(msg['user_message'])
                    st.write("**📊 Análisis:**")
                    st.write(f"• Intent: {msg['intent_detected']}")
                    st.write(f"• Confianza: {msg['confidence']:.3f}")
                
                with col2:
                    st.write("**🤖 Bot respondió:**")
                    st.write(msg['bot_response'])
                    if msg['feedback_comment']:
                        st.warning(f"**💭 Comentario:** {msg['feedback_comment']}")
                
                st.error("💡 **Acción recomendada:** Mejorar la respuesta para este tipo de consulta")
    
    with tab2:
        st.subheader("👍 Mensajes con Feedback Positivo")
        
        positive_messages = logger_instance.get_feedback_messages('positive', limit=30)
        
        if not positive_messages:
            st.info("📝 Aún no hay feedback positivo registrado")
            return
        
        st.write(f"📋 **{len(positive_messages)} mensajes** con feedback positivo:")
        
        # Mostrar estadísticas de éxito
        if positive_messages:
            intents_exitosos = {}
            for msg in positive_messages:
                intent = msg['intent_detected'] or 'No detectado'
                intents_exitosos[intent] = intents_exitosos.get(intent, 0) + 1
            
            st.subheader("🎯 Intents Más Exitosos")
            for intent, count in sorted(intents_exitosos.items(), key=lambda x: x[1], reverse=True)[:5]:
                st.write(f"• **{intent}**: {count} éxitos")
        
        # Mostrar ejemplos exitosos
        st.subheader("✅ Ejemplos de Respuestas Exitosas")
        for msg in positive_messages[:5]:
            with st.expander(f"👍 {msg['user_message'][:50]}... • Confianza: {msg['confidence']:.2f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**👤 Usuario:**")
                    st.write(msg['user_message'])
                    st.write(f"**Intent:** {msg['intent_detected']}")
                
                with col2:
                    st.write("**🤖 Respuesta exitosa:**")
                    st.write(msg['bot_response'])
                
                st.success("💡 Esta respuesta fue útil - Usar como referencia")

# =====================================================
# PESTAÑA 4: CONVERSACIONES SEMANALES (NUEVA)
# =====================================================

def show_weekly_conversations_tab():
    """Nueva pestaña para conversaciones completas semanales"""
    st.header("📅 Conversaciones de la Semana")
    st.write("Registro completo de todas las conversaciones de usuarios (se guarda 1 semana)")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # Obtener conversaciones semanales
    conversations = logger_instance.get_weekly_conversations()
    
    if not conversations:
        st.info("📝 No hay conversaciones registradas para esta semana")
        st.write("Las conversaciones se guardan automáticamente cuando los usuarios interactúan")
        return
    
    st.write(f"📋 **{len(conversations)} conversaciones** registradas esta semana:")
    
    # Estadísticas generales
    total_messages = sum(c['message_count'] for c in conversations)
    avg_confidence = sum(c['avg_confidence'] for c in conversations) / len(conversations)
    total_positive = sum(c['feedback_positive'] for c in conversations)
    total_negative = sum(c['feedback_negative'] for c in conversations)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💬 Total Mensajes", total_messages)
    with col2:
        st.metric("🎯 Confianza Promedio", f"{avg_confidence:.2f}")
    with col3:
        st.metric("👍 Feedback +", total_positive)
    with col4:
        st.metric("👎 Feedback -", total_negative)
    
    st.markdown("---")
    
    # Mostrar cada conversación
    for i, conv in enumerate(conversations):
        start_time = datetime.fromisoformat(conv['start_time']).strftime("%d/%m %H:%M")
        end_time = datetime.fromisoformat(conv['end_time']).strftime("%H:%M")
        duration = datetime.fromisoformat(conv['end_time']) - datetime.fromisoformat(conv['start_time'])
        
        with st.expander(f"💬 Sesión {conv['session_id'][-8:]} • {start_time}-{end_time} • {conv['message_count']} mensajes"):
            
            # Información de la conversación
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Duración:** {duration}")
                st.write(f"**Mensajes:** {conv['message_count']}")
            with col2:
                st.write(f"**Confianza:** {conv['avg_confidence']:.2f}")
                st.write(f"**Feedback +:** {conv['feedback_positive']}")
            with col3:
                st.write(f"**Feedback -:** {conv['feedback_negative']}")
                st.write(f"**ID Sesión:** {conv['session_id']}")
            
            # Mostrar mensajes de la conversación
            if st.checkbox(f"Ver mensajes completos", key=f"show_msgs_{conv['id']}"):
                conversation_data = conv['conversation_data']
                
                for j, msg in enumerate(conversation_data):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', 'Sin contenido')
                    timestamp = msg.get('timestamp', '')
                    
                    if role == 'user':
                        st.write(f"**👤 Usuario ({timestamp[:16]}):**")
                        st.write(content)
                    elif role == 'assistant':
                        st.write(f"**🤖 Bot ({timestamp[:16]}):**")
                        st.write(content)
                        
                        # Mostrar feedback si existe
                        if msg.get('feedback_thumbs'):
                            feedback_emoji = "👍" if msg['feedback_thumbs'] == 1 else "👎"
                            st.write(f"**Feedback:** {feedback_emoji}")
                            if msg.get('feedback_comment'):
                                st.write(f"**Comentario:** {msg['feedback_comment']}")
                    
                    st.markdown("---")
            
            # Botón de descarga
            conversation_json = {
                'session_id': conv['session_id'],
                'start_time': conv['start_time'],
                'end_time': conv['end_time'],
                'message_count': conv['message_count'],
                'conversation_data': conv['conversation_data']
            }
            
            st.download_button(
                "📄 Descargar JSON",
                data=json.dumps(conversation_json, indent=2, ensure_ascii=False),
                file_name=f"conversacion_{conv['session_id'][-8:]}_{start_time.replace('/', '')}.json",
                mime="application/json",
                key=f"download_conv_{conv['id']}"
            )

# =====================================================
# DASHBOARD PRINCIPAL SIMPLIFICADO
# =====================================================

def show_simplified_learning_dashboard():
    """Dashboard principal simplificado con solo funcionalidades útiles"""
    
    st.title("📊 Dashboard de Aprendizaje Simplificado")
    st.markdown("---")
    
    # Verificar conexión
    if not get_db_connection():
        st.error("❌ No se puede conectar a la base de datos")
        st.info("Verifica que PostgreSQL esté ejecutándose y las credenciales sean correctas")
        return
    
    # Sidebar con controles
    with st.sidebar:
        st.header("🎛️ Controles")
        
        if st.button("🔄 Actualizar Todo"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Estado del sistema
        st.subheader("ℹ️ Estado")
        
        # Verificar si hay logger mejorado
        logger_instance = get_improved_conversation_logger()
        if logger_instance:
            st.success("✅ Logger mejorado activo")
        else:
            if st.button("🔧 Inicializar Logger"):
                logger_instance = initialize_improved_logger()
                if logger_instance:
                    st.success("Logger inicializado")
                    st.rerun()
        
        st.markdown("---")
        
        # Información
        st.write("**Funcionalidades:**")
        st.write("• Estadísticas esenciales")
        st.write("• Mensajes para revisar")
        st.write("• Feedback funcional")
        st.write("• Conversaciones semanales")
    
    # Pestañas principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Resumen",
        "🗂️ Para Revisar", 
        "💬 Feedback",
        "📅 Conversaciones Semanales"
    ])
    
    with tab1:
        show_summary_tab_simplified()
    
    with tab2:
        show_review_tab_functional()
    
    with tab3:
        show_feedback_tab_functional()
    
    with tab4:
        show_weekly_conversations_tab()

# =====================================================
# PUNTO DE ENTRADA
# =====================================================

if __name__ == "__main__":
    show_simplified_learning_dashboard()