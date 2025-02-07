import cv2
import pyvirtualcam

# URL do feed RTSP (inclua usuário e senha se necessário)
rtsp_url = "rtsp://dtp:admin@192.168.0.102:554/stream"

# Abre o feed RTSP
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("Erro: Não foi possível acessar o feed RTSP.")
    exit()

# Lê as especificações do vídeo
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30  # Define FPS padrão se não estiver disponível

print(f"Resolução: {frame_width}x{frame_height}, FPS: {fps}")

# Configura a câmera virtual
with pyvirtualcam.Camera(width=frame_width, height=frame_height, fps=fps, fmt=pyvirtualcam.PixelFormat.BGR) as cam:
    print(f"Câmera virtual iniciada: {cam.device}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erro: Não foi possível ler o frame do feed RTSP.")
            break

        # Mostra o feed em uma janela (opcional)
        cv2.imshow("Feed RTSP", frame)

        # Envia o frame para a câmera virtual
        cam.send(frame)
        cam.sleep_until_next_frame()

        # Sai do loop ao pressionar 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Libera os recursos
cap.release()
cv2.destroyAllWindows()
