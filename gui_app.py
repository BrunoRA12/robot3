# gui_app.py (Se ejecuta en la PC)

import tkinter as tk
from tkinter import messagebox
import sys
# Importar la clase Cliente
from cliente_control import RobotClient

# --- CONFIGURACIÓN ---
# ¡CAMBIA ESTE VALOR AL PUERTO CORRECTO DE TU ROBOT!
PUERTO_HUB = "COM4" 

# Inicializar el cliente (instancia única de RobotClient)
try:
    client = RobotClient(port_name=PUERTO_HUB)
except Exception as e:
    # Esto ocurre si falta alguna dependencia crítica al iniciar
    messagebox.showerror("Error de Inicio", f"Fallo al inicializar RobotClient: {e}")
    sys.exit()

# --- Funciones de la GUI (Manejadores de Eventos) ---

def handle_connect_button():
    """Llama al método de conexión del Cliente y actualiza la GUI."""
    status_label.config(text=f"Conectando a {PUERTO_HUB}...", fg="orange")
    root.update()
    
    # Llamada al método sincrónico del Cliente
    success = client.connect() 
    
    if success:
        status_label.config(text=f"¡Conectado por USB a {PUERTO_HUB}!", fg="green")
    else:
        status_label.config(text="Desconectado", fg="red")
        messagebox.showerror("Conexión Fallida", "No se pudo conectar. Verifique el puerto y el robot.")

def handle_direction_command(direction: str):
    """Maneja los botones direccionales."""
    
    command_map = {
        "forward": "FWD:500", 
        "backward": "FWD:-500", 
        "right": "TURN:90",   
        "left": "TURN:-90",
        "stop": "STOP:",
    }
    
    comando = command_map.get(direction)
    if comando:
        # Llamada al método sincrónico del Cliente
        result = client.send_command(comando) 
        if "Error" in result:
             messagebox.showwarning("Comando Fallido", result)

def on_closing():
    """Llamado al cerrar la ventana. Limpia el cliente y detiene el hilo."""
    client.disconnect()
    root.destroy()

# --- Creación de la Interfaz Gráfica (Tkinter) ---

root = tk.Tk()
root.title("Control de Robot (Cliente-Servidor USB)")
root.protocol("WM_DELETE_WINDOW", on_closing) # Asegura la limpieza al cerrar

# 1. Sección de Conexión
connection_frame = tk.LabelFrame(root, text="Estado de Conexión", padx=10, pady=10)
connection_frame.pack(padx=20, pady=10, fill="x")

status_label = tk.Label(connection_frame, text="Desconectado", fg="red", font=("Arial", 12, "bold"))
status_label.pack(side="left")

connect_button = tk.Button(connection_frame, text="Conectar por USB", command=handle_connect_button)
connect_button.pack(side="right")

# 2. Sección de Control (Botones)
control_frame = tk.LabelFrame(root, text="Control Direccional", padx=10, pady=10)
control_frame.pack(padx=20, pady=10)

# Botones en formato D-Pad
tk.Button(control_frame, text="▲ Adelante", command=lambda: handle_direction_command("forward"), width=15).grid(row=0, column=1, padx=5, pady=5)
tk.Button(control_frame, text="◀ Izquierda", command=lambda: handle_direction_command("left"), width=10).grid(row=1, column=0, padx=5, pady=5)
tk.Button(control_frame, text="■ Detener", fg="red", command=lambda: handle_direction_command("stop"), width=10).grid(row=1, column=1, padx=5, pady=5)
tk.Button(control_frame, text="Derecha ▶", command=lambda: handle_direction_command("right"), width=10).grid(row=1, column=2, padx=5, pady=5)
tk.Button(control_frame, text="▼ Atrás", command=lambda: handle_direction_command("backward"), width=15).grid(row=2, column=1, padx=5, pady=5)

if __name__ == "__main__":
    root.mainloop()