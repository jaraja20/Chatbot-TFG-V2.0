# 📧 GUÍA DE CONFIGURACIÓN DE EMAIL

## ✅ Paso 1: Obtener App Password de Gmail

1. **Ir a tu cuenta de Google**
   - Visita: https://myaccount.google.com/

2. **Activar Verificación en 2 Pasos** (si no está activada)
   - Menú lateral: "Seguridad"
   - Busca "Verificación en dos pasos" y actívala
   - Sigue los pasos para configurarla

3. **Crear App Password**
   - En "Seguridad", busca "Contraseñas de aplicaciones" (App Passwords)
   - Si no aparece, busca: https://myaccount.google.com/apppasswords
   - Selecciona:
     - **App**: Correo
     - **Dispositivo**: Windows/Linux/Mac
   - Click en "Generar"
   - **COPIA la contraseña de 16 caracteres** (sin espacios)

## ✅ Paso 2: Crear archivo .env

1. **Copia el archivo de ejemplo**
   ```bash
   cd "c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot"
   copy .env.example .env
   ```

2. **Edita el archivo `.env`** con tus credenciales:
   ```env
   # Configuración de Email
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   
   # Tu email de Gmail
   SMTP_EMAIL=tu_email@gmail.com
   
   # App Password de Gmail (16 caracteres SIN espacios)
   SMTP_PASSWORD=abcdEFGHijklMNOP
   
   # URL base del sistema
   BASE_URL=http://localhost:5000
   ```

   **IMPORTANTE**: 
   - Reemplaza `tu_email@gmail.com` con tu email real
   - Reemplaza `abcdEFGHijklMNOP` con tu App Password (16 caracteres sin espacios)

## ✅ Paso 3: Verificar instalación

Ejecuta este comando para verificar que todo esté configurado:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('SMTP_EMAIL:', os.getenv('SMTP_EMAIL')); print('SMTP_PASSWORD configurado:', 'SI' if os.getenv('SMTP_PASSWORD') else 'NO')"
```

Deberías ver:
```
SMTP_EMAIL: tu_email@gmail.com
SMTP_PASSWORD configurado: SI
```

## ✅ Paso 4: Reiniciar el servidor

```bash
# Detener el servidor Flask si está corriendo (Ctrl+C)
# Volver a ejecutar:
python app.py
```

## ✅ Paso 5: Probar el envío

1. Completa el flujo de agendamiento en el chatbot
2. Al confirmar el turno, verás en los logs:
   ```
   ✅ QR generado para turno 123
   ✅ Email enviado a usuario@example.com
   ```
3. Revisa tu bandeja de entrada (y spam) en el email que proporcionaste

---

## 🔧 Solución de Problemas

### Error: "SMTP authentication failed"
- Verifica que la App Password sea correcta (16 caracteres sin espacios)
- Asegúrate de haber activado la Verificación en 2 Pasos
- Intenta generar una nueva App Password

### Error: "Connection refused"
- Verifica que `SMTP_PORT=587` esté correcto
- Comprueba tu firewall/antivirus

### Email no llega
- Revisa carpeta de spam
- Verifica que el email del destinatario sea correcto
- Revisa los logs del servidor para ver si hay errores

### No se lee el archivo .env
- Asegúrate de que el archivo se llame exactamente `.env` (sin extensión .txt)
- Verifica que esté en la carpeta `flask-chatbot`
- Reinicia el servidor Flask

---

## 📝 Notas de Seguridad

⚠️ **IMPORTANTE**: 
- El archivo `.env` contiene credenciales sensibles
- NO lo subas a GitHub o repositorios públicos
- Agrega `.env` al archivo `.gitignore`
- No compartas tu App Password con nadie

## ✉️ Formato del Email que se enviará

El usuario recibirá un email con:
- ✅ Detalles del turno (nombre, cédula, fecha, hora)
- 📱 Código QR para confirmar asistencia
- 🔗 Link para confirmar/cancelar el turno
- ⚠️ Instrucciones importantes

---

## 🎯 Verificación Rápida

Ejecuta este test rápido:
```bash
cd "c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot"
python -c "import smtplib; from dotenv import load_dotenv; import os; load_dotenv(); s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(os.getenv('SMTP_EMAIL'), os.getenv('SMTP_PASSWORD')); print('✅ Conexión exitosa!'); s.quit()"
```

Si ves `✅ Conexión exitosa!`, todo está configurado correctamente.
