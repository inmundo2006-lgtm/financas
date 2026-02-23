"""
Aplicativo de Gestão de Finanças Pessoais
Desenvolvido com Streamlit para aprendizado de Python
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
from database import (
    init_database,
    adicionar_transacao,
    adicionar_conta_fixa,
    adicionar_compra_parcelada,
    obter_transacoes,
    obter_todos_com_futuros,
    obter_a_vencer,
    obter_total_pendente_mes,
    obter_resumo_mensal,
    obter_gastos_por_categoria,
    excluir_transacao,
    excluir_grupo,
    marcar_como_pago,
    obter_saldo_acumulado,
    STATUS_PAGO, STATUS_PENDENTE, STATUS_ATRASADO,
    TIPO_NORMAL, TIPO_FIXA, TIPO_PARCELADA,
)

# ── Meses ────────────────────────────────────────────────────────────────────
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

st.set_page_config(page_title="Finanças Pessoais", page_icon="💰", layout="wide")

# CSS (mantido igual)
st.markdown("""<style> ... seu CSS completo ... </style>""", unsafe_allow_html=True)

init_database()

st.title("💰 Gestão de Finanças Pessoais")
st.markdown("---")

with st.sidebar:
    st.header("📊 Menu")
    pagina = st.radio("Navegação:", ["Dashboard", "Nova Transação", "Contas Fixas", "Compras Parceladas", "A Vencer", "Histórico", "Relatórios"])

# (o resto do app.py continua exatamente como você enviou, só a seção "Contas Fixas" foi substituída)

elif pagina == "Contas Fixas":
    st.header("🔄 Cadastrar Conta Fixa Recorrente")
    st.caption("Gera lançamentos mensais automáticos")

    with st.form("form_fixa"):
        col1, col2 = st.columns(2)
        with col1:
            tipo_fixa = st.selectbox("Tipo:", ["Despesa", "Receita"])
            valor_fixa = st.number_input("Valor mensal (R$):", min_value=0.01, step=0.01, format="%.2f")
            dia_venc = st.number_input("Dia de vencimento:", min_value=1, max_value=31, value=10, step=1)
        with col2:
            cat_fixa = st.selectbox("Categoria:", ["Contas", "Moradia", "Transporte", "Saúde", "Educação", "Internet", "Telefone", "Outras Despesas"])
            desc_fixa = st.text_input("Descrição:", placeholder="Ex: Conta de luz")
            data_primeira_input = st.date_input("Data da primeira parcela (opcional)", value=None, min_value=date.today())
            meses_fixa = st.slider("Gerar para quantos meses:", 1, 36, 12)

        if st.form_submit_button("🔄 Gerar Lançamentos"):
            if not desc_fixa.strip() or valor_fixa <= 0:
                st.error("Preencha todos os campos obrigatórios.")
            else:
                data_primeira_str = data_primeira_input.strftime("%Y-%m-%d") if data_primeira_input else None
                adicionar_conta_fixa(
                    tipo=tipo_fixa,
                    valor=valor_fixa,
                    categoria=cat_fixa,
                    descricao=desc_fixa.strip(),
                    dia_vencimento=int(dia_venc),
                    meses_a_adicionar=meses_fixa,
                    data_primeira=data_primeira_str
                )
                st.success("Lançamentos gerados com sucesso!")
                st.rerun()

# (o resto do seu app.py fica igual)
