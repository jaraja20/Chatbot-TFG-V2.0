"""
Test directo de envío de email para diagnosticar problemas
"""

import sys
import os

# Agregar path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'notificaciones'))

from dotenv import load_dotenv
load_dotenv()

print("🔍 DIAGNÓSTICO DE ENVÍO DE EMAIL")
print("=" * 60)

# 1. Verificar variables de entorno
print("\n1️⃣ Verificando configuración:")
smtp_email = os.getenv('SMTP_EMAIL')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
smtp_port = int(os.getenv('SMTP_PORT', 587))

print(f"   SMTP_SERVER: {smtp_server}")
print(f"   SMTP_PORT: {smtp_port}")
print(f"   SMTP_EMAIL: {smtp_email}")
print(f"   SMTP_PASSWORD: {'*' * 8}...{'*' * 4} (configurado: {bool(smtp_password)})")

if not smtp_email or not smtp_password:
    print("\n❌ ERROR: Credenciales de email no configuradas en .env")
    sys.exit(1)

# 2. Verificar que el módulo email_sender existe
print("\n2️⃣ Verificando módulo email_sender:")
try:
    from email_sender import EmailNotificationSender
    print("   ✅ Módulo email_sender encontrado")
except ImportError as e:
    print(f"   ❌ ERROR: No se puede importar email_sender: {e}")
    print(f"   📂 Buscando en: {os.path.join(os.path.dirname(__file__), '..', 'notificaciones')}")
    sys.exit(1)

# 3. Crear instancia del sender
print("\n3️⃣ Creando EmailNotificationSender:")
try:
    email_sender = EmailNotificationSender(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        email=smtp_email,
        password=smtp_password
    )
    print("   ✅ EmailNotificationSender creado correctamente")
except Exception as e:
    print(f"   ❌ ERROR al crear EmailNotificationSender: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Preparar datos de prueba
print("\n4️⃣ Preparando datos de prueba:")
turno_data = {
    'nombre': 'Juan Pérez TEST',
    'cedula': '1234567',
    'fecha': '2025-11-04',
    'hora': '09:00',
    'numero_turno': '999',
    'codigo_turno': 'TEST1'
}
print(f"   📋 Datos de turno: {turno_data}")

# 5. Generar QR (opcional)
print("\n5️⃣ Generando QR:")
try:
    from qr_generator import QRConfirmationGenerator
    qr_gen = QRConfirmationGenerator(base_url="http://localhost:5000")
    qr_data = qr_gen.generate_qr_confirmation(turno_data)
    print(f"   ✅ QR generado correctamente")
except Exception as e:
    print(f"   ⚠️ WARNING: No se pudo generar QR: {e}")
    qr_data = None

# 6. Enviar email de prueba
print("\n6️⃣ Enviando email de prueba:")
email_destino = smtp_email  # Enviar a tu propio email para prueba
print(f"   📧 Destinatario: {email_destino}")

try:
    email_sender.send_confirmation_email(email_destino, turno_data, qr_data)
    print(f"   ✅ EMAIL ENVIADO EXITOSAMENTE a {email_destino}")
    print(f"\n🎉 PRUEBA COMPLETADA CON ÉXITO")
    print(f"   Revisa tu bandeja de entrada: {email_destino}")
    print(f"   (Si no lo ves, revisa la carpeta de SPAM)")
except Exception as e:
    print(f"   ❌ ERROR al enviar email: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
