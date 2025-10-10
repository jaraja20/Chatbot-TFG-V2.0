import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(12, 14))
ax.set_xlim(0, 10)
ax.set_ylim(0, 16)
ax.axis('off')

# Colores
color_input = '#E3F2FD'
color_process = '#BBDEFB'
color_core = '#64B5F6'
color_output = '#90CAF9'
color_final = '#C8E6C9'

# Función para crear cajas
def create_box(ax, x, y, width, height, text, color, fontsize=11, bold=False):
    box = FancyBboxPatch((x, y), width, height, 
                         boxstyle="round,pad=0.1", 
                         edgecolor='#1976D2', 
                         facecolor=color, 
                         linewidth=2)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + width/2, y + height/2, text, 
            ha='center', va='center', 
            fontsize=fontsize, weight=weight, 
            wrap=True)

# Función para crear flechas
def create_arrow(ax, x1, y1, x2, y2):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle='->', 
                           mutation_scale=30, 
                           linewidth=2.5,
                           color='#1976D2')
    ax.add_patch(arrow)

# ENTRADA
create_box(ax, 1, 14.5, 8, 1, 
           'ENTRADA DEL USUARIO\n"Quiero mi cédula para mañana a las 10"', 
           color_input, 12, True)
create_arrow(ax, 5, 14.5, 5, 13.8)

# TOKENIZACIÓN
create_box(ax, 1, 13, 8, 0.7, 
           'TOKENIZACIÓN\n["quiero", "mi", "cédula", "para", "mañana", "a", "10"]', 
           color_process, 10)
create_arrow(ax, 5, 13, 5, 12.3)

# EMBEDDINGS
create_box(ax, 1, 11.5, 8, 0.7, 
           'EMBEDDINGS (Vectorización)\nConvierte palabras en vectores numéricos', 
           color_process, 10)
create_arrow(ax, 5, 11.5, 5, 10.5)

# TRANSFORMER ENCODER (caja grande)
create_box(ax, 0.5, 7.5, 9, 2.8, '', color_core)
ax.text(5, 10, 'TRANSFORMER ENCODER (Núcleo DIET)', 
        ha='center', va='center', fontsize=12, weight='bold')

# Capas internas del transformer
create_box(ax, 1.5, 8.5, 7, 0.5, 
           'Capa de Auto-Atención 1', '#42A5F5', 9)
create_box(ax, 1.5, 8.8, 7, 0.5, 
           'Capa de Auto-Atención 2', '#42A5F5', 9)
create_box(ax, 1.5, 9.1, 7, 0.5, 
           'Capa de Auto-Atención N', '#42A5F5', 9)
ax.text(5, 9.6, 'Analiza relaciones entre palabras\nComprende contexto', 
        ha='center', va='center', fontsize=9, style='italic')

# Flechas divergentes
create_arrow(ax, 5, 7.5, 2.5, 6.5)
create_arrow(ax, 5, 7.5, 7.5, 6.5)

# SALIDA DUAL
# Clasificador de Intenciones (izquierda)
create_box(ax, 0.5, 5, 4, 1.3, 
           'CLASIFICADOR DE\nINTENCIONES\n\nsolicitar_turno\n(confianza: 0.94)', 
           color_output, 10, True)

# Extractor de Entidades (derecha)
create_box(ax, 5.5, 5, 4, 1.3, 
           'EXTRACTOR DE\nENTIDADES\n\n• fecha: "mañana"\n• hora: "10:00"', 
           color_output, 10, True)

# Flechas convergentes
create_arrow(ax, 2.5, 5, 5, 4)
create_arrow(ax, 7.5, 5, 5, 4)

# SALIDA ESTRUCTURADA
create_box(ax, 1, 2.5, 8, 1.3, 
           'SALIDA ESTRUCTURADA\n\nIntención: solicitar_turno\nEntidades: {fecha: "mañana", hora: "10:00"}\n\n→ Pasa a Gestor de Diálogo', 
           color_final, 10, True)

# Flecha final
create_arrow(ax, 5, 2.5, 5, 1.5)

# SALIDA FINAL
create_box(ax, 2, 0.5, 6, 0.8, 
           'Procesamiento adicional (Lógica Difusa / Acciones)', 
           '#A5D6A7', 10)

# Título
ax.text(5, 15.5, 'ARQUITECTURA DEL MODELO DIET', 
        ha='center', va='center', fontsize=16, weight='bold')
ax.text(5, 15.2, '(Dual Intent and Entity Transformer)', 
        ha='center', va='center', fontsize=11, style='italic')

plt.tight_layout()
plt.savefig('Diagrama_DIET.png', dpi=300, bbox_inches='tight', facecolor='white')
print("✓ Diagrama guardado como 'Diagrama_DIET.png'")
plt.show()