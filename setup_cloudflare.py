"""
Script simplificado para configurar Cloudflare Tunnel
"""

import subprocess
import sys
import os
import time
import json

def print_header():
    print("="*80)
    print("🌐 CONFIGURACIÓN DE CLOUDFLARE TUNNEL")
    print("   Sistema de Turnos - Ciudad del Este")
    print("="*80)
    print()

def check_cloudflared():
    """Verifica que cloudflared esté instalado"""
    try:
        result = subprocess.run(
            ["cloudflared", "--version"],
            capture_output=True,
            text=True
        )
        print(f"✅ Cloudflared instalado: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("❌ Cloudflared NO está instalado")
        print()
        print("🔧 INSTALACIÓN:")
        print("   1. Descarga desde: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
        print("   2. O usa winget: winget install --id Cloudflare.cloudflared")
        return False

def check_authentication():
    """Verifica si ya está autenticado"""
    cert_path = os.path.expanduser("~/.cloudflared/cert.pem")
    
    if os.path.exists(cert_path):
        print(f"✅ Ya estás autenticado (cert.pem encontrado)")
        return True
    else:
        print("⚠️  No estás autenticado con Cloudflare")
        return False

def authenticate():
    """Autentica con Cloudflare"""
    print("\n🔐 Iniciando autenticación con Cloudflare...")
    print("   Se abrirá tu navegador para autorizar el acceso")
    print()
    
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "login"],
            check=False
        )
        
        if result.returncode == 0:
            print("\n✅ Autenticación exitosa!")
            return True
        else:
            print("\n❌ Error en autenticación")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def list_tunnels():
    """Lista los tunnels existentes"""
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "list"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n📋 TUNNELS EXISTENTES:")
            print("-"*80)
            print(result.stdout)
            return result.stdout
        else:
            print("⚠️  No se pudieron listar los tunnels")
            return ""
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return ""

def create_tunnel(tunnel_name="chatbot-cde"):
    """Crea un nuevo tunnel"""
    print(f"\n🔧 Creando tunnel '{tunnel_name}'...")
    
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "create", tunnel_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Tunnel '{tunnel_name}' creado exitosamente")
            print(result.stdout)
            
            # Extraer ID del tunnel
            for line in result.stdout.split('\n'):
                if "Created tunnel" in line:
                    print(f"\n📝 {line}")
            
            return True
        else:
            if "already exists" in result.stderr:
                print(f"✅ Tunnel '{tunnel_name}' ya existe")
                return True
            else:
                print(f"❌ Error creando tunnel: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_config_file(tunnel_name="chatbot-cde"):
    """Crea el archivo de configuración del tunnel"""
    
    config_content = f"""tunnel: {tunnel_name}
credentials-file: C:\\Users\\{os.getenv('USERNAME')}\\.cloudflared\\{tunnel_name}.json

ingress:
  - service: http://localhost:5000
"""
    
    config_path = "cloudflare-config.yml"
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        print(f"\n✅ Archivo de configuración creado: {config_path}")
        print("\n📄 Contenido:")
        print("-"*80)
        print(config_content)
        print("-"*80)
        return True
        
    except Exception as e:
        print(f"❌ Error creando config: {e}")
        return False

def run_tunnel(tunnel_name="chatbot-cde"):
    """Inicia el tunnel"""
    print(f"\n🚀 Iniciando tunnel '{tunnel_name}'...")
    print("   Presiona Ctrl+C para detener")
    print()
    
    try:
        # Ejecutar tunnel con config
        subprocess.run(
            ["cloudflared", "tunnel", "--config", "cloudflare-config.yml", "run", tunnel_name],
            check=False
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  Tunnel detenido")
    except Exception as e:
        print(f"\n❌ Error ejecutando tunnel: {e}")

def get_tunnel_url(tunnel_name="chatbot-cde"):
    """Obtiene la URL del tunnel"""
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "info", tunnel_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("\n🌐 INFORMACIÓN DEL TUNNEL:")
            print("-"*80)
            print(result.stdout)
            return True
        else:
            print("⚠️  No se pudo obtener info del tunnel")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print_header()
    
    # 1. Verificar instalación
    if not check_cloudflared():
        return
    
    print()
    
    # 2. Verificar autenticación
    if not check_authentication():
        respuesta = input("\n¿Deseas autenticarte ahora? (s/n): ")
        if respuesta.lower() == 's':
            if not authenticate():
                return
        else:
            print("❌ Autenticación requerida para continuar")
            return
    
    print()
    
    # 3. Listar tunnels existentes
    tunnels_output = list_tunnels()
    
    # 4. Preguntar nombre del tunnel
    print("\n" + "="*80)
    tunnel_name = input("Nombre para el tunnel (default: chatbot-cde): ").strip()
    if not tunnel_name:
        tunnel_name = "chatbot-cde"
    
    # 5. Crear tunnel si no existe
    if tunnel_name not in tunnels_output:
        if not create_tunnel(tunnel_name):
            return
    
    # 6. Crear archivo de configuración
    if not create_config_file(tunnel_name):
        return
    
    # 7. Obtener información del tunnel
    get_tunnel_url(tunnel_name)
    
    # 8. Preguntar si iniciar tunnel
    print("\n" + "="*80)
    print("⚠️  IMPORTANTE:")
    print("   - El servidor Flask debe estar corriendo en localhost:5000")
    print("   - El tunnel permanecerá activo hasta que lo detengas con Ctrl+C")
    print()
    
    respuesta = input("¿Deseas iniciar el tunnel ahora? (s/n): ")
    if respuesta.lower() == 's':
        run_tunnel(tunnel_name)
    else:
        print("\n✅ Configuración completada!")
        print(f"\n📝 Para iniciar el tunnel más tarde, ejecuta:")
        print(f"   cloudflared tunnel --config cloudflare-config.yml run {tunnel_name}")
        print()
        print(f"📝 Para obtener la URL pública, ejecuta:")
        print(f"   cloudflared tunnel info {tunnel_name}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Configuración cancelada")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
