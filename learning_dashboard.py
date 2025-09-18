# learning_dashboard.py
# Dashboard de aprendizaje para el chatbot usando Streamlit

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from conversation_logger import setup_learning_system
from typing import Dict, List
import psycopg2
from collections import Counter
import re

class LearningDashboard:
    def __init__(self, db_config):
        self.db_config = db_config
    
    def get_connection(self):
        """Obtiene conexión segura a la base de datos"""
        try:
            return psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                client_encoding='utf8'
            )
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return None
    
    def safe_query(self, query, params=None):
        """Ejecuta queries de forma segura"""
        conn = self.get_connection()
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

def show_learning_dashboard():
    """Dashboard principal de aprendizaje"""
    
    st.title("📊 Dashboard de Aprendizaje del Chatbot")
    st.markdown("---")
    
    # Configurar conexión
    db_config = {
        'host': 'localhost',
        'database': 'chatbotdb',
        'user': 'botuser',
        'password': 'root'
    }
    
    try:
        dashboard = LearningDashboard(db_config)
        
        # Sidebar con controles
        with st.sidebar:
            st.header("🎛️ Controles")
            
            # Actualizar datos
            if st.button("🔄 Actualizar Datos"):
                st.cache_data.clear()
                st.rerun()
            
            # Filtros de fecha
            st.subheader("📅 Filtros")
            date_range = st.selectbox(
                "Rango de fechas:",
                ["Últimos 7 días", "Últimos 30 días", "Últimos 90 días", "Todo el tiempo"]
            )
            
            # Filtros de confianza
            min_confidence = st.slider("Confianza mínima:", 0.0, 1.0, 0.0, 0.1)
            
            st.markdown("---")
            st.markdown("### 📋 Acciones Rápidas")
            
            if st.button("📥 Exportar Reporte"):
                generate_export_report(dashboard)
            
            if st.button("🧹 Limpiar Datos Antiguos"):
                clean_old_data(dashboard)
        
        # Pestañas principales
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Estadísticas Generales",
            "💬 Todos los Registros", 
            "❌ Interacciones Fallidas",
            "🔤 Palabras Frecuentes",
            "💡 Sugerencias de Mejora"
        ])
        
        with tab1:
            show_general_statistics(dashboard, date_range)
        
        with tab2:
            show_all_conversations(dashboard, min_confidence, date_range)
        
        with tab3:
            show_failed_interactions(dashboard, date_range)
        
        with tab4:
            show_word_patterns(dashboard, date_range)
        
        with tab5:
            show_improvement_suggestions(dashboard)
            
    except Exception as e:
        st.error(f"❌ Error conectando al sistema de aprendizaje: {e}")
        st.info("Asegúrate de que:")
        st.markdown("""
        - PostgreSQL esté ejecutándose
        - Las tablas de aprendizaje estén creadas
        - Las credenciales de BD sean correctas
        """)

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_cached_stats(db_config, date_range):
    """Obtiene estadísticas con cache"""
    dashboard = LearningDashboard(db_config)
    return get_general_stats_data(dashboard, date_range)

def get_date_filter(date_range):
    """Obtiene el filtro de fecha basado en la selección"""
    if date_range == "Últimos 7 días":
        return datetime.now() - timedelta(days=7)
    elif date_range == "Últimos 30 días":
        return datetime.now() - timedelta(days=30)
    elif date_range == "Últimos 90 días":
        return datetime.now() - timedelta(days=90)
    else:
        return datetime.now() - timedelta(days=365*10)  # Todo el tiempo

def get_general_stats_data(dashboard, date_range):
    """Obtiene datos de estadísticas generales"""
    date_filter = get_date_filter(date_range)
    
    # Estadísticas básicas con nombres de columnas correctos y conversión de tipos
    stats_query = """
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(DISTINCT session_id) as unique_sessions,
            ROUND(AVG(CASE 
                WHEN confidence IS NOT NULL AND confidence > 0 
                THEN confidence::numeric 
                ELSE NULL 
            END), 2) as avg_confidence,
            COUNT(CASE 
                WHEN intent_detected = 'No detectado' 
                OR intent_detected IS NULL 
                OR confidence < 0.5 
                THEN 1 
            END) as problematic_messages
        FROM conversation_logs
        WHERE timestamp >= %s
    """
    
    stats_df = dashboard.safe_query(stats_query, (date_filter,))
    
    if stats_df.empty:
        return {
            'total_conversations': 0,
            'unique_sessions': 0,
            'avg_confidence': 0.0,
            'problematic_messages': 0,
            'daily_usage': [],
            'intent_stats': []
        }
    
    stats = stats_df.iloc[0].to_dict()
    
    # Actividad diaria
    daily_query = """
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as conversations,
            COUNT(DISTINCT session_id) as sessions
        FROM conversation_logs
        WHERE timestamp >= %s
        GROUP BY DATE(timestamp)
        ORDER BY date
    """
    
    daily_df = dashboard.safe_query(daily_query, (date_filter,))
    daily_usage = daily_df.values.tolist() if not daily_df.empty else []
    
    # Estadísticas de intents con conversión de tipos
    intent_query = """
        SELECT 
            COALESCE(intent_detected, 'No detectado') as intent,
            COUNT(*) as count,
            ROUND(AVG(CASE 
                WHEN confidence IS NOT NULL 
                THEN confidence::numeric
                ELSE 0::numeric
            END), 2) as avg_confidence
        FROM conversation_logs
        WHERE timestamp >= %s
        GROUP BY intent_detected
        ORDER BY count DESC
    """
    
    intent_df = dashboard.safe_query(intent_query, (date_filter,))
    intent_stats = intent_df.values.tolist() if not intent_df.empty else []
    
    stats.update({
        'daily_usage': daily_usage,
        'intent_stats': intent_stats
    })
    
    return stats

def show_general_statistics(dashboard, date_range):
    """Muestra estadísticas generales del chatbot"""
    
    st.header("📊 Estadísticas Generales")
    
    try:
        stats = get_cached_stats(dashboard.db_config, date_range)
        
        if not stats or stats['total_conversations'] == 0:
            st.warning("⚠️ No hay datos disponibles para el rango seleccionado. Interactúa con el chatbot para generar estadísticas.")
            return
        
        # Métricas principales en cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💬 Total Conversaciones", 
                stats.get('total_conversations', 0),
                help="Número total de mensajes procesados"
            )
        
        with col2:
            st.metric(
                "👥 Sesiones Únicas", 
                stats.get('unique_sessions', 0),
                help="Usuarios únicos que han interactuado"
            )
        
        with col3:
            confidence_val = stats.get('avg_confidence', 0)
            st.metric(
                "🎯 Confianza Promedio", 
                f"{confidence_val:.2f}" if confidence_val else "0.00",
                help="Nivel promedio de confianza en la detección de intents"
            )
        
        with col4:
            problematic = stats.get('problematic_messages', 0)
            st.metric(
                "⚠️ Mensajes Problemáticos", 
                problematic,
                help="Mensajes con confianza menor a 0.5"
            )
        
        st.markdown("---")
        
        # Gráficos en dos columnas
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de uso diario
            st.subheader("📅 Actividad Diaria")
            daily_data = stats.get('daily_usage', [])
            
            if daily_data:
                df_daily = pd.DataFrame(daily_data, columns=['Fecha', 'Conversaciones', 'Sesiones'])
                df_daily['Fecha'] = pd.to_datetime(df_daily['Fecha'])
                
                fig_daily = px.line(
                    df_daily, 
                    x='Fecha', 
                    y='Conversaciones',
                    title='Conversaciones por Día',
                    markers=True
                )
                fig_daily.update_layout(
                    xaxis_title="Fecha",
                    yaxis_title="Número de Conversaciones",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_daily, use_container_width=True)
            else:
                st.info("No hay suficientes datos para mostrar el gráfico diario")
        
        with col2:
            # Gráfico de distribución de intents
            st.subheader("🎯 Distribución de Intents")
            intent_data = stats.get('intent_stats', [])
            
            if intent_data and len(intent_data) > 0:
                df_intents = pd.DataFrame(
                    intent_data[:10], 
                    columns=['Intent', 'Frecuencia', 'Confianza Promedio']
                )
                
                fig_intents = px.bar(
                    df_intents,
                    x='Frecuencia',
                    y='Intent',
                    orientation='h',
                    title='Top 10 Intents Más Utilizados',
                    color='Confianza Promedio',
                    color_continuous_scale='RdYlGn'
                )
                fig_intents.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_intents, use_container_width=True)
            else:
                st.info("No hay datos de intents disponibles")
        
        # Análisis de rendimiento
        st.markdown("---")
        st.subheader("📈 Análisis de Rendimiento")
        
        if intent_data:
            # Tabla de rendimiento por intent
            performance_df = pd.DataFrame(intent_data, columns=['Intent', 'Usos', 'Confianza Promedio'])
            performance_df['Estado'] = performance_df['Confianza Promedio'].apply(
                lambda x: '🟢 Excelente' if x > 0.8 else '🟡 Bueno' if x > 0.6 else '🔴 Necesita Mejora'
            )
            
            st.dataframe(
                performance_df[['Intent', 'Usos', 'Confianza Promedio', 'Estado']],
                use_container_width=True,
                hide_index=True
            )
            
            # Alerta para intents problemáticos
            problematic_intents = performance_df[performance_df['Confianza Promedio'] < 0.7]
            if not problematic_intents.empty:
                st.warning(f"⚠️ {len(problematic_intents)} intents tienen confianza baja y necesitan más ejemplos de entrenamiento")
        
    except Exception as e:
        st.error(f"Error cargando estadísticas: {e}")

def show_all_conversations(dashboard, min_confidence=0.0, date_range="Últimos 30 días"):
    """Muestra todos los registros de conversaciones"""
    
    st.header("💬 Registro Completo de Conversaciones")
    
    try:
        date_filter = get_date_filter(date_range)
        
        # Query con nombres de columnas correctos
        query = """
            SELECT 
                timestamp,
                session_id,
                user_message,
                bot_response,
                COALESCE(intent_detected, 'No detectado') as intent_detected,
                COALESCE(confidence, 0) as confidence,
                feedback_score
            FROM conversation_logs
            WHERE timestamp >= %s
            AND (confidence >= %s OR confidence IS NULL)
            ORDER BY timestamp DESC
            LIMIT 500
        """
        
        conversations_df = dashboard.safe_query(query, (date_filter, min_confidence))
        
        if conversations_df.empty:
            st.info("No hay conversaciones registradas para los filtros seleccionados.")
            return
        
        # Convertir a lista de diccionarios para compatibilidad
        conversations = conversations_df.to_dict('records')
        
        # Filtros adicionales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            unique_intents = conversations_df['intent_detected'].unique().tolist()
            filter_intent = st.selectbox(
                "Filtrar por Intent:",
                ["Todos"] + unique_intents
            )
        
        with col2:
            unique_sessions = conversations_df['session_id'].unique().tolist()
            filter_session = st.selectbox(
                "Filtrar por Sesión:",
                ["Todas"] + unique_sessions
            )
        
        with col3:
            show_only_problems = st.checkbox("Solo mostrar problemáticos", value=False)
        
        # Aplicar filtros
        filtered_df = conversations_df.copy()
        
        if filter_intent != "Todos":
            filtered_df = filtered_df[filtered_df['intent_detected'] == filter_intent]
        
        if filter_session != "Todas":
            filtered_df = filtered_df[filtered_df['session_id'] == filter_session]
        
        if show_only_problems:
            filtered_df = filtered_df[
                (filtered_df['confidence'] < 0.7) | 
                (filtered_df['feedback_score'] <= 2) |
                (filtered_df['intent_detected'] == 'No detectado')
            ]
        
        st.write(f"Mostrando {len(filtered_df)} de {len(conversations_df)} conversaciones")
        
        # Tabla de conversaciones
        if not filtered_df.empty:
            # Preparar datos para mostrar
            display_data = []
            for _, row in filtered_df.iterrows():
                timestamp = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                
                # Truncar mensajes largos
                user_msg = row['user_message'][:80] + "..." if len(str(row['user_message'])) > 80 else row['user_message']
                bot_msg = str(row['bot_response'])[:80] + "..." if row['bot_response'] and len(str(row['bot_response'])) > 80 else row['bot_response']
                
                # Color coding para confianza
                confidence = row['confidence']
                if confidence and confidence > 0:
                    if confidence > 0.8:
                        conf_display = f"🟢 {confidence:.2f}"
                    elif confidence > 0.6:
                        conf_display = f"🟡 {confidence:.2f}"
                    else:
                        conf_display = f"🔴 {confidence:.2f}"
                else:
                    conf_display = "➖"
                
                display_data.append({
                    'Timestamp': timestamp,
                    'Sesión': str(row['session_id'])[-8:],  # Solo últimos 8 caracteres
                    'Mensaje Usuario': user_msg,
                    'Respuesta Bot': bot_msg or "Sin respuesta",
                    'Intent': row['intent_detected'],
                    'Confianza': conf_display,
                    'Feedback': row['feedback_score'] if pd.notna(row['feedback_score']) else "➖"
                })
            
            st.dataframe(
                pd.DataFrame(display_data),
                use_container_width=True,
                hide_index=True
            )
            
            # Estadísticas de la vista actual
            st.subheader("📊 Estadísticas de Vista Actual")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                valid_confidence = filtered_df[filtered_df['confidence'] > 0]['confidence']
                avg_conf = valid_confidence.mean() if not valid_confidence.empty else 0
                st.metric("Confianza Promedio", f"{avg_conf:.2f}")
            
            with col2:
                problematic = len(filtered_df[
                    (filtered_df['confidence'] < 0.7) | 
                    (filtered_df['intent_detected'] == 'No detectado')
                ])
                st.metric("Mensajes Problemáticos", problematic)
            
            with col3:
                unique_intents = filtered_df['intent_detected'].nunique()
                st.metric("Intents Únicos", unique_intents)
        
    except Exception as e:
        st.error(f"Error cargando conversaciones: {e}")

def show_failed_interactions(dashboard, date_range):
    """Muestra interacciones fallidas con recomendaciones"""
    
    st.header("❌ Interacciones Fallidas y Recomendaciones")
    
    try:
        date_filter = get_date_filter(date_range)
        
        # Pestañas para diferentes tipos de problemas
        subtab1, subtab2, subtab3 = st.tabs([
            "🔴 Baja Confianza",
            "🚫 Frases No Entendidas", 
            "👎 Feedback Negativo"
        ])
        
        with subtab1:
            st.subheader("Mensajes con Baja Confianza")
            
            low_confidence_query = """
                SELECT 
                    timestamp, session_id, user_message, bot_response,
                    intent_detected, confidence
                FROM conversation_logs
                WHERE timestamp >= %s 
                AND confidence IS NOT NULL 
                AND confidence < 0.7
                ORDER BY timestamp DESC
                LIMIT 50
            """
            
            low_confidence_df = dashboard.safe_query(low_confidence_query, (date_filter,))
            
            if not low_confidence_df.empty:
                for _, row in low_confidence_df.iterrows():
                    with st.expander(f"🔴 {str(row['user_message'])[:60]}... (Confianza: {row['confidence']:.2f})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Mensaje del usuario:**")
                            st.write(row['user_message'])
                            st.write("**Intent detectado:**", row['intent_detected'])
                            st.write("**Confianza:**", f"{row['confidence']:.2f}")
                        
                        with col2:
                            st.write("**Respuesta del bot:**")
                            st.write(row['bot_response'] or "Sin respuesta")
                            st.write("**Timestamp:**", row['timestamp'])
                        
                        # Sugerencia de mejora
                        st.info(f"💡 **Sugerencia:** Agregar más ejemplos del tipo '{row['user_message']}' al intent `{row['intent_detected']}` en nlu.yml")
            else:
                st.success("No hay mensajes con baja confianza recientes.")
        
        with subtab2:
            st.subheader("Frases Frecuentes No Entendidas")
            
            unknown_phrases_query = """
                SELECT 
                    user_message,
                    COUNT(*) as frequency,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen,
                    'frase_ambigua' as suggested_intent
                FROM conversation_logs
                WHERE timestamp >= %s
                AND (intent_detected = 'No detectado' OR intent_detected IS NULL)
                AND user_message IS NOT NULL
                GROUP BY user_message
                HAVING COUNT(*) > 1
                ORDER BY frequency DESC
                LIMIT 20
            """
            
            unknown_df = dashboard.safe_query(unknown_phrases_query, (date_filter,))
            
            if not unknown_df.empty:
                for idx, row in unknown_df.iterrows():
                    with st.expander(f"🚫 '{row['user_message']}' (aparece {row['frequency']} veces)"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Frase:**", row['user_message'])
                            st.write("**Frecuencia:**", row['frequency'])
                            st.write("**Primera vez vista:**", row['first_seen'])
                            st.write("**Última vez vista:**", row['last_seen'])
                        
                        with col2:
                            st.write("**Intent sugerido:**", row['suggested_intent'])
                            
                            # Selector para asignar intent
                            suggested_intent = st.selectbox(
                                "Asignar a intent:",
                                ["Seleccionar...", "agendar_turno", "consultar_horarios", "consultar_requisitos", 
                                 "cancelar_turno", "frase_ambigua", "consultar_disponibilidad"],
                                key=f"intent_{idx}"
                            )
                            
                            if st.button("✅ Marcar como Resuelto", key=f"resolve_{idx}"):
                                st.success("Marcado como resuelto!")
                        
                        # Generar código YAML
                        intent_to_use = suggested_intent if suggested_intent != "Seleccionar..." else row['suggested_intent']
                        st.code(f"""
# Agregar a nlu.yml bajo el intent apropiado:
- intent: {intent_to_use}
  examples: |
    - {row['user_message']}
                        """, language="yaml")
            else:
                st.success("No hay frases no entendidas frecuentes.")
        
        with subtab3:
            st.subheader("Conversaciones con Feedback Negativo")
            
            negative_feedback_query = """
                SELECT 
                    timestamp, session_id, user_message, bot_response,
                    intent_detected, confidence, feedback_score
                FROM conversation_logs
                WHERE timestamp >= %s
                AND feedback_score IS NOT NULL 
                AND feedback_score <= 2
                ORDER BY timestamp DESC
                LIMIT 20
            """
            
            negative_df = dashboard.safe_query(negative_feedback_query, (date_filter,))
            
            if not negative_df.empty:
                for _, row in negative_df.iterrows():
                    with st.expander(f"👎 Score: {row['feedback_score']}/5 - {str(row['user_message'])[:50]}..."):
                        st.write("**Mensaje:**", row['user_message'])
                        st.write("**Respuesta:**", row['bot_response'])
                        st.write("**Intent:**", row['intent_detected'])
                        st.write("**Confianza:**", row['confidence'])
                        st.write("**Score de feedback:**", f"{row['feedback_score']}/5")
                        
                        st.warning("💡 **Acción requerida:** Revisar y mejorar la respuesta para este tipo de consulta")
            else:
                st.success("No hay feedback negativo reciente.")
        
    except Exception as e:
        st.error(f"Error cargando interacciones fallidas: {e}")

def show_word_patterns(dashboard, date_range):
    """Muestra patrones de palabras y frases más frecuentes"""
    
    st.header("🔤 Análisis de Palabras y Frases Frecuentes")
    
    try:
        date_filter = get_date_filter(date_range)
        
        # Pestañas para diferentes tipos de patrones
        subtab1, subtab2 = st.tabs(["📝 Palabras", "💬 Frases"])
        
        with subtab1:
            st.subheader("Palabras Más Utilizadas")
            
            # Obtener mensajes para análisis de palabras
            messages_query = """
                SELECT user_message
                FROM conversation_logs
                WHERE timestamp >= %s
                AND user_message IS NOT NULL 
                AND user_message != ''
            """
            
            messages_df = dashboard.safe_query(messages_query, (date_filter,))
            
            if not messages_df.empty:
                # Extraer y contar palabras
                all_words = []
                for message in messages_df['user_message']:
                    if pd.notna(message):
                        # Limpiar y extraer palabras
                        words = re.findall(r'\b\w+\b', str(message).lower())
                        all_words.extend([w for w in words if len(w) > 2])
                
                if all_words:
                    # Contar frecuencias
                    word_counts = Counter(all_words)
                    
                    # Convertir a DataFrame
                    word_df = pd.DataFrame([
                        {'Palabra': word, 'Frecuencia': count}
                        for word, count in word_counts.most_common(20)
                    ])
                    
                    # Gráfico de palabras más frecuentes
                    fig_words = px.bar(
                        word_df,
                        x='Frecuencia',
                        y='Palabra',
                        orientation='h',
                        title='Top 20 Palabras Más Frecuentes',
                        color='Frecuencia',
                        color_continuous_scale='viridis'
                    )
                    fig_words.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_words, use_container_width=True)
                    
                    # Tabla de palabras
                    st.dataframe(word_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay palabras suficientes para analizar.")
            else:
                st.info("No hay datos de palabras para el rango seleccionado.")
        
        with subtab2:
            st.subheader("Frases Más Utilizadas")
            
            # Frases frecuentes
            phrases_query = """
                SELECT 
                    user_message as frase,
                    COUNT(*) as frecuencia,
                    MAX(intent_detected) as intent_principal
                FROM conversation_logs
                WHERE timestamp >= %s
                AND user_message IS NOT NULL 
                AND user_message != ''
                GROUP BY user_message
                HAVING COUNT(*) > 1
                ORDER BY frecuencia DESC
                LIMIT 20
            """
            
            phrases_df = dashboard.safe_query(phrases_query, (date_filter,))
            
            if not phrases_df.empty:
                # Renombrar columnas para visualización
                phrases_display = phrases_df.copy()
                phrases_display.columns = ['Frase', 'Frecuencia', 'Intent Principal']
                
                st.dataframe(phrases_display, use_container_width=True, hide_index=True)
                
                # Análisis de frases por intent
                if 'Intent Principal' in phrases_display.columns:
                    st.subheader("📊 Distribución de Frases por Intent")
                    
                    intent_phrase_count = phrases_display.groupby('Intent Principal').size().reset_index(name='Cantidad')
                    
                    if not intent_phrase_count.empty:
                        fig_intent_phrases = px.pie(
                            intent_phrase_count,
                            values='Cantidad',
                            names='Intent Principal',
                            title='Distribución de Frases por Intent'
                        )
                        st.plotly_chart(fig_intent_phrases, use_container_width=True)
            else:
                st.info("No hay frases frecuentes para el rango seleccionado.")
        
        # Insights automáticos
        st.markdown("---")
        st.subheader("🔍 Insights Automáticos")
        
        # Obtener estadísticas para insights
        insights_query = """
            SELECT 
                COUNT(DISTINCT user_message) as unique_messages,
                COUNT(*) as total_messages,
                COUNT(DISTINCT intent_detected) as unique_intents
            FROM conversation_logs
            WHERE timestamp >= %s
        """
        
        insights_df = dashboard.safe_query(insights_query, (date_filter,))
        
        if not insights_df.empty:
            stats = insights_df.iloc[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Mensajes Únicos", stats['unique_messages'])
            
            with col2:
                st.metric("Total Mensajes", stats['total_messages'])
            
            with col3:
                st.metric("Intents Únicos", stats['unique_intents'])
            
            # Calcular diversidad
            if stats['total_messages'] > 0:
                diversity_ratio = stats['unique_messages'] / stats['total_messages']
                if diversity_ratio > 0.8:
                    st.success("📈 **Alta diversidad de mensajes:** Los usuarios usan variedad de expresiones.")
                elif diversity_ratio < 0.3:
                    st.warning("🔄 **Mensajes repetitivos:** Los usuarios tienden a usar las mismas frases.")
                else:
                    st.info("📊 **Diversidad moderada:** Balance normal entre repetición y variedad.")
        
    except Exception as e:
        st.error(f"Error cargando patrones de palabras: {e}")

def show_improvement_suggestions(dashboard):
    """Muestra sugerencias detalladas de mejora"""
    
    st.header("💡 Sugerencias de Mejora del Modelo")
    
    try:
        # Obtener datos para generar sugerencias con conversión de tipos
        stats_query = """
            SELECT 
                COUNT(*) as total_conversations,
                AVG(confidence::numeric) as avg_confidence,
                COUNT(CASE WHEN confidence < 0.7 THEN 1 END) as low_confidence_count,
                COUNT(CASE WHEN intent_detected = 'No detectado' OR intent_detected IS NULL THEN 1 END) as undetected_count
            FROM conversation_logs
            WHERE timestamp >= NOW() - INTERVAL '30 days'
        """
        
        stats_df = dashboard.safe_query(stats_query)
        
        if not stats_df.empty:
            stats = stats_df.iloc[0]
            suggestions = []
            
            # Generar sugerencias basadas en estadísticas
            if stats['avg_confidence'] and stats['avg_confidence'] < 0.7:
                suggestions.append({
                    'type': '⚠️ Baja Confianza General',
                    'description': f"La confianza promedio es {stats['avg_confidence']:.2f}. Se recomienda revisar y ampliar los datos de entrenamiento.",
                    'action': "Agregar más ejemplos de entrenamiento para los intents principales"
                })
            
            if stats['low_confidence_count'] > stats['total_conversations'] * 0.3:
                suggestions.append({
                    'type': '🔴 Muchos Mensajes con Baja Confianza',
                    'description': f"{stats['low_confidence_count']} de {stats['total_conversations']} mensajes tienen baja confianza.",
                    'action': "Revisar los intents con baja confianza y agregar más ejemplos de entrenamiento"
                })
            
            if stats['undetected_count'] > 0:
                suggestions.append({
                    'type': '❓ Intents No Detectados',
                    'description': f"Se encontraron {stats['undetected_count']} mensajes sin intent detectado.",
                    'action': "Revisar estos mensajes y crear nuevos intents o mejorar los existentes"
                })
            
            # Mostrar sugerencias
            if suggestions:
                for i, suggestion in enumerate(suggestions):
                    with st.expander(f"{suggestion['type']}", expanded=True):
                        st.write(f"**Descripción:** {suggestion['description']}")
                        st.write(f"**Acción recomendada:** {suggestion['action']}")
            else:
                st.success("🎉 ¡El chatbot está funcionando bien! No se detectaron problemas importantes.")
        
        st.markdown("---")
        
        # Exportar datos para entrenamiento
        st.subheader("📥 Exportar Datos para Reentrenamiento")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generar Archivo YAML"):
                # Obtener frases no entendidas
                unknown_query = """
                    SELECT 
                        user_message,
                        COUNT(*) as frequency
                    FROM conversation_logs
                    WHERE (intent_detected = 'No detectado' OR intent_detected IS NULL)
                    AND user_message IS NOT NULL
                    GROUP BY user_message
                    HAVING COUNT(*) > 1
                    ORDER BY frequency DESC
                    LIMIT 20
                """
                
                unknown_df = dashboard.safe_query(unknown_query)
                
                if not unknown_df.empty:
                    yaml_content = generate_yaml_training_data(unknown_df)
                    
                    st.text_area(
                        "Contenido para nlu.yml:",
                        value=yaml_content,
                        height=400,
                        help="Copia este contenido y agrégalo a tu archivo nlu.yml"
                    )
                    
                    # Botón de descarga
                    st.download_button(
                        label="💾 Descargar YAML",
                        data=yaml_content,
                        file_name=f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml",
                        mime="text/yaml"
                    )
                else:
                    st.info("No hay frases nuevas para exportar.")
        
        with col2:
            if st.button("📊 Generar Reporte Completo"):
                report = generate_full_analysis_report(dashboard)
                
                st.download_button(
                    label="📄 Descargar Reporte Markdown",
                    data=report,
                    file_name=f"analisis_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
                
                st.success("Reporte generado! Haz clic para descargar.")
        
        # Métricas de mejora
        st.markdown("---")
        st.subheader("📈 Métricas de Mejora Potencial")
        
        if not stats_df.empty:
            # Obtener datos adicionales
            unknown_count_query = """
                SELECT COUNT(DISTINCT user_message) as unknown_phrases
                FROM conversation_logs
                WHERE (intent_detected = 'No detectado' OR intent_detected IS NULL)
                AND user_message IS NOT NULL
            """
            
            unknown_count_df = dashboard.safe_query(unknown_count_query)
            unknown_count = unknown_count_df.iloc[0]['unknown_phrases'] if not unknown_count_df.empty else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Frases a Mejorar",
                    unknown_count,
                    help="Frases únicas que el modelo no entiende bien"
                )
            
            with col2:
                st.metric(
                    "Interacciones Fallidas",
                    int(stats['low_confidence_count']),
                    help="Conversaciones que necesitan atención"
                )
            
            with col3:
                improvement_potential = unknown_count + int(stats['low_confidence_count'])
                total_conversations = int(stats['total_conversations'])
                improvement_percentage = (improvement_potential / total_conversations) * 100 if total_conversations > 0 else 0
                
                st.metric(
                    "Potencial de Mejora",
                    f"{improvement_percentage:.1f}%",
                    help="Porcentaje de conversaciones que se podrían mejorar"
                )
        
    except Exception as e:
        st.error(f"Error generando sugerencias: {e}")

def generate_yaml_training_data(unknown_df):
    """Genera contenido YAML para entrenamiento"""
    yaml_content = [
        "# Nuevos datos de entrenamiento basados en conversaciones reales",
        f"# Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# INSTRUCCIONES: Copia las líneas apropiadas a tu archivo nlu.yml\n"
    ]
    
    yaml_content.append("# Intent sugerido: frase_ambigua")
    yaml_content.append("# Agregar estas líneas bajo '- intent: frase_ambigua' en nlu.yml:")
    yaml_content.append("# examples: |")
    
    for _, row in unknown_df.iterrows():
        yaml_content.append(f"#   - {row['user_message']}  # (frecuencia: {row['frequency']})")
    
    yaml_content.append("")
    yaml_content.append("# También considera crear nuevos intents específicos si estas frases")
    yaml_content.append("# representan necesidades particulares de los usuarios")
    
    return "\n".join(yaml_content)

def generate_full_analysis_report(dashboard):
    """Genera reporte completo de análisis"""
    # Obtener estadísticas básicas con conversión de tipos
    stats_query = """
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(DISTINCT session_id) as unique_sessions,
            AVG(confidence::numeric) as avg_confidence,
            COUNT(CASE WHEN confidence < 0.7 THEN 1 END) as low_confidence_count
        FROM conversation_logs
        WHERE timestamp >= NOW() - INTERVAL '30 days'
    """
    
    stats_df = dashboard.safe_query(stats_query)
    
    report = [
        f"# Reporte Completo de Análisis del Chatbot",
        f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        
        "## Resumen Ejecutivo"
    ]
    
    if not stats_df.empty:
        stats = stats_df.iloc[0]
        report.extend([
            f"- Total de conversaciones analizadas: {int(stats['total_conversations'])}",
            f"- Sesiones únicas: {int(stats['unique_sessions'])}",
            f"- Confianza promedio del modelo: {stats['avg_confidence']:.2f}" if stats['avg_confidence'] else "- Confianza promedio del modelo: N/A",
            f"- Mensajes problemáticos identificados: {int(stats['low_confidence_count'])}\n"
        ])
    
    # Obtener distribución de intents con conversión de tipos
    intent_query = """
        SELECT 
            intent_detected,
            COUNT(*) as count,
            AVG(confidence::numeric) as avg_confidence
        FROM conversation_logs
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY intent_detected
        ORDER BY count DESC
        LIMIT 10
    """
    
    intent_df = dashboard.safe_query(intent_query)
    
    report.append("## Análisis Detallado\n### Rendimiento por Intent")
    
    if not intent_df.empty:
        for _, row in intent_df.iterrows():
            intent = row['intent_detected'] or 'No detectado'
            count = int(row['count'])
            avg_conf = row['avg_confidence'] or 0
            status = "✅ Excelente" if avg_conf > 0.8 else "⚠️ Necesita mejora" if avg_conf < 0.7 else "✅ Bueno"
            report.append(f"- **{intent}**: {count} usos, confianza {avg_conf:.2f} {status}")
    
    # Obtener frases no entendidas
    unknown_query = """
        SELECT user_message, COUNT(*) as frequency
        FROM conversation_logs
        WHERE (intent_detected = 'No detectado' OR intent_detected IS NULL)
        AND user_message IS NOT NULL
        AND timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY user_message
        HAVING COUNT(*) > 1
        ORDER BY frequency DESC
        LIMIT 10
    """
    
    unknown_df = dashboard.safe_query(unknown_query)
    
    report.append("\n### Recomendaciones de Mejora")
    
    if not unknown_df.empty:
        report.append("#### Frases para agregar al entrenamiento:")
        for _, row in unknown_df.iterrows():
            report.append(f"- '{row['user_message']}' (frecuencia: {int(row['frequency'])})")
    
    report.append(f"\n---\nReporte generado automáticamente por el sistema de aprendizaje del chatbot.")
    
    return "\n".join(report)

def generate_export_report(dashboard):
    """Genera y descarga reporte de exportación"""
    try:
        report = generate_full_analysis_report(dashboard)
        st.download_button(
            label="📄 Descargar Reporte de Análisis",
            data=report,
            file_name=f"reporte_exportacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        st.success("Reporte de exportación generado!")
    except Exception as e:
        st.error(f"Error generando reporte de exportación: {e}")

def clean_old_data(dashboard):
    """Limpia datos antiguos (función placeholder)"""
    st.info("Funcionalidad de limpieza en desarrollo. Por ahora, los datos se mantienen para análisis histórico.")

if __name__ == "__main__":
    show_learning_dashboard()