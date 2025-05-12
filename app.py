
import streamlit as st
import pandas as pd
import easyocr
import fitz  # PyMuPDF
from PIL import Image
import io
import re
from difflib import SequenceMatcher

st.set_page_config(page_title="Verificador de Tabloide", layout="wide")
st.title("🛒 Verificador de Tabloide - Rede Bom Lugar")

pdf_file = st.file_uploader("📄 Envie o PDF do tabloide", type=["pdf"])
excel_file = st.file_uploader("📊 Envie a planilha Excel de produtos", type=["xls", "xlsx"])

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def normalize(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()

def valor_em_pdf(valor, texto):
    if not valor:
        return False
    valor = str(valor).replace(".", ",") if "," in texto else str(valor)
    padrao = re.sub(r"[.,]", r"[.,\n]", valor)
    return re.search(padrao, texto.replace(" ", ""), re.IGNORECASE) is not None

if pdf_file and excel_file:
    df = pd.read_excel(excel_file)
    df = df.iloc[2:].copy()
    df.columns = [
        "COD", "DESCRICAO_SISTEMA", "SETOR", "DESCRICAO_TABLOIDE", "CUSTO", "VENDA", 
        "SELL_OUT", "VENDA_APP", "SELL_OUT_APP", "MARGEM", "MARGEM_APP", "FORNECEDOR", 
        "SELLOUT", "ENCARTE"
    ]
    df = df[df["DESCRICAO_SISTEMA"].notna()].reset_index(drop=True)

    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    reader = easyocr.Reader(["pt"], gpu=False)
    ocr_text = ""

    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        result = reader.readtext(img_bytes, detail=0, paragraph=True)
        ocr_text += "\n".join(result) + "\n"

    relatorio = []
    nomes_pdf = re.findall(r'[A-Z0-9 \-\.,]{5,}', ocr_text.upper())

    for _, row in df.iterrows():
        nome = row["DESCRICAO_SISTEMA"]
        preco = str(row["VENDA"]).replace(",", ".")
        preco_app = str(row["VENDA_APP"]).replace(",", ".") if pd.notna(row["VENDA_APP"]) else ""
        descricao_tab = row["DESCRICAO_TABLOIDE"]

        erros = []
        if not any(similar(nome.upper(), n.strip()) > 0.75 for n in nomes_pdf):
            erros.append("Nome/Marca possivelmente não identificado")

        match_gram = re.search(r'(\d+[,\.]?\d*)(kg|g|ml|l)', nome.lower())
        if match_gram and normalize(match_gram.group()) not in normalize(ocr_text):
            erros.append("Gramatura divergente ou ausente")

        if preco and not valor_em_pdf(preco, ocr_text):
            erros.append(f"Preço normal {preco} não encontrado")

        if preco_app and not valor_em_pdf(preco_app, ocr_text):
            erros.append(f"Preço App {preco_app} não encontrado")

        if erros:
            relatorio.append({
                "Produto": nome,
                "Descrição": descricao_tab,
                "Erros": "; ".join(erros)
            })

    if relatorio:
        st.subheader("❌ Erros Encontrados")
        st.dataframe(pd.DataFrame(relatorio))
    else:
        st.success("✅ Nenhum erro identificado nos produtos comparados.")

st.markdown("""<hr><center><small>Desenvolvido para Rede Bom Lugar · Paola</small></center>""", unsafe_allow_html=True)
