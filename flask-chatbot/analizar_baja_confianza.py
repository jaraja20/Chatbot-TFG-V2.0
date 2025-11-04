"""
Script para analizar mensajes con baja confianza (<60%)
Muestra qué mensajes están causando el 83.8% de baja confianza
"""

import psycopg2
from collections import Counter
import sys

# Configuración de BD
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

def analizar_mensajes_baja_confianza():
    """Analiza los mensajes con confianza < 60%"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("="*80)
        print("📊 ANÁLISIS DE MENSAJES CON BAJA CONFIANZA (<60%)")
        print("="*80)
        
        # 1. Contar total de mensajes
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        total = cursor.fetchone()[0]
        print(f"\n📈 Total de mensajes: {total}")
        
        # 2. Mensajes con baja confianza
        cursor.execute("""
            SELECT COUNT(*) 
            FROM conversation_messages 
            WHERE confidence < 0.60
        """)
        baja_confianza = cursor.fetchone()[0]
        porcentaje = (baja_confianza / total * 100) if total > 0 else 0
        print(f"⚠️  Baja confianza (<60%): {baja_confianza} ({porcentaje:.1f}%)")
        
        # 3. Top 20 intents de baja confianza
        print("\n" + "="*80)
        print("🔍 TOP 20 INTENTS CON BAJA CONFIANZA")
        print("="*80)
        
        cursor.execute("""
            SELECT 
                intent_detected,
                COUNT(*) as cantidad,
                AVG(confidence) as confianza_promedio,
                MIN(confidence) as confianza_min,
                MAX(confidence) as confianza_max
            FROM conversation_messages
            WHERE confidence < 0.60
            GROUP BY intent_detected
            ORDER BY cantidad DESC
            LIMIT 20
        """)
        
        intents = cursor.fetchall()
        
        if intents:
            print(f"\n{'Intent':<30} {'Cant.':<8} {'Conf. Prom.':<15} {'Min':<8} {'Max':<8}")
            print("-"*80)
            for intent, cant, prom, minc, maxc in intents:
                intent_display = intent if intent else "(NULL/Sin intent)"
                prom_display = f"{prom:.2%}" if prom is not None else "N/A"
                minc_display = f"{minc:.2%}" if minc is not None else "N/A"
                maxc_display = f"{maxc:.2%}" if maxc is not None else "N/A"
                print(f"{intent_display:<30} {cant:<8} {prom_display:>13} {minc_display:>7} {maxc_display:>7}")
        
        # 4. Mostrar ejemplos de mensajes para cada intent problemático
        print("\n" + "="*80)
        print("💬 EJEMPLOS DE MENSAJES POR INTENT (Top 5)")
        print("="*80)
        
        for intent, cant, prom, minc, maxc in intents[:5]:
            intent_display = intent if intent else "(NULL/Sin intent)"
            prom_display = f"{prom:.2%}" if prom is not None else "N/A"
            print(f"\n📌 Intent: {intent_display} ({cant} mensajes, conf. prom: {prom_display})")
            print("-"*80)
            
            if intent:
                cursor.execute("""
                    SELECT 
                        user_message,
                        confidence,
                        timestamp
                    FROM conversation_messages
                    WHERE intent_detected = %s AND confidence < 0.60
                    ORDER BY confidence ASC
                    LIMIT 5
                """, (intent,))
            else:
                cursor.execute("""
                    SELECT 
                        user_message,
                        confidence,
                        timestamp
                    FROM conversation_messages
                    WHERE (intent_detected IS NULL OR intent_detected = '') AND confidence < 0.60
                    ORDER BY confidence ASC
                    LIMIT 5
                """)
            
            ejemplos = cursor.fetchall()
            for idx, (msg, conf, fecha) in enumerate(ejemplos, 1):
                conf_display = f"{conf:.2%}" if conf is not None else "N/A"
                print(f"  {idx}. [{conf_display}] {msg[:80] if msg else '(mensaje vacío)'}")
                if msg and len(msg) > 80:
                    print(f"     {'...' + msg[80:]}")
        
        # 5. Mensajes que NO son nlu_fallback pero tienen baja confianza
        print("\n" + "="*80)
        print("🤔 MENSAJES NO-FALLBACK CON BAJA CONFIANZA")
        print("="*80)
        
        cursor.execute("""
            SELECT 
                intent_detected,
                COUNT(*) as cantidad
            FROM conversation_messages
            WHERE confidence < 0.60 
              AND intent_detected != 'nlu_fallback'
              AND intent_detected NOT LIKE '%fallback%'
            GROUP BY intent_detected
            ORDER BY cantidad DESC
            LIMIT 10
        """)
        
        no_fallback = cursor.fetchall()
        
        if no_fallback:
            print("\nIntents específicos con baja confianza (no son fallback):")
            print(f"\n{'Intent':<30} {'Cantidad':<10}")
            print("-"*40)
            for intent, cant in no_fallback:
                print(f"{intent:<30} {cant:<10}")
                
                # Mostrar 2 ejemplos
                cursor.execute("""
                    SELECT user_message, confidence
                    FROM conversation_messages
                    WHERE intent_detected = %s AND confidence < 0.60
                    ORDER BY confidence ASC
                    LIMIT 2
                """, (intent,))
                
                ejemplos = cursor.fetchall()
                for msg, conf in ejemplos:
                    print(f"  └─ [{conf:.2%}] {msg[:70]}")
        
        # 6. Estadísticas por rango de confianza
        print("\n" + "="*80)
        print("📊 DISTRIBUCIÓN DETALLADA POR RANGOS")
        print("="*80)
        
        rangos = [
            ("0-10%", 0.0, 0.10),
            ("10-20%", 0.10, 0.20),
            ("20-30%", 0.20, 0.30),
            ("30-40%", 0.30, 0.40),
            ("40-50%", 0.40, 0.50),
            ("50-60%", 0.50, 0.60),
        ]
        
        print(f"\n{'Rango':<15} {'Cantidad':<12} {'Porcentaje':<12}")
        print("-"*40)
        
        for nombre, min_conf, max_conf in rangos:
            cursor.execute("""
                SELECT COUNT(*)
                FROM conversation_messages
                WHERE confidence >= %s AND confidence < %s
            """, (min_conf, max_conf))
            
            count = cursor.fetchone()[0]
            pct = (count / total * 100) if total > 0 else 0
            print(f"{nombre:<15} {count:<12} {pct:>10.1f}%")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*80)
        print("✅ Análisis completado")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analizar_mensajes_baja_confianza()
