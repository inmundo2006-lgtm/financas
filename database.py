import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ============================
# 1. CONEXÃO COM GOOGLE SHEETS
# ============================

def conectar():
    creds_info = st.secrets["google_service_account"]

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)

    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sheet = client.open_by_url(spreadsheet_url).worksheet("transacoes")

    return sheet


# ============================
# 2. INICIALIZAR BANCO
# ============================

def init_database():
    sheet = conectar()

    # Se a planilha estiver vazia, cria o cabeçalho
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["id", "data", "tipo", "categoria", "descricao", "valor"])


# ============================
# 3. OBTER TODAS AS TRANSAÇÕES
# ============================

def obter_transacoes(mes=None, ano=None):
    sheet = conectar()
    dados = sheet.get_all_records()

    df = pd.DataFrame(dados)

    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = df["valor"].astype(float)

    if mes:
        df = df[df["data"].dt.month == mes]
    if ano:
        df = df[df["data"].dt.year == ano]

    return df


# ============================
# 4. ADICIONAR TRANSAÇÃO
# ============================

def adicionar_transacao(tipo, valor, categoria, descricao, data):
    sheet = conectar()
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    novo_id = 1 if df.empty else df["id"].max() + 1

    # 🔥 Correção importante: garantir que o valor é float
    valor = float(valor)

    nova_linha = [
        novo_id,
        data,
        tipo,
        categoria,
        descricao,
        valor
    ]

    sheet.append_row(nova_linha)


# ============================
# 5. EXCLUIR TRANSAÇÃO
# ============================

def excluir_transacao(id_transacao):
    sheet = conectar()
    dados = sheet.get_all_records()

    df = pd.DataFrame(dados)

    if df.empty or id_transacao not in df["id"].values:
        return False

    linha = df.index[df["id"] == id_transacao][0] + 2  # +2 por causa do cabeçalho
    sheet.delete_rows(linha)

    return True


# ============================
# 6. RESUMO MENSAL
# ============================

def obter_resumo_mensal(mes, ano):
    df = obter_transacoes(mes, ano)

    if df.empty:
        return {
            "receitas": 0,
            "despesas": 0,
            "total_transacoes": 0
        }

    receitas = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas = df[df["tipo"] == "Despesa"]["valor"].sum()

    return {
        "receitas": receitas,
        "despesas": despesas,
        "total_transacoes": len(df)
    }


# ============================
# 7. GASTOS POR CATEGORIA
# ============================

def obter_gastos_por_categoria(mes, ano):
    df = obter_transacoes(mes, ano)

    if df.empty:
        return pd.DataFrame()

    despesas = df[df["tipo"] == "Despesa"]

    if despesas.empty:
        return pd.DataFrame()

    return despesas.groupby("categoria")["valor"].sum().reset_index(name="total")
