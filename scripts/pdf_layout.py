import os
import pandas as pd
import fdb
import tkinter as tk
from tkinter import messagebox, Toplevel, Text, Scrollbar, RIGHT, Y, END
from dotenv import load_dotenv
from weasyprint import HTML, CSS

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
    AND item.TPCMP IN ('C', 'S', 'H') 
    ORDER BY item.SERIEO, item.ITEMID
    """
    return pd.read_sql(query, conn, params=[cdfil, nrorc])

def formatar_dados(itens_orcamento):
    """Formata os dados do orçamento."""
    formatted_data = []
    sub_total = 0
    for serie, grupo in itens_orcamento.groupby('SERIEO'):
        serie_total = grupo['VRCMP'].sum()
        formatted_data.append(f"ORC:{int(grupo.iloc[0]['CDFIL']):04d}-{grupo.iloc[0]['NRORC']}-{serie}:")
        for _, row in grupo.iterrows():
            descricao = f" - {row['DESCR'] or 'Descrição não disponível'}: {row['QUANT']}{row['UNIDA']} | {row['CDPRO']}"
            formatted_data.append(descricao)
        formatted_data.append(f"Total da Série {serie}: R$ {serie_total:.2f}\n")
        sub_total += serie_total
    formatted_data.append(f"\nTOTAL: R$ {sub_total:.2f}")
    return formatted_data, sub_total

def criar_pdf(formatted_data, sub_total, cdfil, nrorc):
    """Cria o PDF com os dados formatados."""
    download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    pdf_path = os.path.join(download_folder, f"Orcamento_{cdfil}_{nrorc}.pdf")
    logo_path = os.path.join(os.path.expanduser("~"), "img", "logo.png")
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ text-align: center; }}
            .logo {{ width: 200px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="file://{logo_path}" class="logo">
            <h2>Segue Orçamento</h2>
            <pre>{'\n'.join(formatted_data)}</pre>
            <h3>Total: R$ {sub_total:.2f}</h3>
        </div>
    </body>
    </html>
    """
    HTML(string=html_content).write_pdf(pdf_path)
    return pdf_path

def exibir_preview(formatted_data, sub_total, cdfil, nrorc):
    """Exibe o preview antes de salvar o PDF."""
    preview_window = Toplevel()
    preview_window.title("Pré-visualização do PDF")
    text_widget = Text(preview_window, wrap="word", width=80, height=25)
    scrollbar = Scrollbar(preview_window, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=RIGHT, fill=Y)
    text_widget.pack(expand=True, fill="both")
    text_widget.insert(END, '\n'.join(formatted_data))
    
    def salvar_pdf():
        pdf_path = criar_pdf(formatted_data, sub_total, cdfil, nrorc)
        messagebox.showinfo("Sucesso", f"PDF salvo em: {pdf_path}")
        preview_window.destroy()
    
    tk.Button(preview_window, text="Salvar PDF", command=salvar_pdf).pack(pady=10)

def gerar_pdf(cdfil, nrorc):
    """Controla o fluxo de geração do PDF."""
    try:
        conn = conectar_banco()
        try:
            itens_orcamento = recuperar_dados_orcamento(conn, cdfil, nrorc)
            formatted_data, sub_total = formatar_dados(itens_orcamento)
            exibir_preview(formatted_data, sub_total, cdfil, nrorc)
        finally:
            conn.close()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao gerar PDF: {e}")

def criar_interface():
    """Cria a interface gráfica."""
    root = tk.Tk()
    root.title("Gerar PDF de Orçamento")
    tk.Label(root, text="CDFIL:").grid(row=0, column=0)
    cdfil_entry = tk.Entry(root)
    cdfil_entry.grid(row=0, column=1)
    tk.Label(root, text="NRORC:").grid(row=1, column=0)
    nrorc_entry = tk.Entry(root)
    nrorc_entry.grid(row=1, column=1)
    
    def on_gerar_pdf():
        cdfil, nrorc = cdfil_entry.get(), nrorc_entry.get()
        if cdfil.isdigit() and nrorc.isdigit():
            gerar_pdf(int(cdfil), int(nrorc))
        else:
            messagebox.showerror("Erro", "Por favor, insira valores numéricos válidos.")
    
    tk.Button(root, text="Gerar PDF", command=on_gerar_pdf).grid(row=2, columnspan=2)
    root.mainloop()

if __name__ == "__main__":
    criar_interface()
