import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

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


def init_database():
    sheet = conectar()

    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["id", "data", "tipo", "categoria", "descricao", "valor"])


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


def adicionar_transacao(tipo, valor, categoria, descricao, data):
    sheet = conectar()
    dados = sheet.get_all_records()
    df = pd.DataFrame(dados)

    # 🔥 Correção DEFINITIVA: garantir que o ID é numérico
    if df.empty:
        novo_id = 1
    else:
        df["id"] = pd.to_numeric(df["id"], errors="coerce")
        novo_id = int(df["id"].max() + 1)

    nova_linha = [
        novo_id,
        str(data),
        str(tipo),
        str(categoria),
        str(descricao),
        float(valor)
    ]

    sheet.append_row(nova_linha)


def excluir_transacao(id_transacao):
    sheet = conectar()
    dados = sheet.get_all_records()

    df = pd.DataFrame(dados)

    if df.empty or id_transacao not in df["id"].values:
        return False

    linha = df.index[df["id"] == id_transacao][0] + 2
    sheet.delete_rows(linha)

    return True


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


def obter_gastos_por_categoria(mes, ano):
    df = obter_transacoes(mes, ano)

    if df.empty:
        return pd.DataFrame()

    despesas = df[df["tipo"] == "Despesa"]

    if despesas.empty:
        return pd.DataFrame()

    return despesas.groupby("categoria")["valor"].sum().reset_index(name="total")
