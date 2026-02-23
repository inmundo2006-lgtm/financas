import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database import (
    init_database,
    adicionar_transacao,
    obter_transacoes,
    excluir_transacao,
    obter_resumo_mensal,
    obter_gastos_por_categoria
)

# ============================
# CONFIGURAÇÃO DO APP
# ============================

st.set_page_config(
    page_title="Gestão Financeira",
    page_icon="💰",
    layout="wide"
)

init_database()

# ============================
# MENU LATERAL
# ============================

st.sidebar.title("📊 Menu")
pagina = st.sidebar.radio("Navegação:", ["Dashboard", "Nova Transação", "Histórico", "Relatórios"])

st.sidebar.info("💡 Dica: Use este app para controlar suas receitas e despesas!")

# ============================
# PÁGINA: NOVA TRANSAÇÃO
# ============================

if pagina == "Nova Transação":
    st.title("💰 Gestão de Finanças Pessoais")
    st.header("➕ Adicionar Nova Transação")

    tipo = st.radio("Tipo de Transação:", ["Receita", "Despesa"])
    valor = st.number_input("Valor (R$):", min_value=0.0, format="%.2f")
    data = st.date_input("Data:", value=date.today())
    st.write(f"📅 Data selecionada: {data.strftime('%d/%m/%Y')}")

    categoria = st.selectbox("Categoria:", [
        "Salário", "Alimentação", "Transporte", "Lazer", "Moradia",
        "Saúde", "Educação", "Investimentos", "Outros"
    ])

    descricao = st.text_input("Descrição:")

    if st.button("Salvar Transação"):
        adicionar_transacao(
            tipo=tipo,
            valor=float(valor),
            categoria=categoria,
            descricao=descricao,
            data=str(data)  # 🔥 CORREÇÃO DEFINITIVA
        )
        st.success("Transação adicionada com sucesso!")

# ============================
# PÁGINA: HISTÓRICO
# ============================

elif pagina == "Histórico":
    st.title("📜 Histórico de Transações")

    df = obter_transacoes()

    if df.empty:
        st.warning("Nenhuma transação encontrada.")
    else:
        st.dataframe(df)

        id_excluir = st.number_input("ID da transação para excluir:", min_value=1, step=1)

        if st.button("Excluir"):
            if excluir_transacao(id_excluir):
                st.success("Transação excluída!")
            else:
                st.error("ID não encontrado.")

# ============================
# PÁGINA: DASHBOARD
# ============================

elif pagina == "Dashboard":
    st.title("📊 Dashboard Financeiro")

    hoje = date.today()
    mes = hoje.month
    ano = hoje.year

    resumo = obter_resumo_mensal(mes, ano)

    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R$ {resumo['receitas']:.2f}")
    col2.metric("Despesas", f"R$ {resumo['despesas']:.2f}")
    col3.metric("Total de Transações", resumo["total_transacoes"])

    df = obter_transacoes(mes, ano)

    if not df.empty:
        fig = px.bar(df, x="data", y="valor", color="tipo", title="Movimentações do Mês")
        st.plotly_chart(fig, use_container_width=True)

# ============================
# PÁGINA: RELATÓRIOS
# ============================

elif pagina == "Relatórios":
    st.title("📈 Relatórios Financeiros")

    mes = st.selectbox("Selecione o mês:", list(range(1, 13)))
    ano = st.number_input("Ano:", min_value=2000, max_value=2100, value=date.today().year)

    df = obter_transacoes(mes, ano)

    if df.empty:
        st.warning("Nenhuma transação encontrada para o período.")
    else:
        st.subheader("📌 Gastos por Categoria")
        gastos = obter_gastos_por_categoria(mes, ano)

        if gastos.empty:
            st.info("Nenhuma despesa registrada.")
        else:
            fig = px.pie(gastos, names="categoria", values="total", title="Distribuição de Gastos")
            st.plotly_chart(fig, use_container_width=True)
