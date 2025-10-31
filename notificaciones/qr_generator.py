# qr_generator.py
import qrcode
import secrets
import json
from io import BytesIO
import base64

class QRConfirmationGenerator:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
    
    def generate_confirmation_token(self):
        """Genera token único para confirmación"""
        return secrets.token_urlsafe(32)
    
    def generate_qr_confirmation(self, turno_data):
        """
        Genera QR con URL de confirmación
        """
        token = self.generate_confirmation_token()
        
        # URL que contiene token para confirmación
        confirmation_url = f"{self.base_url}/confirmar_turno/{token}"
        
        # Crear QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(confirmation_url)
        qr.make(fit=True)
        
        # Generar imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64 para email
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'token': token,
            'qr_base64': qr_base64,
            'confirmation_url': confirmation_url,
            'turno_data': turno_data
        }