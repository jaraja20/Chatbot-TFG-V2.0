# confirmation_server.py (Flask simple)
from flask import Flask, request, render_template
import psycopg2

app = Flask(__name__)

@app.route('/confirmar_turno/<token>')
def confirmar_turno(token):
    action = request.args.get('action', 'confirm')
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="chatbotdb",
            user="postgres",
            password="tu_password"
        )
        cur = conn.cursor()
        
        # Buscar turno por token
        cur.execute("""
            SELECT id, nombre, fecha, hora, numero_turno, confirmado
            FROM turnos WHERE token_confirmacion = %s
        """, (token,))
        
        turno = cur.fetchone()
        
        if not turno:
            return render_template('error.html', message="Token inválido")
        
        if action == 'cancel':
            # Cancelar turno
            cur.execute("""
                UPDATE turnos SET confirmado = FALSE, 
                fecha_confirmacion = CURRENT_TIMESTAMP
                WHERE token_confirmacion = %s
            """, (token,))
            message = "❌ Turno cancelado exitosamente"
        else:
            # Confirmar turno
            cur.execute("""
                UPDATE turnos SET confirmado = TRUE, 
                fecha_confirmacion = CURRENT_TIMESTAMP
                WHERE token_confirmacion = %s
            """, (token,))
            message = "✅ Turno confirmado exitosamente"
        
        conn.commit()
        cur.close()
        conn.close()
        
        return render_template('confirmation.html', 
                             message=message, 
                             turno=turno)
        
    except Exception as e:
        return render_template('error.html', message=f"Error: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, port=5000)