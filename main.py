import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import threading
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE TU API / IA TOKEN ---
API_TOKEN = "AQ.Ab8RN6Kj_iBIl1VvmdSvxIdr5Bc__bZ1nevRMaooKnhBXZnGHg"

class RomFlasherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Android Custom ROM & Recovery ToolKit [PRO API]")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        # Configuración de directorios y herramientas SDK
        self.base_dir = os.getcwd()
        self.usroms_dir = os.path.join(self.base_dir, "{USROMS}")
        self.fastboot_path = os.path.join(self.base_dir, "platform-tools", "fastboot")
        self.adb_path = os.path.join(self.base_dir, "platform-tools", "adb")
        
        if not os.path.exists(self.usroms_dir):
            os.makedirs(self.usroms_dir)

        self.setup_ui()
        self.detect_device()

    def setup_ui(self):
        # --- FILA 1: COMANDOS DE FLASHEO Y DESBLOQUEO ---
        frame_top = tk.Frame(self.root, pady=5)
        frame_top.pack(fill=tk.X)

        tk.Button(frame_top, text="[FLASHEAR RECOVERY]", command=lambda: self.execute_fastboot("flash"), bg="#d32f2f", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="[BOOTEAR (Solo Probar)]", command=lambda: self.execute_fastboot("boot"), bg="#fbc02d", fg="black", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="[DESBLOQUEAR OEM]", command=lambda: self.execute_cmd("unlock_oem"), bg="#e53935", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        # --- FILA 2: CONTROLES DE ENERGÍA Y CONSOLA ---
        frame_mid = tk.Frame(self.root, pady=5)
        frame_mid.pack(fill=tk.X)

        tk.Button(frame_mid, text="[REINICIAR AL BOOTLOADER]", command=lambda: self.execute_cmd("reboot_bootloader"), bg="#5e35b1", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_mid, text="[REINICIAR SISTEMA]", command=lambda: self.execute_cmd("reboot_system"), bg="#0288d1", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_mid, text="[VER CONSOLA]", command=self.show_console, bg="#333", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_mid, text="[INFO DISPOSITIVO]", command=self.get_info, bg="#1976d2", fg="white").pack(side=tk.LEFT, padx=5)

        # --- FILA 3: ESTADO DEL DISPOSITIVO ---
        frame_device = tk.Frame(self.root, pady=10)
        frame_device.pack(fill=tk.X)
        self.lbl_device = tk.Label(frame_device, text="[DEVICE: BUSCANDO DISPOSITIVO...]", font=("Arial", 11, "bold"), fg="#388e3c")
        self.lbl_device.pack()

        # --- FILA 4: BUSCADOR IA DIRECTO (API INTEGRADA) ---
        frame_search = tk.LabelFrame(self.root, text="[DESCARGA DIRECTA POR IA - SIN NAVEGADOR]", pady=10, padx=10)
        frame_search.pack(fill=tk.BOTH, expand=False, padx=20, pady=5)

        tk.Label(frame_search, text="[TIPO]").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Label(frame_search, text="[SISTEMA / RECOVERY]").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        tk.Label(frame_search, text="[Escribe el CODENAME]").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Selectores
        self.cb_tipo = ttk.Combobox(frame_search, values=["RECOVERY", "OS"], state="readonly", width=15)
        self.cb_tipo.grid(row=1, column=0, padx=5, pady=5)
        self.cb_tipo.bind("<<ComboboxSelected>>", self.update_options)
        self.cb_tipo.set("RECOVERY")

        self.cb_sistema = ttk.Combobox(frame_search, state="readonly", width=20)
        self.cb_sistema.grid(row=1, column=1, padx=5, pady=5)
        
        self.entry_modelo = tk.Entry(frame_search, width=25)
        self.entry_modelo.insert(0, "Ej: vayu")
        self.entry_modelo.grid(row=1, column=2, padx=5, pady=5)

        # Botón de descarga autónoma
        tk.Button(frame_search, text="[DESCARGAR DIRECTO EN {USROMS}]", command=self.start_download_thread, bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).grid(row=2, column=0, columnspan=3, pady=15)

        self.update_options(None)

        # --- FILA 5: BARRA DE PROGRESO ---
        frame_progress = tk.Frame(self.root)
        frame_progress.pack(fill=tk.X, padx=20, pady=5)
        self.lbl_progreso = tk.Label(frame_progress, text="[PROGRESO: ESPERANDO...]")
        self.lbl_progreso.pack(anchor="w")
        self.progress = ttk.Progressbar(frame_progress, orient="horizontal", length=750, mode="determinate")
        self.progress.pack(pady=5)

        # --- CONSOLA ---
        self.txt_console = tk.Text(self.root, height=8, bg="black", fg="#00FF00", font=("Consolas", 9))
        self.txt_console.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

    def update_options(self, event):
        tipo = self.cb_tipo.get()
        if tipo == "RECOVERY":
            self.cb_sistema.config(values=["TWRP", "Orange FOX"])
            self.cb_sistema.set("TWRP")
        else:
            self.cb_sistema.config(values=["Lineage OS", "Pixel Experience", "CRdroid", "Graphene OS", "Kali NetHunter", "Oxygen OS"])
            self.cb_sistema.set("Lineage OS")

    # --- LÓGICA DE COMANDOS ADB Y FASTBOOT ---

    def run_command(self, cmd_list, silent=False):
        """Ejecuta comandos CMD. Si silent=True, no muestra salida en consola (útil para detectar background)."""
        def task():
            try:
                if not silent:
                    self.txt_console.insert(tk.END, f"\n[CMD] > {' '.join(cmd_list)}\n")
                process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                for line in process.stdout:
                    if not silent:
                        self.txt_console.insert(tk.END, line)
                        self.txt_console.see(tk.END)
                process.wait()
            except FileNotFoundError:
                if not silent:
                    self.txt_console.insert(tk.END, "\n[ERROR] Herramientas platform-tools no encontradas.\n")
        
        threading.Thread(target=task, daemon=True).start()

    def execute_cmd(self, action):
        """Envía comandos de energía y seguridad usando adb o fastboot inteligentemente."""
        if action == "reboot_bootloader":
            # Envía a ambos, el dispositivo responderá al que le corresponda según su estado
            self.run_command([self.adb_path, "reboot", "bootloader"])
            self.run_command([self.fastboot_path, "reboot-bootloader"])
        elif action == "reboot_system":
            self.run_command([self.adb_path, "reboot"])
            self.run_command([self.fastboot_path, "reboot"])
        elif action == "unlock_oem":
            # Ambos comandos (Antiguo y Nuevo estándar de Android)
            self.run_command([self.fastboot_path, "oem", "unlock"])
            self.run_command([self.fastboot_path, "flashing", "unlock"])

    def execute_fastboot(self, action):
        if action not in ["flash", "boot"]: return
        file_path = filedialog.askopenfilename(initialdir=self.usroms_dir, title=f"Seleccionar archivo", filetypes=(("Archivos", "*.img *.zip"), ("Todos", "*.*")))
        if file_path:
            if action == "flash":
                self.run_command([self.fastboot_path, "flash", "recovery", file_path])
            elif action == "boot":
                self.run_command([self.fastboot_path, "boot", file_path])

    def get_info(self):
        self.run_command([self.fastboot_path, "getvar", "all"])

    def show_console(self):
        if self.txt_console.winfo_ismapped():
            self.txt_console.pack_forget()
        else:
            self.txt_console.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

    def detect_device(self):
        """Intenta detectar el dispositivo en ADB o Fastboot."""
        try:
            fb_res = subprocess.run([self.fastboot_path, "devices"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if fb_res.stdout.strip():
                self.lbl_device.config(text=f"[DEVICE: {fb_res.stdout.split()[0]} {{FASTBOOT CONECTADO}}]")
                return
                
            adb_res = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if "device" in adb_res.stdout and len(adb_res.stdout.split('\n')) > 2:
                self.lbl_device.config(text=f"[DEVICE: ADB MODE CONECTADO]")
            else:
                self.lbl_device.config(text="[DEVICE: NINGUNO CONECTADO - ESPERANDO...]")
        except:
            pass # Ignorar fallos de detección silenciosa

    # --- RESOLUCIÓN INTELIGENTE (API) Y DESCARGA DIRECTA ---

    def get_direct_download_link(self, sistema, codename):
        """Usa las APIs reales y tu Token para extraer los links directos del servidor."""
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Flasher"
        }
        
        try:
            if sistema == "Lineage OS":
                # API Oficial LineageOS
                url = f"https://download.lineageos.org/api/v2/devices/{codename}/builds"
                res = requests.get(url, headers=headers).json()
                if res and isinstance(res, list):
                    link = res[0]['files'][0]['url']
                    name = res[0]['files'][0]['filename']
                    return link, name
            
            elif sistema == "Orange FOX":
                # API Oficial OrangeFox
                url = f"https://api.orangefox.download/v3/releases/?codename={codename}&limit=1"
                res = requests.get(url, headers=headers).json()
                if res.get('data') and len(res['data']) > 0:
                    release = res['data'][0]
                    link = release.get('url') or release.get('download')
                    name = release.get('file_name', f"OrangeFox_{codename}.zip")
                    return link, name
                    
            elif sistema == "TWRP":
                # Análisis de servidor Mirror Europeo
                url = f"https://eu.dl.twrp.me/{codename}/"
                html = requests.get(url, headers=headers).text
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup.find_all("a"):
                    href = tag.get("href")
                    if href and href.endswith(".img"):
                        link = f"https://eu.dl.twrp.me{href}"
                        return link, href.strip("/")
                        
            # Para otros sistemas como CRdroid se requeriría añadir su API de GitHub Releases aquí.
            
        except Exception as e:
            self.txt_console.insert(tk.END, f"\n[ERROR API] El servidor rechazó la conexión o el dispositivo no existe: {e}\n")
        
        return None, None

    def start_download_thread(self):
        sistema = self.cb_sistema.get()
        # Limpiar entrada para extraer solo el "codename" puro (Ej: "vayu", "sweet", "alioth")
        modelo_raw = self.entry_modelo.get().strip().lower()
        if "(" in modelo_raw:
            codename = modelo_raw.split("(")[-1].replace(")", "").strip()
        else:
            codename = modelo_raw
            
        if not sistema or not codename or "ej:" in codename:
            messagebox.showwarning("Atención", "Por favor, escribe un CODENAME válido (Ej: vayu, sweet, chiron).")
            return

        threading.Thread(target=self.search_and_download, args=(sistema, codename), daemon=True).start()

    def search_and_download(self, sistema, codename):
        self.txt_console.insert(tk.END, f"\n[IA BUSCADOR API] Resolviendo enlace oculto para: {sistema} (Codename: {codename})...\n")
        self.txt_console.see(tk.END)
        self.lbl_progreso.config(text="[PROGRESO: COMUNICÁNDOSE CON LOS SERVIDORES...]")
        
        url, filename = self.get_direct_download_link(sistema, codename)
        
        if url:
            self.txt_console.insert(tk.END, f"[IA API] ¡Archivo encontrado! Iniciando descarga en segundo plano...\n-> {url}\n")
            self.download_file(url, filename)
        else:
            self.txt_console.insert(tk.END, f"[IA API] Error: No se encontró build de {sistema} para '{codename}'.\n")
            self.lbl_progreso.config(text="[PROGRESO: ERROR - ROM O DISPOSITIVO NO ENCONTRADO]")

    def download_file(self, url, filename):
        filepath = os.path.join(self.usroms_dir, filename)
        try:
            # Importante: Añadimos stream=True y un Referer ficticio por si el servidor pide validación
            headers = {"Authorization": f"Bearer {API_TOKEN}", "Referer": "https://twrp.me/"}
            with requests.get(url, stream=True, headers=headers) as r:
                r.raise_for_status()
                total_length = int(r.headers.get('content-length', 0))
                
                with open(filepath, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if total_length > 0:
                                done = int(100 * dl / total_length)
                                self.progress["value"] = done
                                self.lbl_progreso.config(text=f"[PROGRESO: DESCARGANDO... {done}%]")
                                self.root.update_idletasks()
                                
            self.lbl_progreso.config(text=f"[PROGRESO: COMPLETADO - ARCHIVO LISTO EN {{USROMS}}]")
            self.txt_console.insert(tk.END, f"\n[ÉXITO] Archivo {filename} descargado exitosamente.\n")
        except Exception as e:
            self.lbl_progreso.config(text="[PROGRESO: ERROR EN DESCARGA]")
            self.txt_console.insert(tk.END, f"\n[ERROR DE DESCARGA]: {e}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = RomFlasherApp(root)
    root.mainloop()