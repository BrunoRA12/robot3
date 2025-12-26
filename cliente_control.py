import asyncio
import threading
import tempfile
import os
from queue import Queue, Empty
import tkinter as tk
from tkinter import ttk

# Requirements: pip install pybricksdev
from pybricksdev.ble import find_device
from pybricksdev.connections.pybricks import PybricksHubBLE

# -------------------- HUB GATEWAY CODE --------------------
HUB_GATEWAY_CODE = """
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port
from pybricks.tools import wait
import uselect
import usys

hub = PrimeHub()
motor_l = Motor(Port.D)
motor_r = Motor(Port.B)

poll = uselect.poll()
poll.register(usys.stdin, uselect.POLLIN)

hub.display.char('K') # 'K' for Keyboard Mode

while True:
    if poll.poll(10):
        cmd = usys.stdin.read(1)
        if cmd == 'F':
            motor_l.run(800)
            motor_r.run(-800)
        elif cmd == 'B':
            motor_l.run(-800)
            motor_r.run(800)
        elif cmd == 'L':
            motor_l.run(-500)
            motor_r.run(-500)
        elif cmd == 'R':
            motor_l.run(500)
            motor_r.run(500)
        elif cmd == 'S':
            motor_l.stop()
            motor_r.stop()
    wait(10)
"""

# -------------------- WORKER BLE --------------------

class BLEWorker:
    def __init__(self, log_queue: Queue):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.queue = None
        self.hub = None
        self.running = threading.Event()
        self.log_queue = log_queue

    def log(self, msg: str):
        self.log_queue.put(msg)

    def _thread_main(self):
        asyncio.set_event_loop(self.loop)
        self.queue = asyncio.Queue()
        self.loop.create_task(self._runner())
        self.loop.run_forever()

    async def _runner(self):
        temp_path = None
        try:
            self.log("Buscando Hub...")
            device = await find_device()
            if not device:
                self.log("Error: No se encontró Hub.")
                return

            self.hub = PybricksHubBLE(device)
            await self.hub.connect()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tf:
                tf.write(HUB_GATEWAY_CODE)
                temp_path = tf.name

            self.log("Conectado. Cargando teclado...")
            asyncio.create_task(self.hub.run(temp_path))
            self.running.set()

            while True:
                char_cmd = await self.queue.get()
                await self.hub.write(char_cmd.encode())

        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            if temp_path and os.path.exists(temp_path): os.unlink(temp_path)
            if self.hub: await self.hub.disconnect()
            self.running.clear()

    def start(self):
        if not self.thread.is_alive(): self.thread.start()

    def stop(self):
        if self.loop.is_running(): self.loop.call_soon_threadsafe(self.loop.stop)

    def send_command(self, cmd: str):
        mapping = {"fwd": "F", "bwd": "B", "left": "L", "right": "R", "stop": "S"}
        char = mapping.get(cmd)
        if char and self.loop.is_running() and self.queue is not None:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, char)


# -------------------- GUI --------------------

class LegoGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LEGO Keyboard Remote")
        self.root.geometry("400x550")
        
        self.log_queue = Queue()
        self.worker = BLEWorker(self.log_queue)
        
        # Track which keys are currently held down
        self.active_keys = set()

        self._build_ui()
        self._setup_keyboard()
        self._poll_logs()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill='x')
        ttk.Button(top, text="Conectar", command=self.on_connect).pack(side='left', padx=5)
        self.status_label = ttk.Label(top, text="Estado: OFF", foreground="red")
        self.status_label.pack(side='right')

        info = ttk.Label(self.root, text="Usa las FLECHAS del teclado para conducir", font=("Arial", 10, "italic"))
        info.pack(pady=5)

        ctrl_frame = ttk.Labelframe(self.root, text="Controles Visuales", padding=20)
        ctrl_frame.pack(pady=10)

        # Directional Buttons
        self.btns = {}
        def create_btn(text, cmd, row, col):
            btn = ttk.Button(ctrl_frame, text=text)
            btn.grid(row=row, column=col, padx=5, pady=5)
            btn.bind("<ButtonPress>", lambda e: self.worker.send_command(cmd))
            btn.bind("<ButtonRelease>", lambda e: self.worker.send_command("stop"))
            self.btns[cmd] = btn

        create_btn("▲", "fwd", 0, 1)
        create_btn("◄", "left", 1, 0)
        create_btn("■", "stop", 1, 1)
        create_btn("►", "right", 1, 2)
        create_btn("▼", "bwd", 2, 1)

        self.log_text = tk.Text(self.root, height=10, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)

    def _setup_keyboard(self):
        """Binds physical keyboard keys to the worker commands."""
        key_map = {
            "Up": "fwd",
            "Down": "bwd",
            "Left": "left",
            "Right": "right"
        }

        def on_key_press(event):
            if event.keysym in key_map and event.keysym not in self.active_keys:
                cmd = key_map[event.keysym]
                self.active_keys.add(event.keysym)
                self.worker.send_command(cmd)
                # Visual feedback on buttons
                if cmd in self.btns: self.btns[cmd].state(['pressed'])

        def on_key_release(event):
            if event.keysym in key_map:
                cmd = key_map[event.keysym]
                if event.keysym in self.active_keys:
                    self.active_keys.remove(event.keysym)
                
                # Only stop if no other directional keys are held
                if not self.active_keys:
                    self.worker.send_command("stop")
                
                if cmd in self.btns: self.btns[cmd].state(['!pressed'])

        self.root.bind("<KeyPress>", on_key_press)
        self.root.bind("<KeyRelease>", on_key_release)

    def on_connect(self):
        self.status_label.configure(text="Conectando...", foreground="orange")
        self.worker.start()
        self._check_status()

    def _check_status(self):
        if self.worker.running.is_set():
            self.status_label.configure(text="Conectado", foreground="green")
            self.root.focus_set() # Ensure keyboard focus
        else:
            self.root.after(500, self._check_status)

    def _poll_logs(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert('end', f"> {msg}\n")
                self.log_text.see('end')
                self.log_text.configure(state='disabled')
        except Empty: pass
        self.root.after(100, self._poll_logs)

if __name__ == '__main__':
    root = tk.Tk()
    app = LegoGUI(root)
    root.mainloop()