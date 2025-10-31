# email_sender.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import base64

class EmailNotificationSender:
    def __init__(self, smtp_server, smtp_port, email, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
    
    def send_confirmation_email(self, recipient_email, turno_data, qr_data):
        """
        Envía email de confirmación con QR
        """
        msg = MIMEMultipart('related')
        msg['From'] = self.email
        msg['To'] = recipient_email
        msg['Subject'] = f"Confirma tu turno - {turno_data['fecha']} {turno_data['hora']}"
        
        # Cuerpo del email HTML
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">🏛️ Confirmación de Turno - Oficina de Identificaciones</h2>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3>📅 Detalles de tu turno:</h3>
                    <p><strong>Nombre:</strong> {turno_data['nombre']}</p>
                    <p><strong>Cédula:</strong> {turno_data['cedula']}</p>
                    <p><strong>Fecha:</strong> {turno_data['fecha']}</p>
                    <p><strong>Hora:</strong> {turno_data['hora']}</p>
                    <p><strong>Número de Turno:</strong> {turno_data['numero_turno']}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <h3>📱 Escanea el código QR para confirmar:</h3>
                    <img src="cid:qr_code" alt="Código QR de Confirmación" style="max-width: 200px;">
                </div>
                
                <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px;">
                    <p><strong>⚠️ Importante:</strong></p>
                    <ul>
                        <li>Confirma tu asistencia escaneando el QR o haciendo clic en el enlace</li>
                        <li>Si no puedes asistir, cancela tu turno para que otros puedan usarlo</li>
                        <li>Llega 15 minutos antes de tu hora asignada</li>
                        <li>Trae todos los documentos requeridos</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{qr_data['confirmation_url']}" 
                       style="background-color: #27ae60; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        ✅ CONFIRMAR TURNO
                    </a>
                    <br><br>
                    <a href="{qr_data['confirmation_url']}?action=cancel" 
                       style="background-color: #e74c3c; color: white; padding: 10px 20px; 
                              text-decoration: none; border-radius: 5px;">
                        ❌ Cancelar Turno
                    </a>
                </div>
                
                <p style="color: #7f8c8d; font-size: 12px;">
                    Este mensaje fue enviado automáticamente. No respondas a este email.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Adjuntar HTML
        msg.attach(MIMEText(html_body, 'html'))
        
        # Adjuntar imagen QR
        qr_image_data = base64.b64decode(qr_data['qr_base64'])
        qr_image = MIMEImage(qr_image_data)
        qr_image.add_header('Content-ID', '<qr_code>')
        msg.attach(qr_image)
        
        # Enviar email
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Error enviando email: {e}")
            return False