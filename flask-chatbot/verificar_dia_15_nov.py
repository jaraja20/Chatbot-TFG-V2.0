from datetime import datetime

fecha = datetime(2025, 11, 15)
dia_semana = fecha.strftime('%A')  # Nombre del día en inglés
dias_espanol = {
    'Monday': 'Lunes',
    'Tuesday': 'Martes',
    'Wednesday': 'Miércoles',
    'Thursday': 'Jueves',
    'Friday': 'Viernes',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

print(f"📅 15 de Noviembre de 2025 es: {dias_espanol[dia_semana]}")
