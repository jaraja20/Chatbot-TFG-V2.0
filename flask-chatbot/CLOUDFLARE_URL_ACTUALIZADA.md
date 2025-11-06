# 🌐 Actualización de URL Pública - Cloudflare Tunnel

## ✅ Cambio Aplicado

**Fecha**: 2025-11-06  
**Nuevo enlace**: `https://precision-exhibition-surprised-webmasters.trycloudflare.com`

---

## 📝 ¿Qué se actualizó?

### Archivo modificado: `.env`

```bash
# ANTES
BASE_URL=https://delight-limitation-ministry-powerpoint.trycloudflare.com

# AHORA
BASE_URL=https://precision-exhibition-surprised-webmasters.trycloudflare.com
```

---

## 🔍 ¿Dónde se usa esta URL?

### 1. **Códigos QR de Confirmación** 📱
Cuando un usuario agenda un turno y se genera el código QR:

```python
# orquestador_inteligente.py línea ~3442
base_url = os.getenv('BASE_URL', 'http://localhost:5000')
qr_gen = QRConfirmationGenerator(base_url=base_url)
```

**El QR contiene**:
- Enlace: `https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/<token>`
- Al escanear → Abre página de confirmación del turno
- Token único para validar autenticidad

---

### 2. **Emails de Confirmación** 📧
Los emails enviados a usuarios incluyen:

**a) Enlace de Confirmación**:
```
🔗 Confirmar turno: https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/abc123...
```

**b) Enlace "Agregar a Google Calendar"**:
```
📅 https://calendar.google.com/calendar/render?action=TEMPLATE&text=...
&location=https://precision-exhibition-surprised-webmasters.trycloudflare.com
```

**c) Código QR adjunto (imagen)**:
- El QR mismo contiene el enlace de confirmación

---

### 3. **Botón de Confirmación en Chat** 💬
Cuando el bot muestra el resumen final:

```
"🔗 Link de confirmación: https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/<token>"
```

---

## 🚀 ¿Cómo funciona el sistema?

### Flujo completo con la nueva URL:

```
1️⃣ Usuario agenda turno en chatbot
   ↓
2️⃣ Sistema genera token único: "abc123def456..."
   ↓
3️⃣ Se crea URL de confirmación:
   https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/abc123def456
   ↓
4️⃣ Esta URL se usa en:
   - Código QR (imagen PNG)
   - Email HTML
   - Mensaje del bot
   ↓
5️⃣ Usuario abre el enlace:
   - Desde QR (escaneando con celular)
   - Desde email (clic en botón)
   - Desde mensaje del bot
   ↓
6️⃣ Cloudflare Tunnel redirige a tu servidor local:
   https://precision-exhibition... → http://localhost:5000/confirmar/abc123...
   ↓
7️⃣ Flask procesa la confirmación:
   - Valida token en BD
   - Marca turno como confirmado
   - Muestra página de éxito
```

---

## 🔄 ¿Cuándo necesitas cambiar la URL?

### Cloudflare Tunnel genera URLs dinámicas que cambian cuando:
- Reinicias el tunnel
- Caduca la sesión (generalmente 24-48 horas sin uso)
- Cambias de servidor

### Para actualizar:

1. **Obtén la nueva URL** de Cloudflare:
   ```bash
   cloudflared tunnel --url http://localhost:5000
   # Output: https://nueva-url-random.trycloudflare.com
   ```

2. **Actualiza el `.env`**:
   ```bash
   BASE_URL=https://nueva-url-random.trycloudflare.com
   ```

3. **Reinicia el servidor Flask**:
   ```bash
   # Watchdog lo recargará automáticamente
   # O manualmente: Ctrl+C y volver a ejecutar python app.py
   ```

4. **Verifica en logs**:
   ```
   INFO: 📍 Usando BASE_URL para QR: https://nueva-url-random.trycloudflare.com
   ```

---

## 📊 Verificación

### Comprobar que la nueva URL está activa:

#### 1. **Verificar archivo `.env`**:
```bash
cat flask-chatbot/.env | grep BASE_URL
# Esperado: BASE_URL=https://precision-exhibition-surprised-webmasters.trycloudflare.com
```

#### 2. **Verificar en logs del servidor**:
Cuando alguien agenda un turno, deberías ver:
```
INFO: 📍 Usando BASE_URL para QR: https://precision-exhibition-surprised-webmasters.trycloudflare.com
INFO: ✅ QR generado para turno 123 con código ABC...
```

#### 3. **Probar el enlace manualmente**:
```bash
# Abrir en navegador
https://precision-exhibition-surprised-webmasters.trycloudflare.com

# Debería mostrar el chatbot
```

#### 4. **Verificar QR generado**:
- Agenda un turno de prueba
- Descarga el QR del email
- Escanea con tu celular
- Debería abrir: `https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/...`

---

## 🛡️ Seguridad

### El token en la URL es seguro porque:
1. **Único por turno**: No se puede reutilizar
2. **Aleatorio**: 64 caracteres hexadecimales
3. **Validado en BD**: Solo tokens existentes funcionan
4. **Una sola vez**: Después de confirmar, se marca como usado

### Ejemplo de token:
```
https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/
a3f8b2c1d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

---

## 🔧 Troubleshooting

### Problema: "No puedo acceder al enlace del QR"
**Solución**:
1. Verifica que Cloudflare Tunnel esté corriendo
2. Comprueba que la URL en `.env` sea la actual
3. Reinicia el servidor Flask

### Problema: "El QR muestra localhost:5000"
**Solución**:
- La variable `BASE_URL` no se está cargando
- Verifica que `load_dotenv()` esté en el código
- Reinicia el servidor después de cambiar `.env`

### Problema: "URL de Cloudflare caducó"
**Solución**:
1. Genera nueva URL con cloudflared
2. Actualiza `.env`
3. Reinicia servidor
4. Los QR antiguos dejarán de funcionar (normal)

---

## 📌 Notas Importantes

### ⚠️ URLs de Cloudflare Free son temporales
- Cambian cada vez que reinicias el tunnel
- No son ideales para producción permanente
- Considera opciones de hosting permanente para producción

### ✅ Para producción permanente considera:
- **Cloudflare Tunnel con dominio propio**: `turnos.tuempresa.com`
- **VPS con dominio**: DigitalOcean, Linode, AWS
- **Heroku/Railway/Render**: Deployment automático

### 🔄 Automatización futura:
Podrías crear un script que actualice automáticamente el `.env` cuando detecte cambio de URL en Cloudflare.

---

## 📧 Impacto en Emails

### Ejemplo de email con la nueva URL:

```html
<h2>✅ Turno Confirmado</h2>

<p>Nombre: Juan Pérez</p>
<p>Fecha: 2025-11-10</p>
<p>Hora: 09:00</p>

<a href="https://precision-exhibition-surprised-webmasters.trycloudflare.com/confirmar/abc123...">
  🔗 Confirmar Turno
</a>

<img src="cid:qr_code" alt="Código QR">

<a href="https://calendar.google.com/calendar/render?action=TEMPLATE&...">
  📅 Agregar a Google Calendar
</a>
```

---

**Estado**: ✅ **ACTUALIZADO Y LISTO**  
**Próxima acción**: Reiniciar servidor Flask para aplicar cambios (watchdog debería hacerlo automáticamente)
