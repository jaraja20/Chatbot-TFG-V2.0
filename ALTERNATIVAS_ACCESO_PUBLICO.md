# 🌐 Alternativas para Acceso Público Gratuito

## Problema Actual
Cloudflare Tunnel gratuito NO permite URLs fijas sin un dominio personalizado.
La URL `https://chatbot-cde.trycloudflare.com` es temporal y cambia.

---

## ✅ Alternativas Gratuitas Recomendadas

### 1. **ngrok** (Más Popular y Fácil) ⭐ RECOMENDADO

#### Ventajas:
- ✅ URL pública funcional
- ✅ Gratis con URLs que duran 2 horas
- ✅ Muy fácil de usar
- ✅ Plan gratuito generoso

#### Instalación:
```powershell
# Opción 1: Con winget
winget install ngrok

# Opción 2: Descargar desde
# https://ngrok.com/download
```

#### Uso:
```powershell
# 1. Crear cuenta gratis en https://ngrok.com
# 2. Obtener tu authtoken
# 3. Configurar token
ngrok config add-authtoken TU_TOKEN_AQUI

# 4. Iniciar tunnel
ngrok http 5000
```

#### Resultado:
```
Forwarding https://abc123.ngrok.io -> http://localhost:5000
```

**Plan Gratis:** URL cambia cada vez que reinicias, pero funciona perfectamente.
**Plan Básico ($8/mes):** URL fija personalizada (ej: `chatbot-cde.ngrok.io`)

---

### 2. **localhost.run** (Sin Instalación)

#### Ventajas:
- ✅ NO requiere instalación
- ✅ NO requiere cuenta
- ✅ Solo un comando

#### Uso:
```powershell
ssh -R 80:localhost:5000 nokey@localhost.run
```

#### Resultado:
Te dará una URL como: `https://random123.lhr.life`

**Limitación:** URL cambia cada vez, pero es instantáneo y sin registro.

---

### 3. **Serveo** (Sin Instalación)

#### Uso:
```powershell
ssh -R 80:localhost:5000 serveo.net
```

#### Resultado:
URL temporal como: `https://random.serveo.net`

---

### 4. **localtunnel** (Node.js)

#### Instalación:
```powershell
npm install -g localtunnel
```

#### Uso:
```powershell
lt --port 5000
```

#### Resultado:
URL como: `https://random-word-123.loca.lt`

---

### 5. **Pagekite** (Opción con URL Fija Gratis por 30 días)

#### Instalación:
```powershell
pip install pagekite
```

#### Uso:
```powershell
pagekite.py 5000 yourname.pagekite.me
```

**Limitación:** Gratis 30 días, luego $4/mes

---

## 🎯 Comparación Rápida

| Herramienta | URL Fija | Gratis | Sin Instalación | Estabilidad |
|-------------|----------|--------|-----------------|-------------|
| **ngrok** | No* | ✅ | No | ⭐⭐⭐⭐⭐ |
| localhost.run | No | ✅ | ✅ | ⭐⭐⭐⭐ |
| Serveo | No | ✅ | ✅ | ⭐⭐⭐ |
| localtunnel | No | ✅ | No | ⭐⭐⭐ |
| Pagekite | Sí (30 días) | ⚠️ | No | ⭐⭐⭐⭐ |

*Con plan de pago

---

## 🚀 Script Automático con ngrok

He creado un script que:
1. Inicia Flask
2. Inicia ngrok
3. Muestra la URL pública
4. Mantiene todo corriendo

```powershell
python start_with_ngrok.py
```

---

## 💡 Recomendación para Uso Real

### Para Desarrollo/Pruebas (GRATIS):
✅ **ngrok plan gratuito**
- La URL cambia cada vez que reinicias
- Pero funciona perfectamente para demos y pruebas
- Puedes compartir el link temporalmente

### Para Producción (NECESITAS PAGAR):

**Opción A:** Dominio propio + Cloudflare Tunnel
- Compra un dominio ($10-15/año)
- Cloudflare Tunnel gratis con dominio propio
- **Total: ~$10-15/año**

**Opción B:** ngrok con URL fija
- Plan Básico: $8/mes
- URL personalizada: `chatbot-cde.ngrok.io`
- **Total: $96/año**

**Opción C:** Hosting en la nube (VPS)
- DigitalOcean: $6/mes
- Linode: $5/mes
- **Total: $60-72/año**

---

## 🎓 Para tu TFG

Si esto es para tu Trabajo Final de Grado:

1. **Para la presentación:** Usa ngrok gratuito
   - La URL temporal es suficiente
   - Funciona perfectamente durante la demo

2. **Para la documentación:** Explica que:
   - El sistema está diseñado para acceso local
   - Se puede exponer públicamente con ngrok/cloudflare
   - URL fija requiere dominio personalizado

3. **Para el tribunal:** Demuestra en vivo con:
   - localhost (más confiable)
   - O ngrok si quieres mostrar acceso remoto

---

## ❓ ¿Qué Prefieres?

1. **ngrok** - Instalar y configurar (5 minutos)
2. **localhost.run** - Usar sin instalar (30 segundos)
3. **Mantener en localhost** - Solo para acceso local

Dime cuál prefieres y te ayudo a configurarlo 🚀
