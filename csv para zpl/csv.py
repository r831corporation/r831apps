import os
import csv
from tkinter import Tk, filedialog
import barcode
from barcode.writer import ImageWriter
import sys
from PIL import Image, ImageDraw

def gerar_codigo_barras(numero):
    # Gera o código de barras EAN-13 sem texto abaixo, utilizando diferentes estratégias para removê-lo.
    ean = barcode.get_barcode_class('ean13')
    codigo_barras = ean(numero, writer=ImageWriter())

    # Tentativas de remover ou não renderizar texto abaixo do código de barras.
    codigo_barras_writer_options = {
        'text': '',  # Estratégia simples para não renderizar texto, mas tentaremos mais opções.
        'text_distance': 0,  # Tenta forçar a distância para o texto ser removido (não ajuda sozinha).
        'font_size': 0,  # Define o tamanho da fonte como zero para tentar "ocultar" o texto.
        'text': False,  # Tenta uma abordagem de desabilitação do texto completamente.
    }

    # Outra abordagem mais complexa, criando uma imagem em branco e desenhando o código manualmente.
    imagem = codigo_barras.render(writer_options=codigo_barras_writer_options)

    # Aqui tentamos manipular a imagem gerada diretamente com PIL para apagar ou mover o texto.
    # Inicializa a imagem e o contexto de desenho.
    img = Image.open(imagem)
    draw = ImageDraw.Draw(img)

    # Obtém as dimensões da imagem e apaga a área onde o texto estava.
    largura, altura = img.size
    margem_texto = 40  # Distância do topo da imagem onde o texto geralmente aparece
    draw.rectangle([0, altura - margem_texto, largura, altura], fill=(255, 255, 255))  # Apaga a área do texto.

    # Salva a imagem com a área de texto apagada.
    img_path = f"codigo_barras_{numero}.png"
    img.save(img_path)

    return img_path

def gerar_zpl(sku, localizacao, nome, gtin, x_offset, y_offset):
    # Formatação ajustada para a ZPL, com GTIN na segunda linha e texto bem organizado.
    zpl = f"""
    ^XA
    ^CF0,20
    ^FO50,{y_offset}^BY2^BCN,60,Y,N,N^FD{gtin}^FS
    ^FO50,{y_offset + 70}^BY2^BCN,60,Y,N,N^FD{gtin}^FS
    ^XZ
    """
    return zpl

def selecionar_arquivo_csv():
    root = Tk()
    root.withdraw()  # Oculta a janela principal
    caminho_arquivo = filedialog.askopenfilename(
        title="Selecione o arquivo CSV",
        filetypes=[("CSV Files", "*.csv")]
    )
    return caminho_arquivo

def salvar_arquivo_zpl():
    root = Tk()
    root.withdraw()  # Oculta a janela principal
    caminho_arquivo = filedialog.asksaveasfilename(
        title="Salvar arquivo ZPL",
        defaultextension=".zpl",
        filetypes=[("ZPL Files", "*.zpl")]
    )
    return caminho_arquivo

def fechar_aplicacao():
    sys.exit()

def gerar_etiquetas(arquivo_csv, arquivo_zpl):
    etiquetas = []

    with open(arquivo_csv, 'r', encoding='utf-8') as csvfile:
        linhas = csvfile.readlines()

        for i, linha in enumerate(linhas[1:]):  # Ignora o cabeçalho
            campos = linha.strip().split(",")  # Divide a linha com base nas vírgulas
            if len(campos) >= 4:  # Verifica se há pelo menos 4 campos
                sku = campos[0]
                localizacao = campos[1]
                gtin = campos[2]  # O GTIN
                nome = campos[3]  # Nome é o quarto campo

                y_offset = 50 + (i * 140)  # Definindo o deslocamento y para cada etiqueta na coluna
                etiquetas.append(gerar_zpl(sku, localizacao, nome, gtin, 50, y_offset))

    # Agora escreve todas as etiquetas em um único arquivo ZPL
    with open(arquivo_zpl, 'w', encoding='utf-8') as zplfile:
        for etiqueta in etiquetas:
            zplfile.write(etiqueta + "\n")

    print(f"Arquivo ZPL gerado com sucesso: {arquivo_zpl}")

# Seleção de arquivos e execução do processo
arquivo_csv = selecionar_arquivo_csv()
if not arquivo_csv:
    print("Nenhum arquivo CSV selecionado.")
else:
    arquivo_zpl = salvar_arquivo_zpl()
    if not arquivo_zpl:
        print("Nenhum arquivo ZPL selecionado.")
    else:
        gerar_etiquetas(arquivo_csv, arquivo_zpl)
        fechar_aplicacao()  # Encerra a aplicação após a conversão
