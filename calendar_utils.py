"""
Integración completa con Google Calendar para el sistema de turnos
"""

from __future__ import print_function
import datetime
import os
import pickle
import logging
from typing import Optional, Dict, Tuple

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Alcance para acceso de lectura/escritura en Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Configuración de la zona horaria
TIMEZONE = 'America/Asuncion'

def get_calendar_service():
    """Obtiene el servicio de Google Calendar autenticado"""
    creds = None
    
    # Cargar credenciales previas si existen
    if os.path.exists('token.pkl'):
        try:
            with open('token.pkl', 'rb') as token:
                creds = pickle.load(token)
            logger.info("Token cargado correctamente")
        except Exception as e:
            logger.error(f"Error cargando token: {e}")
            creds = None
    
    # Si no hay credenciales o son inválidas, iniciar autenticación
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Token refrescado correctamente")
            except Exception as e:
                logger.error(f"Error refrescando token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                logger.error("Archivo credentials.json no encontrado")
                raise FileNotFoundError("credentials.json no encontrado en el directorio")
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Autenticación completada exitosamente")
        
        # Guardar token para futuras ejecuciones
        try:
            with open('token.pkl', 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Token guardado correctamente")
        except Exception as e:
            logger.error(f"Error guardando token: {e}")
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error construyendo servicio de Calendar: {e}")
        raise

def crear_evento_turno(nombre: str, cedula: str, fecha_hora: datetime.datetime, 
                       codigo_turno: str, email_usuario: Optional[str] = None) -> Tuple[bool, str]:
    """
    Crea un evento en Google Calendar para un turno
    
    Args:
        nombre: Nombre completo del usuario
        cedula: Número de cédula (o "PRIMERA_VEZ")
        fecha_hora: Fecha y hora del turno
        codigo_turno: Código único del turno
        email_usuario: Email del usuario (opcional, para invitación)
    
    Returns:
        Tuple (éxito: bool, mensaje: str)
    """
    try:
        service = get_calendar_service()
        
        # Calcular hora de fin (20 minutos después)
        hora_fin = fecha_hora + datetime.timedelta(minutes=20)
        
        # Preparar descripción del evento
        tipo_tramite = "Primera cédula" if cedula == "PRIMERA_VEZ" else f"Renovación/Trámite - CI: {cedula}"
        
        descripcion = f"""
🎫 TURNO AGENDADO - Sistema Automatizado

👤 Nombre: {nombre}
🆔 {tipo_tramite}
🎫 Código de turno: {codigo_turno}

📍 Oficina de Identificaciones
Av. Pioneros del Este, Ciudad del Este

⚠️ IMPORTANTE:
- Llegar 15 minutos antes
- Traer código de turno: {codigo_turno}
- Traer documentos requeridos
- Tolerancia: 15 minutos

📋 Documentos necesarios:
"""
        
        if cedula == "PRIMERA_VEZ":
            descripcion += """
- Partida de nacimiento ORIGINAL
- Comprobante de pago (25.000 Gs)
- Acompañante si sos menor de edad
"""
        else:
            descripcion += """
- Cédula de identidad anterior
- Comprobante de pago (25.000 Gs)
"""
        
        descripcion += f"\n🤖 Turno generado automáticamente el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Crear estructura del evento
        evento = {
            'summary': f'Turno Cédula - {nombre}',
            'location': 'Oficina de Identificaciones, Av. Pioneros del Este, Ciudad del Este',
            'description': descripcion,
            'start': {
                'dateTime': fecha_hora.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': hora_fin.isoformat(),
                'timeZone': TIMEZONE,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                    {'method': 'popup', 'minutes': 60},        # 1 hora antes
                    {'method': 'popup', 'minutes': 15},        # 15 minutos antes
                ],
            },
            'colorId': '11',  # Rojo para destacar
        }
        
        # Agregar asistente si se proporciona email
        if email_usuario:
            evento['attendees'] = [
                {'email': email_usuario}
            ]
        
        # Crear el evento
        evento_creado = service.events().insert(
            calendarId='primary',
            body=evento,
            sendNotifications=True if email_usuario else False
        ).execute()
        
        evento_link = evento_creado.get('htmlLink')
        
        logger.info(f"Evento creado exitosamente: {evento_creado.get('id')}")
        logger.info(f"Link del evento: {evento_link}")
        
        return True, evento_link
        
    except HttpError as error:
        logger.error(f"Error HTTP creando evento: {error}")
        return False, f"Error de Google Calendar: {error}"
    except Exception as e:
        logger.error(f"Error inesperado creando evento: {e}")
        return False, f"Error inesperado: {str(e)}"

def consultar_disponibilidad(fecha: datetime.date) -> Dict[str, int]:
    """
    Consulta cuántos turnos hay agendados para una fecha específica
    
    Args:
        fecha: Fecha a consultar
    
    Returns:
        Dict con conteo de turnos por franja horaria
    """
    try:
        service = get_calendar_service()
        
        # Definir inicio y fin del día
        inicio_dia = datetime.datetime.combine(fecha, datetime.time(7, 0))
        fin_dia = datetime.datetime.combine(fecha, datetime.time(17, 0))
        
        # Consultar eventos del día
        events_result = service.events().list(
            calendarId='primary',
            timeMin=inicio_dia.isoformat() + 'Z',
            timeMax=fin_dia.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos = events_result.get('items', [])
        
        # Contar por franjas horarias
        franjas = {
            'temprano': 0,   # 7-9
            'manana': 0,     # 9-12
            'mediodia': 0,   # 12-14
            'tarde': 0       # 14-17
        }
        
        for evento in eventos:
            if 'Turno Cédula' in evento.get('summary', ''):
                start = evento['start'].get('dateTime', evento['start'].get('date'))
                hora = datetime.datetime.fromisoformat(start.replace('Z', '')).hour
                
                if 7 <= hora < 9:
                    franjas['temprano'] += 1
                elif 9 <= hora < 12:
                    franjas['manana'] += 1
                elif 12 <= hora < 14:
                    franjas['mediodia'] += 1
                elif 14 <= hora < 17:
                    franjas['tarde'] += 1
        
        logger.info(f"Disponibilidad para {fecha}: {franjas}")
        return franjas
        
    except Exception as e:
        logger.error(f"Error consultando disponibilidad: {e}")
        return {'temprano': 0, 'manana': 0, 'mediodia': 0, 'tarde': 0}

def cancelar_turno_por_codigo(codigo_turno: str) -> Tuple[bool, str]:
    """
    Busca y cancela un turno por su código
    
    Args:
        codigo_turno: Código único del turno
    
    Returns:
        Tuple (éxito: bool, mensaje: str)
    """
    try:
        service = get_calendar_service()
        
        # Buscar eventos con el código
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            q=codigo_turno,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos = events_result.get('items', [])
        
        if not eventos:
            return False, "No se encontró ningún turno con ese código"
        
        # Eliminar el primer evento encontrado
        service.events().delete(
            calendarId='primary',
            eventId=eventos[0]['id']
        ).execute()
        
        logger.info(f"Turno cancelado: {codigo_turno}")
        return True, "Turno cancelado exitosamente"
        
    except Exception as e:
        logger.error(f"Error cancelando turno: {e}")
        return False, f"Error al cancelar: {str(e)}"

def listar_proximos_turnos(limite: int = 10) -> list:
    """
    Lista los próximos turnos agendados
    
    Args:
        limite: Número máximo de turnos a mostrar
    
    Returns:
        Lista de diccionarios con información de turnos
    """
    try:
        service = get_calendar_service()
        
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=limite,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        eventos = events_result.get('items', [])
        
        turnos = []
        for evento in eventos:
            if 'Turno Cédula' in evento.get('summary', ''):
                start = evento['start'].get('dateTime', evento['start'].get('date'))
                turnos.append({
                    'titulo': evento['summary'],
                    'fecha_hora': start,
                    'descripcion': evento.get('description', '')
                })
        
        return turnos
        
    except Exception as e:
        logger.error(f"Error listando turnos: {e}")
        return []

# Función de prueba
# Función de prueba
if __name__ == '__main__':
    print("=== Test de Google Calendar Integration ===\n")
    
    try:
        # 1. Obtener servicio
        print("1. Conectando con Google Calendar...")
        service = get_calendar_service()
        print("✓ Conexión exitosa\n")
        
        # 2. Listar próximos eventos
        print("2. Listando próximos 5 eventos...")
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=5,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            print('   No hay eventos próximos.')
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                # Manejar eventos sin título
                titulo = event.get('summary', '(Sin título)')
                print(f'   - {start}: {titulo}')
        
        print("\n3. Creando turno de prueba...")
        fecha_prueba = datetime.datetime.now() + datetime.timedelta(days=2, hours=2)
        exito, mensaje = crear_evento_turno(
            nombre="Juan Pérez Prueba",
            cedula="1234567",
            fecha_hora=fecha_prueba,
            codigo_turno="TEST123"
        )
        
        if exito:
            print(f"✓ Turno creado exitosamente")
            print(f"  Link: {mensaje}")
        else:
            print(f"✗ Error: {mensaje}")
        
        print("\n4. Verificando el turno creado...")
        # Listar de nuevo para ver el turno recién creado
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
            q='TEST123'  # Buscar por código
        ).execute()
        eventos_test = events_result.get('items', [])
        
        if eventos_test:
            print(f"✓ Turno encontrado en el calendario:")
            for evt in eventos_test:
                print(f"   - {evt.get('summary', 'Sin título')}")
                print(f"   - Fecha: {evt['start'].get('dateTime', evt['start'].get('date'))}")
        else:
            print("⚠ No se encontró el turno en el calendario")
        
        print("\n=== Test completado exitosamente ===")
        
    except Exception as e:
        print(f"\n✗ Error en el test: {e}")
        import traceback
        traceback.print_exc()