from PyPDF2 import PdfMerger
import os

def unir_pdfs(arquivos, caminho_saida):
    merger = PdfMerger()
    for arquivo in arquivos:
        if arquivo and os.path.exists(arquivo):
            merger.append(arquivo)
    merger.write(caminho_saida)
    merger.close()
