# 🌐 Sistema de Turnos - Acceso Público Configurado

**Fecha de configuración:** 3 de Noviembre, 2025  
**Estado:** ✅ Activo y Funcionando

---

## 📡 URLs de Acceso

### 🌍 URL Pública (Cloudflare Tunnel)
```
https://chatbot-cde.trycloudflare.com
```
- ✅ Accesible desde cualquier lugar del mundo
- ✅ HTTPS automático (conexión segura)
- ✅ Sin necesidad de configurar puertos o firewall
- ✅ URL permanente mientras el tunnel esté activo

### 🏠 URL Local
```
http://localhost:5000
```
- Solo accesible desde tu computadora

---

## 🔧 Configuración Técnica

### Tunnel ID
```
cfa52155-f486-4406-8bf2-516a6e06c4d2
```

### Tunnel Name
```
chatbot-cde
```

### Archivo de Configuración
```
cloudflare-config.yml
```

### Credenciales
```
C:\Users\jhoni\.cloudflared\cfa52155-f486-4406-8bf2-516a6e06c4d2.json
```

---

## 🚀 Cómo Iniciar el Sistema

### Opción 1: Inicio Manual (2 terminales)

**Terminal 1 - Flask:**
```powershell
cd "c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot"
& "C:/tfg funcional/.venv/Scripts/python.exe" app.py
```

**Terminal 2 - Cloudflare Tunnel:**
```powershell
cd "c:\tfg funcional\Chatbot-TFG-V2.0"
cloudflared tunnel --config cloudflare-config.yml run chatbot-cde
```

### Opción 2: Inicio Automático (1 comando)
```powershell
cd "c:\tfg funcional\Chatbot-TFG-V2.0"
python start_public.py
```

---

## ⏹️ Cómo Detener el Sistema

1. Presiona `Ctrl + C` en cada terminal
2. O cierra las ventanas de terminal directamente

---

## 📊 Acceso al Dashboard de Administración

Desde el chat (público o local), escribe cualquiera de estos comandos:
- `admin`
- `dashboard`
- `modo desarrollador`
- `panel admin`

Se mostrará un botón morado "📊 Abrir Dashboard" que te llevará al panel de administración.

---

## ✅ Funcionalidades Activas

### Sistema de Turnos
- ✅ Horarios: 7:00 AM - 3:00 PM
- ✅ 2 turnos cada 30 minutos (34 turnos/día)
- ✅ Código único de 5 caracteres
- ✅ Email con QR y confirmación
- ✅ Consulta por franjas horarias (mañana/tarde)

### Sistema de Logs
- ✅ Filtros automáticos de mensajes innecesarios
- ✅ NO guarda "Inicio de sesión" automáticos
- ✅ NO guarda mensajes con confidence=0 sin intent
- ✅ Estadísticas limpias y precisas

### Dashboard
- ✅ Estadísticas de confianza: 68.9% muy alta
- ✅ Solo 3.1% de baja confianza
- ✅ 161 mensajes reales registrados
- ✅ Feedback de usuarios integrado

---

## 🔒 Seguridad

- ✅ HTTPS automático con Cloudflare
- ✅ Credenciales SMTP en archivo `.env`
- ✅ Token de Google Calendar en `.gitignore`
- ✅ Base de datos PostgreSQL local

---

## 📝 Comandos Útiles

### Ver información del tunnel:
```powershell
cloudflared tunnel info chatbot-cde
```

### Listar todos los tunnels:
```powershell
cloudflared tunnel list
```

### Ver logs del tunnel en tiempo real:
Los logs se muestran automáticamente en la terminal donde corre el tunnel

### Verificar servidor Flask:
```powershell
Invoke-WebRequest -Uri "http://localhost:5000" -Method GET
```

---

## 🐛 Solución de Problemas

### El tunnel no se conecta:
1. Verifica que estés autenticado: `cloudflared tunnel login`
2. Verifica que el archivo de config existe: `cloudflare-config.yml`
3. Verifica las credenciales en: `C:\Users\jhoni\.cloudflared\`

### El chat no responde:
1. Verifica que Flask esté corriendo en localhost:5000
2. Revisa los logs en la terminal de Flask
3. Verifica que el tunnel esté activo

### Estadísticas incorrectas en dashboard:
1. Ejecuta limpieza: `python ejecutar_limpieza_directa.py`
2. Los filtros automáticos ahora previenen mensajes basura
3. Solo se guardan interacciones reales

---

## 📧 Configuración de Email

Las credenciales SMTP están en: `flask-chatbot/.env`

```env
SMTP_EMAIL=jhonivillalba15@gmail.com
SMTP_PASSWORD=[App Password de Gmail]
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

⚠️ **Importante:** Usa una contraseña de aplicación de Gmail, no tu contraseña personal.

---

## 📦 Dependencias Principales

- **Python:** 3.8.10
- **Flask:** 3.0.0
- **Rasa:** (opcional para modo offline)
- **PostgreSQL:** Base de datos local
- **Cloudflared:** 2025.8.1
- **qrcode[pil]:** 7.4.2
- **python-dotenv:** Variables de entorno

---

## 🎯 Próximos Pasos Opcionales

1. **Dominio personalizado:** Configura un dominio propio en Cloudflare
2. **Backup automático:** Implementar respaldo de base de datos
3. **Monitoreo:** Agregar alertas de disponibilidad
4. **Analytics:** Integrar Google Analytics en el frontend

---

## 👤 Información del Proyecto

- **Usuario:** Jhoni Villalba
- **Email:** jhonivillalba15@gmail.com
- **Repositorio:** jaraja20/Chatbot-TFG-V2.0
- **Branch:** main

---

## 📞 Soporte

Si tienes problemas, revisa:
1. Los logs en las terminales
2. El archivo `verificar_filtros.py` para estadísticas
3. El archivo `analizar_baja_confianza.py` para diagnosticar problemas

---

**Última actualización:** 3 de Noviembre, 2025  
**Estado del sistema:** 🟢 Operacional
