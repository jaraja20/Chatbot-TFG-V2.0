"""
Script para limpiar mensajes automáticos "Inicio de sesión" de la BD
Estos mensajes contaminan las estadísticas del dashboard
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

def limpiar_datos():
    """Elimina mensajes automáticos y de prueba"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("="*80)
        print("🧹 LIMPIEZA DE DATOS DEL CHATBOT")
        print("="*80)
        
        # 1. Contar mensajes antes
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        total_antes = cursor.fetchone()[0]
        print(f"\n📊 Total de mensajes ANTES: {total_antes}")
        
        # 2. Eliminar mensajes "Inicio de sesión"
        print("\n🗑️  Eliminando mensajes 'Inicio de sesión'...")
        cursor.execute("""
            DELETE FROM conversation_messages 
            WHERE user_message = 'Inicio de sesión'
        """)
        deleted_inicio = cursor.rowcount
        print(f"   ✅ Eliminados: {deleted_inicio} mensajes")
        
        # 3. Eliminar mensajes con intent = 'error' (comandos admin fallidos)
        print("\n🗑️  Eliminando mensajes con intent 'error'...")
        cursor.execute("""
            DELETE FROM conversation_messages 
            WHERE intent_detected = 'error'
        """)
        deleted_error = cursor.rowcount
        print(f"   ✅ Eliminados: {deleted_error} mensajes")
        
        # 4. Eliminar mensajes con intent NULL o vacío y confidence 0
        print("\n🗑️  Eliminando mensajes NULL/vacíos con confianza 0...")
        cursor.execute("""
            DELETE FROM conversation_messages 
            WHERE (intent_detected IS NULL OR intent_detected = '')
              AND confidence = 0
              AND user_message != 'Inicio de sesión'
        """)
        deleted_null = cursor.rowcount
        print(f"   ✅ Eliminados: {deleted_null} mensajes")
        
        # 5. Contar mensajes después
        cursor.execute("SELECT COUNT(*) FROM conversation_messages")
        total_despues = cursor.fetchone()[0]
        
        print("\n" + "="*80)
        print("📊 RESUMEN DE LIMPIEZA")
        print("="*80)
        print(f"Mensajes antes:      {total_antes}")
        print(f"Mensajes eliminados: {total_antes - total_despues}")
        print(f"Mensajes después:    {total_despues}")
        print(f"Porcentaje limpiado: {((total_antes - total_despues) / total_antes * 100):.1f}%")
        
        # 6. Mostrar nueva distribución de confianza
        print("\n" + "="*80)
        print("📈 NUEVA DISTRIBUCIÓN DE CONFIANZA")
        print("="*80)
        
        if total_despues > 0:
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN confidence >= 0.90 THEN 'Muy Alta (90-100%)'
                        WHEN confidence >= 0.75 THEN 'Alta (75-89%)'
                        WHEN confidence >= 0.60 THEN 'Media (60-74%)'
                        ELSE 'Baja (<60%)'
                    END as rango,
                    COUNT(*) as cantidad
                FROM conversation_messages
                GROUP BY rango
                ORDER BY 
                    CASE 
                        WHEN confidence >= 0.90 THEN 1
                        WHEN confidence >= 0.75 THEN 2
                        WHEN confidence >= 0.60 THEN 3
                        ELSE 4
                    END
            """)
        
            distribucion = cursor.fetchall()
            
            print(f"\n{'Rango':<20} {'Cantidad':<12} {'Porcentaje':<12}")
            print("-"*50)
            for rango, cant in distribucion:
                pct = (cant / total_despues * 100) if total_despues > 0 else 0
                print(f"{rango:<20} {cant:<12} {pct:>10.1f}%")
        else:
            print("\n⚠️  No hay mensajes después de la limpieza")
        
        # Confirmar cambios
        print("\n" + "="*80)
        respuesta = input("¿Confirmar limpieza? (escribe 'SI' para confirmar): ")
        
        if respuesta.upper() == 'SI':
            conn.commit()
            print("\n✅ ¡Limpieza completada exitosamente!")
            print("   Los datos han sido actualizados en la base de datos.")
        else:
            conn.rollback()
            print("\n❌ Limpieza cancelada. No se realizaron cambios.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n⚠️  ADVERTENCIA: Este script eliminará datos de la base de datos")
    print("   Se eliminarán:")
    print("   - Mensajes 'Inicio de sesión' (automáticos)")
    print("   - Mensajes con intent 'error'")
    print("   - Mensajes NULL con confianza 0")
    print()
    
    respuesta = input("¿Deseas continuar? (escribe 'CONTINUAR' para proceder): ")
    
    if respuesta.upper() == 'CONTINUAR':
        limpiar_datos()
    else:
        print("\n❌ Operación cancelada.")
