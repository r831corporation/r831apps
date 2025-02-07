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
from onvif import ONVIFCamera

CONFIG_FILE = "config.ini"
address = ""
port = ""
username = ""
password = ""
running = False
cap = None
cam = None
log_lines = []
auto_debug = False


def load_config():
    global address, port, username, password, auto_debug
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "ONVIF" in config:
            address = config["ONVIF"].get("address", "")
            port = config["ONVIF"].get("port", "80")
            username = config["ONVIF"].get("username", "")
            password = config["ONVIF"].get("password", "")
        if "DEBUG" in config and "auto_debug" in config["DEBUG"]:
            auto_debug = config["DEBUG"].get("auto_debug", "false").lower() == "true"
    else:
        save_config()
        messagebox.showerror("Erro de Configuração", "Arquivo config.ini não encontrado ou inválido. Configure as credenciais ONVIF antes de continuar.")
        sys.exit()


def save_config():
    config = configparser.ConfigParser()
    config["ONVIF"] = {
        "address": address,
        "port": port,
        "username": username,
        "password": password
    }
    config["DEBUG"] = {"auto_debug": str(auto_debug)}
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def log(message):
    global log_lines
    print(message)
    log_lines.append(message)


def get_rtsp_url():
    global address, port, username, password
    try:
        if not address or not username or not password:
            log("Erro: Credenciais ONVIF não configuradas corretamente.")
            return None

        camera = ONVIFCamera(address, int(port), username, password)
        media_service = camera.create_media_service()
        profiles = media_service.GetProfiles()

        # Selecionar o primeiro perfil
        profile_token = profiles[0].token
        stream_uri = media_service.GetStreamUri({
            'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': 'RTSP'},
            'ProfileToken': profile_token
        })
        return stream_uri.Uri
    except Exception as e:
        log(f"Erro ao obter URL RTSP: {e}")
        return None


def start_feed():
    global running, cap, cam
    try:
        if running:
            return

        rtsp_url = get_rtsp_url()
        if not rtsp_url:
            log("Erro: Não foi possível obter a URL RTSP da câmera ONVIF.")
            messagebox.showerror("Erro", "Não foi possível obter a URL RTSP da câmera ONVIF. Verifique as configurações.")
            return

        running = True
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            log(f"Erro: Não foi possível acessar o feed RTSP em {rtsp_url}.")
            running = False
            return

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

            if frame is None or frame.size == 0:
                log("Aviso: Frame inválido ou corrompido descartado.")
                continue

            current_time = time.time()
            elapsed_time = current_time - last_frame_time
            if elapsed_time > frame_interval:
                log("Aviso: Pulando frame para sincronizar com o feed ao vivo.")
                last_frame_time = current_time
                continue

            cam.send(frame)
            cam.sleep_until_next_frame()
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


def view_feed():
    global running, cap
    try:
        rtsp_url = get_rtsp_url()
        if not rtsp_url:
            log("Erro: Não foi possível obter a URL RTSP da câmera ONVIF.")
            messagebox.showerror("Erro", "Não foi possível obter a URL RTSP da câmera ONVIF. Verifique as configurações.")
            return

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if not cap.isOpened():
            log(f"Erro: Não foi possível acessar o feed RTSP em {rtsp_url}.")
            return

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                log("Erro: Não foi possível ler o frame do feed RTSP.")
                break

            cv2.imshow("Feed da Câmera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()


def open_config_window():
    global address, port, username, password
    stop_feed()

    root = tk.Tk()
    root.withdraw()

    new_address = simpledialog.askstring("Configuração", "Insira o endereço IP da câmera:", initialvalue=address)
    new_port = simpledialog.askstring("Configuração", "Insira a porta da câmera:", initialvalue=port)
    new_username = simpledialog.askstring("Configuração", "Insira o nome de usuário:", initialvalue=username)
    new_password = simpledialog.askstring("Configuração", "Insira a senha:", initialvalue=password, show='*')

    if new_address and new_username and new_password:
        address = new_address
        port = new_port or "80"
        username = new_username
        password = new_password
        save_config()
        messagebox.showinfo("Configuração", "Configurações ONVIF atualizadas com sucesso.")

    root.destroy()


def setup_tray():
    image = Image.new("RGB", (64, 64), color=(0, 128, 255))

    # Iniciar o feed automaticamente ao iniciar o aplicativo
    threading.Thread(target=start_feed, daemon=True).start()

    menu = Menu(
        MenuItem("Iniciar Feed", lambda: threading.Thread(target=start_feed, daemon=True).start()),
        MenuItem("Parar Feed", lambda: threading.Thread(target=stop_feed, daemon=True).start()),
        MenuItem("Visualizar Feed", lambda: threading.Thread(target=view_feed, daemon=True).start()),
        MenuItem("Configuração", lambda: threading.Thread(target=open_config_window, daemon=True).start()),
        MenuItem("Sair", lambda: quit_app(icon))
    )

    icon = Icon("ONVIF VirtualCam", image, menu=menu)
    icon.run()


def quit_app(icon):
    stop_feed()
    icon.stop()
    sys.exit()


if __name__ == "__main__":
    try:
        load_config()

        if auto_debug:
            log("Modo de depuração ativado automaticamente.")

        setup_tray()
    except Exception as e:
        log(f"Erro ao iniciar o aplicativo: {e}")
