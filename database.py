import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

COLUNAS = ["id", "data", "tipo", "categoria", "descricao", "valor"]


@st.cache_resource
def conectar():
    """Conexão autenticada reutilizável — criada apenas uma vez."""
    creds_info = st.secrets["google_service_account"]
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sheet = client.open_by_url(spreadsheet_url).worksheet("transacoes")
    return sheet


@st.cache_data(ttl=60)
def _ler_dataframe():
    """
    Lê todos os dados da planilha de forma confiável.
    Cache de 60s — limpo automaticamente após mutações.
    """
    sheet = conectar()
    valores = sheet.get_all_values()  # get_all_records() pode perder linhas duplicadas
    if len(valores) <= 1:
        return pd.DataFrame(columns=COLUNAS)
    cabecalho = valores[0]
    dados = valores[1:]
    df = pd.DataFrame(dados, columns=cabecalho)
    return df


def _limpar_cache():
    """Invalida o cache de leitura após qualquer mutação."""
    _ler_dataframe.clear()


def init_database():
    sheet = conectar()
    if not sheet.get_all_values():
        sheet.append_row(COLUNAS)


def obter_transacoes(mes=None, ano=None):
    df = _ler_dataframe().copy()
    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["data", "valor"])

    if mes:
        df = df[df["data"].dt.month == mes]
    if ano:
        df = df[df["data"].dt.year == ano]

    return df.reset_index(drop=True)


def adicionar_transacao(tipo, valor, categoria, descricao, data):
    sheet = conectar()

    # Busca fresca direto da API (sem cache) para calcular próxima linha real
    todos_valores = sheet.get_all_values()
    total_linhas = len(todos_valores)  # inclui cabeçalho

    # Calcula novo ID a partir das linhas existentes
    if total_linhas <= 1:
        novo_id = 1
    else:
        ids_existentes = []
        for linha in todos_valores[1:]:  # pula cabeçalho
            try:
                ids_existentes.append(int(linha[0]))
            except (ValueError, IndexError):
                pass
        novo_id = max(ids_existentes) + 1 if ids_existentes else 1

    nova_linha = [
        novo_id,
        str(data),
        str(tipo),
        str(categoria),
        str(descricao),
        float(valor)
    ]

    # Escreve diretamente na próxima linha vazia — evita conflito com Tabelas do Google Sheets
    proxima_linha = total_linhas + 1
    col_inicio = "A"
    col_fim = "F"
    intervalo = f"{col_inicio}{proxima_linha}:{col_fim}{proxima_linha}"
    sheet.update(intervalo, [nova_linha], value_input_option="USER_ENTERED")

    _limpar_cache()


def excluir_transacao(id_transacao):
    sheet = conectar()
    df = _ler_dataframe()

    if df.empty:
        return False

    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    match = df[df["id"] == id_transacao]

    if match.empty:
        return False

    linha_planilha = match.index[0] + 2  # +1 cabeçalho, +1 índice base 0
    sheet.delete_rows(linha_planilha)
    _limpar_cache()
    return True


def obter_resumo_mensal(mes, ano):
    df = obter_transacoes(mes, ano)
    if df.empty:
        return {"receitas": 0.0, "despesas": 0.0, "total_transacoes": 0}

    receitas = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas = df[df["tipo"] == "Despesa"]["valor"].sum()
    return {
        "receitas": float(receitas),
        "despesas": float(despesas),
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
