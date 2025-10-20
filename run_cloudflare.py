"""
Script para ejecutar el chatbot con Cloudflare Tunnel
TODO SE EJECUTA LOCALMENTE (Rasa, PostgreSQL, Google Calendar)
La interfaz es accesible públicamente vía Cloudflare.

REQUISITOS PREVIOS:
1. Instalar Cloudflare cloudflared:
   Windows: https://github.com/cloudflare/cloudflared/releases
   Linux: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
   Mac: brew install cloudflare/cloudflare/cloudflared

2. Tener Rasa ejecutándose en localhost:5005
   Terminal separada: rasa run --enable-api --cors "*"

3. PostgreSQL ejecutándose en localhost:5432

4. Python packages:
   pip install streamlit

USO:
    python run_cloudflare.py
"""

import subprocess
import sys
import os
import time
import signal
import requests
from datetime import datetime

class CloudflareChatbotLauncher:
    def __init__(self):
        self.streamlit_process = None
        self.cloudflare_process = None
        self.rasa_online = False
        
    def print_header(self):
        """Imprime el header del script"""
        print("=" * 70)
        print("🏛️  SISTEMA DE TURNOS CÉDULAS - CLOUDFLARE TUNNEL")
        print("    Ciudad del Este - Acceso Público")
        print("=" * 70)
        print()
    
    def check_rasa(self):
        """Verifica que Rasa esté corriendo"""
        print("📡 Verificando Rasa...")
        
        try:
            response = requests.get("http://localhost:5005/status", timeout=5)
            if response.status_code == 200:
                self.rasa_online = True
                print("✅ Rasa está corriendo en localhost:5005")
                return True
            else:
                print("⚠️  Rasa no responde correctamente")
                return False
        except Exception as e:
            print("❌ Rasa NO está ejecutándose")
            print()
            print("🔧 SOLUCIÓN:")
            print("   Abre una terminal separada y ejecuta:")
            print("   → rasa run --enable-api --cors \"*\"")
            print()
            print("   O si prefieres con acciones personalizadas:")
            print("   Terminal 1: rasa run actions")
            print("   Terminal 2: rasa run --enable-api --cors \"*\"")
            print()
            return False
    
    def check_cloudflared(self):
        """Verifica que cloudflared esté instalado"""
        print("🔍 Verificando cloudflared...")
        
        try:
            result = subprocess.run(
                ["cloudflared", "--version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✅ cloudflared encontrado: {result.stdout.strip()}")
                return True
            else:
                return False
        except FileNotFoundError:
            print("❌ cloudflared NO está instalado")
            print()
            print("📥 DESCARGA E INSTALACIÓN:")
            print()
            print("Windows:")
            print("  1. Ve a: https://github.com/cloudflare/cloudflared/releases")
            print("  2. Descarga: cloudflared-windows-amd64.exe")
            print("  3. Renómbralo a: cloudflared.exe")
            print("  4. Muévelo a una carpeta en tu PATH")
            print()
            print("Mac:")
            print("  brew install cloudflare/cloudflare/cloudflared")
            print()
            print("Linux:")
            print("  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64")
            print("  chmod +x cloudflared-linux-amd64")
            print("  sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared")
            print()
            return False
    
    def start_streamlit(self, app_file="app.py"):
        """Inicia Streamlit"""
        print(f"\n🚀 Iniciando Streamlit con {app_file}...")
        
        if not os.path.exists(app_file):
            print(f"❌ Error: {app_file} no encontrado")
            return False
        
        try:
            self.streamlit_process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", app_file, 
                 "--server.headless", "true",
                 "--server.port", "8501"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar a que Streamlit inicie
            print("⏳ Esperando que Streamlit inicie...")
            time.sleep(8)
            
            if self.streamlit_process.poll() is not None:
                print("❌ Streamlit no pudo iniciar")
                return False
            
            print("✅ Streamlit iniciado en http://localhost:8501")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando Streamlit: {e}")
            return False
    
    def start_cloudflare_tunnel(self):
        """Inicia el túnel de Cloudflare"""
        print("\n📡 Creando túnel público con Cloudflare...")
        print("⏳ Esto puede tardar unos segundos...")
        print()
        
        try:
            self.cloudflare_process = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", "http://localhost:8501"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Leer la salida para encontrar la URL
            url_found = False
            for line in iter(self.cloudflare_process.stdout.readline, ''):
                line = line.strip()
                
                # Mostrar líneas importantes
                if "trycloudflare.com" in line or "INF" in line or "error" in line.lower():
                    print(line)
                
                # Detectar la URL pública
                if "trycloudflare.com" in line and not url_found:
                    import re
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        url = match.group(0)
                        self.display_success(url)
                        url_found = True
                        
                        # Seguir mostrando logs pero no bloquear
                        break
                
                if self.cloudflare_process.poll() is not None:
                    break
            
            if not url_found:
                print("⚠️  No se pudo obtener la URL del túnel")
                print("   Pero el túnel puede estar activo. Revisa los logs arriba.")
            
            # Mantener el proceso vivo
            print("\n💡 Presiona Ctrl+C para detener el túnel")
            print()
            
            # Bloquear aquí para que siga ejecutándose
            try:
                self.cloudflare_process.wait()
            except KeyboardInterrupt:
                pass
            
        except Exception as e:
            print(f"❌ Error creando túnel: {e}")
            return False
    
    def display_success(self, url):
        """Muestra mensaje de éxito con la URL"""
        print()
        print("=" * 70)
        print("✅ ¡TÚNEL CLOUDFLARE CREADO EXITOSAMENTE!")
        print("=" * 70)
        print()
        print(f"🌐 URL PÚBLICA: {url}")
        print()
        print("=" * 70)
        print()
        print("📋 Información importante:")
        print("   • Comparte este link con quien quieras")
        print("   • El chatbot se conecta a tu Rasa y BD locales")
        print("   • ⚡ Gratis sin límites de tiempo (Cloudflare)")
        print("   • 🔒 Protegido por la red de Cloudflare")
        print()
        print("⚠️  RECUERDA:")
        print("   • Tu computadora debe permanecer encendida")
        print("   • Rasa debe estar ejecutándose (localhost:5005)")
        print("   • PostgreSQL debe estar activo")
        print()
        print("🛑 Para detener: Presiona Ctrl+C")
        print()
        print("-" * 70)
        print()
    
    def cleanup(self):
        """Limpia los procesos al salir"""
        print("\n\n🛑 Cerrando túnel y aplicación...")
        
        if self.cloudflare_process:
            try:
                self.cloudflare_process.terminate()
                self.cloudflare_process.wait(timeout=5)
            except:
                self.cloudflare_process.kill()
        
        if self.streamlit_process:
            try:
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=5)
            except:
                self.streamlit_process.kill()
        
        print("✅ Procesos cerrados correctamente")
        print()
        print("👋 ¡Hasta luego!")
    
    def run(self):
        """Ejecuta todo el proceso"""
        self.print_header()
        
        # 1. Verificar Rasa
        if not self.check_rasa():
            input("\nPresiona Enter para salir...")
            return
        
        print()
        
        # 2. Verificar cloudflared
        if not self.check_cloudflared():
            input("\nPresiona Enter para salir...")
            return
        
        # 3. Seleccionar archivo de app
        print("\n📂 ¿Qué interfaz quieres usar?")
        print("   1. app.py - Versión completa con sidebar y dashboard")
        print("   2. app_public.py - Versión moderna con burbujas")
        print()
        
        choice = input("Selecciona (1 o 2) [default: 1]: ").strip()
        
        if choice == "2" and os.path.exists("app_public.py"):
            app_file = "app_public.py"
        else:
            app_file = "app.py"
        
        print(f"\n✅ Usando: {app_file}")
        
        try:
            # 4. Iniciar Streamlit
            if not self.start_streamlit(app_file):
                input("\nPresiona Enter para salir...")
                return
            
            # 5. Crear túnel de Cloudflare
            self.start_cloudflare_tunnel()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupción detectada...")
        
        finally:
            self.cleanup()

def main():
    """Función principal"""
    launcher = CloudflareChatbotLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
"""
Script para ejecutar el chatbot con Cloudflare Tunnel
Todo se ejecuta localmente (Rasa, PostgreSQL) pero la interfaz
es accesible desde cualquier lugar vía Cloudflare.

VENTAJAS:
- Gratis sin límites de tiempo
- Más rápido que Ngrok
- Red global de Cloudflare
- Protección DDoS incluida

REQUISITOS:
1. Instalar cloudflared:
   Windows: https://github.com/cloudflare/cloudflared/releases
   Linux: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
   Mac: brew install cloudflare/cloudflare/cloudflared

2. Python packages:
   pip install streamlit

USO:
    python run_cloudflare.py
"""

import subprocess
import sys
import os
import glob
import time
import signal
import threading

class CloudflareStreamlitRunner:
    def __init__(self):
        self.streamlit_process = None
        self.cloudflare_process = None
        
    def find_app_file(self):
        """Encuentra el archivo principal de la app"""
        py_files = glob.glob("*.py")
        py_files = [f for f in py_files if f not in ["run_cloudflare.py", "run_public.py"]]
        
        if len(py_files) == 1:
            return py_files[0]
        else:
            print("📄 Archivos Python encontrados:")
            for i, f in enumerate(py_files, 1):
                print(f"   {i}. {f}")
            
            choice = input("\nSelecciona el archivo de la app (número): ")
            return py_files[int(choice) - 1]
    
    def check_cloudflared(self):
        """Verifica si cloudflared está instalado"""
        try:
            result = subprocess.run(
                ["cloudflared", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def start_streamlit(self, app_file):
        """Inicia Streamlit"""
        print(f"🚀 Iniciando Streamlit con {app_file}...")
        self.streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", app_file, "--server.headless", "true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar a que Streamlit inicie
        print("⏳ Esperando que Streamlit inicie...")
        time.sleep(5)
        
        if self.streamlit_process.poll() is not None:
            print("❌ Error: Streamlit no pudo iniciar")
            return False
        
        print("✅ Streamlit iniciado en http://localhost:8501")
        return True
    
    def start_cloudflare_tunnel(self):
        """Inicia el túnel de Cloudflare"""
        print("\n📡 Creando túnel público con Cloudflare...")
        
        self.cloudflare_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", "http://localhost:8501"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Leer la salida para encontrar la URL
        url_found = False
        for line in iter(self.cloudflare_process.stdout.readline, ''):
            print(line.strip())
            
            if "trycloudflare.com" in line and not url_found:
                # Extraer la URL
                import re
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    url = match.group(0)
                    self.display_success(url)
                    url_found = True
            
            if self.cloudflare_process.poll() is not None:
                break
    
    def display_success(self, url):
        """Muestra mensaje de éxito con la URL"""
        print("\n" + "=" * 70)
        print("✅ ¡TÚNEL CLOUDFLARE CREADO EXITOSAMENTE!")
        print("=" * 70)
        print()
        print(f"🌐 URL PÚBLICA: {url}")
        print()
        print("=" * 70)
        print()
        print("📋 Comparte este link con quien quieras")
        print("⚡ Ventajas:")
        print("   • Gratis sin límites de tiempo")
        print("   • Protegido por la red de Cloudflare")
        print("   • Rápido y confiable")
        print()
        print("⚠️  IMPORTANTE:")
        print("   • Tu computadora debe permanecer encendida")
        print("   • Rasa debe estar en localhost:5005")
        print("   • PostgreSQL debe estar activo")
        print()
        print("🛑 Para detener: Presiona Ctrl+C")
        print()
        print("-" * 70)
    
    def cleanup(self):
        """Limpia los procesos al salir"""
        print("\n\n🛑 Cerrando túnel y aplicación...")
        
        if self.cloudflare_process:
            self.cloudflare_process.terminate()
            self.cloudflare_process.wait()
        
        if self.streamlit_process:
            self.streamlit_process.terminate()
            self.streamlit_process.wait()
        
        print("✅ Cerrado correctamente")
    
    def run(self):
        """Ejecuta todo el proceso"""
        print("=" * 70)
        print("🏛️  SISTEMA DE TURNOS - CÉDULAS DE IDENTIDAD")
        print("    Ciudad del Este - Cloudflare Tunnel")
        print("=" * 70)
        print()
        
        # Verificar cloudflared
        if not self.check_cloudflared():
            print("❌ ERROR: cloudflared no está instalado")
            print()
            print("📥 Descarga e instala cloudflared:")
            print("   Windows: https://github.com/cloudflare/cloudflared/releases")
            print("   Mac: brew install cloudflare/cloudflare/cloudflared")
            print("   Linux: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64")
            return
        
        print("✅ cloudflared detectado")
        
        # Encontrar archivo de la app
        app_file = self.find_app_file()
        print(f"📄 Archivo de la app: {app_file}")
        print()
        
        try:
            # Iniciar Streamlit
            if not self.start_streamlit(app_file):
                return
            
            # Iniciar Cloudflare Tunnel
            self.start_cloudflare_tunnel()
            
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

def main():
    runner = CloudflareStreamlitRunner()
    runner.run()

if __name__ == "__main__":
    main()