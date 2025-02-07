import tkinter as tk
from tkinter import filedialog

def gerar_zpl_personalizado():
    # Cria e oculta a janela principal do Tkinter
    root = tk.Tk()
    root.withdraw()

    # Seleciona o arquivo CSV
    csv_path = filedialog.askopenfilename(
        title="Selecione o arquivo CSV",
        filetypes=[("Arquivos CSV", "*.csv")]
    )
    if not csv_path:
        print("Arquivo CSV não selecionado!")
        return

    # Seleciona onde salvar o arquivo ZPL
    output_path = filedialog.asksaveasfilename(
        title="Salvar arquivo ZPL",
        defaultextension=".zpl",
        filetypes=[("Arquivos ZPL", "*.zpl"), ("Arquivos de Texto", "*.txt")]
    )
    if not output_path:
        print("Arquivo de saída não selecionado!")
        return

    # Lê o CSV linha por linha
    with open(csv_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    if not lines:
        print("O arquivo CSV está vazio!")
        return

    # Considera a primeira linha como cabeçalho
    header = lines[0].strip().split(',')
    header = [h.strip() for h in header]

    # Procura os índices dos campos esperados
    try:
        idx_nome = header.index("nome")
        idx_local = header.index("local")
        idx_sku = header.index("sku")
        idx_gtin = header.index("gtin")
    except ValueError:
        print("Erro: Certifique-se de que o CSV contenha os cabeçalhos: nome, local, sku, gtin")
        return

    zpl_output = ""
    waiting_record = None  # Armazena um registro enquanto aguarda seu par

    # Ajuste no espaçamento entre colunas (originalmente 400, agora +2 dots)
    col2_x = 409  # Posição da segunda coluna (adicionamos 2 dots para 0,6 mm)

    # Processa as linhas de dados
    for i, line in enumerate(lines[1:]):
        line = line.strip()
        if not line:
            continue  # pula linhas vazias

        # Divide a linha manualmente
        fields = line.split(',')
        if len(fields) < len(header):
            continue  # ignora linhas com campos incompletos
        fields = [f.strip() for f in fields]

        # Cria um registro (dicionário) com os campos esperados
        record = {
            "nome": fields[idx_nome][:15],  # Limita o nome a 15 caracteres
            "local": fields[idx_local],
            "sku": fields[idx_sku],
            "gtin": fields[idx_gtin]
        }

        # Se não houver um registro de espera, guarda este para a coluna esquerda
        if waiting_record is None:
            waiting_record = record
        else:
            # Já existe um registro aguardando: este é para a coluna direita
            left = waiting_record
            right = record
            waiting_record = None  # zera para o próximo par

            # Monta os dados de cada coluna
            left_data = f"{left['sku']} - {left['local']} | {left['nome']}"
            left_gtin = left['gtin']
            right_data = f"{right['sku']} - {right['local']} | {right['nome']}"
            right_gtin = right['gtin']

            # Monta os blocos ZPL, garantindo 39mm (~150 dots) para o GTIN
            label = "^XA\n"
            label += "^PW780\n"  # Largura total
            label += "^LL240\n"  # Altura total da etiqueta

            # Primeira etiqueta (coluna esquerda)
            label += "^FO10,10^A0N,25,25^FD" + left_data + "^FS\n"  # Nome acima
            label += "^FO10,40^BY2,2.0,50^BCN,50,Y,N,N^FD" + left_gtin + "^FS\n"  # GTIN abaixo

            # Segunda etiqueta (coluna direita) com espaçamento ajustado
            label += f"^FO{col2_x},10^A0N,25,25^FD" + right_data + "^FS\n"  # Nome acima
            label += f"^FO{col2_x},40^BY2,2.0,50^BCN,50,Y,N,N^FD" + right_gtin + "^FS\n"  # GTIN abaixo

            label += "^XZ\n"  # Finaliza a etiqueta dupla
            zpl_output += label

    # Se sobrar um registro (número ímpar de registros), cria uma etiqueta com a coluna direita vazia
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

    # Escreve o conteúdo ZPL no arquivo de saída
    with open(output_path, 'w', encoding='utf-8') as out_file:
        out_file.write(zpl_output)

    print(f"Arquivo ZPL gerado com sucesso: {output_path}")

if __name__ == "__main__":
    gerar_zpl_personalizado()
