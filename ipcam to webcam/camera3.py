import cv2
import pyvirtualcam
from pystray import Icon, MenuItem, Menu
from PIL import Image
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import configparser
import sys
import os
import time
import re  # Para validação do IP

CONFIG_FILE = "config.ini"
rtsp_url = ""
running = False
cap = None
cam = None
log_lines = []
auto_debug = False
stream_method = "ffmpeg"
frame_skip = 5

def load_config():
    global rtsp_url, auto_debug, stream_method
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "RTSP" in config and "url" in config["RTSP"]:
            rtsp_url = config["RTSP"]["url"]
        if "DEBUG" in config and "auto_debug" in config["DEBUG"]:
            auto_debug = config["DEBUG"]["auto_debug"].lower() == "true"
        if "STREAM" in config and "method" in config["STREAM"]:
            stream_method = config["STREAM"]["method"]
    else:
        save_config()
        messagebox.showerror("Erro de Configuração", "Arquivo config.ini não encontrado ou inválido. Por favor, configure o IP do feed RTSP antes de continuar.")
        sys.exit()

def save_config():
    config = configparser.ConfigParser()
    config["RTSP"] = {"url": rtsp_url}
    config["DEBUG"] = {"auto_debug": str(auto_debug)}
    config["STREAM"] = {"method": stream_method}
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

def log(message):
    global log_lines
    print(message)
    log_lines.append(message)

def validate_rtsp_url(url):
    """Valida o formato do IP/URL para o RTSP"""
    if re.match(r"^rtsp://\d{1,3}(\.\d{1,3}){3}(:\d+)?/.*$", url):
        return True
    else:
        return False

def start_feed():
    global running, cap, cam, rtsp_url, stream_method
    try:
        if running:
            return

        if not rtsp_url:
            log("Erro: URL do feed RTSP não configurada.")
            messagebox.showerror("Erro", "URL do feed RTSP não configurada. Atualize as configurações.")
            return

        if not validate_rtsp_url(rtsp_url):
            log(f"Erro: URL do RTSP inválida. URL fornecida: {rtsp_url}")
            messagebox.showerror("Erro", f"URL do RTSP inválida. Certifique-se de que segue o formato correto: rtsp://<IP>:<PORTA>/<CAMINHO>")
            return

        running = True

        if stream_method == "ffmpeg":
            start_ffmpeg_feed()
        elif stream_method == "gstreamer":
            start_gstreamer_feed()
        else:
            log("Erro: Método de streaming desconhecido.")
            return

    finally:
        if cap:
            cap.release()
        if cam:
            cam.close()

def start_gstreamer_feed():
    global cap, cam, rtsp_url
    log(f"Iniciando feed com GStreamer usando a URL: {rtsp_url}...")
    
    # Pipeline GStreamer
    pipeline = f"rtspsrc location={rtsp_url} latency=0 ! decodebin ! videoconvert ! appsink"
    
    try:
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not cap.isOpened():
            log(f"Erro: Não foi possível acessar o feed RTSP com GStreamer.")
            error_code = cap.get(cv2.CAP_PROP_POS_FRAMES)  # Apenas exemplo; retorna informações sobre erro, se disponível
            log(f"Detalhes do erro do GStreamer: Código do erro retornado: {error_code}")
            return

        # Configurações de frame
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        frame_interval = 1 / fps

        log(f"Resolução: {frame_width}x{frame_height}, FPS: {fps}")

        cam = pyvirtualcam.Camera(width=frame_width, height=frame_height, fps=fps, fmt=pyvirtualcam.PixelFormat.BGR)
        log(f"Câmera virtual iniciada: {cam.device}")

        last_frame_time = time.time()
        frame_counter = 0  # Para pular frames

        while running:
            ret, frame = cap.read()
            if not ret:
                log("Erro: Não foi possível ler o frame do feed RTSP.")
                continue

            if frame is None or frame.size == 0:
                log("Aviso: Frame inválido ou corrompido descartado.")
                continue

            frame_counter += 1
            if frame_counter % frame_skip == 0:
                cam.send(frame)
                cam.sleep_until_next_frame()

            current_time = time.time()
            elapsed_time = current_time - last_frame_time
            delay = frame_interval - elapsed_time
            if delay > 0:
                time.sleep(delay)
            last_frame_time = time.time()
    except Exception as e:
        log(f"Erro inesperado ao tentar iniciar o feed com GStreamer: {str(e)}")

def stop_feed():
    global running
    if running:
        running = False
        log("Feed RTSP encerrado. Para iniciar novamente, reabra a câmera pela bandeja do sistema.")

def open_config_window():
    global rtsp_url, stream_method
    stop_feed()

    root = tk.Tk()
    root.withdraw()

    new_url = simpledialog.askstring("Configuração", "Insira o link do Feed RTSP atualizado:", initialvalue=rtsp_url)
    if new_url:
        rtsp_url = new_url
        save_config()
        messagebox.showinfo("Configuração", f"Link do Feed RTSP atualizado para: {rtsp_url}")

    method_choice = simpledialog.askstring("Método de Streaming", "Escolha o método de streaming (ffmpeg ou gstreamer):", initialvalue=stream_method)
    if method_choice and method_choice in ["ffmpeg", "gstreamer"]:
        stream_method = method_choice
        save_config()
        messagebox.showinfo("Configuração", f"Método de streaming atualizado para: {stream_method}")
    
    threading.Thread(target=start_feed, daemon=True).start()
    root.destroy()

def show_debug_window():
    def update_log():
        while True:
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "\n".join(log_lines[-100:]))
            text_widget.config(state=tk.DISABLED)
            root.update()

    root = tk.Tk()
    root.title("Debug")

    text_widget = scrolledtext.ScrolledText(root, state=tk.DISABLED, width=100, height=30)
    text_widget.pack()

    threading.Thread(target=update_log, daemon=True).start()
    root.mainloop()

def quit_app(icon):
    stop_feed()
    icon.stop()
    sys.exit()

def setup_tray():
    image = Image.new("RGB", (64, 64), color=(255, 255, 255))
    menu = Menu(
        MenuItem("Mostrar Logs", lambda: threading.Thread(target=show_debug_window, daemon=True).start()),
        MenuItem("Configurações", lambda: threading.Thread(target=open_config_window, daemon=True).start()),
        MenuItem("Sair", quit_app)
    )

    icon = Icon("RTSP Viewer", image, menu=menu)
    icon.run()

if __name__ == "__main__":
    load_config()
    setup_tray()