"""
Script de diagnóstico para verificar configuración de email
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("\n" + "="*80)
print("🔍 DIAGNÓSTICO DE CONFIGURACIÓN DE EMAIL")
print("="*80 + "\n")

# Verificar variables de entorno
smtp_email = os.getenv('SMTP_EMAIL')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
smtp_port = os.getenv('SMTP_PORT', '587')

print("📋 Variables de entorno:")
print(f"   SMTP_SERVER: {smtp_server}")
print(f"   SMTP_PORT: {smtp_port}")
print(f"   SMTP_EMAIL: {smtp_email if smtp_email else '❌ NO CONFIGURADO'}")
print(f"   SMTP_PASSWORD: {'✅ Configurado' if smtp_password else '❌ NO CONFIGURADO'}")

if not smtp_email or not smtp_password:
    print("\n" + "="*80)
    print("❌ PROBLEMA IDENTIFICADO:")
    print("="*80)
    print("\nLas credenciales SMTP no están configuradas.")
    print("\n📝 SOLUCIÓN:")
    print("1. Crea un archivo .env en la carpeta flask-chatbot/")
    print("2. Agrega las siguientes variables:")
    print("\n   SMTP_EMAIL=tu_email@gmail.com")
    print("   SMTP_PASSWORD=tu_contraseña_de_aplicacion")
    print("   SMTP_SERVER=smtp.gmail.com")
    print("   SMTP_PORT=587")
    print("\n⚠️ IMPORTANTE:")
    print("   - Para Gmail, debes usar una 'Contraseña de aplicación'")
    print("   - NO uses tu contraseña normal de Gmail")
    print("   - Genera una en: https://myaccount.google.com/apppasswords")
    print("\n" + "="*80)
    sys.exit(1)

print("\n✅ Credenciales configuradas correctamente")
print("\n🔄 Probando conexión SMTP...")

try:
    import smtplib
    server = smtplib.SMTP(smtp_server, int(smtp_port))
    server.starttls()
    server.login(smtp_email, smtp_password)
    server.quit()
    
    print("✅ Conexión SMTP exitosa!")
    print(f"✅ Email configurado: {smtp_email}")
    print("\n" + "="*80)
    print("✅ TODO FUNCIONA CORRECTAMENTE")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Error al conectar con SMTP:")
    print(f"   {str(e)}")
    print("\n📝 Posibles soluciones:")
    print("   1. Verifica que el email y contraseña sean correctos")
    print("   2. Para Gmail, asegúrate de usar una 'Contraseña de aplicación'")
    print("   3. Verifica que el servidor SMTP sea correcto")
    print("   4. Revisa que el puerto sea el correcto (587 para TLS)")
    print("\n" + "="*80)
    sys.exit(1)
