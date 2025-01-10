import pandas as pd
import fdb
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tkinter as tk
from tkinter import messagebox, Toplevel, Text, Scrollbar, RIGHT, Y, END
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def conectar_banco():
    """Conecta ao banco de dados Firebird."""
    try:
        return fdb.connect(
            dsn=f"{os.getenv('FIREBIRD_HOST')}:{os.getenv('FIREBIRD_DATABASE')}",
            user=os.getenv("FIREBIRD_USER"),
            password=os.getenv("FIREBIRD_PASSWORD")
        )
    except Exception as e:
        raise ConnectionError(f"Erro ao conectar ao banco de dados: {e}")

def recuperar_dados_orcamento(conn, cdfil, nrrqu):
    """Recupera os dados do orçamento e itens."""
    query1 = """
    SELECT o.NRORC, o.DTENTR, o.CDCLI, o.NOMEPA, 
           f.NRCRM, o.VRRQU, o.ENDEPA, o.CDCON
    FROM FC15000 o
    JOIN FC15100 f ON o.NRORC = f.NRORC
    WHERE o.NRORC = ?
    """
    query2 = """
    SELECT CDFIL, NRORC AS NRRQU, SERIEO AS SERIER, TITROT AS DESCRDAV, 
           QTCONT AS QTDAV, UNIVOL AS UNIDADAV, PRREAL AS VALOR
    FROM FC15100
    WHERE CDFIL = ? AND NRORC = ?
    ORDER BY SERIEO
    """
    dados_orcamento = pd.read_sql(query1, conn, params=[nrrqu])
    itens_orcamento = pd.read_sql(query2, conn, params=[cdfil, nrrqu])
    
    return dados_orcamento, itens_orcamento

def formatar_dados(dados_orcamento, itens_orcamento):
    """Formata os dados do orçamento no formato solicitado."""
    formatted_data = []
    for _, row in itens_orcamento.iterrows():
        orcamento = f"ORC:{int(row['CDFIL']):04d}-{row['NRRQU']}-{row['SERIER']}"
        descricao = f"{row['DESCRDAV']} {row['QTDAV']}{row['UNIDADAV']}"
        valor = f"Valor R$: {row['VALOR']:.2f}" if not pd.isnull(row['VALOR']) else "Valor não disponível"
        formatted_data.append(f"{orcamento}\nFORMULA MANIPULADA - {descricao}\n{valor}")
    return formatted_data

def criar_pdf(formatted_data, cdfil, nrrqu):
    """Cria o PDF com os dados formatados e o salva na pasta Downloads."""
    download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    pdf_path = os.path.join(download_folder, f"Orcamento_{cdfil}_{nrrqu}.pdf")
    
    pdf = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 40, "Relatório de Orçamento")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 60, f"CDFIL: {cdfil}, NRRQU: {nrrqu}")
    pdf.drawString(50, height - 75, f"Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")

    y = height - 100
    for line in formatted_data:
        pdf.drawString(50, y, line)
        y -= 30  # Ajuste para espaçamento entre as linhas
        if y < 40:
            pdf.showPage()
            y = height - 40

    pdf.save()
    return pdf_path

def exibir_preview(formatted_data, cdfil, nrrqu):
    """Exibe o preview dos dados formatados antes de salvar o PDF."""
    preview_window = Toplevel()
    preview_window.title("Pré-visualização do PDF")

    text_widget = Text(preview_window, wrap="word", width=80, height=25)
    scrollbar = Scrollbar(preview_window, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=RIGHT, fill=Y)
    text_widget.pack(expand=True, fill="both")

    for line in formatted_data:
        text_widget.insert(END, line + "\n")

    def salvar_pdf():
        pdf_path = criar_pdf(formatted_data, cdfil, nrrqu)
        messagebox.showinfo("Sucesso", f"PDF salvo com sucesso na pasta Downloads: {pdf_path}")
        preview_window.destroy()

    tk.Button(preview_window, text="Salvar PDF", command=salvar_pdf).pack(pady=10)

def gerar_pdf(cdfil, nrrqu):
    """Controla o fluxo de geração de PDF."""
    try:
        conn = conectar_banco()
        try:
            dados_orcamento, itens_orcamento = recuperar_dados_orcamento(conn, cdfil, nrrqu)
            formatted_data = formatar_dados(dados_orcamento, itens_orcamento)
            exibir_preview(formatted_data, cdfil, nrrqu)
        finally:
            conn.close()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao gerar PDF: {e}")

def criar_interface():
    """Cria a interface gráfica para entrada de dados."""
    root = tk.Tk()
    root.title("Gerar PDF de Orçamento")

    tk.Label(root, text="CDFIL:").grid(row=0, column=0)
    cdfil_entry = tk.Entry(root)
    cdfil_entry.grid(row=0, column=1)

    tk.Label(root, text="NRRQU:").grid(row=1, column=0)
    nrrqu_entry = tk.Entry(root)
    nrrqu_entry.grid(row=1, column=1)

    def on_gerar_pdf():
        cdfil = cdfil_entry.get()
        nrrqu = nrrqu_entry.get()
        if cdfil.isdigit() and nrrqu.isdigit():
            gerar_pdf(int(cdfil), int(nrrqu))
        else:
            messagebox.showerror("Erro", "Por favor, insira valores numéricos válidos.")

    tk.Button(root, text="Gerar PDF", command=on_gerar_pdf).grid(row=2, columnspan=2)

    root.mainloop()

if __name__ == "__main__":
    criar_interface()
