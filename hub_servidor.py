# robot_server.py (Cargar en el Spike Prime Hub con Pybricks)

from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Direction, Color
from pybricks.tools import wait

# --- CONFIGURACIÓN DE PUERTOS ---
# Puertos: Motor Izquierdo (D), Motor Derecho (B)
hub = PrimeHub()
try:
    motor_izq = Motor(Port.D, Direction.COUNTERCLOCKWISE) 
    motor_der = Motor(Port.B, Direction.CLOCKWISE) 
except ValueError:
    hub.display.text("FAIL")
    print("ERROR: Motores no conectados.")

VELOCIDAD_MOVIMIENTO = 360  
VELOCIDAD_GIRO = 180       

def ejecutar_comando(comando: str):
    """Analiza y ejecuta el comando recibido por el Cliente."""
    hub.light.on(Color.BLUE) 
    
    try:
        accion, valor_str = comando.split(':')
        valor = float(valor_str)

        if accion == "FWD":
            motor_izq.run_angle(VELOCIDAD_MOVIMIENTO, valor, wait=False)
            motor_der.run_angle(VELOCIDAD_MOVIMIENTO, valor, wait=True)
            hub.light.on(Color.GREEN)
            
        elif accion == "TURN":
            motor_izq.run_angle(VELOCIDAD_GIRO, valor, wait=False)
            motor_der.run_angle(VELOCIDAD_GIRO, -valor, wait=True)
            hub.light.on(Color.CYAN)
            
        elif accion == "STOP":
            motor_izq.stop()
            motor_der.stop()
            hub.light.on(Color.WHITE)
            
        else:
            hub.light.on(Color.RED)
            
    except Exception as e:
        print(f"Error de comando: {e}")
        hub.light.on(Color.RED)

# Bucle principal para mantener el programa corriendo y el REPL activo.
hub.display.text("RUN") 
print("Servidor listo. Esperando comandos...")
while True:
    wait(100)