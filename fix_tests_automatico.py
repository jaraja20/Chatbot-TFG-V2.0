"""
Script para arreglar automáticamente todos los tests
- Elimina emojis problemáticos
- Actualiza imports
- Agrega manejo de errores
"""
import os
import re
from pathlib import Path

# Mapa de emojis a texto
EMOJI_MAP = {
    '✅': '[OK]',
    '❌': '[FAIL]',
    '⏱️': '[TIME]',
    '⏱': '[TIME]',
    '🔧': '[FIX]',
    '📝': '[NOTE]',
    '🎯': '[TARGET]',
    '🚀': '[START]',
    '📊': '[STATS]',
    '🧪': '[TEST]',
    '🔍': '[SEARCH]',
    '💬': '[CHAT]',
    '🕐': '[CLOCK]',
    '📧': '[EMAIL]',
    '🗣️': '[TALK]',
    '🗣': '[TALK]',
    '🧠': '[BRAIN]',
    '📅': '[CAL]',
    '⚠️': '[WARN]',
    '⚠': '[WARN]',
    '🔄': '[LOOP]',
    '✨': '[STAR]',
    '👤': '[USER]',
    '🤖': '[BOT]',
    '📈': '[GRAPH]',
    '🎓': '[EDU]',
    '💡': '[IDEA]',
    '🏥': '[HEALTH]',
}

def eliminar_emojis(texto):
    """Elimina o reemplaza emojis problemáticos"""
    for emoji, replacement in EMOJI_MAP.items():
        texto = texto.replace(emoji, replacement)
    
    # Eliminar otros emojis usando regex
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # símbolos & pictogramas
        u"\U0001F680-\U0001F6FF"  # transporte & símbolos de mapa
        u"\U0001F1E0-\U0001F1FF"  # banderas
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    texto = emoji_pattern.sub('[*]', texto)
    
    return texto

def agregar_encoding_header(contenido):
    """Agrega header de encoding si no existe"""
    if '# -*- coding: utf-8 -*-' not in contenido and '# coding: utf-8' not in contenido:
        # Agregar después de la primera línea de docstring si existe
        lines = contenido.split('\n')
        if lines and lines[0].startswith('"""'):
            # Buscar el cierre del docstring
            for i, line in enumerate(lines[1:], 1):
                if '"""' in line:
                    lines.insert(i + 1, '# -*- coding: utf-8 -*-')
                    return '\n'.join(lines)
        # Si no hay docstring, agregar al principio
        return '# -*- coding: utf-8 -*-\n' + contenido
    return contenido

def actualizar_imports(contenido):
    """Actualiza imports obsoletos"""
    # Agregar sys.path si no existe
    if 'sys.path' not in contenido and 'from razonamiento_difuso' in contenido:
        lines = contenido.split('\n')
        # Buscar la primera línea de import
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                # Agregar configuración de path antes
                lines.insert(i, 'import sys')
                lines.insert(i + 1, 'from pathlib import Path')
                lines.insert(i + 2, 'sys.path.insert(0, str(Path(__file__).parent.parent / "flask-chatbot"))')
                lines.insert(i + 3, '')
                return '\n'.join(lines)
    
    return contenido

def agregar_try_except(contenido):
    """Agrega try-except al código principal si no existe"""
    if 'if __name__' in contenido and 'try:' not in contenido.split('if __name__')[1]:
        contenido = contenido.replace(
            'if __name__ == "__main__":',
            '''if __name__ == "__main__":
    try:'''
        )
        # Agregar except al final si no existe
        if not contenido.strip().endswith('pass'):
            contenido += '''
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
'''
    return contenido

def fix_test_file(filepath):
    """Arregla un archivo de test"""
    try:
        # Leer archivo
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
        
        original = contenido
        
        # Aplicar fixes
        contenido = eliminar_emojis(contenido)
        contenido = agregar_encoding_header(contenido)
        contenido = actualizar_imports(contenido)
        contenido = agregar_try_except(contenido)
        
        # Guardar si hubo cambios
        if contenido != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(contenido)
            return True, "Actualizado"
        else:
            return False, "Sin cambios"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Procesa todos los tests"""
    tests_dir = Path(__file__).parent / "tests"
    
    print("="*70)
    print(" ACTUALIZADOR AUTOMATICO DE TESTS")
    print("="*70)
    print(f"Directorio: {tests_dir}")
    print()
    
    archivos_procesados = 0
    archivos_actualizados = 0
    archivos_error = 0
    
    # Procesar todos los archivos .py en tests/
    for test_file in sorted(tests_dir.glob("test_*.py")):
        print(f"Procesando: {test_file.name}...", end=" ")
        actualizado, mensaje = fix_test_file(test_file)
        
        if actualizado:
            print(f"[OK] {mensaje}")
            archivos_actualizados += 1
        elif "Error" in mensaje:
            print(f"[FAIL] {mensaje}")
            archivos_error += 1
        else:
            print(f"[SKIP] {mensaje}")
        
        archivos_procesados += 1
    
    print()
    print("="*70)
    print(" RESUMEN")
    print("="*70)
    print(f"Total procesados: {archivos_procesados}")
    print(f"Actualizados:     {archivos_actualizados}")
    print(f"Sin cambios:      {archivos_procesados - archivos_actualizados - archivos_error}")
    print(f"Errores:          {archivos_error}")
    print("="*70)
    print()
    print("[OK] Proceso completado")
    print()
    print("Siguiente paso:")
    print("  python ejecutor_tests_completo.py")
    print()

if __name__ == "__main__":
    main()
