"""
🔍 Script de Verificación - Configuración de URL de Cloudflare
Verifica que el sistema esté usando la URL correcta para emails y QR
"""

import os
from dotenv import load_dotenv

print("=" * 70)
print("🔍 VERIFICACIÓN DE CONFIGURACIÓN - URL DE CLOUDFLARE")
print("=" * 70)

# Cargar variables de entorno
load_dotenv()

# Obtener BASE_URL
base_url = os.getenv('BASE_URL', 'NO ENCONTRADA')

print(f"\n📋 BASE_URL configurada:")
print(f"   {base_url}")

# Verificar si es la URL correcta
expected_url = "https://precision-exhibition-surprised-webmasters.trycloudflare.com"

if base_url == expected_url:
    print(f"\n✅ CORRECTO: La URL está actualizada")
elif base_url == "NO ENCONTRADA":
    print(f"\n❌ ERROR: Variable BASE_URL no encontrada en .env")
    print(f"   Por favor, crea el archivo .env con BASE_URL={expected_url}")
elif "localhost" in base_url:
    print(f"\n⚠️  ADVERTENCIA: Usando localhost, no es accesible públicamente")
    print(f"   Debería ser: {expected_url}")
else:
    print(f"\n⚠️  ADVERTENCIA: URL diferente a la esperada")
    print(f"   Actual:   {base_url}")
    print(f"   Esperada: {expected_url}")

# Verificar otras configuraciones importantes
print(f"\n📧 Configuración de Email:")
smtp_email = os.getenv('SMTP_EMAIL', 'NO ENCONTRADO')
smtp_password = os.getenv('SMTP_PASSWORD', 'NO ENCONTRADO')

if smtp_email != 'NO ENCONTRADO':
    print(f"   Email: {smtp_email}")
else:
    print(f"   ❌ SMTP_EMAIL no configurado")

if smtp_password != 'NO ENCONTRADO':
    print(f"   Password: {'*' * len(smtp_password)} (oculto)")
else:
    print(f"   ❌ SMTP_PASSWORD no configurado")

# Verificar que load_dotenv funcione
print(f"\n🔧 Sistema:")
print(f"   Python: {os.sys.version.split()[0]}")
print(f"   Directorio: {os.getcwd()}")

# Test de generación de URL de confirmación
if base_url != "NO ENCONTRADA":
    ejemplo_token = "abc123def456xyz789"
    url_confirmacion = f"{base_url}/confirmar/{ejemplo_token}"
    print(f"\n🔗 Ejemplo de URL de confirmación:")
    print(f"   {url_confirmacion}")
    
    # Verificar longitud
    if len(url_confirmacion) < 200:
        print(f"   ✅ Longitud adecuada para QR: {len(url_confirmacion)} caracteres")
    else:
        print(f"   ⚠️  URL muy larga para QR: {len(url_confirmacion)} caracteres")

print("\n" + "=" * 70)
print("📊 RESUMEN")
print("=" * 70)

issues = []
if base_url == "NO ENCONTRADA":
    issues.append("❌ BASE_URL no configurada")
elif base_url != expected_url and "localhost" not in base_url:
    issues.append("⚠️  BASE_URL diferente a la esperada")
elif "localhost" in base_url:
    issues.append("⚠️  BASE_URL apunta a localhost (no público)")

if smtp_email == 'NO ENCONTRADO':
    issues.append("❌ SMTP_EMAIL no configurado")
if smtp_password == 'NO ENCONTRADO':
    issues.append("❌ SMTP_PASSWORD no configurado")

if issues:
    print("\n🔴 Problemas encontrados:")
    for issue in issues:
        print(f"   {issue}")
else:
    print("\n✅ TODO CONFIGURADO CORRECTAMENTE")
    print("\n🎉 El sistema está listo para:")
    print("   • Generar códigos QR con la URL pública")
    print("   • Enviar emails con enlaces de confirmación")
    print("   • Agregar eventos a Google Calendar")

print("\n💡 Próximos pasos:")
print("   1. Reinicia el servidor Flask (o espera a watchdog)")
print("   2. Agenda un turno de prueba")
print("   3. Verifica que el QR contenga la URL de Cloudflare")
print("   4. Escanea el QR para confirmar que funciona")

print("\n" + "=" * 70)
