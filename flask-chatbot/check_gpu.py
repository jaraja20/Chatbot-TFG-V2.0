import torch

print("=" * 60)
print("🔍 DIAGNÓSTICO DE GPU")
print("=" * 60)

# CUDA disponible
cuda_available = torch.cuda.is_available()
print(f"\n✅ CUDA disponible: {cuda_available}")

if cuda_available:
    print(f"✅ Versión CUDA: {torch.version.cuda}")
    print(f"✅ Número de GPUs: {torch.cuda.device_count()}")
    print(f"✅ GPU actual: {torch.cuda.get_device_name(0)}")
    print(f"✅ Memoria total: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print("\n❌ CUDA no está disponible")
    print("\n🔍 Posibles causas:")
    print("   1. PyTorch instalado sin soporte CUDA")
    print("   2. Drivers NVIDIA no instalados o desactualizados")
    print("   3. CUDA Toolkit no compatible con PyTorch")
    
    print("\n📝 Versión actual de PyTorch:")
    print(f"   PyTorch: {torch.__version__}")
    
    print("\n💡 Para instalar PyTorch con CUDA:")
    print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")

print("\n" + "=" * 60)
