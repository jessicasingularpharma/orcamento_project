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

def recuperar_dados_orcamento(conn, cdfil, nrorc):
    """Recupera os dados do orçamento e itens."""
    query = """
    SELECT item.CDFIL, item.NRORC, item.SERIEO, item.ITEMID, item.DESCR, item.QUANT, item.UNIDA, item.VRCMP, item.CDPRO, 
           orc.VOLUME, orc.UNIVOL, orc.TPCAP
    FROM FC15110 item
    LEFT JOIN FC15100 orc ON item.CDFIL = orc.CDFIL AND item.NRORC = orc.NRORC AND item.SERIEO = orc.SERIEO
    WHERE item.CDFIL = ? AND item.NRORC = ?
    AND item.TPCMP IN ( 'C', 'S','H' ) 
    ORDER BY item.SERIEO, item.ITEMID
    """
    itens_orcamento = pd.read_sql(query, conn, params=[cdfil, nrorc])

    return itens_orcamento

def formatar_dados(itens_orcamento):
    """Formata os dados do orçamento no formato solicitado."""
    formatted_data = []
    sub_total = 0  # Variável para calcular o subtotal

    for serie, grupo in itens_orcamento.groupby('SERIEO'):
        serie_total = 0  # Variável para calcular o total por série
        formatted_data.append(f"ORC:{int(grupo.iloc[0]['CDFIL']):04d}-{grupo.iloc[0]['NRORC']}-{serie}:")
        for _, row in grupo.iterrows():
            descricao = f" - {row['DESCR'] or 'Descrição não disponível'}: {row['QUANT']}{row['UNIDA']} | {row['CDPRO']}"
            volume = f"Volume: {row['VOLUME']} {row['UNIVOL']}, Tipo de Cápsula: {row['TPCAP']}" if row['VOLUME'] and row['UNIVOL'] and row['TPCAP'] else ""
            formatted_data.append(f"{descricao}\n{volume}\n")
            sub_total += row['VRCMP'] if not pd.isnull(row['VRCMP']) else 0
            serie_total += row['VRCMP'] if not pd.isnull(row['VRCMP']) else 0

        # Adicionar total da série ao final dos dados da série
        formatted_data.append(f"Total da Série {serie}: R$ {serie_total:.2f}\n")

    # Adicionar subtotal e total ao final dos dados formatados
    formatted_data.append(f"\nSUB-TOTAL: R$ {sub_total:.2f}")
    formatted_data.append(f"TOTAL: R$ {sub_total:.2f}")

    return formatted_data

def criar_pdf(formatted_data, cdfil, nrorc):
    """Cria o PDF com os dados formatados e o salva na pasta Downloads."""
    download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    pdf_path = os.path.join(download_folder, f"Orcamento_{cdfil}_{nrorc}.pdf")

    pdf = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 40, "Relatório de Orçamento")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 60, f"CDFIL: {cdfil}, NRORC: {nrorc}")
    pdf.drawString(50, height - 75, f"Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}")

    y = height - 100
    for line in formatted_data:
        for subline in line.split("\n"):
            pdf.drawString(50, y, subline)
            y -= 20
            if y < 40:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 40

    pdf.save()
    return pdf_path

def exibir_preview(formatted_data, cdfil, nrorc):
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
        pdf_path = criar_pdf(formatted_data, cdfil, nrorc)
        messagebox.showinfo("Sucesso", f"PDF salvo com sucesso na pasta Downloads: {pdf_path}")
        preview_window.destroy()

    tk.Button(preview_window, text="Salvar PDF", command=salvar_pdf).pack(pady=10)

def gerar_pdf(cdfil, nrorc):
    """Controla o fluxo de geração de PDF."""
    try:
        conn = conectar_banco()
        try:
            itens_orcamento = recuperar_dados_orcamento(conn, cdfil, nrorc)
            formatted_data = formatar_dados(itens_orcamento)
            exibir_preview(formatted_data, cdfil, nrorc)
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

    tk.Label(root, text="NRORC:").grid(row=1, column=0)
    nrorc_entry = tk.Entry(root)
    nrorc_entry.grid(row=1, column=1)

    def on_gerar_pdf():
        cdfil = cdfil_entry.get()
        nrorc = nrorc_entry.get()
        if cdfil.isdigit() and nrorc.isdigit():
            gerar_pdf(int(cdfil), int(nrorc))
        else:
            messagebox.showerror("Erro", "Por favor, insira valores numéricos válidos.")

    tk.Button(root, text="Gerar PDF", command=on_gerar_pdf).grid(row=2, columnspan=2)

    root.mainloop()

if __name__ == "__main__":
    criar_interface()
