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

def show_learning_dashboard():
    """Dashboard principal de aprendizaje"""
    
    st.title("📊 Dashboard de Aprendizaje del Chatbot")
    st.markdown("---")
    
    # Configurar conexión
    DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'
    
    try:
        logger = setup_learning_system(DATABASE_URL)
        
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
                generate_export_report(logger)
            
            if st.button("🧹 Limpiar Datos Antiguos"):
                clean_old_data(logger)
        
        # Pestañas principales
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Estadísticas Generales",
            "💬 Todos los Registros", 
            "❌ Interacciones Fallidas",
            "🔤 Palabras Frecuentes",
            "💡 Sugerencias de Mejora"
        ])
        
        with tab1:
            show_general_statistics(logger)
        
        with tab2:
            show_all_conversations(logger, min_confidence)
        
        with tab3:
            show_failed_interactions(logger)
        
        with tab4:
            show_word_patterns(logger)
        
        with tab5:
            show_improvement_suggestions(logger)
            
    except Exception as e:
        st.error(f"❌ Error conectando al sistema de aprendizaje: {e}")
        st.info("Asegúrate de que:")
        st.markdown("""
        - PostgreSQL esté ejecutándose
        - Las tablas de aprendizaje estén creadas
        - Las credenciales de BD sean correctas
        """)

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_cached_stats(database_url: str):
    """Obtiene estadísticas con cache"""
    logger = setup_learning_system(database_url)
    return logger.get_conversation_stats()

def show_general_statistics(logger):
    """Muestra estadísticas generales del chatbot"""
    
    st.header("📊 Estadísticas Generales")
    
    try:
        stats = get_cached_stats('postgresql://botuser:root@localhost:5432/chatbotdb')
        
        if not stats:
            st.warning("⚠️ No hay datos disponibles aún. Interactúa con el chatbot para generar estadísticas.")
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
            confidence_val = stats.get('average_confidence', 0)
            confidence_color = "normal" if confidence_val > 0.7 else "inverse"
            st.metric(
                "🎯 Confianza Promedio", 
                f"{confidence_val:.2f}",
                help="Nivel promedio de confianza en la detección de intents"
            )
        
        with col4:
            problematic = stats.get('low_confidence_count', 0)
            st.metric(
                "⚠️ Mensajes Problemáticos", 
                problematic,
                help="Mensajes con confianza menor a 0.7"
            )
        
        st.markdown("---")
        
        # Gráficos en dos columnas
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de uso diario
            st.subheader("📅 Actividad Diaria")
            daily_data = stats.get('daily_usage', [])
            
            if daily_data:
                df_daily = pd.DataFrame(daily_data, columns=['Fecha', 'Conversaciones'])
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

def show_all_conversations(logger, min_confidence=0.0):
    """Muestra todos los registros de conversaciones"""
    
    st.header("💬 Registro Completo de Conversaciones")
    
    try:
        conversations = logger.get_all_conversations(limit=500)
        
        if not conversations:
            st.info("No hay conversaciones registradas aún.")
            return
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_intent = st.selectbox(
                "Filtrar por Intent:",
                ["Todos"] + list(set([c['intent_detected'] for c in conversations if c['intent_detected']]))
            )
        
        with col2:
            filter_session = st.selectbox(
                "Filtrar por Sesión:",
                ["Todas"] + list(set([c['session_id'] for c in conversations]))
            )
        
        with col3:
            show_only_problems = st.checkbox("Solo mostrar problemáticos", value=False)
        
        # Aplicar filtros
        filtered_conversations = conversations
        
        if filter_intent != "Todos":
            filtered_conversations = [c for c in filtered_conversations if c['intent_detected'] == filter_intent]
        
        if filter_session != "Todas":
            filtered_conversations = [c for c in filtered_conversations if c['session_id'] == filter_session]
        
        if show_only_problems:
            filtered_conversations = [
                c for c in filtered_conversations 
                if (c['confidence'] and c['confidence'] < 0.7) or 
                   (c['feedback_score'] and c['feedback_score'] <= 2)
            ]
        
        if min_confidence > 0:
            filtered_conversations = [
                c for c in filtered_conversations 
                if c['confidence'] and c['confidence'] >= min_confidence
            ]
        
        st.write(f"Mostrando {len(filtered_conversations)} de {len(conversations)} conversaciones")
        
        # Tabla de conversaciones
        if filtered_conversations:
            df_conversations = pd.DataFrame(filtered_conversations)
            
            # Preparar datos para mostrar
            display_data = []
            for conv in filtered_conversations:
                timestamp = datetime.fromisoformat(conv['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                
                # Truncar mensajes largos
                user_msg = conv['user_message'][:80] + "..." if len(conv['user_message']) > 80 else conv['user_message']
                bot_msg = conv['bot_response'][:80] + "..." if conv['bot_response'] and len(conv['bot_response']) > 80 else conv['bot_response']
                
                # Color coding para confianza
                confidence = conv['confidence']
                if confidence:
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
                    'Sesión': conv['session_id'][-8:],  # Solo últimos 8 caracteres
                    'Mensaje Usuario': user_msg,
                    'Respuesta Bot': bot_msg or "Sin respuesta",
                    'Intent': conv['intent_detected'] or "No detectado",
                    'Confianza': conf_display,
                    'Feedback': conv['feedback_score'] or "➖"
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
                avg_conf = sum(c['confidence'] for c in filtered_conversations if c['confidence']) / len([c for c in filtered_conversations if c['confidence']])
                st.metric("Confianza Promedio", f"{avg_conf:.2f}" if filtered_conversations else "N/A")
            
            with col2:
                problematic = len([c for c in filtered_conversations if c['confidence'] and c['confidence'] < 0.7])
                st.metric("Mensajes Problemáticos", problematic)
            
            with col3:
                unique_intents = len(set(c['intent_detected'] for c in filtered_conversations if c['intent_detected']))
                st.metric("Intents Únicos", unique_intents)
        
    except Exception as e:
        st.error(f"Error cargando conversaciones: {e}")

def show_failed_interactions(logger):
    """Muestra interacciones fallidas con recomendaciones"""
    
    st.header("❌ Interacciones Fallidas y Recomendaciones")
    
    try:
        failed = logger.get_failed_interactions()
        unknown_phrases = logger.get_unknown_phrases()
        
        if not failed and not unknown_phrases:
            st.success("🎉 ¡Excelente! No hay interacciones fallidas recientes.")
            return
        
        # Pestañas para diferentes tipos de problemas
        subtab1, subtab2, subtab3 = st.tabs([
            "🔴 Baja Confianza",
            "🚫 Frases No Entendidas", 
            "👎 Feedback Negativo"
        ])
        
        with subtab1:
            st.subheader("Mensajes con Baja Confianza")
            
            low_confidence = [f for f in failed if f['confidence'] and f['confidence'] < 0.7]
            
            if low_confidence:
                for interaction in low_confidence[:20]:
                    with st.expander(f"🔴 {interaction['user_message'][:60]}... (Confianza: {interaction['confidence']:.2f})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Mensaje del usuario:**")
                            st.write(interaction['user_message'])
                            st.write("**Intent detectado:**", interaction['intent_detected'])
                            st.write("**Confianza:**", f"{interaction['confidence']:.2f}")
                        
                        with col2:
                            st.write("**Respuesta del bot:**")
                            st.write(interaction['bot_response'] or "Sin respuesta")
                            st.write("**Timestamp:**", interaction['timestamp'])
                        
                        # Sugerencia de mejora
                        st.info(f"💡 **Sugerencia:** Agregar más ejemplos del tipo '{interaction['user_message']}' al intent `{interaction['intent_detected']}` en nlu.yml")
            else:
                st.success("No hay mensajes con baja confianza recientes.")
        
        with subtab2:
            st.subheader("Frases Frecuentes No Entendidas")
            
            if unknown_phrases:
                for phrase in unknown_phrases:
                    with st.expander(f"🚫 '{phrase['phrase']}' (aparece {phrase['frequency']} veces)"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Frase:**", phrase['phrase'])
                            st.write("**Frecuencia:**", phrase['frequency'])
                            st.write("**Primera vez vista:**", phrase['first_seen'])
                            st.write("**Última vez vista:**", phrase['last_seen'])
                        
                        with col2:
                            st.write("**Intent sugerido:**", phrase['suggested_intent'] or "No determinado")
                            
                            # Selector para asignar intent
                            suggested_intent = st.selectbox(
                                "Asignar a intent:",
                                ["Seleccionar...", "agendar_turno", "consultar_horarios", "consultar_requisitos", 
                                 "cancelar_turno", "frase_ambigua", "consultar_disponibilidad"],
                                key=f"intent_{phrase['id']}"
                            )
                            
                            if st.button("✅ Marcar como Resuelto", key=f"resolve_{phrase['id']}"):
                                logger.mark_phrase_as_resolved(phrase['id'])
                                st.success("Marcado como resuelto!")
                                st.rerun()
                        
                        # Generar código YAML
                        st.code(f"""
# Agregar a nlu.yml bajo el intent apropiado:
- intent: {suggested_intent if suggested_intent != "Seleccionar..." else "[INTENT_APROPIADO]"}
  examples: |
    - {phrase['phrase']}
                        """, language="yaml")
            else:
                st.success("No hay frases no entendidas frecuentes.")
        
        with subtab3:
            st.subheader("Conversaciones con Feedback Negativo")
            
            negative_feedback = [f for f in failed if f['feedback_score'] and f['feedback_score'] <= 2]
            
            if negative_feedback:
                for interaction in negative_feedback[:15]:
                    with st.expander(f"👎 Score: {interaction['feedback_score']}/5 - {interaction['user_message'][:50]}..."):
                        st.write("**Mensaje:**", interaction['user_message'])
                        st.write("**Respuesta:**", interaction['bot_response'])
                        st.write("**Intent:**", interaction['intent_detected'])
                        st.write("**Confianza:**", interaction['confidence'])
                        st.write("**Score de feedback:**", f"{interaction['feedback_score']}/5")
                        
                        st.warning("💡 **Acción requerida:** Revisar y mejorar la respuesta para este tipo de consulta")
            else:
                st.success("No hay feedback negativo reciente.")
        
    except Exception as e:
        st.error(f"Error cargando interacciones fallidas: {e}")

def show_word_patterns(logger):
    """Muestra patrones de palabras y frases más frecuentes"""
    
    st.header("🔤 Análisis de Palabras y Frases Frecuentes")
    
    try:
        # Pestañas para diferentes tipos de patrones
        subtab1, subtab2 = st.tabs(["📝 Palabras", "💬 Frases"])
        
        with subtab1:
            st.subheader("Palabras Más Utilizadas")
            
            word_patterns = logger.get_word_patterns(category='word', limit=50)
            
            if word_patterns:
                words_data = [
                    {
                        'Palabra': pattern[0],
                        'Frecuencia': pattern[1],
                        'Intent Principal': pattern[2] or "Varios",
                        'Categoría': pattern[3]
                    }
                    for pattern in word_patterns
                    if len(pattern[0]) > 2  # Filtrar palabras muy cortas
                ]
                
                if words_data:
                    df_words = pd.DataFrame(words_data)
                    
                    # Gráfico de palabras más frecuentes
                    fig_words = px.bar(
                        df_words.head(20),
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
                    st.dataframe(df_words, use_container_width=True, hide_index=True)
            else:
                st.info("No hay suficientes datos de palabras aún.")
        
        with subtab2:
            st.subheader("Frases Más Utilizadas")
            
            phrase_patterns = logger.get_word_patterns(category='phrase', limit=30)
            
            if phrase_patterns:
                phrases_data = [
                    {
                        'Frase': pattern[0],
                        'Frecuencia': pattern[1],
                        'Intent Principal': pattern[2] or "Varios",
                        'Categoría': pattern[3]
                    }
                    for pattern in phrase_patterns
                    if len(pattern[0]) > 5  # Filtrar frases muy cortas
                ]
                
                if phrases_data:
                    df_phrases = pd.DataFrame(phrases_data)
                    
                    # Tabla de frases
                    st.dataframe(df_phrases, use_container_width=True, hide_index=True)
                    
                    # Análisis de frases por intent
                    st.subheader("📊 Distribución de Frases por Intent")
                    
                    intent_phrase_count = df_phrases.groupby('Intent Principal').size().reset_index(name='Cantidad')
                    
                    fig_intent_phrases = px.pie(
                        intent_phrase_count,
                        values='Cantidad',
                        names='Intent Principal',
                        title='Distribución de Frases por Intent'
                    )
                    st.plotly_chart(fig_intent_phrases, use_container_width=True)
            else:
                st.info("No hay suficientes datos de frases aún.")
        
        # Insights automáticos
        st.markdown("---")
        st.subheader("🔍 Insights Automáticos")
        
        all_patterns = logger.get_word_patterns(limit=100)
        if all_patterns:
            # Palabras emergentes (alta frecuencia, pocas asociaciones)
            emerging_words = [p for p in all_patterns if p[1] > 5 and p[3] == 'word']
            if emerging_words:
                st.info(f"📈 **Palabras emergentes:** {', '.join([w[0] for w in emerging_words[:10]])}")
            
            # Frases que podrían ser nuevos intents
            potential_intents = [p for p in all_patterns if p[1] > 3 and p[3] == 'phrase' and not p[2]]
            if potential_intents:
                st.warning(f"💡 **Posibles nuevos intents:** {', '.join([p[0] for p in potential_intents[:5]])}")
        
    except Exception as e:
        st.error(f"Error cargando patrones de palabras: {e}")

def show_improvement_suggestions(logger):
    """Muestra sugerencias detalladas de mejora"""
    
    st.header("💡 Sugerencias de Mejora del Modelo")
    
    try:
        suggestions = logger.generate_training_suggestions()
        
        if suggestions:
            st.markdown(suggestions)
        else:
            st.info("No hay sugerencias disponibles. Necesitas más datos de conversaciones.")
        
        st.markdown("---")
        
        # Exportar datos para entrenamiento
        st.subheader("📥 Exportar Datos para Reentrenamiento")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generar Archivo YAML"):
                unknown_phrases = logger.get_unknown_phrases()
                
                if unknown_phrases:
                    yaml_content = generate_yaml_training_data(unknown_phrases)
                    
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
                report = generate_full_analysis_report(logger)
                
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
        
        stats = logger.get_conversation_stats()
        unknown_phrases = logger.get_unknown_phrases()
        failed_interactions = logger.get_failed_interactions()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Frases a Mejorar",
                len(unknown_phrases),
                help="Frases frecuentes que el modelo no entiende bien"
            )
        
        with col2:
            st.metric(
                "Interacciones Fallidas",
                len(failed_interactions),
                help="Conversaciones que necesitan atención"
            )
        
        with col3:
            improvement_potential = len(unknown_phrases) + len(failed_interactions)
            total_conversations = stats.get('total_conversations', 1)
            improvement_percentage = (improvement_potential / total_conversations) * 100 if total_conversations > 0 else 0
            
            st.metric(
                "Potencial de Mejora",
                f"{improvement_percentage:.1f}%",
                help="Porcentaje de conversaciones que se podrían mejorar"
            )
        
    except Exception as e:
        st.error(f"Error generando sugerencias: {e}")

def generate_yaml_training_data(unknown_phrases):
    """Genera contenido YAML para entrenamiento"""
    yaml_content = [
        "# Nuevos datos de entrenamiento basados en conversaciones reales",
        f"# Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# INSTRUCCIONES: Copia las líneas apropiadas a tu archivo nlu.yml\n"
    ]
    
    # Agrupar por intent sugerido
    by_intent = {}
    for phrase in unknown_phrases:
        intent = phrase['suggested_intent'] or 'intent_desconocido'
        if intent not in by_intent:
            by_intent[intent] = []
        by_intent[intent].append(phrase)
    
    for intent, phrases in by_intent.items():
        yaml_content.append(f"# Intent sugerido: {intent}")
        yaml_content.append(f"# Agregar estas líneas bajo '- intent: {intent}' en nlu.yml:")
        yaml_content.append("# examples: |")
        
        for phrase in phrases[:10]:  # Limitar a 10 por intent
            yaml_content.append(f"#   - {phrase['phrase']}  # (frecuencia: {phrase['frequency']})")
        
        yaml_content.append("")
    
    return "\n".join(yaml_content)

def generate_full_analysis_report(logger):
    """Genera reporte completo de análisis"""
    stats = logger.get_conversation_stats()
    unknown_phrases = logger.get_unknown_phrases()
    failed_interactions = logger.get_failed_interactions()
    
    report = [
        f"# Reporte Completo de Análisis del Chatbot",
        f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        
        "## Resumen Ejecutivo",
        f"- Total de conversaciones analizadas: {stats.get('total_conversations', 0)}",
        f"- Confianza promedio del modelo: {stats.get('average_confidence', 0):.2f}",
        f"- Mensajes problemáticos identificados: {len(failed_interactions)}",
        f"- Frases nuevas para entrenamiento: {len(unknown_phrases)}\n",
        
        "## Análisis Detallado",
        
        "### Rendimiento por Intent",
    ]
    
    for intent, count, avg_conf in stats.get('intent_stats', [])[:10]:
        status = "✅ Excelente" if avg_conf > 0.8 else "⚠️ Necesita mejora" if avg_conf < 0.7 else "✅ Bueno"
        report.append(f"- **{intent}**: {count} usos, confianza {avg_conf:.2f} {status}")
    
    report.append("\n### Recomendaciones de Mejora")
    
    if unknown_phrases:
        report.append("#### Frases para agregar al entrenamiento:")
        for phrase in unknown_phrases[:20]:
            report.append(f"- '{phrase['phrase']}' (frecuencia: {phrase['frequency']})")
    
    if failed_interactions:
        low_conf = [f for f in failed_interactions if f['confidence'] and f['confidence'] < 0.7]
        if low_conf:
            report.append("\n#### Intents que necesitan más ejemplos:")
            intent_counts = {}
            for interaction in low_conf:
                intent = interaction['intent_detected']
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"- {intent}: {count} casos de baja confianza")
    
    report.append(f"\n---\nReporte generado automáticamente por el sistema de aprendizaje del chatbot.")
    
    return "\n".join(report)

def generate_export_report(logger):
    """Genera y descarga reporte de exportación"""
    try:
        report = generate_full_analysis_report(logger)
        st.download_button(
            label="📄 Descargar Reporte de Análisis",
            data=report,
            file_name=f"reporte_exportacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        st.success("Reporte de exportación generado!")
    except Exception as e:
        st.error(f"Error generando reporte de exportación: {e}")

def clean_old_data(logger):
    """Limpia datos antiguos (función placeholder)"""
    st.info("Funcionalidad de limpieza en desarrollo. Por ahora, los datos se mantienen para análisis histórico.")

if __name__ == "__main__":
    show_learning_dashboard()