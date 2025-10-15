"""
Dashboard de aprendizaje simplificado para el chatbot
3 pestañas: Resumen, Guardados (No interpretados), Feedback
CORREGIDO para compatibilidad con PostgreSQL
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import psycopg2
from collections import Counter
import re

# =====================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =====================================================

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# =====================================================
# FUNCIONES DE CONEXIÓN Y UTILIDAD
# =====================================================

def get_db_connection():
    """Obtiene conexión segura a PostgreSQL"""
    try:
        return psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            client_encoding='utf8'
        )
    except Exception as e:
        st.error(f"Error de conexión a BD: {e}")
        return None

def safe_query(query, params=None):
    """Ejecuta queries de forma segura y retorna DataFrame"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error en query: {e}")
        if conn:
            conn.close()
        return pd.DataFrame()

def check_and_add_missing_columns():
    """Verifica y agrega columnas faltantes en conversation_logs"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar columnas existentes
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'conversation_logs'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        columns_to_add = {
            'feedback_thumbs': 'SMALLINT',
            'feedback_comment': 'TEXT',
            'needs_review': 'BOOLEAN DEFAULT FALSE',
            'message_block': 'TEXT'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE conversation_logs ADD COLUMN {column_name} {column_type}")
                    conn.commit()
                    st.success(f"✅ Columna {column_name} agregada exitosamente")
                except Exception as e:
                    st.warning(f"⚠️ No se pudo agregar {column_name}: {e}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error verificando columnas: {e}")
        if conn:
            conn.close()
        return False

def update_needs_review_status(log_id, status=False):
    """Actualiza el estado needs_review de un registro"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversation_logs SET needs_review = %s WHERE id = %s",
            (status, log_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error actualizando estado: {e}")
        if conn:
            conn.close()
        return False

def generate_yaml_suggestion(user_message, intent_suggestion="nlu_fallback"):
    """Genera sugerencia YAML para nlu.yml"""
    return f"""- intent: {intent_suggestion}
  examples: |
    - {user_message}"""

def generate_message_block_if_missing(user_message, bot_response):
    """Genera message_block si no existe"""
    return f"[USUARIO]\n{user_message}\n\n[BOT]\n{bot_response}"

# =====================================================
# PESTAÑA 1: RESUMEN (CORREGIDA)
# =====================================================

def show_summary_tab():
    """📈 Pestaña de resumen con estadísticas globales"""
    st.header("📈 Resumen General")
    
    # Verificar y agregar columnas faltantes
    check_and_add_missing_columns()
    
    # Query corregida para PostgreSQL
    stats_query = """
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(DISTINCT session_id) as unique_sessions,
            CAST(AVG(CASE WHEN confidence > 0 THEN confidence::numeric ELSE NULL END) AS numeric(10,3)) as avg_confidence,
            COUNT(CASE WHEN needs_review = TRUE THEN 1 END) as needs_review_count,
            COUNT(CASE WHEN feedback_thumbs = 1 THEN 1 END) as positive_feedback,
            COUNT(CASE WHEN feedback_thumbs = -1 THEN 1 END) as negative_feedback
        FROM conversation_logs
        WHERE timestamp >= NOW() - INTERVAL '30 days'
    """
    
    stats_df = safe_query(stats_query)
    
    if stats_df.empty:
        st.warning("⚠️ No hay datos disponibles. Interactúa con el chatbot para generar estadísticas.")
        return
    
    stats = stats_df.iloc[0]
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💬 Total Conversaciones",
            int(stats['total_conversations']),
            help="Mensajes procesados en últimos 30 días"
        )
    
    with col2:
        st.metric(
            "👥 Sesiones Únicas",
            int(stats['unique_sessions']),
            help="Usuarios que han interactuado"
        )
    
    with col3:
        confidence_val = float(stats['avg_confidence']) if stats['avg_confidence'] else 0
        st.metric(
            "🎯 Confianza Promedio",
            f"{confidence_val:.3f}",
            help="Nivel promedio de confianza del modelo"
        )
    
    with col4:
        st.metric(
            "⚠️ Requieren Revisión",
            int(stats['needs_review_count']),
            help="Mensajes marcados para revisión"
        )
    
    st.markdown("---")
    
    # Métricas de feedback
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "👍 Feedback Positivo",
            int(stats['positive_feedback']),
            help="Usuarios que dieron like"
        )
    
    with col2:
        st.metric(
            "👎 Feedback Negativo",
            int(stats['negative_feedback']),
            help="Usuarios que reportaron problemas"
        )
    
    with col3:
        total_feedback = int(stats['positive_feedback']) + int(stats['negative_feedback'])
        satisfaction_rate = (int(stats['positive_feedback']) / max(1, total_feedback)) * 100
        st.metric(
            "😊 Satisfacción",
            f"{satisfaction_rate:.1f}%",
            help="Porcentaje de feedback positivo"
        )
    
    # Gráficos
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de intents más utilizados
        st.subheader("🎯 Intents Más Utilizados")
        
        intent_query = """
            SELECT 
                COALESCE(intent_detected, 'No detectado') as intent,
                COUNT(*) as count
            FROM conversation_logs
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY intent_detected
            ORDER BY count DESC
            LIMIT 10
        """
        
        intent_df = safe_query(intent_query)
        
        if not intent_df.empty:
            fig_intents = px.bar(
                intent_df,
                x='count',
                y='intent',
                orientation='h',
                title='Top 10 Intents',
                color='count',
                color_continuous_scale='viridis'
            )
            fig_intents.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_intents, use_container_width=True)
        else:
            st.info("No hay datos de intents disponibles")
    
    with col2:
        # Actividad por días
        st.subheader("📅 Actividad Diaria")
        
        daily_query = """
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as conversations
            FROM conversation_logs
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        
        daily_df = safe_query(daily_query)
        
        if not daily_df.empty:
            fig_daily = px.line(
                daily_df,
                x='date',
                y='conversations',
                title='Conversaciones por Día',
                markers=True
            )
            fig_daily.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Número de Conversaciones"
            )
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("No hay datos de actividad diaria disponibles")

# =====================================================
# PESTAÑA 2: GUARDADOS (CORREGIDA)
# =====================================================

def show_saved_tab():
    """🗂️ Pestaña de mensajes guardados que necesitan revisión"""
    st.header("🗂️ Guardados (No interpretados)")
    st.write("Mensajes que el sistema marcó automáticamente para revisión")
    
    # Verificar si la columna message_block existe
    check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'conversation_logs' AND column_name = 'message_block'
    """
    
    check_df = safe_query(check_query)
    has_message_block = not check_df.empty
    
    # Query adaptada según si existe message_block
    if has_message_block:
        review_query = """
            SELECT 
                id, session_id, user_message, bot_response, 
                intent_detected, confidence, timestamp, message_block
            FROM conversation_logs
            WHERE needs_review = TRUE
            ORDER BY timestamp DESC
            LIMIT 50
        """
    else:
        review_query = """
            SELECT 
                id, session_id, user_message, bot_response, 
                intent_detected, confidence, timestamp
            FROM conversation_logs
            WHERE (intent_detected IS NULL OR intent_detected = 'No detectado' OR confidence < 0.75)
            ORDER BY timestamp DESC
            LIMIT 50
        """
    
    review_df = safe_query(review_query)
    
    if review_df.empty:
        st.success("🎉 ¡Excelente! No hay mensajes pendientes de revisión.")
        st.info("Los mensajes se marcan automáticamente cuando:")
        st.markdown("""
        - No se detecta un intent específico
        - La confianza es menor a 0.75
        - El usuario da feedback negativo (👎)
        """)
        
        # Botón para agregar columnas faltantes
        if not has_message_block:
            st.warning("⚠️ Faltan columnas en la tabla. Haz clic para agregarlas:")
            if st.button("🔧 Agregar Columnas Faltantes"):
                if check_and_add_missing_columns():
                    st.success("Columnas agregadas. Recarga la página.")
                    st.rerun()
        return
    
    st.write(f"📋 **{len(review_df)} mensajes** requieren tu atención:")
    
    # Mostrar cada mensaje en un expander
    for idx, row in review_df.iterrows():
        # Crear título descriptivo para el expander
        user_msg_preview = row['user_message'][:50] + "..." if len(row['user_message']) > 50 else row['user_message']
        confidence_str = f"Confianza: {row['confidence']:.2f}" if row['confidence'] else "Sin confianza"
        
        expander_title = f"📝 {user_msg_preview} • {confidence_str}"
        
        with st.expander(expander_title):
            # Mostrar el message_block o generarlo
            st.subheader("💬 Conversación Completa")
            
            if has_message_block and row.get('message_block'):
                message_content = row['message_block']
            else:
                # Generar message_block si no existe
                message_content = generate_message_block_if_missing(
                    row['user_message'], 
                    row['bot_response']
                )
            
            st.text_area(
                "Bloque de mensaje:",
                value=message_content,
                height=120,
                key=f"block_{row['id']}",
                disabled=True
            )
            
            # Información adicional
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Detalles:**")
                st.write(f"- **ID:** {row['id']}")
                st.write(f"- **Sesión:** {str(row['session_id'])[-8:]}")
                st.write(f"- **Intent detectado:** {row['intent_detected'] or 'No detectado'}")
                st.write(f"- **Timestamp:** {row['timestamp']}")
            
            with col2:
                st.write("**Acciones:**")
                
                # Botón de descarga
                st.download_button(
                    label="📄 Descargar .txt",
                    data=message_content,
                    file_name=f"mensaje_{row['id']}.txt",
                    mime="text/plain",
                    key=f"download_{row['id']}"
                )
            
            # Sugerencia YAML automática
            st.subheader("🔧 Sugerencia para nlu.yml")
            
            # Determinar intent sugerido
            if row['intent_detected'] and row['intent_detected'] != 'No detectado':
                suggested_intent = row['intent_detected']
            else:
                suggested_intent = "nlu_fallback"
            
            yaml_suggestion = generate_yaml_suggestion(row['user_message'], suggested_intent)
            st.code(yaml_suggestion, language="yaml")
            
            # Botón para marcar como revisado (solo si existe la columna)
            if has_message_block:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(
                        "✅ Marcar como revisado",
                        key=f"reviewed_{row['id']}",
                        help="Eliminar de la lista de revisión"
                    ):
                        if update_needs_review_status(row['id'], False):
                            st.success("Marcado como revisado!")
                            st.rerun()
                        else:
                            st.error("Error al actualizar estado")
                
                with col2:
                    # Selector de intent para reasignar
                    new_intent = st.selectbox(
                        "Reasignar intent:",
                        ["Seleccionar...", "agendar_turno", "consultar_horarios", 
                         "consultar_requisitos", "cancelar_turno", "frase_ambigua", 
                         "consultar_disponibilidad", "nlu_fallback"],
                        key=f"intent_select_{row['id']}"
                    )
                    
                    if new_intent != "Seleccionar...":
                        st.info(f"Intent sugerido: {new_intent}")

# =====================================================
# PESTAÑA 3: FEEDBACK (CORREGIDA)
# =====================================================

def show_feedback_tab():
    """💬 Pestaña de feedback con subpestañas de 👎 y 👍"""
    st.header("💬 Feedback de Usuarios")
    st.write("Análisis de feedback directo de los usuarios")
    
    # Verificar si existen las columnas de feedback
    feedback_check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'conversation_logs' 
        AND column_name IN ('feedback_thumbs', 'feedback_comment')
    """
    
    feedback_columns_df = safe_query(feedback_check_query)
    has_feedback_columns = len(feedback_columns_df) >= 1
    
    if not has_feedback_columns:
        st.warning("⚠️ Las columnas de feedback no existen aún en la base de datos.")
        st.info("Usa el chatbot y da feedback con 👍/👎 para generar datos aquí.")
        
        if st.button("🔧 Agregar Columnas de Feedback"):
            if check_and_add_missing_columns():
                st.success("Columnas agregadas. Recarga la página.")
                st.rerun()
        return
    
    # Crear subpestañas para feedback negativo y positivo
    subtab1, subtab2 = st.tabs(["👎 Feedback Negativo", "👍 Feedback Positivo"])
    
    with subtab1:
        st.subheader("👎 Mensajes con Feedback Negativo")
        
        # Obtener feedback negativo
        negative_query = """
            SELECT 
                id, session_id, user_message, bot_response, 
                intent_detected, confidence, timestamp, feedback_comment
            FROM conversation_logs
            WHERE feedback_thumbs = -1
            ORDER BY timestamp DESC
            LIMIT 50
        """
        
        negative_df = safe_query(negative_query)
        
        if negative_df.empty:
            st.success("🎉 ¡No hay feedback negativo reciente!")
            st.info("Esto significa que los usuarios están satisfechos con las respuestas.")
            return
        
        st.write(f"📋 **{len(negative_df)} mensajes** con feedback negativo:")
        
        for idx, row in negative_df.iterrows():
            user_msg_preview = row['user_message'][:50] + "..." if len(row['user_message']) > 50 else row['user_message']
            
            with st.expander(f"👎 {user_msg_preview} • {row['timestamp'].strftime('%Y-%m-%d %H:%M')}"):
                # Mostrar conversación
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Mensaje del usuario:**")
                    st.write(row['user_message'])
                    st.write("**Intent detectado:**")
                    st.write(row['intent_detected'] or 'No detectado')
                    st.write("**Confianza:**")
                    st.write(f"{row['confidence']:.3f}" if row['confidence'] else "N/A")
                
                with col2:
                    st.write("**Respuesta del bot:**")
                    st.write(row['bot_response'])
                    st.write("**Comentario del usuario:**")
                    if row.get('feedback_comment'):
                        st.warning(f"💭 {row['feedback_comment']}")
                    else:
                        st.write("Sin comentario específico")
                
                # Sugerencia YAML
                st.subheader("🔧 Sugerencia para Mejora")
                yaml_suggestion = generate_yaml_suggestion(
                    row['user_message'], 
                    row['intent_detected'] or "nlu_fallback"
                )
                st.code(yaml_suggestion, language="yaml")
                
                st.info("💡 **Acción recomendada:** Revisar y mejorar la respuesta para este tipo de consulta")
    
    with subtab2:
        st.subheader("👍 Mensajes con Feedback Positivo")
        
        # Obtener feedback positivo
        positive_query = """
            SELECT 
                id, session_id, user_message, bot_response, 
                intent_detected, confidence, timestamp
            FROM conversation_logs
            WHERE feedback_thumbs = 1
            ORDER BY timestamp DESC
            LIMIT 50
        """
        
        positive_df = safe_query(positive_query)
        
        if positive_df.empty:
            st.info("📝 Aún no hay feedback positivo registrado.")
            st.write("Los usuarios pueden dar 👍 a las respuestas útiles del chatbot.")
            return
        
        st.write(f"📋 **{len(positive_df)} mensajes** con feedback positivo:")
        
        # Mostrar estadísticas de respuestas exitosas
        if not positive_df.empty:
            # Análisis de intents exitosos
            intent_success = positive_df['intent_detected'].value_counts()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Intents Más Exitosos")
                for intent, count in intent_success.head(5).items():
                    st.write(f"- **{intent or 'No detectado'}**: {count} éxitos")
            
            with col2:
                st.subheader("📊 Estadísticas de Éxito")
                avg_confidence = positive_df[positive_df['confidence'] > 0]['confidence'].mean()
                st.metric("Confianza promedio", f"{avg_confidence:.3f}" if avg_confidence else "N/A")
                st.metric("Total respuestas exitosas", len(positive_df))
        
        # Mostrar ejemplos de respuestas exitosas
        st.subheader("✅ Ejemplos de Respuestas Exitosas")
        
        for idx, row in positive_df.head(10).iterrows():
            user_msg_preview = row['user_message'][:50] + "..." if len(row['user_message']) > 50 else row['user_message']
            
            with st.expander(f"👍 {user_msg_preview} • Confianza: {row['confidence']:.2f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Mensaje del usuario:**")
                    st.write(row['user_message'])
                    st.write("**Intent detectado:**")
                    st.write(row['intent_detected'] or 'No detectado')
                
                with col2:
                    st.write("**Respuesta exitosa:**")
                    st.write(row['bot_response'])
                    st.write("**Timestamp:**")
                    st.write(row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'))
                
                st.success("💡 **Esta respuesta fue útil para el usuario** - Considerar como referencia para casos similares")

# =====================================================
# FUNCIÓN PRINCIPAL DEL DASHBOARD
# =====================================================

def show_learning_dashboard():
    """Dashboard principal con 3 pestañas simplificadas"""
    
    st.title("📊 Dashboard de Aprendizaje del Chatbot")
    st.markdown("---")
    
    # Verificar conexión a base de datos
    if not get_db_connection():
        st.error("❌ No se puede conectar a la base de datos")
        st.info("Asegúrate de que:")
        st.markdown("""
        - PostgreSQL esté ejecutándose
        - La base de datos 'chatbotdb' exista
        - Las credenciales sean correctas (user: botuser, password: root)
        - Las tablas de conversación estén creadas
        """)
        return
    
    # Sidebar con controles
    with st.sidebar:
        st.header("🎛️ Controles del Dashboard")
        
        # Botón de actualizar
        if st.button("🔄 Actualizar Datos", help="Recargar información desde la BD"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Verificar estructura de base de datos
        st.subheader("🔧 Estado de la BD")
        
        if st.button("📋 Verificar Columnas"):
            check_and_add_missing_columns()
            st.rerun()
        
        st.markdown("---")
        
        # Información del sistema
        st.subheader("ℹ️ Estado del Sistema")
        
        # Verificar si hay datos
        test_query = "SELECT COUNT(*) as count FROM conversation_logs"
        test_df = safe_query(test_query)
        
        if not test_df.empty:
            total_messages = test_df.iloc[0]['count']
            st.metric("Total mensajes", total_messages)
            
            if total_messages > 0:
                st.success("✅ Sistema funcionando")
            else:
                st.warning("⚠️ Sin datos aún")
        
        st.markdown("---")
        
        # Acciones de exportación
        st.subheader("📥 Exportación")
        
        if st.button("📄 Generar Reporte Completo"):
            # Obtener datos para reporte
            report_query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN needs_review = TRUE THEN 1 END) as needs_review,
                    COUNT(CASE WHEN feedback_thumbs = 1 THEN 1 END) as positive,
                    COUNT(CASE WHEN feedback_thumbs = -1 THEN 1 END) as negative
                FROM conversation_logs
                WHERE timestamp >= NOW() - INTERVAL '30 days'
            """
            
            report_df = safe_query(report_query)
            
            if not report_df.empty:
                stats = report_df.iloc[0]
                
                report_content = f"""# Reporte de Dashboard de Aprendizaje
Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Resumen Ejecutivo
- Total conversaciones: {stats['total']}
- Necesitan revisión: {stats['needs_review']}
- Feedback positivo: {stats['positive']}
- Feedback negativo: {stats['negative']}

## Recomendaciones
- Revisar {stats['needs_review']} mensajes marcados
- Analizar {stats['negative']} casos de feedback negativo
- Mantener calidad basada en {stats['positive']} casos exitosos
"""
                
                st.download_button(
                    label="📄 Descargar Reporte",
                    data=report_content,
                    file_name=f"reporte_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
    
    # Pestañas principales del dashboard
    tab1, tab2, tab3 = st.tabs([
        "📈 Resumen",
        "🗂️ Guardados (No interpretados)", 
        "💬 Feedback (👎 / 👍)"
    ])
    
    with tab1:
        show_summary_tab()
    
    with tab2:
        show_saved_tab()
    
    with tab3:
        show_feedback_tab()

# =====================================================
# PUNTO DE ENTRADA
# =====================================================

if __name__ == "__main__":
    show_learning_dashboard()