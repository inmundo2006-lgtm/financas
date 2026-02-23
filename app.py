"""
Aplicativo de Gestão de Finanças Pessoais
Desenvolvido com Streamlit para aprendizado de Python
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from database import (
    init_database,
    adicionar_transacao,
    obter_transacoes,
    obter_resumo_mensal,
    obter_gastos_por_categoria,
    excluir_transacao
)

# ── Meses em português ──────────────────────────────────────────────────────
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Finanças Pessoais",
    page_icon="💰",
    layout="wide"
)

# ── CSS personalizado ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Paleta e tipografia */
    :root {
        --verde:  #00c896;
        --vermelho: #ff4f6d;
        --azul:   #3b82f6;
        --fundo:  #0f1117;
        --card:   #1a1d27;
        --borda:  #2a2d3a;
        --texto:  #e2e8f0;
        --muted:  #8892a4;
    }

    /* Cards de métricas */
    div[data-testid="metric-container"] {
        background: var(--card);
        border: 1px solid var(--borda);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        transition: transform .15s, box-shadow .15s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,.4);
    }

    /* Separadores mais suaves */
    hr { border-color: var(--borda) !important; }

    /* Badge de tipo na tabela */
    .badge-receita {
        background: rgba(0,200,150,.15);
        color: #00c896;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: .8rem;
        font-weight: 600;
    }
    .badge-despesa {
        background: rgba(255,79,109,.15);
        color: #ff4f6d;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: .8rem;
        font-weight: 600;
    }

    /* Aviso de saldo negativo */
    .alerta-negativo {
        background: rgba(255,79,109,.1);
        border-left: 3px solid #ff4f6d;
        padding: .6rem 1rem;
        border-radius: 0 8px 8px 0;
        color: #ff4f6d;
        font-weight: 600;
        margin-top: .5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Inicializar BD ──────────────────────────────────────────────────────────
init_database()

# ── Título ──────────────────────────────────────────────────────────────────
st.title("💰 Gestão de Finanças Pessoais")
st.markdown("---")

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📊 Menu")
    pagina = st.radio(
        "Navegação:",
        ["Dashboard", "Nova Transação", "Histórico", "Relatórios"]
    )
    st.markdown("---")
    st.info("💡 **Dica:** Use este app para controlar suas receitas e despesas!")


# ════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════
if pagina == "Dashboard":
    st.header("📈 Dashboard Financeiro")

    col1, col2 = st.columns(2)
    with col1:
        mes_selecionado = st.selectbox(
            "Mês:", range(1, 13),
            index=datetime.now().month - 1,
            format_func=lambda x: MESES_PT[x]
        )
    with col2:
        ano_selecionado = st.selectbox(
            "Ano:", range(2020, 2031),
            index=list(range(2020, 2031)).index(datetime.now().year)
        )

    resumo = obter_resumo_mensal(mes_selecionado, ano_selecionado)
    saldo = resumo["receitas"] - resumo["despesas"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 Receitas", f"R$ {resumo['receitas']:,.2f}")
    with col2:
        st.metric("💸 Despesas", f"R$ {resumo['despesas']:,.2f}")
    with col3:
        st.metric(
            "💰 Saldo",
            f"R$ {saldo:,.2f}",
            delta=f"R$ {saldo:,.2f}" if saldo >= 0 else f"-R$ {abs(saldo):,.2f}",
            delta_color="normal" if saldo >= 0 else "inverse"
        )
        if saldo < 0:
            st.markdown(
                '<div class="alerta-negativo">⚠️ Despesas acima das receitas!</div>',
                unsafe_allow_html=True
            )
    with col4:
        st.metric("📝 Transações", resumo["total_transacoes"])

    st.markdown("---")

    if resumo["total_transacoes"] > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Despesas por Categoria")
            gastos = obter_gastos_por_categoria(mes_selecionado, ano_selecionado)
            if not gastos.empty:
                fig = px.pie(
                    gastos, values="total", names="categoria",
                    title="Distribuição de Despesas",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma despesa registrada neste período")

        with col2:
            st.subheader("📈 Evolução Diária Acumulada")
            transacoes = obter_transacoes(mes_selecionado, ano_selecionado)

            if not transacoes.empty:
                # ── Corrigido: gera série contínua por dia do mês ──────────
                transacoes["dia"] = transacoes["data"].dt.day
                max_dia = transacoes["dia"].max()
                todos_dias = pd.DataFrame({"dia": range(1, max_dia + 1)})

                rec_dia = (
                    transacoes[transacoes["tipo"] == "Receita"]
                    .groupby("dia")["valor"].sum()
                    .reindex(range(1, max_dia + 1), fill_value=0)
                    .cumsum()
                    .reset_index()
                    .rename(columns={"valor": "Receitas"})
                )
                desp_dia = (
                    transacoes[transacoes["tipo"] == "Despesa"]
                    .groupby("dia")["valor"].sum()
                    .reindex(range(1, max_dia + 1), fill_value=0)
                    .cumsum()
                    .reset_index()
                    .rename(columns={"valor": "Despesas"})
                )
                evolucao = rec_dia.merge(desp_dia, on="dia")

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=evolucao["dia"], y=evolucao["Receitas"],
                    mode="lines+markers", name="Receitas",
                    line=dict(color="#00c896", width=2.5),
                    fill="tozeroy", fillcolor="rgba(0,200,150,.08)"
                ))
                fig.add_trace(go.Scatter(
                    x=evolucao["dia"], y=evolucao["Despesas"],
                    mode="lines+markers", name="Despesas",
                    line=dict(color="#ff4f6d", width=2.5),
                    fill="tozeroy", fillcolor="rgba(255,79,109,.08)"
                ))
                fig.update_layout(
                    title="Acumulado no Mês",
                    xaxis_title="Dia", yaxis_title="Valor (R$)",
                    hovermode="x unified",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                    xaxis=dict(gridcolor="#2a2d3a"),
                    yaxis=dict(gridcolor="#2a2d3a")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhuma transação registrada neste período")
    else:
        st.info("🚀 Nenhuma transação ainda. Comece adicionando uma nova transação!")


# ════════════════════════════════════════════════════════════════
# NOVA TRANSAÇÃO
# ════════════════════════════════════════════════════════════════
elif pagina == "Nova Transação":
    st.header("➕ Adicionar Nova Transação")

    tipo = st.selectbox("Tipo de Transação:", ["Receita", "Despesa"], key="tipo_transacao")

    categorias_receita = ["Salário", "Freelance", "Investimentos", "Presente", "Outras Receitas"]
    categorias_despesa = [
        "Alimentação", "Transporte", "Moradia", "Saúde",
        "Educação", "Lazer", "Compras", "Contas", "Outras Despesas"
    ]
    categorias = categorias_receita if tipo == "Receita" else categorias_despesa

    st.markdown("---")

    with st.form("form_transacao", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            valor = st.number_input(
                "Valor (R$):", min_value=0.01, step=0.01, format="%.2f",
                help="O valor deve ser maior que R$ 0,00"
            )
            data = st.date_input("Data:", value=datetime.now(), format="DD/MM/YYYY")
            st.caption(f"📅 Data selecionada: {data.strftime('%d/%m/%Y')}")

        with col2:
            categoria = st.selectbox("Categoria:", categorias)
            descricao = st.text_input(
                "Descrição:", placeholder="Ex: Supermercado, Conta de luz...",
                max_chars=100
            )

        submitted = st.form_submit_button("💾 Salvar Transação", use_container_width=True)

        if submitted:
            erros = []
            if not descricao.strip():
                erros.append("Adicione uma descrição para a transação.")
            if valor <= 0:
                erros.append("O valor precisa ser maior que R$ 0,00.")

            if erros:
                for e in erros:
                    st.error(f"⚠️ {e}")
            else:
                with st.spinner("Salvando..."):
                    adicionar_transacao(
                        tipo=tipo,
                        valor=valor,
                        categoria=categoria,
                        descricao=descricao.strip(),
                        data=str(data)
                    )
                st.success(f"✅ {tipo} de **R$ {valor:,.2f}** ({categoria}) adicionada com sucesso!")
                if tipo == "Receita":
                    st.balloons()
                else:
                    st.snow()


# ════════════════════════════════════════════════════════════════
# HISTÓRICO
# ════════════════════════════════════════════════════════════════
elif pagina == "Histórico":
    st.header("📜 Histórico de Transações")

    col1, col2, col3 = st.columns(3)
    with col1:
        mes_filtro = st.selectbox(
            "Filtrar por mês:",
            ["Todos"] + list(range(1, 13)),
            format_func=lambda x: "Todos os meses" if x == "Todos" else MESES_PT[x]
        )
    with col2:
        ano_filtro = st.selectbox(
            "Filtrar por ano:",
            ["Todos"] + list(range(2020, 2031)),
            format_func=lambda x: "Todos os anos" if x == "Todos" else str(x)
        )
    with col3:
        tipo_filtro = st.selectbox("Tipo:", ["Todos", "Receita", "Despesa"])

    mes = None if mes_filtro == "Todos" else mes_filtro
    ano = None if ano_filtro == "Todos" else ano_filtro

    transacoes = obter_transacoes(mes, ano)

    if tipo_filtro != "Todos":
        transacoes = transacoes[transacoes["tipo"] == tipo_filtro]

    if not transacoes.empty:
        total_rec = transacoes[transacoes["tipo"] == "Receita"]["valor"].sum()
        total_desp = transacoes[transacoes["tipo"] == "Despesa"]["valor"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Registros", len(transacoes))
        c2.metric("💵 Receitas filtradas", f"R$ {total_rec:,.2f}")
        c3.metric("💸 Despesas filtradas", f"R$ {total_desp:,.2f}")

        st.markdown("---")

        exibir = transacoes.copy()
        exibir["data"] = pd.to_datetime(exibir["data"]).dt.strftime("%d/%m/%Y")
        exibir["valor_fmt"] = exibir["valor"].apply(lambda x: f"R$ {x:,.2f}")
        exibir = exibir[["id", "data", "tipo", "categoria", "descricao", "valor_fmt"]]
        exibir.columns = ["ID", "Data", "Tipo", "Categoria", "Descrição", "Valor"]

        st.dataframe(exibir, use_container_width=True, hide_index=True)

        # ── Exclusão segura via selectbox ──────────────────────────────
        st.markdown("---")
        st.subheader("🗑️ Excluir Transação")
        st.caption("Selecione a transação que deseja remover. A ação é irreversível.")

        opcoes = {
            f"[{int(row['ID'])}] {row['Data']} · {row['Tipo']} · {row['Categoria']} · {row['Descrição']} · {row['Valor']}": int(row["ID"])
            for _, row in exibir.iterrows()
        }
        selecao = st.selectbox("Escolha a transação:", list(opcoes.keys()))

        col_btn, col_aviso = st.columns([1, 3])
        with col_btn:
            confirmar = st.checkbox("✅ Confirmar exclusão")
            if st.button("🗑️ Excluir", use_container_width=True, type="primary", disabled=not confirmar):
                id_excluir = opcoes[selecao]
                with st.spinner("Excluindo..."):
                    if excluir_transacao(id_excluir):
                        st.success("Transação excluída com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir. Tente novamente.")
        with col_aviso:
            if confirmar:
                st.warning(f"⚠️ Você está prestes a excluir: **{selecao}**")
    else:
        st.warning("Nenhuma transação encontrada com os filtros selecionados.")


# ════════════════════════════════════════════════════════════════
# RELATÓRIOS
# ════════════════════════════════════════════════════════════════
elif pagina == "Relatórios":
    st.header("📊 Relatórios Detalhados")

    col1, col2 = st.columns(2)
    with col1:
        mes_relatorio = st.selectbox(
            "Mês:", range(1, 13),
            index=datetime.now().month - 1,
            format_func=lambda x: MESES_PT[x]
        )
    with col2:
        ano_relatorio = st.selectbox(
            "Ano:", range(2020, 2031),
            index=list(range(2020, 2031)).index(datetime.now().year)
        )

    transacoes = obter_transacoes(mes_relatorio, ano_relatorio)

    if not transacoes.empty:
        despesas = transacoes[transacoes["tipo"] == "Despesa"]
        receitas = transacoes[transacoes["tipo"] == "Receita"]

        # ── Gráfico de barras por categoria ───────────────────────────
        st.subheader("📊 Comparativo por Categoria")

        if not despesas.empty:
            desp_cat = despesas.groupby("categoria")["valor"].sum().reset_index()
            fig_bar = px.bar(
                desp_cat.sort_values("valor", ascending=True),
                x="valor", y="categoria", orientation="h",
                title="Despesas por Categoria",
                color="valor",
                color_continuous_scale=["#ff4f6d", "#ffb347"],
                labels={"valor": "Total (R$)", "categoria": ""}
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                xaxis=dict(gridcolor="#2a2d3a"),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # ── Resumo por categoria ───────────────────────────────────────
        st.subheader("💳 Análise por Categoria")
        col1, col2 = st.columns(2)

        with col1:
            if not despesas.empty:
                st.markdown("**📉 Despesas:**")
                desp_cat = despesas.groupby("categoria")["valor"].sum().sort_values(ascending=False)
                total_desp = desp_cat.sum()
                for cat, val in desp_cat.items():
                    pct = val / total_desp * 100
                    st.write(f"• **{cat}**: R$ {val:,.2f} ({pct:.1f}%)")
                    st.progress(pct / 100)
            else:
                st.info("Nenhuma despesa no período")

        with col2:
            if not receitas.empty:
                st.markdown("**📈 Receitas:**")
                rec_cat = receitas.groupby("categoria")["valor"].sum().sort_values(ascending=False)
                total_rec = rec_cat.sum()
                for cat, val in rec_cat.items():
                    pct = val / total_rec * 100
                    st.write(f"• **{cat}**: R$ {val:,.2f} ({pct:.1f}%)")
                    st.progress(pct / 100)
            else:
                st.info("Nenhuma receita no período")

        st.markdown("---")

        # ── Exportar ───────────────────────────────────────────────────
        st.subheader("💾 Exportar Dados")
        csv = transacoes.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name=f"financas_{MESES_PT[mes_relatorio]}_{ano_relatorio}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("Nenhuma transação encontrada no período selecionado.")


# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center;color:#8892a4;font-size:.85rem;'>
        💡 <b>Desenvolvido para aprendizado de Python</b> &nbsp;·&nbsp;
        Streamlit + Google Sheets + Plotly
    </div>
    """,
    unsafe_allow_html=True
)
