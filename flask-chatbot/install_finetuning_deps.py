"""
Instalador de dependencias para fine-tuning
"""

import subprocess
import sys

print("📦 Instalando dependencias para fine-tuning...")
print("=" * 60)

dependencies = [
    "torch",  # Ya debería estar instalado
    "transformers>=4.36.0",
    "datasets",
    "peft",  # Para LoRA
    "accelerate",  # Para optimización
    "bitsandbytes",  # Para quantización 4-bit
]

# Intentar instalar unsloth (opcional, solo en Linux/WSL)
optional_deps = [
    "unsloth",  # Más rápido pero solo en ciertos sistemas
]

for dep in dependencies:
    print(f"\n📥 Instalando {dep}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "--quiet"])
        print(f"✅ {dep} instalado")
    except Exception as e:
        print(f"❌ Error instalando {dep}: {e}")

print("\n⚠️ Intentando instalar unsloth (opcional, puede fallar en Windows)...")
for dep in optional_deps:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "--quiet"])
        print(f"✅ {dep} instalado")
    except Exception as e:
        print(f"⚠️ {dep} no disponible (normal en Windows), usaremos transformers estándar")

print("\n" + "=" * 60)
print("✅ Instalación completada!")
print("=" * 60)
print("\n📝 Resumen:")
print("   - torch: Framework base")
print("   - transformers: Modelos y tokenizers")
print("   - datasets: Manejo de datasets")
print("   - peft: LoRA (eficiente)")
print("   - accelerate: Optimización")
print("   - bitsandbytes: Quantización")
print("\n🚀 Listo para ejecutar fine_tune_llm.py")
