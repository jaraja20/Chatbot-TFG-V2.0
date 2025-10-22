"""
Dashboard de Aprendizaje Mejorado
Sistema completo de análisis y mejora del chatbot

FUNCIONALIDADES PRINCIPALES:
1. 📋 Mensajes no entendidos CON contexto (anterior + posterior + sugerencia)
2. 👎 Mensajes con feedback negativo CON contexto completo
3. 📊 Eficacia del modelo según pulgares positivos (media de todas las conversaciones)

Autor: Sistema de aprendizaje mejorado
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import psycopg2
from typing import Dict, List

# Importar el logger mejorado
try:
    from conversation_logger import (
        ImprovedConversationLogger, 
        get_improved_conversation_logger,
        setup_improved_logging_system
    )
    LOGGER_AVAILABLE = True
except ImportError as e:
    LOGGER_AVAILABLE = False
    st.error(f"❌ Sistema de logging mejorado no disponible: {e}")

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
# 📋 PESTAÑA 1: MENSAJES NO ENTENDIDOS CON CONTEXTO
# =====================================================

def show_problematic_messages_tab():
    """
    ✅ Muestra mensajes no entendidos CON CONTEXTO COMPLETO
    Incluye: mensaje anterior, mensaje problemático, mensaje posterior, sugerencia
    """
    st.header("📋 Mensajes No Entendidos (Con Contexto)")
    st.write("Mensajes que el bot no pudo entender correctamente, con contexto completo para mejorar el modelo")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # Obtener mensajes problemáticos con contexto
    problematic_messages = logger_instance.get_problematic_messages_with_context(limit=50)
    
    if not problematic_messages:
        st.success("🎉 ¡Excelente! No hay mensajes problemáticos pendientes de revisión")
        st.info("Los mensajes se capturan automáticamente cuando:")
        st.markdown("""
        - El intent detectado es `nlu_fallback`
        - La confianza es menor al 70%
        - El usuario da feedback negativo (👎)
        """)
        return
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox(
            "Filtrar por tipo:",
            ["Todos", "Fallback", "Baja confianza", "Feedback negativo"]
        )
    
    with col2:
        show_resolved = st.checkbox("Mostrar resueltos", value=False)
    
    # Filtrar mensajes
    filtered_messages = problematic_messages
    if filter_type != "Todos":
        type_mapping = {
            "Fallback": "fallback",
            "Baja confianza": "low_confidence",
            "Feedback negativo": "thumbs_down"
        }
        filtered_messages = [m for m in problematic_messages 
                           if m['feedback_type'] == type_mapping[filter_type]]
    
    st.write(f"📋 **{len(filtered_messages)} mensajes** requieren atención:")
    st.markdown("---")
    
    # Mostrar cada mensaje con su contexto completo
    for i, msg in enumerate(filtered_messages):
        # Determinar el emoji según el tipo
        emoji_map = {
            'fallback': '❓',
            'low_confidence': '⚠️',
            'thumbs_down': '👎',
            'misunderstanding': '🤔'
        }
        emoji = emoji_map.get(msg['feedback_type'], '📝')
        
        # Título del expander
        title = f"{emoji} {msg['problematic_message'][:70]}... • Confianza: {msg['confidence']:.2f}"
        
        with st.expander(title, expanded=(i < 3)):  # Los primeros 3 expandidos
            
            # ✅ MOSTRAR CONTEXTO EN 3 COLUMNAS
            col_prev, col_prob, col_next = st.columns(3)
            
            # CONTEXTO ANTERIOR
            with col_prev:
                st.markdown("### 📍 Mensaje Anterior")
                if msg['previous_user_message']:
                    st.info(f"**Usuario:** {msg['previous_user_message']}")
                    if msg['previous_bot_response']:
                        st.success(f"**Bot:** {msg['previous_bot_response']}")
                    if msg['previous_intent']:
                        st.caption(f"Intent: `{msg['previous_intent']}`")
                else:
                    st.caption("_No hay mensaje anterior (inicio de conversación)_")
            
            # MENSAJE PROBLEMÁTICO
            with col_prob:
                st.markdown("### 🔴 Mensaje Problemático")
                st.error(f"**Usuario:** {msg['problematic_message']}")
                st.warning(f"**Bot:** {msg['bot_response']}")
                st.caption(f"Intent detectado: `{msg['intent_detected']}`")
                st.caption(f"Confianza: `{msg['confidence']:.3f}`")
                st.caption(f"Tipo: `{msg['feedback_type']}`")
                
                # Mostrar comentario si existe
                if msg['feedback_comment']:
                    st.markdown("**💬 Comentario del usuario:**")
                    st.text_area("", msg['feedback_comment'], height=80, disabled=True, 
                               key=f"comment_{msg['id']}")
            
            # CONTEXTO POSTERIOR
            with col_next:
                st.markdown("### 📍 Mensaje Siguiente")
                if msg['next_user_message']:
                    st.info(f"**Usuario:** {msg['next_user_message']}")
                    if msg['next_bot_response']:
                        st.success(f"**Bot:** {msg['next_bot_response']}")
                    if msg['next_intent']:
                        st.caption(f"Intent: `{msg['next_intent']}`")
                else:
                    st.caption("_Aún no hay mensaje siguiente_")
            
            st.markdown("---")
            
            # ✅ SUGERENCIA AUTOMÁTICA DE ARREGLO
            st.markdown("### 🔧 Sugerencia de Arreglo")
            
            col_sugg1, col_sugg2 = st.columns([2, 1])
            
            with col_sugg1:
                suggested_intent = msg['suggested_intent']
                
                if suggested_intent and suggested_intent != 'REVISAR_MANUALMENTE':
                    st.success(f"✅ **Intent sugerido:** `{suggested_intent}`")
                    
                    # Mostrar ejemplo YAML
                    st.subheader("📝 Agregar a nlu.yml:")
                    yaml_code = msg['suggested_training_example'] or f"""- intent: {suggested_intent}
  examples: |
    - {msg['problematic_message']}"""
                    
                    st.code(yaml_code, language="yaml")
                    
                    # Botón de copiar
                    st.download_button(
                        "📋 Copiar YAML",
                        data=yaml_code,
                        file_name=f"fix_{suggested_intent}.yml",
                        mime="text/yaml",
                        key=f"copy_yaml_{msg['id']}"
                    )
                else:
                    st.warning("⚠️ Revisar manualmente - no se pudo sugerir un intent automáticamente")
                    st.info(f"Considera crear un nuevo intent o agregar este ejemplo a un intent existente")
            
            with col_sugg2:
                st.markdown("### 🎯 Acciones")
                
                # Marcar como resuelto
                if st.button("✅ Marcar resuelto", key=f"resolve_{msg['id']}"):
                    admin_notes = st.text_input("Notas (opcional):", key=f"notes_{msg['id']}")
                    if logger_instance.mark_context_as_resolved(msg['id'], admin_notes):
                        st.success("✅ Marcado como resuelto")
                        st.rerun()
                    else:
                        st.error("Error al marcar")
                
                # Descargar contexto completo
                context_json = {
                    'timestamp': msg['timestamp'],
                    'session_id': msg['session_id'],
                    'context': {
                        'previous': {
                            'user': msg['previous_user_message'],
                            'bot': msg['previous_bot_response'],
                            'intent': msg['previous_intent']
                        },
                        'problematic': {
                            'user': msg['problematic_message'],
                            'bot': msg['bot_response'],
                            'intent': msg['intent_detected'],
                            'confidence': msg['confidence']
                        },
                        'next': {
                            'user': msg['next_user_message'],
                            'bot': msg['next_bot_response'],
                            'intent': msg['next_intent']
                        }
                    },
                    'suggestion': {
                        'intent': msg['suggested_intent'],
                        'example': msg['suggested_training_example']
                    }
                }
                
                st.download_button(
                    "💾 JSON",
                    data=json.dumps(context_json, indent=2, ensure_ascii=False),
                    file_name=f"context_{msg['id']}.json",
                    mime="application/json",
                    key=f"download_context_{msg['id']}"
                )
            
            st.markdown("---")

# =====================================================
# 👎 PESTAÑA 2: FEEDBACK NEGATIVO CON CONTEXTO
# =====================================================

def show_negative_feedback_tab():
    """
    ✅ Muestra mensajes con feedback negativo (botón abajo) CON CONTEXTO
    """
    st.header("👎 Feedback Negativo (Con Contexto)")
    st.write("Mensajes donde los usuarios presionaron 👎, con contexto completo de la conversación")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # Obtener mensajes con feedback negativo (filtrados por tipo)
    all_problematic = logger_instance.get_problematic_messages_with_context(limit=100)
    negative_feedback_messages = [m for m in all_problematic if m['feedback_type'] == 'thumbs_down']
    
    if not negative_feedback_messages:
        st.success("🎉 ¡Excelente! No hay feedback negativo reciente")
        st.info("Los usuarios pueden dar feedback negativo (👎) cuando:")
        st.markdown("""
        - La respuesta no fue útil
        - El bot no entendió su pregunta
        - La información fue incorrecta
        """)
        return
    
    st.write(f"📋 **{len(negative_feedback_messages)} mensajes** con feedback negativo:")
    st.markdown("---")
    
    # Estadísticas rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        with_comment = len([m for m in negative_feedback_messages if m['feedback_comment']])
        st.metric("Con comentario", with_comment)
    with col2:
        avg_confidence = sum(m['confidence'] for m in negative_feedback_messages) / len(negative_feedback_messages)
        st.metric("Confianza promedio", f"{avg_confidence:.2f}")
    with col3:
        fallback_count = len([m for m in negative_feedback_messages if m['intent_detected'] == 'nlu_fallback'])
        st.metric("Fallback", fallback_count)
    
    st.markdown("---")
    
    # Mostrar cada mensaje con feedback negativo
    for i, msg in enumerate(negative_feedback_messages):
        title = f"👎 {msg['problematic_message'][:70]}..."
        if msg['feedback_comment']:
            title += " 💬"
        
        with st.expander(title, expanded=(i < 5)):
            
            # ✅ CONTEXTO COMPLETO EN 3 COLUMNAS
            col_prev, col_prob, col_next = st.columns(3)
            
            with col_prev:
                st.markdown("### 📍 Antes")
                if msg['previous_user_message']:
                    st.info(msg['previous_user_message'])
                    if msg['previous_bot_response']:
                        st.success(msg['previous_bot_response'][:200] + "...")
                else:
                    st.caption("_Inicio de conversación_")
            
            with col_prob:
                st.markdown("### 👎 Feedback Negativo")
                st.error(f"**Usuario:** {msg['problematic_message']}")
                st.warning(f"**Bot:** {msg['bot_response'][:200]}...")
                st.caption(f"Intent: `{msg['intent_detected']}` • Confianza: `{msg['confidence']:.2f}`")
                
                # ✅ COMENTARIO DEL USUARIO (muy importante)
                if msg['feedback_comment']:
                    st.markdown("---")
                    st.markdown("**💬 Por qué no le gustó:**")
                    st.error(msg['feedback_comment'])
            
            with col_next:
                st.markdown("### 📍 Después")
                if msg['next_user_message']:
                    st.info(msg['next_user_message'])
                    if msg['next_bot_response']:
                        st.success(msg['next_bot_response'][:200] + "...")
                else:
                    st.caption("_Fin de conversación_")
            
            st.markdown("---")
            
            # ✅ ANÁLISIS Y SUGERENCIA
            col_analysis, col_action = st.columns([3, 1])
            
            with col_analysis:
                st.markdown("### 🔍 Análisis")
                
                # Determinar el problema
                problems = []
                if msg['intent_detected'] == 'nlu_fallback':
                    problems.append("❌ No se detectó ningún intent válido")
                if msg['confidence'] < 0.5:
                    problems.append("❌ Confianza muy baja")
                elif msg['confidence'] < 0.7:
                    problems.append("⚠️ Confianza baja")
                if msg['feedback_comment']:
                    problems.append(f"💬 Usuario explicó: '{msg['feedback_comment']}'")
                
                for problem in problems:
                    st.write(problem)
                
                # Sugerencia
                st.markdown("---")
                st.markdown("### 🔧 Sugerencia")
                
                if msg['suggested_intent'] and msg['suggested_intent'] != 'REVISAR_MANUALMENTE':
                    st.success(f"Agregar a intent: `{msg['suggested_intent']}`")
                    st.code(msg['suggested_training_example'], language="yaml")
                else:
                    st.info("Considera crear un nuevo intent o mejorar el existente")
            
            with col_action:
                st.markdown("### 🎯 Acciones")
                
                if st.button("✅ Resuelto", key=f"resolve_neg_{msg['id']}"):
                    if logger_instance.mark_context_as_resolved(msg['id'], "Feedback negativo revisado"):
                        st.success("✅ Marcado")
                        st.rerun()
                
                # Exportar
                export_data = {
                    'user_complaint': msg['feedback_comment'],
                    'conversation': {
                        'before': msg['previous_user_message'],
                        'problem': msg['problematic_message'],
                        'after': msg['next_user_message']
                    },
                    'bot_response': msg['bot_response'],
                    'suggestion': msg['suggested_training_example']
                }
                
                st.download_button(
                    "📄 Exportar",
                    data=json.dumps(export_data, indent=2, ensure_ascii=False),
                    file_name=f"feedback_{msg['id']}.json",
                    key=f"export_neg_{msg['id']}"
                )

# =====================================================
# 📊 PESTAÑA 3: EFICACIA DEL MODELO
# =====================================================

def show_model_efficiency_tab():
    """
    ✅ Muestra eficacia del modelo según pulgares positivos
    Media de todas las conversaciones
    """
    st.header("📊 Eficacia del Modelo")
    st.write("Análisis de rendimiento basado en feedback de usuarios (👍 vs 👎)")
    
    logger_instance = get_improved_conversation_logger()
    if not logger_instance:
        logger_instance = initialize_improved_logger()
    
    if not logger_instance:
        st.error("Sistema de logging no disponible")
        return
    
    # ✅ RESUMEN GENERAL (MEDIA DE TODAS LAS CONVERSACIONES)
    st.subheader("🎯 Resumen General (Últimos 30 días)")
    
    overall_summary = logger_instance.get_overall_efficiency_summary()
    
    if not overall_summary or overall_summary.get('total_feedbacks', 0) == 0:
        st.warning("⚠️ No hay suficientes datos de feedback aún")
        st.info("Los usuarios deben dar feedback (👍 o 👎) para generar estadísticas")
        return
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "👍 Feedback Positivo",
            overall_summary['positive_feedbacks'],
            help="Total de respuestas con 👍"
        )
    
    with col2:
        st.metric(
            "👎 Feedback Negativo",
            overall_summary['negative_feedbacks'],
            delta=f"-{overall_summary['negative_feedbacks']}",
            delta_color="inverse",
            help="Total de respuestas con 👎"
        )
    
    with col3:
        satisfaction = overall_summary['avg_satisfaction']
        st.metric(
            "😊 Satisfacción",
            f"{satisfaction:.1f}%",
            delta=f"{satisfaction - 50:.1f}%",
            help="(Positivos - Negativos) / Total Feedback × 100"
        )
    
    with col4:
        efficiency = overall_summary['overall_efficiency']
        st.metric(
            "⚡ Eficiencia Global",
            f"{efficiency:.1f}%",
            help="Métrica combinada de rendimiento general"
        )
    
    st.markdown("---")
    
    # ✅ GRÁFICO DE TENDENCIA (últimos 7 días)
    st.subheader("📈 Tendencia de Eficiencia")
    
    efficiency_stats = logger_instance.get_model_efficiency_stats(days=30)
    
    if efficiency_stats:
        df = pd.DataFrame(efficiency_stats)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Gráfico de líneas múltiples
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['success_rate'],
            name='Tasa de éxito',
            line=dict(color='green', width=3),
            mode='lines+markers'
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['user_satisfaction'],
            name='Satisfacción usuario',
            line=dict(color='blue', width=3),
            mode='lines+markers'
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['fallback_rate'],
            name='Tasa de fallback',
            line=dict(color='red', width=2, dash='dash'),
            mode='lines+markers'
        ))
        
        fig.update_layout(
            title="Evolución de Métricas de Calidad",
            xaxis_title="Fecha",
            yaxis_title="Porcentaje (%)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ✅ TABLA DE DATOS DETALLADOS
        st.subheader("📋 Datos Detallados por Día")
        
        # Preparar tabla para mostrar
        display_df = df.copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
        display_df = display_df[[
            'date', 'total_interactions', 'successful_interactions', 
            'failed_interactions', 'success_rate', 'user_satisfaction'
        ]]
        display_df.columns = [
            'Fecha', 'Total', 'Éxitos (👍)', 'Fallos (👎)', 
            'Tasa Éxito %', 'Satisfacción %'
        ]
        
        st.dataframe(
            display_df.style.format({
                'Tasa Éxito %': '{:.1f}',
                'Satisfacción %': '{:.1f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("---")
    
    # ✅ GRÁFICO DE DISTRIBUCIÓN DE FEEDBACK
    st.subheader("🎭 Distribución de Feedback")
    
    total_positive = overall_summary['positive_feedbacks']
    total_negative = overall_summary['negative_feedbacks']
    
    if total_positive + total_negative > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Positivo 👍', 'Negativo 👎'],
            values=[total_positive, total_negative],
            marker=dict(colors=['#28a745', '#dc3545']),
            hole=0.4
        )])
        
        fig_pie.update_layout(
            title="Proporción de Feedback de Usuarios",
            height=350
        )
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.markdown("### 📈 Interpretación")
            
            positive_pct = (total_positive / (total_positive + total_negative)) * 100
            
            if positive_pct >= 80:
                st.success("🌟 **Excelente** - El modelo funciona muy bien")
            elif positive_pct >= 70:
                st.info("✅ **Bueno** - El modelo es efectivo")
            elif positive_pct >= 60:
                st.warning("⚠️ **Regular** - Hay margen de mejora")
            else:
                st.error("🔴 **Necesita mejoras** - Revisar mensajes con 👎")
            
            st.metric("Feedback positivo", f"{positive_pct:.1f}%")
    
    # ✅ RECOMENDACIONES
    st.markdown("---")
    st.subheader("💡 Recomendaciones")
    
    recommendations = []
    
    if overall_summary['avg_satisfaction'] < 50:
        recommendations.append("🔴 **Crítico:** Más usuarios dan 👎 que 👍. Revisa urgentemente los mensajes con feedback negativo.")
    
    if efficiency_stats:
        latest_fallback = efficiency_stats[0]['fallback_rate']
        if latest_fallback > 20:
            recommendations.append(f"⚠️ **Alto fallback:** {latest_fallback:.1f}% de mensajes no se entienden. Agrega más ejemplos al NLU.")
    
    if overall_summary['negative_feedbacks'] > overall_summary['positive_feedbacks']:
        recommendations.append("📚 **Entrenamiento:** Considera agregar los ejemplos sugeridos en la pestaña de mensajes no entendidos.")
    
    if overall_summary['overall_efficiency'] > 80:
        recommendations.append("🌟 **Excelente trabajo:** El modelo está funcionando muy bien. Mantén el monitoreo regular.")
    
    if not recommendations:
        recommendations.append("✅ El modelo funciona adecuadamente. Continúa monitoreando el feedback de usuarios.")
    
    for rec in recommendations:
        st.markdown(rec)

# =====================================================
# 📈 PESTAÑA 4: RESUMEN GENERAL
# =====================================================

def show_summary_tab():
    """Resumen general del sistema"""
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
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💬 Total Conversaciones", stats['total_conversations'])
        st.metric("🎯 Confianza Promedio", f"{stats['avg_confidence']:.3f}")
    
    with col2:
        st.metric("⚠️ Requieren Revisión", stats['needs_review'])
        st.metric("👍 Feedback Positivo", stats['positive_feedback'])
    
    with col3:
        st.metric("👎 Feedback Negativo", stats['negative_feedback'])
        st.metric("😊 Satisfacción", f"{stats['satisfaction_rate']:.1f}%")
    
    # Alertas
    if stats['needs_review'] > 10:
        st.warning(f"⚠️ Hay {stats['needs_review']} mensajes que requieren tu atención")
    
    if stats['satisfaction_rate'] < 70 and (stats['positive_feedback'] + stats['negative_feedback']) > 5:
        st.error("🔴 Satisfacción baja. Revisa el feedback negativo.")
    
    # Botón de actualización
    if st.button("🔄 Actualizar Datos"):
        st.rerun()

# =====================================================
# DASHBOARD PRINCIPAL
# =====================================================

def main():
    """Dashboard principal mejorado"""
    
    
    st.title("📊 Dashboard de Aprendizaje Mejorado")
    st.markdown("Sistema de análisis y mejora continua del chatbot")
    st.markdown("---")
    
    # Verificar conexión
    if not get_db_connection():
        st.error("❌ No se puede conectar a la base de datos")
        st.info("Verifica que PostgreSQL esté ejecutándose")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Panel de Control")
        
        if st.button("🔄 Actualizar Todo"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Estado del logger
        logger_instance = get_improved_conversation_logger()
        if logger_instance:
            st.success("✅ Logger activo")
        else:
            if st.button("🔧 Inicializar Logger"):
                logger_instance = initialize_improved_logger()
                if logger_instance:
                    st.success("Logger inicializado")
                    st.rerun()
        
        st.markdown("---")
        st.markdown("### 📚 Guía Rápida")
        st.markdown("""
        **Mensajes No Entendidos:** 
        Muestra el contexto completo (antes, durante, después) con sugerencias de arreglo
        
        **Feedback Negativo:** 
        Mensajes donde usuarios dieron 👎 con sus comentarios y contexto
        
        **Eficacia del Modelo:** 
        Estadísticas basadas en feedback de usuarios (👍 vs 👎)
        """)
    
    # Pestañas principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Resumen",
        "📋 Mensajes No Entendidos",
        "👎 Feedback Negativo",
        "📊 Eficacia del Modelo"
    ])
    
    with tab1:
        show_summary_tab()
    
    with tab2:
        show_problematic_messages_tab()
    
    with tab3:
        show_negative_feedback_tab()
    
    with tab4:
        show_model_efficiency_tab()

if __name__ == "__main__":
    main()
    
# =====================================================
# 🔁 EXPORTACIÓN PARA app.py
# =====================================================

def show_learning_dashboard():
    """Permite que app.py muestre el dashboard embebido"""
    main()