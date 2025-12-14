# cliente_control.py (Versión Bluetooth BLE)

import asyncio
import threading
from pybricksdev.connections import PybricksHub # Usando la importación de compatibilidad
from pybricksdev.ble import find_device       # <-- ¡Nueva importación para buscar BLE!

class RobotClient:
    """
    Gestiona la conexión con el Hub del robot y el envío de comandos
    utilizando un hilo separado para asyncio.
    """
    # Usaremos el nombre de Hub por defecto de Pybricks
    DEVICE_NAME = "Pybricks Hub" 
    
    def __init__(self):
        # Eliminamos la variable PORT_NAME
        self.hub = None
        self.connected = False
        self.loop = None
        
        # Iniciar el hilo de asyncio al crear el cliente
        self._start_asyncio_loop_thread()

    # --- MÉTODOS INTERNOS (Threading/Asyncio - SIN CAMBIOS) ---

    def _start_asyncio_loop_thread(self):
        """Inicia el bucle de asyncio en un hilo separado (daemon)."""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        """Función ejecutada por el hilo para iniciar el bucle de asyncio."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        print("Asyncio loop iniciado en hilo separado.")
        self.loop.run_forever()

    # --- MÉTODOS ASÍNCRONOS (ejecutados en el hilo de asyncio) ---

    async def _connect_async(self):
        """Lógica de conexión asíncrona (Bluetooth BLE)."""
        try:
            print(f"Buscando dispositivo: {self.DEVICE_NAME}...")
            
            # 1. Encontrar el dispositivo por BLE
            dispositivo_ble = await find_device(self.DEVICE_NAME) # <-- ¡Cambio clave!
            
            # 2. Conectar al Hub usando el dispositivo BLE encontrado
            print("Dispositivo encontrado. Conectando...")
            self.hub = PybricksHub(dispositivo_ble)
            await self.hub.connect()
            
            self.connected = True
            print("Conexión BLE exitosa.")
            return True
            
        except Exception as e:
            self.connected = False
            self.hub = None
            print(f"Error de conexión BLE: {e}")
            return False

    async def _send_command_async(self, command: str):
        # (Esta función se mantiene igual a la versión USB/Serial)
        if not self.connected:
            return "Error: Desconectado"

        try:
            command_executable = f"ejecutar_comando('{command}')\n"
            await self.hub.write_output(command_executable.encode('utf-8'))
            return "Comando enviado"
            
        except Exception as e:
            self.connected = False
            self.hub = None
            return f"Error de envío: {e}"

    # --- MÉTODOS SINCRÓNICOS (llamados por la GUI - SE MANTIENEN IGUAL) ---

    def connect(self):
        """Llama al método de conexión asíncrono de forma segura."""
        if self.connected:
            return True
        future = asyncio.run_coroutine_threadsafe(self._connect_async(), self.loop)
        return future.result() # Espera sincrónicamente el resultado

    def send_command(self, command: str):
        # ... (Se mantiene igual)
        if not self.connected:
            return "Error: Robot no conectado."
        future = asyncio.run_coroutine_threadsafe(self._send_command_async(command), self.loop)
        return future.result()

    def disconnect(self):
        # ... (Se mantiene igual)
        if self.hub and self.connected:
            self.loop.call_soon_threadsafe(self.hub.disconnect)
            self.connected = False
        self.loop.call_soon_threadsafe(self.loop.stop)