
import subprocess
import sys
import os
import time
import requests
from datetime import datetime
import json

class CloudflarePermanentTunnel:
    def __init__(self):
        self.streamlit_process = None
        self.cloudflare_process = None
        self.rasa_online = False
        
        # CONFIGURACIÓN DEL TUNNEL PERMANENTE
        self.tunnel_name = "identificaciones-cde"
        self.config_file = "cloudflare-tunnel-config.yml"
        self.credentials_file = None
        self.streamlit_port = 8501
        
    def print_header(self):
        """Imprime el header del script"""
        print("=" * 70)
        print("🏛️  SISTEMA DE TURNOS CÉDULAS - TUNNEL PERMANENTE")
        print("    Ciudad del Este - URL Fija para Acceso Público")
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
        except Exception:
            print("❌ Rasa NO está ejecutándose")
            print()
            print("🔧 SOLUCIÓN:")
            print("   Abre una terminal separada y ejecuta:")
            print("   → rasa run --enable-api --cors \"*\"")
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
                print(f"✅ cloudflared encontrado")
                return True
            else:
                print("❌ cloudflared no funciona correctamente")
                return False
                
        except FileNotFoundError:
            print("❌ cloudflared NO está instalado")
            print()
            print("📥 SOLUCIÓN:")
            print("   Descarga desde: https://github.com/cloudflare/cloudflared/releases")
            print("   O ejecuta: pip install cloudflared")
            print()
            return False
        except Exception as e:
            print(f"❌ Error verificando cloudflared: {e}")
            return False
    
    def authenticate_cloudflare(self):
        """Autentica con Cloudflare (solo primera vez)"""
        print("🔐 Verificando autenticación con Cloudflare...")
        
        # Verificar si ya está autenticado
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Ya autenticado con Cloudflare")
                return True
            else:
                print("🔑 Necesitas autenticarte con Cloudflare")
                print("   Se abrirá tu navegador para autorizar...")
                
                # Ejecutar autenticación
                auth_result = subprocess.run(
                    ["cloudflared", "tunnel", "login"],
                    capture_output=True,
                    text=True
                )
                
                if auth_result.returncode == 0:
                    print("✅ Autenticación exitosa")
                    return True
                else:
                    print("❌ Error en autenticación")
                    print(auth_result.stderr)
                    return False
                    
        except Exception as e:
            print(f"❌ Error verificando autenticación: {e}")
            return False
    
    def check_tunnel_exists(self):
        """Verifica si el tunnel ya existe"""
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list"],
                capture_output=True,
                text=True
            )
            
            if self.tunnel_name in result.stdout:
                print(f"✅ Tunnel '{self.tunnel_name}' ya existe")
                return True
            else:
                print(f"🔧 Creando tunnel permanente '{self.tunnel_name}'...")
                return False
                
        except Exception as e:
            print(f"⚠️  Error verificando tunnel: {e}")
            return False
    
    def create_tunnel(self):
        """Crea el tunnel permanente"""
        try:
            # Crear tunnel
            result = subprocess.run(
                ["cloudflared", "tunnel", "create", self.tunnel_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✅ Tunnel '{self.tunnel_name}' creado exitosamente")
                return True
            else:
                print(f"❌ Error creando tunnel: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error creando tunnel: {e}")
            return False
    
    def get_tunnel_info(self):
        """Obtiene información del tunnel"""
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list"],
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.split('\n')
            for line in lines:
                if self.tunnel_name in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        tunnel_id = parts[0]
                        print(f"📋 Tunnel ID: {tunnel_id}")
                        return tunnel_id
            
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo info del tunnel: {e}")
            return None
    
    def create_config_file(self, tunnel_id):
        """Crea archivo de configuración para el tunnel"""
        try:
            # Buscar archivo de credenciales
            home_dir = os.path.expanduser("~")
            cred_path = os.path.join(home_dir, ".cloudflared", f"{tunnel_id}.json")
            
            if not os.path.exists(cred_path):
                print(f"⚠️  Archivo de credenciales no encontrado en: {cred_path}")
                return False
            
            # Crear contenido de configuración
            config_content = f"""tunnel: {tunnel_id}
credentials-file: {cred_path}

ingress:
  - service: http://localhost:{self.streamlit_port}
"""
            
            # Escribir archivo de configuración
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            
            print(f"✅ Archivo de configuración creado: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error creando archivo de configuración: {e}")
            return False
    
    def start_streamlit(self):
        """Inicia Streamlit"""
        print(f"🚀 Iniciando Streamlit en puerto {self.streamlit_port}...")
        
        try:
            # Comando para iniciar Streamlit
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                "app_public.py",
                "--server.port", str(self.streamlit_port),
                "--server.address", "localhost",
                "--server.headless", "true"
            ]
            
            self.streamlit_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar un poco para que Streamlit inicie
            time.sleep(3)
            
            if self.streamlit_process.poll() is None:
                print(f"✅ Streamlit iniciado en http://localhost:{self.streamlit_port}")
                return True
            else:
                print("❌ Error iniciando Streamlit")
                return False
                
        except Exception as e:
            print(f"❌ Error iniciando Streamlit: {e}")
            return False
    
    def start_tunnel(self):
        """Inicia el tunnel permanente"""
        print("🌐 Iniciando Cloudflare Tunnel...")
        print()
        print("🔗 Tu URL será:")
        print("   https://identificaciones-cde-XXX.trycloudflare.com")
        print()
        print("📌 Esta URL será SIEMPRE LA MISMA")
        print("   Guárdala para acceso futuro")
        print()
        
        try:
            # Comando para iniciar tunnel
            cmd = [
                "cloudflared", "tunnel",
                "--config", self.config_file,
                "run", self.tunnel_name
            ]
            
            # Ejecutar tunnel (esto bloquea hasta que se termine)
            self.cloudflare_process = subprocess.run(cmd)
            
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo tunnel...")
        except Exception as e:
            print(f"❌ Error ejecutando tunnel: {e}")
    
    def cleanup(self):
        """Limpia procesos al terminar"""
        print("\n🧹 Limpiando procesos...")
        
        if self.streamlit_process:
            try:
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=5)
                print("✅ Streamlit detenido")
            except:
                self.streamlit_process.kill()
                print("⚠️  Streamlit forzado a terminar")
    
    def setup_permanent_tunnel(self):
        """Configura el tunnel permanente (solo primera vez)"""
        print("⚙️  CONFIGURACIÓN INICIAL DEL TUNNEL PERMANENTE")
        print("=" * 50)
        
        # 1. Autenticar
        if not self.authenticate_cloudflare():
            return False
        
        # 2. Verificar/crear tunnel
        if not self.check_tunnel_exists():
            if not self.create_tunnel():
                return False
        
        # 3. Obtener info del tunnel
        tunnel_id = self.get_tunnel_info()
        if not tunnel_id:
            print("❌ No se pudo obtener información del tunnel")
            return False
        
        # 4. Crear archivo de configuración
        if not self.create_config_file(tunnel_id):
            return False
        
        print("\n✅ CONFIGURACIÓN COMPLETADA")
        print("   Tu tunnel permanente está listo")
        print()
        
        return True
    
    def run(self):
        """Función principal"""
        try:
            self.print_header()
            
            # Verificaciones previas
            if not self.check_cloudflared():
                return
            
            # Verificar Rasa (opcional pero recomendado)
            self.check_rasa()
            
            # Configurar tunnel permanente si es necesario
            if not os.path.exists(self.config_file):
                print("🔧 Primera ejecución - Configurando tunnel permanente...")
                if not self.setup_permanent_tunnel():
                    return
            else:
                print("✅ Configuración existente encontrada")
            
            # Iniciar Streamlit
            if not self.start_streamlit():
                return
            
            print("\n" + "="*50)
            print("🎉 SISTEMA LISTO")
            print("="*50)
            
            # Iniciar tunnel (esto bloquea hasta Ctrl+C)
            self.start_tunnel()
            
        except KeyboardInterrupt:
            print("\n\n🛑 Deteniendo sistema...")
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
        finally:
            self.cleanup()
            print("\n👋 Sistema detenido. ¡Hasta luego!")

if __name__ == "__main__":
    tunnel = CloudflarePermanentTunnel()
    tunnel.run()