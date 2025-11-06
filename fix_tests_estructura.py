"""
Script mejorado para arreglar TODOS los tests automáticamente
Agrega:
- Función main()
- if __name__ == "__main__"
- Código de salida apropiado
- Try-except
"""
import sys
import re
from pathlib import Path

def tiene_main_correcto(contenido):
    """Verifica si el test ya tiene estructura main correcta"""
    return (
        'def main():' in contenido and
        'if __name__ == "__main__":' in contenido and
        'sys.exit(' in contenido
    )

def envolver_en_main(contenido):
    """Envuelve el código principal en una función main()"""
    lines = contenido.split('\n')
    
    # Encontrar donde empieza el código ejecutable (después de imports y funciones)
    codigo_inicio = 0
    en_funcion = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip líneas vacías, comentarios, imports, docstrings
        if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        if stripped.startswith('import ') or stripped.startswith('from '):
            codigo_inicio = i + 1
            continue
        if stripped.startswith('def '):
            en_funcion = True
            continue
        if en_funcion and not line.startswith(' ') and not line.startswith('\t'):
            en_funcion = False
            codigo_inicio = i
            break
        if not en_funcion and (stripped.startswith('print(') or stripped.startswith('casos_') or '=' in stripped):
            codigo_inicio = i
            break
    
    # Separar imports/funciones del código principal
    parte_imports = lines[:codigo_inicio]
    parte_codigo = lines[codigo_inicio:]
    
    # Indentar el código principal
    parte_codigo_indentada = []
    for line in parte_codigo:
        if line.strip():  # No agregar espacios a líneas vacías
            parte_codigo_indentada.append('    ' + line)
        else:
            parte_codigo_indentada.append(line)
    
    # Buscar si hay un print final con resultados
    tiene_resultado = any('print(' in line and ('correctos' in line.lower() or 'resultado' in line.lower()) 
                         for line in parte_codigo)
    
    # Construir la nueva estructura
    nuevo_codigo = parte_imports + [
        '',
        'def main():',
    ] + parte_codigo_indentada
    
    # Agregar return apropiado si no existe
    if 'return ' not in '\n'.join(parte_codigo):
        if tiene_resultado:
            nuevo_codigo += [
                '    ',
                '    # TODO: Agregar lógica de éxito/fallo',
                '    return 0  # Cambiar según criterio de éxito',
            ]
        else:
            nuevo_codigo += [
                '    return 0',
            ]
    
    # Agregar if __name__ == "__main__"
    nuevo_codigo += [
        '',
        'if __name__ == "__main__":',
        '    try:',
        '        exit_code = main()',
        '        sys.exit(exit_code)',
        '    except Exception as e:',
        '        print(f"[ERROR] {type(e).__name__}: {str(e)}")',
        '        import traceback',
        '        traceback.print_exc()',
        '        sys.exit(1)',
    ]
    
    return '\n'.join(nuevo_codigo)

def fix_test_avanzado(filepath):
    """Arregla un test con estructura main correcta"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
        
        # Si ya tiene estructura correcta, skip
        if tiene_main_correcto(contenido):
            return False, "Ya tiene estructura correcta"
        
        # Si tiene if __name__ pero sin sys.exit
        if 'if __name__ == "__main__":' in contenido and 'sys.exit(' not in contenido:
            # Solo agregar sys.exit
            contenido = contenido.replace(
                'if __name__ == "__main__":',
                '''if __name__ == "__main__":
    try:
        exit_code = main() if 'def main()' in globals() else 0
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
'''
            )
        else:
            # Envolver todo en main()
            contenido = envolver_en_main(contenido)
        
        # Guardar
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        return True, "Estructurado"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    tests_dir = Path(__file__).parent / "tests"
    
    print("="*70)
    print(" REESTRUCTURADOR AVANZADO DE TESTS")
    print("="*70)
    print()
    
    archivos_actualizados = 0
    archivos_skip = 0
    archivos_error = 0
    
    for test_file in sorted(tests_dir.glob("test_*.py")):
        # Skip los que ya sabemos que funcionan
        if test_file.name in ['test_affirm.py', 'test_urgencia.py', 'test_fuzzy_mejorado.py']:
            print(f"{test_file.name:50} [SKIP] Ya arreglado")
            archivos_skip += 1
            continue
            
        print(f"{test_file.name:50}", end=" ")
        actualizado, mensaje = fix_test_avanzado(test_file)
        
        if actualizado:
            print(f"[OK] {mensaje}")
            archivos_actualizados += 1
        elif "Error" in mensaje:
            print(f"[FAIL] {mensaje}")
            archivos_error += 1
        else:
            print(f"[SKIP] {mensaje}")
            archivos_skip += 1
    
    print()
    print("="*70)
    print(f"Actualizados: {archivos_actualizados}")
    print(f"Sin cambios:  {archivos_skip}")
    print(f"Errores:      {archivos_error}")
    print("="*70)

if __name__ == "__main__":
    main()
