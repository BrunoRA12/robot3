#!/usr/bin/env pybricks-micropython
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Direction, Stop
from pybricks.tools import wait
from pybricks.iodevices import XboxController
from pybricks.parameters import Color

# IMPORTANTE: Para usar BLE con Pybricks necesitas configurar el servidor
# Esta es una versión simplificada usando print() que funciona con 
# la conexión Bluetooth automática de Pybricks

# Inicializar el hub
hub = PrimeHub()
    
# Inicializar motores (ajusta los puertos según tu robot)
try:
    motor_izquierdo = Motor(Port.D, Direction.COUNTERCLOCKWISE)
    motor_derecho = Motor(Port.B, Direction.CLOCKWISE)
    motores_ok = True
    print("Motores inicializados en puertos D y B")
except:
    motores_ok = False
    print("ERROR: No se detectaron motores en D y B")

def procesar_comando(cmd):
    """Procesa comandos recibidos"""
    if not motores_ok:
        return "ERROR:NO_MOTORS"
    
    try:
        cmd = cmd.strip()
        
        if cmd == "STOP":
            motor_izquierdo.stop(Stop.BRAKE)
            motor_derecho.stop(Stop.BRAKE)
            hub.light.on('red')
            return "OK:STOP"
        
        elif cmd.startswith("FWD:"):
            vel = int(cmd.split(":")[1])
            motor_izquierdo.run(vel)
            motor_derecho.run(vel)
            hub.light.on('green')
            return "OK:FWD"
        
        elif cmd.startswith("BWD:"):
            vel = int(cmd.split(":")[1])
            motor_izquierdo.run(-vel)
            motor_derecho.run(-vel)
            hub.light.on('yellow')
            return "OK:BWD"
        
        elif cmd.startswith("LEFT:"):
            vel = int(cmd.split(":")[1])
            motor_izquierdo.run(-vel)
            motor_derecho.run(vel)
            hub.light.on('blue')
            return "OK:LEFT"
        
        elif cmd.startswith("RIGHT:"):
            vel = int(cmd.split(":")[1])
            motor_izquierdo.run(vel)
            motor_derecho.run(-vel)
            hub.light.on('cyan')
            return "OK:RIGHT"
        
        elif cmd == "STATUS":
            v = hub.battery.voltage()
            return "STATUS:BAT:" + str(v)
        
        elif cmd == "BEEP":
            hub.speaker.beep(1000, 100)
            return "OK:BEEP"
        
        else:
            return "ERROR:UNKNOWN:" + cmd
    except Exception as e:
        return "ERROR:" + str(e)

# Inicialización
hub.light.on(Color.WHITE)
print("===SPIKE_READY===")
hub.speaker.beep(500, 100)
wait(100)
hub.speaker.beep(700, 100)

# Loop principal
while True:
    try:
        # input() en Pybricks lee desde la conexión activa (USB o BT)
        comando = input()
        respuesta = procesar_comando(comando)
        print(respuesta)
    except:
        # Sin entrada, esperar
        wait(50)