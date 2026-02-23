import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials
import locale

# Configuração de locale para formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

# ── Schema ──────────────────────────────────────────────────────────────────
COLUNAS = [
    "id", "data", "tipo", "categoria", "descricao", "valor",
    "status", "data_vencimento", "tipo_lancamento",
    "parcela_atual", "total_parcelas", "id_grupo"
]

STATUS_PAGO     = "Pago"
STATUS_PENDENTE = "Pendente"
STATUS_ATRASADO = "Atrasado"

TIPO_NORMAL    = "Normal"
TIPO_FIXA      = "Fixa"
TIPO_PARCELADA = "Parcelada"


# ── Conexão ──────────────────────────────────────────────────────────────────
@st.cache_resource
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


# ── Leitura ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def _ler_dataframe():
    sheet = conectar()
    valores = sheet.get_all_values()
    if len(valores) <= 1:
        return pd.DataFrame(columns=COLUNAS)
    cabecalho = valores[0]
    dados = valores[1:]
    df = pd.DataFrame(dados, columns=cabecalho)
    return df


def _limpar_cache():
    _ler_dataframe.clear()


# ── Inicialização ─────────────────────────────────────────────────────────────
def init_database():
    sheet = conectar()
    valores = sheet.get_all_values()
    if not valores:
        sheet.append_rows([COLUNAS], value_input_option="USER_ENTERED")
        return

    cabecalho = valores[0]
    if len(cabecalho) < len(COLUNAS):
        novas = COLUNAS[len(cabecalho):]
        col_inicio = len(cabecalho) + 1
        for i, col in enumerate(novas):
            sheet.update_cell(1, col_inicio + i, col)
        _limpar_cache()


# ── Helpers internos ──────────────────────────────────────────────────────────
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


def _gravar_linhas(linhas: list[list]):
    sheet = conectar()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


# ── EXCLUIR GRUPO ─────────────────────────────────────────────────────────────
def excluir_grupo(id_grupo):
    df = _ler_dataframe().copy()
    if df.empty:
        return False
    df = df[df["id_grupo"] != str(id_grupo)]
    sheet = conectar()
    sheet.clear()
    sheet.append_row(COLUNAS)
    sheet.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    _limpar_cache()
    return True


# ── EXCLUIR TRANSAÇÃO ─────────────────────────────────────────────────────────
def excluir_transacao(id_transacao):
    df = _ler_dataframe().copy()
    if df.empty:
        return False
    df = df[df["id"] != str(id_transacao)]
    sheet = conectar()
    sheet.clear()
    sheet.append_row(COLUNAS)
    sheet.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    _limpar_cache()
    return True


# ── MARCAR COMO PAGO ──────────────────────────────────────────────────────────
def marcar_como_pago(id_transacao):
    df = _ler_dataframe().copy()
    if df.empty:
        return False
    df.loc[df["id"] == str(id_transacao), "status"] = STATUS_PAGO
    sheet = conectar()
    sheet.clear()
    sheet.append_row(COLUNAS)
    sheet.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    _limpar_cache()
    return True


# ── ADICIONAR CONTA FIXA (versão final com data inicial opcional) ─────────────
def adicionar_conta_fixa(tipo, valor, categoria, descricao, dia_vencimento, meses_a_adicionar, data_primeira=None):
    if meses_a_adicionar < 1:
        raise ValueError("Deve adicionar pelo menos 1 mês")
    if not isinstance(valor, (int, float)) or valor <= 0:
        raise ValueError("Valor deve ser positivo")
    if not (1 <= dia_vencimento <= 31):
        raise ValueError("Dia de vencimento inválido (1-31)")

    sheet = conectar()
    todos_valores = sheet.get_all_values()
    id_grupo = _proximo_id_grupo(todos_valores)
    proximo_id_base = _proximo_id(todos_valores)

    hoje = date.today()

    # Determina data inicial
    if data_primeira:
        try:
            data_inicial = datetime.strptime(data_primeira, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Formato de data inválido. Use YYYY-MM-DD")
    else:
        # Próximo vencimento futuro
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

        linha = [
            proximo_id_base + i,
            data_atual.strftime("%Y-%m-%d"),
            tipo,
            categoria,
            descricao,
            valor_str,
            status,
            data_atual.strftime("%Y-%m-%d"),
            TIPO_FIXA,
            "", "", str(id_grupo)
        ]
        linhas.append(linha)

        data_atual += relativedelta(months=1)
        if data_atual.day != dia_vencimento:
            try:
                data_atual = data_atual.replace(day=dia_vencimento)
            except ValueError:
                data_atual = (data_atual + relativedelta(day=31)).replace(day=dia_vencimento)

    _gravar_linhas(linhas)
    _limpar_cache()


# ── (mantenha aqui todas as outras funções que você já tinha: adicionar_transacao, adicionar_compra_parcelada,
#     obter_transacoes, obter_todos_com_futuros, obter_resumo_mensal, etc.) ────────
# (cole o resto do seu database.py antigo aqui, só troque a função adicionar_conta_fixa pela acima)