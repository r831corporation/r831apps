import tkinter as tk
from tkinter import filedialog

def gerar_zpl_personalizado():
    root = tk.Tk()
    root.withdraw()

    csv_path = filedialog.askopenfilename(
        title="Selecione o arquivo CSV",
        filetypes=[("Arquivos CSV", "*.csv")]
    )
    if not csv_path:
        print("Arquivo CSV não selecionado!")
        return

    output_path = filedialog.asksaveasfilename(
        title="Salvar arquivo ZPL",
        defaultextension=".zpl",
        filetypes=[("Arquivos ZPL", "*.zpl"), ("Arquivos de Texto", "*.txt")]
    )
    if not output_path:
        print("Arquivo de saída não selecionado!")
        return

    with open(csv_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    if not lines:
        print("O arquivo CSV está vazio!")
        return

    header = lines[0].strip().split(',')
    header = [h.strip() for h in header]

    try:
        idx_nome = header.index("nome")
        idx_local = header.index("local")
        idx_sku = header.index("sku")
        idx_gtin = header.index("gtin")
    except ValueError:
        print("Erro: Certifique-se de que o CSV contenha os cabeçalhos: nome, local, sku, gtin")
        return

    zpl_output = ""
    waiting_record = None 

    col2_x = 415

    for i, line in enumerate(lines[1:]):
        line = line.strip()
        if not line:
            continue

        fields = line.split(',')
        if len(fields) < len(header):
            continue
        fields = [f.strip() for f in fields]

        record = {
            "nome": fields[idx_nome][:15],
            "local": fields[idx_local],
            "sku": fields[idx_sku],
            "gtin": fields[idx_gtin]
        }

        if waiting_record is None:
            waiting_record = record
        else:
            left = waiting_record
            right = record
            waiting_record = None

            left_data = f"{left['sku']} - {left['local']} | {left['nome']}"
            left_gtin = left['gtin']
            right_data = f"{right['sku']} - {right['local']} | {right['nome']}"
            right_gtin = right['gtin']

            label = "^XA\n"
            label += "^PW780\n" 
            label += "^LL240\n"

            label += "^FO10,10^A0N,25,25^FD" + left_data + "^FS\n" 
            label += "^FO10,40^BY2,2.0,50^BCN,50,Y,N,N^FD" + left_gtin + "^FS\n"

            label += f"^FO{col2_x},10^A0N,25,25^FD" + right_data + "^FS\n"
            label += f"^FO{col2_x},40^BY2,2.0,50^BCN,50,Y,N,N^FD" + right_gtin + "^FS\n"

            label += "^XZ\n" 
            zpl_output += label

    if waiting_record is not None:
        left = waiting_record
        left_data = f"{left['sku']} - {left['local']} | {left['nome']}"
        left_gtin = left['gtin']
        label = "^XA\n"
        label += "^PW780\n"
        label += "^LL240\n"
        label += "^FO10,10^A0N,25,25^FD" + left_data + "^FS\n"
        label += "^FO10,40^BY2,2.0,50^BCN,50,Y,N,N^FD" + left_gtin + "^FS\n"
        label += f"^FO{col2_x},10^A0N,25,25^FD^FS\n"
        label += f"^FO{col2_x},40^BY2,2.0,50^BCN,50,Y,N,N^FD^FS\n"
        label += "^XZ\n"

        zpl_output += label

    with open(output_path, 'w', encoding='utf-8') as out_file:
        out_file.write(zpl_output)

    print(f"Arquivo ZPL gerado com sucesso: {output_path}")

if __name__ == "__main__":
    gerar_zpl_personalizado()
