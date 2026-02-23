import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials

# ── Schema ──────────────────────────────────────────────────────────────────
# id | data | tipo | categoria | descricao | valor |
# status | data_vencimento | tipo_lancamento | parcela_atual | total_parcelas | id_grupo

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
    # Migração: adiciona colunas novas se a planilha é antiga (6 colunas)
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
    ids = []
    for linha in todos_valores[1:]:
        try:
            ids.append(int(linha[0]))
        except (ValueError, IndexError):
            pass
    return max(ids) + 1 if ids else 1


def _proximo_id_grupo(todos_valores):
    if len(todos_valores) <= 1:
        return 1
    grupos = []
    for linha in todos_valores[1:]:
        try:
            if linha[11]:
                grupos.append(int(linha[11]))
        except (ValueError, IndexError):
            pass
    return max(grupos) + 1 if grupos else 1


def _gravar_linhas(linhas: list[list]):
    """Grava uma ou mais linhas no final da planilha."""
    sheet = conectar()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


# ── CRUD Principal ────────────────────────────────────────────────────────────
def obter_transacoes(mes=None, ano=None, incluir_futuros=False):
    df = _ler_dataframe().copy()
    if df.empty:
        return df

    # Garante colunas novas mesmo em planilhas antigas
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""

    df["data"]            = pd.to_datetime(df["data"], errors="coerce")
    df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], errors="coerce")
    df["valor"]           = pd.to_numeric(df["valor"], errors="coerce")
    df["id"]              = pd.to_numeric(df["id"], errors="coerce")
    df["parcela_atual"]   = pd.to_numeric(df["parcela_atual"], errors="coerce")
    df["total_parcelas"]  = pd.to_numeric(df["total_parcelas"], errors="coerce")
    df["id_grupo"]        = pd.to_numeric(df["id_grupo"], errors="coerce")
    df = df.dropna(subset=["data", "valor"])

    # Preenche campos opcionais
    df["status"]          = df["status"].replace("", STATUS_PAGO).fillna(STATUS_PAGO)
    df["tipo_lancamento"] = df["tipo_lancamento"].replace("", TIPO_NORMAL).fillna(TIPO_NORMAL)

    # Atualiza status atrasado automaticamente (só local, sem regravar)
    hoje = pd.Timestamp(date.today())
    mask_atrasado = (
        (df["status"] == STATUS_PENDENTE) &
        (df["data_vencimento"].notna()) &
        (df["data_vencimento"] < hoje)
    )
    df.loc[mask_atrasado, "status"] = STATUS_ATRASADO

    if not incluir_futuros:
        # Por padrão exclui lançamentos futuros ainda pendentes
        df = df[
            (df["status"] == STATUS_PAGO) |
            (df["status"] == STATUS_ATRASADO) |
            (df["data_vencimento"].isna()) |
            (df["data_vencimento"] <= hoje)
        ]

    if mes:
        ref = df["data_vencimento"].fillna(df["data"])
        df = df[ref.dt.month == mes]
    if ano:
        ref = df["data_vencimento"].fillna(df["data"])
        df = df[ref.dt.year == ano]

    return df.reset_index(drop=True)


def obter_todos_com_futuros(mes=None, ano=None):
    """Retorna tudo incluindo lançamentos futuros pendentes."""
    return obter_transacoes(mes=mes, ano=ano, incluir_futuros=True)


def obter_a_vencer(dias=30):
    """Retorna lançamentos pendentes que vencem nos próximos N dias."""
    df = _ler_dataframe().copy()
    if df.empty:
        return pd.DataFrame(columns=COLUNAS)

    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""

    df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], errors="coerce")
    df["valor"]           = pd.to_numeric(df["valor"], errors="coerce")
    df["id"]              = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["data_vencimento", "valor"])

    hoje  = pd.Timestamp(date.today())
    limite = hoje + pd.Timedelta(days=dias)

    pendentes = df[
        (df["status"].isin([STATUS_PENDENTE, ""])) &
        (df["data_vencimento"] >= hoje) &
        (df["data_vencimento"] <= limite)
    ].copy()

    pendentes = pendentes.sort_values("data_vencimento")
    return pendentes.reset_index(drop=True)


def obter_total_pendente_mes(mes, ano):
    """Total de despesas pendentes/atrasadas no mês."""
    df = obter_todos_com_futuros(mes=mes, ano=ano)
    if df.empty:
        return 0.0
    mask = (df["tipo"] == "Despesa") & (df["status"].isin([STATUS_PENDENTE, STATUS_ATRASADO]))
    return float(df.loc[mask, "valor"].sum())


def adicionar_transacao(tipo, valor, categoria, descricao, data,
                        status=STATUS_PAGO, data_vencimento=None,
                        tipo_lancamento=TIPO_NORMAL,
                        parcela_atual=None, total_parcelas=None, id_grupo=None):
    sheet = conectar()
    todos_valores = sheet.get_all_values()
    novo_id = _proximo_id(todos_valores)

    dv = str(data_vencimento) if data_vencimento else str(data)

    nova_linha = [
        novo_id, str(data), str(tipo), str(categoria), str(descricao), float(valor),
        str(status), str(dv), str(tipo_lancamento),
        int(parcela_atual) if parcela_atual else "",
        int(total_parcelas) if total_parcelas else "",
        int(id_grupo) if id_grupo else ""
    ]

    sheet.append_rows([nova_linha], value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


def adicionar_conta_fixa(tipo, valor, categoria, descricao, dia_vencimento, meses=12):
    """Gera lançamentos mensais recorrentes para os próximos N meses."""
    sheet = conectar()
    todos_valores = sheet.get_all_values()
    novo_id    = _proximo_id(todos_valores)
    novo_grupo = _proximo_id_grupo(todos_valores)

    hoje = date.today()
    linhas = []

    for i in range(meses):
        mes_ref = hoje + relativedelta(months=i)
        try:
            venc = date(mes_ref.year, mes_ref.month, dia_vencimento)
        except ValueError:
            # Dia inválido para o mês (ex: 31 em fevereiro) → último dia
            import calendar
            ultimo = calendar.monthrange(mes_ref.year, mes_ref.month)[1]
            venc = date(mes_ref.year, mes_ref.month, ultimo)

        status = STATUS_PAGO if venc <= hoje else STATUS_PENDENTE
        linhas.append([
            novo_id + i, str(hoje), str(tipo), str(categoria),
            str(descricao), float(valor),
            str(status), str(venc), TIPO_FIXA,
            "", "", novo_grupo
        ])

    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


def adicionar_compra_parcelada(tipo, valor_total, categoria, descricao,
                                n_parcelas, data_primeira):
    """Divide o valor total em N parcelas mensais a partir da primeira data."""
    sheet = conectar()
    todos_valores = sheet.get_all_values()
    novo_id    = _proximo_id(todos_valores)
    novo_grupo = _proximo_id_grupo(todos_valores)

    valor_parcela = round(valor_total / n_parcelas, 2)
    hoje  = date.today()
    linhas = []

    for i in range(n_parcelas):
        venc   = data_primeira + relativedelta(months=i)
        status = STATUS_PAGO if venc <= hoje else STATUS_PENDENTE
        desc_parc = f"{descricao} ({i+1}/{n_parcelas})"
        linhas.append([
            novo_id + i, str(hoje), str(tipo), str(categoria),
            str(desc_parc), float(valor_parcela),
            str(status), str(venc), TIPO_PARCELADA,
            i + 1, n_parcelas, novo_grupo
        ])

    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


def marcar_como_pago(id_transacao):
    """Atualiza o status de uma transação para Pago."""
    sheet = conectar()
    todos_valores = sheet.get_all_values()

    for i, linha in enumerate(todos_valores[1:], start=2):
        try:
            if int(linha[0]) == int(id_transacao):
                sheet.update_cell(i, 7, STATUS_PAGO)  # coluna G = status
                _limpar_cache()
                return True
        except (ValueError, IndexError):
            pass
    return False


def excluir_transacao(id_transacao):
    sheet = conectar()
    df = _ler_dataframe()
    if df.empty:
        return False

    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    match = df[df["id"] == id_transacao]
    if match.empty:
        return False

    linha_planilha = match.index[0] + 2
    sheet.delete_rows(linha_planilha)
    _limpar_cache()
    return True


def excluir_grupo(id_grupo):
    """Exclui todas as transações de um grupo (parcelas ou conta fixa)."""
    sheet = conectar()
    df = _ler_dataframe()
    if df.empty:
        return 0

    df["id_grupo"] = pd.to_numeric(df["id_grupo"], errors="coerce")
    linhas = df[df["id_grupo"] == id_grupo]
    if linhas.empty:
        return 0

    # Deleta de baixo para cima para não deslocar índices
    indices = sorted(linhas.index.tolist(), reverse=True)
    for idx in indices:
        sheet.delete_rows(idx + 2)

    _limpar_cache()
    return len(indices)


# ── Resumos ───────────────────────────────────────────────────────────────────
def obter_resumo_mensal(mes, ano):
    df = obter_todos_com_futuros(mes, ano)
    if df.empty:
        return {"receitas": 0.0, "despesas": 0.0, "total_transacoes": 0}

    # Saldo projetado: inclui tudo (pago + pendente + atrasado)
    receitas = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas = df[df["tipo"] == "Despesa"]["valor"].sum()

    # Separado para exibir no dashboard
    receitas_pagas = df[(df["tipo"] == "Receita") & (df["status"] == STATUS_PAGO)]["valor"].sum()
    despesas_pagas = df[(df["tipo"] == "Despesa") & (df["status"] == STATUS_PAGO)]["valor"].sum()

    return {
        "receitas": float(receitas),
        "despesas": float(despesas),
        "receitas_pagas": float(receitas_pagas),
        "despesas_pagas": float(despesas_pagas),
        "total_transacoes": len(df)
    }


def obter_gastos_por_categoria(mes, ano):
    df = obter_transacoes(mes, ano)
    if df.empty:
        return pd.DataFrame()
    despesas = df[(df["tipo"] == "Despesa") & (df["status"] == STATUS_PAGO)]
    if despesas.empty:
        return pd.DataFrame()
    return despesas.groupby("categoria")["valor"].sum().reset_index(name="total")
