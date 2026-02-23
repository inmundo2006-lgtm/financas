import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

COLUNAS = ["id", "data", "tipo", "categoria", "descricao", "valor", "status", "data_vencimento", "tipo_lancamento", "parcela_atual", "total_parcelas", "id_grupo"]

STATUS_PAGO = "Pago"
STATUS_PENDENTE = "Pendente"
STATUS_ATRASADO = "Atrasado"

TIPO_NORMAL = "Normal"
TIPO_FIXA = "Fixa"
TIPO_PARCELADA = "Parcelada"

@st.cache_resource
def conectar():
    creds_info = st.secrets["google_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return client.open_by_url(spreadsheet_url).worksheet("transacoes")

@st.cache_data(ttl=10)
def _ler_dataframe():
    sheet = conectar()
    valores = sheet.get_all_values()
    if len(valores) <= 1:
        return pd.DataFrame(columns=COLUNAS)
    return pd.DataFrame(valores[1:], columns=valores[0])

def _limpar_cache():
    _ler_dataframe.clear()

def init_database():
    sheet = conectar()
    valores = sheet.get_all_values()
    if not valores:
        sheet.append_rows([COLUNAS], value_input_option="USER_ENTERED")
        return
    # ... (resto da função init_database igual ao seu original)

def _proximo_id(todos_valores):
    if len(todos_valores) <= 1:
        return 1
    ids = [int(linha[0]) for linha in todos_valores[1:] if linha[0].isdigit()]
    return max(ids) + 1 if ids else 1

def _proximo_id_grupo(todos_valores):
    if len(todos_valores) <= 1:
        return 1
    grupos = [int(linha[11]) for linha in todos_valores[1:] if linha[11].isdigit()]
    return max(grupos) + 1 if grupos else 1

def _gravar_linhas(linhas):
    sheet = conectar()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()

# Funções de excluir e marcar como pago (mantidas iguais ao seu original)

# ── ADICIONAR TRANSAÇÃO AVULSA ───────────────────────────────────────────────
def adicionar_transacao(tipo, valor, categoria, descricao, data, status, data_vencimento=None):
    sheet = conectar()
    todos = sheet.get_all_values()
    proximo_id = _proximo_id(todos)
    valor_str = locale.currency(float(valor), grouping=True, symbol='R$')
    linha = [proximo_id, data, tipo, categoria, descricao, valor_str, status, data_vencimento or "", TIPO_NORMAL, "", "", ""]
    _gravar_linhas([linha])

# ── ADICIONAR CONTA FIXA (com data inicial opcional) ─────────────────────────
def adicionar_conta_fixa(tipo, valor, categoria, descricao, dia_vencimento, meses_a_adicionar, data_primeira=None):
    if meses_a_adicionar < 1 or valor <= 0 or not (1 <= dia_vencimento <= 31):
        raise ValueError("Parâmetros inválidos")

    sheet = conectar()
    todos = sheet.get_all_values()
    id_grupo = _proximo_id_grupo(todos)
    proximo_id_base = _proximo_id(todos)
    hoje = date.today()

    if data_primeira:
        data_inicial = datetime.strptime(data_primeira, "%Y-%m-%d").date()
    else:
        proximo_mes = hoje
        while True:
            try:
                candidato = proximo_mes.replace(day=dia_vencimento)
                if candidato > hoje:
                    data_inicial = candidato
                    break
            except ValueError:
                pass
            proximo_mes += relativedelta(months=1)

    linhas = []
    data_atual = data_inicial
    for i in range(meses_a_adicionar):
        status = STATUS_PAGO if data_atual <= hoje else STATUS_PENDENTE
        valor_str = locale.currency(float(valor), grouping=True, symbol='R$')
        linha = [proximo_id_base + i, data_atual.strftime("%Y-%m-%d"), tipo, categoria, descricao, valor_str, status, data_atual.strftime("%Y-%m-%d"), TIPO_FIXA, "", "", str(id_grupo)]
        linhas.append(linha)
        data_atual += relativedelta(months=1)
        if data_atual.day != dia_vencimento:
            try:
                data_atual = data_atual.replace(day=dia_vencimento)
            except ValueError:
                data_atual = (data_atual + relativedelta(day=31)).replace(day=dia_vencimento)

    _gravar_linhas(linhas)

# ── ADICIONAR COMPRA PARCELADA (mantida igual ao seu original) ───────────────
def adicionar_compra_parcelada(tipo, valor_total, categoria, descricao, n_parcelas, data_primeira):
    # ... seu código original dessa função ...
    pass  # substitua pela sua versão original se quiser

# (cole aqui todas as outras funções que você já tinha: obter_transacoes, obter_resumo_mensal, etc.)