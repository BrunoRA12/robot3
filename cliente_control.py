"""
Control del Spike Prime via Bluetooth Low Energy (BLE)
Conecta directamente con el servidor BLE de Pybricks

Requisitos: pip install bleak
Autor: Estudiante de Informática
"""

import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from bleak import BleakScanner, BleakClient
import threading
import time

# UUIDs del servicio UART de Pybricks
PYBRICKS_SERVICE_UUID = "c5f50001-8280-46da-89f4-6d8051e4aeef"
PYBRICKS_COMMAND_UUID = "c5f50002-8280-46da-89f4-6d8051e4aeef"  # TX (PC escribe aquí)
PYBRICKS_HUB_UUID = "c5f50003-8280-46da-89f4-6d8051e4aeef"     # RX (PC lee de aquí)

class SpikeBluetoothController:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Control Spike Prime - Bluetooth BLE")
        self.root.geometry("1000x650")
        
        self.client = None
        self.device_address = None
        self.connected = False
        self.loop = None
        self.bt_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # ===== FRAME DE CONEXIÓN =====
        conn_frame = ttk.LabelFrame(self.root, text="📡 Conexión Bluetooth", padding=15)
        conn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(conn_frame, text="Dispositivo:", font=("", 10)).grid(row=0, column=0, sticky="w", padx=5)
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(conn_frame, textvariable=self.device_var, 
                                          width=45, state="readonly", font=("", 9))
        self.device_combo.grid(row=0, column=1, padx=5, pady=8)
        
        self.scan_btn = ttk.Button(conn_frame, text="🔍 Buscar", width=12,
                                    command=self.start_scan)
        self.scan_btn.grid(row=0, column=2, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="🔌 Conectar", width=15,
                                       command=self.toggle_connection)
        self.connect_btn.grid(row=1, column=1, pady=8)
        
        self.status_label = ttk.Label(conn_frame, text="⚫ Desconectado", 
                                       foreground="red", font=("", 11, "bold"))
        self.status_label.grid(row=1, column=2)
        
        # Indicador de búsqueda
        self.scan_progress = ttk.Progressbar(conn_frame, mode='indeterminate', length=200)
        self.scan_progress.grid(row=2, column=1, pady=5)
        self.scan_progress.grid_remove()
        
        # ===== FRAME DE CONTROL =====
        control_frame = ttk.LabelFrame(self.root, text="🎮 Control del Robot", padding=15)
        control_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Control de velocidad
        vel_frame = ttk.Frame(control_frame)
        vel_frame.pack(fill="x", pady=10)
        
        ttk.Label(vel_frame, text="⚡ Velocidad:", font=("", 10, "bold")).pack(side="left", padx=5)
        
        self.speed_var = tk.IntVar(value=400)
        speed_scale = ttk.Scale(vel_frame, from_=100, to=1000, 
                                variable=self.speed_var, orient="horizontal", length=350)
        speed_scale.pack(side="left", padx=10)
        
        self.speed_label = ttk.Label(vel_frame, text="400", 
                                      font=("", 14, "bold"), width=5)
        self.speed_label.pack(side="left", padx=5)
        
        self.speed_var.trace('w', lambda *args: 
                           self.speed_label.config(text=str(self.speed_var.get())))
        
        # Botones de dirección
        btn_container = ttk.Frame(control_frame)
        btn_container.pack(pady=20)
        
        # Crear botones con mejor diseño
        btn_config = {
            'width': 15,
            'padding': 10
        }
        
        # Fila 0: Adelante
        self.fwd_btn = ttk.Button(btn_container, text="⬆\nADELANTE", 
                                   command=lambda: self.send_cmd("FWD"), **btn_config)
        self.fwd_btn.grid(row=0, column=1, padx=8, pady=8)
        
        # Fila 1: Izquierda, Stop, Derecha
        self.left_btn = ttk.Button(btn_container, text="⬅\nIZQUIERDA",
                                    command=lambda: self.send_cmd("LEFT"), **btn_config)
        self.left_btn.grid(row=1, column=0, padx=8, pady=8)
        
        self.stop_btn = ttk.Button(btn_container, text="⬛\nDETENER",
                                    command=lambda: self.send_cmd("STOP"), **btn_config)
        self.stop_btn.grid(row=1, column=1, padx=8, pady=8)
        
        self.right_btn = ttk.Button(btn_container, text="➡\nDERECHA",
                                     command=lambda: self.send_cmd("RIGHT"), **btn_config)
        self.right_btn.grid(row=1, column=2, padx=8, pady=8)
        
        # Fila 2: Atrás
        self.back_btn = ttk.Button(btn_container, text="⬇\nATRÁS",
                                    command=lambda: self.send_cmd("BWD"), **btn_config)
        self.back_btn.grid(row=2, column=1, padx=8, pady=8)
        
        # Botones extra
        extra_frame = ttk.Frame(control_frame)
        extra_frame.pack(pady=10)
        
        ttk.Button(extra_frame, text="📊 Estado", width=12,
                   command=lambda: self.send_cmd("STATUS")).pack(side="left", padx=5)
        
        ttk.Button(extra_frame, text="🔊 Beep", width=12,
                   command=lambda: self.send_cmd("BEEP")).pack(side="left", padx=5)
        
        # Inicialmente deshabilitado
        self.toggle_controls(False)
        
        # ===== LOG =====
        log_frame = ttk.LabelFrame(self.root, text="📝 Registro de Comunicación", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, 
                                                   font=("Consolas", 9),
                                                   bg="#1e1e1e", fg="#00ff00")
        self.log_text.pack(fill="both", expand=True)
        
        self.log("💡 Presiona 'Buscar' para encontrar el Spike Prime")
        self.log("💡 Asegúrate que el hub esté ejecutando el programa Pybricks")
        
    def log(self, msg):
        """Añade mensaje al log con timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        
    def toggle_controls(self, enabled):
        """Habilita/deshabilita controles"""
        state = "normal" if enabled else "disabled"
        for btn in [self.fwd_btn, self.back_btn, self.left_btn, 
                    self.right_btn, self.stop_btn]:
            btn.config(state=state)
    
    def start_scan(self):
        """Inicia búsqueda de dispositivos BLE"""
        self.log("🔍 Buscando dispositivos Pybricks...")
        self.scan_btn.config(state="disabled")
        self.scan_progress.grid()
        self.scan_progress.start()
        
        def scan_task():
            try:
                devices = asyncio.run(self.scan_devices())
                self.root.after(0, lambda: self.handle_scan_results(devices))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Error: {e}"))
            finally:
                self.root.after(0, self.scan_complete)
        
        threading.Thread(target=scan_task, daemon=True).start()
    
    async def scan_devices(self):
        """Escanea dispositivos BLE y filtra Pybricks"""
        devices = await BleakScanner.discover(timeout=8.0)
        pybricks_devices = []
        
        for d in devices:
            # Buscar por nombre que contenga "Pybricks"
            if d.name and "Pybricks" in d.name:
                pybricks_devices.append({
                    'name': d.name,
                    'address': d.address,
                    'rssi': d.rssi if hasattr(d, 'rssi') else 'N/A'
                })
                self.log(f"✓ Encontrado: {d.name} ({d.address})")
        
        return pybricks_devices
    
    def handle_scan_results(self, devices):
        """Maneja resultados del escaneo"""
        if devices:
            device_list = [f"{d['name']} | {d['address']}" for d in devices]
            self.device_combo['values'] = device_list
            self.device_combo.current(0)
            self.log(f"✅ Encontrados {len(devices)} dispositivo(s) Pybricks")
        else:
            self.log("⚠ No se encontraron dispositivos Pybricks")
            messagebox.showwarning("Sin dispositivos", 
                                 "No se encontraron dispositivos Pybricks.\n\n"
                                 "Asegúrate de que:\n"
                                 "• El hub está encendido\n"
                                 "• Está ejecutando código Pybricks\n"
                                 "• Bluetooth está activado en tu PC")
    
    def scan_complete(self):
        """Finaliza la animación de búsqueda"""
        self.scan_progress.stop()
        self.scan_progress.grid_remove()
        self.scan_btn.config(state="normal")
    
    def toggle_connection(self):
        """Conectar/Desconectar"""
        if self.connected:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """Inicia conexión BLE"""
        device_str = self.device_var.get()
        if not device_str:
            messagebox.showwarning("Advertencia", "Selecciona un dispositivo primero")
            return
        
        # Extraer dirección
        self.device_address = device_str.split(" | ")[1]
        
        self.log(f"🔌 Conectando a {self.device_address}...")
        self.connect_btn.config(state="disabled")
        
        def connect_task():
            try:
                # Crear nuevo event loop para este thread
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(self.connect_ble())
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Error: {e}"))
                self.root.after(0, lambda: self.connect_btn.config(state="normal"))
        
        self.bt_thread = threading.Thread(target=connect_task, daemon=True)
        self.bt_thread.start()
    
    async def connect_ble(self):
        """Conexión BLE asíncrona"""
        try:
            self.client = BleakClient(self.device_address, timeout=15.0)
            await self.client.connect()
            
            # Verificar servicios
            services = self.client.services
            self.log(f"📡 Servicios disponibles: {len(services)}")
            
            # Suscribirse a notificaciones del hub
            await self.client.start_notify(PYBRICKS_HUB_UUID, self.notification_handler)
            
            self.connected = True
            self.root.after(0, self.update_connection_ui)
            self.log("✅ ¡Conectado! Listo para enviar comandos")
            
            # Mantener conexión
            while self.connected and self.client.is_connected:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.log(f"❌ Error de conexión: {e}")
            self.connected = False
            self.root.after(0, self.update_connection_ui)
    
    def notification_handler(self, sender, data):
        """Recibe datos del hub"""
        try:
            msg = data.decode('utf-8', errors='ignore').strip()
            if msg:
                self.root.after(0, lambda: self.log(f"⬅ Hub: {msg}"))
        except:
            pass
    
    def update_connection_ui(self):
        """Actualiza UI según estado de conexión"""
        if self.connected:
            self.status_label.config(text="🟢 Conectado", foreground="green")
            self.connect_btn.config(text="🔌 Desconectar", state="normal")
            self.toggle_controls(True)
            self.scan_btn.config(state="disabled")
        else:
            self.status_label.config(text="⚫ Desconectado", foreground="red")
            self.connect_btn.config(text="🔌 Conectar", state="normal")
            self.toggle_controls(False)
            self.scan_btn.config(state="normal")
    
    def disconnect(self):
        """Desconecta del hub"""
        self.log("🔌 Desconectando...")
        self.connected = False
        
        def disconnect_task():
            try:
                if self.client and self.client.is_connected:
                    # Detener motores antes de desconectar
                    asyncio.run_coroutine_threadsafe(
                        self.send_ble_command("STOP"), self.loop
                    ).result(timeout=1)
                    
                    asyncio.run_coroutine_threadsafe(
                        self.client.disconnect(), self.loop
                    ).result(timeout=2)
            except:
                pass
        
        threading.Thread(target=disconnect_task, daemon=True).start()
        self.root.after(500, self.update_connection_ui)
        self.log("✓ Desconectado")
    
    def send_cmd(self, command):
        """Envía comando al hub"""
        if not self.connected:
            messagebox.showwarning("Sin conexión", "Conecta al hub primero")
            return
        
        # Agregar velocidad si es necesario
        if command in ["FWD", "BWD", "LEFT", "RIGHT"]:
            full_cmd = f"{command}:{self.speed_var.get()}"
        else:
            full_cmd = command
        
        self.log(f"➡ Enviando: {full_cmd}")
        
        def send_task():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.send_ble_command(full_cmd), self.loop
                )
                future.result(timeout=2)
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Error: {e}"))
        
        threading.Thread(target=send_task, daemon=True).start()
    
    async def send_ble_command(self, cmd):
        """Envía comando por BLE"""
        try:
            data = (cmd + "\n").encode('utf-8')
            await self.client.write_gatt_char(PYBRICKS_COMMAND_UUID, data, response=False)
        except Exception as e:
            self.log(f"❌ Error enviando: {e}")
    
    def on_close(self):
        """Limpieza al cerrar"""
        if self.connected:
            self.disconnect()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = SpikeBluetoothController(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Centrar ventana
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    print("🤖 Iniciando Control Bluetooth para Spike Prime...")
    print("📦 Requisito: pip install bleak")
    main()