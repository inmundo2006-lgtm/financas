import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2.service_account import Credentials

COLUNAS = [
    "id", "data", "tipo", "categoria", "descricao", "valor",
    "status", "data_vencimento", "tipo_lancamento",
    "parcela_atual", "total_parcelas", "id_grupo", "observacao"
]

STATUS_PAGO     = "Pago"
STATUS_PENDENTE = "Pendente"
STATUS_ATRASADO = "Atrasado"
TIPO_NORMAL    = "Normal"
TIPO_FIXA      = "Fixa"
TIPO_PARCELADA = "Parcelada"


@st.cache_resource
def conectar():
    creds_info = st.secrets["google_service_account"]
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return client.open_by_url(spreadsheet_url).worksheet("transacoes")


@st.cache_data(ttl=10)
def _ler_dataframe():
    sheet = conectar()
    valores = sheet.get_all_values()
    if len(valores) <= 1:
        return pd.DataFrame(columns=COLUNAS)
    df = pd.DataFrame(valores[1:], columns=valores[0])
    return df


def _limpar_cache():
    _ler_dataframe.clear()


def init_database():
    sheet = conectar()
    valores = sheet.get_all_values()
    if not valores:
        sheet.append_rows([COLUNAS], value_input_option="USER_ENTERED")
        return
    cabecalho = valores[0]
    # Adiciona colunas faltantes (incluindo "observacao" para planilhas existentes)
    if len(cabecalho) < len(COLUNAS):
        for i, col in enumerate(COLUNAS[len(cabecalho):]):
            sheet.update_cell(1, len(cabecalho) + i + 1, col)
        _limpar_cache()


def _proximo_id(todos_valores):
    ids = []
    for linha in todos_valores[1:]:
        try:
            ids.append(int(linha[0]))
        except (ValueError, IndexError):
            pass
    return max(ids) + 1 if ids else 1


def _proximo_id_grupo(todos_valores):
    grupos = []
    for linha in todos_valores[1:]:
        try:
            if linha[11]:
                grupos.append(int(linha[11]))
        except (ValueError, IndexError):
            pass
    return max(grupos) + 1 if grupos else 1


def _gravar_linhas(linhas):
    sheet = conectar()
    sheet.append_rows(linhas, value_input_option="USER_ENTERED", table_range="A1")
    _limpar_cache()


def _reescrever_planilha(df):
    sheet = conectar()
    sheet.clear()
    sheet.append_rows([COLUNAS], value_input_option="USER_ENTERED")
    if not df.empty:
        sheet.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    _limpar_cache()


def _preparar_df(df):
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = ""
    df["data"]            = pd.to_datetime(df["data"], errors="coerce")
    df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], errors="coerce")
    def _normalizar_valor(v):
        s = str(v).strip()
        if "," in s and "." in s:
            return s.replace(".", "").replace(",", ".")
        elif "," in s:
            return s.replace(",", ".")
        return s
    df["valor"] = pd.to_numeric(df["valor"].astype(str).apply(_normalizar_valor), errors="coerce")
    df["id"]              = pd.to_numeric(df["id"], errors="coerce")
    df["parcela_atual"]   = pd.to_numeric(df["parcela_atual"], errors="coerce")
    df["total_parcelas"]  = pd.to_numeric(df["total_parcelas"], errors="coerce")
    df["id_grupo"]        = pd.to_numeric(df["id_grupo"], errors="coerce")
    df["observacao"]      = df["observacao"].fillna("").astype(str)
    df = df.dropna(subset=["data", "valor"])
    df["status"]          = df["status"].replace("", STATUS_PAGO).fillna(STATUS_PAGO)
    df["tipo_lancamento"] = df["tipo_lancamento"].replace("", TIPO_NORMAL).fillna(TIPO_NORMAL)
    hoje = pd.Timestamp(date.today())
    mask = (
        (df["status"] == STATUS_PENDENTE) &
        (df["data_vencimento"].notna()) &
        (df["data_vencimento"] < hoje)
    )
    df.loc[mask, "status"] = STATUS_ATRASADO
    return df


def obter_transacoes(mes=None, ano=None):
    df = _preparar_df(_ler_dataframe().copy())
    if df.empty:
        return df
    hoje = pd.Timestamp(date.today())
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
    df = _preparar_df(_ler_dataframe().copy())
    if df.empty:
        return df
    if mes:
        ref = df["data_vencimento"].fillna(df["data"])
        df = df[ref.dt.month == mes]
    if ano:
        ref = df["data_vencimento"].fillna(df["data"])
        df = df[ref.dt.year == ano]
    return df.reset_index(drop=True)


def obter_a_vencer(dias=30):
    df = _preparar_df(_ler_dataframe().copy())
    if df.empty:
        return pd.DataFrame(columns=COLUNAS)
    hoje  = pd.Timestamp(date.today())
    limite = hoje + pd.Timedelta(days=dias)
    return df[
        (df["status"] == STATUS_PENDENTE) &
        (df["data_vencimento"].notna()) &
        (df["data_vencimento"] >= hoje) &
        (df["data_vencimento"] <= limite)
    ].sort_values("data_vencimento").reset_index(drop=True)


def obter_resumo_mensal(mes, ano):
    df = obter_todos_com_futuros(mes, ano)
    if df.empty:
        return {"receitas": 0.0, "despesas": 0.0,
                "receitas_pagas": 0.0, "despesas_pagas": 0.0,
                "total_transacoes": 0}
    receitas       = df[df["tipo"] == "Receita"]["valor"].sum()
    despesas       = df[df["tipo"] == "Despesa"]["valor"].sum()
    rec_pagas      = df[(df["tipo"] == "Receita") & (df["status"] == STATUS_PAGO)]["valor"].sum()
    desp_pagas     = df[(df["tipo"] == "Despesa") & (df["status"] == STATUS_PAGO)]["valor"].sum()
    return {
        "receitas": float(receitas), "despesas": float(despesas),
        "receitas_pagas": float(rec_pagas), "despesas_pagas": float(desp_pagas),
        "total_transacoes": len(df)
    }


def obter_total_pendente_mes(mes, ano):
    df = obter_todos_com_futuros(mes, ano)
    if df.empty:
        return 0.0
    mask = (df["tipo"] == "Despesa") & (df["status"].isin([STATUS_PENDENTE, STATUS_ATRASADO]))
    return float(df.loc[mask, "valor"].sum())


def obter_gastos_por_categoria(mes, ano):
    df = obter_transacoes(mes, ano)
    if df.empty:
        return pd.DataFrame()
    despesas = df[(df["tipo"] == "Despesa") & (df["status"] == STATUS_PAGO)]
    if despesas.empty:
        return pd.DataFrame()
    return despesas.groupby("categoria")["valor"].sum().reset_index(name="total")


def obter_saldo_acumulado():
    df = _preparar_df(_ler_dataframe().copy())
    if df.empty:
        return 0.0
    pagos = df[df["status"] == STATUS_PAGO]
    return float(pagos[pagos["tipo"] == "Receita"]["valor"].sum() -
                 pagos[pagos["tipo"] == "Despesa"]["valor"].sum())


def obter_disponivel_gastar(mes, ano):
    df = _preparar_df(_ler_dataframe().copy())
    if df.empty:
        return 0.0, 0.0, 0.0
    pagos = df[df["status"] == STATUS_PAGO]
    saldo_atual = float(
        pagos[pagos["tipo"] == "Receita"]["valor"].sum() -
        pagos[pagos["tipo"] == "Despesa"]["valor"].sum()
    )
    ref = df["data_vencimento"].fillna(df["data"])
    do_mes = df[
        (df["tipo"] == "Despesa") &
        (df["status"].isin([STATUS_PENDENTE, STATUS_ATRASADO])) &
        (ref.dt.month == mes) &
        (ref.dt.year == ano)
    ]
    total_compromissos = float(do_mes["valor"].sum())
    disponivel = saldo_atual - total_compromissos
    return disponivel, saldo_atual, total_compromissos


def obter_saldo_anterior(mes, ano):
    df = _preparar_df(_ler_dataframe().copy())
    if df.empty:
        return 0.0
    ref = df["data_vencimento"].fillna(df["data"])
    data_corte = pd.Timestamp(year=ano, month=mes, day=1)
    anteriores = df[
        (df["status"].isin([STATUS_PAGO, STATUS_ATRASADO])) & (ref < data_corte)
    ]
    if anteriores.empty:
        return 0.0
    receitas = anteriores[anteriores["tipo"] == "Receita"]["valor"].sum()
    despesas = anteriores[anteriores["tipo"] == "Despesa"]["valor"].sum()
    return float(receitas - despesas)


def adicionar_transacao(tipo, valor, categoria, descricao, data,
                        status=STATUS_PAGO, data_vencimento=None, observacao=""):
    sheet = conectar()
    todos = sheet.get_all_values()
    dv = str(data_vencimento) if data_vencimento else (data if isinstance(data, str) else str(data))
    linha = [
        _proximo_id(todos),
        data if isinstance(data, str) else str(data),
        tipo, categoria, descricao, float(valor),
        status, dv, TIPO_NORMAL, "", "", "",
        str(observacao).strip()
    ]
    _gravar_linhas([linha])


def adicionar_conta_fixa(tipo, valor, categoria, descricao,
                         dia_vencimento, meses_a_adicionar=12,
                         data_primeira=None, observacao=""):
    import calendar
    sheet = conectar()
    todos  = sheet.get_all_values()
    id_grp = _proximo_id_grupo(todos)
    id_base = _proximo_id(todos)
    hoje   = date.today()

    if data_primeira:
        data_atual = (datetime.strptime(data_primeira, "%Y-%m-%d").date()
                      if isinstance(data_primeira, str) else data_primeira)
    else:
        try:
            data_atual = hoje.replace(day=dia_vencimento)
        except ValueError:
            data_atual = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

    linhas = []
    for i in range(meses_a_adicionar):
        status = STATUS_PAGO if data_atual <= hoje else STATUS_PENDENTE
        linhas.append([
            id_base + i, str(hoje), tipo, categoria, descricao,
            float(valor), status, str(data_atual), TIPO_FIXA, "", "", str(id_grp),
            str(observacao).strip()
        ])
        prox = data_atual + relativedelta(months=1)
        try:
            data_atual = prox.replace(day=dia_vencimento)
        except ValueError:
            data_atual = prox.replace(day=calendar.monthrange(prox.year, prox.month)[1])

    _gravar_linhas(linhas)


def adicionar_compra_parcelada(tipo, valor_total, categoria, descricao,
                                n_parcelas, data_primeira, observacao=""):
    sheet   = conectar()
    todos   = sheet.get_all_values()
    id_grp  = _proximo_id_grupo(todos)
    id_base = _proximo_id(todos)
    valor_p = round(float(valor_total) / n_parcelas, 2)
    hoje    = date.today()
    data_b  = (data_primeira if isinstance(data_primeira, date)
               else datetime.strptime(str(data_primeira), "%Y-%m-%d").date())

    linhas = []
    for p in range(1, n_parcelas + 1):
        venc   = data_b + relativedelta(months=p - 1)
        status = STATUS_PAGO if venc <= hoje else STATUS_PENDENTE
        linhas.append([
            id_base + (p - 1), str(hoje), tipo, categoria,
            f"{descricao} ({p}/{n_parcelas})",
            float(valor_p), status, str(venc),
            TIPO_PARCELADA, p, n_parcelas, str(id_grp),
            str(observacao).strip()
        ])
    _gravar_linhas(linhas)


def marcar_como_pago(id_transacao, novo_valor=None):
    df = _ler_dataframe().copy()
    if df.empty:
        return False
    mask = df["id"] == str(id_transacao)
    df.loc[mask, "status"] = STATUS_PAGO
    if novo_valor is not None:
        df.loc[mask, "valor"] = float(novo_valor)
    _reescrever_planilha(df)
    return True


def excluir_transacao(id_transacao):
    df  = _ler_dataframe().copy()
    if df.empty:
        return False
    novo = df[df["id"] != str(id_transacao)]
    if len(novo) == len(df):
        return False
    _reescrever_planilha(novo)
    return True


def excluir_grupo(id_grupo):
    df = _ler_dataframe().copy()
    if df.empty:
        return 0
    novo = df[df["id_grupo"] != str(id_grupo)]
    removidos = len(df) - len(novo)
    if removidos == 0:
        return 0
    _reescrever_planilha(novo)
    return removidos
