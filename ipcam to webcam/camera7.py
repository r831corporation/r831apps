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
max_retries = 3
retry_interval = 5
FPS = 12


def load_config():
    global rtsp_url, auto_debug, max_retries, retry_interval
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "RTSP" in config and "url" in config["RTSP"]:
            rtsp_url = config["RTSP"]["url"]
        if "DEBUG" in config and "auto_debug" in config["DEBUG"]:
            auto_debug = config["DEBUG"]["auto_debug"].lower() == "true"
        if "RETRY" in config:
            max_retries = int(config["RETRY"].get("max_retries", max_retries))
            retry_interval = int(config["RETRY"].get("retry_interval", retry_interval))
    else:
        save_config()
        messagebox.showerror("Erro de Configuração", "Arquivo config.ini não encontrado ou inválido. Por favor, configure o IP do feed RTSP antes de continuar.")
        sys.exit()


def save_config():
    config = configparser.ConfigParser()
    config["RTSP"] = {"url": rtsp_url}
    config["DEBUG"] = {"auto_debug": str(auto_debug)}
    config["RETRY"] = {
        "max_retries": str(max_retries),
        "retry_interval": str(retry_interval),
    }
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

        retries = 0
        while retries < max_retries:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

            if cap.isOpened():
                break

            log(f"Tentativa {retries + 1}/{max_retries}: Não foi possível acessar o feed RTSP. Retentando em {retry_interval} segundos...")
            retries += 1
            time.sleep(retry_interval)

        if not cap.isOpened():
            log(f"Erro: Não foi possível acessar o feed RTSP após {max_retries} tentativas.")
            running = False
            return

        # Configurar FPS fixo e resolução
        cap.set(cv2.CAP_PROP_FPS, FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        log(f"Resolução: {frame_width}x{frame_height}, FPS: {FPS}")

        cam = pyvirtualcam.Camera(width=frame_width, height=frame_height, fps=FPS, fmt=pyvirtualcam.PixelFormat.BGR, print_fps=False)
        log(f"Câmera virtual iniciada: {cam.device}")

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
    global rtsp_url, max_retries, retry_interval
    stop_feed()

    root = tk.Tk()
    root.withdraw()

    new_url = simpledialog.askstring("Configuração", "Insira o link do Feed RTSP atualizado:", initialvalue=rtsp_url)
    if new_url:
        rtsp_url = new_url

    new_max_retries = simpledialog.askinteger("Configuração", "Número máximo de tentativas:", initialvalue=max_retries)
    if new_max_retries is not None:
        max_retries = new_max_retries

    new_retry_interval = simpledialog.askinteger("Configuração", "Intervalo entre tentativas (segundos):", initialvalue=retry_interval)
    if new_retry_interval is not None:
        retry_interval = new_retry_interval

    save_config()
    messagebox.showinfo("Configuração", f"Configurações atualizadas: URL={rtsp_url}, Tentativas={max_retries}, Intervalo={retry_interval}s")
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
        setup_tray()
    except Exception as e:
        log(f"Erro fatal: {e}")
