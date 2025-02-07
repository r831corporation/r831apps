import csv
from tkinter import Tk, filedialog

class ZPL_Config:
    """Configurações de impressão baseadas no artigo técnico"""
    DPI = 203  # Resolução padrão para impressoras Zebra
    LABEL_WIDTH_MM = 83  # Largura total da etiqueta em milímetros
    COLUMN_GAP_MM = 3    # Espaço entre colunas

    @property
    def print_width(self):
        """Calcula a largura de impressão em pontos usando a fórmula do artigo"""
        return int((self.LABEL_WIDTH_MM * self.DPI) / 25.4)

    @property
    def column_width(self):
        """Largura de cada coluna em pontos"""
        return int(((self.LABEL_WIDTH_MM - self.COLUMN_GAP_MM) / 2 * self.DPI) / 25.4)

    def get_x_positions(self):
        """Calcula as posições X das colunas baseado nas dimensões"""
        return {
            'left': 50,
            'right': self.column_width + int((self.COLUMN_GAP_MM * self.DPI) / 25.4)
        }

class ZPL_Generator:
    def __init__(self):
        self.config = ZPL_Config()
    
    def generate_label(self, left_data, right_data=None):
        """Gera uma etiqueta ZPL com duas colunas"""
        positions = self.config.get_x_positions()
        
        zpl = [
            "^XA",
            f"^PW{self.config.print_width}",
            f"^LL{self.config.column_width * 2}"  # Altura baseada no conteúdo
        ]

        # Coluna esquerda
        self._add_content(zpl, positions['left'], left_data)

        # Coluna direita (se existir)
        if right_data:
            self._add_content(zpl, positions['right'], right_data)

        zpl.append("^XZ")
        return '\n'.join(zpl)

    def _add_content(self, zpl, x_pos, data):
        """Adiciona conteúdo para uma coluna"""
        y_text = 50
        y_barcode = 100
        
        # Texto superior
        zpl.append(
            f"^FO{x_pos},{y_text}^A0N,30,30^FD"
            f"{data['sku']} - {data['localizacao']} - {data['nome'][:15]}^FS"
        )
        
        # Código de barras
        zpl.append(
            f"^FO{x_pos},{y_barcode}^BY2^BCN,80,Y,N,N^FD{data['gtin']}^FS"
        )

def process_csv(csv_path):
    """Processa o arquivo CSV e gera etiquetas ZPL"""
    generator = ZPL_Generator()
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    
    zpl_output = []
    for i in range(0, len(rows), 2):
        left = rows[i]
        right = rows[i+1] if (i+1 < len(rows)) else None
        zpl_output.append(generator.generate_label(left, right))
    
    return '\n\n'.join(zpl_output)

def main():
    """Fluxo principal de execução"""
    Tk().withdraw()  # Esconder janela principal
    
    # Selecionar arquivo CSV
    csv_path = filedialog.askopenfilename(
        title="Selecione o arquivo CSV",
        filetypes=[("CSV Files", "*.csv")]
    )
    
    if not csv_path:
        return
    
    # Gerar conteúdo ZPL
    zpl_content = process_csv(csv_path)
    
    # Salvar arquivo ZPL
    zpl_path = filedialog.asksaveasfilename(
        title="Salvar arquivo ZPL",
        defaultextension=".zpl",
        filetypes=[("ZPL Files", "*.zpl")]
    )
    
    if zpl_path:
        with open(zpl_path, 'w', encoding='utf-8') as file:
            file.write(zpl_content)
        print(f"Arquivo ZPL gerado com sucesso: {zpl_path}")

if __name__ == "__main__":
    main()