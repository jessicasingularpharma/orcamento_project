from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def gerar_layout_pdf(output_path, logo_path):
    largura, altura = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # Adicionar logo no cabeçalho
    try:
        logo = ImageReader(logo_path)
        logo_width, logo_height = logo.getSize()
        
        # Calcular novo tamanho proporcional para a logo
        aspect_ratio = logo_height / logo_width
        new_width = largura - 80  # Definindo uma margem
        new_height = new_width * aspect_ratio

        # Centralizar a logo na parte superior
        c.drawImage(logo, (largura - new_width) / 2, altura - new_height - 40, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')
    except Exception as e:
        print(f"Erro ao carregar a logo: {e}")

    # Salvar o PDF
    c.showPage()
    c.save()

# Caminhos (substitua pelos reais)
output_pdf = "layout_pdf.pdf"
logo_path = "img\logo.png"  # Substitua pelo caminho correto da sua logo

gerar_layout_pdf(output_pdf, logo_path)
print(f"PDF gerado em: {output_pdf}")
