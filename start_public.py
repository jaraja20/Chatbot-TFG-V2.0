"""
Script para iniciar el sistema completo con Cloudflare Tunnel
"""

import subprocess
import time
import sys

def print_header():
    print("="*80)
    print("🚀 SISTEMA DE TURNOS - CIUDAD DEL ESTE")
    print("   Iniciando con acceso público mediante Cloudflare")
    print("="*80)
    print()

def start_flask():
    """Inicia el servidor Flask"""
    print("🔷 Iniciando servidor Flask...")
    
    try:
        flask_process = subprocess.Popen(
            [r"C:\tfg funcional\.venv\Scripts\python.exe", "app.py"],
            cwd=r"C:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(3)  # Esperar a que Flask inicie
        
        if flask_process.poll() is None:
            print("✅ Flask corriendo en localhost:5000")
            return flask_process
        else:
            print("❌ Error iniciando Flask")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def start_tunnel():
    """Inicia el Cloudflare Tunnel"""
    print("\n🌐 Iniciando Cloudflare Tunnel...")
    
    try:
        tunnel_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--config", "cloudflare-config.yml", "run", "chatbot-cde"],
            cwd=r"C:\tfg funcional\Chatbot-TFG-V2.0",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Esperar y mostrar logs hasta que se registre la conexión
        print("📡 Esperando conexión...")
        
        for i in range(30):  # Esperar hasta 30 segundos
            line = tunnel_process.stdout.readline()
            if line:
                if "Registered tunnel connection" in line:
                    print("✅ Tunnel conectado!")
                    break
                elif "error" in line.lower() and "Application error 0x0" not in line:
                    print(f"⚠️  {line.strip()}")
            time.sleep(1)
        
        if tunnel_process.poll() is None:
            return tunnel_process
        else:
            print("❌ Error iniciando tunnel")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def show_info():
    """Muestra información del sistema"""
    print("\n" + "="*80)
    print("✅ SISTEMA ACTIVO")
    print("="*80)
    print()
    print("🌐 URL PÚBLICA:")
    print("   https://chatbot-cde.trycloudflare.com")
    print()
    print("📍 URL LOCAL:")
    print("   http://localhost:5000")
    print()
    print("📊 DASHBOARD (modo desarrollador):")
    print("   Escribe 'admin' o 'dashboard' en el chat")
    print()
    print("⏹️  Para detener: Presiona Ctrl+C")
    print("="*80)

def main():
    print_header()
    
    # Iniciar Flask
    flask_process = start_flask()
    if not flask_process:
        print("\n❌ No se pudo iniciar Flask")
        return
    
    # Iniciar Tunnel
    tunnel_process = start_tunnel()
    if not tunnel_process:
        print("\n❌ No se pudo iniciar Tunnel")
        flask_process.terminate()
        return
    
    # Mostrar información
    show_info()
    
    try:
        # Mantener procesos activos
        while True:
            time.sleep(1)
            
            # Verificar si algún proceso murió
            if flask_process.poll() is not None:
                print("\n❌ Flask se detuvo inesperadamente")
                break
            
            if tunnel_process.poll() is not None:
                print("\n❌ Tunnel se detuvo inesperadamente")
                break
                
    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo sistema...")
        
        if tunnel_process and tunnel_process.poll() is None:
            tunnel_process.terminate()
            print("✅ Tunnel detenido")
        
        if flask_process and flask_process.poll() is None:
            flask_process.terminate()
            print("✅ Flask detenido")
        
        print("\n👋 ¡Sistema detenido correctamente!")

if __name__ == "__main__":
    main()
