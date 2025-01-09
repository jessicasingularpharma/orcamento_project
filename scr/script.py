import pandas as pd
import fdb
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv
import os
from pdfrw import PdfReader, PageMerge, PdfWriter

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def gerar_pdf(numero_orcamento):
    try:
        # Conectar ao banco de dados Firebird usando variáveis de ambiente
        conn = fdb.connect(
            dsn=f'{os.getenv("FIREBIRD_HOST")}:{os.getenv("FIREBIRD_DATABASE")}',
            user=os.getenv("FIREBIRD_USER"),
            password=os.getenv("FIREBIRD_PASSWORD")
        )
        cursor = conn.cursor()

        # Recuperar dados do orçamento
        query_orcamento = f"""
            SELECT o.NRORC, o.DTENTR, o.CDCLI, o.NOMEPA, 
                   f.NRCRM, o.VRRQU, o.ENDEPA, o.CDCON
            FROM FC15000 o
            JOIN FC15100 f ON o.NRORC = f.NRORC
            WHERE o.NRORC = {numero_orcamento}
        """
        df_orcamento = pd.read_sql(query_orcamento, conn)

        # Recuperar itens do orçamento
        query_itens = f"SELECT * FROM FC15110 WHERE NRORC = {numero_orcamento}"
        df_itens = pd.read_sql(query_itens, conn)

        # Fechar a conexão
        cursor.close()
        conn.close()

        # Calcular o valor total do orçamento
        valor_total_orcamento = df_orcamento['VRRQU'].sum()

        # Ler o modelo de orçamento PDF
        modelo_orcamento = PdfReader('modelo_orcamento.pdf')
        first_page = modelo_orcamento.pages[0]

        # Criar PDF usando o modelo de fundo
        overlay = canvas.Canvas('overlay.pdf', pagesize=letter)
        width, height = letter

        # Adicionar Cabeçalho e Informações
        overlay.setFont("Helvetica-Bold", 10)
        overlay.drawString(50, height - 40, "EMPRESA LTDA.")
        overlay.setFont("Helvetica", 10)
        overlay.drawString(50, height - 60, "RUA DAS CASAS, 666, ITAPEVI, SP")
        overlay.drawString(50, height - 75, "CNPJ: 99.999.999/9999-62")

        overlay.setFont("Helvetica-Bold", 12)
        overlay.drawString(400, height - 40, f"Data: {pd.Timestamp.now().strftime('%d/%m/%Y')}")
        overlay.drawString(400, height - 60, f"Hora: {pd.Timestamp.now().strftime('%H:%M:%S')}")
        overlay.drawString(400, height - 75, f"Número do Orçamento: {numero_orcamento}")

        overlay.setLineWidth(1)
        overlay.line(50, height - 85, width - 50, height - 85)

        overlay.setFont("Helvetica-Bold", 10)
        overlay.drawString(50, height - 100, "Informações do Cliente")
        overlay.setFont("Helvetica", 10)
        for _, row in df_orcamento.iterrows():
            overlay.drawString(50, height - 115, f"Nome do Paciente: {str(row['NOMEPA'])}")
            overlay.drawString(50, height - 130, f"Endereço: {str(row['ENDEPA'])}")
            overlay.drawString(50, height - 145, f"CRM do Médico: {str(row['NRCRM'])}")
            overlay.drawString(50, height - 160, f"Data de Entrada: {str(row['DTENTR'])}")

        overlay.setLineWidth(1)
        overlay.line(50, height - 175, width - 50, height - 175)

        overlay.setFont("Helvetica-Bold", 10)
        overlay.drawString(50, height - 190, "Itens do Orçamento")
        y = height - 205
        overlay.setFont("Helvetica", 10)
        overlay.drawString(50, y, "Produto")
        overlay.drawString(200, y, "Descrição")
        overlay.drawString(350, y, "Quantidade")
        overlay.drawString(450, y, "Preço Unitário")
        overlay.drawString(550, y, "Total")
        y -= 15

        for _, row in df_itens.iterrows():
            overlay.drawString(50, y, str(row['CDPRO']))
            overlay.drawString(200, y, str(row['DESCR']))
            overlay.drawString(350, y, str(row['QUANT']))
            overlay.drawString(450, y, f"{row['VRCMP']:.2f}")
            overlay.drawString(550, y, f"{row['VRCMP'] * row['QUANT']:.2f}")
            y -= 15
            if y < 40:
                overlay.showPage()
                y = height - 40
                overlay.setFont("Helvetica", 10)

        overlay.setLineWidth(1)
        overlay.line(50, y - 5, width - 50, y - 5)

        overlay.setFont("Helvetica-Bold", 10)
        overlay.drawString(50, y - 20, f'Valor Total do Orçamento: R$ {valor_total_orcamento:.2f}')

        overlay.setFont("Helvetica", 8)
        overlay.drawString(50, 30, "Obrigado por escolher nossa empresa.")
        overlay.drawString(50, 20, "Entre em contato para mais informações.")

        # Salvar a sobreposição
        overlay.save()
        
        # Mesclar a sobreposição com o modelo
        overlay_reader = PdfReader('overlay.pdf')
        overlay_page = overlay_reader.pages[0]

        merger = PageMerge(first_page)
        merger.add(overlay_page).render()

        output = PdfWriter()
        output.addpage(first_page)
        output.write(f'relatorio_{numero_orcamento}.pdf')

        messagebox.showinfo("Sucesso", f"Relatório PDF gerado: relatorio_{numero_orcamento}.pdf")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao gerar PDF: {e}")

def criar_interface():
    root = tk.Tk()
    root.title("Gerar PDF de Orçamento")

    tk.Label(root, text="Número do Orçamento:").grid(row=0, column=0)
    numero_orcamento_entry = tk.Entry(root)
    numero_orcamento_entry.grid(row=0, column=1)

    def on_gerar_pdf():
        numero_orcamento = numero_orcamento_entry.get()
        if numero_orcamento.isdigit():
            gerar_pdf(numero_orcamento)
        else:
            messagebox.showerror("Erro", "Por favor, insira um número de orçamento válido.")

    tk.Button(root, text="Gerar PDF", command=on_gerar_pdf).grid(row=1, columnspan=2)

    root.mainloop()

if __name__ == "__main__":
    criar_interface()
