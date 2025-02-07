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

CONFIG_FILE = "config.ini"
rtsp_url = ""
running = False
cap = None
cam = None
log_lines = [] 
auto_debug = False


def load_config():
    global rtsp_url, auto_debug
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "RTSP" in config and "url" in config["RTSP"]:
            rtsp_url = config["RTSP"]["url"]
        if "DEBUG" in config and "auto_debug" in config["DEBUG"]:
            auto_debug = config["DEBUG"]["auto_debug"].lower() == "true"
    else:
        save_config()
        messagebox.showerror("Erro de Configuração", "Arquivo config.ini não encontrado ou inválido. Por favor, configure o IP do feed RTSP antes de continuar.")
        sys.exit()


def save_config():
    config = configparser.ConfigParser()
    config["RTSP"] = {"url": rtsp_url}
    config["DEBUG"] = {"auto_debug": str(auto_debug)}
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def log(message):
    global log_lines
    print(message)
    log_lines.append(message)


def start_feed():
    global running, cap, cam, rtsp_url
    try:
        if running:
            return

        if not rtsp_url:
            log("Erro: URL do feed RTSP não configurada.")
            messagebox.showerror("Erro", "URL do feed RTSP não configurada. Atualize as configurações.")
            return

        running = True
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            log(f"Erro: Não foi possível acessar o feed RTSP em {rtsp_url}.")
            running = False
            return

        # Configurar codec explicitamente para evitar erros de decodificação
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        frame_interval = 1 / fps

        log(f"Resolução: {frame_width}x{frame_height}, FPS: {fps}")

        cam = pyvirtualcam.Camera(width=frame_width, height=frame_height, fps=fps, fmt=pyvirtualcam.PixelFormat.BGR)
        log(f"Câmera virtual iniciada: {cam.device}")

        last_frame_time = time.time()

        while running:
            ret, frame = cap.read()
            if not ret:
                log("Erro: Não foi possível ler o frame do feed RTSP. Descarta frame corrompido.")
                continue

            # Verificar se o frame está corrompido ou inválido
            if frame is None or frame.size == 0:
                log("Aviso: Frame inválido ou corrompido descartado.")
                continue

            cam.send(frame)
            cam.sleep_until_next_frame()

            current_time = time.time()
            elapsed_time = current_time - last_frame_time
            delay = frame_interval - elapsed_time
            if delay > 0:
                time.sleep(delay)
            last_frame_time = time.time()

    finally:
        if cap:
            cap.release()
        if cam:
            cam.close()


def stop_feed():
    global running
    if running:
        running = False
        log("Feed RTSP encerrado. Para iniciar novamente, reabra a câmera pela bandeja do sistema.")


def open_config_window():
    global rtsp_url
    stop_feed()

    root = tk.Tk()
    root.withdraw()

    new_url = simpledialog.askstring("Configuração", "Insira o link do Feed RTSP atualizado:", initialvalue=rtsp_url)
    if new_url:
        rtsp_url = new_url
        save_config()
        messagebox.showinfo("Configuração", f"Link do Feed RTSP atualizado para: {rtsp_url}")
        threading.Thread(target=start_feed, daemon=True).start()

    root.destroy()


def show_feed_window():
    def feed_loop():
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            log(f"Erro: Não foi possível acessar o feed RTSP em {rtsp_url}.")
            return

        window_name = "Feed RTSP"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                log("Erro: Não foi possível ler o frame do feed RTSP.")
                break

            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyWindow(window_name)

    threading.Thread(target=feed_loop, daemon=True).start()


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
    image = Image.new("RGB", (64, 64), color=(0, 128, 255))

    menu = Menu(
        MenuItem("Iniciar Feed", lambda: threading.Thread(target=start_feed, daemon=True).start()),
        MenuItem("Parar Feed", lambda: threading.Thread(target=stop_feed, daemon=True).start()),
        MenuItem("Visualizar Feed", lambda: threading.Thread(target=show_feed_window, daemon=True).start()),
        MenuItem("Debug", lambda: threading.Thread(target=show_debug_window, daemon=True).start()),
        MenuItem("Configuração", lambda: threading.Thread(target=open_config_window, daemon=True).start()),
        MenuItem("Sair", lambda: quit_app(icon))
    )

    icon = Icon("RTSP VirtualCam", image, menu=menu)
    icon.run()


if __name__ == "__main__":
    try:
        load_config()

        threading.Thread(target=start_feed, daemon=True).start()

        if auto_debug:
            threading.Thread(target=show_debug_window, daemon=True).start()

        setup_tray()
    except Exception as e:
        log(f"Erro ao iniciar o aplicativo: {e}")