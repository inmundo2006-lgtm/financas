import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials

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
    ids = []
    for linha in todos_valores[1:]:
        try:
            ids.append(int(linha[0]))
        except:
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
        except:
            pass
    return max(grupos) + 1 if grupos else 1


def _gravar_linhas(linhas: list[list]):
    sheet = conectar()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


# ── EXCLUIR GRUPO (parceladas ou fixas) ───────────────────────────────────────
def excluir_grupo(id_grupo):
    df = _ler_dataframe().copy()
    if df.empty:
        return False

    df = df[df["id_grupo"] != id_grupo]

    sheet = conectar()
    sheet.clear()
    sheet.append_row(COLUNAS)

    linhas = df.astype(str).values.tolist()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED")

    _limpar_cache()
    return True


# ── EXCLUIR TRANSAÇÃO ─────────────────────────────────────────────────────────
def excluir_transacao(id_transacao):
    df = _ler_dataframe().copy()
    if df.empty:
        return False

    df = df[df["id"] != id_transacao]

    sheet = conectar()
    sheet.clear()
    sheet.append_row(COLUNAS)
    linhas = df.astype(str).values.tolist()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED")

    _limpar_cache()
    return True


# ── MARCAR COMO PAGO ─────────────────────────────────────────────────────────
def marcar_como_pago(id_transacao):
    df = _ler_dataframe().copy()
    if df.empty:
        return False

    df.loc[df["id"] == id_transacao, "status"] = STATUS_PAGO

    sheet = conectar()
    sheet.clear()
    sheet.append_row(COLUNAS)
    linhas = df.astype(str).values.tolist()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED")

    _limpar_cache()
    return True


# ── CRUD Principal ────────────────────────────────────────────────────────────
def obter_transacoes(mes=None, ano=None, incluir_futuros=False):
    df = _ler_dataframe().copy()
    if df.empty:
        return df

    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""

    df["data"]            = pd.to_datetime(df["data"], errors="coerce")
    df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], errors="coerce")

    df["valor"] = (
        df["valor"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .astype(float)
    )

    df["id"]              = pd.to_numeric(df["id"], errors="coerce")
    df["parcela_atual"]   = pd.to_numeric(df["parcela_atual"], errors="coerce")
    df["total_parcelas"]  = pd.to_numeric(df["total_parcelas"], errors="coerce")
    df["id_grupo"]        = pd.to_numeric(df["id_grupo"], errors="coerce")
    df = df.dropna(subset=["data", "valor"])

    df["status"]          = df["status"].replace("", STATUS_PAGO).fillna(STATUS_PAGO)
    df["tipo_lancamento"] = df["tipo_lancamento"].replace("", TIPO_NORMAL).fillna(TIPO_NORMAL)

    hoje = pd.Timestamp(date.today())
    mask_atrasado = (
        (df["status"] == STATUS_PENDENTE) &
        (df["data_vencimento"].notna()) &
        (df["data_vencimento"] < hoje)
    )
    df.loc[mask_atrasado, "status"] = STATUS_ATRASADO

    if not incluir_futuros:
        df = df[
            (df["status"] == STATUS_PAGO) |
            (df["status"] == STATUS_ATRASADO) |
            (df["data_vencimento"].isna()) |
            (df["data_vencimento"] <= hoje)
        ]

    if mes:
        ref = df["data"].where(
            (df["status"] == STATUS_PAGO) | (df["tipo"] == "Receita"),
            df["data_vencimento"]
        )
        df = df[ref.dt.month == mes]

    if ano:
        ref = df["data"].where(
            (df["status"] == STATUS_PAGO) | (df["tipo"] == "Receita"),
            df["data_vencimento"]
        )
        df = df[ref.dt.year == ano]

    return df.reset_index(drop=True)


def obter_todos_com_futuros(mes=None, ano=None):
    return obter_transacoes(mes=mes, ano=ano, incluir_futuros=True)


# ── SALDO ACUMULADO ENTRE MESES ───────────────────────────────────────────────
def obter_saldo_acumulado(mes, ano):
    saldo = 0.0

    for a in range(2020, ano + 1):
        for m in range(1, 13):
            if a == ano and m >= mes:
                break

            resumo = obter_resumo_mensal(m, a)
            saldo += resumo["receitas"] - resumo["despesas"]

    resumo_atual = obter_resumo_mensal(mes, ano)
    saldo += resumo_atual["receitas"] - resumo_atual["despesas"]

    return saldo


# ── A VENCER ───────────────────────────────────────────────────────────────────
def obter_a_vencer(dias=30):
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

    return pendentes.sort_values("data_vencimento").reset_index(drop=True)


# ── RESUMOS ───────────────────────────────────────────────────────────────────
def obter_resumo_mensal(mes, ano):
    df = obter_todos_com_futuros(mes, ano)
    if df.empty:
        return {"receitas": 0.0, "despesas": 0.0, "total_transacoes": 0}

    receitas = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas = df[df["tipo"] == "Despesa"]["valor"].sum()

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


# ── TOTAL PENDENTE DO MÊS ─────────────────────────────────────────────────────
def obter_total_pendente_mes(mes, ano):
    df = obter_todos_com_futuros(mes, ano)
    if df.empty:
        return 0.0

    pendentes = df[df["status"].isin([STATUS_PENDENTE, STATUS_ATRASADO])]
    return float(pendentes["valor"].sum())
# ── ADICIONAR TRANSAÇÃO AVULSA ───────────────────────────────────────────────
def adicionar_transacao(tipo, valor, categoria, descricao, data, status, data_vencimento=None):
    """
    Adiciona uma transação única (normal/avulsa).
    """
    sheet = conectar()
    todos_valores = sheet.get_all_values()
    proximo_id = _proximo_id(todos_valores)

    # Formata valor como string para o Sheets (ex: "R$ 1.234,56")
    valor_str = f"R$ {float(valor):,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")

    linha = [
        proximo_id,
        data.strftime("%Y-%m-%d") if isinstance(data, (datetime, date)) else data,
        tipo,
        categoria,
        descricao,
        valor_str,
        status,
        data_vencimento.strftime("%Y-%m-%d") if data_vencimento and isinstance(data_vencimento, (datetime, date)) else data_vencimento or "",
        TIPO_NORMAL,
        "",           # parcela_atual
        "",           # total_parcelas
        ""            # id_grupo
    ]

    _gravar_linhas([linha])
    _limpar_cache()

# ── ADICIONAR CONTA FIXA (mensal recorrente) ─────────────────────────────────
def adicionar_conta_fixa(tipo, valor, categoria, descricao, dia_vencimento, meses_a_adicionar):
    """
    Cria lançamentos recorrentes todo mês por X meses.
    """
    sheet = conectar()
    todos_valores = sheet.get_all_values()
    id_grupo = _proximo_id_grupo(todos_valores)

    hoje = datetime.now().date()
    linhas = []

    for i in range(meses_a_adicionar):
        mes_futuro = hoje + relativedelta(months=i)
        # Ajusta para o dia de vencimento desejado
        try:
            data_venc = mes_futuro.replace(day=dia_vencimento)
        except ValueError:  # ex: 31 em fevereiro
            data_venc = (mes_futuro + relativedelta(day=31)).replace(day=dia_vencimento)

        status = STATUS_PAGO if data_venc < date.today() else STATUS_PENDENTE

        valor_str = f"R$ {float(valor):,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")

        linha = [
            _proximo_id(sheet.get_all_values()),  # novo id por linha
            data_venc.strftime("%Y-%m-%d"),
            tipo,
            categoria,
            descricao,
            valor_str,
            status,
            data_venc.strftime("%Y-%m-%d"),
            TIPO_FIXA,
            "", "", str(id_grupo)
        ]
        linhas.append(linha)

    _gravar_linhas(linhas)
    _limpar_cache()

# ── ADICIONAR COMPRA PARCELADA ───────────────────────────────────────────────
def adicionar_compra_parcelada(tipo, valor_total, categoria, descricao, n_parcelas, data_primeira_parcela):
    """
    Divide o valor total em N parcelas a partir de uma data inicial.
    """
    sheet = conectar()
    todos_valores = sheet.get_all_values()
    id_grupo = _proximo_id_grupo(todos_valores)

    valor_parcela = float(valor_total) / n_parcelas
    data_base = datetime.strptime(data_primeira_parcela, "%Y-%m-%d").date() if isinstance(data_primeira_parcela, str) else data_primeira_parcela

    linhas = []

    for parcela in range(1, n_parcelas + 1):
        venc_parcela = data_base + relativedelta(months=parcela - 1)
        desc_parcela = f"{descricao} ({parcela}/{n_parcelas})"

        valor_str = f"R$ {valor_parcela:,.2f}".replace(".", "#").replace(",", ".").replace("#", ",")

        linha = [
            _proximo_id(sheet.get_all_values()),
            venc_parcela.strftime("%Y-%m-%d"),
            tipo,
            categoria,
            desc_parcela,
            valor_str,
            STATUS_PENDENTE,  # parcelas futuras começam pendentes
            venc_parcela.strftime("%Y-%m-%d"),
            TIPO_PARCELADA,
            parcela,
            n_parcelas,
            str(id_grupo)
        ]
        linhas.append(linha)

    _gravar_linhas(linhas)
    _limpar_cache()

