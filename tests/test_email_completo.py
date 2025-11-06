"""
Test completo del sistema de email con QR
"""
# -*- coding: utf-8 -*-
import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar path de notificaciones
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'notificaciones'))

print("\n" + "="*80)
print("[TEST] TEST DE ENVÍO DE EMAIL CON QR")
print("="*80 + "\n")

# 1. Verificar credenciales
smtp_email = os.getenv('SMTP_EMAIL')
smtp_password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
smtp_port = int(os.getenv('SMTP_PORT', 587))

print("[*] Configuración:")
print(f"   SMTP Server: {smtp_server}:{smtp_port}")
print(f"   Email: {smtp_email}")
print(f"   Password: {'[OK] Configurado' if smtp_password else '[FAIL] NO CONFIGURADO'}")

if not smtp_email or not smtp_password:
    print("\n[FAIL] Error: Credenciales SMTP no configuradas")
    sys.exit(1)

# 2. Generar QR de prueba
print("\n[LOOP] Generando código QR de prueba...")
try:
    from qr_generator import QRConfirmationGenerator
    
    qr_gen = QRConfirmationGenerator(base_url="http://localhost:5000")
    
    turno_data = {
        'turno_id': '12345-TEST',
        'nombre': 'Juan Pérez',
        'cedula': '12345678',
        'fecha': '2025-11-05',
        'hora': '10:00',
        'numero_turno': 'TEST-001'
    }
    
    qr_data = qr_gen.generate_qr_confirmation(turno_data)
    print(f"[OK] QR generado exitosamente")
    print(f"   Código de turno: {turno_data['numero_turno']}")
    print(f"   URL de confirmación: {qr_data['confirmation_url']}")
    
except Exception as e:
    print(f"[FAIL] Error generando QR: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

# 3. Enviar email de prueba
print("\n[EMAIL] Enviando email de prueba...")
try:
    from email_sender import EmailNotificationSender
    
    email_sender = EmailNotificationSender(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        email=smtp_email,
        password=smtp_password
    )
    
    # Email de destino (usa el tuyo para probar)
    recipient_email = input("\n[*] Ingresa el email de destino (o Enter para usar el configurado): ").strip()
    if not recipient_email:
        recipient_email = smtp_email
    
    print(f"\n[*] Enviando a: {recipient_email}")
    resultado = email_sender.send_confirmation_email(recipient_email, turno_data, qr_data)
    
    if resultado:
        print("\n" + "="*80)
        print("[OK] EMAIL ENVIADO EXITOSAMENTE")
        print("="*80)
        print(f"\n[EMAIL] Revisa la bandeja de entrada de: {recipient_email}")
        print("   (Si no lo ves, revisa la carpeta de spam)")
    else:
        print("\n" + "="*80)
        print("[FAIL] ERROR AL ENVIAR EMAIL")
        print("="*80)
        sys.exit(1)
        
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)
