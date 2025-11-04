"""
Script para iniciar Cloudflare Tunnel en modo rápido (sin configuración)
Genera una URL temporal automáticamente
"""

import subprocess
import time
import re

def print_header():
    print("="*80)
    print("🚀 INICIANDO CLOUDFLARE TUNNEL (MODO RÁPIDO)")
    print("   URL temporal - Cambia cada vez que reinicias")
    print("="*80)
    print()

def check_flask():
    """Verifica que Flask esté corriendo"""
    import requests
    try:
        response = requests.get("http://localhost:5000", timeout=2)
        print("✅ Flask está corriendo en localhost:5000")
        return True
    except:
        print("❌ Flask NO está corriendo")
        print()
        print("🔧 SOLUCIÓN: Abre otra terminal y ejecuta:")
        print('   cd "c:\\tfg funcional\\Chatbot-TFG-V2.0\\flask-chatbot"')
        print('   & "C:/tfg funcional/.venv/Scripts/python.exe" app.py')
        print()
        return False

def start_tunnel():
    """Inicia Cloudflare tunnel en modo rápido"""
    print("\n🌐 Iniciando Cloudflare Tunnel...")
    print("   Generando URL temporal...")
    print()
    
    try:
        # Iniciar tunnel
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Buscar la URL en el output
        url_found = False
        
        for line in process.stdout:
            print(line.strip())
            
            # Buscar patrón de URL
            if "trycloudflare.com" in line:
                # Extraer URL
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    url = match.group(0)
                    if not url_found:
                        print("\n" + "="*80)
                        print("✅ ¡TUNNEL ACTIVO!")
                        print("="*80)
                        print()
                        print("🌐 URL PÚBLICA:")
                        print(f"   {url}")
                        print()
                        print("📍 URL LOCAL:")
                        print("   http://localhost:5000")
                        print()
                        print("📊 DASHBOARD:")
                        print("   Escribe 'admin' en el chat")
                        print()
                        print("⏹️  Para detener: Presiona Ctrl+C")
                        print("="*80)
                        print()
                        url_found = True
            
            # Mostrar errores importantes
            if "error" in line.lower() and "Application error 0x0" not in line:
                if "cloudflared does not support" not in line:  # Ignorar warning de certificados
                    print(f"⚠️  {line.strip()}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tunnel detenido por el usuario")
        process.terminate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print_header()
    
    # Verificar Flask
    if not check_flask():
        respuesta = input("¿Iniciar Flask automáticamente? (s/n): ")
        if respuesta.lower() == 's':
            print("\n🔷 Iniciando Flask...")
            flask_process = subprocess.Popen(
                [r"C:\tfg funcional\.venv\Scripts\python.exe", "app.py"],
                cwd=r"C:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot",
            )
            time.sleep(3)
            print("✅ Flask iniciado")
        else:
            print("\n❌ Flask debe estar corriendo para continuar")
            return
    
    # Iniciar tunnel
    start_tunnel()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 ¡Sistema detenido!")
